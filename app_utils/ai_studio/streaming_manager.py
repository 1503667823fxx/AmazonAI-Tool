"""
Streaming Manager for AI Studio
Handles real-time streaming with error recovery and user interruption capabilities
"""

import streamlit as st
import time
import threading
from typing import Optional, Callable, Generator, Any, Dict
from dataclasses import dataclass
from enum import Enum
from .enhanced_state_manager import state_manager
from .error_handler import handle_streaming_error, handle_api_error, ErrorType, with_error_handling


class StreamingState(Enum):
    """States for streaming operations"""
    IDLE = "idle"
    STARTING = "starting"
    STREAMING = "streaming"
    PAUSED = "paused"
    INTERRUPTED = "interrupted"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class StreamingSession:
    """Information about a streaming session"""
    session_id: str
    message_id: str
    model_used: str
    start_time: float
    state: StreamingState = StreamingState.IDLE
    accumulated_content: str = ""
    chunk_count: int = 0
    error_count: int = 0
    max_errors: int = 3


class StreamingManager:
    """Manages real-time streaming operations with error handling"""
    
    def __init__(self):
        self.current_session: Optional[StreamingSession] = None
        self.interrupt_requested = False
        self.typing_indicator_active = False
        self.progress_callback: Optional[Callable] = None
        self.error_callback: Optional[Callable] = None
    
    @with_error_handling(ErrorType.STREAMING_ERROR)
    def start_streaming(self, message_id: str, model_used: str, 
                       content_generator: Generator[str, None, None],
                       progress_callback: Optional[Callable] = None) -> bool:
        """
        Start a streaming session
        
        Args:
            message_id: ID of the message being streamed
            model_used: Model being used for generation
            content_generator: Generator that yields content chunks
            progress_callback: Optional callback for progress updates
            
        Returns:
            True if streaming started successfully, False otherwise
        """
        
        try:
            # Check if already streaming
            if self.current_session and self.current_session.state == StreamingState.STREAMING:
                handle_streaming_error(
                    RuntimeError("Cannot start streaming: another session is active"),
                    {"current_session": self.current_session.session_id}
                )
                return False
            
            # Create new streaming session
            session_id = f"stream_{int(time.time() * 1000)}"
            self.current_session = StreamingSession(
                session_id=session_id,
                message_id=message_id,
                model_used=model_used,
                start_time=time.time()
            )
            
            # Set streaming state
            state_manager.set_streaming_state(True)
            self.current_session.state = StreamingState.STARTING
            self.progress_callback = progress_callback
            self.interrupt_requested = False
            
            # Start typing indicator
            self._show_typing_indicator(True)
            
            # Process streaming content
            success = self._process_streaming_content(content_generator)
            
            if success:
                self.current_session.state = StreamingState.COMPLETED
                self._show_typing_indicator(False)
                state_manager.set_streaming_state(False)
                return True
            else:
                self._handle_streaming_failure()
                return False
                
        except Exception as e:
            handle_streaming_error(e, {
                "operation": "start_streaming",
                "message_id": message_id,
                "model": model_used
            })
            self._cleanup_session()
            return False
    
    def _process_streaming_content(self, content_generator: Generator[str, None, None]) -> bool:
        """Process streaming content chunks"""
        
        try:
            self.current_session.state = StreamingState.STREAMING
            
            for chunk in content_generator:
                # Check for interruption
                if self.interrupt_requested:
                    self.current_session.state = StreamingState.INTERRUPTED
                    self._handle_interruption()
                    return True  # Interruption is considered successful
                
                # Process chunk
                if chunk:
                    self.current_session.accumulated_content += chunk
                    self.current_session.chunk_count += 1
                    
                    # Update message content
                    self._update_streaming_message(self.current_session.accumulated_content)
                    
                    # Call progress callback if provided
                    if self.progress_callback:
                        try:
                            self.progress_callback(
                                self.current_session.chunk_count,
                                len(self.current_session.accumulated_content)
                            )
                        except Exception as callback_error:
                            # Don't fail streaming for callback errors
                            handle_streaming_error(callback_error, {
                                "operation": "progress_callback",
                                "chunk_count": self.current_session.chunk_count
                            })
                
                # Small delay to prevent overwhelming the UI
                time.sleep(0.01)
            
            return True
            
        except Exception as e:
            self.current_session.error_count += 1
            
            if self.current_session.error_count <= self.current_session.max_errors:
                # Try to recover from error
                handle_streaming_error(e, {
                    "operation": "process_streaming_content",
                    "chunk_count": self.current_session.chunk_count,
                    "error_count": self.current_session.error_count,
                    "accumulated_length": len(self.current_session.accumulated_content)
                })
                
                # Attempt to continue streaming
                time.sleep(1)  # Brief pause before retry
                return True
            else:
                # Too many errors, fail the session
                handle_streaming_error(e, {
                    "operation": "process_streaming_content",
                    "error": "max_errors_exceeded",
                    "error_count": self.current_session.error_count
                })
                return False
    
    def _update_streaming_message(self, content: str) -> None:
        """Update the streaming message content"""
        
        try:
            state = state_manager.get_state()
            
            # Find the message being streamed
            for msg in state.messages:
                if msg.id == self.current_session.message_id:
                    msg.content = content
                    break
            
            # Update state
            state_manager.update_state(state)
            
            # Force UI update (in a real implementation, this might use st.rerun())
            # For now, we just update the state
            
        except Exception as e:
            handle_streaming_error(e, {
                "operation": "update_streaming_message",
                "message_id": self.current_session.message_id,
                "content_length": len(content)
            })
    
    def interrupt_streaming(self) -> bool:
        """Request interruption of current streaming session"""
        
        if not self.current_session or self.current_session.state != StreamingState.STREAMING:
            return False
        
        self.interrupt_requested = True
        return True
    
    def _handle_interruption(self) -> None:
        """Handle streaming interruption"""
        
        try:
            # Preserve partial content
            if self.current_session.accumulated_content:
                self._update_streaming_message(self.current_session.accumulated_content)
            
            # Update UI to show interruption
            self._show_interruption_message()
            
            # Clean up
            self._show_typing_indicator(False)
            state_manager.set_streaming_state(False)
            
        except Exception as e:
            handle_streaming_error(e, {
                "operation": "handle_interruption",
                "session_id": self.current_session.session_id
            })
    
    def _handle_streaming_failure(self) -> None:
        """Handle streaming failure"""
        
        try:
            self.current_session.state = StreamingState.ERROR
            
            # Preserve any partial content
            if self.current_session.accumulated_content:
                self._update_streaming_message(self.current_session.accumulated_content)
            
            # Show error message
            st.error("Streaming was interrupted due to an error. Partial content has been preserved.")
            
            # Clean up
            self._cleanup_session()
            
        except Exception as e:
            handle_streaming_error(e, {
                "operation": "handle_streaming_failure",
                "session_id": self.current_session.session_id if self.current_session else "unknown"
            })
    
    def _cleanup_session(self) -> None:
        """Clean up streaming session"""
        
        self._show_typing_indicator(False)
        state_manager.set_streaming_state(False)
        self.interrupt_requested = False
        self.progress_callback = None
        
        if self.current_session:
            self.current_session.state = StreamingState.IDLE
    
    def _show_typing_indicator(self, show: bool) -> None:
        """Show or hide typing indicator"""
        
        self.typing_indicator_active = show
        
        if show:
            # In a real implementation, this would show a typing indicator in the UI
            # For now, we just track the state
            pass
        else:
            # Hide typing indicator
            pass
    
    def _show_interruption_message(self) -> None:
        """Show message about streaming interruption"""
        
        st.info("🛑 Streaming was interrupted. Partial response has been preserved.")
    
    def get_streaming_status(self) -> Dict[str, Any]:
        """Get current streaming status"""
        
        if not self.current_session:
            return {
                "active": False,
                "state": StreamingState.IDLE.value
            }
        
        return {
            "active": self.current_session.state == StreamingState.STREAMING,
            "state": self.current_session.state.value,
            "session_id": self.current_session.session_id,
            "message_id": self.current_session.message_id,
            "model_used": self.current_session.model_used,
            "chunk_count": self.current_session.chunk_count,
            "content_length": len(self.current_session.accumulated_content),
            "duration": time.time() - self.current_session.start_time,
            "error_count": self.current_session.error_count,
            "typing_indicator": self.typing_indicator_active
        }
    
    def is_streaming(self) -> bool:
        """Check if currently streaming"""
        
        return (self.current_session is not None and 
                self.current_session.state == StreamingState.STREAMING)
    
    def get_partial_content(self) -> Optional[str]:
        """Get partial content from current streaming session"""
        
        if self.current_session:
            return self.current_session.accumulated_content
        return None
    
    def pause_streaming(self) -> bool:
        """Pause current streaming session"""
        
        if not self.current_session or self.current_session.state != StreamingState.STREAMING:
            return False
        
        self.current_session.state = StreamingState.PAUSED
        self._show_typing_indicator(False)
        return True
    
    def resume_streaming(self) -> bool:
        """Resume paused streaming session"""
        
        if not self.current_session or self.current_session.state != StreamingState.PAUSED:
            return False
        
        self.current_session.state = StreamingState.STREAMING
        self._show_typing_indicator(True)
        return True
    
    def reset_session(self) -> None:
        """Reset the streaming session"""
        
        if self.current_session:
            self._cleanup_session()
            self.current_session = None


# Global streaming manager instance
streaming_manager = StreamingManager()


# Convenience functions
def start_ai_response_streaming(message_id: str, model_used: str, 
                               content_generator: Generator[str, None, None]) -> bool:
    """Start streaming an AI response"""
    return streaming_manager.start_streaming(message_id, model_used, content_generator)


def interrupt_current_streaming() -> bool:
    """Interrupt the current streaming session"""
    return streaming_manager.interrupt_streaming()


def get_streaming_status() -> Dict[str, Any]:
    """Get current streaming status"""
    return streaming_manager.get_streaming_status()


def is_currently_streaming() -> bool:
    """Check if currently streaming"""
    return streaming_manager.is_streaming()