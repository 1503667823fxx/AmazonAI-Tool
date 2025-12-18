"""
Video Studio - Professional Image-to-Video Workflow System

This module provides a comprehensive video generation workflow system with support for
multiple AI models, asset management, and error handling.
"""

from .models import (
    VideoConfig,
    Scene,
    TaskInfo,
    TaskStatus,
    VideoQuality,
    AspectRatio,
    AudioConfig,
    TextOverlay,
    ConfigurationManager
)

from .error_handler import (
    VideoStudioErrorHandler,
    VideoStudioErrorType,
    ErrorSeverity,
    VideoStudioErrorInfo,
    video_studio_error_handler,
    handle_model_adapter_error,
    handle_generation_error,
    handle_asset_management_error,
    handle_workflow_error,
    handle_configuration_error,
    handle_rendering_error,
    handle_template_error,
    handle_scene_processing_error,
    with_video_studio_error_handling,
    with_circuit_breaker
)

from .config import (
    VideoStudioConfig,
    ModelConfig,
    StorageConfig,
    WorkflowConfig,
    RenderingConfig,
    ConfigurationManager,
    config_manager,
    get_config,
    reload_config,
    get_model_config,
    get_enabled_models
)

from .logging_config import (
    VideoStudioLogger,
    LogLevel,
    setup_logging,
    get_logger,
    log_info,
    log_error,
    log_warning,
    log_debug,
    main_logger,
    model_logger,
    workflow_logger,
    asset_logger,
    render_logger
)

from .model_adapter import (
    ModelAdapter,
    GenerationConfig,
    GenerationResult,
    JobStatus,
    ModelCapability,
    ModelAdapterRegistry,
    model_registry,
    register_adapter,
    get_adapter,
    list_adapters,
    get_adapters_by_capability,
    get_best_adapter_for_config
)

from .generation_engine import (
    GenerationEngine,
    LoadBalancingStrategy,
    ModelSelectionCriteria,
    get_generation_engine,
    generate_video,
    batch_generate_videos
)

from .adapters import (
    LumaAdapter,
    RunwayAdapter,
    PikaAdapter
)

from .workflow_manager import (
    WorkflowManager,
    TaskPriority,
    TaskContext,
    get_workflow_manager,
    create_video_task,
    get_task_status,
    cancel_task
)

from .task_scheduler import (
    TaskScheduler,
    SchedulingStrategy,
    ResourceManager,
    ScheduledTask,
    get_task_scheduler,
    schedule_task
)

from .notification_system import (
    NotificationSystem,
    NotificationType,
    NotificationChannel,
    NotificationMessage,
    WebSocketNotificationHandler,
    EmailNotificationHandler,
    WebhookNotificationHandler,
    get_notification_system,
    send_notification
)

from .asset_manager import (
    AssetManager,
    AssetType,
    AssetStatus,
    AssetMetadata,
    ImageProcessingOptions,
    upload_image_file,
    upload_video_file
)

from .file_manager import (
    FileManager,
    get_file_manager,
    upload_file,
    get_file_path,
    get_file_info,
    list_files,
    delete_file,
    validate_file,
    get_storage_info,
    cleanup_old_files
)

from .video_manager import (
    VideoManager,
    VideoProcessingOptions,
    VideoMetadata,
    get_video_manager
)

from .cleanup_service import (
    CleanupService,
    CleanupPolicy,
    CleanupRule,
    CleanupResult,
    get_cleanup_service,
    run_cleanup,
    check_storage_health,
    optimize_storage
)

from .scene_generator import (
    SceneGenerator,
    ScenePreviewManager,
    BatchSceneProcessor,
    ValidationError,
    ScriptValidationResult,
    ScenePreview,
    BatchGenerationResult
)

from .render_pipeline import (
    RenderPipeline,
    VideoSegment,
    AudioTrack,
    RenderSettings,
    RenderProgress,
    QualityControlSettings,
    QualityAssessment,
    AudioSyncResult,
    PlatformSettings,
    FormatConversionSettings,
    PlatformOptimizer,
    FormatConverter,
    TransitionType,
    VideoFormat,
    CompressionLevel,
    AudioSyncMethod,
    QualityMetric,
    Platform,
    VideoCodec,
    AudioCodec,
    get_render_pipeline,
    compose_video,
    optimize_for_platform,
    generate_multi_format_output
)

from .template_manager import (
    TemplateManager,
    VideoTemplate,
    TemplateConfig,
    TemplateMetadata,
    TemplateCategory,
    VideoStyle
)

from .performance_monitor import (
    PerformanceMonitor,
    SystemMetrics,
    MetricType,
    MetricData,
    PerformanceThresholds,
    performance_monitor,
    get_performance_monitor,
    start_monitoring,
    stop_monitoring,
    get_current_metrics,
    get_performance_summary
)

from .rate_limiter import (
    RateLimiter,
    CircuitBreaker,
    ProtectionManager,
    RateLimitConfig,
    CircuitBreakerConfig,
    RateLimitStrategy,
    CircuitState,
    protection_manager,
    get_protection_manager,
    with_rate_limit,
    with_circuit_breaker
)

from .analytics_engine import (
    AnalyticsEngine,
    UsageRecord,
    CostRecord,
    ModelPricing,
    UsageStatistics,
    CostAnalysis,
    ReportPeriod,
    CostCategory,
    analytics_engine,
    get_analytics_engine,
    record_usage,
    generate_report,
    get_cost_analysis
)

from .performance_optimizer import (
    PerformanceOptimizer,
    OptimizationLevel,
    OptimizationType,
    OptimizationResult,
    PerformanceProfile,
    get_performance_optimizer,
    optimize_system,
    detect_bottlenecks,
    get_optimization_summary
)

from .resource_manager import (
    ResourceManager,
    ResourceType,
    ResourcePriority,
    ResourceRequest,
    ResourceAllocation,
    ResourcePool,
    get_resource_manager,
    request_memory,
    request_cpu,
    release_allocation,
    get_resource_status
)

__all__ = [
    # Core Models
    'VideoConfig',
    'Scene', 
    'TaskInfo',
    'TaskStatus',
    'VideoQuality',
    'AspectRatio',
    'AudioConfig',
    'TextOverlay',
    'ConfigurationManager',
    
    # Error Handling
    'VideoStudioErrorHandler',
    'VideoStudioErrorType',
    'ErrorSeverity',
    'VideoStudioErrorInfo',
    'video_studio_error_handler',
    'handle_model_adapter_error',
    'handle_generation_error',
    'handle_asset_management_error',
    'handle_workflow_error',
    'handle_configuration_error',
    'handle_rendering_error',
    'handle_template_error',
    'handle_scene_processing_error',
    'with_video_studio_error_handling',
    'with_circuit_breaker',
    
    # Configuration Management
    'VideoStudioConfig',
    'ModelConfig',
    'StorageConfig',
    'WorkflowConfig',
    'RenderingConfig',
    'config_manager',
    'get_config',
    'reload_config',
    'get_model_config',
    'get_enabled_models',
    
    # Model Adapter System
    'ModelAdapter',
    'GenerationConfig',
    'GenerationResult',
    'JobStatus',
    'ModelCapability',
    'ModelAdapterRegistry',
    'model_registry',
    'register_adapter',
    'get_adapter',
    'list_adapters',
    'get_adapters_by_capability',
    'get_best_adapter_for_config',
    
    # Generation Engine
    'GenerationEngine',
    'LoadBalancingStrategy',
    'ModelSelectionCriteria',
    'get_generation_engine',
    'generate_video',
    'batch_generate_videos',
    
    # Model Adapters
    'LumaAdapter',
    'RunwayAdapter',
    'PikaAdapter',
    
    # Workflow Management
    'WorkflowManager',
    'TaskPriority',
    'TaskContext',
    'get_workflow_manager',
    'create_video_task',
    'get_task_status',
    'cancel_task',
    
    # Task Scheduling
    'TaskScheduler',
    'SchedulingStrategy',
    'ResourceManager',
    'ScheduledTask',
    'get_task_scheduler',
    'schedule_task',
    
    # Notification System
    'NotificationSystem',
    'NotificationType',
    'NotificationChannel',
    'NotificationMessage',
    'WebSocketNotificationHandler',
    'EmailNotificationHandler',
    'WebhookNotificationHandler',
    'get_notification_system',
    'send_notification',
    
    # Asset Management
    'AssetManager',
    'AssetType',
    'AssetStatus',
    'AssetMetadata',
    'ImageProcessingOptions',
    'upload_image_file',
    'upload_video_file',
    
    # File Management
    'FileManager',
    'get_file_manager',
    'upload_file',
    'get_file_path',
    'get_file_info',
    'list_files',
    'delete_file',
    'validate_file',
    'get_storage_info',
    'cleanup_old_files',
    
    # Video Management
    'VideoManager',
    'VideoProcessingOptions',
    'VideoMetadata',
    'get_video_manager',
    
    # Cleanup Service
    'CleanupService',
    'CleanupPolicy',
    'CleanupRule',
    'CleanupResult',
    'get_cleanup_service',
    'run_cleanup',
    'check_storage_health',
    'optimize_storage',
    
    # Scene Generation
    'SceneGenerator',
    'ScenePreviewManager',
    'BatchSceneProcessor',
    'ValidationError',
    'ScriptValidationResult',
    'ScenePreview',
    'BatchGenerationResult',
    
    # Render Pipeline
    'RenderPipeline',
    'VideoSegment',
    'AudioTrack',
    'RenderSettings',
    'RenderProgress',
    'QualityControlSettings',
    'QualityAssessment',
    'AudioSyncResult',
    'PlatformSettings',
    'FormatConversionSettings',
    'PlatformOptimizer',
    'FormatConverter',
    'TransitionType',
    'VideoFormat',
    'CompressionLevel',
    'AudioSyncMethod',
    'QualityMetric',
    'Platform',
    'VideoCodec',
    'AudioCodec',
    'get_render_pipeline',
    'compose_video',
    'optimize_for_platform',
    'generate_multi_format_output',
    
    # Template Management
    'TemplateManager',
    'VideoTemplate',
    'TemplateConfig',
    'TemplateMetadata',
    'TemplateCategory',
    'VideoStyle',
    
    # Performance Monitoring
    'PerformanceMonitor',
    'SystemMetrics',
    'MetricType',
    'MetricData',
    'PerformanceThresholds',
    'performance_monitor',
    'get_performance_monitor',
    'start_monitoring',
    'stop_monitoring',
    'get_current_metrics',
    'get_performance_summary',
    
    # Rate Limiting and Circuit Breaker
    'RateLimiter',
    'CircuitBreaker',
    'ProtectionManager',
    'RateLimitConfig',
    'CircuitBreakerConfig',
    'RateLimitStrategy',
    'CircuitState',
    'protection_manager',
    'get_protection_manager',
    'with_rate_limit',
    'with_circuit_breaker',
    
    # Analytics and Cost Analysis
    'AnalyticsEngine',
    'UsageRecord',
    'CostRecord',
    'ModelPricing',
    'UsageStatistics',
    'CostAnalysis',
    'ReportPeriod',
    'CostCategory',
    'analytics_engine',
    'get_analytics_engine',
    'record_usage',
    'generate_report',
    'get_cost_analysis',
    
    # Performance Optimization
    'PerformanceOptimizer',
    'OptimizationLevel',
    'OptimizationType',
    'OptimizationResult',
    'PerformanceProfile',
    'get_performance_optimizer',
    'optimize_system',
    'detect_bottlenecks',
    'get_optimization_summary',
    
    # Resource Management
    'ResourceManager',
    'ResourceType',
    'ResourcePriority',
    'ResourceRequest',
    'ResourceAllocation',
    'ResourcePool',
    'get_resource_manager',
    'request_memory',
    'request_cpu',
    'release_allocation',
    'get_resource_status',
    
    # Logging
    'VideoStudioLogger',
    'LogLevel',
    'setup_logging',
    'get_logger',
    'log_info',
    'log_error',
    'log_warning',
    'log_debug',
    'main_logger',
    'model_logger',
    'workflow_logger',
    'asset_logger',
    'render_logger'
]

# Version information
__version__ = "1.0.0"
__author__ = "Video Studio Team"
__description__ = "Professional Image-to-Video Workflow System"