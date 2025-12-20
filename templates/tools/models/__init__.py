"""
模板库管理系统核心数据模型

此模块包含系统中使用的所有核心数据结构和模型类。
"""

from .template import Template, TemplateConfig, TemplateStatus, TemplateType
from .file_structure import FileStructure, FileInfo, DirectoryInfo
from .metadata import TemplateMetadata, ImageAnalysis, DesignFeatures
from .validation import ValidationResult, ValidationError, ValidationRule
from .search import SearchQuery, SearchResult, FilterCriteria
from .operations import BatchOperation, BatchResult, OperationResult

__all__ = [
    'Template',
    'TemplateConfig', 
    'TemplateStatus',
    'TemplateType',
    'FileStructure',
    'FileInfo',
    'DirectoryInfo',
    'TemplateMetadata',
    'ImageAnalysis',
    'DesignFeatures',
    'ValidationResult',
    'ValidationError',
    'ValidationRule',
    'SearchQuery',
    'SearchResult',
    'FilterCriteria',
    'BatchOperation',
    'BatchResult',
    'OperationResult'
]