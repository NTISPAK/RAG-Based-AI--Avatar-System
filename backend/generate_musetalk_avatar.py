"""
Generate MuseTalk avatar data from a video file.
Uses face_detection (already installed) instead of mmpose for face detection.
Produces: full_imgs/, coords.pkl, latents.pt, mask/, mask_coords.pkl, avator_info.json
"""
import argparse
import glob
import json
import os
import pickle
import sys

import cv2
import numpy as np
import torch
from PIL import Image
from tqdm import tqdm

from face_alignment import FaceAlignment, LandmarksType
from musetalk.utils.blending import get_image_prepare_material
from musetalk.models.vae import VAE

# FaceParsing is optional; fallback to simple elliptical mask if BiSeNet weights missing
_FACE_PARSING_AVAILABLE = False
FaceParsing = None
try:
    from musetalk.utils.face_parsing import FaceParsing as _FP
    # Also verify the weights file exists
    _bisent_weights = './models/face-parse-bisent/79999_iter.pth'
    if os.path.exists(_bisent_weights) and os.path.getsize(_bisent_weights) > 1000000:
        FaceParsing = _FP
        _FACE_PARSING_AVAILABLE = True
    else:
        print("[WARN] BiSeNet weights not found, using simple elliptical mask fallback")
except Exception as e:
    print(f"[WARN] FaceParsing not available ({e}), using simple elliptical mask fallback")


class SimpleFaceMask:
    """Fallback face mask generator using an ellipse inside the crop box."""
    def __init__(self, left_cheek_width=80, right_cheek_width=80):
        pass  # no weights needed

    def __call__(self, image, size=(512, 512), mode="raw"):
        """Return an elliptical mask image matching the input image size."""
        if isinstance(image, str):
            image = Image.open(image)
        w, h = image.size
        mask = np.zeros((h, w), dtype=np.uint8)
        # Draw an ellipse covering most of the face area
        cx, cy = w // 2, h // 2
        a, b = int(w * 0.42), int(h * 0.48)  # slightly narrower ellipse
        cv2.ellipse(mask, (cx, cy), (a, b), 0, 0, 360, 255, -1)
        # Gaussian blur to feather edges
        blur = cv2.GaussianBlur(mask, (51, 51), 0)
        return Image.fromarray(blur)



def video2imgs(vid_path, save_path, max_frames=10000):
    """Extract frames from video."""
    cap = cv2.VideoCapture(vid_path)
    count = 0
    while count < max_frames:
        ret, frame = cap.read()
        if not ret:
            break
        cv2.imwrite(f"{save_path}/{count:08d}.png", frame)
        count += 1
    cap.release()
    print(f"  Extracted {count} frames")
    return count


def get_face_bbox(fa, frame, bbox_shift=0):
    """Get face bounding box using face_alignment library with landmark refinement."""
    # Get landmarks (68-point) - this also detects the face
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    landmarks = fa.get_landmarks(rgb_frame)
    if landmarks is None or len(landmarks) == 0:
        return None

    lm = landmarks[0]  # First face, shape (68, 2)
    # 68-point landmarks layout:
    # 0-16 = jaw, 17-21 = left eyebrow, 22-26 = right eyebrow
    # 27-30 = nose bridge, 31-35 = nose bottom, 36-41 = left eye, 42-47 = right eye
    # 48-67 = mouth
    
    # Get the nose bridge midpoint (similar to mmpose's half_face_coord)
    nose_bridge = lm[30]  # tip of nose bridge
    
    # Calculate half face distance
    face_bottom = np.max(lm[:, 1])
    half_face_coord_y = nose_bridge[1]
    
    if bbox_shift != 0:
        half_face_coord_y += bbox_shift
        
    half_face_dist = face_bottom - half_face_coord_y
    upper_bond = max(0, int(half_face_coord_y - half_face_dist))
    
    # Use landmark extents for x
    lm_x1 = int(np.min(lm[:, 0]))
    lm_x2 = int(np.max(lm[:, 0]))
    lm_y2 = int(np.max(lm[:, 1]))
    
    # Sanity check
    if lm_x2 - lm_x1 > 0 and lm_y2 - upper_bond > 0 and lm_x1 >= 0:
        return (lm_x1, upper_bond, lm_x2, lm_y2)
    
    # Fallback: use raw landmark extents
    return (int(np.min(lm[:, 0])), int(np.min(lm[:, 1])),
            int(np.max(lm[:, 0])), int(np.max(lm[:, 1])))


def main():
    parser = argparse.ArgumentParser(description="Generate MuseTalk avatar data")
    parser.add_argument("--file", type=str, required=True, help="Path to video file or image directory")
    parser.add_argument("--avatar_id", type=str, default="musetalk_businesswoman", help="Avatar ID")
    parser.add_argument("--bbox_shift", type=int, default=0, help="Bounding box vertical shift")
    parser.add_argument("--version", type=str, default="v15", choices=["v1", "v15"])
    parser.add_argument("--extra_margin", type=int, default=10, help="Extra margin for v15 face cropping")
    parser.add_argument("--parsing_mode", default="jaw", help="Face parsing mode: raw, neck, jaw")
    parser.add_argument("--left_cheek_width", type=int, default=90)
    parser.add_argument("--right_cheek_width", type=int, default=90)
    parser.add_argument("--gpu_id", type=int, default=0)
    args = parser.parse_args()

    if torch.cuda.is_available():
        device = torch.device(f"cuda:{args.gpu_id}")
    elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        device = torch.device("mps")
    else:
        device = torch.device("cpu")
    print(f"Using device: {device}")

    # Paths
    avatar_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "avatars", args.avatar_id)
    full_imgs_path = f"{avatar_path}/full_imgs"
    mask_out_path = f"{avatar_path}/mask"
    coords_path = f"{avatar_path}/coords.pkl"
    mask_coords_path = f"{avatar_path}/mask_coords.pkl"
    latents_out_path = f"{avatar_path}/latents.pt"
    info_path = f"{avatar_path}/avator_info.json"

    os.makedirs(full_imgs_path, exist_ok=True)
    os.makedirs(mask_out_path, exist_ok=True)

    # Save avatar info
    with open(info_path, "w") as f:
        json.dump({
            "avatar_id": args.avatar_id,
            "video_path": args.file,
            "bbox_shift": args.bbox_shift
        }, f)

    # Step 1: Extract frames
    print("\n[1/5] Extracting frames from video...")
    if os.path.isfile(args.file) and args.file.lower().endswith(('.mp4', '.avi', '.mov', '.mkv')):
        video2imgs(args.file, full_imgs_path)
    elif os.path.isdir(args.file):
        import shutil
        for f in sorted(os.listdir(args.file)):
            if f.endswith('.png'):
                shutil.copy2(os.path.join(args.file, f), os.path.join(full_imgs_path, f))
        print(f"  Copied {len(os.listdir(full_imgs_path))} frames")
    else:
        raise ValueError(f"Unsupported input: {args.file}")

    # Load frame list
    input_img_list = sorted(glob.glob(os.path.join(full_imgs_path, '*.[jpJP][pnPN]*[gG]')))
    print(f"  Total frames: {len(input_img_list)}")

    # Step 2: Detect face landmarks and bounding boxes
    print("\n[2/5] Detecting faces...")
    fa = FaceAlignment(LandmarksType.TWO_D, flip_input=False, device=str(device))
    
    coord_list = []
    frame_list = []
    for img_path in tqdm(input_img_list):
        frame = cv2.imread(img_path)
        frame_list.append(frame)
        bbox = get_face_bbox(fa, frame, args.bbox_shift)
        if bbox is None:
            coord_list.append((0.0, 0.0, 0.0, 0.0))
        else:
            coord_list.append(bbox)

    # Step 3: Load VAE and encode face latents
    print("\n[3/5] Encoding face latents with VAE...")
    vae = VAE(model_path="./models/sd-vae")
    vae.vae = vae.vae.half().to(device)

    input_latent_list = []
    coord_placeholder = (0.0, 0.0, 0.0, 0.0)
    
    for idx, (bbox, frame) in enumerate(tqdm(zip(coord_list, frame_list), total=len(frame_list))):
        if bbox == coord_placeholder:
            # Use a zero latent as placeholder
            input_latent_list.append(torch.zeros(1, 8, 32, 32))
            continue
        
        x1, y1, x2, y2 = [int(v) for v in bbox]
        
        # Apply extra margin for v15
        if args.version == "v15":
            y2 = min(y2 + args.extra_margin, frame.shape[0])
            coord_list[idx] = (x1, y1, x2, y2)
        
        crop_frame = frame[y1:y2, x1:x2]
        if crop_frame.size == 0:
            input_latent_list.append(torch.zeros(1, 8, 32, 32))
            continue
            
        resized_crop_frame = cv2.resize(crop_frame, (256, 256), interpolation=cv2.INTER_LANCZOS4)
        latents = vae.get_latents_for_unet(resized_crop_frame)
        input_latent_list.append(latents)

    # Step 4: Generate face parsing masks
    print("\n[4/5] Generating face masks...")
    if FaceParsing is not None:
        if args.version == "v15":
            fp = FaceParsing(left_cheek_width=args.left_cheek_width, right_cheek_width=args.right_cheek_width)
        else:
            fp = FaceParsing()
    else:
        fp = SimpleFaceMask()
        print("  (Using SimpleFaceMask fallback - no BiSeNet weights)")

    mask_coords_list = []
    for i, frame in enumerate(tqdm(frame_list)):
        x1, y1, x2, y2 = [int(v) for v in coord_list[i]]
        if (x1, y1, x2, y2) == (0, 0, 0, 0):
            # No face detected - use dummy mask
            mask = np.zeros((256, 256), dtype=np.uint8)
            crop_box = [0, 0, frame.shape[1], frame.shape[0]]
        else:
            mode = args.parsing_mode if args.version == "v15" else "raw"
            mask, crop_box = get_image_prepare_material(frame, [x1, y1, x2, y2], fp=fp, mode=mode)
        
        cv2.imwrite(f"{mask_out_path}/{i:08d}.png", mask)
        mask_coords_list.append(crop_box)

    # Step 5: Save all data
    print("\n[5/5] Saving avatar data...")
    with open(coords_path, 'wb') as f:
        pickle.dump(coord_list, f)
    
    with open(mask_coords_path, 'wb') as f:
        pickle.dump(mask_coords_list, f)
    
    torch.save(input_latent_list, latents_out_path)

    print(f"\n{'='*60}")
    print(f"SUCCESS! MuseTalk avatar generated: {args.avatar_id}")
    print(f"  Frames: {len(frame_list)}")
    print(f"  Latents: {len(input_latent_list)}")
    print(f"  Masks: {len(mask_coords_list)}")
    print(f"  Path: {avatar_path}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
