# bot/utils.py

import re

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
