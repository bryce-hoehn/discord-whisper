# Discord Whisper Bot

A Discord bot that records voice channel audio and transcribes it using Whisper.

## Features

- Record audio from Discord voice channels
- Separate audio files per speaker
- Transcribe speech using Whisper (base.en model)
- Generate summaries of transcriptions

## Setup

1. Create a `.env` file with your Discord bot token:
   ```
   DISCORD_TOKEN=YOUR_TOKEN_HERE
   ```

2. Build and run with Docker:
   `docker-compose up --build`

## Usage

1. Join a voice channel
2. Type `/record` in a text channel
3. Speak in the voice channel
4. Type `/stop` to stop recording
5. The bot will post the transcription and summary

## Requirements

- Docker
- [Discord bot token](https://guide.pycord.dev/getting-started/creating-your-first-bot)
- Whisper model (auto-downloaded on first run)

## Project Structure

- `main.py` - Bot entry point and Discord commands
- `transcription.py` - Audio transcription using Whisper
- `summarization.py` - Text summarization using Qwen3 model defined in docker-compose.yml
- `recordings/` - Saved audio files (created automatically)
