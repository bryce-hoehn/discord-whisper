import os
import discord
from discord.ext import pages
from mlx_lm import load, generate


def generate_summary(transcript_text):
    model, tokenizer = load("lmstudio-community/Qwen3-8B-MLX-4bit")

    prompt = f"""
        Summarize the meeting transcript in Discord markdown format with these sections:
        - Project Updates
        - Discussion Points
        - Action Items
        - Next Sprint Assignments
        
        Be concise and focus on key points only.

        Transcript:

        {transcript_text}
    """

    messages = [{"role": "user", "content": prompt}]

    prompt = tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True, enable_thinking=False
    )

    summary = generate(model, tokenizer, prompt=prompt, verbose=True, max_tokens=131072)

    # Remove markdown code block formatting if present
    if summary.startswith("```"):
        lines = summary.split("\n")
        lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        summary = "\n".join(lines).strip()

    return summary


def create_summary_embed(summary):
    """Create Discord embed(s) from the summary without truncation.
    Splits at heading boundaries when possible to keep sections intact.
    """

    max_length = 4096
    embed_title = "📝 Meeting Summary"
    embed_color = discord.Color.blue()

    def is_heading(line):
        """Check if line is a heading."""
        stripped = line.strip()
        return (
            stripped.startswith("##")
            or stripped.startswith("###")
            or (stripped.startswith("**") and stripped.endswith("**"))
        )

    # Split summary into sections (heading + content)
    sections = []
    current_section = []
    for line in summary.split("\n"):
        if is_heading(line) and current_section:
            sections.append("\n".join(current_section))
            current_section = [line]
        else:
            current_section.append(line)
    if current_section:
        sections.append("\n".join(current_section))

    # Build chunks from sections
    chunks = []
    current_chunk = ""

    for section in sections:
        # If section is too long for one chunk, split it by line
        if len(section) > max_length:
            if current_chunk:
                chunks.append(current_chunk)
                current_chunk = ""
            for line in section.split("\n"):
                if len(current_chunk) + len(line) + 1 > max_length:
                    if current_chunk:
                        chunks.append(current_chunk)
                    current_chunk = line
                else:
                    current_chunk += "\n" + line if current_chunk else line
        # If section fits in current chunk
        elif len(current_chunk) + len(section) + 1 <= max_length:
            current_chunk += "\n" + section if current_chunk else section
        # Start new chunk with this section
        else:
            if current_chunk:
                chunks.append(current_chunk)
            current_chunk = section

    if current_chunk:
        chunks.append(current_chunk)

    # Create Page objects
    page_list = []
    for i, chunk in enumerate(chunks):
        title = (
            f"{embed_title} ({i + 1}/{len(chunks)})" if len(chunks) > 1 else embed_title
        )
        embed = discord.Embed(title=title, description=chunk, color=embed_color)
        page_list.append(pages.Page(embeds=[embed]))

    return page_list
