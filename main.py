import discord
import time
import os
import logging
import asyncio
from discord.ext import commands
from dotenv import load_dotenv

# Import from our modules
from audio_sink import PerUserAudioSink
from transcription import transcribe_with_timestamps, combine_transcripts
from summarization import generate_summary

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Suppress verbose discord logs
logging.getLogger("discord").setLevel(logging.WARNING)

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

        # Create recordings directory if it doesn't exist
        os.makedirs("recordings", exist_ok=True)

        timestamp = int(time.time())
        base_path = f"recordings/recording_{ctx.guild.id}_{timestamp}"

        # Create our custom sink
        sink = PerUserAudioSink()

        # Store connection info
        connections[ctx.guild.id] = {
            "voice_client": vc,
            "sink": sink,
            "start_time": time.time(),
            "base_path": base_path,
            "channel": ctx.channel,
        }

        # Start recording with callback
        vc.start_recording(sink, finished_callback, ctx.channel, ctx.guild.id)

        await ctx.send(f"🎤 Started recording in {voice.channel.name}")

    except Exception as e:
        logger.error(f"Error starting recording: {e}", exc_info=True)
        await ctx.send(f"Error: {str(e)}")


async def finished_callback(
    sink: PerUserAudioSink, channel: discord.TextChannel, *args
):
    """Called when recording is finished"""
    try:
        # Extract guild_id from args
        guild_id = args[0] if args else None

        if guild_id is None or guild_id not in connections:
            await channel.send("Error: Recording data not found!")
            return

        recording_info = connections[guild_id]
        start_time = recording_info["start_time"]
        base_path = recording_info["base_path"]

        # Calculate duration
        duration = time.time() - start_time
        minutes = int(duration // 60)
        seconds = int(duration % 60)

        # Disconnect from voice
        await sink.vc.disconnect()

        # Get audio data
        audio_data = sink.get_all_audio()
        user_info = sink.get_user_info()

        # Clean up connection
        del connections[guild_id]

        if not audio_data:
            await channel.send("Recording stopped, but no audio was captured.")
            return

        await channel.send(f"🛑 Recording stopped! Duration: {minutes}m {seconds}s")
        await channel.send(f"Processing {len(audio_data)} user recordings...")

        # Save each user's audio to a file
        user_files = []
        for user_id, audio in audio_data.items():
            user_file = f"{base_path}_user_{user_id}.wav"

            # Write audio data to file
            with open(user_file, "wb") as f:
                audio.file.seek(0)
                f.write(audio.file.read())

            user_files.append(user_file)

        # Transcribe each user file separately
        user_transcripts = {}
        all_full_texts = []

        for user_file in user_files:
            try:
                # Extract user_id from filename
                user_id = int(user_file.split("_user_")[1].replace(".wav", ""))
                user = user_info.get(user_id)
                user_name = user.name if user else f"User_{user_id}"

                # Transcribe with timestamps
                transcript_lines, full_text = transcribe_with_timestamps(
                    user_file, user_name
                )

                # Save individual user transcript
                user_transcript_path = user_file.replace(".wav", ".txt")
                with open(user_transcript_path, "w") as f:
                    f.write("\n".join(transcript_lines))

                user_transcripts[user_id] = (transcript_lines, full_text, user_name)
                all_full_texts.append(full_text)

            except Exception as e:
                logger.error(f"Error transcribing {user_file}: {e}", exc_info=True)
                continue

        if not user_transcripts:
            await channel.send("Failed to transcribe audio.")
            return

        # Combine all transcripts chronologically
        combined_lines = combine_transcripts(user_transcripts)
        combined_text = " ".join(all_full_texts)

        # Save combined transcript
        combined_transcript_path = f"{base_path}_combined.txt"
        with open(combined_transcript_path, "w") as f:
            f.write("\n".join(combined_lines))

        # Generate summary from combined text
        await channel.send("Generating summary...")
        summary = generate_summary(combined_text)

        # Save summary
        summary_path = f"{base_path}_summary.md"
        with open(summary_path, "w") as f:
            f.write(summary)

        # Send summary in chunks (split by empty lines/paragraphs)
        paragraphs = summary.split("\n\n")
        for paragraph in paragraphs:
            if paragraph.strip():
                await channel.send(paragraph.strip())

        # Send completion message
        await channel.send(
            f"✅ Processing complete! Transcripts saved to:\n"
            f"- Individual: `{base_path}_user_*.txt`\n"
            f"- Combined: `{combined_transcript_path}`\n"
            f"- Summary: `{summary_path}`"
        )

    except Exception as e:
        logger.error(f"Error in finished_callback: {e}", exc_info=True)
        await channel.send(f"Error processing recording: {str(e)}")


@bot.command()
async def stop(ctx):
    """Stop recording and process audio"""
    try:
        if ctx.guild.id not in connections:
            await ctx.send("Not recording in this server!")
            return

        # Get voice client and stop recording
        recording_info = connections[ctx.guild.id]
        vc = recording_info["voice_client"]

        # Stop recording - this will trigger the callback
        vc.stop_recording()

        await ctx.send("⏹️ Stopping recording and processing audio...")

    except Exception as e:
        logger.error(f"Error stopping recording: {e}", exc_info=True)
        await ctx.send(f"Error: {str(e)}")


if __name__ == "__main__":
    os.makedirs("recordings", exist_ok=True)
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        print("Error: DISCORD_TOKEN not found in environment variables!")
        exit(1)
    bot.run(token)
