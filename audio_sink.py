import discord
import io


class PerUserAudioSink(discord.sinks.Sink):
    """Custom sink that stores audio per user in memory"""

    def __init__(self):
        super().__init__()
        self.audio_data = {}
        self.user_info = {}

    def write(self, data, user):
        """Called when audio data is received from a user"""
        if user is None:
            return

        user_id = user.id

        # Store user info
        if user_id not in self.user_info:
            self.user_info[user_id] = user

        # Initialize audio data buffer for this user if not exists
        if user_id not in self.audio_data:
            self.audio_data[user_id] = discord.sinks.core.AudioData(io.BytesIO())

        # Write the PCM audio data
        self.audio_data[user_id].write(data)

    def cleanup(self):
        """Called when recording stops"""
        # Seek to beginning of all audio buffers
        for audio in self.audio_data.values():
            audio.file.seek(0)

    def get_all_audio(self):
        """Get all audio data organized by user"""
        return self.audio_data

    def get_user_info(self):
        """Return user_id to user object mapping"""
        return self.user_info

    @discord.sinks.Filters.container
    def get_container_format(self):
        """Return the audio container format"""
        return "wav"
