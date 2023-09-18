import discord
import os
import asyncio
import python_terraform

from discord.ext import commands
from discord.ext.commands import Bot
from discord.utils import get
from dotenv import load_dotenv
from discord import Intents

# Enable all standard intents and message content
# (prefix commands generally require message content)
intents = Intents.default()
intents.message_content = True

load_dotenv()
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.all()

bot = commands.Bot(command_prefix="!", intents=intents)

# Reference code

# @bot.command()
# async def permit(ctx, user : discord.Member):
#     def check(m):
#         if m.author == ctx.author and m.channel == ctx.channel:
#             try:
#                 float(m.content)
#                 return True
#             except ValueError:
#                 return False
#         return False
#     permitRole=ctx.guild.get_role(941361821816860732)#the id of particular role you want to give 
#     await ctx.send("Tell me the hours")
#     res = await bot.wait_for("message", check=check)
#     bot.seconds = float(res.content) * 3600
#     await user.add_roles(permitRole)#giving the role to mentioned user
#     await ctx.send(f"Added role to {user.mention}")#tells the user that the role is given
#     await ctx.send(f"The time is {bot.seconds} seconds")#tells the time period of the role to the user
#     toime=float(res.content)#gets the message input as float variable
#     toimefoinal=toime*3600 #converts to seconds
#     await asyncio.sleep(toimefoinal)#sleeps the command 
#     await ctx.send("TIME UP")#this is after the time period 
#     await user.remove_roles(permitRole)#removes the role 
#     await ctx.send("TY FOR CHOOSING THIS SERVER!")

# bot.run(os.getenv('DISCORD_TOKEN'))#bot token

# @bot.command()
# def valheim_server_up():
#     os.