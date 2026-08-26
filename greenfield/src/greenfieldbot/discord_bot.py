import discord
from discord.ext import commands

from greenfieldbot.commands import valheim


def create_bot():
    intents = discord.Intents.all()

    bot = commands.Bot(
        command_prefix="!",
        intents=intents,
    )

    valheim.setup(bot)

    return bot