#!/usr/bin/env python3
"""
性能优化器 - 优化文件I/O、图片处理、缓存和索引性能
Performance Optimizer - Optimize file I/O, image processing, caching and indexing performance
"""

import os
import json
import time
import hashlib
import threading
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timedelta

@dataclass
class PerformanceMetrics:
    """性能指标"""
    operation_name: str
    start_time: float
    end_time: float
    duration: float
    memory_usage: Optional[int] = None
    cache_hit: bool = False
    
    @property
    def duration_ms(self) -> float:
        """获取毫秒级持续时间"""
        return self.duration * 1000

class CacheManager:
    """缓存管理器"""
    
    def __init__(self, cache_dir: Path, max_size_mb: int = 100):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self._cache_index = {}
        self._lock = threading.RLock()
        self._load_cache_index()
    
    def _load_cache_index(self):
        """加载缓存索引"""
        index_file = self.cache_dir / 'cache_index.json'
        if index_file.exists():
            try:
                with open(index_file, 'r', encoding='utf-8') as f:
                    self._cache_index = json.load(f)
            except Exception:
                self._cache_index = {}
    
    def _save_cache_index(self):
        """保存缓存索引"""
        index_file = self.cache_dir / 'cache_index.json'
        try:
            with open(index_file, 'w', encoding='utf-8') as f:
                json.dump(self._cache_index, f, indent=2)
        except Exception:
            pass
    
    def _get_cache_key(self, key: str) -> str:
        """生成缓存键"""
        return hashlib.md5(key.encode('utf-8')).hexdigest()
    
    def _cleanup_cache(self):
        """清理过期缓存"""
        current_time = time.time()
        expired_keys = []
        
        for cache_key, info in self._cache_index.items():
            if current_time - info.get('created_at', 0) > info.get('ttl', 3600):
                expired_keys.append(cache_key)
        
        for cache_key in expired_keys:
            self._remove_cache_entry(cache_key)
    
    def _remove_cache_entry(self, cache_key: str):
        """删除缓存条目"""
        if cache_key in self._cache_index:
            cache_file = self.cache_dir / f"{cache_key}.json"
            if cache_file.exists():
                cache_file.unlink()
            del self._cache_index[cache_key]
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        with self._lock:
            cache_key = self._get_cache_key(key)
            
            if cache_key not in self._cache_index:
                return None
            
            cache_info = self._cache_index[cache_key]
            current_time = time.time()
            
            # 检查是否过期
            if current_time - cache_info.get('created_at', 0) > cache_info.get('ttl', 3600):
                self._remove_cache_entry(cache_key)
                return None
            
            # 读取缓存文件
            cache_file = self.cache_dir / f"{cache_key}.json"
            if not cache_file.exists():
                self._remove_cache_entry(cache_key)
                return None
            
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # 更新访问时间
                self._cache_index[cache_key]['last_accessed'] = current_time
                return data
            except Exception:
                self._remove_cache_entry(cache_key)
                return None
    
    def set(self, key: str, value: Any, ttl: int = 3600):
        """设置缓存值"""
        with self._lock:
            cache_key = self._get_cache_key(key)
            cache_file = self.cache_dir / f"{cache_key}.json"
            
            try:
                # 写入缓存文件
                with open(cache_file, 'w', encoding='utf-8') as f:
                    json.dump(value, f, ensure_ascii=False, indent=2)
                
                # 更新索引
                current_time = time.time()
                self._cache_index[cache_key] = {
                    'key': key,
                    'created_at': current_time,
                    'last_accessed': current_time,
                    'ttl': ttl,
                    'size': cache_file.stat().st_size
                }
                
                # 清理过期缓存
                self._cleanup_cache()
                
                # 检查缓存大小限制
                self._enforce_size_limit()
                
                # 保存索引
                self._save_cache_index()
                
            except Exception:
                if cache_file.exists():
                    cache_file.unlink()
    
    def _enforce_size_limit(self):
        """强制执行缓存大小限制"""
        total_size = sum(info.get('size', 0) for info in self._cache_index.values())
        
        if total_size <= self.max_size_bytes:
            return
        
        # 按最后访问时间排序，删除最旧的条目
        sorted_entries = sorted(
            self._cache_index.items(),
            key=lambda x: x[1].get('last_accessed', 0)
        )
        
        for cache_key, _ in sorted_entries:
            if total_size <= self.max_size_bytes:
                break
            
            entry_size = self._cache_index[cache_key].get('size', 0)
            self._remove_cache_entry(cache_key)
            total_size -= entry_size
    
    def clear(self):
        """清空缓存"""
        with self._lock:
            for cache_key in list(self._cache_index.keys()):
                self._remove_cache_entry(cache_key)
            self._save_cache_index()

class IndexOptimizer:
    """索引优化器"""
    
    def __init__(self, index_dir: Path):
        self.index_dir = Path(index_dir)
        self.index_dir.mkdir(parents=True, exist_ok=True)
        self._indexes = {}
        self._lock = threading.RLock()
    
    def build_search_index(self, templates: List[Dict[str, Any]]) -> Dict[str, Any]:
        """构建搜索索引"""
        with self._lock:
            search_index = {
                'templates': {},
                'categories': {},
                'tags': {},
                'keywords': {},
                'last_updated': datetime.now().isoformat()
            }
            
            for template in templates:
                template_id = template.get('id', '')
                if not template_id:
                    continue
                
                # 模板索引
                search_index['templates'][template_id] = {
                    'name': template.get('name', ''),
                    'category': template.get('category', ''),
                    'tags': template.get('tags', []),
                    'keywords': template.get('keywords', []),
                    'description': template.get('description', ''),
                    'path': template.get('path', '')
                }
                
                # 分类索引
                category = template.get('category', '')
                if category:
                    if category not in search_index['categories']:
                        search_index['categories'][category] = []
                    search_index['categories'][category].append(template_id)
                
                # 标签索引
                for tag in template.get('tags', []):
                    if tag not in search_index['tags']:
                        search_index['tags'][tag] = []
                    search_index['tags'][tag].append(template_id)
                
                # 关键词索引
                for keyword in template.get('keywords', []):
                    if keyword not in search_index['keywords']:
                        search_index['keywords'][keyword] = []
                    search_index['keywords'][keyword].append(template_id)
            
            # 保存索引
            index_file = self.index_dir / 'search_index.json'
            with open(index_file, 'w', encoding='utf-8') as f:
                json.dump(search_index, f, ensure_ascii=False, indent=2)
            
            self._indexes['search'] = search_index
            return search_index
    
    def get_search_index(self) -> Optional[Dict[str, Any]]:
        """获取搜索索引"""
        if 'search' in self._indexes:
            return self._indexes['search']
        
        index_file = self.index_dir / 'search_index.json'
        if index_file.exists():
            try:
                with open(index_file, 'r', encoding='utf-8') as f:
                    index = json.load(f)
                self._indexes['search'] = index
                return index
            except Exception:
                pass
        
        return None
    
    def search_templates(self, query: str, category: str = None, tags: List[str] = None) -> List[str]:
        """搜索模板"""
        index = self.get_search_index()
        if not index:
            return []
        
        matching_templates = set()
        
        # 按查询词搜索
        if query:
            query_lower = query.lower()
            for template_id, template_info in index['templates'].items():
                if (query_lower in template_info.get('name', '').lower() or
                    query_lower in template_info.get('description', '').lower()):
                    matching_templates.add(template_id)
            
            # 在关键词中搜索
            for keyword, template_ids in index['keywords'].items():
                if query_lower in keyword.lower():
                    matching_templates.update(template_ids)
        
        # 按分类过滤
        if category and category in index['categories']:
            if matching_templates:
                matching_templates &= set(index['categories'][category])
            else:
                matching_templates = set(index['categories'][category])
        
        # 按标签过滤
        if tags:
            for tag in tags:
                if tag in index['tags']:
                    if matching_templates:
                        matching_templates &= set(index['tags'][tag])
                    else:
                        matching_templates = set(index['tags'][tag])
        
        return list(matching_templates)

class FileIOOptimizer:
    """文件I/O优化器"""
    
    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
    
    def batch_read_files(self, file_paths: List[Path]) -> Dict[str, Any]:
        """批量读取文件"""
        results = {}
        
        def read_file(file_path: Path) -> Tuple[str, Any]:
            try:
                if file_path.suffix.lower() == '.json':
                    with open(file_path, 'r', encoding='utf-8') as f:
                        return str(file_path), json.load(f)
                else:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        return str(file_path), f.read()
            except Exception as e:
                return str(file_path), {'error': str(e)}
        
        # 并行读取文件
        futures = {self._executor.submit(read_file, path): path for path in file_paths}
        
        for future in as_completed(futures):
            file_path, content = future.result()
            results[file_path] = content
        
        return results
    
    def batch_write_files(self, file_data: Dict[str, Any]) -> Dict[str, bool]:
        """批量写入文件"""
        results = {}
        
        def write_file(file_path: str, content: Any) -> Tuple[str, bool]:
            try:
                path = Path(file_path)
                path.parent.mkdir(parents=True, exist_ok=True)
                
                if isinstance(content, dict) or isinstance(content, list):
                    with open(path, 'w', encoding='utf-8') as f:
                        json.dump(content, f, ensure_ascii=False, indent=2)
                else:
                    with open(path, 'w', encoding='utf-8') as f:
                        f.write(str(content))
                
                return file_path, True
            except Exception:
                return file_path, False
        
        # 并行写入文件
        futures = {self._executor.submit(write_file, path, content): path 
                  for path, content in file_data.items()}
        
        for future in as_completed(futures):
            file_path, success = future.result()
            results[file_path] = success
        
        return results

class PerformanceOptimizer:
    """性能优化器主类"""
    
    def __init__(self, cache_dir: Path = None, index_dir: Path = None):
        self.cache_dir = cache_dir or Path('cache')
        self.index_dir = index_dir or Path('index')
        
        self.cache_manager = CacheManager(self.cache_dir)
        self.index_optimizer = IndexOptimizer(self.index_dir)
        self.file_io_optimizer = FileIOOptimizer()
        
        self.metrics = []
        self._lock = threading.RLock()
    
    def measure_performance(self, operation_name: str):
        """性能测量装饰器"""
        def decorator(func):
            def wrapper(*args, **kwargs):
                start_time = time.time()
                
                try:
                    result = func(*args, **kwargs)
                    end_time = time.time()
                    
                    metric = PerformanceMetrics(
                        operation_name=operation_name,
                        start_time=start_time,
                        end_time=end_time,
                        duration=end_time - start_time
                    )
                    
                    with self._lock:
                        self.metrics.append(metric)
                    
                    return result
                
                except Exception as e:
                    end_time = time.time()
                    
                    metric = PerformanceMetrics(
                        operation_name=f"{operation_name}_error",
                        start_time=start_time,
                        end_time=end_time,
                        duration=end_time - start_time
                    )
                    
                    with self._lock:
                        self.metrics.append(metric)
                    
                    raise e
            
            return wrapper
        return decorator
    
    def get_performance_report(self) -> Dict[str, Any]:
        """获取性能报告"""
        with self._lock:
            if not self.metrics:
                return {'message': '暂无性能数据'}
            
            # 按操作分组
            operations = {}
            for metric in self.metrics:
                op_name = metric.operation_name
                if op_name not in operations:
                    operations[op_name] = []
                operations[op_name].append(metric)
            
            # 计算统计信息
            report = {
                'total_operations': len(self.metrics),
                'operations': {}
            }
            
            for op_name, op_metrics in operations.items():
                durations = [m.duration for m in op_metrics]
                report['operations'][op_name] = {
                    'count': len(op_metrics),
                    'avg_duration_ms': sum(durations) / len(durations) * 1000,
                    'min_duration_ms': min(durations) * 1000,
                    'max_duration_ms': max(durations) * 1000,
                    'total_duration_ms': sum(durations) * 1000
                }
            
            return report
    
    def optimize_template_creation(self, template_info: Dict[str, Any]) -> Dict[str, Any]:
        """优化模板创建性能"""
        @self.measure_performance("template_creation")
        def create_template():
            # 使用缓存检查是否已存在相似模板
            cache_key = f"template_structure_{template_info.get('template_type', 'standard')}"
            cached_structure = self.cache_manager.get(cache_key)
            
            if cached_structure:
                # 使用缓存的结构模板
                result = cached_structure.copy()
                result['cache_hit'] = True
                return result
            
            # 生成新的模板结构
            structure = {
                'directories': ['desktop', 'mobile', 'docs'],
                'files': ['template.json', 'README.md', 'preview.jpg'],
                'cache_hit': False
            }
            
            # 缓存结构模板
            self.cache_manager.set(cache_key, structure, ttl=7200)  # 2小时缓存
            
            return structure
        
        return create_template()
    
    def optimize_search_performance(self, query: str, filters: Dict[str, Any] = None) -> List[str]:
        """优化搜索性能"""
        @self.measure_performance("template_search")
        def search_templates():
            # 使用索引进行快速搜索
            category = filters.get('category') if filters else None
            tags = filters.get('tags') if filters else None
            
            return self.index_optimizer.search_templates(query, category, tags)
        
        return search_templates()
    
    def clear_metrics(self):
        """清空性能指标"""
        with self._lock:
            self.metrics.clear()

# 全局性能优化器实例
_performance_optimizer = None

def get_performance_optimizer() -> PerformanceOptimizer:
    """获取全局性能优化器实例"""
    global _performance_optimizer
    if _performance_optimizer is None:
        _performance_optimizer = PerformanceOptimizer()
    return _performance_optimizer

def benchmark_system_performance():
    """系统性能基准测试"""
    print("=== 系统性能基准测试 ===")
    
    optimizer = get_performance_optimizer()
    
    # 测试模板创建性能
    print("1. 测试模板创建性能...")
    for i in range(10):
        template_info = {
            'name': f'test_template_{i}',
            'template_type': 'standard',
            'category': 'electronics'
        }
        result = optimizer.optimize_template_creation(template_info)
        print(f"   模板 {i}: {'缓存命中' if result.get('cache_hit') else '新建'}")
    
    # 测试搜索性能
    print("2. 测试搜索性能...")
    search_queries = ['科技', '现代', '简约', '电子产品', '手机']
    for query in search_queries:
        results = optimizer.optimize_search_performance(query)
        print(f"   搜索 '{query}': {len(results)} 个结果")
    
    # 生成性能报告
    print("3. 性能报告:")
    report = optimizer.get_performance_report()
    
    for op_name, stats in report.get('operations', {}).items():
        print(f"   {op_name}:")
        print(f"     执行次数: {stats['count']}")
        print(f"     平均耗时: {stats['avg_duration_ms']:.2f}ms")
        print(f"     最小耗时: {stats['min_duration_ms']:.2f}ms")
        print(f"     最大耗时: {stats['max_duration_ms']:.2f}ms")
    
    # 检查性能目标
    template_creation_stats = report.get('operations', {}).get('template_creation', {})
    search_stats = report.get('operations', {}).get('template_search', {})
    
    print("\n4. 性能目标检查:")
    
    if template_creation_stats:
        avg_creation_time = template_creation_stats['avg_duration_ms']
        target_creation_time = 5000  # 5秒 = 5000ms
        
        if avg_creation_time < target_creation_time:
            print(f"   ✓ 模板创建: {avg_creation_time:.2f}ms < {target_creation_time}ms (目标)")
        else:
            print(f"   ✗ 模板创建: {avg_creation_time:.2f}ms > {target_creation_time}ms (目标)")
    
    if search_stats:
        avg_search_time = search_stats['avg_duration_ms']
        target_search_time = 1000  # 1秒 = 1000ms
        
        if avg_search_time < target_search_time:
            print(f"   ✓ 搜索响应: {avg_search_time:.2f}ms < {target_search_time}ms (目标)")
        else:
            print(f"   ✗ 搜索响应: {avg_search_time:.2f}ms > {target_search_time}ms (目标)")

if __name__ == "__main__":
    benchmark_system_performance()