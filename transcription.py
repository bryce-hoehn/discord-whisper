import os
from pywhispercpp.model import Model
from datetime import timedelta

def format_timestamp(seconds):
    """Convert seconds to [MM:SS] format"""
    td = timedelta(seconds=seconds)
    minutes = int(td.seconds // 60)
    seconds = int(td.seconds % 60)
    return f"[{minutes:02d}:{seconds:02d}]"


def transcribe_audio(audio_file, user_name=None):
    """
    Transcribe a single audio file using pywhispercpp.
    """
    model = Model('base.en')
    segments = model.transcribe(audio_file)

    # Extract segments with timestamps
    transcript_lines = []
    full_text = ""

    if segments:
        for segment in segments:
            start_time = segment.t0
            text = segment.text.strip()

            if text:
                timestamp = format_timestamp(start_time)
                if user_name:
                    transcript_lines.append(f"{timestamp} {user_name}: {text}")
                else:
                    transcript_lines.append(f"{timestamp}: {text}")
                full_text += " " + text

    return transcript_lines, full_text.strip()
