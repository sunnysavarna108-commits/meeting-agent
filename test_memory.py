from extract import extract
from qdrant_store import store, recall

transcript = open("sample_transcript.txt").read()
for item in extract(transcript):
    store(item)
    print("stored:", item["task"])

print("\nRecall 'Rahul':")
for r in recall("what did I promise Rahul?"):
    print("-", r["text"])