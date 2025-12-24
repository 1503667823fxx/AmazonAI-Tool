"""
A+ 智能工作流产品分析服务

该模块实现产品图片上传处理和AI产品分析功能，包括：
- 图片文件验证（格式、大小、数量限制）
- 多图片上传和预处理
- 调用Gemini API进行产品图片分析
- 产品特征提取和分类
- 生成产品分析报告结构
"""

import logging
import uuid
import hashlib
import json
from datetime import datetime
from typing import List, Dict, Optional, Any, Tuple, Union
from dataclasses import dataclass
from PIL import Image, ImageOps
import io
import base64
import streamlit as st
import google.generativeai as genai

from .models import ProductCategory, ValidationStatus
from .intelligent_workflow import ProductAnalysis
from .performance_monitor import (
    PerformanceMonitor, performance_monitor, get_global_performance_monitor
)
from .error_handler import (
    ErrorHandler, error_handler, get_global_error_handler
)

logger = logging.getLogger(__name__)


# 产品图片上传配置常量
UPLOAD_CONFIG = {
    "max_files": 5,
    "max_file_size": 10 * 1024 * 1024,  # 10MB
    "supported_formats": ["JPG", "JPEG", "PNG", "WEBP"],
    "min_dimensions": (200, 200),
    "max_dimensions": (4096, 4096),
    "quality_threshold": 0.7
}


@dataclass
class UploadedProductImage:
    """上传的产品图片信息"""
    file_id: str
    filename: str
    file_size: int
    format: str
    dimensions: Tuple[int, int]
    image_data: bytes
    pil_image: Image.Image
    upload_timestamp: datetime
    validation_status: ValidationStatus = ValidationStatus.PENDING
    validation_issues: List[str] = None
    
    def __post_init__(self):
        if self.validation_issues is None:
            self.validation_issues = []
    
    def get_base64_data(self) -> str:
        """获取base64编码的图片数据"""
        return base64.b64encode(self.image_data).decode('utf-8')
    
    def get_file_hash(self) -> str:
        """获取文件哈希值"""
        return hashlib.md5(self.image_data).hexdigest()


@dataclass
class ImageValidationResult:
    """图片验证结果"""
    is_valid: bool
    issues: List[str]
    warnings: List[str]
    quality_score: float
    
    def add_issue(self, issue: str):
        """添加验证问题"""
        self.issues.append(issue)
        self.is_valid = False
    
    def add_warning(self, warning: str):
        """添加验证警告"""
        self.warnings.append(warning)


@dataclass
class ProductImageSet:
    """产品图片集合"""
    images: List[UploadedProductImage]
    primary_image: Optional[UploadedProductImage] = None
    total_size: int = 0
    upload_session_id: str = ""
    
    def __post_init__(self):
        if not self.upload_session_id:
            self.upload_session_id = str(uuid.uuid4())
        
        self.total_size = sum(img.file_size for img in self.images)
        
        # 自动设置主图片（第一张有效图片）
        if not self.primary_image and self.images:
            valid_images = [img for img in self.images if img.validation_status == ValidationStatus.PASSED]
            if valid_images:
                self.primary_image = valid_images[0]
    
    def get_valid_images(self) -> List[UploadedProductImage]:
        """获取验证通过的图片"""
        return [img for img in self.images if img.validation_status == ValidationStatus.PASSED]
    
    def get_failed_images(self) -> List[UploadedProductImage]:
        """获取验证失败的图片"""
        return [img for img in self.images if img.validation_status == ValidationStatus.FAILED]


class ProductImageProcessor:
    """产品图片处理器"""
    
    def __init__(self):
        self.config = UPLOAD_CONFIG.copy()
        logger.info("Product Image Processor initialized")
    
    def validate_uploaded_file(self, file_data: bytes, filename: str) -> ImageValidationResult:
        """验证上传的文件"""
        result = ImageValidationResult(
            is_valid=True,
            issues=[],
            warnings=[],
            quality_score=1.0
        )
        
        try:
            # 检查文件大小
            if len(file_data) > self.config["max_file_size"]:
                result.add_issue(f"文件大小超过限制 ({len(file_data) / 1024 / 1024:.1f}MB > {self.config['max_file_size'] / 1024 / 1024}MB)")
            
            # 检查文件格式
            try:
                image = Image.open(io.BytesIO(file_data))
                image_format = image.format
                
                if image_format not in self.config["supported_formats"]:
                    result.add_issue(f"不支持的文件格式: {image_format}")
                
                # 检查图片尺寸
                width, height = image.size
                min_w, min_h = self.config["min_dimensions"]
                max_w, max_h = self.config["max_dimensions"]
                
                if width < min_w or height < min_h:
                    result.add_issue(f"图片尺寸过小: {width}x{height} < {min_w}x{min_h}")
                
                if width > max_w or height > max_h:
                    result.add_warning(f"图片尺寸较大: {width}x{height} > {max_w}x{max_h}，建议压缩")
                    result.quality_score *= 0.9
                
                # 检查图片质量
                if self._assess_image_quality(image) < self.config["quality_threshold"]:
                    result.add_warning("图片质量较低，可能影响AI分析效果")
                    result.quality_score *= 0.8
                
                # 检查是否为产品图片
                if not self._is_likely_product_image(image):
                    result.add_warning("图片可能不是产品图片，建议使用清晰的产品照片")
                    result.quality_score *= 0.9
                
            except Exception as e:
                result.add_issue(f"无法解析图片文件: {str(e)}")
            
        except Exception as e:
            result.add_issue(f"文件验证失败: {str(e)}")
            logger.error(f"File validation error: {str(e)}")
        
        return result
    
    def _assess_image_quality(self, image: Image.Image) -> float:
        """评估图片质量"""
        try:
            # 转换为RGB模式
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # 简化的质量评估（基于图片尺寸和文件大小）
            width, height = image.size
            total_pixels = width * height
            
            # 基于分辨率的质量评分
            if total_pixels >= 1000000:  # >= 1MP
                quality_score = 0.9
            elif total_pixels >= 500000:  # >= 0.5MP
                quality_score = 0.8
            elif total_pixels >= 200000:  # >= 0.2MP
                quality_score = 0.7
            else:
                quality_score = 0.6
            
            return quality_score
            
        except Exception as e:
            logger.warning(f"Image quality assessment failed: {str(e)}")
            return 0.7  # 默认质量分数
    
    def _is_likely_product_image(self, image: Image.Image) -> bool:
        """判断是否可能是产品图片"""
        try:
            # 简单的启发式判断
            width, height = image.size
            aspect_ratio = width / height
            
            # 产品图片通常有合理的宽高比
            if 0.5 <= aspect_ratio <= 2.0:
                return True
            
            # 检查图片是否有足够的对比度（简化版本）
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # 简单的对比度检查：采样几个像素点
            pixels = list(image.getdata())
            if len(pixels) > 100:
                sample_pixels = pixels[::len(pixels)//100]  # 采样100个像素
                
                # 计算RGB值的标准差作为对比度指标
                r_values = [p[0] for p in sample_pixels]
                g_values = [p[1] for p in sample_pixels]
                b_values = [p[2] for p in sample_pixels]
                
                # 简单的标准差计算
                def simple_std(values):
                    mean_val = sum(values) / len(values)
                    variance = sum((x - mean_val) ** 2 for x in values) / len(values)
                    return variance ** 0.5
                
                avg_std = (simple_std(r_values) + simple_std(g_values) + simple_std(b_values)) / 3
                
                # 产品图片通常有较好的对比度
                return avg_std > 20
            
            return True  # 默认认为是产品图片
            
        except Exception as e:
            logger.warning(f"Product image detection failed: {str(e)}")
            return True  # 默认认为是产品图片
    
    def process_uploaded_image(self, file_data: bytes, filename: str) -> UploadedProductImage:
        """处理上传的图片"""
        try:
            # 验证文件
            validation_result = self.validate_uploaded_file(file_data, filename)
            
            # 创建PIL图片对象
            image = Image.open(io.BytesIO(file_data))
            
            # 自动旋转图片（基于EXIF信息）
            image = ImageOps.exif_transpose(image)
            
            # 创建上传图片对象
            uploaded_image = UploadedProductImage(
                file_id=str(uuid.uuid4()),
                filename=filename,
                file_size=len(file_data),
                format=image.format,
                dimensions=image.size,
                image_data=file_data,
                pil_image=image,
                upload_timestamp=datetime.now(),
                validation_status=ValidationStatus.PASSED if validation_result.is_valid else ValidationStatus.FAILED,
                validation_issues=validation_result.issues + validation_result.warnings
            )
            
            logger.info(f"Processed uploaded image: {filename} ({uploaded_image.file_id})")
            return uploaded_image
            
        except Exception as e:
            logger.error(f"Failed to process uploaded image {filename}: {str(e)}")
            raise
    
    def create_image_set(self, uploaded_images: List[UploadedProductImage]) -> ProductImageSet:
        """创建产品图片集合"""
        try:
            # 验证图片数量
            if len(uploaded_images) > self.config["max_files"]:
                raise ValueError(f"图片数量超过限制: {len(uploaded_images)} > {self.config['max_files']}")
            
            if len(uploaded_images) == 0:
                raise ValueError("至少需要上传一张产品图片")
            
            # 创建图片集合
            image_set = ProductImageSet(images=uploaded_images)
            
            # 验证总文件大小
            total_size_mb = image_set.total_size / 1024 / 1024
            max_total_size_mb = (self.config["max_file_size"] * self.config["max_files"]) / 1024 / 1024
            
            if image_set.total_size > self.config["max_file_size"] * self.config["max_files"]:
                logger.warning(f"Total file size is large: {total_size_mb:.1f}MB")
            
            # 检查是否有有效图片
            valid_images = image_set.get_valid_images()
            if len(valid_images) == 0:
                raise ValueError("没有有效的产品图片，请检查图片格式和质量")
            
            logger.info(f"Created product image set: {len(uploaded_images)} images, {len(valid_images)} valid")
            return image_set
            
        except Exception as e:
            logger.error(f"Failed to create image set: {str(e)}")
            raise
    
    def optimize_images_for_analysis(self, image_set: ProductImageSet) -> ProductImageSet:
        """优化图片用于AI分析"""
        try:
            optimized_images = []
            
            for img in image_set.get_valid_images():
                try:
                    # 优化图片尺寸（AI分析不需要过大的图片）
                    optimized_image = self._optimize_image_for_ai(img.pil_image)
                    
                    # 转换为字节数据
                    img_buffer = io.BytesIO()
                    optimized_image.save(img_buffer, format='JPEG', quality=85)
                    optimized_data = img_buffer.getvalue()
                    
                    # 创建优化后的图片对象
                    optimized_img = UploadedProductImage(
                        file_id=img.file_id + "_optimized",
                        filename=f"optimized_{img.filename}",
                        file_size=len(optimized_data),
                        format="JPEG",
                        dimensions=optimized_image.size,
                        image_data=optimized_data,
                        pil_image=optimized_image,
                        upload_timestamp=img.upload_timestamp,
                        validation_status=ValidationStatus.PASSED
                    )
                    
                    optimized_images.append(optimized_img)
                    
                except Exception as e:
                    logger.warning(f"Failed to optimize image {img.filename}: {str(e)}")
                    # 如果优化失败，使用原图
                    optimized_images.append(img)
            
            # 创建优化后的图片集合
            optimized_set = ProductImageSet(images=optimized_images)
            
            logger.info(f"Optimized {len(optimized_images)} images for AI analysis")
            return optimized_set
            
        except Exception as e:
            logger.error(f"Image optimization failed: {str(e)}")
            return image_set  # 返回原始图片集合
    
    def _optimize_image_for_ai(self, image: Image.Image, max_size: int = 1024) -> Image.Image:
        """优化单张图片用于AI分析"""
        try:
            # 转换为RGB模式
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # 计算缩放比例
            width, height = image.size
            if max(width, height) > max_size:
                if width > height:
                    new_width = max_size
                    new_height = int(height * max_size / width)
                else:
                    new_height = max_size
                    new_width = int(width * max_size / height)
                
                # 使用高质量重采样
                image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            return image
            
        except Exception as e:
            logger.warning(f"Image optimization failed: {str(e)}")
            return image


class ProductAnalysisService:
    """产品分析服务"""
    
    def __init__(self):
        self.image_processor = ProductImageProcessor()
        self.analysis_timeout = 60  # 60秒超时
        self._gemini_model = None
        
        # 初始化性能监控和错误处理
        self._performance_monitor = get_global_performance_monitor()
        self._error_handler = get_global_error_handler()
        
        # 注册回退处理器
        self._register_fallback_handlers()
        
        logger.info("Product Analysis Service initialized")
    
    def _register_fallback_handlers(self):
        """注册回退处理器"""
        def analysis_fallback(*args, **kwargs):
            logger.info("Using fallback for product analysis")
            return {
                "product_category": ProductCategory.OTHER,
                "product_type": "通用产品",
                "key_features": ["实用功能", "优质设计", "便捷操作"],
                "materials": ["优质材料"],
                "target_audience": "普通用户",
                "use_cases": ["日常使用"],
                "marketing_angles": ["实用便捷", "品质可靠"],
                "confidence_score": 0.5
            }
        
        self._error_handler.register_fallback_handler("analyze_product_images", analysis_fallback)
    
    def _get_gemini_client(self):
        """获取Gemini客户端"""
        if self._gemini_model is None:
            try:
                api_key = st.secrets["GOOGLE_API_KEY"]
                genai.configure(api_key=api_key)
                # 使用Gemini 3.0 Pro Preview模型进行图片分析
                self._gemini_model = genai.GenerativeModel('models/gemini-3-pro-preview')
                logger.info("Gemini client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Gemini client: {str(e)}")
                raise ValueError(f"Gemini API配置错误: {str(e)}")
        
        return self._gemini_model
    
    @performance_monitor("process_uploaded_files", cache_key_params={"files_data": 0}, enable_cache=False)
    @error_handler("process_uploaded_files", max_retries=2, enable_recovery=True)
    def process_uploaded_files(self, files_data: List[Tuple[bytes, str]]) -> ProductImageSet:
        """处理上传的文件列表
        
        Args:
            files_data: 文件数据列表，每个元素为(文件字节数据, 文件名)元组
            
        Returns:
            ProductImageSet: 处理后的产品图片集合
            
        Raises:
            ValueError: 文件验证失败或数量超限
            Exception: 处理过程中的其他错误
        """
        try:
            logger.info(f"Processing {len(files_data)} uploaded files")
            
            # 验证文件数量
            if len(files_data) > UPLOAD_CONFIG["max_files"]:
                raise ValueError(f"上传文件数量超过限制: {len(files_data)} > {UPLOAD_CONFIG['max_files']}")
            
            if len(files_data) == 0:
                raise ValueError("请至少上传一张产品图片")
            
            uploaded_images = []
            processing_errors = []
            
            # 处理每个文件
            for file_data, filename in files_data:
                try:
                    uploaded_image = self.image_processor.process_uploaded_image(file_data, filename)
                    uploaded_images.append(uploaded_image)
                    
                except Exception as e:
                    error_msg = f"处理文件 {filename} 失败: {str(e)}"
                    processing_errors.append(error_msg)
                    logger.error(error_msg)
            
            # 检查是否有成功处理的图片
            if len(uploaded_images) == 0:
                raise ValueError(f"所有文件处理失败: {'; '.join(processing_errors)}")
            
            # 创建图片集合
            image_set = self.image_processor.create_image_set(uploaded_images)
            
            # 优化图片用于AI分析
            optimized_set = self.image_processor.optimize_images_for_analysis(image_set)
            
            logger.info(f"Successfully processed {len(uploaded_images)} images, {len(optimized_set.get_valid_images())} valid")
            
            # 如果有处理错误，记录警告
            if processing_errors:
                logger.warning(f"Some files failed to process: {processing_errors}")
            
            return optimized_set
            
        except Exception as e:
            logger.error(f"Failed to process uploaded files: {str(e)}")
            raise
    
    @performance_monitor("analyze_product_images", cache_key_params={"image_set": 0, "language": 1}, cache_ttl=3600)
    @error_handler("analyze_product_images", max_retries=3, enable_recovery=True)
    def analyze_product_images(self, image_set: ProductImageSet, language: str = "zh") -> ProductAnalysis:
        """分析产品图片
        
        Args:
            image_set: 产品图片集合
            language: 分析语言 (zh, en)
            
        Returns:
            ProductAnalysis: 产品分析结果
            
        Raises:
            ValueError: 输入参数无效
            TimeoutError: 分析超时
            Exception: AI分析失败
        """
        try:
            logger.info(f"Starting product image analysis for {len(image_set.get_valid_images())} images")
            
            # 验证输入
            valid_images = image_set.get_valid_images()
            if len(valid_images) == 0:
                raise ValueError("没有有效的产品图片可供分析")
            
            # 生成产品ID
            product_id = f"product_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{image_set.upload_session_id[:8]}"
            
            # 调用AI分析（这里先返回模拟结果，后续会集成真实的Gemini API）
            analysis_result = self._analyze_with_ai(valid_images, language)
            
            # 创建产品分析对象
            product_analysis = ProductAnalysis(
                product_id=product_id,
                product_category=analysis_result["product_category"],
                product_type=analysis_result["product_type"],
                key_features=analysis_result["key_features"],
                materials=analysis_result["materials"],
                target_audience=analysis_result["target_audience"],
                use_cases=analysis_result["use_cases"],
                marketing_angles=analysis_result["marketing_angles"],
                confidence_score=analysis_result["confidence_score"]
            )
            
            logger.info(f"Product analysis completed: {product_analysis.product_type} ({product_analysis.confidence_score:.2f})")
            return product_analysis
            
        except Exception as e:
            logger.error(f"Product image analysis failed: {str(e)}")
            raise
    
    def _analyze_with_ai(self, images: List[UploadedProductImage], language: str) -> Dict[str, Any]:
        """使用Gemini AI分析产品图片"""
        try:
            logger.info(f"Starting Gemini AI analysis for {len(images)} images")
            
            # 获取Gemini客户端
            model = self._get_gemini_client()
            
            # 构建分析提示词
            analysis_prompt = self._build_analysis_prompt(language)
            
            # 准备图片数据
            image_inputs = []
            for img in images[:3]:  # 最多分析3张图片以控制API成本
                image_inputs.append(img.pil_image)
            
            # 构建完整的输入
            content_parts = [analysis_prompt] + image_inputs
            
            # 调用Gemini API
            response = model.generate_content(
                content_parts,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.3,  # 较低的温度以获得更一致的分析结果
                    max_output_tokens=2048,
                )
            )
            
            if not response.text:
                raise Exception("Gemini API返回空响应")
            
            # 解析AI响应
            analysis_result = self._parse_ai_response(response.text, language)
            
            logger.info(f"Gemini analysis completed: {analysis_result['product_type']} (confidence: {analysis_result['confidence_score']:.2f})")
            return analysis_result
            
        except Exception as e:
            logger.error(f"Gemini AI analysis failed: {str(e)}")
            # 回退到模拟分析
            logger.info("Falling back to simulated analysis")
            return self._simulate_analysis(images, language)
    
    def _build_analysis_prompt(self, language: str) -> str:
        """构建产品分析提示词"""
        if language == "zh":
            prompt = """请分析这些产品图片，并提供详细的产品分析报告。请以JSON格式返回分析结果，包含以下字段：

{
  "product_category": "产品类别 (technology/home_living/fashion/sports/health_beauty/automotive/tools/other)",
  "product_type": "具体产品类型 (如：智能手机、笔记本电脑、家用电器等)",
  "key_features": ["关键特征1", "关键特征2", "关键特征3", "关键特征4", "关键特征5"],
  "materials": ["材料1", "材料2", "材料3"],
  "target_audience": "目标用户群体描述",
  "use_cases": ["使用场景1", "使用场景2", "使用场景3"],
  "marketing_angles": ["营销角度1", "营销角度2", "营销角度3"],
  "confidence_score": 0.85
}

分析要求：
1. 仔细观察产品的外观、设计、材质和功能特征
2. 根据产品特征判断最合适的类别
3. 提取3-5个最重要的产品特征
4. 识别产品使用的主要材料
5. 分析目标用户群体和使用场景
6. 提供有效的营销角度建议
7. 给出分析置信度评分(0-1)

请确保返回有效的JSON格式，不要包含其他解释文字。"""
        else:
            prompt = """Please analyze these product images and provide a detailed product analysis report. Return the analysis in JSON format with the following fields:

{
  "product_category": "Product category (technology/home_living/fashion/sports/health_beauty/automotive/tools/other)",
  "product_type": "Specific product type (e.g., smartphone, laptop, home appliance, etc.)",
  "key_features": ["Key feature 1", "Key feature 2", "Key feature 3", "Key feature 4", "Key feature 5"],
  "materials": ["Material 1", "Material 2", "Material 3"],
  "target_audience": "Target audience description",
  "use_cases": ["Use case 1", "Use case 2", "Use case 3"],
  "marketing_angles": ["Marketing angle 1", "Marketing angle 2", "Marketing angle 3"],
  "confidence_score": 0.85
}

Analysis requirements:
1. Carefully observe the product's appearance, design, materials, and functional features
2. Determine the most appropriate category based on product characteristics
3. Extract 3-5 most important product features
4. Identify the main materials used in the product
5. Analyze target audience and use scenarios
6. Provide effective marketing angle suggestions
7. Give analysis confidence score (0-1)

Please ensure valid JSON format is returned without additional explanatory text."""
        
        return prompt
    
    def _parse_ai_response(self, response_text: str, language: str) -> Dict[str, Any]:
        """解析AI响应"""
        try:
            # 尝试直接解析JSON
            response_text = response_text.strip()
            
            # 移除可能的markdown代码块标记
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            
            response_text = response_text.strip()
            
            # 解析JSON
            parsed_data = json.loads(response_text)
            
            # 验证和转换数据
            result = {
                "product_category": self._parse_product_category(parsed_data.get("product_category", "other")),
                "product_type": parsed_data.get("product_type", "未知产品"),
                "key_features": parsed_data.get("key_features", [])[:5],  # 最多5个特征
                "materials": parsed_data.get("materials", [])[:5],  # 最多5种材料
                "target_audience": parsed_data.get("target_audience", "普通用户"),
                "use_cases": parsed_data.get("use_cases", [])[:5],  # 最多5个使用场景
                "marketing_angles": parsed_data.get("marketing_angles", [])[:5],  # 最多5个营销角度
                "confidence_score": min(max(float(parsed_data.get("confidence_score", 0.7)), 0.0), 1.0)
            }
            
            # 确保所有列表字段都有内容
            if not result["key_features"]:
                result["key_features"] = ["实用功能", "优质设计"]
            if not result["materials"]:
                result["materials"] = ["优质材料"]
            if not result["use_cases"]:
                result["use_cases"] = ["日常使用"]
            if not result["marketing_angles"]:
                result["marketing_angles"] = ["实用便捷", "品质可靠"]
            
            return result
            
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse AI response as JSON: {str(e)}")
            # 尝试从文本中提取信息
            return self._extract_from_text_response(response_text, language)
        except Exception as e:
            logger.error(f"Error parsing AI response: {str(e)}")
            # 返回默认结果
            return self._get_default_analysis_result(language)
    
    def _parse_product_category(self, category_str: str) -> ProductCategory:
        """解析产品类别字符串"""
        category_mapping = {
            "technology": ProductCategory.TECHNOLOGY,
            "home_living": ProductCategory.HOME_LIVING,
            "fashion": ProductCategory.FASHION,
            "sports": ProductCategory.SPORTS,
            "health_beauty": ProductCategory.HEALTH_BEAUTY,
            "automotive": ProductCategory.AUTOMOTIVE,
            "tools": ProductCategory.TOOLS,
            "other": ProductCategory.OTHER
        }
        
        category_str = category_str.lower().strip()
        return category_mapping.get(category_str, ProductCategory.OTHER)
    
    def _extract_from_text_response(self, response_text: str, language: str) -> Dict[str, Any]:
        """从文本响应中提取产品信息"""
        try:
            # 简单的文本解析逻辑
            result = self._get_default_analysis_result(language)
            
            # 尝试从文本中提取产品类型
            text_lower = response_text.lower()
            
            # 检测产品类别
            if any(word in text_lower for word in ["phone", "smartphone", "computer", "laptop", "tech"]):
                result["product_category"] = ProductCategory.TECHNOLOGY
                result["product_type"] = "电子产品"
            elif any(word in text_lower for word in ["home", "kitchen", "furniture", "appliance"]):
                result["product_category"] = ProductCategory.HOME_LIVING
                result["product_type"] = "家居用品"
            elif any(word in text_lower for word in ["fashion", "clothing", "apparel", "wear"]):
                result["product_category"] = ProductCategory.FASHION
                result["product_type"] = "时尚用品"
            
            # 降低置信度
            result["confidence_score"] = 0.6
            
            return result
            
        except Exception as e:
            logger.error(f"Text extraction failed: {str(e)}")
            return self._get_default_analysis_result(language)
    
    def _get_default_analysis_result(self, language: str) -> Dict[str, Any]:
        """获取默认分析结果"""
        if language == "zh":
            return {
                "product_category": ProductCategory.OTHER,
                "product_type": "电子产品",
                "key_features": ["实用功能", "优质设计", "便捷操作"],
                "materials": ["优质材料", "精工制造"],
                "target_audience": "普通用户",
                "use_cases": ["日常使用", "便民生活"],
                "marketing_angles": ["实用便捷", "品质可靠", "性价比高"],
                "confidence_score": 0.5
            }
        else:
            return {
                "product_category": ProductCategory.OTHER,
                "product_type": "Electronic Product",
                "key_features": ["Practical Function", "Quality Design", "Easy Operation"],
                "materials": ["Quality Materials", "Fine Manufacturing"],
                "target_audience": "General Users",
                "use_cases": ["Daily Use", "Convenient Life"],
                "marketing_angles": ["Practical Convenience", "Reliable Quality", "Great Value"],
                "confidence_score": 0.5
            }
    
    def _simulate_analysis(self, images: List[UploadedProductImage], language: str) -> Dict[str, Any]:
        """模拟AI分析（备用方案）"""
        try:
            logger.info("Using simulated analysis as fallback")
            
            # 基于图片特征进行简单分析
            primary_image = images[0]
            width, height = primary_image.dimensions
            
            # 简单的产品类型推断
            filename_lower = primary_image.filename.lower()
            
            if any(word in filename_lower for word in ["phone", "mobile", "smartphone"]):
                product_category = ProductCategory.TECHNOLOGY
                product_type = "智能手机" if language == "zh" else "Smartphone"
                key_features = ["高性能处理器", "大容量电池", "高清摄像头"] if language == "zh" else ["High Performance Processor", "Large Battery", "HD Camera"]
                materials = ["金属", "玻璃"] if language == "zh" else ["Metal", "Glass"]
                target_audience = "科技爱好者" if language == "zh" else "Tech Enthusiasts"
                use_cases = ["日常通讯", "娱乐", "办公"] if language == "zh" else ["Daily Communication", "Entertainment", "Office Work"]
                marketing_angles = ["性能强劲", "拍照清晰", "续航持久"] if language == "zh" else ["Powerful Performance", "Clear Photography", "Long Battery Life"]
            elif any(word in filename_lower for word in ["laptop", "computer", "pc"]):
                product_category = ProductCategory.TECHNOLOGY
                product_type = "笔记本电脑" if language == "zh" else "Laptop Computer"
                key_features = ["高性能CPU", "大内存", "轻薄设计"] if language == "zh" else ["High Performance CPU", "Large Memory", "Slim Design"]
                materials = ["铝合金", "塑料"] if language == "zh" else ["Aluminum Alloy", "Plastic"]
                target_audience = "专业人士" if language == "zh" else "Professionals"
                use_cases = ["办公", "编程", "设计"] if language == "zh" else ["Office Work", "Programming", "Design"]
                marketing_angles = ["高效办公", "便携轻薄", "性能卓越"] if language == "zh" else ["Efficient Office", "Portable Slim", "Excellent Performance"]
            else:
                # 默认分析结果
                product_category = ProductCategory.OTHER
                product_type = "电子产品" if language == "zh" else "Electronic Product"
                key_features = ["实用功能", "优质材料", "精美设计"] if language == "zh" else ["Practical Function", "Quality Materials", "Beautiful Design"]
                materials = ["塑料", "金属"] if language == "zh" else ["Plastic", "Metal"]
                target_audience = "普通用户" if language == "zh" else "General Users"
                use_cases = ["日常使用", "便民生活"] if language == "zh" else ["Daily Use", "Convenient Life"]
                marketing_angles = ["实用便捷", "品质可靠", "性价比高"] if language == "zh" else ["Practical Convenience", "Reliable Quality", "Great Value"]
            
            # 基于图片数量和质量调整置信度
            confidence_score = 0.7
            if len(images) >= 3:
                confidence_score += 0.1
            if all(img.file_size > 500 * 1024 for img in images):  # 大于500KB
                confidence_score += 0.05
            
            confidence_score = min(confidence_score, 0.85)
            
            return {
                "product_category": product_category,
                "product_type": product_type,
                "key_features": key_features,
                "materials": materials,
                "target_audience": target_audience,
                "use_cases": use_cases,
                "marketing_angles": marketing_angles,
                "confidence_score": confidence_score
            }
            
        except Exception as e:
            logger.error(f"Simulated analysis failed: {str(e)}")
            return self._get_default_analysis_result(language)
    
    def extract_product_features(self, analysis: ProductAnalysis) -> Dict[str, Any]:
        """提取产品特征用于后续推荐"""
        try:
            features = {
                "category": analysis.product_category,
                "type": analysis.product_type,
                "complexity": self._assess_product_complexity(analysis),
                "target_market": self._determine_target_market(analysis),
                "key_selling_points": analysis.key_features[:3],  # 取前3个关键特征
                "material_focus": len(analysis.materials) > 2,  # 是否需要强调材质
                "technical_focus": self._has_technical_focus(analysis),
                "lifestyle_focus": self._has_lifestyle_focus(analysis)
            }
            
            logger.info(f"Extracted product features: {features['type']} - {features['complexity']} complexity")
            return features
            
        except Exception as e:
            logger.error(f"Feature extraction failed: {str(e)}")
            return {
                "category": ProductCategory.OTHER,
                "type": "未知产品",
                "complexity": "medium",
                "target_market": "general",
                "key_selling_points": [],
                "material_focus": False,
                "technical_focus": False,
                "lifestyle_focus": False
            }
    
    def _assess_product_complexity(self, analysis: ProductAnalysis) -> str:
        """评估产品复杂度"""
        complexity_indicators = 0
        
        # 技术特征数量
        if len(analysis.key_features) > 5:
            complexity_indicators += 1
        
        # 材料种类
        if len(analysis.materials) > 3:
            complexity_indicators += 1
        
        # 使用场景多样性
        if len(analysis.use_cases) > 3:
            complexity_indicators += 1
        
        # 技术类产品通常更复杂
        if analysis.product_category in [ProductCategory.TECHNOLOGY, ProductCategory.AUTOMOTIVE]:
            complexity_indicators += 1
        
        if complexity_indicators >= 3:
            return "high"
        elif complexity_indicators >= 1:
            return "medium"
        else:
            return "low"
    
    def _determine_target_market(self, analysis: ProductAnalysis) -> str:
        """确定目标市场"""
        audience = analysis.target_audience.lower()
        
        if "专业" in audience or "技术" in audience:
            return "professional"
        elif "高端" in audience or "奢华" in audience:
            return "premium"
        elif "家庭" in audience or "日常" in audience:
            return "consumer"
        else:
            return "general"
    
    def _has_technical_focus(self, analysis: ProductAnalysis) -> bool:
        """判断是否有技术重点"""
        technical_keywords = ["性能", "技术", "规格", "参数", "配置", "处理器", "内存", "功率"]
        
        all_text = " ".join(analysis.key_features + analysis.marketing_angles)
        return any(keyword in all_text for keyword in technical_keywords)
    
    def _has_lifestyle_focus(self, analysis: ProductAnalysis) -> bool:
        """判断是否有生活方式重点"""
        lifestyle_keywords = ["生活", "家居", "舒适", "便捷", "时尚", "美观", "体验"]
        
        all_text = " ".join(analysis.key_features + analysis.marketing_angles + analysis.use_cases)
        return any(keyword in all_text for keyword in lifestyle_keywords)
    
    def generate_analysis_summary(self, analysis: ProductAnalysis) -> Dict[str, Any]:
        """生成分析摘要"""
        try:
            summary = {
                "product_info": {
                    "id": analysis.product_id,
                    "type": analysis.product_type,
                    "category": analysis.product_category.value
                },
                "key_insights": {
                    "primary_features": analysis.key_features[:3],
                    "target_audience": analysis.target_audience,
                    "main_use_cases": analysis.use_cases[:3]
                },
                "marketing_recommendations": {
                    "key_angles": analysis.marketing_angles[:3],
                    "material_emphasis": len(analysis.materials) > 2,
                    "technical_focus": self._has_technical_focus(analysis)
                },
                "analysis_metadata": {
                    "confidence_score": analysis.confidence_score,
                    "analysis_timestamp": analysis.analysis_timestamp.isoformat(),
                    "quality_assessment": "high" if analysis.confidence_score > 0.8 else "medium" if analysis.confidence_score > 0.6 else "low"
                }
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"Failed to generate analysis summary: {str(e)}")
            return {
                "error": str(e),
                "product_info": {"id": analysis.product_id if analysis else "unknown"}
            }