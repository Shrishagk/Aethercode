import os
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
import tiktoken

MODEL = SentenceTransformer("all-MiniLM-L6-v2")  # free, runs locally

CHUNK_SIZE = 400
CHUNK_OVERLAP = 50

def chunk_code(file_path: str, content: str) -> list[dict]:
    enc = tiktoken.get_encoding("cl100k_base")
    tokens = enc.encode(content)
    chunks = []
    start = 0
    while start < len(tokens):
        end = min(start + CHUNK_SIZE, len(tokens))
        chunk_text = enc.decode(tokens[start:end])
        chunks.append({
            "file": file_path,
            "text": chunk_text,
            "start_token": start
        })
        start += CHUNK_SIZE - CHUNK_OVERLAP
    return chunks

def build_index(file_contents: dict) -> tuple:
    all_chunks = []
    for file_path, content in file_contents.items():
        all_chunks.extend(chunk_code(file_path, content))

    print(f"Total chunks: {len(all_chunks)}")

    texts = [c["text"] for c in all_chunks]
    print("Generating embeddings locally (no API needed)...")
    embeddings = MODEL.encode(texts, show_progress_bar=True)

    dim = embeddings.shape[1]
    index = faiss.IndexFlatL2(dim)
    index.add(np.array(embeddings, dtype="float32"))

    print(f"Index built with {index.ntotal} vectors")
    return index, all_chunks

def search_index(query: str, index, chunks: list, top_k: int = 5) -> list[dict]:
    query_vec = MODEL.encode([query])
    query_vec = np.array(query_vec, dtype="float32")
    distances, indices = index.search(query_vec, top_k)
    results = []
    for i, idx in enumerate(indices[0]):
        results.append({
            **chunks[idx],
            "score": float(distances[0][i])
        })
    return results