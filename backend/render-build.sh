#!/usr/bin/env bash
# ==============================================================================
# TermShield Render Build Script
# 
# Installs Tesseract OCR engine, language data, and shared C libraries into a
# local .apt directory, then installs Python requirements. Compatible with both:
#  - Render Root Directory set to "backend" (cwd: /opt/render/project/src/backend)
#  - Render Root Directory set to "." (cwd: /opt/render/project/src)
# ==============================================================================
set -e

echo "=== [1/3] Detecting project root and installing Python dependencies ==="

CURRENT_DIR="$(pwd)"
echo "Current build directory: $CURRENT_DIR"

if [ -f "requirements.txt" ]; then
    REQ_FILE="requirements.txt"
    TARGET_DIR="$CURRENT_DIR"
elif [ -f "backend/requirements.txt" ]; then
    REQ_FILE="backend/requirements.txt"
    TARGET_DIR="$CURRENT_DIR/backend"
else
    echo "ERROR: requirements.txt not found!"
    exit 1
fi

echo "Requirements file: $REQ_FILE"
echo "Target directory: $TARGET_DIR"

pip install --upgrade pip
pip install -r "$REQ_FILE"

echo "=== [2/3] Installing Tesseract OCR system dependencies ==="

if [ -f "scripts/install_tesseract_render.py" ]; then
    python scripts/install_tesseract_render.py "$TARGET_DIR"
elif [ -f "backend/scripts/install_tesseract_render.py" ]; then
    python backend/scripts/install_tesseract_render.py "$TARGET_DIR"
else
    echo "Warning: install_tesseract_render.py not found, checking existing binaries..."
fi

echo "=== [3/3] Verifying Tesseract runtime and startup diagnostics ==="

python -c "
import sys
from app.services.ocr_service import OCRService
OCRService.log_startup_diagnostics()
diag = OCRService.get_diagnostics()
if sys.platform == 'linux' and not diag['is_available']:
    print('FATAL: Tesseract is not available after build!')
    sys.exit(1)
print('Tesseract verification complete. Status is_available:', diag['is_available'])
"

echo "=== TermShield Render Build Completed Successfully ==="
