"""
Google Veo 3.1 API Service

真正的Google Veo API调用服务 - 支持Gemini API和Vertex AI两种方式
"""

import json
import base64
import requests
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import streamlit as st


class VeoAPIService:
    """Google Veo 3.1 API服务 - 同步版本"""
    
    def __init__(self):
        # 检查API配置方式
        self.use_gemini_api = "GOOGLE_API_KEY" in st.secrets
        
        if self.use_gemini_api:
            # 使用Gemini API
            self.api_key = st.secrets["GOOGLE_API_KEY"]
            self.model_id = "veo-3.1-generate-preview"
            self.base_url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_id}"
            print(f"[DEBUG] 使用Gemini API")
            print(f"  模型ID: {self.model_id}")
            print(f"  基础URL: {self.base_url}")
        else:
            # 使用Vertex AI
            self.project_id = st.secrets.get("GOOGLE_CLOUD_PROJECT_ID", "cohesive-point-481508-d4")
            self.location = st.secrets.get("GOOGLE_CLOUD_LOCATION", "us-central1")
            self.model_id = "veo-3.1-generate-001"
            self.base_url = f"https://{self.location}-aiplatform.googleapis.com/v1/projects/{self.project_id}/locations/{self.location}/publishers/google/models/{self.model_id}"
            print(f"[DEBUG] 使用Vertex AI")
            print(f"  项目ID: {self.project_id}")
            print(f"  地区: {self.location}")
            print(f"  模型ID: {self.model_id}")
            print(f"  基础URL: {self.base_url}")
        
        self._access_token: Optional[str] = None
        self._token_expiry: Optional[datetime] = None
    
    def _get_access_token(self) -> str:
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
        """
        生成视频 - 同步版本，支持Gemini API和Vertex AI
        """
        try:
            if self.use_gemini_api:
                return self._generate_video_gemini(
                    prompt, duration, aspect_ratio, quality, 
                    reference_image, negative_prompt, seed, generate_audio
                )
            else:
                return self._generate_video_vertex(
                    prompt, duration, aspect_ratio, quality, 
                    reference_image, negative_prompt, seed, generate_audio
                )
                
        except Exception as e:
            return {
                "success": False,
                "error": f"生成失败: {str(e)}"
            }
    
    def _generate_video_gemini(
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
        """使用Gemini API生成视频"""
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
            
            # 构建参数 - 使用Gemini API格式
            parameters = {
                "aspectRatio": aspect_ratio,
                "durationSeconds": min(duration, 8),  # 限制最大8秒
                "resolution": quality.lower(),  # 确保是小写格式，如 "720p", "1080p"
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
            
            # 发送请求到Gemini API
            url = f"{self.base_url}:predictLongRunning"
            
            print(f"[DEBUG] Gemini API请求到: {url}")
            print(f"[DEBUG] 请求头: {headers}")
            print(f"[DEBUG] 请求数据: {json.dumps(request_data, indent=2, ensure_ascii=False)}")
            
            response = requests.post(url, json=request_data, headers=headers, timeout=60)
            
            print(f"[DEBUG] 响应状态码: {response.status_code}")
            print(f"[DEBUG] 响应头: {dict(response.headers)}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"[DEBUG] 成功响应: {json.dumps(result, indent=2, ensure_ascii=False)}")
                
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
                    "message": "视频生成任务已创建 (Gemini API)"
                }
            else:
                return self._handle_error_response(response, url)
                
        except requests.RequestException as e:
            return {
                "success": False,
                "error": f"网络错误: {str(e)}"
            }
    
    def _generate_video_vertex(
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
        """使用Vertex AI生成视频"""
        try:
            # 获取访问令牌
            access_token = self._get_access_token()
            
            # 构建请求头
            headers = {
                "Authorization": f"Bearer {access_token}",
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
            
            # 发送请求到Vertex AI
            url = f"{self.base_url}:predictLongRunning"
            
            print(f"[DEBUG] Vertex AI请求到: {url}")
            print(f"[DEBUG] 请求头: {headers}")
            print(f"[DEBUG] 请求数据: {json.dumps(request_data, indent=2, ensure_ascii=False)}")
            
            response = requests.post(url, json=request_data, headers=headers, timeout=60)
            
            print(f"[DEBUG] 响应状态码: {response.status_code}")
            print(f"[DEBUG] 响应头: {dict(response.headers)}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"[DEBUG] 成功响应: {json.dumps(result, indent=2, ensure_ascii=False)}")
                
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
                    "message": "视频生成任务已创建 (Vertex AI)"
                }
            else:
                return self._handle_error_response(response, url)
                
        except requests.RequestException as e:
            return {
                "success": False,
                "error": f"网络错误: {str(e)}"
            }
    
    def _handle_error_response(self, response: requests.Response, url: str) -> Dict[str, Any]:
        """处理错误响应"""
        # 记录错误响应
        try:
            error_data = response.json()
            print(f"[DEBUG] 错误响应: {json.dumps(error_data, indent=2, ensure_ascii=False)}")
        except:
            print(f"[DEBUG] 错误响应文本: {response.text}")
        
        if response.status_code == 401:
            return {
                "success": False,
                "error": "认证失败，请检查API密钥或Google Cloud凭据"
            }
        elif response.status_code == 403:
            return {
                "success": False,
                "error": "权限不足，请检查API权限或服务账号权限"
            }
        elif response.status_code == 404:
            return {
                "success": False,
                "error": f"API端点不存在 (404): {url}。可能原因：1) Veo API在该地区不可用 2) 模型名称错误 3) 项目配置问题"
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
    
    def get_video_status(self, operation_name: str) -> Dict[str, Any]:
        """
        获取视频生成状态 - 同步版本，支持Gemini API和Vertex AI
        """
        try:
            if self.use_gemini_api:
                return self._get_video_status_gemini(operation_name)
            else:
                return self._get_video_status_vertex(operation_name)
                
        except Exception as e:
            return {
                "status": "error",
                "progress": 0,
                "error": f"状态查询失败: {str(e)}"
            }
    
    def _get_video_status_gemini(self, operation_name: str) -> Dict[str, Any]:
        """使用Gemini API获取视频状态"""
        try:
            # 构建请求头
            headers = {
                "x-goog-api-key": self.api_key,
                "Content-Type": "application/json"
            }
            
            # 构建操作状态查询URL
            url = f"https://generativelanguage.googleapis.com/v1beta/{operation_name}"
            
            response = requests.get(url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                
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
                    return {
                        "status": "processing",
                        "progress": 50,  # 默认进度
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
    
    def _get_video_status_vertex(self, operation_name: str) -> Dict[str, Any]:
        """使用Vertex AI获取视频状态"""
        try:
            # 获取访问令牌
            access_token = self._get_access_token()
            
            # 构建请求头
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            # 构建操作状态查询URL
            url = f"https://{self.location}-aiplatform.googleapis.com/v1/{operation_name}"
            
            response = requests.get(url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                
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
                    return {
                        "status": "processing",
                        "progress": 50,  # 默认进度
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


# 全局服务实例
_veo_service: Optional[VeoAPIService] = None


def get_veo_service() -> Optional[VeoAPIService]:
    """获取Veo服务实例"""
    global _veo_service
    
    try:
        # 检查API配置
        has_gemini_key = "GOOGLE_API_KEY" in st.secrets
        has_vertex_config = all(key in st.secrets for key in ["GOOGLE_CLOUD_PROJECT_ID", "GOOGLE_CLOUD_LOCATION", "GOOGLE_CLOUD_CREDENTIALS"])
        
        if not has_gemini_key and not has_vertex_config:
            print("[DEBUG] 没有找到有效的API配置")
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
            "error": "Veo服务未配置，请检查Google Cloud凭据"
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


def get_video_status_sync(operation_name: str) -> Dict[str, Any]:
    """同步获取视频状态（用于Streamlit）"""
    service = get_veo_service()
    if not service:
        return {
            "status": "error",
            "error": "Veo服务未配置"
        }
    
    return service.get_video_status(operation_name)
