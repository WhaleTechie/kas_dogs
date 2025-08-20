import os
import faiss
import pickle
import numpy as np
from bot.embeddings import get_embedding

# --- Paths ---
INDEX_FILE = "dog_index.faiss"
LABELS_FILE = "dog_labels.pkl"   # <-- use .pkl

print("Loading FAISS index and labels...")

# Load FAISS index
index = faiss.read_index(INDEX_FILE)

# Load labels
with open(LABELS_FILE, "rb") as f:
    labels = pickle.load(f)

print(f"Loaded index with {len(labels)} labels.")

def search_image(img, k=5):
    """Search for similar images in the index."""
    emb = get_embedding(img).astype("float32").reshape(1, -1)
    distances, indices = index.search(emb, k)
    results = [(labels[i], float(distances[0][j])) for j, i in enumerate(indices[0])]
    return results
