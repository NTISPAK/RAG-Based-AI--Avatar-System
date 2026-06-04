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

if torch.cuda.is_available():
    _gpu_name = torch.cuda.get_device_name(0)
    _has_tensor_cores = torch.cuda.get_device_capability()[0] >= 7 and "16" not in _gpu_name
    torch.backends.cudnn.benchmark = _has_tensor_cores
    logger.info(f'[CUDA] cudnn.benchmark={_has_tensor_cores} on {_gpu_name}')


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
    # elif opt.model == 'ernerf':
    #     from nerfreal import NeRFReal
    #     nerfreal = NeRFReal(opt,model,avatar)
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

    # if len(nerfreals) >= opt.max_session:
    #     logger.info('reach max session')
    #     return web.Response(
    #         content_type="application/json",
    #         text=json.dumps(
    #             {"code": -1, "msg": "reach max session"}
    #         ),
    #     )
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
            # gc.collect()

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

    #return jsonify({"sdp": pc.localDescription.sdp, "type": pc.localDescription.type})

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
            #nerfreals[sessionid].put_msg_txt(res)

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
            # nerfreals[sessionid].put_msg_txt(params['text'])
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

async def render_video(request):
    """Generate a full MP4 video from text (TTS + offline MuseTalk inference)."""
    try:
        import librosa
    except ImportError:
        return web.Response(status=503, text='librosa not installed. Run: pip install librosa')
    try:
        params = await request.json()
        text = params.get('text', '').strip()
        voice = params.get('voice', opt.REF_FILE if opt else 'en-US-JennyNeural')
        sessionid = params.get('sessionid', 0)
        if not text:
            return web.Response(status=400, text='no text')

        global model, avatar
        if model is None or avatar is None:
            return web.Response(status=503, text='model not loaded yet')

        vae, unet, pe, timesteps, audio_processor, use_autocast = model
        frame_list_cycle, mask_list_cycle, coord_list_cycle, mask_coords_list_cycle, input_latent_list_cycle = avatar
        device = unet.device
        length = len(input_latent_list_cycle)
        fps = opt.fps if opt else 25
        batch_size = opt.batch_size if opt else 4

        # Ensure videos directory exists
        videos_dir = os.path.join('data', 'videos')
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

        # 2. Load audio
        wav, _ = librosa.load(temp_audio, sr=16000)
        audio_duration = len(wav) / 16000.0
        num_video_frames = int(audio_duration * fps)
        logger.info(f'[RenderVideo] Audio: {audio_duration:.2f}s -> {num_video_frames} frames')

        # 3. Extract Whisper features
        t0 = time.perf_counter()
        whisper_features = audio_processor.audio2feat(wav)
        logger.info(f'[RenderVideo] Whisper features in {(time.perf_counter()-t0):.2f}s')

        # 4. Pre-load latents to GPU
        input_latent_list_cycle = [l.to(device=device, dtype=unet.model.dtype) for l in input_latent_list_cycle]

        # 5. Batch inference + compositing
        output_frames = []
        from musetalk.utils.blending import get_image_blending

        def mirror_index(length, index):
            turn = index // length
            res = index % length
            if turn % 2 == 0:
                return res
            return length - res - 1

        with torch.no_grad():
            for i in range(0, num_video_frames, batch_size):
                batch_end = min(i + batch_size, num_video_frames)
                actual_batch = batch_end - i

                latent_batch = []
                whisper_batch = []
                for j in range(actual_batch):
                    idx = i + j
                    m_idx = mirror_index(length, idx)
                    latent_batch.append(input_latent_list_cycle[m_idx])
                    feat, _ = audio_processor.get_sliced_feature(
                        feature_array=whisper_features,
                        vid_idx=idx,
                        audio_feat_length=[2, 2],
                        fps=fps,
                    )
                    whisper_batch.append(feat)

                latent_batch = torch.cat(latent_batch, dim=0)
                whisper_batch = np.stack(whisper_batch, axis=0)
                audio_feature_batch = torch.from_numpy(whisper_batch).to(device=device, dtype=unet.model.dtype)
                audio_feature_batch = pe(audio_feature_batch)

                # UNet
                if use_autocast:
                    with torch.autocast(device_type=device.type, enabled=True):
                        pred_latents = unet.model(latent_batch, timesteps, encoder_hidden_states=audio_feature_batch).sample
                else:
                    pred_latents = unet.model(latent_batch, timesteps, encoder_hidden_states=audio_feature_batch).sample
                pred_latents = pred_latents.float().clamp(-10, 10)

                # VAE
                recon = vae.decode_latents(pred_latents)

                # Composite each frame
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
                    logger.info(f'[RenderVideo] {len(output_frames)}/{num_video_frames} frames done...')

        logger.info(f'[RenderVideo] Inference complete. {len(output_frames)} frames generated.')

        # 6. Write video with ffmpeg
        if output_frames:
            h, w = output_frames[0].shape[:2]
            temp_video = out_path.replace('.mp4', '_temp.mp4')
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            writer = cv2.VideoWriter(temp_video, fourcc, fps, (w, h))
            for frame in output_frames:
                writer.write(frame)
            writer.release()

            # Mux with audio
            cmd = [
                'ffmpeg', '-y',
                '-i', temp_video,
                '-i', temp_audio,
                '-c:v', 'libx264', '-preset', 'fast',
                '-c:a', 'aac', '-b:a', '128k',
                '-shortest',
                '-movflags', '+faststart',
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
        else:
            out_path = None

        # Cleanup temp audio
        if os.path.exists(temp_audio):
            os.remove(temp_audio)

        return web.Response(
            content_type='application/json',
            text=json.dumps({
                'code': 0,
                'video_url': f'/videos/{out_name}' if out_path else None,
                'frames': len(output_frames),
            })
        )
    except Exception as e:
        logger.exception('[RenderVideo] error:')
        return web.Response(status=500, text=str(e))

async def on_shutdown(app):
    # close peer connections
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
# os.environ['MKL_SERVICE_FORCE_INTEL'] = '1'
# os.environ['MULTIPROCESSING_METHOD'] = 'forkserver'                                                    
if __name__ == '__main__':
    mp.set_start_method('spawn')
    parser = argparse.ArgumentParser()
    
    # audio FPS
    parser.add_argument('--fps', type=int, default=50, help="audio fps,must be 50")
    # sliding window left-middle-right length (unit: 20ms)
    parser.add_argument('-l', type=int, default=10)
    parser.add_argument('-m', type=int, default=8)
    parser.add_argument('-r', type=int, default=10)

    parser.add_argument('--W', type=int, default=450, help="GUI width")
    parser.add_argument('--H', type=int, default=450, help="GUI height")

    #musetalk opt
    parser.add_argument('--avatar_id', type=str, default='avator_1', help="define which avatar in data/avatars")
    #parser.add_argument('--bbox_shift', type=int, default=5)
    parser.add_argument('--batch_size', type=int, default=16, help="infer batch")

    parser.add_argument('--customvideo_config', type=str, default='', help="custom action json")

    parser.add_argument('--tts', type=str, default='edgetts', help="tts service type") #xtts gpt-sovits cosyvoice fishtts tencent doubao indextts2 azuretts
    parser.add_argument('--REF_FILE', type=str, default="en-US-JennyNeural",help="Voice model ID for edgetts (default: en-US-JennyNeural). For azuretts, use Azure voice IDs like en-US-JennyMultilingualNeural")
    parser.add_argument('--REF_TEXT', type=str, default=None)
    parser.add_argument('--TTS_SERVER', type=str, default='http://127.0.0.1:9880') # http://localhost:9000
    # parser.add_argument('--CHARACTER', type=str, default='test')
    # parser.add_argument('--EMOTION', type=str, default='default')

    parser.add_argument('--model', type=str, default='musetalk') #musetalk wav2lip ultralight

    parser.add_argument('--transport', type=str, default='rtcpush') #webrtc rtcpush virtualcam
    parser.add_argument('--push_url', type=str, default='http://localhost:1985/rtc/v1/whip/?app=live&stream=livestream') #rtmp://localhost/live/livestream

    parser.add_argument('--max_session', type=int, default=1)  #multi session count
    parser.add_argument('--listenport', type=int, default=8010, help="web listen port")

    opt = parser.parse_args()
    #app.config.from_object(opt)
    #print(app.config)
    opt.customopt = []
    if opt.customvideo_config!='':
        with open(opt.customvideo_config,'r') as file:
            opt.customopt = json.load(file)

    # if opt.model == 'ernerf':       
    #     from nerfreal import NeRFReal,load_model,load_avatar
    #     model = load_model(opt)
    #     avatar = load_avatar(opt) 
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
        model = load_model("./models/wav2lip.pth")
        avatar = load_avatar(opt.avatar_id)
        warm_up(opt.batch_size,model,256)
    elif opt.model == 'ultralight':
        from lightreal import LightReal,load_model,load_avatar,warm_up
        logger.info(opt)
        model = load_model(opt)
        avatar = load_avatar(opt.avatar_id)
        warm_up(opt.batch_size,avatar,160)

    # if opt.transport=='rtmp':
    #     thread_quit = Event()
    #     nerfreals[0] = build_nerfreal(0)
    #     rendthrd = Thread(target=nerfreals[0].render,args=(thread_quit,))
    #     rendthrd.start()
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
    appasync.router.add_static('/videos', path=os.path.join('data', 'videos'))
    appasync.router.add_static('/',path='web')

    # Configure default CORS settings.
    cors = aiohttp_cors.setup(appasync, defaults={
            "*": aiohttp_cors.ResourceOptions(
                allow_credentials=True,
                expose_headers="*",
                allow_headers="*",
            )
        })
    # Configure CORS on all routes.
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
    #Thread(target=run_server, args=(web.AppRunner(appasync),)).start()
    run_server(web.AppRunner(appasync))

    #app.on_shutdown.append(on_shutdown)
    #app.router.add_post("/offer", offer)

    # print('start websocket server')
    # server = pywsgi.WSGIServer(('0.0.0.0', 8000), app, handler_class=WebSocketHandler)
    # server.serve_forever()
    
    
