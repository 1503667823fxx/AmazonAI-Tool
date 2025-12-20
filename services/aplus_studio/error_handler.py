"""
A+Studio错误处理和重试机制
实现API调用失败的错误处理、重试逻辑和熔断保护
"""

import time
import logging
import random
from typing import Dict, Any, Callable, Optional, Type, Union
from functools import wraps
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timedelta


class ErrorType(Enum):
    """错误类型枚举"""
    NETWORK_ERROR = "network_error"
    API_ERROR = "api_error"
    RATE_LIMIT_ERROR = "rate_limit_error"
    AUTHENTICATION_ERROR = "authentication_error"
    VALIDATION_ERROR = "validation_error"
    TIMEOUT_ERROR = "timeout_error"
    SERVER_ERROR = "server_error"
    UNKNOWN_ERROR = "unknown_error"


class RetryStrategy(Enum):
    """重试策略枚举"""
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    LINEAR_BACKOFF = "linear_backoff"
    FIXED_DELAY = "fixed_delay"
    RANDOM_JITTER = "random_jitter"


@dataclass
class RetryConfig:
    """重试配置"""
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    backoff_multiplier: float = 2.0
    jitter: bool = True
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF


@dataclass
class CircuitBreakerConfig:
    """熔断器配置"""
    failure_threshold: int = 5
    recovery_timeout: float = 60.0
    half_open_max_calls: int = 3


class CircuitBreakerState(Enum):
    """熔断器状态"""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class ErrorStats:
    """错误统计"""
    total_calls: int = 0
    failed_calls: int = 0
    success_calls: int = 0
    last_failure_time: Optional[datetime] = None
    last_success_time: Optional[datetime] = None
    error_types: Dict[ErrorType, int] = field(default_factory=dict)
    
    @property
    def failure_rate(self) -> float:
        """失败率"""
        if self.total_calls == 0:
            return 0.0
        return self.failed_calls / self.total_calls
    
    @property
    def success_rate(self) -> float:
        """成功率"""
        return 1.0 - self.failure_rate


class CircuitBreaker:
    """熔断器实现"""
    
    def __init__(self, config: CircuitBreakerConfig):
        self.config = config
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.half_open_calls = 0
    
    def can_execute(self) -> bool:
        """检查是否可以执行"""
        if self.state == CircuitBreakerState.CLOSED:
            return True
        
        if self.state == CircuitBreakerState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitBreakerState.HALF_OPEN
                self.half_open_calls = 0
                return True
            return False
        
        if self.state == CircuitBreakerState.HALF_OPEN:
            return self.half_open_calls < self.config.half_open_max_calls
        
        return False
    
    def record_success(self):
        """记录成功调用"""
        if self.state == CircuitBreakerState.HALF_OPEN:
            self.half_open_calls += 1
            if self.half_open_calls >= self.config.half_open_max_calls:
                self.state = CircuitBreakerState.CLOSED
                self.failure_count = 0
        elif self.state == CircuitBreakerState.CLOSED:
            self.failure_count = max(0, self.failure_count - 1)
    
    def record_failure(self):
        """记录失败调用"""
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        
        if self.state == CircuitBreakerState.HALF_OPEN:
            self.state = CircuitBreakerState.OPEN
        elif (self.state == CircuitBreakerState.CLOSED and 
              self.failure_count >= self.config.failure_threshold):
            self.state = CircuitBreakerState.OPEN
    
    def _should_attempt_reset(self) -> bool:
        """检查是否应该尝试重置"""
        if not self.last_failure_time:
            return True
        
        time_since_failure = datetime.now() - self.last_failure_time
        return time_since_failure.total_seconds() >= self.config.recovery_timeout


class ErrorHandler:
    """错误处理器"""
    
    def __init__(self, 
                 retry_config: Optional[RetryConfig] = None,
                 circuit_breaker_config: Optional[CircuitBreakerConfig] = None,
                 enable_logging: bool = True):
        self.retry_config = retry_config or RetryConfig()
        self.circuit_breaker = CircuitBreaker(circuit_breaker_config or CircuitBreakerConfig())
        self.stats = ErrorStats()
        self.enable_logging = enable_logging
        
        if enable_logging:
            self.logger = logging.getLogger(__name__)
    
    def handle_with_retry(self, func: Callable, *args, **kwargs) -> Any:
        """带重试的函数执行"""
        last_exception = None
        
        for attempt in range(self.retry_config.max_attempts):
            # 检查熔断器状态
            if not self.circuit_breaker.can_execute():
                raise Exception("Circuit breaker is open")
            
            try:
                self.stats.total_calls += 1
                result = func(*args, **kwargs)
                
                # 记录成功
                self.stats.success_calls += 1
                self.stats.last_success_time = datetime.now()
                self.circuit_breaker.record_success()
                
                if self.enable_logging:
                    self.logger.info(f"Function {func.__name__} succeeded on attempt {attempt + 1}")
                
                return result
                
            except Exception as e:
                last_exception = e
                error_type = self._classify_error(e)
                
                # 记录失败
                self.stats.failed_calls += 1
                self.stats.last_failure_time = datetime.now()
                self.stats.error_types[error_type] = self.stats.error_types.get(error_type, 0) + 1
                self.circuit_breaker.record_failure()
                
                if self.enable_logging:
                    self.logger.warning(f"Function {func.__name__} failed on attempt {attempt + 1}: {e}")
                
                # 检查是否应该重试
                if not self._should_retry(error_type, attempt):
                    break
                
                # 计算延迟时间
                if attempt < self.retry_config.max_attempts - 1:
                    delay = self._calculate_delay(attempt)
                    if self.enable_logging:
                        self.logger.info(f"Retrying in {delay:.2f} seconds...")
                    time.sleep(delay)
        
        # 所有重试都失败了
        if self.enable_logging:
            self.logger.error(f"Function {func.__name__} failed after {self.retry_config.max_attempts} attempts")
        
        raise last_exception
    
    def _classify_error(self, error: Exception) -> ErrorType:
        """分类错误类型"""
        error_message = str(error).lower()
        
        if "network" in error_message or "connection" in error_message:
            return ErrorType.NETWORK_ERROR
        elif "rate limit" in error_message or "quota" in error_message:
            return ErrorType.RATE_LIMIT_ERROR
        elif "authentication" in error_message or "unauthorized" in error_message:
            return ErrorType.AUTHENTICATION_ERROR
        elif "timeout" in error_message:
            return ErrorType.TIMEOUT_ERROR
        elif "server error" in error_message or "500" in error_message:
            return ErrorType.SERVER_ERROR
        elif "validation" in error_message or "invalid" in error_message:
            return ErrorType.VALIDATION_ERROR
        elif "api" in error_message:
            return ErrorType.API_ERROR
        else:
            return ErrorType.UNKNOWN_ERROR
    
    def _should_retry(self, error_type: ErrorType, attempt: int) -> bool:
        """判断是否应该重试"""
        # 某些错误类型不应该重试
        non_retryable_errors = {
            ErrorType.AUTHENTICATION_ERROR,
            ErrorType.VALIDATION_ERROR
        }
        
        if error_type in non_retryable_errors:
            return False
        
        return attempt < self.retry_config.max_attempts - 1
    
    def _calculate_delay(self, attempt: int) -> float:
        """计算延迟时间"""
        if self.retry_config.strategy == RetryStrategy.EXPONENTIAL_BACKOFF:
            delay = self.retry_config.base_delay * (self.retry_config.backoff_multiplier ** attempt)
        elif self.retry_config.strategy == RetryStrategy.LINEAR_BACKOFF:
            delay = self.retry_config.base_delay * (attempt + 1)
        elif self.retry_config.strategy == RetryStrategy.FIXED_DELAY:
            delay = self.retry_config.base_delay
        elif self.retry_config.strategy == RetryStrategy.RANDOM_JITTER:
            delay = self.retry_config.base_delay + random.uniform(0, self.retry_config.base_delay)
        else:
            delay = self.retry_config.base_delay
        
        # 应用抖动
        if self.retry_config.jitter:
            jitter = random.uniform(0.1, 0.3) * delay
            delay += jitter
        
        # 限制最大延迟
        return min(delay, self.retry_config.max_delay)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取错误统计信息"""
        return {
            "total_calls": self.stats.total_calls,
            "success_calls": self.stats.success_calls,
            "failed_calls": self.stats.failed_calls,
            "success_rate": self.stats.success_rate,
            "failure_rate": self.stats.failure_rate,
            "last_success_time": self.stats.last_success_time.isoformat() if self.stats.last_success_time else None,
            "last_failure_time": self.stats.last_failure_time.isoformat() if self.stats.last_failure_time else None,
            "error_types": {error_type.value: count for error_type, count in self.stats.error_types.items()},
            "circuit_breaker_state": self.circuit_breaker.state.value,
            "circuit_breaker_failure_count": self.circuit_breaker.failure_count
        }
    
    def reset_stats(self):
        """重置统计信息"""
        self.stats = ErrorStats()
        self.circuit_breaker = CircuitBreaker(self.circuit_breaker.config)


def with_error_handling(retry_config: Optional[RetryConfig] = None,
                       circuit_breaker_config: Optional[CircuitBreakerConfig] = None,
                       enable_logging: bool = True):
    """错误处理装饰器"""
    def decorator(func: Callable) -> Callable:
        error_handler = ErrorHandler(retry_config, circuit_breaker_config, enable_logging)
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            return error_handler.handle_with_retry(func, *args, **kwargs)
        
        # 添加统计信息访问方法
        wrapper.get_error_stats = error_handler.get_stats
        wrapper.reset_error_stats = error_handler.reset_stats
        
        return wrapper
    
    return decorator


# 预定义的错误处理配置
DEFAULT_RETRY_CONFIG = RetryConfig(
    max_attempts=3,
    base_delay=1.0,
    max_delay=30.0,
    backoff_multiplier=2.0,
    jitter=True,
    strategy=RetryStrategy.EXPONENTIAL_BACKOFF
)

API_RETRY_CONFIG = RetryConfig(
    max_attempts=5,
    base_delay=2.0,
    max_delay=60.0,
    backoff_multiplier=1.5,
    jitter=True,
    strategy=RetryStrategy.EXPONENTIAL_BACKOFF
)

NETWORK_RETRY_CONFIG = RetryConfig(
    max_attempts=3,
    base_delay=0.5,
    max_delay=10.0,
    backoff_multiplier=2.0,
    jitter=True,
    strategy=RetryStrategy.EXPONENTIAL_BACKOFF
)

DEFAULT_CIRCUIT_BREAKER_CONFIG = CircuitBreakerConfig(
    failure_threshold=5,
    recovery_timeout=60.0,
    half_open_max_calls=3
)


# 便捷的装饰器
def with_api_retry(func: Callable) -> Callable:
    """API调用重试装饰器"""
    return with_error_handling(API_RETRY_CONFIG, DEFAULT_CIRCUIT_BREAKER_CONFIG)(func)


def with_network_retry(func: Callable) -> Callable:
    """网络调用重试装饰器"""
    return with_error_handling(NETWORK_RETRY_CONFIG, DEFAULT_CIRCUIT_BREAKER_CONFIG)(func)


def with_simple_retry(max_attempts: int = 3, delay: float = 1.0) -> Callable:
    """简单重试装饰器"""
    config = RetryConfig(
        max_attempts=max_attempts,
        base_delay=delay,
        strategy=RetryStrategy.FIXED_DELAY,
        jitter=False
    )
    return with_error_handling(config, None, False)