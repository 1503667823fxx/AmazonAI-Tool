"""
视频代理服务 - 用于处理需要认证的视频URL访问
"""

import requests
import streamlit as st
from typing import Optional, Dict, Any
import base64
import io


class VideoProxyService:
    """视频代理服务，处理需要认证的视频访问"""
    
    def __init__(self):
        self.api_key = st.secrets.get("GOOGLE_API_KEY")
    
    def get_video_with_auth(self, video_url: str) -> Optional[bytes]:
        """
        使用认证头获取视频内容
        """
        if not self.api_key:
            return None
        
        try:
            headers = {
                "x-goog-api-key": self.api_key,
                "User-Agent": "VideoStudio-Proxy/1.0"
            }
            
            response = requests.get(video_url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                return response.content
            else:
                print(f"[DEBUG] 视频获取失败: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"[DEBUG] 视频代理错误: {str(e)}")
            return None
    
    def create_downloadable_video(self, video_url: str, job_id: str) -> Optional[str]:
        """
        创建可下载的视频数据URL
        """
        video_content = self.get_video_with_auth(video_url)
        
        if video_content:
            # 创建base64编码的数据URL
            video_base64 = base64.b64encode(video_content).decode('utf-8')
            data_url = f"data:video/mp4;base64,{video_base64}"
            return data_url
        
        return None
    
    def get_video_info(self, video_url: str) -> Dict[str, Any]:
        """
        获取视频信息（不下载完整内容）
        """
        if not self.api_key:
            return {"accessible": False, "reason": "No API key"}
        
        try:
            headers = {
                "x-goog-api-key": self.api_key,
                "User-Agent": "VideoStudio-Proxy/1.0"
            }
            
            # 只获取头部信息
            response = requests.head(video_url, headers=headers, timeout=10)
            
            return {
                "accessible": response.status_code == 200,
                "status_code": response.status_code,
                "content_type": response.headers.get("content-type", "unknown"),
                "content_length": response.headers.get("content-length", "unknown"),
                "reason": "OK" if response.status_code == 200 else f"HTTP {response.status_code}"
            }
            
        except Exception as e:
            return {
                "accessible": False,
                "reason": str(e)
            }


# 全局服务实例
_video_proxy_service: Optional[VideoProxyService] = None


def get_video_proxy_service() -> Optional[VideoProxyService]:
    """获取视频代理服务实例"""
    global _video_proxy_service
    
    try:
        if _video_proxy_service is None:
            _video_proxy_service = VideoProxyService()
        
        return _video_proxy_service
    except Exception:
        return None


def test_video_accessibility(video_url: str) -> Dict[str, Any]:
    """测试视频URL的可访问性"""
    service = get_video_proxy_service()
    if not service:
        return {"accessible": False, "reason": "Service not available"}
    
    return service.get_video_info(video_url)


def create_authenticated_download(video_url: str, job_id: str) -> Optional[str]:
    """创建认证下载链接"""
    service = get_video_proxy_service()
    if not service:
        return None
    
    return service.create_downloadable_video(video_url, job_id)