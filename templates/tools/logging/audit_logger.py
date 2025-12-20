#!/usr/bin/env python3
"""
审计日志系统 - 创建详细的操作日志和审计跟踪
Audit Logging System - Create detailed operation logs and audit tracking
"""

import json
import logging
import threading
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
import hashlib
import uuid

class AuditEventType(Enum):
    """审计事件类型"""
    TEMPLATE_CREATE = "template_create"
    TEMPLATE_UPDATE = "template_update"
    TEMPLATE_DELETE = "template_delete"
    TEMPLATE_SEARCH = "template_search"
    CONFIG_CHANGE = "config_change"
    CATEGORY_CHANGE = "category_change"
    FILE_OPERATION = "file_operation"
    VALIDATION = "validation"
    SYSTEM_START = "system_start"
    SYSTEM_STOP = "system_stop"
    USER_ACTION = "user_action"
    PERFORMANCE_METRIC = "performance_metric"
    ERROR_OCCURRED = "error_occurred"

@dataclass
class AuditEvent:
    """审计事件"""
    event_id: str
    event_type: AuditEventType
    timestamp: datetime
    user_id: Optional[str]
    session_id: Optional[str]
    operation: str
    resource: Optional[str]
    details: Dict[str, Any]
    result: str  # success, failure, partial
    duration_ms: Optional[float] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        data['event_type'] = self.event_type.value
        data['timestamp'] = self.timestamp.isoformat()
        return data

class AuditLogger:
    """审计日志记录器"""
    
    def __init__(self, log_dir: Path = None, max_log_size_mb: int = 100):
        self.log_dir = log_dir or Path('logs/audit')
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        self.max_log_size_bytes = max_log_size_mb * 1024 * 1024
        self.current_session_id = str(uuid.uuid4())
        
        self.audit_events = []
        self._lock = threading.RLock()
        
        # 设置日志记录器
        self.logger = self._setup_logger()
        
        # 记录系统启动事件
        self.log_system_event("system_start", {"session_id": self.current_session_id})
    
    def _setup_logger(self) -> logging.Logger:
        """设置日志记录器"""
        logger = logging.getLogger('template_library_audit')
        logger.setLevel(logging.INFO)
        
        # 清除现有处理器
        logger.handlers.clear()
        
        # 审计日志文件处理器
        audit_file = self.log_dir / f"audit_{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = logging.FileHandler(audit_file, encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        
        # 格式化器 - 使用JSON格式便于解析
        formatter = logging.Formatter('%(message)s')
        file_handler.setFormatter(formatter)
        
        logger.addHandler(file_handler)
        
        return logger
    
    def _generate_event_id(self) -> str:
        """生成事件ID"""
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        random_part = str(uuid.uuid4())[:8]
        return f"AUD_{timestamp}_{random_part}"
    
    def log_event(self, event_type: AuditEventType, operation: str, 
                  resource: str = None, details: Dict[str, Any] = None,
                  result: str = "success", duration_ms: float = None,
                  user_id: str = None, ip_address: str = None) -> str:
        """记录审计事件"""
        
        event = AuditEvent(
            event_id=self._generate_event_id(),
            event_type=event_type,
            timestamp=datetime.now(),
            user_id=user_id or "system",
            session_id=self.current_session_id,
            operation=operation,
            resource=resource,
            details=details or {},
            result=result,
            duration_ms=duration_ms,
            ip_address=ip_address
        )
        
        with self._lock:
            # 添加到内存缓存
            self.audit_events.append(event)
            
            # 只保留最近10000条事件
            if len(self.audit_events) > 10000:
                self.audit_events = self.audit_events[-10000:]
            
            # 写入日志文件
            self.logger.info(json.dumps(event.to_dict(), ensure_ascii=False))
        
        return event.event_id
    
    def log_template_operation(self, operation: str, template_id: str, 
                             details: Dict[str, Any] = None, result: str = "success",
                             duration_ms: float = None, user_id: str = None) -> str:
        """记录模板操作"""
        
        event_type_map = {
            'create': AuditEventType.TEMPLATE_CREATE,
            'update': AuditEventType.TEMPLATE_UPDATE,
            'delete': AuditEventType.TEMPLATE_DELETE,
            'search': AuditEventType.TEMPLATE_SEARCH
        }
        
        event_type = event_type_map.get(operation, AuditEventType.USER_ACTION)
        
        return self.log_event(
            event_type=event_type,
            operation=f"template_{operation}",
            resource=f"template:{template_id}",
            details=details,
            result=result,
            duration_ms=duration_ms,
            user_id=user_id
        )
    
    def log_config_change(self, config_file: str, changes: Dict[str, Any],
                         user_id: str = None, result: str = "success") -> str:
        """记录配置变更"""
        
        details = {
            'config_file': config_file,
            'changes': changes,
            'change_count': len(changes)
        }
        
        return self.log_event(
            event_type=AuditEventType.CONFIG_CHANGE,
            operation="config_update",
            resource=f"config:{config_file}",
            details=details,
            result=result,
            user_id=user_id
        )
    
    def log_file_operation(self, operation: str, file_path: str,
                          details: Dict[str, Any] = None, result: str = "success",
                          user_id: str = None) -> str:
        """记录文件操作"""
        
        file_details = {
            'operation': operation,
            'file_path': file_path,
            'file_size': None,
            'file_hash': None
        }
        
        # 尝试获取文件信息
        try:
            path = Path(file_path)
            if path.exists():
                file_details['file_size'] = path.stat().st_size
                
                # 计算文件哈希（仅对小文件）
                if file_details['file_size'] < 1024 * 1024:  # 1MB以下
                    with open(path, 'rb') as f:
                        file_details['file_hash'] = hashlib.md5(f.read()).hexdigest()
        except Exception:
            pass
        
        if details:
            file_details.update(details)
        
        return self.log_event(
            event_type=AuditEventType.FILE_OPERATION,
            operation=f"file_{operation}",
            resource=f"file:{file_path}",
            details=file_details,
            result=result,
            user_id=user_id
        )
    
    def log_performance_metric(self, metric_name: str, value: float,
                             unit: str = "ms", details: Dict[str, Any] = None) -> str:
        """记录性能指标"""
        
        perf_details = {
            'metric_name': metric_name,
            'value': value,
            'unit': unit
        }
        
        if details:
            perf_details.update(details)
        
        return self.log_event(
            event_type=AuditEventType.PERFORMANCE_METRIC,
            operation="performance_measurement",
            resource=f"metric:{metric_name}",
            details=perf_details,
            result="success"
        )
    
    def log_error_event(self, error_id: str, error_category: str, error_message: str,
                       context: Dict[str, Any] = None, user_id: str = None) -> str:
        """记录错误事件"""
        
        error_details = {
            'error_id': error_id,
            'error_category': error_category,
            'error_message': error_message,
            'context': context or {}
        }
        
        return self.log_event(
            event_type=AuditEventType.ERROR_OCCURRED,
            operation="error_handling",
            resource=f"error:{error_id}",
            details=error_details,
            result="failure",
            user_id=user_id
        )
    
    def log_system_event(self, event: str, details: Dict[str, Any] = None) -> str:
        """记录系统事件"""
        
        event_type_map = {
            'system_start': AuditEventType.SYSTEM_START,
            'system_stop': AuditEventType.SYSTEM_STOP
        }
        
        event_type = event_type_map.get(event, AuditEventType.USER_ACTION)
        
        return self.log_event(
            event_type=event_type,
            operation=event,
            resource="system",
            details=details,
            result="success"
        )
    
    def get_audit_trail(self, resource: str = None, user_id: str = None,
                       event_type: AuditEventType = None, 
                       start_time: datetime = None, end_time: datetime = None,
                       limit: int = 100) -> List[AuditEvent]:
        """获取审计跟踪"""
        
        with self._lock:
            filtered_events = self.audit_events.copy()
        
        # 应用过滤条件
        if resource:
            filtered_events = [e for e in filtered_events if e.resource and resource in e.resource]
        
        if user_id:
            filtered_events = [e for e in filtered_events if e.user_id == user_id]
        
        if event_type:
            filtered_events = [e for e in filtered_events if e.event_type == event_type]
        
        if start_time:
            filtered_events = [e for e in filtered_events if e.timestamp >= start_time]
        
        if end_time:
            filtered_events = [e for e in filtered_events if e.timestamp <= end_time]
        
        # 按时间倒序排列
        filtered_events.sort(key=lambda x: x.timestamp, reverse=True)
        
        # 应用限制
        return filtered_events[:limit]
    
    def get_audit_statistics(self, days: int = 7) -> Dict[str, Any]:
        """获取审计统计"""
        
        cutoff_time = datetime.now() - timedelta(days=days)
        
        with self._lock:
            recent_events = [e for e in self.audit_events if e.timestamp >= cutoff_time]
        
        if not recent_events:
            return {'message': f'最近{days}天无审计记录'}
        
        # 按事件类型统计
        event_type_stats = {}
        result_stats = {}
        user_stats = {}
        daily_stats = {}
        
        for event in recent_events:
            # 事件类型统计
            event_type = event.event_type.value
            if event_type not in event_type_stats:
                event_type_stats[event_type] = 0
            event_type_stats[event_type] += 1
            
            # 结果统计
            result = event.result
            if result not in result_stats:
                result_stats[result] = 0
            result_stats[result] += 1
            
            # 用户统计
            user = event.user_id or 'unknown'
            if user not in user_stats:
                user_stats[user] = 0
            user_stats[user] += 1
            
            # 每日统计
            day = event.timestamp.strftime('%Y-%m-%d')
            if day not in daily_stats:
                daily_stats[day] = 0
            daily_stats[day] += 1
        
        # 性能统计
        performance_events = [e for e in recent_events 
                            if e.event_type == AuditEventType.PERFORMANCE_METRIC]
        
        avg_duration = None
        if performance_events:
            durations = [e.duration_ms for e in performance_events if e.duration_ms]
            if durations:
                avg_duration = sum(durations) / len(durations)
        
        return {
            'period_days': days,
            'total_events': len(recent_events),
            'event_type_distribution': event_type_stats,
            'result_distribution': result_stats,
            'user_activity': user_stats,
            'daily_activity': daily_stats,
            'performance': {
                'avg_duration_ms': avg_duration,
                'performance_events_count': len(performance_events)
            }
        }
    
    def export_audit_log(self, output_file: Path, format: str = "json",
                        start_time: datetime = None, end_time: datetime = None) -> bool:
        """导出审计日志"""
        
        try:
            events = self.get_audit_trail(
                start_time=start_time,
                end_time=end_time,
                limit=None  # 导出所有符合条件的事件
            )
            
            if format.lower() == "json":
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(
                        [event.to_dict() for event in events],
                        f,
                        ensure_ascii=False,
                        indent=2
                    )
            
            elif format.lower() == "csv":
                import csv
                
                with open(output_file, 'w', newline='', encoding='utf-8') as f:
                    if events:
                        writer = csv.DictWriter(f, fieldnames=events[0].to_dict().keys())
                        writer.writeheader()
                        for event in events:
                            writer.writerow(event.to_dict())
            
            return True
            
        except Exception:
            return False
    
    def cleanup_old_logs(self, days_to_keep: int = 30):
        """清理旧日志文件"""
        
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        
        # 清理日志文件
        for log_file in self.log_dir.glob("audit_*.log"):
            try:
                # 从文件名提取日期
                date_str = log_file.stem.split('_')[1]
                file_date = datetime.strptime(date_str, '%Y%m%d')
                
                if file_date < cutoff_date:
                    log_file.unlink()
                    
            except Exception:
                continue
        
        # 清理内存中的旧事件
        with self._lock:
            self.audit_events = [
                e for e in self.audit_events 
                if e.timestamp >= cutoff_date
            ]

# 全局审计日志记录器实例
_audit_logger = None

def get_audit_logger() -> AuditLogger:
    """获取全局审计日志记录器实例"""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger

def audit_decorator(operation: str, resource_func: callable = None):
    """审计装饰器"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            start_time = datetime.now()
            
            try:
                result = func(*args, **kwargs)
                end_time = datetime.now()
                duration_ms = (end_time - start_time).total_seconds() * 1000
                
                # 确定资源
                resource = None
                if resource_func:
                    try:
                        resource = resource_func(*args, **kwargs)
                    except Exception:
                        pass
                
                # 记录成功事件
                get_audit_logger().log_event(
                    event_type=AuditEventType.USER_ACTION,
                    operation=operation,
                    resource=resource,
                    details={'function': func.__name__},
                    result="success",
                    duration_ms=duration_ms
                )
                
                return result
                
            except Exception as e:
                end_time = datetime.now()
                duration_ms = (end_time - start_time).total_seconds() * 1000
                
                # 记录失败事件
                get_audit_logger().log_event(
                    event_type=AuditEventType.ERROR_OCCURRED,
                    operation=operation,
                    resource=resource_func(*args, **kwargs) if resource_func else None,
                    details={
                        'function': func.__name__,
                        'error': str(e),
                        'error_type': type(e).__name__
                    },
                    result="failure",
                    duration_ms=duration_ms
                )
                
                raise e
        
        return wrapper
    return decorator

if __name__ == "__main__":
    # 测试审计日志系统
    print("=== 审计日志系统测试 ===")
    
    logger = get_audit_logger()
    
    # 测试各种事件记录
    print("1. 记录模板操作...")
    logger.log_template_operation("create", "test_template_1", 
                                {"category": "electronics", "type": "standard"})
    
    logger.log_template_operation("update", "test_template_1",
                                {"changes": ["name", "description"]})
    
    print("2. 记录配置变更...")
    logger.log_config_change("categories.yaml", 
                            {"electronics": {"new_subcategory": "wearables"}})
    
    print("3. 记录文件操作...")
    logger.log_file_operation("create", "/tmp/test_file.json",
                            {"size": 1024, "encoding": "utf-8"})
    
    print("4. 记录性能指标...")
    logger.log_performance_metric("template_creation_time", 1250.5, "ms",
                                {"template_type": "standard"})
    
    print("5. 记录错误事件...")
    logger.log_error_event("ERR_20241219_001", "validation", 
                          "Invalid template name", {"field": "name"})
    
    # 获取审计统计
    print("\n=== 审计统计 ===")
    stats = logger.get_audit_statistics(days=1)
    
    print(f"总事件数: {stats['total_events']}")
    print("事件类型分布:")
    for event_type, count in stats['event_type_distribution'].items():
        print(f"  {event_type}: {count}")
    
    print("结果分布:")
    for result, count in stats['result_distribution'].items():
        print(f"  {result}: {count}")
    
    # 获取审计跟踪
    print("\n=== 最近审计跟踪 ===")
    trail = logger.get_audit_trail(limit=5)
    
    for event in trail:
        print(f"[{event.timestamp.strftime('%H:%M:%S')}] {event.operation} - {event.result}")
        if event.resource:
            print(f"  资源: {event.resource}")
        if event.details:
            print(f"  详情: {list(event.details.keys())}")
    
    print("\n✓ 审计日志系统测试完成")