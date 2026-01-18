import discord
import time
import os
import logging
import mlx_whisper
import threading
import asyncio
from mlx_lm import load, generate
from discord.ext import commands, voice_recv
from dotenv import load_dotenv

load_dotenv()

logging.getLogger('discord.ext.voice_recv').setLevel(logging.WARNING)
logging.getLogger('discord.voice_client').setLevel(logging.WARNING)

discord.opus._load_default()

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(command_prefix='!', intents=intents)

model, tokenizer = load("lmstudio-community/Qwen3-4B-Instruct-2507-MLX-4bit")

recordings = {}

def transcribe(ctx, audio_path):
    transcription = mlx_whisper.transcribe(audio_path, path_or_hf_repo="mlx-community/whisper-tiny.en-mlx-q4")
            
    # Save transcript
    text_filepath = audio_path.replace('.ogg', '.txt')
    with open(text_filepath, "w") as f:
        f.write(transcription['text'])
    
    # Generate summary
    prompt = '''
        Summarize the meeting transcript in Discord markdown format with these sections:
        - Project Updates
        - Discussion Points
        - Action Items
        - Next Sprint Assignments
        
        Be concise and focus on key points only.
        
        Transcript:
        ''' + transcription['text']
    
    messages = [{"role": "user", "content": prompt}]
    prompt = tokenizer.apply_chat_template(messages, add_generation_prompt=True)
    
    response = generate(
        model,
        tokenizer,
        prompt=prompt,
        verbose=True,
        max_tokens=8192,
    )
    
    if '<think>' in response and '</think>' in response:
        response = response.split('</think>', 1)[1].strip()
    
    # Remove markdown code block formatting if present
    response = response.strip()

    if response.startswith('```'):
        lines = response.split('\n')
        lines = lines[1:]
        if lines and lines[-1].strip() == '```':
            lines = lines[:-1]
        
        if lines:
            min_leading = float('inf')
            for line in lines:
                if line.strip():
                    leading = len(line) - len(line.lstrip())
                    if leading < min_leading:
                        min_leading = leading
            
            if min_leading != float('inf') and min_leading > 0:
                lines = [line[min_leading:] if len(line) >= min_leading else line for line in lines]
        
        response = '\n'.join(lines).strip()
    
    summary_filepath = audio_path.replace('.ogg', '.md')

    with open(summary_filepath, "w") as f:
        f.write(response)
    
    return response

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
        
        audio_path = f"recordings/{timestamp}.ogg"

        sink = voice_recv.FFmpegSink(
            filename=audio_path,
            options="-acodec libopus -b:a 96k -vbr on"
        )
        
        vc.start_listening(sink)
        
        recordings[ctx.guild.id] = {
            'voice_client': vc,
            'sink': sink,
            'start_time': time.time(),
            'audio_path': audio_path
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
        audio_path = recording_info['audio_path']
        
        # Stop listening and disconnect
        if vc:
            vc.stop_listening()
            await vc.disconnect()
        
        # Calculate duration
        duration = time.time() - start_time
        minutes = int(duration // 60)
        seconds = int(duration % 60)
        
        # Clean up
        del recordings[ctx.guild.id]
        
        if audio_path and os.path.exists(audio_path):
            file_size = os.path.getsize(audio_path) / (1024 * 1024)  # MB
            await ctx.send(f"🛑 Recording stopped! Duration: {minutes}m {seconds}s, Size: {file_size:.2f} MB")
            await ctx.send(f"Processing file...")

            transcription = threading.Thread(target=transcribe, args=(ctx, audio_path))
            transcription.start()

            response = transcription.join()

            response = response.split('\n')
            
            for r in response:
                await ctx.send(r)

        else:
            await ctx.send("Recording stopped, but no audio was captured.")
            
    except Exception as e:
        await ctx.send(f"Error: {str(e)}")

if __name__ == "__main__":
    os.makedirs("recordings", exist_ok=True)
    bot.run(os.getenv("DISCORD_TOKEN"))