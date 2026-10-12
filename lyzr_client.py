import os, json, uuid, httpx
from dotenv import load_dotenv

load_dotenv()

URL = "https://agent-prod.studio.lyzr.ai/v3/inference/chat/"

def call_lyzr(message, agent_id=None):
    resp = httpx.post(
        URL,
        headers={
            "Content-Type": "application/json",
            "x-api-key": os.getenv("LYZR_API_KEY"),
        },
        json={
            "user_id": "meeting-agent-user",
            "agent_id": agent_id or os.getenv("LYZR_AGENT_ID"),
            "session_id": str(uuid.uuid4()),   # new session each call
            "message": message,
        },
        timeout=60,
    )
    resp.raise_for_status()
    data = resp.json()
    # The reply text is expected under "response"; print raw data if this differs
    return data["response"] if isinstance(data, dict) and "response" in data else json.dumps(data)

if __name__ == "__main__":
    transcript = open("sample_transcript.txt").read()
    print(call_lyzr(transcript))