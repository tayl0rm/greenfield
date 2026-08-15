import asyncio
import os

import discord
from discord.ext import commands
from googleapiclient import discovery
from googleapiclient.errors import HttpError
from google.oauth2 import service_account

# Configuration


DISCORD_BOT = os.getenv("DISCORD_BOT")

GCP_PROJECT = os.getenv("GCP_PROJECT")
GCP_ZONE = os.getenv("GCP_ZONE")
GCP_INSTANCE = os.getenv("GCP_INSTANCE")

VALHEIM_SERVER_PASSWORD = os.getenv("VALHEIM_SERVER_PASSWORD")

GCP_CREDENTIALS_FILE = os.getenv(
    "GOOGLE_APPLICATION_CREDENTIALS", "/var/secrets/google/credentials.json"
)

# Polling configuration
POLL_INTERVAL = 10
POLL_TIMEOUT = 180


# Valheim configuration


VALHEIM_SERVER_NAME = "SuperDuperVikingFunTime"


# Discord


intents = discord.Intents.all()

bot = commands.Bot(command_prefix="!", intents=intents)


# Google Cloud


def get_compute_service():
    credentials = service_account.Credentials.from_service_account_file(
        GCP_CREDENTIALS_FILE
    )

    return discovery.build("compute", "v1", credentials=credentials)


def get_instance(service):
    """
    Retrieve the configured GCP instance.

    Returns:
        dict: Instance information if it exists.
        None: If the instance doesn't exist.

    Raises:
        HttpError: For errors other than 404.
    """

    try:
        return (
            service.instances()
            .get(project=GCP_PROJECT, zone=GCP_ZONE, instance=GCP_INSTANCE)
            .execute()
        )

    except HttpError as error:
        if error.resp.status == 404:
            return None

        raise


def get_instance_ip(instance):
    """
    Extract the public IP from a GCP instance.

    Returns:
        str: Public IP address.
        None: If no public IP is configured.
    """

    try:
        return instance["networkInterfaces"][0]["accessConfigs"][0]["natIP"]

    except (KeyError, IndexError):
        return None


async def wait_for_instance_running(service):
    """
    Poll the GCP instance until it reaches RUNNING.

    Returns:
        dict: Instance information once RUNNING.
        None: If the instance disappears or timeout is reached.

    Raises:
        HttpError: If Google Cloud returns an unexpected error.
    """

    elapsed = 0

    while elapsed < POLL_TIMEOUT:

        instance = get_instance(service)

        # Instance disappeared while waiting
        if instance is None:
            return None

        status = instance.get("status")

        print(f"Valheim instance status: {status} " f"({elapsed}/{POLL_TIMEOUT}s)")

        if status == "RUNNING":
            return instance

        if status in (
            "PROVISIONING",
            "STAGING",
        ):
            await asyncio.sleep(POLL_INTERVAL)
            elapsed += POLL_INTERVAL
            continue

        # Something unexpected happened
        print(f"Unexpected instance status: {status}")
        return instance

    return None


async def wait_for_instance_stopped(service):
    """
    Poll the GCP instance until it reaches TERMINATED.

    Returns:
        True: Instance successfully stopped.
        False: Timeout or instance disappeared.
    """

    elapsed = 0

    while elapsed < POLL_TIMEOUT:

        instance = get_instance(service)

        # Instance disappeared
        if instance is None:
            return False

        status = instance.get("status")

        print(f"Valheim shutdown status: {status} " f"({elapsed}/{POLL_TIMEOUT}s)")

        if status == "TERMINATED":
            return True

        await asyncio.sleep(POLL_INTERVAL)
        elapsed += POLL_INTERVAL

    return False


# !valheim-up


@bot.command(name="valheim-up")
async def valheim_up(ctx):

    service = get_compute_service()

    # Check whether the VM exists

    try:
        instance = get_instance(service)

    except HttpError as error:

        print(f"Error checking Valheim instance: {error}")

        await ctx.channel.send(
            "I couldn't check the Valheim server status because "
            "Google Cloud returned an error. Please try again later."
        )

        return

    # VM doesn't exist
    if instance is None:

        await ctx.channel.send(
            f"The Valheim server **{VALHEIM_SERVER_NAME}** doesn't "
            "currently exist. It may be pending creation. "
            "Please try again later."
        )

        return

    status = instance.get("status")

    # Already running

    if status == "RUNNING":

        ip = get_instance_ip(instance)

        if ip:

            await ctx.channel.send(
                f"The Valheim server **{VALHEIM_SERVER_NAME}** "
                f"is already running at `{ip}`!"
            )

        else:

            await ctx.channel.send(
                f"The Valheim server **{VALHEIM_SERVER_NAME}** "
                "is already running, but I couldn't determine "
                "its public IP."
            )

        return

    # Already starting

    if status in ("PROVISIONING", "STAGING"):

        await ctx.channel.send(
            f"The Valheim server **{VALHEIM_SERVER_NAME}** is "
            "already starting. I'll wait for it to become available."
        )

    # Currently stopping

    elif status == "STOPPING":

        await ctx.channel.send(
            f"The Valheim server **{VALHEIM_SERVER_NAME}** is "
            "currently shutting down. Please wait for it to finish "
            "before trying to start it again."
        )

        return

    # Suspended

    elif status == "SUSPENDED":

        await ctx.channel.send(
            f"The Valheim server **{VALHEIM_SERVER_NAME}** is "
            "suspended and cannot currently be started."
        )

        return

    # Stopped

    elif status == "TERMINATED":

        await ctx.channel.send(
            "The Valheim server is currently offline. " "Starting it now, Ol'bean!"
        )

        try:

            request = service.instances().start(
                project=GCP_PROJECT, zone=GCP_ZONE, instance=GCP_INSTANCE
            )

            request.execute()

        except HttpError as error:

            if error.resp.status == 404:

                await ctx.channel.send(
                    f"The Valheim server **{VALHEIM_SERVER_NAME}** "
                    "no longer exists. It may be pending creation."
                )

                return

            print(f"Error starting Valheim server: {error}")

            await ctx.channel.send(
                "I couldn't start the Valheim server because "
                "Google Cloud returned an error."
            )

            return

    # Unexpected state

    else:

        await ctx.channel.send(
            f"The Valheim server is currently in an unexpected " f"state: **{status}**."
        )

        return

    # Poll for RUNNING

    await ctx.channel.send("Waiting for the Valheim server to become available...")

    try:

        instance = await wait_for_instance_running(service)

    except HttpError as error:

        print(f"Error polling Valheim instance: {error}")

        await ctx.channel.send(
            "The Valheim server is starting, but I encountered "
            "an error while checking its status."
        )

        return

    # Timeout / disappeared

    if instance is None:

        await ctx.channel.send(
            "I couldn't confirm that the Valheim server finished "
            "starting within the expected time. Please check again "
            "shortly."
        )

        return

    # Final status

    status = instance.get("status")

    if status != "RUNNING":

        await ctx.channel.send(
            f"The Valheim server hasn't finished starting yet. "
            f"Google Cloud reports its status as **{status}**. "
            "Please try again shortly."
        )

        return

    # Get IP

    ip = get_instance_ip(instance)

    if not ip:

        await ctx.channel.send(
            f"The Valheim server **{VALHEIM_SERVER_NAME}** is "
            "running, but I couldn't determine its public IP address."
        )

        return

    # Success

    await ctx.channel.send(
        f"I'd like to inform you that the Valheim Server, "
        f"**{VALHEIM_SERVER_NAME}**, is now running!\n\n"
        f"**Server IP:** `{ip}`\n"
        f"**Password:** `{VALHEIM_SERVER_PASSWORD}`"
    )


# !valheim-down


@bot.command(name="valheim-down")
async def valheim_down(ctx):

    service = get_compute_service()

    # Check whether VM exists

    try:

        instance = get_instance(service)

    except HttpError as error:

        print(f"Error checking Valheim instance: {error}")

        await ctx.channel.send(
            "I couldn't check the Valheim server status because "
            "Google Cloud returned an error."
        )

        return

    # VM doesn't exist
    if instance is None:

        await ctx.channel.send(
            f"The Valheim server **{VALHEIM_SERVER_NAME}** " "doesn't currently exist."
        )

        return

    status = instance.get("status")

    # Already stopped

    if status == "TERMINATED":

        await ctx.channel.send("The Valheim server is already shut down.")

        return

    # Already stopping

    if status == "STOPPING":

        await ctx.channel.send("The Valheim server is already shutting down.")

        return

    # Not running

    if status != "RUNNING":

        await ctx.channel.send(
            f"The Valheim server cannot currently be shut down. "
            f"Google Cloud reports its status as **{status}**."
        )

        return

    # Stop VM

    await ctx.channel.send("The Valheim server is currently shutting down!")

    try:

        request = service.instances().stop(
            project=GCP_PROJECT, zone=GCP_ZONE, instance=GCP_INSTANCE
        )

        request.execute()

    except HttpError as error:

        if error.resp.status == 404:

            await ctx.channel.send(
                f"The Valheim server **{VALHEIM_SERVER_NAME}** " "no longer exists."
            )

            return

        print(f"Error stopping Valheim server: {error}")

        await ctx.channel.send(
            "I couldn't shut down the Valheim server because "
            "Google Cloud returned an error."
        )

        return

    # Poll until stopped

    await ctx.channel.send("Waiting for the Valheim server to finish shutting down...")

    try:

        stopped = await wait_for_instance_stopped(service)

    except HttpError as error:

        print(f"Error polling Valheim shutdown: {error}")

        await ctx.channel.send(
            "The Valheim server is shutting down, but I encountered "
            "an error while checking its status."
        )

        return

    if stopped:

        await ctx.channel.send(
            "The Valheim server has shut down, as it descends "
            "into a slumber. Fear not, you may rekindle the "
            "server with the invocation of *!valheim-up*!"
        )

    else:

        await ctx.channel.send(
            "The Valheim server is still shutting down. "
            "Google Cloud hasn't reported it as fully stopped yet."
        )


# Startup validation


if not DISCORD_BOT:
    raise RuntimeError("DISCORD_BOT environment variable is not set")

if not VALHEIM_SERVER_PASSWORD:
    raise RuntimeError("VALHEIM_SERVER_PASSWORD environment variable is not set")

if not GCP_PROJECT:
    raise RuntimeError("GCP_PROJECT environment variable is not set")

if not GCP_ZONE:
    raise RuntimeError("GCP_ZONE environment variable is not set")

if not GCP_INSTANCE:
    raise RuntimeError("GCP_INSTANCE environment variable is not set")


# Start bot


bot.run(DISCORD_BOT)
