import os, json, datetime
from extract import extract, SOURCE
from qdrant_store import store, recall, llm

os.makedirs("outputs", exist_ok=True)

QA_MODELS = ["gemini-3.8-flash", "gemini-flash-latest"]


def log(agent, message):
    """Write each agent step to a log file (shown in the dashboard) and print it."""
    entry = {
        "time": datetime.datetime.now().isoformat(timespec="seconds"),
        "agent": agent,
        "message": message,
    }
    with open("outputs/agent_log.jsonl", "a") as f:
        f.write(json.dumps(entry) + "\n")
    print(f"[{agent}] {message}")


def decide_and_act(item):
    """Action agent: decides what to do for each task without being asked."""
    if item.get("type") == "promise_to_person" and item.get("person"):
        body = (
            f"Subject: Follow-up: {item['task']}\n\n"
            f"Hi {item['person']},\n\n"
            f"Just confirming I will take care of '{item['task']}' "
            f"by {item.get('deadline')}.\n\nBest regards"
        )
        path = f"outputs/email_draft_{item['person']}.txt"
        with open(path, "w") as f:
            f.write(body)
        log("ActionAgent", f"Drafted follow-up email -> {path}")

    if item.get("deadline"):
        log("ActionAgent", f"Reminder scheduled: {item['task']} (due {item['deadline']})")


def handle_transcript(text):
    """Main loop: transcript in -> extract -> recall/store memory -> act."""
    log("ExtractorAgent", "Extracting tasks from transcript")
    items = extract(text)
    items = [i for i in items if isinstance(i, dict) and (i.get("task") or "").strip()]
    log("ExtractorAgent", f"Extracted {len(items)} tasks via {SOURCE['last']}")

    if not items:
        log("ExtractorAgent", "No action items found; nothing stored")
        return []

    for item in items:
        try:
            past = recall(item["task"], limit=2)
            log("MemoryAgent", f"Recalled {len(past)} related past items for: {item['task']}")
            store(item)
            log("MemoryAgent", f"Stored: {item['task']}")
            decide_and_act(item)
        except Exception as e:
            log("MemoryAgent", f"Skipped one item due to error: {str(e)[:100]}")
    return items


def ask(question):
    """Q&A agent: answers questions from stored meeting memory."""
    context = "\n".join(r["text"] for r in recall(question, limit=5))
    log("QAAgent", f"Answering: {question}")

    last_error = None
    for model in QA_MODELS:
        try:
            resp = llm.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "Answer using only the meeting memory provided. If the answer is not in the memory, say you don't know."},
                    {"role": "user", "content": f"Memory:\n{context}\n\nQuestion: {question}"},
                ],
            )
            return resp.choices[0].message.content
        except Exception as e:
            last_error = e
            log("QAAgent", f"{model} failed: {str(e)[:80]}")
    raise last_error


if __name__ == "__main__":
    handle_transcript(open("sample_transcript.txt").read())
    print("\nQ&A:", ask("What did I promise Rahul?"))