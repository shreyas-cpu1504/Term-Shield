#!/usr/bin/env python3
"""
TermShield Tesseract OCR Installer for Render (Linux / Debian / Ubuntu)
Downloads and unpacks Tesseract OCR binary, libraries, and language models
into a local .apt directory for non-root runtime environments.
"""

import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

# Core Jammy packages (Ubuntu 22.04 LTS - Render default)
UBUNTU_PACKAGES = [
    ("tesseract-ocr", "http://archive.ubuntu.com/ubuntu/pool/universe/t/tesseract/tesseract-ocr_4.1.1-2.1build1_amd64.deb"),
    ("libtesseract4", "http://archive.ubuntu.com/ubuntu/pool/universe/t/tesseract/libtesseract4_4.1.1-2.1build1_amd64.deb"),
    ("liblept5", "http://archive.ubuntu.com/ubuntu/pool/universe/l/leptonlib/liblept5_1.82.0-3build1_amd64.deb"),
    ("tesseract-ocr-eng", "http://archive.ubuntu.com/ubuntu/pool/universe/t/tesseract-lang/tesseract-ocr-eng_4.00~git30-7274cfa-1.1_all.deb"),
    ("libgif7", "http://archive.ubuntu.com/ubuntu/pool/main/g/giflib/libgif7_5.1.9-2build2_amd64.deb"),
    ("libopenjp2-7", "http://archive.ubuntu.com/ubuntu/pool/main/o/openjpeg2/libopenjp2-7_2.4.0-6ubuntu0.2_amd64.deb"),
    ("libwebpmux3", "http://archive.ubuntu.com/ubuntu/pool/main/libw/libwebp/libwebpmux3_1.2.2-2ubuntu0.22.04.2_amd64.deb"),
]

DIRECT_TRAINEDDATA_URLS = [
    ("eng.traineddata", "https://raw.githubusercontent.com/tesseract-ocr/tessdata_fast/main/eng.traineddata"),
    ("osd.traineddata", "https://raw.githubusercontent.com/tesseract-ocr/tessdata_fast/main/osd.traineddata"),
]


def download_file(url: str, dest_path: Path, timeout: int = 30) -> bool:
    """Download a file with user-agent headers and error handling."""
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "TermShield-Build/1.0 (Render; Linux x86_64)"},
    )
    try:
        print(f"  Downloading: {dest_path.name} from {url}...")
        with urllib.request.urlopen(req, timeout=timeout) as response, open(dest_path, "wb") as out_file:
            shutil.copyfileobj(response, out_file)
        return True
    except Exception as exc:
        print(f"  Warning: Failed to download {url}: {exc}")
        return False


def extract_deb(deb_file: Path, target_dir: Path) -> bool:
    """Extract a .deb file into target directory using dpkg-deb, ar, or tar."""
    if shutil.which("dpkg-deb"):
        res = subprocess.run(["dpkg-deb", "-x", str(deb_file), str(target_dir)], capture_output=True, text=True)
        if res.returncode == 0:
            return True
        print(f"  dpkg-deb error for {deb_file.name}: {res.stderr.strip()}")

    if shutil.which("dpkg"):
        res = subprocess.run(["dpkg", "-x", str(deb_file), str(target_dir)], capture_output=True, text=True)
        if res.returncode == 0:
            return True
        print(f"  dpkg error for {deb_file.name}: {res.stderr.strip()}")

    # Pure Python fallback using ar / tarfile
    try:
        import tarfile

        with open(deb_file, "rb") as f:
            data = f.read()

        # Find data.tar archive inside ar archive
        for ext in (b"data.tar.xz", b"data.tar.gz", b"data.tar.zst", b"data.tar.bz2"):
            idx = data.find(ext)
            if idx != -1:
                # Seek to header line end
                header_end = data.find(b"\n", idx)
                if header_end != -1:
                    raw_tar = data[header_end + 1 :]
                    with tempfile.NamedTemporaryFile(suffix=ext.decode("ascii", "ignore"), delete=False) as tf:
                        tf.write(raw_tar)
                        tf_path = Path(tf.name)
                    try:
                        with tarfile.open(tf_path) as tar:
                            tar.extractall(path=target_dir)
                        tf_path.unlink(missing_ok=True)
                        return True
                    except Exception:
                        tf_path.unlink(missing_ok=True)
    except Exception as exc:
        print(f"  Fallback extraction failed for {deb_file.name}: {exc}")

    return False


def create_tesseract_wrapper(apt_dir: Path) -> Path:
    """
    Create a robust wrapper script at .apt/usr/bin/tesseract that automatically
    sets LD_LIBRARY_PATH and TESSDATA_PREFIX before executing the real binary.
    """
    bin_dir = apt_dir / "usr" / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)

    real_bin = bin_dir / "tesseract-bin"
    installed_bin = bin_dir / "tesseract"

    # If tesseract already exists and is an ELF binary (not a wrapper), rename it to tesseract-bin
    if installed_bin.is_file() and not real_bin.exists():
        with open(installed_bin, "rb") as f:
            header = f.read(4)
        if header.startswith(b"\x7fELF"):
            installed_bin.rename(real_bin)
        elif header.startswith(b"#!/"):
            # Already a script
            pass

    wrapper_content = """#!/usr/bin/env bash
# TermShield Auto-Configuring Tesseract Wrapper
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Add vendor shared libraries to dynamic linker search path
export LD_LIBRARY_PATH="$APT_ROOT/usr/lib/x86_64-linux-gnu:$APT_ROOT/usr/lib:$APT_ROOT/lib/x86_64-linux-gnu:$APT_ROOT/lib:$LD_LIBRARY_PATH"

# Resolve TESSDATA_PREFIX dynamically if unset
if [ -z "$TESSDATA_PREFIX" ]; then
    for candidate in "$APT_ROOT/usr/share/tesseract-ocr/4.00/tessdata" "$APT_ROOT/usr/share/tesseract-ocr/5/tessdata" "$APT_ROOT/usr/share/tessdata"; do
        if [ -d "$candidate" ] && [ -f "$candidate/eng.traineddata" ]; then
            export TESSDATA_PREFIX="$candidate"
            break
        fi
    done
fi

TARGET_BIN="$SCRIPT_DIR/tesseract-bin"
if [ ! -f "$TARGET_BIN" ]; then
    TARGET_BIN="$SCRIPT_DIR/tesseract"
fi

exec "$TARGET_BIN" "$@"
"""

    installed_bin.write_text(wrapper_content, encoding="utf-8")
    installed_bin.chmod(0o755)
    if real_bin.is_file():
        real_bin.chmod(0o755)

    return installed_bin


def main():
    target_root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd().resolve()
    print(f"=== Installing Tesseract OCR into: {target_root} ===")

    # If system tesseract is already functional, verify and return
    sys_tesseract = shutil.which("tesseract")
    if sys_tesseract and not any(".apt" in p for p in Path(sys_tesseract).parts):
        try:
            ver_check = subprocess.run([sys_tesseract, "--version"], capture_output=True, text=True, check=True)
            print(f"System Tesseract is already installed and working: {sys_tesseract}")
            print(f"  {ver_check.stdout.splitlines()[0] if ver_check.stdout else ''}")
            return 0
        except Exception as exc:
            print(f"System Tesseract found at {sys_tesseract} but check failed ({exc}). Installing local vendor...")

    apt_dir = target_root / ".apt"
    apt_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as temp_dir_str:
        temp_dir = Path(temp_dir_str)

        # 1. Download and extract Ubuntu deb packages
        for pkg_name, deb_url in UBUNTU_PACKAGES:
            deb_filename = deb_url.split("/")[-1]
            deb_path = temp_dir / deb_filename
            if download_file(deb_url, deb_path):
                print(f"  Extracting {deb_filename} into {apt_dir}...")
                extract_deb(deb_path, apt_dir)

        # 2. Ensure traineddata files exist in standard directories
        tessdata_dirs = [
            apt_dir / "usr" / "share" / "tesseract-ocr" / "4.00" / "tessdata",
            apt_dir / "usr" / "share" / "tesseract-ocr" / "5" / "tessdata",
            apt_dir / "usr" / "share" / "tessdata",
        ]
        for td in tessdata_dirs:
            td.mkdir(parents=True, exist_ok=True)

        for filename, td_url in DIRECT_TRAINEDDATA_URLS:
            primary_target = tessdata_dirs[0] / filename
            if not primary_target.is_file() or primary_target.stat().st_size == 0:
                download_file(td_url, primary_target)
            # Copy to other candidate directories for seamless compatibility
            if primary_target.is_file():
                for alt_td in tessdata_dirs[1:]:
                    alt_target = alt_td / filename
                    if not alt_target.is_file():
                        shutil.copy2(primary_target, alt_target)

    # 3. Create wrapper script
    wrapper = create_tesseract_wrapper(apt_dir)
    print(f"Configured wrapper script: {wrapper}")

    # 4. Verify binary execution
    test_env = os.environ.copy()
    test_env["PATH"] = f"{apt_dir / 'usr' / 'bin'}:{test_env.get('PATH', '')}"
    test_env["LD_LIBRARY_PATH"] = f"{apt_dir / 'usr' / 'lib' / 'x86_64-linux-gnu'}:{apt_dir / 'usr' / 'lib'}:{test_env.get('LD_LIBRARY_PATH', '')}"
    test_env["TESSDATA_PREFIX"] = str(apt_dir / "usr" / "share" / "tesseract-ocr" / "4.00" / "tessdata")

    try:
        cmd = str(apt_dir / "usr" / "bin" / "tesseract")
        res = subprocess.run([cmd, "--version"], capture_output=True, text=True, env=test_env, timeout=10)
        if res.returncode == 0:
            print(f"=== Verification SUCCESS: {cmd} ===")
            print(f"Output: {res.stdout.strip()}")
            return 0
        else:
            print(f"=== Verification FAILED with exit code {res.returncode} ===")
            print(f"STDOUT: {res.stdout.strip()}")
            print(f"STDERR: {res.stderr.strip()}")
            # Do not exit with 1 if running on non-Linux (e.g. during local Windows builds)
            if sys.platform != "linux":
                print("Note: Non-Linux platform detected during verification. Continuing.")
                return 0
            return 1
    except Exception as exc:
        print(f"Verification exception: {exc}")
        if sys.platform != "linux":
            return 0
        return 1


if __name__ == "__main__":
    sys.exit(main())
