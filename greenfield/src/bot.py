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

GCP_CREDENTIALS_FILE = os.getenv(
    "GOOGLE_APPLICATION_CREDENTIALS", "/var/secrets/google/credentials.json"
)


# Valheim configuration
VALHEIM_SERVER_NAME = "SuperDuperVikingFunTime"
VALHEIM_SERVER_PASSWORD = "SuperDuperVikingFunTime1066"


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
    Get the configured VM.

    Returns:
        Instance dictionary if it exists.
        None if the instance doesn't exist.

    Raises:
        HttpError for other GCP/API errors.
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


# Commands
@bot.command(name="valheim-up")
async def valheim_up(ctx):
    service = get_compute_service()

    # Check whether the VM exists
    try:
        instance = get_instance(service)

    except HttpError as error:
        await ctx.channel.send(
            "I couldn't check the Valheim server status because "
            "Google Cloud returned an error. Please try again later."
        )

        print(f"Error checking Valheim instance: {error}")
        return

    # VM doesn't exist
    if instance is None:
        await ctx.channel.send(
            f"The Valheim server **{VALHEIM_SERVER_NAME}** doesn't currently "
            "exist. It may be pending creation. Please try again later."
        )
        return

    # Check current VM state
    status = instance.get("status")

    if status == "RUNNING":
        # Get the current IP
        try:
            ip = instance["networkInterfaces"][0]["accessConfigs"][0]["natIP"]
        except (KeyError, IndexError):
            ip = None

        if ip:
            await ctx.channel.send(
                f"The Valheim server **{VALHEIM_SERVER_NAME}** is already "
                f"running at `{ip}`!"
            )
        else:
            await ctx.channel.send(
                f"The Valheim server **{VALHEIM_SERVER_NAME}** is already "
                "running, but I couldn't determine its public IP."
            )

        return

    if status in ("PROVISIONING", "STAGING"):
        await ctx.channel.send(
            f"The Valheim server **{VALHEIM_SERVER_NAME}** is already "
            "starting up. Please give it a little while longer."
        )
        return

    if status == "STOPPING":
        await ctx.channel.send(
            f"The Valheim server **{VALHEIM_SERVER_NAME}** is currently "
            "shutting down. Please wait until it has stopped before "
            "trying to start it again."
        )
        return

    if status == "SUSPENDED":
        await ctx.channel.send(
            f"The Valheim server **{VALHEIM_SERVER_NAME}** is suspended "
            "and cannot currently be started by this command."
        )
        return

    # Start the VM
    await ctx.channel.send(
        "The Valheim server is in the process of starting up, Ol'bean!"
    )

    try:
        request = service.instances().start(
            project=GCP_PROJECT, zone=GCP_ZONE, instance=GCP_INSTANCE
        )

        request.execute()

    except HttpError as error:
        if error.resp.status == 404:
            await ctx.channel.send(
                f"The Valheim server **{VALHEIM_SERVER_NAME}** no longer "
                "exists. It may be pending creation."
            )
            return

        print(f"Error starting Valheim server: {error}")

        await ctx.channel.send(
            "I couldn't start the Valheim server because Google Cloud "
            "returned an error. Please try again later."
        )
        return

    # Wait for the VM to start
    await asyncio.sleep(60)

    # Get updated instance information
    try:
        instance = get_instance(service)

    except HttpError as error:
        print(f"Error checking Valheim server after startup: {error}")

        await ctx.channel.send(
            "The Valheim server was started, but I couldn't retrieve "
            "its current status. Please try again later."
        )
        return

    if instance is None:
        await ctx.channel.send(
            f"The Valheim server **{VALHEIM_SERVER_NAME}** appears to have "
            "disappeared while starting."
        )
        return

    status = instance.get("status")

    if status != "RUNNING":
        await ctx.channel.send(
            f"The Valheim server is still starting. "
            f"Google Cloud reports its status as **{status}**. "
            "Please try again shortly."
        )
        return

    # Get public IP
    try:
        valheim_server_ip = instance["networkInterfaces"][0]["accessConfigs"][0][
            "natIP"
        ]

    except (KeyError, IndexError):
        await ctx.channel.send(
            f"The Valheim server **{VALHEIM_SERVER_NAME}** is running, "
            "but I couldn't determine its public IP address."
        )
        return

    await ctx.channel.send(
        f"I'd like to inform you that the Valheim Server, "
        f"**{VALHEIM_SERVER_NAME}**, is currently accessible at "
        f"`{valheim_server_ip}`!\n\n"
        f"To gain entry, please use the password: "
        f"`{VALHEIM_SERVER_PASSWORD}`."
    )


@bot.command(name="valheim-down")
async def valheim_down(ctx):
    service = get_compute_service()

    # Check whether the VM exists
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
            f"The Valheim server **{VALHEIM_SERVER_NAME}** doesn't " "currently exist."
        )
        return

    status = instance.get("status")

    if status == "TERMINATED":
        await ctx.channel.send("The Valheim server is already shut down.")
        return

    if status == "STOPPING":
        await ctx.channel.send("The Valheim server is already shutting down.")
        return

    if status != "RUNNING":
        await ctx.channel.send(
            f"The Valheim server cannot currently be shut down. "
            f"Google Cloud reports its status as **{status}**."
        )
        return

    await ctx.channel.send("The Valheim server is currently shutting down!")

    try:
        request = service.instances().stop(
            project=GCP_PROJECT, zone=GCP_ZONE, instance=GCP_INSTANCE
        )

        request.execute()

    except HttpError as error:
        if error.resp.status == 404:
            await ctx.channel.send(
                f"The Valheim server **{VALHEIM_SERVER_NAME}** no longer exists."
            )
            return

        print(f"Error stopping Valheim server: {error}")

        await ctx.channel.send(
            "I couldn't shut down the Valheim server because Google Cloud "
            "returned an error."
        )
        return

    await asyncio.sleep(15)

    await ctx.channel.send(
        "The Valheim server has shut down, as it descends into a slumber. "
        "Fear not, you may rekindle the server with the invocation of "
        "*!valheim-up*!"
    )


# Startup validation
if not DISCORD_BOT:
    raise RuntimeError("DISCORD_BOT environment variable is not set")

if not GCP_PROJECT:
    raise RuntimeError("GCP_PROJECT environment variable is not set")

if not GCP_ZONE:
    raise RuntimeError("GCP_ZONE environment variable is not set")

if not GCP_INSTANCE:
    raise RuntimeError("GCP_INSTANCE environment variable is not set")


# Start bot
bot.run(DISCORD_BOT)
