import chromadb
from config.settings import CHROMA_PERSIST_DIR, COLLECTION_NAME


def _get_collection():
    client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"}
    )


def index_letter(
    doc_id: str,
    text: str,
    lor_type: str,
    field: str,
    approved_date: str,
) -> None:
    collection = _get_collection()
    collection.add(
        ids=[doc_id],
        documents=[text],
        metadatas=[{
            "lor_type": lor_type,
            "field": field,
            "approved_date": approved_date,
        }]
    )


def retrieve_examples(query: str, lor_type: str, n: int = 3) -> list:
    collection = _get_collection()
    results = collection.query(
        query_texts=[query],
        n_results=n,
        where={"lor_type": lor_type} if lor_type else None,
    )
    return results["documents"][0] if results["documents"] else []
