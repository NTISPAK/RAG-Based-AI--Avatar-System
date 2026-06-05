"""
Fix failed model downloads using huggingface_hub and requests.
"""
import os
import sys
import requests

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(BASE_DIR, "models")

def download_hf_file(repo_id, filename, local_dir):
    """Download using huggingface_hub library."""
    from huggingface_hub import hf_hub_download
    dest = os.path.join(local_dir, os.path.basename(filename))
    if os.path.exists(dest) and os.path.getsize(dest) > 1000:
        print(f"[SKIP] Already exists: {dest} ({os.path.getsize(dest) / 1024 / 1024:.1f} MB)")
        return
    print(f"[DOWNLOAD] {repo_id}/{filename}")
    print(f"      to: {dest}")
    downloaded = hf_hub_download(
        repo_id=repo_id,
        filename=filename,
        local_dir=local_dir,
        local_dir_use_symlinks=False,
    )
    print(f"[DONE] {downloaded}")

def download_with_requests(url, dest, desc=""):
    """Download using requests with progress."""
    if os.path.exists(dest) and os.path.getsize(dest) > 1000:
        print(f"[SKIP] Already exists: {dest}")
        return
    print(f"[DOWNLOAD] {desc or os.path.basename(dest)}")
    print(f"      from: {url}")
    print(f"      to:   {dest}")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    }
    
    with requests.get(url, headers=headers, stream=True, timeout=300) as r:
        r.raise_for_status()
        total = int(r.headers.get('content-length', 0))
        downloaded = 0
        chunk_size = 1024 * 1024  # 1MB
        
        with open(dest, 'wb') as f:
            for chunk in r.iter_content(chunk_size=chunk_size):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total > 0:
                        pct = downloaded * 100 // total
                        print(f"\r      Progress: {pct}% ({downloaded / 1024 / 1024:.1f} / {total / 1024 / 1024:.1f} MB)", end='', flush=True)
        print()  # newline after progress
    
    final_size = os.path.getsize(dest)
    print(f"[DONE] {dest} ({final_size / 1024 / 1024:.1f} MB)")

def main():
    print("=" * 60)
    print("Fixing Failed Model Downloads")
    print("=" * 60)
    
    # 1. MuseTalk unet.pth
    print("\n[1/2] MuseTalk unet.pth (3.2 GB)")
    musetalk_dir = os.path.join(MODELS_DIR, "musetalkV15")
    os.makedirs(musetalk_dir, exist_ok=True)
    try:
        download_hf_file("TMElyralab/MuseTalk", "musetalkV15/unet.pth", musetalk_dir)
    except Exception as e:
        print(f"[ERROR] Failed to download unet.pth: {e}")
    
    # 2. Face Parsing weights
    print("\n[2/2] Face Parsing BiSeNet 79999_iter.pth (51 MB)")
    face_parse_dir = os.path.join(MODELS_DIR, "face-parse-bisent")
    os.makedirs(face_parse_dir, exist_ok=True)
    
    # Try multiple mirrors
    urls = [
        "https://github.com/zllrunning/face-parsing.PyTorch/releases/download/v1.0/79999_iter.pth",
        "https://github.com/zllrunning/face-parsing.PyTorch/raw/master/79999_iter.pth",
        "https://github.com/hhj1897/face_parsing/releases/download/v1.0/79999_iter.pth",
    ]
    
    dest = os.path.join(face_parse_dir, "79999_iter.pth")
    success = False
    for url in urls:
        try:
            download_with_requests(url, dest, "BiSeNet weights")
            if os.path.getsize(dest) > 1000000:  # > 1MB
                success = True
                break
        except Exception as e:
            print(f"[ERROR] Failed with {url}: {e}")
            if os.path.exists(dest):
                os.remove(dest)
    
    if not success:
        print("[WARNING] Could not download 79999_iter.pth automatically.")
        print("  Please download manually from:")
        print("  https://drive.google.com/open?id=154JgKpzM2e1DP0hpC4O0bkpqU2eSpd_M")
        print("  And place it at: models/face-parse-bisent/79999_iter.pth")
    
    print("\n" + "=" * 60)
    print("Download Fix Complete")
    print("=" * 60)

if __name__ == "__main__":
    main()
