"""
A+ 分类管理服务
负责模板分类的管理和层级结构维护
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
import json
import os

from app_utils.aplus_studio.interfaces import ICategoryManager
from app_utils.aplus_studio.models.core_models import Category


class CategoryService(ICategoryManager):
    """A+ 分类管理服务"""
    
    def __init__(self, config_file: str = "templates/categories_config.json"):
        self.config_file = config_file
        self._categories_cache: Dict[str, Category] = {}
        self._load_categories()
    
    def _load_categories(self) -> None:
        """加载所有分类到缓存"""
        self._categories_cache.clear()
        
        config_data = self._load_config_file()
        
        # 转换为Category对象
        for category_id, category_data in config_data.get("categories", {}).items():
            try:
                category = self._convert_config_to_category(category_id, category_data)
                self._categories_cache[category_id] = category
            except Exception as e:
                print(f"警告: 加载分类 {category_id} 失败: {e}")
        
        # 构建层级关系
        self._build_hierarchy()
    
    def _load_config_file(self) -> Dict[str, Any]:
        """加载分类配置文件"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(f"警告: 分类配置文件加载失败: {e}")
                return self._create_default_config()
        else:
            # 创建默认配置并保存
            default_config = self._create_default_config()
            self._save_config_file(default_config)
            return default_config
    
    def _save_config_file(self, config_data: Dict[str, Any]) -> None:
        """保存配置文件"""
        os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, ensure_ascii=False, indent=2)
        except IOError as e:
            print(f"错误: 分类配置文件保存失败: {e}")
    
    def _create_default_config(self) -> Dict[str, Any]:
        """创建默认分类配置"""
        return {
            "version": "1.0",
            "categories": {
                "electronics": {
                    "name": "电子产品",
                    "parent_id": None,
                    "level": 0,
                    "description": "各类电子产品模板",
                    "tags": ["电子", "科技", "数码"],
                    "template_count": 0,
                    "metadata": {
                        "icon": "electronics",
                        "color": "#2196F3",
                        "created_by": "system"
                    }
                },
                "beauty": {
                    "name": "美妆护肤",
                    "parent_id": None,
                    "level": 0,
                    "description": "美妆护肤品模板",
                    "tags": ["美妆", "护肤", "化妆品"],
                    "template_count": 0,
                    "metadata": {
                        "icon": "beauty",
                        "color": "#E91E63",
                        "created_by": "system"
                    }
                },
                "home": {
                    "name": "家居用品",
                    "parent_id": None,
                    "level": 0,
                    "description": "家居生活用品模板",
                    "tags": ["家居", "生活", "用品"],
                    "template_count": 0,
                    "metadata": {
                        "icon": "home",
                        "color": "#4CAF50",
                        "created_by": "system"
                    }
                },
                "sports": {
                    "name": "运动户外",
                    "parent_id": None,
                    "level": 0,
                    "description": "运动户外用品模板",
                    "tags": ["运动", "户外", "健身"],
                    "template_count": 0,
                    "metadata": {
                        "icon": "sports",
                        "color": "#FF9800",
                        "created_by": "system"
                    }
                },
                "baby": {
                    "name": "母婴用品",
                    "parent_id": None,
                    "level": 0,
                    "description": "母婴儿童用品模板",
                    "tags": ["母婴", "儿童", "宝宝"],
                    "template_count": 0,
                    "metadata": {
                        "icon": "baby",
                        "color": "#9C27B0",
                        "created_by": "system"
                    }
                }
            }
        }
    
    def _convert_config_to_category(self, category_id: str, config_data: Dict[str, Any]) -> Category:
        """将配置数据转换为Category对象"""
        return Category(
            id=category_id,
            name=config_data["name"],
            parent_id=config_data.get("parent_id"),
            level=config_data.get("level", 0),
            description=config_data.get("description", ""),
            tags=config_data.get("tags", []),
            template_count=config_data.get("template_count", 0),
            subcategories=[],  # 将在_build_hierarchy中填充
            metadata=config_data.get("metadata", {})
        )
    
    def _build_hierarchy(self) -> None:
        """构建分类层级关系"""
        # 清空所有子分类
        for category in self._categories_cache.values():
            category.subcategories = []
        
        # 构建父子关系
        for category in self._categories_cache.values():
            if category.parent_id and category.parent_id in self._categories_cache:
                parent = self._categories_cache[category.parent_id]
                parent.subcategories.append(category)
    
    # ICategoryManager接口实现
    def get_category(self, category_id: str) -> Optional[Category]:
        """获取指定分类"""
        return self._categories_cache.get(category_id)
    
    def get_all_categories(self) -> List[Category]:
        """获取所有分类"""
        return list(self._categories_cache.values())
    
    def get_root_categories(self) -> List[Category]:
        """获取根分类（顶级分类）"""
        return [cat for cat in self._categories_cache.values() if cat.parent_id is None]
    
    def get_subcategories(self, parent_id: str) -> List[Category]:
        """获取子分类"""
        parent = self.get_category(parent_id)
        return parent.subcategories if parent else []
    
    def create_category(self, category: Category) -> bool:
        """创建新分类"""
        try:
            # 验证分类ID唯一性
            if category.id in self._categories_cache:
                print(f"分类ID {category.id} 已存在")
                return False
            
            # 验证父分类存在性
            if category.parent_id and category.parent_id not in self._categories_cache:
                print(f"父分类 {category.parent_id} 不存在")
                return False
            
            # 添加到缓存
            self._categories_cache[category.id] = category
            
            # 重建层级关系
            self._build_hierarchy()
            
            # 保存到配置文件
            self._save_categories_to_config()
            
            return True
        except Exception as e:
            print(f"创建分类失败: {e}")
            return False
    
    def update_category(self, category: Category) -> bool:
        """更新分类"""
        try:
            if category.id not in self._categories_cache:
                print(f"分类 {category.id} 不存在")
                return False
            
            # 更新缓存
            self._categories_cache[category.id] = category
            
            # 重建层级关系
            self._build_hierarchy()
            
            # 保存到配置文件
            self._save_categories_to_config()
            
            return True
        except Exception as e:
            print(f"更新分类失败: {e}")
            return False
    
    def delete_category(self, category_id: str) -> bool:
        """删除分类"""
        try:
            category = self.get_category(category_id)
            if not category:
                print(f"分类 {category_id} 不存在")
                return False
            
            # 检查是否有子分类
            if category.subcategories:
                print(f"分类 {category_id} 还有子分类，无法删除")
                return False
            
            # 检查是否有模板
            if category.template_count > 0:
                print(f"分类 {category_id} 还有模板，无法删除")
                return False
            
            # 从缓存中删除
            del self._categories_cache[category_id]
            
            # 重建层级关系
            self._build_hierarchy()
            
            # 保存到配置文件
            self._save_categories_to_config()
            
            return True
        except Exception as e:
            print(f"删除分类失败: {e}")
            return False
    
    def increment_template_count(self, category_id: str) -> bool:
        """增加分类的模板数量"""
        category = self.get_category(category_id)
        if category:
            category.template_count += 1
            self._save_categories_to_config()
            return True
        return False
    
    def decrement_template_count(self, category_id: str) -> bool:
        """减少分类的模板数量"""
        category = self.get_category(category_id)
        if category and category.template_count > 0:
            category.template_count -= 1
            self._save_categories_to_config()
            return True
        return False
    
    def get_category_statistics(self) -> Dict[str, Any]:
        """获取分类统计信息"""
        categories = self.get_all_categories()
        root_categories = self.get_root_categories()
        
        total_templates = sum(cat.template_count for cat in categories)
        
        return {
            "total_categories": len(categories),
            "root_categories": len(root_categories),
            "total_templates": total_templates,
            "last_updated": datetime.now().isoformat()
        }
    
    def _save_categories_to_config(self) -> None:
        """将分类保存到配置文件"""
        config_data = {
            "version": "1.0",
            "categories": {}
        }
        
        for category_id, category in self._categories_cache.items():
            config_data["categories"][category_id] = {
                "name": category.name,
                "parent_id": category.parent_id,
                "level": category.level,
                "description": category.description,
                "tags": category.tags,
                "template_count": category.template_count,
                "metadata": category.metadata
            }
        
        self._save_config_file(config_data)
    
    def reload_categories(self) -> None:
        """重新加载所有分类"""
        self._load_categories()