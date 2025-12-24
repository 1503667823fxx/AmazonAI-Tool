"""
Batch Image Generation Service for A+ Intelligent Workflow

This service handles batch generation of A+ compliant images with parallel processing,
progress tracking, and result validation. It integrates with existing image generation
services and applies A+ specific prompts and validation.

Requirements covered:
- 9.1: 实现批量图片生成 - 集成现有的图片生成API
- 9.1: 实现批量图片生成 - 应用A+页面专用提示词  
- 9.1: 实现批量图片生成 - 实现并行生成和进度跟踪
- 9.2: 批量生成支持
- 16.1: A+页面专业规范遵守
"""

import asyncio
import time
import logging
from typing import List, Dict, Optional, Any, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

from .models import (
    ModuleType, GenerationResult, GenerationStatus, ValidationStatus,
    IntelligentModuleContent, IntelligentStyleThemeConfig, ModulePrompt
)
from .image_service import APlusImageService
from .aplus_specification_service import AplusSpecificationService
from .image_generation_validation_service import ImageGenerationValidationService, RetryConfig

logger = logging.getLogger(__name__)


class BatchGenerationMode(Enum):
    """批量生成模式"""
    SEQUENTIAL = "sequential"  # 顺序生成
    PARALLEL = "parallel"     # 并行生成
    MIXED = "mixed"          # 混合模式（部分并行）


@dataclass
class BatchGenerationProgress:
    """批量生成进度信息"""
    total_modules: int
    completed_modules: int
    failed_modules: int
    current_module: Optional[ModuleType] = None
    overall_progress: float = 0.0
    estimated_remaining_time: float = 0.0
    start_time: datetime = field(default_factory=datetime.now)
    module_progress: Dict[ModuleType, float] = field(default_factory=dict)
    module_status: Dict[ModuleType, GenerationStatus] = field(default_factory=dict)
    error_messages: Dict[ModuleType, str] = field(default_factory=dict)
    
    def update_progress(self):
        """更新整体进度"""
        if self.total_modules > 0:
            self.overall_progress = (self.completed_modules + self.failed_modules) / self.total_modules
        
        # 计算预估剩余时间
        elapsed_time = (datetime.now() - self.start_time).total_seconds()
        if self.completed_modules > 0 and self.overall_progress > 0:
            total_estimated_time = elapsed_time / self.overall_progress
            self.estimated_remaining_time = max(0, total_estimated_time - elapsed_time)


@dataclass
class BatchGenerationConfig:
    """批量生成配置"""
    modules: List[ModuleType]
    module_contents: Dict[ModuleType, IntelligentModuleContent]
    style_theme: IntelligentStyleThemeConfig
    generation_mode: BatchGenerationMode = BatchGenerationMode.PARALLEL
    max_parallel_jobs: int = 3
    timeout_per_module: int = 120  # seconds
    retry_attempts: int = 2
    quality_threshold: float = 0.7
    enable_validation: bool = True
    reference_images: Optional[List[Any]] = None


@dataclass
class BatchGenerationResult:
    """批量生成结果"""
    results: Dict[ModuleType, GenerationResult]
    progress: BatchGenerationProgress
    success_count: int
    failure_count: int
    total_generation_time: float
    average_quality_score: float
    validation_summary: Dict[str, Any]
    completion_timestamp: datetime = field(default_factory=datetime.now)
    
    @property
    def success_rate(self) -> float:
        """成功率"""
        total = self.success_count + self.failure_count
        return self.success_count / total if total > 0 else 0.0


class BatchImageGenerationService:
    """批量图片生成服务"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        初始化批量图片生成服务
        
        Args:
            api_key: API密钥
        """
        self.image_service = APlusImageService(api_key)
        self.aplus_spec_service = AplusSpecificationService()
        self.validation_service = ImageGenerationValidationService()
        
        # 进度回调函数
        self.progress_callbacks: List[Callable[[BatchGenerationProgress], None]] = []
        
        # 线程锁用于进度更新
        self._progress_lock = threading.Lock()
        
        # 生成统计
        self.generation_stats = {
            "total_batches": 0,
            "total_modules_generated": 0,
            "average_generation_time": 0.0,
            "success_rate": 0.0
        }
    
    def add_progress_callback(self, callback: Callable[[BatchGenerationProgress], None]):
        """
        添加进度回调函数
        
        Args:
            callback: 进度更新回调函数
        """
        self.progress_callbacks.append(callback)
    
    def remove_progress_callback(self, callback: Callable[[BatchGenerationProgress], None]):
        """
        移除进度回调函数
        
        Args:
            callback: 要移除的回调函数
        """
        if callback in self.progress_callbacks:
            self.progress_callbacks.remove(callback)
    
    def _notify_progress(self, progress: BatchGenerationProgress):
        """
        通知进度更新
        
        Args:
            progress: 进度信息
        """
        for callback in self.progress_callbacks:
            try:
                callback(progress)
            except Exception as e:
                logger.error(f"Progress callback error: {str(e)}")
    
    async def generate_batch(
        self, 
        config: BatchGenerationConfig,
        progress_callback: Optional[Callable[[BatchGenerationProgress], None]] = None
    ) -> BatchGenerationResult:
        """
        批量生成A+模块图片
        
        Args:
            config: 批量生成配置
            progress_callback: 进度回调函数
            
        Returns:
            批量生成结果
        """
        logger.info(f"Starting batch generation for {len(config.modules)} modules")
        
        # 添加临时进度回调
        if progress_callback:
            self.add_progress_callback(progress_callback)
        
        try:
            # 初始化进度跟踪
            progress = BatchGenerationProgress(
                total_modules=len(config.modules),
                completed_modules=0,
                failed_modules=0
            )
            
            # 初始化模块状态
            for module_type in config.modules:
                progress.module_status[module_type] = GenerationStatus.NOT_STARTED
                progress.module_progress[module_type] = 0.0
            
            self._notify_progress(progress)
            
            # 根据生成模式选择处理方式
            if config.generation_mode == BatchGenerationMode.SEQUENTIAL:
                results = await self._generate_sequential(config, progress)
            elif config.generation_mode == BatchGenerationMode.PARALLEL:
                results = await self._generate_parallel(config, progress)
            else:  # MIXED
                results = await self._generate_mixed(config, progress)
            
            # 计算最终统计
            success_count = sum(1 for result in results.values() 
                              if result.validation_status != ValidationStatus.FAILED)
            failure_count = len(results) - success_count
            
            total_time = sum(result.generation_time for result in results.values())
            avg_quality = (sum(result.quality_score for result in results.values()) 
                          / len(results)) if results else 0.0
            
            # 生成验证摘要
            validation_summary = self._create_validation_summary(results)
            
            # 更新最终进度
            progress.completed_modules = success_count
            progress.failed_modules = failure_count
            progress.update_progress()
            self._notify_progress(progress)
            
            # 更新统计信息
            self._update_generation_stats(len(config.modules), total_time, success_count / len(results))
            
            batch_result = BatchGenerationResult(
                results=results,
                progress=progress,
                success_count=success_count,
                failure_count=failure_count,
                total_generation_time=total_time,
                average_quality_score=avg_quality,
                validation_summary=validation_summary
            )
            
            logger.info(f"Batch generation completed: {success_count}/{len(results)} successful")
            return batch_result
            
        except Exception as e:
            logger.error(f"Batch generation failed: {str(e)}")
            raise
        finally:
            # 移除临时进度回调
            if progress_callback:
                self.remove_progress_callback(progress_callback)
    
    async def _generate_sequential(
        self, 
        config: BatchGenerationConfig, 
        progress: BatchGenerationProgress
    ) -> Dict[ModuleType, GenerationResult]:
        """
        顺序生成模块图片
        
        Args:
            config: 生成配置
            progress: 进度跟踪
            
        Returns:
            生成结果字典
        """
        results = {}
        
        for i, module_type in enumerate(config.modules):
            logger.info(f"Generating module {i+1}/{len(config.modules)}: {module_type.value}")
            
            # 更新当前模块
            progress.current_module = module_type
            progress.module_status[module_type] = GenerationStatus.IN_PROGRESS
            self._notify_progress(progress)
            
            try:
                # 生成单个模块
                result = await self._generate_single_module(
                    module_type, 
                    config.module_contents[module_type],
                    config.style_theme,
                    config.reference_images,
                    config.timeout_per_module
                )
                
                results[module_type] = result
                
                # 更新进度
                if result.validation_status != ValidationStatus.FAILED:
                    progress.completed_modules += 1
                    progress.module_status[module_type] = GenerationStatus.COMPLETED
                else:
                    progress.failed_modules += 1
                    progress.module_status[module_type] = GenerationStatus.FAILED
                    progress.error_messages[module_type] = result.metadata.get("error", "Generation failed")
                
                progress.module_progress[module_type] = 1.0
                progress.update_progress()
                self._notify_progress(progress)
                
            except Exception as e:
                logger.error(f"Failed to generate module {module_type.value}: {str(e)}")
                
                # 创建失败结果
                results[module_type] = GenerationResult(
                    module_type=module_type,
                    image_data=None,
                    image_path=None,
                    prompt_used="",
                    generation_time=0.0,
                    quality_score=0.0,
                    validation_status=ValidationStatus.FAILED,
                    metadata={"error": str(e)}
                )
                
                progress.failed_modules += 1
                progress.module_status[module_type] = GenerationStatus.FAILED
                progress.error_messages[module_type] = str(e)
                progress.module_progress[module_type] = 0.0
                progress.update_progress()
                self._notify_progress(progress)
        
        return results
    
    async def _generate_parallel(
        self, 
        config: BatchGenerationConfig, 
        progress: BatchGenerationProgress
    ) -> Dict[ModuleType, GenerationResult]:
        """
        并行生成模块图片
        
        Args:
            config: 生成配置
            progress: 进度跟踪
            
        Returns:
            生成结果字典
        """
        results = {}
        
        # 创建并行任务
        tasks = []
        for module_type in config.modules:
            task = self._generate_single_module_with_progress(
                module_type,
                config.module_contents[module_type],
                config.style_theme,
                config.reference_images,
                config.timeout_per_module,
                progress
            )
            tasks.append((module_type, task))
        
        # 限制并发数量
        semaphore = asyncio.Semaphore(config.max_parallel_jobs)
        
        async def run_with_semaphore(module_type: ModuleType, task):
            async with semaphore:
                return module_type, await task
        
        # 执行并行任务
        parallel_tasks = [run_with_semaphore(module_type, task) for module_type, task in tasks]
        
        # 等待所有任务完成
        for completed_task in asyncio.as_completed(parallel_tasks):
            try:
                module_type, result = await completed_task
                results[module_type] = result
                
                # 更新进度
                with self._progress_lock:
                    if result.validation_status != ValidationStatus.FAILED:
                        progress.completed_modules += 1
                        progress.module_status[module_type] = GenerationStatus.COMPLETED
                    else:
                        progress.failed_modules += 1
                        progress.module_status[module_type] = GenerationStatus.FAILED
                        progress.error_messages[module_type] = result.metadata.get("error", "Generation failed")
                    
                    progress.module_progress[module_type] = 1.0
                    progress.update_progress()
                    self._notify_progress(progress)
                
            except Exception as e:
                logger.error(f"Parallel generation task failed: {str(e)}")
        
        return results
    
    async def _generate_mixed(
        self, 
        config: BatchGenerationConfig, 
        progress: BatchGenerationProgress
    ) -> Dict[ModuleType, GenerationResult]:
        """
        混合模式生成（部分并行）
        
        Args:
            config: 生成配置
            progress: 进度跟踪
            
        Returns:
            生成结果字典
        """
        # 将模块分组，复杂模块顺序生成，简单模块并行生成
        complex_modules = [
            ModuleType.FEATURE_ANALYSIS,
            ModuleType.INSTALLATION_GUIDE,
            ModuleType.MATERIAL_CRAFTSMANSHIP
        ]
        
        simple_modules = [m for m in config.modules if m not in complex_modules]
        complex_selected = [m for m in config.modules if m in complex_modules]
        
        results = {}
        
        # 先并行生成简单模块
        if simple_modules:
            simple_config = BatchGenerationConfig(
                modules=simple_modules,
                module_contents=config.module_contents,
                style_theme=config.style_theme,
                generation_mode=BatchGenerationMode.PARALLEL,
                max_parallel_jobs=min(config.max_parallel_jobs, len(simple_modules)),
                timeout_per_module=config.timeout_per_module,
                reference_images=config.reference_images
            )
            
            simple_results = await self._generate_parallel(simple_config, progress)
            results.update(simple_results)
        
        # 再顺序生成复杂模块
        if complex_selected:
            complex_config = BatchGenerationConfig(
                modules=complex_selected,
                module_contents=config.module_contents,
                style_theme=config.style_theme,
                generation_mode=BatchGenerationMode.SEQUENTIAL,
                timeout_per_module=config.timeout_per_module,
                reference_images=config.reference_images
            )
            
            complex_results = await self._generate_sequential(complex_config, progress)
            results.update(complex_results)
        
        return results
    
    async def _generate_single_module_with_progress(
        self,
        module_type: ModuleType,
        module_content: IntelligentModuleContent,
        style_theme: IntelligentStyleThemeConfig,
        reference_images: Optional[List[Any]],
        timeout: int,
        progress: BatchGenerationProgress
    ) -> GenerationResult:
        """
        生成单个模块并更新进度
        
        Args:
            module_type: 模块类型
            module_content: 模块内容
            style_theme: 风格主题
            reference_images: 参考图片
            timeout: 超时时间
            progress: 进度跟踪
            
        Returns:
            生成结果
        """
        # 更新状态为进行中
        with self._progress_lock:
            progress.module_status[module_type] = GenerationStatus.IN_PROGRESS
            self._notify_progress(progress)
        
        try:
            result = await self._generate_single_module(
                module_type, module_content, style_theme, reference_images, timeout
            )
            return result
            
        except Exception as e:
            logger.error(f"Failed to generate module {module_type.value}: {str(e)}")
            return GenerationResult(
                module_type=module_type,
                image_data=None,
                image_path=None,
                prompt_used="",
                generation_time=0.0,
                quality_score=0.0,
                validation_status=ValidationStatus.FAILED,
                metadata={"error": str(e)}
            )
    
    async def _generate_single_module(
        self,
        module_type: ModuleType,
        module_content: IntelligentModuleContent,
        style_theme: IntelligentStyleThemeConfig,
        reference_images: Optional[List[Any]],
        timeout: int
    ) -> GenerationResult:
        """
        生成单个模块图片
        
        Args:
            module_type: 模块类型
            module_content: 模块内容
            style_theme: 风格主题
            reference_images: 参考图片
            timeout: 超时时间
            
        Returns:
            生成结果
        """
        try:
            # 生成A+专用提示词
            aplus_prompt = self.aplus_spec_service.generate_module_prompt(
                module_content, style_theme
            )
            
            # 创建模块提示词对象
            module_prompt = ModulePrompt(
                module_type=module_type,
                base_prompt=aplus_prompt,
                style_modifiers=[
                    f"Style theme: {style_theme.theme_name}",
                    f"Color palette: {', '.join(style_theme.color_palette[:3])}",
                    f"Design style: {style_theme.design_style}"
                ],
                technical_requirements=[
                    "600x450 pixels (4:3 aspect ratio)",
                    "High resolution for Amazon A+ pages",
                    "Professional e-commerce quality",
                    "Information-dense design",
                    "Product-focused composition"
                ],
                aspect_ratio="4:3 aspect ratio, 600x450 pixels"
            )
            
            # 调用图片生成服务
            start_time = time.time()
            result = await asyncio.wait_for(
                self.image_service.generate_aplus_image(module_prompt, reference_images),
                timeout=timeout
            )
            generation_time = time.time() - start_time
            
            # 更新生成时间
            result.generation_time = generation_time
            
            # 验证生成结果
            if result.image_data:
                assessment = self.validation_service.validate_generation_result(result, strict_mode=False)
                
                # 更新结果的验证信息
                result.metadata.update({
                    "validation_assessment": {
                        "overall_score": assessment.overall_score,
                        "is_acceptable": assessment.is_acceptable,
                        "issues_count": len(assessment.issues),
                        "recommendations": assessment.recommendations
                    }
                })
                
                # 如果质量不佳，尝试自动修复
                if not assessment.is_acceptable and assessment.issues:
                    auto_fixable_issues = [issue for issue in assessment.issues if issue.auto_fixable]
                    if auto_fixable_issues:
                        logger.info(f"Attempting auto-fix for {len(auto_fixable_issues)} issues")
                        fixed_data = self.validation_service.auto_fix_issues(result.image_data, auto_fixable_issues)
                        if fixed_data:
                            result.image_data = fixed_data
                            result.metadata["auto_fixed"] = True
                            logger.info("Auto-fix applied successfully")
                            
                            # 重新验证修复后的结果
                            fixed_assessment = self.validation_service.validate_generation_result(result, strict_mode=False)
                            result.metadata["validation_assessment"] = {
                                "overall_score": fixed_assessment.overall_score,
                                "is_acceptable": fixed_assessment.is_acceptable,
                                "issues_count": len(fixed_assessment.issues),
                                "recommendations": fixed_assessment.recommendations
                            }
                
                # 更新质量评分
                if "validation_assessment" in result.metadata:
                    result.quality_score = result.metadata["validation_assessment"]["overall_score"]
            
            logger.info(f"Generated module {module_type.value} in {generation_time:.2f}s")
            return result
            
        except asyncio.TimeoutError:
            logger.error(f"Module {module_type.value} generation timed out after {timeout}s")
            return GenerationResult(
                module_type=module_type,
                image_data=None,
                image_path=None,
                prompt_used="",
                generation_time=timeout,
                quality_score=0.0,
                validation_status=ValidationStatus.FAILED,
                metadata={"error": f"Generation timed out after {timeout} seconds"}
            )
        except Exception as e:
            logger.error(f"Module {module_type.value} generation failed: {str(e)}")
            return GenerationResult(
                module_type=module_type,
                image_data=None,
                image_path=None,
                prompt_used="",
                generation_time=0.0,
                quality_score=0.0,
                validation_status=ValidationStatus.FAILED,
                metadata={"error": str(e)}
            )
    
    def _create_validation_summary(self, results: Dict[ModuleType, GenerationResult]) -> Dict[str, Any]:
        """
        创建验证摘要
        
        Args:
            results: 生成结果
            
        Returns:
            验证摘要
        """
        summary = {
            "total_modules": len(results),
            "passed_validation": 0,
            "failed_validation": 0,
            "needs_review": 0,
            "average_quality": 0.0,
            "validation_issues": [],
            "recommendations": []
        }
        
        total_quality = 0.0
        
        for module_type, result in results.items():
            total_quality += result.quality_score
            
            if result.validation_status == ValidationStatus.PASSED:
                summary["passed_validation"] += 1
            elif result.validation_status == ValidationStatus.FAILED:
                summary["failed_validation"] += 1
            else:
                summary["needs_review"] += 1
            
            # 收集验证问题
            if "validation_issues" in result.metadata:
                for issue in result.metadata["validation_issues"]:
                    summary["validation_issues"].append(f"{module_type.value}: {issue}")
            
            # 收集建议
            if "validation_suggestions" in result.metadata:
                for suggestion in result.metadata["validation_suggestions"]:
                    summary["recommendations"].append(f"{module_type.value}: {suggestion}")
        
        summary["average_quality"] = total_quality / len(results) if results else 0.0
        
        return summary
    
    def _update_generation_stats(self, module_count: int, total_time: float, success_rate: float):
        """
        更新生成统计信息
        
        Args:
            module_count: 模块数量
            total_time: 总时间
            success_rate: 成功率
        """
        self.generation_stats["total_batches"] += 1
        self.generation_stats["total_modules_generated"] += module_count
        
        # 更新平均生成时间
        current_avg = self.generation_stats["average_generation_time"]
        total_modules = self.generation_stats["total_modules_generated"]
        self.generation_stats["average_generation_time"] = (
            (current_avg * (total_modules - module_count) + total_time) / total_modules
        )
        
        # 更新成功率
        current_success_rate = self.generation_stats["success_rate"]
        total_batches = self.generation_stats["total_batches"]
        self.generation_stats["success_rate"] = (
            (current_success_rate * (total_batches - 1) + success_rate) / total_batches
        )
    
    def get_generation_stats(self) -> Dict[str, Any]:
        """
        获取生成统计信息
        
        Returns:
            统计信息字典
        """
        return self.generation_stats.copy()
    
    def estimate_batch_time(self, modules: List[ModuleType]) -> float:
        """
        估算批量生成时间
        
        Args:
            modules: 模块列表
            
        Returns:
            估算时间（秒）
        """
        # 基础时间估算（每个模块）
        base_times = {
            ModuleType.PRODUCT_OVERVIEW: 25,
            ModuleType.FEATURE_ANALYSIS: 35,
            ModuleType.SPECIFICATION_COMPARISON: 30,
            ModuleType.USAGE_SCENARIOS: 30,
            ModuleType.PROBLEM_SOLUTION: 35,
            ModuleType.MATERIAL_CRAFTSMANSHIP: 40,
            ModuleType.INSTALLATION_GUIDE: 45,
            ModuleType.SIZE_COMPATIBILITY: 25,
            ModuleType.PACKAGE_CONTENTS: 20,
            ModuleType.QUALITY_ASSURANCE: 25,
            ModuleType.CUSTOMER_REVIEWS: 30,
            ModuleType.MAINTENANCE_CARE: 35
        }
        
        total_time = sum(base_times.get(module, 30) for module in modules)
        
        # 考虑并行处理的时间节省（假设3个并行任务）
        if len(modules) > 1:
            parallel_factor = min(3, len(modules)) / len(modules)
            total_time *= (1 - parallel_factor * 0.6)  # 并行可节省60%时间
        
        return total_time
    
    def cancel_batch_generation(self):
        """
        取消批量生成（如果支持的话）
        """
        # 这里可以实现取消逻辑
        # 由于当前使用的是异步任务，可以通过设置标志位来实现
        logger.info("Batch generation cancellation requested")
        # TODO: 实现取消逻辑
    
    async def retry_failed_modules(
        self,
        failed_results: Dict[ModuleType, GenerationResult],
        config: BatchGenerationConfig,
        retry_config: Optional[RetryConfig] = None
    ) -> Dict[ModuleType, GenerationResult]:
        """
        重试失败的模块生成
        
        Args:
            failed_results: 失败的生成结果
            config: 原始生成配置
            retry_config: 重试配置
            
        Returns:
            重试后的结果
        """
        if not retry_config:
            retry_config = RetryConfig(
                max_attempts=2,
                retry_delay=3.0,
                retry_on_quality_threshold=0.6
            )
        
        logger.info(f"Retrying {len(failed_results)} failed modules")
        
        retry_results = {}
        
        for module_type, failed_result in failed_results.items():
            logger.info(f"Retrying module: {module_type.value}")
            
            # 创建重试生成函数
            async def retry_generation():
                return await self._generate_single_module(
                    module_type,
                    config.module_contents[module_type],
                    config.style_theme,
                    config.reference_images,
                    config.timeout_per_module
                )
            
            # 执行重试
            retry_result = self.validation_service.retry_failed_generation(
                failed_result,
                retry_generation,
                retry_config
            )
            
            if retry_result.success and retry_result.final_result:
                retry_results[module_type] = retry_result.final_result
                logger.info(f"Retry successful for module: {module_type.value}")
            else:
                retry_results[module_type] = failed_result  # 保持原始失败结果
                logger.warning(f"Retry failed for module: {module_type.value}")
        
        return retry_results