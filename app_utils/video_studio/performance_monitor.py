"""
Performance Monitoring and Metrics Collection for Video Studio

This module provides comprehensive system performance monitoring including CPU, memory,
network usage tracking, and real-time metrics collection for the video generation workflow.

Validates: Requirements 7.1
"""

import psutil
import time
import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
from collections import deque
import threading


class MetricType(Enum):
    """Types of metrics that can be collected"""
    CPU_USAGE = "cpu_usage"
    MEMORY_USAGE = "memory_usage"
    DISK_USAGE = "disk_usage"
    NETWORK_IO = "network_io"
    TASK_DURATION = "task_duration"
    API_LATENCY = "api_latency"
    ERROR_RATE = "error_rate"
    THROUGHPUT = "throughput"


@dataclass
class MetricData:
    """Single metric data point"""
    metric_type: MetricType
    value: float
    timestamp: datetime
    unit: str
    tags: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metric to dictionary"""
        return {
            "metric_type": self.metric_type.value,
            "value": self.value,
            "timestamp": self.timestamp.isoformat(),
            "unit": self.unit,
            "tags": self.tags
        }


@dataclass
class SystemMetrics:
    """Snapshot of system performance metrics"""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    memory_available_mb: float
    disk_usage_percent: float
    disk_free_gb: float
    network_bytes_sent: int
    network_bytes_recv: int
    active_tasks: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert system metrics to dictionary"""
        return {
            "timestamp": self.timestamp.isoformat(),
            "cpu_percent": self.cpu_percent,
            "memory_percent": self.memory_percent,
            "memory_used_mb": self.memory_used_mb,
            "memory_available_mb": self.memory_available_mb,
            "disk_usage_percent": self.disk_usage_percent,
            "disk_free_gb": self.disk_free_gb,
            "network_bytes_sent": self.network_bytes_sent,
            "network_bytes_recv": self.network_bytes_recv,
            "active_tasks": self.active_tasks
        }


@dataclass
class PerformanceThresholds:
    """Thresholds for performance alerts"""
    cpu_warning: float = 70.0  # Percentage
    cpu_critical: float = 90.0
    memory_warning: float = 75.0
    memory_critical: float = 90.0
    disk_warning: float = 80.0
    disk_critical: float = 95.0
    task_duration_warning: float = 300.0  # Seconds
    task_duration_critical: float = 600.0
    error_rate_warning: float = 0.05  # 5%
    error_rate_critical: float = 0.15  # 15%


class PerformanceMonitor:
    """
    Comprehensive performance monitoring system for Video Studio.
    
    Collects and tracks system metrics including CPU, memory, disk, and network usage.
    Provides real-time monitoring and historical data analysis.
    """
    
    def __init__(self, collection_interval: float = 5.0, history_size: int = 1000):
        """
        Initialize performance monitor.
        
        Args:
            collection_interval: Seconds between metric collections
            history_size: Number of historical data points to retain
        """
        self.collection_interval = collection_interval
        self.history_size = history_size
        
        # Metric storage
        self.metrics_history: Dict[MetricType, deque] = {
            metric_type: deque(maxlen=history_size)
            for metric_type in MetricType
        }
        self.system_metrics_history: deque = deque(maxlen=history_size)
        
        # Performance thresholds
        self.thresholds = PerformanceThresholds()
        
        # Alert callbacks
        self.alert_callbacks: List[Callable] = []
        
        # Monitoring state
        self._monitoring = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._last_network_io: Optional[Dict[str, int]] = None
        
        # Task tracking
        self.active_tasks: Dict[str, datetime] = {}
        self.completed_tasks: List[Dict[str, Any]] = []
        
        # API call tracking
        self.api_calls: Dict[str, List[float]] = {}  # model_name -> [latencies]
        
        # Error tracking
        self.error_count = 0
        self.total_operations = 0
    
    def start_monitoring(self) -> bool:
        """Start continuous performance monitoring"""
        if self._monitoring:
            return False
        
        self._monitoring = True
        self._monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self._monitor_thread.start()
        return True
    
    def stop_monitoring(self) -> bool:
        """Stop performance monitoring"""
        if not self._monitoring:
            return False
        
        self._monitoring = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5.0)
        return True
    
    def _monitoring_loop(self):
        """Main monitoring loop running in background thread"""
        while self._monitoring:
            try:
                metrics = self.collect_system_metrics()
                self.system_metrics_history.append(metrics)
                
                # Check thresholds and trigger alerts
                self._check_thresholds(metrics)
                
                time.sleep(self.collection_interval)
            except Exception:
                # Continue monitoring even if collection fails
                time.sleep(self.collection_interval)
    
    def collect_system_metrics(self) -> SystemMetrics:
        """Collect current system performance metrics"""
        # CPU metrics
        cpu_percent = psutil.cpu_percent(interval=0.1)
        
        # Memory metrics
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        memory_used_mb = memory.used / (1024 * 1024)
        memory_available_mb = memory.available / (1024 * 1024)
        
        # Disk metrics
        disk = psutil.disk_usage('/')
        disk_usage_percent = disk.percent
        disk_free_gb = disk.free / (1024 * 1024 * 1024)
        
        # Network metrics
        network = psutil.net_io_counters()
        network_bytes_sent = network.bytes_sent
        network_bytes_recv = network.bytes_recv
        
        metrics = SystemMetrics(
            timestamp=datetime.now(),
            cpu_percent=cpu_percent,
            memory_percent=memory_percent,
            memory_used_mb=memory_used_mb,
            memory_available_mb=memory_available_mb,
            disk_usage_percent=disk_usage_percent,
            disk_free_gb=disk_free_gb,
            network_bytes_sent=network_bytes_sent,
            network_bytes_recv=network_bytes_recv,
            active_tasks=len(self.active_tasks)
        )
        
        # Store individual metrics
        self._store_metric(MetricType.CPU_USAGE, cpu_percent, "%")
        self._store_metric(MetricType.MEMORY_USAGE, memory_percent, "%")
        self._store_metric(MetricType.DISK_USAGE, disk_usage_percent, "%")
        
        # Calculate network throughput if we have previous data
        if self._last_network_io:
            bytes_sent_delta = network_bytes_sent - self._last_network_io['sent']
            bytes_recv_delta = network_bytes_recv - self._last_network_io['recv']
            
            # Convert to KB/s
            throughput_sent = (bytes_sent_delta / self.collection_interval) / 1024
            throughput_recv = (bytes_recv_delta / self.collection_interval) / 1024
            
            self._store_metric(MetricType.NETWORK_IO, throughput_sent, "KB/s", {"direction": "sent"})
            self._store_metric(MetricType.NETWORK_IO, throughput_recv, "KB/s", {"direction": "recv"})
        
        self._last_network_io = {'sent': network_bytes_sent, 'recv': network_bytes_recv}
        
        return metrics
    
    def _store_metric(self, metric_type: MetricType, value: float, unit: str, tags: Optional[Dict[str, str]] = None):
        """Store a metric data point"""
        metric = MetricData(
            metric_type=metric_type,
            value=value,
            timestamp=datetime.now(),
            unit=unit,
            tags=tags or {}
        )
        self.metrics_history[metric_type].append(metric)
    
    def _check_thresholds(self, metrics: SystemMetrics):
        """Check if metrics exceed thresholds and trigger alerts"""
        alerts = []
        
        # CPU alerts
        if metrics.cpu_percent >= self.thresholds.cpu_critical:
            alerts.append(("critical", f"CPU usage critical: {metrics.cpu_percent:.1f}%"))
        elif metrics.cpu_percent >= self.thresholds.cpu_warning:
            alerts.append(("warning", f"CPU usage high: {metrics.cpu_percent:.1f}%"))
        
        # Memory alerts
        if metrics.memory_percent >= self.thresholds.memory_critical:
            alerts.append(("critical", f"Memory usage critical: {metrics.memory_percent:.1f}%"))
        elif metrics.memory_percent >= self.thresholds.memory_warning:
            alerts.append(("warning", f"Memory usage high: {metrics.memory_percent:.1f}%"))
        
        # Disk alerts
        if metrics.disk_usage_percent >= self.thresholds.disk_critical:
            alerts.append(("critical", f"Disk usage critical: {metrics.disk_usage_percent:.1f}%"))
        elif metrics.disk_usage_percent >= self.thresholds.disk_warning:
            alerts.append(("warning", f"Disk usage high: {metrics.disk_usage_percent:.1f}%"))
        
        # Trigger alert callbacks
        for severity, message in alerts:
            self._trigger_alerts(severity, message, metrics)
    
    def _trigger_alerts(self, severity: str, message: str, metrics: SystemMetrics):
        """Trigger registered alert callbacks"""
        for callback in self.alert_callbacks:
            try:
                callback(severity, message, metrics)
            except Exception:
                pass  # Don't let callback errors stop monitoring
    
    def register_alert_callback(self, callback: Callable):
        """Register a callback function for performance alerts"""
        if callback not in self.alert_callbacks:
            self.alert_callbacks.append(callback)
    
    def unregister_alert_callback(self, callback: Callable):
        """Unregister an alert callback"""
        if callback in self.alert_callbacks:
            self.alert_callbacks.remove(callback)
    
    def track_task_start(self, task_id: str):
        """Track the start of a task"""
        self.active_tasks[task_id] = datetime.now()
    
    def track_task_end(self, task_id: str, success: bool = True):
        """Track the end of a task"""
        if task_id not in self.active_tasks:
            return
        
        start_time = self.active_tasks.pop(task_id)
        duration = (datetime.now() - start_time).total_seconds()
        
        # Store task duration metric
        self._store_metric(
            MetricType.TASK_DURATION,
            duration,
            "seconds",
            {"task_id": task_id, "success": str(success)}
        )
        
        # Track completed task
        self.completed_tasks.append({
            "task_id": task_id,
            "duration": duration,
            "success": success,
            "completed_at": datetime.now()
        })
        
        # Update operation counts
        self.total_operations += 1
        if not success:
            self.error_count += 1
        
        # Check task duration thresholds
        if duration >= self.thresholds.task_duration_critical:
            self._trigger_alerts("critical", f"Task {task_id} took {duration:.1f}s (critical)", None)
        elif duration >= self.thresholds.task_duration_warning:
            self._trigger_alerts("warning", f"Task {task_id} took {duration:.1f}s (slow)", None)
    
    def track_api_call(self, model_name: str, latency: float):
        """Track API call latency"""
        if model_name not in self.api_calls:
            self.api_calls[model_name] = []
        
        self.api_calls[model_name].append(latency)
        
        # Store API latency metric
        self._store_metric(
            MetricType.API_LATENCY,
            latency,
            "seconds",
            {"model": model_name}
        )
    
    def get_current_metrics(self) -> Optional[SystemMetrics]:
        """Get the most recent system metrics"""
        if not self.system_metrics_history:
            return self.collect_system_metrics()
        return self.system_metrics_history[-1]
    
    def get_metrics_history(self, metric_type: MetricType, duration_minutes: Optional[int] = None) -> List[MetricData]:
        """
        Get historical metrics for a specific type.
        
        Args:
            metric_type: Type of metric to retrieve
            duration_minutes: Optional time window in minutes (None = all history)
        
        Returns:
            List of metric data points
        """
        metrics = list(self.metrics_history[metric_type])
        
        if duration_minutes is not None:
            cutoff_time = datetime.now() - timedelta(minutes=duration_minutes)
            metrics = [m for m in metrics if m.timestamp >= cutoff_time]
        
        return metrics
    
    def get_average_metric(self, metric_type: MetricType, duration_minutes: Optional[int] = None) -> Optional[float]:
        """Calculate average value for a metric type"""
        metrics = self.get_metrics_history(metric_type, duration_minutes)
        
        if not metrics:
            return None
        
        return sum(m.value for m in metrics) / len(metrics)
    
    def get_peak_metric(self, metric_type: MetricType, duration_minutes: Optional[int] = None) -> Optional[float]:
        """Get peak value for a metric type"""
        metrics = self.get_metrics_history(metric_type, duration_minutes)
        
        if not metrics:
            return None
        
        return max(m.value for m in metrics)
    
    def get_error_rate(self) -> float:
        """Calculate current error rate"""
        if self.total_operations == 0:
            return 0.0
        
        return self.error_count / self.total_operations
    
    def get_throughput(self, duration_minutes: int = 60) -> float:
        """
        Calculate task throughput (tasks per minute).
        
        Args:
            duration_minutes: Time window for calculation
        
        Returns:
            Tasks per minute
        """
        cutoff_time = datetime.now() - timedelta(minutes=duration_minutes)
        recent_tasks = [
            task for task in self.completed_tasks
            if task['completed_at'] >= cutoff_time
        ]
        
        if not recent_tasks:
            return 0.0
        
        return len(recent_tasks) / duration_minutes
    
    def get_average_api_latency(self, model_name: Optional[str] = None) -> Optional[float]:
        """
        Get average API call latency.
        
        Args:
            model_name: Specific model name (None = all models)
        
        Returns:
            Average latency in seconds
        """
        if model_name:
            latencies = self.api_calls.get(model_name, [])
        else:
            latencies = [lat for lats in self.api_calls.values() for lat in lats]
        
        if not latencies:
            return None
        
        return sum(latencies) / len(latencies)
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary"""
        current = self.get_current_metrics()
        
        return {
            "current_metrics": current.to_dict() if current else None,
            "averages": {
                "cpu_percent": self.get_average_metric(MetricType.CPU_USAGE, 60),
                "memory_percent": self.get_average_metric(MetricType.MEMORY_USAGE, 60),
                "disk_percent": self.get_average_metric(MetricType.DISK_USAGE, 60),
            },
            "peaks": {
                "cpu_percent": self.get_peak_metric(MetricType.CPU_USAGE, 60),
                "memory_percent": self.get_peak_metric(MetricType.MEMORY_USAGE, 60),
            },
            "task_metrics": {
                "active_tasks": len(self.active_tasks),
                "completed_tasks": len(self.completed_tasks),
                "error_rate": self.get_error_rate(),
                "throughput_per_minute": self.get_throughput(60),
            },
            "api_metrics": {
                "average_latency": self.get_average_api_latency(),
                "models_tracked": list(self.api_calls.keys()),
            }
        }
    
    def reset_metrics(self):
        """Reset all collected metrics"""
        for metric_type in MetricType:
            self.metrics_history[metric_type].clear()
        
        self.system_metrics_history.clear()
        self.active_tasks.clear()
        self.completed_tasks.clear()
        self.api_calls.clear()
        self.error_count = 0
        self.total_operations = 0
        self._last_network_io = None


# Global performance monitor instance
performance_monitor = PerformanceMonitor()


def get_performance_monitor() -> PerformanceMonitor:
    """Get the global performance monitor instance"""
    return performance_monitor


def start_monitoring() -> bool:
    """Start global performance monitoring"""
    return performance_monitor.start_monitoring()


def stop_monitoring() -> bool:
    """Stop global performance monitoring"""
    return performance_monitor.stop_monitoring()


def get_current_metrics() -> Optional[SystemMetrics]:
    """Get current system metrics"""
    return performance_monitor.get_current_metrics()


def get_performance_summary() -> Dict[str, Any]:
    """Get performance summary"""
    return performance_monitor.get_performance_summary()
