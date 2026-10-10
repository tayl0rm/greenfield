import asyncio
import logging

from greenfieldbot.gcp.compute import (
    get_compute_service,
    get_external_ip,
    get_instance,
    start_instance,
    stop_instance,
)
from greenfieldbot.gcp.secrets import get_valheim_password
from greenfieldbot.services.valheim import get_player_info
from greenfieldbot.services.valheim_monitor import ValheimMonitor

logger = logging.getLogger(__name__)


def setup(bot):
    def ensure_monitor(channel_id: int):
        """Ensure exactly one Valheim monitor task is running."""
        monitor = getattr(bot, "valheim_monitor", None)

        if monitor is None:
            monitor = ValheimMonitor(
                bot=bot,
                channel_id=channel_id,
            )
            bot.valheim_monitor = monitor

        monitor.start()

    @bot.command(name="valheim-up")
    async def valheim_up(ctx):
        await ctx.channel.send(
            "The Valheim server is in the process of starting up, Ol'bean!"
        )

        try:
            service = await asyncio.to_thread(get_compute_service)

            # Check the instance.
            try:
                instance = await asyncio.to_thread(get_instance, service)
            except Exception as exc:
                error_text = str(exc)

                if "404" in error_text or "notFound" in error_text:
                    await ctx.channel.send(
                        "The Valheim server instance doesn't currently exist. "
                        "It may still be pending deployment."
                    )
                    return

                raise

            status = instance.get("status")

            # The VM may already be running without a monitor.
            if status == "RUNNING":
                ensure_monitor(ctx.channel.id)
                await ctx.channel.send(
                    "The Valheim server is already running. "
                    "Activity monitoring is enabled."
                )
                return

            if status not in ("TERMINATED", "STOPPED"):
                await ctx.channel.send(
                    "The Valheim server is currently in state "
                    f"`{status}` and cannot be started yet."
                )
                return

            # Start the instance.
            await asyncio.to_thread(start_instance, service)

            await ctx.channel.send(
                "The Valheim server is starting. "
                "I'll check it periodically and let you know when it's ready."
            )

            # Poll until the VM reaches RUNNING.
            for _ in range(12):
                await asyncio.sleep(10)

                instance = await asyncio.to_thread(get_instance, service)
                status = instance.get("status")

                if status == "RUNNING":
                    break

                if status not in ("PROVISIONING", "STAGING"):
                    await ctx.channel.send(
                        "The Valheim server failed to start. "
                        f"Current instance state: `{status}`."
                    )
                    return
            else:
                await ctx.channel.send(
                    "The Valheim server is taking longer than expected "
                    "to start. Please try again shortly."
                )
                return

            # Start monitoring as soon as the VM is running.
            # The monitor safely retries if Valheim is not ready yet.
            ensure_monitor(ctx.channel.id)

            # Get the external IP.
            valheim_server_ip = get_external_ip(instance)

            if not valheim_server_ip:
                await ctx.channel.send(
                    "The Valheim server is running, but its external "
                    "IP address is not available yet. "
                    "Activity monitoring is enabled."
                )
                return

            await ctx.channel.send(
                "The VM is running. Waiting for the Valheim server "
                "to finish starting..."
            )

            # Allow time for the Valheim server to initialise.
            await asyncio.sleep(60)

            # Get the server password.
            password = await asyncio.to_thread(get_valheim_password)

            await ctx.channel.send(
                "I'd like to inform you that the Valheim Server, "
                "**SuperDuperVikingFunTime**, is now accessible at "
                f"**{valheim_server_ip}**!\n\n"
                f"Server password: **{password}**"
            )

        except Exception:
            logger.exception("Failed to start the Valheim server")
            await ctx.channel.send(
                "Something went wrong while starting the Valheim server. "
                "Check the bot logs for more information."
            )

    @bot.command(name="valheim-down")
    async def valheim_down(ctx):
        await ctx.channel.send("The Valheim server is currently shutting down!")

        try:
            # Stop activity monitoring before manually stopping the VM.
            monitor = getattr(bot, "valheim_monitor", None)

            if monitor:
                await monitor.stop()
                bot.valheim_monitor = None

            service = await asyncio.to_thread(get_compute_service)

            # Check the instance.
            try:
                instance = await asyncio.to_thread(get_instance, service)
            except Exception as exc:
                error_text = str(exc)

                if "404" in error_text or "notFound" in error_text:
                    await ctx.channel.send("The Valheim server instance doesn't exist.")
                    return

                raise

            status = instance.get("status")

            if status in ("TERMINATED", "STOPPED"):
                await ctx.channel.send("The Valheim server is already shut down.")
                return

            if status != "RUNNING":
                await ctx.channel.send(
                    "The Valheim server is currently in state "
                    f"`{status}` and cannot be stopped."
                )
                return

            # Request shutdown.
            await asyncio.to_thread(stop_instance, service)

            await ctx.channel.send(
                "The Valheim server has been instructed to shut down."
            )

            # Poll for termination.
            max_attempts = 12
            poll_interval = 5

            for _ in range(max_attempts):
                await asyncio.sleep(poll_interval)

                instance = await asyncio.to_thread(get_instance, service)
                status = instance.get("status")

                if status in ("TERMINATED", "STOPPED"):
                    await ctx.channel.send(
                        "The Valheim server has shut down, "
                        "as it descends into a slumber. Fear not, "
                        "you may rekindle the server with "
                        "the invocation of *!valheim-up*!"
                    )
                    return

            await ctx.channel.send(
                "The Valheim server is shutting down, but is taking "
                "longer than expected. Check again shortly."
            )

        except Exception:
            logger.exception("Failed to stop the Valheim server")
            await ctx.channel.send(
                "Something went wrong while shutting down the "
                "Valheim server. Check the bot logs for more information."
            )

    @bot.command(name="player")
    async def player(ctx):
        """Show the current Valheim player count."""
        try:
            service = await asyncio.to_thread(get_compute_service)
            instance = await asyncio.to_thread(get_instance, service)

            if instance.get("status") != "RUNNING":
                await ctx.send("The Valheim server is not running.")
                return

            server_ip = get_external_ip(instance)

            if not server_ip:
                await ctx.send("The server's external IP address is not available.")
                return

            info = await get_player_info(server_ip)

            if info is None:
                await ctx.send(
                    "Unable to retrieve the player count. "
                    "The server may still be starting up or its query "
                    "port may be unreachable."
                )
                return

            count = info.player_count
            maximum = info.max_players

            if count == 0:
                await ctx.send(
                    f"**Valheim players online: {count}/{maximum}**\nNobody is online."
                )
            else:
                await ctx.send(f"**Valheim players online: {count}/{maximum}**")

        except Exception:
            logger.exception("Failed to query Valheim player count")
            await ctx.send(
                "Unable to retrieve the player count. "
                "Check the bot logs for more information."
            )
