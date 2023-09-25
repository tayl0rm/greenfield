import discord
import os
import asyncio
import sys

from discord.ext import commands
from discord.ext.commands import Bot
from discord.utils import get
from dotenv import load_dotenv
from discord import Intents
from typing import Any
from googleapiclient import discovery
from google.cloud import compute_v1

load_dotenv()

credential_path = "/workspaces/greenfield/gcloud-service-account.json"
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credential_path

DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)


@bot.command(name="valheim-up")
async def valheim_up(ctx):
    await ctx.channel.send('The Valheim Server is spinning up!')
    service = discovery.build('compute', 'v1')

    project = "ga-test-project-503ca"
    zone = "europe-west1-b"
    instance = "python-test-instance"

    request = service.instances().start(project=project, zone=zone, instance=instance)
    response = request.execute()

    response = service.instances().get(
        project=project, zone=zone, instance=instance).execute()
    vahleim_server_ip = response['networkInterfaces'][0]['accessConfigs'][0]['natIP']

    await asyncio.sleep(60)
    await ctx.channel.send(f'The Valheim Server is accessible at {vahleim_server_ip}!')


@bot.command(name="valheim-down")
async def valheim_down(ctx):
    await ctx.channel.send('The Valheim Server is spinning down!')
    service = discovery.build('compute', 'v1')

    project = "ga-test-project-503ca"
    zone = "europe-west1-b"
    instance = "python-test-instance"

    request = service.instances().stop(project=project, zone=zone, instance=instance)
    response = request.execute()

    await asyncio.sleep(60)
    await ctx.channel.send('The Valheim Server has shutdown, you can use *!vaheim-up* to restart the server!')

bot.run(os.getenv('DISCORD_TOKEN'))  # bot
