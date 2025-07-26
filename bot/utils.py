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
    if not dog_data:
        return None

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

    try:
        font = ImageFont.truetype("arial.ttf", font_size)
    except:
        font = ImageFont.load_default()

    # Extra space at the top for the caption/empty line
    top_margin = font_size + 20  # adjust space height here

    collage_width = cols * cell_width
    collage_height = rows * (cell_height + font_size + 10) + top_margin

    collage = Image.new("RGB", (collage_width, collage_height), color="white")
    draw = ImageDraw.Draw(collage)

    # Draw empty line or caption text at the top (if you want it empty, just skip this)
    # For example, to add a blank line, just do nothing here.
    # Or to add text:
    # caption_text = "Dogs filtered by ..."
    # w, h = draw.textsize(caption_text, font=font)
    # draw.text(((collage_width - w) / 2, top_margin // 2 - h // 2), caption_text, fill="black", font=font)

    for idx, (img, name) in enumerate(images):
        img.thumbnail(cell_size, Image.LANCZOS)

        x = (idx % cols) * cell_width + (cell_width - img.width) // 2
        y = top_margin + (idx // cols) * (cell_height + font_size + 10)

        collage.paste(img, (x, y))

        name_width = draw.textlength(name, font=font)
        text_x = (idx % cols) * cell_width + (cell_width - name_width) // 2
        text_y = y + img.height + 5
        draw.text((text_x, text_y), name, fill="black", font=font)

    temp_dir = os.getenv("TEMP") or "/tmp"
    out_path = os.path.join(temp_dir, f"{collage_name.replace(' ', '_')}.jpg")
    collage.save(out_path, format="JPEG")
    return out_path
