import os
import sqlite3
import pickle
from bot.recognition import extract_features

DB_PATH = "db/dogs.db"


def ensure_column(conn):
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(dogs)")
    cols = [row[1] for row in cur.fetchall()]
    if "embedding" not in cols:
        cur.execute("ALTER TABLE dogs ADD COLUMN embedding BLOB")
        conn.commit()


def migrate():
    if not os.path.exists(DB_PATH):
        print(f"Database {DB_PATH} not found")
        return
    conn = sqlite3.connect(DB_PATH)
    ensure_column(conn)
    cur = conn.cursor()
    cur.execute("SELECT id, photo_path, embedding FROM dogs")
    rows = cur.fetchall()
    for dog_id, path, emb in rows:
        if emb is not None or not path or not os.path.exists(path):
            continue
        try:
            vec = extract_features(path)
        except Exception as e:
            print(f"Failed to process {path}: {e}")
            continue
        blob = pickle.dumps(vec)
        cur.execute("UPDATE dogs SET embedding=? WHERE id=?", (blob, dog_id))
        conn.commit()
    conn.close()
    print("Migration complete")


if __name__ == "__main__":
    migrate()
