"""
replace_background.py — Replace greenscreen background in avatar frames

Usage:
    python scripts/replace_background.py \
        --avatar_id indian_female \
        --background path/to/background.jpg

This modifies the full_imgs/ frames in-place using chroma key.
The rendering pipeline only touches the face/mouth region, so the
static background will never morph with avatar movement.

Optional flags:
    --green_hue_low   Lower HSV hue bound for green (default: 35)
    --green_hue_high  Upper HSV hue bound for green (default: 85)
    --sat_low         Minimum saturation to be considered green (default: 40)
    --val_low         Minimum value/brightness for green (default: 40)
    --blur            Feather the edge mask by this many pixels (default: 3)
    --backup          Save original frames to full_imgs_orig/ before replacing
    --preview         Write a single preview.jpg and exit (no in-place changes)
"""

import argparse
import os
import sys
import shutil
import cv2
import numpy as np
from glob import glob

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AVATARS_DIR  = os.path.join(PROJECT_ROOT, "backend", "data", "avatars")


def build_green_mask(frame_bgr, hue_low, hue_high, sat_low, val_low, blur):
    hsv = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV)
    lower = np.array([hue_low,  sat_low, val_low], dtype=np.uint8)
    upper = np.array([hue_high, 255,     255     ], dtype=np.uint8)
    mask_green = cv2.inRange(hsv, lower, upper)

    if blur > 0:
        k = blur * 2 + 1
        mask_green = cv2.GaussianBlur(mask_green, (k, k), 0)
        _, mask_green = cv2.threshold(mask_green, 10, 255, cv2.THRESH_BINARY)

    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    mask_green = cv2.morphologyEx(mask_green, cv2.MORPH_CLOSE, kernel, iterations=2)
    mask_green = cv2.morphologyEx(mask_green, cv2.MORPH_DILATE, kernel, iterations=1)

    return mask_green  # 255 = green (background), 0 = foreground


def composite(frame_bgr, bg_bgr, mask_green, blur):
    h, w = frame_bgr.shape[:2]
    bg_resized = cv2.resize(bg_bgr, (w, h), interpolation=cv2.INTER_LANCZOS4)

    if blur > 0:
        k = blur * 2 + 1
        soft_mask = cv2.GaussianBlur(mask_green, (k, k), 0).astype(np.float32) / 255.0
    else:
        soft_mask = (mask_green.astype(np.float32) / 255.0)

    soft_mask = soft_mask[:, :, np.newaxis]  # (H, W, 1)
    fg = frame_bgr.astype(np.float32)
    bg = bg_resized.astype(np.float32)
    result = fg * (1.0 - soft_mask) + bg * soft_mask
    return result.astype(np.uint8)


def process_avatar(args):
    avatar_path = os.path.join(AVATARS_DIR, args.avatar_id)
    full_imgs_path = os.path.join(avatar_path, "full_imgs")

    if not os.path.isdir(full_imgs_path):
        print(f"[ERROR] full_imgs not found: {full_imgs_path}")
        sys.exit(1)

    if not os.path.isfile(args.background):
        print(f"[ERROR] Background image not found: {args.background}")
        sys.exit(1)

    bg = cv2.imread(args.background)
    if bg is None:
        print(f"[ERROR] Could not load background image: {args.background}")
        sys.exit(1)

    frames = sorted(
        glob(os.path.join(full_imgs_path, "*.[jpJP][pnPN]*[gG]")),
        key=lambda x: int(os.path.splitext(os.path.basename(x))[0])
    )
    if not frames:
        print(f"[ERROR] No images found in {full_imgs_path}")
        sys.exit(1)

    print(f"[INFO] Avatar: {args.avatar_id}")
    print(f"[INFO] Frames: {len(frames)}")
    print(f"[INFO] Background: {args.background}")

    if args.preview:
        sample = cv2.imread(frames[len(frames) // 2])
        mask = build_green_mask(sample, args.green_hue_low, args.green_hue_high,
                                args.sat_low, args.val_low, args.blur)
        result = composite(sample, bg, mask, args.blur)
        preview_path = os.path.join(avatar_path, "preview_background.jpg")
        cv2.imwrite(preview_path, result)
        print(f"[PREVIEW] Saved: {preview_path}")
        print("[INFO] Re-run without --preview to apply to all frames.")
        return

    if args.backup:
        backup_path = os.path.join(avatar_path, "full_imgs_orig")
        if os.path.isdir(backup_path):
            print(f"[INFO] Backup already exists at {backup_path}, skipping.")
        else:
            shutil.copytree(full_imgs_path, backup_path)
            print(f"[INFO] Backed up original frames to {backup_path}")

    print("[INFO] Replacing backgrounds...")
    for i, fpath in enumerate(frames):
        frame = cv2.imread(fpath)
        if frame is None:
            continue
        mask = build_green_mask(frame, args.green_hue_low, args.green_hue_high,
                                args.sat_low, args.val_low, args.blur)
        result = composite(frame, bg, mask, args.blur)
        cv2.imwrite(fpath, result)

        if (i + 1) % 50 == 0 or i == len(frames) - 1:
            print(f"  {i + 1}/{len(frames)} frames done")

    print(f"\n[DONE] All {len(frames)} frames updated.")
    print("Restart the avatar server to apply the new frames.")


def main():
    parser = argparse.ArgumentParser(description="Replace greenscreen background in avatar frames")
    parser.add_argument("--avatar_id",      required=True, help="Avatar ID, e.g. indian_female")
    parser.add_argument("--background",     required=True, help="Path to background image (jpg/png)")
    parser.add_argument("--green_hue_low",  type=int, default=35,  help="HSV hue lower bound (default: 35)")
    parser.add_argument("--green_hue_high", type=int, default=85,  help="HSV hue upper bound (default: 85)")
    parser.add_argument("--sat_low",        type=int, default=40,  help="Minimum saturation (default: 40)")
    parser.add_argument("--val_low",        type=int, default=40,  help="Minimum brightness (default: 40)")
    parser.add_argument("--blur",           type=int, default=3,   help="Edge feathering in px (default: 3)")
    parser.add_argument("--backup",         action="store_true",   help="Back up original frames first")
    parser.add_argument("--preview",        action="store_true",   help="Save one preview frame and exit")
    args = parser.parse_args()

    process_avatar(args)


if __name__ == "__main__":
    main()
