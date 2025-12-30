"""
Google Veo 3.1 API Service - 简化版，只使用Gemini API

使用同步HTTP请求避免事件循环问题
"""

import json
import base64
import requests
from datetime import datetime
from typing import Optional, Dict, Any
import streamlit as st


class VeoAPIService:
    """Google Veo 3.1 API服务 - 只使用Gemini API"""
    
    def __init__(self):
        # 只使用Gemini API
        self.api_key = st.secrets["GOOGLE_API_KEY"]
        self.model_id = "veo-3.1-generate-preview"
        self.base_url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_id}"
        
        print(f"[DEBUG] 使用Gemini API")
        print(f"  模型ID: {self.model_id}")
        print(f"  基础URL: {self.base_url}")
    
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
            
            # 构建参数 - 确保符合Veo 3.1限制
            valid_durations = [4, 6, 8]
            if duration not in valid_durations:
                duration = min(valid_durations, key=lambda x: abs(x - duration))
            
            # 参考图片转视频只支持8秒
            if reference_image and duration != 8:
                duration = 8
            
            parameters = {
                "aspectRatio": aspect_ratio,
                "durationSeconds": duration,
                "resolution": quality.lower(),
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
            
            print(f"[DEBUG] 发送请求到: {url}")
            print(f"[DEBUG] 请求数据: {json.dumps(request_data, indent=2, ensure_ascii=False)}")
            
            response = requests.post(url, json=request_data, headers=headers, timeout=60)
            
            print(f"[DEBUG] 响应状态码: {response.status_code}")
            
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
    
    def get_video_status(self, operation_name: str) -> Dict[str, Any]:
        """获取视频生成状态"""
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
                print(f"[DEBUG] 状态响应: {json.dumps(result, indent=2, ensure_ascii=False)}")
                
                # 检查操作是否完成
                if result.get("done", False):
                    if "error" in result:
                        return {
                            "status": "failed",
                            "progress": 0,
                            "error": result["error"].get("message", "生成失败")
                        }
                    else:
                        # 提取视频数据 - 优先字节数据，备用URL
                        video_data = None
                        video_url = None
                        video_bytes = None
                        
                        if "response" in result:
                            response_data = result["response"]
                            video_info = self._extract_video_data(response_data)
                            video_bytes = video_info.get("video_bytes")
                            video_url = video_info.get("video_url")
                        
                        print(f"[DEBUG] 提取结果 - 字节数据: {'有' if video_bytes else '无'}, URL: {video_url}")
                        
                        return {
                            "status": "completed",
                            "progress": 100,
                            "video_bytes": video_bytes,
                            "video_url": video_url,
                            "message": "视频生成完成",
                            "raw_response": result
                        }
                else:
                    # 仍在处理中
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
        """从响应数据中提取视频数据（优先获取字节数据）"""
        result = {"video_url": None, "video_bytes": None}
        
        # 方法1: 检查predictions结构
        if "predictions" in response_data:
            predictions = response_data["predictions"]
            if predictions and len(predictions) > 0:
                prediction = predictions[0]
                
                # 检查视频数据对象
                if "video" in prediction:
                    video_data = prediction["video"]
                    
                    # 优先获取字节数据（官方推荐方式）
                    if "video_bytes" in video_data:
                        result["video_bytes"] = video_data["video_bytes"]
                    elif "videoBytes" in video_data:
                        result["video_bytes"] = video_data["videoBytes"]
                    elif "bytesBase64Encoded" in video_data:
                        result["video_bytes"] = video_data["bytesBase64Encoded"]
                    
                    # 备用：获取URL
                    if not result["video_bytes"]:
                        video_url = (video_data.get("uri") or 
                                   video_data.get("gcsUri") or
                                   video_data.get("url") or
                                   video_data.get("downloadUrl") or
                                   video_data.get("signedUrl") or
                                   video_data.get("videoUri") or
                                   video_data.get("fileUri"))
                        if video_url:
                            result["video_url"] = video_url
                
                # 检查预测对象的直接字段
                if not result["video_bytes"] and not result["video_url"]:
                    # 检查字节数据
                    if "video_bytes" in prediction:
                        result["video_bytes"] = prediction["video_bytes"]
                    elif "videoBytes" in prediction:
                        result["video_bytes"] = prediction["videoBytes"]
                    elif "bytesBase64Encoded" in prediction:
                        result["video_bytes"] = prediction["bytesBase64Encoded"]
                    
                    # 检查URL
                    if not result["video_bytes"]:
                        video_url = (prediction.get("uri") or 
                                   prediction.get("gcsUri") or
                                   prediction.get("url") or
                                   prediction.get("downloadUrl") or
                                   prediction.get("signedUrl") or
                                   prediction.get("videoUri") or
                                   prediction.get("fileUri") or
                                   prediction.get("video_uri"))
                        if video_url:
                            result["video_url"] = video_url
        
        # 方法2: 检查generatedVideos结构
        if not result["video_bytes"] and not result["video_url"] and "generatedVideos" in response_data:
            generated_videos = response_data["generatedVideos"]
            if generated_videos and len(generated_videos) > 0:
                video_info = generated_videos[0]
                
                if "video" in video_info:
                    video_data = video_info["video"]
                    
                    # 优先获取字节数据
                    if "video_bytes" in video_data:
                        result["video_bytes"] = video_data["video_bytes"]
                    elif "videoBytes" in video_data:
                        result["video_bytes"] = video_data["videoBytes"]
                    elif "bytesBase64Encoded" in video_data:
                        result["video_bytes"] = video_data["bytesBase64Encoded"]
                    
                    # 备用：获取URL
                    if not result["video_bytes"]:
                        video_url = (video_data.get("uri") or 
                                   video_data.get("gcsUri") or
                                   video_data.get("url") or
                                   video_data.get("downloadUrl") or
                                   video_data.get("signedUrl") or
                                   video_data.get("videoUri") or
                                   video_data.get("fileUri"))
                        if video_url:
                            result["video_url"] = video_url
        
        # 方法3: 递归搜索所有可能的字节数据和URL字段
        if not result["video_bytes"] and not result["video_url"]:
            def find_video_data_in_dict(data, depth=0):
                if depth > 5:  # 防止无限递归
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
                            if not found_result["video_bytes"]:  # 只有没有字节数据时才返回URL
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
            
            result = find_video_data_in_dict(response_data)
        
        return result
    
    def _handle_error_response(self, response: requests.Response, url: str) -> Dict[str, Any]:
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
        # 只检查Gemini API密钥
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


def get_video_status_sync(operation_name: str) -> Dict[str, Any]:
    """同步获取视频状态（用于Streamlit）"""
    service = get_veo_service()
    if not service:
        return {
            "status": "error",
            "error": "Veo服务未配置"
        }
    
    return service.get_video_status(operation_name)
