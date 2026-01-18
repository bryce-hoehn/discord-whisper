import mlx_whisper
from datetime import timedelta

def format_timestamp(seconds):
    """Convert seconds to [MM:SS] format"""
    td = timedelta(seconds=seconds)
    minutes = int(td.seconds // 60)
    seconds = int(td.seconds % 60)
    return f"[{minutes:02d}:{seconds:02d}]"

def transcribe_with_timestamps(audio_path, user_name=None):
    """Transcribe audio file with word-level timestamps"""
    # Use mlx_whisper with timestamp option
    transcription = mlx_whisper.transcribe(
        audio_path, 
        path_or_hf_repo="mlx-community/whisper-tiny.en-mlx-q4",
        word_timestamps=True  # Enable word-level timestamps
    )
    
    # Extract segments with timestamps
    transcript_lines = []
    if 'segments' in transcription:
        for segment in transcription['segments']:
            start_time = segment['start']
            end_time = segment['end']
            text = segment['text'].strip()
            
            if text:
                timestamp = format_timestamp(start_time)
                if user_name:
                    transcript_lines.append(f"{timestamp} {user_name}: {text}")
                else:
                    transcript_lines.append(f"{timestamp}: {text}")
    
    # Fallback if no segments
    if not transcript_lines and 'text' in transcription:
        if user_name:
            transcript_lines.append(f"{user_name}: {transcription['text'].strip()}")
        else:
            transcript_lines.append(transcription['text'].strip())
    
    return transcript_lines, transcription.get('text', '')

def combine_transcripts(user_transcripts):
    """Combine multiple user transcripts chronologically"""
    # Flatten all transcript lines with user info
    all_lines = []
    for user_id, (lines, full_text, user_name) in user_transcripts.items():
        all_lines.extend(lines)
    
    # Sort by timestamp (simple string sort works for [MM:SS] format)
    all_lines.sort(key=lambda x: x.split(']')[0] if ']' in x else '')
    
    return all_lines