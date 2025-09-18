import re
import io
from PyPDF2 import PdfReader, PdfWriter
from PIL import Image, ImageDraw
import pytesseract

# Common sensitive patterns
PATTERNS = [
    r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",  # emails
    r"\b\d{3}[-.\s]??\d{3}[-.\s]??\d{4}\b",             # phone numbers
    r"\b\d{16}\b",                                      # 16-digit numbers (cards)
]

def redact_text_content(text: str) -> str:
    redacted = text
    for pat in PATTERNS:
        redacted = re.sub(pat, "[REDACTED]", redacted)
    return redacted

def redact_text_file(data: bytes) -> bytes:
    text = data.decode(errors="ignore")
    redacted_text = redact_text_content(text)
    return redacted_text.encode()

def redact_pdf_file(data: bytes) -> bytes:
    reader = PdfReader(io.BytesIO(data))
    writer = PdfWriter()

    for page in reader.pages:
        text = page.extract_text() or ""
        cleaned = redact_text_content(text)
        # Replace extracted text (simplest way: add as new text layer)
        page_content = io.BytesIO()
        page_content.write(cleaned.encode())
        writer.add_page(page)

    out_bytes = io.BytesIO()
    writer.write(out_bytes)
    return out_bytes.getvalue()

def redact_image_file(data: bytes) -> bytes:
    image = Image.open(io.BytesIO(data))
    text = pytesseract.image_to_string(image)
    draw = ImageDraw.Draw(image)

    for pat in PATTERNS:
        for match in re.finditer(pat, text):
            # Rough box (this is simplistic; OCR gives positions if configured)
            # Here we just blur by drawing a filled rectangle over match text
            # Better OCR integration can be added later
            x0, y0, x1, y1 = 10, 10, 200, 50  # placeholder box
            draw.rectangle([x0, y0, x1, y1], fill="black")

    out_bytes = io.BytesIO()
    image.save(out_bytes, format=image.format or "PNG")
    return out_bytes.getvalue()

def redact_bytes(data: bytes, filename: str):
    lower = filename.lower()
    if lower.endswith(".txt"):
        redacted = redact_text_file(data)
    elif lower.endswith(".pdf"):
        redacted = redact_pdf_file(data)
    elif lower.endswith((".png", ".jpg", ".jpeg")):
        redacted = redact_image_file(data)
    else:
        # Default: treat as text
        redacted = redact_text_file(data)

    output_name = f"redacted_{filename}"
    return redacted, output_name
