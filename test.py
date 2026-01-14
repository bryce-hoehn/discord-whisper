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

model, tokenizer = load("lmstudio-community/Qwen3-8B-MLX-4bit")

filepath = "./recordings/recording.txt"

@bot.command()
async def test(ctx):
    await ctx.send("Starting test processing...")

    with open(filepath, 'r') as transcript:
      prompt = '''
        Summarize the meeting transcript in markdown format with these sections:
        - Project Updates
        - Discussion Points  
        - Action Items
        - Next Sprint Assignments
        
        Be concise and focus on key points only.
        
        Transcript:
        ''' + transcript.read()
      
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

      # Remove <think> tags and content
      if '<think>' in response and '</think>' in response:
          # Extract only what's after </think>
          response = response.split('</think>', 1)[1].strip()
          
      await ctx.send(response, files=[discord.File(filepath)])

if __name__ == "__main__":
  os.makedirs("recordings", exist_ok=True)
  bot.run(os.getenv("DISCORD_TOKEN"))