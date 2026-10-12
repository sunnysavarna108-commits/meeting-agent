from qdrant_store import qdrant, COLLECTION

if qdrant.collection_exists(COLLECTION):
    qdrant.delete_collection(COLLECTION)
    print("Deleted", COLLECTION)
else:
    print("Nothing to delete")