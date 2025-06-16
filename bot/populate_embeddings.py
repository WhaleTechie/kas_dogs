import sqlite3
import os
import pickle
from bot.recognition import extract_features

def populate_embeddings(db_path="db/dogs.db"):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Make sure embedding column exists
    try:
        cur.execute("ALTER TABLE dogs ADD COLUMN embedding BLOB")
    except sqlite3.OperationalError:
        print("✅ Column 'embedding' already exists.")

    cur.execute("SELECT id, photo_path FROM dogs")
    dogs = cur.fetchall()

    updated = 0
    for dog_id, photo_path in dogs:
        if not os.path.exists(photo_path):
            print(f"⚠️ Photo not found for dog ID {dog_id}: {photo_path}")
            continue

        emb = extract_features(photo_path)
        emb_blob = pickle.dumps(emb)

        cur.execute("UPDATE dogs SET embedding = ? WHERE id = ?", (emb_blob, dog_id))
        updated += 1

    conn.commit()
    conn.close()
    print(f"🎉 Updated embeddings for {updated} dogs.")

if __name__ == "__main__":
    populate_embeddings()
