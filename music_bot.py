from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from pytz import timezone


import discord
from discord.ext import commands
import yt_dlp as youtube_dl
import asyncio
import random
import logging
import datetime

# Load environment variables
from dotenv import load_dotenv
import os

logging.basicConfig()
logging.getLogger('apscheduler').setLevel(logging.DEBUG)


song_queue = []
current_song_index = 0
music_dir = 'download/'


load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
CHANNEL_ID = os.getenv('CHANNEL_ID')
USER_ID = os.getenv('USER_ID')
USER_MAX_ID = os.getenv('USER_MAX_ID')



intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.voice_states = True
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)


scheduler = AsyncIOScheduler(timezone="Europe/Tallinn")



@bot.event
async def on_ready():
    print(f'{bot.user.name} has connected to Discord!')

    # Decide the recipient for the scheduled message
    default_recipient_id = USER_MAX_ID  # or USER_MAX_ID, depending on your preference

    tatjana_recipient_id = USER_ID
    # Schedule morning message at 9:30 AM
    scheduler.add_job(send_love_message, CronTrigger(hour=9, minute=30), args=[default_recipient_id])
    # Schedule evening message at 8 PM
    scheduler.add_job(send_love_message, CronTrigger(hour=9, minute=45), args=[tatjana_recipient_id])

    scheduler.start()



bot.remove_command('help')  # Remove the default help command


@bot.command(name='help', help='Displays all available commands')
async def custom_help(ctx):
    help_message = "**Available Commands:**\n```css\n"  # CSS for syntax highlighting
    commands_list = sorted(bot.commands, key=lambda x: x.name)  # Sort commands alphabetically
    longest_command = max(len(command.name) for command in commands_list) + 2  # Find the longest command for padding
    longest_description = max(len(command.help) for command in commands_list if command.help) + 2  # Find the longest description
    line = '-' * (longest_command + longest_description + 3)  # Create a dividing line

    # Add table headers
    help_message += f"{'Command'.ljust(longest_command)} | {'Description'.ljust(longest_description)}\n"
    help_message += f"{line}\n"

    # Add each command and its description to the table
    for command in commands_list:
        command_name = f"!{command.name}".ljust(longest_command)  # Pad the command name
        description = (command.help or "No description").ljust(longest_description)  # Pad the description
        help_message += f"{command_name} | {description}\n"

    help_message += "```"  # End the code block
    await ctx.send(help_message)

def get_local_songs():
    # Get all files in the music directory
    return [os.path.join(music_dir, f) for f in os.listdir(music_dir) if f.endswith(('.mp3', '.ogg', '.wav', '.webm'))]



@bot.command(name='shuffle', help='Shuffles and plays the music queue randomly from local files')
async def shuffle(ctx):
    global song_queue
    song_queue = get_local_songs()  # Reload the song list in case new songs have been added

    if not song_queue:
        await ctx.send("No songs found in the local directory.")
        return

    await play_next_song(ctx)  # Start playing a random song

async def play_local(ctx, song_path):
    voice_client = ctx.guild.voice_client
    if not voice_client:
        await ctx.send("The bot is not in a voice channel.")
        return

    # Play the song and set play_next_song as the after callback
    voice_client.play(discord.FFmpegPCMAudio(song_path), after=lambda e: asyncio.run_coroutine_threadsafe(play_next_song(ctx), bot.loop))
    await ctx.send(f"Now playing: {os.path.basename(song_path)}")



@bot.command(name='join', help='Tells the bot to join the voice channel')
async def join(ctx):
    print("Attempting to join a voice channel...")
    if not ctx.message.author.voice:
        await ctx.send("You are not connected to a voice channel")
        return

    channel = ctx.message.author.voice.channel
    voice_client = await channel.connect()
    print(f"Joined {channel.name} successfully.")
    await ctx.send("Bot has joined the voice channel. Type `!help` to see all commands.")

    # Play an audio file upon joining
    entrance_sound = 'sounds/nokia-tune-1600-36527.mp3'  # Update this path to your audio file
    if not voice_client.is_playing():
        voice_client.play(discord.FFmpegPCMAudio(entrance_sound), after=lambda e: print('Entrance sound finished playing.', e) if e else None)

@bot.command(name='leave', help='To make the bot leave the voice channel')
async def leave(ctx):
    print("Attempting to leave a voice channel...")
    voice_client = ctx.message.guild.voice_client
    if voice_client.is_connected():
        await voice_client.disconnect()
        print("Disconnected successfully.")
    else:
        await ctx.send("The bot is not connected to a voice channel.")
        print("The bot was not in a voice channel.")


def format_duration(seconds):
    mins, secs = divmod(int(seconds), 60)
    hours, mins = divmod(mins, 60)
    if hours:
        return f"{hours:d}:{mins:02d}:{secs:02d}"
    else:
        return f"{mins:d}:{secs:02d}"


@bot.command(name='play', help='To play or search a song from YouTube')
async def play(ctx, *, search: str):
    server = ctx.message.guild
    voice_channel = server.voice_client
    # Stop current audio if playing
    if voice_channel.is_playing():
        voice_channel.stop()

    async with ctx.typing():
        print("Searching for video...")
        # Use the search method to get the video URL
        video_url = await YTDLSource.search(search, loop=bot.loop)

        # Check if the search function returned an error message
        if video_url.startswith("An error occurred"):
            await ctx.send(video_url)  # Send the error message to the Discord channel
            return

        # Use the from_url method to play the audio from the search result
        try:
            player = await YTDLSource.from_url(video_url, loop=bot.loop)
            total_duration = format_duration(player.data['duration'])
            await ctx.send(f"**Now playing:** {player.data['fulltitle']} **Duration:** {total_duration}")

        except Exception as e:
            await ctx.send(f"An error occurred: {e}")
            print(f"An error occurred: {e}")
    

@bot.command(name='stop', help='Stops the music and clears the queue')
async def stop(ctx):
    voice_client = ctx.message.guild.voice_client
    if voice_client.is_playing():
        voice_client.stop()
        await ctx.send("Music stopped.")
    else:
        await ctx.send("No music is playing.")

@bot.command(name='resume', help='Resumes the music')
async def resume(ctx):
    voice_client = ctx.guild.voice_client
    if voice_client and not voice_client.is_playing():
        voice_client.resume()


class YTDLSource(discord.PCMVolumeTransformer):
    YDL_OPTIONS = {
        'format': 'bestaudio',
        'noplaylist': 'True',
        # Specify the output template here, including the directory
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
            'noplaylist': True,  # only download single song, not playlist
            'nocheckcertificate': True,
            'ignoreerrors': False,
            'logtostderr': False,
            'quiet': True,
            'no_warnings': True,
            'default_search': f'ytsearch{max_results}',
            'source_address': '0.0.0.0'  # bind to ipv4 since ipv6 addresses cause issues sometimes
        }

        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            try:
                # The 'ytsearchN:' prefix tells yt-dlp to perform a search and return the top N results
                info = await loop.run_in_executor(None, lambda: ydl.extract_info(f"ytsearch{max_results}:{search_query}", download=False))
                if 'entries' not in info or not info['entries']:
                    print(f"No entries found for search query: {search_query}")
                    return None
                results = []
                for entry in info['entries']:
                    # Check if the expected keys exist before accessing them
                    if 'title' in entry and 'webpage_url' in entry:
                        results.append((entry['title'], entry['webpage_url']))
                return results if results else None
            except Exception as e:
                print(f"An error occurred during the search: {e}")
                return None
            

@bot.command(name='search', help='Searches for songs on YouTube and allows selection')
async def search(ctx, *, query: str):
    voice_channel = ctx.guild.voice_client
    if not voice_channel:
        await ctx.send("Bot is not connected to a voice channel.")
        return

    search_results = await YTDLSource.search(query, loop=bot.loop)
    if not search_results:
        await ctx.send("No results found.")
        return

    results_message = "\n".join([f"{index}. {title}" for index, (title, _) in enumerate(search_results[:10], start=1)])
    message = await ctx.send(f"Search results:\n{results_message}\n\nReact to choose a song or ❌ to cancel.")

    # Add reactions for song selection and actions
    selection_emojis = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣', '🔟', '🔀', '⬅️', '➡️', '❌']
    for emoji in selection_emojis:
        await message.add_reaction(emoji)

    def check(reaction, user):
        return user == ctx.author and str(reaction.emoji) in selection_emojis and reaction.message.id == message.id

    try:
        reaction, user = await bot.wait_for('reaction_add', timeout=60.0, check=check)
        await message.clear_reactions()

        if str(reaction.emoji) == '❌':
            await ctx.send("Search cancelled.")
        elif str(reaction.emoji) == '🔀':
            await shuffle(ctx)  # Assumes you have a shuffle function that plays songs
        elif str(reaction.emoji) == '⬅️':
            await previous_song(ctx)  # Assumes you have a previous song function
        elif str(reaction.emoji) == '➡️':
            await next_song(ctx)  # Assumes you have a next song function
        else:
            # Handle song selection based on reaction
            song_index = selection_emojis.index(str(reaction.emoji))
            if 0 <= song_index < len(search_results):
                title, url = search_results[song_index]
                player = await YTDLSource.from_url(url, loop=bot.loop)
                voice_channel.play(player, after=lambda e: print(f'Player error: {e}') if e else None)
                await ctx.send(f'**Now playing:** {title}')

    except asyncio.TimeoutError:
        await message.clear_reactions()
        await ctx.send("No response in time.")




def choose_song(search_results):
    for index, (title, _) in enumerate(search_results, start=1):
        print(f"{index}. {title}")

    while True:
        choice = input("Enter the number of the song you want to play: ")
        if choice.isdigit() and 1 <= int(choice) <= len(search_results):
            return search_results[int(choice) - 1]
        else:
            print("Invalid choice. Please enter a number between 1 and 10.")


async def play_next_song(ctx):
    global current_song_index

    if song_queue:
        # Select a random song
        current_song_index = random.randint(0, len(song_queue) - 1)
        song_path = song_queue[current_song_index]
        await play_local(ctx, song_path)
    else:
        await ctx.send("The song queue is empty.")


@bot.command(name='next', help='Plays the next song in the queue')
async def next_song(ctx):
    global current_song_index
    current_song_index += 1
    if current_song_index < len(song_queue):
        await play_song(ctx, song_queue[current_song_index])
    else:
        await ctx.send("Reached the end of the queue.")

@bot.command(name='previous', help='Plays the previous song in the queue')
async def previous_song(ctx):
    global current_song_index
    if current_song_index > 0:
        current_song_index -= 1
        await play_song(ctx, song_queue[current_song_index])
    else:
        await ctx.send("This is the first song in the queue.")

async def play_song(ctx, song_path):  # song_path is a string, not a dictionary
    voice_client = ctx.guild.voice_client
    if not voice_client:
        await ctx.send("The bot is not in a voice channel.")
        return

    voice_client.play(discord.FFmpegPCMAudio(song_path), after=lambda e: asyncio.run_coroutine_threadsafe(play_next_song(ctx), bot.loop))
    await ctx.send(f"Now playing: {os.path.basename(song_path)}")
    await ctx.send(f"Now playing: {ctx['title']}")


#Reload
@bot.command(name='reload', help='Reloads a module.')
@commands.is_owner()  # Only allow the owner of the bot to use this command
async def reload(ctx, extension=None):
    if extension:
        try:
            bot.reload_extension(f'cogs.{extension}')
            await ctx.send(f'Reloaded `{extension}` cog.')
        except Exception as e:
            await ctx.send(f'Error reloading `{extension}`: {e}')
    else:
        # Default action if no extension is specified
        await ctx.send('No extension specified.')


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


@bot.command(name='love', help='Schedules a love message. Type the command and follow the prompt.')
async def love(ctx):
    await ctx.send("Please enter the hour (0-23) to schedule the love message:")

    def check_hour(msg):
        return msg.author == ctx.author and msg.channel == ctx.channel and msg.content.isdigit() and 0 <= int(msg.content) <= 23

    try:
        hour_msg = await bot.wait_for('message', check=check_hour, timeout=30.0)
        hour = int(hour_msg.content)

        await ctx.send("Please enter the minutes (0-59):")

        def check_minutes(msg):
            return msg.author == ctx.author and msg.channel == ctx.channel and msg.content.isdigit() and 0 <= int(msg.content) <= 59

        minutes_msg = await bot.wait_for('message', check=check_minutes, timeout=30.0)
        minutes = int(minutes_msg.content)

        sender_id = ctx.author.id
        recipient_id = USER_ID if str(sender_id) == USER_MAX_ID else USER_MAX_ID

        # Schedule the love message
        scheduler.add_job(send_love_message, CronTrigger(hour=hour, minute=minutes), args=[recipient_id], id=f"love_message_{ctx.author.id}_{recipient_id}_{hour:02d}:{minutes:02d}")

        await ctx.send(f"Love message scheduled for {hour:02d}:{minutes:02d} to <@{recipient_id}>.")
    except asyncio.TimeoutError:
        await ctx.send("You didn't respond in time, please try the command again.")
    except Exception as e:
        await ctx.send(f"An error occurred: {e}")

bot.run(TOKEN)



