"""
Property-Based Tests for System Monitoring and Alerting

**Feature: video-studio-redesign, Property 12: 系统监控和告警**

Tests that the system correctly records key performance indicators,
implements protection mechanisms (rate limiting, circuit breaker),
and automatically triggers alerts when thresholds are exceeded.

**Validates: Requirements 7.1, 7.2, 7.4**
"""

import time
import pytest
from hypothesis import given, strategies as st, settings, assume, HealthCheck
from datetime import datetime, timedelta
from typing import List, Dict, Any

from app_utils.video_studio.performance_monitor import (
    PerformanceMonitor,
    MetricType,
    PerformanceThresholds,
    SystemMetrics
)
from app_utils.video_studio.rate_limiter import (
    RateLimiter,
    CircuitBreaker,
    RateLimitConfig,
    CircuitBreakerConfig,
    RateLimitStrategy,
    CircuitState,
    ProtectionManager
)
from app_utils.video_studio.analytics_engine import (
    AnalyticsEngine,
    UsageRecord,
    ModelPricing,
    ReportPeriod
)


# ============================================================================
# Property 12.1: Performance Metrics Collection Consistency
# ============================================================================

@given(
    collection_count=st.integers(min_value=1, max_value=10)
)
@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_property_performance_metrics_collection_consistency(collection_count):
    """
    Property: For any number of metric collections, the system should
    successfully collect and store all key performance indicators
    (CPU, memory, disk, network) without data loss.
    
    Validates: Requirements 7.1
    """
    monitor = PerformanceMonitor(collection_interval=0.1, history_size=100)
    
    # Collect metrics multiple times
    collected_metrics = []
    for _ in range(collection_count):
        metrics = monitor.collect_system_metrics()
        collected_metrics.append(metrics)
        time.sleep(0.05)  # Small delay between collections
    
    # Property: All collections should succeed
    assert len(collected_metrics) == collection_count, \
        "All metric collections should succeed"
    
    # Property: Each metric should have all required fields
    for metrics in collected_metrics:
        assert isinstance(metrics, SystemMetrics), \
            "Collected data should be SystemMetrics instance"
        assert metrics.cpu_percent >= 0, \
            "CPU percentage should be non-negative"
        assert metrics.memory_percent >= 0, \
            "Memory percentage should be non-negative"
        assert metrics.disk_usage_percent >= 0, \
            "Disk usage should be non-negative"
        assert metrics.network_bytes_sent >= 0, \
            "Network bytes sent should be non-negative"
        assert metrics.network_bytes_recv >= 0, \
            "Network bytes received should be non-negative"
    
    # Property: Metrics should be stored in history
    assert len(monitor.system_metrics_history) == collection_count, \
        "All metrics should be stored in history"


# ============================================================================
# Property 12.2: Alert Triggering Consistency
# ============================================================================

@given(
    cpu_threshold=st.floats(min_value=50.0, max_value=95.0),
    memory_threshold=st.floats(min_value=50.0, max_value=95.0)
)
@settings(max_examples=100, deadline=None)
def test_property_alert_triggering_consistency(cpu_threshold, memory_threshold):
    """
    Property: For any threshold configuration, when metrics exceed
    the threshold, alerts should be triggered consistently.
    
    Validates: Requirements 7.1, 7.4
    """
    monitor = PerformanceMonitor()
    
    # Configure thresholds
    monitor.thresholds.cpu_warning = cpu_threshold
    monitor.thresholds.memory_warning = memory_threshold
    
    # Track alerts
    alerts_triggered = []
    
    def alert_callback(severity, message, metrics):
        alerts_triggered.append({
            'severity': severity,
            'message': message,
            'metrics': metrics
        })
    
    monitor.register_alert_callback(alert_callback)
    
    # Create mock metrics that exceed thresholds
    mock_metrics = SystemMetrics(
        timestamp=datetime.now(),
        cpu_percent=cpu_threshold + 5.0,  # Exceed threshold
        memory_percent=memory_threshold + 5.0,  # Exceed threshold
        memory_used_mb=1000.0,
        memory_available_mb=500.0,
        disk_usage_percent=50.0,
        disk_free_gb=100.0,
        network_bytes_sent=1000,
        network_bytes_recv=1000,
        active_tasks=0
    )
    
    # Check thresholds (this should trigger alerts)
    monitor._check_thresholds(mock_metrics)
    
    # Property: Alerts should be triggered for exceeded thresholds
    assert len(alerts_triggered) >= 1, \
        "Alerts should be triggered when thresholds are exceeded"
    
    # Property: Alert messages should contain relevant information
    for alert in alerts_triggered:
        assert 'severity' in alert, "Alert should have severity"
        assert 'message' in alert, "Alert should have message"
        assert alert['severity'] in ['warning', 'critical'], \
            "Alert severity should be valid"


# ============================================================================
# Property 12.3: Rate Limiting Consistency
# ============================================================================

@given(
    max_requests=st.integers(min_value=1, max_value=20),
    time_window=st.floats(min_value=1.0, max_value=10.0),
    request_count=st.integers(min_value=1, max_value=30)
)
@settings(max_examples=100, deadline=None)
def test_property_rate_limiting_consistency(max_requests, time_window, request_count):
    """
    Property: For any rate limit configuration, the rate limiter should
    allow at most max_requests within the time window, blocking additional
    requests consistently.
    
    Validates: Requirements 7.2
    """
    assume(request_count > max_requests)  # Only test when we exceed limit
    
    config = RateLimitConfig(
        max_requests=max_requests,
        time_window_seconds=time_window,
        strategy=RateLimitStrategy.SLIDING_WINDOW
    )
    
    limiter = RateLimiter(config, identifier="test_limiter")
    
    # Make requests
    allowed_count = 0
    blocked_count = 0
    
    for _ in range(request_count):
        if limiter.is_allowed():
            allowed_count += 1
        else:
            blocked_count += 1
    
    # Property: Should allow exactly max_requests
    assert allowed_count == max_requests, \
        f"Should allow exactly {max_requests} requests, but allowed {allowed_count}"
    
    # Property: Should block excess requests
    assert blocked_count == request_count - max_requests, \
        f"Should block {request_count - max_requests} requests, but blocked {blocked_count}"
    
    # Property: Remaining quota should be zero after hitting limit
    remaining = limiter.get_remaining_quota()
    assert remaining == 0, \
        "Remaining quota should be zero after hitting rate limit"


# ============================================================================
# Property 12.4: Circuit Breaker State Transitions
# ============================================================================

@given(
    failure_threshold=st.integers(min_value=2, max_value=10),
    failure_count=st.integers(min_value=1, max_value=15)
)
@settings(max_examples=100, deadline=None)
def test_property_circuit_breaker_state_transitions(failure_threshold, failure_count):
    """
    Property: For any failure threshold, the circuit breaker should
    transition to OPEN state when failures reach the threshold,
    and block subsequent requests consistently.
    
    Validates: Requirements 7.2
    """
    config = CircuitBreakerConfig(
        failure_threshold=failure_threshold,
        success_threshold=2,
        timeout_seconds=60.0
    )
    
    breaker = CircuitBreaker(config, identifier="test_breaker")
    
    # Initial state should be CLOSED
    assert breaker.get_state() == CircuitState.CLOSED, \
        "Circuit breaker should start in CLOSED state"
    
    # Record failures
    for _ in range(failure_count):
        breaker.record_failure()
    
    # Property: Circuit should open when threshold is reached
    if failure_count >= failure_threshold:
        assert breaker.get_state() == CircuitState.OPEN, \
            f"Circuit should be OPEN after {failure_count} failures (threshold: {failure_threshold})"
        
        # Property: Requests should be blocked when circuit is open
        assert not breaker.is_allowed(), \
            "Requests should be blocked when circuit is OPEN"
    else:
        assert breaker.get_state() == CircuitState.CLOSED, \
            f"Circuit should remain CLOSED with {failure_count} failures (threshold: {failure_threshold})"


# ============================================================================
# Property 12.5: Task Duration Tracking Accuracy
# ============================================================================

@given(
    task_count=st.integers(min_value=1, max_value=20),
    sleep_duration=st.floats(min_value=0.01, max_value=0.1)
)
@settings(max_examples=50, deadline=None)
def test_property_task_duration_tracking_accuracy(task_count, sleep_duration):
    """
    Property: For any number of tasks, the performance monitor should
    accurately track task durations and maintain correct counts of
    active and completed tasks.
    
    Validates: Requirements 7.1
    """
    monitor = PerformanceMonitor()
    
    # Track multiple tasks
    task_ids = [f"task_{i}" for i in range(task_count)]
    
    for task_id in task_ids:
        monitor.track_task_start(task_id)
        time.sleep(sleep_duration)
        monitor.track_task_end(task_id, success=True)
    
    # Property: All tasks should be completed
    assert len(monitor.completed_tasks) == task_count, \
        f"Should have {task_count} completed tasks"
    
    # Property: No tasks should be active
    assert len(monitor.active_tasks) == 0, \
        "No tasks should be active after all complete"
    
    # Property: Each task duration should be approximately correct
    for task in monitor.completed_tasks:
        assert task['duration'] >= sleep_duration * 0.8, \
            f"Task duration {task['duration']} should be at least {sleep_duration * 0.8}"
        assert task['duration'] <= sleep_duration * 2.0, \
            f"Task duration {task['duration']} should not exceed {sleep_duration * 2.0}"


# ============================================================================
# Property 12.6: Analytics Cost Calculation Consistency
# ============================================================================

@given(
    duration=st.floats(min_value=1.0, max_value=100.0),
    cost_per_second=st.floats(min_value=0.01, max_value=1.0),
    cost_per_request=st.floats(min_value=0.0, max_value=5.0)
)
@settings(max_examples=100, deadline=None)
def test_property_analytics_cost_calculation_consistency(duration, cost_per_second, cost_per_request):
    """
    Property: For any usage duration and pricing configuration, the
    analytics engine should calculate costs consistently and accurately.
    
    Validates: Requirements 7.5
    """
    # Create pricing model
    pricing = ModelPricing(
        model_name="test_model",
        cost_per_second=cost_per_second,
        cost_per_request=cost_per_request,
        minimum_charge=0.0
    )
    
    # Calculate expected cost
    expected_cost = (duration * cost_per_second) + cost_per_request
    
    # Calculate actual cost
    actual_cost = pricing.calculate_cost(duration, 0.0, 0.0)
    
    # Property: Calculated cost should match expected cost
    assert abs(actual_cost - expected_cost) < 0.01, \
        f"Cost calculation mismatch: expected {expected_cost:.2f}, got {actual_cost:.2f}"
    
    # Property: Cost should never be negative
    assert actual_cost >= 0, \
        "Cost should never be negative"


# ============================================================================
# Property 12.7: Usage Statistics Aggregation Correctness
# ============================================================================

@given(
    task_count=st.integers(min_value=1, max_value=50),
    success_rate=st.floats(min_value=0.0, max_value=1.0)
)
@settings(max_examples=100, deadline=None)
def test_property_usage_statistics_aggregation_correctness(task_count, success_rate):
    """
    Property: For any number of usage records, the analytics engine
    should correctly aggregate statistics including success rate,
    total duration, and task counts.
    
    Validates: Requirements 7.5
    """
    engine = AnalyticsEngine(storage_path="./test_analytics_property")
    
    # Generate usage records
    start_date = datetime.now() - timedelta(hours=1)
    end_date = datetime.now()
    
    expected_successful = 0
    expected_failed = 0
    expected_duration = 0.0
    
    for i in range(task_count):
        success = (i / task_count) < success_rate
        duration = float(i + 1)
        
        if success:
            expected_successful += 1
        else:
            expected_failed += 1
        
        expected_duration += duration
        
        usage = UsageRecord(
            timestamp=start_date + timedelta(minutes=i),
            user_id=f"user_{i % 5}",
            task_id=f"task_{i}",
            model_name="test_model",
            operation_type="generation",
            duration_seconds=duration,
            success=success
        )
        engine.record_usage(usage)
    
    # Get statistics
    stats = engine.get_usage_statistics(start_date, end_date)
    
    # Property: Total tasks should match
    assert stats.total_tasks == task_count, \
        f"Total tasks mismatch: expected {task_count}, got {stats.total_tasks}"
    
    # Property: Successful tasks should match
    assert stats.successful_tasks == expected_successful, \
        f"Successful tasks mismatch: expected {expected_successful}, got {stats.successful_tasks}"
    
    # Property: Failed tasks should match
    assert stats.failed_tasks == expected_failed, \
        f"Failed tasks mismatch: expected {expected_failed}, got {stats.failed_tasks}"
    
    # Property: Total duration should match (with small tolerance)
    assert abs(stats.total_duration_seconds - expected_duration) < 0.1, \
        f"Duration mismatch: expected {expected_duration}, got {stats.total_duration_seconds}"


# ============================================================================
# Property 12.8: Protection Manager Integration
# ============================================================================

@given(
    rate_limit=st.integers(min_value=1, max_value=10),
    failure_threshold=st.integers(min_value=1, max_value=5)
)
@settings(max_examples=100, deadline=None)
def test_property_protection_manager_integration(rate_limit, failure_threshold):
    """
    Property: For any protection configuration, the protection manager
    should correctly coordinate rate limiting and circuit breaking,
    providing consistent protection decisions.
    
    Validates: Requirements 7.2
    """
    manager = ProtectionManager()
    
    # Create rate limiter
    rate_config = RateLimitConfig(
        max_requests=rate_limit,
        time_window_seconds=10.0,
        strategy=RateLimitStrategy.SLIDING_WINDOW
    )
    manager.create_rate_limiter("test_service", rate_config)
    
    # Create circuit breaker
    circuit_config = CircuitBreakerConfig(
        failure_threshold=failure_threshold,
        timeout_seconds=60.0
    )
    manager.create_circuit_breaker("test_service", circuit_config)
    
    # Property: Initial check should allow requests
    allowed, reason = manager.check_protection("test_service")
    assert allowed, "Initial protection check should allow requests"
    
    # Exhaust rate limit
    for _ in range(rate_limit):
        manager.get_rate_limiter("test_service").is_allowed()
    
    # Property: Should be blocked by rate limit
    allowed, reason = manager.check_protection("test_service")
    assert not allowed, "Should be blocked after exhausting rate limit"
    assert reason == "Rate limit exceeded", \
        f"Reason should be rate limit, got: {reason}"
    
    # Reset rate limiter and trigger circuit breaker
    manager.get_rate_limiter("test_service").reset()
    
    for _ in range(failure_threshold):
        manager.get_circuit_breaker("test_service").record_failure()
    
    # Property: Should be blocked by circuit breaker
    allowed, reason = manager.check_protection("test_service")
    assert not allowed, "Should be blocked by open circuit"
    assert "Circuit breaker" in reason, \
        f"Reason should mention circuit breaker, got: {reason}"


# ============================================================================
# Property 12.9: Metric History Management
# ============================================================================

@given(
    history_size=st.integers(min_value=5, max_value=50),
    metric_count=st.integers(min_value=1, max_value=100)
)
@settings(max_examples=100, deadline=None)
def test_property_metric_history_management(history_size, metric_count):
    """
    Property: For any history size configuration, the performance monitor
    should maintain at most history_size metrics, discarding oldest entries
    when the limit is exceeded.
    
    Validates: Requirements 7.1
    """
    monitor = PerformanceMonitor(history_size=history_size)
    
    # Store metrics
    for i in range(metric_count):
        monitor._store_metric(
            MetricType.CPU_USAGE,
            float(i),
            "%"
        )
    
    # Property: History should not exceed configured size
    actual_size = len(monitor.metrics_history[MetricType.CPU_USAGE])
    assert actual_size <= history_size, \
        f"History size {actual_size} should not exceed {history_size}"
    
    # Property: If we stored more than history_size, should have exactly history_size
    if metric_count > history_size:
        assert actual_size == history_size, \
            f"Should have exactly {history_size} metrics when storing {metric_count}"


def run_all_property_tests():
    """Run all property-based tests for system monitoring and alerting"""
    print("Running Property-Based Tests for Video Studio System Monitoring and Alerting")
    print("=" * 80)
    print()
    
    all_passed = True
    
    # Test 12.1: Performance Metrics Collection Consistency
    print("Test 12.1: Performance Metrics Collection Consistency")
    try:
        test_property_performance_metrics_collection_consistency()
        print("✓ PASSED\n")
    except Exception as e:
        print(f"✗ FAILED: {e}\n")
        all_passed = False
    
    # Test 12.2: Alert Triggering Consistency
    print("Test 12.2: Alert Triggering Consistency")
    try:
        test_property_alert_triggering_consistency()
        print("✓ PASSED\n")
    except Exception as e:
        print(f"✗ FAILED: {e}\n")
        all_passed = False
    
    # Test 12.3: Rate Limiting Consistency
    print("Test 12.3: Rate Limiting Consistency")
    try:
        test_property_rate_limiting_consistency()
        print("✓ PASSED\n")
    except Exception as e:
        print(f"✗ FAILED: {e}\n")
        all_passed = False
    
    # Test 12.4: Circuit Breaker State Transitions
    print("Test 12.4: Circuit Breaker State Transitions")
    try:
        test_property_circuit_breaker_state_transitions()
        print("✓ PASSED\n")
    except Exception as e:
        print(f"✗ FAILED: {e}\n")
        all_passed = False
    
    # Test 12.5: Task Duration Tracking Accuracy
    print("Test 12.5: Task Duration Tracking Accuracy")
    try:
        test_property_task_duration_tracking_accuracy()
        print("✓ PASSED\n")
    except Exception as e:
        print(f"✗ FAILED: {e}\n")
        all_passed = False
    
    # Test 12.6: Analytics Cost Calculation Consistency
    print("Test 12.6: Analytics Cost Calculation Consistency")
    try:
        test_property_analytics_cost_calculation_consistency()
        print("✓ PASSED\n")
    except Exception as e:
        print(f"✗ FAILED: {e}\n")
        all_passed = False
    
    # Test 12.7: Usage Statistics Aggregation Correctness
    print("Test 12.7: Usage Statistics Aggregation Correctness")
    try:
        test_property_usage_statistics_aggregation_correctness()
        print("✓ PASSED\n")
    except Exception as e:
        print(f"✗ FAILED: {e}\n")
        all_passed = False
    
    # Test 12.8: Protection Manager Integration
    print("Test 12.8: Protection Manager Integration")
    try:
        test_property_protection_manager_integration()
        print("✓ PASSED\n")
    except Exception as e:
        print(f"✗ FAILED: {e}\n")
        all_passed = False
    
    # Test 12.9: Metric History Management
    print("Test 12.9: Metric History Management")
    try:
        test_property_metric_history_management()
        print("✓ PASSED\n")
    except Exception as e:
        print(f"✗ FAILED: {e}\n")
        all_passed = False
    
    print("=" * 80)
    if all_passed:
        print("✓ ALL PROPERTY TESTS PASSED")
    else:
        print("✗ SOME PROPERTY TESTS FAILED")
    print("=" * 80)
    
    return all_passed


if __name__ == "__main__":
    import sys
    success = run_all_property_tests()
    sys.exit(0 if success else 1)
