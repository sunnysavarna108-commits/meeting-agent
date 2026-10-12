import json, os, time
from dotenv import load_dotenv
from openai import OpenAI
from lyzr_client import call_lyzr

load_dotenv()

client = OpenAI(
    api_key=os.getenv("GEMINI_API_KEY"),
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
)

PROMPT = """You extract action items from meeting transcripts.
Only extract real commitments, requests or deadlines. Ignore small talk, unclear speech and non-English noise.
If there are no real action items, return [].
Return ONLY valid JSON: a list of objects with keys:
task, owner, person, deadline, type, priority.
type is one of: promise_to_person, personal_todo, delegated.
priority must be one of: high, medium, low (infer from urgency and deadlines).
Use null for unknown fields. No extra text."""

MODELS = ["gemini-3.8-flash", "gemini-flash-latest"]

# Records which engine produced the last result (used by pipeline.py for logging)
SOURCE = {"last": None}


def parse_json(text):
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```")[1].removeprefix("json").strip()
    return json.loads(text)


def extract_with_gemini(transcript):
    last_error = None
    for model in MODELS:
        for attempt in range(3):
            try:
                resp = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": PROMPT},
                        {"role": "user", "content": transcript},
                    ],
                    temperature=0,
                )
                return parse_json(resp.choices[0].message.content)
            except Exception as e:
                last_error = e
                print(f"{model} attempt {attempt + 1} failed: {str(e)[:80]}")
                time.sleep(2 * (attempt + 1))
    raise last_error


def extract(transcript):
    """Try the Lyzr agent first; fall back to Gemini if Lyzr fails."""
    try:
        items = parse_json(call_lyzr(transcript))
        SOURCE["last"] = "Lyzr agent"
        return items
    except Exception as e:
        print(f"Lyzr failed ({str(e)[:80]}), falling back to Gemini")
        SOURCE["last"] = "Gemini fallback"
        return extract_with_gemini(transcript)


if __name__ == "__main__":
    transcript = open("sample_transcript.txt").read()
    for item in extract(transcript):
        print(item)
    print("Source:", SOURCE["last"])