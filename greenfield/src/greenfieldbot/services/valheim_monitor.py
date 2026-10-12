import asyncio
import logging

import discord

from greenfieldbot.gcp.compute import (
    get_compute_service,
    get_instance,
    stop_instance,
)

logger = logging.getLogger(__name__)

# Ask whether the server is still needed every two hours.
CHECK_INTERVAL = 2 * 60 * 60

# Allow 15 minutes for a response.
RESPONSE_TIMEOUT = 15 * 60


class ServerUsageView(discord.ui.View):
    """Yes/No prompt for deciding whether to keep the server running."""

    def __init__(self):
        super().__init__(timeout=RESPONSE_TIMEOUT)
        self.answer: str | None = None
        self.message: discord.Message | None = None

    async def _record_answer(
        self,
        interaction: discord.Interaction,
        answer: str,
    ):
        if self.answer is not None:
            await interaction.response.send_message(
                "This server usage prompt has already been answered.",
                ephemeral=True,
            )
            return

        self.answer = answer

        # Disable both buttons immediately to prevent multiple responses.
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = True

        await interaction.response.edit_message(view=self)
        self.stop()

    @discord.ui.button(
        label="Yes",
        style=discord.ButtonStyle.success,
        custom_id="valheim_usage_yes",
    )
    async def yes_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        await self._record_answer(interaction, "yes")

    @discord.ui.button(
        label="No",
        style=discord.ButtonStyle.danger,
        custom_id="valheim_usage_no",
    )
    async def no_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        await self._record_answer(interaction, "no")

    async def on_timeout(self):
        # Disable buttons when the 15-minute response window expires.
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = True

        if self.message:
            try:
                await self.message.edit(view=self)
            except discord.HTTPException:
                logger.exception("Could not disable expired Valheim prompt buttons.")


class ValheimMonitor:
    def __init__(self, bot, channel_id: int):
        self.bot = bot
        self.channel_id = channel_id
        self._monitor_task: asyncio.Task | None = None
        self._current_view: ServerUsageView | None = None

    def start(self):
        """Start monitoring if it is not already running."""
        if self._monitor_task and not self._monitor_task.done():
            logger.info("Valheim monitor is already running.")
            return

        self._monitor_task = asyncio.create_task(
            self._monitor(),
            name="valheim-monitor",
        )
        logger.info("Valheim usage monitor started.")

    async def stop(self):
        """Stop monitoring and invalidate any outstanding prompt."""
        view = self._current_view

        if view is not None:
            view.stop()

            for child in view.children:
                if isinstance(child, discord.ui.Button):
                    child.disabled = True

            if view.message:
                try:
                    await view.message.edit(
                        content="Valheim monitoring stopped.",
                        view=view,
                    )
                except discord.HTTPException:
                    logger.warning("Could not update the active Valheim prompt.")

            self._current_view = None

        task = self._monitor_task

        if task and not task.done():
            task.cancel()

            try:
                await task
            except asyncio.CancelledError:
                pass

        self._monitor_task = None
        logger.info("Valheim monitor stopped.")

    async def _get_channel(self):
        """Resolve the Discord channel used for prompts and notifications."""
        channel = self.bot.get_channel(self.channel_id)

        if channel is None:
            channel = await self.bot.fetch_channel(self.channel_id)

        return channel

    async def _monitor(self):
        """Ask every two hours whether the Valheim server is still needed."""
        try:
            while True:
                logger.info(
                    "Next Valheim usage prompt in %d seconds.",
                    CHECK_INTERVAL,
                )
                await asyncio.sleep(CHECK_INTERVAL)

                service = await asyncio.to_thread(get_compute_service)
                instance = await asyncio.to_thread(get_instance, service)

                if instance.get("status") != "RUNNING":
                    logger.info(
                        "Valheim VM is no longer running; ending usage monitoring."
                    )
                    return

                channel = await self._get_channel()
                view = ServerUsageView()
                self._current_view = view

                view.message = await channel.send(
                    "⏰ **Valheim server check-in**\n\n"
                    "Is the server still being used?\n"
                    "Select **Yes** to keep it running for another "
                    "2 hours, or **No** to shut it down.\n\n"
                    "If nobody responds within 15 minutes, "
                    "the server will be shut down automatically.",
                    view=view,
                )

                logger.info("Valheim usage prompt sent to Discord.")

                timed_out = await view.wait()
                self._current_view = None

                if view.answer == "yes":
                    await view.message.edit(
                        content=(
                            "✅ **Valheim server confirmed in use.**\n"
                            "I'll ask again in 2 hours."
                        ),
                        view=None,
                    )
                    logger.info(
                        "Valheim server confirmed in use; resetting the two-hour timer."
                    )
                    continue

                if view.answer == "no":
                    reason = "No was selected."
                elif timed_out:
                    reason = "Nobody responded within 15 minutes."
                else:
                    # Unexpected termination must not cause shutdown.
                    logger.warning(
                        "Valheim prompt ended without an answer or timeout; "
                        "keeping the VM running."
                    )
                    continue

                await view.message.edit(
                    content=f"🛑 **Valheim server shutdown:** {reason}",
                    view=None,
                )

                await channel.send(
                    f"🛑 {reason} Requesting shutdown of the Valheim server now."
                )

                stopped = await self._shutdown_vm()

                if stopped:
                    await channel.send(
                        "✅ The Valheim server shutdown request "
                        "was submitted successfully."
                    )
                else:
                    await channel.send(
                        "⚠️ I couldn't confirm that the shutdown request "
                        "was submitted. Please check the bot logs and "
                        "Google Cloud status."
                    )

                # The server is being stopped; don't ask again.
                return

        except asyncio.CancelledError:
            logger.info("Valheim monitor task cancelled.")
            raise

        except Exception:
            logger.exception("Unexpected error in the Valheim usage monitor.")
            try:
                channel = await self._get_channel()
                await channel.send(
                    "⚠️ The Valheim usage monitor encountered an error. "
                    "Automatic shutdown could not be completed reliably. "
                    "Please check the bot logs."
                )
            except Exception:
                logger.exception("Could not notify Discord about the monitor error.")

    async def _shutdown_vm(self) -> bool:
        """Stop the VM if it is still running; return success status."""
        try:
            service = await asyncio.to_thread(get_compute_service)
            instance = await asyncio.to_thread(get_instance, service)

            status = instance.get("status")

            if status in ("TERMINATED", "STOPPED"):
                logger.info("Valheim VM is already stopped.")
                return True

            if status != "RUNNING":
                logger.warning(
                    "Cannot stop Valheim VM in state %s.",
                    status or "unknown",
                )
                return False

            logger.info("Requesting Valheim VM shutdown.")
            await asyncio.to_thread(stop_instance, service)
            logger.info("Valheim VM shutdown request submitted.")
            return True

        except Exception:
            logger.exception("Failed to stop the Valheim VM.")
            return False
