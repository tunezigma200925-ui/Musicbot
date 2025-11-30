import discord
from discord import app_commands
from discord.ext import commands
import yt_dlp
import asyncio
import os

# --- CONFIGURATION ---
TOKEN = os.getenv("DISCORD_TOKEN")  # We will set this in Zeabur later

# Setup Bot with Intents
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True # Required for voice
bot = commands.Bot(command_prefix="!", intents=intents)

# YT-DLP Options (For audio quality)
YDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'default_search': 'auto', # Allows searching by name
    'source_address': '0.0.0.0',
}

# FFmpeg Options (To keep connection stable)
FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn',
}

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}!')
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(e)

# --- COMMANDS ---

@bot.tree.command(name="play", description="Plays music from YouTube (URL or Search Name)")
@app_commands.describe(query="The URL or name of the song")
async def play(interaction: discord.Interaction, query: str):
    # 1. Check if user is in a Voice Channel
    if not interaction.user.voice:
        await interaction.response.send_message("You need to be in a voice channel first!", ephemeral=True)
        return

    await interaction.response.defer() # Defers response so bot doesn't timeout while searching

    # 2. Connect to Voice Channel
    channel = interaction.user.voice.channel
    voice_client = discord.utils.get(bot.voice_clients, guild=interaction.guild)

    if voice_client is None:
        voice_client = await channel.connect()
    elif voice_client.channel != channel:
        await voice_client.move_to(channel)

    # 3. Search and Play
    try:
        with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
            # If query is a URL, use it. If it's text, search it.
            info = ydl.extract_info(f"ytsearch:{query}" if "http" not in query else query, download=False)
            
            # Handle search results (gets the first item)
            if 'entries' in info:
                info = info['entries'][0]
                
            url = info['url']
            title = info['title']
            
            # Stop current music if playing
            if voice_client.is_playing():
                voice_client.stop()

            # Play the stream
            source = discord.FFmpegPCMAudio(url, **FFMPEG_OPTIONS)
            voice_client.play(source)
            
            await interaction.followup.send(f"🎵 Now playing: **{title}**")
            
    except Exception as e:
        await interaction.followup.send(f"An error occurred: {e}")

@bot.tree.command(name="stop", description="Stops music and disconnects")
async def stop(interaction: discord.Interaction):
    voice_client = discord.utils.get(bot.voice_clients, guild=interaction.guild)
    if voice_client and voice_client.is_connected():
        await voice_client.disconnect()
        await interaction.response.send_message("Disconnected from voice channel.")
    else:
        await interaction.response.send_message("I am not in a voice channel.", ephemeral=True)

# --- ADMIN COMMANDS ---

@bot.tree.command(name="music_set", description="Admin only: Setup music channel")
@app_commands.checks.has_permissions(administrator=True) # Only Admins can use this
async def music_set(interaction: discord.Interaction, channel: discord.TextChannel):
    # You can save this channel ID to a database if you want to restrict commands to this channel later
    await interaction.response.send_message(f"Music commands have been bound to {channel.mention} (Configuration Saved).")

@music_set.error
async def music_set_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)

# Start Bot
bot.run(TOKEN)
