import os
import numpy as np
import torch
import torchvision.models as models
import torchvision.transforms as T
import faiss
from supabase import create_client, Client
from PIL import Image
import io

from dotenv import load_dotenv
import os

# --- Load environment variables ---
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
BUCKET_NAME = "kas.dogs"  # your bucket name

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- Load ResNet50 once ---
_model = models.resnet50(weights=models.ResNet50_Weights.DEFAULT)
_model.fc = torch.nn.Identity()  # remove classification head
_model.eval()

# --- Image transforms ---
_transform = T.Compose([
    T.Resize((224, 224)),
    T.ToTensor(),
    T.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
])

def get_embedding(img):
    img_tensor = _transform(img).unsqueeze(0)
    with torch.no_grad():
        emb = _model(img_tensor).numpy()
    return emb.squeeze()

def list_all_files(path=""):
    """Recursively list all files in a Supabase bucket, with correct paths."""
    all_files = []
    items = supabase.storage.from_(BUCKET_NAME).list(path)

    for item in items:
        # If item has no id → it's a folder
        if item.get("id") is None:
            sub_path = f"{path}{item['name']}" if path == "" else f"{path}/{item['name']}"
            all_files.extend(list_all_files(sub_path))
        else:
            # Build full path
            file_path = f"{path}/{item['name']}" if path else item["name"]
            all_files.append(file_path)

    return all_files

def get_image_from_supabase(file_path):
    """Download image from Supabase and return PIL.Image"""
    response = supabase.storage.from_(BUCKET_NAME).download(file_path)
    data = io.BytesIO(response)
    return Image.open(data).convert("RGB")

if __name__ == "__main__":
    files = list_all_files()
    for f in files[:20]:
        print("Found file:", f)

def build_index_from_supabase():
    print("Listing all images in Supabase bucket...")
    file_list = list_all_files()
    if not file_list:
        print("No images found.")
        return None, None

    embeddings, labels = [], []
    for file_path in file_list:
        try:
            img = get_image_from_supabase(file_path)
            emb = get_embedding(img)
            embeddings.append(emb)
            labels.append(file_path.split("/")[0])
        except Exception as e:
            print(f"Skipping {file_path}: {e}")

    embeddings = np.vstack(embeddings).astype("float32")
    index = faiss.IndexFlatL2(embeddings.shape[1])
    index.add(embeddings)

    # Save index + labels
    faiss.write_index(index, "dog_index.faiss")
    np.save("dog_labels.npy", np.array(labels))
    
    print(f"✅ Built FAISS index with {len(labels)} images.")
    return index, labels

if __name__ == "__main__":
    build_index_from_supabase()
