#!/usr/bin/env python3
"""
分类组织器
负责管理模板分类体系，包括分类的增删改查、层级管理和引用更新
"""

import json
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class CategoryNode:
    """分类节点"""
    id: str
    name: str
    description: str = ""
    parent_id: Optional[str] = None
    children: List[str] = field(default_factory=list)
    subcategories: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def add_child(self, child_id: str):
        """添加子分类"""
        if child_id not in self.children:
            self.children.append(child_id)
            self.updated_at = datetime.now()
    
    def remove_child(self, child_id: str):
        """移除子分类"""
        if child_id in self.children:
            self.children.remove(child_id)
            self.updated_at = datetime.now()
    
    def add_subcategory(self, subcategory: str):
        """添加子分类标识符"""
        if subcategory not in self.subcategories:
            self.subcategories.append(subcategory)
            self.updated_at = datetime.now()
    
    def remove_subcategory(self, subcategory: str):
        """移除子分类标识符"""
        if subcategory in self.subcategories:
            self.subcategories.remove(subcategory)
            self.updated_at = datetime.now()


@dataclass
class CategoryTree:
    """分类树结构"""
    nodes: Dict[str, CategoryNode] = field(default_factory=dict)
    root_categories: List[str] = field(default_factory=list)
    
    def add_node(self, node: CategoryNode):
        """添加节点"""
        self.nodes[node.id] = node
        if not node.parent_id:
            if node.id not in self.root_categories:
                self.root_categories.append(node.id)
    
    def remove_node(self, node_id: str) -> bool:
        """移除节点"""
        if node_id not in self.nodes:
            return False
        
        node = self.nodes[node_id]
        
        # 移除父节点的引用
        if node.parent_id and node.parent_id in self.nodes:
            self.nodes[node.parent_id].remove_child(node_id)
        
        # 处理子节点
        for child_id in node.children[:]:
            if child_id in self.nodes:
                child_node = self.nodes[child_id]
                child_node.parent_id = node.parent_id
                if node.parent_id and node.parent_id in self.nodes:
                    self.nodes[node.parent_id].add_child(child_id)
                elif child_id not in self.root_categories:
                    self.root_categories.append(child_id)
        
        # 从根分类中移除
        if node_id in self.root_categories:
            self.root_categories.remove(node_id)
        
        # 删除节点
        del self.nodes[node_id]
        return True
    
    def get_path(self, node_id: str) -> List[str]:
        """获取节点路径"""
        path = []
        current_id = node_id
        
        while current_id and current_id in self.nodes:
            path.insert(0, current_id)
            current_id = self.nodes[current_id].parent_id
        
        return path
    
    def get_descendants(self, node_id: str) -> List[str]:
        """获取所有后代节点"""
        if node_id not in self.nodes:
            return []
        
        descendants = []
        queue = [node_id]
        
        while queue:
            current_id = queue.pop(0)
            if current_id in self.nodes:
                children = self.nodes[current_id].children
                descendants.extend(children)
                queue.extend(children)
        
        return descendants
    
    def validate_structure(self) -> Tuple[bool, List[str]]:
        """验证树结构的完整性"""
        errors = []
        
        # 检查循环引用
        for node_id in self.nodes:
            path = self.get_path(node_id)
            if len(path) != len(set(path)):
                errors.append(f"检测到循环引用: {node_id}")
        
        # 检查孤儿节点
        for node_id, node in self.nodes.items():
            if node.parent_id and node.parent_id not in self.nodes:
                errors.append(f"孤儿节点: {node_id} 的父节点 {node.parent_id} 不存在")
        
        # 检查根节点一致性
        for root_id in self.root_categories:
            if root_id not in self.nodes:
                errors.append(f"根分类 {root_id} 不存在于节点中")
            elif self.nodes[root_id].parent_id:
                errors.append(f"根分类 {root_id} 不应该有父节点")
        
        return len(errors) == 0, errors


class CategoryOrganizer:
    """分类组织器"""
    
    def __init__(self, config_root: Path):
        """初始化分类组织器
        
        Args:
            config_root: 配置根目录
        """
        self.config_root = Path(config_root)
        self.categories_config_path = self.config_root / "categories.yaml"
        self.style_tags_config_path = self.config_root / "style_tags.yaml"
        
        # 内存中的分类树
        self.category_tree = CategoryTree()
        
        # 加载现有配置
        self._load_categories()
    
    def _load_categories(self):
        """加载分类配置"""
        if not self.categories_config_path.exists():
            logger.warning(f"分类配置文件不存在: {self.categories_config_path}")
            return
        
        try:
            with open(self.categories_config_path, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f) or {}
            
            # 解析分类数据
            categories = config_data.get('categories', {})
            
            # 创建分类节点
            for category_id, category_data in categories.items():
                if isinstance(category_data, dict):
                    node = CategoryNode(
                        id=category_id,
                        name=category_data.get('name', category_id),
                        description=category_data.get('description', ''),
                        subcategories=category_data.get('subcategories', []),
                        metadata=category_data.get('metadata', {})
                    )
                    self.category_tree.add_node(node)
                else:
                    # 简单字符串格式
                    node = CategoryNode(
                        id=category_id,
                        name=str(category_data)
                    )
                    self.category_tree.add_node(node)
            
            logger.info(f"加载了 {len(self.category_tree.nodes)} 个分类")
            
        except Exception as e:
            logger.error(f"加载分类配置失败: {e}")
    
    def save_categories(self):
        """保存分类配置到文件"""
        try:
            # 构建配置数据结构
            config_data = {
                'categories': {},
                'style_tags': self._load_style_tags()
            }
            
            # 转换分类树为配置格式
            for node_id, node in self.category_tree.nodes.items():
                if not node.parent_id:  # 只保存根分类
                    config_data['categories'][node_id] = {
                        'name': node.name,
                        'description': node.description,
                        'subcategories': node.subcategories,
                        'metadata': node.metadata
                    }
            
            # 确保目录存在
            self.categories_config_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 保存到YAML文件
            with open(self.categories_config_path, 'w', encoding='utf-8') as f:
                yaml.dump(config_data, f, default_flow_style=False, 
                         allow_unicode=True, sort_keys=False)
            
            logger.info(f"分类配置已保存到: {self.categories_config_path}")
            
        except Exception as e:
            logger.error(f"保存分类配置失败: {e}")
            raise
    
    def _load_style_tags(self) -> Dict[str, Any]:
        """加载样式标签配置"""
        if self.categories_config_path.exists():
            try:
                with open(self.categories_config_path, 'r', encoding='utf-8') as f:
                    config_data = yaml.safe_load(f) or {}
                return config_data.get('style_tags', {})
            except Exception as e:
                logger.warning(f"加载样式标签失败: {e}")
        
        # 返回默认样式标签
        return {
            'design_style': ['modern', 'vintage', 'minimal', 'luxury', 'casual', 'professional'],
            'color_tone': ['warm', 'cool', 'neutral', 'vibrant', 'monochrome'],
            'target_audience': ['young_adults', 'professionals', 'families', 'seniors', 'tech_enthusiasts']
        }
    
    # CRUD操作
    
    def create_category(
        self,
        category_id: str,
        name: str,
        description: str = "",
        parent_id: Optional[str] = None,
        subcategories: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """创建新分类
        
        Args:
            category_id: 分类ID
            name: 分类名称
            description: 分类描述
            parent_id: 父分类ID
            subcategories: 子分类列表
            metadata: 元数据
            
        Returns:
            是否创建成功
        """
        # 检查分类ID是否已存在
        if category_id in self.category_tree.nodes:
            logger.error(f"分类ID已存在: {category_id}")
            return False
        
        # 检查父分类是否存在
        if parent_id and parent_id not in self.category_tree.nodes:
            logger.error(f"父分类不存在: {parent_id}")
            return False
        
        # 创建分类节点
        node = CategoryNode(
            id=category_id,
            name=name,
            description=description,
            parent_id=parent_id,
            subcategories=subcategories or [],
            metadata=metadata or {}
        )
        
        # 添加到分类树
        self.category_tree.add_node(node)
        
        # 更新父节点
        if parent_id and parent_id in self.category_tree.nodes:
            self.category_tree.nodes[parent_id].add_child(category_id)
        
        logger.info(f"创建分类成功: {category_id}")
        return True
    
    def get_category(self, category_id: str) -> Optional[CategoryNode]:
        """获取分类信息
        
        Args:
            category_id: 分类ID
            
        Returns:
            分类节点或None
        """
        return self.category_tree.nodes.get(category_id)
    
    def update_category(
        self,
        category_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        subcategories: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """更新分类信息
        
        Args:
            category_id: 分类ID
            name: 新名称
            description: 新描述
            subcategories: 新子分类列表
            metadata: 新元数据
            
        Returns:
            是否更新成功
        """
        if category_id not in self.category_tree.nodes:
            logger.error(f"分类不存在: {category_id}")
            return False
        
        node = self.category_tree.nodes[category_id]
        
        # 更新字段
        if name is not None:
            node.name = name
        if description is not None:
            node.description = description
        if subcategories is not None:
            node.subcategories = subcategories
        if metadata is not None:
            node.metadata.update(metadata)
        
        node.updated_at = datetime.now()
        
        logger.info(f"更新分类成功: {category_id}")
        return True
    
    def delete_category(self, category_id: str, force: bool = False) -> bool:
        """删除分类
        
        Args:
            category_id: 分类ID
            force: 是否强制删除（即使有子分类）
            
        Returns:
            是否删除成功
        """
        if category_id not in self.category_tree.nodes:
            logger.error(f"分类不存在: {category_id}")
            return False
        
        node = self.category_tree.nodes[category_id]
        
        # 检查是否有子分类
        if node.children and not force:
            logger.error(f"分类 {category_id} 有子分类，无法删除。使用 force=True 强制删除")
            return False
        
        # 删除节点
        success = self.category_tree.remove_node(category_id)
        
        if success:
            logger.info(f"删除分类成功: {category_id}")
        else:
            logger.error(f"删除分类失败: {category_id}")
        
        return success
    
    def list_categories(self, parent_id: Optional[str] = None) -> List[CategoryNode]:
        """列出分类
        
        Args:
            parent_id: 父分类ID，None表示列出根分类
            
        Returns:
            分类节点列表
        """
        if parent_id is None:
            # 返回根分类
            return [self.category_tree.nodes[cat_id] 
                   for cat_id in self.category_tree.root_categories
                   if cat_id in self.category_tree.nodes]
        else:
            # 返回指定父分类的子分类
            if parent_id not in self.category_tree.nodes:
                return []
            
            parent_node = self.category_tree.nodes[parent_id]
            return [self.category_tree.nodes[child_id]
                   for child_id in parent_node.children
                   if child_id in self.category_tree.nodes]
    
    def get_category_path(self, category_id: str) -> List[str]:
        """获取分类路径
        
        Args:
            category_id: 分类ID
            
        Returns:
            从根到该分类的路径
        """
        return self.category_tree.get_path(category_id)
    
    def get_category_hierarchy(self, category_id: str) -> Dict[str, Any]:
        """获取分类层级结构
        
        Args:
            category_id: 分类ID
            
        Returns:
            层级结构字典
        """
        if category_id not in self.category_tree.nodes:
            return {}
        
        node = self.category_tree.nodes[category_id]
        
        hierarchy = {
            'id': node.id,
            'name': node.name,
            'description': node.description,
            'subcategories': node.subcategories,
            'children': []
        }
        
        # 递归构建子分类层级
        for child_id in node.children:
            if child_id in self.category_tree.nodes:
                child_hierarchy = self.get_category_hierarchy(child_id)
                hierarchy['children'].append(child_hierarchy)
        
        return hierarchy
    
    def move_category(self, category_id: str, new_parent_id: Optional[str]) -> bool:
        """移动分类到新的父分类下
        
        Args:
            category_id: 要移动的分类ID
            new_parent_id: 新父分类ID，None表示移动到根级别
            
        Returns:
            是否移动成功
        """
        if category_id not in self.category_tree.nodes:
            logger.error(f"分类不存在: {category_id}")
            return False
        
        # 检查新父分类是否存在
        if new_parent_id and new_parent_id not in self.category_tree.nodes:
            logger.error(f"新父分类不存在: {new_parent_id}")
            return False
        
        # 检查是否会造成循环引用
        if new_parent_id:
            descendants = self.category_tree.get_descendants(category_id)
            if new_parent_id in descendants:
                logger.error(f"移动会造成循环引用: {category_id} -> {new_parent_id}")
                return False
        
        node = self.category_tree.nodes[category_id]
        old_parent_id = node.parent_id
        
        # 从旧父分类中移除
        if old_parent_id and old_parent_id in self.category_tree.nodes:
            self.category_tree.nodes[old_parent_id].remove_child(category_id)
        elif category_id in self.category_tree.root_categories:
            self.category_tree.root_categories.remove(category_id)
        
        # 设置新父分类
        node.parent_id = new_parent_id
        node.updated_at = datetime.now()
        
        # 添加到新父分类
        if new_parent_id and new_parent_id in self.category_tree.nodes:
            self.category_tree.nodes[new_parent_id].add_child(category_id)
        else:
            # 移动到根级别
            if category_id not in self.category_tree.root_categories:
                self.category_tree.root_categories.append(category_id)
        
        logger.info(f"移动分类成功: {category_id} -> {new_parent_id}")
        return True
    
    def validate_category_name_uniqueness(self, name: str, exclude_id: Optional[str] = None) -> bool:
        """验证分类名称唯一性
        
        Args:
            name: 分类名称
            exclude_id: 排除的分类ID（用于更新时检查）
            
        Returns:
            名称是否唯一
        """
        for node_id, node in self.category_tree.nodes.items():
            if node_id != exclude_id and node.name == name:
                return False
        return True
    
    def search_categories(self, query: str, search_in: List[str] = None) -> List[CategoryNode]:
        """搜索分类
        
        Args:
            query: 搜索关键词
            search_in: 搜索字段列表 ['name', 'description', 'subcategories']
            
        Returns:
            匹配的分类节点列表
        """
        if search_in is None:
            search_in = ['name', 'description']
        
        query_lower = query.lower()
        results = []
        
        for node in self.category_tree.nodes.values():
            match = False
            
            if 'name' in search_in and query_lower in node.name.lower():
                match = True
            elif 'description' in search_in and query_lower in node.description.lower():
                match = True
            elif 'subcategories' in search_in:
                for subcat in node.subcategories:
                    if query_lower in subcat.lower():
                        match = True
                        break
            
            if match:
                results.append(node)
        
        return results
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取分类统计信息
        
        Returns:
            统计信息字典
        """
        total_categories = len(self.category_tree.nodes)
        root_categories = len(self.category_tree.root_categories)
        
        # 计算层级深度
        max_depth = 0
        for node_id in self.category_tree.nodes:
            path = self.category_tree.get_path(node_id)
            max_depth = max(max_depth, len(path))
        
        # 计算子分类数量分布
        subcategory_counts = {}
        for node in self.category_tree.nodes.values():
            count = len(node.subcategories)
            subcategory_counts[count] = subcategory_counts.get(count, 0) + 1
        
        return {
            'total_categories': total_categories,
            'root_categories': root_categories,
            'max_depth': max_depth,
            'subcategory_distribution': subcategory_counts,
            'tree_valid': self.category_tree.validate_structure()[0]
        }
    
    def export_categories(self, format_type: str = 'yaml') -> str:
        """导出分类配置
        
        Args:
            format_type: 导出格式 ('yaml', 'json')
            
        Returns:
            导出的配置字符串
        """
        # 构建导出数据
        export_data = {
            'categories': {},
            'style_tags': self._load_style_tags(),
            'metadata': {
                'exported_at': datetime.now().isoformat(),
                'total_categories': len(self.category_tree.nodes)
            }
        }
        
        # 转换分类数据
        for node_id, node in self.category_tree.nodes.items():
            if not node.parent_id:  # 只导出根分类
                export_data['categories'][node_id] = {
                    'name': node.name,
                    'description': node.description,
                    'subcategories': node.subcategories,
                    'metadata': node.metadata,
                    'created_at': node.created_at.isoformat(),
                    'updated_at': node.updated_at.isoformat()
                }
        
        # 根据格式导出
        if format_type.lower() == 'json':
            return json.dumps(export_data, ensure_ascii=False, indent=2)
        else:
            return yaml.dump(export_data, default_flow_style=False, 
                           allow_unicode=True, sort_keys=False)
    
    def import_categories(self, config_data: str, format_type: str = 'yaml', merge_mode: str = 'update') -> bool:
        """导入分类配置
        
        Args:
            config_data: 配置数据字符串
            format_type: 数据格式 ('yaml', 'json')
            merge_mode: 合并模式 ('update', 'replace', 'merge')
            
        Returns:
            是否导入成功
        """
        try:
            # 解析数据
            if format_type.lower() == 'json':
                data = json.loads(config_data)
            else:
                data = yaml.safe_load(config_data)
            
            categories = data.get('categories', {})
            
            if merge_mode == 'replace':
                # 完全替换
                self.category_tree = CategoryTree()
            
            # 导入分类
            for category_id, category_data in categories.items():
                if merge_mode == 'update' and category_id in self.category_tree.nodes:
                    # 更新现有分类
                    self.update_category(
                        category_id,
                        name=category_data.get('name'),
                        description=category_data.get('description'),
                        subcategories=category_data.get('subcategories'),
                        metadata=category_data.get('metadata')
                    )
                else:
                    # 创建新分类
                    self.create_category(
                        category_id,
                        name=category_data.get('name', category_id),
                        description=category_data.get('description', ''),
                        subcategories=category_data.get('subcategories', []),
                        metadata=category_data.get('metadata', {})
                    )
            
            logger.info(f"导入分类配置成功，共 {len(categories)} 个分类")
            return True
            
        except Exception as e:
            logger.error(f"导入分类配置失败: {e}")
            return False
    
    def validate_structure(self) -> Tuple[bool, List[str]]:
        """验证分类结构完整性
        
        Returns:
            (是否有效, 错误列表)
        """
        return self.category_tree.validate_structure()