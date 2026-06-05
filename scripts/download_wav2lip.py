#!/usr/bin/env python3
"""
Download the Wav2Lip model checkpoint (wav2lip.pth) to the correct location.

Run from project root:
    python scripts/download_wav2lip.py

The Wav2Lip checkpoint is ~155 MB. This script tries multiple mirrors
and falls back to manual instructions if all fail.
"""
import os
import sys
import shutil
import urllib.request

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
DEST = os.path.join(PROJECT_ROOT, "backend", "models", "wav2lip.pth")

# Known direct-download URLs (tried in order)
URLS = [
    # HuggingFace mirror (most reliable)
    "https://huggingface.co/spaces/ziqiaoqiao/Wav2Lip/resolve/main/checkpoints/wav2lip.pth",
    # Alternative HF mirror
    "https://huggingface.co/spaces/akhaliq/wav2lip/resolve/main/checkpoints/wav2lip.pth",
    # Google Drive direct (may be rate-limited)
    # Note: gdown is needed for GDrive; we skip direct GDrive here
]


def download_with_progress(url, dest):
    """Download a file with a simple progress indicator."""
    print(f"  [DOWNLOAD] {url}")
    tmp = dest + ".tmp"
    try:
        # Use urllib with a callback for progress
        def report(block_num, block_size, total_size):
            downloaded = block_num * block_size
            if total_size > 0:
                pct = min(downloaded * 100 // total_size, 100)
                mb = downloaded / 1024 / 1024
                total_mb = total_size / 1024 / 1024
                sys.stdout.write(f"\r      Progress: {pct}% ({mb:.1f} / {total_mb:.1f} MB)")
                sys.stdout.flush()

        urllib.request.urlretrieve(url, tmp, reporthook=report)
        print()  # newline after progress
        shutil.move(tmp, dest)
        size_mb = os.path.getsize(dest) / 1024 / 1024
        print(f"  [DONE] Saved to {dest} ({size_mb:.1f} MB)")
        return True
    except Exception as e:
        print(f"\n  [ERROR] {e}")
        if os.path.exists(tmp):
            os.remove(tmp)
        return False


def try_gdown():
    """Attempt to download via gdown (Google Drive)."""
    try:
        import gdown
    except ImportError:
        print("  [SKIP] gdown not installed. Run: pip install gdown")
        return False

    # Wav2Lip Google Drive file ID (from the original repo README)
    file_id = "1l9cHb5qQ8pI7pWnRCEHuFja9tpZpxTPP"
    url = f"https://drive.google.com/uc?id={file_id}"
    print(f"  [DOWNLOAD] via gdown (Google Drive)")
    tmp = DEST + ".tmp"
    try:
        gdown.download(url, tmp, quiet=False)
        shutil.move(tmp, DEST)
        size_mb = os.path.getsize(DEST) / 1024 / 1024
        print(f"  [DONE] Saved to {DEST} ({size_mb:.1f} MB)")
        return True
    except Exception as e:
        print(f"  [ERROR] gdown failed: {e}")
        if os.path.exists(tmp):
            os.remove(tmp)
        return False


def main():
    print("=" * 60)
    print("Downloading Wav2Lip Checkpoint (wav2lip.pth)")
    print("=" * 60)

    # Already present?
    if os.path.exists(DEST) and os.path.getsize(DEST) > 10_000_000:
        size_mb = os.path.getsize(DEST) / 1024 / 1024
        print(f"  [SKIP] Already exists: {DEST} ({size_mb:.1f} MB)")
        print("\n  Nothing to do.")
        return 0

    os.makedirs(os.path.dirname(DEST), exist_ok=True)

    # Try direct URLs first
    for url in URLS:
        print(f"\n[Trying] Mirror {URLS.index(url) + 1}/{len(URLS)}")
        if download_with_progress(url, DEST):
            return 0

    # Try Google Drive via gdown
    print("\n[Trying] Google Drive (via gdown)")
    if try_gdown():
        return 0

    # All failed
    print("\n" + "=" * 60)
    print("Automatic download failed.")
    print("=" * 60)
    print("\nPlease download wav2lip.pth manually:")
    print("  1. Visit: https://github.com/Rudrabha/Wav2Lip")
    print("  2. Follow the README link to download the checkpoint")
    print(f"  3. Place it at: {DEST}")
    print("\nOr install gdown and retry:")
    print("  pip install gdown")
    print("  python scripts/download_wav2lip.py")
    print("=" * 60)
    return 1


if __name__ == "__main__":
    sys.exit(main())
