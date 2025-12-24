"""
Core data models and enums for A+ Studio system.

This module defines the data structures used throughout the A+ image workflow system,
including product information, analysis results, generation parameters, and session data.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Dict, Optional, Any, Union
from PIL import Image


class ModuleType(Enum):
    """A+ 模块类型枚举 - 新的12个专业模块"""
    # 原有4个模块（保持向后兼容）
    IDENTITY = "identity"      # 身份代入
    SENSORY = "sensory"        # 感官解构
    EXTENSION = "extension"    # 多维延展
    TRUST = "trust"           # 信任转化
    
    # 新增12个专业模块
    PRODUCT_OVERVIEW = "product_overview"        # 产品概览
    PROBLEM_SOLUTION = "problem_solution"        # 问题解决
    FEATURE_ANALYSIS = "feature_analysis"        # 功能解析
    SPECIFICATION_COMPARISON = "specification_comparison"  # 规格对比
    USAGE_SCENARIOS = "usage_scenarios"          # 使用场景
    INSTALLATION_GUIDE = "installation_guide"   # 安装指南
    SIZE_COMPATIBILITY = "size_compatibility"   # 尺寸兼容
    MAINTENANCE_CARE = "maintenance_care"        # 维护保养
    MATERIAL_CRAFTSMANSHIP = "material_craftsmanship"  # 材质工艺
    QUALITY_ASSURANCE = "quality_assurance"     # 品质保证
    CUSTOMER_REVIEWS = "customer_reviews"       # 用户评价
    PACKAGE_CONTENTS = "package_contents"       # 包装内容


class MaterialType(Enum):
    """素材类型枚举"""
    IMAGE = "image"
    DOCUMENT = "document"
    TEXT = "text"
    CUSTOM_PROMPT = "custom_prompt"


class MaterialPriority(Enum):
    """素材优先级枚举"""
    REQUIRED = "required"      # 必需 (红色)
    RECOMMENDED = "recommended"  # 推荐 (黄色)
    AI_GENERATED = "ai_generated"  # AI生成 (绿色)


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


class ComplianceStatus(Enum):
    """亚马逊A+合规状态枚举"""
    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    NEEDS_OPTIMIZATION = "needs_optimization"
    PENDING_REVIEW = "pending_review"


# Amazon A+ 规范常量
APLUS_IMAGE_SPECS = {
    "dimensions": (600, 450),
    "max_file_size": 5 * 1024 * 1024,  # 5MB
    "supported_formats": ["PNG", "JPG", "JPEG"],
    "min_resolution": 72,
    "color_space": "sRGB"
}


@dataclass
class MaterialRequirement:
    """单个素材需求"""
    material_type: MaterialType
    priority: MaterialPriority
    description: str
    examples: List[str] = field(default_factory=list)
    file_formats: List[str] = field(default_factory=list)
    max_file_size: Optional[int] = None  # bytes
    tooltip: Optional[str] = None


@dataclass
class MaterialRequirements:
    """模块素材需求集合"""
    module_type: ModuleType
    requirements: List[MaterialRequirement]
    
    def get_required_materials(self) -> List[MaterialRequirement]:
        """获取必需素材"""
        return [req for req in self.requirements if req.priority == MaterialPriority.REQUIRED]
    
    def get_recommended_materials(self) -> List[MaterialRequirement]:
        """获取推荐素材"""
        return [req for req in self.requirements if req.priority == MaterialPriority.RECOMMENDED]


@dataclass
class UploadedFile:
    """上传文件信息"""
    filename: str
    file_type: MaterialType
    file_size: int
    content: Union[bytes, str, Image.Image]
    upload_timestamp: datetime = field(default_factory=datetime.now)
    validation_status: ValidationStatus = ValidationStatus.PENDING


@dataclass
class MaterialSet:
    """用户上传的素材集合"""
    images: List[UploadedFile] = field(default_factory=list)
    documents: List[UploadedFile] = field(default_factory=list)
    text_inputs: Dict[str, str] = field(default_factory=dict)
    custom_prompts: Dict[str, str] = field(default_factory=dict)
    
    def get_total_file_size(self) -> int:
        """获取总文件大小"""
        total_size = 0
        for file in self.images + self.documents:
            total_size += file.file_size
        return total_size
    
    def get_files_by_type(self, material_type: MaterialType) -> List[UploadedFile]:
        """按类型获取文件"""
        if material_type == MaterialType.IMAGE:
            return self.images
        elif material_type == MaterialType.DOCUMENT:
            return self.documents
        return []


@dataclass
class ModuleInfo:
    """模块信息和元数据"""
    module_type: ModuleType
    name: str
    description: str
    category: str
    recommended_use_cases: List[str]
    material_requirements: MaterialRequirements
    estimated_generation_time: int = 60  # seconds
    complexity_level: str = "medium"  # low, medium, high
    
    def get_display_name(self) -> str:
        """获取显示名称"""
        display_names = {
            ModuleType.PRODUCT_OVERVIEW: "产品概览",
            ModuleType.PROBLEM_SOLUTION: "问题解决", 
            ModuleType.FEATURE_ANALYSIS: "功能解析",
            ModuleType.SPECIFICATION_COMPARISON: "规格对比",
            ModuleType.USAGE_SCENARIOS: "使用场景",
            ModuleType.INSTALLATION_GUIDE: "安装指南",
            ModuleType.SIZE_COMPATIBILITY: "尺寸兼容",
            ModuleType.MAINTENANCE_CARE: "维护保养",
            ModuleType.MATERIAL_CRAFTSMANSHIP: "材质工艺",
            ModuleType.QUALITY_ASSURANCE: "品质保证",
            ModuleType.CUSTOMER_REVIEWS: "用户评价",
            ModuleType.PACKAGE_CONTENTS: "包装内容",
            # 保持向后兼容
            ModuleType.IDENTITY: "身份代入",
            ModuleType.SENSORY: "感官解构",
            ModuleType.EXTENSION: "多维延展",
            ModuleType.TRUST: "信任转化"
        }
        return display_names.get(self.module_type, self.name)


@dataclass
class GenerationConfig:
    """生成配置参数"""
    selected_modules: List[ModuleType]
    language: str = "zh"
    style_preferences: Dict[str, Any] = field(default_factory=dict)
    compliance_level: str = "strict"  # strict, moderate, lenient
    batch_mode: bool = False
    quality_threshold: float = 0.8
    timeout_seconds: int = 120
    retry_attempts: int = 3
    preserve_visual_consistency: bool = True


@dataclass
class GeneratedModule:
    """生成的模块结果（新版本）"""
    module_type: ModuleType
    image_data: Optional[bytes]
    image_path: Optional[str]
    metadata: Dict[str, Any] = field(default_factory=dict)
    compliance_status: ComplianceStatus = ComplianceStatus.PENDING_REVIEW
    generation_timestamp: datetime = field(default_factory=datetime.now)
    materials_used: Optional[MaterialSet] = None
    quality_score: float = 0.0
    validation_status: ValidationStatus = ValidationStatus.PENDING
    prompt_used: str = ""
    generation_time: float = 0.0
    
    def is_compliant(self) -> bool:
        """检查是否符合A+规范"""
        return self.compliance_status == ComplianceStatus.COMPLIANT


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
    product_info: Optional[ProductInfo] = None  # 添加产品信息字段
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
    """A+制作会话 - 更新以支持新模块系统"""
    session_id: str
    product_info: Optional[ProductInfo]
    analysis_result: Optional[AnalysisResult]
    visual_style: Optional[VisualStyle]
    # 保持向后兼容的字段
    module_results: Dict[ModuleType, GenerationResult] = field(default_factory=dict)
    generation_status: Dict[ModuleType, GenerationStatus] = field(default_factory=dict)
    # 新增字段
    selected_modules: List[ModuleType] = field(default_factory=list)
    material_sets: Dict[ModuleType, MaterialSet] = field(default_factory=dict)
    generation_config: Optional[GenerationConfig] = None
    batch_generation_progress: Dict[str, Any] = field(default_factory=dict)
    creation_time: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        """初始化默认状态"""
        # 确保所有模块都有状态
        all_modules = list(ModuleType)
        for module_type in all_modules:
            if module_type not in self.generation_status:
                self.generation_status[module_type] = GenerationStatus.NOT_STARTED
    
    def get_selected_module_count(self) -> int:
        """获取选中的模块数量"""
        return len(self.selected_modules)
    
    def get_completed_modules(self) -> List[ModuleType]:
        """获取已完成的模块"""
        return [
            module_type for module_type, status in self.generation_status.items()
            if status == GenerationStatus.COMPLETED
        ]
    
    def get_progress_percentage(self) -> float:
        """获取整体进度百分比"""
        if not self.selected_modules:
            return 0.0
        completed = len([
            m for m in self.selected_modules 
            if self.generation_status.get(m) == GenerationStatus.COMPLETED
        ])
        return (completed / len(self.selected_modules)) * 100


@dataclass
class GeminiConfig:
    """Gemini API配置"""
    api_key: str
    text_model: str = "models/gemini-3-pro-preview"
    image_model: str = "models/gemini-3-pro-image-preview"
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

# 新模块的默认配置
DEFAULT_MODULE_CONFIGS = {
    ModuleType.PRODUCT_OVERVIEW: {
        "focus": "hero_showcase",
        "layout": "large_product_with_features",
        "emphasis": "key_selling_points"
    },
    ModuleType.PROBLEM_SOLUTION: {
        "format": "before_after_comparison",
        "visual_style": "problem_solution_arrows",
        "emphasis": "pain_point_resolution"
    },
    ModuleType.FEATURE_ANALYSIS: {
        "format": "technical_diagram",
        "annotation_style": "callouts_and_labels",
        "complexity": "detailed_breakdown"
    },
    ModuleType.SPECIFICATION_COMPARISON: {
        "format": "comparison_table",
        "highlight_style": "superior_specs",
        "include_charts": True
    },
    ModuleType.USAGE_SCENARIOS: {
        "format": "multi_panel_scenarios",
        "focus": "practical_applications",
        "avoid_lifestyle": True
    },
    ModuleType.INSTALLATION_GUIDE: {
        "format": "step_by_step_visual",
        "include_tools": True,
        "safety_warnings": True
    },
    ModuleType.SIZE_COMPATIBILITY: {
        "format": "dimension_charts",
        "include_scale": True,
        "measurement_units": "both"
    },
    ModuleType.MAINTENANCE_CARE: {
        "format": "care_instructions",
        "include_products": True,
        "visual_demonstrations": True
    },
    ModuleType.MATERIAL_CRAFTSMANSHIP: {
        "format": "material_closeups",
        "focus": "quality_details",
        "construction_highlights": True
    },
    ModuleType.QUALITY_ASSURANCE: {
        "format": "certification_display",
        "include_badges": True,
        "trust_indicators": True
    },
    ModuleType.CUSTOMER_REVIEWS: {
        "format": "review_showcase",
        "include_photos": True,
        "rating_display": True
    },
    ModuleType.PACKAGE_CONTENTS: {
        "format": "unboxing_display",
        "item_labeling": True,
        "value_emphasis": True
    }
}


def get_module_info_by_type(module_type: ModuleType) -> ModuleInfo:
    """根据模块类型获取模块信息"""
    # 这里可以实现从配置文件或数据库加载模块信息的逻辑
    # 暂时返回基本信息
    return ModuleInfo(
        module_type=module_type,
        name=module_type.value,
        description=f"{module_type.value} module description",
        category="professional",
        recommended_use_cases=[],
        material_requirements=MaterialRequirements(
            module_type=module_type,
            requirements=[]
        )
    )


def get_all_available_modules() -> List[ModuleInfo]:
    """获取所有可用模块信息"""
    return [get_module_info_by_type(module_type) for module_type in ModuleType]


def is_legacy_module(module_type: ModuleType) -> bool:
    """检查是否为旧版模块"""
    legacy_modules = {ModuleType.IDENTITY, ModuleType.SENSORY, ModuleType.EXTENSION, ModuleType.TRUST}
    return module_type in legacy_modules


def get_new_professional_modules() -> List[ModuleType]:
    """获取新的12个专业模块"""
    return [
        ModuleType.PRODUCT_OVERVIEW,
        ModuleType.PROBLEM_SOLUTION,
        ModuleType.FEATURE_ANALYSIS,
        ModuleType.SPECIFICATION_COMPARISON,
        ModuleType.USAGE_SCENARIOS,
        ModuleType.INSTALLATION_GUIDE,
        ModuleType.SIZE_COMPATIBILITY,
        ModuleType.MAINTENANCE_CARE,
        ModuleType.MATERIAL_CRAFTSMANSHIP,
        ModuleType.QUALITY_ASSURANCE,
        ModuleType.CUSTOMER_REVIEWS,
        ModuleType.PACKAGE_CONTENTS
    ]