"""
Enhanced A+ Batch Image Generation Service

结合了batch_image_generation_service.py的先进技术，但完全兼容当前新架构的数据结构。
提供并行处理、进度跟踪、质量验证、重试机制等高级功能。
"""

import asyncio
import time
import logging
import threading
from typing import Dict, List, Optional, Any, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from PIL import Image

from .image_service import APlusImageService
from .models import ModuleType, ModulePrompt

logger = logging.getLogger(__name__)


class BatchGenerationMode(Enum):
    """批量生成模式"""
    SEQUENTIAL = "sequential"  # 顺序生成
    PARALLEL = "parallel"     # 并行生成
    MIXED = "mixed"          # 混合模式（部分并行）


class GenerationStatus(Enum):
    """生成状态"""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


@dataclass
class EnhancedBatchProgress:
    """增强的批量生成进度信息"""
    total_modules: int
    completed_modules: int = 0
    failed_modules: int = 0
    current_module: Optional[str] = None
    overall_progress: float = 0.0
    estimated_remaining_time: float = 0.0
    start_time: datetime = field(default_factory=datetime.now)
    module_progress: Dict[str, float] = field(default_factory=dict)
    module_status: Dict[str, GenerationStatus] = field(default_factory=dict)
    error_messages: Dict[str, str] = field(default_factory=dict)
    quality_scores: Dict[str, float] = field(default_factory=dict)
    generation_times: Dict[str, float] = field(default_factory=dict)
    
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
class EnhancedBatchConfig:
    """增强的批量生成配置"""
    final_content: Dict[str, Dict[str, Any]]
    style_theme: Dict[str, Any]
    generation_mode: BatchGenerationMode = BatchGenerationMode.PARALLEL
    max_parallel_jobs: int = 3
    timeout_per_module: int = 120  # seconds
    retry_attempts: int = 2
    quality_threshold: float = 0.7
    enable_validation: bool = True
    enable_quality_enhancement: bool = True
    reference_images: Optional[List[Any]] = None


class EnhancedAPlusBatchService:
    """增强的A+批量图片生成服务 - 兼容当前架构但功能完整"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        初始化增强批量图片生成服务
        
        Args:
            api_key: API密钥
        """
        self.image_service = APlusImageService(api_key)
        
        # 进度回调函数
        self.progress_callbacks: List[Callable[[str, float], None]] = []
        
        # 线程锁用于进度更新
        self._progress_lock = threading.Lock()
        
        # 生成统计
        self.generation_stats = {
            "total_batches": 0,
            "total_modules_generated": 0,
            "successful_generations": 0,
            "failed_generations": 0,
            "average_generation_time": 0.0,
            "average_quality_score": 0.0,
            "success_rate": 0.0,
            "total_time": 0.0
        }
        
        # 模块复杂度映射（用于混合模式）
        self.module_complexity = {
            "product_overview": "simple",
            "feature_analysis": "complex",
            "specification_comparison": "medium",
            "usage_scenarios": "medium",
            "problem_solution": "complex",
            "material_craftsmanship": "complex",
            "installation_guide": "complex",
            "size_compatibility": "simple",
            "package_contents": "simple",
            "quality_assurance": "medium",
            "customer_reviews": "medium",
            "maintenance_care": "medium"
        }
    
    def generate_batch_sync(
        self,
        final_content: Dict[str, Dict[str, Any]],
        style_theme: Dict[str, Any],
        progress_callback: Optional[Callable[[str, float], None]] = None,
        generation_mode: BatchGenerationMode = BatchGenerationMode.PARALLEL,
        max_parallel_jobs: int = 3,
        retry_attempts: int = 2,
        quality_threshold: float = 0.7
    ) -> Dict[str, Dict[str, Any]]:
        """
        同步批量生成图片 - 兼容Streamlit环境，但功能增强
        
        Args:
            final_content: 最终内容数据 (当前格式)
            style_theme: 风格主题数据 (当前格式)
            progress_callback: 进度回调函数 (module_name, progress)
            generation_mode: 生成模式
            max_parallel_jobs: 最大并行任务数
            retry_attempts: 重试次数
            quality_threshold: 质量阈值
            
        Returns:
            生成结果字典 (当前期望格式)
        """
        logger.info(f"Starting enhanced batch generation for {len(final_content)} modules")
        
        # 创建增强配置
        config = EnhancedBatchConfig(
            final_content=final_content,
            style_theme=style_theme,
            generation_mode=generation_mode,
            max_parallel_jobs=max_parallel_jobs,
            retry_attempts=retry_attempts,
            quality_threshold=quality_threshold
        )
        
        # 添加进度回调
        if progress_callback:
            self.progress_callbacks.append(progress_callback)
        
        try:
            # 在新的事件循环中运行异步批量生成
            results = self._run_async_batch_generation(config)
            
            # 更新统计信息
            self._update_generation_stats(results)
            
            logger.info(f"Enhanced batch generation completed: {len([r for r in results.values() if r.get('success', False)])}/{len(results)} successful")
            return results
            
        except Exception as e:
            logger.error(f"Enhanced batch generation failed: {str(e)}")
            # 返回失败结果
            return {module_key: self._create_failed_result(str(e)) 
                   for module_key in final_content.keys()}
        finally:
            # 移除进度回调
            if progress_callback and progress_callback in self.progress_callbacks:
                self.progress_callbacks.remove(progress_callback)
    
    def _run_async_batch_generation(self, config: EnhancedBatchConfig) -> Dict[str, Dict[str, Any]]:
        """
        在新的事件循环中运行异步批量生成
        
        Args:
            config: 批量生成配置
            
        Returns:
            生成结果字典
        """
        # 创建新的事件循环
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            return loop.run_until_complete(self._generate_batch_async(config))
        finally:
            loop.close()
    
    async def _generate_batch_async(self, config: EnhancedBatchConfig) -> Dict[str, Dict[str, Any]]:
        """
        异步批量生成核心逻辑
        
        Args:
            config: 批量生成配置
            
        Returns:
            生成结果字典
        """
        # 初始化进度跟踪
        progress = EnhancedBatchProgress(
            total_modules=len(config.final_content)
        )
        
        # 初始化模块状态
        for module_key in config.final_content.keys():
            progress.module_status[module_key] = GenerationStatus.NOT_STARTED
            progress.module_progress[module_key] = 0.0
        
        self._notify_progress_callbacks("开始生成", 0.0)
        
        # 根据生成模式选择处理方式
        if config.generation_mode == BatchGenerationMode.SEQUENTIAL:
            results = await self._generate_sequential(config, progress)
        elif config.generation_mode == BatchGenerationMode.PARALLEL:
            results = await self._generate_parallel(config, progress)
        else:  # MIXED
            results = await self._generate_mixed(config, progress)
        
        # 质量检查和重试
        if config.retry_attempts > 0:
            results = await self._retry_failed_modules(results, config, progress)
        
        # 质量增强
        if config.enable_quality_enhancement:
            results = await self._enhance_quality(results, config, progress)
        
        # 最终进度更新
        self._notify_progress_callbacks("完成", 1.0)
        
        return results
    
    async def _generate_sequential(
        self, 
        config: EnhancedBatchConfig, 
        progress: EnhancedBatchProgress
    ) -> Dict[str, Dict[str, Any]]:
        """
        顺序生成模块图片
        
        Args:
            config: 生成配置
            progress: 进度跟踪
            
        Returns:
            生成结果字典
        """
        results = {}
        
        for i, (module_key, content_data) in enumerate(config.final_content.items()):
            logger.info(f"Generating module {i+1}/{len(config.final_content)}: {module_key}")
            
            # 更新当前模块
            progress.current_module = module_key
            progress.module_status[module_key] = GenerationStatus.IN_PROGRESS
            self._notify_progress_callbacks(module_key, i / len(config.final_content))
            
            try:
                # 生成单个模块
                result = await self._generate_single_module_async(
                    module_key, 
                    content_data,
                    config.style_theme,
                    config.timeout_per_module
                )
                
                results[module_key] = result
                
                # 更新进度
                if result.get('success', False):
                    progress.completed_modules += 1
                    progress.module_status[module_key] = GenerationStatus.COMPLETED
                    progress.quality_scores[module_key] = result.get('quality_score', 0.0)
                else:
                    progress.failed_modules += 1
                    progress.module_status[module_key] = GenerationStatus.FAILED
                    progress.error_messages[module_key] = result.get('error', 'Generation failed')
                
                progress.module_progress[module_key] = 1.0
                progress.generation_times[module_key] = result.get('generation_time', 0.0)
                progress.update_progress()
                
            except Exception as e:
                logger.error(f"Failed to generate module {module_key}: {str(e)}")
                
                results[module_key] = self._create_failed_result(str(e))
                progress.failed_modules += 1
                progress.module_status[module_key] = GenerationStatus.FAILED
                progress.error_messages[module_key] = str(e)
                progress.module_progress[module_key] = 0.0
                progress.update_progress()
        
        return results
    
    async def _generate_parallel(
        self, 
        config: EnhancedBatchConfig, 
        progress: EnhancedBatchProgress
    ) -> Dict[str, Dict[str, Any]]:
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
        for module_key, content_data in config.final_content.items():
            task = self._generate_single_module_with_progress(
                module_key,
                content_data,
                config.style_theme,
                config.timeout_per_module,
                progress
            )
            tasks.append((module_key, task))
        
        # 限制并发数量
        semaphore = asyncio.Semaphore(config.max_parallel_jobs)
        
        async def run_with_semaphore(module_key: str, task):
            async with semaphore:
                return module_key, await task
        
        # 执行并行任务
        parallel_tasks = [run_with_semaphore(module_key, task) for module_key, task in tasks]
        
        # 等待所有任务完成
        completed_count = 0
        for completed_task in asyncio.as_completed(parallel_tasks):
            try:
                module_key, result = await completed_task
                results[module_key] = result
                completed_count += 1
                
                # 更新进度
                with self._progress_lock:
                    if result.get('success', False):
                        progress.completed_modules += 1
                        progress.module_status[module_key] = GenerationStatus.COMPLETED
                        progress.quality_scores[module_key] = result.get('quality_score', 0.0)
                    else:
                        progress.failed_modules += 1
                        progress.module_status[module_key] = GenerationStatus.FAILED
                        progress.error_messages[module_key] = result.get('error', 'Generation failed')
                    
                    progress.module_progress[module_key] = 1.0
                    progress.generation_times[module_key] = result.get('generation_time', 0.0)
                    progress.update_progress()
                    
                    # 通知进度
                    self._notify_progress_callbacks(
                        f"已完成 {completed_count}/{len(config.final_content)}", 
                        completed_count / len(config.final_content)
                    )
                
            except Exception as e:
                logger.error(f"Parallel generation task failed: {str(e)}")
        
        return results
    
    async def _generate_mixed(
        self, 
        config: EnhancedBatchConfig, 
        progress: EnhancedBatchProgress
    ) -> Dict[str, Dict[str, Any]]:
        """
        混合模式生成（根据模块复杂度选择策略）
        
        Args:
            config: 生成配置
            progress: 进度跟踪
            
        Returns:
            生成结果字典
        """
        # 根据复杂度分组模块
        simple_modules = {}
        complex_modules = {}
        
        for module_key, content_data in config.final_content.items():
            complexity = self.module_complexity.get(module_key, "medium")
            if complexity == "simple":
                simple_modules[module_key] = content_data
            else:
                complex_modules[module_key] = content_data
        
        results = {}
        
        # 先并行生成简单模块
        if simple_modules:
            logger.info(f"Generating {len(simple_modules)} simple modules in parallel")
            simple_config = EnhancedBatchConfig(
                final_content=simple_modules,
                style_theme=config.style_theme,
                generation_mode=BatchGenerationMode.PARALLEL,
                max_parallel_jobs=min(config.max_parallel_jobs, len(simple_modules)),
                timeout_per_module=config.timeout_per_module
            )
            
            simple_results = await self._generate_parallel(simple_config, progress)
            results.update(simple_results)
        
        # 再顺序生成复杂模块
        if complex_modules:
            logger.info(f"Generating {len(complex_modules)} complex modules sequentially")
            complex_config = EnhancedBatchConfig(
                final_content=complex_modules,
                style_theme=config.style_theme,
                generation_mode=BatchGenerationMode.SEQUENTIAL,
                timeout_per_module=config.timeout_per_module * 2  # 复杂模块给更多时间
            )
            
            complex_results = await self._generate_sequential(complex_config, progress)
            results.update(complex_results)
        
        return results
    
    async def _generate_single_module_with_progress(
        self,
        module_key: str,
        content_data: Dict[str, Any],
        style_theme: Dict[str, Any],
        timeout: int,
        progress: EnhancedBatchProgress
    ) -> Dict[str, Any]:
        """
        生成单个模块并更新进度
        
        Args:
            module_key: 模块键
            content_data: 内容数据
            style_theme: 风格主题
            timeout: 超时时间
            progress: 进度跟踪
            
        Returns:
            生成结果
        """
        # 更新状态为进行中
        with self._progress_lock:
            progress.module_status[module_key] = GenerationStatus.IN_PROGRESS
        
        try:
            result = await self._generate_single_module_async(
                module_key, content_data, style_theme, timeout
            )
            return result
            
        except Exception as e:
            logger.error(f"Failed to generate module {module_key}: {str(e)}")
            return self._create_failed_result(str(e))
    
    async def _generate_single_module_async(
        self,
        module_key: str,
        content_data: Dict[str, Any],
        style_theme: Dict[str, Any],
        timeout: int
    ) -> Dict[str, Any]:
        """
        异步生成单个模块图片
        
        Args:
            module_key: 模块键
            content_data: 内容数据
            style_theme: 风格主题
            timeout: 超时时间
            
        Returns:
            生成结果字典
        """
        start_time = time.time()
        
        try:
            # 转换模块类型
            module_type = self._convert_module_key(module_key)
            if not module_type:
                return self._create_failed_result(f"Unknown module type: {module_key}")
            
            # 构建增强的提示词
            prompt = self._build_enhanced_module_prompt(module_type, content_data, style_theme)
            
            # 创建ModulePrompt对象
            module_prompt = ModulePrompt(
                module_type=module_type,
                base_prompt=prompt,
                style_modifiers=self._extract_style_modifiers(style_theme),
                technical_requirements=[
                    "600x450 pixels (4:3 aspect ratio)",
                    "High resolution for Amazon A+ pages",
                    "Professional e-commerce quality",
                    "Information-dense design",
                    "Product-focused composition",
                    "Clear visual hierarchy",
                    "Optimized for online retail display"
                ],
                aspect_ratio="4:3 aspect ratio, 600x450 pixels"
            )
            
            # 调用图片生成服务
            generation_result = await asyncio.wait_for(
                self.image_service.generate_aplus_image(module_prompt),
                timeout=timeout
            )
            
            generation_time = time.time() - start_time
            
            # 验证和质量评估
            if generation_result.image_data:
                # 使用APlusImageService的内置验证
                try:
                    validation_result = self.image_service.validate_aplus_requirements(generation_result.image_data)
                    
                    # 计算综合质量评分
                    quality_score = self._calculate_quality_score(generation_result, validation_result)
                    
                    return {
                        'image_data': generation_result.image_data,
                        'image_path': generation_result.image_path,
                        'generation_time': generation_time,
                        'quality_score': quality_score,
                        'prompt_used': generation_result.prompt_used,
                        'validation_status': generation_result.validation_status.value if hasattr(generation_result.validation_status, 'value') else str(generation_result.validation_status),
                        'metadata': {
                            **generation_result.metadata,
                            'validation_result': {
                                'is_valid': validation_result.is_valid,
                                'quality_metrics': validation_result.quality_metrics,
                                'issues': validation_result.issues,
                                'suggestions': validation_result.suggestions
                            },
                            'module_complexity': self.module_complexity.get(module_key, "medium"),
                            'generation_timestamp': datetime.now().isoformat()
                        },
                        'success': True
                    }
                except Exception as validation_error:
                    logger.warning(f"Validation failed for module {module_key}: {str(validation_error)}")
                    # 即使验证失败，也返回生成的图片
                    return {
                        'image_data': generation_result.image_data,
                        'image_path': generation_result.image_path,
                        'generation_time': generation_time,
                        'quality_score': generation_result.quality_score,  # 使用原始质量评分
                        'prompt_used': generation_result.prompt_used,
                        'validation_status': generation_result.validation_status.value if hasattr(generation_result.validation_status, 'value') else str(generation_result.validation_status),
                        'metadata': {
                            **generation_result.metadata,
                            'validation_error': str(validation_error),
                            'module_complexity': self.module_complexity.get(module_key, "medium"),
                            'generation_timestamp': datetime.now().isoformat()
                        },
                        'success': True
                    }
            else:
                return self._create_failed_result(
                    generation_result.metadata.get('error', 'Generation failed'),
                    generation_time
                )
                
        except asyncio.TimeoutError:
            generation_time = time.time() - start_time
            logger.error(f"Module {module_key} generation timed out after {timeout}s")
            return self._create_failed_result(
                f"Generation timed out after {timeout} seconds",
                generation_time
            )
        except Exception as e:
            generation_time = time.time() - start_time
            logger.error(f"Module {module_key} generation failed: {str(e)}")
            return self._create_failed_result(str(e), generation_time)
    
    async def _retry_failed_modules(
        self,
        results: Dict[str, Dict[str, Any]],
        config: EnhancedBatchConfig,
        progress: EnhancedBatchProgress
    ) -> Dict[str, Dict[str, Any]]:
        """
        重试失败的模块生成
        
        Args:
            results: 初始生成结果
            config: 生成配置
            progress: 进度跟踪
            
        Returns:
            重试后的结果
        """
        failed_modules = {k: v for k, v in results.items() if not v.get('success', False)}
        
        if not failed_modules:
            return results
        
        logger.info(f"Retrying {len(failed_modules)} failed modules")
        
        for attempt in range(config.retry_attempts):
            if not failed_modules:
                break
                
            logger.info(f"Retry attempt {attempt + 1}/{config.retry_attempts}")
            
            retry_results = {}
            for module_key, failed_result in list(failed_modules.items()):
                # 更新状态为重试中
                progress.module_status[module_key] = GenerationStatus.RETRYING
                self._notify_progress_callbacks(f"重试 {module_key}", progress.overall_progress)
                
                try:
                    # 等待一段时间再重试
                    if attempt > 0:
                        await asyncio.sleep(2.0 * (attempt + 1))  # 递增等待时间
                    
                    # 重新生成
                    result = await self._generate_single_module_async(
                        module_key,
                        config.final_content[module_key],
                        config.style_theme,
                        config.timeout_per_module
                    )
                    
                    # 如果生成成功，更新结果并从失败列表中移除
                    if result.get('success', False):
                        retry_results[module_key] = result
                        failed_modules.pop(module_key)
                        progress.module_status[module_key] = GenerationStatus.COMPLETED
                        progress.completed_modules += 1
                        progress.failed_modules -= 1
                        logger.info(f"Retry successful for module: {module_key}")
                    else:
                        retry_results[module_key] = result
                        
                except Exception as e:
                    logger.warning(f"Retry attempt {attempt + 1} failed for {module_key}: {str(e)}")
                    retry_results[module_key] = self._create_failed_result(str(e))
            
            # 更新结果
            results.update(retry_results)
        
        # 标记最终失败的模块
        for module_key in failed_modules:
            progress.module_status[module_key] = GenerationStatus.FAILED
        
        return results
    
    async def _enhance_quality(
        self,
        results: Dict[str, Dict[str, Any]],
        config: EnhancedBatchConfig,
        progress: EnhancedBatchProgress
    ) -> Dict[str, Dict[str, Any]]:
        """
        质量增强处理
        
        Args:
            results: 生成结果
            config: 生成配置
            progress: 进度跟踪
            
        Returns:
            质量增强后的结果
        """
        if not config.enable_quality_enhancement:
            return results
        
        low_quality_modules = {
            k: v for k, v in results.items() 
            if v.get('success', False) and v.get('quality_score', 0.0) < config.quality_threshold
        }
        
        if not low_quality_modules:
            return results
        
        logger.info(f"Enhancing quality for {len(low_quality_modules)} modules")
        
        enhanced_results = {}
        for module_key, result in low_quality_modules.items():
            try:
                self._notify_progress_callbacks(f"质量增强 {module_key}", progress.overall_progress)
                
                # 使用更高质量的提示词重新生成
                enhanced_result = await self._generate_single_module_async(
                    module_key,
                    config.final_content[module_key],
                    config.style_theme,
                    config.timeout_per_module
                )
                
                # 如果增强后质量更好，使用新结果
                if (enhanced_result.get('success', False) and 
                    enhanced_result.get('quality_score', 0.0) > result.get('quality_score', 0.0)):
                    enhanced_results[module_key] = enhanced_result
                    logger.info(f"Quality enhanced for module: {module_key}")
                else:
                    enhanced_results[module_key] = result  # 保持原结果
                    
            except Exception as e:
                logger.warning(f"Quality enhancement failed for {module_key}: {str(e)}")
                enhanced_results[module_key] = result  # 保持原结果
        
        # 更新结果
        results.update(enhanced_results)
        return results
    
    def _convert_module_key(self, module_key: str) -> Optional[ModuleType]:
        """
        转换模块键为ModuleType枚举
        
        Args:
            module_key: 模块键 (字符串)
            
        Returns:
            ModuleType枚举或None
        """
        try:
            # 直接尝试通过值匹配
            for module_type in ModuleType:
                if module_type.value == module_key:
                    return module_type
            
            # 如果直接匹配失败，尝试构造函数
            return ModuleType(module_key)
            
        except (ValueError, AttributeError) as e:
            logger.warning(f"Cannot convert module key '{module_key}' to ModuleType: {str(e)}")
            return None
    
    def _build_enhanced_module_prompt(
        self,
        module_type: ModuleType,
        content_data: Dict[str, Any],
        style_theme: Dict[str, Any]
    ) -> str:
        """
        构建增强的模块专用提示词
        
        Args:
            module_type: 模块类型
            content_data: 内容数据
            style_theme: 风格主题
            
        Returns:
            生成的提示词
        """
        # 提取内容信息
        title = content_data.get('title', '')
        description = content_data.get('description', '')
        key_points = content_data.get('key_points', [])
        
        # 提取风格信息
        theme_name = style_theme.get('theme_name', '现代科技风')
        theme_config = style_theme.get('theme_config', {})
        colors = theme_config.get('colors', ['深蓝色', '白色', '银灰色'])
        style_description = theme_config.get('description', '简洁现代风格')
        
        # 模块特定的增强要求
        module_specific_requirements = self._get_module_specific_requirements(module_type)
        
        # 构建增强提示词
        prompt = f"""
Create a professional, high-quality Amazon A+ page image for the {module_type.value} module.

Content Information:
- Title: {title}
- Description: {description}
- Key Points: {', '.join(key_points[:5])}

Style Requirements:
- Theme: {theme_name}
- Style: {style_description}
- Color Palette: {', '.join(colors[:4])}

Module-Specific Requirements:
{chr(10).join(f"- {req}" for req in module_specific_requirements)}

Technical Specifications:
- Dimensions: 600x450 pixels (4:3 aspect ratio)
- High resolution (300 DPI minimum)
- Professional e-commerce quality
- Clear visual hierarchy with proper typography
- Product-focused composition with balanced layout
- Optimized for Amazon A+ page standards
- Information-dense but not cluttered design
- Clear call-to-action elements where appropriate

Quality Standards:
- Professional photography-style lighting
- Sharp, clear imagery with high contrast
- Consistent branding elements
- Accessible color combinations
- Mobile-responsive design considerations

Create a visually compelling, professional image that effectively communicates the product information while exceeding Amazon A+ quality standards.
        """
        
        return prompt.strip()
    
    def _get_module_specific_requirements(self, module_type: ModuleType) -> List[str]:
        """
        获取模块特定的要求
        
        Args:
            module_type: 模块类型
            
        Returns:
            模块特定要求列表
        """
        requirements_map = {
            ModuleType.PRODUCT_OVERVIEW: [
                "Hero-style layout with prominent product display",
                "Clear product name and key benefit statement",
                "Lifestyle context showing product in use"
            ],
            ModuleType.FEATURE_ANALYSIS: [
                "Detailed feature callouts with annotations",
                "Comparison elements or before/after visuals",
                "Technical diagrams or infographics"
            ],
            ModuleType.SPECIFICATION_COMPARISON: [
                "Clear comparison table or chart format",
                "Highlight competitive advantages",
                "Easy-to-scan technical specifications"
            ],
            ModuleType.USAGE_SCENARIOS: [
                "Multiple use case scenarios",
                "Lifestyle photography or illustrations",
                "Step-by-step usage demonstration"
            ],
            ModuleType.PROBLEM_SOLUTION: [
                "Problem identification with visual cues",
                "Clear solution demonstration",
                "Before and after comparison"
            ],
            ModuleType.MATERIAL_CRAFTSMANSHIP: [
                "Close-up material details",
                "Quality indicators and certifications",
                "Manufacturing process highlights"
            ],
            ModuleType.INSTALLATION_GUIDE: [
                "Step-by-step visual instructions",
                "Required tools and components",
                "Safety warnings and tips"
            ],
            ModuleType.SIZE_COMPATIBILITY: [
                "Size comparison with common objects",
                "Dimensional drawings or diagrams",
                "Compatibility charts or guides"
            ],
            ModuleType.PACKAGE_CONTENTS: [
                "All included items clearly displayed",
                "Organized layout with item labels",
                "Quantity indicators for each item"
            ],
            ModuleType.QUALITY_ASSURANCE: [
                "Quality certifications and badges",
                "Testing process visualization",
                "Warranty and guarantee information"
            ],
            ModuleType.CUSTOMER_REVIEWS: [
                "Review highlights and ratings",
                "Customer photos or testimonials",
                "Trust indicators and social proof"
            ],
            ModuleType.MAINTENANCE_CARE: [
                "Care instruction icons and text",
                "Maintenance schedule or timeline",
                "Cleaning and storage recommendations"
            ]
        }
        
        return requirements_map.get(module_type, [
            "Clear information presentation",
            "Professional product photography",
            "Engaging visual design"
        ])
    
    def _extract_style_modifiers(self, style_theme: Dict[str, Any]) -> List[str]:
        """
        提取风格修饰符
        
        Args:
            style_theme: 风格主题数据
            
        Returns:
            风格修饰符列表
        """
        modifiers = []
        
        theme_name = style_theme.get('theme_name')
        if theme_name:
            modifiers.append(f"Style theme: {theme_name}")
        
        theme_config = style_theme.get('theme_config', {})
        colors = theme_config.get('colors', [])
        if colors:
            modifiers.append(f"Color palette: {', '.join(colors[:4])}")
        
        description = theme_config.get('description')
        if description:
            modifiers.append(f"Design style: {description}")
        
        # 添加高级风格修饰符
        modifiers.extend([
            "Professional e-commerce photography style",
            "High-end product presentation",
            "Amazon A+ page optimized design",
            "Information-rich visual layout"
        ])
        
        return modifiers
    
    def _calculate_quality_score(self, generation_result, validation_result) -> float:
        """
        计算综合质量评分
        
        Args:
            generation_result: 生成结果
            validation_result: 验证结果 (可能为None)
            
        Returns:
            质量评分 (0.0-1.0)
        """
        base_score = generation_result.quality_score
        
        # 如果验证结果存在且有质量指标
        if validation_result and hasattr(validation_result, 'quality_metrics') and validation_result.quality_metrics:
            validation_score = validation_result.quality_metrics.get('overall_quality_score', 0.8)
            # 综合评分：70%生成质量 + 30%验证质量
            combined_score = base_score * 0.7 + validation_score * 0.3
        else:
            # 如果验证失败或不可用，只使用生成质量评分
            combined_score = base_score
        
        # 确保评分在合理范围内
        return max(0.0, min(1.0, combined_score))
    
    def _create_failed_result(self, error_message: str, generation_time: float = 0.0) -> Dict[str, Any]:
        """
        创建失败结果
        
        Args:
            error_message: 错误消息
            generation_time: 生成时间
            
        Returns:
            失败结果字典
        """
        return {
            'image_data': None,
            'image_path': None,
            'generation_time': generation_time,
            'quality_score': 0.0,
            'prompt_used': '',
            'validation_status': 'failed',
            'metadata': {
                'error': error_message,
                'generation_timestamp': datetime.now().isoformat(),
                'failure_reason': 'generation_error'
            },
            'success': False,
            'error': error_message
        }
    
    def _notify_progress_callbacks(self, module_name: str, progress: float):
        """
        通知进度回调
        
        Args:
            module_name: 模块名称
            progress: 进度值
        """
        for callback in self.progress_callbacks:
            try:
                callback(module_name, progress)
            except Exception as e:
                logger.error(f"Progress callback error: {str(e)}")
    
    def _update_generation_stats(self, results: Dict[str, Dict[str, Any]]):
        """
        更新生成统计信息
        
        Args:
            results: 生成结果
        """
        successful = sum(1 for r in results.values() if r.get('success', False))
        failed = len(results) - successful
        total_time = sum(r.get('generation_time', 0.0) for r in results.values())
        total_quality = sum(r.get('quality_score', 0.0) for r in results.values() if r.get('success', False))
        
        self.generation_stats["total_batches"] += 1
        self.generation_stats["total_modules_generated"] += len(results)
        self.generation_stats["successful_generations"] += successful
        self.generation_stats["failed_generations"] += failed
        self.generation_stats["total_time"] += total_time
        
        # 更新平均值
        if self.generation_stats["total_modules_generated"] > 0:
            self.generation_stats["average_generation_time"] = (
                self.generation_stats["total_time"] / self.generation_stats["total_modules_generated"]
            )
            self.generation_stats["success_rate"] = (
                self.generation_stats["successful_generations"] / self.generation_stats["total_modules_generated"]
            )
        
        if successful > 0:
            self.generation_stats["average_quality_score"] = total_quality / successful
    
    def get_generation_stats(self) -> Dict[str, Any]:
        """
        获取生成统计信息
        
        Returns:
            统计信息字典
        """
        stats = self.generation_stats.copy()
        
        # 添加额外的统计信息
        stats.update({
            "total_modules": self.generation_stats["total_modules_generated"],
            "average_generation_time": self.generation_stats["average_generation_time"],
            "total_generation_time": self.generation_stats["total_time"]
        })
        
        return stats
    
    def reset_stats(self):
        """重置统计信息"""
        self.generation_stats = {
            "total_batches": 0,
            "total_modules_generated": 0,
            "successful_generations": 0,
            "failed_generations": 0,
            "average_generation_time": 0.0,
            "average_quality_score": 0.0,
            "success_rate": 0.0,
            "total_time": 0.0
        }
    
    def estimate_batch_time(self, final_content: Dict[str, Dict[str, Any]]) -> float:
        """
        估算批量生成时间
        
        Args:
            final_content: 最终内容数据
            
        Returns:
            估算时间（秒）
        """
        # 基础时间估算（每个模块）
        base_times = {
            "product_overview": 25,
            "feature_analysis": 35,
            "specification_comparison": 30,
            "usage_scenarios": 30,
            "problem_solution": 35,
            "material_craftsmanship": 40,
            "installation_guide": 45,
            "size_compatibility": 25,
            "package_contents": 20,
            "quality_assurance": 25,
            "customer_reviews": 30,
            "maintenance_care": 35
        }
        
        total_time = sum(base_times.get(module_key, 30) for module_key in final_content.keys())
        
        # 考虑并行处理的时间节省
        if len(final_content) > 1:
            parallel_factor = min(3, len(final_content)) / len(final_content)
            total_time *= (1 - parallel_factor * 0.6)  # 并行可节省60%时间
        
        return total_time
    
    def get_module_complexity_info(self) -> Dict[str, str]:
        """
        获取模块复杂度信息
        
        Returns:
            模块复杂度映射
        """
        return self.module_complexity.copy()
