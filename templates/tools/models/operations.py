"""
操作相关的数据模型
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Union


class OperationType(Enum):
    """操作类型"""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    MOVE = "move"
    COPY = "copy"
    VALIDATE = "validate"
    EXPORT = "export"
    IMPORT = "import"


class OperationStatus(Enum):
    """操作状态"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PARTIAL_SUCCESS = "partial_success"


@dataclass
class OperationResult:
    """单个操作结果"""
    operation_id: str
    operation_type: OperationType
    status: OperationStatus
    
    # 目标信息
    target: str
    target_type: str = "template"
    
    # 结果信息
    success: bool = False
    message: str = ""
    error_code: Optional[str] = None
    
    # 详细信息
    details: Dict[str, Any] = field(default_factory=dict)
    
    # 时间信息
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    duration_ms: float = 0.0
    
    def __post_init__(self):
        """初始化后处理"""
        if isinstance(self.operation_type, str):
            self.operation_type = OperationType(self.operation_type)
        if isinstance(self.status, str):
            self.status = OperationStatus(self.status)
    
    def mark_success(self, message: str = "", details: Dict[str, Any] = None):
        """标记为成功"""
        self.status = OperationStatus.SUCCESS
        self.success = True
        self.message = message
        self.completed_at = datetime.now()
        if details:
            self.details.update(details)
        self._calculate_duration()
    
    def mark_failed(self, message: str = "", error_code: str = None, details: Dict[str, Any] = None):
        """标记为失败"""
        self.status = OperationStatus.FAILED
        self.success = False
        self.message = message
        self.error_code = error_code
        self.completed_at = datetime.now()
        if details:
            self.details.update(details)
        self._calculate_duration()
    
    def _calculate_duration(self):
        """计算执行时长"""
        if self.completed_at:
            delta = self.completed_at - self.started_at
            self.duration_ms = delta.total_seconds() * 1000
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "operation_id": self.operation_id,
            "operation_type": self.operation_type.value,
            "status": self.status.value,
            "target": self.target,
            "target_type": self.target_type,
            "success": self.success,
            "message": self.message,
            "error_code": self.error_code,
            "details": self.details,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_ms": self.duration_ms
        }


@dataclass
class BatchOperation:
    """批量操作"""
    operation_id: str
    operation_type: OperationType
    description: str
    
    # 目标列表
    targets: List[str] = field(default_factory=list)
    
    # 操作参数
    parameters: Dict[str, Any] = field(default_factory=dict)
    
    # 执行选项
    continue_on_error: bool = True
    max_parallel: int = 1
    timeout_seconds: int = 300
    
    # 进度跟踪
    total_items: int = 0
    processed_items: int = 0
    successful_items: int = 0
    failed_items: int = 0
    
    def __post_init__(self):
        """初始化后处理"""
        if isinstance(self.operation_type, str):
            self.operation_type = OperationType(self.operation_type)
        self.total_items = len(self.targets)
    
    @property
    def progress_percentage(self) -> float:
        """获取进度百分比"""
        if self.total_items == 0:
            return 0.0
        return (self.processed_items / self.total_items) * 100
    
    @property
    def success_rate(self) -> float:
        """获取成功率"""
        if self.processed_items == 0:
            return 0.0
        return (self.successful_items / self.processed_items) * 100
    
    def add_target(self, target: str):
        """添加目标"""
        if target not in self.targets:
            self.targets.append(target)
            self.total_items = len(self.targets)
    
    def remove_target(self, target: str):
        """移除目标"""
        if target in self.targets:
            self.targets.remove(target)
            self.total_items = len(self.targets)
    
    def update_progress(self, processed: int = 1, successful: bool = True):
        """更新进度"""
        self.processed_items += processed
        if successful:
            self.successful_items += processed
        else:
            self.failed_items += processed


@dataclass
class BatchResult:
    """批量操作结果"""
    batch_operation: BatchOperation
    results: List[OperationResult] = field(default_factory=list)
    
    # 整体状态
    overall_status: OperationStatus = OperationStatus.PENDING
    
    # 时间信息
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    total_duration_ms: float = 0.0
    
    # 统计信息
    summary: Dict[str, Any] = field(default_factory=dict)
    
    def add_result(self, result: OperationResult):
        """添加操作结果"""
        self.results.append(result)
        self._update_summary()
    
    def _update_summary(self):
        """更新统计摘要"""
        total = len(self.results)
        successful = sum(1 for r in self.results if r.success)
        failed = total - successful
        
        self.summary = {
            "total_operations": total,
            "successful_operations": successful,
            "failed_operations": failed,
            "success_rate": (successful / total * 100) if total > 0 else 0.0,
            "average_duration_ms": sum(r.duration_ms for r in self.results) / total if total > 0 else 0.0
        }
        
        # 更新整体状态
        if total == 0:
            self.overall_status = OperationStatus.PENDING
        elif failed == 0:
            self.overall_status = OperationStatus.SUCCESS
        elif successful == 0:
            self.overall_status = OperationStatus.FAILED
        else:
            self.overall_status = OperationStatus.PARTIAL_SUCCESS
    
    def mark_completed(self):
        """标记为完成"""
        self.completed_at = datetime.now()
        if self.completed_at:
            delta = self.completed_at - self.started_at
            self.total_duration_ms = delta.total_seconds() * 1000
        self._update_summary()
    
    def get_failed_results(self) -> List[OperationResult]:
        """获取失败的结果"""
        return [result for result in self.results if not result.success]
    
    def get_successful_results(self) -> List[OperationResult]:
        """获取成功的结果"""
        return [result for result in self.results if result.success]
    
    def get_results_by_type(self, operation_type: OperationType) -> List[OperationResult]:
        """按操作类型获取结果"""
        return [result for result in self.results if result.operation_type == operation_type]
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "batch_operation": {
                "operation_id": self.batch_operation.operation_id,
                "operation_type": self.batch_operation.operation_type.value,
                "description": self.batch_operation.description,
                "total_items": self.batch_operation.total_items,
                "progress_percentage": self.batch_operation.progress_percentage,
                "success_rate": self.batch_operation.success_rate
            },
            "overall_status": self.overall_status.value,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "total_duration_ms": self.total_duration_ms,
            "summary": self.summary,
            "results": [result.to_dict() for result in self.results],
            "failed_operations": len(self.get_failed_results()),
            "successful_operations": len(self.get_successful_results())
        }


@dataclass
class ExportResult:
    """导出结果"""
    export_id: str
    export_type: str  # full, selective, category, etc.
    
    # 导出信息
    exported_templates: List[str] = field(default_factory=list)
    export_path: Optional[str] = None
    file_size_mb: float = 0.0
    
    # 导出统计
    total_templates: int = 0
    total_files: int = 0
    total_size_mb: float = 0.0
    
    # 状态信息
    success: bool = False
    message: str = ""
    errors: List[str] = field(default_factory=list)
    
    # 时间信息
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    
    def add_template(self, template_id: str):
        """添加导出的模板"""
        if template_id not in self.exported_templates:
            self.exported_templates.append(template_id)
            self.total_templates = len(self.exported_templates)
    
    def add_error(self, error: str):
        """添加错误"""
        self.errors.append(error)
    
    def mark_completed(self, success: bool = True, message: str = ""):
        """标记完成"""
        self.success = success
        self.message = message
        self.completed_at = datetime.now()


@dataclass
class ImportResult:
    """导入结果"""
    import_id: str
    import_type: str
    source_path: str
    
    # 导入信息
    imported_templates: List[str] = field(default_factory=list)
    skipped_templates: List[str] = field(default_factory=list)
    failed_templates: List[str] = field(default_factory=list)
    
    # 冲突处理
    conflicts: List[Dict[str, Any]] = field(default_factory=list)
    conflict_resolution: str = "skip"  # skip, overwrite, rename
    
    # 导入统计
    total_templates: int = 0
    successful_imports: int = 0
    failed_imports: int = 0
    
    # 状态信息
    success: bool = False
    message: str = ""
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    # 时间信息
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    
    def add_imported_template(self, template_id: str):
        """添加成功导入的模板"""
        if template_id not in self.imported_templates:
            self.imported_templates.append(template_id)
            self.successful_imports = len(self.imported_templates)
    
    def add_failed_template(self, template_id: str):
        """添加导入失败的模板"""
        if template_id not in self.failed_templates:
            self.failed_templates.append(template_id)
            self.failed_imports = len(self.failed_templates)
    
    def add_skipped_template(self, template_id: str):
        """添加跳过的模板"""
        if template_id not in self.skipped_templates:
            self.skipped_templates.append(template_id)
    
    def add_conflict(self, template_id: str, conflict_type: str, details: Dict[str, Any]):
        """添加冲突"""
        conflict = {
            "template_id": template_id,
            "conflict_type": conflict_type,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }
        self.conflicts.append(conflict)
    
    def add_error(self, error: str):
        """添加错误"""
        self.errors.append(error)
    
    def add_warning(self, warning: str):
        """添加警告"""
        self.warnings.append(warning)
    
    def mark_completed(self, success: bool = True, message: str = ""):
        """标记完成"""
        self.success = success
        self.message = message
        self.completed_at = datetime.now()