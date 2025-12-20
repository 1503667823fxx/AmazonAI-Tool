"""
A+Studio核心数据模型
定义系统中使用的核心数据结构
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from enum import Enum
import json


class WorkflowStatus(Enum):
    """工作流状态枚举"""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Area:
    """可替换区域定义"""
    x: int
    y: int
    width: int
    height: int
    type: str  # "image", "text", "logo"
    constraints: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "type": self.type,
            "constraints": self.constraints
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Area':
        """从字典创建实例"""
        return cls(
            x=data["x"],
            y=data["y"],
            width=data["width"],
            height=data["height"],
            type=data["type"],
            constraints=data.get("constraints", {})
        )


@dataclass
class Template:
    """模板数据模型"""
    id: str
    name: str
    category: str
    description: str
    tags: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    holiday: Optional[str] = None
    season: Optional[str] = None
    style_attributes: Dict[str, str] = field(default_factory=dict)
    color_schemes: List[str] = field(default_factory=list)
    sections: List[str] = field(default_factory=list)
    replaceable_areas: Dict[str, Area] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "description": self.description,
            "tags": self.tags,
            "keywords": self.keywords,
            "holiday": self.holiday,
            "season": self.season,
            "style_attributes": self.style_attributes,
            "color_schemes": self.color_schemes,
            "sections": self.sections,
            "replaceable_areas": {k: v.to_dict() for k, v in self.replaceable_areas.items()},
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Template':
        """从字典创建实例"""
        replaceable_areas = {}
        for k, v in data.get("replaceable_areas", {}).items():
            replaceable_areas[k] = Area.from_dict(v)
        
        return cls(
            id=data["id"],
            name=data["name"],
            category=data["category"],
            description=data["description"],
            tags=data.get("tags", []),
            keywords=data.get("keywords", []),
            holiday=data.get("holiday"),
            season=data.get("season"),
            style_attributes=data.get("style_attributes", {}),
            color_schemes=data.get("color_schemes", []),
            sections=data.get("sections", []),
            replaceable_areas=replaceable_areas,
            metadata=data.get("metadata", {}),
            created_at=datetime.fromisoformat(data.get("created_at", datetime.now().isoformat())),
            updated_at=datetime.fromisoformat(data.get("updated_at", datetime.now().isoformat()))
        )


@dataclass
class UploadedFile:
    """上传文件数据模型"""
    filename: str
    content_type: str
    size: int
    data: bytes
    upload_time: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（不包含二进制数据）"""
        return {
            "filename": self.filename,
            "content_type": self.content_type,
            "size": self.size,
            "upload_time": self.upload_time.isoformat()
        }


@dataclass
class ProductData:
    """产品数据模型"""
    name: str
    category: str
    features: List[str]
    brand_name: str
    brand_color: str
    images: List[UploadedFile] = field(default_factory=list)
    additional_info: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "category": self.category,
            "features": self.features,
            "brand_name": self.brand_name,
            "brand_color": self.brand_color,
            "images": [img.to_dict() for img in self.images],
            "additional_info": self.additional_info
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProductData':
        """从字典创建实例"""
        images = []
        for img_data in data.get("images", []):
            # 注意：这里不包含二进制数据的重建
            images.append(UploadedFile(
                filename=img_data["filename"],
                content_type=img_data["content_type"],
                size=img_data["size"],
                data=b"",  # 空数据，实际使用时需要从存储中加载
                upload_time=datetime.fromisoformat(img_data["upload_time"])
            ))
        
        return cls(
            name=data["name"],
            category=data["category"],
            features=data["features"],
            brand_name=data["brand_name"],
            brand_color=data["brand_color"],
            images=images,
            additional_info=data.get("additional_info", {})
        )


@dataclass
class WorkflowSession:
    """工作流会话数据模型"""
    session_id: str
    user_id: str
    template_id: str
    current_step: int
    total_steps: int
    step_data: Dict[str, Any] = field(default_factory=dict)
    product_data: Optional[ProductData] = None
    customization_options: Dict[str, Any] = field(default_factory=dict)
    status: WorkflowStatus = WorkflowStatus.NOT_STARTED
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "template_id": self.template_id,
            "current_step": self.current_step,
            "total_steps": self.total_steps,
            "step_data": self.step_data,
            "product_data": self.product_data.to_dict() if self.product_data else None,
            "customization_options": self.customization_options,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WorkflowSession':
        """从字典创建实例"""
        product_data = None
        if data.get("product_data"):
            product_data = ProductData.from_dict(data["product_data"])
        
        return cls(
            session_id=data["session_id"],
            user_id=data["user_id"],
            template_id=data["template_id"],
            current_step=data["current_step"],
            total_steps=data["total_steps"],
            step_data=data.get("step_data", {}),
            product_data=product_data,
            customization_options=data.get("customization_options", {}),
            status=WorkflowStatus(data.get("status", WorkflowStatus.NOT_STARTED.value)),
            created_at=datetime.fromisoformat(data.get("created_at", datetime.now().isoformat())),
            updated_at=datetime.fromisoformat(data.get("updated_at", datetime.now().isoformat()))
        )


@dataclass
class Category:
    """分类数据模型"""
    id: str
    name: str
    parent_id: Optional[str] = None
    level: int = 0
    description: str = ""
    tags: List[str] = field(default_factory=list)
    template_count: int = 0
    subcategories: List['Category'] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "parent_id": self.parent_id,
            "level": self.level,
            "description": self.description,
            "tags": self.tags,
            "template_count": self.template_count,
            "subcategories": [sub.to_dict() for sub in self.subcategories],
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Category':
        """从字典创建实例"""
        subcategories = []
        for sub_data in data.get("subcategories", []):
            subcategories.append(cls.from_dict(sub_data))
        
        return cls(
            id=data["id"],
            name=data["name"],
            parent_id=data.get("parent_id"),
            level=data.get("level", 0),
            description=data.get("description", ""),
            tags=data.get("tags", []),
            template_count=data.get("template_count", 0),
            subcategories=subcategories,
            metadata=data.get("metadata", {})
        )


# 数据验证函数
def validate_template(template: Template) -> List[str]:
    """验证模板数据"""
    errors = []
    
    # 基本字段验证
    if not template.id or not isinstance(template.id, str):
        errors.append("模板ID不能为空且必须是字符串")
    
    if not template.name or not isinstance(template.name, str):
        errors.append("模板名称不能为空且必须是字符串")
    
    if not template.category or not isinstance(template.category, str):
        errors.append("模板分类不能为空且必须是字符串")
    
    if not template.sections or not isinstance(template.sections, list):
        errors.append("模板必须包含至少一个部分且必须是列表")
    
    # 类型验证
    if not isinstance(template.tags, list):
        errors.append("标签必须是列表")
    
    if not isinstance(template.keywords, list):
        errors.append("关键词必须是列表")
    
    if not isinstance(template.style_attributes, dict):
        errors.append("样式属性必须是字典")
    
    if not isinstance(template.color_schemes, list):
        errors.append("色彩方案必须是列表")
    
    if not isinstance(template.replaceable_areas, dict):
        errors.append("可替换区域必须是字典")
    
    if not isinstance(template.metadata, dict):
        errors.append("元数据必须是字典")
    
    # 可替换区域验证
    for area_name, area in template.replaceable_areas.items():
        if not isinstance(area, Area):
            errors.append(f"可替换区域 '{area_name}' 必须是Area类型")
            continue
        
        if area.width <= 0 or area.height <= 0:
            errors.append(f"可替换区域 '{area_name}' 的宽度和高度必须大于0")
        
        if area.type not in ["image", "text", "logo"]:
            errors.append(f"可替换区域 '{area_name}' 的类型必须是 'image', 'text' 或 'logo'")
    
    # 日期验证
    if not isinstance(template.created_at, datetime):
        errors.append("创建时间必须是datetime类型")
    
    if not isinstance(template.updated_at, datetime):
        errors.append("更新时间必须是datetime类型")
    
    return errors


def validate_product_data(product_data: ProductData) -> List[str]:
    """验证产品数据"""
    errors = []
    
    # 基本字段验证
    if not product_data.name or not isinstance(product_data.name, str):
        errors.append("产品名称不能为空且必须是字符串")
    
    if not product_data.category or not isinstance(product_data.category, str):
        errors.append("产品分类不能为空且必须是字符串")
    
    if not product_data.features or not isinstance(product_data.features, list):
        errors.append("产品特性不能为空且必须是列表")
    
    if not product_data.brand_name or not isinstance(product_data.brand_name, str):
        errors.append("品牌名称不能为空且必须是字符串")
    
    if not product_data.brand_color or not isinstance(product_data.brand_color, str):
        errors.append("品牌颜色不能为空且必须是字符串")
    
    # 类型验证
    if not isinstance(product_data.images, list):
        errors.append("图片列表必须是列表")
    
    if not isinstance(product_data.additional_info, dict):
        errors.append("附加信息必须是字典")
    
    # 图片验证
    for i, image in enumerate(product_data.images):
        if not isinstance(image, UploadedFile):
            errors.append(f"图片 {i+1} 必须是UploadedFile类型")
    
    # 品牌颜色格式验证（简单的十六进制颜色检查）
    if product_data.brand_color and not product_data.brand_color.startswith('#'):
        errors.append("品牌颜色必须是十六进制格式（以#开头）")
    
    return errors


def validate_workflow_session(session: WorkflowSession) -> List[str]:
    """验证工作流会话数据"""
    errors = []
    
    # 基本字段验证
    if not session.session_id or not isinstance(session.session_id, str):
        errors.append("会话ID不能为空且必须是字符串")
    
    if not session.user_id or not isinstance(session.user_id, str):
        errors.append("用户ID不能为空且必须是字符串")
    
    if not session.template_id or not isinstance(session.template_id, str):
        errors.append("模板ID不能为空且必须是字符串")
    
    # 步骤验证
    if not isinstance(session.current_step, int):
        errors.append("当前步骤必须是整数")
    elif session.current_step < 0 or session.current_step > session.total_steps:
        errors.append("当前步骤数无效")
    
    if not isinstance(session.total_steps, int):
        errors.append("总步骤数必须是整数")
    elif session.total_steps <= 0:
        errors.append("总步骤数必须大于0")
    
    # 类型验证
    if not isinstance(session.step_data, dict):
        errors.append("步骤数据必须是字典")
    
    if not isinstance(session.customization_options, dict):
        errors.append("自定义选项必须是字典")
    
    if not isinstance(session.status, WorkflowStatus):
        errors.append("状态必须是WorkflowStatus枚举类型")
    
    # 产品数据验证
    if session.product_data is not None:
        if not isinstance(session.product_data, ProductData):
            errors.append("产品数据必须是ProductData类型")
        else:
            # 递归验证产品数据
            product_errors = validate_product_data(session.product_data)
            errors.extend([f"产品数据: {error}" for error in product_errors])
    
    # 日期验证
    if not isinstance(session.created_at, datetime):
        errors.append("创建时间必须是datetime类型")
    
    if not isinstance(session.updated_at, datetime):
        errors.append("更新时间必须是datetime类型")
    
    return errors


def validate_category(category: Category) -> List[str]:
    """验证分类数据"""
    errors = []
    
    # 基本字段验证
    if not category.id or not isinstance(category.id, str):
        errors.append("分类ID不能为空且必须是字符串")
    
    if not category.name or not isinstance(category.name, str):
        errors.append("分类名称不能为空且必须是字符串")
    
    # 类型验证
    if category.parent_id is not None and not isinstance(category.parent_id, str):
        errors.append("父分类ID必须是字符串或None")
    
    if not isinstance(category.level, int):
        errors.append("分类级别必须是整数")
    elif category.level < 0:
        errors.append("分类级别不能为负数")
    
    if not isinstance(category.description, str):
        errors.append("分类描述必须是字符串")
    
    if not isinstance(category.tags, list):
        errors.append("标签必须是列表")
    
    if not isinstance(category.template_count, int):
        errors.append("模板数量必须是整数")
    elif category.template_count < 0:
        errors.append("模板数量不能为负数")
    
    if not isinstance(category.subcategories, list):
        errors.append("子分类必须是列表")
    
    if not isinstance(category.metadata, dict):
        errors.append("元数据必须是字典")
    
    # 子分类验证
    for i, subcategory in enumerate(category.subcategories):
        if not isinstance(subcategory, Category):
            errors.append(f"子分类 {i+1} 必须是Category类型")
        else:
            # 递归验证子分类
            sub_errors = validate_category(subcategory)
            errors.extend([f"子分类 {i+1}: {error}" for error in sub_errors])
    
    return errors


def validate_uploaded_file(file: UploadedFile) -> List[str]:
    """验证上传文件数据"""
    errors = []
    
    # 基本字段验证
    if not file.filename or not isinstance(file.filename, str):
        errors.append("文件名不能为空且必须是字符串")
    
    if not file.content_type or not isinstance(file.content_type, str):
        errors.append("内容类型不能为空且必须是字符串")
    
    if not isinstance(file.size, int):
        errors.append("文件大小必须是整数")
    elif file.size <= 0:
        errors.append("文件大小必须大于0")
    
    if not isinstance(file.data, bytes):
        errors.append("文件数据必须是bytes类型")
    
    if not isinstance(file.upload_time, datetime):
        errors.append("上传时间必须是datetime类型")
    
    # 文件名格式验证
    if '/' in file.filename or '\\' in file.filename:
        errors.append("文件名不能包含路径分隔符")
    
    # 内容类型验证
    supported_types = ["image/jpeg", "image/png", "image/gif", "image/webp"]
    if file.content_type not in supported_types:
        errors.append(f"不支持的文件类型: {file.content_type}")
    
    return errors


def validate_area(area: Area) -> List[str]:
    """验证区域数据"""
    errors = []
    
    # 坐标和尺寸验证
    if not isinstance(area.x, int):
        errors.append("X坐标必须是整数")
    elif area.x < 0:
        errors.append("X坐标不能为负数")
    
    if not isinstance(area.y, int):
        errors.append("Y坐标必须是整数")
    elif area.y < 0:
        errors.append("Y坐标不能为负数")
    
    if not isinstance(area.width, int):
        errors.append("宽度必须是整数")
    elif area.width <= 0:
        errors.append("宽度必须大于0")
    
    if not isinstance(area.height, int):
        errors.append("高度必须是整数")
    elif area.height <= 0:
        errors.append("高度必须大于0")
    
    # 类型验证
    if not isinstance(area.type, str):
        errors.append("区域类型必须是字符串")
    elif area.type not in ["image", "text", "logo"]:
        errors.append("区域类型必须是 'image', 'text' 或 'logo'")
    
    if not isinstance(area.constraints, dict):
        errors.append("约束条件必须是字典")
    
    return errors