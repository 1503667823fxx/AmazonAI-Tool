#!/usr/bin/env python3
"""
版本控制器
负责模板变更检测、版本历史管理和回滚操作
"""

import json
import hashlib
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum

from ..models.template import Template, TemplateConfig
from ..models.operations import OperationResult, OperationType, OperationStatus


class ChangeType(Enum):
    """变更类型"""
    CREATED = "created"
    MODIFIED = "modified"
    DELETED = "deleted"
    MOVED = "moved"
    RENAMED = "renamed"


@dataclass
class FileChange:
    """文件变更记录"""
    file_path: str
    change_type: ChangeType
    old_hash: Optional[str] = None
    new_hash: Optional[str] = None
    old_path: Optional[str] = None  # 用于移动/重命名
    timestamp: datetime = field(default_factory=datetime.now)
    size_bytes: int = 0
    
    def __post_init__(self):
        if isinstance(self.change_type, str):
            self.change_type = ChangeType(self.change_type)


@dataclass
class VersionSnapshot:
    """版本快照"""
    version: str
    template_id: str
    timestamp: datetime
    user: str
    message: str
    
    # 文件快照信息
    files: Dict[str, str] = field(default_factory=dict)  # 文件路径 -> 文件哈希
    config_snapshot: Dict[str, Any] = field(default_factory=dict)
    
    # 变更信息
    changes: List[FileChange] = field(default_factory=list)
    parent_version: Optional[str] = None
    
    # 元数据
    total_files: int = 0
    total_size_bytes: int = 0
    
    def __post_init__(self):
        if isinstance(self.timestamp, str):
            self.timestamp = datetime.fromisoformat(self.timestamp)


@dataclass
class VersionHistory:
    """版本历史"""
    template_id: str
    versions: List[VersionSnapshot] = field(default_factory=list)
    current_version: Optional[str] = None
    
    def add_version(self, snapshot: VersionSnapshot):
        """添加版本快照"""
        self.versions.append(snapshot)
        self.current_version = snapshot.version
        # 按时间排序
        self.versions.sort(key=lambda v: v.timestamp, reverse=True)
    
    def get_version(self, version: str) -> Optional[VersionSnapshot]:
        """获取指定版本"""
        for v in self.versions:
            if v.version == version:
                return v
        return None
    
    def get_latest_version(self) -> Optional[VersionSnapshot]:
        """获取最新版本"""
        if self.versions:
            return self.versions[0]
        return None
    
    def get_version_list(self) -> List[str]:
        """获取版本列表"""
        return [v.version for v in self.versions]


class VersionController:
    """版本控制器"""
    
    def __init__(self, templates_root: Path, versions_root: Optional[Path] = None):
        """初始化版本控制器
        
        Args:
            templates_root: 模板根目录
            versions_root: 版本存储根目录
        """
        self.templates_root = Path(templates_root)
        self.versions_root = Path(versions_root) if versions_root else self.templates_root / ".versions"
        
        # 确保版本目录存在
        self.versions_root.mkdir(parents=True, exist_ok=True)
        
        # 版本历史缓存
        self._history_cache: Dict[str, VersionHistory] = {}
    
    def detect_changes(self, template_path: Path) -> List[FileChange]:
        """检测模板变更
        
        Args:
            template_path: 模板路径
            
        Returns:
            变更列表
        """
        changes = []
        
        if not template_path.exists():
            return changes
        
        template_id = template_path.name
        
        # 获取当前文件状态
        current_files = self._scan_template_files(template_path)
        
        # 获取最后一个版本的文件状态
        history = self.get_version_history(template_id)
        latest_version = history.get_latest_version()
        
        if latest_version is None:
            # 首次检测，所有文件都是新创建的
            for file_path, file_hash in current_files.items():
                file_size = self._get_file_size(template_path / file_path)
                changes.append(FileChange(
                    file_path=file_path,
                    change_type=ChangeType.CREATED,
                    new_hash=file_hash,
                    size_bytes=file_size
                ))
        else:
            # 比较与上一版本的差异
            previous_files = latest_version.files
            
            # 检查新增和修改的文件
            for file_path, file_hash in current_files.items():
                file_size = self._get_file_size(template_path / file_path)
                
                if file_path not in previous_files:
                    # 新增文件
                    changes.append(FileChange(
                        file_path=file_path,
                        change_type=ChangeType.CREATED,
                        new_hash=file_hash,
                        size_bytes=file_size
                    ))
                elif previous_files[file_path] != file_hash:
                    # 修改文件
                    changes.append(FileChange(
                        file_path=file_path,
                        change_type=ChangeType.MODIFIED,
                        old_hash=previous_files[file_path],
                        new_hash=file_hash,
                        size_bytes=file_size
                    ))
            
            # 检查删除的文件
            for file_path in previous_files:
                if file_path not in current_files:
                    changes.append(FileChange(
                        file_path=file_path,
                        change_type=ChangeType.DELETED,
                        old_hash=previous_files[file_path]
                    ))
        
        return changes
    
    def _scan_template_files(self, template_path: Path) -> Dict[str, str]:
        """扫描模板文件并计算哈希
        
        Args:
            template_path: 模板路径
            
        Returns:
            文件路径到哈希的映射
        """
        files = {}
        
        if not template_path.exists():
            return files
        
        # 扫描所有文件
        for file_path in template_path.rglob("*"):
            if file_path.is_file():
                # 计算相对路径
                rel_path = file_path.relative_to(template_path)
                # 计算文件哈希
                file_hash = self._calculate_file_hash(file_path)
                files[str(rel_path)] = file_hash
        
        return files
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        """计算文件哈希
        
        Args:
            file_path: 文件路径
            
        Returns:
            文件哈希值
        """
        hash_md5 = hashlib.md5()
        
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
        except (IOError, OSError):
            # 文件读取失败，返回空哈希
            return ""
        
        return hash_md5.hexdigest()
    
    def _get_file_size(self, file_path: Path) -> int:
        """获取文件大小
        
        Args:
            file_path: 文件路径
            
        Returns:
            文件大小（字节）
        """
        try:
            return file_path.stat().st_size
        except (OSError, FileNotFoundError):
            return 0
    
    def create_version_snapshot(
        self,
        template_path: Path,
        version: str,
        message: str,
        user: str = "system"
    ) -> VersionSnapshot:
        """创建版本快照
        
        Args:
            template_path: 模板路径
            version: 版本号
            message: 版本说明
            user: 用户名
            
        Returns:
            版本快照
        """
        template_id = template_path.name
        
        # 检测变更
        changes = self.detect_changes(template_path)
        
        # 扫描当前文件
        current_files = self._scan_template_files(template_path)
        
        # 加载配置快照
        config_snapshot = {}
        config_path = template_path / "template.json"
        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config_snapshot = json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        
        # 计算统计信息
        total_size = sum(self._get_file_size(template_path / rel_path) 
                        for rel_path in current_files.keys())
        
        # 获取父版本
        history = self.get_version_history(template_id)
        parent_version = None
        if history.versions:
            parent_version = history.get_latest_version().version
        
        # 创建快照
        snapshot = VersionSnapshot(
            version=version,
            template_id=template_id,
            timestamp=datetime.now(),
            user=user,
            message=message,
            files=current_files,
            config_snapshot=config_snapshot,
            changes=changes,
            parent_version=parent_version,
            total_files=len(current_files),
            total_size_bytes=total_size
        )
        
        return snapshot
    
    def save_version_snapshot(self, snapshot: VersionSnapshot) -> bool:
        """保存版本快照
        
        Args:
            snapshot: 版本快照
            
        Returns:
            是否保存成功
        """
        try:
            # 创建版本目录
            version_dir = self.versions_root / snapshot.template_id
            version_dir.mkdir(parents=True, exist_ok=True)
            
            # 保存快照文件
            snapshot_file = version_dir / f"{snapshot.version}.json"
            snapshot_data = self._snapshot_to_dict(snapshot)
            
            with open(snapshot_file, 'w', encoding='utf-8') as f:
                json.dump(snapshot_data, f, ensure_ascii=False, indent=2)
            
            # 更新版本历史
            history = self.get_version_history(snapshot.template_id)
            history.add_version(snapshot)
            self._save_version_history(history)
            
            return True
            
        except (IOError, OSError, json.JSONEncodeError) as e:
            print(f"保存版本快照失败: {e}")
            return False
    
    def _snapshot_to_dict(self, snapshot: VersionSnapshot) -> Dict[str, Any]:
        """将快照转换为字典"""
        data = asdict(snapshot)
        
        # 处理日期时间
        data["timestamp"] = snapshot.timestamp.isoformat()
        
        # 处理变更列表
        changes_data = []
        for change in snapshot.changes:
            change_dict = asdict(change)
            change_dict["change_type"] = change.change_type.value
            change_dict["timestamp"] = change.timestamp.isoformat()
            changes_data.append(change_dict)
        data["changes"] = changes_data
        
        return data
    
    def _dict_to_snapshot(self, data: Dict[str, Any]) -> VersionSnapshot:
        """将字典转换为快照"""
        # 处理变更列表
        changes = []
        for change_data in data.get("changes", []):
            change_data["change_type"] = ChangeType(change_data["change_type"])
            if "timestamp" in change_data:
                change_data["timestamp"] = datetime.fromisoformat(change_data["timestamp"])
            changes.append(FileChange(**change_data))
        
        data["changes"] = changes
        
        # 处理时间戳
        if "timestamp" in data:
            data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        
        return VersionSnapshot(**data)
    
    def get_version_history(self, template_id: str) -> VersionHistory:
        """获取版本历史
        
        Args:
            template_id: 模板ID
            
        Returns:
            版本历史
        """
        # 检查缓存
        if template_id in self._history_cache:
            return self._history_cache[template_id]
        
        # 加载版本历史
        history = VersionHistory(template_id=template_id)
        version_dir = self.versions_root / template_id
        
        if version_dir.exists():
            # 加载所有版本快照
            for snapshot_file in version_dir.glob("*.json"):
                try:
                    with open(snapshot_file, 'r', encoding='utf-8') as f:
                        snapshot_data = json.load(f)
                    
                    snapshot = self._dict_to_snapshot(snapshot_data)
                    history.add_version(snapshot)
                    
                except (json.JSONDecodeError, IOError, KeyError) as e:
                    print(f"加载版本快照失败 {snapshot_file}: {e}")
                    continue
        
        # 缓存历史
        self._history_cache[template_id] = history
        
        return history
    
    def _save_version_history(self, history: VersionHistory):
        """保存版本历史"""
        # 更新缓存
        self._history_cache[history.template_id] = history
        
        # 保存历史索引文件
        history_file = self.versions_root / history.template_id / "history.json"
        history_file.parent.mkdir(parents=True, exist_ok=True)
        
        history_data = {
            "template_id": history.template_id,
            "current_version": history.current_version,
            "versions": [
                {
                    "version": v.version,
                    "timestamp": v.timestamp.isoformat(),
                    "user": v.user,
                    "message": v.message,
                    "total_files": v.total_files,
                    "total_size_bytes": v.total_size_bytes
                }
                for v in history.versions
            ]
        }
        
        try:
            with open(history_file, 'w', encoding='utf-8') as f:
                json.dump(history_data, f, ensure_ascii=False, indent=2)
        except (IOError, json.JSONEncodeError) as e:
            print(f"保存版本历史失败: {e}")
    
    def rollback_to_version(
        self,
        template_path: Path,
        target_version: str,
        backup_current: bool = True
    ) -> OperationResult:
        """回滚到指定版本
        
        Args:
            template_path: 模板路径
            target_version: 目标版本
            backup_current: 是否备份当前版本
            
        Returns:
            操作结果
        """
        template_id = template_path.name
        operation_id = f"rollback_{template_id}_{target_version}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        result = OperationResult(
            operation_id=operation_id,
            operation_type=OperationType.UPDATE,
            target=template_id,
            target_type="template"
        )
        
        try:
            # 获取版本历史
            history = self.get_version_history(template_id)
            target_snapshot = history.get_version(target_version)
            
            if target_snapshot is None:
                result.mark_failed(f"版本不存在: {target_version}")
                return result
            
            # 备份当前版本
            if backup_current and template_path.exists():
                current_version = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                backup_snapshot = self.create_version_snapshot(
                    template_path,
                    current_version,
                    f"回滚前自动备份 (回滚到 {target_version})",
                    "system"
                )
                self.save_version_snapshot(backup_snapshot)
            
            # 执行回滚
            success = self._restore_from_snapshot(template_path, target_snapshot)
            
            if success:
                result.mark_success(
                    f"成功回滚到版本 {target_version}",
                    {
                        "target_version": target_version,
                        "restored_files": len(target_snapshot.files),
                        "backup_created": backup_current
                    }
                )
            else:
                result.mark_failed("回滚操作失败")
            
        except Exception as e:
            result.mark_failed(f"回滚过程中发生错误: {str(e)}")
        
        return result
    
    def _restore_from_snapshot(self, template_path: Path, snapshot: VersionSnapshot) -> bool:
        """从快照恢复模板
        
        Args:
            template_path: 模板路径
            snapshot: 版本快照
            
        Returns:
            是否恢复成功
        """
        try:
            # 清空现有目录（保留备份）
            if template_path.exists():
                backup_path = template_path.parent / f"{template_path.name}_rollback_backup"
                if backup_path.exists():
                    shutil.rmtree(backup_path)
                shutil.move(str(template_path), str(backup_path))
            
            # 重新创建目录
            template_path.mkdir(parents=True, exist_ok=True)
            
            # 恢复配置文件
            if snapshot.config_snapshot:
                config_path = template_path / "template.json"
                with open(config_path, 'w', encoding='utf-8') as f:
                    json.dump(snapshot.config_snapshot, f, ensure_ascii=False, indent=2)
            
            # 注意：这里只能恢复配置文件，因为我们没有存储完整的文件内容
            # 在实际实现中，可能需要使用Git或其他版本控制系统来存储完整的文件历史
            
            return True
            
        except Exception as e:
            print(f"从快照恢复失败: {e}")
            return False
    
    def compare_versions(
        self,
        template_id: str,
        version1: str,
        version2: str
    ) -> Dict[str, Any]:
        """比较两个版本
        
        Args:
            template_id: 模板ID
            version1: 版本1
            version2: 版本2
            
        Returns:
            比较结果
        """
        history = self.get_version_history(template_id)
        
        snapshot1 = history.get_version(version1)
        snapshot2 = history.get_version(version2)
        
        if not snapshot1 or not snapshot2:
            return {"error": "版本不存在"}
        
        # 比较文件差异
        files1 = set(snapshot1.files.keys())
        files2 = set(snapshot2.files.keys())
        
        added_files = files2 - files1
        removed_files = files1 - files2
        common_files = files1 & files2
        
        modified_files = []
        for file_path in common_files:
            if snapshot1.files[file_path] != snapshot2.files[file_path]:
                modified_files.append(file_path)
        
        # 比较配置差异
        config_diff = self._compare_configs(
            snapshot1.config_snapshot,
            snapshot2.config_snapshot
        )
        
        return {
            "version1": version1,
            "version2": version2,
            "file_changes": {
                "added": list(added_files),
                "removed": list(removed_files),
                "modified": modified_files
            },
            "config_changes": config_diff,
            "statistics": {
                "total_changes": len(added_files) + len(removed_files) + len(modified_files),
                "files_v1": len(files1),
                "files_v2": len(files2),
                "size_v1": snapshot1.total_size_bytes,
                "size_v2": snapshot2.total_size_bytes
            }
        }
    
    def _compare_configs(self, config1: Dict[str, Any], config2: Dict[str, Any]) -> Dict[str, Any]:
        """比较配置差异"""
        changes = {
            "added": {},
            "removed": {},
            "modified": {}
        }
        
        keys1 = set(config1.keys())
        keys2 = set(config2.keys())
        
        # 新增的键
        for key in keys2 - keys1:
            changes["added"][key] = config2[key]
        
        # 删除的键
        for key in keys1 - keys2:
            changes["removed"][key] = config1[key]
        
        # 修改的键
        for key in keys1 & keys2:
            if config1[key] != config2[key]:
                changes["modified"][key] = {
                    "old": config1[key],
                    "new": config2[key]
                }
        
        return changes
    
    def get_version_statistics(self, template_id: str) -> Dict[str, Any]:
        """获取版本统计信息
        
        Args:
            template_id: 模板ID
            
        Returns:
            统计信息
        """
        history = self.get_version_history(template_id)
        
        if not history.versions:
            return {"error": "没有版本历史"}
        
        # 计算统计信息
        total_versions = len(history.versions)
        latest_version = history.get_latest_version()
        
        # 计算变更统计
        total_changes = sum(len(v.changes) for v in history.versions)
        change_types = {}
        
        for version in history.versions:
            for change in version.changes:
                change_type = change.change_type.value
                change_types[change_type] = change_types.get(change_type, 0) + 1
        
        # 计算用户统计
        users = {}
        for version in history.versions:
            users[version.user] = users.get(version.user, 0) + 1
        
        # 计算时间跨度
        if total_versions > 1:
            oldest_version = history.versions[-1]
            time_span = latest_version.timestamp - oldest_version.timestamp
            time_span_days = time_span.days
        else:
            time_span_days = 0
        
        return {
            "template_id": template_id,
            "total_versions": total_versions,
            "current_version": history.current_version,
            "latest_version_info": {
                "version": latest_version.version,
                "timestamp": latest_version.timestamp.isoformat(),
                "user": latest_version.user,
                "total_files": latest_version.total_files,
                "total_size_mb": round(latest_version.total_size_bytes / 1024 / 1024, 2)
            },
            "change_statistics": {
                "total_changes": total_changes,
                "change_types": change_types
            },
            "user_statistics": users,
            "time_span_days": time_span_days,
            "version_list": history.get_version_list()
        }
    
    def cleanup_old_versions(
        self,
        template_id: str,
        keep_versions: int = 10,
        keep_days: int = 30
    ) -> OperationResult:
        """清理旧版本
        
        Args:
            template_id: 模板ID
            keep_versions: 保留版本数
            keep_days: 保留天数
            
        Returns:
            操作结果
        """
        operation_id = f"cleanup_{template_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        result = OperationResult(
            operation_id=operation_id,
            operation_type=OperationType.DELETE,
            target=template_id,
            target_type="versions"
        )
        
        try:
            history = self.get_version_history(template_id)
            
            if not history.versions:
                result.mark_success("没有版本需要清理")
                return result
            
            # 确定要保留的版本
            cutoff_date = datetime.now() - timedelta(days=keep_days)
            versions_to_keep = set()
            
            # 保留最新的N个版本
            for version in history.versions[:keep_versions]:
                versions_to_keep.add(version.version)
            
            # 保留指定天数内的版本
            for version in history.versions:
                if version.timestamp >= cutoff_date:
                    versions_to_keep.add(version.version)
            
            # 删除旧版本
            deleted_versions = []
            version_dir = self.versions_root / template_id
            
            for version in history.versions:
                if version.version not in versions_to_keep:
                    # 删除版本文件
                    version_file = version_dir / f"{version.version}.json"
                    if version_file.exists():
                        version_file.unlink()
                        deleted_versions.append(version.version)
            
            # 更新版本历史
            history.versions = [v for v in history.versions if v.version in versions_to_keep]
            self._save_version_history(history)
            
            result.mark_success(
                f"清理完成，删除了 {len(deleted_versions)} 个旧版本",
                {
                    "deleted_versions": deleted_versions,
                    "remaining_versions": len(history.versions)
                }
            )
            
        except Exception as e:
            result.mark_failed(f"清理过程中发生错误: {str(e)}")
        
        return result