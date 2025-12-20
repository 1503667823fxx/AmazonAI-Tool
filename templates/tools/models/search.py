"""
搜索相关的数据模型
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Union


class SearchOperator(Enum):
    """搜索操作符"""
    AND = "and"
    OR = "or"
    NOT = "not"


class SortOrder(Enum):
    """排序顺序"""
    ASC = "asc"
    DESC = "desc"


class SortField(Enum):
    """排序字段"""
    NAME = "name"
    CREATED_AT = "created_at"
    UPDATED_AT = "updated_at"
    CATEGORY = "category"
    QUALITY_SCORE = "quality_score"
    USAGE_COUNT = "usage_count"
    RELEVANCE = "relevance"


@dataclass
class FilterCriteria:
    """过滤条件"""
    field: str
    operator: str  # eq, ne, gt, lt, gte, lte, in, not_in, contains, starts_with, ends_with
    value: Any
    
    def matches(self, item_value: Any) -> bool:
        """检查是否匹配"""
        if self.operator == "eq":
            return item_value == self.value
        elif self.operator == "ne":
            return item_value != self.value
        elif self.operator == "gt":
            return item_value > self.value
        elif self.operator == "lt":
            return item_value < self.value
        elif self.operator == "gte":
            return item_value >= self.value
        elif self.operator == "lte":
            return item_value <= self.value
        elif self.operator == "in":
            return item_value in self.value
        elif self.operator == "not_in":
            return item_value not in self.value
        elif self.operator == "contains":
            return str(self.value).lower() in str(item_value).lower()
        elif self.operator == "starts_with":
            return str(item_value).lower().startswith(str(self.value).lower())
        elif self.operator == "ends_with":
            return str(item_value).lower().endswith(str(self.value).lower())
        else:
            return False


@dataclass
class SearchQuery:
    """搜索查询"""
    # 基本查询
    query_text: str = ""
    
    # 过滤条件
    filters: List[FilterCriteria] = field(default_factory=list)
    filter_operator: SearchOperator = SearchOperator.AND
    
    # 分类和标签
    categories: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    
    # 状态和类型
    statuses: List[str] = field(default_factory=list)
    template_types: List[str] = field(default_factory=list)
    
    # 时间范围
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None
    updated_after: Optional[datetime] = None
    updated_before: Optional[datetime] = None
    
    # 排序
    sort_by: SortField = SortField.RELEVANCE
    sort_order: SortOrder = SortOrder.DESC
    
    # 分页
    page: int = 1
    page_size: int = 20
    
    # 高级选项
    include_archived: bool = False
    fuzzy_search: bool = True
    case_sensitive: bool = False
    
    def __post_init__(self):
        """初始化后处理"""
        if isinstance(self.filter_operator, str):
            self.filter_operator = SearchOperator(self.filter_operator)
        if isinstance(self.sort_by, str):
            self.sort_by = SortField(self.sort_by)
        if isinstance(self.sort_order, str):
            self.sort_order = SortOrder(self.sort_order)
    
    def add_filter(self, field: str, operator: str, value: Any):
        """添加过滤条件"""
        self.filters.append(FilterCriteria(field, operator, value))
    
    def add_category_filter(self, category: str):
        """添加分类过滤"""
        if category not in self.categories:
            self.categories.append(category)
    
    def add_tag_filter(self, tag: str):
        """添加标签过滤"""
        if tag not in self.tags:
            self.tags.append(tag)
    
    def add_keyword_filter(self, keyword: str):
        """添加关键词过滤"""
        if keyword not in self.keywords:
            self.keywords.append(keyword)
    
    def set_date_range(self, start_date: Optional[datetime], end_date: Optional[datetime], field: str = "created"):
        """设置日期范围"""
        if field == "created":
            self.created_after = start_date
            self.created_before = end_date
        elif field == "updated":
            self.updated_after = start_date
            self.updated_before = end_date
    
    def get_offset(self) -> int:
        """获取偏移量"""
        return (self.page - 1) * self.page_size
    
    def is_empty(self) -> bool:
        """检查是否为空查询"""
        return (
            not self.query_text and
            not self.filters and
            not self.categories and
            not self.tags and
            not self.keywords and
            not self.statuses and
            not self.template_types
        )


@dataclass
class SearchResult:
    """搜索结果项"""
    template_id: str
    name: str
    category: str
    template_type: str
    status: str
    description: str
    
    # 匹配信息
    relevance_score: float = 0.0
    matched_fields: List[str] = field(default_factory=list)
    highlights: Dict[str, str] = field(default_factory=dict)
    
    # 基本信息
    tags: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    # 质量和使用信息
    quality_score: float = 0.0
    usage_count: int = 0
    
    # 文件信息
    preview_image: Optional[str] = None
    file_count: int = 0
    total_size_mb: float = 0.0
    
    def add_matched_field(self, field: str):
        """添加匹配字段"""
        if field not in self.matched_fields:
            self.matched_fields.append(field)
    
    def add_highlight(self, field: str, highlighted_text: str):
        """添加高亮文本"""
        self.highlights[field] = highlighted_text
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "template_id": self.template_id,
            "name": self.name,
            "category": self.category,
            "template_type": self.template_type,
            "status": self.status,
            "description": self.description,
            "relevance_score": self.relevance_score,
            "matched_fields": self.matched_fields,
            "highlights": self.highlights,
            "tags": self.tags,
            "keywords": self.keywords,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "quality_score": self.quality_score,
            "usage_count": self.usage_count,
            "preview_image": self.preview_image,
            "file_count": self.file_count,
            "total_size_mb": self.total_size_mb
        }


@dataclass
class SearchResults:
    """搜索结果集"""
    query: SearchQuery
    results: List[SearchResult] = field(default_factory=list)
    
    # 分页信息
    total_count: int = 0
    page: int = 1
    page_size: int = 20
    total_pages: int = 0
    
    # 搜索统计
    search_time_ms: float = 0.0
    facets: Dict[str, Dict[str, int]] = field(default_factory=dict)
    
    # 建议
    suggestions: List[str] = field(default_factory=list)
    did_you_mean: Optional[str] = None
    
    def __post_init__(self):
        """初始化后处理"""
        self.total_pages = (self.total_count + self.page_size - 1) // self.page_size
    
    @property
    def has_results(self) -> bool:
        """是否有结果"""
        return len(self.results) > 0
    
    @property
    def has_more_pages(self) -> bool:
        """是否有更多页面"""
        return self.page < self.total_pages
    
    @property
    def has_previous_page(self) -> bool:
        """是否有上一页"""
        return self.page > 1
    
    def get_page_info(self) -> Dict[str, Any]:
        """获取分页信息"""
        return {
            "current_page": self.page,
            "page_size": self.page_size,
            "total_pages": self.total_pages,
            "total_count": self.total_count,
            "has_previous": self.has_previous_page,
            "has_next": self.has_more_pages,
            "start_index": (self.page - 1) * self.page_size + 1,
            "end_index": min(self.page * self.page_size, self.total_count)
        }
    
    def add_facet(self, field: str, values: Dict[str, int]):
        """添加分面统计"""
        self.facets[field] = values
    
    def add_suggestion(self, suggestion: str):
        """添加搜索建议"""
        if suggestion not in self.suggestions:
            self.suggestions.append(suggestion)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "results": [result.to_dict() for result in self.results],
            "pagination": self.get_page_info(),
            "search_time_ms": self.search_time_ms,
            "facets": self.facets,
            "suggestions": self.suggestions,
            "did_you_mean": self.did_you_mean,
            "query_info": {
                "query_text": self.query.query_text,
                "filters_count": len(self.query.filters),
                "categories": self.query.categories,
                "tags": self.query.tags,
                "sort_by": self.query.sort_by.value,
                "sort_order": self.query.sort_order.value
            }
        }