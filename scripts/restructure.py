#!/usr/bin/env python3
"""
Production restructure script.
Separates frontend and backend into clean directories.
Run from project root: python scripts/restructure.py
"""

import os
import shutil
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(PROJECT_ROOT)

def mkdir(path):
    os.makedirs(path, exist_ok=True)
    print(f"  mkdir {path}")

def move(src, dst):
    if os.path.exists(src):
        shutil.move(src, dst)
        print(f"  mv {src} -> {dst}")
    else:
        print(f"  SKIP (not found): {src}")

def copy(src, dst):
    if os.path.exists(src):
        if os.path.isdir(src):
            shutil.copytree(src, dst, dirs_exist_ok=True)
        else:
            shutil.copy2(src, dst)
        print(f"  cp {src} -> {dst}")
    else:
        print(f"  SKIP (not found): {src}")

print("="*60)
print("Production Restructure: Frontend / Backend Separation")
print("="*60)

# ------------------------------------------------------------------
# 1. Create directory structure
# ------------------------------------------------------------------
print("\n[1/6] Creating directories...")
mkdir("backend")
mkdir("backend/musetalk")
mkdir("backend/wav2lip")
mkdir("backend/ultralight")
mkdir("backend/models")
mkdir("backend/data/avatars")
mkdir("backend/data/videos")
mkdir("backend/data/customvideo")
mkdir("frontend/src")
mkdir("frontend/js")
mkdir("frontend/assets")
mkdir("frontend/assets/css")

# ------------------------------------------------------------------
# 2. Move backend Python files
# ------------------------------------------------------------------
print("\n[2/6] Moving backend Python files...")
backend_py_files = [
    "LiveTalking/musereal.py",
    "LiveTalking/ttsreal.py",
    "LiveTalking/basereal.py",
    "LiveTalking/baseasr.py",
    "LiveTalking/museasr.py",
    "LiveTalking/lipreal.py",
    "LiveTalking/lipasr.py",
    "LiveTalking/lightreal.py",
    "LiveTalking/hubertasr.py",
    "LiveTalking/webrtc.py",
    "LiveTalking/llm.py",
    "LiveTalking/logger.py",
    "LiveTalking/offline_musetalk.py",
    "LiveTalking/generate_musetalk_avatar.py",
    "LiveTalking/download_models.py",
    "LiveTalking/download_models_fix.py",
]
for f in backend_py_files:
    move(f, "backend/")

# ------------------------------------------------------------------
# 3. Move backend packages & assets
# ------------------------------------------------------------------
print("\n[3/6] Moving backend packages & model data...")
move("LiveTalking/musetalk", "backend/musetalk")
move("LiveTalking/wav2lip", "backend/wav2lip")
move("LiveTalking/ultralight", "backend/ultralight")

# Move data and models (large files, avoid duplication)
if os.path.exists("LiveTalking/data"):
    print("  Moving data/...")
    shutil.move("LiveTalking/data", "backend/data")
if os.path.exists("LiveTalking/models"):
    print("  Moving models/...")
    shutil.move("LiveTalking/models", "backend/models")

# ------------------------------------------------------------------
# 4. Move frontend files
# ------------------------------------------------------------------
print("\n[4/6] Moving frontend files...")
web_dir = "LiveTalking/web"
if os.path.exists(web_dir):
    for item in os.listdir(web_dir):
        src = os.path.join(web_dir, item)
        if item.endswith('.html'):
            move(src, "frontend/src/")
        elif item.endswith('.js'):
            move(src, "frontend/js/")
        elif item == 'assets':
            for asset in os.listdir(src):
                move(os.path.join(src, asset), "frontend/assets/")
            os.rmdir(src)
        else:
            # Other files (css, etc.)
            move(src, "frontend/assets/")

# ------------------------------------------------------------------
# 5. Fix paths in backend files
# ------------------------------------------------------------------
print("\n[5/6] Fixing paths in backend files...")

def fix_file(filepath, replacements):
    if not os.path.exists(filepath):
        print(f"  SKIP (not found): {filepath}")
        return
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    for old, new in replacements:
        content = content.replace(old, new)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"  Fixed paths in {filepath}")

# Fix musereal.py, lipreal.py, lightreal.py: ./data/avatars -> relative paths
avatar_path_fixes = [
    ('avatar_path = f"./data/avatars/{avatar_id}"',
     'avatar_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "avatars", avatar_id)'),
]
for fname in ["backend/musereal.py", "backend/lipreal.py", "backend/lightreal.py"]:
    fix_file(fname, avatar_path_fixes)

# Fix generate_musetalk_avatar.py
fix_file("backend/generate_musetalk_avatar.py", [
    ('avatar_path = f"./data/avatars/{args.avatar_id}"',
     'avatar_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "avatars", args.avatar_id)'),
])

# Fix musetalk/genavatar.py (inside copied package)
genavatar_path = "backend/musetalk/genavatar.py"
if os.path.exists(genavatar_path):
    fix_file(genavatar_path, [
        ("f'./data/avatars/{avatar_id}'",
         'os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "avatars", avatar_id)'),
        ("f'./data/avatars/{avatar_id}/full_imgs'",
         'os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "avatars", avatar_id, "full_imgs")'),
        ("f'./data/avatars/{avatar_id}/mask'",
         'os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "avatars", avatar_id, "mask")'),
    ])

# Fix app.py static paths (should already be written by user with write_to_file)
# But if copied from old location, fix it:
backend_app = "backend/app.py"
if os.path.exists(backend_app):
    with open(backend_app, 'r') as f:
        content = f.read()
    # Ensure it has BASE_DIR setup
    if "BASE_DIR" not in content:
        print("  WARNING: backend/app.py missing BASE_DIR. Please use the provided app.py.")

# ------------------------------------------------------------------
# 6. Cleanup old LiveTalking directory
# ------------------------------------------------------------------
print("\n[6/6] Cleanup...")
if os.path.exists("LiveTalking"):
    shutil.rmtree("LiveTalking")
    print("  Removed LiveTalking/")

# Move root-level RAG files to backend/rag/
print("\n[Bonus] Organizing RAG backend files...")
mkdir("backend/rag")
rag_files = ["main.py", "ingest.py", "translation_service.py"]
for f in rag_files:
    if os.path.exists(f):
        move(f, "backend/rag/")

print("\n" + "="*60)
print("Done! Next steps:")
print("  1. cd backend && python -m venv .venv")
print("  2. source backend/.venv/bin/activate  (or .venv\\Scripts\\activate on Windows)")
print("  3. pip install -r backend/requirements.txt")
print("  4. cd backend && python app.py --model musetalk --avatar_id ...")
print("="*60)
