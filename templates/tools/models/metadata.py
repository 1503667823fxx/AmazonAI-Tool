"""
元数据相关的数据模型
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple


@dataclass
class ImageAnalysis:
    """图片分析结果"""
    width: int
    height: int
    format: str
    file_size: int
    color_mode: str
    
    # 色彩分析
    dominant_colors: List[str] = field(default_factory=list)
    color_palette: List[str] = field(default_factory=list)
    brightness: float = 0.0
    contrast: float = 0.0
    saturation: float = 0.0
    
    # 内容分析
    has_text: bool = False
    has_faces: bool = False
    has_products: bool = False
    
    # 质量指标
    sharpness: float = 0.0
    noise_level: float = 0.0
    compression_quality: float = 0.0
    
    @property
    def aspect_ratio(self) -> float:
        """获取宽高比"""
        return self.width / self.height if self.height > 0 else 0.0
    
    @property
    def megapixels(self) -> float:
        """获取像素数(百万像素)"""
        return (self.width * self.height) / 1_000_000
    
    @property
    def file_size_mb(self) -> float:
        """获取文件大小(MB)"""
        return self.file_size / (1024 * 1024)
    
    def is_valid_dimensions(self, expected_width: int, expected_height: int, tolerance: int = 0) -> bool:
        """检查尺寸是否符合要求"""
        width_ok = abs(self.width - expected_width) <= tolerance
        height_ok = abs(self.height - expected_height) <= tolerance
        return width_ok and height_ok


@dataclass
class DesignFeatures:
    """设计特征分析"""
    style_category: str = ""
    color_tone: str = ""  # warm, cool, neutral
    design_complexity: str = ""  # simple, moderate, complex
    visual_weight: str = ""  # light, medium, heavy
    
    # 设计元素
    has_gradients: bool = False
    has_patterns: bool = False
    has_shadows: bool = False
    has_borders: bool = False
    
    # 布局特征
    layout_type: str = ""  # grid, freeform, centered
    text_density: str = ""  # low, medium, high
    image_ratio: float = 0.0  # 图片占比
    
    # 风格标签
    style_tags: List[str] = field(default_factory=list)
    mood_tags: List[str] = field(default_factory=list)
    
    # 目标受众推断
    target_audience: List[str] = field(default_factory=list)
    use_cases: List[str] = field(default_factory=list)
    
    def add_style_tag(self, tag: str):
        """添加风格标签"""
        if tag not in self.style_tags:
            self.style_tags.append(tag)
    
    def add_mood_tag(self, tag: str):
        """添加情绪标签"""
        if tag not in self.mood_tags:
            self.mood_tags.append(tag)


@dataclass
class QualityMetrics:
    """质量指标"""
    completeness_score: float = 0.0  # 完整性评分 (0-100)
    design_quality: float = 0.0      # 设计质量 (0-100)
    usability_score: float = 0.0     # 可用性评分 (0-100)
    performance_score: float = 0.0   # 性能评分 (0-100)
    accessibility_score: float = 0.0 # 可访问性评分 (0-100)
    
    # 具体指标
    image_quality: float = 0.0       # 图片质量
    config_completeness: float = 0.0 # 配置完整性
    naming_consistency: float = 0.0  # 命名一致性
    structure_compliance: float = 0.0 # 结构规范性
    
    @property
    def overall_score(self) -> float:
        """计算总体评分"""
        scores = [
            self.completeness_score,
            self.design_quality,
            self.usability_score,
            self.performance_score,
            self.accessibility_score
        ]
        valid_scores = [s for s in scores if s > 0]
        return sum(valid_scores) / len(valid_scores) if valid_scores else 0.0
    
    def get_grade(self) -> str:
        """获取等级评定"""
        score = self.overall_score
        if score >= 90:
            return "A+"
        elif score >= 80:
            return "A"
        elif score >= 70:
            return "B"
        elif score >= 60:
            return "C"
        else:
            return "D"


@dataclass
class TemplateMetadata:
    """模板元数据"""
    template_id: str
    
    # 文件信息
    file_info: Dict[str, Any] = field(default_factory=dict)
    
    # 图片分析结果
    image_analyses: Dict[str, ImageAnalysis] = field(default_factory=dict)
    
    # 设计特征
    design_features: DesignFeatures = field(default_factory=DesignFeatures)
    
    # 质量指标
    quality_metrics: QualityMetrics = field(default_factory=QualityMetrics)
    
    # 自动生成的标签和关键词
    generated_tags: List[str] = field(default_factory=list)
    generated_keywords: List[str] = field(default_factory=list)
    suggested_categories: List[str] = field(default_factory=list)
    
    # 元数据时间戳
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    analysis_version: str = "1.0"
    
    def add_image_analysis(self, image_path: str, analysis: ImageAnalysis):
        """添加图片分析结果"""
        self.image_analyses[image_path] = analysis
        self.updated_at = datetime.now()
    
    def get_image_analysis(self, image_path: str) -> Optional[ImageAnalysis]:
        """获取图片分析结果"""
        return self.image_analyses.get(image_path)
    
    def update_design_features(self, features: DesignFeatures):
        """更新设计特征"""
        self.design_features = features
        self.updated_at = datetime.now()
    
    def update_quality_metrics(self, metrics: QualityMetrics):
        """更新质量指标"""
        self.quality_metrics = metrics
        self.updated_at = datetime.now()
    
    def add_generated_tag(self, tag: str):
        """添加生成的标签"""
        if tag not in self.generated_tags:
            self.generated_tags.append(tag)
            self.updated_at = datetime.now()
    
    def add_generated_keyword(self, keyword: str):
        """添加生成的关键词"""
        if keyword not in self.generated_keywords:
            self.generated_keywords.append(keyword)
            self.updated_at = datetime.now()
    
    def suggest_category(self, category: str):
        """建议分类"""
        if category not in self.suggested_categories:
            self.suggested_categories.append(category)
            self.updated_at = datetime.now()
    
    def get_summary(self) -> Dict[str, Any]:
        """获取元数据摘要"""
        return {
            "template_id": self.template_id,
            "total_images": len(self.image_analyses),
            "design_style": self.design_features.style_category,
            "color_tone": self.design_features.color_tone,
            "overall_quality": self.quality_metrics.overall_score,
            "quality_grade": self.quality_metrics.get_grade(),
            "generated_tags_count": len(self.generated_tags),
            "generated_keywords_count": len(self.generated_keywords),
            "last_updated": self.updated_at.isoformat(),
            "analysis_version": self.analysis_version
        }
    
    def validate_image_dimensions(self, requirements: Dict[str, Tuple[int, int]]) -> List[str]:
        """验证图片尺寸"""
        errors = []
        
        for image_path, analysis in self.image_analyses.items():
            # 从路径推断格式类型
            if "desktop" in image_path:
                format_type = "desktop"
            elif "mobile" in image_path:
                format_type = "mobile"
            elif "preview" in image_path:
                format_type = "preview"
            else:
                continue
            
            if format_type in requirements:
                expected_width, expected_height = requirements[format_type]
                if not analysis.is_valid_dimensions(expected_width, expected_height):
                    errors.append(
                        f"{image_path}: 尺寸不符合要求 "
                        f"(实际: {analysis.width}x{analysis.height}, "
                        f"期望: {expected_width}x{expected_height})"
                    )
        
        return errors