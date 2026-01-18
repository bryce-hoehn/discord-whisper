import discord
import time
import os
import logging
import asyncio
from discord.ext import commands, voice_recv
from dotenv import load_dotenv

# Import from our modules
from audio_sink import PerUserRecordingSink
from transcription import transcribe_with_timestamps, combine_transcripts
from summarization import generate_summary
from audio_processing import combine_audio_files

load_dotenv()

logging.getLogger('discord.ext.voice_recv').setLevel(logging.WARNING)
logging.getLogger('discord.voice_client').setLevel(logging.WARNING)

discord.opus._load_default()

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(command_prefix='!', intents=intents)

# Global state
recordings = {}

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name} ({bot.user.id})')

@bot.command()
async def record(ctx):
    """Start recording audio from voice channel"""
    timestamp = int(time.time())
    try:
        if not ctx.author.voice:
            await ctx.send("You need to be in a voice channel first!")
            return
            
        if ctx.guild.id in recordings:
            await ctx.send("Already recording in this server!")
            return
            
        vc = await ctx.author.voice.channel.connect(cls=voice_recv.VoiceRecvClient)
        
        # Create recordings directory if it doesn't exist
        os.makedirs("recordings", exist_ok=True)
        
        base_path = f"recordings/{timestamp}"
        
        # Create per-user recording sink
        sink = PerUserRecordingSink(base_path)
        
        vc.listen(sink)
        
        recordings[ctx.guild.id] = {
            'voice_client': vc,
            'sink': sink,
            'start_time': time.time(),
            'base_path': base_path,
            'guild': ctx.guild
        }
        
        await ctx.send(f"🎤 Started recording in {ctx.author.voice.channel.name}")
        
    except Exception as e:
        await ctx.send(f"Error: {str(e)}")

@bot.command()
async def stop(ctx):
    """Stop recording, transcribe and summarize"""
    try:
        if ctx.guild.id not in recordings:
            await ctx.send("Not recording in this server!")
            return
            
        # Get recording info
        recording_info = recordings[ctx.guild.id]
        vc = recording_info['voice_client']
        start_time = recording_info['start_time']
        sink = recording_info['sink']
        base_path = recording_info['base_path']
        guild = recording_info['guild']
        
        # Stop listening and disconnect
        if vc:
            vc.stop_listening()
            await vc.disconnect()
        
        # Calculate duration
        duration = time.time() - start_time
        minutes = int(duration // 60)
        seconds = int(duration % 60)
        
        # Clean up sink and get user files
        sink.cleanup()
        user_files = sink.get_user_files()
        user_info = sink.get_user_info()
        
        # Clean up
        del recordings[ctx.guild.id]
        
        if user_files:
            await ctx.send(f"🛑 Recording stopped! Duration: {minutes}m {seconds}s")
            await ctx.send(f"Processing {len(user_files)} user recordings...")
            
            # Transcribe each user file separately
            user_transcripts = {}
            all_full_texts = []
            
            for user_file in user_files:
                # Extract user_id from filename
                try:
                    user_id = int(user_file.split('_user_')[1].replace('.ogg', ''))
                    user = user_info.get(user_id)
                    user_name = user.name if user else f"User_{user_id}"
                    
                    # Transcribe with timestamps
                    transcript_lines, full_text = transcribe_with_timestamps(user_file, user_name)
                    
                    # Save individual user transcript
                    user_transcript_path = user_file.replace('.ogg', '.txt')
                    with open(user_transcript_path, 'w') as f:
                        f.write('\n'.join(transcript_lines))
                    
                    user_transcripts[user_id] = (transcript_lines, full_text, user_name)
                    all_full_texts.append(full_text)
                    
                except Exception as e:
                    print(f"Error transcribing {user_file}: {e}")
                    continue
            
            # Combine all transcripts chronologically
            combined_lines = combine_transcripts(user_transcripts)
            combined_text = ' '.join(all_full_texts)
            
            # Save combined transcript
            combined_transcript_path = f"{base_path}_combined.txt"
            with open(combined_transcript_path, 'w') as f:
                f.write('\n'.join(combined_lines))
            
            # Generate summary from combined text
            await ctx.send("Generating summary...")
            summary = generate_summary(combined_text)
            
            # Save summary
            summary_path = f"{base_path}_summary.md"
            with open(summary_path, 'w') as f:
                f.write(summary)
            
            # Send summary in chunks
            summary_lines = summary.split('\n')
            for line in summary_lines:
                if line.strip():
                    await ctx.send(line)
            
            # Send completion message
            await ctx.send(f"✅ Processing complete! Transcripts saved to:\n- Individual: `{base_path}_user_*.txt`\n- Combined: `{combined_transcript_path}`\n- Summary: `{summary_path}`")
            
        else:
            await ctx.send("Recording stopped, but no audio was captured.")
            
    except Exception as e:
        await ctx.send(f"Error: {str(e)}")

if __name__ == "__main__":
    os.makedirs("recordings", exist_ok=True)
    bot.run(os.getenv("DISCORD_TOKEN"))