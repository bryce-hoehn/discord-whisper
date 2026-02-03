import discord
import os
from dotenv import load_dotenv
from transcription import transcribe_audio
from summarization import generate_summary, split_summary_by_headings

load_dotenv()

bot = discord.Bot(intents=discord.Intents.all())

opus_path = "/opt/homebrew/opt/opus/lib/libopus.0.dylib"
discord.opus.load_opus(opus_path)

# Global state
connections = {}

async def once_done(sink: discord.sinks, channel: discord.TextChannel, *args):
    """
    Callback when recording is complete. Saves each speaker's audio file
    to the recordings folder, then transcribes them separately.
    """
    await sink.vc.disconnect()
    
    # Create recordings directory if it doesn't exist
    recordings_dir = "recordings"
    os.makedirs(recordings_dir, exist_ok=True)
    
    all_transcripts = []

    for user_id, audio in sink.audio_data.items():
        user = sink.vc.guild.get_member(user_id)
        user_name = user.display_name if user else f"User {user_id}"
        timestamp = int(discord.utils.utcnow().timestamp())
        filename = f"{user_name}_{user_id}_{timestamp}.ogg"
        filepath = os.path.join(recordings_dir, filename)
        
        with open(filepath, "wb") as f:
            f.write(audio.file.read())
        
        # Pass filepath to transcribe_audio
        transcript_lines = transcribe_audio(filepath, user_name)
        all_transcripts.extend(transcript_lines)
    
    all_transcripts.sort()

    transcript = "\n".join(all_transcripts)

    summary = generate_summary("**Transcript:**\n" + transcript)
    
    # Split summary by headings and send each as separate message
    summary_messages = split_summary_by_headings(summary)
    for msg in summary_messages:
        await channel.send(msg)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name} ({bot.user.id})")

@bot.command()
async def record(ctx):
    voice = ctx.author.voice

    if not voice:
        await ctx.respond("You aren't in a voice channel!")

    vc = await voice.channel.connect()  # Connect to the voice channel the author is in.
    connections.update({ctx.guild.id: vc})  # Updating the cache with the guild and channel.

    vc.start_recording(
        discord.sinks.OGGSink(),  # The sink type to use.
        once_done,  # What to do once done.
        ctx.channel  # The channel to disconnect from.
    )
    await ctx.respond("Started recording!")

@bot.command()
async def stop(ctx):
    if ctx.guild.id in connections:  # Check if the guild is in the cache.
        vc = connections[ctx.guild.id]
        vc.stop_recording()  # Stop recording, and call the callback (once_done).
        del connections[ctx.guild.id]  # Remove the guild from the cache.
        await ctx.delete()  # And delete.
    else:
        await ctx.respond("I am currently not recording here.")  # Respond with this if we aren't recording.


if __name__ == "__main__":
    bot.run(os.getenv("DISCORD_TOKEN"))