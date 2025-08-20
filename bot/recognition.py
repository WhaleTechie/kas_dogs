# bot/recognition.py
import os
import faiss
import numpy as np
import torch
import torchvision.models as models
import torchvision.transforms as T
from PIL import Image
from torchvision.models import resnet18, ResNet18_Weights

# --- Paths to index & metadata ---
BASE_DIR = os.path.dirname(__file__)
INDEX_PATH = os.path.join(BASE_DIR, "dog_index.faiss")
METADATA_PATH = os.path.join(BASE_DIR, "dog_labels.npy")

print(f"[Recognition] BASE_DIR = {BASE_DIR}")
print(f"[Recognition] INDEX_PATH exists? {os.path.exists(INDEX_PATH)}")
print(f"[Recognition] METADATA_PATH exists? {os.path.exists(METADATA_PATH)}")

if not os.path.exists(INDEX_PATH) or not os.path.exists(METADATA_PATH):
    raise FileNotFoundError(f"Index or metadata not found: {INDEX_PATH}, {METADATA_PATH}")

# --- Load FAISS index & metadata ---
index = faiss.read_index(INDEX_PATH)
metadata = np.load(METADATA_PATH, allow_pickle=True).tolist()

# --- Device ---
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# --- Load ResNet18 embedding model ---
weights = ResNet18_Weights.DEFAULT
resnet = resnet18(weights=weights)
resnet.fc = torch.nn.Identity()  # Remove classification head
resnet = resnet.to(device).eval()

# --- Image preprocessing ---
transform = T.Compose([
    T.Resize((224, 224)),
    T.ToTensor(),
    T.Normalize(mean=[0.485, 0.456, 0.406],
                std=[0.229, 0.224, 0.225]),
])

# --- Helper: get embedding ---
def get_embedding(img_path: str):
    try:
        img = Image.open(img_path).convert("RGB")
    except Exception as e:
        print(f"[Recognition] Failed to open image {img_path}: {e}")
        return None
    tensor = transform(img).unsqueeze(0).to(device)
    with torch.no_grad():
        emb = resnet(tensor).cpu().numpy()
    return emb.astype("float32")

# --- Main recognition function ---
def get_dog_by_photo(photo_path: str):
    try:
        query_emb = get_embedding(photo_path)
        if query_emb is None:
            print(f"[Recognition] Failed to get embedding for {photo_path}")
            return None

        D, I = index.search(query_emb, k=1)
        print(f"[Recognition] FAISS distances: {D}, indices: {I}")

        if len(I) == 0 or I[0][0] == -1:
            print("[Recognition] FAISS returned no valid indices.")
            return None

        if I[0][0] >= len(metadata):
            print(f"[Recognition] FAISS index {I[0][0]} out of bounds for metadata length {len(metadata)}")
            return None

        match = metadata[I[0][0]]
        print(f"[Recognition] Matched dog: {match}")
        return match

    except Exception as e:
        print(f"[Recognition] Exception in get_dog_by_photo: {e}")
        return None
