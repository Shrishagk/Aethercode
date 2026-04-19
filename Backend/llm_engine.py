import os
import json
import time
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("MISTRAL_API_KEY")
API_URL = "https://api.mistral.ai/v1/chat/completions"

SYSTEM_PROMPT = """
You are AetherCode, an AI assistant that helps developers understand
how to safely modify a codebase.

Given a developer task and relevant code snippets, respond ONLY in
this exact JSON format with absolutely no extra text outside it:

{
  "files_to_modify": ["file1.py", "file2.py"],
  "reason": "Why these files are relevant",
  "impact": "What else in the codebase might be affected",
  "risk": "What could break or go wrong",
  "steps": ["Step 1: ...", "Step 2: ...", "Step 3: ..."]
}

Be specific. Reference actual file names from the snippets.
Do not write anything outside the JSON block.
"""

def build_user_prompt(task: str, chunks: list[dict]) -> str:
    context = ""
    for i, chunk in enumerate(chunks[:4]):
        context += f"\n--- Snippet {i+1} from {chunk['file']} ---\n"
        context += chunk["text"][:300]
        context += "\n"
    return f"""
Developer task: {task}

Relevant code snippets from the repository:
{context}

Respond with JSON only. No explanation outside the JSON block.
"""

def get_change_plan(task: str, chunks: list[dict]) -> dict:
    user_prompt = build_user_prompt(task, chunks)

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "mistral-small-latest",
        "temperature": 0.2,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": user_prompt}
        ]
    }

    for attempt in range(3):
        try:
            response = requests.post(API_URL, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            raw = response.json()["choices"][0]["message"]["content"].strip()
            break
        except Exception as e:
            if attempt < 2:
                print(f"Attempt {attempt+1} failed: {e}. Retrying in 10s...")
                time.sleep(10)
            else:
                return {"error": str(e)}

    # Strip markdown fences if present
    if "```" in raw:
        parts = raw.split("```")
        for part in parts:
            part = part.strip()
            if part.startswith("json"):
                part = part[4:]
            try:
                return json.loads(part.strip())
            except json.JSONDecodeError:
                continue

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {
            "raw_response": raw,
            "parse_error": "Could not parse JSON"
        }