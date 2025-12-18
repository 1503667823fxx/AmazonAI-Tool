"""
Model Adapter System for Video Studio

This module provides the abstract base class and interfaces for AI model adapters,
enabling unified integration of different video generation models.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional, List, Union
import asyncio
import json
from .models import VideoConfig, Scene
from .config import ModelConfig
from .error_handler import VideoStudioErrorHandler, VideoStudioErrorType


class JobStatus(Enum):
    """Status of a video generation job."""
    PENDING = "pending"
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ModelCapability(Enum):
    """Capabilities supported by different models."""
    IMAGE_TO_VIDEO = "image_to_video"
    TEXT_TO_VIDEO = "text_to_video"
    VIDEO_EXTENSION = "video_extension"
    STYLE_TRANSFER = "style_transfer"
    CAMERA_CONTROL = "camera_control"
    MOTION_CONTROL = "motion_control"


@dataclass
class GenerationConfig:
    """Configuration for video generation requests."""
    prompt: str
    reference_image: Optional[str] = None
    duration: float = 5.0
    aspect_ratio: str = "16:9"
    quality: str = "1080p"
    style: Optional[str] = None
    camera_movement: Optional[str] = None
    motion_strength: float = 0.5
    seed: Optional[int] = None
    custom_parameters: Dict[str, Any] = field(default_factory=dict)
    
    def validate(self) -> bool:
        """Validate generation configuration."""
        if not self.prompt or not isinstance(self.prompt, str):
            return False
        if self.duration <= 0 or self.duration > 300:  # Max 5 minutes
            return False
        if self.aspect_ratio not in ["16:9", "9:16", "1:1"]:
            return False
        if self.quality not in ["720p", "1080p", "4k"]:
            return False
        if not (0.0 <= self.motion_strength <= 1.0):
            return False
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API calls."""
        return {
            "prompt": self.prompt,
            "reference_image": self.reference_image,
            "duration": self.duration,
            "aspect_ratio": self.aspect_ratio,
            "quality": self.quality,
            "style": self.style,
            "camera_movement": self.camera_movement,
            "motion_strength": self.motion_strength,
            "seed": self.seed,
            **self.custom_parameters
        }


@dataclass
class GenerationResult:
    """Result of a video generation request."""
    job_id: str
    status: JobStatus
    video_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    progress: float = 0.0
    estimated_completion: Optional[datetime] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def is_completed(self) -> bool:
        """Check if generation is completed successfully."""
        return self.status == JobStatus.COMPLETED and self.video_url is not None
    
    def is_failed(self) -> bool:
        """Check if generation has failed."""
        return self.status == JobStatus.FAILED
    
    def is_processing(self) -> bool:
        """Check if generation is still in progress."""
        return self.status in [JobStatus.PENDING, JobStatus.QUEUED, JobStatus.PROCESSING]


class ModelAdapter(ABC):
    """
    Abstract base class for AI model adapters.
    
    This class defines the unified interface that all model adapters must implement,
    ensuring consistent behavior across different AI video generation services.
    """
    
    def __init__(self, config: ModelConfig, error_handler: VideoStudioErrorHandler):
        """
        Initialize the model adapter.
        
        Args:
            config: Model configuration containing API keys, endpoints, etc.
            error_handler: Error handler for managing failures and retries
        """
        self.config = config
        self.error_handler = error_handler
        self.name = config.name
        self.enabled = config.enabled
        self._validate_config()
    
    def _validate_config(self) -> None:
        """Validate the model configuration."""
        if not self.config.validate():
            raise ValueError(f"Invalid configuration for model '{self.name}'")
        
        if not self.config.api_key:
            raise ValueError(f"API key required for model '{self.name}'")
    
    @property
    @abstractmethod
    def capabilities(self) -> List[ModelCapability]:
        """Return list of capabilities supported by this model."""
        pass
    
    @property
    @abstractmethod
    def supported_aspect_ratios(self) -> List[str]:
        """Return list of supported aspect ratios."""
        pass
    
    @property
    @abstractmethod
    def supported_qualities(self) -> List[str]:
        """Return list of supported video qualities."""
        pass
    
    @property
    @abstractmethod
    def max_duration(self) -> float:
        """Return maximum supported video duration in seconds."""
        pass
    
    @abstractmethod
    async def generate(self, config: GenerationConfig) -> GenerationResult:
        """
        Start video generation with the given configuration.
        
        Args:
            config: Generation configuration
            
        Returns:
            GenerationResult with job_id and initial status
            
        Raises:
            ValueError: If configuration is invalid
            RuntimeError: If generation fails to start
        """
        pass
    
    @abstractmethod
    async def get_status(self, job_id: str) -> GenerationResult:
        """
        Get the current status of a generation job.
        
        Args:
            job_id: Unique identifier for the generation job
            
        Returns:
            GenerationResult with current status and progress
            
        Raises:
            ValueError: If job_id is invalid
            RuntimeError: If status check fails
        """
        pass
    
    @abstractmethod
    async def cancel_job(self, job_id: str) -> bool:
        """
        Cancel a running generation job.
        
        Args:
            job_id: Unique identifier for the generation job
            
        Returns:
            True if cancellation was successful, False otherwise
        """
        pass
    
    def validate_config(self, config: GenerationConfig) -> tuple[bool, Optional[str]]:
        """
        Validate generation configuration for this specific model.
        
        Args:
            config: Generation configuration to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Basic validation
        if not config.validate():
            return False, "Basic configuration validation failed"
        
        # Model-specific validation
        if config.aspect_ratio not in self.supported_aspect_ratios:
            return False, f"Aspect ratio '{config.aspect_ratio}' not supported by {self.name}"
        
        if config.quality not in self.supported_qualities:
            return False, f"Quality '{config.quality}' not supported by {self.name}"
        
        if config.duration > self.max_duration:
            return False, f"Duration {config.duration}s exceeds maximum {self.max_duration}s for {self.name}"
        
        return True, None
    
    async def wait_for_completion(
        self, 
        job_id: str, 
        timeout: Optional[float] = None,
        poll_interval: float = 5.0
    ) -> GenerationResult:
        """
        Wait for a generation job to complete.
        
        Args:
            job_id: Unique identifier for the generation job
            timeout: Maximum time to wait in seconds (None for no timeout)
            poll_interval: Time between status checks in seconds
            
        Returns:
            Final GenerationResult
            
        Raises:
            asyncio.TimeoutError: If timeout is reached
            RuntimeError: If job fails
        """
        start_time = datetime.now()
        
        while True:
            result = await self.get_status(job_id)
            
            if result.is_completed():
                return result
            
            if result.is_failed():
                error_msg = result.error_message or "Generation failed"
                raise RuntimeError(f"Generation job {job_id} failed: {error_msg}")
            
            # Check timeout
            if timeout is not None:
                elapsed = (datetime.now() - start_time).total_seconds()
                if elapsed >= timeout:
                    raise asyncio.TimeoutError(f"Generation job {job_id} timed out after {timeout}s")
            
            await asyncio.sleep(poll_interval)
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about this model adapter.
        
        Returns:
            Dictionary containing model information
        """
        return {
            "name": self.name,
            "enabled": self.enabled,
            "capabilities": [cap.value for cap in self.capabilities],
            "supported_aspect_ratios": self.supported_aspect_ratios,
            "supported_qualities": self.supported_qualities,
            "max_duration": self.max_duration,
            "config": {
                "timeout": self.config.timeout,
                "max_retries": self.config.max_retries,
                "rate_limit": self.config.rate_limit
            }
        }
    
    def __str__(self) -> str:
        """String representation of the adapter."""
        return f"{self.__class__.__name__}(name='{self.name}', enabled={self.enabled})"
    
    def __repr__(self) -> str:
        """Detailed string representation of the adapter."""
        return (f"{self.__class__.__name__}("
                f"name='{self.name}', "
                f"enabled={self.enabled}, "
                f"capabilities={[cap.value for cap in self.capabilities]})")


class ModelAdapterRegistry:
    """
    Registry for managing model adapters.
    
    Provides centralized registration, discovery, and management of model adapters.
    """
    
    def __init__(self):
        self._adapters: Dict[str, ModelAdapter] = {}
        self._error_handler = VideoStudioErrorHandler()
    
    def register(self, adapter: ModelAdapter) -> None:
        """
        Register a model adapter.
        
        Args:
            adapter: Model adapter instance to register
            
        Raises:
            ValueError: If adapter name already exists
        """
        if adapter.name in self._adapters:
            raise ValueError(f"Model adapter '{adapter.name}' already registered")
        
        self._adapters[adapter.name] = adapter
    
    def unregister(self, name: str) -> bool:
        """
        Unregister a model adapter.
        
        Args:
            name: Name of the adapter to unregister
            
        Returns:
            True if adapter was found and removed, False otherwise
        """
        if name in self._adapters:
            del self._adapters[name]
            return True
        return False
    
    def get_adapter(self, name: str) -> Optional[ModelAdapter]:
        """
        Get a model adapter by name.
        
        Args:
            name: Name of the adapter
            
        Returns:
            Model adapter instance or None if not found
        """
        return self._adapters.get(name)
    
    def list_adapters(self, enabled_only: bool = False) -> List[str]:
        """
        List all registered adapter names.
        
        Args:
            enabled_only: If True, only return enabled adapters
            
        Returns:
            List of adapter names
        """
        if enabled_only:
            return [name for name, adapter in self._adapters.items() if adapter.enabled]
        return list(self._adapters.keys())
    
    def get_adapters_by_capability(self, capability: ModelCapability) -> List[ModelAdapter]:
        """
        Get all adapters that support a specific capability.
        
        Args:
            capability: Required capability
            
        Returns:
            List of adapters supporting the capability
        """
        return [
            adapter for adapter in self._adapters.values()
            if capability in adapter.capabilities and adapter.enabled
        ]
    
    def get_best_adapter_for_config(self, config: GenerationConfig) -> Optional[ModelAdapter]:
        """
        Find the best adapter for a given configuration.
        
        Args:
            config: Generation configuration
            
        Returns:
            Best matching adapter or None if no suitable adapter found
        """
        suitable_adapters = []
        
        for adapter in self._adapters.values():
            if not adapter.enabled:
                continue
            
            is_valid, _ = adapter.validate_config(config)
            if is_valid:
                suitable_adapters.append(adapter)
        
        if not suitable_adapters:
            return None
        
        # For now, return the first suitable adapter
        # In the future, this could implement more sophisticated selection logic
        return suitable_adapters[0]
    
    def get_registry_info(self) -> Dict[str, Any]:
        """
        Get information about all registered adapters.
        
        Returns:
            Dictionary containing registry information
        """
        return {
            "total_adapters": len(self._adapters),
            "enabled_adapters": len([a for a in self._adapters.values() if a.enabled]),
            "adapters": {name: adapter.get_model_info() for name, adapter in self._adapters.items()}
        }


# Global registry instance
model_registry = ModelAdapterRegistry()


def register_adapter(adapter: ModelAdapter) -> None:
    """Register a model adapter in the global registry."""
    model_registry.register(adapter)


def get_adapter(name: str) -> Optional[ModelAdapter]:
    """Get a model adapter from the global registry."""
    return model_registry.get_adapter(name)


def list_adapters(enabled_only: bool = False) -> List[str]:
    """List all registered adapter names."""
    return model_registry.list_adapters(enabled_only)


def get_adapters_by_capability(capability: ModelCapability) -> List[ModelAdapter]:
    """Get all adapters that support a specific capability."""
    return model_registry.get_adapters_by_capability(capability)


def get_best_adapter_for_config(config: GenerationConfig) -> Optional[ModelAdapter]:
    """Find the best adapter for a given configuration."""
    return model_registry.get_best_adapter_for_config(config)