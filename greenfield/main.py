import discord, os, requests
from dotenv import load_dotenv

client = discord.Client(intents=discord.Intents.default())

load_dotenv()
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
RIOT_TOKEN = os.getenv('RIOT_TOKEN')

def lol_status():
  payload = {'api_key': RIOT_TOKEN}
  lol_return_status = requests.get('https://euw1.api.riotgames.com/lol/status/v4/platform-data?', params=payload)
  print(lol_return_status)

def val_status():
  payload = {'api_key': RIOT_TOKEN}
  val_return_status = requests.get('https://eu.api.riotgames.com/val/status/v1/platform-data?', params=payload)
  print(val_return_status)


@client.event
async def on_ready():
    print('We have logged in as {0.user}'.format(client))

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content.startswith("val status"):
        await message.channel.send("Hello")

client.run(os.getenv('DISCORD_TOKEN'))

