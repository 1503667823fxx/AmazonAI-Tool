"""
A+ 智能工作流性能监控服务

该模块实现性能监控和优化功能，包括：
- 添加各步骤的性能计时
- 实现异步处理和缓存机制
- 优化AI API调用频率
- 性能数据收集和分析
- 自动性能优化建议
"""

import logging
import time
import asyncio
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps
import json
from collections import defaultdict, deque
import hashlib

logger = logging.getLogger(__name__)


class PerformanceMetricType(Enum):
    """性能指标类型"""
    EXECUTION_TIME = "execution_time"
    API_CALL_COUNT = "api_call_count"
    CACHE_HIT_RATE = "cache_hit_rate"
    MEMORY_USAGE = "memory_usage"
    ERROR_RATE = "error_rate"
    THROUGHPUT = "throughput"


class PerformanceLevel(Enum):
    """性能等级"""
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    CRITICAL = "critical"


@dataclass
class PerformanceMetric:
    """性能指标"""
    metric_type: PerformanceMetricType
    value: float
    unit: str
    timestamp: datetime
    context: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "metric_type": self.metric_type.value,
            "value": self.value,
            "unit": self.unit,
            "timestamp": self.timestamp.isoformat(),
            "context": self.context
        }


@dataclass
class PerformanceReport:
    """性能报告"""
    operation_name: str
    start_time: datetime
    end_time: datetime
    duration: float
    success: bool
    metrics: List[PerformanceMetric] = field(default_factory=list)
    error_message: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def performance_level(self) -> PerformanceLevel:
        """获取性能等级"""
        if not self.success:
            return PerformanceLevel.CRITICAL
        
        # 基于执行时间判断性能等级
        if self.duration < 1.0:
            return PerformanceLevel.EXCELLENT
        elif self.duration < 5.0:
            return PerformanceLevel.GOOD
        elif self.duration < 15.0:
            return PerformanceLevel.FAIR
        elif self.duration < 60.0:
            return PerformanceLevel.POOR
        else:
            return PerformanceLevel.CRITICAL
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "operation_name": self.operation_name,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "duration": self.duration,
            "success": self.success,
            "performance_level": self.performance_level.value,
            "metrics": [metric.to_dict() for metric in self.metrics],
            "error_message": self.error_message,
            "context": self.context
        }


class PerformanceCache:
    """性能缓存系统"""
    
    def __init__(self, max_size: int = 1000, ttl_seconds: int = 3600):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._access_times: Dict[str, datetime] = {}
        self._hit_count = 0
        self._miss_count = 0
        self._lock = threading.RLock()
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        with self._lock:
            if key not in self._cache:
                self._miss_count += 1
                return None
            
            # 检查是否过期
            if self._is_expired(key):
                self._remove(key)
                self._miss_count += 1
                return None
            
            # 更新访问时间
            self._access_times[key] = datetime.now()
            self._hit_count += 1
            
            return self._cache[key]["value"]
    
    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        """设置缓存值"""
        with self._lock:
            # 如果缓存已满，移除最旧的项
            if len(self._cache) >= self.max_size and key not in self._cache:
                self._evict_oldest()
            
            ttl = ttl_seconds or self.ttl_seconds
            expire_time = datetime.now() + timedelta(seconds=ttl)
            
            self._cache[key] = {
                "value": value,
                "expire_time": expire_time
            }
            self._access_times[key] = datetime.now()
    
    def invalidate(self, key: str) -> bool:
        """使缓存失效"""
        with self._lock:
            if key in self._cache:
                self._remove(key)
                return True
            return False
    
    def clear(self) -> None:
        """清空缓存"""
        with self._lock:
            self._cache.clear()
            self._access_times.clear()
            self._hit_count = 0
            self._miss_count = 0
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        with self._lock:
            total_requests = self._hit_count + self._miss_count
            hit_rate = (self._hit_count / total_requests) if total_requests > 0 else 0.0
            
            return {
                "size": len(self._cache),
                "max_size": self.max_size,
                "hit_count": self._hit_count,
                "miss_count": self._miss_count,
                "hit_rate": hit_rate,
                "ttl_seconds": self.ttl_seconds
            }
    
    def _is_expired(self, key: str) -> bool:
        """检查缓存项是否过期"""
        if key not in self._cache:
            return True
        
        expire_time = self._cache[key]["expire_time"]
        return datetime.now() > expire_time
    
    def _remove(self, key: str) -> None:
        """移除缓存项"""
        self._cache.pop(key, None)
        self._access_times.pop(key, None)
    
    def _evict_oldest(self) -> None:
        """移除最旧的缓存项"""
        if not self._access_times:
            return
        
        oldest_key = min(self._access_times.keys(), key=lambda k: self._access_times[k])
        self._remove(oldest_key)


class APIRateLimiter:
    """API调用频率限制器"""
    
    def __init__(self, max_calls_per_minute: int = 60):
        self.max_calls_per_minute = max_calls_per_minute
        self.call_times: deque = deque()
        self._lock = threading.RLock()
    
    def can_make_call(self) -> bool:
        """检查是否可以进行API调用"""
        with self._lock:
            now = datetime.now()
            
            # 移除超过1分钟的调用记录
            while self.call_times and (now - self.call_times[0]).total_seconds() > 60:
                self.call_times.popleft()
            
            return len(self.call_times) < self.max_calls_per_minute
    
    def record_call(self) -> None:
        """记录API调用"""
        with self._lock:
            self.call_times.append(datetime.now())
    
    def wait_time(self) -> float:
        """获取需要等待的时间（秒）"""
        with self._lock:
            if self.can_make_call():
                return 0.0
            
            if not self.call_times:
                return 0.0
            
            # 计算到最早调用过期的时间
            oldest_call = self.call_times[0]
            wait_seconds = 60 - (datetime.now() - oldest_call).total_seconds()
            return max(wait_seconds, 0.0)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取限流器统计信息"""
        with self._lock:
            now = datetime.now()
            
            # 清理过期记录
            while self.call_times and (now - self.call_times[0]).total_seconds() > 60:
                self.call_times.popleft()
            
            return {
                "current_calls": len(self.call_times),
                "max_calls_per_minute": self.max_calls_per_minute,
                "can_make_call": self.can_make_call(),
                "wait_time": self.wait_time()
            }


class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self):
        self.reports: List[PerformanceReport] = []
        self.cache = PerformanceCache()
        self.api_limiter = APIRateLimiter()
        self.metrics_history: Dict[str, List[PerformanceMetric]] = defaultdict(list)
        self._lock = threading.RLock()
        
        # 性能阈值配置
        self.thresholds = {
            "product_analysis_max_time": 60.0,  # 产品分析最大时间（秒）
            "module_recommendation_max_time": 10.0,  # 模块推荐最大时间（秒）
            "content_generation_max_time": 30.0,  # 内容生成最大时间（秒）
            "image_generation_max_time": 90.0,  # 图片生成最大时间（秒）
            "max_api_calls_per_minute": 60,  # 每分钟最大API调用次数
            "cache_hit_rate_threshold": 0.3,  # 缓存命中率阈值
            "error_rate_threshold": 0.05  # 错误率阈值
        }
        
        logger.info("Performance Monitor initialized")
    
    def start_operation(self, operation_name: str, context: Optional[Dict[str, Any]] = None) -> str:
        """开始监控操作"""
        operation_id = f"{operation_name}_{int(time.time() * 1000)}"
        
        with self._lock:
            # 创建性能报告
            report = PerformanceReport(
                operation_name=operation_name,
                start_time=datetime.now(),
                end_time=datetime.now(),  # 临时值，结束时更新
                duration=0.0,
                success=False,
                context=context or {}
            )
            
            # 添加操作ID到上下文
            report.context["operation_id"] = operation_id
            
            # 暂存报告
            setattr(self, f"_temp_report_{operation_id}", report)
        
        logger.debug(f"Started monitoring operation: {operation_name} ({operation_id})")
        return operation_id
    
    def end_operation(self, operation_id: str, success: bool = True, 
                     error_message: Optional[str] = None,
                     additional_metrics: Optional[List[PerformanceMetric]] = None) -> PerformanceReport:
        """结束监控操作"""
        with self._lock:
            # 获取临时报告
            temp_report = getattr(self, f"_temp_report_{operation_id}", None)
            if not temp_report:
                logger.warning(f"No temporary report found for operation: {operation_id}")
                return None
            
            # 更新报告
            end_time = datetime.now()
            temp_report.end_time = end_time
            temp_report.duration = (end_time - temp_report.start_time).total_seconds()
            temp_report.success = success
            temp_report.error_message = error_message
            
            # 添加额外指标
            if additional_metrics:
                temp_report.metrics.extend(additional_metrics)
            
            # 添加基础性能指标
            temp_report.metrics.append(PerformanceMetric(
                metric_type=PerformanceMetricType.EXECUTION_TIME,
                value=temp_report.duration,
                unit="seconds",
                timestamp=end_time,
                context={"operation_name": temp_report.operation_name}
            ))
            
            # 保存报告
            self.reports.append(temp_report)
            
            # 更新指标历史
            for metric in temp_report.metrics:
                self.metrics_history[metric.metric_type.value].append(metric)
            
            # 清理临时报告
            delattr(self, f"_temp_report_{operation_id}")
            
            # 检查性能阈值
            self._check_performance_thresholds(temp_report)
        
        logger.info(f"Completed monitoring operation: {temp_report.operation_name} "
                   f"({operation_id}) - Duration: {temp_report.duration:.2f}s, "
                   f"Success: {success}, Level: {temp_report.performance_level.value}")
        
        return temp_report
    
    def record_metric(self, metric: PerformanceMetric) -> None:
        """记录性能指标"""
        with self._lock:
            self.metrics_history[metric.metric_type.value].append(metric)
        
        logger.debug(f"Recorded metric: {metric.metric_type.value} = {metric.value} {metric.unit}")
    
    def get_cache_key(self, operation: str, params: Dict[str, Any]) -> str:
        """生成缓存键"""
        # 创建参数的哈希值
        params_str = json.dumps(params, sort_keys=True, default=str)
        params_hash = hashlib.md5(params_str.encode()).hexdigest()[:8]
        
        return f"{operation}:{params_hash}"
    
    def get_cached_result(self, cache_key: str) -> Optional[Any]:
        """获取缓存结果"""
        result = self.cache.get(cache_key)
        
        # 记录缓存指标
        if result is not None:
            self.record_metric(PerformanceMetric(
                metric_type=PerformanceMetricType.CACHE_HIT_RATE,
                value=1.0,
                unit="hit",
                timestamp=datetime.now(),
                context={"cache_key": cache_key}
            ))
        else:
            self.record_metric(PerformanceMetric(
                metric_type=PerformanceMetricType.CACHE_HIT_RATE,
                value=0.0,
                unit="miss",
                timestamp=datetime.now(),
                context={"cache_key": cache_key}
            ))
        
        return result
    
    def set_cached_result(self, cache_key: str, result: Any, ttl_seconds: Optional[int] = None) -> None:
        """设置缓存结果"""
        self.cache.set(cache_key, result, ttl_seconds)
        logger.debug(f"Cached result for key: {cache_key}")
    
    def can_make_api_call(self) -> bool:
        """检查是否可以进行API调用"""
        return self.api_limiter.can_make_call()
    
    def record_api_call(self) -> None:
        """记录API调用"""
        self.api_limiter.record_call()
        
        # 记录API调用指标
        self.record_metric(PerformanceMetric(
            metric_type=PerformanceMetricType.API_CALL_COUNT,
            value=1.0,
            unit="call",
            timestamp=datetime.now()
        ))
    
    def wait_for_api_rate_limit(self) -> float:
        """等待API调用限制"""
        wait_time = self.api_limiter.wait_time()
        if wait_time > 0:
            logger.info(f"API rate limit reached, waiting {wait_time:.2f} seconds")
            time.sleep(wait_time)
        return wait_time
    
    def get_performance_summary(self, hours: int = 24) -> Dict[str, Any]:
        """获取性能摘要"""
        with self._lock:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            
            # 筛选时间范围内的报告
            recent_reports = [
                report for report in self.reports
                if report.start_time >= cutoff_time
            ]
            
            if not recent_reports:
                return {
                    "period_hours": hours,
                    "total_operations": 0,
                    "success_rate": 0.0,
                    "average_duration": 0.0,
                    "performance_distribution": {},
                    "cache_stats": self.cache.get_stats(),
                    "api_limiter_stats": self.api_limiter.get_stats()
                }
            
            # 计算统计信息
            total_operations = len(recent_reports)
            successful_operations = sum(1 for report in recent_reports if report.success)
            success_rate = successful_operations / total_operations
            
            total_duration = sum(report.duration for report in recent_reports)
            average_duration = total_duration / total_operations
            
            # 性能等级分布
            performance_distribution = defaultdict(int)
            for report in recent_reports:
                performance_distribution[report.performance_level.value] += 1
            
            # 按操作类型分组的统计
            operation_stats = defaultdict(lambda: {"count": 0, "total_duration": 0.0, "success_count": 0})
            for report in recent_reports:
                stats = operation_stats[report.operation_name]
                stats["count"] += 1
                stats["total_duration"] += report.duration
                if report.success:
                    stats["success_count"] += 1
            
            # 计算每个操作的平均时间和成功率
            for operation_name, stats in operation_stats.items():
                stats["average_duration"] = stats["total_duration"] / stats["count"]
                stats["success_rate"] = stats["success_count"] / stats["count"]
            
            return {
                "period_hours": hours,
                "total_operations": total_operations,
                "success_rate": success_rate,
                "average_duration": average_duration,
                "performance_distribution": dict(performance_distribution),
                "operation_stats": dict(operation_stats),
                "cache_stats": self.cache.get_stats(),
                "api_limiter_stats": self.api_limiter.get_stats(),
                "slowest_operations": self._get_slowest_operations(recent_reports, 5),
                "failed_operations": self._get_failed_operations(recent_reports, 5)
            }
    
    def get_optimization_recommendations(self) -> List[Dict[str, Any]]:
        """获取性能优化建议"""
        recommendations = []
        
        # 获取最近24小时的性能摘要
        summary = self.get_performance_summary(24)
        
        # 检查缓存命中率
        cache_stats = summary["cache_stats"]
        if cache_stats["hit_rate"] < self.thresholds["cache_hit_rate_threshold"]:
            recommendations.append({
                "type": "cache_optimization",
                "priority": "high",
                "title": "提高缓存命中率",
                "description": f"当前缓存命中率为 {cache_stats['hit_rate']:.2%}，低于阈值 {self.thresholds['cache_hit_rate_threshold']:.2%}",
                "suggestions": [
                    "增加缓存TTL时间",
                    "优化缓存键生成策略",
                    "增加缓存容量",
                    "预加载常用数据"
                ]
            })
        
        # 检查API调用频率
        api_stats = summary["api_limiter_stats"]
        if api_stats["current_calls"] > api_stats["max_calls_per_minute"] * 0.8:
            recommendations.append({
                "type": "api_optimization",
                "priority": "medium",
                "title": "优化API调用频率",
                "description": f"API调用接近限制 ({api_stats['current_calls']}/{api_stats['max_calls_per_minute']})",
                "suggestions": [
                    "增加请求批处理",
                    "实现更智能的缓存策略",
                    "使用异步处理减少等待时间",
                    "优化API调用时机"
                ]
            })
        
        # 检查操作性能
        for operation_name, stats in summary.get("operation_stats", {}).items():
            threshold_key = f"{operation_name.lower().replace(' ', '_')}_max_time"
            threshold = self.thresholds.get(threshold_key)
            
            if threshold and stats["average_duration"] > threshold:
                recommendations.append({
                    "type": "operation_optimization",
                    "priority": "high" if stats["average_duration"] > threshold * 1.5 else "medium",
                    "title": f"优化{operation_name}性能",
                    "description": f"平均执行时间 {stats['average_duration']:.2f}s 超过阈值 {threshold}s",
                    "suggestions": [
                        "检查算法效率",
                        "增加并行处理",
                        "优化数据库查询",
                        "减少不必要的计算"
                    ]
                })
        
        # 检查成功率
        if summary["success_rate"] < (1.0 - self.thresholds["error_rate_threshold"]):
            recommendations.append({
                "type": "reliability_improvement",
                "priority": "high",
                "title": "提高操作成功率",
                "description": f"成功率 {summary['success_rate']:.2%} 低于预期",
                "suggestions": [
                    "增强错误处理机制",
                    "添加重试逻辑",
                    "改进输入验证",
                    "优化异常恢复"
                ]
            })
        
        return recommendations
    
    def _check_performance_thresholds(self, report: PerformanceReport) -> None:
        """检查性能阈值"""
        operation_name = report.operation_name.lower().replace(' ', '_')
        threshold_key = f"{operation_name}_max_time"
        threshold = self.thresholds.get(threshold_key)
        
        if threshold and report.duration > threshold:
            logger.warning(f"Performance threshold exceeded for {report.operation_name}: "
                         f"{report.duration:.2f}s > {threshold}s")
    
    def _get_slowest_operations(self, reports: List[PerformanceReport], limit: int) -> List[Dict[str, Any]]:
        """获取最慢的操作"""
        sorted_reports = sorted(reports, key=lambda r: r.duration, reverse=True)
        
        return [
            {
                "operation_name": report.operation_name,
                "duration": report.duration,
                "timestamp": report.start_time.isoformat(),
                "success": report.success,
                "performance_level": report.performance_level.value
            }
            for report in sorted_reports[:limit]
        ]
    
    def _get_failed_operations(self, reports: List[PerformanceReport], limit: int) -> List[Dict[str, Any]]:
        """获取失败的操作"""
        failed_reports = [report for report in reports if not report.success]
        sorted_reports = sorted(failed_reports, key=lambda r: r.start_time, reverse=True)
        
        return [
            {
                "operation_name": report.operation_name,
                "duration": report.duration,
                "timestamp": report.start_time.isoformat(),
                "error_message": report.error_message,
                "performance_level": report.performance_level.value
            }
            for report in sorted_reports[:limit]
        ]
    
    def clear_old_data(self, days: int = 7) -> int:
        """清理旧的性能数据"""
        cutoff_time = datetime.now() - timedelta(days=days)
        
        with self._lock:
            # 清理报告
            old_reports_count = len(self.reports)
            self.reports = [report for report in self.reports if report.start_time >= cutoff_time]
            removed_reports = old_reports_count - len(self.reports)
            
            # 清理指标历史
            for metric_type, metrics in self.metrics_history.items():
                old_metrics_count = len(metrics)
                self.metrics_history[metric_type] = [
                    metric for metric in metrics if metric.timestamp >= cutoff_time
                ]
                removed_metrics = old_metrics_count - len(self.metrics_history[metric_type])
                
                if removed_metrics > 0:
                    logger.debug(f"Removed {removed_metrics} old {metric_type} metrics")
        
        if removed_reports > 0:
            logger.info(f"Cleaned up {removed_reports} old performance reports (older than {days} days)")
        
        return removed_reports


def performance_monitor(operation_name: str, cache_key_params: Optional[Dict[str, Any]] = None,
                       cache_ttl: Optional[int] = None, enable_cache: bool = True):
    """性能监控装饰器"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 获取性能监控器实例
            monitor = getattr(args[0], '_performance_monitor', None) if args else None
            if not monitor:
                # 如果没有监控器，直接执行函数
                return func(*args, **kwargs)
            
            # 生成缓存键
            cache_key = None
            if enable_cache and cache_key_params:
                try:
                    # 从参数中提取缓存键参数
                    cache_params = {}
                    for param_name in cache_key_params:
                        if param_name in kwargs:
                            cache_params[param_name] = kwargs[param_name]
                        elif len(args) > cache_key_params.get(param_name, -1):
                            cache_params[param_name] = args[cache_key_params[param_name]]
                    
                    cache_key = monitor.get_cache_key(operation_name, cache_params)
                    
                    # 尝试从缓存获取结果
                    cached_result = monitor.get_cached_result(cache_key)
                    if cached_result is not None:
                        logger.debug(f"Cache hit for {operation_name}")
                        return cached_result
                
                except Exception as e:
                    logger.warning(f"Cache key generation failed for {operation_name}: {e}")
            
            # 开始性能监控
            operation_id = monitor.start_operation(operation_name, {
                "function_name": func.__name__,
                "cache_enabled": enable_cache,
                "cache_key": cache_key
            })
            
            try:
                # 执行函数
                result = func(*args, **kwargs)
                
                # 缓存结果
                if enable_cache and cache_key:
                    monitor.set_cached_result(cache_key, result, cache_ttl)
                
                # 结束监控（成功）
                monitor.end_operation(operation_id, success=True)
                
                return result
                
            except Exception as e:
                # 结束监控（失败）
                monitor.end_operation(operation_id, success=False, error_message=str(e))
                raise
        
        return wrapper
    return decorator


# 全局性能监控器实例
_global_performance_monitor = PerformanceMonitor()


def get_global_performance_monitor() -> PerformanceMonitor:
    """获取全局性能监控器"""
    return _global_performance_monitor