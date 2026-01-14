import os
from PIL import Image

OUTPUT_ROOT = "calendar_outputs"


def sanitize_name(name: str) -> str:
    """
    Make a filesystem-safe folder name.
    """
    return name.strip().replace(" ", "_")


def save_calendar_images(partner_name: str, images: dict):
    """
    Save calendar images to:
    calendar_outputs/<partner_name>/<month>.jpg
    """
    safe_name = sanitize_name(partner_name)
    partner_dir = os.path.join(OUTPUT_ROOT, safe_name)

    os.makedirs(partner_dir, exist_ok=True)

    for month, img in images.items():
        file_path = os.path.join(partner_dir, f"{month}.jpg")
        img.save(file_path, format="JPEG", quality=95)

    return partner_dir
