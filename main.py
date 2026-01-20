import discord
from enum import Enum
import os
import asyncio
from dotenv import load_dotenv

from transcription import transcribe_with_timestamps, combine_transcripts
from summarization import generate_summary

load_dotenv()

try:
    asyncio.get_running_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

bot = discord.Bot(intents=discord.Intents.all())

# Global state
connections = {}

async def finished_callback(sink, channel: discord.TextChannel, *args):
    recorded_users = [f"<@{user_id}>" for user_id, audio in sink.audio_data.items()]
    await sink.vc.disconnect()
    files = [
        discord.File(audio.file, f"{user_id}.{sink.encoding}")
        for user_id, audio in sink.audio_data.items()
    ]
    await channel.send(
        f"Finished! Recorded audio for {', '.join(recorded_users)}.", files=files
    )

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name} ({bot.user.id})")

@bot.slash_command(name="record")
async def record(ctx: discord.ApplicationContext):
    """Record your voice!"""
    voice = ctx.author.voice

    if not voice:
        return await ctx.respond("You're not in a vc right now")

    vc = await voice.channel.connect()
    connections.update({ctx.guild.id: vc})

    vc.play("obama.mp3")
            
    vc.start_recording(
        discord.sinks.OGGSink,
        finished_callback,
        ctx.channel,
    )

    await ctx.respond("The recording has started!")

@bot.slash_command(name="stop")
async def stop(ctx: discord.ApplicationContext):
    """Stop recording."""
    if ctx.guild.id in connections:
        vc = connections[ctx.guild.id]
        vc.stop_recording()
        del connections[ctx.guild.id]
        await ctx.delete()
    else:
        await ctx.respond("Not recording in this guild.")

if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    bot.run(token)
