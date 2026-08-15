import requests

from config import (
    MISTRAL_API_KEY,
    MISTRAL_MODEL
)

def build_prompt(
    question,
    chunks,
    history=""
):
    """
    Build final prompt
    """

    context = "\n\n".join([
        f"[Chunk {i+1}]\n{chunk}"
        for i, chunk in enumerate(chunks[:4])
    ])

    return f"""
You are an AI project intelligence assistant.

Answer ONLY from the provided context.

PREVIOUS CHAT:
{history}

PROJECT CONTEXT:
{context}

USER QUESTION:
{question}

Give:
- operational answer
- concise explanation
- structured response
- bullet points if needed
"""


def generate_answer(prompt: str):
    """
    Generate answer using Mistral chat API
    """

    url = "https://api.mistral.ai/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {MISTRAL_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": MISTRAL_MODEL,
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.2
    }

    response = requests.post(
        url,
        headers=headers,
        json=payload,
        timeout=120
    )

    response.raise_for_status()

    data = response.json()

    return data["choices"][0]["message"]["content"]
