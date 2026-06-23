###############################################################################
#  Copyright (C) 2024 LiveTalking@lipku https://github.com/lipku/LiveTalking
#  email: lipku@foxmail.com
# 
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#  
#       http://www.apache.org/licenses/LICENSE-2.0
# 
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
###############################################################################

# server.py
from flask import Flask, render_template,send_from_directory,request, jsonify
from flask_sockets import Sockets
import base64
import json
#import gevent
#from gevent import pywsgi
#from geventwebsocket.handler import WebSocketHandler
import re
import numpy as np
from threading import Thread,Event
#import multiprocessing
import torch.multiprocessing as mp

from aiohttp import web
import aiohttp
import aiohttp_cors
from aiortc import RTCPeerConnection, RTCSessionDescription,RTCIceServer,RTCConfiguration
from aiortc.rtcrtpsender import RTCRtpSender
from webrtc import HumanPlayer
from basereal import BaseReal
from llm import llm_response

import argparse
import random
import shutil
import asyncio
import torch
from typing import Dict
from logger import logger
import gc
import time
import cv2
import subprocess
import os
import io

# ------------------------------------------------------------------
# Base directory: all relative paths resolve from this script's location
# ------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.abspath(os.path.join(BASE_DIR, '..', 'frontend', 'src'))
DATA_DIR = os.path.join(BASE_DIR, 'data')
MODELS_DIR = os.path.join(BASE_DIR, 'models')

if torch.cuda.is_available():
    _gpu_name = torch.cuda.get_device_name(0)
    _cap = torch.cuda.get_device_capability()
    _non_rtx = any(x in _gpu_name.lower() for x in ['gtx 16', 'tesla t4', 'quadro'])
    _has_tensor_cores = (_cap[0] > 7 or (_cap[0] == 7 and _cap[1] >= 5)) and not _non_rtx
    torch.backends.cudnn.benchmark = _has_tensor_cores
    _is_ampere_or_newer = _cap[0] >= 8
    torch.backends.cuda.matmul.allow_tf32 = _is_ampere_or_newer
    torch.backends.cudnn.allow_tf32 = _is_ampere_or_newer
    logger.info(f'[CUDA] cudnn.benchmark={_has_tensor_cores}, tf32={_is_ampere_or_newer} on {_gpu_name} (cap={_cap})')


app = Flask(__name__)
#sockets = Sockets(app)
nerfreals:Dict[int, BaseReal] = {} #sessionid:BaseReal
opt = None
model = None  # loaded model tuple (vae, unet, pe, timesteps, audio_processor, use_autocast)
avatar = None  # loaded avatar tuple
        

#####webrtc###############################
pcs = set()

def randN(N)->int:
    '''生成长度为 N的随机数 '''
    min = pow(10, N - 1)
    max = pow(10, N)
    return random.randint(min, max - 1)

def build_nerfreal(sessionid:int)->BaseReal:
    opt.sessionid=sessionid
    if opt.model == 'wav2lip':
        from lipreal import LipReal
        nerfreal = LipReal(opt,model,avatar)
    elif opt.model == 'musetalk':
        from musereal import MuseReal
        nerfreal = MuseReal(opt,model,avatar)
    elif opt.model == 'ultralight':
        from lightreal import LightReal
        nerfreal = LightReal(opt,model,avatar)
    return nerfreal

#@app.route('/offer', methods=['POST'])
async def offer(request):
    try:
        params = await request.json()
        offer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])
    except Exception as e:
        logger.error(f"Error parsing offer request: {e}")
        return web.Response(
            content_type="application/json",
            text=json.dumps({"code": -1, "msg": f"Invalid request: {str(e)}"}),
            status=400
        )

    sessionid = randN(6) #len(nerfreals)
    nerfreals[sessionid] = None
    logger.info('sessionid=%d, session num=%d',sessionid,len(nerfreals))
    nerfreal = await asyncio.get_event_loop().run_in_executor(None, build_nerfreal,sessionid)
    nerfreals[sessionid] = nerfreal
    
    ice_server = RTCIceServer(urls='stun:stun.l.google.com:19302')
    pc = RTCPeerConnection(configuration=RTCConfiguration(iceServers=[ice_server]))
    pcs.add(pc)

    @pc.on("connectionstatechange")
    async def on_connectionstatechange():
        logger.info("Connection state is %s" % pc.connectionState)
        if pc.connectionState == "failed":
            await pc.close()
            pcs.discard(pc)
            del nerfreals[sessionid]
        if pc.connectionState == "closed":
            pcs.discard(pc)
            del nerfreals[sessionid]

    player = HumanPlayer(nerfreals[sessionid])
    audio_sender = pc.addTrack(player.audio)
    video_sender = pc.addTrack(player.video)
    capabilities = RTCRtpSender.getCapabilities("video")
    preferences = list(filter(lambda x: x.name == "H264", capabilities.codecs))
    preferences += list(filter(lambda x: x.name == "VP8", capabilities.codecs))
    preferences += list(filter(lambda x: x.name == "rtx", capabilities.codecs))
    transceiver = pc.getTransceivers()[1]
    transceiver.setCodecPreferences(preferences)

    await pc.setRemoteDescription(offer)

    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)

    return web.Response(
        content_type="application/json",
        text=json.dumps(
            {"sdp": pc.localDescription.sdp, "type": pc.localDescription.type, "sessionid":sessionid}
        ),
    )

async def human(request):
    try:
        params = await request.json()

        sessionid = params.get('sessionid',0)
        if params.get('interrupt'):
            nerfreals[sessionid].flush_talk()

        if params['type']=='echo':
            nerfreals[sessionid].put_msg_txt(params['text'])
        elif params['type']=='chat':
            asyncio.get_event_loop().run_in_executor(None, llm_response, params['text'],nerfreals[sessionid])                          

        return web.Response(
            content_type="application/json",
            text=json.dumps(
                {"code": 0, "msg":"ok"}
            ),
        )
    except Exception as e:
        logger.exception('exception:')
        return web.Response(
            content_type="application/json",
            text=json.dumps(
                {"code": -1, "msg": str(e)}
            ),
        )

async def interrupt_talk(request):
    try:
        params = await request.json()

        sessionid = params.get('sessionid',0)
        nerfreals[sessionid].flush_talk()
        
        return web.Response(
            content_type="application/json",
            text=json.dumps(
                {"code": 0, "msg":"ok"}
            ),
        )
    except Exception as e:
        logger.exception('exception:')
        return web.Response(
            content_type="application/json",
            text=json.dumps(
                {"code": -1, "msg": str(e)}
            ),
        )

async def humanaudio(request):
    try:
        form= await request.post()
        sessionid = int(form.get('sessionid',0))
        fileobj = form["file"]
        filename=fileobj.filename
        filebytes=fileobj.file.read()
        nerfreals[sessionid].put_audio_file(filebytes)

        return web.Response(
            content_type="application/json",
            text=json.dumps(
                {"code": 0, "msg":"ok"}
            ),
        )
    except Exception as e:
        logger.exception('exception:')
        return web.Response(
            content_type="application/json",
            text=json.dumps(
                {"code": -1, "msg": str(e)}
            ),
        )

async def set_audiotype(request):
    try:
        params = await request.json()

        sessionid = params.get('sessionid',0)    
        nerfreals[sessionid].set_custom_state(params['audiotype'],params['reinit'])

        return web.Response(
            content_type="application/json",
            text=json.dumps(
                {"code": 0, "msg":"ok"}
            ),
        )
    except Exception as e:
        logger.exception('exception:')
        return web.Response(
            content_type="application/json",
            text=json.dumps(
                {"code": -1, "msg": str(e)}
            ),
        )

async def record(request):
    try:
        params = await request.json()

        sessionid = params.get('sessionid',0)
        if params['type']=='start_record':
            nerfreals[sessionid].start_recording()
        elif params['type']=='end_record':
            nerfreals[sessionid].stop_recording()
        return web.Response(
            content_type="application/json",
            text=json.dumps(
                {"code": 0, "msg":"ok"}
            ),
        )
    except Exception as e:
        logger.exception('exception:')
        return web.Response(
            content_type="application/json",
            text=json.dumps(
                {"code": -1, "msg": str(e)}
            ),
        )

async def is_speaking(request):
    params = await request.json()

    sessionid = params.get('sessionid',0)
    return web.Response(
        content_type="application/json",
        text=json.dumps(
            {"code": 0, "data": nerfreals[sessionid].is_speaking()}
        ),
    )


async def tts_preview(request):
    try:
        params = await request.json()
        text = params.get('text', '').strip()
        voice = params.get('voice', opt.REF_FILE if opt else 'en-US-JennyNeural')
        if not text:
            return web.Response(status=400, text='no text')
        import edge_tts, io
        buf = io.BytesIO()
        communicate = edge_tts.Communicate(text, voice)
        async for chunk in communicate.stream():
            if chunk['type'] == 'audio':
                buf.write(chunk['data'])
        buf.seek(0)
        return web.Response(body=buf.read(), content_type='audio/mpeg')
    except Exception as e:
        logger.exception('tts_preview error:')
        return web.Response(status=500, text=str(e))

def find_ffmpeg():
    """Locate ffmpeg executable dynamically (handles Windows PATH refresh issues)."""
    import shutil
    exe = shutil.which('ffmpeg')
    if exe:
        return exe
    for p in [r'C:\ProgramData\chocolatey\bin\ffmpeg.exe', r'C:\ffmpeg\bin\ffmpeg.exe', r'C:\Users\ASUS-PC\scoop\shims\ffmpeg.exe']:
        if os.path.exists(p):
            return p
    return 'ffmpeg'

async def render_video(request):
    """Generate a full MP4 video from text (TTS + offline MuseTalk inference)."""
    try:
        import librosa
    except ImportError:
        return web.json_response({'code': 1, 'msg': 'librosa not installed. Run: pip install librosa'}, status=503)
    try:
        params = await request.json()
        text = params.get('text', '').strip()
        voice = params.get('voice', opt.REF_FILE if opt else 'en-US-JennyNeural')
        sessionid = params.get('sessionid', 0)
        if not text:
            return web.json_response({'code': 1, 'msg': 'no text'}, status=400)

        # If chat mode, fetch answer from RAG/Gemini first
        msg_type = params.get('type', 'echo')
        if msg_type == 'chat':
            from llm import get_rag_answer
            logger.info(f'[RenderVideo] Fetching RAG answer for: "{text}"')
            answer, error = await asyncio.get_event_loop().run_in_executor(None, get_rag_answer, text)
            if error:
                logger.error(f'[RenderVideo] RAG error: {error}')
                return web.json_response({'code': 1, 'msg': error}, status=503)
            if not answer:
                return web.json_response({'code': 1, 'msg': 'Empty RAG response'}, status=503)
            text = answer
            logger.info(f'[RenderVideo] RAG answer: "{text[:120]}..." ({len(text)} chars)')

        global model, avatar
        if model is None or avatar is None:
            return web.json_response({'code': 1, 'msg': 'model not loaded yet'}, status=503)

        vae, unet, pe, timesteps, audio_processor, use_autocast = model
        frame_list_cycle, mask_list_cycle, coord_list_cycle, mask_coords_list_cycle, input_latent_list_cycle = avatar
        device = unet.device
        length = len(input_latent_list_cycle)
        fps = opt.fps if opt else 25
        batch_size = opt.batch_size if opt else 4

        # Ensure videos directory exists (relative to BASE_DIR)
        videos_dir = os.path.join(DATA_DIR, 'videos')
        os.makedirs(videos_dir, exist_ok=True)
        ts = int(time.time())
        out_name = f"session{sessionid}_{ts}.mp4"
        out_path = os.path.join(videos_dir, out_name)
        temp_audio = os.path.join(videos_dir, f"_temp_audio_{ts}.wav")

        logger.info(f'[RenderVideo] Starting render for: "{text}"')

        # 1. Generate TTS audio
        t0 = time.perf_counter()
        import edge_tts
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(temp_audio)
        logger.info(f'[RenderVideo] TTS generated in {(time.perf_counter()-t0):.2f}s')

        # All blocking CPU/GPU work runs in a thread so the event loop
        # stays free to handle WebRTC keep-alives (prevents ICE timeout & disconnect).
        loop = asyncio.get_event_loop()

        def _blocking_render():
            from musetalk.utils.blending import get_image_blending

            # Initialize GFPGAN face restoration if requested
            face_enhancer = None
            if opt and getattr(opt, 'enhance', False):
                try:
                    from gfpgan import GFPGANer
                    model_path = os.path.join(MODELS_DIR, 'gfpgan', 'GFPGANv1.4.pth')
                    if os.path.exists(model_path):
                        face_enhancer = GFPGANer(
                            model_path=model_path,
                            upscale=1,
                            arch='clean',
                            channel_only=False,
                            bg_upsampler=None
                        )
                        logger.info('[RenderVideo] GFPGAN face enhancement enabled')
                    else:
                        logger.warning(f'[RenderVideo] GFPGAN model not found at {model_path}, skipping enhancement')
                except ImportError:
                    logger.warning('[RenderVideo] gfpgan not installed, run: pip install gfpgan')

            # 2. Load audio
            wav, _ = librosa.load(temp_audio, sr=16000)
            audio_duration = len(wav) / 16000.0
            nframes = int(audio_duration * fps)
            logger.info(f'[RenderVideo] Audio: {audio_duration:.2f}s -> {nframes} frames')

            # 2a. Silence detection
            spf = int(16000 / fps)
            silence_threshold = 0.015
            is_speaking_mask = []
            for f in range(nframes):
                seg = wav[f * spf:(f + 1) * spf]
                rms = np.sqrt(np.mean(seg**2)) if len(seg) > 0 else 0.0
                is_speaking_mask.append(rms >= silence_threshold)
            logger.info(f'[RenderVideo] {sum(1 for x in is_speaking_mask if not x)}/{nframes} silent frames')

            # 3. Whisper features
            t0 = time.perf_counter()
            whisper_features = audio_processor.audio2feat(wav)
            logger.info(f'[RenderVideo] Whisper features in {(time.perf_counter()-t0):.2f}s')

            # 4. Pre-load latents to GPU
            latents_gpu = [l.to(device=device, dtype=unet.model.dtype) for l in input_latent_list_cycle]

            def mirror_index(n, idx):
                turn = idx // n
                res = idx % n
                return res if turn % 2 == 0 else n - res - 1

            # 5. Batch inference + compositing — write directly to video to avoid RAM OOM
            frame_shape = frame_list_cycle[0].shape
            h, w = frame_shape[:2]
            temp_video = out_path.replace('.mp4', '_temp.mp4')
            writer = cv2.VideoWriter(temp_video, cv2.VideoWriter_fourcc(*'mp4v'), fps, (w, h))
            last_written = None
            written_count = 0

            with torch.no_grad():
                for i in range(0, nframes, batch_size):
                    batch_end = min(i + batch_size, nframes)
                    actual_batch = batch_end - i

                    speaking_indices = [j for j in range(actual_batch) if is_speaking_mask[i + j]]
                    silent_indices   = [j for j in range(actual_batch) if not is_speaking_mask[i + j]]

                    if speaking_indices:
                        latent_batch, whisper_batch = [], []
                        for j in speaking_indices:
                            idx = i + j
                            m_idx = mirror_index(length, idx)
                            latent_batch.append(latents_gpu[m_idx])
                            feat, _ = audio_processor.get_sliced_feature(
                                feature_array=whisper_features,
                                vid_idx=idx,
                                audio_feat_length=[2, 2],
                                fps=fps,
                            )
                            whisper_batch.append(feat)

                        latent_batch = torch.cat(latent_batch, dim=0)
                        audio_feature_batch = torch.from_numpy(
                            np.stack(whisper_batch, axis=0)
                        ).to(device=device, dtype=unet.model.dtype)
                        audio_feature_batch = pe(audio_feature_batch)

                        if use_autocast:
                            with torch.autocast(device_type=device.type, enabled=True):
                                pred_latents = unet.model(latent_batch, timesteps, encoder_hidden_states=audio_feature_batch).sample
                        else:
                            pred_latents = unet.model(latent_batch, timesteps, encoder_hidden_states=audio_feature_batch).sample
                        pred_latents = pred_latents.float().clamp(-10, 10)
                        recon = vae.decode_latents(pred_latents)

                    # Process speaking frames
                    for batch_j, j in enumerate(speaking_indices):
                        idx = i + j
                        m_idx = mirror_index(length, idx)
                        pred_frame = recon[batch_j]
                        ori_frame = frame_list_cycle[m_idx]
                        out_frame = ori_frame
                        if pred_frame is not None and np.isfinite(pred_frame).all():
                            mouth_half = pred_frame[pred_frame.shape[0] // 2:, :, :]
                            if not (np.std(mouth_half) < 4.0 and 90.0 <= np.mean(mouth_half) <= 165.0):
                                bbox = coord_list_cycle[m_idx]
                                x1, y1, x2, y2 = bbox
                                try:
                                    res_frame = cv2.resize(pred_frame.astype(np.uint8), (x2 - x1, y2 - y1), interpolation=cv2.INTER_LANCZOS4)
                                    combine_frame = get_image_blending(ori_frame, res_frame, bbox, mask_list_cycle[m_idx], mask_coords_list_cycle[m_idx])
                                    gaussian = cv2.GaussianBlur(combine_frame, (0, 0), 1.5)
                                    out_frame = cv2.addWeighted(combine_frame, 1.3, gaussian, -0.3, 0)
                                except MemoryError:
                                    logger.warning(f'[RenderVideo] MemoryError on speaking frame {idx}, using original')
                        # Apply GFPGAN face restoration if enabled (only on modified frames)
                        if face_enhancer is not None and out_frame is not ori_frame:
                            try:
                                x1f, y1f, x2f, y2f = bbox
                                margin = 20
                                x1c = max(0, x1f - margin)
                                y1c = max(0, y1f - margin)
                                x2c = min(out_frame.shape[1], x2f + margin)
                                y2c = min(out_frame.shape[0], y2f + margin)
                                face_crop = out_frame[y1c:y2c, x1c:x2c]
                                _, restored_crop, _ = face_enhancer.enhance(face_crop, has_aligned=False, only_center_face=False)
                                if restored_crop is not None and restored_crop.shape == face_crop.shape:
                                    out_frame[y1c:y2c, x1c:x2c] = restored_crop
                            except Exception as e:
                                logger.warning(f'[RenderVideo] GFPGAN enhancement failed on frame {idx}: {e}')
                        writer.write(out_frame)
                        last_written = out_frame

                    # Process silent frames
                    for j in silent_indices:
                        m_idx = mirror_index(length, i + j)
                        writer.write(frame_list_cycle[m_idx])
                        last_written = frame_list_cycle[m_idx]

                    written_count += actual_batch

                    # GC + cache clear every 50 batches
                    if (i // batch_size + 1) % 50 == 0:
                        import gc
                        gc.collect()
                        if hasattr(torch, 'cuda') and torch.cuda.is_available():
                            torch.cuda.empty_cache()
                        logger.info(f'[RenderVideo] {written_count}/{nframes} frames done (gc)...')
                    elif (i // batch_size + 1) % 10 == 0:
                        logger.info(f'[RenderVideo] {written_count}/{nframes} frames done...')

            logger.info(f'[RenderVideo] Inference complete. {written_count} frames written.')

            # 5b. Cooldown cross-fade — write directly, never accumulate
            if last_written is not None:
                cooldown_frames = int(0.8 * fps)
                last_f = last_written.astype(np.float32)
                for k in range(cooldown_frames):
                    m_idx = mirror_index(length, nframes + k)
                    idle_f = frame_list_cycle[m_idx].astype(np.float32)
                    alpha = k / max(1, cooldown_frames - 1)
                    blend = ((1 - alpha) * last_f + alpha * idle_f).astype(np.uint8)
                    writer.write(blend)
                    written_count += 1
                logger.info(f'[RenderVideo] Cooldown done. Total: {written_count} frames')
            writer.release()

            ffmpeg_exe = find_ffmpeg()
            cmd = [
                ffmpeg_exe, '-y',
                '-i', temp_video, '-i', temp_audio,
                '-c:v', 'libx264', '-preset', 'fast',
                '-c:a', 'aac', '-b:a', '128k',
                '-shortest', '-movflags', '+faststart',
                out_path,
            ]
            try:
                subprocess.run(cmd, check=True, capture_output=True)
                os.remove(temp_video)
                logger.info(f'[RenderVideo] Saved: {out_path}')
            except Exception as e:
                logger.warning(f'[RenderVideo] ffmpeg mux failed ({e}), keeping silent video')
                if os.path.exists(temp_video):
                    os.rename(temp_video, out_path)

            if os.path.exists(temp_audio):
                os.remove(temp_audio)

            return written_count

        total_frames = await loop.run_in_executor(None, _blocking_render)
        out_path = out_path if total_frames else None

        return web.Response(
            content_type='application/json',
            text=json.dumps({
                'code': 0,
                'video_url': f'/videos/{out_name}' if out_path else None,
                'frames': total_frames or 0,
            })
        )
    except Exception as e:
        logger.exception('[RenderVideo] error:')
        return web.json_response({'code': 1, 'msg': str(e)}, status=500)

async def on_shutdown(app):
    coros = [pc.close() for pc in pcs]
    await asyncio.gather(*coros)
    pcs.clear()

async def post(url,data):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url,data=data) as response:
                return await response.text()
    except aiohttp.ClientError as e:
        logger.info(f'Error: {e}')

async def run(push_url,sessionid):
    nerfreal = await asyncio.get_event_loop().run_in_executor(None, build_nerfreal,sessionid)
    nerfreals[sessionid] = nerfreal

    pc = RTCPeerConnection()
    pcs.add(pc)

    @pc.on("connectionstatechange")
    async def on_connectionstatechange():
        logger.info("Connection state is %s" % pc.connectionState)
        if pc.connectionState == "failed":
            await pc.close()
            pcs.discard(pc)

    player = HumanPlayer(nerfreals[sessionid])
    audio_sender = pc.addTrack(player.audio)
    video_sender = pc.addTrack(player.video)

    await pc.setLocalDescription(await pc.createOffer())
    answer = await post(push_url,pc.localDescription.sdp)
    await pc.setRemoteDescription(RTCSessionDescription(sdp=answer,type='answer'))
##########################################
if __name__ == '__main__':
    mp.set_start_method('spawn')
    parser = argparse.ArgumentParser()
    
    parser.add_argument('--fps', type=int, default=50, help="audio fps,must be 50")
    parser.add_argument('-l', type=int, default=10)
    parser.add_argument('-m', type=int, default=8)
    parser.add_argument('-r', type=int, default=10)

    parser.add_argument('--W', type=int, default=450, help="GUI width")
    parser.add_argument('--H', type=int, default=450, help="GUI height")

    parser.add_argument('--avatar_id', type=str, default='avator_1', help="define which avatar in data/avatars")
    parser.add_argument('--batch_size', type=int, default=16, help="infer batch")

    parser.add_argument('--customvideo_config', type=str, default='', help="custom action json")

    parser.add_argument('--tts', type=str, default='edgetts', help="tts service type")
    parser.add_argument('--REF_FILE', type=str, default="ur-PK-UzmaNeural",help="Voice model ID for edgetts")
    parser.add_argument('--enhance', action='store_true', help="Apply GFPGAN face restoration to pre-rendered frames (slower, higher quality)")
    parser.add_argument('--REF_TEXT', type=str, default=None)
    parser.add_argument('--TTS_SERVER', type=str, default='http://127.0.0.1:9880')

    parser.add_argument('--model', type=str, default='musetalk')

    parser.add_argument('--transport', type=str, default='rtcpush')
    parser.add_argument('--push_url', type=str, default='http://localhost:1985/rtc/v1/whip/?app=live&stream=livestream')

    parser.add_argument('--max_session', type=int, default=1)
    parser.add_argument('--listenport', type=int, default=8010, help="web listen port")

    opt = parser.parse_args()
    opt.customopt = []
    if opt.customvideo_config!='':
        config_path = opt.customvideo_config
        if not os.path.isabs(config_path):
            config_path = os.path.join(BASE_DIR, config_path)
        with open(config_path,'r') as file:
            opt.customopt = json.load(file)

    if opt.model == 'musetalk':
        from musereal import MuseReal,load_model,load_avatar,warm_up
        logger.info(opt)
        model = load_model()
        avatar = load_avatar(opt.avatar_id)
        warm_up(opt.batch_size,model)
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            reserved = torch.cuda.memory_reserved(0)/1024**3
            allocated = torch.cuda.memory_allocated(0)/1024**3
            logger.info(f'[VRAM] after warmup: allocated={allocated:.2f}GB reserved={reserved:.2f}GB')
    elif opt.model == 'wav2lip':
        from lipreal import LipReal,load_model,load_avatar,warm_up
        logger.info(opt)
        model = load_model(os.path.join(MODELS_DIR, "wav2lip.pth"))
        avatar = load_avatar(opt.avatar_id)
        warm_up(opt.batch_size,model,256)
    elif opt.model == 'ultralight':
        from lightreal import LightReal,load_model,load_avatar,warm_up
        logger.info(opt)
        model = load_model(opt)
        avatar = load_avatar(opt.avatar_id)
        warm_up(opt.batch_size,avatar,160)

    if opt.transport=='virtualcam':
        thread_quit = Event()
        nerfreals[0] = build_nerfreal(0)
        rendthrd = Thread(target=nerfreals[0].render,args=(thread_quit,))
        rendthrd.start()

    #############################################################################
    appasync = web.Application(client_max_size=1024**2*100)
    appasync.on_shutdown.append(on_shutdown)
    appasync.router.add_post("/offer", offer)
    appasync.router.add_post("/human", human)
    appasync.router.add_post("/humanaudio", humanaudio)
    appasync.router.add_post("/set_audiotype", set_audiotype)
    appasync.router.add_post("/record", record)
    appasync.router.add_post("/interrupt_talk", interrupt_talk)
    appasync.router.add_post("/is_speaking", is_speaking)
    appasync.router.add_post("/tts_preview", tts_preview)
    appasync.router.add_post("/render_video", render_video)
    appasync.router.add_static('/videos', path=os.path.join(DATA_DIR, 'videos'))
    appasync.router.add_static('/', path=FRONTEND_DIR)

    cors = aiohttp_cors.setup(appasync, defaults={
            "*": aiohttp_cors.ResourceOptions(
                allow_credentials=True,
                expose_headers="*",
                allow_headers="*",
            )
        })
    for route in list(appasync.router.routes()):
        cors.add(route)

    pagename='webrtcapi.html'
    if opt.transport=='rtmp':
        pagename='echoapi.html'
    elif opt.transport=='rtcpush':
        pagename='rtcpushapi.html'
    logger.info('start http server; http://<serverip>:'+str(opt.listenport)+'/'+pagename)
    logger.info('如果使用webrtc，推荐访问webrtc集成前端: http://<serverip>:'+str(opt.listenport)+'/dashboard.html')
    def run_server(runner):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(runner.setup())
        site = web.TCPSite(runner, '0.0.0.0', opt.listenport)
        loop.run_until_complete(site.start())
        if opt.transport=='rtcpush':
            for k in range(opt.max_session):
                push_url = opt.push_url
                if k!=0:
                    push_url = opt.push_url+str(k)
                loop.run_until_complete(run(push_url,k))
        loop.run_forever()    
    run_server(web.AppRunner(appasync))
