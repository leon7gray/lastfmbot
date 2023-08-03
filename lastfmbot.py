import asyncio
from hashlib import md5
import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
import requests
import database
import json
import base64

#Discord token
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix='$', intents=intents)

#Spotify token
CLIENT_ID = os.getenv('CLIENT_ID')
CLIENT_SECRET = os.getenv('CLIENT_SECRET')
SPOTIFY_URL = "https://api.spotify.com"

#last.fm token
API_KEY = os.getenv('API_KEY')
SHARED_SECRET = os.getenv('SHARED_SECRET')
ROOT_URL = "http://ws.audioscrobbler.com/2.0/"


def get_lastfm_token():
    url = "?method=auth.gettoken&api_key=" + API_KEY + "&format=json"
    result = requests.post(ROOT_URL + url)
    return result.json()['token']

def get_spotify_token():
    result = requests.post(url="https://accounts.spotify.com/api/token", headers={ "Content-Type": "application/x-www-form-urlencoded" }, 
                           data="grant_type=client_credentials&client_id=" + CLIENT_ID + "&client_secret=" + CLIENT_SECRET)
    print(result.json())
    return result.json()["token_type"], result.json()['access_token']


FM_TOKEN = get_lastfm_token()
SPOTIFY_TOKEN_TYPE, SPOTIFY_TOKEN = get_spotify_token()

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

def get_usertopartists(user):
    url = "?method=user.gettopartists&user=" + user + "&api_key=" + API_KEY + "&format=json&limit=5"
    result = requests.post(ROOT_URL + url)
    return(result.json()["topartists"]["artist"])

def get_nowplaying(user):
    url = "?method=user.getrecenttracks&user=" + user + "&api_key=" + API_KEY + "&format=json&limit=1"
    result = requests.post(ROOT_URL + url)
    return(result.json()["recenttracks"]["track"])

def get_recent(user):
    url = "?method=user.getrecenttracks&user=" + user + "&api_key=" + API_KEY + "&format=json&limit=50"
    result = requests.post(ROOT_URL + url)
    return(result.json()["recenttracks"]["track"])

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
    token = get_lastfm_token()

@bot.command()
async def login(ctx):
    url = "http://www.last.fm/api/auth/?api_key="+ API_KEY + "&token=" + FM_TOKEN
    await ctx.send(url)
    get_session(FM_TOKEN)

@bot.command()
async def set(ctx, user):
    database.set_default_user(ctx.author.name, user)
    await ctx.send("You successfully set your username!")

@bot.command()
async def info(ctx, user=None):
    pass

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

def toptracks_message(message, current_page, time, lastupdated):
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
    else:
        message = ("```" + '\nOverall, you listened to\n' + '\n'.join(message) + "\nlast updated: " + lastupdated.strftime("%Y-%m-%d %H:%M:%S") + '\nTo specify a time frame use overall | 7day | 1month | 3month | 6month | 12month' + "```")
    return message

@bot.command()    
async def np(ctx):
    user = database.get_default_user(ctx.author.name)
    if (user == None):
        await ctx.send("Please set your last.fm username using $set (username)")
        return
    result = get_nowplaying(user)
    if (len(result) == 0):
        await ctx.send("You have not listened to any songs yet.")
    else:
        await ctx.send("Now Playing: " + result[0]["name"])
    
@bot.command()    
async def playing(ctx):
    nowplaying = []
    for member in ctx.guild.members:
        user = database.get_default_user(member.name)
        if user != None:
            np = get_nowplaying(user)
            if (len(np) == 0):
                continue
            if np[0]["@attr"]["nowplaying"] == "true":
                nowplaying.append(member.display_name)
    await ctx.send(', '.join(nowplaying) + " are currently listening to music")

@bot.command()    
async def recent(ctx):
    user = database.get_default_user(ctx.author.name)
    if (user == None):
        await ctx.send("Please set your last.fm username using $set (username)")
        return
    result = database.get_recent(ctx.author.name)
    if (result == None):
        database.insert_recent(ctx.author.name, get_recent(user))
        result = database.get_recent(ctx.author.name)
    message = [(track['name']) for track in result["tracks"]]
    lastupdated = result["lastupdated"]
    for i in range(len(message)):
        message[i] = str(i + 1) + ". " + message[i]

    current_page = 1
    bot_message = await ctx.send(recent_message(message, current_page, lastupdated))
    await bot_message.add_reaction("⬅️")
    await bot_message.add_reaction("➡️")

    # Pagination loop
    def check(reaction, user):
        return (
            reaction.message.id == bot_message.id
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

            page_message = recent_message(message, current_page, lastupdated)
            await bot_message.edit(content=page_message)
            await bot_message.remove_reaction(reaction, user)

        except asyncio.TimeoutError:
            await bot_message.clear_reactions()
            break

def recent_message(message, current_page, lastupdated):
    start_index = (current_page - 1) * 10
    end_index = min(start_index + 10, len(message))
    message = message[start_index:end_index]
    message = ("```" + '\nYou recently listened to\n' + '\n'.join(message) + "\nlast updated: " + lastupdated.strftime("%Y-%m-%d %H:%M:%S") + "```")
    return message

@bot.command()    
async def topArtists(ctx, user):
    result = get_usertopartists(user)
    message = [artist['name'] for artist in result]
    for i in range(len(message)):
        message[i] = (i + 1) + ". " + message[i]
    print(message)
    await ctx.send("```" + '\n' + '\n'.join(message) + "```")

@bot.command()
async def update(ctx):
    database.update(ctx.author.name)
    await ctx.send("Your data has been updated!")

@bot.command()
async def search(ctx, search_type: str, *, query: str):
    """
    Search for music tracks, albums, or artists on Last.fm
    # Define the search URL based on the search type
    if search_type.lower() == "track":
        url = f"?method=track.search&track={query}&api_key={API_KEY}&format=json&limit=1"
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
    """
    result = requests.get(url=SPOTIFY_URL + "/v1/search?q=" + query + "&type=" + search_type + "&limit=1", headers= {"Authorization": SPOTIFY_TOKEN_TYPE + " " + SPOTIFY_TOKEN})
    
    if search_type.lower() == "artist":

        embed = discord.Embed(title=result.json()["artists"]["items"][0]["name"], 
                            url=result.json()["artists"]["items"][0]["external_urls"]["spotify"], 
                            description="Followers: " + str(result.json()["artists"]["items"][0]["followers"]["total"]) , 
                            color=discord.Color.blue())
        embed.add_field(name="Genre(s)", 
                        value=', '.join(result.json()["artists"]["items"][0]["genres"]))
        embed.set_image(url=result.json()["artists"]["items"][0]["images"][0]["url"])
        await ctx.send(embed=embed)
        return
    
    elif search_type.lower() == "album":
        embed = discord.Embed(title=result.json()["albums"]["items"][0]["name"], 
                            url=result.json()["albums"]["items"][0]["external_urls"]["spotify"], 
                            description=result.json()["albums"]["items"][0]["album_type"] + "\n" +  str(result.json()["albums"]["items"][0]["total_tracks"]) + " tracks", 
                            color=discord.Color.blue())
        embed.add_field(name="Released On: " + result.json()["albums"]["items"][0]["release_date"], 
                        value="By " + ", ".join(artist["name"] for artist in result.json()["albums"]["items"][0]["artists"]),
                        inline=False)
        embed.set_image(url=result.json()["albums"]["items"][0]["images"][0]["url"])
        await ctx.send(embed=embed)
        return
    
    else:
        await ctx.send("Invalid search type. Please enter either 'track', 'album', or 'artist'.")
        return

@bot.command()
async def h(ctx):
    help = """```$login: authorize access\n
$set [username]: set your last.fm uesrname\n
$toptrack (overall | 7day | 1month | 3month | 6month | 12month): show top 50 tracks for the user in a given timeframe\n
$update: update all to the latest data\n
$np shows the currently playing song or last listened song\n
$playing shows people in the server who are listening to music right now\n
$recent shows top 50 most recent songs listened
$search (artist | album | track) ```"""

    await ctx.send(help)

bot.run(TOKEN)