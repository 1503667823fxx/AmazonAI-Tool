"""
Google Veo 3.1 API Service - 云端Streamlit兼容版

基于官方文档: https://ai.google.dev/gemini-api/docs/video
针对云端Streamlit环境优化，支持图片到视频功能
"""

import os
import time
import base64
from datetime import datetime
from typing import Optional, Dict, Any
import streamlit as st

# 导入图片处理器
from .image_processor import process_image_for_video_generation

# 尝试导入Google GenAI SDK
try:
    from google import genai
    from google.genai import types
    SDK_AVAILABLE = True
except ImportError as e:
    SDK_AVAILABLE = False


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
            # 构建配置 - 处理分辨率和时长的限制
            # 根据API错误：1080p只支持8秒，720p支持4、6、8秒
            
            # 自动调整分辨率和时长的组合
            if quality.lower() == "1080p" and duration != 8:
                adjusted_quality = "720p"
            else:
                adjusted_quality = quality.lower()
            
            config_params = {
                "aspect_ratio": aspect_ratio,
                "duration_seconds": duration,
                "resolution": adjusted_quality
            }
            
            # 添加可选参数（排除不支持的参数）
            if seed is not None:
                config_params["seed"] = seed
            
            # 注意：generate_audio 在Gemini API中不支持，只在Vertex AI中支持
            # if generate_audio:
            #     config_params["generate_audio"] = generate_audio
            
            try:
                config = types.GenerateVideosConfig(**config_params)
            except Exception as e:
                raise
            
            # 生成视频
            if reference_image:
                # 处理图片
                image_result = process_image_for_video_generation(reference_image)
                
                if not image_result["success"]:
                    raise RuntimeError(f"图片处理失败: {image_result['error']}")
                
                # 使用SDK的文件上传方式
                try:
                    import tempfile
                    import os
                    from pathlib import Path
                    
                    # 创建临时文件
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp_file:
                        tmp_file.write(image_result["optimized_bytes"])
                        tmp_file_path = tmp_file.name
                    
                    # 使用官方示例的正确方法
                    try:
                        if hasattr(types, 'Image') and hasattr(types.Image, 'from_file'):
                            uploaded_file = types.Image.from_file(location=tmp_file_path)
                        else:
                            raise AttributeError("types.Image.from_file 不存在")
                    except Exception as e:
                        raise RuntimeError(f"图片文件加载失败: {str(e)}")
                    
                    if not uploaded_file:
                        raise RuntimeError("无法创建图片对象")
                    
                    # 使用图片对象生成视频
                    operation = self.client.models.generate_videos(
                        model=self.model_id,
                        prompt=prompt,
                        image=uploaded_file,
                        config=config
                    )
                    
                    # 清理临时文件
                    try:
                        os.unlink(tmp_file_path)
                    except:
                        pass
                    
                except Exception as e:
                    # 清理临时文件
                    try:
                        if 'tmp_file_path' in locals():
                            os.unlink(tmp_file_path)
                    except:
                        pass
                    
                    raise RuntimeError(f"图片到视频生成失败: {str(e)}")
                        
            else:
                try:
                    operation = self.client.models.generate_videos(
                        model=self.model_id,
                        prompt=prompt,
                        config=config
                    )
                except Exception as e:
                    raise RuntimeError(f"视频生成失败: {str(e)}")
            
            return {
                "success": True,
                "job_id": operation.name.split("/")[-1],
                "operation_name": operation.name,
                "status": "processing",
                "message": "视频生成任务已创建"
            }
            
        except Exception as e:
            error_msg = f"生成失败: {str(e)}"
            return {
                "success": False,
                "error": error_msg
            }
    
    def get_video_status(self, operation_name: str) -> Dict[str, Any]:
        """获取视频生成状态"""
        try:
            # 使用HTTP请求直接查询状态，避免SDK序列化问题
            try:
                import requests
                
                # 构建请求头
                headers = {
                    "x-goog-api-key": self.api_key,
                    "Content-Type": "application/json"
                }
                
                # 构建URL - 直接使用operation_name作为路径
                url = f"https://generativelanguage.googleapis.com/v1beta/{operation_name}"
                
                response = requests.get(url, headers=headers, timeout=30)
                
                if response.status_code == 200:
                    result = response.json()
                    
                    # 检查操作是否完成
                    if result.get("done", False):
                        if "error" in result:
                            error_msg = result["error"].get("message", "生成失败")
                            return {
                                "status": "failed",
                                "progress": 0,
                                "error": error_msg
                            }
                        else:
                            # 尝试提取视频URI和数据
                            video_uri = None
                            
                            if "response" in result:
                                response_data = result["response"]
                                # 提取视频URI
                                video_uri = self._extract_video_uri_from_response(response_data)
                            else:
                                # 有些API可能直接在根级别返回数据
                                video_uri = self._extract_video_uri_from_response(result)
                            
                            return {
                                "status": "completed",
                                "progress": 100,
                                "video_uri": video_uri,  # 返回URI用于下载
                                "video_bytes": None,     # 暂不下载
                                "message": "视频生成完成",
                                "raw_response": result  # 保存原始响应用于调试
                            }
                    else:
                        return {
                            "status": "processing",
                            "progress": 50,
                            "message": "正在生成视频..."
                        }
                elif response.status_code == 404:
                    return {
                        "status": "error",
                        "progress": 0,
                        "error": "操作不存在或已过期"
                    }
                else:
                    # 尝试解析错误响应
                    try:
                        error_data = response.json()
                        error_msg = error_data.get("error", {}).get("message", f"HTTP {response.status_code}")
                    except:
                        error_msg = f"HTTP请求失败: {response.status_code}"
                    
                    return {
                        "status": "error",
                        "progress": 0,
                        "error": error_msg
                    }
                    
            except requests.exceptions.RequestException as e:
                return {
                    "status": "error",
                    "progress": 0,
                    "error": f"网络请求失败: {str(e)}"
                }
            except Exception as e:
                return {
                    "status": "error",
                    "progress": 0,
                    "error": f"状态查询失败: {str(e)}"
                }
                
        except Exception as e:
            error_msg = f"无法获取操作状态: {str(e)}"
            return {
                "status": "error",
                "progress": 0,
                "error": error_msg
            }
    
    def _extract_video_bytes_from_response(self, response_data: dict) -> str:
        """从响应数据中提取视频字节数据"""
        # 提取视频URI（Google Veo API的标准格式）
        video_uri = self._extract_video_uri_from_response(response_data)
        if video_uri:
            return self._download_video_from_uri(video_uri)
        
        return None
    
    def _extract_video_uri_from_response(self, response_data: dict) -> str:
        """从响应中提取视频URI"""
        try:
            # Google Veo API的标准响应结构
            if "generateVideoResponse" in response_data:
                generate_response = response_data["generateVideoResponse"]
                if "generatedSamples" in generate_response:
                    samples = generate_response["generatedSamples"]
                    if samples and len(samples) > 0:
                        first_sample = samples[0]
                        if "video" in first_sample and "uri" in first_sample["video"]:
                            return first_sample["video"]["uri"]
            
            return None
            
        except Exception as e:
            return None
    
    def _download_video_from_uri(self, video_uri: str) -> str:
        """从URI下载视频并转换为base64"""
        try:
            import requests
            import base64
            
            # 使用API密钥下载视频
            headers = {
                "x-goog-api-key": self.api_key
            }
            
            response = requests.get(video_uri, headers=headers, timeout=60)
            
            if response.status_code == 200:
                video_bytes = response.content
                
                # 转换为base64
                video_base64 = base64.b64encode(video_bytes).decode('utf-8')
                
                return video_base64
            else:
                return None
                
        except Exception as e:
            return None
    
    def _download_video_streaming(self, video_uri: str, progress_callback=None):
        """流式下载视频，支持进度回调"""
        try:
            import requests
            import base64
            import tempfile
            import os
            
            # 使用API密钥下载视频
            headers = {
                "x-goog-api-key": self.api_key
            }
            
            response = requests.get(video_uri, headers=headers, stream=True, timeout=60)
            
            if response.status_code == 200:
                # 获取文件总大小
                total_size = int(response.headers.get('content-length', 0))
                downloaded = 0
                
                # 创建临时文件
                with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp_file:
                    tmp_file_path = tmp_file.name
                    
                    # 流式下载
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            tmp_file.write(chunk)
                            downloaded += len(chunk)
                            
                            # 调用进度回调
                            if progress_callback and total_size > 0:
                                progress = downloaded / total_size
                                progress_callback(progress, downloaded, total_size, tmp_file_path)
                
                # 读取完整文件并转换为base64
                with open(tmp_file_path, 'rb') as f:
                    video_bytes = f.read()
                
                # 清理临时文件
                try:
                    os.unlink(tmp_file_path)
                except:
                    pass
                
                # 转换为base64
                video_base64 = base64.b64encode(video_bytes).decode('utf-8')
                
                return video_base64
            else:
                return None
                
        except Exception as e:
            return None



# 全局服务实例和缓存
_veo_service: Optional[VeoAPIService] = None
_video_cache: Dict[str, str] = {}  # 简单的内存缓存


def get_veo_service() -> Optional[VeoAPIService]:
    """获取Veo服务实例"""
    global _veo_service
    
    try:
        if "GOOGLE_API_KEY" not in st.secrets:
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


def get_video_status_sync(operation_name: str) -> Dict[str, Any]:
    """同步获取视频状态（用于Streamlit）"""
    try:
        service = get_veo_service()
        if not service:
            return {
                "status": "error",
                "error": "Veo服务未配置"
            }
        
        result = service.get_video_status(operation_name)
        return result
        
    except Exception as e:
        error_msg = f"get_video_status_sync 异常: {str(e)}"
        return {
            "status": "error",
            "progress": 0,
            "error": error_msg
        }


def download_video_with_progress(video_uri: str, progress_callback=None) -> Optional[str]:
    """带进度的视频下载"""
    global _video_cache
    
    # 检查缓存
    if video_uri in _video_cache:
        return _video_cache[video_uri]
    
    service = get_veo_service()
    if not service:
        return None
    
    # 流式下载
    video_base64 = service._download_video_streaming(video_uri, progress_callback)
    
    # 缓存结果
    if video_base64:
        _video_cache[video_uri] = video_base64
    
    return video_base64


def get_cached_video(video_uri: str) -> Optional[str]:
    """获取缓存的视频"""
    global _video_cache
    return _video_cache.get(video_uri)


def clear_video_cache():
    """清理视频缓存"""
    global _video_cache
    _video_cache.clear()
