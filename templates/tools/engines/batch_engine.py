#!/usr/bin/env python3
"""
批量操作引擎实现
提供批量操作、进度跟踪、错误处理等功能
"""

import json
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import time

from ..models.operations import (
    BatchOperation, BatchResult, OperationResult, OperationType, OperationStatus
)
from ..models.search import SearchQuery


class ProgressTracker:
    """进度跟踪器"""
    
    def __init__(self, total_items: int):
        self.total_items = total_items
        self.processed_items = 0
        self.successful_items = 0
        self.failed_items = 0
        self.start_time = time.time()
        self.lock = threading.Lock()
        self.callbacks: List[Callable[[Dict[str, Any]], None]] = []
    
    def add_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """添加进度回调"""
        self.callbacks.append(callback)
    
    def update(self, processed: int = 1, successful: bool = True):
        """更新进度"""
        with self.lock:
            self.processed_items += processed
            if successful:
                self.successful_items += processed
            else:
                self.failed_items += processed
            
            # 调用回调
            progress_data = self.get_progress_data()
            for callback in self.callbacks:
                try:
                    callback(progress_data)
                except Exception:
                    pass  # 忽略回调错误
    
    def get_progress_data(self) -> Dict[str, Any]:
        """获取进度数据"""
        elapsed_time = time.time() - self.start_time
        progress_percentage = (self.processed_items / self.total_items * 100) if self.total_items > 0 else 0
        
        # 估算剩余时间
        if self.processed_items > 0:
            avg_time_per_item = elapsed_time / self.processed_items
            remaining_items = self.total_items - self.processed_items
            estimated_remaining_time = avg_time_per_item * remaining_items
        else:
            estimated_remaining_time = 0
        
        return {
            "total_items": self.total_items,
            "processed_items": self.processed_items,
            "successful_items": self.successful_items,
            "failed_items": self.failed_items,
            "progress_percentage": progress_percentage,
            "elapsed_time": elapsed_time,
            "estimated_remaining_time": estimated_remaining_time,
            "success_rate": (self.successful_items / self.processed_items * 100) if self.processed_items > 0 else 0
        }


class BatchEngine:
    """批量操作引擎"""
    
    def __init__(self, templates_root: Path, config_root: Path):
        """初始化批量操作引擎
        
        Args:
            templates_root: 模板根目录
            config_root: 配置根目录
        """
        self.templates_root = templates_root
        self.config_root = config_root
        
        # 操作历史
        self.operation_history: List[BatchResult] = []
        
        # 默认配置
        self.default_max_workers = 4
        self.default_timeout = 300
        
    def execute_batch_operation(self, batch_op: BatchOperation, 
                              progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None) -> BatchResult:
        """执行批量操作
        
        Args:
            batch_op: 批量操作定义
            progress_callback: 进度回调函数
            
        Returns:
            批量操作结果
        """
        # 创建结果对象
        batch_result = BatchResult(batch_operation=batch_op)
        
        # 创建进度跟踪器
        progress_tracker = ProgressTracker(len(batch_op.targets))
        if progress_callback:
            progress_tracker.add_callback(progress_callback)
        
        try:
            # 根据操作类型选择执行方法
            if batch_op.operation_type == OperationType.DELETE:
                self._execute_batch_delete(batch_op, batch_result, progress_tracker)
            elif batch_op.operation_type == OperationType.MOVE:
                self._execute_batch_move(batch_op, batch_result, progress_tracker)
            elif batch_op.operation_type == OperationType.COPY:
                self._execute_batch_copy(batch_op, batch_result, progress_tracker)
            elif batch_op.operation_type == OperationType.UPDATE:
                self._execute_batch_update(batch_op, batch_result, progress_tracker)
            elif batch_op.operation_type == OperationType.VALIDATE:
                self._execute_batch_validate(batch_op, batch_result, progress_tracker)
            else:
                raise ValueError(f"不支持的批量操作类型: {batch_op.operation_type}")
            
            batch_result.mark_completed()
            
        except Exception as e:
            batch_result.overall_status = OperationStatus.FAILED
            batch_result.mark_completed()
            
            # 添加失败结果
            for target in batch_op.targets:
                if not any(r.target == target for r in batch_result.results):
                    error_result = OperationResult(
                        operation_id=str(uuid.uuid4()),
                        operation_type=batch_op.operation_type,
                        target=target
                    )
                    error_result.mark_failed(f"批量操作失败: {e}")
                    batch_result.add_result(error_result)
        
        # 添加到历史记录
        self.operation_history.append(batch_result)
        
        return batch_result
    
    def select_templates_by_query(self, query: SearchQuery) -> List[str]:
        """根据查询条件选择模板
        
        Args:
            query: 搜索查询
            
        Returns:
            模板ID列表
        """
        from .search_engine import SearchEngine
        
        # 创建搜索引擎
        index_root = Path("index")
        search_engine = SearchEngine(self.templates_root, index_root)
        
        # 执行搜索
        results = search_engine.search(query)
        
        return [result.template_id for result in results.results]
    
    def select_templates_by_pattern(self, pattern: str, field: str = "name") -> List[str]:
        """根据模式选择模板
        
        Args:
            pattern: 匹配模式 (支持通配符)
            field: 匹配字段
            
        Returns:
            模板ID列表
        """
        from .search_engine import SearchEngine
        
        # 创建搜索引擎
        index_root = Path("index")
        search_engine = SearchEngine(self.templates_root, index_root)
        
        # 通配符搜索
        results = search_engine.search_by_wildcard(pattern, field)
        
        return [template.get('id', '') for template in results]
    
    def validate_batch_operation(self, batch_op: BatchOperation) -> Tuple[bool, List[str]]:
        """验证批量操作
        
        Args:
            batch_op: 批量操作
            
        Returns:
            (是否有效, 错误列表)
        """
        errors = []
        
        # 检查目标列表
        if not batch_op.targets:
            errors.append("目标列表为空")
        
        # 检查操作类型
        if batch_op.operation_type not in OperationType:
            errors.append(f"无效的操作类型: {batch_op.operation_type}")
        
        # 检查目标是否存在
        missing_targets = []
        for target in batch_op.targets:
            template_path = self._find_template_path(target)
            if not template_path or not template_path.exists():
                missing_targets.append(target)
        
        if missing_targets:
            errors.append(f"以下模板不存在: {', '.join(missing_targets)}")
        
        # 检查操作特定参数
        if batch_op.operation_type == OperationType.MOVE:
            target_category = batch_op.parameters.get('target_category')
            if not target_category:
                errors.append("移动操作需要指定目标分类")
        
        return len(errors) == 0, errors
    
    def estimate_operation_time(self, batch_op: BatchOperation) -> float:
        """估算操作时间
        
        Args:
            batch_op: 批量操作
            
        Returns:
            估算时间(秒)
        """
        # 基础时间估算 (每个操作的平均时间)
        base_times = {
            OperationType.DELETE: 0.5,
            OperationType.MOVE: 1.0,
            OperationType.COPY: 2.0,
            OperationType.UPDATE: 0.8,
            OperationType.VALIDATE: 0.3
        }
        
        base_time = base_times.get(batch_op.operation_type, 1.0)
        total_time = len(batch_op.targets) * base_time
        
        # 并行处理调整
        if batch_op.max_parallel > 1:
            total_time = total_time / min(batch_op.max_parallel, len(batch_op.targets))
        
        return total_time
    
    def get_operation_history(self, limit: int = 10) -> List[BatchResult]:
        """获取操作历史
        
        Args:
            limit: 返回数量限制
            
        Returns:
            操作历史列表
        """
        return self.operation_history[-limit:]
    
    def cancel_operation(self, operation_id: str) -> bool:
        """取消操作 (如果支持)
        
        Args:
            operation_id: 操作ID
            
        Returns:
            是否成功取消
        """
        # 简单实现：标记为取消状态
        # 实际实现需要更复杂的线程控制
        for batch_result in self.operation_history:
            if batch_result.batch_operation.operation_id == operation_id:
                if batch_result.overall_status == OperationStatus.RUNNING:
                    batch_result.overall_status = OperationStatus.CANCELLED
                    return True
        
        return False
    
    def _execute_batch_delete(self, batch_op: BatchOperation, batch_result: BatchResult, 
                            progress_tracker: ProgressTracker):
        """执行批量删除"""
        def delete_template(template_id: str) -> OperationResult:
            result = OperationResult(
                operation_id=str(uuid.uuid4()),
                operation_type=OperationType.DELETE,
                target=template_id
            )
            
            try:
                template_path = self._find_template_path(template_id)
                if not template_path or not template_path.exists():
                    result.mark_failed(f"模板不存在: {template_id}")
                    return result
                
                # 删除模板目录
                shutil.rmtree(template_path)
                
                result.mark_success(f"成功删除模板: {template_id}")
                
            except Exception as e:
                result.mark_failed(f"删除失败: {e}")
            
            return result
        
        # 执行删除操作
        self._execute_parallel_operation(
            batch_op.targets, delete_template, batch_result, progress_tracker, batch_op.max_parallel
        )
    
    def _execute_batch_move(self, batch_op: BatchOperation, batch_result: BatchResult, 
                          progress_tracker: ProgressTracker):
        """执行批量移动"""
        target_category = batch_op.parameters.get('target_category')
        if not target_category:
            raise ValueError("移动操作需要指定目标分类")
        
        def move_template(template_id: str) -> OperationResult:
            result = OperationResult(
                operation_id=str(uuid.uuid4()),
                operation_type=OperationType.MOVE,
                target=template_id
            )
            
            try:
                template_path = self._find_template_path(template_id)
                if not template_path or not template_path.exists():
                    result.mark_failed(f"模板不存在: {template_id}")
                    return result
                
                # 构建目标路径
                target_dir = self.templates_root / "by_category" / target_category
                target_dir.mkdir(parents=True, exist_ok=True)
                target_path = target_dir / template_path.name
                
                # 检查目标是否已存在
                if target_path.exists():
                    result.mark_failed(f"目标位置已存在模板: {target_path}")
                    return result
                
                # 移动模板
                shutil.move(str(template_path), str(target_path))
                
                # 更新配置文件中的分类
                config_path = target_path / "template.json"
                if config_path.exists():
                    self._update_template_category(config_path, target_category)
                
                result.mark_success(f"成功移动模板到分类: {target_category}")
                
            except Exception as e:
                result.mark_failed(f"移动失败: {e}")
            
            return result
        
        # 执行移动操作
        self._execute_parallel_operation(
            batch_op.targets, move_template, batch_result, progress_tracker, batch_op.max_parallel
        )
    
    def _execute_batch_copy(self, batch_op: BatchOperation, batch_result: BatchResult, 
                          progress_tracker: ProgressTracker):
        """执行批量复制"""
        target_category = batch_op.parameters.get('target_category')
        name_suffix = batch_op.parameters.get('name_suffix', '_copy')
        
        def copy_template(template_id: str) -> OperationResult:
            result = OperationResult(
                operation_id=str(uuid.uuid4()),
                operation_type=OperationType.COPY,
                target=template_id
            )
            
            try:
                template_path = self._find_template_path(template_id)
                if not template_path or not template_path.exists():
                    result.mark_failed(f"模板不存在: {template_id}")
                    return result
                
                # 构建目标路径
                new_name = template_path.name + name_suffix
                if target_category:
                    target_dir = self.templates_root / "by_category" / target_category
                else:
                    target_dir = template_path.parent
                
                target_dir.mkdir(parents=True, exist_ok=True)
                target_path = target_dir / new_name
                
                # 检查目标是否已存在
                if target_path.exists():
                    result.mark_failed(f"目标位置已存在模板: {target_path}")
                    return result
                
                # 复制模板
                shutil.copytree(template_path, target_path)
                
                # 更新配置文件
                config_path = target_path / "template.json"
                if config_path.exists():
                    self._update_copied_template_config(config_path, new_name, target_category)
                
                result.mark_success(f"成功复制模板: {new_name}")
                
            except Exception as e:
                result.mark_failed(f"复制失败: {e}")
            
            return result
        
        # 执行复制操作
        self._execute_parallel_operation(
            batch_op.targets, copy_template, batch_result, progress_tracker, batch_op.max_parallel
        )
    
    def _execute_batch_update(self, batch_op: BatchOperation, batch_result: BatchResult, 
                            progress_tracker: ProgressTracker):
        """执行批量更新"""
        updates = batch_op.parameters.get('updates', {})
        if not updates:
            raise ValueError("更新操作需要指定更新内容")
        
        def update_template(template_id: str) -> OperationResult:
            result = OperationResult(
                operation_id=str(uuid.uuid4()),
                operation_type=OperationType.UPDATE,
                target=template_id
            )
            
            try:
                template_path = self._find_template_path(template_id)
                if not template_path or not template_path.exists():
                    result.mark_failed(f"模板不存在: {template_id}")
                    return result
                
                config_path = template_path / "template.json"
                if not config_path.exists():
                    result.mark_failed(f"配置文件不存在: {config_path}")
                    return result
                
                # 加载配置
                with open(config_path, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                
                # 应用更新
                updated_fields = []
                for field, value in updates.items():
                    if field in config_data:
                        old_value = config_data[field]
                        config_data[field] = value
                        updated_fields.append(f"{field}: {old_value} -> {value}")
                    else:
                        config_data[field] = value
                        updated_fields.append(f"{field}: (新增) {value}")
                
                # 更新时间戳
                if 'metadata' not in config_data:
                    config_data['metadata'] = {}
                config_data['metadata']['updated_at'] = datetime.now().isoformat()
                
                # 保存配置
                with open(config_path, 'w', encoding='utf-8') as f:
                    json.dump(config_data, f, ensure_ascii=False, indent=2)
                
                result.mark_success(f"成功更新字段: {', '.join(updated_fields)}")
                
            except Exception as e:
                result.mark_failed(f"更新失败: {e}")
            
            return result
        
        # 执行更新操作
        self._execute_parallel_operation(
            batch_op.targets, update_template, batch_result, progress_tracker, batch_op.max_parallel
        )
    
    def _execute_batch_validate(self, batch_op: BatchOperation, batch_result: BatchResult, 
                              progress_tracker: ProgressTracker):
        """执行批量验证"""
        from ..validators.structure_validator import StructureValidator
        from ..validators.config_validator import ConfigValidator
        from ..validators.image_validator import ImageValidator
        
        # 初始化验证器
        structure_validator = StructureValidator()
        config_validator = ConfigValidator()
        image_validator = ImageValidator()
        
        def validate_template(template_id: str) -> OperationResult:
            result = OperationResult(
                operation_id=str(uuid.uuid4()),
                operation_type=OperationType.VALIDATE,
                target=template_id
            )
            
            try:
                template_path = self._find_template_path(template_id)
                if not template_path or not template_path.exists():
                    result.mark_failed(f"模板不存在: {template_id}")
                    return result
                
                all_errors = []
                
                # 结构验证
                is_valid, errors = structure_validator.validate_template_directory(
                    template_path, validate_images=False, validate_config=False
                )
                if not is_valid:
                    all_errors.extend(errors)
                
                # 配置验证
                config_path = template_path / "template.json"
                if config_path.exists():
                    is_valid, errors = config_validator.validate_config(config_path)
                    if not is_valid:
                        all_errors.extend(errors)
                
                # 图片验证
                image_results = image_validator.validate_template_images(template_path)
                for img_path, (is_valid, errors) in image_results.items():
                    if not is_valid:
                        all_errors.extend(errors)
                
                if all_errors:
                    result.mark_failed(f"验证失败: {len(all_errors)} 个问题")
                    result.details['errors'] = all_errors
                else:
                    result.mark_success("验证通过")
                
            except Exception as e:
                result.mark_failed(f"验证失败: {e}")
            
            return result
        
        # 执行验证操作
        self._execute_parallel_operation(
            batch_op.targets, validate_template, batch_result, progress_tracker, batch_op.max_parallel
        )
    
    def _execute_parallel_operation(self, targets: List[str], operation_func: Callable[[str], OperationResult],
                                  batch_result: BatchResult, progress_tracker: ProgressTracker, 
                                  max_workers: int = 1):
        """执行并行操作"""
        if max_workers <= 1:
            # 串行执行
            for target in targets:
                result = operation_func(target)
                batch_result.add_result(result)
                progress_tracker.update(1, result.success)
        else:
            # 并行执行
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # 提交所有任务
                future_to_target = {executor.submit(operation_func, target): target for target in targets}
                
                # 收集结果
                for future in as_completed(future_to_target):
                    target = future_to_target[future]
                    try:
                        result = future.result()
                        batch_result.add_result(result)
                        progress_tracker.update(1, result.success)
                    except Exception as e:
                        # 创建失败结果
                        error_result = OperationResult(
                            operation_id=str(uuid.uuid4()),
                            operation_type=batch_result.batch_operation.operation_type,
                            target=target
                        )
                        error_result.mark_failed(f"执行异常: {e}")
                        batch_result.add_result(error_result)
                        progress_tracker.update(1, False)
    
    def _find_template_path(self, template_id: str) -> Optional[Path]:
        """查找模板路径"""
        by_category_dir = self.templates_root / "by_category"
        
        if by_category_dir.exists():
            for category_dir in by_category_dir.iterdir():
                if category_dir.is_dir():
                    for template_dir in category_dir.iterdir():
                        if template_dir.is_dir():
                            # 检查目录名
                            if template_dir.name == template_id:
                                return template_dir
                            
                            # 检查配置文件中的ID
                            config_path = template_dir / "template.json"
                            if config_path.exists():
                                try:
                                    with open(config_path, 'r', encoding='utf-8') as f:
                                        config_data = json.load(f)
                                        if config_data.get('id') == template_id:
                                            return template_dir
                                except Exception:
                                    continue
        
        return None
    
    def _update_template_category(self, config_path: Path, new_category: str):
        """更新模板分类"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            config_data['category'] = new_category
            
            # 更新时间戳
            if 'metadata' not in config_data:
                config_data['metadata'] = {}
            config_data['metadata']['updated_at'] = datetime.now().isoformat()
            
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            print(f"更新模板分类失败: {e}")
    
    def _update_copied_template_config(self, config_path: Path, new_name: str, new_category: Optional[str]):
        """更新复制模板的配置"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            # 生成新ID
            config_data['id'] = new_name
            config_data['name'] = config_data.get('name', '') + ' (副本)'
            
            if new_category:
                config_data['category'] = new_category
            
            # 更新时间戳
            if 'metadata' not in config_data:
                config_data['metadata'] = {}
            config_data['metadata']['created_at'] = datetime.now().isoformat()
            config_data['metadata']['updated_at'] = datetime.now().isoformat()
            
            # 重置使用统计
            if 'usage_stats' in config_data.get('metadata', {}):
                config_data['metadata']['usage_stats'] = {
                    'download_count': 0,
                    'usage_count': 0,
                    'rating': None,
                    'feedback_count': 0
                }
            
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            print(f"更新复制模板配置失败: {e}")