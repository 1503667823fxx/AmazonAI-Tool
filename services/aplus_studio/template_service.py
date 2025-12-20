"""
A+ 模板管理服务
负责模板的加载、管理和AI处理
"""

import os
import json
from typing import Dict, List, Optional, Tuple, Any
from PIL import Image, ImageDraw, ImageFont
import io
import base64
from datetime import datetime
import uuid

from app_utils.aplus_studio.interfaces import ITemplateManager
from app_utils.aplus_studio.models.core_models import Template, Area, validate_template

class TemplateService(ITemplateManager):
    """A+ 模板管理服务 - 符合新设计规范的实现"""
    
    def __init__(self, templates_dir: str = "templates"):
        self.templates_dir = templates_dir
        self.config_file = os.path.join(templates_dir, "templates_config.json")
        self._templates_cache: Dict[str, Template] = {}
        self._load_templates()
    
    def _load_templates(self) -> None:
        """加载所有模板到缓存"""
        self._templates_cache.clear()
        
        # 加载配置文件
        config_data = self._load_config_file()
        
        # 转换为Template对象
        for template_id, template_data in config_data.get("templates", {}).items():
            try:
                template = self._convert_config_to_template(template_id, template_data)
                self._templates_cache[template_id] = template
            except Exception as e:
                print(f"警告: 加载模板 {template_id} 失败: {e}")
    
    def _load_config_file(self) -> Dict[str, Any]:
        """加载模板配置文件"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(f"警告: 配置文件加载失败: {e}")
                return self._create_default_config()
        else:
            # 创建默认配置并保存
            default_config = self._create_default_config()
            self._save_config_file(default_config)
            return default_config
    
    def _save_config_file(self, config_data: Dict[str, Any]) -> None:
        """保存配置文件"""
        os.makedirs(self.templates_dir, exist_ok=True)
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, ensure_ascii=False, indent=2)
        except IOError as e:
            print(f"错误: 配置文件保存失败: {e}")
    
    def _create_default_config(self) -> Dict[str, Any]:
        """创建默认模板配置"""
        return {
            "version": "1.0",
            "templates": {
                "tech_modern": {
                    "name": "科技现代风",
                    "category": "电子产品",
                    "description": "适合科技产品的现代简约风格",
                    "tags": ["科技", "现代", "简约", "电子"],
                    "keywords": ["科技", "现代", "电子产品", "数码"],
                    "holiday": None,
                    "season": None,
                    "style_attributes": {
                        "color_tone": "冷色调",
                        "layout": "网格布局",
                        "typography": "现代字体"
                    },
                    "color_schemes": ["蓝色科技", "黑白简约", "渐变炫彩"],
                    "sections": ["header", "features", "gallery", "specs"],
                    "replaceable_areas": {
                        "product_image": {
                            "x": 100, "y": 50, "width": 300, "height": 300,
                            "type": "image", "constraints": {"aspect_ratio": "1:1"}
                        },
                        "title_text": {
                            "x": 450, "y": 80, "width": 400, "height": 60,
                            "type": "text", "constraints": {"max_chars": 50}
                        },
                        "feature_1": {
                            "x": 450, "y": 160, "width": 400, "height": 40,
                            "type": "text", "constraints": {"max_chars": 100}
                        }
                    },
                    "metadata": {
                        "author": "system",
                        "version": "1.0",
                        "file_path": "tech_modern"
                    }
                },
                "beauty_elegant": {
                    "name": "美妆优雅风",
                    "category": "美妆护肤",
                    "description": "适合美妆护肤品的优雅风格",
                    "tags": ["美妆", "优雅", "护肤", "女性"],
                    "keywords": ["美妆", "护肤", "化妆品", "优雅"],
                    "holiday": None,
                    "season": None,
                    "style_attributes": {
                        "color_tone": "暖色调",
                        "layout": "流动布局",
                        "typography": "优雅字体"
                    },
                    "color_schemes": ["粉色浪漫", "金色奢华", "自然绿调"],
                    "sections": ["hero", "ingredients", "results", "usage"],
                    "replaceable_areas": {
                        "product_image": {
                            "x": 50, "y": 100, "width": 250, "height": 350,
                            "type": "image", "constraints": {"aspect_ratio": "5:7"}
                        },
                        "brand_logo": {
                            "x": 350, "y": 50, "width": 200, "height": 80,
                            "type": "logo", "constraints": {"format": "png"}
                        }
                    },
                    "metadata": {
                        "author": "system",
                        "version": "1.0",
                        "file_path": "beauty_elegant"
                    }
                }
            }
        }
    
    def _convert_config_to_template(self, template_id: str, config_data: Dict[str, Any]) -> Template:
        """将配置数据转换为Template对象"""
        # 转换可替换区域
        replaceable_areas = {}
        for area_name, area_data in config_data.get("replaceable_areas", {}).items():
            replaceable_areas[area_name] = Area(
                x=area_data["x"],
                y=area_data["y"],
                width=area_data["width"],
                height=area_data["height"],
                type=area_data["type"],
                constraints=area_data.get("constraints", {})
            )
        
        # 创建Template对象
        template = Template(
            id=template_id,
            name=config_data["name"],
            category=config_data["category"],
            description=config_data["description"],
            tags=config_data.get("tags", []),
            keywords=config_data.get("keywords", []),
            holiday=config_data.get("holiday"),
            season=config_data.get("season"),
            style_attributes=config_data.get("style_attributes", {}),
            color_schemes=config_data.get("color_schemes", []),
            sections=config_data.get("sections", []),
            replaceable_areas=replaceable_areas,
            metadata=config_data.get("metadata", {}),
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        return template
    
    def _convert_template_to_config(self, template: Template) -> Dict[str, Any]:
        """将Template对象转换为配置数据"""
        return {
            "name": template.name,
            "category": template.category,
            "description": template.description,
            "tags": template.tags,
            "keywords": template.keywords,
            "holiday": template.holiday,
            "season": template.season,
            "style_attributes": template.style_attributes,
            "color_schemes": template.color_schemes,
            "sections": template.sections,
            "replaceable_areas": {
                name: area.to_dict() for name, area in template.replaceable_areas.items()
            },
            "metadata": template.metadata
        }
    
    # ITemplateManager接口实现
    def load_template(self, template_id: str) -> Optional[Template]:
        """加载指定模板"""
        return self._templates_cache.get(template_id)
    
    def get_available_templates(self) -> List[Template]:
        """获取所有可用模板"""
        return list(self._templates_cache.values())
    
    def get_templates_by_category(self, category: str) -> List[Template]:
        """根据分类获取模板"""
        return [
            template for template in self._templates_cache.values()
            if template.category.lower() == category.lower()
        ]
    
    def save_template(self, template: Template) -> bool:
        """保存模板"""
        try:
            # 验证模板数据
            validation_errors = validate_template(template)
            if validation_errors:
                print(f"模板验证失败: {validation_errors}")
                return False
            
            # 更新缓存
            template.updated_at = datetime.now()
            self._templates_cache[template.id] = template
            
            # 保存到配置文件
            config_data = self._load_config_file()
            config_data["templates"][template.id] = self._convert_template_to_config(template)
            self._save_config_file(config_data)
            
            return True
        except Exception as e:
            print(f"保存模板失败: {e}")
            return False
    
    def delete_template(self, template_id: str) -> bool:
        """删除模板"""
        try:
            # 从缓存中删除
            if template_id in self._templates_cache:
                del self._templates_cache[template_id]
            
            # 从配置文件中删除
            config_data = self._load_config_file()
            if template_id in config_data.get("templates", {}):
                del config_data["templates"][template_id]
                self._save_config_file(config_data)
            
            # 删除模板文件夹（如果存在）
            template_dir = os.path.join(self.templates_dir, template_id)
            if os.path.exists(template_dir):
                import shutil
                shutil.rmtree(template_dir)
            
            return True
        except Exception as e:
            print(f"删除模板失败: {e}")
            return False
    
    # 扩展功能
    def create_template(self, name: str, category: str, description: str, **kwargs) -> Template:
        """创建新模板"""
        template_id = kwargs.get('template_id', str(uuid.uuid4()))
        
        template = Template(
            id=template_id,
            name=name,
            category=category,
            description=description,
            tags=kwargs.get('tags', []),
            keywords=kwargs.get('keywords', []),
            holiday=kwargs.get('holiday'),
            season=kwargs.get('season'),
            style_attributes=kwargs.get('style_attributes', {}),
            color_schemes=kwargs.get('color_schemes', []),
            sections=kwargs.get('sections', []),
            replaceable_areas=kwargs.get('replaceable_areas', {}),
            metadata=kwargs.get('metadata', {}),
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        return template
    
    def extract_template_metadata(self, template_path: str) -> Dict[str, Any]:
        """提取模板元数据"""
        metadata = {
            "file_path": template_path,
            "extracted_at": datetime.now().isoformat()
        }
        
        # 检查模板文件夹是否存在
        full_path = os.path.join(self.templates_dir, template_path)
        if os.path.exists(full_path):
            # 获取文件信息
            metadata["exists"] = True
            metadata["files"] = []
            
            try:
                for file_name in os.listdir(full_path):
                    file_path = os.path.join(full_path, file_name)
                    if os.path.isfile(file_path):
                        file_info = {
                            "name": file_name,
                            "size": os.path.getsize(file_path),
                            "modified": datetime.fromtimestamp(
                                os.path.getmtime(file_path)
                            ).isoformat()
                        }
                        
                        # 如果是图片文件，尝试获取尺寸信息
                        if file_name.lower().endswith(('.jpg', '.jpeg', '.png', '.gif')):
                            try:
                                with Image.open(file_path) as img:
                                    file_info["dimensions"] = {
                                        "width": img.width,
                                        "height": img.height
                                    }
                            except Exception:
                                pass
                        
                        metadata["files"].append(file_info)
            except Exception as e:
                metadata["error"] = f"读取文件夹失败: {e}"
        else:
            metadata["exists"] = False
        
        return metadata
    
    def get_template_statistics(self) -> Dict[str, Any]:
        """获取模板统计信息"""
        templates = self.get_available_templates()
        
        # 按分类统计
        category_stats = {}
        for template in templates:
            category = template.category
            if category not in category_stats:
                category_stats[category] = 0
            category_stats[category] += 1
        
        # 按标签统计
        tag_stats = {}
        for template in templates:
            for tag in template.tags:
                if tag not in tag_stats:
                    tag_stats[tag] = 0
                tag_stats[tag] += 1
        
        return {
            "total_templates": len(templates),
            "categories": category_stats,
            "tags": tag_stats,
            "last_updated": datetime.now().isoformat()
        }
    
    def reload_templates(self) -> None:
        """重新加载所有模板"""
        self._load_templates()