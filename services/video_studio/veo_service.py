"""
Google Veo 3.1 API Service - 云端Streamlit兼容版

基于官方文档: https://ai.google.dev/gemini-api/docs/video
针对云端Streamlit环境优化
"""

import os
import time
import base64
from datetime import datetime
from typing import Optional, Dict, Any
import streamlit as st

# 尝试导入Google GenAI SDK
try:
    from google import genai
    from google.genai import types
    SDK_AVAILABLE = True
    print("[DEBUG] Google GenAI SDK 可用")
except ImportError as e:
    SDK_AVAILABLE = False
    print(f"[DEBUG] Google GenAI SDK 不可用: {str(e)}")
    print("[DEBUG] 这在云端Streamlit环境中是常见的")


class VeoAPIService:
    """Google Veo 3.1 API服务 - 云端兼容版"""
    
    def __init__(self):
        self.api_key = st.secrets["GOOGLE_API_KEY"]
        
        if not SDK_AVAILABLE:
            st.error("⚠️ Google GenAI SDK 不可用")
            st.info("💡 这通常发生在云端Streamlit环境中，SDK可能未正确安装")
            st.code("pip install google-genai")
            raise RuntimeError("Google GenAI SDK 不可用")
        
        try:
            self.client = genai.Client(api_key=self.api_key)
            self.model_id = "veo-3.1-generate-preview"
            print(f"[DEBUG] 使用官方Google GenAI SDK")
            print(f"  模型ID: {self.model_id}")
        except Exception as e:
            st.error(f"⚠️ 初始化Google GenAI客户端失败: {str(e)}")
            raise
    
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
                "resolution": quality.lower()
            }
            
            # 添加可选参数（排除不支持的参数）
            if seed is not None:
                config_params["seed"] = seed
            
            # 注意：generate_audio 在Gemini API中不支持，只在Vertex AI中支持
            # if generate_audio:
            #     config_params["generate_audio"] = generate_audio
            
            print(f"[DEBUG] 配置参数: {config_params}")
            
            try:
                config = types.GenerateVideosConfig(**config_params)
                print(f"[DEBUG] 配置对象创建成功")
            except Exception as e:
                print(f"[DEBUG] 配置对象创建失败: {str(e)}")
                raise
            
            # 生成视频
            if reference_image:
                print(f"[DEBUG] 处理参考图片，大小: {len(reference_image)} bytes")
                try:
                    # 尝试不同的图片创建方式
                    if hasattr(types.Image, 'from_bytes'):
                        image = types.Image.from_bytes(reference_image)
                    elif hasattr(types, 'Part'):
                        # 备用方式
                        image = types.Part.from_bytes(data=reference_image, mime_type="image/jpeg")
                    else:
                        raise RuntimeError("无法找到合适的图片创建方法")
                    
                    print(f"[DEBUG] 图片对象创建成功")
                    
                    operation = self.client.models.generate_videos(
                        model=self.model_id,
                        prompt=prompt,
                        image=image,
                        config=config
                    )
                except Exception as e:
                    print(f"[DEBUG] 图片处理失败: {str(e)}")
                    raise RuntimeError(f"图片处理失败: {str(e)}")
            else:
                print(f"[DEBUG] 文本到视频生成")
                try:
                    operation = self.client.models.generate_videos(
                        model=self.model_id,
                        prompt=prompt,
                        config=config
                    )
                except Exception as e:
                    print(f"[DEBUG] 文本到视频生成失败: {str(e)}")
                    raise RuntimeError(f"视频生成失败: {str(e)}")
            
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
            error_msg = f"生成失败: {str(e)}"
            print(f"[DEBUG] {error_msg}")
            return {
                "success": False,
                "error": error_msg
            }
    
    def get_video_status(self, operation_name: str, operation=None) -> Dict[str, Any]:
        """获取视频生成状态"""
        try:
            if not operation:
                print(f"[DEBUG] 根据名称重新获取操作: {operation_name}")
                try:
                    # 尝试从操作名称重新获取操作对象
                    operation = self.client.operations.get(operation_name)
                except Exception as e:
                    print(f"[DEBUG] 无法重新获取操作对象: {str(e)}")
                    return {
                        "status": "error",
                        "progress": 0,
                        "error": f"无法获取操作状态: {str(e)}"
                    }
            else:
                print(f"[DEBUG] 刷新现有操作状态")
                try:
                    # 刷新操作状态
                    operation = self.client.operations.get(operation)
                except Exception as e:
                    print(f"[DEBUG] 刷新操作状态失败: {str(e)}")
                    return {
                        "status": "error",
                        "progress": 0,
                        "error": f"刷新操作状态失败: {str(e)}"
                    }
            
            if operation.done:
                print(f"[DEBUG] 操作已完成")
                
                if hasattr(operation, 'error') and operation.error:
                    error_msg = str(operation.error)
                    print(f"[DEBUG] 操作错误: {error_msg}")
                    return {
                        "status": "failed",
                        "progress": 0,
                        "error": error_msg
                    }
                else:
                    try:
                        # 获取生成的视频
                        generated_video = operation.response.generated_videos[0]
                        print(f"[DEBUG] 获取到生成的视频对象")
                        
                        print(f"[DEBUG] 开始下载视频文件...")
                        
                        # 尝试不同的方式获取视频数据
                        video_bytes = None
                        
                        # 方式1: 直接从video对象获取字节数据
                        if hasattr(generated_video.video, 'video_bytes'):
                            video_bytes = base64.b64encode(generated_video.video.video_bytes).decode('utf-8')
                            print(f"[DEBUG] 从video_bytes获取数据，大小: {len(generated_video.video.video_bytes)} bytes")
                        
                        # 方式2: 通过下载文件获取
                        elif hasattr(self.client.files, 'download'):
                            try:
                                video_file = self.client.files.download(file=generated_video.video)
                                if hasattr(video_file, 'read'):
                                    video_content = video_file.read()
                                    video_bytes = base64.b64encode(video_content).decode('utf-8')
                                    print(f"[DEBUG] 从下载文件获取数据，大小: {len(video_content)} bytes")
                                elif isinstance(video_file, bytes):
                                    video_bytes = base64.b64encode(video_file).decode('utf-8')
                                    print(f"[DEBUG] 直接从字节数据获取，大小: {len(video_file)} bytes")
                            except Exception as e:
                                print(f"[DEBUG] 文件下载失败: {str(e)}")
                        
                        if video_bytes:
                            print(f"[DEBUG] 视频下载完成，base64编码长度: {len(video_bytes)}")
                        else:
                            print(f"[DEBUG] 警告：无法获取视频字节数据")
                            print(f"[DEBUG] 可用属性: {dir(generated_video.video)}")
                        
                        return {
                            "status": "completed",
                            "progress": 100,
                            "video_bytes": video_bytes,
                            "message": "视频生成完成",
                            "operation": operation  # 保持操作对象
                        }
                        
                    except Exception as e:
                        error_msg = f"处理完成的视频失败: {str(e)}"
                        print(f"[DEBUG] {error_msg}")
                        return {
                            "status": "error",
                            "progress": 0,
                            "error": error_msg
                        }
            else:
                print(f"[DEBUG] 操作仍在进行中")
                return {
                    "status": "processing",
                    "progress": 50,
                    "message": "正在生成视频...",
                    "operation": operation  # 保持操作对象
                }
                
        except Exception as e:
            error_msg = f"状态查询失败: {str(e)}"
            print(f"[DEBUG] {error_msg}")
            return {
                "status": "error",
                "progress": 0,
                "error": error_msg
            }


# 全局服务实例
_veo_service: Optional[VeoAPIService] = None


def get_veo_service() -> Optional[VeoAPIService]:
    """获取Veo服务实例"""
    global _veo_service
    
    try:
        if "GOOGLE_API_KEY" not in st.secrets:
            print("[DEBUG] 没有找到GOOGLE_API_KEY")
            st.error("⚠️ 未配置GOOGLE_API_KEY")
            return None
        
        if not SDK_AVAILABLE:
            st.error("⚠️ Google GenAI SDK 不可用")
            st.info("💡 请确保在云端环境中正确安装了 google-genai 包")
            return None
        
        if _veo_service is None:
            _veo_service = VeoAPIService()
        
        return _veo_service
    except Exception as e:
        print(f"[DEBUG] 创建Veo服务失败: {str(e)}")
        st.error(f"⚠️ 创建Veo服务失败: {str(e)}")
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
            "error": "Veo服务未配置，请检查SDK安装和API密钥"
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
