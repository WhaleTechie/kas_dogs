# build_index.py
import os
import numpy as np
import torch
import torchvision.models as models
import torchvision.transforms as T
from PIL import Image
import faiss

# --- Model ---
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
resnet = models.resnet18(pretrained=True)
resnet.fc = torch.nn.Identity()
resnet = resnet.to(device).eval()

transform = T.Compose([
    T.Resize((224, 224)),
    T.ToTensor(),
    T.Normalize(mean=[0.485, 0.456, 0.406],
                std=[0.229, 0.224, 0.225]),
])

def get_embedding(img_path: str) -> np.ndarray:
    img = Image.open(img_path).convert("RGB")
    tensor = transform(img).unsqueeze(0).to(device)
    with torch.no_grad():
        emb = resnet(tensor).cpu().numpy()
    return emb.astype("float32")

# --- Build index ---
embeddings = []
metadata = []  # stores {id, category, name}

root = "dogs_dataset"  # local root with subfolders like 0001/, 0002/
for folder in os.listdir(root):
    folder_path = os.path.join(root, folder)
    if not os.path.isdir(folder_path):
        continue
    for fname in os.listdir(folder_path):
        if not fname.lower().endswith((".jpg", ".jpeg", ".png")):
            continue

        img_path = os.path.join(folder_path, fname)
        emb = get_embedding(img_path)
        embeddings.append(emb)

        dog_id = folder  # folder name is ID (e.g. "0001")
        name = os.path.splitext(fname)[0]

        metadata.append({
            "id": dog_id,        # instead of local path
            "category": folder,  # category = folder (can be refined later)
            "name": name,        # filename without extension
        })

# --- Save index ---
emb_matrix = np.vstack(embeddings)
index = faiss.IndexFlatL2(emb_matrix.shape[1])
index.add(emb_matrix)

faiss.write_index(index, "dog_index.faiss")
np.save("dogs.npy", metadata)
print(f"✅ Saved {len(metadata)} embeddings")
