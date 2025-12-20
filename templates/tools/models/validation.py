"""
验证相关的数据模型
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Callable
import re


class ValidationLevel(Enum):
    """验证级别"""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class ValidationCategory(Enum):
    """验证类别"""
    STRUCTURE = "structure"
    CONFIG = "config"
    IMAGE = "image"
    NAMING = "naming"
    CONTENT = "content"
    QUALITY = "quality"


@dataclass
class ValidationError:
    """验证错误"""
    level: ValidationLevel
    category: ValidationCategory
    code: str
    message: str
    field: Optional[str] = None
    value: Optional[Any] = None
    suggestion: Optional[str] = None
    
    def __post_init__(self):
        """初始化后处理"""
        if isinstance(self.level, str):
            self.level = ValidationLevel(self.level)
        if isinstance(self.category, str):
            self.category = ValidationCategory(self.category)
    
    @property
    def is_error(self) -> bool:
        """是否为错误级别"""
        return self.level == ValidationLevel.ERROR
    
    @property
    def is_warning(self) -> bool:
        """是否为警告级别"""
        return self.level == ValidationLevel.WARNING
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "level": self.level.value,
            "category": self.category.value,
            "code": self.code,
            "message": self.message,
            "field": self.field,
            "value": self.value,
            "suggestion": self.suggestion
        }


@dataclass
class ValidationRule:
    """验证规则"""
    name: str
    category: ValidationCategory
    description: str
    validator: Callable[[Any], List[ValidationError]]
    required: bool = True
    enabled: bool = True
    
    def validate(self, value: Any) -> List[ValidationError]:
        """执行验证"""
        if not self.enabled:
            return []
        
        try:
            return self.validator(value)
        except Exception as e:
            return [ValidationError(
                level=ValidationLevel.ERROR,
                category=self.category,
                code="VALIDATION_EXCEPTION",
                message=f"验证规则 '{self.name}' 执行失败: {str(e)}"
            )]


@dataclass
class ValidationResult:
    """验证结果"""
    is_valid: bool
    errors: List[ValidationError] = field(default_factory=list)
    warnings: List[ValidationError] = field(default_factory=list)
    info: List[ValidationError] = field(default_factory=list)
    
    # 验证统计
    total_checks: int = 0
    passed_checks: int = 0
    failed_checks: int = 0
    
    # 验证时间
    validation_time: datetime = field(default_factory=datetime.now)
    duration_ms: float = 0.0
    
    def add_error(self, error: ValidationError):
        """添加错误"""
        if error.level == ValidationLevel.ERROR:
            self.errors.append(error)
            self.failed_checks += 1
        elif error.level == ValidationLevel.WARNING:
            self.warnings.append(error)
        else:
            self.info.append(error)
        
        self.total_checks += 1
        self._update_validity()
    
    def add_errors(self, errors: List[ValidationError]):
        """批量添加错误"""
        for error in errors:
            self.add_error(error)
    
    def _update_validity(self):
        """更新有效性状态"""
        self.is_valid = len(self.errors) == 0
        self.passed_checks = self.total_checks - self.failed_checks
    
    @property
    def has_errors(self) -> bool:
        """是否有错误"""
        return len(self.errors) > 0
    
    @property
    def has_warnings(self) -> bool:
        """是否有警告"""
        return len(self.warnings) > 0
    
    @property
    def error_count(self) -> int:
        """错误数量"""
        return len(self.errors)
    
    @property
    def warning_count(self) -> int:
        """警告数量"""
        return len(self.warnings)
    
    @property
    def success_rate(self) -> float:
        """成功率"""
        if self.total_checks == 0:
            return 100.0
        return (self.passed_checks / self.total_checks) * 100
    
    def get_errors_by_category(self, category: ValidationCategory) -> List[ValidationError]:
        """按类别获取错误"""
        return [error for error in self.errors if error.category == category]
    
    def get_warnings_by_category(self, category: ValidationCategory) -> List[ValidationError]:
        """按类别获取警告"""
        return [warning for warning in self.warnings if warning.category == category]
    
    def get_summary(self) -> Dict[str, Any]:
        """获取验证摘要"""
        return {
            "is_valid": self.is_valid,
            "total_checks": self.total_checks,
            "passed_checks": self.passed_checks,
            "failed_checks": self.failed_checks,
            "success_rate": self.success_rate,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "validation_time": self.validation_time.isoformat(),
            "duration_ms": self.duration_ms
        }
    
    def get_detailed_report(self) -> Dict[str, Any]:
        """获取详细报告"""
        return {
            "summary": self.get_summary(),
            "errors": [error.to_dict() for error in self.errors],
            "warnings": [warning.to_dict() for warning in self.warnings],
            "info": [info.to_dict() for info in self.info],
            "errors_by_category": {
                category.value: len(self.get_errors_by_category(category))
                for category in ValidationCategory
            },
            "warnings_by_category": {
                category.value: len(self.get_warnings_by_category(category))
                for category in ValidationCategory
            }
        }


class CommonValidators:
    """常用验证器"""
    
    @staticmethod
    def validate_template_name(name: str) -> List[ValidationError]:
        """验证模板名称"""
        errors = []
        
        if not name:
            errors.append(ValidationError(
                level=ValidationLevel.ERROR,
                category=ValidationCategory.NAMING,
                code="EMPTY_NAME",
                message="模板名称不能为空"
            ))
            return errors
        
        # 检查长度
        if len(name) < 3:
            errors.append(ValidationError(
                level=ValidationLevel.ERROR,
                category=ValidationCategory.NAMING,
                code="NAME_TOO_SHORT",
                message="模板名称至少需要3个字符",
                value=name
            ))
        
        if len(name) > 50:
            errors.append(ValidationError(
                level=ValidationLevel.ERROR,
                category=ValidationCategory.NAMING,
                code="NAME_TOO_LONG",
                message="模板名称不能超过50个字符",
                value=name
            ))
        
        # 检查格式
        pattern = r'^[a-z][a-z0-9_]*[a-z0-9]$'$'
        if not re.match(pattern, name):
            errors.append(ValidationError(
                level=ValidationLevel.ERROR,
                category=ValidationCategory.NAMING,
                code="INVALID_NAME_FORMAT",
                message="模板名称必须以字母开头，只能包含小写字母、数字和下划线",
                value=name,
                suggestion="使用kebab-case格式，如: tech_modern"
            ))
        
        return errors
    
    @staticmethod
    def validate_image_dimensions(width: int, height: int, expected_width: int, expected_height: int, tolerance: int = 0) -> List[ValidationError]:
        """验证图片尺寸"""
        errors = []
        
        width_diff = abs(width - expected_width)
        height_diff = abs(height - expected_height)
        
        if width_diff > tolerance:
            errors.append(ValidationError(
                level=ValidationLevel.ERROR,
                category=ValidationCategory.IMAGE,
                code="INVALID_WIDTH",
                message=f"图片宽度不符合要求: 实际{width}px, 期望{expected_width}px",
                value=width
            ))
        
        if height_diff > tolerance:
            errors.append(ValidationError(
                level=ValidationLevel.ERROR,
                category=ValidationCategory.IMAGE,
                code="INVALID_HEIGHT",
                message=f"图片高度不符合要求: 实际{height}px, 期望{expected_height}px",
                value=height
            ))
        
        return errors
    
    @staticmethod
    def validate_required_fields(data: Dict[str, Any], required_fields: List[str]) -> List[ValidationError]:
        """验证必填字段"""
        errors = []
        
        for field in required_fields:
            if field not in data:
                errors.append(ValidationError(
                    level=ValidationLevel.ERROR,
                    category=ValidationCategory.CONFIG,
                    code="MISSING_REQUIRED_FIELD",
                    message=f"缺少必填字段: {field}",
                    field=field
                ))
            elif data[field] is None or (isinstance(data[field], str) and not data[field].strip()):
                errors.append(ValidationError(
                    level=ValidationLevel.ERROR,
                    category=ValidationCategory.CONFIG,
                    code="EMPTY_REQUIRED_FIELD",
                    message=f"必填字段不能为空: {field}",
                    field=field,
                    value=data[field]
                ))
        
        return errors
    
    @staticmethod
    def validate_file_structure(files: List[str], required_files: List[str], required_dirs: List[str]) -> List[ValidationError]:
        """验证文件结构"""
        errors = []
        
        # 检查必需文件
        for required_file in required_files:
            if required_file not in files:
                errors.append(ValidationError(
                    level=ValidationLevel.ERROR,
                    category=ValidationCategory.STRUCTURE,
                    code="MISSING_REQUIRED_FILE",
                    message=f"缺少必需文件: {required_file}",
                    field=required_file
                ))
        
        # 检查必需目录
        dirs = [f for f in files if f.endswith('/')]
        for required_dir in required_dirs:
            dir_path = required_dir if required_dir.endswith('/') else required_dir + '/'
            if dir_path not in dirs:
                errors.append(ValidationError(
                    level=ValidationLevel.ERROR,
                    category=ValidationCategory.STRUCTURE,
                    code="MISSING_REQUIRED_DIRECTORY",
                    message=f"缺少必需目录: {required_dir}",
                    field=required_dir
                ))
        
        return errors