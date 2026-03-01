import discord
import os
import asyncio
from discord.ext.pages import Paginator, Page
from datetime import datetime
from dotenv import load_dotenv
from transcription import transcribe_audio
from summarization import generate_summary, create_summary_embed


load_dotenv()

bot = discord.Bot(intents=discord.Intents.all())

opus_path = "/opt/homebrew/opt/opus/lib/libopus.0.dylib"
discord.opus.load_opus(opus_path)

# Global state
connections = {}
recording_state = {}


async def update_timer(guild_id: int):
    """Background task to update the recording timer message."""
    while guild_id in recording_state:
        state = recording_state[guild_id]
        elapsed = datetime.utcnow() - state["start_time"]
        minutes, seconds = divmod(int(elapsed.total_seconds()), 60)

        # Create updated embed
        embed = discord.Embed(
            title="🎙️ Voice Recording",
            description=f"**Duration:** `{minutes:02d}:{seconds:02d}`\n\n"
            f"📌 **Channel:** {state['vc'].channel.name}\n"
            f"👥 **Participants:** {len(state['vc'].channel.members) - 1}",
            color=discord.Color.red(),
        )
        embed.set_footer(text="Click the stop button to end recording")

        try:
            await state["message"].edit(embed=embed, view=state["view"])
        except discord.NotFound:
            del recording_state[guild_id]
            return

        await asyncio.sleep(1)


class RecordView(discord.ui.View):
    def __init__(self):
        super().__init__()

    @discord.ui.button(
        label="Stop Recording", style=discord.ButtonStyle.danger, emoji="⏹️"
    )
    async def stop_button_callback(self, button, interaction):
        if interaction.guild.id in connections:
            if interaction.guild.id in recording_state:
                recording_state[interaction.guild.id]["timer_task"].cancel()
                del recording_state[interaction.guild.id]

            # Update embed to show stopped state
            embed = discord.Embed(
                title="✅ Recording Stopped",
                description="Processing audio and generating transcript...",
                color=discord.Color.green(),
            )
            embed.set_footer(text="Please wait")

            self.disable_all_items()
            await interaction.response.edit_message(embed=embed, view=self)

            vc = connections[interaction.guild.id]
            vc.stop_recording()
            del connections[interaction.guild.id]
        else:
            await interaction.response.send_message(
                "I am currently not recording here.", ephemeral=True
            )


async def once_done(sink: discord.sinks, channel: discord.TextChannel, *args):
    """Callback when recording is complete."""

    if channel.guild.id in recording_state:
        recording_state[channel.guild.id]["timer_task"].cancel()
        del recording_state[channel.guild.id]

    await sink.vc.disconnect()

    recordings_dir = "recordings"
    os.makedirs(recordings_dir, exist_ok=True)

    all_transcripts = []

    for user_id, audio in sink.audio_data.items():
        user = sink.vc.guild.get_member(user_id)
        user_name = user.display_name if user else f"User {user_id}"
        timestamp = int(discord.utils.utcnow().timestamp())
        filename = f"{user_name}_{user_id}_{timestamp}.ogg"
        filepath = os.path.join(recordings_dir, filename)

        with open(filepath, "wb") as f:
            f.write(audio.file.read())

        transcript_lines = transcribe_audio(filepath, user_name)
        all_transcripts.extend(transcript_lines)

    all_transcripts.sort()
    transcript = "\n".join(all_transcripts)
    summary = generate_summary("**Transcript:**\n" + transcript)

    md_file = f"recordings/summary_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.md"

    with open(md_file, "w") as f:
        f.write(summary)

    await channel.send(
        "Summary attached!", file=discord.File(md_file, filename="meeting_summary.md")
    )


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name} ({bot.user.id})")


@bot.command()
async def record(ctx):
    voice = ctx.author.voice

    if not voice:
        await ctx.respond("You aren't in a voice channel!", ephemeral=True)
        return

    vc = await voice.channel.connect()
    connections.update({ctx.guild.id: vc})

    vc.start_recording(
        discord.sinks.OGGSink(),
        once_done,
        ctx.channel,
    )

    # Create initial embed
    embed = discord.Embed(
        title="🎙️ Voice Recording",
        description=f"**Duration:** `00:00`\n\n"
        f"📌 **Channel:** {vc.channel.name}\n"
        f"👥 **Participants:** {len(vc.channel.members) - 1}",
        color=discord.Color.red(),
    )
    # embed.set_footer(text="Click the stop button to end recording")

    view = RecordView()
    message = await ctx.respond(embed=embed, view=view)

    recording_state[ctx.guild.id] = {
        "start_time": datetime.utcnow(),
        "message": message,
        "view": view,
        "vc": vc,
        "timer_task": bot.loop.create_task(update_timer(ctx.guild.id)),
    }


if __name__ == "__main__":
    bot.run(os.getenv("DISCORD_TOKEN"))
