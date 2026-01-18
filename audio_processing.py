import subprocess
import shutil

def combine_audio_files(user_files, output_path):
    """Combine multiple audio files into one using FFmpeg"""
    if not user_files:
        return False
    
    if len(user_files) == 1:
        # If only one user, just copy the file
        shutil.copy2(user_files[0], output_path)
        return True
    
    # Build FFmpeg command to mix audio files
    inputs = []
    filter_complex = []
    
    for i, file in enumerate(user_files):
        inputs.extend(['-i', file])
        filter_complex.append(f'[{i}:a]')
    
    # Use amix filter to combine audio
    filter_complex.append(f'amix=inputs={len(user_files)}:duration=longest')
    
    cmd = [
        'ffmpeg',
        '-y',  # Overwrite output file
        *inputs,
        '-filter_complex',
        ''.join(filter_complex),
        '-ac', '2',
        output_path
    ]
    
    try:
        subprocess.run(cmd, check=True, capture_output=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"FFmpeg error: {e.stderr.decode()}")
        return False