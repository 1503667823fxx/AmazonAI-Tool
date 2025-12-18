"""
Comprehensive Error Handling System for Video Studio
Provides centralized error handling with recovery options and user guidance for video generation workflows
"""

import streamlit as st
import time
import traceback
import asyncio
from typing import Dict, Any, Optional, Callable, List
from enum import Enum
from dataclasses import dataclass
from datetime import datetime
from functools import wraps


class VideoStudioErrorType(Enum):
    """Types of errors that can occur in the Video Studio"""
    MODEL_ADAPTER_ERROR = "model_adapter_error"
    GENERATION_ERROR = "generation_error"
    ASSET_MANAGEMENT_ERROR = "asset_management_error"
    WORKFLOW_ERROR = "workflow_error"
    CONFIGURATION_ERROR = "configuration_error"
    RENDERING_ERROR = "rendering_error"
    TEMPLATE_ERROR = "template_error"
    SCENE_PROCESSING_ERROR = "scene_processing_error"
    NETWORK_ERROR = "network_error"
    TIMEOUT_ERROR = "timeout_error"
    RATE_LIMIT_ERROR = "rate_limit_error"
    VALIDATION_ERROR = "validation_error"


class ErrorSeverity(Enum):
    """Severity levels for errors"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class VideoStudioErrorInfo:
    """Information about an error occurrence in Video Studio"""
    error_type: VideoStudioErrorType
    severity: ErrorSeverity
    message: str
    details: Optional[str] = None
    timestamp: datetime = None
    user_message: Optional[str] = None
    recovery_options: List[str] = None
    retry_count: int = 0
    max_retries: int = 3
    task_id: Optional[str] = None  # Associated task ID if applicable
    model_name: Optional[str] = None  # Associated model name if applicable
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.recovery_options is None:
            self.recovery_options = []


class RecoveryAction:
    """Represents a recovery action that can be taken after an error"""
    
    def __init__(self, name: str, description: str, action: Callable, 
                 requires_user_input: bool = False, is_async: bool = False):
        self.name = name
        self.description = description
        self.action = action
        self.requires_user_input = requires_user_input
        self.is_async = is_async


class VideoStudioErrorHandler:
    """Comprehensive error handler with recovery mechanisms for Video Studio"""
    
    def __init__(self):
        self.error_history: List[VideoStudioErrorInfo] = []
        self.retry_delays = [1, 2, 4, 8, 16]  # Exponential backoff in seconds
        self.recovery_actions: Dict[VideoStudioErrorType, List[RecoveryAction]] = {}
        self.circuit_breaker_state: Dict[str, Dict[str, Any]] = {}
        self._setup_default_recovery_actions()
    
    def _setup_default_recovery_actions(self):
        """Setup default recovery actions for different error types"""
        
        # Model Adapter Error recovery actions
        self.recovery_actions[VideoStudioErrorType.MODEL_ADAPTER_ERROR] = [
            RecoveryAction(
                "retry_model_call", 
                "Retry the model API call",
                self._retry_with_backoff,
                is_async=True
            ),
            RecoveryAction(
                "switch_model", 
                "Switch to a different AI model",
                self._suggest_model_switch,
                requires_user_input=True
            ),
            RecoveryAction(
                "check_model_config", 
                "Verify model configuration",
                self._check_model_config_guidance,
                requires_user_input=True
            )
        ]
        
        # Generation Error recovery actions
        self.recovery_actions[VideoStudioErrorType.GENERATION_ERROR] = [
            RecoveryAction(
                "retry_generation", 
                "Retry video generation",
                self._retry_generation,
                is_async=True
            ),
            RecoveryAction(
                "adjust_parameters", 
                "Adjust generation parameters",
                self._suggest_parameter_adjustment,
                requires_user_input=True
            ),
            RecoveryAction(
                "fallback_model", 
                "Use fallback model",
                self._use_fallback_model,
                is_async=True
            )
        ]
        
        # Asset Management Error recovery actions
        self.recovery_actions[VideoStudioErrorType.ASSET_MANAGEMENT_ERROR] = [
            RecoveryAction(
                "retry_asset_operation", 
                "Retry asset operation",
                self._retry_asset_operation,
                is_async=True
            ),
            RecoveryAction(
                "check_storage_space", 
                "Check available storage space",
                self._check_storage_guidance
            ),
            RecoveryAction(
                "cleanup_temp_files", 
                "Clean up temporary files",
                self._cleanup_temp_files,
                is_async=True
            )
        ]
        
        # Workflow Error recovery actions
        self.recovery_actions[VideoStudioErrorType.WORKFLOW_ERROR] = [
            RecoveryAction(
                "restart_workflow", 
                "Restart the workflow",
                self._restart_workflow,
                is_async=True
            ),
            RecoveryAction(
                "resume_from_checkpoint", 
                "Resume from last checkpoint",
                self._resume_from_checkpoint,
                is_async=True
            )
        ]
        
        # Configuration Error recovery actions
        self.recovery_actions[VideoStudioErrorType.CONFIGURATION_ERROR] = [
            RecoveryAction(
                "validate_config", 
                "Validate configuration",
                self._validate_configuration
            ),
            RecoveryAction(
                "reset_to_defaults", 
                "Reset to default configuration",
                self._reset_to_defaults,
                requires_user_input=True
            )
        ]
        
        # Rendering Error recovery actions
        self.recovery_actions[VideoStudioErrorType.RENDERING_ERROR] = [
            RecoveryAction(
                "retry_rendering", 
                "Retry video rendering",
                self._retry_rendering,
                is_async=True
            ),
            RecoveryAction(
                "reduce_quality", 
                "Reduce output quality",
                self._suggest_quality_reduction,
                requires_user_input=True
            )
        ]
        
        # Network Error recovery actions
        self.recovery_actions[VideoStudioErrorType.NETWORK_ERROR] = [
            RecoveryAction(
                "retry_connection", 
                "Retry network connection",
                self._retry_with_backoff,
                is_async=True
            ),
            RecoveryAction(
                "check_connection", 
                "Check internet connection",
                self._check_network_guidance,
                requires_user_input=True
            )
        ]
    
    def handle_error(self, error: Exception, error_type: VideoStudioErrorType, 
                    context: Optional[Dict[str, Any]] = None) -> VideoStudioErrorInfo:
        """
        Handle an error with appropriate recovery options
        
        Args:
            error: The exception that occurred
            error_type: Type of error for categorization
            context: Additional context about the error (task_id, model_name, etc.)
            
        Returns:
            VideoStudioErrorInfo object with error details and recovery options
        """
        
        # Check circuit breaker
        if self._is_circuit_breaker_open(error_type, context):
            return self._handle_circuit_breaker_error(error_type, context)
        
        # Determine error severity
        severity = self._determine_severity(error, error_type)
        
        # Create error info
        error_info = VideoStudioErrorInfo(
            error_type=error_type,
            severity=severity,
            message=str(error),
            details=traceback.format_exc() if severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL] else None,
            user_message=self._generate_user_message(error, error_type),
            recovery_options=[action.name for action in self.recovery_actions.get(error_type, [])],
            task_id=context.get('task_id') if context else None,
            model_name=context.get('model_name') if context else None
        )
        
        # Add to error history
        self.error_history.append(error_info)
        
        # Update circuit breaker
        self._update_circuit_breaker(error_type, context, success=False)
        
        # Display error to user
        self._display_error(error_info)
        
        # Auto-recovery for low severity errors
        if severity == ErrorSeverity.LOW and error_info.recovery_options:
            asyncio.create_task(self._attempt_auto_recovery(error_info))
        
        return error_info
    
    def _determine_severity(self, error: Exception, error_type: VideoStudioErrorType) -> ErrorSeverity:
        """Determine the severity of an error"""
        
        error_str = str(error).lower()
        
        # Critical errors that break core functionality
        if error_type == VideoStudioErrorType.WORKFLOW_ERROR and "task_manager" in error_str:
            return ErrorSeverity.CRITICAL
        
        if error_type == VideoStudioErrorType.CONFIGURATION_ERROR and "invalid" in error_str:
            return ErrorSeverity.CRITICAL
        
        # High severity errors that significantly impact user experience
        if error_type in [VideoStudioErrorType.MODEL_ADAPTER_ERROR, VideoStudioErrorType.GENERATION_ERROR]:
            if any(keyword in error_str for keyword in ["authentication", "unauthorized", "api key"]):
                return ErrorSeverity.HIGH
        
        if error_type == VideoStudioErrorType.RENDERING_ERROR:
            return ErrorSeverity.HIGH
        
        # Medium severity errors that cause feature failures
        if error_type in [VideoStudioErrorType.ASSET_MANAGEMENT_ERROR, VideoStudioErrorType.TEMPLATE_ERROR, 
                         VideoStudioErrorType.SCENE_PROCESSING_ERROR, VideoStudioErrorType.VALIDATION_ERROR]:
            return ErrorSeverity.MEDIUM
        
        # Network and timeout errors are usually temporary
        if error_type in [VideoStudioErrorType.NETWORK_ERROR, VideoStudioErrorType.TIMEOUT_ERROR, 
                         VideoStudioErrorType.RATE_LIMIT_ERROR]:
            return ErrorSeverity.LOW
        
        # Default to medium severity
        return ErrorSeverity.MEDIUM
    
    def _generate_user_message(self, error: Exception, error_type: VideoStudioErrorType) -> str:
        """Generate a user-friendly error message"""
        
        error_messages = {
            VideoStudioErrorType.MODEL_ADAPTER_ERROR: "There was an issue connecting to the AI video generation service. This might be due to network issues or API configuration.",
            VideoStudioErrorType.GENERATION_ERROR: "Video generation failed. This could be due to invalid parameters or service issues.",
            VideoStudioErrorType.ASSET_MANAGEMENT_ERROR: "Asset management operation failed. Please check file permissions and available storage space.",
            VideoStudioErrorType.WORKFLOW_ERROR: "The video generation workflow encountered an issue. The task may need to be restarted.",
            VideoStudioErrorType.CONFIGURATION_ERROR: "Configuration validation failed. Please check your video generation settings.",
            VideoStudioErrorType.RENDERING_ERROR: "Video rendering failed. This might be due to insufficient resources or invalid scene data.",
            VideoStudioErrorType.TEMPLATE_ERROR: "Template processing failed. The selected template may be corrupted or incompatible.",
            VideoStudioErrorType.SCENE_PROCESSING_ERROR: "Scene processing failed. Please check your scene configuration and input data.",
            VideoStudioErrorType.NETWORK_ERROR: "Network connection issue detected. Please check your internet connection.",
            VideoStudioErrorType.TIMEOUT_ERROR: "The operation took too long to complete. This might be due to high server load.",
            VideoStudioErrorType.RATE_LIMIT_ERROR: "Too many requests have been made. Please wait a moment before trying again.",
            VideoStudioErrorType.VALIDATION_ERROR: "The input provided doesn't meet the required format or constraints."
        }
        
        base_message = error_messages.get(error_type, "An unexpected error occurred in the video generation system.")
        
        # Add specific guidance based on error content
        error_str = str(error).lower()
        
        if "api key" in error_str or "authentication" in error_str:
            base_message += " Please check your API key configuration."
        elif "file size" in error_str or "too large" in error_str:
            base_message += " The file may be too large. Try a smaller file or different format."
        elif "timeout" in error_str or "connection" in error_str:
            base_message += " This is usually temporary. Please try again in a moment."
        elif "memory" in error_str or "resource" in error_str:
            base_message += " The system may be running low on resources. Try reducing the complexity of your request."
        
        return base_message
    
    def _is_circuit_breaker_open(self, error_type: VideoStudioErrorType, context: Optional[Dict[str, Any]]) -> bool:
        """Check if circuit breaker is open for this error type/context"""
        
        key = self._get_circuit_breaker_key(error_type, context)
        breaker_info = self.circuit_breaker_state.get(key, {})
        
        if not breaker_info:
            return False
        
        failure_count = breaker_info.get('failure_count', 0)
        last_failure_time = breaker_info.get('last_failure_time')
        
        # Open circuit if too many failures
        if failure_count >= 5:
            # Check if enough time has passed to try again (circuit breaker timeout)
            if last_failure_time and (datetime.now() - last_failure_time).total_seconds() < 300:  # 5 minutes
                return True
            else:
                # Reset circuit breaker after timeout
                self.circuit_breaker_state[key] = {'failure_count': 0}
                return False
        
        return False
    
    def _update_circuit_breaker(self, error_type: VideoStudioErrorType, context: Optional[Dict[str, Any]], success: bool):
        """Update circuit breaker state"""
        
        key = self._get_circuit_breaker_key(error_type, context)
        
        if success:
            # Reset on success
            if key in self.circuit_breaker_state:
                self.circuit_breaker_state[key] = {'failure_count': 0}
        else:
            # Increment failure count
            if key not in self.circuit_breaker_state:
                self.circuit_breaker_state[key] = {'failure_count': 0}
            
            self.circuit_breaker_state[key]['failure_count'] += 1
            self.circuit_breaker_state[key]['last_failure_time'] = datetime.now()
    
    def _get_circuit_breaker_key(self, error_type: VideoStudioErrorType, context: Optional[Dict[str, Any]]) -> str:
        """Generate a key for circuit breaker tracking"""
        
        base_key = error_type.value
        
        if context:
            if 'model_name' in context:
                base_key += f"_{context['model_name']}"
            if 'task_id' in context:
                base_key += f"_{context['task_id']}"
        
        return base_key
    
    def _handle_circuit_breaker_error(self, error_type: VideoStudioErrorType, context: Optional[Dict[str, Any]]) -> VideoStudioErrorInfo:
        """Handle error when circuit breaker is open"""
        
        error_info = VideoStudioErrorInfo(
            error_type=error_type,
            severity=ErrorSeverity.HIGH,
            message="Service temporarily unavailable due to repeated failures",
            user_message="This service is temporarily unavailable due to repeated failures. Please try again in a few minutes.",
            recovery_options=["wait_and_retry"],
            task_id=context.get('task_id') if context else None,
            model_name=context.get('model_name') if context else None
        )
        
        self._display_error(error_info)
        return error_info
    
    async def _attempt_auto_recovery(self, error_info: VideoStudioErrorInfo) -> bool:
        """Attempt automatic recovery for low severity errors"""
        
        if not error_info.recovery_options:
            return False
        
        # Try the first available recovery action
        first_action_name = error_info.recovery_options[0]
        action = self._get_recovery_action(error_info.error_type, first_action_name)
        
        if action and not action.requires_user_input:
            try:
                if action.is_async:
                    result = await action.action()
                else:
                    result = action.action()
                
                if result:
                    st.success(f"✅ Automatically recovered using: {action.description}")
                    return True
            except Exception:
                pass  # Auto-recovery failed, user will need to handle manually
        
        return False
    
    def _display_error(self, error_info: VideoStudioErrorInfo) -> None:
        """Display error information to the user"""
        
        # Choose appropriate Streamlit component based on severity
        if error_info.severity == ErrorSeverity.CRITICAL:
            st.error(f"🚨 Critical Error: {error_info.user_message}")
        elif error_info.severity == ErrorSeverity.HIGH:
            st.error(f"❌ Error: {error_info.user_message}")
        elif error_info.severity == ErrorSeverity.MEDIUM:
            st.warning(f"⚠️ Warning: {error_info.user_message}")
        else:
            st.info(f"ℹ️ Notice: {error_info.user_message}")
        
        # Show task and model context if available
        if error_info.task_id or error_info.model_name:
            context_info = []
            if error_info.task_id:
                context_info.append(f"Task ID: {error_info.task_id}")
            if error_info.model_name:
                context_info.append(f"Model: {error_info.model_name}")
            
            st.caption(" | ".join(context_info))
        
        # Show recovery options if available
        if error_info.recovery_options:
            with st.expander("🔧 Recovery Options"):
                for option in error_info.recovery_options:
                    action = self._get_recovery_action(error_info.error_type, option)
                    if action:
                        if st.button(f"{action.name.replace('_', ' ').title()}", 
                                   key=f"recovery_{error_info.timestamp}_{option}"):
                            if action.is_async:
                                asyncio.create_task(self._execute_recovery_action_async(action, error_info))
                            else:
                                self._execute_recovery_action(action, error_info)
        
        # Show technical details for high/critical errors
        if error_info.severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL] and error_info.details:
            with st.expander("🔍 Technical Details"):
                st.code(error_info.details)
    
    def _get_recovery_action(self, error_type: VideoStudioErrorType, action_name: str) -> Optional[RecoveryAction]:
        """Get a recovery action by name for a specific error type"""
        
        actions = self.recovery_actions.get(error_type, [])
        for action in actions:
            if action.name == action_name:
                return action
        return None
    
    def _execute_recovery_action(self, action: RecoveryAction, error_info: VideoStudioErrorInfo) -> None:
        """Execute a recovery action (synchronous)"""
        
        try:
            if action.requires_user_input:
                st.info(f"Executing: {action.description}")
            
            # Execute the recovery action
            result = action.action()
            
            if result:
                st.success(f"✅ Recovery action '{action.name}' completed successfully")
            else:
                st.warning(f"⚠️ Recovery action '{action.name}' completed with warnings")
                
        except Exception as e:
            st.error(f"❌ Recovery action failed: {str(e)}")
    
    async def _execute_recovery_action_async(self, action: RecoveryAction, error_info: VideoStudioErrorInfo) -> None:
        """Execute a recovery action (asynchronous)"""
        
        try:
            if action.requires_user_input:
                st.info(f"Executing: {action.description}")
            
            # Execute the recovery action
            result = await action.action()
            
            if result:
                st.success(f"✅ Recovery action '{action.name}' completed successfully")
            else:
                st.warning(f"⚠️ Recovery action '{action.name}' completed with warnings")
                
        except Exception as e:
            st.error(f"❌ Recovery action failed: {str(e)}")
    
    async def _retry_with_backoff(self, operation: Optional[Callable] = None, 
                                 error_info: Optional[VideoStudioErrorInfo] = None) -> bool:
        """Retry an operation with exponential backoff"""
        
        if error_info and error_info.retry_count >= error_info.max_retries:
            st.error("Maximum retry attempts reached. Please try again later.")
            return False
        
        if error_info:
            error_info.retry_count += 1
            delay = self.retry_delays[min(error_info.retry_count - 1, len(self.retry_delays) - 1)]
            
            with st.spinner(f"Retrying in {delay} seconds... (Attempt {error_info.retry_count}/{error_info.max_retries})"):
                await asyncio.sleep(delay)
        
        # In a real implementation, this would retry the actual operation
        return True
    
    # Recovery action implementations
    def _suggest_model_switch(self) -> bool:
        """Suggest switching to a different AI model"""
        st.info("""
        **Model Switch Suggestion:**
        
        Try switching to a different AI model in the sidebar. Some models may be:
        - Temporarily unavailable
        - Experiencing high load
        - Not compatible with your current request
        
        Available models: Runway Gen-2, Pika Labs, Stable Video Diffusion
        """)
        return True
    
    def _check_model_config_guidance(self) -> bool:
        """Provide guidance for model configuration issues"""
        st.info("""
        **Model Configuration Help:**
        
        1. Check that your API keys are correctly set for the selected model
        2. Verify the API keys have the necessary permissions
        3. Ensure the API keys haven't expired
        4. Check model-specific parameter requirements
        5. Try regenerating the API key if issues persist
        """)
        return True
    
    async def _retry_generation(self) -> bool:
        """Retry video generation operation"""
        st.info("Retrying video generation. Please wait...")
        # In a real implementation, this would trigger the generation retry
        await asyncio.sleep(1)
        return True
    
    def _suggest_parameter_adjustment(self) -> bool:
        """Suggest adjusting generation parameters"""
        st.info("""
        **Parameter Adjustment Suggestions:**
        
        - Try reducing the video duration
        - Lower the output quality setting
        - Simplify the visual prompt
        - Reduce the number of scenes
        - Check aspect ratio compatibility
        """)
        return True
    
    async def _use_fallback_model(self) -> bool:
        """Use fallback model for generation"""
        st.info("Switching to fallback model for generation...")
        # In a real implementation, this would switch to a fallback model
        await asyncio.sleep(1)
        return True
    
    async def _retry_asset_operation(self) -> bool:
        """Retry asset management operation"""
        st.info("Retrying asset operation. Please wait...")
        await asyncio.sleep(1)
        return True
    
    def _check_storage_guidance(self) -> bool:
        """Display storage requirements information"""
        st.info("""
        **Storage Requirements:**
        
        - Ensure sufficient disk space for video processing
        - Check file permissions for the working directory
        - Verify network storage connectivity if applicable
        - Consider cleaning up old temporary files
        """)
        return True
    
    async def _cleanup_temp_files(self) -> bool:
        """Clean up temporary files"""
        st.info("Cleaning up temporary files...")
        # In a real implementation, this would clean up actual temp files
        await asyncio.sleep(1)
        return True
    
    async def _restart_workflow(self) -> bool:
        """Restart the workflow"""
        st.info("Restarting workflow...")
        # In a real implementation, this would restart the actual workflow
        await asyncio.sleep(1)
        return True
    
    async def _resume_from_checkpoint(self) -> bool:
        """Resume workflow from last checkpoint"""
        st.info("Resuming from last checkpoint...")
        # In a real implementation, this would resume from actual checkpoint
        await asyncio.sleep(1)
        return True
    
    def _validate_configuration(self) -> bool:
        """Validate current configuration"""
        st.info("Validating configuration...")
        # In a real implementation, this would validate actual configuration
        return True
    
    def _reset_to_defaults(self) -> bool:
        """Reset configuration to defaults"""
        st.warning("""
        **Reset Configuration to Defaults**
        
        This will reset all video generation settings to their default values.
        Are you sure you want to continue?
        """)
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("Yes, Reset", type="primary"):
                st.success("Configuration has been reset to defaults.")
                return True
        
        with col2:
            if st.button("Cancel"):
                return False
        
        return False
    
    async def _retry_rendering(self) -> bool:
        """Retry video rendering"""
        st.info("Retrying video rendering. Please wait...")
        await asyncio.sleep(2)
        return True
    
    def _suggest_quality_reduction(self) -> bool:
        """Suggest reducing output quality"""
        st.info("""
        **Quality Reduction Suggestions:**
        
        - Try reducing from 4K to 1080p or 720p
        - Lower the frame rate if supported
        - Reduce the bitrate settings
        - Simplify visual effects or transitions
        """)
        return True
    
    def _check_network_guidance(self) -> bool:
        """Provide network troubleshooting guidance"""
        st.info("""
        **Network Connection Help:**
        
        1. Check your internet connection stability
        2. Try refreshing the page
        3. Disable VPN if you're using one
        4. Check if your firewall is blocking the connection
        5. Verify API endpoint accessibility
        6. Try again in a few minutes
        """)
        return True


# Global error handler instance for Video Studio
video_studio_error_handler = VideoStudioErrorHandler()


# Convenience functions for common error handling scenarios
def handle_model_adapter_error(error: Exception, context: Optional[Dict[str, Any]] = None) -> VideoStudioErrorInfo:
    """Handle model adapter related errors"""
    return video_studio_error_handler.handle_error(error, VideoStudioErrorType.MODEL_ADAPTER_ERROR, context)


def handle_generation_error(error: Exception, context: Optional[Dict[str, Any]] = None) -> VideoStudioErrorInfo:
    """Handle video generation errors"""
    return video_studio_error_handler.handle_error(error, VideoStudioErrorType.GENERATION_ERROR, context)


def handle_asset_management_error(error: Exception, context: Optional[Dict[str, Any]] = None) -> VideoStudioErrorInfo:
    """Handle asset management errors"""
    return video_studio_error_handler.handle_error(error, VideoStudioErrorType.ASSET_MANAGEMENT_ERROR, context)


def handle_workflow_error(error: Exception, context: Optional[Dict[str, Any]] = None) -> VideoStudioErrorInfo:
    """Handle workflow management errors"""
    return video_studio_error_handler.handle_error(error, VideoStudioErrorType.WORKFLOW_ERROR, context)


def handle_configuration_error(error: Exception, context: Optional[Dict[str, Any]] = None) -> VideoStudioErrorInfo:
    """Handle configuration validation errors"""
    return video_studio_error_handler.handle_error(error, VideoStudioErrorType.CONFIGURATION_ERROR, context)


def handle_rendering_error(error: Exception, context: Optional[Dict[str, Any]] = None) -> VideoStudioErrorInfo:
    """Handle video rendering errors"""
    return video_studio_error_handler.handle_error(error, VideoStudioErrorType.RENDERING_ERROR, context)


def handle_template_error(error: Exception, context: Optional[Dict[str, Any]] = None) -> VideoStudioErrorInfo:
    """Handle template processing errors"""
    return video_studio_error_handler.handle_error(error, VideoStudioErrorType.TEMPLATE_ERROR, context)


def handle_scene_processing_error(error: Exception, context: Optional[Dict[str, Any]] = None) -> VideoStudioErrorInfo:
    """Handle scene processing errors"""
    return video_studio_error_handler.handle_error(error, VideoStudioErrorType.SCENE_PROCESSING_ERROR, context)


# Decorator for automatic error handling in Video Studio
def with_video_studio_error_handling(error_type: VideoStudioErrorType):
    """Decorator to automatically handle errors in Video Studio functions"""
    
    def decorator(func):
        if asyncio.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    video_studio_error_handler.handle_error(e, error_type)
                    return None
            return async_wrapper
        else:
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    video_studio_error_handler.handle_error(e, error_type)
                    return None
            return sync_wrapper
    return decorator


# Circuit breaker decorator for critical operations
def with_circuit_breaker(error_type: VideoStudioErrorType, failure_threshold: int = 5, timeout_seconds: int = 300):
    """Decorator to implement circuit breaker pattern for critical operations"""
    
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            context = kwargs.get('context', {})
            
            if video_studio_error_handler._is_circuit_breaker_open(error_type, context):
                raise Exception("Circuit breaker is open - service temporarily unavailable")
            
            try:
                result = await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)
                video_studio_error_handler._update_circuit_breaker(error_type, context, success=True)
                return result
            except Exception as e:
                video_studio_error_handler._update_circuit_breaker(error_type, context, success=False)
                raise e
        
        return wrapper
    return decorator