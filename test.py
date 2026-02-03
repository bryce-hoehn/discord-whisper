import os
from summarization import generate_summary, split_summary_by_headings
from transcription import transcribe_audio
    
# Create recordings directory if it doesn't exist
recordings_dir = "recordings"
os.makedirs(recordings_dir, exist_ok=True)

all_transcripts = []

for f in os.listdir(recordings_dir):
    if f.endswith(".ogg"):
        user_name = f.split("_")[0]
        transcript_lines = transcribe_audio(f"{recordings_dir}/{f}", user_name)
        all_transcripts.extend(transcript_lines)

all_transcripts.sort()

transcript = "\n".join(all_transcripts)

with open(f"{recordings_dir}/transcript.txt", "w") as f:
    f.write(transcript)

summary = generate_summary("**Transcript:**\n" + transcript)

# Split summary by headings for file output
summary_messages = split_summary_by_headings(summary)
with open(f"{recordings_dir}/summary.md", "w") as f:
    for msg in summary_messages:
        f.write(msg + "\n\n")
