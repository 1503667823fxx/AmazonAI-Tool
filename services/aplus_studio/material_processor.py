"""
素材处理器

处理用户上传的文件和文本，包括图像处理、文档解析、验证和优化。
"""

import logging
import hashlib
import tempfile
import os
from typing import List, Dict, Any, Optional, Union, Tuple
from datetime import datetime
from PIL import Image, ImageOps
import io

from .models import (
    MaterialSet, UploadedFile, MaterialType, ValidationStatus,
    APLUS_IMAGE_SPECS
)

logger = logging.getLogger(__name__)


class MaterialProcessingError(Exception):
    """素材处理错误"""
    pass


class MaterialProcessor:
    """
    素材处理器
    
    提供图像处理、文档解析、文件验证等功能。
    """
    
    def __init__(self):
        self.temp_dir = tempfile.mkdtemp(prefix="aplus_materials_")
        self._processing_stats = {
            'total_processed': 0,
            'successful_processed': 0,
            'failed_processed': 0,
            'images_processed': 0,
            'documents_processed': 0
        }
        
        # 支持的文件格式
        self.supported_image_formats = {'PNG', 'JPG', 'JPEG', 'WEBP'}
        self.supported_document_formats = {'PDF', 'DOC', 'DOCX', 'TXT'}
        
        # 图像处理配置
        self.image_config = {
            'max_size': APLUS_IMAGE_SPECS['max_file_size'],
            'target_dimensions': APLUS_IMAGE_SPECS['dimensions'],
            'min_resolution': APLUS_IMAGE_SPECS['min_resolution'],
            'quality': 85,
            'optimize': True
        }
    
    def process_uploaded_file(self, 
                            file_content: Union[bytes, str, Image.Image],
                            filename: str,
                            file_type: MaterialType) -> UploadedFile:
        """
        处理单个上传文件
        
        Args:
            file_content: 文件内容
            filename: 文件名
            file_type: 文件类型
            
        Returns:
            处理后的上传文件对象
            
        Raises:
            MaterialProcessingError: 处理失败时抛出
        """
        try:
            self._processing_stats['total_processed'] += 1
            
            # 创建基础文件对象
            uploaded_file = UploadedFile(
                filename=filename,
                file_type=file_type,
                file_size=self._calculate_file_size(file_content),
                content=file_content,
                validation_status=ValidationStatus.PENDING
            )
            
            # 根据文件类型进行处理
            if file_type == MaterialType.IMAGE:
                uploaded_file = self._process_image(uploaded_file)
                self._processing_stats['images_processed'] += 1
            elif file_type == MaterialType.DOCUMENT:
                uploaded_file = self._process_document(uploaded_file)
                self._processing_stats['documents_processed'] += 1
            
            # 验证处理结果
            validation_result = self._validate_processed_file(uploaded_file)
            uploaded_file.validation_status = (
                ValidationStatus.PASSED if validation_result['is_valid'] 
                else ValidationStatus.FAILED
            )
            
            self._processing_stats['successful_processed'] += 1
            logger.info(f"Successfully processed {filename}")
            
            return uploaded_file
            
        except Exception as e:
            self._processing_stats['failed_processed'] += 1
            logger.error(f"Failed to process {filename}: {str(e)}")
            raise MaterialProcessingError(f"Failed to process {filename}: {str(e)}") from e
    
    def _process_image(self, uploaded_file: UploadedFile) -> UploadedFile:
        """
        处理图像文件
        
        Args:
            uploaded_file: 上传文件对象
            
        Returns:
            处理后的文件对象
        """
        try:
            # 如果内容已经是PIL Image，直接使用
            if isinstance(uploaded_file.content, Image.Image):
                image = uploaded_file.content
            else:
                # 从字节数据创建图像
                if isinstance(uploaded_file.content, bytes):
                    image = Image.open(io.BytesIO(uploaded_file.content))
                else:
                    raise MaterialProcessingError("Invalid image content type")
            
            # 图像优化处理
            processed_image = self._optimize_image(image)
            
            # 生成缩略图
            thumbnail = self._generate_thumbnail(processed_image)
            
            # 更新文件内容
            uploaded_file.content = processed_image
            
            # 添加元数据
            if 'metadata' not in uploaded_file.__dict__:
                uploaded_file.__dict__['metadata'] = {}
            
            uploaded_file.__dict__['metadata'].update({
                'original_size': image.size,
                'processed_size': processed_image.size,
                'format': processed_image.format,
                'mode': processed_image.mode,
                'has_thumbnail': True,
                'thumbnail': thumbnail,
                'optimization_applied': True
            })
            
            return uploaded_file
            
        except Exception as e:
            raise MaterialProcessingError(f"Image processing failed: {str(e)}") from e
    
    def _optimize_image(self, image: Image.Image) -> Image.Image:
        """
        优化图像以符合A+规范
        
        Args:
            image: 原始图像
            
        Returns:
            优化后的图像
        """
        # 转换为RGB模式（A+要求）
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # 调整尺寸以符合A+规范
        target_size = self.image_config['target_dimensions']
        if image.size != target_size:
            # 保持宽高比的情况下调整尺寸
            image = ImageOps.fit(image, target_size, Image.Resampling.LANCZOS)
        
        # 自动调整方向
        image = ImageOps.exif_transpose(image)
        
        return image
    
    def _generate_thumbnail(self, image: Image.Image, size: Tuple[int, int] = (150, 150)) -> Image.Image:
        """
        生成缩略图
        
        Args:
            image: 原始图像
            size: 缩略图尺寸
            
        Returns:
            缩略图
        """
        thumbnail = image.copy()
        thumbnail.thumbnail(size, Image.Resampling.LANCZOS)
        return thumbnail
    
    def _process_document(self, uploaded_file: UploadedFile) -> UploadedFile:
        """
        处理文档文件
        
        Args:
            uploaded_file: 上传文件对象
            
        Returns:
            处理后的文件对象
        """
        try:
            # 提取文本内容
            extracted_text = self._extract_text_from_document(uploaded_file)
            
            # 添加元数据
            if 'metadata' not in uploaded_file.__dict__:
                uploaded_file.__dict__['metadata'] = {}
            
            uploaded_file.__dict__['metadata'].update({
                'extracted_text': extracted_text,
                'text_length': len(extracted_text),
                'extraction_successful': bool(extracted_text),
                'processing_timestamp': datetime.now().isoformat()
            })
            
            return uploaded_file
            
        except Exception as e:
            raise MaterialProcessingError(f"Document processing failed: {str(e)}") from e
    
    def _extract_text_from_document(self, uploaded_file: UploadedFile) -> str:
        """
        从文档中提取文本
        
        Args:
            uploaded_file: 上传文件对象
            
        Returns:
            提取的文本内容
        """
        filename = uploaded_file.filename.lower()
        
        if filename.endswith('.txt'):
            # 处理纯文本文件
            if isinstance(uploaded_file.content, bytes):
                return uploaded_file.content.decode('utf-8', errors='ignore')
            elif isinstance(uploaded_file.content, str):
                return uploaded_file.content
        
        elif filename.endswith('.pdf'):
            # PDF文件处理（需要安装PyPDF2或类似库）
            return self._extract_pdf_text(uploaded_file.content)
        
        elif filename.endswith(('.doc', '.docx')):
            # Word文档处理（需要安装python-docx）
            return self._extract_word_text(uploaded_file.content)
        
        return ""
    
    def _extract_pdf_text(self, content: bytes) -> str:
        """
        从PDF提取文本（简化实现）
        
        Args:
            content: PDF文件内容
            
        Returns:
            提取的文本
        """
        try:
            # 这里应该使用PyPDF2或pdfplumber等库
            # 暂时返回占位符
            return "[PDF文本提取需要安装相应库]"
        except Exception as e:
            logger.warning(f"PDF text extraction failed: {str(e)}")
            return ""
    
    def _extract_word_text(self, content: bytes) -> str:
        """
        从Word文档提取文本（简化实现）
        
        Args:
            content: Word文档内容
            
        Returns:
            提取的文本
        """
        try:
            # 这里应该使用python-docx库
            # 暂时返回占位符
            return "[Word文档文本提取需要安装相应库]"
        except Exception as e:
            logger.warning(f"Word text extraction failed: {str(e)}")
            return ""
    
    def _calculate_file_size(self, content: Union[bytes, str, Image.Image]) -> int:
        """
        计算文件大小
        
        Args:
            content: 文件内容
            
        Returns:
            文件大小（字节）
        """
        if isinstance(content, bytes):
            return len(content)
        elif isinstance(content, str):
            return len(content.encode('utf-8'))
        elif isinstance(content, Image.Image):
            # 估算PIL图像的内存大小
            return content.size[0] * content.size[1] * len(content.getbands())
        else:
            return 0
    
    def _validate_processed_file(self, uploaded_file: UploadedFile) -> Dict[str, Any]:
        """
        验证处理后的文件
        
        Args:
            uploaded_file: 处理后的文件
            
        Returns:
            验证结果
        """
        validation_result = {
            'is_valid': True,
            'issues': [],
            'warnings': []
        }
        
        # 文件大小检查
        if uploaded_file.file_size > self.image_config['max_size']:
            validation_result['is_valid'] = False
            validation_result['issues'].append(f"File size {uploaded_file.file_size} exceeds maximum {self.image_config['max_size']}")
        
        # 图像特定验证
        if uploaded_file.file_type == MaterialType.IMAGE:
            if isinstance(uploaded_file.content, Image.Image):
                image = uploaded_file.content
                
                # 尺寸检查
                if image.size != self.image_config['target_dimensions']:
                    validation_result['warnings'].append(f"Image size {image.size} differs from target {self.image_config['target_dimensions']}")
                
                # 格式检查
                if image.format not in self.supported_image_formats:
                    validation_result['warnings'].append(f"Image format {image.format} may not be optimal")
        
        return validation_result
    
    def batch_process_materials(self, material_set: MaterialSet) -> MaterialSet:
        """
        批量处理素材集合
        
        Args:
            material_set: 原始素材集合
            
        Returns:
            处理后的素材集合
        """
        processed_set = MaterialSet()
        
        # 处理图像
        for image_file in material_set.images:
            try:
                processed_file = self.process_uploaded_file(
                    image_file.content,
                    image_file.filename,
                    MaterialType.IMAGE
                )
                processed_set.images.append(processed_file)
            except MaterialProcessingError as e:
                logger.error(f"Failed to process image {image_file.filename}: {str(e)}")
        
        # 处理文档
        for doc_file in material_set.documents:
            try:
                processed_file = self.process_uploaded_file(
                    doc_file.content,
                    doc_file.filename,
                    MaterialType.DOCUMENT
                )
                processed_set.documents.append(processed_file)
            except MaterialProcessingError as e:
                logger.error(f"Failed to process document {doc_file.filename}: {str(e)}")
        
        # 复制文本输入和自定义提示
        processed_set.text_inputs = material_set.text_inputs.copy()
        processed_set.custom_prompts = material_set.custom_prompts.copy()
        
        return processed_set
    
    def generate_material_preview(self, uploaded_file: UploadedFile) -> Dict[str, Any]:
        """
        生成素材预览信息
        
        Args:
            uploaded_file: 上传文件
            
        Returns:
            预览信息字典
        """
        preview = {
            'filename': uploaded_file.filename,
            'file_type': uploaded_file.file_type.value,
            'file_size': uploaded_file.file_size,
            'validation_status': uploaded_file.validation_status.value,
            'upload_timestamp': uploaded_file.upload_timestamp.isoformat()
        }
        
        # 添加类型特定的预览信息
        if uploaded_file.file_type == MaterialType.IMAGE and isinstance(uploaded_file.content, Image.Image):
            image = uploaded_file.content
            preview.update({
                'dimensions': image.size,
                'format': image.format,
                'mode': image.mode,
                'has_thumbnail': hasattr(uploaded_file, 'metadata') and 
                               uploaded_file.__dict__.get('metadata', {}).get('has_thumbnail', False)
            })
        
        elif uploaded_file.file_type == MaterialType.DOCUMENT:
            metadata = uploaded_file.__dict__.get('metadata', {})
            preview.update({
                'text_extracted': metadata.get('extraction_successful', False),
                'text_length': metadata.get('text_length', 0)
            })
        
        return preview
    
    def assess_material_quality(self, uploaded_file: UploadedFile) -> Dict[str, Any]:
        """
        评估素材质量
        
        Args:
            uploaded_file: 上传文件
            
        Returns:
            质量评估结果
        """
        quality_assessment = {
            'overall_score': 0.0,
            'factors': {},
            'recommendations': []
        }
        
        if uploaded_file.file_type == MaterialType.IMAGE and isinstance(uploaded_file.content, Image.Image):
            image = uploaded_file.content
            
            # 分辨率评分
            resolution_score = min(1.0, min(image.size) / 600)  # 基于最小边长
            quality_assessment['factors']['resolution'] = resolution_score
            
            # 尺寸匹配评分
            target_size = self.image_config['target_dimensions']
            size_match_score = 1.0 if image.size == target_size else 0.8
            quality_assessment['factors']['size_match'] = size_match_score
            
            # 格式评分
            format_score = 1.0 if image.format in self.supported_image_formats else 0.7
            quality_assessment['factors']['format'] = format_score
            
            # 计算总分
            quality_assessment['overall_score'] = (
                resolution_score * 0.4 + 
                size_match_score * 0.3 + 
                format_score * 0.3
            )
            
            # 生成建议
            if resolution_score < 0.8:
                quality_assessment['recommendations'].append("建议使用更高分辨率的图像")
            if size_match_score < 1.0:
                quality_assessment['recommendations'].append("图像尺寸将被调整以符合A+规范")
            if format_score < 1.0:
                quality_assessment['recommendations'].append("建议使用PNG或JPG格式")
        
        return quality_assessment
    
    def cleanup_temp_files(self):
        """清理临时文件"""
        try:
            import shutil
            if os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
                logger.info("Cleaned up temporary files")
        except Exception as e:
            logger.warning(f"Failed to cleanup temp files: {str(e)}")
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """
        获取处理统计信息
        
        Returns:
            统计信息字典
        """
        return self._processing_stats.copy()
    
    def reset_stats(self):
        """重置统计信息"""
        self._processing_stats = {
            'total_processed': 0,
            'successful_processed': 0,
            'failed_processed': 0,
            'images_processed': 0,
            'documents_processed': 0
        }
    
    def health_check(self) -> Dict[str, Any]:
        """
        健康检查
        
        Returns:
            健康状态信息
        """
        stats = self.get_processing_stats()
        success_rate = (
            stats['successful_processed'] / max(1, stats['total_processed'])
        )
        
        return {
            'status': 'healthy' if success_rate > 0.8 else 'degraded',
            'success_rate': success_rate,
            'temp_dir_exists': os.path.exists(self.temp_dir),
            'processing_stats': stats
        }