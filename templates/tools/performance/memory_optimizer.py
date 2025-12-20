#!/usr/bin/env python3
"""
内存优化器 - 优化内存使用和响应时间
Memory Optimizer - Optimize memory usage and response time
"""

import gc
import sys
import psutil
import threading
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime
import weakref

@dataclass
class MemoryStats:
    """内存统计信息"""
    total_memory: int
    available_memory: int
    used_memory: int
    memory_percent: float
    process_memory: int
    timestamp: datetime

class ObjectPool:
    """对象池 - 重用对象以减少内存分配"""
    
    def __init__(self, factory_func, max_size: int = 100):
        self.factory_func = factory_func
        self.max_size = max_size
        self._pool = []
        self._lock = threading.Lock()
    
    def get_object(self):
        """获取对象"""
        with self._lock:
            if self._pool:
                return self._pool.pop()
            else:
                return self.factory_func()
    
    def return_object(self, obj):
        """归还对象"""
        with self._lock:
            if len(self._pool) < self.max_size:
                # 重置对象状态
                if hasattr(obj, 'reset'):
                    obj.reset()
                self._pool.append(obj)

class LazyLoader:
    """延迟加载器 - 按需加载数据"""
    
    def __init__(self, loader_func):
        self.loader_func = loader_func
        self._data = None
        self._loaded = False
        self._lock = threading.Lock()
    
    def get_data(self):
        """获取数据"""
        if not self._loaded:
            with self._lock:
                if not self._loaded:
                    self._data = self.loader_func()
                    self._loaded = True
        return self._data
    
    def clear(self):
        """清空数据"""
        with self._lock:
            self._data = None
            self._loaded = False

class WeakReferenceCache:
    """弱引用缓存 - 自动清理不再使用的对象"""
    
    def __init__(self):
        self._cache = {}
        self._lock = threading.RLock()
    
    def get(self, key: str):
        """获取缓存对象"""
        with self._lock:
            if key in self._cache:
                obj = self._cache[key]()  # 调用弱引用
                if obj is not None:
                    return obj
                else:
                    # 对象已被垃圾回收，清理缓存
                    del self._cache[key]
            return None
    
    def set(self, key: str, obj):
        """设置缓存对象"""
        with self._lock:
            def cleanup_callback(ref):
                # 对象被垃圾回收时的回调
                with self._lock:
                    if key in self._cache and self._cache[key] is ref:
                        del self._cache[key]
            
            self._cache[key] = weakref.ref(obj, cleanup_callback)
    
    def clear(self):
        """清空缓存"""
        with self._lock:
            self._cache.clear()

class MemoryOptimizer:
    """内存优化器"""
    
    def __init__(self):
        self.object_pools = {}
        self.lazy_loaders = {}
        self.weak_cache = WeakReferenceCache()
        self._memory_stats = []
        self._lock = threading.RLock()
    
    def get_memory_stats(self) -> MemoryStats:
        """获取当前内存统计"""
        # 系统内存信息
        memory = psutil.virtual_memory()
        
        # 当前进程内存信息
        process = psutil.Process()
        process_memory = process.memory_info().rss
        
        stats = MemoryStats(
            total_memory=memory.total,
            available_memory=memory.available,
            used_memory=memory.used,
            memory_percent=memory.percent,
            process_memory=process_memory,
            timestamp=datetime.now()
        )
        
        with self._lock:
            self._memory_stats.append(stats)
            # 只保留最近100条记录
            if len(self._memory_stats) > 100:
                self._memory_stats = self._memory_stats[-100:]
        
        return stats
    
    def get_object_pool(self, pool_name: str, factory_func, max_size: int = 100) -> ObjectPool:
        """获取或创建对象池"""
        if pool_name not in self.object_pools:
            self.object_pools[pool_name] = ObjectPool(factory_func, max_size)
        return self.object_pools[pool_name]
    
    def create_lazy_loader(self, loader_name: str, loader_func) -> LazyLoader:
        """创建延迟加载器"""
        if loader_name not in self.lazy_loaders:
            self.lazy_loaders[loader_name] = LazyLoader(loader_func)
        return self.lazy_loaders[loader_name]
    
    def optimize_garbage_collection(self):
        """优化垃圾回收"""
        # 手动触发垃圾回收
        collected = gc.collect()
        
        # 获取垃圾回收统计
        stats = gc.get_stats()
        
        return {
            'collected_objects': collected,
            'gc_stats': stats
        }
    
    def clear_all_caches(self):
        """清空所有缓存"""
        # 清空弱引用缓存
        self.weak_cache.clear()
        
        # 清空延迟加载器
        for loader in self.lazy_loaders.values():
            loader.clear()
        
        # 触发垃圾回收
        self.optimize_garbage_collection()
    
    def get_memory_usage_report(self) -> Dict[str, Any]:
        """获取内存使用报告"""
        current_stats = self.get_memory_stats()
        
        with self._lock:
            if len(self._memory_stats) < 2:
                return {
                    'current': {
                        'total_mb': current_stats.total_memory / 1024 / 1024,
                        'available_mb': current_stats.available_memory / 1024 / 1024,
                        'used_mb': current_stats.used_memory / 1024 / 1024,
                        'process_mb': current_stats.process_memory / 1024 / 1024,
                        'usage_percent': current_stats.memory_percent
                    }
                }
            
            # 计算趋势
            first_stats = self._memory_stats[0]
            last_stats = self._memory_stats[-1]
            
            process_memory_change = last_stats.process_memory - first_stats.process_memory
            
            return {
                'current': {
                    'total_mb': current_stats.total_memory / 1024 / 1024,
                    'available_mb': current_stats.available_memory / 1024 / 1024,
                    'used_mb': current_stats.used_memory / 1024 / 1024,
                    'process_mb': current_stats.process_memory / 1024 / 1024,
                    'usage_percent': current_stats.memory_percent
                },
                'trend': {
                    'process_memory_change_mb': process_memory_change / 1024 / 1024,
                    'samples_count': len(self._memory_stats),
                    'monitoring_duration_minutes': (
                        last_stats.timestamp - first_stats.timestamp
                    ).total_seconds() / 60
                },
                'object_pools': {
                    name: len(pool._pool) for name, pool in self.object_pools.items()
                },
                'lazy_loaders': {
                    name: loader._loaded for name, loader in self.lazy_loaders.items()
                }
            }
    
    def monitor_memory_threshold(self, threshold_percent: float = 80.0) -> bool:
        """监控内存阈值"""
        stats = self.get_memory_stats()
        
        if stats.memory_percent > threshold_percent:
            # 内存使用率过高，执行清理
            self.clear_all_caches()
            return True
        
        return False

# 全局内存优化器实例
_memory_optimizer = None

def get_memory_optimizer() -> MemoryOptimizer:
    """获取全局内存优化器实例"""
    global _memory_optimizer
    if _memory_optimizer is None:
        _memory_optimizer = MemoryOptimizer()
    return _memory_optimizer

def benchmark_memory_performance():
    """内存性能基准测试"""
    print("=== 内存性能基准测试 ===")
    
    optimizer = get_memory_optimizer()
    
    # 获取初始内存状态
    print("1. 初始内存状态:")
    initial_stats = optimizer.get_memory_stats()
    print(f"   系统内存: {initial_stats.total_memory / 1024 / 1024:.1f} MB")
    print(f"   可用内存: {initial_stats.available_memory / 1024 / 1024:.1f} MB")
    print(f"   进程内存: {initial_stats.process_memory / 1024 / 1024:.1f} MB")
    print(f"   使用率: {initial_stats.memory_percent:.1f}%")
    
    # 测试对象池
    print("\n2. 测试对象池:")
    
    class TestObject:
        def __init__(self):
            self.data = [0] * 1000  # 分配一些内存
        
        def reset(self):
            self.data = [0] * 1000
    
    pool = optimizer.get_object_pool('test_objects', TestObject, max_size=50)
    
    # 创建和归还对象
    objects = []
    for i in range(100):
        obj = pool.get_object()
        objects.append(obj)
    
    for obj in objects:
        pool.return_object(obj)
    
    print(f"   对象池大小: {len(pool._pool)}")
    
    # 测试延迟加载
    print("\n3. 测试延迟加载:")
    
    def load_large_data():
        return list(range(10000))  # 模拟大数据加载
    
    lazy_loader = optimizer.create_lazy_loader('large_data', load_large_data)
    print(f"   加载前状态: {lazy_loader._loaded}")
    
    data = lazy_loader.get_data()
    print(f"   加载后状态: {lazy_loader._loaded}")
    print(f"   数据大小: {len(data)}")
    
    # 测试弱引用缓存
    print("\n4. 测试弱引用缓存:")
    
    class CacheableObject:
        def __init__(self, value):
            self.value = value
    
    obj1 = CacheableObject("test1")
    optimizer.weak_cache.set("key1", obj1)
    
    cached_obj = optimizer.weak_cache.get("key1")
    print(f"   缓存命中: {cached_obj is not None}")
    
    # 删除原始引用
    del obj1
    gc.collect()
    
    cached_obj_after_gc = optimizer.weak_cache.get("key1")
    print(f"   GC后缓存: {cached_obj_after_gc is not None}")
    
    # 获取最终内存状态
    print("\n5. 最终内存状态:")
    final_stats = optimizer.get_memory_stats()
    print(f"   进程内存: {final_stats.process_memory / 1024 / 1024:.1f} MB")
    
    memory_change = (final_stats.process_memory - initial_stats.process_memory) / 1024 / 1024
    print(f"   内存变化: {memory_change:+.1f} MB")
    
    # 生成内存报告
    print("\n6. 内存使用报告:")
    report = optimizer.get_memory_usage_report()
    
    current = report['current']
    print(f"   当前使用: {current['process_mb']:.1f} MB")
    print(f"   系统使用率: {current['usage_percent']:.1f}%")
    
    if 'trend' in report:
        trend = report['trend']
        print(f"   内存趋势: {trend['process_memory_change_mb']:+.1f} MB")
    
    # 测试内存阈值监控
    print("\n7. 内存阈值监控:")
    threshold_triggered = optimizer.monitor_memory_threshold(50.0)  # 50%阈值
    print(f"   阈值触发: {threshold_triggered}")

if __name__ == "__main__":
    benchmark_memory_performance()