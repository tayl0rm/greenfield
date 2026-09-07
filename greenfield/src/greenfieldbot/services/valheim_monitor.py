import asyncio
import logging

import discord
from greenfieldbot.gcp.compute import (
    get_compute_service,
    get_instance,
    stop_instance,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

CHECK_INTERVAL = 3 * 60  # 5 hours
RESPONSE_TIMEOUT = 1 * 60  # 15 minutes


# ---------------------------------------------------------------------------
# Discord confirmation view
# ---------------------------------------------------------------------------


class ServerCheckView(discord.ui.View):
    """Discord UI asking whether the Valheim server should remain online."""

    def __init__(self, monitor: "ValheimMonitor"):
        super().__init__(timeout=RESPONSE_TIMEOUT)

        self.monitor = monitor
        self.response = asyncio.Event()
        self.action: str | None = None

    async def _respond(
        self,
        interaction: discord.Interaction,
        action: str,
        message: str,
    ):
        """Handle a response from either button."""

        # Prevent multiple interactions from being processed.
        if self.action is not None:
            return

        self.action = action

        await interaction.response.send_message(message)

        self.response.set()
        self.stop()

    @discord.ui.button(
        label="Yes",
        style=discord.ButtonStyle.green,
        custom_id="valheim_still_playing_yes",
    )
    async def yes_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        await self._respond(
            interaction,
            "yes",
            "Excellent. The Valheim server will remain online for another 5 hours.",
        )

    @discord.ui.button(
        label="No",
        style=discord.ButtonStyle.red,
        custom_id="valheim_still_playing_no",
    )
    async def no_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        await self._respond(
            interaction,
            "no",
            "Understood. The Valheim server will now shut down.",
        )

    async def on_timeout(self):
        """Handle the user not responding within the timeout period."""

        if self.action is not None:
            return

        self.action = "timeout"
        self.response.set()


# ---------------------------------------------------------------------------
# Valheim monitor
# ---------------------------------------------------------------------------


class ValheimMonitor:
    """Monitors the Valheim server and periodically asks whether it is still
    being used.
    """

    def __init__(self, bot, channel_id: int):
        self.bot = bot
        self.channel_id = channel_id
        self.task: asyncio.Task | None = None

    # -----------------------------------------------------------------------
    # Lifecycle
    # -----------------------------------------------------------------------

    def start(self):
        """Start the monitor if it is not already running."""

        if self.task and not self.task.done():
            logger.info("Valheim monitor is already running.")
            return

        self.task = asyncio.create_task(self._monitor())

        logger.info("Valheim monitor started.")

    async def stop(self):
        """Stop the monitor task."""

        if not self.task or self.task.done():
            self.task = None
            return

        current_task = asyncio.current_task()

        # Don't attempt to cancel ourselves.
        if self.task is current_task:
            return

        self.task.cancel()

        try:
            await self.task
        except asyncio.CancelledError:
            pass

        self.task = None

        logger.info("Valheim monitor stopped.")

    # -----------------------------------------------------------------------
    # Monitoring
    # -----------------------------------------------------------------------

    async def _monitor(self):
        """Main monitoring loop."""

        try:
            while True:
                logger.info(
                    "Valheim activity monitor sleeping for %s hours.",
                    CHECK_INTERVAL / 3600,
                )

                await asyncio.sleep(CHECK_INTERVAL)

                if not self._is_server_running():
                    logger.info(
                        "Valheim server is no longer running. Stopping monitor."
                    )
                    return

                channel = self._get_channel()

                if channel is None:
                    return

                action = await self._ask_if_server_is_still_active(channel)

                if action == "yes":
                    logger.info(
                        "Valheim server confirmed active. "
                        "Starting another 5-hour period."
                    )
                    continue

                if action == "timeout":
                    await channel.send(
                        "⏰ Nobody responded within 15 minutes. "
                        "The Valheim server will now shut down."
                    )

                await self.shutdown()
                return

        except asyncio.CancelledError:
            logger.info("Valheim monitor cancelled.")
            raise

        except Exception:
            logger.exception("Valheim monitor failed.")

    # -----------------------------------------------------------------------
    # GCE state
    # -----------------------------------------------------------------------

    def _is_server_running(self) -> bool:
        """Return True if the Valheim GCE instance is running."""

        service = get_compute_service()
        instance = get_instance(service)

        status = instance.get("status")

        logger.info(
            "Valheim GCE instance status: %s",
            status,
        )

        return status == "RUNNING"

    # -----------------------------------------------------------------------
    # Discord
    # -----------------------------------------------------------------------

    def _get_channel(self):
        """Return the configured Discord channel."""

        channel = self.bot.get_channel(self.channel_id)

        if channel is None:
            logger.error(
                "Could not find Discord channel %s.",
                self.channel_id,
            )

        return channel

    async def _ask_if_server_is_still_active(
        self,
        channel,
    ) -> str:
        """Ask Discord whether anybody is still playing.

        Returns:
            "yes"
            "no"
            "timeout"
        """

        view = ServerCheckView(self)

        await channel.send(
            "🎮 **Is anyone still playing on the Valheim server?**\n\n"
            "The server has been running for 5 hours. "
            "Please select **Yes** if someone is still playing.\n\n"
            "If nobody responds within 15 minutes, "
            "the server will automatically shut down.",
            view=view,
        )

        await view.response.wait()

        logger.info(
            "Valheim activity response received: %s",
            view.action,
        )

        return view.action

    # -----------------------------------------------------------------------
    # Shutdown
    # -----------------------------------------------------------------------

    async def shutdown(self):
        """Stop the Valheim server and terminate monitoring."""

        service = get_compute_service()
        instance = get_instance(service)

        status = instance.get("status")

        if status != "RUNNING":
            logger.info(
                "Valheim server is already in state %s.",
                status,
            )
            return

        stop_instance(service)

        logger.info("Valheim server shutdown initiated.")
