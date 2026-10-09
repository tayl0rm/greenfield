import asyncio
import logging

import a2s

from greenfieldbot.gcp.compute import (
    get_compute_service,
    get_external_ip,
    get_instance,
    start_instance,
    stop_instance,
)
from greenfieldbot.gcp.secrets import get_valheim_password
from greenfieldbot.services.valheim_monitor import ValheimMonitor

logger = logging.getLogger(__name__)

A2S_PORT = 2457
A2S_QUERY_TIMEOUT = 5.0


def setup(bot):

    @bot.command(name="valheim-up")
    async def valheim_up(ctx):
        await ctx.channel.send(
            "The Valheim server is in the process of starting up, Ol'bean!"
        )

        try:
            service = await asyncio.to_thread(get_compute_service)

            # Check instance
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

            if status == "RUNNING":
                await ctx.channel.send("The Valheim server is already running.")
                return

            if status not in ("TERMINATED", "STOPPED"):
                await ctx.channel.send(
                    f"The Valheim server is currently in state "
                    f"`{status}` and cannot be started yet."
                )
                return

            # Start instance
            await asyncio.to_thread(start_instance, service)

            await ctx.channel.send(
                "The Valheim server is starting. "
                "I'll check it periodically and let you know when it's ready."
            )

            # Poll for instance to reach RUNNING
            for _ in range(12):
                await asyncio.sleep(10)

                instance = await asyncio.to_thread(get_instance, service)
                status = instance.get("status")

                if status == "RUNNING":
                    break

                if status not in ("PROVISIONING", "STAGING", "RUNNING"):
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

            # Get external IP
            valheim_server_ip = get_external_ip(instance)

            if not valheim_server_ip:
                await ctx.channel.send(
                    "The Valheim server is running, but its external "
                    "IP address is not available yet."
                )
                return

            # Wait for Valheim to finish starting
            await ctx.channel.send(
                "The VM is running. Waiting for the Valheim server "
                "to finish starting..."
            )

            await asyncio.sleep(60)

            # Get server password
            password = await asyncio.to_thread(get_valheim_password)

            await ctx.channel.send(
                "I'd like to inform you that the Valheim Server, "
                "**SuperDuperVikingFunTime**, is now accessible at "
                f"**{valheim_server_ip}**!\n\n"
                f"Server password: **{password}**"
            )

            # Stop any existing monitor to avoid duplicate timers.
            existing_monitor = getattr(bot, "valheim_monitor", None)

            if existing_monitor:
                await existing_monitor.stop()

            bot.valheim_monitor = ValheimMonitor(
                bot=bot,
                channel_id=ctx.channel.id,
            )

            bot.valheim_monitor.start()

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
            # Stop activity monitor
            monitor = getattr(bot, "valheim_monitor", None)

            if monitor:
                await monitor.stop()
                bot.valheim_monitor = None

            # Get compute service
            service = await asyncio.to_thread(get_compute_service)

            # Check instance
            try:
                instance = await asyncio.to_thread(get_instance, service)

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

            # Stop instance
            await asyncio.to_thread(stop_instance, service)

            await ctx.channel.send(
                "The Valheim server has been instructed to shut down."
            )

            # Poll for termination
            max_attempts = 12
            poll_interval = 5

            for _ in range(max_attempts):
                await asyncio.sleep(poll_interval)

                instance = await asyncio.to_thread(get_instance, service)
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
            logger.exception("Failed to stop the Valheim server")
            await ctx.channel.send(
                "Something went wrong while shutting down the "
                "Valheim server. Check the bot logs for more information."
            )

    @bot.command(name="player")
    async def player(ctx):
        """Show the current player count and any names returned by A2S."""

        try:
            # Check whether the VM is running.
            service = await asyncio.to_thread(get_compute_service)
            instance = await asyncio.to_thread(get_instance, service)

            if instance.get("status") != "RUNNING":
                await ctx.send("The Valheim server is not running.")
                return

            # Get external IP.
            server_ip = get_external_ip(instance)

            if not server_ip:
                await ctx.send("The server's external IP address is not available.")
                return

            address = (server_ip, A2S_PORT)

            # Query player count.
            info = await asyncio.to_thread(
                a2s.info,
                address,
                timeout=A2S_QUERY_TIMEOUT,
            )

            # Query individual player names separately.
            try:
                players = await asyncio.to_thread(
                    a2s.players,
                    address,
                    timeout=A2S_QUERY_TIMEOUT,
                )
            except Exception:
                logger.exception("Failed to retrieve Valheim player names")
                players = None

            count = info.player_count
            maximum = info.max_players

            message = [f"**Valheim players online: {count}/{maximum}**"]

            if players is None:
                message.append("Player names could not be retrieved.")
            else:
                names = sorted(
                    {p.name.strip() for p in players if p.name and p.name.strip()},
                    key=str.casefold,
                )

                if names:
                    message.extend(f"• {name}" for name in names)
                elif count > 0:
                    message.append(
                        "The server reports players online, "
                        "but their names weren't returned by the query."
                    )
                else:
                    message.append("Nobody is online.")

            await ctx.send("\n".join(message))

        except Exception:
            logger.exception("Failed to query Valheim player status")
            await ctx.send("Unable to retrieve player status. Check the bot logs.")
