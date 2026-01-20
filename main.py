import discord
import os
from discord.ext import commands
from dotenv import load_dotenv

from transcription import transcribe_with_timestamps, combine_transcripts
from summarization import generate_summary

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Global state
connections = {}

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name} ({bot.user.id})")

@bot.command()
async def record(ctx):
    """Start recording audio from voice channel"""
    try:
        voice = ctx.author.voice
        if not voice:
            await ctx.send("You need to be in a voice channel first!")
            return

        if ctx.guild.id in connections:
            await ctx.send("Already recording in this server!")
            return

        # Connect to voice channel
        vc = await voice.channel.connect()
        
        connections.update({ctx.guild.id: vc}) 

        # Start recording with callback
        vc.start_recording(
            discord.sinks.OGGSink(),
            once_done,
            ctx.channel
        )

        await ctx.respond("Started recording!")

    except Exception as e:
        await ctx.send(f"Error: {str(e)}")


async def once_done(sink: discord.sinks, channel: discord.TextChannel, *args):
    recorded_users = [  # A list of recorded users
        f"<@{user_id}>"
        for user_id, audio in sink.audio_data.items()
    ]
    await sink.vc.disconnect()  # Disconnect from the voice channel.
    files = [discord.File(audio.file, f"{user_id}.{sink.encoding}") for user_id, audio in sink.audio_data.items()]  # List down the files.
    await channel.send(f"finished recording audio for: {', '.join(recorded_users)}.", files=files)

@bot.command()
async def stop_recording(ctx):
    if ctx.guild.id in connections:  # Check if the guild is in the cache.
        vc = connections[ctx.guild.id]
        vc.stop_recording()  # Stop recording, and call the callback (once_done).
        del connections[ctx.guild.id]  # Remove the guild from the cache.
        await ctx.delete()  # And delete.
    else:
        await ctx.respond("I am currently not recording here.")  # Respond with this if we aren't recording.

if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    bot.run(token)
