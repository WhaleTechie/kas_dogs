### Updated recognition.py
import os
import sqlite3
import torch
from torchvision import models, transforms
from PIL import Image
import numpy as np
import pickle
from supabase import create_client

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

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_dog_by_photo(file_path: str) -> dict:
    try:
        # Expecting file named like 'dogid_filename.jpg'
        filename = os.path.basename(file_path)
        dog_id = filename.split('_')[0]

        response = supabase.table("dogs").select("*").eq("id", dog_id).single().execute()

        if response.data:
            dog = response.data
            dog["photo_path"] = file_path
            return dog
        else:
            print(f"[WARN] No dog found for ID: {dog_id}")
            return {}
    except Exception as e:
        print(f"[ERROR] Fetching dog by photo: {e}")
        return {}
