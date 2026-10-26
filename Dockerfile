# Official Python 3.11 slim image (Debian based)
FROM python:3.11-slim

# Prevent Python from writing .pyc files and buffer stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=10000

# Install Tesseract OCR engine, language data (eng & osd), and all image libraries
# (JPEG, PNG, TIFF, WebP, OpenJPEG, Leptonica) using official Debian apt-get
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-eng \
    tesseract-ocr-osd \
    liblept5 \
    libjpeg62-turbo \
    libpng16-16 \
    libtiff6 \
    libwebp7 \
    libopenjp2-7 \
    libgl1 \
    libglib2.0-0 \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Build-time verification: verify binary execution and available languages
RUN tesseract --version && tesseract --list-langs

WORKDIR /app

# Install Python dependencies from backend/requirements.txt
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy backend application source
COPY backend/ /app/

# Ensure storage directory exists
RUN mkdir -p storage

EXPOSE 10000

# Run uvicorn with 1 worker to conserve RAM within Render's 512 MB limit
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-10000} --workers 1"]
