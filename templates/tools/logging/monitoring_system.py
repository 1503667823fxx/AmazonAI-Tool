#!/usr/bin/env python3
"""
监控和告警系统 - 建立监控和告警系统
Monitoring and Alerting System - Establish monitoring and alerting system
"""

import time
import threading
import json
from typing import Dict, Any, List, Callable, Optional
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
import psutil

class AlertLevel(Enum):
    """告警级别"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class MetricType(Enum):
    """指标类型"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"

@dataclass
class Alert:
    """告警信息"""
    alert_id: str
    level: AlertLevel
    title: str
    message: str
    timestamp: datetime
    metric_name: str
    current_value: float
    threshold_value: float
    context: Dict[str, Any]
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        data['level'] = self.level.value
        data['timestamp'] = self.timestamp.isoformat()
        if self.resolved_at:
            data['resolved_at'] = self.resolved_at.isoformat()
        return data

@dataclass
class Metric:
    """监控指标"""
    name: str
    type: MetricType
    value: float
    timestamp: datetime
    labels: Dict[str, str]
    description: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        data['type'] = self.type.value
        data['timestamp'] = self.timestamp.isoformat()
        return data

@dataclass
class Threshold:
    """阈值配置"""
    metric_name: str
    warning_threshold: Optional[float] = None
    error_threshold: Optional[float] = None
    critical_threshold: Optional[float] = None
    comparison: str = "greater"  # greater, less, equal
    enabled: bool = True

class MetricCollector:
    """指标收集器"""
    
    def __init__(self):
        self.metrics = {}
        self._lock = threading.RLock()
    
    def record_counter(self, name: str, value: float = 1, labels: Dict[str, str] = None):
        """记录计数器指标"""
        with self._lock:
            key = f"{name}:{json.dumps(labels or {}, sort_keys=True)}"
            if key in self.metrics:
                self.metrics[key].value += value
                self.metrics[key].timestamp = datetime.now()
            else:
                self.metrics[key] = Metric(
                    name=name,
                    type=MetricType.COUNTER,
                    value=value,
                    timestamp=datetime.now(),
                    labels=labels or {}
                )
    
    def record_gauge(self, name: str, value: float, labels: Dict[str, str] = None):
        """记录仪表盘指标"""
        with self._lock:
            key = f"{name}:{json.dumps(labels or {}, sort_keys=True)}"
            self.metrics[key] = Metric(
                name=name,
                type=MetricType.GAUGE,
                value=value,
                timestamp=datetime.now(),
                labels=labels or {}
            )
    
    def record_timer(self, name: str, duration_ms: float, labels: Dict[str, str] = None):
        """记录计时器指标"""
        with self._lock:
            key = f"{name}:{json.dumps(labels or {}, sort_keys=True)}"
            self.metrics[key] = Metric(
                name=name,
                type=MetricType.TIMER,
                value=duration_ms,
                timestamp=datetime.now(),
                labels=labels or {}
            )
    
    def get_metrics(self) -> List[Metric]:
        """获取所有指标"""
        with self._lock:
            return list(self.metrics.values())
    
    def get_metric(self, name: str, labels: Dict[str, str] = None) -> Optional[Metric]:
        """获取特定指标"""
        with self._lock:
            key = f"{name}:{json.dumps(labels or {}, sort_keys=True)}"
            return self.metrics.get(key)
    
    def clear_metrics(self):
        """清空指标"""
        with self._lock:
            self.metrics.clear()

class SystemMonitor:
    """系统监控器"""
    
    def __init__(self, collector: MetricCollector):
        self.collector = collector
        self._monitoring = False
        self._monitor_thread = None
        self._lock = threading.Lock()
    
    def start_monitoring(self, interval_seconds: int = 30):
        """开始监控"""
        with self._lock:
            if self._monitoring:
                return
            
            self._monitoring = True
            self._monitor_thread = threading.Thread(
                target=self._monitor_loop,
                args=(interval_seconds,),
                daemon=True
            )
            self._monitor_thread.start()
    
    def stop_monitoring(self):
        """停止监控"""
        with self._lock:
            self._monitoring = False
            if self._monitor_thread:
                self._monitor_thread.join(timeout=5)
    
    def _monitor_loop(self, interval_seconds: int):
        """监控循环"""
        while self._monitoring:
            try:
                self._collect_system_metrics()
                time.sleep(interval_seconds)
            except Exception:
                # 监控出错时继续运行
                time.sleep(interval_seconds)
    
    def _collect_system_metrics(self):
        """收集系统指标"""
        # CPU使用率
        cpu_percent = psutil.cpu_percent(interval=1)
        self.collector.record_gauge("system_cpu_usage_percent", cpu_percent)
        
        # 内存使用情况
        memory = psutil.virtual_memory()
        self.collector.record_gauge("system_memory_usage_percent", memory.percent)
        self.collector.record_gauge("system_memory_available_mb", memory.available / 1024 / 1024)
        
        # 磁盘使用情况
        disk = psutil.disk_usage('/')
        disk_percent = (disk.used / disk.total) * 100
        self.collector.record_gauge("system_disk_usage_percent", disk_percent)
        self.collector.record_gauge("system_disk_free_gb", disk.free / 1024 / 1024 / 1024)
        
        # 进程信息
        process = psutil.Process()
        process_memory = process.memory_info().rss / 1024 / 1024  # MB
        self.collector.record_gauge("process_memory_usage_mb", process_memory)
        
        # 文件描述符数量（Unix系统）
        try:
            fd_count = process.num_fds()
            self.collector.record_gauge("process_file_descriptors", fd_count)
        except AttributeError:
            # Windows系统不支持
            pass

class AlertManager:
    """告警管理器"""
    
    def __init__(self, log_dir: Path = None):
        self.log_dir = log_dir or Path('logs/alerts')
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        self.thresholds = {}
        self.alerts = []
        self.alert_handlers = []
        self._lock = threading.RLock()
    
    def add_threshold(self, threshold: Threshold):
        """添加阈值配置"""
        with self._lock:
            self.thresholds[threshold.metric_name] = threshold
    
    def add_alert_handler(self, handler: Callable[[Alert], None]):
        """添加告警处理器"""
        with self._lock:
            self.alert_handlers.append(handler)
    
    def check_thresholds(self, metrics: List[Metric]):
        """检查阈值"""
        for metric in metrics:
            threshold = self.thresholds.get(metric.name)
            if not threshold or not threshold.enabled:
                continue
            
            alert_level = self._evaluate_threshold(metric.value, threshold)
            if alert_level:
                self._create_alert(metric, threshold, alert_level)
    
    def _evaluate_threshold(self, value: float, threshold: Threshold) -> Optional[AlertLevel]:
        """评估阈值"""
        if threshold.comparison == "greater":
            if threshold.critical_threshold and value > threshold.critical_threshold:
                return AlertLevel.CRITICAL
            elif threshold.error_threshold and value > threshold.error_threshold:
                return AlertLevel.ERROR
            elif threshold.warning_threshold and value > threshold.warning_threshold:
                return AlertLevel.WARNING
        
        elif threshold.comparison == "less":
            if threshold.critical_threshold and value < threshold.critical_threshold:
                return AlertLevel.CRITICAL
            elif threshold.error_threshold and value < threshold.error_threshold:
                return AlertLevel.ERROR
            elif threshold.warning_threshold and value < threshold.warning_threshold:
                return AlertLevel.WARNING
        
        return None
    
    def _create_alert(self, metric: Metric, threshold: Threshold, level: AlertLevel):
        """创建告警"""
        # 检查是否已存在相同的未解决告警
        existing_alert = self._find_existing_alert(metric.name, level)
        if existing_alert:
            return
        
        alert_id = f"ALT_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{id(metric)}"
        
        # 确定阈值值
        threshold_value = None
        if level == AlertLevel.CRITICAL:
            threshold_value = threshold.critical_threshold
        elif level == AlertLevel.ERROR:
            threshold_value = threshold.error_threshold
        elif level == AlertLevel.WARNING:
            threshold_value = threshold.warning_threshold
        
        alert = Alert(
            alert_id=alert_id,
            level=level,
            title=f"{metric.name} {level.value.upper()} Alert",
            message=f"Metric {metric.name} value {metric.value} exceeds {level.value} threshold {threshold_value}",
            timestamp=datetime.now(),
            metric_name=metric.name,
            current_value=metric.value,
            threshold_value=threshold_value or 0,
            context={
                'metric_labels': metric.labels,
                'threshold_comparison': threshold.comparison
            }
        )
        
        with self._lock:
            self.alerts.append(alert)
            
            # 只保留最近1000条告警
            if len(self.alerts) > 1000:
                self.alerts = self.alerts[-1000:]
        
        # 执行告警处理器
        self._execute_alert_handlers(alert)
        
        # 记录告警日志
        self._log_alert(alert)
    
    def _find_existing_alert(self, metric_name: str, level: AlertLevel) -> Optional[Alert]:
        """查找现有告警"""
        with self._lock:
            for alert in reversed(self.alerts):
                if (alert.metric_name == metric_name and 
                    alert.level == level and 
                    not alert.resolved):
                    return alert
        return None
    
    def _execute_alert_handlers(self, alert: Alert):
        """执行告警处理器"""
        for handler in self.alert_handlers:
            try:
                handler(alert)
            except Exception:
                # 告警处理器出错不应影响系统运行
                pass
    
    def _log_alert(self, alert: Alert):
        """记录告警日志"""
        alert_file = self.log_dir / f"alerts_{datetime.now().strftime('%Y%m%d')}.json"
        
        try:
            # 读取现有告警
            if alert_file.exists():
                with open(alert_file, 'r', encoding='utf-8') as f:
                    alerts_data = json.load(f)
            else:
                alerts_data = {'alerts': []}
            
            # 添加新告警
            alerts_data['alerts'].append(alert.to_dict())
            
            # 写回文件
            with open(alert_file, 'w', encoding='utf-8') as f:
                json.dump(alerts_data, f, ensure_ascii=False, indent=2)
                
        except Exception:
            pass
    
    def resolve_alert(self, alert_id: str) -> bool:
        """解决告警"""
        with self._lock:
            for alert in self.alerts:
                if alert.alert_id == alert_id and not alert.resolved:
                    alert.resolved = True
                    alert.resolved_at = datetime.now()
                    return True
        return False
    
    def get_active_alerts(self) -> List[Alert]:
        """获取活跃告警"""
        with self._lock:
            return [alert for alert in self.alerts if not alert.resolved]
    
    def get_alert_statistics(self) -> Dict[str, Any]:
        """获取告警统计"""
        with self._lock:
            if not self.alerts:
                return {'message': '暂无告警记录'}
            
            # 按级别统计
            level_stats = {}
            resolved_count = 0
            
            for alert in self.alerts:
                level = alert.level.value
                if level not in level_stats:
                    level_stats[level] = 0
                level_stats[level] += 1
                
                if alert.resolved:
                    resolved_count += 1
            
            return {
                'total_alerts': len(self.alerts),
                'active_alerts': len(self.alerts) - resolved_count,
                'resolved_alerts': resolved_count,
                'level_distribution': level_stats,
                'resolution_rate': resolved_count / len(self.alerts) * 100
            }

class MonitoringSystem:
    """监控系统主类"""
    
    def __init__(self, log_dir: Path = None):
        self.log_dir = log_dir or Path('logs/monitoring')
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        self.collector = MetricCollector()
        self.system_monitor = SystemMonitor(self.collector)
        self.alert_manager = AlertManager(self.log_dir / 'alerts')
        
        self._setup_default_thresholds()
        self._setup_default_alert_handlers()
    
    def _setup_default_thresholds(self):
        """设置默认阈值"""
        # CPU使用率阈值
        self.alert_manager.add_threshold(Threshold(
            metric_name="system_cpu_usage_percent",
            warning_threshold=70.0,
            error_threshold=85.0,
            critical_threshold=95.0,
            comparison="greater"
        ))
        
        # 内存使用率阈值
        self.alert_manager.add_threshold(Threshold(
            metric_name="system_memory_usage_percent",
            warning_threshold=80.0,
            error_threshold=90.0,
            critical_threshold=95.0,
            comparison="greater"
        ))
        
        # 磁盘使用率阈值
        self.alert_manager.add_threshold(Threshold(
            metric_name="system_disk_usage_percent",
            warning_threshold=80.0,
            error_threshold=90.0,
            critical_threshold=95.0,
            comparison="greater"
        ))
        
        # 进程内存使用阈值
        self.alert_manager.add_threshold(Threshold(
            metric_name="process_memory_usage_mb",
            warning_threshold=500.0,
            error_threshold=1000.0,
            critical_threshold=2000.0,
            comparison="greater"
        ))
    
    def _setup_default_alert_handlers(self):
        """设置默认告警处理器"""
        
        def console_alert_handler(alert: Alert):
            """控制台告警处理器"""
            level_symbols = {
                AlertLevel.INFO: "ℹ️",
                AlertLevel.WARNING: "⚠️",
                AlertLevel.ERROR: "❌",
                AlertLevel.CRITICAL: "🚨"
            }
            
            symbol = level_symbols.get(alert.level, "❓")
            print(f"{symbol} [{alert.level.value.upper()}] {alert.title}")
            print(f"   {alert.message}")
            print(f"   Time: {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        
        self.alert_manager.add_alert_handler(console_alert_handler)
    
    def start_monitoring(self, interval_seconds: int = 30):
        """开始监控"""
        self.system_monitor.start_monitoring(interval_seconds)
        
        # 启动告警检查线程
        def alert_check_loop():
            while True:
                try:
                    metrics = self.collector.get_metrics()
                    self.alert_manager.check_thresholds(metrics)
                    time.sleep(60)  # 每分钟检查一次告警
                except Exception:
                    time.sleep(60)
        
        alert_thread = threading.Thread(target=alert_check_loop, daemon=True)
        alert_thread.start()
    
    def stop_monitoring(self):
        """停止监控"""
        self.system_monitor.stop_monitoring()
    
    def record_business_metric(self, name: str, value: float, labels: Dict[str, str] = None):
        """记录业务指标"""
        self.collector.record_gauge(name, value, labels)
    
    def record_operation_time(self, operation: str, duration_ms: float, labels: Dict[str, str] = None):
        """记录操作时间"""
        self.collector.record_timer(f"operation_duration_{operation}", duration_ms, labels)
    
    def get_monitoring_dashboard(self) -> Dict[str, Any]:
        """获取监控仪表板数据"""
        metrics = self.collector.get_metrics()
        active_alerts = self.alert_manager.get_active_alerts()
        
        # 系统指标
        system_metrics = {}
        for metric in metrics:
            if metric.name.startswith('system_') or metric.name.startswith('process_'):
                system_metrics[metric.name] = {
                    'value': metric.value,
                    'timestamp': metric.timestamp.isoformat(),
                    'type': metric.type.value
                }
        
        # 业务指标
        business_metrics = {}
        for metric in metrics:
            if not metric.name.startswith('system_') and not metric.name.startswith('process_'):
                business_metrics[metric.name] = {
                    'value': metric.value,
                    'timestamp': metric.timestamp.isoformat(),
                    'type': metric.type.value,
                    'labels': metric.labels
                }
        
        return {
            'system_metrics': system_metrics,
            'business_metrics': business_metrics,
            'active_alerts': [alert.to_dict() for alert in active_alerts],
            'alert_statistics': self.alert_manager.get_alert_statistics(),
            'last_updated': datetime.now().isoformat()
        }

# 全局监控系统实例
_monitoring_system = None

def get_monitoring_system() -> MonitoringSystem:
    """获取全局监控系统实例"""
    global _monitoring_system
    if _monitoring_system is None:
        _monitoring_system = MonitoringSystem()
    return _monitoring_system

def monitor_decorator(operation_name: str):
    """监控装饰器"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                
                # 记录成功操作
                duration_ms = (time.time() - start_time) * 1000
                get_monitoring_system().record_operation_time(operation_name, duration_ms)
                get_monitoring_system().collector.record_counter(f"operation_success_{operation_name}")
                
                return result
                
            except Exception as e:
                # 记录失败操作
                duration_ms = (time.time() - start_time) * 1000
                get_monitoring_system().record_operation_time(f"{operation_name}_failed", duration_ms)
                get_monitoring_system().collector.record_counter(f"operation_failure_{operation_name}")
                
                raise e
        
        return wrapper
    return decorator

if __name__ == "__main__":
    # 测试监控系统
    print("=== 监控系统测试 ===")
    
    monitoring = get_monitoring_system()
    
    # 启动监控
    print("1. 启动系统监控...")
    monitoring.start_monitoring(interval_seconds=5)
    
    # 等待收集一些指标
    print("2. 等待指标收集...")
    time.sleep(10)
    
    # 记录一些业务指标
    print("3. 记录业务指标...")
    monitoring.record_business_metric("template_count", 150)
    monitoring.record_business_metric("active_users", 25)
    monitoring.record_operation_time("template_creation", 1250.5)
    monitoring.record_operation_time("template_search", 85.2)
    
    # 获取监控仪表板
    print("4. 获取监控仪表板...")
    dashboard = monitoring.get_monitoring_dashboard()
    
    print(f"   系统指标数量: {len(dashboard['system_metrics'])}")
    print(f"   业务指标数量: {len(dashboard['business_metrics'])}")
    print(f"   活跃告警数量: {len(dashboard['active_alerts'])}")
    
    # 显示一些关键指标
    system_metrics = dashboard['system_metrics']
    if 'system_cpu_usage_percent' in system_metrics:
        cpu_usage = system_metrics['system_cpu_usage_percent']['value']
        print(f"   CPU使用率: {cpu_usage:.1f}%")
    
    if 'system_memory_usage_percent' in system_metrics:
        memory_usage = system_metrics['system_memory_usage_percent']['value']
        print(f"   内存使用率: {memory_usage:.1f}%")
    
    # 显示告警统计
    alert_stats = dashboard['alert_statistics']
    if 'total_alerts' in alert_stats:
        print(f"   总告警数: {alert_stats['total_alerts']}")
        print(f"   活跃告警数: {alert_stats['active_alerts']}")
    
    # 停止监控
    print("5. 停止监控...")
    monitoring.stop_monitoring()
    
    print("\n✓ 监控系统测试完成")