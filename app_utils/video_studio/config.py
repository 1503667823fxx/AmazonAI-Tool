"""
Configuration Management for Video Studio

This module handles configuration loading, validation, and management for the video studio system.
"""

import os
import json
from pathlib import Path

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum


class ConfigFormat(Enum):
    """Supported configuration file formats"""
    JSON = "json"
    YAML = "yaml"
    ENV = "env"


@dataclass
class ModelConfig:
    """Configuration for AI model adapters"""
    name: str
    api_key: str
    base_url: Optional[str] = None
    timeout: int = 300
    max_retries: int = 3
    rate_limit: Optional[int] = None
    enabled: bool = True
    parameters: Dict[str, Any] = field(default_factory=dict)
    
    def validate(self) -> bool:
        """Validate model configuration"""
        if not self.name or not isinstance(self.name, str):
            return False
        # Only validate API key if the model is enabled
        if self.enabled and (not self.api_key or not isinstance(self.api_key, str)):
            return False
        if self.timeout <= 0:
            return False
        if self.max_retries < 0:
            return False
        return True


@dataclass
class StorageConfig:
    """Configuration for asset storage"""
    base_path: str = "./video_studio_assets"
    temp_path: str = "./video_studio_temp"
    max_file_size_mb: int = 100
    allowed_image_formats: List[str] = field(default_factory=lambda: ["jpg", "jpeg", "png", "webp"])
    allowed_video_formats: List[str] = field(default_factory=lambda: ["mp4", "mov", "avi"])
    cleanup_interval_hours: int = 24
    max_storage_gb: int = 10
    
    def validate(self) -> bool:
        """Validate storage configuration"""
        if not self.base_path or not isinstance(self.base_path, str):
            return False
        if not self.temp_path or not isinstance(self.temp_path, str):
            return False
        if self.max_file_size_mb <= 0:
            return False
        if self.cleanup_interval_hours <= 0:
            return False
        if self.max_storage_gb <= 0:
            return False
        return True


@dataclass
class WorkflowConfig:
    """Configuration for workflow management"""
    max_concurrent_tasks: int = 5
    task_timeout_minutes: int = 30
    checkpoint_interval_seconds: int = 60
    auto_cleanup_completed_tasks: bool = True
    completed_task_retention_hours: int = 48
    enable_progress_notifications: bool = True
    
    def validate(self) -> bool:
        """Validate workflow configuration"""
        if self.max_concurrent_tasks <= 0:
            return False
        if self.task_timeout_minutes <= 0:
            return False
        if self.checkpoint_interval_seconds <= 0:
            return False
        if self.completed_task_retention_hours <= 0:
            return False
        return True


@dataclass
class RenderingConfig:
    """Configuration for video rendering"""
    default_quality: str = "1080p"
    default_aspect_ratio: str = "16:9"
    max_duration_seconds: int = 300
    default_fps: int = 30
    enable_hardware_acceleration: bool = True
    output_formats: List[str] = field(default_factory=lambda: ["mp4", "mov"])
    compression_quality: str = "high"
    
    def validate(self) -> bool:
        """Validate rendering configuration"""
        if self.default_quality not in ["720p", "1080p", "4k"]:
            return False
        if self.default_aspect_ratio not in ["16:9", "9:16", "1:1"]:
            return False
        if self.max_duration_seconds <= 0:
            return False
        if self.default_fps <= 0:
            return False
        if self.compression_quality not in ["low", "medium", "high"]:
            return False
        return True


@dataclass
class VideoStudioConfig:
    """Main configuration class for Video Studio"""
    models: Dict[str, ModelConfig] = field(default_factory=dict)
    storage: StorageConfig = field(default_factory=StorageConfig)
    workflow: WorkflowConfig = field(default_factory=WorkflowConfig)
    rendering: RenderingConfig = field(default_factory=RenderingConfig)
    debug_mode: bool = False
    log_level: str = "INFO"
    
    def validate(self) -> tuple[bool, Optional[str]]:
        """Validate the complete configuration"""
        try:
            # Validate models (only check enabled ones strictly)
            enabled_models = []
            for name, model_config in self.models.items():
                if not model_config.validate():
                    return False, f"Invalid model configuration for '{name}'. Check API key if model is enabled."
                if model_config.enabled:
                    enabled_models.append(name)
            
            # Warn if no models are enabled but don't fail validation
            if not enabled_models:
                # This is a warning condition, not a failure
                pass
            
            # Validate other components
            if not self.storage.validate():
                return False, "Invalid storage configuration"
            
            if not self.workflow.validate():
                return False, "Invalid workflow configuration"
            
            if not self.rendering.validate():
                return False, "Invalid rendering configuration"
            
            # Validate log level
            if self.log_level not in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
                return False, "Invalid log level"
            
            return True, None
        except Exception as e:
            return False, f"Configuration validation error: {str(e)}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        return {
            "models": {name: model.__dict__ for name, model in self.models.items()},
            "storage": self.storage.__dict__,
            "workflow": self.workflow.__dict__,
            "rendering": self.rendering.__dict__,
            "debug_mode": self.debug_mode,
            "log_level": self.log_level
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'VideoStudioConfig':
        """Create configuration from dictionary"""
        models = {}
        for name, model_data in data.get("models", {}).items():
            models[name] = ModelConfig(**model_data)
        
        storage = StorageConfig(**data.get("storage", {}))
        workflow = WorkflowConfig(**data.get("workflow", {}))
        rendering = RenderingConfig(**data.get("rendering", {}))
        
        return cls(
            models=models,
            storage=storage,
            workflow=workflow,
            rendering=rendering,
            debug_mode=data.get("debug_mode", False),
            log_level=data.get("log_level", "INFO")
        )


class ConfigurationManager:
    """Manages configuration loading, saving, and validation"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or self._get_default_config_path()
        self.config: Optional[VideoStudioConfig] = None
        self._env_prefix = "VIDEO_STUDIO_"
    
    def _get_default_config_path(self) -> str:
        """Get default configuration file path"""
        # Look for config file in order of preference
        possible_paths = [
            "./video_studio_config.json",
            "./config/video_studio.json"
        ]
        
        if YAML_AVAILABLE:
            possible_paths.extend([
                "./video_studio_config.yaml",
                "./config/video_studio.yaml",
                os.path.expanduser("~/.video_studio/config.yaml")
            ])
        
        for path in possible_paths:
            if os.path.exists(path):
                return path
        
        # Return default path if none found
        return "./video_studio_config.json"
    
    def load_config(self) -> VideoStudioConfig:
        """Load configuration from file and environment variables"""
        try:
            config = self._load_from_file()
            config = self._override_with_env_vars(config)
            
            # Validate configuration
            is_valid, error_message = config.validate()
            if not is_valid:
                raise ValueError(f"Invalid configuration: {error_message}")
            
            self.config = config
            return config
        except Exception as e:
            # If configuration loading fails, create a minimal working config
            print(f"Warning: Failed to load configuration ({str(e)}), using minimal default config")
            config = self._create_minimal_config()
            self.config = config
            return config
    
    def _create_minimal_config(self) -> VideoStudioConfig:
        """Create a minimal configuration that works without API keys"""
        return VideoStudioConfig(
            models={},  # No models enabled
            storage=StorageConfig(),
            workflow=WorkflowConfig(),
            rendering=RenderingConfig(),
            debug_mode=True,  # Enable debug mode for troubleshooting
            log_level="INFO"
        )
    
    def _load_from_file(self) -> VideoStudioConfig:
        """Load configuration from file"""
        if not os.path.exists(self.config_path):
            # Create default configuration
            return self._create_default_config()
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                if (self.config_path.endswith('.yaml') or self.config_path.endswith('.yml')) and YAML_AVAILABLE:
                    data = yaml.safe_load(f)
                else:
                    data = json.load(f)
            
            return VideoStudioConfig.from_dict(data)
        except Exception as e:
            raise ValueError(f"Failed to load configuration from {self.config_path}: {str(e)}")
    
    def _create_default_config(self) -> VideoStudioConfig:
        """Create default configuration"""
        # Check for API keys and only enable models that have them
        luma_api_key = os.getenv("LUMA_API_KEY", "")
        runway_api_key = os.getenv("RUNWAY_API_KEY", "")
        pika_api_key = os.getenv("PIKA_API_KEY", "")
        
        default_models = {
            "luma": ModelConfig(
                name="luma",
                api_key=luma_api_key,
                base_url="https://api.lumalabs.ai/dream-machine/v1",
                timeout=300,
                max_retries=3,
                enabled=bool(luma_api_key)  # Only enable if API key is available
            ),
            "runway": ModelConfig(
                name="runway",
                api_key=runway_api_key,
                base_url="https://api.runwayml.com/v1",
                timeout=300,
                max_retries=3,
                enabled=bool(runway_api_key)  # Only enable if API key is available
            ),
            "pika": ModelConfig(
                name="pika",
                api_key=pika_api_key,
                base_url="https://api.pika.art/v1",
                timeout=300,
                max_retries=3,
                enabled=bool(pika_api_key)  # Only enable if API key is available
            )
        }
        
        return VideoStudioConfig(
            models=default_models,
            storage=StorageConfig(),
            workflow=WorkflowConfig(),
            rendering=RenderingConfig(),
            debug_mode=False,
            log_level="INFO"
        )
    
    def _override_with_env_vars(self, config: VideoStudioConfig) -> VideoStudioConfig:
        """Override configuration with environment variables and Streamlit secrets"""
        # Try to import streamlit to check for secrets
        try:
            import streamlit as st
            has_streamlit = True
        except ImportError:
            has_streamlit = False
        
        # Override model API keys
        for model_name, model_config in config.models.items():
            env_key = f"{self._env_prefix}{model_name.upper()}_API_KEY"
            simple_key = f"{model_name.upper()}_API_KEY"
            
            # Check environment variables first
            api_key = os.getenv(env_key) or os.getenv(simple_key)
            
            # Check Streamlit secrets if available
            if not api_key and has_streamlit:
                try:
                    api_key = st.secrets.get(simple_key) or st.secrets.get(env_key)
                except:
                    pass
            
            if api_key:
                model_config.api_key = api_key
                model_config.enabled = True  # Enable model if API key is found
        
        # Override other settings
        if os.getenv(f"{self._env_prefix}DEBUG_MODE"):
            config.debug_mode = os.getenv(f"{self._env_prefix}DEBUG_MODE").lower() == "true"
        
        if os.getenv(f"{self._env_prefix}LOG_LEVEL"):
            config.log_level = os.getenv(f"{self._env_prefix}LOG_LEVEL")
        
        if os.getenv(f"{self._env_prefix}MAX_CONCURRENT_TASKS"):
            config.workflow.max_concurrent_tasks = int(os.getenv(f"{self._env_prefix}MAX_CONCURRENT_TASKS"))
        
        if os.getenv(f"{self._env_prefix}STORAGE_BASE_PATH"):
            config.storage.base_path = os.getenv(f"{self._env_prefix}STORAGE_BASE_PATH")
        
        return config
    
    def save_config(self, config: Optional[VideoStudioConfig] = None) -> bool:
        """Save configuration to file"""
        if config is None:
            config = self.config
        
        if config is None:
            return False
        
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            
            with open(self.config_path, 'w', encoding='utf-8') as f:
                if (self.config_path.endswith('.yaml') or self.config_path.endswith('.yml')) and YAML_AVAILABLE:
                    yaml.dump(config.to_dict(), f, default_flow_style=False, indent=2)
                else:
                    json.dump(config.to_dict(), f, indent=2, ensure_ascii=False)
            
            return True
        except Exception:
            return False
    
    def get_model_config(self, model_name: str) -> Optional[ModelConfig]:
        """Get configuration for a specific model"""
        if not self.config:
            return None
        
        return self.config.models.get(model_name)
    
    def add_model_config(self, model_name: str, model_config: ModelConfig) -> bool:
        """Add or update model configuration"""
        if not self.config:
            return False
        
        if not model_config.validate():
            return False
        
        self.config.models[model_name] = model_config
        return True
    
    def remove_model_config(self, model_name: str) -> bool:
        """Remove model configuration"""
        if not self.config or model_name not in self.config.models:
            return False
        
        del self.config.models[model_name]
        return True
    
    def get_enabled_models(self) -> List[str]:
        """Get list of enabled model names"""
        if not self.config:
            return []
        
        return [name for name, config in self.config.models.items() if config.enabled]
    
    def reload_config(self) -> VideoStudioConfig:
        """Reload configuration from file"""
        return self.load_config()
    
    def validate_current_config(self) -> tuple[bool, Optional[str]]:
        """Validate current configuration"""
        if not self.config:
            return False, "No configuration loaded"
        
        return self.config.validate()


# Global configuration manager instance
config_manager = ConfigurationManager()


def get_config() -> VideoStudioConfig:
    """Get the current configuration"""
    if config_manager.config is None:
        config_manager.load_config()
    return config_manager.config


def reload_config() -> VideoStudioConfig:
    """Reload configuration from file"""
    return config_manager.reload_config()


def get_model_config(model_name: str) -> Optional[ModelConfig]:
    """Get configuration for a specific model"""
    return config_manager.get_model_config(model_name)


def get_enabled_models() -> List[str]:
    """Get list of enabled model names"""
    return config_manager.get_enabled_models()
