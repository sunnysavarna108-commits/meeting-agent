import json, os, threading
from fastapi import FastAPI, Request
from pipeline import handle_transcript, ask, log

app = FastAPI(title="Meeting-to-Action Agent")
os.makedirs("outputs", exist_ok=True)

FLUSH_SECONDS = 30      # process after this much silence
MIN_WORDS = 6           # ignore tiny fragments
buffers, timers = {}, {}
lock = threading.Lock()


def flush(session_id):
    with lock:
        lines = buffers.pop(session_id, [])
        timers.pop(session_id, None)
    text = "\n".join(lines)
    if len(text.split()) < MIN_WORDS:
        log("OmiWebhook", f"Session {session_id}: skipped (too short)")
        return
    try:
        log("OmiWebhook", f"Session {session_id}: processing {len(lines)} segments")
        handle_transcript(text)
    except Exception as e:
        log("OmiWebhook", f"Pipeline error: {str(e)[:120]}")


@app.post("/webhook/transcript")
async def omi_transcript(request: Request, session_id: str = "default", uid: str = ""):
    data = await request.json()
    with open("outputs/omi_raw.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(data) + "\n")
    sid = data.get("session_id", session_id)
    with lock:
        for s in data.get("segments", []):
            text = (s.get("text") or "").strip()
            if not text:
                continue
            who = "Me" if s.get("is_user") else (s.get("speaker") or "Other")
            buffers.setdefault(sid, []).append(f"{who}: {text}")
        if sid in timers:
            timers[sid].cancel()
        timers[sid] = threading.Timer(FLUSH_SECONDS, flush, args=[sid])
        timers[sid].start()
    log("OmiWebhook", f"Received segments for session {sid}")
    return {"status": "received"}


@app.post("/simulate")
async def simulate(request: Request):
    data = await request.json()
    return {"tasks": handle_transcript(data["text"])}


@app.get("/ask")
def ask_endpoint(q: str):
    return {"answer": ask(q)}


@app.get("/")
def health():
    return {"status": "ok"}