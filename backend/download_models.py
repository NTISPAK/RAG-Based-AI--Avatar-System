"""
Download all MuseTalk required models.
Run from within the LiveTalking directory.
"""
import os
import sys
import urllib.request
import shutil

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(BASE_DIR, "models")

def ensure_dir(path):
    os.makedirs(path, exist_ok=True)

def download_file(url, dest, desc=""):
    if os.path.exists(dest):
        print(f"  [SKIP] Already exists: {dest}")
        return
    print(f"  [DOWNLOAD] {desc or os.path.basename(dest)}")
    print(f"      from: {url}")
    print(f"      to:   {dest}")
    tmp = dest + ".tmp"
    try:
        urllib.request.urlretrieve(url, tmp)
        shutil.move(tmp, dest)
        print(f"  [DONE] {dest}")
    except Exception as e:
        print(f"  [ERROR] {e}")
        if os.path.exists(tmp):
            os.remove(tmp)
        raise

def download_hf_file(repo_id, filename, local_dir, desc=""):
    """Download a single file from HuggingFace hub using the raw URL."""
    url = f"https://huggingface.co/{repo_id}/resolve/main/{filename}"
    dest = os.path.join(local_dir, os.path.basename(filename))
    download_file(url, dest, desc)

def clone_hf_repo(repo_id, local_dir, desc=""):
    """Clone a HuggingFace repo (or use snapshot_download if huggingface_hub available)."""
    if os.path.exists(local_dir) and len(os.listdir(local_dir)) > 2:
        print(f"  [SKIP] Repo already exists: {local_dir}")
        return
    print(f"  [DOWNLOAD] {desc}")
    print(f"      repo: {repo_id}")
    print(f"      to:   {local_dir}")
    try:
        from huggingface_hub import snapshot_download
        snapshot_download(repo_id=repo_id, local_dir=local_dir)
        print(f"  [DONE] {local_dir}")
    except Exception as e:
        print(f"  [ERROR] huggingface_hub snapshot_download failed: {e}")
        print(f"  [FALLBACK] Please clone manually: git clone https://huggingface.co/{repo_id} {local_dir}")

def main():
    print("=" * 60)
    print("Downloading MuseTalk Required Models")
    print("=" * 60)

    # 1. MuseTalk UNet weights + config
    print("\n[1/5] MuseTalk V1.5 UNet (3.2 GB)")
    musetalk_dir = os.path.join(MODELS_DIR, "musetalkV15")
    ensure_dir(musetalk_dir)
    # Try downloading specific files from HF
    download_hf_file("TMElyralab/MuseTalk", "musetalkV15/unet.pth", musetalk_dir, "unet.pth (3.2 GB)")
    download_hf_file("TMElyralab/MuseTalk", "musetalkV15/musetalk.json", musetalk_dir, "musetalk.json")

    # 2. SD-VAE
    print("\n[2/5] Stable Diffusion VAE-FT-MSE (319 MB)")
    sd_vae_dir = os.path.join(MODELS_DIR, "sd-vae")
    ensure_dir(sd_vae_dir)
    clone_hf_repo("stabilityai/sd-vae-ft-mse", sd_vae_dir, "SD-VAE-FT-MSE")

    # 3. Whisper Tiny
    print("\n[3/5] OpenAI Whisper Tiny (144 MB)")
    whisper_dir = os.path.join(MODELS_DIR, "whisper")
    ensure_dir(whisper_dir)
    clone_hf_repo("openai/whisper-tiny", whisper_dir, "Whisper Tiny")

    # 4. Face Parsing BiSeNet
    print("\n[4/5] Face Parsing BiSeNet (51 MB)")
    face_parse_dir = os.path.join(MODELS_DIR, "face-parse-bisent")
    ensure_dir(face_parse_dir)
    # 79999_iter.pth from the GitHub release / Google Drive alternative
    # The original repo: https://github.com/zllrunning/face-parsing.PyTorch
    # Using a known mirror URL
    download_file(
        "https://github.com/zllrunning/face-parsing.PyTorch/releases/download/v1.0/79999_iter.pth",
        os.path.join(face_parse_dir, "79999_iter.pth"),
        "BiSeNet weights (51 MB)"
    )
    # resnet18 pretrained weights (standard torchvision)
    # These are auto-downloaded by torchvision, but we'll ensure they're available
    # Actually torchvision downloads this automatically when BiSeNet loads, but we can pre-download
    resnet_dest = os.path.join(face_parse_dir, "resnet18-5c106cde.pth")
    if not os.path.exists(resnet_dest):
        print(f"  [INFO] resnet18 weights will be auto-downloaded by torchvision when needed.")
        print(f"         (Or download manually from pytorch model zoo)")
    else:
        print(f"  [SKIP] resnet18 weights already present")

    # 5. Check wav2lip.pth exists
    print("\n[5/5] Verifying existing models")
    wav2lip_path = os.path.join(MODELS_DIR, "wav2lip.pth")
    if os.path.exists(wav2lip_path):
        print(f"  [OK] wav2lip.pth exists ({os.path.getsize(wav2lip_path) / 1024 / 1024:.0f} MB)")
    else:
        print(f"  [MISSING] wav2lip.pth - needed for Wav2Lip fallback mode")

    print("\n" + "=" * 60)
    print("Download Summary")
    print("=" * 60)
    for subdir in sorted(os.listdir(MODELS_DIR)):
        subpath = os.path.join(MODELS_DIR, subdir)
        if os.path.isdir(subpath):
            files = os.listdir(subpath)
            print(f"  {subdir}/: {len(files)} item(s)")
        else:
            size = os.path.getsize(subpath) / 1024 / 1024
            print(f"  {subdir}: {size:.1f} MB")

if __name__ == "__main__":
    main()
