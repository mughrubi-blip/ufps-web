FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive
# Install system deps for OCR, PDF rasterization, and Pillow runtime libs
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-eng \
    libtesseract-dev \
    poppler-utils \
    libjpeg62-turbo \
    zlib1g \
    libpng16-16 \
    libfreetype6 \
    libopenjp2-7 \
    libtiff6 \
    build-essential \
 && rm -rf /var/lib/apt/lists/*

# Workdir
WORKDIR /app

# Copy project
COPY . /app

# Python deps
RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8000
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
