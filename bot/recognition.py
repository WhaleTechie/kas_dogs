import os
import sqlite3
import torch
from torchvision import models, transforms
from PIL import Image
import numpy as np
import pickle

MODEL = None
TRANSFORM = transforms.Compose([
    transforms.Resize(256),
    transforms.CenterCrop(224),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
])

def _get_model():
    global MODEL
    if MODEL is None:
        model = models.resnet18(weights=models.ResNet18_Weights.DEFAULT)
        model.fc = torch.nn.Identity()
        model.eval()
        MODEL = model
    return MODEL

def extract_features(image_path: str) -> np.ndarray:
    model = _get_model()
    with Image.open(image_path) as img:
        img = img.convert("RGB").copy()
    tensor = TRANSFORM(img).unsqueeze(0)
    with torch.no_grad():
        features = model(tensor)
    return features.numpy().flatten()

def get_dog_by_photo(image_path: str, threshold: float = 0.8):
    query_emb = extract_features(image_path).flatten()

    conn = sqlite3.connect("db/dogs.db")
    cur = conn.cursor()
    cur.execute("SELECT id, name, pen, status, description, photo_folder, embeddings FROM dogs")
    rows = cur.fetchall()
    conn.close()

    best_score = -1.0
    best_dog = None

    for row in rows:
        dog_id, name, pen, status, desc, folder, emb_blob = row
        if emb_blob is None:
            continue

        try:
            emb_list = pickle.loads(emb_blob)
        except Exception as e:
            print(f"⚠️ Failed to load embeddings for dog {dog_id}: {e}")
            continue

        for db_emb in emb_list:
            db_emb = np.array(db_emb).flatten()
            if db_emb.shape != (512,):
                print(f"⚠️ Skipping mismatched embedding shape: {db_emb.shape}")
                continue

            score = np.dot(query_emb, db_emb) / (np.linalg.norm(query_emb) * np.linalg.norm(db_emb))
            if score > best_score:
                best_score = score
                best_dog = {
                    "id": dog_id,
                    "name": name,
                    "pen": pen,
                    "status": status,
                    "description": desc,
                    "photo_path": os.path.join(folder, os.listdir(folder)[0]) if folder else None,
                    "score": score,
                }

    if best_dog and best_score >= threshold:
        return best_dog
    return None
