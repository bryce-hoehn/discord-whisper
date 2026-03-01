import os
import discord
from discord.ext import pages
from mlx_lm import load, generate


def generate_summary(transcript_text):
    model, tokenizer = load("lmstudio-community/Qwen3-8B-MLX-4bit")

    # Pass 1: Create a detailed condensed summary
    pass1_system_prompt = """
        You are a meeting transcript processor. Your task is to create a highly detailed but more condensed summary of the transcript.
        - Keep ALL main ideas and paraphrase every point made
        - Remove timestamps, filler words, and redundant content
        - Preserve the flow of conversation and who said what
        - Do NOT add any formatting or structure - just provide a clean, condensed narrative
    """

    pass1_user_prompt = transcript_text

    messages = [
        {"role": "system", "content": pass1_system_prompt},
        {"role": "user", "content": pass1_user_prompt},
    ]

    prompt = tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True, enable_thinking=False
    )

    condensed_summary = generate(
        model, tokenizer, prompt=prompt, verbose=True, max_tokens=131072
    )

    # Pass 2: Format into Discord markdown with sections
    pass2_system_prompt = """
        Summarize the meeting transcript in Discord markdown format with these sections:
        - Project Updates
        - Discussion Points
        - Action Items
        - Next Sprint Assignments

        Be concise and focus on key points only.
    """

    pass2_user_prompt = condensed_summary

    messages = [
        {"role": "system", "content": pass2_system_prompt},
        {"role": "user", "content": pass2_user_prompt},
    ]

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
