#!/usr/bin/env python3
"""
Download all AI model weights required by the avatar backend.

Run this on a fresh clone before starting the servers:
    python scripts/download_models.py

What it downloads:
  - MuseTalk UNet weights (3.2 GB)
  - Stable Diffusion VAE-FT-MSE (~330 MB)
  - OpenAI Whisper Tiny (~150 MB)
  - Face Parsing BiSeNet weights (~50 MB)

What it does NOT download (you must handle separately):
  - wav2lip.pth  →  see script output for manual download link
  - Avatar data  →  copy from your existing PC or regenerate from video
"""
import os
import sys
import shutil

# Resolve project root regardless of where script is run from
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
MODELS_DIR = os.path.join(PROJECT_ROOT, "backend", "models")


def ensure_dir(path):
    os.makedirs(path, exist_ok=True)


def download_hf(repo_id, local_dir, allow_patterns=None, ignore_patterns=None):
    """Download a HuggingFace model/repository using snapshot_download."""
    from huggingface_hub import snapshot_download
    ensure_dir(local_dir)
    print(f"  repo: {repo_id}")
    print(f"  to:   {local_dir}")
    snapshot_download(
        repo_id=repo_id,
        local_dir=local_dir,
        local_dir_use_symlinks=False,
        allow_patterns=allow_patterns,
        ignore_patterns=ignore_patterns,
    )
    print(f"  [DONE]")


def download_hf_file(repo_id, filename, local_dir):
    """Download a single file from HuggingFace hub."""
    from huggingface_hub import hf_hub_download
    ensure_dir(local_dir)
    dest = os.path.join(local_dir, os.path.basename(filename))
    if os.path.exists(dest) and os.path.getsize(dest) > 1000:
        print(f"  [SKIP] Already exists: {dest}")
        return
    print(f"  [DOWNLOAD] {repo_id}/{filename}")
    downloaded = hf_hub_download(
        repo_id=repo_id,
        filename=filename,
        local_dir=local_dir,
        local_dir_use_symlinks=False,
    )
    print(f"  [DONE] {downloaded}")


def check_wav2lip():
    """wav2lip.pth is not on HuggingFace; check presence and print instructions."""
    path = os.path.join(MODELS_DIR, "wav2lip.pth")
    if os.path.exists(path) and os.path.getsize(path) > 1000000:
        size_mb = os.path.getsize(path) / 1024 / 1024
        print(f"  [OK] wav2lip.pth exists ({size_mb:.0f} MB)")
        return True
    print(f"  [MISSING] wav2lip.pth")
    print("  -> Download manually from: https://github.com/Rudrabha/Wav2Lip")
    print("     Place it at: backend/models/wav2lip.pth")
    return False


def main():
    print("=" * 60)
    print("Downloading AI Model Weights")
    print("=" * 60)

    # --- 1. MuseTalk UNet weights ---
    print("\n[1/5] MuseTalk V1.5 UNet (3.2 GB)")
    musetalk_dir = os.path.join(MODELS_DIR, "musetalkV15")
    download_hf_file("TMElyralab/MuseTalk", "musetalk/unet.pth", musetalk_dir)
    download_hf_file("TMElyralab/MuseTalk", "musetalk/musetalk.json", musetalk_dir)

    # --- 2. SD-VAE ---
    print("\n[2/5] Stable Diffusion VAE-FT-MSE (~330 MB)")
    sd_vae_dir = os.path.join(MODELS_DIR, "sd-vae")
    download_hf("stabilityai/sd-vae-ft-mse", sd_vae_dir)

    # --- 3. Whisper ---
    print("\n[3/5] OpenAI Whisper Tiny (~150 MB)")
    whisper_dir = os.path.join(MODELS_DIR, "whisper")
    download_hf("openai/whisper-tiny", whisper_dir)

    # --- 4. Face Parsing BiSeNet ---
    print("\n[4/5] Face Parsing BiSeNet weights (~50 MB)")
    face_parse_dir = os.path.join(MODELS_DIR, "face-parse-bisent")
    ensure_dir(face_parse_dir)
    bisenet_dest = os.path.join(face_parse_dir, "79999_iter.pth")
    if os.path.exists(bisenet_dest) and os.path.getsize(bisenet_dest) > 1000000:
        print(f"  [SKIP] Already exists: {bisenet_dest}")
    else:
        import urllib.request
        url = "https://github.com/zllrunning/face-parsing.PyTorch/releases/download/v1.0/79999_iter.pth"
        print(f"  [DOWNLOAD] {url}")
        print(f"  [DOWNLOAD] -> {bisenet_dest}")
        tmp = bisenet_dest + ".tmp"
        try:
            urllib.request.urlretrieve(url, tmp)
            shutil.move(tmp, bisenet_dest)
            print(f"  [DONE]")
        except Exception as e:
            print(f"  [ERROR] {e}")
            if os.path.exists(tmp):
                os.remove(tmp)

    # --- 5. Wav2Lip ---
    print("\n[5/5] Wav2Lip weights")
    check_wav2lip()

    # --- Summary ---
    print("\n" + "=" * 60)
    print("Download Summary")
    print("=" * 60)
    for name in sorted(os.listdir(MODELS_DIR)):
        p = os.path.join(MODELS_DIR, name)
        if os.path.isdir(p):
            files = [f for f in os.listdir(p) if not f.startswith(".")]
            print(f"  {name}/: {len(files)} file(s)")
        else:
            mb = os.path.getsize(p) / 1024 / 1024
            print(f"  {name}: {mb:.1f} MB")

    print("\n" + "=" * 60)
    print("Next steps:")
    print("  1. If wav2lip.pth is missing, download it manually (see above).")
    print("  2. Copy your avatar data folder to backend/data/avatars/")
    print("     OR generate a new avatar from a video:")
    print("     python scripts/generate_avatar.py --video custom-videos/indian-female.mp4 --avatar_id indian_female")
    print("=" * 60)


if __name__ == "__main__":
    try:
        from huggingface_hub import snapshot_download, hf_hub_download
    except ImportError:
        print("[ERROR] huggingface_hub is not installed.")
        print("  Run: pip install huggingface_hub")
        sys.exit(1)
    main()
