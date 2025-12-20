#!/usr/bin/env python3
"""
模板生成器
自动创建模板目录结构和基础文件
"""

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import asdict

from ..models.template import (
    Template, TemplateConfig, TemplateType, TemplateStatus,
    LayoutFormat, VisibilityRules, ColorScheme
)
from ..models.file_structure import FileStructure


class TemplateGenerator:
    """模板生成器"""
    
    def __init__(self, templates_root: Path):
        """初始化生成器
        
        Args:
            templates_root: 模板根目录路径
        """
        self.templates_root = Path(templates_root)
        self.config_root = self.templates_root / "config"
        
        # 标准目录结构
        self.required_directories = ["desktop", "mobile"]
        self.optional_directories = ["docs", "metadata", "assets"]
        
        # 标准文件
        self.required_files = {
            "template.json": "模板配置文件",
            "README.md": "模板说明文档",
            "preview.jpg": "预览缩略图"
        }
        
        # 标准图片尺寸
        self.image_dimensions = {
            "desktop": (1464, 600),
            "mobile": (600, 450),
            "preview": (300, 200)
        }
        
        # 标准模块名称
        self.standard_sections = [
            "header", "hero", "features", "gallery", "specs",
            "lifestyle", "ingredients", "results", "usage"
        ]
    
    def create_template(
        self,
        template_id: str,
        name: str,
        category: str,
        template_type: TemplateType = TemplateType.STANDARD,
        subcategory: Optional[str] = None,
        sections: Optional[List[str]] = None,
        **kwargs
    ) -> Template:
        """创建新模板
        
        Args:
            template_id: 模板ID
            name: 模板显示名称
            category: 主分类
            template_type: 模板类型
            subcategory: 子分类
            sections: 模板包含的模块列表
            **kwargs: 其他配置参数
            
        Returns:
            创建的模板对象
            
        Raises:
            FileExistsError: 模板已存在
            ValueError: 参数无效
        """
        # 验证参数
        self._validate_template_params(template_id, name, category)
        
        # 确定模板路径
        template_path = self._get_template_path(category, template_id, subcategory)
        
        # 检查模板是否已存在
        if template_path.exists():
            raise FileExistsError(f"模板已存在: {template_path}")
        
        # 创建目录结构
        self._create_directory_structure(template_path)
        
        # 生成配置文件
        config = self._generate_template_config(
            template_id, name, category, template_type,
            subcategory, sections, **kwargs
        )
        
        # 创建模板对象
        template = Template(
            id=template_id,
            name=name,
            category=category,
            template_type=template_type,
            status=TemplateStatus.DRAFT,
            config=config,
            root_path=template_path,
            created_by=kwargs.get("created_by", "system")
        )
        
        # 保存配置文件
        self._save_template_config(template_path, config)
        
        # 创建README文件
        self._create_readme_file(template_path, template)
        
        # 创建占位符图片文件说明
        self._create_placeholder_files(template_path, sections or [])
        
        return template
    
    def _validate_template_params(self, template_id: str, name: str, category: str):
        """验证模板参数"""
        if not template_id or not template_id.replace("_", "").replace("-", "").isalnum():
            raise ValueError(f"无效的模板ID: {template_id}")
        
        if not name or len(name.strip()) == 0:
            raise ValueError("模板名称不能为空")
        
        if not category or len(category.strip()) == 0:
            raise ValueError("模板分类不能为空")
    
    def _get_template_path(self, category: str, template_id: str, subcategory: Optional[str] = None) -> Path:
        """获取模板路径"""
        if subcategory:
            return self.templates_root / "by_category" / category / subcategory / template_id
        else:
            return self.templates_root / "by_category" / category / template_id
    
    def _create_directory_structure(self, template_path: Path):
        """创建目录结构"""
        # 创建根目录
        template_path.mkdir(parents=True, exist_ok=True)
        
        # 创建必需目录
        for directory in self.required_directories:
            (template_path / directory).mkdir(exist_ok=True)
        
        # 创建可选目录
        for directory in self.optional_directories:
            (template_path / directory).mkdir(exist_ok=True)
    
    def _generate_template_config(
        self,
        template_id: str,
        name: str,
        category: str,
        template_type: TemplateType,
        subcategory: Optional[str] = None,
        sections: Optional[List[str]] = None,
        **kwargs
    ) -> TemplateConfig:
        """生成模板配置"""
        # 默认模块
        if not sections:
            sections = ["hero", "features", "gallery", "specs"]
        
        # 创建配置对象
        config = TemplateConfig(
            id=template_id,
            name=name,
            version="1.0.0",
            category=category,
            template_type=template_type,
            status=TemplateStatus.DRAFT,
            description=kwargs.get("description", f"{name}模板"),
            subcategory=subcategory,
            tags=kwargs.get("tags", []),
            keywords=kwargs.get("keywords", []),
            sections=sections,
            style_attributes=kwargs.get("style_attributes", {}),
            color_schemes=self._get_default_color_schemes(),
            assets=self._generate_assets_config(sections),
            replaceable_areas=self._generate_replaceable_areas(sections),
            visibility_rules=VisibilityRules(),
            customization_options=kwargs.get("customization_options", {}),
            quality_metrics=kwargs.get("quality_metrics", {})
        )
        
        return config
    
    def _get_default_color_schemes(self) -> List[ColorScheme]:
        """获取默认配色方案"""
        return [
            ColorScheme(
                name="经典蓝",
                primary="#2196F3",
                secondary="#1976D2",
                accent="#03DAC6",
                description="专业稳重的蓝色系"
            ),
            ColorScheme(
                name="现代灰",
                primary="#37474F",
                secondary="#263238",
                accent="#FF5722",
                description="简约现代的灰色系"
            )
        ]
    
    def _generate_assets_config(self, sections: List[str]) -> Dict[str, Any]:
        """生成资源配置"""
        assets = {
            "preview": "preview.jpg",
            "desktop": {},
            "mobile": {}
        }
        
        # 为每个模块生成资源配置
        for section in sections:
            assets["desktop"][section] = f"desktop/{section}.jpg"
            assets["mobile"][section] = f"mobile/{section}.jpg"
        
        return assets
    
    def _generate_replaceable_areas(self, sections: List[str]) -> Dict[str, Dict[str, Any]]:
        """生成可替换区域配置"""
        replaceable_areas = {
            "desktop": {},
            "mobile": {}
        }
        
        # 桌面版标准区域
        desktop_areas = {
            "product_image": {
                "x": 200, "y": 100, "width": 400, "height": 400,
                "description": "主产品图片位置",
                "constraints": {"aspect_ratio": "1:1", "min_resolution": "400x400"}
            },
            "brand_logo": {
                "x": 100, "y": 50, "width": 200, "height": 80,
                "description": "品牌标志位置",
                "constraints": {"format": ["PNG", "SVG"], "transparent_bg": True}
            },
            "title_text": {
                "x": 700, "y": 150, "width": 600, "height": 100,
                "description": "产品标题文字",
                "constraints": {"max_length": 50, "font_size": "32-48px"}
            }
        }
        
        # 移动版标准区域
        mobile_areas = {
            "product_image": {
                "x": 100, "y": 50, "width": 200, "height": 200,
                "description": "主产品图片位置",
                "constraints": {"aspect_ratio": "1:1", "min_resolution": "200x200"}
            },
            "brand_logo": {
                "x": 50, "y": 20, "width": 120, "height": 40,
                "description": "品牌标志位置",
                "constraints": {"format": ["PNG", "SVG"], "transparent_bg": True}
            },
            "title_text": {
                "x": 320, "y": 80, "width": 250, "height": 60,
                "description": "产品标题文字",
                "constraints": {"max_length": 30, "font_size": "18-24px"}
            }
        }
        
        replaceable_areas["desktop"] = desktop_areas
        replaceable_areas["mobile"] = mobile_areas
        
        return replaceable_areas
    
    def _save_template_config(self, template_path: Path, config: TemplateConfig):
        """保存模板配置文件"""
        config_file = template_path / "template.json"
        
        # 转换为字典并处理特殊类型
        config_dict = self._config_to_dict(config)
        
        # 保存JSON文件
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config_dict, f, ensure_ascii=False, indent=2)
    
    def _config_to_dict(self, config: TemplateConfig) -> Dict[str, Any]:
        """将配置对象转换为字典"""
        config_dict = asdict(config)
        
        # 处理枚举类型
        config_dict["template_type"] = config.template_type.value
        config_dict["status"] = config.status.value
        
        # 处理日期时间
        if hasattr(config, 'created_at') and config_dict.get('created_at'):
            config_dict["created_at"] = config_dict["created_at"].isoformat()
        if hasattr(config, 'updated_at') and config_dict.get('updated_at'):
            config_dict["updated_at"] = config_dict["updated_at"].isoformat()
        
        # 添加元数据
        config_dict["metadata"] = {
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "created_by": "template_generator",
            "version_history": [
                {
                    "version": "1.0.0",
                    "date": datetime.now().isoformat(),
                    "changes": "初始版本创建"
                }
            ],
            "file_info": {
                "total_size": "0MB",
                "image_count": len(config.sections) * 2,  # desktop + mobile
                "asset_count": len(config.sections) * 2 + 1,  # + preview
                "config_size": "0KB"
            }
        }
        
        return config_dict
    
    def _create_readme_file(self, template_path: Path, template: Template):
        """创建README文件"""
        readme_content = f"""# {template.name}

## 模板信息

- **模板ID**: {template.id}
- **分类**: {template.category}
- **类型**: {template.template_type.value}
- **状态**: {template.status.value}
- **版本**: {template.config.version}

## 描述

{template.config.description}

## 模块结构

本模板包含以下模块:

"""
        
        for i, section in enumerate(template.config.sections, 1):
            readme_content += f"{i}. **{section}**: {section}模块\n"
        
        readme_content += f"""

## 文件结构

```
{template.id}/
├── template.json          # 模板配置文件
├── README.md             # 本文件
├── preview.jpg           # 预览缩略图 (300x200px)
├── desktop/              # 桌面版资源 (1464x600px)
"""
        
        for section in template.config.sections:
            readme_content += f"│   ├── {section}.jpg\n"
        
        readme_content += "├── mobile/               # 移动版资源 (600x450px)\n"
        
        for section in template.config.sections:
            readme_content += f"│   ├── {section}.jpg\n"
        
        readme_content += """├── docs/                 # 文档目录
├── metadata/             # 元数据目录
└── assets/               # 额外资源目录
```

## 使用说明

1. 将产品图片放置到对应的可替换区域
2. 根据需要调整文字内容和品牌标识
3. 确保图片尺寸符合规范要求

## 可替换区域

### 桌面版 (1464x600px)

- **产品图片**: 200x100, 400x400px
- **品牌标志**: 100x50, 200x80px  
- **标题文字**: 700x150, 600x100px

### 移动版 (600x450px)

- **产品图片**: 100x50, 200x200px
- **品牌标志**: 50x20, 120x40px
- **标题文字**: 320x80, 250x60px

## 注意事项

- 请确保所有图片文件符合指定尺寸要求
- 建议使用高质量的JPG格式图片
- 品牌标志建议使用PNG格式以支持透明背景

---

*此文件由模板生成器自动创建于 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""
        
        readme_file = template_path / "README.md"
        with open(readme_file, 'w', encoding='utf-8') as f:
            f.write(readme_content)
    
    def _create_placeholder_files(self, template_path: Path, sections: List[str]):
        """创建占位符文件说明"""
        # 创建桌面版占位符说明
        desktop_dir = template_path / "desktop"
        desktop_readme = desktop_dir / "README.md"
        
        desktop_content = f"""# 桌面版资源文件

## 图片规格要求

- **尺寸**: 1464x600 像素
- **格式**: JPG (推荐) 或 PNG
- **质量**: 高质量，建议90%以上压缩质量
- **文件大小**: 建议每个文件不超过500KB

## 需要的文件

"""
        
        for section in sections:
            desktop_content += f"- `{section}.jpg`: {section}模块图片\n"
        
        desktop_content += """

## 注意事项

1. 所有图片必须严格按照1464x600像素尺寸制作
2. 图片内容应该清晰、美观，符合模板设计风格
3. 文件命名必须与配置文件中的定义一致
4. 建议使用专业的图片编辑软件进行制作

---

*请将制作好的图片文件放置在此目录下*
"""
        
        with open(desktop_readme, 'w', encoding='utf-8') as f:
            f.write(desktop_content)
        
        # 创建移动版占位符说明
        mobile_dir = template_path / "mobile"
        mobile_readme = mobile_dir / "README.md"
        
        mobile_content = f"""# 移动版资源文件

## 图片规格要求

- **尺寸**: 600x450 像素
- **格式**: JPG (推荐) 或 PNG
- **质量**: 高质量，建议90%以上压缩质量
- **文件大小**: 建议每个文件不超过200KB

## 需要的文件

"""
        
        for section in sections:
            mobile_content += f"- `{section}.jpg`: {section}模块图片\n"
        
        mobile_content += """

## 注意事项

1. 所有图片必须严格按照600x450像素尺寸制作
2. 移动版设计应考虑小屏幕显示效果
3. 文字和图标应该足够大，确保在手机上清晰可见
4. 文件命名必须与配置文件中的定义一致

---

*请将制作好的图片文件放置在此目录下*
"""
        
        with open(mobile_readme, 'w', encoding='utf-8') as f:
            f.write(mobile_content)
        
        # 创建预览图说明
        preview_readme = template_path / "preview_requirements.md"
        preview_content = """# 预览图要求

## 规格要求

- **尺寸**: 300x200 像素
- **格式**: JPG
- **文件名**: preview.jpg
- **质量**: 高质量，建议90%以上压缩质量
- **文件大小**: 建议不超过50KB

## 设计要求

1. 预览图应该能够代表整个模板的设计风格
2. 建议使用模板中最具代表性的模块作为预览
3. 图片应该清晰、美观，能够吸引用户注意
4. 避免使用过于复杂的设计，确保在小尺寸下仍然清晰

## 制作建议

- 可以使用桌面版的某个模块按比例缩放制作
- 也可以创建专门的预览图设计
- 确保品牌标识和主要产品清晰可见
- 保持与整体模板风格的一致性

---

*制作完成后请将文件命名为 preview.jpg 并放置在模板根目录*
"""
        
        with open(preview_readme, 'w', encoding='utf-8') as f:
            f.write(preview_content)
    
    def get_template_structure(self, template_path: Path) -> FileStructure:
        """获取模板文件结构"""
        return FileStructure.from_directory(template_path)
    
    def validate_template_structure(self, template_path: Path) -> tuple[bool, List[str]]:
        """验证模板结构"""
        errors = []
        
        # 检查必需文件
        for filename in self.required_files:
            file_path = template_path / filename
            if not file_path.exists():
                errors.append(f"缺少必需文件: {filename}")
        
        # 检查必需目录
        for dirname in self.required_directories:
            dir_path = template_path / dirname
            if not dir_path.exists():
                errors.append(f"缺少必需目录: {dirname}")
        
        return len(errors) == 0, errors