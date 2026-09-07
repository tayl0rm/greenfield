import asyncio
import logging

import discord
from greenfieldbot.gcp.compute import (
    get_compute_service,
    get_instance,
    stop_instance,
)

logger = logging.getLogger(__name__)

CHECK_INTERVAL = 3 * 60 
RESPONSE_TIMEOUT = 1 * 60


class ServerCheckView(discord.ui.View):
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
        if self.action is not None:
            return

        self.action = "timeout"

        self.response.set()


class ValheimMonitor:
    def __init__(self, bot, channel_id: int):
        self.bot = bot
        self.channel_id = channel_id
        self.task: asyncio.Task | None = None

    def start(self):
        if self.task and not self.task.done():
            logger.info("Valheim monitor is already running.")
            return

        self.task = asyncio.create_task(self._monitor())

        logger.info("Valheim monitor started.")

    async def stop(self):
        if not self.task or self.task.done():
            self.task = None
            return

        current_task = asyncio.current_task()

        if self.task is current_task:
            return

        self.task.cancel()

        try:
            await self.task
        except asyncio.CancelledError:
            pass

        self.task = None

        logger.info("Valheim monitor stopped.")

    async def _monitor(self):
        try:
            while True:
                logger.info("Valheim activity monitor sleeping for 5 hours.")

                await asyncio.sleep(CHECK_INTERVAL)

                service = get_compute_service()
                instance = get_instance(service)

                if instance.get("status") != "RUNNING":
                    logger.info(
                        "Valheim server is no longer running. Stopping monitor."
                    )
                    return

                channel = self.bot.get_channel(self.channel_id)

                if channel is None:
                    logger.error(
                        "Could not find Discord channel %s.",
                        self.channel_id,
                    )
                    return

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

                if view.action == "yes":
                    logger.info(
                        "Valheim server confirmed active. "
                        "Starting another 5-hour period."
                    )
                    continue

                if view.action in ("no", "timeout"):
                    if view.action == "timeout":
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
