"""
Google Veo 3.1 API Service - 只使用官方Google GenAI SDK

基于官方文档: https://ai.google.dev/gemini-api/docs/video
"""

import os
import time
import base64
from datetime import datetime
from typing import Optional, Dict, Any
import streamlit as st

from google import genai
from google.genai import types


class VeoAPIService:
    """Google Veo 3.1 API服务 - 只使用官方SDK"""
    
    def __init__(self):
        self.api_key = st.secrets["GOOGLE_API_KEY"]
        self.client = genai.Client(api_key=self.api_key)
        self.model_id = "veo-3.1-generate-preview"
        
        print(f"[DEBUG] 使用官方Google GenAI SDK")
        print(f"  模型ID: {self.model_id}")
    
    def generate_video(
        self,
        prompt: str,
        duration: int = 4,
        aspect_ratio: str = "16:9",
        quality: str = "1080p",
        reference_image: Optional[bytes] = None,
        negative_prompt: Optional[str] = None,
        seed: Optional[int] = None,
        generate_audio: bool = False
    ) -> Dict[str, Any]:
        """生成视频"""
        try:
            # 构建配置
            config_params = {
                "aspect_ratio": aspect_ratio,
                "duration_seconds": duration,
                "resolution": quality.lower(),
                "generate_audio": generate_audio
            }
            
            # 添加可选参数
            if seed is not None:
                config_params["seed"] = seed
            
            config = types.GenerateVideosConfig(**config_params)
            
            # 生成视频
            if reference_image:
                # 图片到视频
                image = types.Image.from_bytes(reference_image)
                operation = self.client.models.generate_videos(
                    model=self.model_id,
                    prompt=prompt,
                    image=image,
                    config=config
                )
            else:
                # 文本到视频
                operation = self.client.models.generate_videos(
                    model=self.model_id,
                    prompt=prompt,
                    config=config
                )
            
            print(f"[DEBUG] SDK操作已创建: {operation.name}")
            
            return {
                "success": True,
                "job_id": operation.name.split("/")[-1],
                "operation_name": operation.name,
                "operation": operation,  # 保存操作对象
                "status": "processing",
                "message": "视频生成任务已创建"
            }
            
        except Exception as e:
            print(f"[DEBUG] SDK生成失败: {str(e)}")
            return {
                "success": False,
                "error": f"生成失败: {str(e)}"
            }
    
    def get_video_status(self, operation_name: str, operation=None) -> Dict[str, Any]:
        """获取视频生成状态"""
        try:
            if not operation:
                # 如果没有操作对象，根据名称重新获取
                operation = self.client.operations.get(operation_name)
            else:
                # 刷新操作状态
                operation = self.client.operations.get(operation)
            
            if operation.done:
                if hasattr(operation, 'error') and operation.error:
                    return {
                        "status": "failed",
                        "progress": 0,
                        "error": str(operation.error)
                    }
                else:
                    # 获取生成的视频
                    generated_video = operation.response.generated_videos[0]
                    
                    print(f"[DEBUG] 开始下载视频文件...")
                    
                    # 下载视频字节数据
                    video_file = self.client.files.download(file=generated_video.video)
                    
                    # 获取视频字节数据
                    video_bytes = None
                    if hasattr(generated_video.video, 'video_bytes'):
                        video_bytes = base64.b64encode(generated_video.video.video_bytes).decode('utf-8')
                        print(f"[DEBUG] 从video_bytes获取数据，大小: {len(generated_video.video.video_bytes)} bytes")
                    elif hasattr(video_file, 'read'):
                        video_content = video_file.read()
                        video_bytes = base64.b64encode(video_content).decode('utf-8')
                        print(f"[DEBUG] 从下载文件获取数据，大小: {len(video_content)} bytes")
                    elif isinstance(video_file, bytes):
                        video_bytes = base64.b64encode(video_file).decode('utf-8')
                        print(f"[DEBUG] 直接从字节数据获取，大小: {len(video_file)} bytes")
                    
                    if video_bytes:
                        print(f"[DEBUG] 视频下载完成，base64编码长度: {len(video_bytes)}")
                    else:
                        print(f"[DEBUG] 警告：无法获取视频字节数据")
                    
                    return {
                        "status": "completed",
                        "progress": 100,
                        "video_bytes": video_bytes,
                        "message": "视频生成完成",
                        "operation": operation  # 保持操作对象
                    }
            else:
                return {
                    "status": "processing",
                    "progress": 50,
                    "message": "正在生成视频...",
                    "operation": operation  # 保持操作对象
                }
                
        except Exception as e:
            print(f"[DEBUG] SDK状态查询失败: {str(e)}")
            return {
                "status": "error",
                "progress": 0,
                "error": f"状态查询失败: {str(e)}"
            }


# 全局服务实例
_veo_service: Optional[VeoAPIService] = None


def get_veo_service() -> Optional[VeoAPIService]:
    """获取Veo服务实例"""
    global _veo_service
    
    try:
        if "GOOGLE_API_KEY" not in st.secrets:
            print("[DEBUG] 没有找到GOOGLE_API_KEY")
            return None
        
        if _veo_service is None:
            _veo_service = VeoAPIService()
        
        return _veo_service
    except Exception as e:
        print(f"[DEBUG] 创建Veo服务失败: {str(e)}")
        return None


def generate_video_sync(
    prompt: str,
    duration: int = 4,
    aspect_ratio: str = "16:9",
    quality: str = "1080p",
    reference_image: Optional[bytes] = None,
    negative_prompt: Optional[str] = None,
    seed: Optional[int] = None,
    generate_audio: bool = False
) -> Dict[str, Any]:
    """同步生成视频（用于Streamlit）"""
    service = get_veo_service()
    if not service:
        return {
            "success": False,
            "error": "Veo服务未配置，请检查GOOGLE_API_KEY"
        }
    
    return service.generate_video(
        prompt=prompt,
        duration=duration,
        aspect_ratio=aspect_ratio,
        quality=quality,
        reference_image=reference_image,
        negative_prompt=negative_prompt,
        seed=seed,
        generate_audio=generate_audio
    )


def get_video_status_sync(operation_name: str, operation=None) -> Dict[str, Any]:
    """同步获取视频状态（用于Streamlit）"""
    service = get_veo_service()
    if not service:
        return {
            "status": "error",
            "error": "Veo服务未配置"
        }
    
    return service.get_video_status(operation_name, operation)
