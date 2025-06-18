import os
import pickle
import sqlite3
import numpy as np
from bot.recognition import extract_features

def compute_embeddings_for_dog(folder_path):
    embeddings = []
    for fname in os.listdir(folder_path):
        if fname.lower().endswith(('.jpg', '.jpeg', '.png')):
            img_path = os.path.join(folder_path, fname)
            try:
                emb = extract_features(img_path)
                emb = emb.flatten()
                if emb.shape == (512,):
                    print(f"{fname} → {emb.shape}")
                    embeddings.append(emb)
                else:
                    print(f"⚠️ Skipping {fname} due to shape {emb.shape}")
            except Exception as e:
                print(f"⚠️ Error processing {img_path}: {e}")
    return embeddings

def main():
    conn = sqlite3.connect("db/dogs.db")
    cur = conn.cursor()
    cur.execute("SELECT id FROM dogs")
    dog_ids = [row[0] for row in cur.fetchall()]

    updated = 0
    skipped = 0

    for dog_id in dog_ids:
        folder = os.path.join("photos", str(dog_id).zfill(4))
        print(f"🔍 Checking: {folder}")
        if os.path.isdir(folder):
            embs = compute_embeddings_for_dog(folder)
            if embs:
                blob = pickle.dumps(embs)
                try:
                    cur.execute("UPDATE dogs SET embeddings = ? WHERE id = ?", (blob, dog_id))
                    print(f"✅ Dog {dog_id}: {len(embs)} embeddings saved.")
                    updated += 1
                except Exception as e:
                    print(f"❌ DB update failed for dog {dog_id}: {e}")
            else:
                print(f"⚠️ Dog {dog_id}: No valid images.")
                skipped += 1
        else:
            print(f"🚫 Folder not found for dog {dog_id}")
            skipped += 1

    conn.commit()
    conn.close()
    print(f"\n🎉 Done: {updated} dogs updated, {skipped} skipped.")

if __name__ == "__main__":
    main()
