"""
文件结构相关的数据模型
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import os


@dataclass
class FileInfo:
    """文件信息"""
    name: str
    path: Path
    size: int
    created_at: datetime
    modified_at: datetime
    file_type: str
    mime_type: Optional[str] = None
    checksum: Optional[str] = None
    
    def __post_init__(self):
        """初始化后处理"""
        if isinstance(self.path, str):
            self.path = Path(self.path)
    
    @property
    def extension(self) -> str:
        """获取文件扩展名"""
        return self.path.suffix.lower()
    
    @property
    def size_mb(self) -> float:
        """获取文件大小(MB)"""
        return self.size / (1024 * 1024)
    
    def is_image(self) -> bool:
        """检查是否为图片文件"""
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
        return self.extension in image_extensions
    
    def is_config(self) -> bool:
        """检查是否为配置文件"""
        config_extensions = {'.json', '.yaml', '.yml', '.toml', '.ini'}
        return self.extension in config_extensions


@dataclass
class DirectoryInfo:
    """目录信息"""
    name: str
    path: Path
    created_at: datetime
    modified_at: datetime
    file_count: int = 0
    subdirectory_count: int = 0
    total_size: int = 0
    
    def __post_init__(self):
        """初始化后处理"""
        if isinstance(self.path, str):
            self.path = Path(self.path)
    
    @property
    def total_size_mb(self) -> float:
        """获取总大小(MB)"""
        return self.total_size / (1024 * 1024)


@dataclass
class FileStructure:
    """文件结构数据模型"""
    root_path: Path
    directories: Dict[str, DirectoryInfo] = field(default_factory=dict)
    files: Dict[str, FileInfo] = field(default_factory=dict)
    
    # 分类文件
    config_files: List[str] = field(default_factory=list)
    asset_files: List[str] = field(default_factory=list)
    document_files: List[str] = field(default_factory=list)
    
    # 统计信息
    total_files: int = 0
    total_directories: int = 0
    total_size: int = 0
    
    def __post_init__(self):
        """初始化后处理"""
        if isinstance(self.root_path, str):
            self.root_path = Path(self.root_path)
    
    @classmethod
    def from_directory(cls, directory_path: Path) -> 'FileStructure':
        """从目录创建文件结构"""
        if isinstance(directory_path, str):
            directory_path = Path(directory_path)
            
        if not directory_path.exists():
            raise FileNotFoundError(f"目录不存在: {directory_path}")
        
        structure = cls(root_path=directory_path)
        structure._scan_directory()
        return structure
    
    def _scan_directory(self):
        """扫描目录结构"""
        if not self.root_path.exists():
            return
            
        for root, dirs, files in os.walk(self.root_path):
            root_path = Path(root)
            
            # 处理目录
            for dir_name in dirs:
                dir_path = root_path / dir_name
                relative_path = dir_path.relative_to(self.root_path)
                
                try:
                    stat = dir_path.stat()
                    dir_info = DirectoryInfo(
                        name=dir_name,
                        path=dir_path,
                        created_at=datetime.fromtimestamp(stat.st_ctime),
                        modified_at=datetime.fromtimestamp(stat.st_mtime)
                    )
                    self.directories[str(relative_path)] = dir_info
                    self.total_directories += 1
                except (OSError, PermissionError):
                    continue
            
            # 处理文件
            for file_name in files:
                file_path = root_path / file_name
                relative_path = file_path.relative_to(self.root_path)
                
                try:
                    stat = file_path.stat()
                    file_info = FileInfo(
                        name=file_name,
                        path=file_path,
                        size=stat.st_size,
                        created_at=datetime.fromtimestamp(stat.st_ctime),
                        modified_at=datetime.fromtimestamp(stat.st_mtime),
                        file_type=file_path.suffix.lower()
                    )
                    
                    self.files[str(relative_path)] = file_info
                    self.total_files += 1
                    self.total_size += stat.st_size
                    
                    # 分类文件
                    self._categorize_file(str(relative_path), file_info)
                    
                except (OSError, PermissionError):
                    continue
    
    def _categorize_file(self, relative_path: str, file_info: FileInfo):
        """分类文件"""
        if file_info.is_config():
            self.config_files.append(relative_path)
        elif file_info.is_image():
            self.asset_files.append(relative_path)
        elif file_info.extension in {'.md', '.txt', '.rst', '.pdf'}:
            self.document_files.append(relative_path)
    
    def get_file(self, relative_path: str) -> Optional[FileInfo]:
        """获取文件信息"""
        return self.files.get(relative_path)
    
    def get_directory(self, relative_path: str) -> Optional[DirectoryInfo]:
        """获取目录信息"""
        return self.directories.get(relative_path)
    
    def list_files_by_type(self, file_type: str) -> List[FileInfo]:
        """按类型列出文件"""
        return [
            file_info for file_info in self.files.values()
            if file_info.file_type == file_type
        ]
    
    def list_images(self) -> List[FileInfo]:
        """列出所有图片文件"""
        return [
            file_info for file_info in self.files.values()
            if file_info.is_image()
        ]
    
    def validate_structure(self, required_files: List[str], required_dirs: List[str]) -> List[str]:
        """验证文件结构"""
        errors = []
        
        # 检查必需文件
        for required_file in required_files:
            if required_file not in self.files:
                errors.append(f"缺少必需文件: {required_file}")
        
        # 检查必需目录
        for required_dir in required_dirs:
            if required_dir not in self.directories:
                errors.append(f"缺少必需目录: {required_dir}")
        
        return errors
    
    @property
    def total_size_mb(self) -> float:
        """获取总大小(MB)"""
        return self.total_size / (1024 * 1024)
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "total_files": self.total_files,
            "total_directories": self.total_directories,
            "total_size_mb": self.total_size_mb,
            "config_files": len(self.config_files),
            "asset_files": len(self.asset_files),
            "document_files": len(self.document_files),
            "file_types": self._get_file_type_stats()
        }
    
    def _get_file_type_stats(self) -> Dict[str, int]:
        """获取文件类型统计"""
        type_stats = {}
        for file_info in self.files.values():
            file_type = file_info.file_type or "unknown"
            type_stats[file_type] = type_stats.get(file_type, 0) + 1
        return type_stats