import discord
import wave
import time
import os
import logging
import mlx_whisper
from mlx_lm import load, generate
from discord.ext import commands, voice_recv
from dotenv import load_dotenv

load_dotenv()

logging.getLogger('discord.ext.voice_recv').setLevel(logging.WARNING)
logging.getLogger('discord.voice_client').setLevel(logging.WARNING)

# Ensure opus is loaded
discord.opus._load_default()

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(command_prefix='!', intents=intents)

model, tokenizer = load("lmstudio-community/Qwen3-4B-Instruct-2507-MLX-4bit")

class RecordingSink(voice_recv.AudioSink):
    def __init__(self, guild_id, bot_id):
        self.guild_id = guild_id
        self.bot_id = bot_id
        self.audio_data = []
        self.is_recording = False
        
    def wants_opus(self):
        return False
        
    def write(self, user, data):
        """Called when audio data is received"""
        if not self.is_recording:
            return
            
        # Skip bot's own audio to avoid feedback
        if user and user.id == self.bot_id:
            return
            
        if hasattr(data, 'pcm') and data.pcm:
            self.audio_data.append(data.pcm)
        
    def cleanup(self):
        pass
        
    def start_recording(self):
        self.audio_data = []
        self.is_recording = True
        print(f"Started recording for guild {self.guild_id}")
        
    def stop_recording(self):
        self.is_recording = False
        
    def save(self):
        if not self.audio_data:
            return None
            
        # Create filename
        timestamp = int(time.time())
        filename = f"recording_{self.guild_id}_{timestamp}.wav"
        filepath = os.path.join("recordings", filename)
        
        # Ensure directory exists
        os.makedirs("recordings", exist_ok=True)
        
        # Save as WAV file
        with wave.open(filepath, 'wb') as wav_file:
            wav_file.setnchannels(2)
            wav_file.setsampwidth(2)
            wav_file.setframerate(48000)
            wav_file.writeframes(b''.join(self.audio_data))
            
        return filepath

recordings = {}

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name} ({bot.user.id})')

@bot.command()
async def record(ctx):
    """Start recording audio from voice channel"""
    try:
        # Check if user is in voice channel
        if not ctx.author.voice:
            await ctx.send("You need to be in a voice channel first!")
            return
            
        # Check if already recording
        if ctx.guild.id in recordings:
            await ctx.send("Already recording in this server!")
            return
            
        # Join voice channel
        vc = await ctx.author.voice.channel.connect(cls=voice_recv.VoiceRecvClient)
        
        # Create and start recording sink
        sink = RecordingSink(ctx.guild.id, bot.user.id)
        sink.start_recording()
        
        # Start listening
        vc.listen(sink)
        
        # Store recording info
        recordings[ctx.guild.id] = {
            'voice_client': vc,
            'sink': sink,
            'start_time': time.time()
        }
        
        await ctx.send(f"🎤 Started recording in {ctx.author.voice.channel.name}!")
        
    except Exception as e:
        await ctx.send(f"Error: {str(e)}")

@bot.command()
async def stop(ctx):
    """Stop recording and save"""
    try:
        # Check if recording
        if ctx.guild.id not in recordings:
            await ctx.send("Not recording in this server!")
            return
            
        # Get recording info
        recording_info = recordings[ctx.guild.id]
        vc = recording_info['voice_client']
        sink = recording_info['sink']
        
        # Stop recording
        sink.stop_recording()
        
        # Save the recording
        filepath = sink.save()
        
        # Disconnect
        await vc.disconnect()
        
        # Calculate duration
        duration = time.time() - recording_info['start_time']
        minutes = int(duration // 60)
        seconds = int(duration % 60)
        
        # Clean up
        del recordings[ctx.guild.id]
        
        if filepath:
            await ctx.send(f"🛑 Recording stopped! Duration: {minutes}m {seconds}s")
            await ctx.send(f"Processing the recording...")

            transcription = mlx_whisper.transcribe(filepath, path_or_hf_repo="mlx-community/whisper-medium.en-mlx-4bit")
            text_filepath = filepath.replace('.wav', '.txt')

            with open(text_filepath, "w") as f:
                f.write(transcription['text'])
            
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

            prompt = tokenizer.apply_chat_template(
                messages, add_generation_prompt=True
            )

            response = generate(
                model, 
                tokenizer, 
                prompt=prompt, 
                verbose=True,
                max_tokens=8192,
            )

            if '<think>' in response and '</think>' in response:
                response = response.split('</think>', 1)[1].strip()
                
            await ctx.send(response, files=[discord.File(text_filepath)])

        else:
            await ctx.send("Recording stopped, but no audio was captured.")
            
    except Exception as e:
        await ctx.send(f"Error: {str(e)}")

if __name__ == "__main__":
  os.makedirs("recordings", exist_ok=True)
  bot.run(os.getenv("DISCORD_TOKEN"))
