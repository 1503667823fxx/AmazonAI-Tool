"""
Advanced Resource Management System for Video Studio

This module provides intelligent resource management including:
- Dynamic resource allocation
- Memory pool management
- Connection pooling
- Resource usage prediction
- Automatic scaling and throttling

Validates: Requirements 4.3, 7.1, 7.3
"""

import asyncio
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
import logging
from collections import deque
import weakref

from .performance_monitor import PerformanceMonitor, SystemMetrics
from .config import get_config


class ResourceType(Enum):
    """Types of resources managed by the system"""
    MEMORY = "memory"
    CPU = "cpu"
    DISK_IO = "disk_io"
    NETWORK = "network"
    GPU = "gpu"
    THREAD_POOL = "thread_pool"
    CONNECTION_POOL = "connection_pool"


class ResourcePriority(Enum):
    """Priority levels for resource allocation"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class ResourceRequest:
    """Request for resource allocation"""
    request_id: str
    resource_type: ResourceType
    amount: float
    priority: ResourcePriority
    requester_id: str
    timeout_seconds: Optional[float] = None
    created_at: datetime = field(default_factory=datetime.now)
    callback: Optional[Callable] = None


@dataclass
class ResourceAllocation:
    """Allocated resource information"""
    allocation_id: str
    request: ResourceRequest
    allocated_amount: float
    allocated_at: datetime
    expires_at: Optional[datetime] = None
    
    def is_expired(self) -> bool:
        """Check if allocation has expired"""
        return self.expires_at is not None and datetime.now() > self.expires_at


@dataclass
class ResourcePool:
    """Resource pool configuration and state"""
    resource_type: ResourceType
    total_capacity: float
    available_capacity: float
    allocated_capacity: float
    min_reserved: float = 0.0
    max_per_request: Optional[float] = None
    allocations: Dict[str, ResourceAllocation] = field(default_factory=dict)
    
    def can_allocate(self, amount: float) -> bool:
        """Check if the requested amount can be allocated"""
        return (self.available_capacity >= amount and 
                (self.max_per_request is None or amount <= self.max_per_request))
    
    def allocate(self, allocation: ResourceAllocation) -> bool:
        """Allocate resources"""
        if self.can_allocate(allocation.allocated_amount):
            self.allocations[allocation.allocation_id] = allocation
            self.available_capacity -= allocation.allocated_amount
            self.allocated_capacity += allocation.allocated_amount
            return True
        return False
    
    def deallocate(self, allocation_id: str) -> bool:
        """Deallocate resources"""
        if allocation_id in self.allocations:
            allocation = self.allocations.pop(allocation_id)
            self.available_capacity += allocation.allocated_amount
            self.allocated_capacity -= allocation.allocated_amount
            return True
        return False
    
    def get_utilization(self) -> float:
        """Get current utilization percentage"""
        return (self.allocated_capacity / self.total_capacity) * 100


class ResourceManager:
    """
    Advanced resource management system for Video Studio.
    
    Provides intelligent resource allocation, monitoring, and optimization
    to ensure optimal system performance under varying workloads.
    """
    
    def __init__(self, performance_monitor: Optional[PerformanceMonitor] = None):
        """Initialize ResourceManager"""
        self.performance_monitor = performance_monitor or PerformanceMonitor()
        self.config = get_config()
        self.logger = logging.getLogger(__name__)
        
        # Resource pools
        self.resource_pools: Dict[ResourceType, ResourcePool] = {}
        self._initialize_resource_pools()
        
        # Request management
        self.pending_requests: deque = deque()
        self.request_history: List[ResourceRequest] = []
        self.allocation_callbacks: Dict[str, Callable] = {}
        
        # Scheduling and monitoring
        self._scheduler_task: Optional[asyncio.Task] = None
        self._monitor_task: Optional[asyncio.Task] = None
        self._running = False
        
        # Resource usage prediction
        self.usage_history: Dict[ResourceType, deque] = {
            rt: deque(maxlen=1000) for rt in ResourceType
        }
        
        # Throttling and scaling
        self.throttling_enabled = True
        self.auto_scaling_enabled = True
        self.throttle_thresholds = {
            ResourceType.MEMORY: 85.0,
            ResourceType.CPU: 80.0,
            ResourceType.DISK_IO: 90.0
        }
        
        # Connection pooling
        self.connection_pools: Dict[str, Any] = {}
        self.max_connections_per_pool = 10
        
        # Thread safety
        self._lock = threading.RLock()
    
    def _initialize_resource_pools(self) -> None:
        """Initialize resource pools based on system capabilities"""
        # Get system information
        import psutil
        
        # Memory pool (in MB)
        total_memory_mb = psutil.virtual_memory().total / (1024 * 1024)
        available_memory_mb = total_memory_mb * 0.8  # Reserve 20% for system
        
        self.resource_pools[ResourceType.MEMORY] = ResourcePool(
            resource_type=ResourceType.MEMORY,
            total_capacity=available_memory_mb,
            available_capacity=available_memory_mb,
            allocated_capacity=0.0,
            min_reserved=total_memory_mb * 0.1,  # Reserve 10%
            max_per_request=available_memory_mb * 0.5  # Max 50% per request
        )
        
        # CPU pool (in percentage points)
        cpu_count = psutil.cpu_count()
        available_cpu = cpu_count * 80  # 80% of CPU capacity
        
        self.resource_pools[ResourceType.CPU] = ResourcePool(
            resource_type=ResourceType.CPU,
            total_capacity=available_cpu,
            available_capacity=available_cpu,
            allocated_capacity=0.0,
            min_reserved=cpu_count * 10,  # Reserve 10%
            max_per_request=available_cpu * 0.6  # Max 60% per request
        )
        
        # Disk I/O pool (in MB/s)
        self.resource_pools[ResourceType.DISK_IO] = ResourcePool(
            resource_type=ResourceType.DISK_IO,
            total_capacity=1000.0,  # Assume 1GB/s disk throughput
            available_capacity=800.0,  # Reserve 20%
            allocated_capacity=0.0,
            min_reserved=100.0,
            max_per_request=400.0
        )
        
        # Network pool (in MB/s)
        self.resource_pools[ResourceType.NETWORK] = ResourcePool(
            resource_type=ResourceType.NETWORK,
            total_capacity=100.0,  # Assume 100MB/s network
            available_capacity=80.0,  # Reserve 20%
            allocated_capacity=0.0,
            min_reserved=10.0,
            max_per_request=50.0
        )
        
        # Thread pool
        max_threads = min(32, (cpu_count or 1) + 4)
        self.resource_pools[ResourceType.THREAD_POOL] = ResourcePool(
            resource_type=ResourceType.THREAD_POOL,
            total_capacity=max_threads,
            available_capacity=max_threads,
            allocated_capacity=0.0,
            min_reserved=2,
            max_per_request=max_threads // 2
        )
        
        # Connection pool
        self.resource_pools[ResourceType.CONNECTION_POOL] = ResourcePool(
            resource_type=ResourceType.CONNECTION_POOL,
            total_capacity=100,
            available_capacity=100,
            allocated_capacity=0.0,
            min_reserved=5,
            max_per_request=20
        )
    
    async def start_resource_management(self) -> None:
        """Start resource management services"""
        if self._running:
            return
        
        self._running = True
        
        # Start scheduler for processing resource requests
        self._scheduler_task = asyncio.create_task(self._resource_scheduler())
        
        # Start monitor for tracking resource usage
        self._monitor_task = asyncio.create_task(self._resource_monitor())
        
        self.logger.info("Resource management services started")
    
    async def stop_resource_management(self) -> None:
        """Stop resource management services"""
        self._running = False
        
        if self._scheduler_task:
            self._scheduler_task.cancel()
            try:
                await self._scheduler_task
            except asyncio.CancelledError:
                pass
        
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("Resource management services stopped")
    
    async def _resource_scheduler(self) -> None:
        """Main resource scheduling loop"""
        while self._running:
            try:
                await self._process_pending_requests()
                await self._cleanup_expired_allocations()
                await asyncio.sleep(0.1)  # 100ms scheduling interval
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in resource scheduler: {e}")
                await asyncio.sleep(1)
    
    async def _resource_monitor(self) -> None:
        """Resource usage monitoring loop"""
        while self._running:
            try:
                await self._update_resource_usage()
                await self._check_throttling_conditions()
                await asyncio.sleep(5)  # 5 second monitoring interval
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in resource monitor: {e}")
                await asyncio.sleep(5)
    
    async def request_resources(self, resource_type: ResourceType, amount: float,
                              priority: ResourcePriority = ResourcePriority.NORMAL,
                              requester_id: str = "unknown",
                              timeout_seconds: Optional[float] = None) -> Optional[str]:
        """
        Request resource allocation.
        
        Args:
            resource_type: Type of resource to allocate
            amount: Amount of resource needed
            priority: Request priority
            requester_id: ID of the requesting component
            timeout_seconds: Request timeout
            
        Returns:
            Allocation ID if successful, None if failed
        """
        request_id = f"{resource_type.value}_{int(time.time() * 1000)}"
        
        request = ResourceRequest(
            request_id=request_id,
            resource_type=resource_type,
            amount=amount,
            priority=priority,
            requester_id=requester_id,
            timeout_seconds=timeout_seconds
        )
        
        with self._lock:
            # Check if we can allocate immediately
            pool = self.resource_pools.get(resource_type)
            if pool and pool.can_allocate(amount):
                allocation_id = f"alloc_{request_id}"
                allocation = ResourceAllocation(
                    allocation_id=allocation_id,
                    request=request,
                    allocated_amount=amount,
                    allocated_at=datetime.now(),
                    expires_at=datetime.now() + timedelta(seconds=timeout_seconds) if timeout_seconds else None
                )
                
                if pool.allocate(allocation):
                    self.logger.debug(f"Immediate allocation: {allocation_id} ({amount} {resource_type.value})")
                    return allocation_id
            
            # Queue the request for later processing
            self.pending_requests.append(request)
            self.request_history.append(request)
            
            # Keep history limited
            if len(self.request_history) > 10000:
                self.request_history = self.request_history[-5000:]
        
        self.logger.debug(f"Queued resource request: {request_id}")
        return None
    
    async def release_resources(self, allocation_id: str) -> bool:
        """
        Release allocated resources.
        
        Args:
            allocation_id: ID of the allocation to release
            
        Returns:
            True if successfully released
        """
        with self._lock:
            for pool in self.resource_pools.values():
                if allocation_id in pool.allocations:
                    success = pool.deallocate(allocation_id)
                    if success:
                        self.logger.debug(f"Released allocation: {allocation_id}")
                    return success
        
        return False
    
    async def _process_pending_requests(self) -> None:
        """Process pending resource requests"""
        if not self.pending_requests:
            return
        
        with self._lock:
            # Sort requests by priority and age
            sorted_requests = sorted(
                self.pending_requests,
                key=lambda r: (r.priority.value, r.created_at),
                reverse=True
            )
            
            processed_requests = []
            
            for request in sorted_requests:
                # Check timeout
                if (request.timeout_seconds and 
                    (datetime.now() - request.created_at).total_seconds() > request.timeout_seconds):
                    processed_requests.append(request)
                    continue
                
                # Try to allocate
                pool = self.resource_pools.get(request.resource_type)
                if pool and pool.can_allocate(request.amount):
                    allocation_id = f"alloc_{request.request_id}"
                    allocation = ResourceAllocation(
                        allocation_id=allocation_id,
                        request=request,
                        allocated_amount=request.amount,
                        allocated_at=datetime.now(),
                        expires_at=datetime.now() + timedelta(seconds=request.timeout_seconds) if request.timeout_seconds else None
                    )
                    
                    if pool.allocate(allocation):
                        processed_requests.append(request)
                        
                        # Notify callback if provided
                        if request.callback:
                            try:
                                await request.callback(allocation_id)
                            except Exception as e:
                                self.logger.error(f"Error in allocation callback: {e}")
                        
                        self.logger.debug(f"Processed allocation: {allocation_id}")
            
            # Remove processed requests
            for request in processed_requests:
                try:
                    self.pending_requests.remove(request)
                except ValueError:
                    pass
    
    async def _cleanup_expired_allocations(self) -> None:
        """Clean up expired resource allocations"""
        with self._lock:
            for pool in self.resource_pools.values():
                expired_allocations = [
                    alloc_id for alloc_id, allocation in pool.allocations.items()
                    if allocation.is_expired()
                ]
                
                for alloc_id in expired_allocations:
                    pool.deallocate(alloc_id)
                    self.logger.debug(f"Cleaned up expired allocation: {alloc_id}")
    
    async def _update_resource_usage(self) -> None:
        """Update resource usage statistics"""
        # Get current system metrics
        metrics = self.performance_monitor.get_current_metrics()
        if not metrics:
            return
        
        # Update usage history
        current_time = datetime.now()
        
        self.usage_history[ResourceType.MEMORY].append({
            'timestamp': current_time,
            'usage_percent': metrics.memory_percent,
            'allocated': self.resource_pools[ResourceType.MEMORY].allocated_capacity
        })
        
        self.usage_history[ResourceType.CPU].append({
            'timestamp': current_time,
            'usage_percent': metrics.cpu_percent,
            'allocated': self.resource_pools[ResourceType.CPU].allocated_capacity
        })
        
        self.usage_history[ResourceType.DISK_IO].append({
            'timestamp': current_time,
            'usage_percent': metrics.disk_usage_percent,
            'allocated': self.resource_pools[ResourceType.DISK_IO].allocated_capacity
        })
    
    async def _check_throttling_conditions(self) -> None:
        """Check if throttling should be applied"""
        if not self.throttling_enabled:
            return
        
        metrics = self.performance_monitor.get_current_metrics()
        if not metrics:
            return
        
        # Check memory throttling
        if metrics.memory_percent > self.throttle_thresholds[ResourceType.MEMORY]:
            await self._apply_throttling(ResourceType.MEMORY, 0.5)  # Reduce by 50%
        
        # Check CPU throttling
        if metrics.cpu_percent > self.throttle_thresholds[ResourceType.CPU]:
            await self._apply_throttling(ResourceType.CPU, 0.7)  # Reduce by 30%
        
        # Check disk I/O throttling
        if metrics.disk_usage_percent > self.throttle_thresholds[ResourceType.DISK_IO]:
            await self._apply_throttling(ResourceType.DISK_IO, 0.6)  # Reduce by 40%
    
    async def _apply_throttling(self, resource_type: ResourceType, reduction_factor: float) -> None:
        """Apply throttling to a resource type"""
        with self._lock:
            pool = self.resource_pools.get(resource_type)
            if pool:
                # Temporarily reduce available capacity
                original_capacity = pool.total_capacity
                throttled_capacity = original_capacity * reduction_factor
                
                if pool.available_capacity > throttled_capacity - pool.allocated_capacity:
                    pool.available_capacity = throttled_capacity - pool.allocated_capacity
                    
                    self.logger.warning(
                        f"Applied throttling to {resource_type.value}: "
                        f"reduced capacity to {reduction_factor * 100:.0f}%"
                    )
                    
                    # Schedule throttling removal
                    asyncio.create_task(self._remove_throttling_after_delay(resource_type, 30))
    
    async def _remove_throttling_after_delay(self, resource_type: ResourceType, delay_seconds: int) -> None:
        """Remove throttling after a delay"""
        await asyncio.sleep(delay_seconds)
        
        with self._lock:
            pool = self.resource_pools.get(resource_type)
            if pool:
                # Restore original capacity
                pool.available_capacity = pool.total_capacity - pool.allocated_capacity
                self.logger.info(f"Removed throttling from {resource_type.value}")
    
    def get_resource_status(self) -> Dict[str, Any]:
        """Get current resource status"""
        with self._lock:
            status = {
                'pools': {},
                'pending_requests': len(self.pending_requests),
                'total_allocations': sum(len(pool.allocations) for pool in self.resource_pools.values()),
                'throttling_enabled': self.throttling_enabled,
                'auto_scaling_enabled': self.auto_scaling_enabled
            }
            
            for resource_type, pool in self.resource_pools.items():
                status['pools'][resource_type.value] = {
                    'total_capacity': pool.total_capacity,
                    'available_capacity': pool.available_capacity,
                    'allocated_capacity': pool.allocated_capacity,
                    'utilization_percent': pool.get_utilization(),
                    'active_allocations': len(pool.allocations)
                }
            
            return status
    
    def predict_resource_usage(self, resource_type: ResourceType, 
                              minutes_ahead: int = 30) -> Optional[float]:
        """
        Predict future resource usage based on historical data.
        
        Args:
            resource_type: Type of resource to predict
            minutes_ahead: How many minutes ahead to predict
            
        Returns:
            Predicted usage percentage
        """
        history = self.usage_history.get(resource_type, [])
        if len(history) < 10:
            return None
        
        # Simple linear trend prediction
        recent_data = list(history)[-60:]  # Last 60 data points (5 minutes)
        
        if len(recent_data) < 2:
            return None
        
        # Calculate trend
        time_diffs = []
        usage_diffs = []
        
        for i in range(1, len(recent_data)):
            time_diff = (recent_data[i]['timestamp'] - recent_data[i-1]['timestamp']).total_seconds()
            usage_diff = recent_data[i]['usage_percent'] - recent_data[i-1]['usage_percent']
            
            time_diffs.append(time_diff)
            usage_diffs.append(usage_diff)
        
        if not time_diffs:
            return recent_data[-1]['usage_percent']
        
        # Average rate of change per second
        avg_rate = sum(usage_diffs) / sum(time_diffs) if sum(time_diffs) > 0 else 0
        
        # Predict usage
        current_usage = recent_data[-1]['usage_percent']
        predicted_usage = current_usage + (avg_rate * minutes_ahead * 60)
        
        # Clamp to reasonable bounds
        return max(0, min(100, predicted_usage))
    
    async def optimize_resource_allocation(self) -> Dict[str, Any]:
        """Optimize resource allocation based on usage patterns"""
        optimization_results = {
            'adjustments_made': 0,
            'pools_optimized': [],
            'recommendations': []
        }
        
        with self._lock:
            for resource_type, pool in self.resource_pools.items():
                utilization = pool.get_utilization()
                
                # If utilization is consistently low, reduce reserved capacity
                if utilization < 20:
                    if pool.min_reserved > pool.total_capacity * 0.05:
                        pool.min_reserved = pool.total_capacity * 0.05
                        optimization_results['adjustments_made'] += 1
                        optimization_results['pools_optimized'].append(resource_type.value)
                
                # If utilization is consistently high, increase capacity if possible
                elif utilization > 90:
                    predicted_usage = self.predict_resource_usage(resource_type, 15)
                    if predicted_usage and predicted_usage > 95:
                        optimization_results['recommendations'].append(
                            f"Consider increasing {resource_type.value} capacity - "
                            f"predicted usage: {predicted_usage:.1f}%"
                        )
        
        return optimization_results
    
    def create_connection_pool(self, pool_name: str, factory_func: Callable,
                              max_connections: int = 10) -> None:
        """Create a connection pool for external resources"""
        self.connection_pools[pool_name] = {
            'factory': factory_func,
            'max_connections': max_connections,
            'active_connections': [],
            'available_connections': deque(),
            'created_count': 0
        }
    
    async def get_connection(self, pool_name: str, timeout_seconds: float = 30) -> Optional[Any]:
        """Get a connection from the pool"""
        if pool_name not in self.connection_pools:
            return None
        
        pool = self.connection_pools[pool_name]
        
        # Try to get available connection
        if pool['available_connections']:
            return pool['available_connections'].popleft()
        
        # Create new connection if under limit
        if pool['created_count'] < pool['max_connections']:
            try:
                connection = await pool['factory']()
                pool['created_count'] += 1
                pool['active_connections'].append(weakref.ref(connection))
                return connection
            except Exception as e:
                self.logger.error(f"Failed to create connection for pool {pool_name}: {e}")
                return None
        
        # Wait for available connection
        start_time = time.time()
        while time.time() - start_time < timeout_seconds:
            if pool['available_connections']:
                return pool['available_connections'].popleft()
            await asyncio.sleep(0.1)
        
        return None
    
    def return_connection(self, pool_name: str, connection: Any) -> None:
        """Return a connection to the pool"""
        if pool_name in self.connection_pools:
            pool = self.connection_pools[pool_name]
            pool['available_connections'].append(connection)


# Global resource manager instance
_resource_manager = None


def get_resource_manager() -> ResourceManager:
    """Get global ResourceManager instance"""
    global _resource_manager
    if _resource_manager is None:
        _resource_manager = ResourceManager()
    return _resource_manager


# Convenience functions
async def request_memory(amount_mb: float, priority: ResourcePriority = ResourcePriority.NORMAL,
                        requester_id: str = "unknown") -> Optional[str]:
    """Request memory allocation"""
    return await get_resource_manager().request_resources(
        ResourceType.MEMORY, amount_mb, priority, requester_id
    )


async def request_cpu(percentage: float, priority: ResourcePriority = ResourcePriority.NORMAL,
                     requester_id: str = "unknown") -> Optional[str]:
    """Request CPU allocation"""
    return await get_resource_manager().request_resources(
        ResourceType.CPU, percentage, priority, requester_id
    )


async def release_allocation(allocation_id: str) -> bool:
    """Release resource allocation"""
    return await get_resource_manager().release_resources(allocation_id)


def get_resource_status() -> Dict[str, Any]:
    """Get current resource status"""
    return get_resource_manager().get_resource_status()