import asyncio

from greenfieldbot.gcp.compute import (
    get_compute_service,
    get_external_ip,
    get_instance,
    start_instance,
    stop_instance,
)
from greenfieldbot.gcp.secrets import get_valheim_password
from greenfieldbot.services.valheim_monitor import ValheimMonitor


def setup(bot):

    @bot.command(name="valheim-up")
    async def valheim_up(ctx):
        await ctx.channel.send(
            "The Valheim server is in the process of starting up, Ol'bean!"
        )

        try:
            service = get_compute_service()

            # ----------------------------------------------------
            # Check instance
            # ----------------------------------------------------

            try:
                instance = get_instance(service)

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

            if status == "RUNNING":
                await ctx.channel.send("The Valheim server is already running.")
                return

            if status not in ("TERMINATED", "STOPPED"):
                await ctx.channel.send(
                    f"The Valheim server is currently in state "
                    f"`{status}` and cannot be started yet."
                )
                return

            # ----------------------------------------------------
            # Start instance
            # ----------------------------------------------------

            start_instance(service)

            await ctx.channel.send(
                "The Valheim server is starting. "
                "I'll check it periodically and let you know when it's ready."
            )

            # ----------------------------------------------------
            # Poll for instance to reach RUNNING
            # ----------------------------------------------------

            for _ in range(12):
                await asyncio.sleep(10)

                instance = get_instance(service)
                status = instance.get("status")

                if status == "RUNNING":
                    break

                if status not in ("PROVISIONING", "STAGING", "RUNNING"):
                    await ctx.channel.send(
                        f"The Valheim server failed to start. "
                        f"Current instance state: `{status}`."
                    )
                    return

            else:
                await ctx.channel.send(
                    "The Valheim server is taking longer than expected "
                    "to start. Please try again shortly."
                )
                return

            # ----------------------------------------------------
            # Get external IP
            # ----------------------------------------------------

            valheim_server_ip = get_external_ip(instance)

            if not valheim_server_ip:
                await ctx.channel.send(
                    "The Valheim server is running, but its external "
                    "IP address is not available yet."
                )
                return

            # ----------------------------------------------------
            # Wait for Valheim
            # ----------------------------------------------------

            await ctx.channel.send(
                "The VM is running. Waiting for the Valheim server "
                "to finish starting..."
            )

            await asyncio.sleep(60)

            # ----------------------------------------------------
            # Get server password
            # ----------------------------------------------------

            password = get_valheim_password()

            await ctx.channel.send(
                f"I'd like to inform you that the Valheim Server, "
                f"**SuperDuperVikingFunTime**, is now accessible at "
                f"**{valheim_server_ip}**!\n\n"
                f"Server password: **{password}**"
            )

            # ----------------------------------------------------
            # Start activity monitor
            # ----------------------------------------------------

            # Stop any existing monitor first. This prevents
            # multiple 5-hour timers from being created if
            # !valheim-up is invoked more than once.
            existing_monitor = getattr(bot, "valheim_monitor", None)

            if existing_monitor:
                await existing_monitor.stop()

            bot.valheim_monitor = ValheimMonitor(
                bot=bot,
                channel_id=ctx.channel.id,
            )

            bot.valheim_monitor.start()

        except Exception:
            await ctx.channel.send(
                "Something went wrong while starting the Valheim server. "
                "Check the bot logs for more information."
            )
            raise

    @bot.command(name="valheim-down")
    async def valheim_down(ctx):

        await ctx.channel.send("The Valheim server is currently shutting down!")

        try:
            # ----------------------------------------------------
            # Stop activity monitor
            # ----------------------------------------------------

            monitor = getattr(bot, "valheim_monitor", None)

            if monitor:
                await monitor.stop()
                bot.valheim_monitor = None

            # ----------------------------------------------------
            # Get compute service
            # ----------------------------------------------------

            service = get_compute_service()

            # ----------------------------------------------------
            # Check instance
            # ----------------------------------------------------

            try:
                instance = get_instance(service)

            except Exception as exc:
                error_text = str(exc)

                if "404" in error_text or "notFound" in error_text:
                    await ctx.channel.send("The Valheim server instance doesn't exist.")
                    return

                raise

            status = instance.get("status")

            if status == "TERMINATED":
                await ctx.channel.send("The Valheim server is already shut down.")
                return

            if status != "RUNNING":
                await ctx.channel.send(
                    f"The Valheim server is currently in state "
                    f"`{status}` and cannot be stopped."
                )
                return

            # ----------------------------------------------------
            # Stop instance
            # ----------------------------------------------------

            stop_instance(service)

            await ctx.channel.send(
                "The Valheim server has been instructed to shut down."
            )

            # ----------------------------------------------------
            # Poll for termination
            # ----------------------------------------------------

            max_attempts = 12
            poll_interval = 5

            for _ in range(max_attempts):
                await asyncio.sleep(poll_interval)

                instance = get_instance(service)
                status = instance.get("status")

                if status == "TERMINATED":
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
            await ctx.channel.send(
                "Something went wrong while shutting down the "
                "Valheim server. Check the bot logs for more information."
            )

            raise
