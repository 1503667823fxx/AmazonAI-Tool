"""
Core data models for Video Studio redesign.

This module contains the fundamental data structures used throughout the video generation workflow,
including configuration models, scene definitions, and task management structures.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any, Callable, Set
import json
from pathlib import Path


class TaskStatus(Enum):
    """Enumeration of possible task states in the video generation workflow."""
    PENDING = "pending"
    PROCESSING = "processing"
    GENERATING = "generating"
    RENDERING = "rendering"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class VideoQuality(Enum):
    """Supported video quality levels."""
    HD_720P = "720p"
    FULL_HD_1080P = "1080p"
    UHD_4K = "4k"


class AspectRatio(Enum):
    """Supported aspect ratios for video output."""
    LANDSCAPE = "16:9"
    PORTRAIT = "9:16"
    SQUARE = "1:1"


class TaskPriority(Enum):
    """Task priority levels for queue management."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4


@dataclass
class AudioConfig:
    """Configuration for audio settings in video generation."""
    enabled: bool = False
    background_music: Optional[str] = None
    volume: float = 0.5
    fade_in: float = 0.0
    fade_out: float = 0.0
    
    def validate(self) -> bool:
        """Validate audio configuration parameters."""
        if not isinstance(self.enabled, bool):
            return False
        if self.volume < 0.0 or self.volume > 1.0:
            return False
        if self.fade_in < 0.0 or self.fade_out < 0.0:
            return False
        return True


@dataclass
class TextOverlay:
    """Configuration for text overlays in video scenes."""
    text: str
    position: str  # "top", "center", "bottom"
    font_size: int = 24
    color: str = "#FFFFFF"
    duration: Optional[float] = None  # If None, shows for entire scene
    
    def validate(self) -> bool:
        """Validate text overlay configuration."""
        if not self.text or not isinstance(self.text, str):
            return False
        if self.position not in ["top", "center", "bottom"]:
            return False
        if self.font_size <= 0:
            return False
        if self.duration is not None and self.duration <= 0:
            return False
        return True


@dataclass
class Scene:
    """Represents a single scene in the video generation workflow."""
    scene_id: str
    visual_prompt: str
    duration: float
    camera_movement: Optional[str] = None
    lighting: Optional[str] = None
    reference_image: Optional[str] = None  # Asset ID
    
    def validate(self) -> bool:
        """Validate scene configuration parameters."""
        if not self.scene_id or not isinstance(self.scene_id, str):
            return False
        if not self.visual_prompt or not isinstance(self.visual_prompt, str):
            return False
        if self.duration <= 0:
            return False
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert scene to dictionary for serialization."""
        return {
            "scene_id": self.scene_id,
            "visual_prompt": self.visual_prompt,
            "duration": self.duration,
            "camera_movement": self.camera_movement,
            "lighting": self.lighting,
            "reference_image": self.reference_image
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Scene':
        """Create Scene instance from dictionary."""
        return cls(
            scene_id=data["scene_id"],
            visual_prompt=data["visual_prompt"],
            duration=data["duration"],
            camera_movement=data.get("camera_movement"),
            lighting=data.get("lighting"),
            reference_image=data.get("reference_image")
        )


@dataclass
class VideoConfig:
    """Main configuration class for video generation requests."""
    template_id: str
    input_images: List[str]  # List of Asset IDs
    duration: int  # Total duration in seconds
    aspect_ratio: AspectRatio
    style: str
    quality: VideoQuality
    audio_config: Optional[AudioConfig] = None
    text_overlays: List[TextOverlay] = field(default_factory=list)
    scenes: List[Scene] = field(default_factory=list)
    
    def validate(self) -> bool:
        """Validate the complete video configuration."""
        # Basic validation
        if not self.template_id or not isinstance(self.template_id, str):
            return False
        if not self.input_images or not isinstance(self.input_images, list):
            return False
        if self.duration <= 0:
            return False
        if not isinstance(self.aspect_ratio, AspectRatio):
            return False
        if not self.style or not isinstance(self.style, str):
            return False
        if not isinstance(self.quality, VideoQuality):
            return False
        
        # Validate nested objects
        if self.audio_config and not self.audio_config.validate():
            return False
        
        for overlay in self.text_overlays:
            if not overlay.validate():
                return False
        
        for scene in self.scenes:
            if not scene.validate():
                return False
        
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary for serialization."""
        return {
            "template_id": self.template_id,
            "input_images": self.input_images,
            "duration": self.duration,
            "aspect_ratio": self.aspect_ratio.value,
            "style": self.style,
            "quality": self.quality.value,
            "audio_config": self.audio_config.__dict__ if self.audio_config else None,
            "text_overlays": [overlay.__dict__ for overlay in self.text_overlays],
            "scenes": [scene.to_dict() for scene in self.scenes]
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'VideoConfig':
        """Create VideoConfig instance from dictionary."""
        audio_config = None
        if data.get("audio_config"):
            audio_config = AudioConfig(**data["audio_config"])
        
        text_overlays = [
            TextOverlay(**overlay_data) 
            for overlay_data in data.get("text_overlays", [])
        ]
        
        scenes = [
            Scene.from_dict(scene_data) 
            for scene_data in data.get("scenes", [])
        ]
        
        return cls(
            template_id=data["template_id"],
            input_images=data["input_images"],
            duration=data["duration"],
            aspect_ratio=AspectRatio(data["aspect_ratio"]),
            style=data["style"],
            quality=VideoQuality(data["quality"]),
            audio_config=audio_config,
            text_overlays=text_overlays,
            scenes=scenes
        )


@dataclass
class TaskInfo:
    """Information about a video generation task."""
    task_id: str
    status: TaskStatus
    progress: float  # 0.0 - 1.0
    created_at: datetime
    updated_at: datetime
    config: Optional[VideoConfig] = None
    result_url: Optional[str] = None
    error_message: Optional[str] = None
    
    def validate(self) -> bool:
        """Validate task information."""
        if not self.task_id or not isinstance(self.task_id, str):
            return False
        if not isinstance(self.status, TaskStatus):
            return False
        if not (0.0 <= self.progress <= 1.0):
            return False
        if not isinstance(self.created_at, datetime):
            return False
        if not isinstance(self.updated_at, datetime):
            return False
        if self.config and not self.config.validate():
            return False
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert task info to dictionary for serialization."""
        return {
            "task_id": self.task_id,
            "status": self.status.value,
            "progress": self.progress,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "config": self.config.to_dict() if self.config else None,
            "result_url": self.result_url,
            "error_message": self.error_message
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TaskInfo':
        """Create TaskInfo instance from dictionary."""
        config = None
        if data.get("config"):
            config = VideoConfig.from_dict(data["config"])
        
        return cls(
            task_id=data["task_id"],
            status=TaskStatus(data["status"]),
            progress=data["progress"],
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            config=config,
            result_url=data.get("result_url"),
            error_message=data.get("error_message")
        )


@dataclass
class TaskContext:
    """Extended context information for task execution."""
    task_info: TaskInfo
    priority: TaskPriority = TaskPriority.NORMAL
    retry_count: int = 0
    max_retries: int = 3
    dependencies: Set[str] = field(default_factory=set)
    callbacks: List[Callable] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ConfigurationManager:
    """Manages configuration validation and serialization for the video studio."""
    
    @staticmethod
    def validate_video_config(config: VideoConfig) -> tuple[bool, Optional[str]]:
        """
        Validate a video configuration and return validation result with error message.
        
        Returns:
            tuple: (is_valid, error_message)
        """
        try:
            if not config.validate():
                return False, "Configuration validation failed"
            
            # Additional business logic validation
            total_scene_duration = sum(scene.duration for scene in config.scenes)
            if config.scenes and abs(total_scene_duration - config.duration) > 1.0:
                return False, f"Scene durations ({total_scene_duration}s) don't match total duration ({config.duration}s)"
            
            return True, None
        except Exception as e:
            return False, f"Validation error: {str(e)}"
    
    @staticmethod
    def save_config(config: VideoConfig, filepath: Path) -> bool:
        """Save configuration to JSON file."""
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(config.to_dict(), f, indent=2, ensure_ascii=False)
            return True
        except Exception:
            return False
    
    @staticmethod
    def load_config(filepath: Path) -> Optional[VideoConfig]:
        """Load configuration from JSON file."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return VideoConfig.from_dict(data)
        except Exception:
            return None