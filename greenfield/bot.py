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

load_dotenv()
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.command(name="valheim-up")
async def valheim_up(ctx):
    await ctx.channel.send('The Valheim Server is spinning up!')

    await asyncio.sleep()
    await ctx.channel.send('The Valheim Server is accessible at {valheim_ip.address}!')


@bot.command(name="valheim-down")
async def valheim_down(ctx):
    await ctx.channel.send('The Valheim Server is spinning down!')
    


bot.run(os.getenv('DISCORD_TOKEN'))#bot token