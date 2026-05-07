import os
import glob
from pathlib import Path

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_community.document_loaders import TextLoader
from langchain.schema import Document

from dotenv import load_dotenv

load_dotenv()

DOCS_DIR = Path(__file__).parent / "documents"
CHROMA_DIR = Path(__file__).parent / "chroma_db"
COLLECTION_NAME = "my_rag_collection"
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50

def load_documents(docs_dir: Path = DOCS_DIR) -> list[Document]:
    """Load all text documents from the specified directory."""
    docs = []
    txt_files = sorted(glob.glob(str(docs_dir / "*.txt")))

    if not txt_files:
        print(f"⚠️ No .txt files found in {docs_dir}. Please add some documents.")
        raise FileNotFoundError(f"No .txt files in {docs_dir}")

    for filepath in txt_files:
        loader = TextLoader(filepath, encoding="utf-8")
        loaded_docs = loader.load()
        
        for doc in loaded_docs:
            doc.metadata["source"] = Path(filepath).stem
        
        docs.extend(loaded_docs)
        print(f"✅ Loaded {len(loaded_docs)} documents from {filepath}")
    
    return docs

def split_documents(docs: list[Document]) -> list[Document]:
    """Split documents into smaller chunks using RecursiveCharacterTextSplitter."""
    splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP, separators=["\n\n", "\n", ".", " ", ""])

    chunks = splitter.split_documents(docs)

    print(f"✅ Split {len(docs)} documents into {len(chunks)} chunks (Chunk Size: {CHUNK_SIZE}, Overlap: {CHUNK_OVERLAP})")

    return chunks

def build_vector_store(chunks: list[Document]) -> Chroma:
    """Embed chunks and persist them in a Chroma vector store."""
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

    vector_store = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        collection_name=COLLECTION_NAME,
        persist_directory=str(CHROMA_DIR)
    )

    print(f"✅ Built vector store with {len(chunks)} chunks embedded and persisted to {CHROMA_DIR}")
    return vector_store

def load_vector_store() -> Chroma:
    """Load the Chroma vector store from disk."""
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

    vector_store = Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=embeddings,
        persist_directory=str(CHROMA_DIR)
    )

    print(f"✅ Loaded vector store from {CHROMA_DIR} with collection '{COLLECTION_NAME}'")
    return vector_store 

def ingest_all() -> Chroma: 
    """Full ingestion pipeline: Load, Split, Embed, and Persist."""
    docs = load_documents()
    chunks = split_documents(docs)
    vector_store = build_vector_store(chunks)
    print("✅ Ingestion complete. Vector store is ready for use.")
    return vector_store

# ── Core retrieval function ───────────────────────────────────────────────────

def retrieve_relevant_chunks(query: str, vector_store: Chroma, top_k: int = 3) -> list[dict]:
    """
    Return the top-k most relevant chunks for a given query.

    Parameters
    ----------
    query       : Natural-language question.
    top_k       : Number of chunks to return.
    vectorstore : Pre-loaded Chroma instance (loads from disk if None).

    Returns
    -------
    List of dicts, each with keys:
        - content  : chunk text
        - source   : source document name (e.g. "return_policy")
        - score    : similarity score (lower = more similar for L2 distance)
        - metadata : full LangChain metadata dict
    """

    if vector_store is None:
        vector_store = load_vector_store()

    results = vector_store.similarity_search_with_score(query, k=top_k)

    chunks = []

    for doc, score in results:
        chunks.append({
            "content": doc.page_content,
            "source": doc.metadata.get("source", "unknown"),
            "score": round(float(score), 4),
            "metadata": doc.metadata
        })

    return chunks

# ── CLI / quick test ──────────────────────────────────────────────────────────


def pretty_print_chunks(chunks: list[dict], query: str):
    print(f"\n{'='*60}")
    print(f"Query : {query}")
    print(f"{'='*60}")
    for i, c in enumerate(chunks, 1):
        print(f"\n[Chunk {i}]  source={c['source']}  score={c['score']}")
        print("-" * 40)
        print(c["content"][:400] + ("…" if len(c["content"]) > 400 else ""))
    print()


if __name__ == "__main__":
    vs = ingest_all()

    test_query = "What's the return policy for damaged items?"
    chunks = retrieve_relevant_chunks(test_query, vs, top_k=3)
    pretty_print_chunks(chunks, test_query)
