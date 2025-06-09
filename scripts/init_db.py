import os
import sqlite3

DB_DIR = "db"
DB_PATH = os.path.join(DB_DIR, "dogs.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS dogs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    pen TEXT,
    status TEXT,
    description TEXT,
    photo_path TEXT,
    embedding BLOB
)
"""

def main():
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    with conn:
        conn.execute(SCHEMA)
    print(f"Initialized database at {DB_PATH}")

if __name__ == "__main__":
    main()
