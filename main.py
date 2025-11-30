import discord
from discord import app_commands
from discord.ext import commands
import wavelink
import os

# --- CONFIGURATION ---
TOKEN = os.getenv("DISCORD_TOKEN")

# Setup Bot
class MusicBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix='!', intents=intents)

    async def setup_hook(self):
        # This connects to the Lavalink Node when the bot starts
        nodes = [
            wavelink.Node(
                uri="https://lava-v4.ajieblogs.eu.org:443", # Free Public Node
                password="https://ajieblogs.eu.org",
            )
        ]
        await wavelink.Pool.connect(nodes=nodes, client=self, cache_capacity=100)
        await self.tree.sync()
        print("Connected to Lavalink Node!")

bot = MusicBot()

# --- EVENTS ---
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}!')

@bot.event
async def on_wavelink_node_ready(payload: wavelink.NodeReadyEventPayload):
    print(f"Node {payload.node.identifier} is ready!")

# --- COMMANDS ---

@bot.tree.command(name="play", description="Play music from YouTube/Spotify")
@app_commands.describe(search="URL or Song Name")
async def play(interaction: discord.Interaction, search: str):
    if not interaction.user.voice:
        await interaction.response.send_message("You need to be in a voice channel!", ephemeral=True)
        return

    await interaction.response.defer()
    
    # 1. Connect to Voice Channel
    if not interaction.guild.voice_client:
        vc: wavelink.Player = await interaction.user.voice.channel.connect(cls=wavelink.Player)
    else:
        vc: wavelink.Player = interaction.guild.voice_client

    # 2. Search for the song
    # This automatically handles YouTube, Spotify, and Soundcloud links
    tracks = await wavelink.Playable.search(search)
    
    if not tracks:
        await interaction.followup.send("No song found.")
        return

    track = tracks[0] # Get the first result

    # 3. Play
    if vc.playing:
        await vc.queue.put_wait(track)
        await interaction.followup.send(f"Added to queue: **{track.title}**")
    else:
        await vc.play(track)
        await interaction.followup.send(f"🎵 Now Playing: **{track.title}**")

@bot.tree.command(name="stop", description="Stop music and leave")
async def stop(interaction: discord.Interaction):
    vc: wavelink.Player = interaction.guild.voice_client
    if vc:
        await vc.disconnect()
        await interaction.response.send_message("Disconnected.")
    else:
        await interaction.response.send_message("I'm not playing anything.", ephemeral=True)

# Run Bot
bot.run(TOKEN)
