import os
import mlx_whisper
from datetime import timedelta

def format_timestamp(seconds):
    """Convert seconds to [MM:SS] format"""
    td = timedelta(seconds=seconds)
    minutes = int(td.seconds // 60)
    seconds = int(td.seconds % 60)
    return f"[{minutes:02d}:{seconds:02d}]"


def transcribe_audio(audio_file, user_name=None):
    result = mlx_whisper.transcribe(audio_file, path_or_hf_repo="mlx-community/whisper-base.en-mlx-q4")

    transcript_lines = []

    if result:
        for segment in result["segments"]:
            start_time = segment["start"]
            text = segment["text"].strip()

            if text:
                timestamp = format_timestamp(start_time)
                if user_name:
                    transcript_lines.append(f"{timestamp} {user_name}: {text}")
                else:
                    transcript_lines.append(f"{timestamp}: {text}")

    return transcript_lines
