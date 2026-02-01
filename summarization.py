import os
from openai import OpenAI

summarization_client = OpenAI(
    base_url=os.getenv("SUMMARIZER_URL"),
    api_key="not-needed"  # Required by client but not used by model-runner
)

def generate_summary(transcript_text):
    """Generate summary from transcript text using Docker Model Runner's summarizer model"""
    prompt = """
    Summarize the meeting transcript in Discord markdown format with these sections:
    - Project Updates
    - Discussion Points
    - Action Items
    - Next Sprint Assignments
    
    Be concise and focus on key points only.
    
    Transcript:
    """ + transcript_text

    response = summarization_client.chat.completions.create(
        model=os.getenv("SUMMARIZER_MODEL"),
        messages=[
            {
                "role": "system",
                "content": "You are a helpful assistant that summarizes meeting transcripts."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        max_tokens=262144,
        temperature=0.3
    )

    summary = response.choices[0].message.content.strip()
    
    # Remove markdown code block formatting if present
    if summary.startswith("```"):
        lines = summary.split("\n")
        lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        summary = "\n".join(lines).strip()
    
    return summary
