"""
Core data models and enums for A+ Studio system.

This module defines the data structures used throughout the A+ image workflow system,
including product information, analysis results, generation parameters, and session data.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Dict, Optional, Any
from PIL import Image


class ModuleType(Enum):
    """A+ 模块类型枚举"""
    IDENTITY = "identity"      # 身份代入
    SENSORY = "sensory"        # 感官解构
    EXTENSION = "extension"    # 多维延展
    TRUST = "trust"           # 信任转化


class ValidationStatus(Enum):
    """验证状态枚举"""
    PENDING = "pending"
    PASSED = "passed"
    FAILED = "failed"
    NEEDS_REVIEW = "needs_review"


class GenerationStatus(Enum):
    """生成状态枚举"""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# Amazon A+ 规范常量
APLUS_IMAGE_SPECS = {
    "dimensions": (600, 450),
    "max_file_size": 5 * 1024 * 1024,  # 5MB
    "supported_formats": ["PNG", "JPG", "JPEG"],
    "min_resolution": 72,
    "color_space": "sRGB"
}


@dataclass
class ProductInfo:
    """产品基础信息"""
    name: str
    category: str
    description: str
    key_features: List[str]
    target_audience: str
    price_range: str
    uploaded_images: List[Any] = field(default_factory=list)  # PIL Images or file paths


@dataclass
class ListingAnalysis:
    """Listing分析结果"""
    product_category: str
    target_demographics: str
    key_selling_points: List[str]
    competitive_advantages: List[str]
    emotional_triggers: List[str]
    technical_specifications: Dict[str, str]
    confidence_score: float = 0.0


@dataclass
class ImageAnalysis:
    """图片分析结果"""
    dominant_colors: List[str]
    material_types: List[str]
    design_style: str
    lighting_conditions: str
    composition_elements: List[str]
    quality_assessment: str
    confidence_score: float = 0.0


@dataclass
class VisualStyle:
    """视觉风格定义"""
    color_palette: List[str]
    lighting_style: str
    composition_rules: List[str]
    aesthetic_direction: str
    consistency_guidelines: Dict[str, str]


@dataclass
class AnalysisResult:
    """完整分析结果"""
    listing_analysis: ListingAnalysis
    image_analysis: ImageAnalysis
    visual_style: VisualStyle
    analysis_timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ModulePrompt:
    """模块提示词"""
    module_type: ModuleType
    base_prompt: str
    style_modifiers: List[str]
    technical_requirements: List[str]
    aspect_ratio: str = "600x450"
    quality_settings: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GenerationResult:
    """生成结果"""
    module_type: ModuleType
    image_data: Optional[bytes]
    image_path: Optional[str]
    prompt_used: str
    generation_time: float
    quality_score: float
    validation_status: ValidationStatus
    metadata: Dict[str, Any] = field(default_factory=dict)
    generation_timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class APlusSession:
    """A+制作会话"""
    session_id: str
    product_info: Optional[ProductInfo]
    analysis_result: Optional[AnalysisResult]
    visual_style: Optional[VisualStyle]
    module_results: Dict[ModuleType, GenerationResult] = field(default_factory=dict)
    generation_status: Dict[ModuleType, GenerationStatus] = field(default_factory=dict)
    creation_time: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)


@dataclass
class GeminiConfig:
    """Gemini API配置"""
    api_key: str
    text_model: str = "gemini-1.5-pro"
    image_model: str = "gemini-1.5-pro-vision-latest"
    max_tokens: int = 4096
    temperature: float = 0.7
    timeout: int = 30


@dataclass
class ValidationResult:
    """验证结果"""
    is_valid: bool
    validation_status: ValidationStatus
    issues: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    quality_metrics: Dict[str, float] = field(default_factory=dict)


# Extension Module 特定数据结构
@dataclass
class CarouselSlide:
    """轮播图单张内容"""
    slide_type: str  # "lifestyle", "pain_point", "extreme_performance", "inside_out"
    title: str
    content_focus: str
    navigation_label: str
    prompt: str


@dataclass
class ExtensionPrompts:
    """多维延展模块的四张轮播图提示词"""
    lifestyle_slide: CarouselSlide
    pain_point_slide: CarouselSlide
    performance_slide: CarouselSlide
    inside_out_slide: CarouselSlide
    
    def get_all_slides(self) -> List[CarouselSlide]:
        """获取所有轮播图"""
        return [
            self.lifestyle_slide,
            self.pain_point_slide, 
            self.performance_slide,
            self.inside_out_slide
        ]


# 专业导航术语常量
PROFESSIONAL_NAVIGATION_TERMS = {
    "lifestyle": ["Field Tested", "Real World", "Daily Use", "Home Setup"],
    "pain_point": ["Problem Solved", "Smart Solution", "Pain Relief", "Better Way"],
    "performance": ["The Specs", "Performance", "Stress Test", "Built Tough"],
    "inside_out": ["Inside Look", "Crafted", "Quality Check", "Warranty"]
}