import asyncio
import logging

from greenfieldbot.gcp.compute import (
    get_compute_service,
    get_external_ip,
    get_instance,
    stop_instance,
)
from greenfieldbot.services.valheim import get_player_info

logger = logging.getLogger(__name__)

# Check for players every minute.
CHECK_INTERVAL = 60

# Wait 15 minutes before shutting down an empty server.
RESPONSE_TIMEOUT = 15 * 60

# Recheck player activity every minute during the grace period.
PLAYER_POLL_INTERVAL = 60


class ValheimMonitor:
    def __init__(self, bot, channel_id: int | None = None):
        self.bot = bot
        self.channel_id = channel_id
        self._monitor_task: asyncio.Task | None = None

    def start(self):
        """Start the monitoring task if it is not already running."""
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
        task = self._monitor_task

        if task and not task.done():
            task.cancel()

            try:
                await task
            except asyncio.CancelledError:
                pass

            logger.info("Valheim monitor stopped.")

        self._monitor_task = None

    async def _monitor(self):
        """Monitor player activity and stop the VM after 15 idle minutes."""
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
                        "Valheim VM has no external IP; retrying in %d seconds.",
                        CHECK_INTERVAL,
                    )
                    await asyncio.sleep(CHECK_INTERVAL)
                    continue

                player_count = await self._get_player_count(host)

                if player_count is None:
                    logger.warning(
                        "Could not determine Valheim player count. "
                        "Keeping the VM running and retrying in %d seconds.",
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
                        "Player count became unknown during the grace "
                        "period; cancelling shutdown."
                    )
                    await asyncio.sleep(CHECK_INTERVAL)
                    continue

                # Check again immediately before requesting shutdown.
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

                # Avoid immediately repeating the cycle after shutdown.
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
        Return the player count, or None if the query fails.

        An unknown count must never be interpreted as zero.
        """
        info = await get_player_info(host)

        if info is None:
            return None

        return info.player_count

    async def _wait_for_activity(self, host: str) -> str:
        """
        Monitor player activity throughout the shutdown grace period.

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
        """Request VM shutdown only if Google Cloud confirms it is running."""
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
