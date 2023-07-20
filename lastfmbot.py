import json
import os
from urllib.parse import urlencode
import discord
from discord.ext import commands
from dotenv import load_dotenv
import requests
import base64

#Discord token
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix='$', intents=intents)

#Spotify token
CLIENT_ID = '3a8efb67417c464695fc8ea9d2719e68'
CLIENT_SECRET = '07669f1ed5ae415bb9b047e90646f5f9'
AUTHORIZATION_CODE = ""
#last.fm token
API_KEY = '70560a342afc2fe28d1bcf0ae419690c'
SHARED_SECRET = '3bbc284edee3f6c80f4d2dc3738df101'
ROOT_URL = "http://ws.audioscrobbler.com/2.0/"

def get_token():
    url = "?method=auth.gettoken&api_key=" + API_KEY + "&format=json"
    result = requests.post(ROOT_URL + url)
    return result.json()['token']

def get_session(token):
    url = "?method=auth.getsession&api_key=" + API_KEY + "&token=" + token + "&format=json"
    result = requests.post(ROOT_URL + url)
    print(result.json())

@bot.event
async def on_ready():

    for guild in bot.guilds:
        print(f"- {guild.id} (name: {guild.name})")
        print(guild.text_channels)
              
    print(f"{bot.user} has connected to Discord!")
    
    members = '\n - '.join([member.name for member in guild.members])
    print(f'Guild Members:\n - {members}')

@bot.event
async def on_message(message):
    if (message.content == "hello"):
        await message.channel.send("shut up" + message.author.mention)
    await bot.process_commands(message)
                
@bot.command()
async def stat(ctx):
    token = get_token()

    

@bot.command()
async def login(ctx):
    token = get_token()
    url = "http://www.last.fm/api/auth/?api_key="+ API_KEY + "&token=" + token
    await ctx.send(url)
    get_session()


bot.run(TOKEN)