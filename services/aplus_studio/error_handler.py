"""
A+ 智能工作流简化错误处理

简化版本：保留基本错误处理功能，删除过度复杂的企业级特性
"""

import logging
from typing import Dict, Any, Optional, Callable
from functools import wraps

logger = logging.getLogger(__name__)


def simple_error_handler(operation_name: str = "operation"):
    """简化的错误处理装饰器"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(f"{operation_name} failed: {str(e)}")
                # 返回None或抛出异常，让调用方处理
                raise
        return wrapper
    return decorator


def log_error(operation_name: str, error: Exception, context: Optional[Dict[str, Any]] = None):
    """记录错误日志"""
    logger.error(f"Error in {operation_name}: {str(error)}")
    if context:
        logger.error(f"Context: {context}")


def get_user_friendly_message(error: Exception) -> str:
    """获取用户友好的错误消息"""
    error_messages = {
        "ConnectionError": "网络连接失败，请检查网络连接",
        "TimeoutError": "操作超时，请稍后重试",
        "ValueError": "输入数据格式错误，请检查输入",
        "KeyError": "缺少必要的数据字段",
        "FileNotFoundError": "找不到指定的文件",
    }
    
    error_type = type(error).__name__
    return error_messages.get(error_type, f"操作失败: {str(error)}")


class SimpleErrorHandler:
    """简化的错误处理器"""
    
    def __init__(self):
        self.error_count = 0
        self.fallback_handlers = {}
    
    def handle_error(self, operation_name: str, error: Exception, context: Optional[Dict[str, Any]] = None) -> str:
        """处理错误并返回用户友好消息"""
        self.error_count += 1
        log_error(operation_name, error, context)
        return get_user_friendly_message(error)
    
    def register_fallback_handler(self, operation_name: str, handler: Callable):
        """注册回退处理器"""
        self.fallback_handlers[operation_name] = handler
        logger.debug(f"Registered fallback handler for {operation_name}")
    
    def get_fallback_handler(self, operation_name: str) -> Optional[Callable]:
        """获取回退处理器"""
        return self.fallback_handlers.get(operation_name)
    
    def reset_error_count(self):
        """重置错误计数"""
        self.error_count = 0


# 全局错误处理器实例
_global_error_handler = SimpleErrorHandler()


def get_global_error_handler() -> SimpleErrorHandler:
    """获取全局错误处理器"""
    return _global_error_handler


# 为了兼容性，保留原来的装饰器名称
def error_handler(operation_name: str, max_retries: int = 3, 
                 enable_recovery: bool = True, fallback_result: Any = None):
    """简化的错误处理装饰器（兼容原接口）"""
    return simple_error_handler(operation_name)
