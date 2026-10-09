import asyncio
import logging

import a2s

from greenfieldbot.gcp.compute import (
    get_compute_service,
    get_external_ip,
    get_instance,
    stop_instance,
)

logger = logging.getLogger(__name__)

# Check for players every minute.
CHECK_INTERVAL = 60

# Wait 15 minutes before shutting down an empty server.
RESPONSE_TIMEOUT = 15 * 60

# Recheck player activity every minute during the grace period.
PLAYER_POLL_INTERVAL = 60

# Maximum time to wait for an A2S query.
A2S_QUERY_TIMEOUT = 5.0

# Valheim Steam server query port.
A2S_PORT = 2457


class ValheimMonitor:
    def __init__(self, bot, channel_id: int | None = None):
        self.bot = bot
        self.channel_id = channel_id
        self._monitor_task: asyncio.Task | None = None

    def start(self):
        """Start the background monitoring task if it isn't already running."""
        if self._monitor_task and not self._monitor_task.done():
            logger.info("Valheim monitor is already running.")
            return

        self._monitor_task = asyncio.create_task(
            self._monitor(),
            name="valheim-monitor",
        )
        logger.info("Valheim monitor started.")

    async def stop(self):
        """Cancel the background monitoring task."""
        if self._monitor_task and not self._monitor_task.done():
            self._monitor_task.cancel()

            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass

            logger.info("Valheim monitor stopped.")

        self._monitor_task = None

    async def _monitor(self):
        """Check activity regularly and stop the VM after 15 idle minutes."""
        while True:
            try:
                service = await asyncio.to_thread(get_compute_service)
                instance = await asyncio.to_thread(get_instance, service)

                status = instance.get("status")

                if status != "RUNNING":
                    logger.debug(
                        "Valheim VM is %s; checking again in %d seconds.",
                        status or "in an unknown state",
                        CHECK_INTERVAL,
                    )
                    await asyncio.sleep(CHECK_INTERVAL)
                    continue

                host = get_external_ip(instance)

                if not host:
                    logger.warning(
                        "Valheim VM has no external IP; will retry in %d seconds.",
                        CHECK_INTERVAL,
                    )
                    await asyncio.sleep(CHECK_INTERVAL)
                    continue

                player_count = await self._get_player_count(host)

                if player_count is None:
                    logger.warning(
                        "Could not determine Valheim player count; "
                        "keeping the VM running and retrying in %d seconds.",
                        CHECK_INTERVAL,
                    )
                    await asyncio.sleep(CHECK_INTERVAL)
                    continue

                if player_count > 0:
                    logger.debug(
                        "Valheim has %d player(s) online.",
                        player_count,
                    )
                    await asyncio.sleep(CHECK_INTERVAL)
                    continue

                logger.info(
                    "A2S reports zero players. "
                    "Starting the 15-minute shutdown grace period."
                )

                result = await self._wait_for_activity(host)

                if result == "active":
                    logger.info("Player activity detected; cancelling shutdown.")
                    continue

                if result == "unknown":
                    logger.warning(
                        "Player count became unknown during the grace period; "
                        "cancelling shutdown."
                    )
                    await asyncio.sleep(CHECK_INTERVAL)
                    continue

                # Verify again immediately before requesting shutdown.
                final_count = await self._get_player_count(host)

                if final_count is None:
                    logger.warning("Final A2S query failed; cancelling shutdown.")
                    await asyncio.sleep(CHECK_INTERVAL)
                    continue

                if final_count > 0:
                    logger.info(
                        "Final A2S check found %d player(s); cancelling shutdown.",
                        final_count,
                    )
                    continue

                await self._shutdown_vm()

                # Avoid repeatedly querying the VM immediately after shutdown.
                await asyncio.sleep(CHECK_INTERVAL)

            except asyncio.CancelledError:
                logger.info("Valheim monitor task cancelled.")
                raise

            except Exception:
                logger.exception(
                    "Unexpected error during Valheim monitoring cycle. "
                    "Retrying in %d seconds.",
                    CHECK_INTERVAL,
                )
                await asyncio.sleep(CHECK_INTERVAL)

    async def _get_player_count(self, host: str) -> int | None:
        """
        Return the current A2S player count.

        Returns None if the query fails or the response is invalid.
        Never interpret an unknown count as zero.
        """
        try:
            info = await asyncio.to_thread(
                a2s.info,
                (host, A2S_PORT),
                timeout=A2S_QUERY_TIMEOUT,
            )

            player_count = getattr(info, "player_count", None)

            if (
                not isinstance(player_count, int)
                or isinstance(player_count, bool)
                or player_count < 0
            ):
                logger.warning(
                    "A2S returned an invalid player count: %r",
                    player_count,
                )
                return None

            logger.debug(
                "A2S query for %s:%d reports %d player(s).",
                host,
                A2S_PORT,
                player_count,
            )
            return player_count

        except Exception as exc:
            logger.warning(
                "A2S query failed for %s:%d: %s",
                host,
                A2S_PORT,
                exc,
            )
            return None

    async def _wait_for_activity(self, host: str) -> str:
        """
        Monitor player activity during the shutdown grace period.

        Returns:
            "active"  - players were detected.
            "empty"   - the entire grace period passed with zero players.
            "unknown" - a query failed, so shutdown cannot be confirmed.
        """
        loop = asyncio.get_running_loop()
        deadline = loop.time() + RESPONSE_TIMEOUT

        while True:
            remaining = deadline - loop.time()

            if remaining <= 0:
                logger.info("The 15-minute grace period elapsed with no players.")
                return "empty"

            await asyncio.sleep(min(PLAYER_POLL_INTERVAL, remaining))

            player_count = await self._get_player_count(host)

            if player_count is None:
                return "unknown"

            if player_count > 0:
                logger.info(
                    "Detected %d player(s) during the grace period.",
                    player_count,
                )
                return "active"

            logger.info(
                "Grace-period check: zero players. %.0f seconds remaining.",
                max(0, deadline - loop.time()),
            )

    async def _shutdown_vm(self):
        """Stop the VM only if Google Cloud confirms it is still running."""
        try:
            service = await asyncio.to_thread(get_compute_service)
            instance = await asyncio.to_thread(get_instance, service)

            status = instance.get("status")

            if status != "RUNNING":
                logger.info(
                    "Valheim VM is %s; no shutdown request needed.",
                    status or "in an unknown state",
                )
                return

            logger.info("Requesting shutdown of the Valheim VM.")

            await asyncio.to_thread(stop_instance, service)

            logger.info("Valheim VM shutdown request submitted.")

        except Exception:
            logger.exception(
                "Failed to stop the Valheim VM. The monitor will continue running."
            )
