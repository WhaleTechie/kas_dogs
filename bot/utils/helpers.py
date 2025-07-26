import re
import os
import tempfile
from PIL import Image, ImageDraw, ImageFont

def escape_md(text: str) -> str:
    return re.sub(r'([_\*\[\]()~`>#+\-=|{}.!])', r'\\\1', str(text))

def clean_text(text: str) -> str:
    return text.encode("utf-16", "surrogatepass").decode("utf-16", "ignore")

def escape_md(text: str) -> str:
    """
    Escapes Markdown V2 special characters for Telegram messages.
    """
    if not text:
        return ""
    return re.sub(r'([_*[\]()~`>#+-=|{}.!])', r'\\\1', text)

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

def create_placeholder_image(text, size=(350, 300)):
    img = Image.new("RGB", size, color="white")
    draw = ImageDraw.Draw(img)
    font_size = 30
    try:
        font = ImageFont.truetype("arial.ttf", font_size)
    except:
        font = ImageFont.load_default()

    no_photo_text = "No photo"
    bbox = draw.textbbox((0, 0), no_photo_text, font=font)
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]
    draw.text(((size[0] - w) / 2, size[1] // 4 - h // 2), no_photo_text, fill="gray", font=font)

    bbox = draw.textbbox((0, 0), text, font=font)
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]
    draw.text(((size[0] - w) / 2, size[1] * 3 // 4 - h // 2), text, fill="black", font=font)

    temp_path = os.path.join(tempfile.gettempdir(), f"placeholder_{text.replace(' ', '_')}.jpg")
    img.save(temp_path)
    return temp_path
