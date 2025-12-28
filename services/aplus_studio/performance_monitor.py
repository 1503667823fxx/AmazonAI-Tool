"""
A+ 智能工作流简化性能监控

简化版本：保留基本性能监控功能，删除过度复杂的企业级特性
"""

import logging
import time
from typing import Dict, Any, Optional, Callable
from functools import wraps

logger = logging.getLogger(__name__)


def simple_performance_monitor(operation_name: str = "operation"):
    """简化的性能监控装饰器"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                end_time = time.time()
                duration = end_time - start_time
                logger.debug(f"{operation_name} completed in {duration:.2f}s")
                return result
            except Exception as e:
                end_time = time.time()
                duration = end_time - start_time
                logger.error(f"{operation_name} failed after {duration:.2f}s: {str(e)}")
                raise
        return wrapper
    return decorator


class SimplePerformanceMonitor:
    """简化的性能监控器"""
    
    def __init__(self):
        self.operation_count = 0
        self.total_time = 0.0
    
    def start_operation(self, operation_name: str) -> float:
        """开始操作计时"""
        return time.time()
    
    def end_operation(self, operation_name: str, start_time: float):
        """结束操作计时"""
        duration = time.time() - start_time
        self.operation_count += 1
        self.total_time += duration
        logger.debug(f"Operation {operation_name} took {duration:.2f}s")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        avg_time = self.total_time / max(self.operation_count, 1)
        return {
            'operation_count': self.operation_count,
            'total_time': self.total_time,
            'average_time': avg_time
        }
    
    def reset_stats(self):
        """重置统计信息"""
        self.operation_count = 0
        self.total_time = 0.0


# 全局性能监控器实例
_global_performance_monitor = SimplePerformanceMonitor()


def get_global_performance_monitor() -> SimplePerformanceMonitor:
    """获取全局性能监控器"""
    return _global_performance_monitor


# 为了兼容性，保留原来的装饰器名称
def performance_monitor(operation_name: str, cache_key_params: Optional[Dict] = None, 
                       cache_ttl: int = 3600, enable_cache: bool = True):
    """简化的性能监控装饰器（兼容原接口）"""
    return simple_performance_monitor(operation_name)


# 兼容性类名
class PerformanceMonitor(SimplePerformanceMonitor):
    """兼容性类名"""
    pass