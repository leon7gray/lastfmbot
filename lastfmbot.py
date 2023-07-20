from hashlib import md5
import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
import requests

#Discord token
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix='$', intents=intents)

def get_token():
    url = "?method=auth.gettoken&api_key=" + API_KEY + "&format=json"
    result = requests.post(ROOT_URL + url)
    return result.json()['token']

#last.fm token
API_KEY = os.getenv('API_KEY')
SHARED_SECRET = os.getenv('SHARED_SECRET')
ROOT_URL = "http://ws.audioscrobbler.com/2.0/"
FM_TOKEN = get_token()


def get_session(token):
    signature = md5(("api_key" + API_KEY + "methodauth.getSessiontoken" + FM_TOKEN + SHARED_SECRET).encode('utf-8')).hexdigest()
    data = {
        'token': token,
        'api_key': API_KEY,
        'method': 'auth.getSession',
        'format': 'json',
        'api_sig': signature
    }
    result = requests.post(ROOT_URL, params=data)
    print(result.json())

def get_userinfo(user):
    url = "?method=user.getinfo&user=" + user + "&api_key=" + API_KEY + "&format=json"
    result = requests.post(ROOT_URL + url)
    return(result.json())

def get_usertoptracks(user):
    url = "?method=user.gettoptracks&user=" + user + "&api_key=" + API_KEY + "&format=json&limit=5"
    result = requests.post(ROOT_URL + url)
    return(result.json()["toptracks"]["track"])

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
    url = "http://www.last.fm/api/auth/?api_key="+ API_KEY + "&token=" + FM_TOKEN
    await ctx.send(url)
    get_session(FM_TOKEN)

@bot.command()
async def info(ctx, user):
    await ctx.send(get_userinfo(user))

@bot.command()    
async def top(ctx, user):
    result = get_usertoptracks(user)
    message = [track['name'] for track in result]
    print(message)
    await ctx.send(message)

bot.run(TOKEN)