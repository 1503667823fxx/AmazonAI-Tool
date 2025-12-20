"""
A+ 模板搜索服务
提供智能搜索和相似度匹配功能
"""

from typing import Dict, List, Optional, Tuple, Any
import re
from datetime import datetime
from difflib import SequenceMatcher

from app_utils.aplus_studio.interfaces import ITemplateManager, ICategoryManager
from app_utils.aplus_studio.models.core_models import Template


class SearchService:
    """A+ 模板搜索引擎"""
    
    def __init__(self, template_manager: ITemplateManager, category_manager: ICategoryManager):
        self.template_manager = template_manager
        self.category_manager = category_manager
        
        # 搜索权重配置
        self.search_weights = {
            "name": 3.0,
            "tags": 2.5,
            "keywords": 2.0,
            "category": 1.5,
            "description": 1.0,
            "holiday": 2.0,
            "season": 1.5
        }
        
        # 相似度阈值
        self.similarity_threshold = 0.3
    
    def search_templates(self, query: str, filters: Optional[Dict[str, Any]] = None) -> List[Tuple[Template, float]]:
        """
        搜索模板
        
        Args:
            query: 搜索查询字符串
            filters: 筛选条件
            
        Returns:
            匹配的模板列表，按相关性排序，包含相关性分数
        """
        if not query.strip():
            return []
        
        # 获取所有模板
        all_templates = self.template_manager.get_available_templates()
        
        # 应用筛选条件
        if filters:
            all_templates = self._apply_filters(all_templates, filters)
        
        # 计算相关性分数
        scored_templates = []
        for template in all_templates:
            score = self._calculate_relevance_score(template, query)
            if score > self.similarity_threshold:
                scored_templates.append((template, score))
        
        # 按分数排序
        scored_templates.sort(key=lambda x: x[1], reverse=True)
        
        return scored_templates
    
    def search_by_category(self, category_id: str, query: Optional[str] = None) -> List[Template]:
        """
        按分类搜索模板
        
        Args:
            category_id: 分类ID
            query: 可选的搜索查询
            
        Returns:
            匹配的模板列表
        """
        # 获取分类下的模板
        templates = self.template_manager.get_templates_by_category(category_id)
        
        # 如果有查询字符串，进一步筛选
        if query and query.strip():
            scored_templates = []
            for template in templates:
                score = self._calculate_relevance_score(template, query)
                if score > self.similarity_threshold:
                    scored_templates.append((template, score))
            
            # 按分数排序并返回模板
            scored_templates.sort(key=lambda x: x[1], reverse=True)
            return [template for template, _ in scored_templates]
        
        return templates
    
    def search_by_tags(self, tags: List[str]) -> List[Template]:
        """
        按标签搜索模板
        
        Args:
            tags: 标签列表
            
        Returns:
            匹配的模板列表
        """
        all_templates = self.template_manager.get_available_templates()
        matching_templates = []
        
        for template in all_templates:
            # 计算标签匹配度
            template_tags = [tag.lower() for tag in template.tags]
            search_tags = [tag.lower() for tag in tags]
            
            match_count = sum(1 for tag in search_tags if tag in template_tags)
            if match_count > 0:
                # 计算匹配度分数
                match_ratio = match_count / len(search_tags)
                matching_templates.append((template, match_ratio))
        
        # 按匹配度排序
        matching_templates.sort(key=lambda x: x[1], reverse=True)
        return [template for template, _ in matching_templates]
    
    def search_by_holiday_season(self, holiday: Optional[str] = None, season: Optional[str] = None) -> List[Template]:
        """
        按节日或季节搜索模板
        
        Args:
            holiday: 节日名称
            season: 季节名称
            
        Returns:
            匹配的模板列表
        """
        all_templates = self.template_manager.get_available_templates()
        matching_templates = []
        
        for template in all_templates:
            match = False
            
            if holiday and template.holiday:
                if template.holiday.lower() == holiday.lower():
                    match = True
            
            if season and template.season:
                if template.season.lower() == season.lower():
                    match = True
            
            if match:
                matching_templates.append(template)
        
        return matching_templates
    
    def get_search_suggestions(self, partial_query: str, limit: int = 5) -> List[str]:
        """
        获取搜索建议
        
        Args:
            partial_query: 部分查询字符串
            limit: 建议数量限制
            
        Returns:
            搜索建议列表
        """
        if len(partial_query) < 2:
            return []
        
        suggestions = set()
        all_templates = self.template_manager.get_available_templates()
        
        partial_lower = partial_query.lower()
        
        for template in all_templates:
            # 从模板名称中提取建议
            if partial_lower in template.name.lower():
                suggestions.add(template.name)
            
            # 从标签中提取建议
            for tag in template.tags:
                if partial_lower in tag.lower():
                    suggestions.add(tag)
            
            # 从关键词中提取建议
            for keyword in template.keywords:
                if partial_lower in keyword.lower():
                    suggestions.add(keyword)
        
        # 转换为列表并限制数量
        suggestion_list = list(suggestions)[:limit]
        
        # 按相似度排序
        suggestion_list.sort(key=lambda x: SequenceMatcher(None, partial_query.lower(), x.lower()).ratio(), reverse=True)
        
        return suggestion_list
    
    def get_popular_searches(self) -> List[str]:
        """
        获取热门搜索词
        
        Returns:
            热门搜索词列表
        """
        # 统计所有标签和关键词的使用频率
        tag_counts = {}
        keyword_counts = {}
        
        all_templates = self.template_manager.get_available_templates()
        
        for template in all_templates:
            for tag in template.tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
            
            for keyword in template.keywords:
                keyword_counts[keyword] = keyword_counts.get(keyword, 0) + 1
        
        # 合并并排序
        all_terms = {**tag_counts, **keyword_counts}
        popular_terms = sorted(all_terms.items(), key=lambda x: x[1], reverse=True)
        
        return [term for term, _ in popular_terms[:10]]
    
    def _apply_filters(self, templates: List[Template], filters: Dict[str, Any]) -> List[Template]:
        """应用筛选条件"""
        filtered_templates = templates
        
        # 按分类筛选
        if "category" in filters and filters["category"]:
            filtered_templates = [t for t in filtered_templates if t.category == filters["category"]]
        
        # 按标签筛选
        if "tags" in filters and filters["tags"]:
            filter_tags = [tag.lower() for tag in filters["tags"]]
            filtered_templates = [
                t for t in filtered_templates 
                if any(tag.lower() in filter_tags for tag in t.tags)
            ]
        
        # 按节日筛选
        if "holiday" in filters and filters["holiday"]:
            filtered_templates = [t for t in filtered_templates if t.holiday == filters["holiday"]]
        
        # 按季节筛选
        if "season" in filters and filters["season"]:
            filtered_templates = [t for t in filtered_templates if t.season == filters["season"]]
        
        # 按配色方案筛选
        if "color_scheme" in filters and filters["color_scheme"]:
            filtered_templates = [
                t for t in filtered_templates 
                if filters["color_scheme"] in t.color_schemes
            ]
        
        return filtered_templates
    
    def _calculate_relevance_score(self, template: Template, query: str) -> float:
        """计算模板与查询的相关性分数"""
        query_lower = query.lower()
        total_score = 0.0
        
        # 模板名称匹配
        name_similarity = SequenceMatcher(None, query_lower, template.name.lower()).ratio()
        total_score += name_similarity * self.search_weights["name"]
        
        # 标签匹配
        tag_scores = []
        for tag in template.tags:
            tag_similarity = SequenceMatcher(None, query_lower, tag.lower()).ratio()
            tag_scores.append(tag_similarity)
        
        if tag_scores:
            avg_tag_score = sum(tag_scores) / len(tag_scores)
            total_score += avg_tag_score * self.search_weights["tags"]
        
        # 关键词匹配
        keyword_scores = []
        for keyword in template.keywords:
            keyword_similarity = SequenceMatcher(None, query_lower, keyword.lower()).ratio()
            keyword_scores.append(keyword_similarity)
        
        if keyword_scores:
            avg_keyword_score = sum(keyword_scores) / len(keyword_scores)
            total_score += avg_keyword_score * self.search_weights["keywords"]
        
        # 分类匹配
        category_similarity = SequenceMatcher(None, query_lower, template.category.lower()).ratio()
        total_score += category_similarity * self.search_weights["category"]
        
        # 描述匹配
        desc_similarity = SequenceMatcher(None, query_lower, template.description.lower()).ratio()
        total_score += desc_similarity * self.search_weights["description"]
        
        # 节日匹配
        if template.holiday:
            holiday_similarity = SequenceMatcher(None, query_lower, template.holiday.lower()).ratio()
            total_score += holiday_similarity * self.search_weights["holiday"]
        
        # 季节匹配
        if template.season:
            season_similarity = SequenceMatcher(None, query_lower, template.season.lower()).ratio()
            total_score += season_similarity * self.search_weights["season"]
        
        # 精确匹配加分
        if query_lower in template.name.lower():
            total_score += 1.0
        
        for tag in template.tags:
            if query_lower in tag.lower():
                total_score += 0.5
        
        for keyword in template.keywords:
            if query_lower in keyword.lower():
                total_score += 0.5
        
        # 归一化分数
        max_possible_score = sum(self.search_weights.values()) + 2.0  # 加上精确匹配的分数
        normalized_score = total_score / max_possible_score
        
        return min(normalized_score, 1.0)
    
    def get_search_statistics(self) -> Dict[str, Any]:
        """获取搜索统计信息"""
        all_templates = self.template_manager.get_available_templates()
        
        # 统计各种属性
        categories = set(t.category for t in all_templates)
        tags = set(tag for t in all_templates for tag in t.tags)
        keywords = set(keyword for t in all_templates for keyword in t.keywords)
        holidays = set(t.holiday for t in all_templates if t.holiday)
        seasons = set(t.season for t in all_templates if t.season)
        
        return {
            "total_templates": len(all_templates),
            "unique_categories": len(categories),
            "unique_tags": len(tags),
            "unique_keywords": len(keywords),
            "unique_holidays": len(holidays),
            "unique_seasons": len(seasons),
            "searchable_fields": list(self.search_weights.keys()),
            "last_updated": datetime.now().isoformat()
        }