import asyncio
import os

import discord
from discord.ext import commands
from googleapiclient import discovery
from google.oauth2 import service_account


# Configuration
DISCORD_BOT = os.getenv("DISCORD_BOT")

GCP_PROJECT = os.getenv("GCP_PROJECT")
GCP_ZONE = os.getenv("GCP_ZONE")
GCP_INSTANCE = os.getenv("GCP_INSTANCE")

GCP_CREDENTIALS_FILE = os.getenv(
    "GOOGLE_APPLICATION_CREDENTIALS",
    "/var/secrets/google/credentials.json"
)


# Discord
intents = discord.Intents.all()

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)


# Google Cloud
def get_compute_service():
    credentials = service_account.Credentials.from_service_account_file(
        GCP_CREDENTIALS_FILE
    )

    return discovery.build(
        "compute",
        "v1",
        credentials=credentials
    )


# Commands
@bot.command(name="valheim-up")
async def valheim_up(ctx):
    valheim_server_name = "SuperDuperVikingFunTime"
    valheim_server_password = "SuperDuperVikingFunTime1066"
    await ctx.channel.send(
        "The Valheim server is in the process of starting up, Ol'bean!"
    )
    service = get_compute_service()
    request = service.instances().start(
        project=GCP_PROJECT,
        zone=GCP_ZONE,
        instance=GCP_INSTANCE
    )
    request.execute()

    # Wait for the server to start
    await asyncio.sleep(60)
    response = service.instances().get(
        project=GCP_PROJECT,
        zone=GCP_ZONE,
        instance=GCP_INSTANCE
    ).execute()
    valheim_server_ip = (
        response["networkInterfaces"][0]
        ["accessConfigs"][0]
        ["natIP"]
    )
    await ctx.channel.send(
        f"I'd like to inform you that the Valheim Server, "
        f"{valheim_server_name}, is currently accessible at "
        f"{valheim_server_ip}! "
        f"To gain entry, please utilize the password: "
        f"{valheim_server_password}."
    )


@bot.command(name="valheim-down")
async def valheim_down(ctx):
    await ctx.channel.send(
        "The Valheim server is currently shutting down!"
    )
    service = get_compute_service()
    request = service.instances().stop(
        project=GCP_PROJECT,
        zone=GCP_ZONE,
        instance=GCP_INSTANCE
    )
    request.execute()
    await asyncio.sleep(15)
    await ctx.channel.send(
        "The Valheim server has shut down, as it descends into a slumber. "
        "Fear not, you may rekindle the server with the invocation of "
        "*!valheim-up*!"
    )


# Start bot
if not DISCORD_BOT:
    raise RuntimeError("DISCORD_BOT environment variable is not set")
if not GCP_PROJECT:
    raise RuntimeError("GCP_PROJECT environment variable is not set")
if not GCP_ZONE:
    raise RuntimeError("GCP_ZONE environment variable is not set")
if not GCP_INSTANCE:
    raise RuntimeError("GCP_INSTANCE environment variable is not set")


bot.run(DISCORD_BOT)