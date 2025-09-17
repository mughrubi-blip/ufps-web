import re

# Simple redaction engine
def redact_bytes(data: bytes, filename: str):
    text = data.decode(errors="ignore")

    # Patterns to redact (you can add more)
    patterns = [
        r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",  # emails
        r"\b\d{3}[-.\s]??\d{3}[-.\s]??\d{4}\b",             # phone numbers
        r"\b\d{16}\b",                                      # 16-digit card numbers
    ]

    redacted_text = text
    for pat in patterns:
        redacted_text = re.sub(pat, "[REDACTED]", redacted_text)

    # Convert back to bytes
    redacted_bytes = redacted_text.encode()

    output_name = f"redacted_{filename}"
    return redacted_bytes, output_name
