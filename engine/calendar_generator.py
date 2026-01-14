import os
from io import BytesIO
from PIL import Image
import google.generativeai as genai
from dotenv import load_dotenv

# -------------------------------------------------
# Environment & Gemini setup
# -------------------------------------------------
load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise RuntimeError("GOOGLE_API_KEY not found in environment")

genai.configure(api_key=GOOGLE_API_KEY)

model = genai.GenerativeModel(
    "models/gemini-3-pro-image-preview"
)

# -------------------------------------------------
# Calendar assets
# -------------------------------------------------
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
CALENDAR_DIR = os.path.join(BASE_DIR, "assets", "calendar_templates")

MONTHS = [
    "January", "February", "March", "April",
    "May", "June", "July", "August",
    "September", "October", "November", "December"
]

TEMPLATE_FILES = {
    "January": "Jan.jpg",
    "February": "Feb.jpg",
    "March": "Mar.jpg",
    "April": "Apr.jpg",
    "May": "May.jpg",
    "June": "Jun.jpg",
    "July": "Jul.jpg",
    "August": "Aug.jpg",
    "September": "Sep.jpg",
    "October": "Oct.jpg",
    "November": "Nov.jpg",
    "December": "Dec.jpg",
}

# 🔒 EXACT crop boxes (unchanged)
CROP_BOXES = {
    "January":   (600, 130, 970, 875),
    "February":  (600, 130, 1050, 875),
    "March":     (590, 110, 1080, 875),
    "April":     (550, 130, 1000, 875),
    "May":       (550, 140, 1070, 875),
    "June":      (650, 125, 1060, 875),
    "July":      (640, 185, 1000, 875),
    "August":    (640, 160, 1050, 875),
    "September": (640, 170, 1020, 875),
    "October":   (520, 110, 1020, 875),
    "November":  (630, 160, 1050, 875),
    "December":  (660, 130, 1050, 875),
}

# -------------------------------------------------
# Internal single-month generator
# -------------------------------------------------
def _generate_month(calendar_img: Image.Image, partner_img: Image.Image, month: str) -> Image.Image:
    crop = CROP_BOXES[month]

    instruction = f"""
Replace only the person located inside this rectangle:
Top-left: ({crop[0]}, {crop[1]})
Bottom-right: ({crop[2]}, {crop[3]})

Make the person resemble the partner in the reference photo.
Keep pose, body position, skin tone, clothing style, and illustration style consistent.

Do not change calendar layout, dates, text, background, colors, or framing.
"""

    response = model.generate_content([
        instruction,
        calendar_img,
        partner_img
    ])

    for part in response.candidates[0].content.parts:
        if hasattr(part, "inline_data"):
            return Image.open(BytesIO(part.inline_data.data)).convert("RGB")

    raise RuntimeError(f"No image returned for {month}")

# -------------------------------------------------
# Public APIs
# -------------------------------------------------
def generate_calendar_with_templates(partner_image: Image.Image) -> dict:
    results = {}
    for month in MONTHS:
        template = os.path.join(CALENDAR_DIR, TEMPLATE_FILES[month])
        calendar_img = Image.open(template).convert("RGB")
        results[month] = _generate_month(calendar_img, partner_image, month)
    return results


def regenerate_single_month(partner_image: Image.Image, month: str) -> Image.Image:
    template = os.path.join(CALENDAR_DIR, TEMPLATE_FILES[month])
    calendar_img = Image.open(template).convert("RGB")
    return _generate_month(calendar_img, partner_image, month)
