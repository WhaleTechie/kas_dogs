import os
import pickle
import numpy as np
import sqlite3
from bot.recognition import extract_features

def compute_embeddings_for_dog(folder_path):
    embeddings = []
    for fname in os.listdir(folder_path):
        if fname.lower().endswith(('.jpg', '.jpeg', '.png')):
            img_path = os.path.join(folder_path, fname)
            emb = extract_features(img_path)
            embeddings.append(emb)
    return embeddings

conn = sqlite3.connect("db/dogs.db")
cur = conn.cursor()

# assumes dog ID matches folder name (e.g., photos/1/, photos/2/)
for dog_id in range(1, 100):  # adjust range as needed
    folder = f"photos/{dog_id}"
    if os.path.isdir(folder):
        embs = compute_embeddings_for_dog(folder)
        if embs:
            blob = pickle.dumps(embs)
            cur.execute("UPDATE dogs SET embeddings = ? WHERE id = ?", (blob, dog_id))
            print(f"✅ Updated dog {dog_id} with {len(embs)} embeddings")

conn.commit()
conn.close()
