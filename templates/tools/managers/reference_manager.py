#!/usr/bin/env python3
"""
引用管理器
负责管理模板分类引用的自动更新、影响分析和批量更新验证
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime
import logging
import glob

from .category_organizer import CategoryOrganizer
from ..models.template import Template, TemplateConfig

logger = logging.getLogger(__name__)


@dataclass
class ReferenceInfo:
    """引用信息"""
    template_id: str
    template_path: Path
    old_category: str
    new_category: str
    reference_type: str  # 'primary', 'secondary', 'tag'
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class ImpactAnalysis:
    """影响分析结果"""
    affected_templates: List[str]
    reference_changes: List[ReferenceInfo]
    broken_references: List[str]
    warnings: List[str]
    estimated_update_time: float
    
    def __post_init__(self):
        """计算统计信息"""
        self.total_affected = len(self.affected_templates)
        self.total_changes = len(self.reference_changes)
        self.has_broken_refs = len(self.broken_references) > 0


class ReferenceManager:
    """引用管理器"""
    
    def __init__(self, templates_root: Path, config_root: Path):
        """初始化引用管理器
        
        Args:
            templates_root: 模板根目录
            config_root: 配置根目录
        """
        self.templates_root = Path(templates_root)
        self.config_root = Path(config_root)
        self.category_organizer = CategoryOrganizer(config_root)
        
        # 引用缓存
        self._reference_cache: Dict[str, Set[str]] = {}
        self._last_scan_time: Optional[datetime] = None
        
        # 扫描模板引用
        self._scan_template_references()
    
    def _scan_template_references(self):
        """扫描所有模板的分类引用"""
        logger.info("开始扫描模板分类引用...")
        
        self._reference_cache.clear()
        template_count = 0
        
        # 查找所有模板配置文件
        config_pattern = str(self.templates_root / "**" / "template.json")
        config_files = glob.glob(config_pattern, recursive=True)
        
        for config_file in config_files:
            try:
                config_path = Path(config_file)
                template_path = config_path.parent
                
                # 读取配置文件
                with open(config_path, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                
                template_id = config_data.get('id', template_path.name)
                
                # 提取分类引用
                references = self._extract_category_references(config_data)
                self._reference_cache[template_id] = references
                
                template_count += 1
                
            except Exception as e:
                logger.warning(f"扫描模板配置失败 {config_file}: {e}")
        
        self._last_scan_time = datetime.now()
        logger.info(f"扫描完成，共处理 {template_count} 个模板")
    
    def _extract_category_references(self, config_data: Dict[str, Any]) -> Set[str]:
        """从配置数据中提取分类引用
        
        Args:
            config_data: 模板配置数据
            
        Returns:
            分类引用集合
        """
        references = set()
        
        # 主分类
        if 'category' in config_data:
            references.add(config_data['category'])
        
        # 子分类
        if 'subcategory' in config_data:
            references.add(config_data['subcategory'])
        
        # 分类信息中的次要分类
        classification = config_data.get('classification', {})
        if 'primary_category' in classification:
            references.add(classification['primary_category'])
        
        if 'secondary_categories' in classification:
            for cat in classification['secondary_categories']:
                references.add(cat)
        
        # 标签中的分类引用
        tags = config_data.get('tags', [])
        for tag in tags:
            # 检查标签是否是分类名称
            if self.category_organizer.get_category(tag):
                references.add(tag)
        
        return references
    
    def analyze_category_change_impact(
        self,
        old_category_id: str,
        new_category_id: Optional[str] = None,
        operation: str = 'rename'
    ) -> ImpactAnalysis:
        """分析分类变更的影响
        
        Args:
            old_category_id: 旧分类ID
            new_category_id: 新分类ID（重命名时使用）
            operation: 操作类型 ('rename', 'delete', 'move')
            
        Returns:
            影响分析结果
        """
        logger.info(f"分析分类变更影响: {operation} {old_category_id} -> {new_category_id}")
        
        affected_templates = []
        reference_changes = []
        broken_references = []
        warnings = []
        
        # 查找受影响的模板
        for template_id, references in self._reference_cache.items():
            if old_category_id in references:
                affected_templates.append(template_id)
                
                # 分析引用变更
                if operation == 'rename' and new_category_id:
                    # 重命名操作
                    template_path = self._find_template_path(template_id)
                    if template_path:
                        ref_info = ReferenceInfo(
                            template_id=template_id,
                            template_path=template_path,
                            old_category=old_category_id,
                            new_category=new_category_id,
                            reference_type='primary'  # 简化处理
                        )
                        reference_changes.append(ref_info)
                
                elif operation == 'delete':
                    # 删除操作 - 标记为损坏引用
                    broken_references.append(template_id)
                    warnings.append(f"模板 {template_id} 引用了将被删除的分类 {old_category_id}")
        
        # 检查子分类影响
        category_node = self.category_organizer.get_category(old_category_id)
        if category_node and category_node.children:
            warnings.append(f"分类 {old_category_id} 有 {len(category_node.children)} 个子分类将受影响")
        
        # 估算更新时间（每个模板约0.1秒）
        estimated_time = len(affected_templates) * 0.1
        
        return ImpactAnalysis(
            affected_templates=affected_templates,
            reference_changes=reference_changes,
            broken_references=broken_references,
            warnings=warnings,
            estimated_update_time=estimated_time
        )
    
    def _find_template_path(self, template_id: str) -> Optional[Path]:
        """查找模板路径
        
        Args:
            template_id: 模板ID
            
        Returns:
            模板路径或None
        """
        # 在缓存的扫描结果中查找
        config_pattern = str(self.templates_root / "**" / "template.json")
        config_files = glob.glob(config_pattern, recursive=True)
        
        for config_file in config_files:
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                
                if config_data.get('id') == template_id:
                    return Path(config_file).parent
                    
            except Exception:
                continue
        
        return None
    
    def update_category_references(
        self,
        old_category_id: str,
        new_category_id: str,
        dry_run: bool = False
    ) -> Tuple[bool, List[str]]:
        """更新分类引用
        
        Args:
            old_category_id: 旧分类ID
            new_category_id: 新分类ID
            dry_run: 是否为试运行
            
        Returns:
            (是否成功, 错误列表)
        """
        logger.info(f"更新分类引用: {old_category_id} -> {new_category_id} (dry_run={dry_run})")
        
        errors = []
        updated_count = 0
        
        # 获取影响分析
        impact = self.analyze_category_change_impact(old_category_id, new_category_id, 'rename')
        
        if dry_run:
            logger.info(f"试运行模式：将更新 {len(impact.affected_templates)} 个模板")
            return True, []
        
        # 执行更新
        for template_id in impact.affected_templates:
            try:
                success = self._update_template_category_reference(
                    template_id, old_category_id, new_category_id
                )
                
                if success:
                    updated_count += 1
                else:
                    errors.append(f"更新模板 {template_id} 失败")
                    
            except Exception as e:
                errors.append(f"更新模板 {template_id} 时发生错误: {e}")
        
        # 更新缓存
        self._update_reference_cache(old_category_id, new_category_id)
        
        logger.info(f"分类引用更新完成：成功 {updated_count} 个，失败 {len(errors)} 个")
        
        return len(errors) == 0, errors
    
    def _update_template_category_reference(
        self,
        template_id: str,
        old_category_id: str,
        new_category_id: str
    ) -> bool:
        """更新单个模板的分类引用
        
        Args:
            template_id: 模板ID
            old_category_id: 旧分类ID
            new_category_id: 新分类ID
            
        Returns:
            是否更新成功
        """
        template_path = self._find_template_path(template_id)
        if not template_path:
            logger.error(f"找不到模板路径: {template_id}")
            return False
        
        config_path = template_path / "template.json"
        
        try:
            # 读取配置
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            # 更新分类引用
            updated = False
            
            # 主分类
            if config_data.get('category') == old_category_id:
                config_data['category'] = new_category_id
                updated = True
            
            # 子分类
            if config_data.get('subcategory') == old_category_id:
                config_data['subcategory'] = new_category_id
                updated = True
            
            # 分类信息
            classification = config_data.get('classification', {})
            if classification.get('primary_category') == old_category_id:
                classification['primary_category'] = new_category_id
                updated = True
            
            if 'secondary_categories' in classification:
                secondary_cats = classification['secondary_categories']
                for i, cat in enumerate(secondary_cats):
                    if cat == old_category_id:
                        secondary_cats[i] = new_category_id
                        updated = True
            
            # 标签
            tags = config_data.get('tags', [])
            for i, tag in enumerate(tags):
                if tag == old_category_id:
                    tags[i] = new_category_id
                    updated = True
            
            # 更新时间戳
            if updated:
                config_data['updated_at'] = datetime.now().isoformat()
                
                # 保存配置
                with open(config_path, 'w', encoding='utf-8') as f:
                    json.dump(config_data, f, ensure_ascii=False, indent=2)
                
                logger.debug(f"更新模板配置成功: {template_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"更新模板配置失败 {template_id}: {e}")
            return False
    
    def _update_reference_cache(self, old_category_id: str, new_category_id: str):
        """更新引用缓存
        
        Args:
            old_category_id: 旧分类ID
            new_category_id: 新分类ID
        """
        for template_id, references in self._reference_cache.items():
            if old_category_id in references:
                references.remove(old_category_id)
                references.add(new_category_id)
    
    def batch_update_references(
        self,
        category_mappings: Dict[str, str],
        dry_run: bool = False
    ) -> Tuple[bool, Dict[str, List[str]]]:
        """批量更新分类引用
        
        Args:
            category_mappings: 分类映射字典 {old_id: new_id}
            dry_run: 是否为试运行
            
        Returns:
            (是否全部成功, 错误详情)
        """
        logger.info(f"批量更新分类引用，共 {len(category_mappings)} 个映射")
        
        all_errors = {}
        all_success = True
        
        for old_id, new_id in category_mappings.items():
            success, errors = self.update_category_references(old_id, new_id, dry_run)
            
            if not success:
                all_success = False
                all_errors[f"{old_id}->{new_id}"] = errors
        
        return all_success, all_errors
    
    def validate_references(self) -> Tuple[bool, List[str]]:
        """验证所有分类引用的有效性
        
        Returns:
            (是否全部有效, 无效引用列表)
        """
        logger.info("验证分类引用有效性...")
        
        invalid_references = []
        
        # 获取所有有效分类
        valid_categories = set(self.category_organizer.category_tree.nodes.keys())
        
        # 检查每个模板的引用
        for template_id, references in self._reference_cache.items():
            for ref in references:
                if ref not in valid_categories:
                    invalid_references.append(f"{template_id}: {ref}")
        
        is_valid = len(invalid_references) == 0
        
        if is_valid:
            logger.info("所有分类引用都有效")
        else:
            logger.warning(f"发现 {len(invalid_references)} 个无效引用")
        
        return is_valid, invalid_references
    
    def get_reference_statistics(self) -> Dict[str, Any]:
        """获取引用统计信息
        
        Returns:
            统计信息字典
        """
        # 统计每个分类的引用次数
        category_usage = {}
        total_references = 0
        
        for template_id, references in self._reference_cache.items():
            for ref in references:
                category_usage[ref] = category_usage.get(ref, 0) + 1
                total_references += 1
        
        # 找出未使用的分类
        all_categories = set(self.category_organizer.category_tree.nodes.keys())
        unused_categories = all_categories - set(category_usage.keys())
        
        # 找出最常用的分类
        most_used = sorted(category_usage.items(), key=lambda x: x[1], reverse=True)[:10]
        
        return {
            'total_templates': len(self._reference_cache),
            'total_references': total_references,
            'unique_categories_used': len(category_usage),
            'unused_categories': list(unused_categories),
            'most_used_categories': most_used,
            'average_references_per_template': total_references / len(self._reference_cache) if self._reference_cache else 0,
            'last_scan_time': self._last_scan_time.isoformat() if self._last_scan_time else None
        }
    
    def find_templates_by_category(self, category_id: str) -> List[str]:
        """查找使用指定分类的模板
        
        Args:
            category_id: 分类ID
            
        Returns:
            模板ID列表
        """
        templates = []
        
        for template_id, references in self._reference_cache.items():
            if category_id in references:
                templates.append(template_id)
        
        return templates
    
    def cleanup_broken_references(self, dry_run: bool = False) -> Tuple[int, List[str]]:
        """清理损坏的分类引用
        
        Args:
            dry_run: 是否为试运行
            
        Returns:
            (清理数量, 错误列表)
        """
        logger.info("开始清理损坏的分类引用...")
        
        # 验证引用
        is_valid, invalid_refs = self.validate_references()
        
        if is_valid:
            logger.info("没有发现损坏的引用")
            return 0, []
        
        errors = []
        cleaned_count = 0
        
        # 获取有效分类集合
        valid_categories = set(self.category_organizer.category_tree.nodes.keys())
        
        if dry_run:
            logger.info(f"试运行模式：将清理 {len(invalid_refs)} 个损坏引用")
            return len(invalid_refs), []
        
        # 处理每个模板
        for template_id, references in self._reference_cache.items():
            invalid_refs_in_template = references - valid_categories
            
            if invalid_refs_in_template:
                try:
                    success = self._remove_invalid_references(template_id, invalid_refs_in_template)
                    if success:
                        cleaned_count += len(invalid_refs_in_template)
                        # 更新缓存
                        self._reference_cache[template_id] = references - invalid_refs_in_template
                    else:
                        errors.append(f"清理模板 {template_id} 的引用失败")
                        
                except Exception as e:
                    errors.append(f"清理模板 {template_id} 时发生错误: {e}")
        
        logger.info(f"清理完成：成功 {cleaned_count} 个，失败 {len(errors)} 个")
        
        return cleaned_count, errors
    
    def _remove_invalid_references(self, template_id: str, invalid_refs: Set[str]) -> bool:
        """从模板配置中移除无效引用
        
        Args:
            template_id: 模板ID
            invalid_refs: 无效引用集合
            
        Returns:
            是否移除成功
        """
        template_path = self._find_template_path(template_id)
        if not template_path:
            return False
        
        config_path = template_path / "template.json"
        
        try:
            # 读取配置
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            updated = False
            
            # 清理主分类（如果无效，设为默认值）
            if config_data.get('category') in invalid_refs:
                config_data['category'] = '未分类'
                updated = True
            
            # 清理子分类
            if config_data.get('subcategory') in invalid_refs:
                del config_data['subcategory']
                updated = True
            
            # 清理分类信息
            classification = config_data.get('classification', {})
            if classification.get('primary_category') in invalid_refs:
                classification['primary_category'] = config_data.get('category', '未分类')
                updated = True
            
            if 'secondary_categories' in classification:
                original_cats = classification['secondary_categories']
                valid_cats = [cat for cat in original_cats if cat not in invalid_refs]
                if len(valid_cats) != len(original_cats):
                    classification['secondary_categories'] = valid_cats
                    updated = True
            
            # 清理标签
            if 'tags' in config_data:
                original_tags = config_data['tags']
                valid_tags = [tag for tag in original_tags if tag not in invalid_refs]
                if len(valid_tags) != len(original_tags):
                    config_data['tags'] = valid_tags
                    updated = True
            
            # 保存更新
            if updated:
                config_data['updated_at'] = datetime.now().isoformat()
                
                with open(config_path, 'w', encoding='utf-8') as f:
                    json.dump(config_data, f, ensure_ascii=False, indent=2)
            
            return True
            
        except Exception as e:
            logger.error(f"移除无效引用失败 {template_id}: {e}")
            return False
    
    def refresh_cache(self):
        """刷新引用缓存"""
        logger.info("刷新分类引用缓存...")
        self._scan_template_references()