from discord.ext import voice_recv
import subprocess
import os
import threading
import time

class PerUserRecordingSink(voice_recv.AudioSink):
    def __init__(self, base_path):
        super().__init__()
        self.base_path = base_path
        self.user_sinks = {}  # user_id -> (process, filename)
        self.user_info = {}   # user_id -> user object
        self.user_buffers = {}  # user_id -> list of audio packets
        self.buffer_lock = threading.Lock()
    
    def wants_opus(self):
        return True
    
    def write(self, user, data):
        if not user:
            return
            
        user_id = user.id
        
        # Store user info
        if user_id not in self.user_info:
            self.user_info[user_id] = user
            
        # Buffer audio data
        with self.buffer_lock:
            if user_id not in self.user_buffers:
                self.user_buffers[user_id] = []
            self.user_buffers[user_id].append(data)
            
            # Start FFmpeg process if not already started
            if user_id not in self.user_sinks:
                self._start_ffmpeg_process(user_id)
            
            # Write buffered data to FFmpeg
            self._write_to_ffmpeg(user_id)
    
    def _start_ffmpeg_process(self, user_id):
        """Start FFmpeg process for a user"""
        user_file = f"{self.base_path}_user_{user_id}.ogg"
        
        # FFmpeg command to repackage Opus packets into OGG container
        # Discord sends raw Opus packets, we need to wrap them in OGG
        ffmpeg_cmd = [
            'ffmpeg',
            '-f', 'opus',           # Input format: Opus packets
            '-ar', '48000',         # Input sample rate: 48kHz
            '-ac', '2',             # Input channels: stereo
            '-i', 'pipe:0',         # Read from stdin
            '-c:a', 'copy',         # Copy the Opus stream (no re-encoding)
            '-y',                   # Overwrite output file
            user_file
        ]
        
        try:
            # Start FFmpeg process
            process = subprocess.Popen(
                ffmpeg_cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            self.user_sinks[user_id] = (process, user_file)
            print(f"Started FFmpeg process for user {user_id}")
        except Exception as e:
            print(f"Error starting FFmpeg for user {user_id}: {e}")
    
    def _write_to_ffmpeg(self, user_id):
        """Write buffered audio data to FFmpeg process"""
        if user_id not in self.user_sinks:
            return
            
        process, _ = self.user_sinks[user_id]
        
        with self.buffer_lock:
            if user_id in self.user_buffers and self.user_buffers[user_id]:
                # Combine all buffered packets
                combined_data = b''.join(self.user_buffers[user_id])
                
                try:
                    # Write to FFmpeg stdin
                    process.stdin.write(combined_data)
                    process.stdin.flush()
                except Exception as e:
                    print(f"Error writing to FFmpeg for user {user_id}: {e}")
                
                # Clear buffer
                self.user_buffers[user_id] = []
    
    def cleanup(self):
        """Clean up all FFmpeg processes"""
        for user_id, (process, filename) in self.user_sinks.items():
            # Write any remaining buffered data
            self._write_to_ffmpeg(user_id)
            
            # Close stdin and wait for process
            try:
                if process.stdin:
                    process.stdin.close()
                process.wait(timeout=2)
                print(f"FFmpeg process for user {user_id} completed")
            except Exception as e:
                print(f"Error cleaning up FFmpeg for user {user_id}: {e}")
                process.terminate()
        
        # Clear all buffers
        with self.buffer_lock:
            self.user_buffers.clear()
    
    def get_user_files(self):
        """Return list of user audio files"""
        return [filename for _, filename in self.user_sinks.values()]
    
    def get_user_info(self):
        """Return user_id to user object mapping"""
        return self.user_info