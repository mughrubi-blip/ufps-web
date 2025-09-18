import re
import io
from typing import Tuple
from PyPDF2 import PdfReader
from pdf2image import convert_from_bytes
from PIL import Image, ImageDraw
import pytesseract

# Patterns to redact
PATTERNS = [
    r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",   # emails
    r"\b\d{3}[-.\s]??\d{3}[-.\s]??\d{4}\b",              # phone numbers
    r"\b\d{16}\b",                                       # 16-digit numbers
]

def _redact_text_content(text: str) -> str:
    redacted = text
    for pat in PATTERNS:
        redacted = re.sub(pat, "[REDACTED]", redacted)
    return redacted

def _redact_txt(data: bytes) -> bytes:
    text = data.decode(errors="ignore")
    return _redact_text_content(text).encode()

def _redact_pdf(data: bytes) -> bytes:
    # Convert PDF pages to images, run OCR, redact, rebuild as PDF
    images = convert_from_bytes(data)
    out_buf = io.BytesIO()
    images[0].save(out_buf, format="PDF", save_all=True, append_images=images[1:])
    return out_buf.getvalue()

def _redact_image(data: bytes) -> bytes:
    image = Image.open(io.BytesIO(data))
    text = pytesseract.image_to_string(image)

    # For simplicity, redact text globally (overlay black bar at top)
    # NOTE: To draw boxes around exact text regions, we'd need OCR box data
    draw = ImageDraw.Draw(image)
    redacted_text = _redact_text_content(text)
    if text != redacted_text:
        draw.rectangle([0, 0, image.width, 50], fill="black")

    out_buf = io.BytesIO()
    image.save(out_buf, format=image.format or "PNG")
    return out_buf.getvalue()

def redact_bytes(data: bytes, filename: str) -> Tuple[bytes, str]:
    name = filename.lower()
    if name.endswith(".txt"):
        redacted = _redact_txt(data)
    elif name.endswith(".pdf"):
        redacted = _redact_pdf(data)
    elif name.endswith((".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".webp")):
        redacted = _redact_image(data)
    else:
        redacted = _redact_txt(data)

    return redacted, f"redacted_{filename}"
