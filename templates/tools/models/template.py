"""
模板相关的核心数据模型
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
from pathlib import Path


class TemplateStatus(Enum):
    """模板状态枚举"""
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"
    UNDER_REVIEW = "under_review"


class TemplateType(Enum):
    """模板类型枚举"""
    STANDARD = "standard"
    MINIMAL = "minimal"
    PREMIUM = "premium"


@dataclass
class Area:
    """可替换区域定义"""
    x: int
    y: int
    width: int
    height: int
    description: str = ""
    constraints: Dict[str, Any] = field(default_factory=dict)


@dataclass
class VisibilityRules:
    """可见性规则"""
    environments: List[str] = field(default_factory=lambda: ["development", "production"])
    user_groups: List[str] = field(default_factory=lambda: ["all"])
    geographic_regions: List[str] = field(default_factory=lambda: ["global"])
    effective_date: Optional[datetime] = None
    expiry_date: Optional[datetime] = None
    feature_flags: List[str] = field(default_factory=list)


@dataclass
class ColorScheme:
    """配色方案"""
    name: str
    primary: str
    secondary: str
    accent: str
    description: str = ""


@dataclass
class LayoutFormat:
    """布局格式定义"""
    width: int
    height: int
    description: str = ""


@dataclass
class TemplateConfig:
    """模板配置数据模型"""
    id: str
    name: str
    version: str
    category: str
    template_type: TemplateType
    status: TemplateStatus
    description: str
    
    # 分类和标签
    subcategory: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    
    # 设计属性
    style_attributes: Dict[str, str] = field(default_factory=dict)
    sections: List[str] = field(default_factory=list)
    color_schemes: List[ColorScheme] = field(default_factory=list)
    
    # 布局和格式
    supported_formats: Dict[str, LayoutFormat] = field(default_factory=dict)
    replaceable_areas: Dict[str, Dict[str, Area]] = field(default_factory=dict)
    
    # 资源文件
    assets: Dict[str, Any] = field(default_factory=dict)
    
    # 可见性和发布规则
    visibility_rules: VisibilityRules = field(default_factory=VisibilityRules)
    
    # 定制选项
    customization_options: Dict[str, Any] = field(default_factory=dict)
    
    # 质量指标
    quality_metrics: Dict[str, float] = field(default_factory=dict)
    
    def __post_init__(self):
        """初始化后处理"""
        # 确保枚举类型正确
        if isinstance(self.template_type, str):
            self.template_type = TemplateType(self.template_type)
        if isinstance(self.status, str):
            self.status = TemplateStatus(self.status)
            
        # 设置默认的支持格式
        if not self.supported_formats:
            self.supported_formats = {
                "desktop": LayoutFormat(1464, 600, "桌面版A+页面标准尺寸"),
                "mobile": LayoutFormat(600, 450, "移动版A+页面标准尺寸")
            }


@dataclass
class Template:
    """模板主数据模型"""
    id: str
    name: str
    category: str
    template_type: TemplateType
    status: TemplateStatus
    config: TemplateConfig
    
    # 文件路径信息
    root_path: Path
    file_paths: Dict[str, str] = field(default_factory=dict)
    
    # 元数据
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    created_by: str = ""
    last_modified_by: str = ""
    
    # 版本信息
    version_history: List[Dict[str, Any]] = field(default_factory=list)
    
    # 使用统计
    usage_stats: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """初始化后处理"""
        # 确保枚举类型正确
        if isinstance(self.template_type, str):
            self.template_type = TemplateType(self.template_type)
        if isinstance(self.status, str):
            self.status = TemplateStatus(self.status)
            
        # 确保路径是Path对象
        if isinstance(self.root_path, str):
            self.root_path = Path(self.root_path)
    
    @property
    def is_published(self) -> bool:
        """检查模板是否已发布"""
        return self.status == TemplateStatus.PUBLISHED
    
    @property
    def is_draft(self) -> bool:
        """检查模板是否为草稿状态"""
        return self.status == TemplateStatus.DRAFT
    
    def get_asset_path(self, asset_type: str, format_type: str = "desktop") -> Optional[Path]:
        """获取资源文件路径"""
        if format_type in self.config.assets and asset_type in self.config.assets[format_type]:
            return self.root_path / self.config.assets[format_type][asset_type]
        return None
    
    def update_timestamp(self, user: str = ""):
        """更新时间戳"""
        self.updated_at = datetime.now()
        if user:
            self.last_modified_by = user
    
    def add_version_entry(self, version: str, changes: str, user: str = ""):
        """添加版本历史记录"""
        entry = {
            "version": version,
            "date": datetime.now().isoformat(),
            "changes": changes,
            "user": user
        }
        self.version_history.append(entry)
        self.config.version = version
        self.update_timestamp(user)