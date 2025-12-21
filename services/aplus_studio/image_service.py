"""
A+ Image Generation Service.

This service handles the generation of A+ compliant images using Gemini models,
inheriting from existing vision services and adding A+ specific functionality.
"""

import asyncio
import time
from typing import List, Optional, Dict, Any, Tuple
from PIL import Image
import io
import streamlit as st

# Import the base StudioVisionService
from services.ai_studio.vision_service import StudioVisionService, ImageGenerationResult

from .models import (
    ModulePrompt, GenerationResult, ModuleType, ValidationStatus,
    APLUS_IMAGE_SPECS, ValidationResult
)
from .config import aplus_config, APLUS_GENERATION_CONFIG


class APlusImageService(StudioVisionService):
    """A+图片生成服务 - 继承现有视觉服务，专门处理A+图片生成"""
    
    def __init__(self, api_key: Optional[str] = None):
        # Initialize parent StudioVisionService
        super().__init__(api_key)
        
        # A+ specific configuration
        self.config = aplus_config
        self.generation_config = APLUS_GENERATION_CONFIG
        
        # A+ specific settings
        self.aplus_aspect_ratio = "4:3 aspect ratio, 600x450 pixels"
        self.aplus_quality_requirements = [
            "High resolution suitable for Amazon A+ pages",
            "Professional e-commerce quality",
            "Clear product visibility",
            "Optimized for online retail display"
        ]
    
    async def generate_aplus_image(
        self, 
        prompt: ModulePrompt, 
        reference_images: Optional[List[Image.Image]] = None
    ) -> GenerationResult:
        """生成A+规范的图片"""
        if not self.api_key:
            raise ValueError("API key not configured for A+ image generation")
        
        try:
            # 构建A+专用的完整提示词
            full_prompt = self._build_aplus_generation_prompt(prompt)
            
            # 使用父类的图片生成功能，添加A+特定的宽高比提示
            result = self.generate_image_with_progress(
                prompt=full_prompt,
                model_name=self.config.gemini_config.image_model if self.config.is_configured else "gemini-1.5-pro-vision-latest",
                ref_images=reference_images,
                aspect_ratio_prompt=self.aplus_aspect_ratio,
                progress_callback=None
            )
            
            # 转换为A+特定的GenerationResult格式
            aplus_result = GenerationResult(
                module_type=prompt.module_type,
                image_data=result.image_data,
                image_path=None,
                prompt_used=full_prompt,
                generation_time=result.generation_time or 0.0,
                quality_score=0.8 if result.success else 0.0,
                validation_status=ValidationStatus.PENDING,
                metadata={
                    "dimensions": APLUS_IMAGE_SPECS["dimensions"],
                    "format": "PNG",
                    "model_used": result.model_used,
                    "reference_indicator": result.reference_indicator,
                    "success": result.success,
                    "error": result.error
                }
            )
            
            # 如果生成成功，进行A+规范验证
            if result.success and result.image_data:
                validation_result = self.validate_aplus_requirements(result.image_data)
                aplus_result.validation_status = (
                    ValidationStatus.PASSED if validation_result["is_valid"] 
                    else ValidationStatus.NEEDS_REVIEW
                )
                aplus_result.metadata.update(validation_result)
            else:
                aplus_result.validation_status = ValidationStatus.FAILED
            
            return aplus_result
            
        except Exception as e:
            return GenerationResult(
                module_type=prompt.module_type,
                image_data=None,
                image_path=None,
                prompt_used=prompt.base_prompt,
                generation_time=0.0,
                quality_score=0.0,
                validation_status=ValidationStatus.FAILED,
                metadata={"error": str(e)}
            )
    
    def _build_aplus_generation_prompt(self, prompt: ModulePrompt) -> str:
        """构建A+专用的完整图片生成提示词"""
        full_prompt = f"""
Create a professional Amazon A+ page image with the following specifications:

{prompt.base_prompt}

TECHNICAL REQUIREMENTS:
- Dimensions: {prompt.aspect_ratio} ({APLUS_IMAGE_SPECS['dimensions'][0]}x{APLUS_IMAGE_SPECS['dimensions'][1]} pixels)
- Format: High-quality PNG suitable for e-commerce
- Color space: {APLUS_IMAGE_SPECS['color_space']}
- Resolution: Minimum {APLUS_IMAGE_SPECS['min_resolution']} DPI
- File size: Under {APLUS_IMAGE_SPECS['max_file_size'] // (1024*1024)}MB

STYLE MODIFIERS:
{', '.join(prompt.style_modifiers)}

TECHNICAL SPECIFICATIONS:
{', '.join(prompt.technical_requirements)}

QUALITY STANDARDS:
{', '.join(self.aplus_quality_requirements)}

AMAZON A+ COMPLIANCE:
- Professional e-commerce presentation
- Clear product visibility and appeal
- Suitable for online retail environment
- Optimized for customer conversion
- Clean, uncluttered composition
- High visual impact for product marketing
        """
        
        return full_prompt.strip()
    
    def validate_aplus_requirements(self, image_data: bytes) -> ValidationResult:
        """验证图片是否符合A+规范 - 返回ValidationResult对象"""
        try:
            # 加载图片进行验证
            image = Image.open(io.BytesIO(image_data))
            
            issues = []
            suggestions = []
            quality_metrics = {}
            
            # 检查尺寸
            expected_size = APLUS_IMAGE_SPECS["dimensions"]
            actual_size = image.size
            quality_metrics["dimensions"] = actual_size
            quality_metrics["expected_dimensions"] = expected_size
            
            if actual_size != expected_size:
                issues.append(
                    f"Image size {actual_size} does not match required {expected_size}"
                )
                suggestions.append(
                    f"Resize image to exactly {expected_size[0]}x{expected_size[1]} pixels"
                )
            
            # 检查文件大小
            file_size = len(image_data)
            max_size = APLUS_IMAGE_SPECS["max_file_size"]
            quality_metrics["file_size_bytes"] = file_size
            quality_metrics["file_size_mb"] = file_size / (1024 * 1024)
            
            if file_size > max_size:
                issues.append(
                    f"File size {file_size / (1024*1024):.1f}MB exceeds maximum {max_size / (1024*1024):.1f}MB"
                )
                suggestions.append("Compress image or reduce quality to meet size requirements")
            
            # 检查格式
            image_format = image.format
            quality_metrics["format"] = image_format
            
            if image_format not in APLUS_IMAGE_SPECS["supported_formats"]:
                issues.append(
                    f"Format {image_format} not in supported formats {APLUS_IMAGE_SPECS['supported_formats']}"
                )
                suggestions.append(f"Convert to one of: {', '.join(APLUS_IMAGE_SPECS['supported_formats'])}")
            
            # 检查色彩模式
            color_mode = image.mode
            quality_metrics["color_mode"] = color_mode
            
            if color_mode not in ['RGB', 'RGBA']:
                issues.append(f"Color mode {color_mode} may not be optimal for web display")
                suggestions.append("Convert to RGB color mode for best compatibility")
            
            # 计算宽高比
            aspect_ratio = actual_size[0] / actual_size[1] if actual_size[1] > 0 else 1.0
            expected_ratio = expected_size[0] / expected_size[1]
            quality_metrics["aspect_ratio"] = aspect_ratio
            quality_metrics["expected_aspect_ratio"] = expected_ratio
            
            if abs(aspect_ratio - expected_ratio) > 0.01:  # Allow small tolerance
                issues.append(f"Aspect ratio {aspect_ratio:.3f} differs from expected {expected_ratio:.3f}")
                suggestions.append("Adjust image composition to match 4:3 aspect ratio")
            
            # 整体质量评分
            quality_score = 1.0
            if issues:
                quality_score = max(0.0, 1.0 - (len(issues) * 0.2))  # Reduce score for each issue
            
            quality_metrics["overall_quality_score"] = quality_score
            
            # 确定验证状态
            is_valid = len(issues) == 0
            validation_status = ValidationStatus.PASSED if is_valid else ValidationStatus.NEEDS_REVIEW
            
            return ValidationResult(
                is_valid=is_valid,
                validation_status=validation_status,
                issues=issues,
                suggestions=suggestions,
                quality_metrics=quality_metrics
            )
            
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                validation_status=ValidationStatus.FAILED,
                issues=[f"Validation error: {str(e)}"],
                suggestions=["Please check image format and integrity"],
                quality_metrics={"error": str(e)}
            )
    
    def optimize_for_amazon(self, image_data: bytes) -> bytes:
        """为Amazon平台优化图片 - 自动质量评估和优化处理"""
        try:
            image = Image.open(io.BytesIO(image_data))
            
            # 确保正确的尺寸 (4:3 aspect ratio, 600x450)
            target_size = APLUS_IMAGE_SPECS["dimensions"]
            if image.size != target_size:
                # 使用高质量重采样算法调整尺寸
                image = image.resize(target_size, Image.Resampling.LANCZOS)
            
            # 确保正确的色彩模式
            if image.mode == 'RGBA':
                # 处理透明背景，转换为白色背景
                background = Image.new('RGB', image.size, (255, 255, 255))
                background.paste(image, mask=image.split()[-1])  # Use alpha channel as mask
                image = background
            elif image.mode != 'RGB':
                image = image.convert('RGB')
            
            # 应用Amazon A+优化
            image = self._apply_amazon_optimizations(image)
            
            # 智能压缩 - 在质量和文件大小之间找到平衡
            optimized_data = self._smart_compression(image)
            
            return optimized_data
            
        except Exception as e:
            raise Exception(f"Amazon optimization failed: {str(e)}")
    
    def _apply_amazon_optimizations(self, image: Image.Image) -> Image.Image:
        """应用Amazon A+特定的图片优化"""
        try:
            # 增强对比度和清晰度以适应在线展示
            from PIL import ImageEnhance
            
            # 轻微增强对比度 (1.0 = 原始, >1.0 = 增强)
            contrast_enhancer = ImageEnhance.Contrast(image)
            image = contrast_enhancer.enhance(1.1)
            
            # 轻微增强清晰度
            sharpness_enhancer = ImageEnhance.Sharpness(image)
            image = sharpness_enhancer.enhance(1.05)
            
            # 确保色彩饱和度适中 (避免过度饱和)
            color_enhancer = ImageEnhance.Color(image)
            image = color_enhancer.enhance(1.02)
            
            return image
            
        except Exception as e:
            # 如果优化失败，返回原图
            st.warning(f"Image enhancement failed, using original: {str(e)}")
            return image
    
    def _smart_compression(self, image: Image.Image) -> bytes:
        """智能压缩 - 在质量和文件大小之间找到最佳平衡"""
        max_file_size = APLUS_IMAGE_SPECS["max_file_size"]
        
        # 尝试不同的质量设置，从高到低
        quality_levels = [95, 90, 85, 80, 75, 70]
        
        for quality in quality_levels:
            output = io.BytesIO()
            
            # 对于PNG格式，使用optimize参数
            if quality >= 90:
                image.save(output, format='PNG', optimize=True)
            else:
                # 对于较低质量要求，转换为JPEG以获得更小文件
                image.save(output, format='JPEG', quality=quality, optimize=True)
            
            compressed_data = output.getvalue()
            
            # 如果文件大小符合要求，返回结果
            if len(compressed_data) <= max_file_size:
                return compressed_data
        
        # 如果所有质量级别都无法满足大小要求，返回最低质量版本
        output = io.BytesIO()
        image.save(output, format='JPEG', quality=60, optimize=True)
        return output.getvalue()
    
    def assess_image_quality(self, image_data: bytes) -> Dict[str, Any]:
        """自动质量评估算法"""
        try:
            image = Image.open(io.BytesIO(image_data))
            
            quality_assessment = {
                "overall_score": 0.0,
                "dimension_score": 0.0,
                "file_size_score": 0.0,
                "format_score": 0.0,
                "visual_quality_score": 0.0,
                "amazon_compliance_score": 0.0,
                "recommendations": []
            }
            
            # 1. 尺寸评估
            expected_size = APLUS_IMAGE_SPECS["dimensions"]
            actual_size = image.size
            
            if actual_size == expected_size:
                quality_assessment["dimension_score"] = 1.0
            else:
                # 计算尺寸偏差
                size_deviation = abs(actual_size[0] - expected_size[0]) + abs(actual_size[1] - expected_size[1])
                quality_assessment["dimension_score"] = max(0.0, 1.0 - (size_deviation / 1000))
                quality_assessment["recommendations"].append(f"Resize to {expected_size[0]}x{expected_size[1]} pixels")
            
            # 2. 文件大小评估
            file_size = len(image_data)
            max_size = APLUS_IMAGE_SPECS["max_file_size"]
            
            if file_size <= max_size:
                # 理想文件大小范围：1-3MB
                ideal_min = 1 * 1024 * 1024  # 1MB
                ideal_max = 3 * 1024 * 1024  # 3MB
                
                if ideal_min <= file_size <= ideal_max:
                    quality_assessment["file_size_score"] = 1.0
                elif file_size < ideal_min:
                    quality_assessment["file_size_score"] = 0.8  # 可能质量不够高
                    quality_assessment["recommendations"].append("Consider higher quality for better visual impact")
                else:
                    quality_assessment["file_size_score"] = 0.9  # 文件较大但可接受
            else:
                quality_assessment["file_size_score"] = 0.0
                quality_assessment["recommendations"].append("Reduce file size to under 5MB")
            
            # 3. 格式评估
            image_format = image.format
            if image_format in APLUS_IMAGE_SPECS["supported_formats"]:
                if image_format == 'PNG':
                    quality_assessment["format_score"] = 1.0  # PNG最佳
                elif image_format in ['JPG', 'JPEG']:
                    quality_assessment["format_score"] = 0.9  # JPEG良好
                else:
                    quality_assessment["format_score"] = 0.7
            else:
                quality_assessment["format_score"] = 0.0
                quality_assessment["recommendations"].append(f"Convert to supported format: {', '.join(APLUS_IMAGE_SPECS['supported_formats'])}")
            
            # 4. 视觉质量评估 (基于基本图像属性)
            visual_score = self._assess_visual_quality(image)
            quality_assessment["visual_quality_score"] = visual_score
            
            # 5. Amazon合规性评估
            compliance_score = self._assess_amazon_compliance(image, image_data)
            quality_assessment["amazon_compliance_score"] = compliance_score
            
            # 计算总体评分
            weights = {
                "dimension_score": 0.25,
                "file_size_score": 0.15,
                "format_score": 0.15,
                "visual_quality_score": 0.25,
                "amazon_compliance_score": 0.20
            }
            
            overall_score = sum(
                quality_assessment[key] * weight 
                for key, weight in weights.items()
            )
            quality_assessment["overall_score"] = overall_score
            
            # 添加总体建议
            if overall_score >= 0.9:
                quality_assessment["recommendations"].insert(0, "Excellent quality - ready for Amazon A+")
            elif overall_score >= 0.7:
                quality_assessment["recommendations"].insert(0, "Good quality - minor optimizations recommended")
            elif overall_score >= 0.5:
                quality_assessment["recommendations"].insert(0, "Acceptable quality - several improvements needed")
            else:
                quality_assessment["recommendations"].insert(0, "Poor quality - significant improvements required")
            
            return quality_assessment
            
        except Exception as e:
            return {
                "overall_score": 0.0,
                "error": str(e),
                "recommendations": ["Unable to assess image quality - please check image format"]
            }
    
    def _assess_visual_quality(self, image: Image.Image) -> float:
        """评估图像的视觉质量"""
        try:
            import numpy as np
            
            # 转换为numpy数组进行分析
            img_array = np.array(image)
            
            # 1. 检查图像是否过暗或过亮
            brightness = np.mean(img_array)
            brightness_score = 1.0 - abs(brightness - 128) / 128  # 理想亮度在中等范围
            
            # 2. 检查对比度
            contrast = np.std(img_array)
            contrast_score = min(1.0, contrast / 50)  # 标准化对比度评分
            
            # 3. 检查色彩分布
            if len(img_array.shape) == 3:  # 彩色图像
                color_variance = np.var(img_array, axis=(0, 1))
                color_score = min(1.0, np.mean(color_variance) / 1000)
            else:
                color_score = 0.5  # 灰度图像
            
            # 综合视觉质量评分
            visual_score = (brightness_score * 0.3 + contrast_score * 0.4 + color_score * 0.3)
            return min(1.0, max(0.0, visual_score))
            
        except Exception:
            # 如果numpy不可用或分析失败，返回中等评分
            return 0.7
    
    def _assess_amazon_compliance(self, image: Image.Image, image_data: bytes) -> float:
        """评估Amazon A+合规性"""
        compliance_score = 1.0
        
        # 检查宽高比
        width, height = image.size
        expected_ratio = APLUS_IMAGE_SPECS["dimensions"][0] / APLUS_IMAGE_SPECS["dimensions"][1]
        actual_ratio = width / height if height > 0 else 1.0
        
        if abs(actual_ratio - expected_ratio) > 0.05:  # 5%容差
            compliance_score -= 0.3
        
        # 检查分辨率
        if width < APLUS_IMAGE_SPECS["dimensions"][0] or height < APLUS_IMAGE_SPECS["dimensions"][1]:
            compliance_score -= 0.2
        
        # 检查文件大小
        if len(image_data) > APLUS_IMAGE_SPECS["max_file_size"]:
            compliance_score -= 0.3
        
        # 检查色彩模式
        if image.mode not in ['RGB', 'RGBA']:
            compliance_score -= 0.2
        
        return max(0.0, compliance_score)
    
    def create_module_preview(self, image_data: bytes, preview_size: Tuple[int, int] = (300, 225)) -> bytes:
        """创建模块预览图 - 保持4:3比例的优化预览"""
        try:
            image = Image.open(io.BytesIO(image_data))
            
            # 确保预览尺寸保持4:3比例
            if preview_size[0] / preview_size[1] != 4/3:
                # 调整预览尺寸以保持4:3比例
                if preview_size[0] / preview_size[1] > 4/3:
                    # 宽度过大，调整宽度
                    preview_size = (int(preview_size[1] * 4/3), preview_size[1])
                else:
                    # 高度过大，调整高度
                    preview_size = (preview_size[0], int(preview_size[0] * 3/4))
            
            # 创建高质量预览
            preview_image = image.resize(preview_size, Image.Resampling.LANCZOS)
            
            # 轻微增强预览图的清晰度
            try:
                from PIL import ImageEnhance
                sharpness_enhancer = ImageEnhance.Sharpness(preview_image)
                preview_image = sharpness_enhancer.enhance(1.1)
            except ImportError:
                pass  # 如果PIL增强功能不可用，使用原图
            
            output = io.BytesIO()
            preview_image.save(output, format='PNG', quality=90, optimize=True)
            
            return output.getvalue()
            
        except Exception as e:
            raise Exception(f"Preview creation failed: {str(e)}")
    
    def create_thumbnail(self, image_data: bytes, size: Tuple[int, int] = (150, 113)) -> bytes:
        """创建缩略图 - 用于快速预览和列表显示"""
        try:
            image = Image.open(io.BytesIO(image_data))
            
            # 创建缩略图，保持宽高比
            image.thumbnail(size, Image.Resampling.LANCZOS)
            
            output = io.BytesIO()
            image.save(output, format='JPEG', quality=85, optimize=True)
            
            return output.getvalue()
            
        except Exception as e:
            raise Exception(f"Thumbnail creation failed: {str(e)}")
    
    def get_optimized_formats(self, image_data: bytes) -> Dict[str, bytes]:
        """获取多种优化格式的图片数据"""
        try:
            formats = {}
            
            # 原始优化版本
            formats['optimized'] = self.optimize_for_amazon(image_data)
            
            # 预览版本
            formats['preview'] = self.create_module_preview(image_data)
            
            # 缩略图版本
            formats['thumbnail'] = self.create_thumbnail(image_data)
            
            # 高质量预览版本（用于详细查看）
            formats['hq_preview'] = self.create_high_quality_preview(image_data)
            
            return formats
            
        except Exception as e:
            raise Exception(f"Format optimization failed: {str(e)}")
    
    def create_high_quality_preview(self, image_data: bytes, max_size: Tuple[int, int] = (1200, 900)) -> bytes:
        """创建高质量预览图 - 用于详细查看和质量检查"""
        try:
            image = Image.open(io.BytesIO(image_data))
            
            # 保持4:3比例的高质量预览
            current_ratio = image.size[0] / image.size[1]
            target_ratio = 4 / 3
            
            if abs(current_ratio - target_ratio) > 0.01:
                # 如果比例不正确，进行裁剪或填充
                if current_ratio > target_ratio:
                    # 图片太宽，裁剪宽度
                    new_width = int(image.size[1] * target_ratio)
                    left = (image.size[0] - new_width) // 2
                    image = image.crop((left, 0, left + new_width, image.size[1]))
                else:
                    # 图片太高，裁剪高度
                    new_height = int(image.size[0] / target_ratio)
                    top = (image.size[1] - new_height) // 2
                    image = image.crop((0, top, image.size[0], top + new_height))
            
            # 调整到预览尺寸，保持高质量
            image.thumbnail(max_size, Image.Resampling.LANCZOS)
            
            output = io.BytesIO()
            image.save(output, format='PNG', quality=95, optimize=True)
            
            return output.getvalue()
            
        except Exception as e:
            raise Exception(f"High quality preview creation failed: {str(e)}")
    
    async def generate_module_batch(
        self, 
        prompts: Dict[ModuleType, ModulePrompt],
        reference_images: Optional[List[Image.Image]] = None
    ) -> Dict[ModuleType, GenerationResult]:
        """批量生成多个模块的图片"""
        results = {}
        
        # 并发生成所有模块（除了Extension需要特殊处理）
        tasks = []
        for module_type, prompt in prompts.items():
            if module_type != ModuleType.EXTENSION:
                task = self.generate_aplus_image(prompt, reference_images)
                tasks.append((module_type, task))
        
        # 等待所有任务完成
        for module_type, task in tasks:
            try:
                result = await task
                results[module_type] = result
            except Exception as e:
                results[module_type] = GenerationResult(
                    module_type=module_type,
                    image_data=None,
                    image_path=None,
                    prompt_used="",
                    generation_time=0.0,
                    quality_score=0.0,
                    validation_status=ValidationStatus.FAILED,
                    metadata={"error": str(e)}
                )
        
        return results
    
    def get_generation_stats(self, results: Dict[ModuleType, GenerationResult]) -> Dict[str, Any]:
        """获取生成统计信息"""
        total_time = sum(result.generation_time for result in results.values())
        avg_quality = sum(result.quality_score for result in results.values()) / len(results)
        
        success_count = sum(
            1 for result in results.values() 
            if result.validation_status != ValidationStatus.FAILED
        )
        
        return {
            "total_modules": len(results),
            "successful_generations": success_count,
            "total_generation_time": total_time,
            "average_quality_score": avg_quality,
            "success_rate": success_count / len(results) if results else 0
        }