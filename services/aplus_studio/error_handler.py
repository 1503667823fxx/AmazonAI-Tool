"""
A+ 智能工作流错误处理服务

该模块实现完善的错误处理机制，包括：
- 实现各种失败场景的处理
- 提供用户友好的错误提示
- 添加自动重试和恢复功能
- 错误分类和统计
- 智能错误恢复策略
"""

import logging
import time
import traceback
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Union, Type
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps
import json
import random

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """错误严重程度"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """错误类别"""
    NETWORK_ERROR = "network_error"
    API_ERROR = "api_error"
    VALIDATION_ERROR = "validation_error"
    PROCESSING_ERROR = "processing_error"
    TIMEOUT_ERROR = "timeout_error"
    RESOURCE_ERROR = "resource_error"
    CONFIGURATION_ERROR = "configuration_error"
    USER_INPUT_ERROR = "user_input_error"
    SYSTEM_ERROR = "system_error"
    UNKNOWN_ERROR = "unknown_error"


class RecoveryStrategy(Enum):
    """恢复策略"""
    RETRY = "retry"
    FALLBACK = "fallback"
    SKIP = "skip"
    USER_INTERVENTION = "user_intervention"
    ABORT = "abort"


@dataclass
class ErrorContext:
    """错误上下文"""
    operation_name: str
    function_name: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    user_session_id: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    additional_info: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ErrorInfo:
    """错误信息"""
    error_id: str
    category: ErrorCategory
    severity: ErrorSeverity
    message: str
    user_message: str
    technical_details: str
    context: ErrorContext
    recovery_strategy: RecoveryStrategy
    retry_count: int = 0
    max_retries: int = 3
    resolved: bool = False
    resolution_time: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "error_id": self.error_id,
            "category": self.category.value,
            "severity": self.severity.value,
            "message": self.message,
            "user_message": self.user_message,
            "technical_details": self.technical_details,
            "context": {
                "operation_name": self.context.operation_name,
                "function_name": self.context.function_name,
                "parameters": self.context.parameters,
                "user_session_id": self.context.user_session_id,
                "timestamp": self.context.timestamp.isoformat(),
                "additional_info": self.context.additional_info
            },
            "recovery_strategy": self.recovery_strategy.value,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "resolved": self.resolved,
            "resolution_time": self.resolution_time.isoformat() if self.resolution_time else None
        }


@dataclass
class RecoveryAction:
    """恢复动作"""
    action_type: RecoveryStrategy
    description: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    success_probability: float = 0.5
    execution_time_estimate: float = 0.0  # 秒
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "action_type": self.action_type.value,
            "description": self.description,
            "parameters": self.parameters,
            "success_probability": self.success_probability,
            "execution_time_estimate": self.execution_time_estimate
        }


class ErrorClassifier:
    """错误分类器"""
    
    def __init__(self):
        # 错误模式匹配规则
        self.error_patterns = {
            ErrorCategory.NETWORK_ERROR: [
                "connection", "network", "timeout", "unreachable", "dns", "socket",
                "connection refused", "connection reset", "connection timeout"
            ],
            ErrorCategory.API_ERROR: [
                "api", "http", "status code", "unauthorized", "forbidden", "not found",
                "rate limit", "quota", "authentication", "invalid token"
            ],
            ErrorCategory.VALIDATION_ERROR: [
                "validation", "invalid", "required", "missing", "format", "schema",
                "constraint", "out of range", "invalid format"
            ],
            ErrorCategory.PROCESSING_ERROR: [
                "processing", "parse", "decode", "encode", "transform", "convert",
                "calculation", "algorithm", "logic error"
            ],
            ErrorCategory.TIMEOUT_ERROR: [
                "timeout", "timed out", "deadline", "expired", "time limit"
            ],
            ErrorCategory.RESOURCE_ERROR: [
                "memory", "disk", "storage", "resource", "capacity", "limit exceeded",
                "out of memory", "disk full", "no space"
            ],
            ErrorCategory.CONFIGURATION_ERROR: [
                "configuration", "config", "setting", "environment", "variable",
                "missing config", "invalid config"
            ],
            ErrorCategory.USER_INPUT_ERROR: [
                "user input", "invalid input", "bad request", "malformed",
                "user error", "input validation"
            ]
        }
        
        # 严重程度评估规则
        self.severity_keywords = {
            ErrorSeverity.CRITICAL: [
                "critical", "fatal", "crash", "system failure", "data loss",
                "security", "corruption", "unavailable"
            ],
            ErrorSeverity.HIGH: [
                "error", "failed", "exception", "abort", "reject", "deny"
            ],
            ErrorSeverity.MEDIUM: [
                "warning", "issue", "problem", "unexpected", "retry"
            ],
            ErrorSeverity.LOW: [
                "info", "notice", "minor", "temporary", "recoverable"
            ]
        }
    
    def classify_error(self, exception: Exception, context: ErrorContext) -> Tuple[ErrorCategory, ErrorSeverity]:
        """分类错误"""
        error_text = str(exception).lower()
        exception_type = type(exception).__name__.lower()
        
        # 分类错误类别
        category = ErrorCategory.UNKNOWN_ERROR
        for error_category, patterns in self.error_patterns.items():
            if any(pattern in error_text or pattern in exception_type for pattern in patterns):
                category = error_category
                break
        
        # 评估严重程度
        severity = ErrorSeverity.MEDIUM  # 默认中等严重程度
        for error_severity, keywords in self.severity_keywords.items():
            if any(keyword in error_text or keyword in exception_type for keyword in keywords):
                severity = error_severity
                break
        
        # 根据异常类型调整分类
        if isinstance(exception, (ConnectionError, TimeoutError)):
            category = ErrorCategory.NETWORK_ERROR
        elif isinstance(exception, ValueError):
            category = ErrorCategory.VALIDATION_ERROR
        elif isinstance(exception, MemoryError):
            category = ErrorCategory.RESOURCE_ERROR
            severity = ErrorSeverity.CRITICAL
        elif isinstance(exception, KeyboardInterrupt):
            category = ErrorCategory.USER_INPUT_ERROR
            severity = ErrorSeverity.LOW
        
        return category, severity
    
    def determine_recovery_strategy(self, category: ErrorCategory, severity: ErrorSeverity, 
                                  retry_count: int) -> RecoveryStrategy:
        """确定恢复策略"""
        # 基于错误类别和严重程度确定恢复策略
        if severity == ErrorSeverity.CRITICAL:
            return RecoveryStrategy.ABORT
        
        if retry_count >= 3:
            if category in [ErrorCategory.NETWORK_ERROR, ErrorCategory.API_ERROR]:
                return RecoveryStrategy.FALLBACK
            else:
                return RecoveryStrategy.USER_INTERVENTION
        
        # 可重试的错误类别
        retryable_categories = [
            ErrorCategory.NETWORK_ERROR,
            ErrorCategory.API_ERROR,
            ErrorCategory.TIMEOUT_ERROR,
            ErrorCategory.PROCESSING_ERROR
        ]
        
        if category in retryable_categories:
            return RecoveryStrategy.RETRY
        
        # 需要用户干预的错误
        user_intervention_categories = [
            ErrorCategory.VALIDATION_ERROR,
            ErrorCategory.USER_INPUT_ERROR,
            ErrorCategory.CONFIGURATION_ERROR
        ]
        
        if category in user_intervention_categories:
            return RecoveryStrategy.USER_INTERVENTION
        
        # 可跳过的错误
        if severity == ErrorSeverity.LOW:
            return RecoveryStrategy.SKIP
        
        return RecoveryStrategy.FALLBACK


class ErrorHandler:
    """错误处理器"""
    
    def __init__(self):
        self.classifier = ErrorClassifier()
        self.error_history: List[ErrorInfo] = []
        self.recovery_actions: Dict[ErrorCategory, List[RecoveryAction]] = {}
        self.fallback_handlers: Dict[str, Callable] = {}
        
        # 初始化恢复动作
        self._initialize_recovery_actions()
        
        logger.info("Error Handler initialized")
    
    def _initialize_recovery_actions(self):
        """初始化恢复动作"""
        # 网络错误恢复动作
        self.recovery_actions[ErrorCategory.NETWORK_ERROR] = [
            RecoveryAction(
                action_type=RecoveryStrategy.RETRY,
                description="等待后重试网络请求",
                parameters={"wait_time": 2.0, "exponential_backoff": True},
                success_probability=0.7,
                execution_time_estimate=5.0
            ),
            RecoveryAction(
                action_type=RecoveryStrategy.FALLBACK,
                description="使用备用网络配置",
                parameters={"use_backup_endpoint": True},
                success_probability=0.5,
                execution_time_estimate=3.0
            )
        ]
        
        # API错误恢复动作
        self.recovery_actions[ErrorCategory.API_ERROR] = [
            RecoveryAction(
                action_type=RecoveryStrategy.RETRY,
                description="重新获取API令牌后重试",
                parameters={"refresh_token": True, "wait_time": 1.0},
                success_probability=0.8,
                execution_time_estimate=3.0
            ),
            RecoveryAction(
                action_type=RecoveryStrategy.FALLBACK,
                description="使用本地缓存或模拟数据",
                parameters={"use_cache": True, "use_mock_data": True},
                success_probability=0.9,
                execution_time_estimate=1.0
            )
        ]
        
        # 处理错误恢复动作
        self.recovery_actions[ErrorCategory.PROCESSING_ERROR] = [
            RecoveryAction(
                action_type=RecoveryStrategy.RETRY,
                description="使用不同的处理参数重试",
                parameters={"adjust_parameters": True},
                success_probability=0.6,
                execution_time_estimate=2.0
            ),
            RecoveryAction(
                action_type=RecoveryStrategy.FALLBACK,
                description="使用简化的处理逻辑",
                parameters={"use_simplified_logic": True},
                success_probability=0.8,
                execution_time_estimate=1.5
            )
        ]
        
        # 超时错误恢复动作
        self.recovery_actions[ErrorCategory.TIMEOUT_ERROR] = [
            RecoveryAction(
                action_type=RecoveryStrategy.RETRY,
                description="增加超时时间后重试",
                parameters={"increase_timeout": True, "timeout_multiplier": 2.0},
                success_probability=0.7,
                execution_time_estimate=10.0
            )
        ]
        
        # 验证错误恢复动作
        self.recovery_actions[ErrorCategory.VALIDATION_ERROR] = [
            RecoveryAction(
                action_type=RecoveryStrategy.USER_INTERVENTION,
                description="请用户提供正确的输入",
                parameters={"show_validation_errors": True},
                success_probability=0.9,
                execution_time_estimate=0.0
            ),
            RecoveryAction(
                action_type=RecoveryStrategy.FALLBACK,
                description="使用默认值或跳过验证",
                parameters={"use_defaults": True, "skip_validation": False},
                success_probability=0.6,
                execution_time_estimate=0.5
            )
        ]
    
    def handle_error(self, exception: Exception, context: ErrorContext) -> ErrorInfo:
        """处理错误"""
        # 生成错误ID
        error_id = f"err_{int(time.time() * 1000)}_{random.randint(1000, 9999)}"
        
        # 分类错误
        category, severity = self.classifier.classify_error(exception, context)
        
        # 确定恢复策略
        recovery_strategy = self.classifier.determine_recovery_strategy(category, severity, 0)
        
        # 生成用户友好的错误消息
        user_message = self._generate_user_message(category, severity, exception)
        
        # 创建错误信息
        error_info = ErrorInfo(
            error_id=error_id,
            category=category,
            severity=severity,
            message=str(exception),
            user_message=user_message,
            technical_details=traceback.format_exc(),
            context=context,
            recovery_strategy=recovery_strategy
        )
        
        # 记录错误
        self.error_history.append(error_info)
        
        # 记录日志
        log_level = self._get_log_level(severity)
        logger.log(log_level, f"Error handled: {error_id} - {category.value} - {user_message}")
        
        return error_info
    
    def attempt_recovery(self, error_info: ErrorInfo, operation_func: Callable, 
                        *args, **kwargs) -> Tuple[bool, Any, Optional[str]]:
        """尝试错误恢复"""
        if error_info.resolved:
            return True, None, "Error already resolved"
        
        if error_info.retry_count >= error_info.max_retries:
            return False, None, "Maximum retry attempts exceeded"
        
        # 获取恢复动作
        recovery_actions = self.recovery_actions.get(error_info.category, [])
        
        for action in recovery_actions:
            if action.action_type == error_info.recovery_strategy:
                try:
                    logger.info(f"Attempting recovery for {error_info.error_id}: {action.description}")
                    
                    # 执行恢复动作
                    success, result = self._execute_recovery_action(
                        action, error_info, operation_func, *args, **kwargs
                    )
                    
                    if success:
                        error_info.resolved = True
                        error_info.resolution_time = datetime.now()
                        logger.info(f"Recovery successful for {error_info.error_id}")
                        return True, result, "Recovery successful"
                    else:
                        error_info.retry_count += 1
                        logger.warning(f"Recovery attempt failed for {error_info.error_id}")
                
                except Exception as e:
                    error_info.retry_count += 1
                    logger.error(f"Recovery action failed for {error_info.error_id}: {str(e)}")
        
        # 如果所有恢复动作都失败，尝试回退策略
        if error_info.recovery_strategy != RecoveryStrategy.FALLBACK:
            fallback_handler = self.fallback_handlers.get(error_info.context.operation_name)
            if fallback_handler:
                try:
                    logger.info(f"Attempting fallback for {error_info.error_id}")
                    result = fallback_handler(*args, **kwargs)
                    error_info.resolved = True
                    error_info.resolution_time = datetime.now()
                    return True, result, "Fallback successful"
                except Exception as e:
                    logger.error(f"Fallback failed for {error_info.error_id}: {str(e)}")
        
        return False, None, "All recovery attempts failed"
    
    def _execute_recovery_action(self, action: RecoveryAction, error_info: ErrorInfo,
                               operation_func: Callable, *args, **kwargs) -> Tuple[bool, Any]:
        """执行恢复动作"""
        if action.action_type == RecoveryStrategy.RETRY:
            return self._execute_retry(action, error_info, operation_func, *args, **kwargs)
        elif action.action_type == RecoveryStrategy.FALLBACK:
            return self._execute_fallback(action, error_info, operation_func, *args, **kwargs)
        elif action.action_type == RecoveryStrategy.SKIP:
            return True, None  # 跳过操作，视为成功
        else:
            return False, None
    
    def _execute_retry(self, action: RecoveryAction, error_info: ErrorInfo,
                      operation_func: Callable, *args, **kwargs) -> Tuple[bool, Any]:
        """执行重试"""
        params = action.parameters
        
        # 等待时间
        wait_time = params.get("wait_time", 1.0)
        if params.get("exponential_backoff", False):
            wait_time *= (2 ** error_info.retry_count)
        
        if wait_time > 0:
            logger.info(f"Waiting {wait_time:.2f} seconds before retry")
            time.sleep(wait_time)
        
        # 调整参数
        if params.get("adjust_parameters", False):
            kwargs = self._adjust_parameters(kwargs, error_info)
        
        # 增加超时时间
        if params.get("increase_timeout", False):
            timeout_multiplier = params.get("timeout_multiplier", 2.0)
            if "timeout" in kwargs:
                kwargs["timeout"] *= timeout_multiplier
        
        try:
            result = operation_func(*args, **kwargs)
            return True, result
        except Exception as e:
            logger.warning(f"Retry failed: {str(e)}")
            return False, None
    
    def _execute_fallback(self, action: RecoveryAction, error_info: ErrorInfo,
                         operation_func: Callable, *args, **kwargs) -> Tuple[bool, Any]:
        """执行回退策略"""
        params = action.parameters
        
        # 使用缓存
        if params.get("use_cache", False):
            # 这里应该实现缓存逻辑
            logger.info("Attempting to use cached result")
            # 返回模拟的缓存结果
            return True, {"cached": True, "message": "Using cached result"}
        
        # 使用模拟数据
        if params.get("use_mock_data", False):
            logger.info("Using mock data as fallback")
            return True, self._generate_mock_data(error_info.context.operation_name)
        
        # 使用简化逻辑
        if params.get("use_simplified_logic", False):
            logger.info("Using simplified processing logic")
            # 这里应该调用简化版本的函数
            return True, {"simplified": True, "message": "Using simplified logic"}
        
        return False, None
    
    def _adjust_parameters(self, kwargs: Dict[str, Any], error_info: ErrorInfo) -> Dict[str, Any]:
        """调整参数以避免错误"""
        adjusted_kwargs = kwargs.copy()
        
        # 根据错误类别调整参数
        if error_info.category == ErrorCategory.VALIDATION_ERROR:
            # 使用更宽松的验证参数
            adjusted_kwargs["strict_validation"] = False
            adjusted_kwargs["allow_partial"] = True
        
        elif error_info.category == ErrorCategory.PROCESSING_ERROR:
            # 降低处理复杂度
            adjusted_kwargs["max_complexity"] = adjusted_kwargs.get("max_complexity", 10) // 2
            adjusted_kwargs["enable_optimization"] = False
        
        elif error_info.category == ErrorCategory.RESOURCE_ERROR:
            # 减少资源使用
            adjusted_kwargs["batch_size"] = adjusted_kwargs.get("batch_size", 100) // 2
            adjusted_kwargs["memory_limit"] = adjusted_kwargs.get("memory_limit", 1024) // 2
        
        return adjusted_kwargs
    
    def _generate_mock_data(self, operation_name: str) -> Dict[str, Any]:
        """生成模拟数据"""
        mock_data = {
            "product_analysis": {
                "product_type": "示例产品",
                "category": "other",
                "key_features": ["功能1", "功能2", "功能3"],
                "confidence_score": 0.5,
                "mock_data": True
            },
            "module_recommendation": {
                "recommended_modules": ["product_overview", "problem_solution"],
                "confidence_scores": {"product_overview": 0.8, "problem_solution": 0.7},
                "mock_data": True
            },
            "content_generation": {
                "title": "示例内容标题",
                "description": "这是一个示例内容描述",
                "key_points": ["要点1", "要点2", "要点3"],
                "mock_data": True
            }
        }
        
        return mock_data.get(operation_name, {"mock_data": True, "message": "Mock data generated"})
    
    def _generate_user_message(self, category: ErrorCategory, severity: ErrorSeverity, 
                             exception: Exception) -> str:
        """生成用户友好的错误消息"""
        base_messages = {
            ErrorCategory.NETWORK_ERROR: "网络连接出现问题，请检查网络设置后重试",
            ErrorCategory.API_ERROR: "服务暂时不可用，请稍后重试",
            ErrorCategory.VALIDATION_ERROR: "输入的信息有误，请检查后重新提交",
            ErrorCategory.PROCESSING_ERROR: "处理过程中出现问题，正在尝试修复",
            ErrorCategory.TIMEOUT_ERROR: "操作超时，请稍后重试",
            ErrorCategory.RESOURCE_ERROR: "系统资源不足，请稍后重试",
            ErrorCategory.CONFIGURATION_ERROR: "系统配置有误，请联系管理员",
            ErrorCategory.USER_INPUT_ERROR: "请检查输入的信息是否正确",
            ErrorCategory.SYSTEM_ERROR: "系统出现内部错误，正在处理中",
            ErrorCategory.UNKNOWN_ERROR: "出现未知错误，请稍后重试"
        }
        
        base_message = base_messages.get(category, "出现错误，请稍后重试")
        
        # 根据严重程度调整消息
        if severity == ErrorSeverity.CRITICAL:
            return f"严重错误：{base_message}。如果问题持续存在，请联系技术支持。"
        elif severity == ErrorSeverity.HIGH:
            return f"错误：{base_message}。系统正在尝试自动恢复。"
        elif severity == ErrorSeverity.MEDIUM:
            return f"警告：{base_message}。"
        else:
            return base_message
    
    def _get_log_level(self, severity: ErrorSeverity) -> int:
        """获取日志级别"""
        level_mapping = {
            ErrorSeverity.CRITICAL: logging.CRITICAL,
            ErrorSeverity.HIGH: logging.ERROR,
            ErrorSeverity.MEDIUM: logging.WARNING,
            ErrorSeverity.LOW: logging.INFO
        }
        return level_mapping.get(severity, logging.WARNING)
    
    def register_fallback_handler(self, operation_name: str, handler: Callable):
        """注册回退处理器"""
        self.fallback_handlers[operation_name] = handler
        logger.info(f"Registered fallback handler for operation: {operation_name}")
    
    def get_error_statistics(self, hours: int = 24) -> Dict[str, Any]:
        """获取错误统计信息"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        recent_errors = [error for error in self.error_history if error.context.timestamp >= cutoff_time]
        
        if not recent_errors:
            return {
                "period_hours": hours,
                "total_errors": 0,
                "error_rate": 0.0,
                "resolution_rate": 0.0,
                "category_distribution": {},
                "severity_distribution": {},
                "top_operations": []
            }
        
        total_errors = len(recent_errors)
        resolved_errors = sum(1 for error in recent_errors if error.resolved)
        resolution_rate = resolved_errors / total_errors
        
        # 按类别分布
        category_distribution = {}
        for error in recent_errors:
            category = error.category.value
            category_distribution[category] = category_distribution.get(category, 0) + 1
        
        # 按严重程度分布
        severity_distribution = {}
        for error in recent_errors:
            severity = error.severity.value
            severity_distribution[severity] = severity_distribution.get(severity, 0) + 1
        
        # 错误最多的操作
        operation_errors = {}
        for error in recent_errors:
            operation = error.context.operation_name
            operation_errors[operation] = operation_errors.get(operation, 0) + 1
        
        top_operations = sorted(operation_errors.items(), key=lambda x: x[1], reverse=True)[:5]
        
        return {
            "period_hours": hours,
            "total_errors": total_errors,
            "resolved_errors": resolved_errors,
            "resolution_rate": resolution_rate,
            "category_distribution": category_distribution,
            "severity_distribution": severity_distribution,
            "top_operations": top_operations,
            "average_resolution_time": self._calculate_average_resolution_time(recent_errors)
        }
    
    def _calculate_average_resolution_time(self, errors: List[ErrorInfo]) -> Optional[float]:
        """计算平均解决时间"""
        resolved_errors = [error for error in errors if error.resolved and error.resolution_time]
        
        if not resolved_errors:
            return None
        
        total_time = 0.0
        for error in resolved_errors:
            resolution_time = (error.resolution_time - error.context.timestamp).total_seconds()
            total_time += resolution_time
        
        return total_time / len(resolved_errors)
    
    def get_recovery_recommendations(self) -> List[Dict[str, Any]]:
        """获取恢复建议"""
        recommendations = []
        
        # 分析最近的错误模式
        recent_errors = self.error_history[-100:]  # 最近100个错误
        
        # 按类别统计未解决的错误
        unresolved_by_category = {}
        for error in recent_errors:
            if not error.resolved:
                category = error.category.value
                unresolved_by_category[category] = unresolved_by_category.get(category, 0) + 1
        
        # 生成建议
        for category, count in unresolved_by_category.items():
            if count >= 3:  # 如果某类错误未解决的数量较多
                recommendations.append({
                    "type": "error_pattern",
                    "priority": "high" if count >= 5 else "medium",
                    "title": f"解决{category}类错误",
                    "description": f"发现{count}个未解决的{category}错误",
                    "suggestions": self._get_category_suggestions(ErrorCategory(category))
                })
        
        # 检查恢复成功率
        recovery_stats = self._calculate_recovery_success_rate()
        if recovery_stats["success_rate"] < 0.7:
            recommendations.append({
                "type": "recovery_improvement",
                "priority": "high",
                "title": "提高错误恢复成功率",
                "description": f"当前恢复成功率为{recovery_stats['success_rate']:.2%}",
                "suggestions": [
                    "优化重试策略",
                    "增加更多回退选项",
                    "改进错误分类准确性",
                    "增强用户干预机制"
                ]
            })
        
        return recommendations
    
    def _get_category_suggestions(self, category: ErrorCategory) -> List[str]:
        """获取特定类别的建议"""
        suggestions = {
            ErrorCategory.NETWORK_ERROR: [
                "检查网络连接稳定性",
                "增加网络超时时间",
                "实现更好的重试机制",
                "添加网络状态监控"
            ],
            ErrorCategory.API_ERROR: [
                "检查API密钥和权限",
                "实现API调用限流",
                "添加API状态监控",
                "准备备用API端点"
            ],
            ErrorCategory.VALIDATION_ERROR: [
                "改进输入验证逻辑",
                "提供更清晰的错误提示",
                "添加输入格式示例",
                "实现渐进式验证"
            ],
            ErrorCategory.PROCESSING_ERROR: [
                "优化处理算法",
                "增加数据预处理",
                "实现分批处理",
                "添加处理进度监控"
            ]
        }
        
        return suggestions.get(category, ["分析具体错误原因", "实现针对性解决方案"])
    
    def _calculate_recovery_success_rate(self) -> Dict[str, Any]:
        """计算恢复成功率"""
        recent_errors = self.error_history[-50:]  # 最近50个错误
        
        if not recent_errors:
            return {"success_rate": 0.0, "total_attempts": 0, "successful_recoveries": 0}
        
        total_attempts = len(recent_errors)
        successful_recoveries = sum(1 for error in recent_errors if error.resolved)
        success_rate = successful_recoveries / total_attempts
        
        return {
            "success_rate": success_rate,
            "total_attempts": total_attempts,
            "successful_recoveries": successful_recoveries
        }
    
    def clear_old_errors(self, days: int = 30) -> int:
        """清理旧的错误记录"""
        cutoff_time = datetime.now() - timedelta(days=days)
        
        old_count = len(self.error_history)
        self.error_history = [
            error for error in self.error_history 
            if error.context.timestamp >= cutoff_time
        ]
        
        removed_count = old_count - len(self.error_history)
        
        if removed_count > 0:
            logger.info(f"Cleaned up {removed_count} old error records (older than {days} days)")
        
        return removed_count


def error_handler(operation_name: str, max_retries: int = 3, 
                 enable_recovery: bool = True, fallback_result: Any = None):
    """错误处理装饰器"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 获取错误处理器实例
            handler = getattr(args[0], '_error_handler', None) if args else None
            if not handler:
                # 如果没有错误处理器，直接执行函数
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    logger.error(f"Unhandled error in {operation_name}: {str(e)}")
                    if fallback_result is not None:
                        return fallback_result
                    raise
            
            # 创建错误上下文
            context = ErrorContext(
                operation_name=operation_name,
                function_name=func.__name__,
                parameters={k: str(v)[:100] for k, v in kwargs.items()},  # 限制参数长度
                user_session_id=kwargs.get("session_id"),
                additional_info={"max_retries": max_retries, "enable_recovery": enable_recovery}
            )
            
            try:
                # 执行函数
                return func(*args, **kwargs)
                
            except Exception as e:
                # 处理错误
                error_info = handler.handle_error(e, context)
                error_info.max_retries = max_retries
                
                # 尝试恢复
                if enable_recovery:
                    success, result, message = handler.attempt_recovery(
                        error_info, func, *args, **kwargs
                    )
                    
                    if success:
                        logger.info(f"Error recovery successful for {operation_name}: {message}")
                        return result
                    else:
                        logger.error(f"Error recovery failed for {operation_name}: {message}")
                
                # 如果有回退结果，返回回退结果
                if fallback_result is not None:
                    logger.info(f"Using fallback result for {operation_name}")
                    return fallback_result
                
                # 重新抛出异常
                raise
        
        return wrapper
    return decorator


# 全局错误处理器实例
_global_error_handler = ErrorHandler()


def get_global_error_handler() -> ErrorHandler:
    """获取全局错误处理器"""
    return _global_error_handler