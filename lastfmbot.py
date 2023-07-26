from hashlib import md5
import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
import requests
import database

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

accounts = {}

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
        url = "?method=user.gettoptracks&user=" + user + "&api_key=" + API_KEY + "&format=json&limit=10"
    else:
        url = "?method=user.gettoptracks&user=" + user + "&api_key=" + API_KEY + "&format=json&limit=10&period=" + time
    result = requests.post(ROOT_URL + url)
    return(result.json()["toptracks"]["track"])

def get_usertopartists(user):
    url = "?method=user.gettopartists&user=" + user + "&api_key=" + API_KEY + "&format=json&limit=5"
    result = requests.post(ROOT_URL + url)
    return(result.json()["topartists"]["artist"])

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
async def set(ctx, user):
    database.set_default_user(ctx.author.name, user)
    await ctx.send("You successfully set your username!")

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

@bot.command()    
async def toptracks(ctx, time="overall"):
    user = database.get_default_user(ctx.author.name)
    result = database.get_toptracks(ctx.author.name, time)
    if (result == None):
        database.insert_toptracks(ctx.author.name, get_usertoptracks(user, time), time="overall")
        result = database.get_toptracks(ctx.author.name, time)
    print(result)
    message = [(track['name'] + " - " + track["playcount"] + " times") for track in result["tracks"]]
    current_time = result["lastupdated"]
    for i in range(len(message)):
        message[i] = str(i + 1) + ". " + message[i]
    
    if (time == "overall"):
        await ctx.send("```" + '\nOverall, you listened to\n' + '\n'.join(message) + "\nlast updated: " + current_time.strftime("%Y-%m-%d %H:%M:%S") + "```")
    elif (time == "7day"):
        await ctx.send("```" + '\n' + "For the past week, you listened to " + '\n' + '\n'.join(message) + "```")
    elif (time == "1month"):
        await ctx.send("```" + '\n' + "For the past month, you listened to " + '\n' + '\n'.join(message) + "```")
    elif (time == "3month"):
        await ctx.send("```" + '\n' + "For the past 3 months, you listened to " + '\n' + '\n'.join(message) + "```")
    elif (time == "6month"):
        await ctx.send("```" + '\n' + "For the past 6 months, you listened to " + '\n' + '\n'.join(message) + "```")
    elif (time == "12month"):
        await ctx.send("```" + '\n' + "For the past year, You listened to " + '\n' + '\n'.join(message) + "```")

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
async def h(ctx):
    help = """```$login: authorize access\n
$set [username]: set your last.fm uesrname\n
$toptrack (overall | 7day | 1month | 3month | 6month | 12month): show top 10 tracks for the user in a given timeframe\n
$update: update all to the latest data```"""
    await ctx.send(help)

bot.run(TOKEN)