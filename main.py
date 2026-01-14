import discord
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

class RecordingSink(voice_recv.FFmpegSink):
    def __init__(self, guild_id, bot_id):
        self.guild_id = guild_id
        self.bot_id = bot_id
        self.is_recording = False
        
    def wants_opus(self):
        return True
        
    def write(self, user, data):
        """Called when audio data is received"""
        if not self.is_recording:
            return
            
        if user and user.id == self.bot_id:
            return
            
        # Pass data to parent FFmpegSink
        super().write(user, data)
        
    def start_recording(self):
        self.is_recording = True
        
        self.filepath = None
        
        # Call parent constructor with output format
        timestamp = int(time.time())
        filename = f"recording_{self.guild_id}_{timestamp}.ogg"
        filepath = os.path.join("recordings", filename)
        
        os.makedirs("recordings", exist_ok=True)
        
        # FFmpegSink will handle the conversion to Ogg Opus
        # Input is raw opus, output as ogg container
        super().__init__(filename=filepath, before_options='-f opus -ar 48000 -ac 2')
        
        self.filepath = filepath

        print(f"Started recording to {self.filepath}")
        
    def stop_recording(self):
        self.is_recording = False
        # FFmpegSink will close the file automatically when done
        
    def get_filepath(self):
        return self.filepath
        
    def save(self):
        """Return the file path"""
        return self.filepath

recordings = {}

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name} ({bot.user.id})')

@bot.command()
async def record(ctx):
    """Start recording audio from voice channel"""
    try:
        if not ctx.author.voice:
            await ctx.send("You need to be in a voice channel first!")
            return
            
        if ctx.guild.id in recordings:
            await ctx.send("Already recording in this server!")
            return
            
        vc = await ctx.author.voice.channel.connect(cls=voice_recv.VoiceRecvClient)
        
        sink = RecordingSink(ctx.guild.id, bot.user.id)
        sink.start_recording()
        
        vc.listen(sink)
        
        recordings[ctx.guild.id] = {
            'voice_client': vc,
            'sink': sink,
            'start_time': time.time()
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
            
        recording_info = recordings[ctx.guild.id]
        vc = recording_info['voice_client']
        sink = recording_info['sink']
        
        sink.stop_recording()
        
        audio_path = sink.get_filepath()
        
        await vc.disconnect()
        
        # Calculate duration
        duration = time.time() - recording_info['start_time']
        minutes = int(duration // 60)
        seconds = int(duration % 60)
        
        # Clean up
        del recordings[ctx.guild.id]
        
        if audio_path and os.path.exists(audio_path):
            file_size = os.path.getsize(audio_path) / (1024 * 1024)  # MB
            await ctx.send(f"🛑 Recording stopped! Duration: {minutes}m {seconds}s, Size: {file_size:.2f} MB")
            await ctx.send(f"Processing file...")

            transcription = mlx_whisper.transcribe(audio_path, path_or_hf_repo="mlx-community/whisper-medium.en-mlx-4bit", word_timestamps=True)
            
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
            
            # Save summary
            summary_filepath = audio_path.replace('.ogg', '.md')
            with open(summary_filepath, "w") as f:
                f.write(response)
            
            # Send files to Discord
            await ctx.send(files=[
                discord.File(summary_filepath),
                discord.File(text_filepath)
                # commented out to avoid hitting file size limit
                # discord.File(audio_path)
            ])
            
        else:
            await ctx.send("Recording stopped, but no audio was captured.")
            
    except Exception as e:
        await ctx.send(f"Error: {str(e)}")

if __name__ == "__main__":
    os.makedirs("recordings", exist_ok=True)
    bot.run(os.getenv("DISCORD_TOKEN"))