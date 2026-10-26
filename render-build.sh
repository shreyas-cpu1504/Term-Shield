#!/usr/bin/env bash
# ==============================================================================
# TermShield Render Build Script
# 
# Installs Tesseract OCR engine, language data, and shared C libraries into a
# local .apt directory, then installs Python requirements. Compatible with both:
#  - Render Root Directory set to "." (repository root)
#  - Render Root Directory set to "backend"
# ==============================================================================
set -e

echo "=== [1/3] Detecting project root and requirements.txt ==="

CURRENT_DIR="$(pwd)"
echo "Current working directory: $CURRENT_DIR"

if [ -f "requirements.txt" ]; then
    REQ_FILE="requirements.txt"
    TARGET_DIR="$CURRENT_DIR"
elif [ -f "backend/requirements.txt" ]; then
    REQ_FILE="backend/requirements.txt"
    TARGET_DIR="$CURRENT_DIR/backend"
else
    echo "ERROR: requirements.txt not found in current directory or backend/!"
    exit 1
fi

echo "Using requirements file: $REQ_FILE"
echo "Target application directory: $TARGET_DIR"

# ==============================================================================
# 2. Install Python Dependencies
# ==============================================================================
echo "=== [2/3] Installing Python dependencies ==="
pip install --upgrade pip
pip install -r "$REQ_FILE"

# ==============================================================================
# 3. Check and Install Tesseract OCR System Dependencies
# ==============================================================================
echo "=== [3/3] Configuring Tesseract OCR system dependency ==="

if command -v tesseract >/dev/null 2>&1; then
    echo "System Tesseract binary detected at: $(which tesseract)"
    tesseract --version
else
    echo "Tesseract not found in system PATH. Installing via non-root package extraction..."

    APT_DIR="$TARGET_DIR/.apt"
    mkdir -p "$APT_DIR"

    # Also link if current directory differs from target directory
    if [ "$CURRENT_DIR" != "$TARGET_DIR" ]; then
        ln -sfn "$APT_DIR" "$CURRENT_DIR/.apt" 2>/dev/null || true
    fi

    TEMP_DIR="$(mktemp -d)"
    cd "$TEMP_DIR"

    echo "Updating package index and downloading packages..."
    apt-get update -o dir::cache="$TEMP_DIR" || true

    PACKAGES=(
        tesseract-ocr
        tesseract-ocr-eng
        tesseract-ocr-osd
        libtesseract5
        libtesseract4
        liblept5
        libgomp1
        libdeflate0
        libwebp7
        libopenjp2-7
        libgif7
        libtiff5
        libjbig0
        libpng16-16
        libjpeg8
        libjpeg-turbo8
    )

    for PKG in "${PACKAGES[@]}"; do
        apt-get download "$PKG" 2>/dev/null || true
    done

    echo "Extracting debian packages into $APT_DIR..."
    COUNT=0
    for deb in *.deb; do
        if [ -f "$deb" ]; then
            dpkg -x "$deb" "$APT_DIR"
            COUNT=$((COUNT + 1))
        fi
    done

    cd "$CURRENT_DIR"
    rm -rf "$TEMP_DIR"

    echo "Extracted $COUNT package(s) into $APT_DIR"
fi

# Verify the tesseract binary location
if [ -f "$TARGET_DIR/.apt/usr/bin/tesseract" ]; then
    echo "Tesseract binary successfully installed to: $TARGET_DIR/.apt/usr/bin/tesseract"
    chmod +x "$TARGET_DIR/.apt/usr/bin/tesseract" 2>/dev/null || true
elif command -v tesseract >/dev/null 2>&1; then
    echo "Tesseract ready at $(which tesseract)"
else
    echo "Note: Tesseract extraction completed; will be resolved dynamically by OCRService."
fi

echo "=== TermShield Build Finished Successfully ==="
