#!/usr/bin/env python3
"""
搜索引擎实现
提供模板搜索、索引管理、相关性计算等功能
"""

import json
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import difflib

from ..models.search import SearchQuery, SearchResults, SearchResult, SortField, SortOrder
from ..models.template import Template


@dataclass
class SearchIndex:
    """搜索索引"""
    version: str = "1.0.0"
    last_updated: datetime = None
    templates: Dict[str, Dict[str, Any]] = None
    categories: Dict[str, List[str]] = None
    tags: Dict[str, List[str]] = None
    keywords: Dict[str, List[str]] = None
    
    def __post_init__(self):
        if self.last_updated is None:
            self.last_updated = datetime.now()
        if self.templates is None:
            self.templates = {}
        if self.categories is None:
            self.categories = {}
        if self.tags is None:
            self.tags = {}
        if self.keywords is None:
            self.keywords = {}


class SearchEngine:
    """搜索引擎"""
    
    def __init__(self, templates_root: Path, index_root: Path):
        """初始化搜索引擎
        
        Args:
            templates_root: 模板根目录
            index_root: 索引根目录
        """
        self.templates_root = templates_root
        self.index_root = index_root
        self.index_root.mkdir(exist_ok=True)
        
        # 索引文件路径
        self.search_index_path = index_root / "search_index.json"
        self.category_index_path = index_root / "category_index.json"
        self.tag_index_path = index_root / "tag_index.json"
        
        # 加载索引
        self.search_index = self._load_search_index()
        
        # 搜索配置
        self.fuzzy_threshold = 0.6  # 模糊匹配阈值
        self.max_suggestions = 10   # 最大建议数量
        
    def search(self, query: SearchQuery) -> SearchResults:
        """执行搜索
        
        Args:
            query: 搜索查询
            
        Returns:
            搜索结果
        """
        start_time = time.time()
        
        # 创建结果对象
        results = SearchResults(query=query)
        
        # 获取候选模板
        candidates = self._get_search_candidates(query)
        
        # 应用过滤条件
        filtered_candidates = self._apply_filters(candidates, query)
        
        # 计算相关性分数
        scored_candidates = self._calculate_relevance_scores(filtered_candidates, query)
        
        # 排序
        sorted_candidates = self._sort_results(scored_candidates, query.sort_by, query.sort_order)
        
        # 分页
        paginated_results = self._paginate_results(sorted_candidates, query)
        
        # 转换为搜索结果
        for template_data, score in paginated_results:
            search_result = self._create_search_result(template_data, score, query)
            results.results.append(search_result)
        
        # 设置分页信息
        results.total_count = len(sorted_candidates)
        results.page = query.page
        results.page_size = query.page_size
        results.total_pages = (len(sorted_candidates) + query.page_size - 1) // query.page_size
        
        # 生成搜索建议
        if not results.results and query.query_text:
            results.suggestions = self._generate_suggestions(query.query_text)
            results.did_you_mean = self._generate_did_you_mean(query.query_text)
        
        # 生成分面统计
        results.facets = self._generate_facets(filtered_candidates)
        
        # 计算搜索时间
        results.search_time_ms = (time.time() - start_time) * 1000
        
        return results
    
    def search_by_wildcard(self, pattern: str, field: str = "name") -> List[Dict[str, Any]]:
        """通配符搜索
        
        Args:
            pattern: 通配符模式 (支持 * 和 ?)
            field: 搜索字段
            
        Returns:
            匹配的模板列表
        """
        # 转换通配符为正则表达式
        regex_pattern = pattern.replace('*', '.*').replace('?', '.')
        regex = re.compile(regex_pattern, re.IGNORECASE)
        
        results = []
        for template_id, template_data in self.search_index.templates.items():
            field_value = str(template_data.get(field, ''))
            if regex.match(field_value):
                results.append(template_data)
        
        return results
    
    def search_by_regex(self, pattern: str, field: str = "name") -> List[Dict[str, Any]]:
        """正则表达式搜索
        
        Args:
            pattern: 正则表达式模式
            field: 搜索字段
            
        Returns:
            匹配的模板列表
        """
        try:
            regex = re.compile(pattern, re.IGNORECASE)
        except re.error:
            return []
        
        results = []
        for template_id, template_data in self.search_index.templates.items():
            field_value = str(template_data.get(field, ''))
            if regex.search(field_value):
                results.append(template_data)
        
        return results
    
    def get_similar_templates(self, template_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        """获取相似模板
        
        Args:
            template_id: 模板ID
            limit: 结果数量限制
            
        Returns:
            相似模板列表
        """
        if template_id not in self.search_index.templates:
            return []
        
        target_template = self.search_index.templates[template_id]
        similarities = []
        
        for tid, template_data in self.search_index.templates.items():
            if tid == template_id:
                continue
            
            similarity = self._calculate_template_similarity(target_template, template_data)
            similarities.append((template_data, similarity))
        
        # 按相似度排序
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        return [template for template, _ in similarities[:limit]]
    
    def rebuild_index(self) -> bool:
        """重建搜索索引
        
        Returns:
            是否成功
        """
        try:
            # 创建新索引
            new_index = SearchIndex()
            
            # 扫描模板目录
            by_category_dir = self.templates_root / "by_category"
            if by_category_dir.exists():
                for category_dir in by_category_dir.iterdir():
                    if not category_dir.is_dir():
                        continue
                    
                    category_name = category_dir.name
                    
                    for template_dir in category_dir.iterdir():
                        if not template_dir.is_dir():
                            continue
                        
                        # 加载模板配置
                        config_path = template_dir / "template.json"
                        if not config_path.exists():
                            continue
                        
                        try:
                            template_data = self._load_template_config(config_path)
                            if not template_data:
                                continue
                            
                            template_id = template_data.get('id', template_dir.name)
                            
                            # 添加到索引
                            index_data = self._create_index_entry(template_data, template_dir)
                            new_index.templates[template_id] = index_data
                            
                            # 更新分类索引
                            if category_name not in new_index.categories:
                                new_index.categories[category_name] = []
                            new_index.categories[category_name].append(template_id)
                            
                            # 更新标签索引
                            for tag in template_data.get('tags', []):
                                if tag not in new_index.tags:
                                    new_index.tags[tag] = []
                                new_index.tags[tag].append(template_id)
                            
                            # 更新关键词索引
                            for keyword in template_data.get('keywords', []):
                                if keyword not in new_index.keywords:
                                    new_index.keywords[keyword] = []
                                new_index.keywords[keyword].append(template_id)
                        
                        except Exception as e:
                            print(f"警告: 无法索引模板 {template_dir.name}: {e}")
                            continue
            
            # 保存索引
            self.search_index = new_index
            self._save_search_index()
            
            return True
            
        except Exception as e:
            print(f"重建索引失败: {e}")
            return False
    
    def update_template_index(self, template_id: str, template_data: Dict[str, Any]) -> bool:
        """更新单个模板的索引
        
        Args:
            template_id: 模板ID
            template_data: 模板数据
            
        Returns:
            是否成功
        """
        try:
            # 移除旧索引
            self._remove_template_from_index(template_id)
            
            # 添加新索引
            index_data = self._create_index_entry(template_data, None)
            self.search_index.templates[template_id] = index_data
            
            # 更新分类索引
            category = template_data.get('category', '')
            if category:
                if category not in self.search_index.categories:
                    self.search_index.categories[category] = []
                if template_id not in self.search_index.categories[category]:
                    self.search_index.categories[category].append(template_id)
            
            # 更新标签索引
            for tag in template_data.get('tags', []):
                if tag not in self.search_index.tags:
                    self.search_index.tags[tag] = []
                if template_id not in self.search_index.tags[tag]:
                    self.search_index.tags[tag].append(template_id)
            
            # 更新关键词索引
            for keyword in template_data.get('keywords', []):
                if keyword not in self.search_index.keywords:
                    self.search_index.keywords[keyword] = []
                if template_id not in self.search_index.keywords[keyword]:
                    self.search_index.keywords[keyword].append(template_id)
            
            # 更新时间戳
            self.search_index.last_updated = datetime.now()
            
            # 保存索引
            self._save_search_index()
            
            return True
            
        except Exception as e:
            print(f"更新模板索引失败: {e}")
            return False
    
    def remove_template_from_index(self, template_id: str) -> bool:
        """从索引中移除模板
        
        Args:
            template_id: 模板ID
            
        Returns:
            是否成功
        """
        try:
            self._remove_template_from_index(template_id)
            self.search_index.last_updated = datetime.now()
            self._save_search_index()
            return True
        except Exception as e:
            print(f"移除模板索引失败: {e}")
            return False
    
    def get_search_statistics(self) -> Dict[str, Any]:
        """获取搜索统计信息
        
        Returns:
            统计信息
        """
        return {
            "total_templates": len(self.search_index.templates),
            "total_categories": len(self.search_index.categories),
            "total_tags": len(self.search_index.tags),
            "total_keywords": len(self.search_index.keywords),
            "last_updated": self.search_index.last_updated.isoformat() if self.search_index.last_updated else None,
            "index_version": self.search_index.version
        }
    
    def _get_search_candidates(self, query: SearchQuery) -> List[Dict[str, Any]]:
        """获取搜索候选项"""
        if query.is_empty():
            # 返回所有模板
            return list(self.search_index.templates.values())
        
        candidates = set()
        
        # 文本搜索
        if query.query_text:
            text_matches = self._search_by_text(query.query_text, query.fuzzy_search, query.case_sensitive)
            candidates.update(text_matches)
        
        # 分类搜索
        if query.categories:
            for category in query.categories:
                if category in self.search_index.categories:
                    category_templates = self.search_index.categories[category]
                    for template_id in category_templates:
                        if template_id in self.search_index.templates:
                            candidates.add(template_id)
        
        # 标签搜索
        if query.tags:
            for tag in query.tags:
                if tag in self.search_index.tags:
                    tag_templates = self.search_index.tags[tag]
                    for template_id in tag_templates:
                        if template_id in self.search_index.templates:
                            candidates.add(template_id)
        
        # 关键词搜索
        if query.keywords:
            for keyword in query.keywords:
                if keyword in self.search_index.keywords:
                    keyword_templates = self.search_index.keywords[keyword]
                    for template_id in keyword_templates:
                        if template_id in self.search_index.templates:
                            candidates.add(template_id)
        
        # 如果没有任何匹配，返回所有模板
        if not candidates and not query.is_empty():
            return []
        
        # 转换为模板数据
        return [self.search_index.templates[tid] for tid in candidates if tid in self.search_index.templates]
    
    def _search_by_text(self, text: str, fuzzy: bool, case_sensitive: bool) -> List[str]:
        """按文本搜索"""
        matches = []
        search_text = text if case_sensitive else text.lower()
        
        for template_id, template_data in self.search_index.templates.items():
            # 构建搜索内容
            searchable_fields = [
                template_data.get('name', ''),
                template_data.get('description', ''),
                ' '.join(template_data.get('tags', [])),
                ' '.join(template_data.get('keywords', []))
            ]
            
            searchable_content = ' '.join(searchable_fields)
            if not case_sensitive:
                searchable_content = searchable_content.lower()
            
            # 检查匹配
            if fuzzy:
                # 模糊匹配
                similarity = difflib.SequenceMatcher(None, search_text, searchable_content).ratio()
                if similarity >= self.fuzzy_threshold:
                    matches.append(template_id)
            else:
                # 精确匹配
                if search_text in searchable_content:
                    matches.append(template_id)
        
        return matches
    
    def _apply_filters(self, candidates: List[Dict[str, Any]], query: SearchQuery) -> List[Dict[str, Any]]:
        """应用过滤条件"""
        filtered = []
        
        for template_data in candidates:
            # 应用自定义过滤条件
            if query.filters:
                matches_all_filters = True
                for filter_criteria in query.filters:
                    field_value = template_data.get(filter_criteria.field)
                    if not filter_criteria.matches(field_value):
                        matches_all_filters = False
                        break
                
                if not matches_all_filters:
                    continue
            
            # 状态过滤
            if query.statuses:
                template_status = template_data.get('status', '')
                if template_status not in query.statuses:
                    continue
            
            # 类型过滤
            if query.template_types:
                template_type = template_data.get('template_type', '')
                if template_type not in query.template_types:
                    continue
            
            # 时间范围过滤
            if query.created_after or query.created_before:
                created_at_str = template_data.get('created_at', '')
                if created_at_str:
                    try:
                        created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                        if query.created_after and created_at < query.created_after:
                            continue
                        if query.created_before and created_at > query.created_before:
                            continue
                    except ValueError:
                        continue
            
            # 归档过滤
            if not query.include_archived:
                if template_data.get('status') == 'archived':
                    continue
            
            filtered.append(template_data)
        
        return filtered
    
    def _calculate_relevance_scores(self, candidates: List[Dict[str, Any]], query: SearchQuery) -> List[Tuple[Dict[str, Any], float]]:
        """计算相关性分数"""
        scored = []
        
        for template_data in candidates:
            score = self._calculate_relevance_score(template_data, query)
            scored.append((template_data, score))
        
        return scored
    
    def _calculate_relevance_score(self, template_data: Dict[str, Any], query: SearchQuery) -> float:
        """计算单个模板的相关性分数"""
        if not query.query_text:
            return 1.0
        
        score = 0.0
        search_text = query.query_text.lower()
        
        # 名称匹配 (权重: 10)
        name = template_data.get('name', '').lower()
        if search_text in name:
            if search_text == name:
                score += 20.0  # 完全匹配
            else:
                score += 10.0  # 部分匹配
        
        # 描述匹配 (权重: 5)
        description = template_data.get('description', '').lower()
        if search_text in description:
            score += 5.0
        
        # 标签匹配 (权重: 8)
        for tag in template_data.get('tags', []):
            if search_text in tag.lower():
                if search_text == tag.lower():
                    score += 8.0  # 完全匹配
                else:
                    score += 4.0  # 部分匹配
        
        # 关键词匹配 (权重: 6)
        for keyword in template_data.get('keywords', []):
            if search_text in keyword.lower():
                if search_text == keyword.lower():
                    score += 6.0  # 完全匹配
                else:
                    score += 3.0  # 部分匹配
        
        # 分类匹配 (权重: 4)
        category = template_data.get('category', '').lower()
        if search_text in category:
            score += 4.0
        
        # 质量分数加权 (权重: 0.1)
        quality_score = template_data.get('quality_score', 0)
        score += quality_score * 0.1
        
        # 使用次数加权 (权重: 0.01)
        usage_count = template_data.get('usage_count', 0)
        score += usage_count * 0.01
        
        return score
    
    def _sort_results(self, scored_candidates: List[Tuple[Dict[str, Any], float]], 
                     sort_by: SortField, sort_order: SortOrder) -> List[Tuple[Dict[str, Any], float]]:
        """排序结果"""
        reverse = sort_order == SortOrder.DESC
        
        if sort_by == SortField.RELEVANCE:
            return sorted(scored_candidates, key=lambda x: x[1], reverse=True)
        elif sort_by == SortField.NAME:
            return sorted(scored_candidates, key=lambda x: x[0].get('name', ''), reverse=reverse)
        elif sort_by == SortField.CATEGORY:
            return sorted(scored_candidates, key=lambda x: x[0].get('category', ''), reverse=reverse)
        elif sort_by == SortField.CREATED_AT:
            return sorted(scored_candidates, key=lambda x: x[0].get('created_at', ''), reverse=reverse)
        elif sort_by == SortField.UPDATED_AT:
            return sorted(scored_candidates, key=lambda x: x[0].get('updated_at', ''), reverse=reverse)
        elif sort_by == SortField.QUALITY_SCORE:
            return sorted(scored_candidates, key=lambda x: x[0].get('quality_score', 0), reverse=reverse)
        elif sort_by == SortField.USAGE_COUNT:
            return sorted(scored_candidates, key=lambda x: x[0].get('usage_count', 0), reverse=reverse)
        else:
            return scored_candidates
    
    def _paginate_results(self, sorted_candidates: List[Tuple[Dict[str, Any], float]], 
                         query: SearchQuery) -> List[Tuple[Dict[str, Any], float]]:
        """分页结果"""
        start_idx = query.get_offset()
        end_idx = start_idx + query.page_size
        return sorted_candidates[start_idx:end_idx]
    
    def _create_search_result(self, template_data: Dict[str, Any], score: float, query: SearchQuery) -> SearchResult:
        """创建搜索结果"""
        result = SearchResult(
            template_id=template_data.get('id', ''),
            name=template_data.get('name', ''),
            category=template_data.get('category', ''),
            template_type=template_data.get('template_type', ''),
            status=template_data.get('status', ''),
            description=template_data.get('description', ''),
            relevance_score=score,
            tags=template_data.get('tags', []),
            keywords=template_data.get('keywords', []),
            quality_score=template_data.get('quality_score', 0),
            usage_count=template_data.get('usage_count', 0),
            preview_image=template_data.get('preview_image', ''),
            file_count=template_data.get('file_count', 0),
            total_size_mb=template_data.get('total_size_mb', 0.0)
        )
        
        # 添加高亮
        if query.query_text:
            result.highlights = self._generate_highlights(template_data, query.query_text)
        
        return result
    
    def _generate_highlights(self, template_data: Dict[str, Any], query_text: str) -> Dict[str, str]:
        """生成高亮文本"""
        highlights = {}
        search_text = query_text.lower()
        
        # 高亮名称
        name = template_data.get('name', '')
        if search_text in name.lower():
            highlighted = re.sub(f'({re.escape(query_text)})', r'<mark>\1</mark>', name, flags=re.IGNORECASE)
            highlights['name'] = highlighted
        
        # 高亮描述
        description = template_data.get('description', '')
        if search_text in description.lower():
            highlighted = re.sub(f'({re.escape(query_text)})', r'<mark>\1</mark>', description, flags=re.IGNORECASE)
            highlights['description'] = highlighted
        
        return highlights
    
    def _generate_suggestions(self, query_text: str) -> List[str]:
        """生成搜索建议"""
        suggestions = []
        
        # 从标签中生成建议
        for tag in self.search_index.tags.keys():
            if query_text.lower() in tag.lower() and tag not in suggestions:
                suggestions.append(tag)
        
        # 从关键词中生成建议
        for keyword in self.search_index.keywords.keys():
            if query_text.lower() in keyword.lower() and keyword not in suggestions:
                suggestions.append(keyword)
        
        # 从分类中生成建议
        for category in self.search_index.categories.keys():
            if query_text.lower() in category.lower() and category not in suggestions:
                suggestions.append(category)
        
        return suggestions[:self.max_suggestions]
    
    def _generate_did_you_mean(self, query_text: str) -> Optional[str]:
        """生成"你是否想要"建议"""
        all_terms = list(self.search_index.tags.keys()) + list(self.search_index.keywords.keys())
        
        best_match = None
        best_ratio = 0.0
        
        for term in all_terms:
            ratio = difflib.SequenceMatcher(None, query_text.lower(), term.lower()).ratio()
            if ratio > best_ratio and ratio > 0.6:
                best_ratio = ratio
                best_match = term
        
        return best_match
    
    def _generate_facets(self, candidates: List[Dict[str, Any]]) -> Dict[str, Dict[str, int]]:
        """生成分面统计"""
        facets = {
            "categories": {},
            "template_types": {},
            "statuses": {},
            "tags": {}
        }
        
        for template_data in candidates:
            # 分类统计
            category = template_data.get('category', '')
            if category:
                facets["categories"][category] = facets["categories"].get(category, 0) + 1
            
            # 类型统计
            template_type = template_data.get('template_type', '')
            if template_type:
                facets["template_types"][template_type] = facets["template_types"].get(template_type, 0) + 1
            
            # 状态统计
            status = template_data.get('status', '')
            if status:
                facets["statuses"][status] = facets["statuses"].get(status, 0) + 1
            
            # 标签统计
            for tag in template_data.get('tags', []):
                facets["tags"][tag] = facets["tags"].get(tag, 0) + 1
        
        return facets
    
    def _calculate_template_similarity(self, template1: Dict[str, Any], template2: Dict[str, Any]) -> float:
        """计算模板相似度"""
        similarity = 0.0
        
        # 分类相似度 (权重: 0.3)
        if template1.get('category') == template2.get('category'):
            similarity += 0.3
        
        # 标签相似度 (权重: 0.4)
        tags1 = set(template1.get('tags', []))
        tags2 = set(template2.get('tags', []))
        if tags1 and tags2:
            tag_similarity = len(tags1.intersection(tags2)) / len(tags1.union(tags2))
            similarity += tag_similarity * 0.4
        
        # 关键词相似度 (权重: 0.2)
        keywords1 = set(template1.get('keywords', []))
        keywords2 = set(template2.get('keywords', []))
        if keywords1 and keywords2:
            keyword_similarity = len(keywords1.intersection(keywords2)) / len(keywords1.union(keywords2))
            similarity += keyword_similarity * 0.2
        
        # 类型相似度 (权重: 0.1)
        if template1.get('template_type') == template2.get('template_type'):
            similarity += 0.1
        
        return similarity
    
    def _load_search_index(self) -> SearchIndex:
        """加载搜索索引"""
        if self.search_index_path.exists():
            try:
                with open(self.search_index_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                index = SearchIndex()
                index.version = data.get('version', '1.0.0')
                index.last_updated = datetime.fromisoformat(data.get('last_updated', datetime.now().isoformat()))
                index.templates = data.get('index', {})
                
                # 加载分类索引
                if self.category_index_path.exists():
                    with open(self.category_index_path, 'r', encoding='utf-8') as f:
                        category_data = json.load(f)
                        index.categories = category_data.get('categories', {})
                
                # 加载标签索引
                if self.tag_index_path.exists():
                    with open(self.tag_index_path, 'r', encoding='utf-8') as f:
                        tag_data = json.load(f)
                        index.tags = tag_data.get('tags', {})
                
                return index
                
            except Exception as e:
                print(f"加载搜索索引失败: {e}")
        
        return SearchIndex()
    
    def _save_search_index(self):
        """保存搜索索引"""
        try:
            # 保存主搜索索引
            search_data = {
                "version": self.search_index.version,
                "last_updated": self.search_index.last_updated.isoformat(),
                "total_templates": len(self.search_index.templates),
                "index": self.search_index.templates,
                "metadata": {
                    "created_at": datetime.now().isoformat(),
                    "index_type": "search",
                    "description": "搜索索引，用于快速查找模板"
                }
            }
            
            with open(self.search_index_path, 'w', encoding='utf-8') as f:
                json.dump(search_data, f, ensure_ascii=False, indent=2)
            
            # 保存分类索引
            category_data = {
                "version": self.search_index.version,
                "last_updated": self.search_index.last_updated.isoformat(),
                "categories": self.search_index.categories,
                "metadata": {
                    "created_at": datetime.now().isoformat(),
                    "index_type": "category",
                    "description": "分类索引，按分类组织模板"
                }
            }
            
            with open(self.category_index_path, 'w', encoding='utf-8') as f:
                json.dump(category_data, f, ensure_ascii=False, indent=2)
            
            # 保存标签索引
            tag_data = {
                "version": self.search_index.version,
                "last_updated": self.search_index.last_updated.isoformat(),
                "tags": self.search_index.tags,
                "metadata": {
                    "created_at": datetime.now().isoformat(),
                    "index_type": "tag",
                    "description": "标签索引，按标签组织模板"
                }
            }
            
            with open(self.tag_index_path, 'w', encoding='utf-8') as f:
                json.dump(tag_data, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            print(f"保存搜索索引失败: {e}")
    
    def _load_template_config(self, config_path: Path) -> Optional[Dict[str, Any]]:
        """加载模板配置"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return None
    
    def _create_index_entry(self, template_data: Dict[str, Any], template_dir: Optional[Path]) -> Dict[str, Any]:
        """创建索引条目"""
        entry = {
            "id": template_data.get('id', ''),
            "name": template_data.get('name', ''),
            "category": template_data.get('category', ''),
            "template_type": template_data.get('template_type', ''),
            "status": template_data.get('status', ''),
            "description": template_data.get('description', ''),
            "tags": template_data.get('tags', []),
            "keywords": template_data.get('keywords', []),
            "created_at": template_data.get('metadata', {}).get('created_at', ''),
            "updated_at": template_data.get('metadata', {}).get('updated_at', ''),
            "quality_score": template_data.get('quality_metrics', {}).get('completeness_score', 0),
            "usage_count": template_data.get('metadata', {}).get('usage_stats', {}).get('usage_count', 0),
            "preview_image": template_data.get('assets', {}).get('preview', ''),
            "file_count": 0,
            "total_size_mb": 0.0
        }
        
        # 计算文件统计
        if template_dir and template_dir.exists():
            file_count = 0
            total_size = 0
            for file_path in template_dir.rglob("*"):
                if file_path.is_file():
                    file_count += 1
                    total_size += file_path.stat().st_size
            
            entry["file_count"] = file_count
            entry["total_size_mb"] = total_size / (1024 * 1024)
        
        return entry
    
    def _remove_template_from_index(self, template_id: str):
        """从索引中移除模板"""
        # 从主索引移除
        if template_id in self.search_index.templates:
            template_data = self.search_index.templates[template_id]
            del self.search_index.templates[template_id]
            
            # 从分类索引移除
            category = template_data.get('category', '')
            if category in self.search_index.categories:
                if template_id in self.search_index.categories[category]:
                    self.search_index.categories[category].remove(template_id)
                if not self.search_index.categories[category]:
                    del self.search_index.categories[category]
            
            # 从标签索引移除
            for tag in template_data.get('tags', []):
                if tag in self.search_index.tags:
                    if template_id in self.search_index.tags[tag]:
                        self.search_index.tags[tag].remove(template_id)
                    if not self.search_index.tags[tag]:
                        del self.search_index.tags[tag]
            
            # 从关键词索引移除
            for keyword in template_data.get('keywords', []):
                if keyword in self.search_index.keywords:
                    if template_id in self.search_index.keywords[keyword]:
                        self.search_index.keywords[keyword].remove(template_id)
                    if not self.search_index.keywords[keyword]:
                        del self.search_index.keywords[keyword]