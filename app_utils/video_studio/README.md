# Video Studio - Professional Image-to-Video Workflow System

## Overview

Video Studio is a comprehensive image-to-video generation system that provides a modular, scalable architecture for creating professional marketing videos from product images. The system supports multiple AI models through a unified adapter pattern and includes robust error handling, configuration management, and logging capabilities.

## Architecture

The Video Studio system is built with the following core components:

### Core Data Models (`models.py`)
- **VideoConfig**: Main configuration class for video generation requests
- **Scene**: Represents individual scenes in the video workflow
- **TaskInfo**: Information about video generation tasks
- **TaskStatus**: Enumeration of possible task states
- **AudioConfig**: Configuration for audio settings
- **TextOverlay**: Configuration for text overlays
- **ConfigurationManager**: Manages configuration validation and serialization

### Error Handling System (`error_handler.py`)
- **VideoStudioErrorHandler**: Comprehensive error handler with recovery mechanisms
- **VideoStudioErrorType**: Enumeration of error types specific to video generation
- **Circuit Breaker Pattern**: Prevents cascading failures in model calls
- **Recovery Actions**: Automated and user-guided recovery options
- **Exponential Backoff**: Intelligent retry mechanisms

### Configuration Management (`config.py`)
- **VideoStudioConfig**: Main configuration container
- **ModelConfig**: Configuration for AI model adapters
- **StorageConfig**: Asset storage configuration
- **WorkflowConfig**: Workflow management settings
- **RenderingConfig**: Video rendering parameters
- **Environment Variable Support**: Override configuration with environment variables

### Logging System (`logging_config.py`)
- **VideoStudioLogger**: Centralized logging with structured output
- **Multiple Log Levels**: DEBUG, INFO, WARNING, ERROR, CRITICAL
- **Specialized Loggers**: Separate loggers for models, workflow, assets, and rendering
- **File Rotation**: Automatic log file rotation and cleanup
- **Performance Metrics**: Built-in performance and metric logging

## Project Structure

```
app_utils/video_studio/
├── __init__.py              # Main module exports
├── models.py                # Core data models and validation
├── error_handler.py         # Error handling and recovery system
├── config.py                # Configuration management
├── logging_config.py        # Logging configuration and utilities
├── session_state.py         # Session state management (to be implemented)
├── ui_components.py         # UI components for Streamlit
├── file_manager.py          # File and asset management (to be implemented)
└── README.md               # This documentation
```

## Key Features

### 1. Modular Architecture
- **Plugin-based Design**: Easy to add new AI models and features
- **Separation of Concerns**: Clear boundaries between components
- **Dependency Injection**: Configurable dependencies for testing and flexibility

### 2. Robust Error Handling
- **Comprehensive Error Types**: Specific error types for different failure modes
- **Circuit Breaker Pattern**: Prevents system overload during failures
- **Automatic Recovery**: Intelligent retry mechanisms with exponential backoff
- **User-Friendly Messages**: Clear error messages with recovery suggestions

### 3. Configuration Management
- **Multiple Formats**: Support for JSON and YAML configuration files
- **Environment Variables**: Override configuration with environment variables
- **Validation**: Comprehensive configuration validation with detailed error messages
- **Hot Reload**: Support for configuration updates without system restart

### 4. Comprehensive Logging
- **Structured Logging**: Consistent log format with contextual information
- **Multiple Outputs**: Console and file logging with different levels
- **Performance Tracking**: Built-in performance and metric logging
- **Log Rotation**: Automatic cleanup and rotation of log files

## Usage Examples

### Basic Configuration
```python
from app_utils.video_studio import VideoConfig, AspectRatio, VideoQuality

# Create a video configuration
config = VideoConfig(
    template_id="amazon_minimal",
    input_images=["asset_123", "asset_456"],
    duration=30,
    aspect_ratio=AspectRatio.LANDSCAPE,
    style="Amazon 极简风",
    quality=VideoQuality.FULL_HD_1080P
)

# Validate configuration
is_valid = config.validate()
```

### Error Handling
```python
from app_utils.video_studio import handle_generation_error, VideoStudioErrorType

try:
    # Video generation operation
    result = generate_video(config)
except Exception as e:
    # Handle error with recovery options
    error_info = handle_generation_error(e, context={"task_id": "task_123"})
```

### Configuration Management
```python
from app_utils.video_studio import get_config, get_model_config

# Load configuration
config = get_config()

# Get specific model configuration
luma_config = get_model_config("luma")
```

### Logging
```python
from app_utils.video_studio import get_logger

logger = get_logger("video_studio.workflow")
logger.log_task_start("task_123", "video_generation")
logger.log_task_progress("task_123", 0.5, "Generating scenes")
logger.log_task_complete("task_123", 45.2, {"output_url": "https://..."})
```

## Environment Variables

The system supports the following environment variables for configuration:

- `VIDEO_STUDIO_LUMA_API_KEY`: API key for Luma Dream Machine
- `VIDEO_STUDIO_RUNWAY_API_KEY`: API key for Runway ML
- `VIDEO_STUDIO_PIKA_API_KEY`: API key for Pika Labs
- `VIDEO_STUDIO_DEBUG_MODE`: Enable debug mode (true/false)
- `VIDEO_STUDIO_LOG_LEVEL`: Set logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `VIDEO_STUDIO_MAX_CONCURRENT_TASKS`: Maximum concurrent tasks
- `VIDEO_STUDIO_STORAGE_BASE_PATH`: Base path for asset storage

## Configuration File Example

```json
{
  "models": {
    "luma": {
      "name": "luma",
      "api_key": "your_luma_api_key",
      "base_url": "https://api.lumalabs.ai/dream-machine/v1",
      "timeout": 300,
      "max_retries": 3,
      "enabled": true
    }
  },
  "storage": {
    "base_path": "./video_studio_assets",
    "temp_path": "./video_studio_temp",
    "max_file_size_mb": 100,
    "cleanup_interval_hours": 24
  },
  "workflow": {
    "max_concurrent_tasks": 5,
    "task_timeout_minutes": 30,
    "enable_progress_notifications": true
  },
  "rendering": {
    "default_quality": "1080p",
    "default_aspect_ratio": "16:9",
    "max_duration_seconds": 300
  }
}
```

## Next Steps

The following components are planned for implementation in subsequent tasks:

1. **Model Adapter System**: Unified interfaces for different AI models
2. **Workflow Management**: Task lifecycle and progress tracking
3. **Asset Management**: File upload, processing, and storage
4. **Scene Generation**: JSON script parsing and scene processing
5. **Rendering Pipeline**: Video composition and output generation
6. **Template System**: Pre-configured video templates and styles
7. **Monitoring System**: Performance monitoring and alerting

## Dependencies

- **Python 3.8+**: Core runtime
- **Streamlit**: UI framework
- **asyncio**: Asynchronous operations
- **pathlib**: File system operations
- **json**: Configuration serialization
- **PyYAML** (optional): YAML configuration support

## Testing

The system includes comprehensive testing support:

- **Unit Tests**: Test individual components and functions
- **Property-Based Tests**: Validate system properties across random inputs
- **Integration Tests**: Test component interactions
- **Error Simulation**: Test error handling and recovery mechanisms

## Contributing

When contributing to the Video Studio system:

1. Follow the established architecture patterns
2. Add comprehensive error handling for new components
3. Include logging for important operations
4. Validate all configuration inputs
5. Write tests for new functionality
6. Update documentation for new features