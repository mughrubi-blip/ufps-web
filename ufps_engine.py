import re, io
from typing import Tuple
import fitz  # PyMuPDF
from PIL import Image, ImageDraw
import pytesseract
from pytesseract import Output

import re, io
from typing import Tuple
import fitz  # PyMuPDF
from PIL import Image, ImageDraw
import pytesseract
from pytesseract import Output

pytesseract.pytesseract.tesseract_cmd = "/usr/bin/tesseract"

# Compile sensitive patterns (add more as needed)
PATTERNS = [
    r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",   # emails
    r"\b\d{3}[-.\s]??\d{3}[-.\s]??\d{4}\b",              # phone numbers
    r"\b\d{16}\b",                                       # 16-digit numbers
]
REGEXES = [re.compile(p, re.I) for p in PATTERNS]
MASK = "[REDACTED]"

def _redact_text_content(text: str) -> str:
    out = text
    for rgx in REGEXES:
        out = rgx.sub(MASK, out)
    return out

# ---------- TXT ----------
def _redact_txt(data: bytes) -> bytes:
    text = data.decode(errors="ignore")
    return _redact_text_content(text).encode()

# ---------- PDF (PyMuPDF search via line unions) ----------
def _redact_pdf(data: bytes) -> bytes:
    doc = fitz.open(stream=data, filetype="pdf")

    for page in doc:
        words = page.get_text("words")  # (x0,y0,x1,y1, word, block, line, word_no)
        # Group words by (block,line) -> reconstruct line text + union bbox
        lines = {}
        for x0, y0, x1, y1, w, blk, ln, wno in words:
            key = (blk, ln)
            lines.setdefault(key, {"text": [], "boxes": []})
            lines[key]["text"].append(w)
            lines[key]["boxes"].append((x0, y0, x1, y1))

        # For each line, if regex matches, add a black redaction box over union of its words
        for info in lines.values():
            line_text = " ".join(info["text"])
            if any(r.search(line_text) for r in REGEXES):
                xs0 = min(b[0] for b in info["boxes"])
                ys0 = min(b[1] for b in info["boxes"])
                xs1 = max(b[2] for b in info["boxes"])
                ys1 = max(b[3] for b in info["boxes"])
                page.add_redact_annot(fitz.Rect(xs0, ys0, xs1, ys1), fill=(0, 0, 0))

        page.apply_redactions()

    out = io.BytesIO()
    doc.save(out, deflate=True, clean=True)
    doc.close()
    return out.getvalue()

# ---------- IMAGES (OCR lines; redact any line that matches) ----------
def _redact_image(data: bytes) -> bytes:
    image = Image.open(io.BytesIO(data)).convert("RGB")
    ocr = pytesseract.image_to_data(image, output_type=Output.DICT, lang="eng")

    draw = ImageDraw.Draw(image)
    # Group by line: (block_num, par_num, line_num)
    lines = {}
    n = len(ocr["text"])
    for i in range(n):
        if int(ocr.get("conf", ["-1"])[i]) < 0:  # skip invalid
            continue
        txt = (ocr["text"][i] or "").strip()
        if not txt:
            continue
        key = (ocr["block_num"][i], ocr["par_num"][i], ocr["line_num"][i])
        x, y, w, h = ocr["left"][i], ocr["top"][i], ocr["width"][i], ocr["height"][i]
        lines.setdefault(key, {"text": [], "boxes": []})
        lines[key]["text"].append(txt)
        lines[key]["boxes"].append((x, y, x + w, y + h))

    for info in lines.values():
        line_text = " ".join(info["text"])
        if any(r.search(line_text) for r in REGEXES):
            x0 = min(b[0] for b in info["boxes"])
            y0 = min(b[1] for b in info["boxes"])
            x1 = max(b[2] for b in info["boxes"])
            y1 = max(b[3] for b in info["boxes"])
            draw.rectangle([x0, y0, x1, y1], fill="black")

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
        # default: treat as text
        redacted = _redact_txt(data)

    return redacted, f"redacted_{filename}"
