import os, uuid
from dotenv import load_dotenv
from openai import OpenAI
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct

load_dotenv()

llm = OpenAI(
    api_key=os.getenv("GEMINI_API_KEY"),
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
)
qdrant = QdrantClient(url=os.getenv("QDRANT_URL"), api_key=os.getenv("QDRANT_API_KEY"))

COLLECTION = "meeting_memory"
EMBED_MODEL = "gemini-embedding-001"   # check the exact name in AI Studio if you get 404

def embed(text):
    return llm.embeddings.create(model=EMBED_MODEL, input=text).data[0].embedding

def ensure_collection():
    if not qdrant.collection_exists(COLLECTION):
        size = len(embed("test"))
        qdrant.create_collection(
            collection_name=COLLECTION,
            vectors_config=VectorParams(size=size, distance=Distance.COSINE),
        )

def store(task):
    ensure_collection()
    text = f"{task['task']} | person: {task['person']} | deadline: {task['deadline']} | type: {task['type']}"
    qdrant.upsert(
        collection_name=COLLECTION,
        points=[
            PointStruct(
                id=str(uuid.uuid5(uuid.NAMESPACE_DNS, text)),
                vector=embed(text),
                payload={**task, "text": text}
            )
        ],
    )

def recall(query, limit=3):
    ensure_collection()
    hits = qdrant.query_points(
        collection_name=COLLECTION, query=embed(query), limit=limit
    ).points
    return [h.payload for h in hits]