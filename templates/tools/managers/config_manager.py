#!/usr/bin/env python3
"""
配置管理器
负责模板配置文件的生成、更新、验证和合并
"""

import json
import yaml
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from dataclasses import asdict
import jsonschema
from jsonschema import validate, ValidationError

from ..models.template import TemplateConfig, TemplateType, TemplateStatus, ColorScheme
from ..models.metadata import TemplateMetadata


class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_root: Path, schema_path: Optional[Path] = None):
        """初始化配置管理器
        
        Args:
            config_root: 配置根目录
            schema_path: JSON Schema文件路径
        """
        self.config_root = Path(config_root)
        self.schema_path = schema_path or self.config_root / "schemas" / "template_config_schema.json"
        self.schema = self._load_schema()
        
        # 配置文件路径
        self.categories_config = self.config_root / "categories.yaml"
        self.template_types_config = self.config_root / "template_types.yaml"
        self.validation_rules_config = self.config_root / "validation_rules.yaml"
        self.global_settings_config = self.config_root / "global_settings.yaml"
    
    def _load_schema(self) -> Dict[str, Any]:
        """加载JSON Schema"""
        try:
            if self.schema_path.exists():
                with open(self.schema_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            pass
        
        # 返回默认schema
        return self._get_default_schema()
    
    def _get_default_schema(self) -> Dict[str, Any]:
        """获取默认JSON Schema"""
        return {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "required": ["id", "name", "category", "template_type", "status", "version"],
            "properties": {
                "id": {
                    "type": "string",
                    "pattern": "^[a-z0-9_-]+$",
                    "minLength": 1,
                    "maxLength": 50
                },
                "name": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": 100
                },
                "category": {
                    "type": "string",
                    "minLength": 1
                },
                "template_type": {
                    "type": "string",
                    "enum": ["standard", "premium", "minimal"]
                },
                "status": {
                    "type": "string",
                    "enum": ["draft", "published", "archived", "under_review"]
                },
                "version": {
                    "type": "string",
                    "pattern": "^\\d+\\.\\d+\\.\\d+$"
                },
                "description": {
                    "type": "string"
                },
                "sections": {
                    "type": "array",
                    "items": {"type": "string"},
                    "minItems": 1
                },
                "assets": {
                    "type": "object",
                    "properties": {
                        "preview": {"type": "string"},
                        "desktop": {"type": "object"},
                        "mobile": {"type": "object"}
                    },
                    "required": ["preview", "desktop", "mobile"]
                }
            }
        }
    
    def create_config(
        self,
        template_path: Path,
        metadata: Optional[TemplateMetadata] = None,
        **config_data
    ) -> TemplateConfig:
        """创建模板配置
        
        Args:
            template_path: 模板路径
            metadata: 模板元数据
            **config_data: 配置数据
            
        Returns:
            创建的配置对象
        """
        # 基础配置数据
        base_config = {
            "id": config_data.get("id", template_path.name),
            "name": config_data.get("name", template_path.name),
            "version": config_data.get("version", "1.0.0"),
            "category": config_data.get("category", "未分类"),
            "template_type": TemplateType(config_data.get("template_type", "standard")),
            "status": TemplateStatus(config_data.get("status", "draft")),
            "description": config_data.get("description", ""),
        }
        
        # 从元数据补充配置
        if metadata:
            base_config.update(self._extract_config_from_metadata(metadata))
        
        # 合并用户提供的配置
        base_config.update(config_data)
        
        # 创建配置对象
        config = TemplateConfig(**base_config)
        
        return config
    
    def _extract_config_from_metadata(self, metadata: TemplateMetadata) -> Dict[str, Any]:
        """从元数据提取配置信息"""
        config_data = {}
        
        # 从设计特征提取信息
        if metadata.design_features:
            features = metadata.design_features
            
            config_data["tags"] = features.style_tags + features.mood_tags
            config_data["style_attributes"] = {
                "color_tone": features.color_tone,
                "design_complexity": features.design_complexity,
                "visual_weight": features.visual_weight,
                "layout_type": features.layout_type
            }
            
            if features.target_audience:
                config_data["target_audience"] = features.target_audience
        
        # 从生成的标签和关键词提取
        if metadata.generated_tags:
            config_data.setdefault("tags", []).extend(metadata.generated_tags)
        
        if metadata.generated_keywords:
            config_data["keywords"] = metadata.generated_keywords
        
        # 从建议分类提取
        if metadata.suggested_categories:
            config_data["suggested_category"] = metadata.suggested_categories[0]
        
        return config_data
    
    def update_config(
        self,
        config_path: Path,
        updates: Dict[str, Any],
        merge_mode: str = "update"
    ) -> TemplateConfig:
        """更新配置文件
        
        Args:
            config_path: 配置文件路径
            updates: 更新数据
            merge_mode: 合并模式 ('update', 'replace', 'merge')
            
        Returns:
            更新后的配置对象
        """
        # 加载现有配置
        existing_config = self.load_config(config_path)
        
        if merge_mode == "replace":
            # 完全替换
            updated_data = updates
        elif merge_mode == "merge":
            # 深度合并
            updated_data = self._deep_merge(asdict(existing_config), updates)
        else:
            # 更新模式（默认）
            updated_data = asdict(existing_config)
            updated_data.update(updates)
        
        # 更新时间戳
        updated_data["updated_at"] = datetime.now()
        
        # 创建新的配置对象
        updated_config = TemplateConfig(**updated_data)
        
        # 保存配置
        self.save_config(config_path, updated_config)
        
        return updated_config
    
    def _deep_merge(self, base: Dict[str, Any], updates: Dict[str, Any]) -> Dict[str, Any]:
        """深度合并字典"""
        result = base.copy()
        
        for key, value in updates.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def load_config(self, config_path: Path) -> TemplateConfig:
        """加载配置文件
        
        Args:
            config_path: 配置文件路径
            
        Returns:
            配置对象
        """
        if not config_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {config_path}")
        
        with open(config_path, 'r', encoding='utf-8') as f:
            config_data = json.load(f)
        
        # 处理枚举类型
        if "template_type" in config_data:
            config_data["template_type"] = TemplateType(config_data["template_type"])
        if "status" in config_data:
            config_data["status"] = TemplateStatus(config_data["status"])
        
        # 处理颜色方案
        if "color_schemes" in config_data:
            color_schemes = []
            for scheme_data in config_data["color_schemes"]:
                if isinstance(scheme_data, dict):
                    color_schemes.append(ColorScheme(**scheme_data))
                else:
                    color_schemes.append(scheme_data)
            config_data["color_schemes"] = color_schemes
        
        return TemplateConfig(**config_data)
    
    def save_config(self, config_path: Path, config: TemplateConfig):
        """保存配置文件
        
        Args:
            config_path: 配置文件路径
            config: 配置对象
        """
        # 确保目录存在
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 转换为字典
        config_dict = self._config_to_dict(config)
        
        # 保存JSON文件
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config_dict, f, ensure_ascii=False, indent=2)
    
    def _config_to_dict(self, config: TemplateConfig) -> Dict[str, Any]:
        """将配置对象转换为字典"""
        config_dict = asdict(config)
        
        # 处理枚举类型
        if hasattr(config, 'template_type'):
            config_dict["template_type"] = config.template_type.value
        if hasattr(config, 'status'):
            config_dict["status"] = config.status.value
        
        # 处理日期时间
        for field in ["created_at", "updated_at", "effective_date", "expiry_date"]:
            if field in config_dict and config_dict[field]:
                if hasattr(config_dict[field], 'isoformat'):
                    config_dict[field] = config_dict[field].isoformat()
        
        return config_dict
    
    def validate_config(self, config: Union[TemplateConfig, Dict[str, Any]]) -> tuple[bool, List[str]]:
        """验证配置
        
        Args:
            config: 配置对象或字典
            
        Returns:
            (是否有效, 错误列表)
        """
        errors = []
        
        # 转换为字典
        if isinstance(config, TemplateConfig):
            config_dict = self._config_to_dict(config)
        else:
            config_dict = config
        
        # JSON Schema验证
        try:
            validate(instance=config_dict, schema=self.schema)
        except ValidationError as e:
            errors.append(f"Schema验证失败: {e.message}")
        
        # 自定义验证规则
        custom_errors = self._validate_custom_rules(config_dict)
        errors.extend(custom_errors)
        
        return len(errors) == 0, errors
    
    def _validate_custom_rules(self, config_dict: Dict[str, Any]) -> List[str]:
        """自定义验证规则"""
        errors = []
        
        # 检查必需字段
        required_fields = ["id", "name", "category", "template_type", "status"]
        for field in required_fields:
            if field not in config_dict or not config_dict[field]:
                errors.append(f"缺少必需字段: {field}")
        
        # 检查ID格式
        if "id" in config_dict:
            template_id = config_dict["id"]
            if not template_id.replace("_", "").replace("-", "").isalnum():
                errors.append(f"模板ID格式不正确: {template_id}")
        
        # 检查版本格式
        if "version" in config_dict:
            version = config_dict["version"]
            if not version.count(".") == 2:
                errors.append(f"版本号格式不正确: {version}")
        
        # 检查模块列表
        if "sections" in config_dict:
            sections = config_dict["sections"]
            if not sections or len(sections) == 0:
                errors.append("模板必须包含至少一个模块")
        
        return errors
    
    def merge_configs(self, configs: List[TemplateConfig]) -> TemplateConfig:
        """合并多个配置
        
        Args:
            configs: 配置列表
            
        Returns:
            合并后的配置
        """
        if not configs:
            raise ValueError("配置列表不能为空")
        
        # 以第一个配置为基础
        base_config = asdict(configs[0])
        
        # 合并其他配置
        for config in configs[1:]:
            config_dict = asdict(config)
            
            # 合并标签和关键词
            if "tags" in config_dict:
                base_config.setdefault("tags", []).extend(config_dict["tags"])
            if "keywords" in config_dict:
                base_config.setdefault("keywords", []).extend(config_dict["keywords"])
            
            # 合并样式属性
            if "style_attributes" in config_dict:
                base_config.setdefault("style_attributes", {}).update(config_dict["style_attributes"])
            
            # 合并自定义选项
            if "customization_options" in config_dict:
                base_config.setdefault("customization_options", {}).update(config_dict["customization_options"])
        
        # 去重标签和关键词
        if "tags" in base_config:
            base_config["tags"] = list(set(base_config["tags"]))
        if "keywords" in base_config:
            base_config["keywords"] = list(set(base_config["keywords"]))
        
        return TemplateConfig(**base_config)
    
    def load_global_config(self) -> Dict[str, Any]:
        """加载全局配置"""
        global_config = {}
        
        # 加载分类配置
        if self.categories_config.exists():
            with open(self.categories_config, 'r', encoding='utf-8') as f:
                global_config["categories"] = yaml.safe_load(f)
        
        # 加载模板类型配置
        if self.template_types_config.exists():
            with open(self.template_types_config, 'r', encoding='utf-8') as f:
                global_config["template_types"] = yaml.safe_load(f)
        
        # 加载验证规则
        if self.validation_rules_config.exists():
            with open(self.validation_rules_config, 'r', encoding='utf-8') as f:
                global_config["validation_rules"] = yaml.safe_load(f)
        
        # 加载全局设置
        if self.global_settings_config.exists():
            with open(self.global_settings_config, 'r', encoding='utf-8') as f:
                global_config["global_settings"] = yaml.safe_load(f)
        
        return global_config
    
    def get_available_categories(self) -> List[str]:
        """获取可用分类列表"""
        global_config = self.load_global_config()
        
        if "categories" in global_config:
            categories = global_config["categories"]
            if isinstance(categories, dict):
                return list(categories.keys())
        
        # 默认分类
        return ["electronics", "beauty", "home", "seasonal"]
    
    def get_available_template_types(self) -> List[str]:
        """获取可用模板类型列表"""
        global_config = self.load_global_config()
        
        if "template_types" in global_config:
            template_types = global_config["template_types"]
            if isinstance(template_types, dict):
                return list(template_types.keys())
        
        # 默认类型
        return ["standard", "premium", "minimal"]
    
    def validate_against_global_rules(self, config: TemplateConfig) -> tuple[bool, List[str]]:
        """根据全局规则验证配置"""
        errors = []
        global_config = self.load_global_config()
        
        # 验证分类
        available_categories = self.get_available_categories()
        if config.category not in available_categories:
            errors.append(f"无效的分类: {config.category}")
        
        # 验证模板类型
        available_types = self.get_available_template_types()
        if config.template_type.value not in available_types:
            errors.append(f"无效的模板类型: {config.template_type.value}")
        
        # 验证自定义规则
        if "validation_rules" in global_config:
            rules = global_config["validation_rules"]
            rule_errors = self._apply_validation_rules(config, rules)
            errors.extend(rule_errors)
        
        return len(errors) == 0, errors
    
    def _apply_validation_rules(self, config: TemplateConfig, rules: Dict[str, Any]) -> List[str]:
        """应用验证规则"""
        errors = []
        
        # 检查名称长度规则
        if "name_length" in rules:
            min_length = rules["name_length"].get("min", 1)
            max_length = rules["name_length"].get("max", 100)
            
            if len(config.name) < min_length:
                errors.append(f"模板名称过短，最少{min_length}个字符")
            if len(config.name) > max_length:
                errors.append(f"模板名称过长，最多{max_length}个字符")
        
        # 检查标签数量规则
        if "tags_count" in rules and config.tags:
            min_tags = rules["tags_count"].get("min", 0)
            max_tags = rules["tags_count"].get("max", 20)
            
            if len(config.tags) < min_tags:
                errors.append(f"标签数量过少，最少{min_tags}个")
            if len(config.tags) > max_tags:
                errors.append(f"标签数量过多，最多{max_tags}个")
        
        # 检查模块数量规则
        if "sections_count" in rules and config.sections:
            min_sections = rules["sections_count"].get("min", 1)
            max_sections = rules["sections_count"].get("max", 10)
            
            if len(config.sections) < min_sections:
                errors.append(f"模块数量过少，最少{min_sections}个")
            if len(config.sections) > max_sections:
                errors.append(f"模块数量过多，最多{max_sections}个")
        
        return errors