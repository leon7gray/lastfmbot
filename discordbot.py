# Import necessary libraries
import asyncio
from hashlib import md5
import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
import requests
import database
import youtube_dl
from yt_dlp import YoutubeDL
from discord.ext import commands
from discord import FFmpegPCMAudio
from pytube import YouTube
import pafy
import vlc
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

# Load environment variables
load_dotenv()

# Get the Discord token from environment variables
TOKEN = os.getenv('DISCORD_TOKEN')

# Set up Discord intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=os.getenv('CLIENT_ID'),client_secret=os.getenv('CLIENT_SECRET')))


# Initialize the bot with the specified command prefix and intents
bot = commands.Bot(command_prefix='!', intents=intents)

# Function to get token
def get_token():
    url = "?method=auth.gettoken&api_key=" + API_KEY + "&format=json"
    result = requests.post(ROOT_URL + url)
    return result.json()['token']

# Get the last.fm API key and shared secret from environment variables
API_KEY = os.getenv('API_KEY')
SHARED_SECRET = os.getenv('SHARED_SECRET')
ROOT_URL = "http://ws.audioscrobbler.com/2.0/"

# Get the last.fm token
FM_TOKEN = get_token()

# Initialize an empty dictionary to store accounts
accounts = {}

# Function to get session
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

# Function to get user info
def get_userinfo(user):
    url = "?method=user.getinfo&user=" + user + "&api_key=" + API_KEY + "&format=json"
    result = requests.post(ROOT_URL + url)
    return(result.json())

# Function to get user top tracks
def get_usertoptracks(user, time=None):
    if (time != None and time != "overall" and time != "7day" and time != "1month" and time != "3month" and time != "6month" and time != "12month"):
        pass
    url = ''
    if (time == None):
        url = "?method=user.gettoptracks&user=" + user + "&api_key=" + API_KEY + "&format=json&limit=50"
    else:
        url = "?method=user.gettoptracks&user=" + user + "&api_key=" + API_KEY + "&format=json&limit=50&period=" + time
    result = requests.post(ROOT_URL + url)
    return(result.json()["toptracks"]["track"])

# Function to get now playing track
def get_nowplaying(user):
    url = "?method=user.getrecenttracks&user=" + user + "&api_key=" + API_KEY + "&format=json&limit=1"
    result = requests.post(ROOT_URL + url)
    return(result.json()["recenttracks"]["track"])

# Function to get recent tracks
def get_recent(user):
    url = "?method=user.getrecenttracks&user=" + user + "&api_key=" + API_KEY + "&format=json&limit=50"
    result = requests.post(ROOT_URL + url)
    return(result.json()["recenttracks"]["track"])

# Event handler for when the bot is ready
@bot.event
async def on_ready():
    for guild in bot.guilds:
        print(f"- {guild.id} (name: {guild.name})")
        print(guild.text_channels)
              
    print(f"{bot.user} has connected to Discord!")
    
    members = '\n - '.join([member.name for member in guild.members])
    print(f'Guild Members:\n - {members}')

# Event handler for when a message is received
@bot.event
async def on_message(message):
    if (message.content == "hello"):
        await message.channel.send("shut up" + message.author.mention)
    await bot.process_commands(message)
                
# Command to get stats
@bot.command()
async def stat(ctx):
    token = get_token()

# Command to log in
@bot.command()
async def login(ctx):
    url = "http://www.last.fm/api/auth/?api_key="+ API_KEY + "&token=" + FM_TOKEN
    await ctx.send(url)
    get_session(FM_TOKEN)

# Command to set user
@bot.command()
async def set(ctx, user):
    database.set_default_user(ctx.author.name, user)
    await ctx.send("You successfully set your username!")

# Command to get info
@bot.command()
async def info(ctx, user=None):
    if user != None:
        await ctx.send(get_userinfo(user))
        return
    else:
        if (ctx.author not in accounts.keys()):
            await ctx.send("Please set your default username using the command '$set'")
            return
        await ctx.send(get_userinfo(accounts[ctx.author]))

# Command to get top tracks
@bot.command()    
async def toptracks(ctx, time="overall"):
    user = database.get_default_user(ctx.author.name)
    if (user == None):
        await ctx.send("Please set your last.fm username using $set (username)")
        return
    result = database.get_toptracks(ctx.author.name, time)
    if (result == None):
        database.insert_toptracks(ctx.author.name, get_usertoptracks(user, time), time)
        result = database.get_toptracks(ctx.author.name, time)
    message = [(track['name'] + " - " + track["playcount"] + " times") for track in result["tracks"]]
    lastupdated = result["lastupdated"]
    for i in range(len(message)):
        message[i] = str(i + 1) + ". " + message[i]

    current_page = 1
    bot_message = await ctx.send(toptracks_message(message, current_page, time, lastupdated))
    await bot_message.add_reaction("⬅️")
    await bot_message.add_reaction("➡️")

    # Pagination loop
    def check(reaction, user):
        return (
            reaction.message.id == bot_message.id
            and user == ctx.author
            and str(reaction.emoji) in ["⬅️", "➡️"]
        )

    while True:
        try:
            reaction, user = await bot.wait_for("reaction_add", timeout=60, check=check)

            if str(reaction.emoji) == "➡️" and current_page < 5:
                current_page += 1
            elif str(reaction.emoji) == "⬅️" and current_page > 1:
                current_page -= 1
            else:
                continue

            page_message = toptracks_message(message, current_page, time, lastupdated)
            await bot_message.edit(content=page_message)
            await bot_message.remove_reaction(reaction, user)

        except asyncio.TimeoutError:
            await bot_message.clear_reactions()
            break

# Function to format the top tracks message
def toptracks_message(message, current_page, time, lastupdated):
    start_index = (current_page - 1) * 10
    end_index = min(start_index + 10, len(message))
    message = message[start_index:end_index]
    # Format the message based on the time period
    if (time == "overall"):
        message = ("```" + '\nOverall, you listened to\n' + '\n'.join(message) + "\nlast updated: " + lastupdated.strftime("%Y-%m-%d %H:%M:%S") + "```")
    elif (time == "7day"):
        message = ("```" + '\nFor the past week, you listened to\n' + '\n'.join(message) + "\nlast updated: " + lastupdated.strftime("%Y-%m-%d %H:%M:%S") + "```")
    elif (time == "1month"):
        message = ("```" + '\nFor the past month, you listened to\n' + '\n'.join(message) + "\nlast updated: " + lastupdated.strftime("%Y-%m-%d %H:%M:%S") + "```")
    elif (time == "3month"):
        message = ("```" + '\nFor the past 3 months, you listened to\n' + '\n'.join(message) + "\nlast updated: " + lastupdated.strftime("%Y-%m-%d %H:%M:%S") + "```")
    elif (time == "6month"):
        message = ("```" + '\nFor the past 6 months, you listened to\n' + '\n'.join(message) + "\nlast updated: " + lastupdated.strftime("%Y-%m-%d %H:%M:%S") + "```")
    elif (time == "12month"):
        message = ("```" + '\nFor the past year, you listened to\n' + '\n'.join(message) + "\nlast updated: " + lastupdated.strftime("%Y-%m-%d %H:%M:%S") + "```")
    return message

# Command to get now playing track
@bot.command()    
async def np(ctx):
    user = database.get_default_user(ctx.author.name)
    if (user == None):
        await ctx.send("Please set your last.fm username using $set (username)")
        return
    result = get_nowplaying(user)
    await ctx.send("Now Playing: " + result[0]["name"])
    
# Command to get who's playing music
@bot.command()    
async def playing(ctx):
    nowplaying = []
    for member in ctx.guild.members:
        user = database.get_default_user(ctx.author.name)
        if user != None:
            np = get_nowplaying(user)
            if np[0].nowplaying == "true":
                nowplaying.append(member)
    await ctx.send(', '.join(nowplaying) + " are currently listening to music")

# Command to get recent tracks
@bot.command()    
async def recent(ctx):
    user = database.get_default_user(ctx.author.name)
    if (user == None):
        await ctx.send("Please set your last.fm username using $set (username)")
        return
    result = get_recent(user)
    if (result == None):
        database.insert_recent(ctx.author.name, result)
        result = database.get_recent(ctx.author.name)
    message = [(track['name']) for track in result["tracks"]]
    lastupdated = result["lastupdated"]
    for i in range(len(message)):
        message[i] = str(i + 1) + ". " + message[i]

    current_page = 1
    bot_message = await ctx.send(toptracks_message(message, current_page, lastupdated))
    await bot_message.add_reaction("⬅️")
    await bot_message.add_reaction("➡️")

    # Pagination loop
    def check(reaction, user):
        return (
            reaction.message.id == bot_message.id
            and user == ctx.author
            and str(reaction.emoji) in ["⬅️", "➡️"]
        )

    while True:
        try:
            reaction, user = await bot.wait_for("reaction_add", timeout=60, check=check)

            if str(reaction.emoji) == "➡️" and current_page < 5:
                current_page += 1
            elif str(reaction.emoji) == "⬅️" and current_page > 1:
                current_page -= 1
            else:
                continue

            page_message = toptracks_message(message, current_page, lastupdated)
            await bot_message.edit(content=page_message)
            await bot_message.remove_reaction(reaction, user)

        except asyncio.TimeoutError:
            await bot_message.clear_reactions()
            break   

# Function to format the recent tracks message
def recent_message(message, current_page, lastupdated):
    start_index = (current_page - 1) * 10
    end_index = min(start_index + 10, len(message))
    message = message[start_index:end_index]
    message = ("```" + '\nYou recently listened to\n' + '\n'.join(message) + "\nlast updated: " + lastupdated.strftime("%Y-%m-%d %H:%M:%S") + "```")
    return message


# Command to update data
@bot.command()
async def update(ctx):
    database.update(ctx.author.name)
    await ctx.send("Your data has been updated!")

# Command to display help
@bot.command()
async def h(ctx):
    help = """```$login: authorize access\n
$set [username]: set your last.fm uesrname\n
$toptrack (overall | 7day | 1month | 3month | 6month | 12month): show top 10 tracks for the user in a given timeframe\n
$update: update all to the latest data```"""
    await ctx.send(help)

@bot.command()
async def search(ctx, search_type: str, *, query: str):
    """Search for music tracks, albums, or artists on Last.fm"""
    # Define the search URL based on the search type
    if search_type.lower() == "track":
        url = f"?method=track.search&track={query}&api_key={API_KEY}&format=json"
    elif search_type.lower() == "album":
        url = f"?method=album.search&album={query}&api_key={API_KEY}&format=json"
    elif search_type.lower() == "artist":
        url = f"?method=artist.search&artist={query}&api_key={API_KEY}&format=json"
    else:
        await ctx.send("Invalid search type. Please enter either 'track', 'album', or 'artist'.")
        return

    # send request to the Last.fm API
    response = requests.get(ROOT_URL + url)
    data = response.json()

    # send search results to the user
    await ctx.send(data["results"]["artistmatches"]["artist"][0]["image"])


def get_usertopartists(user, time=None):
    if (time != None and time != "overall" and time != "7day" and time != "1month" and time != "3month" and time != "6month" and time != "12month"):
        pass
    url = ''
    if (time == None):
        url = "?method=user.gettopartists&user=" + user + "&api_key=" + API_KEY + "&format=json&limit=50"
    else:
        url = "?method=user.gettopartists&user=" + user + "&api_key=" + API_KEY + "&format=json&limit=50&period=" + time
    result = requests.post(ROOT_URL + url)
    return(result.json()["topartists"]["artist"])

# Command to get top artists
@bot.command()    
async def topartists(ctx, time="overall"):
    user = database.get_default_user(ctx.author.name)
    if (user == None):
        await ctx.send("Please set your last.fm username using $set (username)")
        return
    result = database.get_topartists(ctx.author.name, time)
    if (result == None):
        database.insert_topartists(ctx.author.name, get_usertopartists(user, time), time)
        result = database.get_topartists(ctx.author.name, time)
    message = [(artist['name'] + " - " + artist["playcount"] + " times") for artist in result["artists"]]
    lastupdated = result["lastupdated"]
    for i in range(len(message)):
        message[i] = str(i + 1) + ". " + message[i]

    current_page = 1
    bot_message = await ctx.send(topartists_message(message, current_page, time, lastupdated))
    await bot_message.add_reaction("⬅️")
    await bot_message.add_reaction("➡️")

    # Pagination loop
    def check(reaction, user):
        return (
            reaction.message.id == bot_message.id
            and user == ctx.author
            and str(reaction.emoji) in ["⬅️", "➡️"]
        )

    while True:
        try:
            reaction, user = await bot.wait_for("reaction_add", timeout=60, check=check)

            if str(reaction.emoji) == "➡️" and current_page < 5:
                current_page += 1
            elif str(reaction.emoji) == "⬅️" and current_page > 1:
                current_page -= 1
            else:
                continue

            page_message = topartists_message(message, current_page, time, lastupdated)
            await bot_message.edit(content=page_message)
            await bot_message.remove_reaction(reaction, user)

        except asyncio.TimeoutError:
            await bot_message.clear_reactions()
            break

# Function to format the top artists message
def topartists_message(message, current_page, time, lastupdated):
    start_index = (current_page - 1) * 10
    end_index = min(start_index + 10, len(message))
    message = message[start_index:end_index]
    if (time == "overall"):
        message = ("```" + '\nOverall, you listened to\n' + '\n'.join(message) + "\nlast updated: " + lastupdated.strftime("%Y-%m-%d %H:%M:%S") + "```")
    elif (time == "7day"):
        message = ("```" + '\nFor the past week, you listened to\n' + '\n'.join(message) + "\nlast updated: " + lastupdated.strftime("%Y-%m-%d %H:%M:%S") + "```")
    elif (time == "1month"):
        message = ("```" + '\nFor the past month, you listened to\n' + '\n'.join(message) + "\nlast updated: " + lastupdated.strftime("%Y-%m-%d %H:%M:%S") + "```")
    elif (time == "3month"):
        message = ("```" + '\nFor the past 3 months, you listened to\n' + '\n'.join(message) + "\nlast updated: " + lastupdated.strftime("%Y-%m-%d %H:%M:%S") + "```")
    elif (time == "6month"):
        message = ("```" + '\nFor the past 6 months, you listened to\n' + '\n'.join(message) + "\nlast updated: " + lastupdated.strftime("%Y-%m-%d %H:%M:%S") + "```")
    elif (time == "12month"):
        message = ("```" + '\nFor the past year, you listened to\n' + '\n'.join(message) + "\nlast updated: " + lastupdated.strftime("%Y-%m-%d %H:%M:%S") + "```")
    return message

@bot.command()
async def join(ctx):
    if ctx.author.voice is None:
        await ctx.send("You're not in a voice channel!")
    else:
        channel = ctx.author.voice.channel
        await channel.connect()

from yt_dlp import YoutubeDL

# Dictionary to store search results
search_results = {}

@bot.command()
async def find(ctx, *, track):
    try:
        results = sp.search(q=track, limit=10, type='track')  # Change limit to the number of results you want to provide
        tracks = results['tracks']['items']
        response = "Here are the top results:\n"
        for i, track in enumerate(tracks, start=1):
            track_name = track['name']
            track_artist = track['artists'][0]['name']
            response += f"{i}. **{track_name}** by **{track_artist}**\n"
        response += "\nType `!play number` to play a track."
        await ctx.send(response)

        # Store the search results in the global dictionary
        search_results[ctx.channel.id] = tracks
    except Exception as e:
        await ctx.send(f"An error occurred while searching for this track: {str(e)}")

@bot.command()
async def play(ctx, number: int):
    channel_id = ctx.channel.id
    if channel_id not in search_results or number < 1 or number > len(search_results[channel_id]):
        await ctx.send("Invalid track number. Please use the `!find` command to get a list of tracks.")
        return

    track = search_results[channel_id][number - 1]
    track_url = track['external_urls']['spotify']
    track_name = track['name']
    track_artist = track['artists'][0]['name']

    await ctx.send(f"Playing track {number}: **{track_name}** by **{track_artist}**\n{track_url}")


@bot.command()
async def leave(ctx):
    voice = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    if voice.is_connected():
        await voice.disconnect()
    else:
        await ctx.send("The bot is not connected to a voice channel.")


# Run the bot
bot.run(TOKEN)

