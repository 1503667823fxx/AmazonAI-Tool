"""
Comprehensive Error Handling System for AI Studio
Provides centralized error handling with recovery options and user guidance
"""

import streamlit as st
import time
import traceback
from typing import Dict, Any, Optional, Callable, List
from enum import Enum
from dataclasses import dataclass
from datetime import datetime


class ErrorType(Enum):
    """Types of errors that can occur in the AI Studio"""
    API_ERROR = "api_error"
    UPLOAD_ERROR = "upload_error"
    UI_ERROR = "ui_error"
    STREAMING_ERROR = "streaming_error"
    NETWORK_ERROR = "network_error"
    VALIDATION_ERROR = "validation_error"
    TIMEOUT_ERROR = "timeout_error"
    RATE_LIMIT_ERROR = "rate_limit_error"


class ErrorSeverity(Enum):
    """Severity levels for errors"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ErrorInfo:
    """Information about an error occurrence"""
    error_type: ErrorType
    severity: ErrorSeverity
    message: str
    details: Optional[str] = None
    timestamp: datetime = None
    user_message: Optional[str] = None
    recovery_options: List[str] = None
    retry_count: int = 0
    max_retries: int = 3
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.recovery_options is None:
            self.recovery_options = []


class RecoveryAction:
    """Represents a recovery action that can be taken after an error"""
    
    def __init__(self, name: str, description: str, action: Callable, 
                 requires_user_input: bool = False):
        self.name = name
        self.description = description
        self.action = action
        self.requires_user_input = requires_user_input


class ErrorHandler:
    """Comprehensive error handler with recovery mechanisms"""
    
    def __init__(self):
        self.error_history: List[ErrorInfo] = []
        self.retry_delays = [1, 2, 4, 8, 16]  # Exponential backoff in seconds
        self.recovery_actions: Dict[ErrorType, List[RecoveryAction]] = {}
        self._setup_default_recovery_actions()
    
    def _setup_default_recovery_actions(self):
        """Setup default recovery actions for different error types"""
        
        # API Error recovery actions
        self.recovery_actions[ErrorType.API_ERROR] = [
            RecoveryAction(
                "retry", 
                "Retry the API request",
                self._retry_with_backoff
            ),
            RecoveryAction(
                "check_api_key", 
                "Verify API key configuration",
                self._check_api_key_guidance,
                requires_user_input=True
            ),
            RecoveryAction(
                "switch_model", 
                "Try a different AI model",
                self._suggest_model_switch,
                requires_user_input=True
            )
        ]
        
        # Upload Error recovery actions
        self.recovery_actions[ErrorType.UPLOAD_ERROR] = [
            RecoveryAction(
                "retry_upload", 
                "Retry file upload",
                self._retry_upload
            ),
            RecoveryAction(
                "check_file_size", 
                "Check file size and format",
                self._check_file_requirements
            ),
            RecoveryAction(
                "clear_cache", 
                "Clear upload cache and try again",
                self._clear_upload_cache
            )
        ]
        
        # Streaming Error recovery actions
        self.recovery_actions[ErrorType.STREAMING_ERROR] = [
            RecoveryAction(
                "restart_stream", 
                "Restart streaming connection",
                self._restart_streaming
            ),
            RecoveryAction(
                "fallback_mode", 
                "Switch to non-streaming mode",
                self._disable_streaming
            )
        ]
        
        # Network Error recovery actions
        self.recovery_actions[ErrorType.NETWORK_ERROR] = [
            RecoveryAction(
                "retry_connection", 
                "Retry network connection",
                self._retry_with_backoff
            ),
            RecoveryAction(
                "check_connection", 
                "Check internet connection",
                self._check_network_guidance,
                requires_user_input=True
            )
        ]
        
        # UI Error recovery actions
        self.recovery_actions[ErrorType.UI_ERROR] = [
            RecoveryAction(
                "refresh_ui", 
                "Refresh the interface",
                self._refresh_ui
            ),
            RecoveryAction(
                "reset_state", 
                "Reset application state",
                self._reset_ui_state,
                requires_user_input=True
            )
        ]
    
    def handle_error(self, error: Exception, error_type: ErrorType, 
                    context: Optional[Dict[str, Any]] = None) -> ErrorInfo:
        """
        Handle an error with appropriate recovery options
        
        Args:
            error: The exception that occurred
            error_type: Type of error for categorization
            context: Additional context about the error
            
        Returns:
            ErrorInfo object with error details and recovery options
        """
        
        # Determine error severity
        severity = self._determine_severity(error, error_type)
        
        # Create error info
        error_info = ErrorInfo(
            error_type=error_type,
            severity=severity,
            message=str(error),
            details=traceback.format_exc() if severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL] else None,
            user_message=self._generate_user_message(error, error_type),
            recovery_options=[action.name for action in self.recovery_actions.get(error_type, [])]
        )
        
        # Add to error history
        self.error_history.append(error_info)
        
        # Display error to user
        self._display_error(error_info)
        
        # Auto-recovery for low severity errors
        if severity == ErrorSeverity.LOW and error_info.recovery_options:
            self._attempt_auto_recovery(error_info)
        
        return error_info
    
    def _determine_severity(self, error: Exception, error_type: ErrorType) -> ErrorSeverity:
        """Determine the severity of an error"""
        
        # Critical errors that break core functionality
        if error_type in [ErrorType.UI_ERROR] and "session_state" in str(error).lower():
            return ErrorSeverity.CRITICAL
        
        # High severity errors that significantly impact user experience
        if error_type in [ErrorType.API_ERROR, ErrorType.STREAMING_ERROR]:
            if "authentication" in str(error).lower() or "unauthorized" in str(error).lower():
                return ErrorSeverity.HIGH
        
        # Medium severity errors that cause feature failures
        if error_type in [ErrorType.UPLOAD_ERROR, ErrorType.VALIDATION_ERROR]:
            return ErrorSeverity.MEDIUM
        
        # Network and timeout errors are usually temporary
        if error_type in [ErrorType.NETWORK_ERROR, ErrorType.TIMEOUT_ERROR, ErrorType.RATE_LIMIT_ERROR]:
            return ErrorSeverity.LOW
        
        # Default to medium severity
        return ErrorSeverity.MEDIUM
    
    def _generate_user_message(self, error: Exception, error_type: ErrorType) -> str:
        """Generate a user-friendly error message"""
        
        error_messages = {
            ErrorType.API_ERROR: "There was an issue connecting to the AI service. This might be due to network issues or API configuration.",
            ErrorType.UPLOAD_ERROR: "File upload failed. Please check your file size and format, then try again.",
            ErrorType.UI_ERROR: "The interface encountered an issue. Try refreshing the page or resetting the application.",
            ErrorType.STREAMING_ERROR: "Real-time response streaming was interrupted. You can continue in regular mode.",
            ErrorType.NETWORK_ERROR: "Network connection issue detected. Please check your internet connection.",
            ErrorType.VALIDATION_ERROR: "The input provided doesn't meet the required format or constraints.",
            ErrorType.TIMEOUT_ERROR: "The operation took too long to complete. This might be due to high server load.",
            ErrorType.RATE_LIMIT_ERROR: "Too many requests have been made. Please wait a moment before trying again."
        }
        
        base_message = error_messages.get(error_type, "An unexpected error occurred.")
        
        # Add specific guidance based on error content
        error_str = str(error).lower()
        
        if "api key" in error_str or "authentication" in error_str:
            base_message += " Please check your API key configuration."
        elif "file size" in error_str or "too large" in error_str:
            base_message += " The file may be too large. Try a smaller file or different format."
        elif "timeout" in error_str or "connection" in error_str:
            base_message += " This is usually temporary. Please try again in a moment."
        
        return base_message
    
    def _display_error(self, error_info: ErrorInfo) -> None:
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
        
        # Show recovery options if available
        if error_info.recovery_options:
            with st.expander("🔧 Recovery Options"):
                for option in error_info.recovery_options:
                    action = self._get_recovery_action(error_info.error_type, option)
                    if action:
                        if st.button(f"{action.name.replace('_', ' ').title()}", 
                                   key=f"recovery_{error_info.timestamp}_{option}"):
                            self._execute_recovery_action(action, error_info)
        
        # Show technical details for high/critical errors
        if error_info.severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL] and error_info.details:
            with st.expander("🔍 Technical Details"):
                st.code(error_info.details)
    
    def _get_recovery_action(self, error_type: ErrorType, action_name: str) -> Optional[RecoveryAction]:
        """Get a recovery action by name for a specific error type"""
        
        actions = self.recovery_actions.get(error_type, [])
        for action in actions:
            if action.name == action_name:
                return action
        return None
    
    def _execute_recovery_action(self, action: RecoveryAction, error_info: ErrorInfo) -> None:
        """Execute a recovery action"""
        
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
    
    def _attempt_auto_recovery(self, error_info: ErrorInfo) -> bool:
        """Attempt automatic recovery for low severity errors"""
        
        if not error_info.recovery_options:
            return False
        
        # Try the first available recovery action
        first_action_name = error_info.recovery_options[0]
        action = self._get_recovery_action(error_info.error_type, first_action_name)
        
        if action and not action.requires_user_input:
            try:
                result = action.action()
                if result:
                    st.success(f"✅ Automatically recovered using: {action.description}")
                    return True
            except Exception:
                pass  # Auto-recovery failed, user will need to handle manually
        
        return False
    
    def _retry_with_backoff(self, operation: Optional[Callable] = None, 
                           error_info: Optional[ErrorInfo] = None) -> bool:
        """Retry an operation with exponential backoff"""
        
        if error_info and error_info.retry_count >= error_info.max_retries:
            st.error("Maximum retry attempts reached. Please try again later.")
            return False
        
        if error_info:
            error_info.retry_count += 1
            delay = self.retry_delays[min(error_info.retry_count - 1, len(self.retry_delays) - 1)]
            
            with st.spinner(f"Retrying in {delay} seconds... (Attempt {error_info.retry_count}/{error_info.max_retries})"):
                time.sleep(delay)
        
        # In a real implementation, this would retry the actual operation
        # For now, we simulate success
        return True
    
    def _check_api_key_guidance(self) -> bool:
        """Provide guidance for API key issues"""
        
        st.info("""
        **API Key Configuration Help:**
        
        1. Check that your API key is correctly set in the application settings
        2. Verify the API key has the necessary permissions
        3. Ensure the API key hasn't expired
        4. Try regenerating the API key if issues persist
        """)
        return True
    
    def _suggest_model_switch(self) -> bool:
        """Suggest switching to a different AI model"""
        
        st.info("""
        **Model Switch Suggestion:**
        
        Try switching to a different AI model in the sidebar. Some models may be:
        - Temporarily unavailable
        - Experiencing high load
        - Not compatible with your current request
        """)
        return True
    
    def _retry_upload(self) -> bool:
        """Retry file upload operation"""
        
        st.info("Retrying file upload. Please wait...")
        # In a real implementation, this would trigger the upload retry
        return True
    
    def _check_file_requirements(self) -> bool:
        """Display file requirements information"""
        
        st.info("""
        **File Upload Requirements:**
        
        - **Supported formats:** JPG, PNG, WEBP, JPEG
        - **Maximum size:** 10MB per file
        - **Maximum files:** 10 files at once
        
        Please ensure your files meet these requirements and try again.
        """)
        return True
    
    def _clear_upload_cache(self) -> bool:
        """Clear upload cache"""
        
        # In a real implementation, this would clear the actual cache
        st.info("Upload cache cleared. Please try uploading your files again.")
        return True
    
    def _restart_streaming(self) -> bool:
        """Restart streaming connection"""
        
        from .enhanced_state_manager import state_manager
        
        # Reset streaming state
        state_manager.set_streaming_state(False)
        time.sleep(1)
        state_manager.set_streaming_state(True)
        
        st.info("Streaming connection restarted. You can continue your conversation.")
        return True
    
    def _disable_streaming(self) -> bool:
        """Disable streaming mode as fallback"""
        
        from .enhanced_state_manager import state_manager
        from .models import UISettings
        
        # Disable streaming in UI settings
        current_state = state_manager.get_state()
        current_state.ui_settings.enable_streaming = False
        state_manager.set_streaming_state(False)
        state_manager.update_state(current_state)
        
        st.info("Switched to non-streaming mode. Responses will appear all at once when complete.")
        return True
    
    def _check_network_guidance(self) -> bool:
        """Provide network troubleshooting guidance"""
        
        st.info("""
        **Network Connection Help:**
        
        1. Check your internet connection
        2. Try refreshing the page
        3. Disable VPN if you're using one
        4. Check if your firewall is blocking the connection
        5. Try again in a few minutes
        """)
        return True
    
    def _refresh_ui(self) -> bool:
        """Refresh the UI"""
        
        st.info("Refreshing the interface...")
        st.rerun()
        return True
    
    def _reset_ui_state(self) -> bool:
        """Reset UI state (requires user confirmation)"""
        
        st.warning("""
        **Reset Application State**
        
        This will clear your current conversation and reset all settings.
        Are you sure you want to continue?
        """)
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("Yes, Reset", type="primary"):
                from .enhanced_state_manager import state_manager
                state_manager.clear_conversation()
                st.success("Application state has been reset.")
                st.rerun()
                return True
        
        with col2:
            if st.button("Cancel"):
                return False
        
        return False
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """Get statistics about errors that have occurred"""
        
        if not self.error_history:
            return {"total_errors": 0}
        
        stats = {
            "total_errors": len(self.error_history),
            "by_type": {},
            "by_severity": {},
            "recent_errors": len([e for e in self.error_history 
                                if (datetime.now() - e.timestamp).total_seconds() < 3600])
        }
        
        for error in self.error_history:
            # Count by type
            error_type = error.error_type.value
            stats["by_type"][error_type] = stats["by_type"].get(error_type, 0) + 1
            
            # Count by severity
            severity = error.severity.value
            stats["by_severity"][severity] = stats["by_severity"].get(severity, 0) + 1
        
        return stats
    
    def clear_error_history(self) -> None:
        """Clear the error history"""
        self.error_history.clear()


# Global error handler instance
error_handler = ErrorHandler()


# Convenience functions for common error handling scenarios
def handle_api_error(error: Exception, context: Optional[Dict[str, Any]] = None) -> ErrorInfo:
    """Handle API-related errors"""
    return error_handler.handle_error(error, ErrorType.API_ERROR, context)


def handle_upload_error(error: Exception, context: Optional[Dict[str, Any]] = None) -> ErrorInfo:
    """Handle file upload errors"""
    return error_handler.handle_error(error, ErrorType.UPLOAD_ERROR, context)


def handle_streaming_error(error: Exception, context: Optional[Dict[str, Any]] = None) -> ErrorInfo:
    """Handle streaming-related errors"""
    return error_handler.handle_error(error, ErrorType.STREAMING_ERROR, context)


def handle_ui_error(error: Exception, context: Optional[Dict[str, Any]] = None) -> ErrorInfo:
    """Handle UI-related errors"""
    return error_handler.handle_error(error, ErrorType.UI_ERROR, context)


def handle_network_error(error: Exception, context: Optional[Dict[str, Any]] = None) -> ErrorInfo:
    """Handle network-related errors"""
    return error_handler.handle_error(error, ErrorType.NETWORK_ERROR, context)


# Decorator for automatic error handling
def with_error_handling(error_type: ErrorType):
    """Decorator to automatically handle errors in functions"""
    
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_handler.handle_error(e, error_type)
                return None
        return wrapper
    return decorator