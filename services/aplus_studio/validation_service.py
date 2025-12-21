"""
Validation Service for A+ Studio system.

This service handles quality validation, A+ compliance checking,
and image optimization for the generated content.
"""

from typing import Dict, List, Any, Optional
from PIL import Image
import io
import colorsys

from .models import (
    ValidationResult, ValidationStatus, GenerationResult, 
    VisualStyle, APLUS_IMAGE_SPECS
)


class ValidationService:
    """验证服务 - 处理质量验证和A+规范检查"""
    
    def __init__(self):
        self.aplus_specs = APLUS_IMAGE_SPECS
    
    def validate_aplus_compliance(self, image_data: bytes) -> ValidationResult:
        """验证A+规范合规性"""
        issues = []
        suggestions = []
        quality_metrics = {}
        
        try:
            image = Image.open(io.BytesIO(image_data))
            
            # 1. 尺寸验证
            expected_size = self.aplus_specs["dimensions"]
            if image.size != expected_size:
                issues.append(f"图片尺寸 {image.size} 不符合要求的 {expected_size}")
                suggestions.append("请调整图片尺寸为600x450像素")
            
            # 2. 文件大小验证
            file_size = len(image_data)
            max_size = self.aplus_specs["max_file_size"]
            if file_size > max_size:
                issues.append(f"文件大小 {file_size/1024/1024:.1f}MB 超过限制 {max_size/1024/1024}MB")
                suggestions.append("请压缩图片以减小文件大小")
            
            # 3. 格式验证
            if image.format not in self.aplus_specs["supported_formats"]:
                issues.append(f"图片格式 {image.format} 不在支持的格式中")
                suggestions.append(f"请使用以下格式之一：{', '.join(self.aplus_specs['supported_formats'])}")
            
            # 4. 色彩空间验证
            if image.mode not in ['RGB', 'RGBA']:
                issues.append(f"色彩模式 {image.mode} 可能不适合网络显示")
                suggestions.append("建议使用RGB色彩模式")
            
            # 5. 质量指标计算
            quality_metrics = self._calculate_quality_metrics(image)
            
            # 确定验证状态
            if not issues:
                status = ValidationStatus.PASSED
            elif len(issues) <= 2:
                status = ValidationStatus.NEEDS_REVIEW
            else:
                status = ValidationStatus.FAILED
            
            return ValidationResult(
                is_valid=len(issues) == 0,
                validation_status=status,
                issues=issues,
                suggestions=suggestions,
                quality_metrics=quality_metrics
            )
            
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                validation_status=ValidationStatus.FAILED,
                issues=[f"验证过程出错：{str(e)}"],
                suggestions=["请检查图片文件的完整性"],
                quality_metrics={}
            )
    
    def _calculate_quality_metrics(self, image: Image.Image) -> Dict[str, float]:
        """计算图片质量指标"""
        metrics = {}
        
        try:
            # 1. 清晰度评估（基于边缘检测的简化版本）
            gray_image = image.convert('L')
            # 这里应该实现更复杂的清晰度算法
            metrics["sharpness_score"] = 0.8  # 占位符
            
            # 2. 对比度评估
            histogram = gray_image.histogram()
            metrics["contrast_score"] = self._calculate_contrast_score(histogram)
            
            # 3. 色彩丰富度
            if image.mode in ['RGB', 'RGBA']:
                metrics["color_richness"] = self._calculate_color_richness(image)
            
            # 4. 构图平衡度（基于重心分析的简化版本）
            metrics["composition_balance"] = 0.7  # 占位符
            
            # 5. 整体质量评分
            metrics["overall_quality"] = (
                metrics.get("sharpness_score", 0) * 0.3 +
                metrics.get("contrast_score", 0) * 0.25 +
                metrics.get("color_richness", 0) * 0.25 +
                metrics.get("composition_balance", 0) * 0.2
            )
            
        except Exception as e:
            metrics["error"] = f"质量计算出错：{str(e)}"
        
        return metrics
    
    def _calculate_contrast_score(self, histogram: List[int]) -> float:
        """计算对比度评分"""
        try:
            # 简化的对比度计算：基于直方图的标准差
            total_pixels = sum(histogram)
            if total_pixels == 0:
                return 0.0
            
            # 计算加权平均值
            weighted_sum = sum(i * count for i, count in enumerate(histogram))
            mean = weighted_sum / total_pixels
            
            # 计算标准差
            variance = sum(count * (i - mean) ** 2 for i, count in enumerate(histogram)) / total_pixels
            std_dev = variance ** 0.5
            
            # 归一化到0-1范围
            contrast_score = min(std_dev / 128.0, 1.0)
            
            return contrast_score
            
        except Exception:
            return 0.5  # 默认中等对比度
    
    def _calculate_color_richness(self, image: Image.Image) -> float:
        """计算色彩丰富度"""
        try:
            # 转换为HSV以分析色彩
            hsv_image = image.convert('HSV')
            
            # 获取饱和度通道
            _, saturation, _ = hsv_image.split()
            sat_histogram = saturation.histogram()
            
            # 计算平均饱和度
            total_pixels = sum(sat_histogram)
            if total_pixels == 0:
                return 0.0
            
            weighted_saturation = sum(i * count for i, count in enumerate(sat_histogram))
            avg_saturation = weighted_saturation / total_pixels / 255.0
            
            return avg_saturation
            
        except Exception:
            return 0.5  # 默认中等色彩丰富度
    
    def validate_visual_consistency(
        self, 
        results: Dict[str, GenerationResult], 
        target_style: VisualStyle
    ) -> ValidationResult:
        """验证视觉连贯性"""
        issues = []
        suggestions = []
        consistency_metrics = {}
        
        try:
            # 检查是否有足够的图片进行比较
            valid_results = [r for r in results.values() if r.image_data]
            if len(valid_results) < 2:
                return ValidationResult(
                    is_valid=True,
                    validation_status=ValidationStatus.PASSED,
                    issues=[],
                    suggestions=["需要至少两张图片才能验证视觉连贯性"],
                    quality_metrics={}
                )
            
            # 分析每张图片的视觉特征
            image_features = []
            for result in valid_results:
                if result.image_data:
                    features = self._extract_visual_features(result.image_data)
                    image_features.append(features)
            
            # 检查色彩一致性
            color_consistency = self._check_color_consistency(image_features, target_style.color_palette)
            consistency_metrics["color_consistency"] = color_consistency
            
            if color_consistency < 0.7:
                issues.append("图片间色彩一致性不足")
                suggestions.append("调整图片色调以保持一致的色彩风格")
            
            # 检查光照风格一致性
            lighting_consistency = self._check_lighting_consistency(image_features)
            consistency_metrics["lighting_consistency"] = lighting_consistency
            
            if lighting_consistency < 0.6:
                issues.append("图片间光照风格差异较大")
                suggestions.append("统一光照风格以增强视觉连贯性")
            
            # 检查构图风格一致性
            composition_consistency = self._check_composition_consistency(image_features)
            consistency_metrics["composition_consistency"] = composition_consistency
            
            if composition_consistency < 0.6:
                issues.append("图片间构图风格不够统一")
                suggestions.append("保持一致的构图规则和视觉重心")
            
            # 计算整体一致性评分
            overall_consistency = (
                color_consistency * 0.4 +
                lighting_consistency * 0.3 +
                composition_consistency * 0.3
            )
            consistency_metrics["overall_consistency"] = overall_consistency
            
            # 确定验证状态
            if overall_consistency >= 0.8:
                status = ValidationStatus.PASSED
            elif overall_consistency >= 0.6:
                status = ValidationStatus.NEEDS_REVIEW
            else:
                status = ValidationStatus.FAILED
            
            return ValidationResult(
                is_valid=overall_consistency >= 0.6,
                validation_status=status,
                issues=issues,
                suggestions=suggestions,
                quality_metrics=consistency_metrics
            )
            
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                validation_status=ValidationStatus.FAILED,
                issues=[f"一致性验证出错：{str(e)}"],
                suggestions=["请检查图片数据的完整性"],
                quality_metrics={}
            )
    
    def _extract_visual_features(self, image_data: bytes) -> Dict[str, Any]:
        """提取图片的视觉特征"""
        try:
            image = Image.open(io.BytesIO(image_data))
            
            features = {}
            
            # 提取主要颜色
            features["dominant_colors"] = self._get_dominant_colors(image)
            
            # 分析亮度分布
            features["brightness_distribution"] = self._analyze_brightness(image)
            
            # 分析对比度
            features["contrast_level"] = self._calculate_contrast_score(
                image.convert('L').histogram()
            )
            
            return features
            
        except Exception as e:
            return {"error": str(e)}
    
    def _get_dominant_colors(self, image: Image.Image, num_colors: int = 5) -> List[tuple]:
        """获取图片的主要颜色"""
        try:
            # 缩小图片以提高处理速度
            small_image = image.resize((100, 100))
            
            # 转换为RGB
            if small_image.mode != 'RGB':
                small_image = small_image.convert('RGB')
            
            # 获取所有像素颜色
            pixels = list(small_image.getdata())
            
            # 简化的颜色聚类（实际应该使用更复杂的算法）
            color_counts = {}
            for pixel in pixels:
                # 量化颜色以减少变化
                quantized = tuple(c // 32 * 32 for c in pixel)
                color_counts[quantized] = color_counts.get(quantized, 0) + 1
            
            # 获取最常见的颜色
            sorted_colors = sorted(color_counts.items(), key=lambda x: x[1], reverse=True)
            dominant_colors = [color for color, count in sorted_colors[:num_colors]]
            
            return dominant_colors
            
        except Exception:
            return [(128, 128, 128)]  # 默认灰色
    
    def _analyze_brightness(self, image: Image.Image) -> Dict[str, float]:
        """分析图片亮度分布"""
        try:
            gray_image = image.convert('L')
            histogram = gray_image.histogram()
            
            total_pixels = sum(histogram)
            if total_pixels == 0:
                return {"mean": 0.5, "std": 0.0}
            
            # 计算平均亮度
            weighted_sum = sum(i * count for i, count in enumerate(histogram))
            mean_brightness = weighted_sum / total_pixels / 255.0
            
            # 计算亮度标准差
            variance = sum(count * (i/255.0 - mean_brightness) ** 2 for i, count in enumerate(histogram)) / total_pixels
            std_brightness = variance ** 0.5
            
            return {
                "mean": mean_brightness,
                "std": std_brightness
            }
            
        except Exception:
            return {"mean": 0.5, "std": 0.2}
    
    def _check_color_consistency(self, image_features: List[Dict], target_palette: List[str]) -> float:
        """检查色彩一致性"""
        try:
            if len(image_features) < 2:
                return 1.0
            
            # 简化的色彩一致性检查
            # 实际应该比较色彩分布的相似性
            consistency_scores = []
            
            for i in range(len(image_features) - 1):
                for j in range(i + 1, len(image_features)):
                    # 比较两张图片的主要颜色
                    colors1 = image_features[i].get("dominant_colors", [])
                    colors2 = image_features[j].get("dominant_colors", [])
                    
                    if colors1 and colors2:
                        # 简化的颜色相似度计算
                        similarity = self._calculate_color_similarity(colors1, colors2)
                        consistency_scores.append(similarity)
            
            return sum(consistency_scores) / len(consistency_scores) if consistency_scores else 0.5
            
        except Exception:
            return 0.5
    
    def _check_lighting_consistency(self, image_features: List[Dict]) -> float:
        """检查光照一致性"""
        try:
            if len(image_features) < 2:
                return 1.0
            
            brightness_values = []
            for features in image_features:
                brightness = features.get("brightness_distribution", {})
                if brightness:
                    brightness_values.append(brightness.get("mean", 0.5))
            
            if len(brightness_values) < 2:
                return 0.5
            
            # 计算亮度值的标准差，标准差越小一致性越好
            mean_brightness = sum(brightness_values) / len(brightness_values)
            variance = sum((b - mean_brightness) ** 2 for b in brightness_values) / len(brightness_values)
            std_dev = variance ** 0.5
            
            # 将标准差转换为一致性评分（0-1）
            consistency = max(0, 1 - std_dev * 2)
            
            return consistency
            
        except Exception:
            return 0.5
    
    def _check_composition_consistency(self, image_features: List[Dict]) -> float:
        """检查构图一致性"""
        try:
            if len(image_features) < 2:
                return 1.0
            
            contrast_values = []
            for features in image_features:
                contrast = features.get("contrast_level", 0.5)
                contrast_values.append(contrast)
            
            if len(contrast_values) < 2:
                return 0.5
            
            # 基于对比度的构图一致性评估
            mean_contrast = sum(contrast_values) / len(contrast_values)
            variance = sum((c - mean_contrast) ** 2 for c in contrast_values) / len(contrast_values)
            std_dev = variance ** 0.5
            
            consistency = max(0, 1 - std_dev * 2)
            
            return consistency
            
        except Exception:
            return 0.5
    
    def _calculate_color_similarity(self, colors1: List[tuple], colors2: List[tuple]) -> float:
        """计算两组颜色的相似度"""
        try:
            if not colors1 or not colors2:
                return 0.0
            
            # 简化的颜色相似度计算
            similarities = []
            
            for color1 in colors1[:3]:  # 只比较前3个主要颜色
                best_similarity = 0
                for color2 in colors2[:3]:
                    # 计算RGB距离
                    distance = sum((c1 - c2) ** 2 for c1, c2 in zip(color1, color2)) ** 0.5
                    # 转换为相似度（0-1）
                    similarity = max(0, 1 - distance / (255 * 3 ** 0.5))
                    best_similarity = max(best_similarity, similarity)
                similarities.append(best_similarity)
            
            return sum(similarities) / len(similarities) if similarities else 0.0
            
        except Exception:
            return 0.0