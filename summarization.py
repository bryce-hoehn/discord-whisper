import os
from mlx_lm import load, generate

def split_summary_by_headings(summary):
    """Split summary into separate messages by # headings"""
    messages = []
    lines = summary.split("\n")
    
    current_message = []
    
    for line in lines:
        if line.strip().startswith("#"):
            # Save previous message if exists
            if current_message:
                messages.append("\n".join(current_message).strip())
            # Start new message with this heading
            current_message = [line]
        else:
            current_message.append(line)
    
    # Add the last message
    if current_message:
        messages.append("\n".join(current_message).strip())
    
    return messages

def generate_summary(transcript_text, arg=""):
    model, tokenizer = load("lmstudio-community/Qwen3-8B-MLX-4bit")

    prompt = f"""
        Summarize the meeting transcript in Discord markdown format with these sections:
        - Project Updates
        - Discussion Points
        - Action Items
        - Next Sprint Assignments
        
        Be concise and focus on key points only.

        {arg}

        Transcript:

        {transcript_text}
    """
    
    messages = [{"role": "user", "content": prompt}]

    prompt = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
        enable_thinking=False
    )

    summary = generate(
        model,
        tokenizer,
        prompt=prompt,
        verbose=True,
        max_tokens=131072)

    # Remove markdown code block formatting if present
    if summary.startswith("```"):
        lines = summary.split("\n")
        lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        summary = "\n".join(lines).strip()
    
    return summary
