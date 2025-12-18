"""
Rate Limiting and Circuit Breaker Protection for Video Studio

This module provides comprehensive rate limiting and circuit breaker mechanisms
to protect the system from overload and prevent cascading failures.

Validates: Requirements 7.2
"""

import time
import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, Optional, Callable, Any, List
from enum import Enum
from collections import deque
from functools import wraps
import threading


class CircuitState(Enum):
    """States of a circuit breaker"""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Blocking requests
    HALF_OPEN = "half_open"  # Testing if service recovered


class RateLimitStrategy(Enum):
    """Rate limiting strategies"""
    FIXED_WINDOW = "fixed_window"
    SLIDING_WINDOW = "sliding_window"
    TOKEN_BUCKET = "token_bucket"
    LEAKY_BUCKET = "leaky_bucket"


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting"""
    max_requests: int
    time_window_seconds: float
    strategy: RateLimitStrategy = RateLimitStrategy.SLIDING_WINDOW
    burst_size: Optional[int] = None  # For token bucket
    
    def validate(self) -> bool:
        """Validate rate limit configuration"""
        if self.max_requests <= 0:
            return False
        if self.time_window_seconds <= 0:
            return False
        if self.burst_size is not None and self.burst_size < self.max_requests:
            return False
        return True


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker"""
    failure_threshold: int = 5  # Number of failures before opening
    success_threshold: int = 2  # Successes needed to close from half-open
    timeout_seconds: float = 60.0  # Time before trying half-open
    half_open_max_calls: int = 3  # Max calls to test in half-open state
    
    def validate(self) -> bool:
        """Validate circuit breaker configuration"""
        if self.failure_threshold <= 0:
            return False
        if self.success_threshold <= 0:
            return False
        if self.timeout_seconds <= 0:
            return False
        if self.half_open_max_calls <= 0:
            return False
        return True


@dataclass
class RequestRecord:
    """Record of a single request"""
    timestamp: datetime
    success: bool
    duration: float = 0.0


class RateLimiter:
    """
    Rate limiter implementation supporting multiple strategies.
    
    Prevents system overload by limiting the number of requests
    within a specified time window.
    """
    
    def __init__(self, config: RateLimitConfig, identifier: str = "default"):
        """
        Initialize rate limiter.
        
        Args:
            config: Rate limit configuration
            identifier: Unique identifier for this limiter
        """
        if not config.validate():
            raise ValueError("Invalid rate limit configuration")
        
        self.config = config
        self.identifier = identifier
        
        # Request tracking
        self.requests: deque = deque()
        self._lock = threading.Lock()
        
        # Token bucket specific
        self.tokens = config.burst_size or config.max_requests
        self.last_refill = time.time()
    
    def is_allowed(self) -> bool:
        """
        Check if a request is allowed under current rate limits.
        
        Returns:
            True if request is allowed, False if rate limited
        """
        with self._lock:
            if self.config.strategy == RateLimitStrategy.SLIDING_WINDOW:
                return self._sliding_window_check()
            elif self.config.strategy == RateLimitStrategy.FIXED_WINDOW:
                return self._fixed_window_check()
            elif self.config.strategy == RateLimitStrategy.TOKEN_BUCKET:
                return self._token_bucket_check()
            elif self.config.strategy == RateLimitStrategy.LEAKY_BUCKET:
                return self._leaky_bucket_check()
            
            return False
    
    def _sliding_window_check(self) -> bool:
        """Sliding window rate limit check"""
        now = datetime.now()
        cutoff = now - timedelta(seconds=self.config.time_window_seconds)
        
        # Remove old requests
        while self.requests and self.requests[0] < cutoff:
            self.requests.popleft()
        
        # Check if under limit
        if len(self.requests) < self.config.max_requests:
            self.requests.append(now)
            return True
        
        return False
    
    def _fixed_window_check(self) -> bool:
        """Fixed window rate limit check"""
        now = datetime.now()
        window_start = datetime.fromtimestamp(
            (now.timestamp() // self.config.time_window_seconds) * self.config.time_window_seconds
        )
        
        # Remove requests from previous windows
        while self.requests and self.requests[0] < window_start:
            self.requests.popleft()
        
        # Check if under limit
        if len(self.requests) < self.config.max_requests:
            self.requests.append(now)
            return True
        
        return False
    
    def _token_bucket_check(self) -> bool:
        """Token bucket rate limit check"""
        now = time.time()
        
        # Refill tokens based on time passed
        time_passed = now - self.last_refill
        tokens_to_add = time_passed * (self.config.max_requests / self.config.time_window_seconds)
        
        max_tokens = self.config.burst_size or self.config.max_requests
        self.tokens = min(max_tokens, self.tokens + tokens_to_add)
        self.last_refill = now
        
        # Check if we have tokens available
        if self.tokens >= 1.0:
            self.tokens -= 1.0
            return True
        
        return False
    
    def _leaky_bucket_check(self) -> bool:
        """Leaky bucket rate limit check"""
        now = datetime.now()
        
        # Calculate leak rate
        leak_rate = self.config.max_requests / self.config.time_window_seconds
        
        # Remove leaked requests
        if self.requests:
            last_request = self.requests[-1]
            time_passed = (now - last_request).total_seconds()
            leaked = int(time_passed * leak_rate)
            
            for _ in range(min(leaked, len(self.requests))):
                if self.requests:
                    self.requests.popleft()
        
        # Check if bucket has space
        if len(self.requests) < self.config.max_requests:
            self.requests.append(now)
            return True
        
        return False
    
    def get_remaining_quota(self) -> int:
        """Get remaining request quota"""
        with self._lock:
            if self.config.strategy == RateLimitStrategy.TOKEN_BUCKET:
                return int(self.tokens)
            else:
                now = datetime.now()
                cutoff = now - timedelta(seconds=self.config.time_window_seconds)
                
                # Count valid requests
                valid_requests = sum(1 for req in self.requests if req >= cutoff)
                return max(0, self.config.max_requests - valid_requests)
    
    def get_reset_time(self) -> Optional[datetime]:
        """Get time when rate limit will reset"""
        with self._lock:
            if not self.requests:
                return None
            
            if self.config.strategy == RateLimitStrategy.FIXED_WINDOW:
                now = datetime.now()
                window_start = datetime.fromtimestamp(
                    (now.timestamp() // self.config.time_window_seconds) * self.config.time_window_seconds
                )
                return window_start + timedelta(seconds=self.config.time_window_seconds)
            else:
                # For sliding window, return when oldest request expires
                if self.requests:
                    oldest = self.requests[0]
                    return oldest + timedelta(seconds=self.config.time_window_seconds)
            
            return None
    
    def reset(self):
        """Reset rate limiter state"""
        with self._lock:
            self.requests.clear()
            self.tokens = self.config.burst_size or self.config.max_requests
            self.last_refill = time.time()


class CircuitBreaker:
    """
    Circuit breaker implementation to prevent cascading failures.
    
    Monitors operation failures and opens the circuit to prevent
    further requests when failure threshold is exceeded.
    """
    
    def __init__(self, config: CircuitBreakerConfig, identifier: str = "default"):
        """
        Initialize circuit breaker.
        
        Args:
            config: Circuit breaker configuration
            identifier: Unique identifier for this breaker
        """
        if not config.validate():
            raise ValueError("Invalid circuit breaker configuration")
        
        self.config = config
        self.identifier = identifier
        
        # State management
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.last_state_change: datetime = datetime.now()
        self.half_open_calls = 0
        
        # Request history
        self.request_history: deque = deque(maxlen=100)
        
        # Callbacks
        self.state_change_callbacks: List[Callable] = []
        
        self._lock = threading.Lock()
    
    def is_allowed(self) -> bool:
        """
        Check if a request is allowed through the circuit breaker.
        
        Returns:
            True if request is allowed, False if circuit is open
        """
        with self._lock:
            if self.state == CircuitState.CLOSED:
                return True
            
            elif self.state == CircuitState.OPEN:
                # Check if timeout has passed
                if self.last_failure_time:
                    time_since_failure = (datetime.now() - self.last_failure_time).total_seconds()
                    if time_since_failure >= self.config.timeout_seconds:
                        self._transition_to_half_open()
                        return True
                
                return False
            
            elif self.state == CircuitState.HALF_OPEN:
                # Allow limited requests in half-open state
                if self.half_open_calls < self.config.half_open_max_calls:
                    self.half_open_calls += 1
                    return True
                
                return False
            
            return False
    
    def record_success(self, duration: float = 0.0):
        """Record a successful operation"""
        with self._lock:
            record = RequestRecord(
                timestamp=datetime.now(),
                success=True,
                duration=duration
            )
            self.request_history.append(record)
            
            if self.state == CircuitState.HALF_OPEN:
                self.success_count += 1
                
                # Close circuit if enough successes
                if self.success_count >= self.config.success_threshold:
                    self._transition_to_closed()
            
            elif self.state == CircuitState.CLOSED:
                # Reset failure count on success
                self.failure_count = 0
    
    def record_failure(self, duration: float = 0.0):
        """Record a failed operation"""
        with self._lock:
            record = RequestRecord(
                timestamp=datetime.now(),
                success=False,
                duration=duration
            )
            self.request_history.append(record)
            
            self.failure_count += 1
            self.last_failure_time = datetime.now()
            
            if self.state == CircuitState.CLOSED:
                # Open circuit if failure threshold exceeded
                if self.failure_count >= self.config.failure_threshold:
                    self._transition_to_open()
            
            elif self.state == CircuitState.HALF_OPEN:
                # Immediately open on any failure in half-open state
                self._transition_to_open()
    
    def _transition_to_open(self):
        """Transition circuit to OPEN state"""
        old_state = self.state
        self.state = CircuitState.OPEN
        self.last_state_change = datetime.now()
        self.success_count = 0
        self.half_open_calls = 0
        
        self._notify_state_change(old_state, CircuitState.OPEN)
    
    def _transition_to_half_open(self):
        """Transition circuit to HALF_OPEN state"""
        old_state = self.state
        self.state = CircuitState.HALF_OPEN
        self.last_state_change = datetime.now()
        self.success_count = 0
        self.failure_count = 0
        self.half_open_calls = 0
        
        self._notify_state_change(old_state, CircuitState.HALF_OPEN)
    
    def _transition_to_closed(self):
        """Transition circuit to CLOSED state"""
        old_state = self.state
        self.state = CircuitState.CLOSED
        self.last_state_change = datetime.now()
        self.failure_count = 0
        self.success_count = 0
        self.half_open_calls = 0
        
        self._notify_state_change(old_state, CircuitState.CLOSED)
    
    def _notify_state_change(self, old_state: CircuitState, new_state: CircuitState):
        """Notify callbacks of state change"""
        for callback in self.state_change_callbacks:
            try:
                callback(self.identifier, old_state, new_state)
            except Exception:
                pass  # Don't let callback errors affect circuit breaker
    
    def register_state_change_callback(self, callback: Callable):
        """Register a callback for state changes"""
        if callback not in self.state_change_callbacks:
            self.state_change_callbacks.append(callback)
    
    def get_state(self) -> CircuitState:
        """Get current circuit state"""
        return self.state
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get circuit breaker metrics"""
        with self._lock:
            recent_requests = list(self.request_history)
            
            total_requests = len(recent_requests)
            successful_requests = sum(1 for r in recent_requests if r.success)
            failed_requests = total_requests - successful_requests
            
            return {
                "state": self.state.value,
                "failure_count": self.failure_count,
                "success_count": self.success_count,
                "last_state_change": self.last_state_change.isoformat(),
                "last_failure_time": self.last_failure_time.isoformat() if self.last_failure_time else None,
                "recent_requests": {
                    "total": total_requests,
                    "successful": successful_requests,
                    "failed": failed_requests,
                    "success_rate": successful_requests / total_requests if total_requests > 0 else 0.0
                }
            }
    
    def reset(self):
        """Reset circuit breaker to closed state"""
        with self._lock:
            self.state = CircuitState.CLOSED
            self.failure_count = 0
            self.success_count = 0
            self.half_open_calls = 0
            self.last_failure_time = None
            self.last_state_change = datetime.now()
            self.request_history.clear()


class ProtectionManager:
    """
    Manages rate limiters and circuit breakers for the entire system.
    
    Provides centralized protection mechanisms for different services and operations.
    """
    
    def __init__(self):
        self.rate_limiters: Dict[str, RateLimiter] = {}
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self._lock = threading.Lock()
    
    def create_rate_limiter(self, identifier: str, config: RateLimitConfig) -> RateLimiter:
        """Create or update a rate limiter"""
        with self._lock:
            limiter = RateLimiter(config, identifier)
            self.rate_limiters[identifier] = limiter
            return limiter
    
    def get_rate_limiter(self, identifier: str) -> Optional[RateLimiter]:
        """Get a rate limiter by identifier"""
        return self.rate_limiters.get(identifier)
    
    def create_circuit_breaker(self, identifier: str, config: CircuitBreakerConfig) -> CircuitBreaker:
        """Create or update a circuit breaker"""
        with self._lock:
            breaker = CircuitBreaker(config, identifier)
            self.circuit_breakers[identifier] = breaker
            return breaker
    
    def get_circuit_breaker(self, identifier: str) -> Optional[CircuitBreaker]:
        """Get a circuit breaker by identifier"""
        return self.circuit_breakers.get(identifier)
    
    def check_protection(self, identifier: str) -> tuple[bool, Optional[str]]:
        """
        Check both rate limiting and circuit breaker for an identifier.
        
        Returns:
            (allowed, reason) - True if allowed, False with reason if blocked
        """
        # Check rate limiter
        limiter = self.get_rate_limiter(identifier)
        if limiter and not limiter.is_allowed():
            return False, "Rate limit exceeded"
        
        # Check circuit breaker
        breaker = self.get_circuit_breaker(identifier)
        if breaker and not breaker.is_allowed():
            return False, f"Circuit breaker is {breaker.get_state().value}"
        
        return True, None
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """Get metrics for all rate limiters and circuit breakers"""
        return {
            "rate_limiters": {
                identifier: {
                    "remaining_quota": limiter.get_remaining_quota(),
                    "reset_time": limiter.get_reset_time().isoformat() if limiter.get_reset_time() else None
                }
                for identifier, limiter in self.rate_limiters.items()
            },
            "circuit_breakers": {
                identifier: breaker.get_metrics()
                for identifier, breaker in self.circuit_breakers.items()
            }
        }


# Global protection manager instance
protection_manager = ProtectionManager()


def get_protection_manager() -> ProtectionManager:
    """Get the global protection manager instance"""
    return protection_manager


# Decorator for rate limiting
def with_rate_limit(identifier: str, config: Optional[RateLimitConfig] = None):
    """
    Decorator to apply rate limiting to a function.
    
    Args:
        identifier: Unique identifier for the rate limiter
        config: Optional rate limit configuration (uses default if None)
    """
    def decorator(func):
        # Create rate limiter if config provided
        if config:
            protection_manager.create_rate_limiter(identifier, config)
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            limiter = protection_manager.get_rate_limiter(identifier)
            if limiter and not limiter.is_allowed():
                raise Exception(f"Rate limit exceeded for {identifier}")
            
            return await func(*args, **kwargs)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            limiter = protection_manager.get_rate_limiter(identifier)
            if limiter and not limiter.is_allowed():
                raise Exception(f"Rate limit exceeded for {identifier}")
            
            return func(*args, **kwargs)
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    return decorator


# Decorator for circuit breaker
def with_circuit_breaker(identifier: str, config: Optional[CircuitBreakerConfig] = None):
    """
    Decorator to apply circuit breaker protection to a function.
    
    Args:
        identifier: Unique identifier for the circuit breaker
        config: Optional circuit breaker configuration (uses default if None)
    """
    def decorator(func):
        # Create circuit breaker if config provided
        if config:
            protection_manager.create_circuit_breaker(identifier, config)
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            breaker = protection_manager.get_circuit_breaker(identifier)
            if breaker and not breaker.is_allowed():
                raise Exception(f"Circuit breaker is {breaker.get_state().value} for {identifier}")
            
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                if breaker:
                    breaker.record_success(duration)
                return result
            except Exception as e:
                duration = time.time() - start_time
                if breaker:
                    breaker.record_failure(duration)
                raise e
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            breaker = protection_manager.get_circuit_breaker(identifier)
            if breaker and not breaker.is_allowed():
                raise Exception(f"Circuit breaker is {breaker.get_state().value} for {identifier}")
            
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                if breaker:
                    breaker.record_success(duration)
                return result
            except Exception as e:
                duration = time.time() - start_time
                if breaker:
                    breaker.record_failure(duration)
                raise e
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    return decorator
