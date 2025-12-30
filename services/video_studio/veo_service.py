"""
Google Veo 3.1 API Service - 使用官方Google GenAI SDK

基于官方文档: https://ai.google.dev/gemini-api/docs/video
"""

import os
import time
import base64
from datetime import datetime
from typing import Optional, Dict, Any
import streamlit as st

try:
    from google import genai
    from google.genai import types
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False
    print("[WARNING] google-genai not available, falling back to HTTP requests")
    import json
    import requests


class VeoAPIService:
    """Google Veo 3.1 API服务 - 使用官方SDK"""
    
    def __init__(self):
        self.api_key = st.secrets["GOOGLE_API_KEY"]
        
        if GENAI_AVAILABLE:
            # 使用官方SDK
            self.client = genai.Client(api_key=self.api_key)
            self.model_id = "veo-3.1-generate-preview"
            print(f"[DEBUG] 使用官方Google GenAI SDK")
        else:
            # 回退到HTTP请求
            self.client = None
            self.model_id = "veo-3.1-generate-preview"
            self.base_url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_id}"
            print(f"[DEBUG] 回退到HTTP请求方式")
        
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
            if GENAI_AVAILABLE and self.client:
                return self._generate_video_sdk(
                    prompt, duration, aspect_ratio, quality, 
                    reference_image, negative_prompt, seed, generate_audio
                )
            else:
                return self._generate_video_http(
                    prompt, duration, aspect_ratio, quality, 
                    reference_image, negative_prompt, seed, generate_audio
                )
        except Exception as e:
            return {
                "success": False,
                "error": f"生成失败: {str(e)}"
            }
    
    def _generate_video_sdk(
        self,
        prompt: str,
        duration: int,
        aspect_ratio: str,
        quality: str,
        reference_image: Optional[bytes],
        negative_prompt: Optional[str],
        seed: Optional[int],
        generate_audio: bool
    ) -> Dict[str, Any]:
        """使用官方SDK生成视频"""
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
                "error": f"SDK生成失败: {str(e)}"
            }
    
    def _generate_video_http(
        self,
        prompt: str,
        duration: int,
        aspect_ratio: str,
        quality: str,
        reference_image: Optional[bytes],
        negative_prompt: Optional[str],
        seed: Optional[int],
        generate_audio: bool
    ) -> Dict[str, Any]:
        """HTTP请求方式生成视频（回退方案）"""
        # 保持原有的HTTP实现作为回退
        try:
            # 构建请求头
            headers = {
                "x-goog-api-key": self.api_key,
                "Content-Type": "application/json",
                "User-Agent": "VideoStudio-Veo/1.0"
            }
            
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
            valid_durations = [4, 6, 8]
            if duration not in valid_durations:
                duration = min(valid_durations, key=lambda x: abs(x - duration))
            
            if reference_image and duration != 8:
                duration = 8
            
            parameters = {
                "aspectRatio": aspect_ratio,
                "durationSeconds": duration,
                "resolution": quality.lower(),
                "sampleCount": 1
            }
            
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
            
            # 发送请求
            url = f"{self.base_url}:predictLongRunning"
            response = requests.post(url, json=request_data, headers=headers, timeout=60)
            
            if response.status_code == 200:
                result = response.json()
                operation_name = result.get("name")
                
                if not operation_name:
                    raise RuntimeError("API返回中没有操作名称")
                
                operation_id = operation_name.split("/")[-1]
                
                return {
                    "success": True,
                    "job_id": operation_id,
                    "operation_name": operation_name,
                    "status": "processing",
                    "message": "视频生成任务已创建"
                }
            else:
                return self._handle_error_response(response, url)
                
        except requests.RequestException as e:
            return {
                "success": False,
                "error": f"网络错误: {str(e)}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"生成失败: {str(e)}"
            }
    
    def get_video_status(self, operation_name: str, operation=None) -> Dict[str, Any]:
        """获取视频生成状态"""
        try:
            if GENAI_AVAILABLE and self.client and operation:
                return self._get_video_status_sdk(operation)
            else:
                return self._get_video_status_http(operation_name)
        except Exception as e:
            return {
                "status": "error",
                "progress": 0,
                "error": f"状态查询失败: {str(e)}"
            }
    
    def _get_video_status_sdk(self, operation) -> Dict[str, Any]:
        """使用SDK获取视频状态"""
        try:
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
                    
                    # 下载视频字节数据
                    print(f"[DEBUG] 开始下载视频文件...")
                    video_file = self.client.files.download(file=generated_video.video)
                    
                    # 获取视频字节数据
                    video_bytes = None
                    if hasattr(generated_video.video, 'video_bytes'):
                        video_bytes = base64.b64encode(generated_video.video.video_bytes).decode('utf-8')
                    elif hasattr(video_file, 'read'):
                        video_content = video_file.read()
                        video_bytes = base64.b64encode(video_content).decode('utf-8')
                    
                    print(f"[DEBUG] 视频下载完成，字节数据: {'有' if video_bytes else '无'}")
                    
                    return {
                        "status": "completed",
                        "progress": 100,
                        "video_bytes": video_bytes,
                        "message": "视频生成完成"
                    }
            else:
                return {
                    "status": "processing",
                    "progress": 50,
                    "message": "正在生成视频..."
                }
                
        except Exception as e:
            print(f"[DEBUG] SDK状态查询失败: {str(e)}")
            return {
                "status": "error",
                "progress": 0,
                "error": f"SDK状态查询失败: {str(e)}"
            }
    
    def _get_video_status_http(self, operation_name: str) -> Dict[str, Any]:
        """HTTP方式获取视频状态（回退方案）"""
        # 保持原有的HTTP实现
        try:
            headers = {
                "x-goog-api-key": self.api_key,
                "Content-Type": "application/json"
            }
            
            url = f"https://generativelanguage.googleapis.com/v1beta/{operation_name}"
            response = requests.get(url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                print(f"[DEBUG] HTTP状态响应: {json.dumps(result, indent=2, ensure_ascii=False)}")
                
                if result.get("done", False):
                    if "error" in result:
                        return {
                            "status": "failed",
                            "progress": 0,
                            "error": result["error"].get("message", "生成失败")
                        }
                    else:
                        # 尝试提取视频数据
                        video_bytes = None
                        video_url = None
                        
                        if "response" in result:
                            response_data = result["response"]
                            print(f"[DEBUG] 完整响应数据结构: {json.dumps(response_data, indent=2, ensure_ascii=False)}")
                            video_info = self._extract_video_data(response_data)
                            video_bytes = video_info.get("video_bytes")
                            video_url = video_info.get("video_url")
                        
                        # 如果没有字节数据，尝试通过URL下载
                        if not video_bytes and video_url:
                            print(f"[DEBUG] 尝试通过URL下载视频字节数据: {video_url}")
                            try:
                                download_headers = {
                                    "x-goog-api-key": self.api_key,
                                    "Authorization": f"Bearer {self.api_key}"
                                }
                                
                                download_response = requests.get(video_url, headers=download_headers, timeout=60)
                                if download_response.status_code == 200:
                                    video_bytes = base64.b64encode(download_response.content).decode('utf-8')
                                    print(f"[DEBUG] 成功通过URL下载视频，大小: {len(download_response.content)} bytes")
                                else:
                                    print(f"[DEBUG] URL下载失败: {download_response.status_code}")
                            except Exception as e:
                                print(f"[DEBUG] URL下载异常: {str(e)}")
                        
                        print(f"[DEBUG] 最终结果 - 字节数据: {'有' if video_bytes else '无'}, URL: {video_url}")
                        
                        return {
                            "status": "completed",
                            "progress": 100,
                            "video_bytes": video_bytes,
                            "video_url": video_url,
                            "message": "视频生成完成",
                            "raw_response": result
                        }
                else:
                    return {
                        "status": "processing",
                        "progress": 50,
                        "message": "正在生成视频..."
                    }
            else:
                return {
                    "status": "error",
                    "progress": 0,
                    "error": f"无法获取状态: HTTP {response.status_code}"
                }
                
        except requests.RequestException as e:
            return {
                "status": "error",
                "progress": 0,
                "error": f"网络错误: {str(e)}"
            }
        except Exception as e:
            return {
                "status": "error",
                "progress": 0,
                "error": f"状态查询失败: {str(e)}"
            }
    
    def _extract_video_data(self, response_data: dict) -> Dict[str, Any]:
        """从响应数据中提取视频数据（HTTP回退方案）"""
        result = {"video_url": None, "video_bytes": None}
        
        # 递归搜索视频数据
        def find_video_data_in_dict(data, depth=0):
            if depth > 5:
                return {"video_url": None, "video_bytes": None}
            
            found_result = {"video_url": None, "video_bytes": None}
            
            if isinstance(data, dict):
                # 检查字节数据字段
                bytes_fields = ['video_bytes', 'videoBytes', 'bytesBase64Encoded', 'base64Data', 'videoData']
                for field in bytes_fields:
                    if field in data and data[field]:
                        found_result["video_bytes"] = data[field]
                        return found_result
                
                # 检查URL字段
                url_fields = ['uri', 'url', 'gcsUri', 'downloadUrl', 'signedUrl', 'videoUri', 'fileUri', 'video_uri', 'download_url', 'publicUrl', 'viewUrl']
                for field in url_fields:
                    if field in data and isinstance(data[field], str) and data[field].startswith(('http', 'gs://')):
                        found_result["video_url"] = data[field]
                        if not found_result["video_bytes"]:
                            return found_result
                
                # 递归搜索嵌套对象
                for value in data.values():
                    nested_result = find_video_data_in_dict(value, depth + 1)
                    if nested_result["video_bytes"]:
                        return nested_result
                    elif nested_result["video_url"] and not found_result["video_url"]:
                        found_result["video_url"] = nested_result["video_url"]
            
            elif isinstance(data, list):
                for item in data:
                    nested_result = find_video_data_in_dict(item, depth + 1)
                    if nested_result["video_bytes"]:
                        return nested_result
                    elif nested_result["video_url"] and not found_result["video_url"]:
                        found_result["video_url"] = nested_result["video_url"]
            
            return found_result
        
        return find_video_data_in_dict(response_data)
    
    def _handle_error_response(self, response, url: str) -> Dict[str, Any]:
        """处理错误响应"""
        try:
            error_data = response.json()
            print(f"[DEBUG] 错误响应: {json.dumps(error_data, indent=2, ensure_ascii=False)}")
        except:
            print(f"[DEBUG] 错误响应文本: {response.text}")
        
        if response.status_code == 401:
            return {
                "success": False,
                "error": "认证失败，请检查API密钥"
            }
        elif response.status_code == 403:
            return {
                "success": False,
                "error": "权限不足，请检查API权限"
            }
        elif response.status_code == 404:
            return {
                "success": False,
                "error": f"API端点不存在 (404): {url}"
            }
        elif response.status_code == 429:
            return {
                "success": False,
                "error": "API调用频率超限，请稍后重试"
            }
        else:
            try:
                error_data = response.json()
                error_message = error_data.get('error', {}).get('message', '未知错误')
            except:
                error_message = f"HTTP {response.status_code}: {response.text}"
            
            return {
                "success": False,
                "error": f"API调用失败 ({response.status_code}): {error_message}"
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
