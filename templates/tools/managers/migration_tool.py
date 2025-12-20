#!/usr/bin/env python3
"""
迁移工具
负责模板库导入导出、跨环境迁移和数据完整性验证
"""

import json
import shutil
import zipfile
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
import hashlib

from ..models.template import Template, TemplateConfig, TemplateStatus, TemplateType
from ..models.operations import (
    OperationResult, OperationType, OperationStatus,
    ExportResult, ImportResult, BatchResult
)
from .config_manager import ConfigManager
from .version_controller import VersionController


class MigrationMode(Enum):
    """迁移模式"""
    FULL = "full"  # 完整迁移
    SELECTIVE = "selective"  # 选择性迁移
    INCREMENTAL = "incremental"  # 增量迁移
    CATEGORY = "category"  # 按分类迁移


class ConflictResolution(Enum):
    """冲突解决策略"""
    SKIP = "skip"  # 跳过冲突项
    OVERWRITE = "overwrite"  # 覆盖现有项
    RENAME = "rename"  # 重命名新项
    MERGE = "merge"  # 合并配置
    ASK = "ask"  # 询问用户


@dataclass
class MigrationFilter:
    """迁移过滤器"""
    categories: List[str] = field(default_factory=list)
    template_types: List[str] = field(default_factory=list)
    status_list: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    date_range: Optional[Tuple[datetime, datetime]] = None
    size_limit_mb: Optional[float] = None
    exclude_patterns: List[str] = field(default_factory=list)
    include_patterns: List[str] = field(default_factory=list)


@dataclass
class MigrationManifest:
    """迁移清单"""
    export_id: str
    export_timestamp: datetime
    source_environment: str
    migration_mode: MigrationMode
    
    # 模板信息
    templates: List[Dict[str, Any]] = field(default_factory=list)
    total_templates: int = 0
    total_size_bytes: int = 0
    
    # 过滤器信息
    filter_criteria: Optional[MigrationFilter] = None
    
    # 元数据
    version: str = "1.0"
    created_by: str = ""
    description: str = ""
    
    def __post_init__(self):
        if isinstance(self.export_timestamp, str):
            self.export_timestamp = datetime.fromisoformat(self.export_timestamp)
        if isinstance(self.migration_mode, str):
            self.migration_mode = MigrationMode(self.migration_mode)


class MigrationTool:
    """迁移工具"""
    
    def __init__(
        self,
        templates_root: Path,
        config_manager: Optional[ConfigManager] = None,
        version_controller: Optional[VersionController] = None
    ):
        """初始化迁移工具
        
        Args:
            templates_root: 模板根目录
            config_manager: 配置管理器
            version_controller: 版本控制器
        """
        self.templates_root = Path(templates_root)
        self.config_manager = config_manager or ConfigManager(self.templates_root / "config")
        self.version_controller = version_controller or VersionController(self.templates_root)
        
        # 导出/导入临时目录
        self.temp_dir = Path(tempfile.gettempdir()) / "template_migration"
        self.temp_dir.mkdir(parents=True, exist_ok=True)
    
    def export_templates(
        self,
        export_path: Path,
        migration_filter: Optional[MigrationFilter] = None,
        migration_mode: MigrationMode = MigrationMode.FULL,
        include_versions: bool = False,
        compress: bool = True
    ) -> ExportResult:
        """导出模板库
        
        Args:
            export_path: 导出路径
            migration_filter: 迁移过滤器
            migration_mode: 迁移模式
            include_versions: 是否包含版本历史
            compress: 是否压缩
            
        Returns:
            导出结果
        """
        export_id = f"export_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        result = ExportResult(
            export_id=export_id,
            export_type=migration_mode.value
        )
        
        try:
            # 获取要导出的模板列表
            templates_to_export = self._get_filtered_templates(migration_filter)
            
            if not templates_to_export:
                result.mark_completed(False, "没有找到符合条件的模板")
                return result
            
            # 创建临时导出目录
            temp_export_dir = self.temp_dir / export_id
            temp_export_dir.mkdir(parents=True, exist_ok=True)
            
            # 导出模板
            exported_templates = []
            total_size = 0
            
            for template_path in templates_to_export:
                try:
                    # 复制模板文件
                    template_name = template_path.name
                    target_dir = temp_export_dir / "templates" / template_name
                    
                    shutil.copytree(template_path, target_dir)
                    
                    # 计算大小
                    template_size = self._calculate_directory_size(target_dir)
                    total_size += template_size
                    
                    exported_templates.append(template_name)
                    result.add_template(template_name)
                    
                except Exception as e:
                    result.add_error(f"导出模板 {template_path.name} 失败: {str(e)}")
                    continue
            
            # 导出版本历史（如果需要）
            if include_versions:
                self._export_version_history(temp_export_dir, exported_templates)
            
            # 导出配置文件
            self._export_global_configs(temp_export_dir)
            
            # 创建迁移清单
            manifest = self._create_migration_manifest(
                export_id, migration_mode, exported_templates, migration_filter
            )
            self._save_migration_manifest(temp_export_dir, manifest)
            
            # 压缩或复制到目标位置
            if compress:
                final_path = self._compress_export(temp_export_dir, export_path)
            else:
                final_path = export_path
                if final_path.exists():
                    shutil.rmtree(final_path)
                shutil.copytree(temp_export_dir, final_path)
            
            # 清理临时目录
            shutil.rmtree(temp_export_dir)
            
            # 更新结果
            result.export_path = str(final_path)
            result.total_templates = len(exported_templates)
            result.total_size_mb = round(total_size / 1024 / 1024, 2)
            result.file_size_mb = round(self._get_file_size(final_path) / 1024 / 1024, 2)
            
            result.mark_completed(True, f"成功导出 {len(exported_templates)} 个模板")
            
        except Exception as e:
            result.mark_completed(False, f"导出过程中发生错误: {str(e)}")
        
        return result
    
    def _get_filtered_templates(self, migration_filter: Optional[MigrationFilter]) -> List[Path]:
        """获取过滤后的模板列表"""
        all_templates = []
        
        # 扫描模板目录
        templates_dir = self.templates_root / "templates"
        if not templates_dir.exists():
            return all_templates
        
        # 递归查找模板目录
        for item in templates_dir.rglob("template.json"):
            template_dir = item.parent
            all_templates.append(template_dir)
        
        # 应用过滤器
        if migration_filter is None:
            return all_templates
        
        filtered_templates = []
        
        for template_path in all_templates:
            if self._matches_filter(template_path, migration_filter):
                filtered_templates.append(template_path)
        
        return filtered_templates
    
    def _matches_filter(self, template_path: Path, migration_filter: MigrationFilter) -> bool:
        """检查模板是否匹配过滤器"""
        try:
            # 加载模板配置
            config_path = template_path / "template.json"
            if not config_path.exists():
                return False
            
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            # 检查分类过滤
            if migration_filter.categories:
                template_category = config_data.get("category", "")
                if template_category not in migration_filter.categories:
                    return False
            
            # 检查模板类型过滤
            if migration_filter.template_types:
                template_type = config_data.get("template_type", "")
                if template_type not in migration_filter.template_types:
                    return False
            
            # 检查状态过滤
            if migration_filter.status_list:
                template_status = config_data.get("status", "")
                if template_status not in migration_filter.status_list:
                    return False
            
            # 检查标签过滤
            if migration_filter.tags:
                template_tags = config_data.get("tags", [])
                if not any(tag in template_tags for tag in migration_filter.tags):
                    return False
            
            # 检查大小限制
            if migration_filter.size_limit_mb:
                template_size = self._calculate_directory_size(template_path)
                size_mb = template_size / 1024 / 1024
                if size_mb > migration_filter.size_limit_mb:
                    return False
            
            # 检查排除模式
            if migration_filter.exclude_patterns:
                template_name = template_path.name
                for pattern in migration_filter.exclude_patterns:
                    if pattern in template_name:
                        return False
            
            # 检查包含模式
            if migration_filter.include_patterns:
                template_name = template_path.name
                if not any(pattern in template_name for pattern in migration_filter.include_patterns):
                    return False
            
            return True
            
        except Exception:
            return False
    
    def _calculate_directory_size(self, directory: Path) -> int:
        """计算目录大小"""
        total_size = 0
        
        try:
            for file_path in directory.rglob("*"):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
        except (OSError, FileNotFoundError):
            pass
        
        return total_size
    
    def _get_file_size(self, file_path: Path) -> int:
        """获取文件大小"""
        try:
            return file_path.stat().st_size
        except (OSError, FileNotFoundError):
            return 0
    
    def _export_version_history(self, export_dir: Path, template_names: List[str]):
        """导出版本历史"""
        versions_dir = export_dir / "versions"
        versions_dir.mkdir(parents=True, exist_ok=True)
        
        for template_name in template_names:
            try:
                # 复制版本历史
                source_version_dir = self.version_controller.versions_root / template_name
                if source_version_dir.exists():
                    target_version_dir = versions_dir / template_name
                    shutil.copytree(source_version_dir, target_version_dir)
            except Exception as e:
                print(f"导出版本历史失败 {template_name}: {e}")
    
    def _export_global_configs(self, export_dir: Path):
        """导出全局配置"""
        config_dir = export_dir / "config"
        config_dir.mkdir(parents=True, exist_ok=True)
        
        # 复制配置文件
        source_config_dir = self.templates_root / "config"
        if source_config_dir.exists():
            for config_file in source_config_dir.glob("*.yaml"):
                shutil.copy2(config_file, config_dir)
            for config_file in source_config_dir.glob("*.json"):
                shutil.copy2(config_file, config_dir)
    
    def _create_migration_manifest(
        self,
        export_id: str,
        migration_mode: MigrationMode,
        template_names: List[str],
        migration_filter: Optional[MigrationFilter]
    ) -> MigrationManifest:
        """创建迁移清单"""
        # 收集模板信息
        templates_info = []
        total_size = 0
        
        for template_name in template_names:
            template_path = self.templates_root / "templates" / template_name
            
            try:
                # 加载配置
                config_path = template_path / "template.json"
                with open(config_path, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                
                # 计算大小
                template_size = self._calculate_directory_size(template_path)
                total_size += template_size
                
                template_info = {
                    "name": template_name,
                    "id": config_data.get("id", template_name),
                    "category": config_data.get("category", ""),
                    "template_type": config_data.get("template_type", ""),
                    "status": config_data.get("status", ""),
                    "version": config_data.get("version", "1.0.0"),
                    "size_bytes": template_size,
                    "file_count": len(list(template_path.rglob("*")))
                }
                
                templates_info.append(template_info)
                
            except Exception as e:
                print(f"收集模板信息失败 {template_name}: {e}")
        
        return MigrationManifest(
            export_id=export_id,
            export_timestamp=datetime.now(),
            source_environment="local",
            migration_mode=migration_mode,
            templates=templates_info,
            total_templates=len(template_names),
            total_size_bytes=total_size,
            filter_criteria=migration_filter,
            created_by="migration_tool"
        )
    
    def _save_migration_manifest(self, export_dir: Path, manifest: MigrationManifest):
        """保存迁移清单"""
        manifest_path = export_dir / "migration_manifest.json"
        
        # 转换为字典
        manifest_data = asdict(manifest)
        manifest_data["export_timestamp"] = manifest.export_timestamp.isoformat()
        manifest_data["migration_mode"] = manifest.migration_mode.value
        
        # 处理过滤器
        if manifest.filter_criteria:
            filter_data = asdict(manifest.filter_criteria)
            if manifest.filter_criteria.date_range:
                start_date, end_date = manifest.filter_criteria.date_range
                filter_data["date_range"] = [start_date.isoformat(), end_date.isoformat()]
            manifest_data["filter_criteria"] = filter_data
        
        with open(manifest_path, 'w', encoding='utf-8') as f:
            json.dump(manifest_data, f, ensure_ascii=False, indent=2)
    
    def _compress_export(self, source_dir: Path, target_path: Path) -> Path:
        """压缩导出文件"""
        if not target_path.suffix:
            target_path = target_path.with_suffix('.zip')
        
        with zipfile.ZipFile(target_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in source_dir.rglob("*"):
                if file_path.is_file():
                    arcname = file_path.relative_to(source_dir)
                    zipf.write(file_path, arcname)
        
        return target_path
    
    def import_templates(
        self,
        import_path: Path,
        conflict_resolution: ConflictResolution = ConflictResolution.SKIP,
        validate_integrity: bool = True,
        create_backup: bool = True
    ) -> ImportResult:
        """导入模板库
        
        Args:
            import_path: 导入路径
            conflict_resolution: 冲突解决策略
            validate_integrity: 是否验证完整性
            create_backup: 是否创建备份
            
        Returns:
            导入结果
        """
        import_id = f"import_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        result = ImportResult(
            import_id=import_id,
            import_type="full",
            source_path=str(import_path),
            conflict_resolution=conflict_resolution.value
        )
        
        try:
            # 解压或复制到临时目录
            temp_import_dir = self.temp_dir / import_id
            temp_import_dir.mkdir(parents=True, exist_ok=True)
            
            if import_path.suffix == '.zip':
                self._extract_import(import_path, temp_import_dir)
            else:
                shutil.copytree(import_path, temp_import_dir, dirs_exist_ok=True)
            
            # 加载迁移清单
            manifest = self._load_migration_manifest(temp_import_dir)
            if manifest:
                result.total_templates = manifest.total_templates
            
            # 验证完整性
            if validate_integrity:
                integrity_check = self._validate_import_integrity(temp_import_dir, manifest)
                if not integrity_check["valid"]:
                    result.add_error(f"完整性验证失败: {integrity_check['error']}")
                    result.mark_completed(False, "导入验证失败")
                    return result
            
            # 创建备份
            if create_backup:
                self._create_import_backup()
            
            # 导入模板
            templates_dir = temp_import_dir / "templates"
            if templates_dir.exists():
                for template_dir in templates_dir.iterdir():
                    if template_dir.is_dir():
                        import_result = self._import_single_template(
                            template_dir, conflict_resolution
                        )
                        
                        if import_result["success"]:
                            result.add_imported_template(template_dir.name)
                        else:
                            result.add_failed_template(template_dir.name)
                            result.add_error(f"{template_dir.name}: {import_result['error']}")
                        
                        # 处理冲突
                        if "conflict" in import_result:
                            result.add_conflict(
                                template_dir.name,
                                import_result["conflict"]["type"],
                                import_result["conflict"]["details"]
                            )
            
            # 导入全局配置
            self._import_global_configs(temp_import_dir)
            
            # 导入版本历史
            self._import_version_history(temp_import_dir)
            
            # 清理临时目录
            shutil.rmtree(temp_import_dir)
            
            # 更新结果
            success_rate = (result.successful_imports / result.total_templates * 100) if result.total_templates > 0 else 0
            
            if result.failed_imports == 0:
                result.mark_completed(True, f"成功导入 {result.successful_imports} 个模板")
            else:
                result.mark_completed(
                    success_rate > 50,
                    f"导入完成，成功 {result.successful_imports} 个，失败 {result.failed_imports} 个"
                )
            
        except Exception as e:
            result.mark_completed(False, f"导入过程中发生错误: {str(e)}")
        
        return result
    
    def _extract_import(self, zip_path: Path, target_dir: Path):
        """解压导入文件"""
        with zipfile.ZipFile(zip_path, 'r') as zipf:
            zipf.extractall(target_dir)
    
    def _load_migration_manifest(self, import_dir: Path) -> Optional[MigrationManifest]:
        """加载迁移清单"""
        manifest_path = import_dir / "migration_manifest.json"
        
        if not manifest_path.exists():
            return None
        
        try:
            with open(manifest_path, 'r', encoding='utf-8') as f:
                manifest_data = json.load(f)
            
            # 处理日期时间
            if "export_timestamp" in manifest_data:
                manifest_data["export_timestamp"] = datetime.fromisoformat(
                    manifest_data["export_timestamp"]
                )
            
            # 处理枚举
            if "migration_mode" in manifest_data:
                manifest_data["migration_mode"] = MigrationMode(manifest_data["migration_mode"])
            
            # 处理过滤器
            if "filter_criteria" in manifest_data and manifest_data["filter_criteria"]:
                filter_data = manifest_data["filter_criteria"]
                if "date_range" in filter_data and filter_data["date_range"]:
                    start_str, end_str = filter_data["date_range"]
                    filter_data["date_range"] = (
                        datetime.fromisoformat(start_str),
                        datetime.fromisoformat(end_str)
                    )
                manifest_data["filter_criteria"] = MigrationFilter(**filter_data)
            
            return MigrationManifest(**manifest_data)
            
        except Exception as e:
            print(f"加载迁移清单失败: {e}")
            return None
    
    def _validate_import_integrity(
        self,
        import_dir: Path,
        manifest: Optional[MigrationManifest]
    ) -> Dict[str, Any]:
        """验证导入完整性"""
        if not manifest:
            return {"valid": False, "error": "缺少迁移清单"}
        
        # 检查模板文件
        templates_dir = import_dir / "templates"
        if not templates_dir.exists():
            return {"valid": False, "error": "缺少模板目录"}
        
        # 验证模板数量
        actual_templates = len([d for d in templates_dir.iterdir() if d.is_dir()])
        if actual_templates != manifest.total_templates:
            return {
                "valid": False,
                "error": f"模板数量不匹配，期望 {manifest.total_templates}，实际 {actual_templates}"
            }
        
        # 验证每个模板
        for template_info in manifest.templates:
            template_name = template_info["name"]
            template_dir = templates_dir / template_name
            
            if not template_dir.exists():
                return {"valid": False, "error": f"模板目录不存在: {template_name}"}
            
            # 检查配置文件
            config_path = template_dir / "template.json"
            if not config_path.exists():
                return {"valid": False, "error": f"模板配置文件不存在: {template_name}"}
        
        return {"valid": True}
    
    def _create_import_backup(self):
        """创建导入前备份"""
        backup_dir = self.templates_root / f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        try:
            # 备份模板目录
            templates_dir = self.templates_root / "templates"
            if templates_dir.exists():
                shutil.copytree(templates_dir, backup_dir / "templates")
            
            # 备份配置目录
            config_dir = self.templates_root / "config"
            if config_dir.exists():
                shutil.copytree(config_dir, backup_dir / "config")
            
            print(f"创建备份: {backup_dir}")
            
        except Exception as e:
            print(f"创建备份失败: {e}")
    
    def _import_single_template(
        self,
        template_dir: Path,
        conflict_resolution: ConflictResolution
    ) -> Dict[str, Any]:
        """导入单个模板"""
        template_name = template_dir.name
        target_path = self.templates_root / "templates" / template_name
        
        result = {"success": False, "error": ""}
        
        try:
            # 检查冲突
            if target_path.exists():
                conflict_info = {
                    "type": "template_exists",
                    "details": {
                        "existing_path": str(target_path),
                        "import_path": str(template_dir)
                    }
                }
                
                if conflict_resolution == ConflictResolution.SKIP:
                    result["conflict"] = conflict_info
                    result["error"] = "模板已存在，跳过导入"
                    return result
                
                elif conflict_resolution == ConflictResolution.RENAME:
                    # 重命名新模板
                    counter = 1
                    while target_path.exists():
                        new_name = f"{template_name}_{counter}"
                        target_path = self.templates_root / "templates" / new_name
                        counter += 1
                    
                    conflict_info["details"]["renamed_to"] = str(target_path)
                    result["conflict"] = conflict_info
                
                elif conflict_resolution == ConflictResolution.OVERWRITE:
                    # 删除现有模板
                    shutil.rmtree(target_path)
                    conflict_info["details"]["action"] = "overwritten"
                    result["conflict"] = conflict_info
                
                elif conflict_resolution == ConflictResolution.MERGE:
                    # 合并配置（简单实现）
                    merge_result = self._merge_template_configs(template_dir, target_path)
                    if not merge_result["success"]:
                        result["error"] = f"合并失败: {merge_result['error']}"
                        return result
                    
                    conflict_info["details"]["action"] = "merged"
                    result["conflict"] = conflict_info
            
            # 复制模板文件
            target_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(template_dir, target_path, dirs_exist_ok=True)
            
            # 验证导入的模板
            validation_result = self._validate_imported_template(target_path)
            if not validation_result["valid"]:
                result["error"] = f"模板验证失败: {validation_result['error']}"
                # 清理失败的导入
                if target_path.exists():
                    shutil.rmtree(target_path)
                return result
            
            result["success"] = True
            
        except Exception as e:
            result["error"] = str(e)
        
        return result
    
    def _merge_template_configs(self, source_dir: Path, target_dir: Path) -> Dict[str, Any]:
        """合并模板配置"""
        try:
            source_config_path = source_dir / "template.json"
            target_config_path = target_dir / "template.json"
            
            if not source_config_path.exists() or not target_config_path.exists():
                return {"success": False, "error": "配置文件不存在"}
            
            # 加载配置
            with open(source_config_path, 'r', encoding='utf-8') as f:
                source_config = json.load(f)
            
            with open(target_config_path, 'r', encoding='utf-8') as f:
                target_config = json.load(f)
            
            # 简单合并策略：合并标签和关键词
            if "tags" in source_config:
                target_tags = target_config.get("tags", [])
                merged_tags = list(set(target_tags + source_config["tags"]))
                target_config["tags"] = merged_tags
            
            if "keywords" in source_config:
                target_keywords = target_config.get("keywords", [])
                merged_keywords = list(set(target_keywords + source_config["keywords"]))
                target_config["keywords"] = merged_keywords
            
            # 更新版本和时间戳
            target_config["updated_at"] = datetime.now().isoformat()
            
            # 保存合并后的配置
            with open(target_config_path, 'w', encoding='utf-8') as f:
                json.dump(target_config, f, ensure_ascii=False, indent=2)
            
            return {"success": True}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _validate_imported_template(self, template_path: Path) -> Dict[str, Any]:
        """验证导入的模板"""
        try:
            # 检查配置文件
            config_path = template_path / "template.json"
            if not config_path.exists():
                return {"valid": False, "error": "缺少配置文件"}
            
            # 验证配置格式
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            # 检查必需字段
            required_fields = ["id", "name", "category", "template_type", "status"]
            for field in required_fields:
                if field not in config_data:
                    return {"valid": False, "error": f"缺少必需字段: {field}"}
            
            # 使用配置管理器验证
            if self.config_manager:
                is_valid, errors = self.config_manager.validate_config(config_data)
                if not is_valid:
                    return {"valid": False, "error": "; ".join(errors)}
            
            return {"valid": True}
            
        except Exception as e:
            return {"valid": False, "error": str(e)}
    
    def _import_global_configs(self, import_dir: Path):
        """导入全局配置"""
        source_config_dir = import_dir / "config"
        target_config_dir = self.templates_root / "config"
        
        if not source_config_dir.exists():
            return
        
        try:
            target_config_dir.mkdir(parents=True, exist_ok=True)
            
            for config_file in source_config_dir.glob("*"):
                if config_file.is_file():
                    target_file = target_config_dir / config_file.name
                    
                    # 检查是否需要合并
                    if target_file.exists() and config_file.suffix in ['.yaml', '.yml', '.json']:
                        # 简单策略：备份现有文件
                        backup_file = target_file.with_suffix(f".backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}{target_file.suffix}")
                        shutil.copy2(target_file, backup_file)
                    
                    shutil.copy2(config_file, target_file)
            
        except Exception as e:
            print(f"导入全局配置失败: {e}")
    
    def _import_version_history(self, import_dir: Path):
        """导入版本历史"""
        source_versions_dir = import_dir / "versions"
        
        if not source_versions_dir.exists():
            return
        
        try:
            for template_version_dir in source_versions_dir.iterdir():
                if template_version_dir.is_dir():
                    template_name = template_version_dir.name
                    target_version_dir = self.version_controller.versions_root / template_name
                    
                    # 合并版本历史
                    if target_version_dir.exists():
                        # 复制新版本文件
                        for version_file in template_version_dir.glob("*.json"):
                            target_file = target_version_dir / version_file.name
                            if not target_file.exists():
                                shutil.copy2(version_file, target_file)
                    else:
                        # 直接复制整个目录
                        shutil.copytree(template_version_dir, target_version_dir)
            
        except Exception as e:
            print(f"导入版本历史失败: {e}")
    
    def migrate_between_environments(
        self,
        source_env: str,
        target_env: str,
        migration_filter: Optional[MigrationFilter] = None
    ) -> BatchResult:
        """环境间迁移
        
        Args:
            source_env: 源环境
            target_env: 目标环境
            migration_filter: 迁移过滤器
            
        Returns:
            批量操作结果
        """
        # 这是一个框架方法，实际实现需要根据具体的环境配置
        # 例如：不同的数据库连接、文件系统路径等
        
        operation_id = f"migrate_{source_env}_to_{target_env}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # 创建批量操作结果
        from ..models.operations import BatchOperation
        
        batch_op = BatchOperation(
            operation_id=operation_id,
            operation_type=OperationType.EXPORT,
            description=f"从 {source_env} 迁移到 {target_env}"
        )
        
        result = BatchResult(batch_operation=batch_op)
        
        try:
            # 1. 导出源环境数据
            temp_export_path = self.temp_dir / f"migration_{operation_id}.zip"
            export_result = self.export_templates(
                temp_export_path,
                migration_filter,
                MigrationMode.SELECTIVE
            )
            
            if not export_result.success:
                result.overall_status = OperationStatus.FAILED
                return result
            
            # 2. 导入到目标环境
            # 注意：这里需要目标环境的MigrationTool实例
            # 实际实现中可能需要通过网络API或其他方式进行
            
            # 3. 验证迁移结果
            
            result.overall_status = OperationStatus.SUCCESS
            
        except Exception as e:
            result.overall_status = OperationStatus.FAILED
        
        result.mark_completed()
        return result
    
    def get_migration_statistics(self) -> Dict[str, Any]:
        """获取迁移统计信息"""
        stats = {
            "total_templates": 0,
            "categories": {},
            "template_types": {},
            "status_distribution": {},
            "total_size_mb": 0.0,
            "average_template_size_mb": 0.0
        }
        
        try:
            templates = self._get_filtered_templates(None)
            stats["total_templates"] = len(templates)
            
            total_size = 0
            
            for template_path in templates:
                # 计算大小
                template_size = self._calculate_directory_size(template_path)
                total_size += template_size
                
                # 加载配置统计
                try:
                    config_path = template_path / "template.json"
                    with open(config_path, 'r', encoding='utf-8') as f:
                        config_data = json.load(f)
                    
                    # 统计分类
                    category = config_data.get("category", "未分类")
                    stats["categories"][category] = stats["categories"].get(category, 0) + 1
                    
                    # 统计类型
                    template_type = config_data.get("template_type", "未知")
                    stats["template_types"][template_type] = stats["template_types"].get(template_type, 0) + 1
                    
                    # 统计状态
                    status = config_data.get("status", "未知")
                    stats["status_distribution"][status] = stats["status_distribution"].get(status, 0) + 1
                    
                except Exception:
                    continue
            
            stats["total_size_mb"] = round(total_size / 1024 / 1024, 2)
            if stats["total_templates"] > 0:
                stats["average_template_size_mb"] = round(
                    stats["total_size_mb"] / stats["total_templates"], 2
                )
            
        except Exception as e:
            stats["error"] = str(e)
        
        return stats