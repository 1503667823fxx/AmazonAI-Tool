"""
Video Studio 图片处理服务
解决图片到视频的API兼容性问题
"""

import base64
import io
from typing import Optional, Dict, Any, Tuple
from PIL import Image


class VideoStudioImageProcessor:
    """Video Studio 图片处理器"""
    
    # 支持的图片格式
    SUPPORTED_FORMATS = ['JPEG', 'PNG', 'WEBP']
    
    # 推荐的图片尺寸
    RECOMMENDED_SIZES = {
        "16:9": (1280, 720),
        "9:16": (720, 1280)
    }
    
    # 最大文件大小 (10MB)
    MAX_FILE_SIZE = 10 * 1024 * 1024
    
    def __init__(self):
        pass
        
    def validate_image(self, image_bytes: bytes) -> Dict[str, Any]:
        """
        验证图片是否符合要求
        
        Args:
            image_bytes: 图片字节数据
            
        Returns:
            验证结果字典
        """
        try:
            # 检查文件大小
            if len(image_bytes) > self.MAX_FILE_SIZE:
                return {
                    "valid": False,
                    "error": f"图片文件过大 ({len(image_bytes)/1024/1024:.1f}MB)，最大支持10MB"
                }
            
            # 尝试打开图片
            try:
                image = Image.open(io.BytesIO(image_bytes))
                image.verify()  # 验证图片完整性
                
                # 重新打开图片（verify后需要重新打开）
                image = Image.open(io.BytesIO(image_bytes))
                
            except Exception as e:
                return {
                    "valid": False,
                    "error": f"无效的图片文件: {str(e)}"
                }
            
            # 检查图片格式
            if image.format not in self.SUPPORTED_FORMATS:
                return {
                    "valid": False,
                    "error": f"不支持的图片格式: {image.format}，支持格式: {', '.join(self.SUPPORTED_FORMATS)}"
                }
            
            # 获取图片信息
            width, height = image.size
            aspect_ratio = self._calculate_aspect_ratio(width, height)
            
            return {
                "valid": True,
                "format": image.format,
                "size": (width, height),
                "aspect_ratio": aspect_ratio,
                "file_size": len(image_bytes),
                "mode": image.mode
            }
            
        except Exception as e:
            return {
                "valid": False,
                "error": f"图片验证失败: {str(e)}"
            }

    
    def prepare_for_veo_api(self, image_bytes: bytes) -> Dict[str, Any]:
        """
        为Veo API准备图片数据，尝试多种格式解决兼容性问题
        """
        try:
            # 验证图片
            validation = self.validate_image(image_bytes)
            if not validation["valid"]:
                return {"success": False, "error": validation["error"]}
            
            # 优化图片
            image = Image.open(io.BytesIO(image_bytes))
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # 调整到合适尺寸
            image = self._resize_image_smart(image, (1280, 720))
            
            # 转换为字节数据
            output_buffer = io.BytesIO()
            image.save(output_buffer, format='JPEG', quality=90)
            optimized_bytes = output_buffer.getvalue()
            
            # 转换为base64
            base64_data = base64.b64encode(optimized_bytes).decode('utf-8')
            
            # 创建多种API格式，提高兼容性
            formats = {
                # 格式1: 标准格式
                "standard": {
                    "bytesBase64Encoded": base64_data,
                    "mimeType": "image/jpeg"
                },
                # 格式2: 简化格式
                "simple": {
                    "data": base64_data,
                    "type": "image/jpeg"
                },
                # 格式3: 原始字节
                "raw_bytes": optimized_bytes
            }
            
            return {
                "success": True,
                "formats": formats,
                "optimized_bytes": optimized_bytes,
                "base64_data": base64_data
            }
            
        except Exception as e:
            return {"success": False, "error": f"图片处理失败: {str(e)}"}

    
    def _resize_image_smart(self, image: Image.Image, target_size: Tuple[int, int]) -> Image.Image:
        """智能调整图片尺寸"""
        original_width, original_height = image.size
        target_width, target_height = target_size
        
        # 计算缩放比例，保持宽高比
        scale_w = target_width / original_width
        scale_h = target_height / original_height
        scale = min(scale_w, scale_h)
        
        # 计算新尺寸
        new_width = int(original_width * scale)
        new_height = int(original_height * scale)
        
        # 调整图片尺寸
        return image.resize((new_width, new_height), Image.Resampling.LANCZOS)



# 全局处理器实例
_image_processor: Optional[VideoStudioImageProcessor] = None


def get_image_processor() -> VideoStudioImageProcessor:
    """获取图片处理器实例"""
    global _image_processor
    
    if _image_processor is None:
        _image_processor = VideoStudioImageProcessor()
    
    return _image_processor


def process_image_for_video_generation(image_bytes: bytes) -> Dict[str, Any]:
    """处理图片用于视频生成"""
    processor = get_image_processor()
    return processor.prepare_for_veo_api(image_bytes)


def validate_uploaded_image(image_bytes: bytes) -> Dict[str, Any]:
    """验证上传的图片"""
    processor = get_image_processor()
    return processor.validate_image(image_bytes)