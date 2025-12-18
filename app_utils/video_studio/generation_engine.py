"""
Generation Engine for Video Studio

This module provides the core generation engine that manages model selection,
load balancing, and orchestrates video generation across multiple AI models.
"""

import asyncio
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import json

from .model_adapter import (
    ModelAdapter, 
    GenerationConfig, 
    GenerationResult, 
    JobStatus, 
    ModelCapability,
    model_registry
)
from .config import VideoStudioConfig, get_config
from .error_handler import VideoStudioErrorHandler, VideoStudioErrorType
from .models import Scene


class LoadBalancingStrategy(Enum):
    """Strategies for load balancing across models."""
    ROUND_ROBIN = "round_robin"
    RANDOM = "random"
    LEAST_LOADED = "least_loaded"
    FASTEST_RESPONSE = "fastest_response"
    COST_OPTIMIZED = "cost_optimized"


class ModelSelectionCriteria(Enum):
    """Criteria for automatic model selection."""
    BEST_QUALITY = "best_quality"
    FASTEST = "fastest"
    CHEAPEST = "cheapest"
    MOST_RELIABLE = "most_reliable"
    BEST_FOR_STYLE = "best_for_style"


@dataclass
class ModelMetrics:
    """Metrics tracking for model performance."""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    average_response_time: float = 0.0
    last_request_time: Optional[datetime] = None
    current_load: int = 0
    error_rate: float = 0.0
    
    def update_success(self, response_time: float):
        """Update metrics for successful request."""
        self.total_requests += 1
        self.successful_requests += 1
        self.last_request_time = datetime.now()
        
        # Update average response time
        if self.average_response_time == 0.0:
            self.average_response_time = response_time
        else:
            self.average_response_time = (self.average_response_time * 0.8) + (response_time * 0.2)
        
        self._update_error_rate()
    
    def update_failure(self):
        """Update metrics for failed request."""
        self.total_requests += 1
        self.failed_requests += 1
        self.last_request_time = datetime.now()
        self._update_error_rate()
    
    def _update_error_rate(self):
        """Calculate current error rate."""
        if self.total_requests > 0:
            self.error_rate = self.failed_requests / self.total_requests
    
    def increment_load(self):
        """Increment current load counter."""
        self.current_load += 1
    
    def decrement_load(self):
        """Decrement current load counter."""
        self.current_load = max(0, self.current_load - 1)


@dataclass
class GenerationRequest:
    """Internal representation of a generation request."""
    request_id: str
    config: GenerationConfig
    preferred_model: Optional[str] = None
    fallback_models: List[str] = field(default_factory=list)
    priority: int = 0  # Higher number = higher priority
    created_at: datetime = field(default_factory=datetime.now)
    max_retries: int = 3
    retry_count: int = 0


class GenerationEngine:
    """
    Core generation engine that manages model selection and orchestrates video generation.
    
    Features:
    - Automatic model selection based on configuration and availability
    - Load balancing across multiple models
    - Fallback handling when models fail
    - Performance monitoring and metrics
    - Hot-swappable model configuration
    """
    
    def __init__(self, config: Optional[VideoStudioConfig] = None):
        """
        Initialize the generation engine.
        
        Args:
            config: Video studio configuration (uses global config if None)
        """
        self.config = config or get_config()
        self.error_handler = VideoStudioErrorHandler()
        
        # Model management
        self._adapters: Dict[str, ModelAdapter] = {}
        self._model_metrics: Dict[str, ModelMetrics] = {}
        
        # Load balancing
        self._load_balancing_strategy = LoadBalancingStrategy.LEAST_LOADED
        self._round_robin_index = 0
        
        # Request queue and processing
        self._request_queue: asyncio.Queue = asyncio.Queue()
        self._active_requests: Dict[str, GenerationRequest] = {}
        self._processing_tasks: List[asyncio.Task] = []
        
        # Performance tracking
        self._total_generations = 0
        self._successful_generations = 0
        
        # Initialize with configured models
        self._initialize_adapters()
    
    def _initialize_adapters(self):
        """Initialize model adapters from configuration."""
        from .adapters import LumaAdapter, RunwayAdapter, PikaAdapter
        
        adapter_classes = {
            "luma": LumaAdapter,
            "runway": RunwayAdapter,
            "pika": PikaAdapter
        }
        
        for model_name, model_config in self.config.models.items():
            if model_config.enabled and model_name in adapter_classes:
                try:
                    adapter_class = adapter_classes[model_name]
                    adapter = adapter_class(model_config, self.error_handler)
                    self.register_adapter(adapter)
                except Exception as e:
                    print(f"Failed to initialize {model_name} adapter: {e}")
    
    def register_adapter(self, adapter: ModelAdapter) -> None:
        """
        Register a model adapter.
        
        Args:
            adapter: Model adapter to register
        """
        self._adapters[adapter.name] = adapter
        self._model_metrics[adapter.name] = ModelMetrics()
        model_registry.register(adapter)
    
    def unregister_adapter(self, name: str) -> bool:
        """
        Unregister a model adapter.
        
        Args:
            name: Name of adapter to unregister
            
        Returns:
            True if adapter was found and removed
        """
        if name in self._adapters:
            del self._adapters[name]
            del self._model_metrics[name]
            model_registry.unregister(name)
            return True
        return False
    
    def get_available_models(self) -> List[str]:
        """Get list of available model names."""
        return [name for name, adapter in self._adapters.items() if adapter.enabled]
    
    def get_model_info(self, model_name: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a specific model.
        
        Args:
            model_name: Name of the model
            
        Returns:
            Model information dictionary or None if not found
        """
        if model_name in self._adapters:
            adapter = self._adapters[model_name]
            metrics = self._model_metrics[model_name]
            
            info = adapter.get_model_info()
            info.update({
                "metrics": {
                    "total_requests": metrics.total_requests,
                    "success_rate": 1.0 - metrics.error_rate,
                    "average_response_time": metrics.average_response_time,
                    "current_load": metrics.current_load,
                    "last_request": metrics.last_request_time.isoformat() if metrics.last_request_time else None
                }
            })
            return info
        return None
    
    def set_load_balancing_strategy(self, strategy: LoadBalancingStrategy) -> None:
        """Set the load balancing strategy."""
        self._load_balancing_strategy = strategy
    
    def _select_model_for_config(
        self, 
        config: GenerationConfig, 
        preferred_model: Optional[str] = None
    ) -> Optional[str]:
        """
        Select the best model for a given configuration.
        
        Args:
            config: Generation configuration
            preferred_model: Preferred model name (if any)
            
        Returns:
            Selected model name or None if no suitable model found
        """
        # If preferred model is specified and available, validate it
        if preferred_model and preferred_model in self._adapters:
            adapter = self._adapters[preferred_model]
            if adapter.enabled:
                is_valid, _ = adapter.validate_config(config)
                if is_valid:
                    return preferred_model
        
        # Find all suitable models
        suitable_models = []
        for name, adapter in self._adapters.items():
            if not adapter.enabled:
                continue
            
            is_valid, _ = adapter.validate_config(config)
            if is_valid:
                suitable_models.append(name)
        
        if not suitable_models:
            return None
        
        # Apply load balancing strategy
        return self._apply_load_balancing(suitable_models)
    
    def _apply_load_balancing(self, models: List[str]) -> str:
        """
        Apply load balancing strategy to select from suitable models.
        
        Args:
            models: List of suitable model names
            
        Returns:
            Selected model name
        """
        if len(models) == 1:
            return models[0]
        
        if self._load_balancing_strategy == LoadBalancingStrategy.RANDOM:
            return random.choice(models)
        
        elif self._load_balancing_strategy == LoadBalancingStrategy.ROUND_ROBIN:
            selected = models[self._round_robin_index % len(models)]
            self._round_robin_index += 1
            return selected
        
        elif self._load_balancing_strategy == LoadBalancingStrategy.LEAST_LOADED:
            # Select model with lowest current load
            min_load = float('inf')
            selected_model = models[0]
            
            for model in models:
                load = self._model_metrics[model].current_load
                if load < min_load:
                    min_load = load
                    selected_model = model
            
            return selected_model
        
        elif self._load_balancing_strategy == LoadBalancingStrategy.FASTEST_RESPONSE:
            # Select model with fastest average response time
            min_time = float('inf')
            selected_model = models[0]
            
            for model in models:
                avg_time = self._model_metrics[model].average_response_time
                if avg_time > 0 and avg_time < min_time:
                    min_time = avg_time
                    selected_model = model
            
            return selected_model
        
        else:
            # Default to random
            return random.choice(models)
    
    async def generate_video(
        self, 
        config: GenerationConfig,
        preferred_model: Optional[str] = None,
        priority: int = 0
    ) -> GenerationResult:
        """
        Generate a video using the best available model.
        
        Args:
            config: Generation configuration
            preferred_model: Preferred model name (optional)
            priority: Request priority (higher = more important)
            
        Returns:
            GenerationResult with job information
            
        Raises:
            ValueError: If configuration is invalid
            RuntimeError: If no suitable model is available or generation fails
        """
        # Validate configuration
        if not config.validate():
            raise ValueError("Invalid generation configuration")
        
        # Select model
        selected_model = self._select_model_for_config(config, preferred_model)
        if not selected_model:
            raise RuntimeError("No suitable model available for this configuration")
        
        # Create request
        request_id = f"gen_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{random.randint(1000, 9999)}"
        request = GenerationRequest(
            request_id=request_id,
            config=config,
            preferred_model=selected_model,
            priority=priority
        )
        
        # Execute generation
        return await self._execute_generation(request)
    
    async def _execute_generation(self, request: GenerationRequest) -> GenerationResult:
        """
        Execute a generation request with error handling and retries.
        
        Args:
            request: Generation request to execute
            
        Returns:
            GenerationResult
        """
        model_name = request.preferred_model
        adapter = self._adapters[model_name]
        metrics = self._model_metrics[model_name]
        
        start_time = datetime.now()
        
        try:
            # Update load tracking
            metrics.increment_load()
            self._active_requests[request.request_id] = request
            
            # Execute generation
            result = await adapter.generate(request.config)
            
            # Update success metrics
            response_time = (datetime.now() - start_time).total_seconds()
            metrics.update_success(response_time)
            metrics.decrement_load()
            
            self._total_generations += 1
            self._successful_generations += 1
            
            return result
            
        except Exception as e:
            # Update failure metrics
            metrics.update_failure()
            metrics.decrement_load()
            
            self._total_generations += 1
            
            # Try fallback models if available and retries remaining
            if request.retry_count < request.max_retries:
                request.retry_count += 1
                
                # Find alternative model
                fallback_model = self._select_model_for_config(
                    request.config, 
                    preferred_model=None  # Don't prefer the failed model
                )
                
                if fallback_model and fallback_model != model_name:
                    request.preferred_model = fallback_model
                    await asyncio.sleep(1)  # Brief delay before retry
                    return await self._execute_generation(request)
            
            # Log error and re-raise
            await self.error_handler.handle_error(
                VideoStudioErrorType.GENERATION_ERROR,
                str(e),
                {
                    "model": model_name,
                    "request_id": request.request_id,
                    "retry_count": request.retry_count
                }
            )
            raise RuntimeError(f"Generation failed after {request.retry_count} retries: {str(e)}")
        
        finally:
            # Cleanup
            if request.request_id in self._active_requests:
                del self._active_requests[request.request_id]
    
    async def batch_generate(
        self, 
        scenes: List[Scene],
        base_config: GenerationConfig,
        max_concurrent: Optional[int] = None
    ) -> List[GenerationResult]:
        """
        Generate videos for multiple scenes concurrently.
        
        Args:
            scenes: List of scenes to generate
            base_config: Base configuration to use for all scenes
            max_concurrent: Maximum concurrent generations (uses config default if None)
            
        Returns:
            List of GenerationResults in the same order as input scenes
        """
        if not scenes:
            return []
        
        max_concurrent = max_concurrent or self.config.workflow.max_concurrent_tasks
        
        # Create generation tasks
        async def generate_scene(scene: Scene) -> GenerationResult:
            # Create config for this scene
            scene_config = GenerationConfig(
                prompt=scene.visual_prompt,
                reference_image=scene.reference_image,
                duration=scene.duration,
                aspect_ratio=base_config.aspect_ratio,
                quality=base_config.quality,
                style=base_config.style,
                camera_movement=scene.camera_movement,
                motion_strength=base_config.motion_strength,
                seed=base_config.seed,
                custom_parameters=base_config.custom_parameters
            )
            
            return await self.generate_video(scene_config)
        
        # Execute with concurrency limit
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def limited_generate(scene: Scene) -> GenerationResult:
            async with semaphore:
                return await generate_scene(scene)
        
        # Run all generations
        tasks = [limited_generate(scene) for scene in scenes]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Convert exceptions to failed results
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                final_results.append(GenerationResult(
                    job_id=f"failed_{i}",
                    status=JobStatus.FAILED,
                    error_message=str(result)
                ))
            else:
                final_results.append(result)
        
        return final_results
    
    async def get_job_status(self, job_id: str, model_name: Optional[str] = None) -> GenerationResult:
        """
        Get status of a generation job.
        
        Args:
            job_id: Job identifier
            model_name: Model name (will try all models if None)
            
        Returns:
            GenerationResult with current status
        """
        if model_name and model_name in self._adapters:
            return await self._adapters[model_name].get_status(job_id)
        
        # Try all adapters if model not specified
        for adapter in self._adapters.values():
            try:
                return await adapter.get_status(job_id)
            except:
                continue
        
        raise RuntimeError(f"Job {job_id} not found in any model")
    
    async def cancel_job(self, job_id: str, model_name: Optional[str] = None) -> bool:
        """
        Cancel a generation job.
        
        Args:
            job_id: Job identifier
            model_name: Model name (will try all models if None)
            
        Returns:
            True if cancellation was successful
        """
        if model_name and model_name in self._adapters:
            return await self._adapters[model_name].cancel_job(job_id)
        
        # Try all adapters if model not specified
        for adapter in self._adapters.values():
            try:
                if await adapter.cancel_job(job_id):
                    return True
            except:
                continue
        
        return False
    
    def get_engine_stats(self) -> Dict[str, Any]:
        """
        Get engine performance statistics.
        
        Returns:
            Dictionary containing engine statistics
        """
        success_rate = 0.0
        if self._total_generations > 0:
            success_rate = self._successful_generations / self._total_generations
        
        return {
            "total_generations": self._total_generations,
            "successful_generations": self._successful_generations,
            "success_rate": success_rate,
            "active_requests": len(self._active_requests),
            "available_models": len([a for a in self._adapters.values() if a.enabled]),
            "load_balancing_strategy": self._load_balancing_strategy.value,
            "model_metrics": {
                name: {
                    "total_requests": metrics.total_requests,
                    "success_rate": 1.0 - metrics.error_rate,
                    "current_load": metrics.current_load,
                    "average_response_time": metrics.average_response_time
                }
                for name, metrics in self._model_metrics.items()
            }
        }
    
    async def reload_config(self) -> None:
        """Reload configuration and reinitialize adapters."""
        self.config = get_config()
        
        # Close existing adapters
        for adapter in self._adapters.values():
            if hasattr(adapter, 'close'):
                await adapter.close()
        
        # Clear and reinitialize
        self._adapters.clear()
        self._model_metrics.clear()
        self._initialize_adapters()
    
    async def shutdown(self) -> None:
        """Shutdown the generation engine and cleanup resources."""
        # Cancel all processing tasks
        for task in self._processing_tasks:
            task.cancel()
        
        # Close all adapters
        for adapter in self._adapters.values():
            if hasattr(adapter, 'close'):
                await adapter.close()
        
        # Clear state
        self._adapters.clear()
        self._model_metrics.clear()
        self._active_requests.clear()


# Global generation engine instance
_generation_engine: Optional[GenerationEngine] = None


def get_generation_engine() -> GenerationEngine:
    """Get the global generation engine instance."""
    global _generation_engine
    if _generation_engine is None:
        _generation_engine = GenerationEngine()
    return _generation_engine


async def generate_video(
    config: GenerationConfig,
    preferred_model: Optional[str] = None,
    priority: int = 0
) -> GenerationResult:
    """Generate a video using the global generation engine."""
    engine = get_generation_engine()
    return await engine.generate_video(config, preferred_model, priority)


async def batch_generate_videos(
    scenes: List[Scene],
    base_config: GenerationConfig,
    max_concurrent: Optional[int] = None
) -> List[GenerationResult]:
    """Generate videos for multiple scenes using the global generation engine."""
    engine = get_generation_engine()
    return await engine.batch_generate(scenes, base_config, max_concurrent)