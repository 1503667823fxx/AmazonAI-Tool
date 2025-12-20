"""
日志和错误处理模块
Logging and Error Handling Module
"""

from .error_handler import (
    ErrorHandler,
    ErrorInfo,
    ErrorSeverity,
    ErrorCategory,
    ErrorRecoveryStrategy,
    TemplateLibraryError,
    ValidationError,
    FileSystemError,
    ConfigurationError,
    BusinessLogicError,
    get_error_handler,
    handle_error,
    error_handler_decorator
)

from .audit_logger import (
    AuditLogger,
    AuditEvent,
    AuditEventType,
    get_audit_logger
)

from .monitoring_system import (
    MonitoringSystem,
    MetricCollector,
    SystemMonitor,
    AlertManager,
    Alert,
    Metric,
    Threshold,
    AlertLevel,
    MetricType,
    get_monitoring_system,
    monitor_decorator
)

__all__ = [
    'ErrorHandler',
    'ErrorInfo',
    'ErrorSeverity',
    'ErrorCategory',
    'ErrorRecoveryStrategy',
    'TemplateLibraryError',
    'ValidationError',
    'FileSystemError',
    'ConfigurationError',
    'BusinessLogicError',
    'get_error_handler',
    'handle_error',
    'error_handler_decorator',
    'AuditLogger',
    'AuditEvent',
    'AuditEventType',
    'get_audit_logger',
    'MonitoringSystem',
    'MetricCollector',
    'SystemMonitor',
    'AlertManager',
    'Alert',
    'Metric',
    'Threshold',
    'AlertLevel',
    'MetricType',
    'get_monitoring_system',
    'monitor_decorator'
]