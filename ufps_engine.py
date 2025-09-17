def redact_bytes(data: bytes, filename: str):
    # Temporary fake redactor: just return the original data
    return data, f"redacted_{filename}"
