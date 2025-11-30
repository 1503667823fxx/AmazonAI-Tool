import time
import requests
import os
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
import streamlit as st

# ==========================================
# 配置区域
# ==========================================
LUMA_API_URL = "https://api.lumalabs.ai/dream-machine/v1/generations"

def _download_video(url, output_dir="temp/videos"):
    """
    内部工具：下载生成的视频 URL 到本地文件系统
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    filename = f"{uuid.uuid4()}.mp4"
    filepath = os.path.join(output_dir, filename)
    
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        return filepath
    except Exception as e:
        print(f"下载视频失败: {e}")
        return None

def _trigger_luma_generation(api_key, prompt, ref_img_url=None):
    """
    提交生成任务给 Luma API
    """
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # 针对亚马逊电商的 Prompt 增强工程
    enhanced_prompt = f"Product cinematic shot, 4k resolution, professional commercial lighting, high detail. {prompt}"
    
    payload = {
        "prompt": enhanced_prompt,
        "aspect_ratio": "16:9", # 或根据 UI 设置动态调整
        "loop": False
    }

    # 关键：如果有参考图 (首图)，使用图生视频功能，保证产品一致性
    if ref_img_url:
        payload["keyframes"] = {
            "frame0": {
                "type": "image",
                "url": ref_img_url
            }
        }

    response = requests.post(LUMA_API_URL, json=payload, headers=headers)
    if response.status_code != 201:
        raise Exception(f"Luma API 提交失败: {response.text}")
    
    return response.json()['id']

def _poll_luma_status(api_key, generation_id):
    """
    轮询检查生成状态
    """
    headers = {"Authorization": f"Bearer {api_key}"}
    url = f"{LUMA_API_URL}/{generation_id}"
    
    while True:
        response = requests.get(url, headers=headers)
        data = response.json()
        state = data.get("state")
        
        if state == "completed":
            return data['assets']['video'] # 返回视频 URL
        elif state == "failed":
            raise Exception("Luma 生成任务报告失败")
        
        time.sleep(3) # 每3秒检查一次，避免撞墙

def generate_single_scene(api_key, scene_data, ref_img_url=None):
    """
    处理单个场景的全流程：提交 -> 等待 -> 下载
    """
    prompt = scene_data.get('visual_prompt')
    scene_id = scene_data.get('scene_id')
    
    try:
        # 1. 提交任务
        gen_id = _trigger_luma_generation(api_key, prompt, ref_img_url)
        print(f"场景 {scene_id} 已提交任务 ID: {gen_id}")
        
        # 2. 轮询等待
        video_url = _poll_luma_status(api_key, gen_id)
        
        # 3. 下载到本地
        local_path = _download_video(video_url)
        
        return {
            "scene_id": scene_id,
            "status": "success",
            "video_path": local_path,
            "original_url": video_url
        }
        
    except Exception as e:
        return {
            "scene_id": scene_id,
            "status": "error",
            "error_msg": str(e)
        }

def batch_generate_videos(api_key, scenes_list, ref_img_url=None):
    """
    [核心入口] 并发生成所有分镜视频
    
    Args:
        api_key (str): Luma API Key
        scenes_list (list): 包含 scene_id 和 visual_prompt 的列表
        ref_img_url (str): 商品主图 URL (用于保持一致性)
        
    Returns:
        dict: {scene_id: video_path} 的映射字典
    """
    results = {}
    
    # 使用线程池并发处理，极大缩短总耗时
    # max_workers=5 表示同时请求5个视频生成，视 API 额度而定
    with ThreadPoolExecutor(max_workers=5) as executor:
        # 提交所有任务
        future_to_scene = {
            executor.submit(generate_single_scene, api_key, scene, ref_img_url): scene['scene_id']
            for scene in scenes_list
        }
        
        # 处理完成的任务
        for future in as_completed(future_to_scene):
            scene_id = future_to_scene[future]
            try:
                data = future.result()
                if data['status'] == 'success':
                    results[scene_id] = data['video_path']
                else:
                    print(f"场景 {scene_id} 生成失败: {data['error_msg']}")
            except Exception as exc:
                print(f"场景 {scene_id} 产生异常: {exc}")
                
    return results
