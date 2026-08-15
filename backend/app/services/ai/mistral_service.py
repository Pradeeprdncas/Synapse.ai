import json
import requests
from app.core.config import MISTRAL_API_KEY


URL = "https://api.mistral.ai/v1/chat/completions"


def generate_project_structure(text: str):

    prompt = f"""
You are an AI Project Architect.

Analyze the following project document/BRD/PRD.

Return ONLY valid JSON.

Do NOT return markdown.
Do NOT return explanations.
Do NOT wrap inside ```json.

Required JSON structure:

{{
  "project_summary": "",
  "modules": [
    {{
      "name": "",
      "description": ""
    }}
  ],
  "tasks": [
    {{
      "title": "",
      "description": "",
      "priority": "LOW"
    }}
  ],
  "checklists": [
    {{
      "title": ""
    }}
  ],
  "risks": [
    {{
      "risk": "",
      "severity": "LOW"
    }}
  ]
}}

Document:
{text}
"""

    headers = {
        "Authorization": f"Bearer {MISTRAL_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "mistral-small-latest",
        "temperature": 0.2,
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ]
    }

    try:

        response = requests.post(
            URL,
            headers=headers,
            json=payload,
            timeout=60
        )

        response.raise_for_status()

        data = response.json()

        content = data["choices"][0]["message"]["content"]

        content = clean_ai_response(content)

        parsed_json = json.loads(content)

        return parsed_json

    except requests.exceptions.RequestException as e:

        return {
            "error": "Mistral API request failed",
            "details": str(e)
        }

    except json.JSONDecodeError:

        return {
            "error": "Invalid JSON returned from AI",
            "raw_response": content
        }

    except Exception as e:

        return {
            "error": "Unexpected AI processing error",
            "details": str(e)
        }


def ask_mistral(prompt: str):

    headers = {
        "Authorization": f"Bearer {MISTRAL_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "mistral-small-latest",
        "temperature": 0.5,
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ]
    }

    try:
        response = requests.post(
            URL,
            headers=headers,
            json=payload,
            timeout=60
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        return f"I encountered an error while processing your request: {str(e)}"


def clean_ai_response(content: str):

    content = content.replace("```json", "")
    content = content.replace("```", "")
    content = content.strip()

    return content
