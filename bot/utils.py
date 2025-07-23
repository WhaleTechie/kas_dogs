# bot/utils.py

import re
from PIL import Image, ImageDraw, ImageFont
import os

def escape_md(text: str) -> str:
    """
    Escapes Markdown V2 special characters for Telegram messages.
    """
    if not text:
        return ""
    return re.sub(r'([_*[\]()~`>#+-=|{}.!])', r'\\\1', text)

def get_dog_by_photo(file_path: str) -> dict:
    """
    Dummy function that should be replaced with your actual dog recognition logic.
    """
    # Placeholder: replace with actual recognition logic
    return {
        "name": "Buddy",
        "category": "street",
        "pen": "",
        "sector": "",
        "status": "Healthy",
        "description": "Loves attention and chasing butterflies.",
        "photo_path": file_path,
    }

def create_collage(dog_data, collage_name="Dogs Collage", cell_size=(350, 300), cols=4):
    """
    dog_data: list of tuples (image_path, dog_name)
    """
    if not dog_data:
        return None

    # Load all images and prepare names
    images = []
    for path, name in dog_data:
        try:
            img = Image.open(path).convert("RGB")
            images.append((img, name))
        except Exception as e:
            print(f"[ERROR] Opening image {path}: {e}")

    rows = (len(images) + cols - 1) // cols
    cell_width, cell_height = cell_size
    font_size = 24

    # Load a basic font
    try:
        font = ImageFont.truetype("arial.ttf", font_size)
    except:
        font = ImageFont.load_default()

    collage_width = cols * cell_width
    collage_height = rows * (cell_height + font_size + 10)

    collage = Image.new("RGB", (collage_width, collage_height), color="white")
    draw = ImageDraw.Draw(collage)

    for idx, (img, name) in enumerate(images):
        # Resize image proportionally
        img.thumbnail(cell_size, Image.LANCZOS)

        x = (idx % cols) * cell_width + (cell_width - img.width) // 2
        y = (idx // cols) * (cell_height + font_size + 10)

        collage.paste(img, (x, y))

        # Draw name centered
        name_width = draw.textlength(name, font=font)
        text_x = (idx % cols) * cell_width + (cell_width - name_width) // 2
        text_y = y + img.height + 5
        draw.text((text_x, text_y), name, fill="black", font=font)

    # Save to temp file
    temp_dir = os.getenv("TEMP") or "/tmp"
    out_path = os.path.join(temp_dir, f"{collage_name.replace(' ', '_')}.jpg")
    collage.save(out_path, format="JPEG")
    return out_path
