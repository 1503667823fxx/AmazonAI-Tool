"""
Google Veo 3.1 API Service

真正的Google Veo API调用服务
"""

import asyncio
import aiohttp
import json
import base64
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import streamlit as st


class VeoAPIService:
    """Google Veo 3.1 API服务"""
    
    def __init__(self):
        # 从Streamlit secrets获取配置
        self.project_id = st.secrets["GOOGLE_CLOUD_PROJECT_ID"]
        self.location = st.secrets["GOOGLE_CLOUD_LOCATION"]
        self.model_id = "veo-3.1-generate-preview"
        
        # 构建API端点
        self.base_url = f"https://{self.location}-aiplatform.googleapis.com/v1/projects/{self.project_id}/locations/{self.location}/publishers/google/models/{self.model_id}"
        
        self.session: Optional[aiohttp.ClientSession] = None
        self._access_token: Optional[str] = None
        self._token_expiry: Optional[datetime] = None
    
    async def _get_access_token(self) -> str:
        """获取Google Cloud访问令牌"""
        # 检查缓存的令牌是否仍然有效
        if self._access_token and self._token_expiry and datetime.now() < self._token_expiry:
            return self._access_token
        
        try:
            # 从Streamlit secrets获取服务账号凭据
            credentials_json = st.secrets["GOOGLE_CLOUD_CREDENTIALS"]
            credentials_info = json.loads(credentials_json)
            
            # 使用Google OAuth2库获取访问令牌
            from google.oauth2 import service_account
            from google.auth.transport.requests import Request
            
            credentials = service_account.Credentials.from_service_account_info(
                credentials_info,
                scopes=['https://www.googleapis.com/auth/cloud-platform']
            )
            
            # 刷新令牌
            credentials.refresh(Request())
            
            self._access_token = credentials.token
            # 设置过期时间为50分钟后（令牌通常1小时有效）
            self._token_expiry = datetime.now() + timedelta(minutes=50)
            
            return self._access_token
            
        except Exception as e:
            raise RuntimeError(f"获取访问令牌失败: {str(e)}")
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """获取HTTP会话"""
        if self.session is None or self.session.closed:
            access_token = await self._get_access_token()
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
                "User-Agent": "VideoStudio-Veo/1.0"
            }
            timeout = aiohttp.ClientTimeout(total=600)  # 10分钟超时
            self.session = aiohttp.ClientSession(
                headers=headers,
                timeout=timeout
            )
        return self.session
    
    async def generate_video(
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
        """
        生成视频
        
        Args:
            prompt: 视频描述
            duration: 时长（秒）
            aspect_ratio: 宽高比
            quality: 质量
            reference_image: 参考图片（字节数据）
            negative_prompt: 负面提示词
            seed: 随机种子
            generate_audio: 是否生成音频
            
        Returns:
            包含任务ID和状态的字典
        """
        try:
            session = await self._get_session()
            
            # 构建实例数据
            instance = {
                "prompt": prompt
            }
            
            # 添加参考图片
            if reference_image:
                base64_image = base64.b64encode(reference_image).decode('utf-8')
                instance["image"] = {
                    "bytesBase64Encoded": base64_image,
                    "mimeType": "image/jpeg"
                }
            
            # 构建参数
            parameters = {
                "aspectRatio": aspect_ratio,
                "durationSeconds": min(duration, 8),  # 限制最大8秒
                "resolution": quality,
                "sampleCount": 1
            }
            
            # 添加可选参数
            if negative_prompt:
                parameters["negativePrompt"] = negative_prompt
            
            if seed is not None:
                parameters["seed"] = seed
            
            if generate_audio:
                parameters["generateAudio"] = True
            
            # 构建完整请求数据
            request_data = {
                "instances": [instance],
                "parameters": parameters
            }
            
            # 发送请求到真实的Google Veo API
            url = f"{self.base_url}:predictLongRunning"
            
            async with session.post(url, json=request_data) as response:
                if response.status == 200:
                    result = await response.json()
                    operation_name = result.get("name")
                    
                    if not operation_name:
                        raise RuntimeError("API返回中没有操作名称")
                    
                    # 提取操作ID
                    operation_id = operation_name.split("/")[-1]
                    
                    return {
                        "success": True,
                        "job_id": operation_id,
                        "operation_name": operation_name,
                        "status": "processing",
                        "message": "视频生成任务已创建"
                    }
                elif response.status == 401:
                    return {
                        "success": False,
                        "error": "认证失败，请检查Google Cloud凭据"
                    }
                elif response.status == 403:
                    return {
                        "success": False,
                        "error": "权限不足，请检查服务账号权限"
                    }
                elif response.status == 429:
                    return {
                        "success": False,
                        "error": "API调用频率超限，请稍后重试"
                    }
                else:
                    error_data = await response.json()
                    return {
                        "success": False,
                        "error": f"API调用失败 ({response.status}): {error_data.get('error', {}).get('message', '未知错误')}"
                    }
                    
        except aiohttp.ClientError as e:
            return {
                "success": False,
                "error": f"网络错误: {str(e)}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"生成失败: {str(e)}"
            }
    
    async def get_video_status(self, operation_name: str) -> Dict[str, Any]:
        """
        获取视频生成状态
        
        Args:
            operation_name: 完整的操作名称
            
        Returns:
            包含状态信息的字典
        """
        try:
            session = await self._get_session()
            
            # 构建操作状态查询URL
            url = f"https://{self.location}-aiplatform.googleapis.com/v1/{operation_name}"
            
            async with session.get(url) as response:
                if response.status == 200:
                    result = await response.json()
                    
                    # 检查操作是否完成
                    if result.get("done", False):
                        if "error" in result:
                            return {
                                "status": "failed",
                                "progress": 0,
                                "error": result["error"].get("message", "生成失败")
                            }
                        else:
                            # 提取视频URL
                            video_url = None
                            if "response" in result:
                                predictions = result["response"].get("predictions", [])
                                if predictions:
                                    video_data = predictions[0].get("video", {})
                                    # 检查不同的URL字段
                                    video_url = (video_data.get("uri") or 
                                               video_data.get("gcsUri") or
                                               video_data.get("url"))
                            
                            return {
                                "status": "completed",
                                "progress": 100,
                                "video_url": video_url,
                                "message": "视频生成完成"
                            }
                    else:
                        # 仍在处理中
                        # 尝试从metadata获取进度信息
                        metadata = result.get("metadata", {})
                        progress = 50  # 默认进度
                        
                        return {
                            "status": "processing",
                            "progress": progress,
                            "message": "正在生成视频..."
                        }
                else:
                    return {
                        "status": "error",
                        "progress": 0,
                        "error": f"无法获取状态: HTTP {response.status}"
                    }
                    
        except Exception as e:
            return {
                "status": "error",
                "progress": 0,
                "error": f"状态查询失败: {str(e)}"
            }
    
    async def close(self):
        """关闭HTTP会话"""
        if self.session and not self.session.closed:
            await self.session.close()


# 全局服务实例
_veo_service: Optional[VeoAPIService] = None


def get_veo_service() -> Optional[VeoAPIService]:
    """获取Veo服务实例"""
    global _veo_service
    
    try:
        # 检查必要的配置
        required_keys = ["GOOGLE_CLOUD_PROJECT_ID", "GOOGLE_CLOUD_LOCATION", "GOOGLE_CLOUD_CREDENTIALS"]
        for key in required_keys:
            if key not in st.secrets:
                return None
        
        if _veo_service is None:
            _veo_service = VeoAPIService()
        
        return _veo_service
    except Exception:
        return None


async def generate_video_async(
    prompt: str,
    duration: int = 4,
    aspect_ratio: str = "16:9",
    quality: str = "1080p",
    reference_image: Optional[bytes] = None,
    negative_prompt: Optional[str] = None,
    seed: Optional[int] = None,
    generate_audio: bool = False
) -> Dict[str, Any]:
    """异步生成视频"""
    service = get_veo_service()
    if not service:
        return {
            "success": False,
            "error": "Veo服务未配置，请检查Google Cloud凭据"
        }
    
    return await service.generate_video(
        prompt=prompt,
        duration=duration,
        aspect_ratio=aspect_ratio,
        quality=quality,
        reference_image=reference_image,
        negative_prompt=negative_prompt,
        seed=seed,
        generate_audio=generate_audio
    )


async def get_video_status_async(operation_name: str) -> Dict[str, Any]:
    """异步获取视频状态"""
    service = get_veo_service()
    if not service:
        return {
            "status": "error",
            "error": "Veo服务未配置"
        }
    
    return await service.get_video_status(operation_name)


def generate_video_sync(*args, **kwargs) -> Dict[str, Any]:
    """同步生成视频（用于Streamlit）"""
    try:
        return asyncio.run(generate_video_async(*args, **kwargs))
    except Exception as e:
        return {
            "success": False,
            "error": f"生成失败: {str(e)}"
        }


def get_video_status_sync(operation_name: str) -> Dict[str, Any]:
    """同步获取视频状态（用于Streamlit）"""
    try:
        return asyncio.run(get_video_status_async(operation_name))
    except Exception as e:
        return {
            "status": "error",
            "error": f"状态查询失败: {str(e)}"
        }
