"""
Enhanced Input Panel Component
Provides modern input interface with file handling and auto-resize functionality
"""

import streamlit as st
from typing import List, Optional, Callable, Dict
from PIL import Image
import io
from ..models import UploadedFile, Attachment
from ..enhanced_state_manager import state_manager
from ..error_handler import handle_upload_error, handle_ui_error, ErrorType, with_error_handling


class InputPanel:
    """Enhanced input interface with file handling and modern UX"""
    
    def __init__(self):
        self.max_files = 10
        self.supported_formats = ["jpg", "jpeg", "png", "webp"]
        self.max_file_size = 10 * 1024 * 1024  # 10MB
        self.auto_resize_enabled = True
    
    def render_input_interface(self, disabled: bool = False) -> tuple[Optional[str], List[Image.Image]]:
        """
        Render the complete input interface with keyboard handling
        
        Args:
            disabled: Whether input should be disabled (e.g., during streaming)
            
        Returns:
            Tuple of (user_input, uploaded_images)
        """
        uploaded_images = []
        
        # Inject keyboard handlers for enhanced interaction
        if not disabled:
            keyboard_js = self.inject_keyboard_handlers()
            # In a real implementation, this would be injected into the page
            # st.components.v1.html(keyboard_js, height=0)
        
        # Render file upload interface
        if not disabled:
            uploaded_images = self._render_file_upload_interface()
        
        # Render text input with keyboard handling
        user_input = self._render_text_input(disabled)
        
        # Handle unsent content protection
        if user_input and self.protect_unsent_content():
            # Content protection is active, handle accordingly
            pass
        
        return user_input, uploaded_images
    
    def _render_file_upload_interface(self) -> List[Image.Image]:
        """Render the file upload interface with drag-and-drop support"""
        
        # Get current uploader key to reset when needed
        state = state_manager.get_state()
        upload_key = f"uploader_{state.uploader_key_id}"
        
        # File upload popover
        with st.popover("📎", use_container_width=False, help="上传参考图片"):
            uploaded_files = st.file_uploader(
                "参考图片",
                type=self.supported_formats,
                accept_multiple_files=True,
                key=upload_key,
                help=f"最多上传 {self.max_files} 张图片 ({', '.join(self.supported_formats)})"
            )
            
            if uploaded_files:
                st.caption(f"已选择 {len(uploaded_files)} 张图片")
                
                # Show image previews
                if len(uploaded_files) <= 4:
                    cols = st.columns(len(uploaded_files))
                    for i, file in enumerate(uploaded_files):
                        with cols[i]:
                            try:
                                img = Image.open(file)
                                st.image(img, use_container_width=True, caption=file.name)
                            except Exception as e:
                                st.error(f"Error loading {file.name}: {e}")
                else:
                    # Grid layout for many images
                    self._render_image_grid(uploaded_files)
        
        # Convert uploaded files to PIL Images
        images = []
        if uploaded_files:
            for file in uploaded_files:
                try:
                    if self._validate_file(file):
                        img = Image.open(file)
                        images.append(img)
                except Exception as e:
                    st.error(f"Error processing {file.name}: {e}")
        
        return images
    
    def _render_image_grid(self, uploaded_files: List) -> None:
        """Render images in a responsive grid layout"""
        
        # Calculate grid dimensions
        cols_per_row = min(4, len(uploaded_files))
        rows = (len(uploaded_files) + cols_per_row - 1) // cols_per_row
        
        for row in range(rows):
            cols = st.columns(cols_per_row)
            for col_idx in range(cols_per_row):
                file_idx = row * cols_per_row + col_idx
                if file_idx < len(uploaded_files):
                    with cols[col_idx]:
                        try:
                            img = Image.open(uploaded_files[file_idx])
                            st.image(img, use_container_width=True, 
                                   caption=uploaded_files[file_idx].name)
                        except Exception as e:
                            st.error(f"Error: {e}")
    
    def _render_text_input(self, disabled: bool = False) -> Optional[str]:
        """Render the text input field with auto-resize and keyboard handling"""
        
        placeholder = "输入您的消息..." if not disabled else "请稍候..."
        
        # Enhanced chat input with keyboard interaction support
        user_input = st.chat_input(
            placeholder=placeholder,
            disabled=disabled,
            key="enhanced_chat_input"
        )
        
        # Note: Message submission is handled by UI controller
        # No need to handle it here to avoid duplicate processing
        
        return user_input
    
    def _handle_message_submission(self, content: str) -> None:
        """Handle message submission with proper state management"""
        
        # Clear any upload queue after successful submission
        state = state_manager.get_state()
        if hasattr(state, 'upload_queue'):
            state.upload_queue.clear()
        
        # Update uploader key to reset file uploader
        state.uploader_key_id += 1
        state_manager.update_state(state)
    
    def enable_auto_resize(self) -> None:
        """Enable auto-resize functionality for the input field"""
        
        self.auto_resize_enabled = True
        
        # In a real implementation, this would inject JavaScript
        # to handle dynamic resizing of the input field
        # For now, we rely on Streamlit's built-in behavior
    
    def disable_auto_resize(self) -> None:
        """Disable auto-resize functionality"""
        
        self.auto_resize_enabled = False
    
    def get_input_field_height(self, content: str) -> int:
        """Calculate appropriate height for input field based on content"""
        
        if not self.auto_resize_enabled:
            return 40  # Default height in pixels
        
        # Calculate height based on content length and line breaks
        lines = content.count('\n') + 1
        base_height = 40
        line_height = 20
        max_height = 200  # Maximum height in pixels
        
        calculated_height = base_height + (lines - 1) * line_height
        return min(calculated_height, max_height)
    
    def inject_keyboard_handlers(self) -> str:
        """Inject JavaScript for enhanced keyboard handling"""
        
        # This would inject custom JavaScript for keyboard event handling
        # For now, we return a placeholder
        
        js_code = """
        <script>
        // Enhanced keyboard handling for AI Studio input
        document.addEventListener('DOMContentLoaded', function() {
            const chatInput = document.querySelector('[data-testid="stChatInput"] textarea');
            
            if (chatInput) {
                // Handle Enter vs Shift+Enter
                chatInput.addEventListener('keydown', function(e) {
                    if (e.key === 'Enter' && !e.shiftKey) {
                        // Enter pressed without Shift - submit message
                        e.preventDefault();
                        // Trigger form submission
                        const form = chatInput.closest('form');
                        if (form) {
                            form.requestSubmit();
                        }
                    }
                    // Shift+Enter allows new line (default behavior)
                });
                
                // Handle Escape key
                chatInput.addEventListener('keydown', function(e) {
                    if (e.key === 'Escape') {
                        // Check for unsent content and show warning if needed
                        if (chatInput.value.trim()) {
                            const confirmed = confirm('Clear unsent content?');
                            if (confirmed) {
                                chatInput.value = '';
                            }
                        }
                    }
                });
                
                // Auto-resize functionality
                chatInput.addEventListener('input', function() {
                    this.style.height = 'auto';
                    this.style.height = Math.min(this.scrollHeight, 200) + 'px';
                });
            }
        });
        </script>
        """
        
        return js_code
    
    def _validate_file(self, file) -> bool:
        """Validate uploaded file"""
        
        try:
            # Check file size
            if hasattr(file, 'size') and file.size > self.max_file_size:
                error_msg = f"File {file.name} is too large. Maximum size: {self.max_file_size // (1024*1024)}MB"
                handle_upload_error(ValueError(error_msg), {
                    "file_name": file.name,
                    "file_size": file.size,
                    "max_size": self.max_file_size
                })
                return False
            
            # Check file type
            if hasattr(file, 'type'):
                file_extension = file.name.split('.')[-1].lower()
                if file_extension not in self.supported_formats:
                    error_msg = f"Unsupported file format: {file_extension}. Supported: {', '.join(self.supported_formats)}"
                    handle_upload_error(ValueError(error_msg), {
                        "file_name": file.name,
                        "file_extension": file_extension,
                        "supported_formats": self.supported_formats
                    })
                    return False
            
            return True
            
        except Exception as e:
            handle_upload_error(e, {"file_name": getattr(file, 'name', 'unknown')})
            return False
    
    def handle_drag_drop(self, files: List) -> List[Image.Image]:
        """Handle drag and drop file upload"""
        
        images = []
        for file in files:
            if self._validate_file(file):
                try:
                    img = Image.open(file)
                    images.append(img)
                except Exception as e:
                    st.error(f"Error processing dropped file {file.name}: {e}")
        
        return images
    
    @with_error_handling(ErrorType.UPLOAD_ERROR)
    def create_attachment(self, file) -> Optional[Attachment]:
        """Create an attachment object from uploaded file"""
        
        try:
            file_data = file.read()
            file.seek(0)  # Reset file pointer
            
            attachment = Attachment(
                id=f"att_{len(file_data)}_{file.name}",
                filename=file.name,
                file_type=file.type if hasattr(file, 'type') else 'unknown',
                size=len(file_data),
                data=file_data
            )
            
            # Create thumbnail for images
            if file.type and file.type.startswith('image/'):
                try:
                    img = Image.open(io.BytesIO(file_data))
                    # Create thumbnail
                    img.thumbnail((150, 150), Image.Resampling.LANCZOS)
                    thumb_buffer = io.BytesIO()
                    img.save(thumb_buffer, format='PNG')
                    attachment.thumbnail = thumb_buffer.getvalue()
                except Exception as thumb_error:
                    # Thumbnail creation failed, continue without it
                    handle_upload_error(thumb_error, {
                        "operation": "thumbnail_creation",
                        "file_name": file.name,
                        "file_type": file.type
                    })
            
            return attachment
            
        except Exception as e:
            handle_upload_error(e, {
                "operation": "create_attachment",
                "file_name": getattr(file, 'name', 'unknown'),
                "file_type": getattr(file, 'type', 'unknown')
            })
            return None
    
    def render_send_button(self, enabled: bool = True) -> bool:
        """Render send button (integrated with chat_input)"""
        # The send functionality is handled by st.chat_input
        # This method is for compatibility and future enhancements
        return enabled
    
    def handle_keyboard_shortcuts(self, key_event: str) -> bool:
        """Handle keyboard shortcuts for input"""
        
        # Enhanced keyboard interaction handling
        # Enter = send message, Shift+Enter = new line
        
        if key_event == "Enter":
            return True  # Send message
        elif key_event == "Shift+Enter":
            return False  # New line (handled by browser)
        elif key_event == "Escape":
            return self._handle_escape_key()
        elif key_event == "Ctrl+A" or key_event == "Cmd+A":
            return self._handle_select_all()
        
        return False
    
    def _handle_escape_key(self) -> bool:
        """Handle Escape key press - clear input or show unsent content warning"""
        
        # Check if there's unsent content
        if self.get_unsent_content_warning():
            # Show confirmation dialog for clearing content
            return self._show_clear_confirmation()
        
        return False
    
    def _handle_select_all(self) -> bool:
        """Handle Ctrl+A / Cmd+A for selecting all text"""
        
        # This would be handled by the browser's native behavior
        # We just return False to let the browser handle it
        return False
    
    def _show_clear_confirmation(self) -> bool:
        """Show confirmation dialog for clearing unsent content"""
        
        # In a real implementation, this would show a modal or confirmation
        # For now, we return False to prevent clearing
        return False
    
    def get_unsent_content_warning(self) -> bool:
        """Check if there's unsent content that might be lost"""
        
        # Check if there's content in the current input state
        # This would be enhanced with actual input tracking
        state = state_manager.get_state()
        
        # Check if there are uploaded files that haven't been sent
        if hasattr(state, 'upload_queue') and state.upload_queue:
            return True
        
        # In a real implementation, we would track the input field content
        # For now, we assume no unsent content unless there are uploads
        return False
    
    def protect_unsent_content(self) -> bool:
        """Protect unsent content from being lost"""
        
        if self.get_unsent_content_warning():
            # In a real implementation, this would show a confirmation dialog
            # For now, we return True to indicate protection is needed
            return True
        
        return False
    
    def confirm_content_loss(self, action: str = "navigate away") -> bool:
        """Show confirmation dialog for potential content loss"""
        
        # This would show a modal dialog in a real implementation
        # For now, we simulate the confirmation logic
        
        if not self.get_unsent_content_warning():
            return True  # No content to lose, allow action
        
        # In a real implementation, this would show:
        # "You have unsent content. Are you sure you want to {action}?"
        # For now, we return False to prevent accidental loss
        return False
    
    def clear_input(self) -> None:
        """Clear the input field"""
        
        # This is handled automatically by st.chat_input after sending
        # But we can trigger a rerun to reset the uploader
        state = state_manager.get_state()
        state.uploader_key_id += 1
        state_manager.update_state(state)
    
    def set_auto_resize(self, enabled: bool) -> None:
        """Enable or disable auto-resize functionality"""
        self.auto_resize_enabled = enabled
    
    def set_max_files(self, max_files: int) -> None:
        """Set maximum number of files that can be uploaded"""
        self.max_files = max_files
    
    def add_supported_format(self, format_ext: str) -> None:
        """Add a supported file format"""
        if format_ext.lower() not in self.supported_formats:
            self.supported_formats.append(format_ext.lower())
    
    def setup_beforeunload_protection(self) -> str:
        """Setup browser beforeunload protection for unsent content"""
        
        # JavaScript to protect against accidental navigation
        protection_js = """
        <script>
        window.addEventListener('beforeunload', function(e) {
            const chatInput = document.querySelector('[data-testid="stChatInput"] textarea');
            const hasUnsentContent = chatInput && chatInput.value.trim().length > 0;
            
            // Check for uploaded files that haven't been sent
            const fileInputs = document.querySelectorAll('input[type="file"]');
            let hasUnsentFiles = false;
            fileInputs.forEach(input => {
                if (input.files && input.files.length > 0) {
                    hasUnsentFiles = true;
                }
            });
            
            if (hasUnsentContent || hasUnsentFiles) {
                const message = 'You have unsent content. Are you sure you want to leave?';
                e.preventDefault();
                e.returnValue = message;
                return message;
            }
        });
        </script>
        """
        
        return protection_js
    
    def handle_enter_key_submission(self, content: str) -> bool:
        """Handle Enter key submission with validation"""
        
        # Validate content before submission
        if not content or not content.strip():
            return False  # Don't submit empty content
        
        # Check if Shift was held (would be passed as parameter in real implementation)
        # For now, we assume Enter without Shift means submit
        return True
    
    def handle_shift_enter_newline(self) -> bool:
        """Handle Shift+Enter for new line insertion"""
        
        # This is handled by the browser's default behavior
        # We just return True to indicate the event was handled
        return True
    
    def get_keyboard_shortcuts_help(self) -> Dict[str, str]:
        """Get help text for keyboard shortcuts"""
        
        return {
            "Enter": "Send message",
            "Shift+Enter": "New line",
            "Escape": "Clear input (with confirmation)",
            "Ctrl+A / Cmd+A": "Select all text"
        }
    
    def is_auto_resize_enabled(self) -> bool:
        """Check if auto-resize is currently enabled"""
        return self.auto_resize_enabled
    
    def validate_keyboard_input(self, key_event: str, content: str) -> bool:
        """Validate keyboard input before processing"""
        
        # Basic validation for keyboard events
        valid_keys = ["Enter", "Shift+Enter", "Escape", "Ctrl+A", "Cmd+A"]
        
        if key_event not in valid_keys:
            return False
        
        # Additional validation based on content
        if key_event == "Enter" and not content.strip():
            return False  # Don't allow empty submissions
        
        return True


# Global instance for easy access
input_panel = InputPanel()
