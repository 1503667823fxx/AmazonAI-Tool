"""
管理器模块
提供配置管理、分类管理、引用管理等功能
"""

from .config_manager import ConfigManager
from .category_organizer import CategoryOrganizer, CategoryNode, CategoryTree
from .reference_manager import ReferenceManager, ReferenceInfo, ImpactAnalysis
from .version_controller import (
    VersionController, VersionSnapshot, VersionHistory, 
    FileChange, ChangeType
)
from .migration_tool import (
    MigrationTool, MigrationFilter, MigrationManifest,
    MigrationMode, ConflictResolution
)

__all__ = [
    'ConfigManager',
    'CategoryOrganizer', 
    'CategoryNode', 
    'CategoryTree',
    'ReferenceManager',
    'ReferenceInfo',
    'ImpactAnalysis',
    'VersionController',
    'VersionSnapshot',
    'VersionHistory',
    'FileChange',
    'ChangeType',
    'MigrationTool',
    'MigrationFilter',
    'MigrationManifest',
    'MigrationMode',
    'ConflictResolution'
]