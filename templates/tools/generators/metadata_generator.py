"""
元数据生成器 - 自动分析模板图片并生成元数据
"""

import os
import json
import colorsys
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from PIL import Image, ImageStat
import numpy as np
try:
    import cv2
    HAS_OPENCV = True
except ImportError:
    HAS_OPENCV = False

from ..models.metadata import (
    ImageAnalysis, DesignFeatures, QualityMetrics, TemplateMetadata
)


class MetadataGenerator:
    """元数据生成器 - 分析图片并生成模板元数据"""
    
    def __init__(self):
        """初始化元数据生成器"""
        # 预定义的分类映射
        self.category_keywords = {
            "electronics": ["科技", "数码", "电子", "智能", "现代", "蓝色", "黑色", "简约"],
            "beauty": ["美妆", "护肤", "优雅", "粉色", "白色", "柔和", "清新", "自然"],
            "home": ["家居", "温馨", "舒适", "木质", "暖色", "生活", "实用", "简洁"],
            "seasonal": ["季节", "节日", "庆祝", "特殊", "限时", "主题"]
        }
        
        # 色调分类
        self.color_tone_ranges = {
            "warm": [(0, 60), (300, 360)],    # 红、橙、黄色调
            "cool": [(180, 300)],             # 蓝、绿、紫色调
            "neutral": [(60, 180)]            # 中性色调
        }
        
        # 设计风格关键词
        self.style_keywords = {
            "modern": ["简约", "现代", "科技", "几何", "线条"],
            "vintage": ["复古", "经典", "怀旧", "传统", "装饰"],
            "minimal": ["简约", "极简", "留白", "干净", "纯净"],
            "luxury": ["奢华", "高端", "精致", "金色", "质感"],
            "casual": ["休闲", "轻松", "自然", "舒适", "日常"],
            "professional": ["专业", "商务", "正式", "严谨", "可靠"]
        }
    
    def analyze_image(self, image_path: str) -> ImageAnalysis:
        """
        分析单张图片
        
        Args:
            image_path: 图片文件路径
            
        Returns:
            ImageAnalysis: 图片分析结果
        """
        try:
            # 打开图片
            with Image.open(image_path) as img:
                # 基本信息
                width, height = img.size
                format_name = img.format or "UNKNOWN"
                file_size = os.path.getsize(image_path)
                color_mode = img.mode
                
                # 创建分析对象
                analysis = ImageAnalysis(
                    width=width,
                    height=height,
                    format=format_name,
                    file_size=file_size,
                    color_mode=color_mode
                )
                
                # 色彩分析
                self._analyze_colors(img, analysis)
                
                # 质量分析
                self._analyze_quality(img, analysis)
                
                # 内容分析
                self._analyze_content(image_path, analysis)
                
                return analysis
                
        except Exception as e:
            # 返回基本信息，即使分析失败
            file_size = os.path.getsize(image_path) if os.path.exists(image_path) else 0
            return ImageAnalysis(
                width=0,
                height=0,
                format="UNKNOWN",
                file_size=file_size,
                color_mode="UNKNOWN"
            )
    
    def _analyze_colors(self, img: Image.Image, analysis: ImageAnalysis):
        """分析图片色彩"""
        try:
            # 转换为RGB模式进行色彩分析
            if img.mode != 'RGB':
                img_rgb = img.convert('RGB')
            else:
                img_rgb = img
            
            # 缩小图片以提高处理速度
            img_small = img_rgb.resize((100, 100))
            
            # 获取像素数据
            pixels = np.array(img_small)
            pixels = pixels.reshape(-1, 3)
            
            # 计算主要颜色
            self._extract_dominant_colors(pixels, analysis)
            
            # 计算色彩统计
            stat = ImageStat.Stat(img_rgb)
            
            # 亮度 (0-255)
            analysis.brightness = sum(stat.mean) / 3 / 255.0
            
            # 对比度 (标准差)
            analysis.contrast = sum(stat.stddev) / 3 / 255.0
            
            # 饱和度 (HSV模式)
            img_hsv = img_rgb.convert('HSV')
            hsv_stat = ImageStat.Stat(img_hsv)
            analysis.saturation = hsv_stat.mean[1] / 255.0
            
        except Exception:
            # 如果色彩分析失败，设置默认值
            analysis.brightness = 0.5
            analysis.contrast = 0.5
            analysis.saturation = 0.5
    
    def _extract_dominant_colors(self, pixels: np.ndarray, analysis: ImageAnalysis):
        """提取主要颜色"""
        try:
            # 尝试使用K-means聚类找到主要颜色
            try:
                from sklearn.cluster import KMeans
                
                # 聚类为5个主要颜色
                kmeans = KMeans(n_clusters=5, random_state=42, n_init=10)
                kmeans.fit(pixels)
                
                # 获取聚类中心（主要颜色）
                colors = kmeans.cluster_centers_.astype(int)
                
                # 转换为十六进制
                analysis.dominant_colors = [
                    f"#{r:02x}{g:02x}{b:02x}" for r, g, b in colors
                ]
                
                # 生成调色板（前3个颜色）
                analysis.color_palette = analysis.dominant_colors[:3]
                
            except ImportError:
                # 如果sklearn不可用，使用简单的颜色提取
                self._simple_color_extraction(pixels, analysis)
                
        except Exception:
            # 设置默认颜色
            analysis.dominant_colors = ["#808080"]
            analysis.color_palette = ["#808080"]
    
    def _simple_color_extraction(self, pixels: np.ndarray, analysis: ImageAnalysis):
        """简单的颜色提取（不依赖sklearn）"""
        # 计算平均颜色
        mean_color = np.mean(pixels, axis=0).astype(int)
        analysis.dominant_colors = [f"#{mean_color[0]:02x}{mean_color[1]:02x}{mean_color[2]:02x}"]
        analysis.color_palette = analysis.dominant_colors
    
    def _analyze_quality(self, img: Image.Image, analysis: ImageAnalysis):
        """分析图片质量"""
        try:
            # 转换为灰度图进行质量分析
            gray = img.convert('L')
            gray_array = np.array(gray)
            
            if HAS_OPENCV:
                # 锐度 (拉普拉斯算子的方差)
                laplacian = cv2.Laplacian(gray_array, cv2.CV_64F)
                analysis.sharpness = laplacian.var() / 10000.0  # 归一化
            else:
                # 简单的锐度估计（基于标准差）
                analysis.sharpness = np.std(gray_array) / 255.0
            
            # 噪声水平 (标准差)
            analysis.noise_level = np.std(gray_array) / 255.0
            
            # 压缩质量估计 (基于文件大小和像素数)
            expected_size = analysis.width * analysis.height * 3  # RGB未压缩大小
            compression_ratio = analysis.file_size / expected_size if expected_size > 0 else 0
            analysis.compression_quality = min(compression_ratio * 10, 1.0)  # 归一化到0-1
            
        except Exception:
            # 设置默认质量值
            analysis.sharpness = 0.5
            analysis.noise_level = 0.1
            analysis.compression_quality = 0.8
    
    def _analyze_content(self, image_path: str, analysis: ImageAnalysis):
        """分析图片内容"""
        try:
            # 基于文件名和路径进行简单的内容推断
            filename = os.path.basename(image_path).lower()
            
            # 检测是否包含文字（基于文件名）
            text_indicators = ['text', 'title', 'header', 'label']
            analysis.has_text = any(indicator in filename for indicator in text_indicators)
            
            # 检测是否包含产品（基于文件名和路径）
            product_indicators = ['product', 'item', 'gallery', 'showcase']
            analysis.has_products = any(indicator in filename for indicator in product_indicators)
            
            # 人脸检测需要更复杂的算法，这里简单设置为False
            analysis.has_faces = False
            
        except Exception:
            # 设置默认值
            analysis.has_text = False
            analysis.has_faces = False
            analysis.has_products = False
    
    def extract_design_features(self, template_path: str, image_analyses: Dict[str, ImageAnalysis]) -> DesignFeatures:
        """
        提取设计特征
        
        Args:
            template_path: 模板路径
            image_analyses: 图片分析结果字典
            
        Returns:
            DesignFeatures: 设计特征
        """
        features = DesignFeatures()
        
        if not image_analyses:
            return features
        
        # 分析整体色调
        self._analyze_color_tone(image_analyses, features)
        
        # 分析设计复杂度
        self._analyze_design_complexity(image_analyses, features)
        
        # 分析视觉重量
        self._analyze_visual_weight(image_analyses, features)
        
        # 分析布局特征
        self._analyze_layout_features(template_path, image_analyses, features)
        
        # 生成风格标签
        self._generate_style_tags(features)
        
        return features
    
    def _analyze_color_tone(self, image_analyses: Dict[str, ImageAnalysis], features: DesignFeatures):
        """分析色调"""
        warm_count = 0
        cool_count = 0
        neutral_count = 0
        
        for analysis in image_analyses.values():
            for color_hex in analysis.dominant_colors:
                # 转换十六进制颜色到HSV
                try:
                    r = int(color_hex[1:3], 16) / 255.0
                    g = int(color_hex[3:5], 16) / 255.0
                    b = int(color_hex[5:7], 16) / 255.0
                    
                    h, s, v = colorsys.rgb_to_hsv(r, g, b)
                    hue_degree = h * 360
                    
                    # 判断色调类型
                    if any(start <= hue_degree <= end for start, end in self.color_tone_ranges["warm"]):
                        warm_count += 1
                    elif any(start <= hue_degree <= end for start, end in self.color_tone_ranges["cool"]):
                        cool_count += 1
                    else:
                        neutral_count += 1
                        
                except (ValueError, IndexError):
                    neutral_count += 1
        
        # 确定主要色调
        if warm_count > cool_count and warm_count > neutral_count:
            features.color_tone = "warm"
        elif cool_count > warm_count and cool_count > neutral_count:
            features.color_tone = "cool"
        else:
            features.color_tone = "neutral"
    
    def _analyze_design_complexity(self, image_analyses: Dict[str, ImageAnalysis], features: DesignFeatures):
        """分析设计复杂度"""
        total_colors = 0
        total_contrast = 0.0
        count = 0
        
        for analysis in image_analyses.values():
            total_colors += len(analysis.dominant_colors)
            total_contrast += analysis.contrast
            count += 1
        
        if count > 0:
            avg_colors = total_colors / count
            avg_contrast = total_contrast / count
            
            # 基于颜色数量和对比度判断复杂度
            complexity_score = (avg_colors / 5.0) + avg_contrast
            
            if complexity_score < 0.5:
                features.design_complexity = "simple"
            elif complexity_score < 1.0:
                features.design_complexity = "moderate"
            else:
                features.design_complexity = "complex"
        else:
            features.design_complexity = "moderate"
    
    def _analyze_visual_weight(self, image_analyses: Dict[str, ImageAnalysis], features: DesignFeatures):
        """分析视觉重量"""
        total_saturation = 0.0
        total_brightness = 0.0
        count = 0
        
        for analysis in image_analyses.values():
            total_saturation += analysis.saturation
            total_brightness += analysis.brightness
            count += 1
        
        if count > 0:
            avg_saturation = total_saturation / count
            avg_brightness = total_brightness / count
            
            # 基于饱和度和亮度判断视觉重量
            weight_score = avg_saturation + (1.0 - avg_brightness)
            
            if weight_score < 0.4:
                features.visual_weight = "light"
            elif weight_score < 0.8:
                features.visual_weight = "medium"
            else:
                features.visual_weight = "heavy"
        else:
            features.visual_weight = "medium"
    
    def _analyze_layout_features(self, template_path: str, image_analyses: Dict[str, ImageAnalysis], features: DesignFeatures):
        """分析布局特征"""
        # 基于文件结构推断布局类型
        template_name = os.path.basename(template_path)
        
        if "grid" in template_name.lower():
            features.layout_type = "grid"
        elif "center" in template_name.lower():
            features.layout_type = "centered"
        else:
            features.layout_type = "freeform"
        
        # 基于图片数量推断文本密度
        image_count = len(image_analyses)
        if image_count <= 2:
            features.text_density = "low"
        elif image_count <= 4:
            features.text_density = "medium"
        else:
            features.text_density = "high"
        
        # 计算图片占比（简化计算）
        features.image_ratio = min(image_count / 6.0, 1.0)  # 假设最多6张图片
    
    def _generate_style_tags(self, features: DesignFeatures):
        """生成风格标签"""
        # 基于色调添加标签
        if features.color_tone == "warm":
            features.add_style_tag("温暖")
            features.add_mood_tag("舒适")
        elif features.color_tone == "cool":
            features.add_style_tag("冷静")
            features.add_mood_tag("专业")
        else:
            features.add_style_tag("平衡")
            features.add_mood_tag("中性")
        
        # 基于复杂度添加标签
        if features.design_complexity == "simple":
            features.add_style_tag("简约")
            features.add_mood_tag("清爽")
        elif features.design_complexity == "complex":
            features.add_style_tag("丰富")
            features.add_mood_tag("动感")
        
        # 基于视觉重量添加标签
        if features.visual_weight == "light":
            features.add_style_tag("轻盈")
        elif features.visual_weight == "heavy":
            features.add_style_tag("厚重")
    
    def suggest_categories(self, features: DesignFeatures) -> List[str]:
        """
        基于设计特征推荐分类
        
        Args:
            features: 设计特征
            
        Returns:
            List[str]: 推荐的分类列表
        """
        suggestions = []
        
        # 基于色调和风格标签匹配分类
        all_tags = features.style_tags + features.mood_tags + [features.color_tone]
        
        for category, keywords in self.category_keywords.items():
            match_count = sum(1 for tag in all_tags if any(keyword in tag for keyword in keywords))
            if match_count > 0:
                suggestions.append((category, match_count))
        
        # 按匹配度排序
        suggestions.sort(key=lambda x: x[1], reverse=True)
        
        return [category for category, _ in suggestions[:3]]  # 返回前3个推荐
    
    def generate_keywords(self, analysis: ImageAnalysis, features: DesignFeatures) -> List[str]:
        """
        生成关键词
        
        Args:
            analysis: 图片分析结果
            features: 设计特征
            
        Returns:
            List[str]: 生成的关键词列表
        """
        keywords = []
        
        # 基于色调生成关键词
        if features.color_tone == "warm":
            keywords.extend(["温暖", "舒适", "亲和"])
        elif features.color_tone == "cool":
            keywords.extend(["冷静", "专业", "科技"])
        else:
            keywords.extend(["平衡", "中性", "通用"])
        
        # 基于设计复杂度生成关键词
        if features.design_complexity == "simple":
            keywords.extend(["简约", "极简", "清爽"])
        elif features.design_complexity == "complex":
            keywords.extend(["丰富", "详细", "全面"])
        
        # 基于视觉重量生成关键词
        if features.visual_weight == "light":
            keywords.extend(["轻盈", "优雅", "精致"])
        elif features.visual_weight == "heavy":
            keywords.extend(["厚重", "稳重", "强烈"])
        
        # 基于图片质量生成关键词
        if analysis.sharpness > 0.7:
            keywords.append("高清")
        if analysis.compression_quality > 0.8:
            keywords.append("高质量")
        
        # 去重并返回
        return list(set(keywords))
    
    def generate_template_metadata(self, template_path: str) -> TemplateMetadata:
        """
        生成完整的模板元数据
        
        Args:
            template_path: 模板目录路径
            
        Returns:
            TemplateMetadata: 完整的模板元数据
        """
        template_id = os.path.basename(template_path)
        metadata = TemplateMetadata(template_id=template_id)
        
        # 分析所有图片
        image_files = self._find_image_files(template_path)
        
        for image_file in image_files:
            image_path = os.path.join(template_path, image_file)
            analysis = self.analyze_image(image_path)
            metadata.add_image_analysis(image_file, analysis)
        
        # 提取设计特征
        design_features = self.extract_design_features(template_path, metadata.image_analyses)
        metadata.update_design_features(design_features)
        
        # 生成推荐分类
        suggested_categories = self.suggest_categories(design_features)
        for category in suggested_categories:
            metadata.suggest_category(category)
        
        # 生成关键词（基于第一张图片的分析）
        if metadata.image_analyses:
            first_analysis = next(iter(metadata.image_analyses.values()))
            keywords = self.generate_keywords(first_analysis, design_features)
            for keyword in keywords:
                metadata.add_generated_keyword(keyword)
        
        # 生成标签
        for tag in design_features.style_tags + design_features.mood_tags:
            metadata.add_generated_tag(tag)
        
        # 计算质量指标
        quality_metrics = self._calculate_quality_metrics(metadata)
        metadata.update_quality_metrics(quality_metrics)
        
        return metadata
    
    def _find_image_files(self, template_path: str) -> List[str]:
        """查找模板目录中的所有图片文件"""
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
        image_files = []
        
        for root, dirs, files in os.walk(template_path):
            for file in files:
                if any(file.lower().endswith(ext) for ext in image_extensions):
                    # 获取相对路径
                    rel_path = os.path.relpath(os.path.join(root, file), template_path)
                    image_files.append(rel_path)
        
        return image_files
    
    def _calculate_quality_metrics(self, metadata: TemplateMetadata) -> QualityMetrics:
        """计算质量指标"""
        metrics = QualityMetrics()
        
        if not metadata.image_analyses:
            return metrics
        
        # 图片质量评分
        total_sharpness = sum(analysis.sharpness for analysis in metadata.image_analyses.values())
        total_compression = sum(analysis.compression_quality for analysis in metadata.image_analyses.values())
        image_count = len(metadata.image_analyses)
        
        metrics.image_quality = ((total_sharpness + total_compression) / (2 * image_count)) * 100
        
        # 完整性评分（基于图片数量和类型）
        has_preview = any('preview' in path for path in metadata.image_analyses.keys())
        has_desktop = any('desktop' in path for path in metadata.image_analyses.keys())
        has_mobile = any('mobile' in path for path in metadata.image_analyses.keys())
        
        completeness_score = 0
        if has_preview:
            completeness_score += 30
        if has_desktop:
            completeness_score += 35
        if has_mobile:
            completeness_score += 35
        
        metrics.completeness_score = completeness_score
        
        # 设计质量评分（基于设计特征）
        design_score = 70  # 基础分
        if metadata.design_features.style_tags:
            design_score += 10
        if metadata.design_features.color_tone:
            design_score += 10
        if metadata.design_features.design_complexity != "":
            design_score += 10
        
        metrics.design_quality = min(design_score, 100)
        
        # 可用性评分（基于标准尺寸符合度）
        dimension_compliance = self._check_dimension_compliance(metadata.image_analyses)
        metrics.usability_score = dimension_compliance * 100
        
        # 性能评分（基于文件大小）
        avg_file_size = sum(analysis.file_size for analysis in metadata.image_analyses.values()) / image_count
        # 理想文件大小约为500KB，超过1MB扣分
        size_score = max(0, 100 - (avg_file_size - 500000) / 10000)
        metrics.performance_score = max(0, min(100, size_score))
        
        # 可访问性评分（基础评分）
        metrics.accessibility_score = 80  # 基础可访问性评分
        
        return metrics
    
    def _check_dimension_compliance(self, image_analyses: Dict[str, ImageAnalysis]) -> float:
        """检查尺寸规范符合度"""
        standard_dimensions = {
            "desktop": (1464, 600),
            "mobile": (600, 450),
            "preview": (300, 200)
        }
        
        compliant_count = 0
        total_count = 0
        
        for image_path, analysis in image_analyses.items():
            for format_type, (expected_width, expected_height) in standard_dimensions.items():
                if format_type in image_path.lower():
                    total_count += 1
                    if analysis.is_valid_dimensions(expected_width, expected_height, tolerance=10):
                        compliant_count += 1
                    break
        
        return compliant_count / total_count if total_count > 0 else 0.0
    
    def save_metadata(self, metadata: TemplateMetadata, output_path: str):
        """
        保存元数据到JSON文件
        
        Args:
            metadata: 模板元数据
            output_path: 输出文件路径
        """
        # 创建输出目录
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # 转换为可序列化的字典
        metadata_dict = {
            "template_id": metadata.template_id,
            "created_at": metadata.created_at.isoformat(),
            "updated_at": metadata.updated_at.isoformat(),
            "analysis_version": metadata.analysis_version,
            
            "file_info": metadata.file_info,
            
            "image_analyses": {
                path: {
                    "width": analysis.width,
                    "height": analysis.height,
                    "format": analysis.format,
                    "file_size": analysis.file_size,
                    "color_mode": analysis.color_mode,
                    "dominant_colors": analysis.dominant_colors,
                    "color_palette": analysis.color_palette,
                    "brightness": analysis.brightness,
                    "contrast": analysis.contrast,
                    "saturation": analysis.saturation,
                    "has_text": analysis.has_text,
                    "has_faces": analysis.has_faces,
                    "has_products": analysis.has_products,
                    "sharpness": analysis.sharpness,
                    "noise_level": analysis.noise_level,
                    "compression_quality": analysis.compression_quality,
                    "aspect_ratio": analysis.aspect_ratio,
                    "megapixels": analysis.megapixels,
                    "file_size_mb": analysis.file_size_mb
                }
                for path, analysis in metadata.image_analyses.items()
            },
            
            "design_features": {
                "style_category": metadata.design_features.style_category,
                "color_tone": metadata.design_features.color_tone,
                "design_complexity": metadata.design_features.design_complexity,
                "visual_weight": metadata.design_features.visual_weight,
                "has_gradients": metadata.design_features.has_gradients,
                "has_patterns": metadata.design_features.has_patterns,
                "has_shadows": metadata.design_features.has_shadows,
                "has_borders": metadata.design_features.has_borders,
                "layout_type": metadata.design_features.layout_type,
                "text_density": metadata.design_features.text_density,
                "image_ratio": metadata.design_features.image_ratio,
                "style_tags": metadata.design_features.style_tags,
                "mood_tags": metadata.design_features.mood_tags,
                "target_audience": metadata.design_features.target_audience,
                "use_cases": metadata.design_features.use_cases
            },
            
            "quality_metrics": {
                "completeness_score": metadata.quality_metrics.completeness_score,
                "design_quality": metadata.quality_metrics.design_quality,
                "usability_score": metadata.quality_metrics.usability_score,
                "performance_score": metadata.quality_metrics.performance_score,
                "accessibility_score": metadata.quality_metrics.accessibility_score,
                "image_quality": metadata.quality_metrics.image_quality,
                "config_completeness": metadata.quality_metrics.config_completeness,
                "naming_consistency": metadata.quality_metrics.naming_consistency,
                "structure_compliance": metadata.quality_metrics.structure_compliance,
                "overall_score": metadata.quality_metrics.overall_score,
                "grade": metadata.quality_metrics.get_grade()
            },
            
            "generated_tags": metadata.generated_tags,
            "generated_keywords": metadata.generated_keywords,
            "suggested_categories": metadata.suggested_categories,
            
            "summary": metadata.get_summary()
        }
        
        # 保存到文件
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(metadata_dict, f, ensure_ascii=False, indent=2)