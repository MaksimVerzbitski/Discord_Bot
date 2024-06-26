import ssl
import certifi
import sys
import os
import logging
import asyncio
import discord
import random
from discord.ext import commands
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from pytz import timezone
import yt_dlp as youtube_dl
from dotenv import load_dotenv
from discord import app_commands

# Configure stdout for utf-8
sys.stdout.reconfigure(encoding='utf-8')

# Configure SSL context
ssl._create_default_https_context = ssl._create_unverified_context
ssl.create_default_context(cafile=certifi.where())

# Configure logging
logging.getLogger('apscheduler').setLevel(logging.DEBUG)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', handlers=[logging.StreamHandler(sys.stdout)])
logger = logging.getLogger()

# Global variables
song_queue = []
current_song_index = 0
music_dir = 'download/'

# Load environment variables
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
CHANNEL_ID = os.getenv('CHANNEL_ID')
USER_ID = os.getenv('USER_ID')
USER_MAX_ID = os.getenv('USER_MAX_ID')

# Define the MusicBot class
class MusicBot(commands.Bot):
    async def setup_hook(self):
        await self.tree.sync()

# Define intents
intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.voice_states = True
intents.message_content = True

# Instantiate the bot
bot = MusicBot(command_prefix='!', intents=intents)

# Define the scheduler
scheduler = AsyncIOScheduler(timezone="Europe/Tallinn")

@bot.event
async def on_ready():
    logger.info(f'{bot.user.name} has connected to Discord!')

    default_recipient_id = USER_MAX_ID
    tatjana_recipient_id = USER_ID

    scheduler.add_job(send_love_message, CronTrigger(hour=9, minute=30), args=[default_recipient_id])
    scheduler.add_job(send_love_message, CronTrigger(hour=9, minute=45), args=[tatjana_recipient_id])

    scheduler.start()
    await bot.tree.sync()

def get_local_songs():
    return [os.path.join(music_dir, f) for f in os.listdir(music_dir) if f.endswith(('.mp3', '.ogg', '.wav', '.webm'))]

async def play_local(interaction, song_path):
    voice_client = interaction.guild.voice_client
    if not voice_client:
        await interaction.response.send_message("The bot is not in a voice channel.")
        return

    if not voice_client.is_playing():
        voice_client.play(discord.FFmpegPCMAudio(song_path), after=lambda e: asyncio.run_coroutine_threadsafe(play_next_song(interaction), bot.loop))
        await interaction.response.send_message(f"Now playing: {os.path.basename(song_path)}")
    else:
        await interaction.response.send_message("Audio is already playing. Please stop the current track first.")

@bot.tree.command(name='join', description='Tells the bot to join the voice channel')
async def join(interaction: discord.Interaction):
    logger.info("Attempting to join a voice channel...")
    if not interaction.user.voice:
        await interaction.response.send_message("You are not connected to a voice channel", ephemeral=True)
        return

    channel = interaction.user.voice.channel
    voice_client = await channel.connect()
    logger.info(f"Joined {channel.name} successfully.")
    await interaction.response.send_message("Bot has joined the voice channel. Type `/help` to see all commands.")

    entrance_sound = 'sounds/nokia-tune-1600-36527.mp3'
    if not voice_client.is_playing():
        voice_client.play(discord.FFmpegPCMAudio(entrance_sound), after=lambda e: logger.info('Entrance sound finished playing.', e) if e else None)

@bot.tree.command(name='leave', description='Leaves the voice channel')
async def leave(interaction: discord.Interaction):
    voice_client = discord.utils.get(bot.voice_clients, guild=interaction.guild)
    if voice_client and voice_client.is_connected():
        await voice_client.disconnect()
        await interaction.response.send_message("The bot has left the voice channel.")
    else:
        await interaction.response.send_message("The bot is not connected to a voice channel.", ephemeral=True)

@bot.tree.command(name='play', description='To play or search a song from YouTube')
@app_commands.describe(search='The song to search or play from YouTube')
async def play(interaction: discord.Interaction, search: str):
    server = interaction.guild
    voice_channel = server.voice_client
    if voice_channel.is_playing():
        voice_channel.stop()

    await interaction.response.defer()
    print("Searching for video...")
    video_url = await YTDLSource.search(search, loop=bot.loop)

    if video_url.startswith("An error occurred"):
        await interaction.followup.send(video_url)
        return

    try:
        player = await YTDLSource.from_url(video_url, loop=bot.loop)
        total_duration = format_duration(player.data['duration'])
        await interaction.followup.send(f"**Now playing:** {player.data['fulltitle']} **Duration:** {total_duration}")

        if not voice_channel.is_playing():
            voice_channel.play(player, after=lambda e: asyncio.run_coroutine_threadsafe(play_next_song(interaction), bot.loop))
        else:
            await interaction.followup.send("Audio is already playing. Please stop the current track first.")

    except Exception as e:
        await interaction.followup.send(f"An error occurred: {e}")
        print(f"An error occurred: {e}")

@bot.tree.command(name='stop', description='Stops the music and clears the queue')
async def stop(interaction: discord.Interaction):
    voice_client = interaction.guild.voice_client
    if voice_client.is_playing():
        voice_client.stop()
        await interaction.response.send_message("Music stopped.")
    else:
        await interaction.response.send_message("No music is playing.", ephemeral=True)

@bot.tree.command(name='resume', description='Resumes the music')
async def resume(interaction: discord.Interaction):
    voice_client = interaction.guild.voice_client
    if voice_client and not voice_client.is_playing():
        voice_client.resume()
        await interaction.response.send_message("Music resumed.")
    else:
        await interaction.response.send_message("No music to resume.", ephemeral=True)

@bot.tree.command(name='shuffle', description='Shuffles and plays the music queue randomly from local files')
async def shuffle(interaction: discord.Interaction):
    global song_queue
    song_queue = get_local_songs()

    if not song_queue:
        await interaction.response.send_message("No songs found in the local directory.")
        return

    await play_next_song(interaction)

class YTDLSource(discord.PCMVolumeTransformer):
    YDL_OPTIONS = {
        'format': 'bestaudio',
        'noplaylist': 'True',
        'outtmpl': 'download/%(title)s-%(id)s.%(ext)s',
    }
    FFMPEG_OPTIONS = {
        'options': '-vn',
    }

    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume=volume)
        self.data = data
        self.title = data.get('title')
        print(f"Initialized YTDLSource with title: {self.title}")

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        print(f"Extracting info from URL: {url}")
        ydl = youtube_dl.YoutubeDL(cls.YDL_OPTIONS)
        data = await loop.run_in_executor(None, lambda: ydl.extract_info(url, download=not stream))
        print("Extraction complete.")

        if 'entries' in data:
            data = data['entries'][0]

        filename = data['url'] if stream else ydl.prepare_filename(data)
        print(f"Preparing to play: {data.get('title')}")
        return cls(discord.FFmpegPCMAudio(filename, **cls.FFMPEG_OPTIONS), data=data)

    @classmethod
    async def search(cls, search_query, *, loop=None, max_results=10):
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
            'restrictfilenames': True,
            'noplaylist': True,
            'nocheckcertificate': True,
            'ignoreerrors': False,
            'logtostderr': False,
            'quiet': True,
            'no_warnings': True,
            'default_search': f'ytsearch{max_results}',
            'source_address': '0.0.0.0'
        }

        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            try:
                info = await loop.run_in_executor(None, lambda: ydl.extract_info(f"ytsearch{max_results}:{search_query}", download=False))
                if 'entries' not in info or not info['entries']:
                    print(f"No entries found for search query: {search_query}")
                    return "No results found."
                results = []
                for entry in info['entries']:
                    if 'title' in entry and 'webpage_url' in entry:
                        results.append((entry['title'], entry['webpage_url']))
                return results if results else "No results found."
            except Exception as e:
                print(f"An error occurred during the search: {e}")
                return f"An error occurred: {e}"

@bot.tree.command(name='search', description='Searches for songs on YouTube and allows selection')
@app_commands.describe(query='The search query to find songs on YouTube')
async def search(interaction: discord.Interaction, query: str):
    voice_channel = interaction.guild.voice_client
    if not voice_channel:
        await interaction.response.send_message("Bot is not connected to a voice channel.")
        return

    await interaction.response.defer()
    search_results = await YTDLSource.search(query, loop=bot.loop)
    if not search_results:
        await interaction.followup.send("No results found.")
        return

    if isinstance(search_results, str):
        await interaction.followup.send(search_results)
        return

    results_message = "\n".join([f"{index + 1}. {title}" for index, (title, _) in enumerate(search_results[:10])])
    message = await interaction.followup.send(f"Search results:\n{results_message}\n\nReact to choose a song or ❌ to cancel.", wait=True)

    selection_emojis = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣', '🔟', '❌']
    for emoji in selection_emojis:
        await message.add_reaction(emoji)

    def check(reaction, user):
        return user == interaction.user and str(reaction.emoji) in selection_emojis and reaction.message.id == message.id

    try:
        reaction, user = await bot.wait_for('reaction_add', timeout=60.0, check=check)
        await message.clear_reactions()

        if str(reaction.emoji) == '❌':
            await interaction.followup.send("Search cancelled.")
        else:
            song_index = selection_emojis.index(str(reaction.emoji))
            if 0 <= song_index < len(search_results):
                title, url = search_results[song_index]
                player = await YTDLSource.from_url(url, loop=bot.loop)
                voice_channel.play(player, after=lambda e: print(f'Player error: {e}') if e else None)
                await interaction.followup.send(f'**Now playing:** {title}')

    except asyncio.TimeoutError:
        await message.clear_reactions()
        await interaction.followup.send("No response in time.")
        
def format_duration(duration):
    minutes, seconds = divmod(duration, 60)
    hours, minutes = divmod(minutes, 60)
    if hours > 0:
        return f"{hours}:{minutes:02}:{seconds:02}"
    else:
        return f"{minutes}:{seconds:02}"

async def play_next_song(ctx):
    global current_song_index

    if song_queue:
        current_song_index = random.randint(0, len(song_queue) - 1)
        song_path = song_queue[current_song_index]
        await play_local(ctx, song_path)
    else:
        await ctx.send("The song queue is empty.")

@bot.tree.command(name='next', description='Plays the next song in the queue')
async def next_song(interaction: discord.Interaction):
    global current_song_index
    current_song_index += 1
    if current_song_index < len(song_queue):
        await play_song(interaction, song_queue[current_song_index])
    else:
        await interaction.response.send_message("Reached the end of the queue.")

@bot.tree.command(name='previous', description='Plays the previous song in the queue')
async def previous_song(interaction: discord.Interaction):
    global current_song_index
    if current_song_index > 0:
        current_song_index -= 1
        await play_song(interaction, song_queue[current_song_index])
    else:
        await interaction.response.send_message("This is the first song in the queue.")

async def play_song(interaction, song_path):
    voice_client = discord.utils.get(bot.voice_clients, guild=interaction.guild)
    if voice_client.is_playing():
        await interaction.response.send_message("Already playing audio.")
        return

    voice_client.play(discord.FFmpegPCMAudio(song_path), after=lambda e: asyncio.run_coroutine_threadsafe(play_next_song(interaction), bot.loop))
    await interaction.response.send_message(f"Now playing: {os.path.basename(song_path)}")

@bot.tree.command(name='reload', description='Reloads a module.')
@commands.is_owner()
@app_commands.describe(extension='The extension to reload')
async def reload(interaction: discord.Interaction, extension: str):
    if extension:
        try:
            await bot.reload_extension(f'cogs.{extension}')
            await interaction.response.send_message(f'Reloaded `{extension}` cog.')
        except Exception as e:
            await interaction.response.send_message(f'Error reloading `{extension}`: {e}')
    else:
        await interaction.response.send_message('No extension specified.')

async def send_love_message(recipient_id=None):
    try:
        channel = bot.get_channel(int(CHANNEL_ID))
        if channel:
            if recipient_id:
                await channel.send(f"<@{recipient_id}> :point_right:, I love you :open_hands: this much :pinching_hand: ❤️")
            else:
                await channel.send("Sending love to everyone! :heart:")
    except Exception as e:
        print(f"Error in send_love_message: {e}")

@bot.tree.command(name='love', description='Schedules a love message. Type the command and follow the prompt.')
async def love(interaction: discord.Interaction):
    await interaction.response.send_message("Please enter the hour (0-23) to schedule the love message:")

    def check_hour(msg):
        return msg.author == interaction.user and msg.channel == interaction.channel and msg.content.isdigit() and 0 <= int(msg.content) <= 23

    try:
        hour_msg = await bot.wait_for('message', check=check_hour, timeout=30.0)
        hour = int(hour_msg.content)

        await interaction.followup.send("Please enter the minutes (0-59):")

        def check_minutes(msg):
            return msg.author == interaction.user and msg.channel == interaction.channel and msg.content.isdigit() and 0 <= int(msg.content) <= 59

        minutes_msg = await bot.wait_for('message', check=check_minutes, timeout=30.0)
        minutes = int(minutes_msg.content)

        sender_id = interaction.user.id
        recipient_id = USER_ID if str(sender_id) == USER_MAX_ID else USER_MAX_ID

        scheduler.add_job(send_love_message, CronTrigger(hour=hour, minute=minutes), args=[recipient_id], id=f"love_message_{interaction.user.id}_{recipient_id}_{hour:02d}:{minutes:02d}")

        await interaction.followup.send(f"Love message scheduled for {hour:02d}:{minutes:02d} to <@{recipient_id}>.")
    except asyncio.TimeoutError:
        await interaction.followup.send("You didn't respond in time, please try the command again.")
    except Exception as e:
        await interaction.followup.send(f"An error occurred: {e}")

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"Missing required argument: {error.param.name}")
    elif isinstance(error, commands.CommandNotFound):
        await ctx.send("Command not found.")
    elif isinstance(error, commands.CommandInvokeError):
        await ctx.send(f"Command invoke error: {error.original}")
        logger.error(f"Command invoke error: {error.original}")
    else:
        await ctx.send("An error occurred while processing your command.")
        logger.error(f"Unexpected error: {error}")
        raise error

@bot.event
async def on_message(message):
    await bot.process_commands(message)

bot.run(TOKEN)
