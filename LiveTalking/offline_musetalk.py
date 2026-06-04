#!/usr/bin/env python
"""
Offline MuseTalk video synthesis.
Processes an entire audio file at once and writes a smooth MP4 video.
No real-time constraints, no WebRTC, no threading.

Usage:
    python offline_musetalk.py --avatar_id musetalk_avatar1 --audio input.wav --output output.mp4 --batch_size 4

Or with text (auto-generates TTS audio):
    python offline_musetalk.py --avatar_id musetalk_avatar1 --text "hello world" --output output.mp4
"""

import os
import sys
import argparse
import time
import math
import numpy as np
import cv2
import torch
import librosa
import subprocess

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from musereal import load_model, load_avatar, warm_up
from musetalk.utils.blending import get_image_blending
from logger import logger


def load_audio(audio_path, sr=16000):
    """Load audio and resample to 16kHz."""
    wav, orig_sr = librosa.load(audio_path, sr=sr)
    return wav


def tts_to_audio(text, voice="en-IN-NeerjaNeural", output_path="temp_tts.wav"):
    """Use edge-tts to generate audio from text."""
    import edge_tts
    import asyncio

    async def _generate():
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(output_path)

    asyncio.run(_generate())
    return output_path


def write_video(frames, output_path, fps=25, audio_path=None):
    """Write frames to MP4. Optionally mux with audio via ffmpeg."""
    if not frames:
        logger.error("No frames to write")
        return

    h, w = frames[0].shape[:2]
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    temp_video = output_path.replace(".mp4", "_temp.mp4")

    writer = cv2.VideoWriter(temp_video, fourcc, fps, (w, h))
    for frame in frames:
        # OpenCV expects BGR, frames are BGR from our pipeline
        writer.write(frame)
    writer.release()

    if audio_path and os.path.exists(audio_path):
        cmd = [
            "ffmpeg", "-y",
            "-i", temp_video,
            "-i", audio_path,
            "-c:v", "libx264", "-preset", "fast",
            "-c:a", "aac", "-b:a", "128k",
            "-shortest",
            "-movflags", "+faststart",
            output_path,
        ]
        try:
            subprocess.run(cmd, check=True, capture_output=True)
            os.remove(temp_video)
            logger.info(f"Video saved: {output_path}")
        except Exception as e:
            logger.warning(f"ffmpeg failed ({e}). Keeping silent video: {temp_video}")
            os.rename(temp_video, output_path)
    else:
        os.rename(temp_video, output_path)
        logger.info(f"Silent video saved: {output_path}")


def mirror_index(length, index):
    """Mirror index for looping avatar frames."""
    turn = index // length
    res = index % length
    if turn % 2 == 0:
        return res
    return length - res - 1


def synthesize(model, avatar, audio_path, output_path, batch_size=4, fps=25):
    """Main offline synthesis loop."""
    vae, unet, pe, timesteps, audio_processor, use_autocast = model
    frame_list_cycle, mask_list_cycle, coord_list_cycle, mask_coords_list_cycle, input_latent_list_cycle = avatar

    device = unet.device
    length = len(input_latent_list_cycle)

    # Pre-load latents to GPU
    input_latent_list_cycle = [l.to(device=device, dtype=unet.model.dtype) for l in input_latent_list_cycle]

    # Load audio and extract whisper features
    logger.info(f"Loading audio: {audio_path}")
    wav = load_audio(audio_path)
    audio_duration = len(wav) / 16000.0
    num_video_frames = int(audio_duration * fps)
    logger.info(f"Audio duration: {audio_duration:.2f}s -> {num_video_frames} video frames @ {fps}fps")

    logger.info("Extracting Whisper features...")
    t0 = time.perf_counter()
    whisper_features = audio_processor.audio2feat(wav)  # shape: (T, layers, 384)
    logger.info(f"Whisper features extracted in {(time.perf_counter()-t0)*1000:.0f}ms, shape: {whisper_features.shape}")

    # Generate frames
    logger.info("Generating frames...")
    output_frames = []
    total_unet_time = 0.0
    total_vae_time = 0.0

    with torch.no_grad():
        for i in range(0, num_video_frames, batch_size):
            batch_end = min(i + batch_size, num_video_frames)
            actual_batch = batch_end - i

            # Build latent batch
            latent_batch = []
            whisper_batch = []
            valid = True

            for j in range(actual_batch):
                idx = i + j
                m_idx = mirror_index(length, idx)
                latent_batch.append(input_latent_list_cycle[m_idx])

                # Extract audio features for this video frame
                if idx < num_video_frames:
                    feat, _ = audio_processor.get_sliced_feature(
                        feature_array=whisper_features,
                        vid_idx=idx,
                        audio_feat_length=[2, 2],
                        fps=fps,
                    )
                    whisper_batch.append(feat)
                else:
                    valid = False
                    break

            if not valid or len(whisper_batch) == 0:
                break

            latent_batch = torch.cat(latent_batch, dim=0)
            whisper_batch = np.stack(whisper_batch, axis=0)
            audio_feature_batch = torch.from_numpy(whisper_batch).to(device=device, dtype=unet.model.dtype)
            audio_feature_batch = pe(audio_feature_batch)

            # UNet inference
            t_unet = time.perf_counter()
            if use_autocast:
                with torch.autocast(device_type=device.type, enabled=True):
                    pred_latents = unet.model(latent_batch, timesteps, encoder_hidden_states=audio_feature_batch).sample
            else:
                pred_latents = unet.model(latent_batch, timesteps, encoder_hidden_states=audio_feature_batch).sample
            pred_latents = pred_latents.float().clamp(-10, 10)
            total_unet_time += (time.perf_counter() - t_unet)

            # VAE decode
            t_vae = time.perf_counter()
            recon = vae.decode_latents(pred_latents)
            total_vae_time += (time.perf_counter() - t_vae)

            # Paste each generated mouth back onto original frame
            for j in range(actual_batch):
                idx = i + j
                m_idx = mirror_index(length, idx)
                pred_frame = recon[j]
                ori_frame = frame_list_cycle[m_idx].copy()

                # Grey-mouth fallback
                if pred_frame is None or not np.isfinite(pred_frame).all():
                    output_frames.append(ori_frame)
                    continue
                mouth_half = pred_frame[pred_frame.shape[0] // 2:, :, :]
                if np.std(mouth_half) < 4.0 and 90.0 <= np.mean(mouth_half) <= 165.0:
                    output_frames.append(ori_frame)
                    continue

                bbox = coord_list_cycle[m_idx]
                x1, y1, x2, y2 = bbox
                res_frame = cv2.resize(pred_frame.astype(np.uint8), (x2 - x1, y2 - y1))
                mask = mask_list_cycle[m_idx]
                mask_crop_box = mask_coords_list_cycle[m_idx]
                combine_frame = get_image_blending(ori_frame, res_frame, bbox, mask, mask_crop_box)
                output_frames.append(combine_frame)

            if (i // batch_size + 1) % 10 == 0:
                logger.info(f"  Generated {len(output_frames)}/{num_video_frames} frames...")

    # Stats
    avg_unet = total_unet_time / max(1, num_video_frames / batch_size)
    avg_vae = total_vae_time / max(1, num_video_frames / batch_size)
    logger.info(f"Done. Avg UNet={avg_unet*1000:.0f}ms/batch, VAE={avg_vae*1000:.0f}ms/batch, total frames: {len(output_frames)}")

    # Write video
    write_video(output_frames, output_path, fps, audio_path)
    return output_path


def main():
    parser = argparse.ArgumentParser(description="Offline MuseTalk video synthesis")
    parser.add_argument("--avatar_id", default="musetalk_avatar1", help="Avatar ID")
    parser.add_argument("--audio", default=None, help="Input audio file (.wav, .mp3)")
    parser.add_argument("--text", default=None, help="Text to synthesize via TTS (alternative to --audio)")
    parser.add_argument("--voice", default="en-IN-NeerjaNeural", help="Edge-TTS voice for --text")
    parser.add_argument("--output", default="output.mp4", help="Output video path")
    parser.add_argument("--batch_size", type=int, default=4, help="Inference batch size")
    parser.add_argument("--fps", type=int, default=25, help="Output video FPS")
    args = parser.parse_args()

    if not args.audio and not args.text:
        parser.error("Must provide either --audio or --text")

    # Resolve audio
    audio_path = args.audio
    temp_audio = None
    if args.text:
        temp_audio = "temp_offline_tts.wav"
        logger.info(f"Generating TTS audio: '{args.text}'")
        audio_path = tts_to_audio(args.text, args.voice, temp_audio)

    # Load models
    logger.info("Loading MuseTalk models...")
    model = load_model()
    avatar = load_avatar(args.avatar_id)
    warm_up(args.batch_size, model)

    # Synthesize
    synthesize(model, avatar, audio_path, args.output, args.batch_size, args.fps)

    # Cleanup
    if temp_audio and os.path.exists(temp_audio):
        os.remove(temp_audio)


if __name__ == "__main__":
    main()
