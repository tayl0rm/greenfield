import asyncio
import os

import discord
from discord.ext import commands
from googleapiclient import discovery
from google.oauth2 import service_account
from google.cloud import secretmanager


# ============================================================
# Configuration
# ============================================================

DISCORD_BOT = os.getenv("DISCORD_BOT")

GCP_PROJECT = os.getenv("GCP_PROJECT")
GCP_ZONE = os.getenv("GCP_ZONE")
GCP_INSTANCE = os.getenv("GCP_INSTANCE")

GCP_CREDENTIALS_FILE = os.getenv(
    "GOOGLE_APPLICATION_CREDENTIALS",
    "/var/secrets/google/credentials.json"
)

VALHEIM_PASSWORD_SECRET = os.getenv(
    "VALHEIM_PASSWORD_SECRET",
    "valheim-server-password"
)


# ============================================================
# Discord
# ============================================================

intents = discord.Intents.all()

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)


# ============================================================
# Google Cloud
# ============================================================

def get_google_credentials():
    return service_account.Credentials.from_service_account_file(
        GCP_CREDENTIALS_FILE
    )


def get_compute_service():
    credentials = get_google_credentials()

    return discovery.build(
        "compute",
        "v1",
        credentials=credentials
    )


def get_secret_manager_client():
    credentials = get_google_credentials()

    return secretmanager.SecretManagerServiceClient(
        credentials=credentials
    )


def get_valheim_password():
    """
    Retrieve the current Valheim server password from
    Google Cloud Secret Manager.
    """

    client = get_secret_manager_client()

    secret_name = (
        f"projects/{GCP_PROJECT}"
        f"/secrets/{VALHEIM_PASSWORD_SECRET}"
        f"/versions/latest"
    )

    response = client.access_secret_version(
        request={
            "name": secret_name
        }
    )

    return response.payload.data.decode("UTF-8")


# ============================================================
# Commands
# ============================================================

@bot.command(name="valheim-up")
async def valheim_up(ctx):

    valheim_server_name = "SuperDuperVikingFunTime"

    await ctx.channel.send(
        "The Valheim server is in the process of starting up, Ol'bean!"
    )

    try:
        service = get_compute_service()

        # ----------------------------------------------------
        # Check that the instance exists
        # ----------------------------------------------------

        try:
            instance = service.instances().get(
                project=GCP_PROJECT,
                zone=GCP_ZONE,
                instance=GCP_INSTANCE
            ).execute()

        except Exception as exc:
            error_text = str(exc)

            if "404" in error_text or "notFound" in error_text:
                await ctx.channel.send(
                    "The Valheim server instance doesn't currently exist. "
                    "It may still be pending deployment."
                )
                return

            raise

        # ----------------------------------------------------
        # Check current state
        # ----------------------------------------------------

        status = instance.get("status")

        if status == "RUNNING":
            await ctx.channel.send(
                "The Valheim server is already running."
            )
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

        service.instances().start(
            project=GCP_PROJECT,
            zone=GCP_ZONE,
            instance=GCP_INSTANCE
        ).execute()

        await ctx.channel.send(
            "The Valheim server is starting. "
            "I'll check it periodically and let you know when it's ready."
        )

        # ----------------------------------------------------
        # Poll until RUNNING
        # ----------------------------------------------------

        max_attempts = 12
        poll_interval = 10

        for attempt in range(max_attempts):

            await asyncio.sleep(poll_interval)

            instance = service.instances().get(
                project=GCP_PROJECT,
                zone=GCP_ZONE,
                instance=GCP_INSTANCE
            ).execute()

            status = instance.get("status")

            if status == "RUNNING":
                break

            if status not in (
                "PROVISIONING",
                "STAGING",
                "RUNNING"
            ):
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
        # Retrieve server IP
        # ----------------------------------------------------

        response = service.instances().get(
            project=GCP_PROJECT,
            zone=GCP_ZONE,
            instance=GCP_INSTANCE
        ).execute()

        interfaces = response.get("networkInterfaces", [])

        if not interfaces:
            await ctx.channel.send(
                "The Valheim server is running, but no network "
                "interface was found yet."
            )
            return

        access_configs = interfaces[0].get("accessConfigs", [])

        if not access_configs:
            await ctx.channel.send(
                "The Valheim server is running, but no external "
                "IP address was found."
            )
            return

        valheim_server_ip = access_configs[0].get("natIP")

        if not valheim_server_ip:
            await ctx.channel.send(
                "The Valheim server is running, but its external "
                "IP address is not available yet."
            )
            return

        # ----------------------------------------------------
        # Wait for Valheim itself to initialise
        # ----------------------------------------------------

        await ctx.channel.send(
            "The VM is running. Waiting for the Valheim server "
            "to finish starting..."
        )

        await asyncio.sleep(60)

        # ----------------------------------------------------
        # Retrieve password from Secret Manager
        # ----------------------------------------------------

        valheim_server_password = get_valheim_password()

        # ----------------------------------------------------
        # Final response
        # ----------------------------------------------------

        await ctx.channel.send(
            f"I'd like to inform you that the Valheim Server, "
            f"**{valheim_server_name}**, is now accessible at "
            f"**{valheim_server_ip}**!\n\n"
            f"Server password: **{valheim_server_password}**"
        )

    except Exception:
        await ctx.channel.send(
            "Something went wrong while starting the Valheim server. "
            "Check the bot logs for more information."
        )

        raise


@bot.command(name="valheim-down")
async def valheim_down(ctx):

    await ctx.channel.send(
        "The Valheim server is currently shutting down!"
    )

    try:
        service = get_compute_service()

        # ----------------------------------------------------
        # Check instance
        # ----------------------------------------------------

        try:
            instance = service.instances().get(
                project=GCP_PROJECT,
                zone=GCP_ZONE,
                instance=GCP_INSTANCE
            ).execute()

        except Exception as exc:
            error_text = str(exc)

            if "404" in error_text or "notFound" in error_text:
                await ctx.channel.send(
                    "The Valheim server instance doesn't exist."
                )
                return

            raise

        status = instance.get("status")

        if status == "TERMINATED":
            await ctx.channel.send(
                "The Valheim server is already shut down."
            )
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

        service.instances().stop(
            project=GCP_PROJECT,
            zone=GCP_ZONE,
            instance=GCP_INSTANCE
        ).execute()

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

            instance = service.instances().get(
                project=GCP_PROJECT,
                zone=GCP_ZONE,
                instance=GCP_INSTANCE
            ).execute()

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


# ============================================================
# Startup validation
# ============================================================

if not DISCORD_BOT:
    raise RuntimeError(
        "DISCORD_BOT environment variable is not set"
    )

if not GCP_PROJECT:
    raise RuntimeError(
        "GCP_PROJECT environment variable is not set"
    )

if not GCP_ZONE:
    raise RuntimeError(
        "GCP_ZONE environment variable is not set"
    )

if not GCP_INSTANCE:
    raise RuntimeError(
        "GCP_INSTANCE environment variable is not set"
    )


# ============================================================
# Start bot
# ============================================================

bot.run(DISCORD_BOT)