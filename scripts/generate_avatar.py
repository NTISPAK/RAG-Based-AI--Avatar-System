#!/usr/bin/env python3
"""
Generate a MuseTalk avatar from a video file.

Run from the project root:
    python scripts/generate_avatar.py --video custom-videos/indian-female.mp4 --avatar_id indian_female

Prerequisites:
  - All model weights downloaded (run: python scripts/download_models.py)
  - A source video file (ideally 5-30 seconds, face clearly visible)

Output:
  - backend/data/avatars/<avatar_id>/
      full_imgs/      -> extracted video frames
      mask/           -> face parsing masks
      coords.pkl      -> face bounding boxes
      mask_coords.pkl -> mask crop coordinates
      latents.pt      -> VAE-encoded face latents
      avator_info.json -> metadata
"""
import argparse
import os
import sys

# Resolve paths so we can run from project root
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
BACKEND_DIR = os.path.join(PROJECT_ROOT, "backend")
MODELS_DIR = os.path.join(BACKEND_DIR, "models")
DATA_DIR = os.path.join(BACKEND_DIR, "data", "avatars")
GENERATOR = os.path.join(BACKEND_DIR, "generate_musetalk_avatar.py")


def check_file(path, desc):
    if os.path.exists(path) and os.path.getsize(path) > 1000:
        print(f"  [OK] {desc}")
        return True
    print(f"  [MISSING] {desc}")
    return False


def check_models():
    print("Checking model weights...")
    ok = True
    ok &= check_file(os.path.join(MODELS_DIR, "musetalkV15", "unet.pth"), "MuseTalk UNet")
    ok &= check_file(os.path.join(MODELS_DIR, "sd-vae", "diffusion_pytorch_model.safetensors"), "SD-VAE")
    ok &= check_file(os.path.join(MODELS_DIR, "whisper", "model.safetensors"), "Whisper Tiny")
    if not ok:
        print("\n  Run: python scripts/download_models.py")
        return False
    return True


def check_video(video_path):
    if not os.path.exists(video_path):
        print(f"[ERROR] Video not found: {video_path}")
        return False
    size_mb = os.path.getsize(video_path) / 1024 / 1024
    print(f"  [OK] Video: {video_path} ({size_mb:.1f} MB)")
    return True


def main():
    parser = argparse.ArgumentParser(description="Generate MuseTalk avatar from video")
    parser.add_argument("--video", type=str, required=True, help="Path to source video file (.mp4, .avi, .mov)")
    parser.add_argument("--avatar_id", type=str, required=True, help="Avatar ID (e.g., my_avatar)")
    parser.add_argument("--bbox_shift", type=int, default=0, help="Vertical shift for face bounding box")
    parser.add_argument("--version", type=str, default="v15", choices=["v1", "v15"], help="MuseTalk version")
    args = parser.parse_args()

    print("=" * 60)
    print("Avatar Generator")
    print("=" * 60)

    # 1. Check prerequisites
    if not check_models():
        sys.exit(1)
    if not check_video(args.video):
        sys.exit(1)

    # 2. Ensure output directory is clean
    out_dir = os.path.join(DATA_DIR, args.avatar_id)
    if os.path.exists(out_dir) and os.listdir(out_dir):
        print(f"\n[WARNING] Output directory already exists: {out_dir}")
        print("  Existing files will be overwritten.")

    # Resolve video path BEFORE changing directory
    video_abs = os.path.abspath(args.video)

    # 3. Change to backend dir so relative paths in generator work
    print(f"\n[Generating] Avatar: {args.avatar_id}")
    print(f"  From: {video_abs}")
    print(f"  To:   {out_dir}")
    print("  This may take a few minutes...\n")

    os.chdir(BACKEND_DIR)
    sys.path.insert(0, BACKEND_DIR)

    # 4. Run the generator by importing its main function
    import importlib.util
    spec = importlib.util.spec_from_file_location("generator", GENERATOR)
    gen_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gen_module)

    # Override sys.argv so the generator argparse works
    original_argv = sys.argv
    sys.argv = [
        GENERATOR,
        "--file", video_abs,
        "--avatar_id", args.avatar_id,
        "--bbox_shift", str(args.bbox_shift),
        "--version", args.version,
    ]
    try:
        gen_module.main()
    except SystemExit:
        pass  # argparse may call sys.exit, which is fine
    finally:
        sys.argv = original_argv

    # 5. Verify output
    print("\n" + "=" * 60)
    print("Verification")
    print("=" * 60)
    expected = ["full_imgs", "mask", "coords.pkl", "mask_coords.pkl", "latents.pt", "avator_info.json"]
    all_ok = True
    for item in expected:
        path = os.path.join(out_dir, item)
        if os.path.exists(path):
            print(f"  [OK] {item}")
        else:
            print(f"  [MISSING] {item}")
            all_ok = False

    print("\n" + "=" * 60)
    if all_ok:
        print("SUCCESS! Avatar generated.")
        print(f"  Location: {out_dir}")
        print(f"\n  To use this avatar, start the server with:")
        print(f"    python app.py --model musetalk --avatar_id {args.avatar_id} --transport webrtc")
    else:
        print("WARNING: Some expected files are missing.")
    print("=" * 60)


if __name__ == "__main__":
    main()
