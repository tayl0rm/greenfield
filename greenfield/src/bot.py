import discord
import os
import asyncio

from discord.ext import commands
from discord.ext.commands import Bot
from discord.utils import get
from dotenv import load_dotenv
from discord import Intents
from typing import Any
from googleapiclient import discovery
from google.auth import compute_engine

load_dotenv()

credentials = compute_engine.Credentials()

os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credentials

DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)


@bot.command(name="valheim-up")
async def valheim_up(ctx):
    valheim_server_name = "SuperDuperVikingFunTime" #os.getenv('valheim_server_name')
    valheim_server_password = "SuperDuperVikingFunTime1066" #os.getenv('valheim_server_password')

    await ctx.channel.send("The Valheim server is in the process of starting up, Ol'bean!")
    service = discovery.build('compute', 'v1')

    project = os.getenv('gcp_project')
    zone = os.getenv('gcp_zone')
    instance = os.getenv('gcp_instance')

    request = service.instances().start(project="ga-test-project-503ca", zone="europe-west1-b", instance="valheim-server")
    response = request.execute()

    response = service.instances().get(
        project=project, zone=zone, instance=instance).execute()

    vahleim_server_ip = response['networkInterfaces'][0]['accessConfigs'][0]['natIP']

    await asyncio.sleep(60)
    await ctx.channel.send(f"I'd like to inform you that the Valheim Server, {valheim_server_name}, is currently accessible at {vahleim_server_ip}! To gain entry, please utilize the password: {valheim_server_password}.")


@bot.command(name="valheim-down")
async def valheim_down(ctx):
    await ctx.channel.send('The Valheim server is currently shutting down!')
    service = discovery.build('compute', 'v1')

    project = os.getenv('gcp_project')
    zone = os.getenv('gcp_zone')
    instance = os.getenv('gcp_instance')

    request = service.instances().stop(project="ga-test-project-503ca", zone="europe-west1-b", instance="valheim-server")
    response = request.execute()

    await asyncio.sleep(15)
    await ctx.channel.send("The Valheim server has shut down, as it descends into a slumber. Fear not, you may rekindle the server with the invocation of *!valheim-up*!")

@bot.command(name="palworld-up")
async def palworld_up(ctx):
    palworld_server_name = "SuperDuperVikingFunTime" #os.getenv('palworld_server_name')
    palworld_server_password = "SuperDuperVikingFunTime1066" #os.getenv('palworld_server_password')

    await ctx.channel.send("The PalWorld server is in the process of starting up, Ol'bean!")
    service = discovery.build('compute', 'v1')

    project = os.getenv('gcp_project')
    zone = os.getenv('gcp_zone')
    instance = os.getenv('gcp_instance')

    request = service.instances().start(project="ga-test-project-503ca", zone="europe-west1-b", instance="palworld-server")
    response = request.execute()

    response = service.instances().get(
        project=project, zone=zone, instance=instance).execute()

    palworld_server_ip = response['networkInterfaces'][0]['accessConfigs'][0]['natIP']

    await asyncio.sleep(60)
    await ctx.channel.send(f"I'd like to inform you that the PalWorld Server, {palworld_server_name}, is currently accessible at {palworld_server_ip}! To gain entry, please utilize the password: {palworld_server_password}.")


@bot.command(name="palworld-down")
async def palworld_down(ctx):
    await ctx.channel.send('The PalWorld server is currently shutting down!')
    service = discovery.build('compute', 'v1')

    project = os.getenv('gcp_project')
    zone = os.getenv('gcp_zone')
    instance = os.getenv('gcp_instance')

    request = service.instances().stop(project="ga-test-project-503ca", zone="europe-west1-b", instance="palworld-server")
    response = request.execute()

    await asyncio.sleep(15)
    await ctx.channel.send("The PalWorld server has shut down, as it descends into a slumber. Fear not, you may rekindle the server with the invocation of *!palworld-up*!")

bot.run(os.getenv('DISCORD_TOKEN'))
