import re, io
from typing import Tuple
import fitz  # PyMuPDF
from PIL import Image, ImageDraw
import pytesseract
from pytesseract import Output

# Point to tesseract in Docker
pytesseract.pytesseract.tesseract_cmd = "/usr/bin/tesseract"

# Patterns
PATTERNS = [
    r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",   # emails
    r"\+?\d[\d\-\s()]{6,}\d",                             # broad phone
    r"\b(?:\d[ -]?){13,19}\b",                            # 13-19 digits (cards)
]
REGEXES = [re.compile(p, re.I) for p in PATTERNS]
MASK = "[REDACTED]"

def _match_any(s: str) -> bool:
    return any(r.search(s) for r in REGEXES)

# ---------- TXT ----------
def _redact_txt(data: bytes) -> bytes:
    text = data.decode(errors="ignore")
    for r in REGEXES:
        text = r.sub(MASK, text)
    return text.encode()

# ---------- PDF (word-level boxes) ----------
def _redact_pdf(data: bytes) -> bytes:
    doc = fitz.open(stream=data, filetype="pdf")
    for page in doc:
        words = page.get_text("words")  # (x0,y0,x1,y1, word, block, line, word_no)
        for x0, y0, x1, y1, w, *_ in words:
            if _match_any(w):
                page.add_redact_annot(fitz.Rect(x0, y0, x1, y1), fill=(0, 0, 0))
        page.apply_redactions()
    out = io.BytesIO()
    doc.save(out, deflate=True, clean=True)
    doc.close()
    return out.getvalue()

# ---------- IMAGES (word-level boxes with OCR) ----------
def _redact_image(data: bytes) -> bytes:
    image = Image.open(io.BytesIO(data)).convert("RGB")
    # OCR per-word with sane defaults
    ocr = pytesseract.image_to_data(
        image, output_type=Output.DICT, lang="eng",
        config="--oem 3 --psm 6"
    )
    draw = ImageDraw.Draw(image)
    n = len(ocr["text"])
    for i in range(n):
        txt = (ocr["text"][i] or "").strip()
        if not txt:
            continue
        # Some OCR tokens split emails; quick join: if token has '@' or looks numeric, treat it
        if _match_any(txt) or "@" in txt or sum(c.isdigit() for c in txt) >= 6:
            x, y, w, h = ocr["left"][i], ocr["top"][i], ocr["width"][i], ocr["height"][i]
            # pad a bit
            pad = 2
            draw.rectangle([x - pad, y - pad, x + w + pad, y + h + pad], fill="black")

    out = io.BytesIO()
    image.save(out, format="PNG")
    return out.getvalue()

# ---------- Entry ----------
def redact_bytes(data: bytes, filename: str) -> Tuple[bytes, str]:
    name = filename.lower().strip()
    if name.endswith(".txt"):
        redacted = _redact_txt(data)
    elif name.endswith(".pdf"):
        redacted = _redact_pdf(data)
    elif name.endswith((".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".webp")):
        redacted = _redact_image(data)
    else:
        redacted = _redact_txt(data)
    return redacted, f"redacted_{filename}"
