from discord.ext import voice_recv

class PerUserRecordingSink(voice_recv.AudioSink):
    def __init__(self, base_path):
        super().__init__()
        self.base_path = base_path
        self.user_sinks = {}  # user_id -> FFmpegSink
        self.user_info = {}   # user_id -> user object
    
    def wants_opus(self):
        return True
    
    def write(self, user, data):
        if user and user.id not in self.user_sinks:
            # Store user info
            self.user_info[user.id] = user
            
            # Create individual file for this user
            user_file = f"{self.base_path}_user_{user.id}.ogg"
            user_sink = voice_recv.FFmpegSink(
                filename=user_file,
                options="-acodec libopus -b:a 128k -ar 48000 -ac 2 -application voip -frame_duration 20 -vbr on"
            )
            self.user_sinks[user.id] = user_sink
        
        # Write to user's individual sink
        if user and user.id in self.user_sinks:
            self.user_sinks[user.id].write(user, data)
    
    def cleanup(self):
        for sink in self.user_sinks.values():
            sink.cleanup()
    
    def get_user_files(self):
        """Return list of user audio files"""
        return [sink.filename for sink in self.user_sinks.values()]
    
    def get_user_info(self):
        """Return user_id to user object mapping"""
        return self.user_info