from mlx_lm import load, generate

# Model will be loaded on first use (lazy loading)
_model = None
_tokenizer = None


def _ensure_model_loaded():
    """Load model and tokenizer if not already loaded"""
    global _model, _tokenizer
    if _model is None:
        _model, _tokenizer = load("lmstudio-community/Qwen3-4B-Instruct-2507-MLX-4bit")
    return _model, _tokenizer


def generate_summary(transcript_text):
    """Generate summary from transcript text"""
    # Load model on first call
    model, tokenizer = _ensure_model_loaded()
    prompt = (
        """
        Summarize the meeting transcript in Discord markdown format with these sections:
        - Project Updates
        - Discussion Points
        - Action Items
        - Next Sprint Assignments
        
        Be concise and focus on key points only.
        
        Transcript:
        """
        + transcript_text
    )

    messages = [{"role": "user", "content": prompt}]
    prompt = tokenizer.apply_chat_template(messages, add_generation_prompt=True)

    response = generate(
        model,
        tokenizer,
        prompt=prompt,
        verbose=True,
        max_tokens=8192,
    )

    if "<think>" in response and "</think>" in response:
        response = response.split("</think>", 1)[1].strip()

    # Remove markdown code block formatting if present
    response = response.strip()

    if response.startswith("```"):
        lines = response.split("\n")
        lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]

        if lines:
            min_leading = float("inf")
            for line in lines:
                if line.strip():
                    leading = len(line) - len(line.lstrip())
                    if leading < min_leading:
                        min_leading = leading

            if min_leading != float("inf") and min_leading > 0:
                lines = [
                    line[min_leading:] if len(line) >= min_leading else line
                    for line in lines
                ]

        response = "\n".join(lines).strip()

    return response
