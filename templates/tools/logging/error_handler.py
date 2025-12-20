#!/usr/bin/env python3
"""
统一错误处理系统 - 实现统一的错误处理和恢复机制
Unified Error Handling System - Implement unified error handling and recovery mechanisms
"""

import sys
import traceback
import logging
import json
from typing import Dict, Any, Optional, List, Callable, Type
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path

class ErrorSeverity(Enum):
    """错误严重程度"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ErrorCategory(Enum):
    """错误分类"""
    VALIDATION = "validation"
    FILE_SYSTEM = "file_system"
    CONFIGURATION = "configuration"
    BUSINESS_LOGIC = "business_logic"
    SYSTEM = "system"
    NETWORK = "network"
    PERMISSION = "permission"

@dataclass
class ErrorInfo:
    """错误信息"""
    error_id: str
    category: ErrorCategory
    severity: ErrorSeverity
    message: str
    details: str
    timestamp: datetime
    context: Dict[str, Any]
    stack_trace: Optional[str] = None
    recovery_suggestions: List[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        data['category'] = self.category.value
        data['severity'] = self.severity.value
        data['timestamp'] = self.timestamp.isoformat()
        return data

class TemplateLibraryError(Exception):
    """模板库基础异常"""
    
    def __init__(self, message: str, category: ErrorCategory = ErrorCategory.SYSTEM,
                 severity: ErrorSeverity = ErrorSeverity.MEDIUM, context: Dict[str, Any] = None):
        super().__init__(message)
        self.message = message
        self.category = category
        self.severity = severity
        self.context = context or {}
        self.timestamp = datetime.now()

class ValidationError(TemplateLibraryError):
    """验证错误"""
    
    def __init__(self, message: str, field: str = None, value: Any = None, **kwargs):
        super().__init__(message, ErrorCategory.VALIDATION, ErrorSeverity.MEDIUM, **kwargs)
        self.field = field
        self.value = value

class FileSystemError(TemplateLibraryError):
    """文件系统错误"""
    
    def __init__(self, message: str, file_path: str = None, operation: str = None, **kwargs):
        super().__init__(message, ErrorCategory.FILE_SYSTEM, ErrorSeverity.HIGH, **kwargs)
        self.file_path = file_path
        self.operation = operation

class ConfigurationError(TemplateLibraryError):
    """配置错误"""
    
    def __init__(self, message: str, config_file: str = None, config_key: str = None, **kwargs):
        super().__init__(message, ErrorCategory.CONFIGURATION, ErrorSeverity.HIGH, **kwargs)
        self.config_file = config_file
        self.config_key = config_key

class BusinessLogicError(TemplateLibraryError):
    """业务逻辑错误"""
    
    def __init__(self, message: str, operation: str = None, **kwargs):
        super().__init__(message, ErrorCategory.BUSINESS_LOGIC, ErrorSeverity.MEDIUM, **kwargs)
        self.operation = operation

class ErrorRecoveryStrategy:
    """错误恢复策略"""
    
    def __init__(self, name: str, description: str, recovery_func: Callable):
        self.name = name
        self.description = description
        self.recovery_func = recovery_func
    
    def execute(self, error_info: ErrorInfo, context: Dict[str, Any] = None) -> bool:
        """执行恢复策略"""
        try:
            return self.recovery_func(error_info, context or {})
        except Exception:
            return False

class ErrorHandler:
    """统一错误处理器"""
    
    def __init__(self, log_dir: Path = None):
        self.log_dir = log_dir or Path('logs')
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        self.error_log = []
        self.recovery_strategies = {}
        self.error_callbacks = {}
        
        # 设置日志记录器
        self.logger = self._setup_logger()
        
        # 注册默认恢复策略
        self._register_default_strategies()
    
    def _setup_logger(self) -> logging.Logger:
        """设置日志记录器"""
        logger = logging.getLogger('template_library_error_handler')
        logger.setLevel(logging.DEBUG)
        
        # 清除现有处理器
        logger.handlers.clear()
        
        # 文件处理器
        file_handler = logging.FileHandler(
            self.log_dir / 'error.log',
            encoding='utf-8'
        )
        file_handler.setLevel(logging.ERROR)
        
        # 控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.WARNING)
        
        # 格式化器
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        return logger
    
    def _register_default_strategies(self):
        """注册默认恢复策略"""
        
        def retry_file_operation(error_info: ErrorInfo, context: Dict[str, Any]) -> bool:
            """重试文件操作"""
            if error_info.category != ErrorCategory.FILE_SYSTEM:
                return False
            
            retry_count = context.get('retry_count', 0)
            max_retries = context.get('max_retries', 3)
            
            if retry_count >= max_retries:
                return False
            
            # 这里可以实现具体的重试逻辑
            return True
        
        def create_missing_directory(error_info: ErrorInfo, context: Dict[str, Any]) -> bool:
            """创建缺失的目录"""
            if 'directory not found' in error_info.message.lower():
                try:
                    file_path = context.get('file_path')
                    if file_path:
                        Path(file_path).parent.mkdir(parents=True, exist_ok=True)
                        return True
                except Exception:
                    pass
            return False
        
        def reset_configuration(error_info: ErrorInfo, context: Dict[str, Any]) -> bool:
            """重置配置"""
            if error_info.category == ErrorCategory.CONFIGURATION:
                # 这里可以实现配置重置逻辑
                return True
            return False
        
        self.register_recovery_strategy(
            ErrorCategory.FILE_SYSTEM,
            ErrorRecoveryStrategy("retry_operation", "重试文件操作", retry_file_operation)
        )
        
        self.register_recovery_strategy(
            ErrorCategory.FILE_SYSTEM,
            ErrorRecoveryStrategy("create_directory", "创建缺失目录", create_missing_directory)
        )
        
        self.register_recovery_strategy(
            ErrorCategory.CONFIGURATION,
            ErrorRecoveryStrategy("reset_config", "重置配置", reset_configuration)
        )
    
    def register_recovery_strategy(self, category: ErrorCategory, strategy: ErrorRecoveryStrategy):
        """注册恢复策略"""
        if category not in self.recovery_strategies:
            self.recovery_strategies[category] = []
        self.recovery_strategies[category].append(strategy)
    
    def register_error_callback(self, error_type: Type[Exception], callback: Callable):
        """注册错误回调"""
        self.error_callbacks[error_type] = callback
    
    def handle_error(self, error: Exception, context: Dict[str, Any] = None,
                    auto_recover: bool = True) -> ErrorInfo:
        """处理错误"""
        
        # 生成错误ID
        error_id = f"ERR_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{id(error)}"
        
        # 确定错误分类和严重程度
        if isinstance(error, TemplateLibraryError):
            category = error.category
            severity = error.severity
            message = error.message
            error_context = error.context
        else:
            category = self._classify_error(error)
            severity = self._assess_severity(error)
            message = str(error)
            error_context = {}
        
        # 合并上下文
        if context:
            error_context.update(context)
        
        # 创建错误信息
        error_info = ErrorInfo(
            error_id=error_id,
            category=category,
            severity=severity,
            message=message,
            details=self._get_error_details(error),
            timestamp=datetime.now(),
            context=error_context,
            stack_trace=traceback.format_exc(),
            recovery_suggestions=self._get_recovery_suggestions(category, error)
        )
        
        # 记录错误
        self._log_error(error_info)
        
        # 执行错误回调
        self._execute_callbacks(error, error_info)
        
        # 尝试自动恢复
        if auto_recover:
            self._attempt_recovery(error_info)
        
        return error_info
    
    def _classify_error(self, error: Exception) -> ErrorCategory:
        """分类错误"""
        error_type = type(error).__name__.lower()
        error_message = str(error).lower()
        
        if 'file' in error_type or 'io' in error_type or 'path' in error_message:
            return ErrorCategory.FILE_SYSTEM
        elif 'permission' in error_message or 'access' in error_message:
            return ErrorCategory.PERMISSION
        elif 'config' in error_message or 'setting' in error_message:
            return ErrorCategory.CONFIGURATION
        elif 'network' in error_message or 'connection' in error_message:
            return ErrorCategory.NETWORK
        elif 'validation' in error_message or 'invalid' in error_message:
            return ErrorCategory.VALIDATION
        else:
            return ErrorCategory.SYSTEM
    
    def _assess_severity(self, error: Exception) -> ErrorSeverity:
        """评估错误严重程度"""
        error_type = type(error).__name__.lower()
        error_message = str(error).lower()
        
        if any(keyword in error_message for keyword in ['critical', 'fatal', 'corrupt']):
            return ErrorSeverity.CRITICAL
        elif any(keyword in error_type for keyword in ['system', 'memory', 'runtime']):
            return ErrorSeverity.HIGH
        elif any(keyword in error_message for keyword in ['warning', 'deprecated']):
            return ErrorSeverity.LOW
        else:
            return ErrorSeverity.MEDIUM
    
    def _get_error_details(self, error: Exception) -> str:
        """获取错误详情"""
        details = {
            'error_type': type(error).__name__,
            'error_module': getattr(error, '__module__', 'unknown'),
            'error_args': error.args
        }
        
        # 添加特定错误类型的详情
        if hasattr(error, '__dict__'):
            details.update({k: v for k, v in error.__dict__.items() 
                          if not k.startswith('_')})
        
        return json.dumps(details, ensure_ascii=False, indent=2)
    
    def _get_recovery_suggestions(self, category: ErrorCategory, error: Exception) -> List[str]:
        """获取恢复建议"""
        suggestions = []
        
        if category == ErrorCategory.FILE_SYSTEM:
            suggestions.extend([
                "检查文件路径是否正确",
                "确认文件或目录是否存在",
                "检查文件权限设置",
                "确保磁盘空间充足"
            ])
        elif category == ErrorCategory.CONFIGURATION:
            suggestions.extend([
                "检查配置文件格式是否正确",
                "验证配置项的值是否有效",
                "尝试重置为默认配置",
                "查看配置文档和示例"
            ])
        elif category == ErrorCategory.VALIDATION:
            suggestions.extend([
                "检查输入数据的格式和类型",
                "确认必填字段是否完整",
                "验证数据范围和约束条件",
                "参考数据验证规则"
            ])
        elif category == ErrorCategory.PERMISSION:
            suggestions.extend([
                "检查文件和目录权限",
                "确认当前用户的访问权限",
                "尝试以管理员权限运行",
                "检查防火墙和安全软件设置"
            ])
        
        return suggestions
    
    def _log_error(self, error_info: ErrorInfo):
        """记录错误"""
        # 添加到内存日志
        self.error_log.append(error_info)
        
        # 只保留最近1000条错误记录
        if len(self.error_log) > 1000:
            self.error_log = self.error_log[-1000:]
        
        # 写入日志文件
        log_level = {
            ErrorSeverity.LOW: logging.INFO,
            ErrorSeverity.MEDIUM: logging.WARNING,
            ErrorSeverity.HIGH: logging.ERROR,
            ErrorSeverity.CRITICAL: logging.CRITICAL
        }.get(error_info.severity, logging.ERROR)
        
        self.logger.log(
            log_level,
            f"[{error_info.error_id}] {error_info.category.value.upper()}: {error_info.message}"
        )
        
        # 写入详细错误日志
        error_log_file = self.log_dir / f"error_details_{datetime.now().strftime('%Y%m%d')}.json"
        
        try:
            # 读取现有日志
            if error_log_file.exists():
                with open(error_log_file, 'r', encoding='utf-8') as f:
                    log_data = json.load(f)
            else:
                log_data = {'errors': []}
            
            # 添加新错误
            log_data['errors'].append(error_info.to_dict())
            
            # 写回文件
            with open(error_log_file, 'w', encoding='utf-8') as f:
                json.dump(log_data, f, ensure_ascii=False, indent=2)
                
        except Exception:
            # 如果写入失败，至少记录到主日志
            self.logger.error(f"Failed to write detailed error log for {error_info.error_id}")
    
    def _execute_callbacks(self, error: Exception, error_info: ErrorInfo):
        """执行错误回调"""
        error_type = type(error)
        
        # 执行特定类型的回调
        if error_type in self.error_callbacks:
            try:
                self.error_callbacks[error_type](error, error_info)
            except Exception as callback_error:
                self.logger.error(f"Error callback failed: {callback_error}")
        
        # 执行通用回调
        if Exception in self.error_callbacks:
            try:
                self.error_callbacks[Exception](error, error_info)
            except Exception as callback_error:
                self.logger.error(f"General error callback failed: {callback_error}")
    
    def _attempt_recovery(self, error_info: ErrorInfo) -> bool:
        """尝试错误恢复"""
        strategies = self.recovery_strategies.get(error_info.category, [])
        
        for strategy in strategies:
            try:
                if strategy.execute(error_info, error_info.context):
                    self.logger.info(f"Recovery successful using strategy: {strategy.name}")
                    return True
            except Exception as recovery_error:
                self.logger.error(f"Recovery strategy {strategy.name} failed: {recovery_error}")
        
        return False
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """获取错误统计"""
        if not self.error_log:
            return {'message': '暂无错误记录'}
        
        # 按分类统计
        category_stats = {}
        severity_stats = {}
        
        for error_info in self.error_log:
            # 分类统计
            category = error_info.category.value
            if category not in category_stats:
                category_stats[category] = 0
            category_stats[category] += 1
            
            # 严重程度统计
            severity = error_info.severity.value
            if severity not in severity_stats:
                severity_stats[severity] = 0
            severity_stats[severity] += 1
        
        # 最近错误
        recent_errors = sorted(self.error_log, key=lambda x: x.timestamp, reverse=True)[:10]
        
        return {
            'total_errors': len(self.error_log),
            'category_distribution': category_stats,
            'severity_distribution': severity_stats,
            'recent_errors': [
                {
                    'id': error.error_id,
                    'category': error.category.value,
                    'severity': error.severity.value,
                    'message': error.message,
                    'timestamp': error.timestamp.isoformat()
                }
                for error in recent_errors
            ]
        }
    
    def clear_error_log(self):
        """清空错误日志"""
        self.error_log.clear()

# 全局错误处理器实例
_error_handler = None

def get_error_handler() -> ErrorHandler:
    """获取全局错误处理器实例"""
    global _error_handler
    if _error_handler is None:
        _error_handler = ErrorHandler()
    return _error_handler

def handle_error(error: Exception, context: Dict[str, Any] = None, auto_recover: bool = True) -> ErrorInfo:
    """处理错误的便捷函数"""
    return get_error_handler().handle_error(error, context, auto_recover)

def error_handler_decorator(auto_recover: bool = True, context: Dict[str, Any] = None):
    """错误处理装饰器"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_context = context.copy() if context else {}
                error_context.update({
                    'function': func.__name__,
                    'args': str(args),
                    'kwargs': str(kwargs)
                })
                
                error_info = handle_error(e, error_context, auto_recover)
                
                # 重新抛出异常，但附加错误ID
                e.error_id = error_info.error_id
                raise e
        
        return wrapper
    return decorator

if __name__ == "__main__":
    # 测试错误处理系统
    print("=== 错误处理系统测试 ===")
    
    handler = get_error_handler()
    
    # 测试不同类型的错误
    test_errors = [
        FileNotFoundError("测试文件不存在"),
        ValueError("无效的参数值"),
        PermissionError("权限不足"),
        ValidationError("验证失败", field="name", value=""),
        ConfigurationError("配置错误", config_file="test.json")
    ]
    
    for i, error in enumerate(test_errors, 1):
        print(f"\n{i}. 处理错误: {type(error).__name__}")
        error_info = handler.handle_error(error, {'test_context': f'test_{i}'})
        print(f"   错误ID: {error_info.error_id}")
        print(f"   分类: {error_info.category.value}")
        print(f"   严重程度: {error_info.severity.value}")
        print(f"   恢复建议: {len(error_info.recovery_suggestions)} 条")
    
    # 显示错误统计
    print("\n=== 错误统计 ===")
    stats = handler.get_error_statistics()
    
    print(f"总错误数: {stats['total_errors']}")
    print("分类分布:")
    for category, count in stats['category_distribution'].items():
        print(f"  {category}: {count}")
    
    print("严重程度分布:")
    for severity, count in stats['severity_distribution'].items():
        print(f"  {severity}: {count}")