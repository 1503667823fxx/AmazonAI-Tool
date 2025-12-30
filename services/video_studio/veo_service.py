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
            # 构建配置 - 处理分辨率和时长的限制
            # 根据API错误：1080p只支持8秒，720p支持4、6、8秒
            
            # 自动调整分辨率和时长的组合
            if quality.lower() == "1080p" and duration != 8:
                print(f"[DEBUG] 1080p分辨率需要8秒时长，当前时长{duration}秒，自动调整为720p")
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
            
            print(f"[DEBUG] 配置参数: {config_params}")
            print(f"[DEBUG] 原始质量: {quality}, 调整后质量: {adjusted_quality}")
            
            try:
                config = types.GenerateVideosConfig(**config_params)
                print(f"[DEBUG] 配置对象创建成功")
            except Exception as e:
                print(f"[DEBUG] 配置对象创建失败: {str(e)}")
                raise
            
            # 生成视频
            if reference_image:
                print(f"[DEBUG] 处理参考图片，大小: {len(reference_image)} bytes")
                
                # 使用图片处理器
                image_result = process_image_for_video_generation(reference_image)
                
                if not image_result["success"]:
                    raise RuntimeError(f"图片处理失败: {image_result['error']}")
                
                print(f"[DEBUG] 图片处理成功")
                
                # 尝试多种格式
                formats = image_result["formats"]
                last_error = None
                
                # 按优先级尝试不同格式和方法
                attempts = [
                    ("standard_dict", formats["standard"]),
                    ("standard_sdk", None),  # 使用SDK方法
                    ("raw_bytes_sdk", formats["raw_bytes"]),
                    ("simple_dict", formats["simple"])
                ]
                
                for attempt_name, format_data in attempts:
                    print(f"[DEBUG] 尝试方法: {attempt_name}")
                    
                    try:
                        if attempt_name == "standard_dict":
                            # 直接使用字典格式
                            operation = self.client.models.generate_videos(
                                model=self.model_id,
                                prompt=prompt,
                                image=format_data,
                                config=config
                            )
                        
                        elif attempt_name == "standard_sdk":
                            # 使用SDK的Image对象
                            if hasattr(types, 'Image') and hasattr(types.Image, 'from_bytes'):
                                image_obj = types.Image.from_bytes(formats["raw_bytes"])
                                operation = self.client.models.generate_videos(
                                    model=self.model_id,
                                    prompt=prompt,
                                    image=image_obj,
                                    config=config
                                )
                            else:
                                raise RuntimeError("SDK Image.from_bytes 不可用")
                        
                        elif attempt_name == "raw_bytes_sdk":
                            # 使用Part对象
                            if hasattr(types, 'Part') and hasattr(types.Part, 'from_bytes'):
                                part_obj = types.Part.from_bytes(data=format_data, mime_type="image/jpeg")
                                operation = self.client.models.generate_videos(
                                    model=self.model_id,
                                    prompt=prompt,
                                    image=part_obj,
                                    config=config
                                )
                            else:
                                raise RuntimeError("SDK Part.from_bytes 不可用")
                        
                        elif attempt_name == "simple_dict":
                            # 简化字典格式
                            operation = self.client.models.generate_videos(
                                model=self.model_id,
                                prompt=prompt,
                                image=format_data,
                                config=config
                            )
                        
                        print(f"[DEBUG] 方法 {attempt_name} 成功!")
                        break
                        
                    except Exception as e:
                        error_msg = str(e)
                        print(f"[DEBUG] 方法 {attempt_name} 失败: {error_msg}")
                        last_error = error_msg
                        continue
                else:
                    # 所有方法都失败了
                    raise RuntimeError(f"所有图片处理方法都失败了。最后错误: {last_error}")
                        
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
    
    def get_video_status(self, operation_name: str) -> Dict[str, Any]:
        """获取视频生成状态"""
        try:
            print(f"[DEBUG] 获取操作状态: {operation_name}")
            
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
                print(f"[DEBUG] 请求URL: {url}")
                
                response = requests.get(url, headers=headers, timeout=30)
                print(f"[DEBUG] HTTP响应状态: {response.status_code}")
                
                if response.status_code == 200:
                    result = response.json()
                    print(f"[DEBUG] 成功获取操作状态")
                    
                    # 检查操作是否完成
                    if result.get("done", False):
                        print(f"[DEBUG] 操作已完成")
                        
                        if "error" in result:
                            error_msg = result["error"].get("message", "生成失败")
                            print(f"[DEBUG] 操作错误: {error_msg}")
                            return {
                                "status": "failed",
                                "progress": 0,
                                "error": error_msg
                            }
                        else:
                            # 尝试提取视频数据
                            video_bytes = None
                            
                            if "response" in result:
                                response_data = result["response"]
                                print(f"[DEBUG] 响应数据结构: {list(response_data.keys())}")
                                
                                # 搜索视频字节数据
                                video_bytes = self._extract_video_bytes_from_response(response_data)
                            else:
                                print(f"[DEBUG] 响应中没有'response'字段，尝试直接搜索")
                                # 有些API可能直接在根级别返回数据
                                video_bytes = self._extract_video_bytes_from_response(result)
                            
                            print(f"[DEBUG] 视频字节数据: {'有' if video_bytes else '无'}")
                            
                            # 如果没找到视频数据，输出完整响应用于调试
                            if not video_bytes:
                                print(f"[DEBUG] 未找到视频数据，完整响应:")
                                import json
                                try:
                                    print(json.dumps(result, indent=2, ensure_ascii=False))
                                except:
                                    print(str(result))
                            
                            return {
                                "status": "completed",
                                "progress": 100,
                                "video_bytes": video_bytes,
                                "message": "视频生成完成",
                                "raw_response": result  # 保存原始响应用于调试
                            }
                    else:
                        print(f"[DEBUG] 操作仍在进行中")
                        return {
                            "status": "processing",
                            "progress": 50,
                            "message": "正在生成视频..."
                        }
                elif response.status_code == 404:
                    print(f"[DEBUG] 操作不存在或已过期")
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
                    
                    print(f"[DEBUG] {error_msg}")
                    return {
                        "status": "error",
                        "progress": 0,
                        "error": error_msg
                    }
                    
            except requests.exceptions.RequestException as e:
                print(f"[DEBUG] HTTP请求异常: {str(e)}")
                return {
                    "status": "error",
                    "progress": 0,
                    "error": f"网络请求失败: {str(e)}"
                }
            except Exception as e:
                print(f"[DEBUG] 其他异常: {str(e)}")
                return {
                    "status": "error",
                    "progress": 0,
                    "error": f"状态查询失败: {str(e)}"
                }
                
        except Exception as e:
            error_msg = f"无法获取操作状态: {str(e)}"
            print(f"[DEBUG] {error_msg}")
            return {
                "status": "error",
                "progress": 0,
                "error": error_msg
            }
    
    def _extract_video_bytes_from_response(self, response_data: dict) -> str:
        """从响应数据中提取视频字节数据"""
        print(f"[DEBUG] 开始提取视频数据，响应结构: {response_data}")
        
        # 首先尝试提取视频URI（Google Veo API的实际格式）
        video_uri = self._extract_video_uri_from_response(response_data)
        if video_uri:
            print(f"[DEBUG] 找到视频URI: {video_uri}")
            # 下载视频并转换为base64
            return self._download_video_from_uri(video_uri)
        
        # 如果没有URI，尝试直接搜索base64数据（备用方案）
        return self._search_direct_video_bytes(response_data)
    
    def _extract_video_uri_from_response(self, response_data: dict) -> str:
        """从响应中提取视频URI"""
        try:
            # Google Veo API的实际响应结构
            if "generateVideoResponse" in response_data:
                generate_response = response_data["generateVideoResponse"]
                if "generatedSamples" in generate_response:
                    samples = generate_response["generatedSamples"]
                    if samples and len(samples) > 0:
                        first_sample = samples[0]
                        if "video" in first_sample and "uri" in first_sample["video"]:
                            return first_sample["video"]["uri"]
            
            # 递归搜索URI字段（备用方案）
            def find_uri(data, depth=0):
                if depth > 10:
                    return None
                
                if isinstance(data, dict):
                    # 搜索URI相关字段
                    uri_fields = ['uri', 'url', 'download_url', 'video_url', 'file_url']
                    for field in uri_fields:
                        if field in data and isinstance(data[field], str):
                            uri = data[field]
                            if uri.startswith('http') and 'generativelanguage.googleapis.com' in uri:
                                return uri
                    
                    # 递归搜索
                    for value in data.values():
                        result = find_uri(value, depth + 1)
                        if result:
                            return result
                
                elif isinstance(data, list):
                    for item in data:
                        result = find_uri(item, depth + 1)
                        if result:
                            return result
                
                return None
            
            return find_uri(response_data)
            
        except Exception as e:
            print(f"[DEBUG] 提取URI时出错: {str(e)}")
            return None
    
    def _download_video_from_uri(self, video_uri: str) -> str:
        """从URI下载视频并转换为base64"""
        try:
            print(f"[DEBUG] 开始下载视频: {video_uri}")
            
            import requests
            import base64
            
            # 使用API密钥下载视频
            headers = {
                "x-goog-api-key": self.api_key
            }
            
            response = requests.get(video_uri, headers=headers, timeout=60)
            print(f"[DEBUG] 下载响应状态: {response.status_code}")
            
            if response.status_code == 200:
                video_bytes = response.content
                print(f"[DEBUG] 视频下载成功，大小: {len(video_bytes)} bytes")
                
                # 转换为base64
                video_base64 = base64.b64encode(video_bytes).decode('utf-8')
                print(f"[DEBUG] Base64转换成功，长度: {len(video_base64)}")
                
                return video_base64
            else:
                print(f"[DEBUG] 视频下载失败: HTTP {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"[DEBUG] 错误详情: {error_data}")
                except:
                    print(f"[DEBUG] 响应文本: {response.text}")
                return None
                
        except Exception as e:
            print(f"[DEBUG] 下载视频时出错: {str(e)}")
            return None
    
    def _search_direct_video_bytes(self, response_data: dict) -> str:
        """搜索直接的视频字节数据（备用方案）"""
        print(f"[DEBUG] 搜索直接的视频字节数据")
        
        # 递归搜索视频字节数据
        def find_video_bytes(data, depth=0, path=""):
            if depth > 10:
                return None
            
            if isinstance(data, dict):
                print(f"[DEBUG] 搜索字典 (深度{depth}, 路径:{path}): {list(data.keys())}")
                
                # 扩展字节数据字段搜索
                bytes_fields = [
                    'video_bytes', 'videoBytes', 'bytesBase64Encoded', 'base64Data', 'videoData',
                    'data', 'content', 'bytes', 'video', 'media', 'file', 'blob',
                    'generatedVideo', 'generated_video', 'output', 'result'
                ]
                
                for field in bytes_fields:
                    if field in data and data[field]:
                        value = data[field]
                        # 检查是否是base64字符串
                        if isinstance(value, str) and len(value) > 100:
                            print(f"[DEBUG] 找到可能的视频数据字段: {field}, 长度: {len(value)}")
                            return value
                
                # 递归搜索所有值
                for key, value in data.items():
                    result = find_video_bytes(value, depth + 1, f"{path}.{key}" if path else key)
                    if result:
                        return result
            
            elif isinstance(data, list):
                print(f"[DEBUG] 搜索列表 (深度{depth}, 路径:{path}): 长度{len(data)}")
                for i, item in enumerate(data):
                    result = find_video_bytes(item, depth + 1, f"{path}[{i}]" if path else f"[{i}]")
                    if result:
                        return result
            
            elif isinstance(data, str) and len(data) > 100:
                # 检查是否是base64编码的视频数据
                print(f"[DEBUG] 检查字符串 (深度{depth}, 路径:{path}): 长度{len(data)}")
                try:
                    import base64
                    # 尝试解码前几个字符看是否是有效的base64
                    test_decode = base64.b64decode(data[:100])
                    print(f"[DEBUG] 可能的base64视频数据，路径: {path}")
                    return data
                except:
                    pass
            
            return None
        
        result = find_video_bytes(response_data)
        
        if result:
            print(f"[DEBUG] 成功提取视频数据，长度: {len(result)}")
        else:
            print(f"[DEBUG] 未找到视频数据")
            # 输出完整的响应结构用于调试
            import json
            print(f"[DEBUG] 完整响应结构: {json.dumps(response_data, indent=2, ensure_ascii=False)}")
        
        return result


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


def get_video_status_sync(operation_name: str) -> Dict[str, Any]:
    """同步获取视频状态（用于Streamlit）"""
    try:
        print(f"[DEBUG] get_video_status_sync 调用，operation_name: {operation_name}")
        print(f"[DEBUG] operation_name 类型: {type(operation_name)}")
        
        service = get_veo_service()
        if not service:
            return {
                "status": "error",
                "error": "Veo服务未配置"
            }
        
        result = service.get_video_status(operation_name)
        print(f"[DEBUG] get_video_status_sync 返回: {result}")
        return result
        
    except Exception as e:
        error_msg = f"get_video_status_sync 异常: {str(e)}"
        print(f"[DEBUG] {error_msg}")
        return {
            "status": "error",
            "progress": 0,
            "error": error_msg
        }
