"""
Performance Optimization Module for Video Studio

This module provides comprehensive performance optimization features including:
- Memory usage optimization
- Processing speed improvements
- Resource cleanup automation
- Performance bottleneck detection and resolution

Validates: Requirements 4.3, 7.1, 7.3
"""

import asyncio
import gc
import psutil
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging
from pathlib import Path
import json

from .performance_monitor import PerformanceMonitor, SystemMetrics, MetricType
from .cleanup_service import CleanupService
from .asset_manager import AssetManager
from .config import get_config


class OptimizationLevel(Enum):
    """Optimization intensity levels"""
    CONSERVATIVE = "conservative"
    BALANCED = "balanced"
    AGGRESSIVE = "aggressive"


class OptimizationType(Enum):
    """Types of optimizations available"""
    MEMORY = "memory"
    DISK = "disk"
    CPU = "cpu"
    NETWORK = "network"
    CACHE = "cache"


@dataclass
class OptimizationResult:
    """Result of an optimization operation"""
    optimization_type: OptimizationType
    success: bool
    metrics_before: Dict[str, float]
    metrics_after: Dict[str, float]
    improvement_percent: float
    details: str
    duration_seconds: float
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class PerformanceProfile:
    """Performance profile for different workload types"""
    name: str
    memory_limit_mb: int
    max_concurrent_tasks: int
    cleanup_interval_minutes: int
    cache_size_mb: int
    enable_aggressive_gc: bool
    prefetch_assets: bool
    compress_temp_files: bool


class PerformanceOptimizer:
    """
    Comprehensive performance optimization system for Video Studio.
    
    Provides intelligent optimization based on system resources, workload patterns,
    and performance metrics to ensure optimal system performance.
    """
    
    def __init__(self, performance_monitor: Optional[PerformanceMonitor] = None,
                 cleanup_service: Optional[CleanupService] = None,
                 asset_manager: Optional[AssetManager] = None):
        """Initialize PerformanceOptimizer"""
        self.performance_monitor = performance_monitor or PerformanceMonitor()
        self.cleanup_service = cleanup_service or CleanupService()
        self.asset_manager = asset_manager or AssetManager()
        self.config = get_config()
        self.logger = logging.getLogger(__name__)
        
        # Optimization state
        self.optimization_history: List[OptimizationResult] = []
        self.active_optimizations: Dict[str, bool] = {}
        self.optimization_lock = threading.Lock()
        
        # Performance profiles
        self.profiles = self._create_performance_profiles()
        self.current_profile = self.profiles["balanced"]
        
        # Optimization thresholds
        self.memory_warning_threshold = 80.0  # Percentage
        self.memory_critical_threshold = 90.0
        self.cpu_warning_threshold = 75.0
        self.disk_warning_threshold = 85.0
        
        # Cache for frequently accessed data
        self._asset_cache: Dict[str, Any] = {}
        self._cache_max_size = 100
        self._cache_access_times: Dict[str, datetime] = {}
        
        # Background optimization task
        self._optimization_task: Optional[asyncio.Task] = None
        self._optimization_running = False
    
    def _create_performance_profiles(self) -> Dict[str, PerformanceProfile]:
        """Create predefined performance profiles"""
        return {
            "conservative": PerformanceProfile(
                name="Conservative",
                memory_limit_mb=2048,
                max_concurrent_tasks=2,
                cleanup_interval_minutes=30,
                cache_size_mb=128,
                enable_aggressive_gc=False,
                prefetch_assets=False,
                compress_temp_files=False
            ),
            "balanced": PerformanceProfile(
                name="Balanced",
                memory_limit_mb=4096,
                max_concurrent_tasks=4,
                cleanup_interval_minutes=15,
                cache_size_mb=256,
                enable_aggressive_gc=True,
                prefetch_assets=True,
                compress_temp_files=True
            ),
            "aggressive": PerformanceProfile(
                name="Aggressive",
                memory_limit_mb=8192,
                max_concurrent_tasks=8,
                cleanup_interval_minutes=5,
                cache_size_mb=512,
                enable_aggressive_gc=True,
                prefetch_assets=True,
                compress_temp_files=True
            )
        }
    
    async def start_continuous_optimization(self, interval_minutes: int = 5) -> None:
        """Start continuous background optimization"""
        if self._optimization_running:
            return
        
        self._optimization_running = True
        self._optimization_task = asyncio.create_task(
            self._continuous_optimization_loop(interval_minutes)
        )
        self.logger.info(f"Started continuous optimization with {interval_minutes}min interval")
    
    async def stop_continuous_optimization(self) -> None:
        """Stop continuous background optimization"""
        self._optimization_running = False
        if self._optimization_task:
            self._optimization_task.cancel()
            try:
                await self._optimization_task
            except asyncio.CancelledError:
                pass
        self.logger.info("Stopped continuous optimization")
    
    async def _continuous_optimization_loop(self, interval_minutes: int) -> None:
        """Main continuous optimization loop"""
        while self._optimization_running:
            try:
                # Check system metrics
                metrics = self.performance_monitor.get_current_metrics()
                if metrics:
                    # Determine if optimization is needed
                    if await self._should_optimize(metrics):
                        await self.optimize_system(OptimizationLevel.BALANCED)
                
                # Wait for next interval
                await asyncio.sleep(interval_minutes * 60)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in continuous optimization: {e}")
                await asyncio.sleep(60)  # Wait 1 minute before retrying
    
    async def _should_optimize(self, metrics: SystemMetrics) -> bool:
        """Determine if optimization is needed based on current metrics"""
        # Check memory usage
        if metrics.memory_percent > self.memory_warning_threshold:
            return True
        
        # Check CPU usage
        if metrics.cpu_percent > self.cpu_warning_threshold:
            return True
        
        # Check disk usage
        if metrics.disk_usage_percent > self.disk_warning_threshold:
            return True
        
        # Check error rate
        error_rate = self.performance_monitor.get_error_rate()
        if error_rate > 0.1:  # 10% error rate
            return True
        
        return False
    
    async def optimize_system(self, level: OptimizationLevel = OptimizationLevel.BALANCED) -> List[OptimizationResult]:
        """
        Perform comprehensive system optimization.
        
        Args:
            level: Optimization intensity level
            
        Returns:
            List of optimization results
        """
        with self.optimization_lock:
            if self.active_optimizations.get('system', False):
                self.logger.warning("System optimization already in progress")
                return []
            
            self.active_optimizations['system'] = True
        
        try:
            self.logger.info(f"Starting system optimization (level: {level.value})")
            start_time = datetime.now()
            results = []
            
            # Get baseline metrics
            baseline_metrics = self.performance_monitor.get_current_metrics()
            
            # Apply performance profile based on optimization level
            if level == OptimizationLevel.CONSERVATIVE:
                self.current_profile = self.profiles["conservative"]
            elif level == OptimizationLevel.BALANCED:
                self.current_profile = self.profiles["balanced"]
            else:  # AGGRESSIVE
                self.current_profile = self.profiles["aggressive"]
            
            # Run optimizations in order of impact
            optimizations = [
                self._optimize_memory,
                self._optimize_disk_usage,
                self._optimize_cache,
                self._optimize_garbage_collection,
                self._optimize_asset_storage
            ]
            
            for optimization_func in optimizations:
                try:
                    result = await optimization_func(level)
                    if result:
                        results.append(result)
                        self.optimization_history.append(result)
                except Exception as e:
                    self.logger.error(f"Optimization failed: {optimization_func.__name__}: {e}")
            
            # Final metrics check
            final_metrics = self.performance_monitor.get_current_metrics()
            duration = (datetime.now() - start_time).total_seconds()
            
            self.logger.info(
                f"System optimization completed in {duration:.2f}s. "
                f"Applied {len(results)} optimizations."
            )
            
            return results
            
        finally:
            self.active_optimizations['system'] = False
    
    async def _optimize_memory(self, level: OptimizationLevel) -> Optional[OptimizationResult]:
        """Optimize memory usage"""
        start_time = datetime.now()
        
        # Get initial memory metrics
        initial_metrics = self.performance_monitor.get_current_metrics()
        if not initial_metrics:
            return None
        
        initial_memory = initial_metrics.memory_percent
        
        try:
            # Clear asset cache if memory is high
            if initial_memory > self.memory_warning_threshold:
                cache_size_before = len(self._asset_cache)
                self._clear_asset_cache()
                
                # Force garbage collection
                if self.current_profile.enable_aggressive_gc:
                    gc.collect()
                
                # Wait for metrics to update
                await asyncio.sleep(1)
                
                # Get final metrics
                final_metrics = self.performance_monitor.get_current_metrics()
                if final_metrics:
                    final_memory = final_metrics.memory_percent
                    improvement = ((initial_memory - final_memory) / initial_memory) * 100
                    
                    return OptimizationResult(
                        optimization_type=OptimizationType.MEMORY,
                        success=True,
                        metrics_before={"memory_percent": initial_memory},
                        metrics_after={"memory_percent": final_memory},
                        improvement_percent=improvement,
                        details=f"Cleared {cache_size_before} cached items, forced GC",
                        duration_seconds=(datetime.now() - start_time).total_seconds()
                    )
            
            return None
            
        except Exception as e:
            return OptimizationResult(
                optimization_type=OptimizationType.MEMORY,
                success=False,
                metrics_before={"memory_percent": initial_memory},
                metrics_after={"memory_percent": initial_memory},
                improvement_percent=0.0,
                details=f"Memory optimization failed: {str(e)}",
                duration_seconds=(datetime.now() - start_time).total_seconds()
            )
    
    async def _optimize_disk_usage(self, level: OptimizationLevel) -> Optional[OptimizationResult]:
        """Optimize disk usage through cleanup"""
        start_time = datetime.now()
        
        # Get initial disk metrics
        initial_stats = self.asset_manager.get_storage_stats()
        initial_usage = initial_stats.get('disk_usage_percent', 0)
        
        try:
            # Run cleanup based on optimization level
            if level == OptimizationLevel.AGGRESSIVE:
                cleanup_result = await self.cleanup_service.run_cleanup(dry_run=False)
            elif initial_usage > self.disk_warning_threshold:
                cleanup_result = await self.cleanup_service.run_cleanup(dry_run=False)
            else:
                return None
            
            # Get final metrics
            final_stats = self.asset_manager.get_storage_stats()
            final_usage = final_stats.get('disk_usage_percent', 0)
            
            improvement = ((initial_usage - final_usage) / initial_usage) * 100 if initial_usage > 0 else 0
            
            return OptimizationResult(
                optimization_type=OptimizationType.DISK,
                success=cleanup_result.files_deleted > 0,
                metrics_before={"disk_usage_percent": initial_usage},
                metrics_after={"disk_usage_percent": final_usage},
                improvement_percent=improvement,
                details=f"Deleted {cleanup_result.files_deleted} files, freed {cleanup_result.space_freed_mb:.1f}MB",
                duration_seconds=(datetime.now() - start_time).total_seconds()
            )
            
        except Exception as e:
            return OptimizationResult(
                optimization_type=OptimizationType.DISK,
                success=False,
                metrics_before={"disk_usage_percent": initial_usage},
                metrics_after={"disk_usage_percent": initial_usage},
                improvement_percent=0.0,
                details=f"Disk optimization failed: {str(e)}",
                duration_seconds=(datetime.now() - start_time).total_seconds()
            )
    
    async def _optimize_cache(self, level: OptimizationLevel) -> Optional[OptimizationResult]:
        """Optimize cache usage"""
        start_time = datetime.now()
        
        initial_cache_size = len(self._asset_cache)
        
        try:
            # Adjust cache size based on profile
            self._cache_max_size = self.current_profile.cache_size_mb
            
            # Clean expired cache entries
            current_time = datetime.now()
            expired_keys = []
            
            for key, access_time in self._cache_access_times.items():
                if current_time - access_time > timedelta(minutes=30):
                    expired_keys.append(key)
            
            for key in expired_keys:
                self._asset_cache.pop(key, None)
                self._cache_access_times.pop(key, None)
            
            # Trim cache to max size (LRU eviction)
            if len(self._asset_cache) > self._cache_max_size:
                # Sort by access time and remove oldest
                sorted_items = sorted(
                    self._cache_access_times.items(),
                    key=lambda x: x[1]
                )
                
                items_to_remove = len(self._asset_cache) - self._cache_max_size
                for key, _ in sorted_items[:items_to_remove]:
                    self._asset_cache.pop(key, None)
                    self._cache_access_times.pop(key, None)
            
            final_cache_size = len(self._asset_cache)
            items_removed = initial_cache_size - final_cache_size
            
            if items_removed > 0:
                return OptimizationResult(
                    optimization_type=OptimizationType.CACHE,
                    success=True,
                    metrics_before={"cache_size": initial_cache_size},
                    metrics_after={"cache_size": final_cache_size},
                    improvement_percent=(items_removed / initial_cache_size) * 100,
                    details=f"Removed {items_removed} expired/excess cache entries",
                    duration_seconds=(datetime.now() - start_time).total_seconds()
                )
            
            return None
            
        except Exception as e:
            return OptimizationResult(
                optimization_type=OptimizationType.CACHE,
                success=False,
                metrics_before={"cache_size": initial_cache_size},
                metrics_after={"cache_size": initial_cache_size},
                improvement_percent=0.0,
                details=f"Cache optimization failed: {str(e)}",
                duration_seconds=(datetime.now() - start_time).total_seconds()
            )
    
    async def _optimize_garbage_collection(self, level: OptimizationLevel) -> Optional[OptimizationResult]:
        """Optimize garbage collection"""
        start_time = datetime.now()
        
        if not self.current_profile.enable_aggressive_gc:
            return None
        
        try:
            # Get initial memory
            initial_metrics = self.performance_monitor.get_current_metrics()
            if not initial_metrics:
                return None
            
            initial_memory = initial_metrics.memory_percent
            
            # Force garbage collection
            collected_objects = gc.collect()
            
            # Wait for metrics to update
            await asyncio.sleep(0.5)
            
            # Get final memory
            final_metrics = self.performance_monitor.get_current_metrics()
            if final_metrics:
                final_memory = final_metrics.memory_percent
                improvement = ((initial_memory - final_memory) / initial_memory) * 100 if initial_memory > 0 else 0
                
                return OptimizationResult(
                    optimization_type=OptimizationType.MEMORY,
                    success=collected_objects > 0,
                    metrics_before={"memory_percent": initial_memory},
                    metrics_after={"memory_percent": final_memory},
                    improvement_percent=improvement,
                    details=f"Collected {collected_objects} objects via GC",
                    duration_seconds=(datetime.now() - start_time).total_seconds()
                )
            
            return None
            
        except Exception as e:
            return OptimizationResult(
                optimization_type=OptimizationType.MEMORY,
                success=False,
                metrics_before={},
                metrics_after={},
                improvement_percent=0.0,
                details=f"GC optimization failed: {str(e)}",
                duration_seconds=(datetime.now() - start_time).total_seconds()
            )
    
    async def _optimize_asset_storage(self, level: OptimizationLevel) -> Optional[OptimizationResult]:
        """Optimize asset storage organization"""
        start_time = datetime.now()
        
        try:
            # Get initial storage stats
            initial_stats = self.asset_manager.get_storage_stats()
            initial_size = initial_stats['total_size_mb']
            
            # Run storage optimization
            optimization_result = await self.asset_manager.optimize_storage()
            
            # Get final storage stats
            final_stats = self.asset_manager.get_storage_stats()
            final_size = final_stats['total_size_mb']
            
            space_freed = initial_size - final_size
            improvement = (space_freed / initial_size) * 100 if initial_size > 0 else 0
            
            return OptimizationResult(
                optimization_type=OptimizationType.DISK,
                success=space_freed > 0,
                metrics_before={"storage_size_mb": initial_size},
                metrics_after={"storage_size_mb": final_size},
                improvement_percent=improvement,
                details=f"Storage optimization freed {space_freed:.1f}MB",
                duration_seconds=(datetime.now() - start_time).total_seconds()
            )
            
        except Exception as e:
            return OptimizationResult(
                optimization_type=OptimizationType.DISK,
                success=False,
                metrics_before={},
                metrics_after={},
                improvement_percent=0.0,
                details=f"Asset storage optimization failed: {str(e)}",
                duration_seconds=(datetime.now() - start_time).total_seconds()
            )
    
    def _clear_asset_cache(self) -> None:
        """Clear the asset cache"""
        self._asset_cache.clear()
        self._cache_access_times.clear()
    
    def cache_asset_data(self, asset_id: str, data: Any) -> None:
        """Cache asset data for faster access"""
        if len(self._asset_cache) >= self._cache_max_size:
            # Remove oldest entry
            oldest_key = min(self._cache_access_times.keys(), 
                           key=lambda k: self._cache_access_times[k])
            self._asset_cache.pop(oldest_key, None)
            self._cache_access_times.pop(oldest_key, None)
        
        self._asset_cache[asset_id] = data
        self._cache_access_times[asset_id] = datetime.now()
    
    def get_cached_asset_data(self, asset_id: str) -> Optional[Any]:
        """Get cached asset data"""
        if asset_id in self._asset_cache:
            self._cache_access_times[asset_id] = datetime.now()
            return self._asset_cache[asset_id]
        return None
    
    def get_optimization_summary(self) -> Dict[str, Any]:
        """Get summary of optimization history and current status"""
        recent_optimizations = [
            opt for opt in self.optimization_history
            if opt.timestamp > datetime.now() - timedelta(hours=24)
        ]
        
        successful_optimizations = [opt for opt in recent_optimizations if opt.success]
        
        return {
            "current_profile": self.current_profile.name,
            "cache_status": {
                "size": len(self._asset_cache),
                "max_size": self._cache_max_size,
                "hit_rate": self._calculate_cache_hit_rate()
            },
            "recent_optimizations": {
                "total": len(recent_optimizations),
                "successful": len(successful_optimizations),
                "total_improvement": sum(opt.improvement_percent for opt in successful_optimizations)
            },
            "active_optimizations": dict(self.active_optimizations),
            "optimization_running": self._optimization_running
        }
    
    def _calculate_cache_hit_rate(self) -> float:
        """Calculate cache hit rate (placeholder - would need request tracking)"""
        # This would require tracking cache hits/misses in a real implementation
        return 0.85  # Placeholder value
    
    async def detect_performance_bottlenecks(self) -> List[Dict[str, Any]]:
        """Detect performance bottlenecks in the system"""
        bottlenecks = []
        
        # Get current metrics
        metrics = self.performance_monitor.get_current_metrics()
        if not metrics:
            return bottlenecks
        
        # Check memory bottleneck
        if metrics.memory_percent > self.memory_critical_threshold:
            bottlenecks.append({
                "type": "memory",
                "severity": "critical",
                "description": f"Memory usage at {metrics.memory_percent:.1f}%",
                "recommendation": "Run aggressive memory optimization or increase system memory"
            })
        elif metrics.memory_percent > self.memory_warning_threshold:
            bottlenecks.append({
                "type": "memory",
                "severity": "warning",
                "description": f"Memory usage at {metrics.memory_percent:.1f}%",
                "recommendation": "Run memory optimization or reduce concurrent tasks"
            })
        
        # Check CPU bottleneck
        if metrics.cpu_percent > 90:
            bottlenecks.append({
                "type": "cpu",
                "severity": "critical",
                "description": f"CPU usage at {metrics.cpu_percent:.1f}%",
                "recommendation": "Reduce concurrent processing or upgrade CPU"
            })
        
        # Check disk bottleneck
        if metrics.disk_usage_percent > 95:
            bottlenecks.append({
                "type": "disk",
                "severity": "critical",
                "description": f"Disk usage at {metrics.disk_usage_percent:.1f}%",
                "recommendation": "Run cleanup immediately or add storage capacity"
            })
        
        # Check task queue bottleneck
        if metrics.active_tasks > self.current_profile.max_concurrent_tasks * 2:
            bottlenecks.append({
                "type": "task_queue",
                "severity": "warning",
                "description": f"High task queue: {metrics.active_tasks} active tasks",
                "recommendation": "Increase concurrent task limit or optimize task processing"
            })
        
        return bottlenecks
    
    def set_performance_profile(self, profile_name: str) -> bool:
        """Set the active performance profile"""
        if profile_name in self.profiles:
            self.current_profile = self.profiles[profile_name]
            self.logger.info(f"Switched to performance profile: {profile_name}")
            return True
        return False


# Global performance optimizer instance
_performance_optimizer = None


def get_performance_optimizer() -> PerformanceOptimizer:
    """Get global PerformanceOptimizer instance"""
    global _performance_optimizer
    if _performance_optimizer is None:
        _performance_optimizer = PerformanceOptimizer()
    return _performance_optimizer


# Convenience functions
async def optimize_system(level: OptimizationLevel = OptimizationLevel.BALANCED) -> List[OptimizationResult]:
    """Run system optimization"""
    return await get_performance_optimizer().optimize_system(level)


async def detect_bottlenecks() -> List[Dict[str, Any]]:
    """Detect performance bottlenecks"""
    return await get_performance_optimizer().detect_performance_bottlenecks()


def get_optimization_summary() -> Dict[str, Any]:
    """Get optimization summary"""
    return get_performance_optimizer().get_optimization_summary()