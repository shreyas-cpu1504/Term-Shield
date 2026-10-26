#!/usr/bin/env bash
# ==============================================================================
# TermShield Build Script
# Compatible with both native and Docker build verification.
# ==============================================================================
set -e

echo "=== [1/2] Installing Python dependencies ==="

CURRENT_DIR="$(pwd)"

if [ -f "requirements.txt" ]; then
    REQ_FILE="requirements.txt"
elif [ -f "backend/requirements.txt" ]; then
    REQ_FILE="backend/requirements.txt"
else
    echo "ERROR: requirements.txt not found!"
    exit 1
fi

echo "Installing requirements from: $REQ_FILE"
pip install --upgrade pip
pip install -r "$REQ_FILE"

echo "=== [2/2] Checking Tesseract OCR system dependencies ==="
if command -v tesseract >/dev/null 2>&1; then
    echo "Tesseract engine detected:"
    tesseract --version
    tesseract --list-langs
else
    echo "Note: Tesseract not found in current shell PATH. In production on Render, deploy using Docker runtime (Dockerfile) where Tesseract is installed natively via apt-get."
fi

echo "=== Build Step Completed Successfully ==="
