# Download Required Models for LiveTalking

## Required Files

You need to download these files before LiveTalking can run:

### 1. Wav2Lip Model (~350MB)
**File**: `wav2lip256.pth`

**Download from one of these sources**:
- **Quark Cloud** (Chinese): https://pan.quark.cn/s/83a750323ef0
- **Google Drive**: https://drive.google.com/drive/folders/1FOC_MD6wdogyyX_7V1d4NDIO7P9NlSAJ

**Installation**:
```bash
# After downloading wav2lip256.pth:
cd /Users/naumanrashid/Desktop/Tester/LiveTalking
mv ~/Downloads/wav2lip256.pth models/wav2lip.pth
```

### 2. Avatar Files (~1.5GB)
**File**: `wav2lip256_avatar1.tar.gz`

**Download from the same sources above**

**Installation**:
```bash
# After downloading wav2lip256_avatar1.tar.gz:
cd /Users/naumanrashid/Desktop/Tester/LiveTalking/data/avatars
tar -xzf ~/Downloads/wav2lip256_avatar1.tar.gz
```

Your directory structure should look like:
```
LiveTalking/
├── models/
│   └── wav2lip.pth          # Renamed from wav2lip256.pth
├── data/
│   └── avatars/
│       └── wav2lip256_avatar1/
│           ├── (various avatar files)
```

## Alternative: Direct Download Commands

If you have `wget` or `curl`, you can try these direct links (if available):

```bash
# Install wget if needed
brew install wget

# Download model (replace with actual direct link if available)
cd /Users/naumanrashid/Desktop/Tester/LiveTalking/models
# wget <direct-link-to-wav2lip256.pth>
# mv wav2lip256.pth wav2lip.pth
```

## After Downloading

Once you have the files in place, verify:

```bash
cd /Users/naumanrashid/Desktop/Tester/LiveTalking

# Check model exists
ls -lh models/wav2lip.pth

# Check avatar exists
ls -la data/avatars/wav2lip256_avatar1/
```

Then you can run LiveTalking!

## Note for Mac M2

Even with models downloaded, LiveTalking will run VERY slowly on Mac M2 because:
- No NVIDIA GPU (uses CPU only)
- Real-time video generation requires GPU
- Expect 1-5 FPS instead of 25+ FPS

For production use, consider deploying on a cloud GPU instance.
