import discord
import os
import asyncio
from discord.ext import commands
from dotenv import load_dotenv

from transcription import transcribe_with_timestamps, combine_transcripts
from summarization import generate_summary

load_dotenv()

# Create an event loop for Python 3.14 compatibility
try:
    asyncio.get_running_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

bot = discord.Bot()

# Global state
connections = {}

async def once_done(sink: discord.sinks, channel: discord.TextChannel, *args):
    recorded_users = [  # A list of recorded users
        f"<@{user_id}>" for user_id, audio in sink.audio_data.items()
    ]
    await sink.vc.disconnect()  # Disconnect from the voice channel.
    files = [
        discord.File(audio.file, f"{user_id}.{sink.encoding}")
        for user_id, audio in sink.audio_data.items()
    ]  # List down the files.
    await channel.send(
        f"finished recording audio for: {', '.join(recorded_users)}.", files=files
    )

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name} ({bot.user.id})")

@bot.slash_command(name="record", description="Start Recording")
async def record(ctx):
    """Start recording audio from voice channel"""
    try:
        voice = ctx.author.voice
        if not voice:
            await ctx.respond("You need to be in a voice channel first!")
            return

        if ctx.guild.id in connections:
            await ctx.respond("Already recording in this server!")
            return

        # Connect to voice channel
        vc = await voice.channel.connect()

        connections.update({ctx.guild.id: vc})

        # Start recording with callback
        vc.start_recording(discord.sinks.OGGSink(), once_done, ctx.channel)

        await ctx.respond("Started recording!")

    except Exception as e:
        await ctx.respond(f"Error: {str(e)}")


@bot.slash_command(name="stop", description="Stop Recording")
async def stop_recording(ctx):
    if ctx.guild.id in connections:
        vc = connections[ctx.guild.id]
        vc.stop_recording()
        del connections[ctx.guild.id]
        await ctx.delete()
    else:
        await ctx.respond("I am currently not recording here.")

if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    bot.run(token)
