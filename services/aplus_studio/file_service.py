"""
A+ 文件管理服务
负责文件上传、验证和处理
"""

import os
import io
import hashlib
from typing import Dict, List, Optional, Any, Tuple
from PIL import Image
from datetime import datetime

from app_utils.aplus_studio.models.core_models import UploadedFile


class FileService:
    """A+ 文件管理服务"""
    
    def __init__(self, upload_dir: str = "data/uploads"):
        self.upload_dir = upload_dir
        self.max_file_size = 10 * 1024 * 1024  # 10MB
        self.allowed_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
        self.allowed_mime_types = {
            'image/jpeg', 'image/png', 'image/gif', 'image/webp'
        }
        
        # 确保上传目录存在
        os.makedirs(upload_dir, exist_ok=True)
    
    def validate_file(self, file_data: bytes, filename: str, content_type: str) -> Dict[str, Any]:
        """验证上传的文件"""
        errors = []
        
        # 检查文件大小
        if len(file_data) > self.max_file_size:
            errors.append(f"文件大小超过限制 ({self.max_file_size // (1024*1024)}MB)")
        
        # 检查文件扩展名
        file_ext = os.path.splitext(filename.lower())[1]
        if file_ext not in self.allowed_extensions:
            errors.append(f"不支持的文件格式: {file_ext}")
        
        # 检查MIME类型
        if content_type not in self.allowed_mime_types:
            errors.append(f"不支持的文件类型: {content_type}")
        
        # 验证图片文件
        try:
            image = Image.open(io.BytesIO(file_data))
            image.verify()  # 验证图片完整性
            
            # 重新打开获取信息（verify后需要重新打开）
            image = Image.open(io.BytesIO(file_data))
            width, height = image.size
            
            # 检查图片尺寸
            if width < 100 or height < 100:
                errors.append("图片尺寸太小，最小100x100像素")
            
            if width > 4096 or height > 4096:
                errors.append("图片尺寸太大，最大4096x4096像素")
            
            image_info = {
                "width": width,
                "height": height,
                "format": image.format,
                "mode": image.mode
            }
            
        except Exception as e:
            errors.append(f"图片文件损坏或格式错误: {e}")
            image_info = {}
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "image_info": image_info
        }
    
    def process_upload(self, file_data: bytes, filename: str, content_type: str) -> Dict[str, Any]:
        """处理文件上传"""
        # 验证文件
        validation_result = self.validate_file(file_data, filename, content_type)
        
        if not validation_result["valid"]:
            return {
                "success": False,
                "errors": validation_result["errors"]
            }
        
        try:
            # 生成文件哈希
            file_hash = hashlib.md5(file_data).hexdigest()
            
            # 创建UploadedFile对象
            uploaded_file = UploadedFile(
                filename=filename,
                content_type=content_type,
                size=len(file_data),
                data=file_data,
                upload_time=datetime.now()
            )
            
            # 保存文件到磁盘（可选）
            saved_path = self._save_file_to_disk(file_data, filename, file_hash)
            
            return {
                "success": True,
                "uploaded_file": uploaded_file,
                "file_hash": file_hash,
                "saved_path": saved_path,
                "image_info": validation_result["image_info"]
            }
            
        except Exception as e:
            return {
                "success": False,
                "errors": [f"文件处理失败: {e}"]
            }
    
    def process_multiple_uploads(self, files_data: List[Tuple[bytes, str, str]]) -> Dict[str, Any]:
        """处理多文件上传"""
        results = []
        successful_uploads = []
        failed_uploads = []
        
        for file_data, filename, content_type in files_data:
            result = self.process_upload(file_data, filename, content_type)
            results.append({
                "filename": filename,
                "result": result
            })
            
            if result["success"]:
                successful_uploads.append(result["uploaded_file"])
            else:
                failed_uploads.append({
                    "filename": filename,
                    "errors": result["errors"]
                })
        
        return {
            "total_files": len(files_data),
            "successful_count": len(successful_uploads),
            "failed_count": len(failed_uploads),
            "successful_uploads": successful_uploads,
            "failed_uploads": failed_uploads,
            "detailed_results": results
        }
    
    def optimize_image(self, image_data: bytes, max_width: int = 1024, 
                      max_height: int = 1024, quality: int = 85) -> bytes:
        """优化图片"""
        try:
            image = Image.open(io.BytesIO(image_data))
            
            # 转换为RGB模式（如果需要）
            if image.mode in ('RGBA', 'LA'):
                background = Image.new('RGB', image.size, (255, 255, 255))
                if image.mode == 'RGBA':
                    background.paste(image, mask=image.split()[-1])
                else:
                    background.paste(image)
                image = background
            elif image.mode != 'RGB':
                image = image.convert('RGB')
            
            # 调整尺寸
            image.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
            
            # 保存为JPEG格式
            output_buffer = io.BytesIO()
            image.save(output_buffer, format='JPEG', quality=quality, optimize=True)
            
            return output_buffer.getvalue()
            
        except Exception as e:
            raise Exception(f"图片优化失败: {e}")
    
    def create_thumbnail(self, image_data: bytes, size: Tuple[int, int] = (200, 200)) -> bytes:
        """创建缩略图"""
        try:
            image = Image.open(io.BytesIO(image_data))
            
            # 创建缩略图
            image.thumbnail(size, Image.Resampling.LANCZOS)
            
            # 保存为PNG格式（保持透明度）
            output_buffer = io.BytesIO()
            image.save(output_buffer, format='PNG')
            
            return output_buffer.getvalue()
            
        except Exception as e:
            raise Exception(f"缩略图创建失败: {e}")
    
    def get_image_info(self, image_data: bytes) -> Dict[str, Any]:
        """获取图片信息"""
        try:
            image = Image.open(io.BytesIO(image_data))
            
            return {
                "width": image.width,
                "height": image.height,
                "format": image.format,
                "mode": image.mode,
                "size_bytes": len(image_data),
                "aspect_ratio": round(image.width / image.height, 2)
            }
            
        except Exception as e:
            return {"error": f"获取图片信息失败: {e}"}
    
    def convert_image_format(self, image_data: bytes, target_format: str, 
                           quality: int = 85) -> bytes:
        """转换图片格式"""
        try:
            image = Image.open(io.BytesIO(image_data))
            
            # 格式映射
            format_map = {
                'jpeg': 'JPEG',
                'jpg': 'JPEG',
                'png': 'PNG',
                'webp': 'WEBP'
            }
            
            pil_format = format_map.get(target_format.lower())
            if not pil_format:
                raise ValueError(f"不支持的目标格式: {target_format}")
            
            # 处理透明度
            if pil_format == 'JPEG' and image.mode in ('RGBA', 'LA'):
                background = Image.new('RGB', image.size, (255, 255, 255))
                if image.mode == 'RGBA':
                    background.paste(image, mask=image.split()[-1])
                else:
                    background.paste(image)
                image = background
            
            # 保存为目标格式
            output_buffer = io.BytesIO()
            
            if pil_format == 'JPEG':
                image.save(output_buffer, format=pil_format, quality=quality)
            else:
                image.save(output_buffer, format=pil_format)
            
            return output_buffer.getvalue()
            
        except Exception as e:
            raise Exception(f"图片格式转换失败: {e}")
    
    def _save_file_to_disk(self, file_data: bytes, filename: str, file_hash: str) -> str:
        """保存文件到磁盘"""
        try:
            # 使用哈希值作为文件名，避免重复
            file_ext = os.path.splitext(filename)[1]
            safe_filename = f"{file_hash}{file_ext}"
            
            # 按日期创建子目录
            date_dir = datetime.now().strftime("%Y/%m/%d")
            full_dir = os.path.join(self.upload_dir, date_dir)
            os.makedirs(full_dir, exist_ok=True)
            
            # 完整文件路径
            file_path = os.path.join(full_dir, safe_filename)
            
            # 如果文件已存在，直接返回路径
            if os.path.exists(file_path):
                return file_path
            
            # 保存文件
            with open(file_path, 'wb') as f:
                f.write(file_data)
            
            return file_path
            
        except Exception as e:
            print(f"保存文件到磁盘失败: {e}")
            return ""
    
    def cleanup_old_files(self, days_old: int = 30) -> int:
        """清理旧文件"""
        cleaned_count = 0
        cutoff_time = datetime.now().timestamp() - (days_old * 24 * 3600)
        
        try:
            for root, dirs, files in os.walk(self.upload_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    
                    # 检查文件修改时间
                    if os.path.getmtime(file_path) < cutoff_time:
                        try:
                            os.remove(file_path)
                            cleaned_count += 1
                        except Exception as e:
                            print(f"删除文件失败 {file_path}: {e}")
            
            # 删除空目录
            for root, dirs, files in os.walk(self.upload_dir, topdown=False):
                for dir_name in dirs:
                    dir_path = os.path.join(root, dir_name)
                    try:
                        if not os.listdir(dir_path):  # 目录为空
                            os.rmdir(dir_path)
                    except Exception:
                        pass
                        
        except Exception as e:
            print(f"清理旧文件失败: {e}")
        
        return cleaned_count
    
    def get_upload_statistics(self) -> Dict[str, Any]:
        """获取上传统计信息"""
        total_files = 0
        total_size = 0
        
        try:
            for root, dirs, files in os.walk(self.upload_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    if os.path.isfile(file_path):
                        total_files += 1
                        total_size += os.path.getsize(file_path)
        except Exception as e:
            print(f"获取统计信息失败: {e}")
        
        return {
            "total_files": total_files,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "max_file_size_mb": self.max_file_size // (1024 * 1024),
            "allowed_extensions": list(self.allowed_extensions),
            "upload_dir": self.upload_dir
        }