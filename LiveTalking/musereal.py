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

import math
import torch
import numpy as np
import subprocess
import os
import time
import torch.nn.functional as F
import cv2
import glob
import pickle

import queue
from queue import Queue
from threading import Thread, Event
import torch.multiprocessing as mp

from musetalk.utils.utils import get_file_type,get_video_fps,datagen
from musetalk.myutil import get_image_blending
from musetalk.utils.utils import load_all_model
from musetalk.whisper.audio2feature import Audio2Feature

from museasr import MuseASR
import asyncio
from av import AudioFrame, VideoFrame
from basereal import BaseReal

from tqdm import tqdm
from logger import logger

def load_model():
    # load model weights
    vae, unet, pe = load_all_model()
    device = torch.device("cuda" if torch.cuda.is_available() else ("mps" if (hasattr(torch.backends, "mps") and torch.backends.mps.is_available()) else "cpu"))
    timesteps = torch.tensor([0], device=device)
    model_dtype = torch.float16 if device.type == "cuda" else torch.float32
    logger.info(f'[MuseTalk] UNet/PE dtype={model_dtype}, VAE dtype=float32 on {device}')
    pe = pe.to(device=device, dtype=model_dtype)
    vae.vae = vae.vae.float().to(device)
    #vae.vae.share_memory().to(device)
    unet.model = unet.model.to(device=device, dtype=model_dtype)
    unet.device = device  # ensure unet.device matches where model weights actually are
    if device.type == "cuda" and hasattr(torch, 'compile'):
        try:
            import triton  # inductor backend requires triton (Linux only)
            unet.model = torch.compile(unet.model, mode='reduce-overhead')
            logger.info('[MuseTalk] UNet compiled with torch.compile (reduce-overhead)')
        except ImportError:
            logger.info('[MuseTalk] triton not available (Windows), skipping torch.compile')
        except Exception as e:
            logger.warning(f'[MuseTalk] torch.compile failed, using eager mode: {e}')
    # Initialize audio processor and Whisper model
    audio_processor = Audio2Feature(model_path="./models/whisper")
    return vae, unet, pe, timesteps, audio_processor

def load_avatar(avatar_id):
    #self.video_path = '' #video_path
    #self.bbox_shift = opt.bbox_shift
    avatar_path = f"./data/avatars/{avatar_id}"
    full_imgs_path = f"{avatar_path}/full_imgs" 
    coords_path = f"{avatar_path}/coords.pkl"
    latents_out_path= f"{avatar_path}/latents.pt"
    video_out_path = f"{avatar_path}/vid_output/"
    mask_out_path =f"{avatar_path}/mask"
    mask_coords_path =f"{avatar_path}/mask_coords.pkl"
    avatar_info_path = f"{avatar_path}/avator_info.json"
    # self.avatar_info = {
    #     "avatar_id":self.avatar_id,
    #     "video_path":self.video_path,
    #     "bbox_shift":self.bbox_shift   
    # }

    input_latent_list_cycle = torch.load(latents_out_path, map_location='cpu')  #,weights_only=True
    with open(coords_path, 'rb') as f:
        coord_list_cycle = pickle.load(f)
    input_img_list = glob.glob(os.path.join(full_imgs_path, '*.[jpJP][pnPN]*[gG]'))
    input_img_list = sorted(input_img_list, key=lambda x: int(os.path.splitext(os.path.basename(x))[0]))
    frame_list_cycle = read_imgs(input_img_list)
    with open(mask_coords_path, 'rb') as f:
        mask_coords_list_cycle = pickle.load(f)
    input_mask_list = glob.glob(os.path.join(mask_out_path, '*.[jpJP][pnPN]*[gG]'))
    input_mask_list = sorted(input_mask_list, key=lambda x: int(os.path.splitext(os.path.basename(x))[0]))
    mask_list_cycle = read_imgs(input_mask_list)
    return frame_list_cycle,mask_list_cycle,coord_list_cycle,mask_coords_list_cycle,input_latent_list_cycle

@torch.no_grad()
def warm_up(batch_size,model):
    # 预热函数
    logger.info('warmup model...')
    vae, unet, pe, timesteps, audio_processor = model
    #batch_size = 16
    #timesteps = torch.tensor([0], device=unet.device)
    whisper_batch = np.ones((batch_size, 50, 384), dtype=np.uint8)
    latent_batch = torch.ones(batch_size, 8, 32, 32).to(unet.device)

    audio_feature_batch = torch.from_numpy(whisper_batch)
    audio_feature_batch = audio_feature_batch.to(device=unet.device, dtype=unet.model.dtype)
    audio_feature_batch = pe(audio_feature_batch)
    latent_batch = latent_batch.to(dtype=unet.model.dtype)
    pred_latents = unet.model(latent_batch,
                              timesteps,
                              encoder_hidden_states=audio_feature_batch).sample
    vae.decode_latents(pred_latents)

def read_imgs(img_list):
    frames = []
    logger.info('reading images...')
    for img_path in tqdm(img_list):
        frame = cv2.imread(img_path)
        frames.append(frame)
    return frames

def __mirror_index(size, index):
    #size = len(self.coord_list_cycle)
    turn = index // size
    res = index % size
    if turn % 2 == 0:
        return res
    else:
        return size - res - 1 

@torch.no_grad()
def inference(quit_event,batch_size,input_latent_list_cycle,audio_feat_queue,audio_out_queue,res_frame_queue,
              vae, unet, pe,timesteps): #vae, unet, pe,timesteps
    
    # vae, unet, pe = load_diffusion_model()
    # device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    # timesteps = torch.tensor([0], device=device)
    # pe = pe.half()
    # vae.vae = vae.vae.half()
    # unet.model = unet.model.half()
    
    length = len(input_latent_list_cycle)
    # Pre-move all latents to GPU once — avoids repeated CPU→GPU transfer in the hot loop
    input_latent_list_cycle = [l.to(device=unet.device, dtype=unet.model.dtype) for l in input_latent_list_cycle]
    logger.info(f'[MuseTalk] {length} latents pre-loaded to {unet.device}')
    index = 0
    count=0
    counttime=0
    skipped_batches=0
    logger.info('start inference')
    while not quit_event.is_set():
        starttime=time.perf_counter()
        try:
            whisper_chunks = audio_feat_queue.get(block=True, timeout=1)
        except queue.Empty:
            continue
        # Catch-up: if multiple batches are queued, drop old ones to reduce latency
        dropped_audio = []
        while not quit_event.is_set():
            try:
                next_whisper_chunks = audio_feat_queue.get_nowait()
                dropped_audio.extend([audio_out_queue.get_nowait() for _ in range(batch_size*2)])
                whisper_chunks = next_whisper_chunks
                skipped_batches += 1
            except queue.Empty:
                break
        if skipped_batches > 0 and skipped_batches % 10 == 0:
            logger.info(f'[Perf] Dropped {skipped_batches} old batches to catch up')
        is_all_silence=True
        audio_frames = []
        for _ in range(batch_size*2):
            frame,type,eventpoint = audio_out_queue.get()
            audio_frames.append((frame,type,eventpoint))
            if type==0:
                is_all_silence=False
        if is_all_silence:
            for i in range(batch_size):
                res_frame_queue.put((None,__mirror_index(length,index),audio_frames[i*2:i*2+2]))
                index = index + 1
        else:
            t_total = time.perf_counter()
            t=time.perf_counter()
            whisper_batch = np.stack(whisper_chunks)
            latent_batch = []
            for i in range(batch_size):
                idx = __mirror_index(length,index+i)
                latent = input_latent_list_cycle[idx]
                latent_batch.append(latent)
            latent_batch = torch.cat(latent_batch, dim=0)
            audio_feature_batch = torch.from_numpy(whisper_batch)
            audio_feature_batch = audio_feature_batch.to(device=unet.device,
                                                            dtype=unet.model.dtype)
            audio_feature_batch = pe(audio_feature_batch)
            latent_batch = latent_batch.to(device=unet.device, dtype=unet.model.dtype)
            t_prep = time.perf_counter() - t

            t=time.perf_counter()
            with torch.autocast(device_type=unet.device.type, enabled=(unet.device.type == 'cuda')):
                pred_latents = unet.model(latent_batch,
                                            timesteps,
                                            encoder_hidden_states=audio_feature_batch).sample
            t_unet = time.perf_counter() - t

            t=time.perf_counter()
            recon = vae.decode_latents(pred_latents)
            t_vae = time.perf_counter() - t

            counttime += (time.perf_counter() - t_total)
            count += batch_size
            if count>=100:
                logger.info(f"------actual avg infer fps:{count/counttime:.4f}")
                count=0
                counttime=0

            t=time.perf_counter()
            for i,res_frame in enumerate(recon):
                res_frame_queue.put((res_frame,__mirror_index(length,index),audio_frames[i*2:i*2+2]))
                index = index + 1
            t_queue = time.perf_counter() - t
            logger.debug(f'[Timing] prep={t_prep*1000:.0f}ms unet={t_unet*1000:.0f}ms vae={t_vae*1000:.0f}ms queue_put={t_queue*1000:.0f}ms')            
    logger.info('musereal inference processor stop')

class MuseReal(BaseReal):
    @torch.no_grad()
    def __init__(self, opt, model, avatar):
        super().__init__(opt)
        #self.opt = opt # shared with the trainer's opt to support in-place modification of rendering parameters.
        # self.W = opt.W
        # self.H = opt.H

        self.fps = opt.fps # 20 ms per frame

        self.batch_size = opt.batch_size
        self.idx = 0
        self.res_frame_queue = mp.Queue(self.batch_size*4)

        self.vae, self.unet, self.pe, self.timesteps, self.audio_processor = model
        self.frame_list_cycle,self.mask_list_cycle,self.coord_list_cycle,self.mask_coords_list_cycle, self.input_latent_list_cycle = avatar
        #self.__loadavatar()

        self.asr = MuseASR(opt,self,self.audio_processor)
        self.asr.warm_up()
        
        self.render_event = mp.Event()

    # def __del__(self):
    #     logger.info(f'musereal({self.sessionid}) delete')
    

    def __mirror_index(self, index):
        size = len(self.coord_list_cycle)
        turn = index // size
        res = index % size
        if turn % 2 == 0:
            return res
        else:
            return size - res - 1  

    def __warm_up(self): 
        self.asr.run_step()
        whisper_chunks = self.asr.get_next_feat()
        whisper_batch = np.stack(whisper_chunks)
        latent_batch = []
        for i in range(self.batch_size):
            idx = self.__mirror_index(self.idx+i)
            latent = self.input_latent_list_cycle[idx]
            latent_batch.append(latent)
        latent_batch = torch.cat(latent_batch, dim=0)
        logger.info('infer=======')
        # for i, (whisper_batch,latent_batch) in enumerate(gen):
        audio_feature_batch = torch.from_numpy(whisper_batch)
        audio_feature_batch = audio_feature_batch.to(device=self.unet.device,
                                                        dtype=self.unet.model.dtype)
        audio_feature_batch = self.pe(audio_feature_batch)
        latent_batch = latent_batch.to(dtype=self.unet.model.dtype)

        pred_latents = self.unet.model(latent_batch, 
                                    self.timesteps, 
                                    encoder_hidden_states=audio_feature_batch).sample
        recon = self.vae.decode_latents(pred_latents)
      

    def paste_back_frame(self,pred_frame,idx:int):
        bbox = self.coord_list_cycle[idx]
        ori_frame = self.frame_list_cycle[idx].copy()
        x1, y1, x2, y2 = bbox

        res_frame = cv2.resize(pred_frame.astype(np.uint8),(x2-x1,y2-y1))
        mask = self.mask_list_cycle[idx]
        mask_crop_box = self.mask_coords_list_cycle[idx]

        combine_frame = get_image_blending(ori_frame,res_frame,bbox,mask,mask_crop_box)
        return combine_frame
            
    def _asr_loop(self, quit_event):
        while not quit_event.is_set():
            self.asr.run_step()

    def render(self,quit_event,loop=None,audio_track=None,video_track=None):
        #if self.opt.asr:
        #     self.asr.warm_up()

        self.init_customindex()
        self.tts.render(quit_event)
        
        infer_quit_event = Event()
        infer_thread = Thread(target=inference, args=(infer_quit_event,self.batch_size,self.input_latent_list_cycle,
                                           self.asr.feat_queue,self.asr.output_queue,self.res_frame_queue,
                                           self.vae, self.unet, self.pe,self.timesteps))
        infer_thread.start()

        asr_quit_event = Event()
        asr_thread = Thread(target=self._asr_loop, args=(asr_quit_event,))
        asr_thread.daemon = True
        asr_thread.start()
        
        process_quit_event = Event()
        process_thread = Thread(target=self.process_frames, args=(process_quit_event,loop,audio_track,video_track))
        process_thread.start()

        while not quit_event.is_set():
            if video_track and video_track._queue.qsize() >= 2 * self.opt.batch_size:
                logger.debug('video queue backlog qsize=%d', video_track._queue.qsize())
                time.sleep(0.01)
            else:
                time.sleep(0.005)
        logger.info('musereal thread stop')

        asr_quit_event.set()
        asr_thread.join(timeout=1)

        infer_quit_event.set()
        infer_thread.join()

        process_quit_event.set()
        process_thread.join()
            
