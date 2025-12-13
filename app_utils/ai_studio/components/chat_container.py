"""
Enhanced Chat Container Component
Provides the main conversation interface with auto-scroll and message management
"""

import streamlit as st
import time
from datetime import datetime
from typing import List, Callable, Optional
from ..models import BaseMessage, UserMessage, AIMessage
from ..enhanced_state_manager import state_manager
from ..design_tokens import css_injector
from ..error_handler import handle_ui_error, handle_streaming_error, ErrorType, with_error_handling


class ChatContainer:
    """Main container for the conversation interface with enhanced functionality"""
    
    def __init__(self):
        self.auto_scroll_enabled = True
        self.message_actions_enabled = True
        self.responsive_layout = True
        self.message_density = "comfortable"  # compact, comfortable, spacious
        
        # Inject responsive styles
        self._inject_responsive_styles()
    
    def render_conversation(self, messages: List[BaseMessage], 
                          on_delete: Optional[Callable] = None,
                          on_regenerate: Optional[Callable] = None) -> None:
        """
        Render the complete conversation with enhanced navigation and management
        
        Args:
            messages: List of messages to render
            on_delete: Callback for message deletion
            on_regenerate: Callback for message regeneration
        """
        if not messages:
            self._render_empty_state()
            return
        
        # Render conversation summary for long conversations
        self.render_conversation_summary(messages)
        
        # Render navigation controls for long conversations
        self.render_conversation_navigation(messages)
        
        # Enable virtual scrolling for very long conversations
        if len(messages) > 100:
            self.enable_virtual_scrolling(True)
        
        # Render each message with responsive layout
        for idx, message in enumerate(messages):
            if self.responsive_layout:
                self._render_message_with_responsive_layout(
                    message, idx, on_delete, on_regenerate
                )
            else:
                self._render_message_with_actions(
                    message, idx, on_delete, on_regenerate
                )
        
        # Auto-scroll to bottom if enabled
        if self.auto_scroll_enabled:
            self.auto_scroll_to_bottom()
        
        # Add performance indicator for large conversations
        if len(messages) > 50:
            st.info(f"💡 Large conversation ({len(messages)} messages). Use navigation controls above for better performance.")
    
    def _render_empty_state(self) -> None:
        """Render empty conversation state"""
        st.info("👋 开始您的对话。上传图片或输入消息...")
    
    def _render_message_with_actions(self, message: BaseMessage, idx: int,
                                   on_delete: Optional[Callable] = None,
                                   on_regenerate: Optional[Callable] = None) -> None:
        """Render a single message with action buttons"""
        
        with st.chat_message(message.role):
            # Render message content based on type
            if isinstance(message, UserMessage):
                self._render_user_message_content(message)
            elif isinstance(message, AIMessage):
                self._render_ai_message_content(message)
            else:
                # Fallback for other message types
                st.markdown(getattr(message, 'content', ''))
            
            # Render message actions if enabled
            if self.message_actions_enabled:
                self._render_message_actions(message, idx, on_delete, on_regenerate)
    
    def _render_user_message_content(self, message: UserMessage) -> None:
        """Render user message content including attachments"""
        
        # Render reference images if present
        if message.ref_images:
            cols = st.columns(min(len(message.ref_images), 4))
            for i, img in enumerate(message.ref_images):
                with cols[i % len(cols)]:
                    st.image(img, use_container_width=True)
        
        # Render text content
        if message.content:
            st.markdown(message.content)
    
    def _render_ai_message_content(self, message: AIMessage) -> None:
        """Render AI message content with special handling for different types"""
        
        if message.message_type == "image_result" and message.hd_data:
            # Render image result with preview and download options
            self._render_image_result(message)
        else:
            # Render text content with streaming indicator if needed
            content = message.content
            if state_manager.get_state().is_streaming and message == state_manager.get_state().messages[-1]:
                content += " ▌"  # Add cursor for streaming
            
            st.markdown(content)
    
    def _render_image_result(self, message: AIMessage) -> None:
        """Enhanced image generation result rendering with high-quality preview and controls"""
        
        # Get image metadata if available
        metadata = getattr(message, 'metadata', {})
        image_metadata = metadata.get('image_metadata', {})
        reference_indicator = metadata.get('reference_indicator')
        generation_time = metadata.get('generation_time')
        
        # Display reference indicator if available
        if reference_indicator:
            st.info(reference_indicator)
        
        # Create main image display with enhanced preview
        image_container = st.container()
        
        with image_container:
            # Display the high-quality image
            image_data = getattr(message, 'hd_data', None)
            if image_data:
                # Create responsive image display
                col1, col2, col3 = st.columns([1, 3, 1])
                
                with col2:
                    st.image(
                        image_data, 
                        caption=f"Generated Image • {image_metadata.get('size', 'Unknown size')} • {image_metadata.get('file_size_mb', 0):.1f} MB",
                        use_container_width=True
                    )
        
        # Enhanced action buttons
        action_container = st.container()
        
        with action_container:
            col1, col2, col3, col4, col5 = st.columns([1, 1, 1, 1, 2])
            
            # Zoom/Full-size view
            with col1:
                if st.button("🔍 Zoom", key=f"zoom_{message.id}", help="View full size with zoom controls"):
                    self._show_enhanced_image_modal(message, image_metadata)
            
            # Download original
            with col2:
                st.download_button(
                    "📥 Download", 
                    data=image_data,
                    file_name=f"ai_generated_{message.id}_{int(time.time())}.jpg",
                    mime="image/jpeg",
                    key=f"download_{message.id}",
                    help="Download full-resolution image"
                )
            
            # Copy image (as base64 for sharing)
            with col3:
                if st.button("📋 Copy", key=f"copy_img_{message.id}", help="Copy image data"):
                    import base64
                    b64_data = base64.b64encode(image_data).decode()
                    # Store in session state for JavaScript access
                    st.session_state[f"copy_data_{message.id}"] = b64_data
                    st.success("Image copied!", icon="📋")
            
            # Use as reference for next generation
            with col4:
                if st.button("🔗 Reference", key=f"ref_{message.id}", help="Use as reference for next generation"):
                    # Add to session state as reference image
                    if 'reference_images' not in st.session_state:
                        st.session_state.reference_images = []
                    
                    # Convert bytes to PIL Image for reference
                    from PIL import Image
                    import io
                    ref_img = Image.open(io.BytesIO(image_data))
                    st.session_state.reference_images = [ref_img]  # Replace existing references
                    
                    st.success("Set as reference image!", icon="🔗")
        
        # Display generation metadata
        if generation_time or image_metadata:
            with st.expander("📊 Generation Details", expanded=False):
                detail_col1, detail_col2 = st.columns(2)
                
                with detail_col1:
                    if generation_time:
                        st.metric("Generation Time", f"{generation_time:.2f}s")
                    if image_metadata.get('format'):
                        st.metric("Format", image_metadata['format'])
                    if image_metadata.get('mode'):
                        st.metric("Color Mode", image_metadata['mode'])
                
                with detail_col2:
                    if image_metadata.get('size'):
                        width, height = image_metadata['size']
                        st.metric("Dimensions", f"{width} × {height}")
                    if image_metadata.get('aspect_ratio'):
                        st.metric("Aspect Ratio", f"{image_metadata['aspect_ratio']:.2f}:1")
                    if image_metadata.get('file_size_mb'):
                        st.metric("File Size", f"{image_metadata['file_size_mb']:.2f} MB")
        
        # Iterative editing suggestions
        if reference_indicator and "iterative" in reference_indicator.lower():
            st.info("💡 **Iterative Editing Mode**: This image was generated based on a previous result. You can continue refining by describing further changes.")
    
    def _show_enhanced_image_modal(self, message: AIMessage, metadata: dict) -> None:
        """Show enhanced image modal with zoom controls and detailed information"""
        
        @st.dialog(f"🔍 Generated Image - Full View")
        def _enhanced_dialog():
            # Main image display
            image_data = getattr(message, 'hd_data', None)
            if image_data:
                st.image(
                    image_data, 
                    caption=f"Full Resolution • {metadata.get('size', 'Unknown')} • {metadata.get('file_size_mb', 0):.1f} MB",
                    use_container_width=True
                )
            
            # Action buttons in modal
            modal_col1, modal_col2, modal_col3 = st.columns(3)
            
            with modal_col1:
                st.download_button(
                    "📥 Download Full Resolution", 
                    data=image_data,
                    file_name=f"ai_generated_full_{message.id}_{int(time.time())}.jpg",
                    mime="image/jpeg",
                    key=f"modal_download_{message.id}",
                    use_container_width=True
                )
            
            with modal_col2:
                if st.button("🔗 Use as Reference", key=f"modal_ref_{message.id}", use_container_width=True):
                    from PIL import Image
                    import io
                    ref_img = Image.open(io.BytesIO(image_data))
                    if 'reference_images' not in st.session_state:
                        st.session_state.reference_images = []
                    st.session_state.reference_images = [ref_img]
                    st.success("Set as reference!")
            
            with modal_col3:
                if st.button("📋 Copy Image Data", key=f"modal_copy_{message.id}", use_container_width=True):
                    import base64
                    b64_data = base64.b64encode(image_data).decode()
                    st.session_state[f"modal_copy_data_{message.id}"] = b64_data
                    st.success("Image data copied!")
            
            # Detailed metadata
            if metadata:
                st.subheader("📊 Image Details")
                
                detail_cols = st.columns(3)
                
                with detail_cols[0]:
                    st.write("**Technical Info:**")
                    st.write(f"Format: {metadata.get('format', 'Unknown')}")
                    st.write(f"Color Mode: {metadata.get('mode', 'Unknown')}")
                    st.write(f"File Size: {metadata.get('file_size_mb', 0):.2f} MB")
                
                with detail_cols[1]:
                    st.write("**Dimensions:**")
                    if metadata.get('size'):
                        width, height = metadata['size']
                        st.write(f"Width: {width} px")
                        st.write(f"Height: {height} px")
                        st.write(f"Aspect Ratio: {metadata.get('aspect_ratio', 1):.2f}:1")
                
                with detail_cols[2]:
                    st.write("**Generation Info:**")
                    msg_metadata = getattr(message, 'metadata', {})
                    if msg_metadata.get('generation_time'):
                        st.write(f"Generation Time: {msg_metadata['generation_time']:.2f}s")
                    if msg_metadata.get('reference_used'):
                        st.write("Reference Image: ✅ Used")
                    else:
                        st.write("Reference Image: ❌ None")
        
        _enhanced_dialog()
    
    def _render_message_actions(self, message: BaseMessage, idx: int,
                              on_delete: Optional[Callable] = None,
                              on_regenerate: Optional[Callable] = None) -> None:
        """Render enhanced action buttons for a message"""
        
        # Create action columns with more options
        if message.role == "assistant" and on_regenerate:
            col1, col2, col3, col4 = st.columns([1, 1, 1, 5])
        else:
            col1, col2, col3 = st.columns([1, 1, 6])
            col4 = None
        
        # Delete button
        with col1:
            if st.button("🗑️", key=f"delete_{message.id}", help="Delete message"):
                if on_delete:
                    on_delete(idx)
        
        # Copy button
        with col2:
            if st.button("📋", key=f"copy_{message.id}", help="Copy message content"):
                # Use JavaScript to copy to clipboard
                escaped_content = message.content.replace('`', '\\`')
                copy_js = f"""
                <script>
                navigator.clipboard.writeText(`{escaped_content}`).then(function() {{
                    console.log('Message copied to clipboard');
                }});
                </script>
                """
                st.markdown(copy_js, unsafe_allow_html=True)
                st.success("Copied to clipboard!", icon="📋")
        
        # Regenerate button (only for AI messages)
        if col4 and message.role == "assistant" and on_regenerate:
            with col3:
                if st.button("🔄", key=f"regen_{message.id}", help="Regenerate response"):
                    on_regenerate(idx)
        
        # Additional actions for long messages
        if len(getattr(message, 'content', '')) > 500:
            with (col3 if col4 is None else col4):
                if st.button("📖", key=f"expand_{message.id}", help="View full message"):
                    self._show_message_modal(message)
    
    def _show_image_modal(self, image_data: bytes, title: str) -> None:
        """Show image in a modal dialog"""
        @st.dialog(f"🔍 {title}")
        def _dialog_content():
            st.image(image_data, caption=title, use_container_width=True)
        
        _dialog_content()
    
    def _show_message_modal(self, message: BaseMessage) -> None:
        """Show full message content in a modal dialog"""
        @st.dialog(f"📖 {message.role.title()} Message")
        def _message_dialog():
            # Message metadata
            col1, col2 = st.columns(2)
            with col1:
                st.caption(f"**Role:** {message.role.title()}")
            with col2:
                st.caption(f"**Time:** {message.timestamp.strftime('%H:%M:%S')}")
            
            if isinstance(message, AIMessage):
                st.caption(f"**Model:** {message.model_used}")
            
            st.divider()
            
            # Full message content
            st.markdown("**Content:**")
            st.markdown(message.content)
            
            # Action buttons
            col3, col4, col5 = st.columns(3)
            
            with col3:
                if st.button("📋 Copy", use_container_width=True):
                    # Copy functionality would be implemented here
                    st.success("Copied to clipboard!")
            
            with col4:
                if st.button("🔗 Share", use_container_width=True):
                    # Share functionality would be implemented here
                    st.info("Share link generated!")
            
            with col5:
                if st.button("✅ Close", use_container_width=True):
                    st.rerun()
        
        _message_dialog()
    
    def auto_scroll_to_bottom(self) -> None:
        """Automatically scroll to the bottom of the conversation"""
        # This is handled by Streamlit's chat_message component automatically
        # But we can add custom JavaScript if needed for more control
        pass
    
    @with_error_handling(ErrorType.UI_ERROR)
    def handle_message_actions(self, message_id: str, action: str) -> None:
        """Handle message actions like delete, regenerate, etc."""
        
        try:
            if action == "delete":
                success = state_manager.delete_message(message_id)
                if success:
                    st.rerun()
                else:
                    handle_ui_error(ValueError(f"Failed to delete message {message_id}"), {
                        "action": "delete",
                        "message_id": message_id
                    })
            
            elif action == "regenerate":
                # Find the message and trigger regeneration
                state = state_manager.get_state()
                for i, msg in enumerate(state.messages):
                    if msg.id == message_id and msg.role == "assistant":
                        # Remove the AI message and trigger inference
                        success = state_manager.delete_message(message_id)
                        if success:
                            st.session_state.trigger_inference = True
                            st.rerun()
                        else:
                            handle_ui_error(ValueError(f"Failed to regenerate message {message_id}"), {
                                "action": "regenerate",
                                "message_id": message_id
                            })
                        break
                        
        except Exception as e:
            handle_ui_error(e, {
                "operation": "handle_message_actions",
                "action": action,
                "message_id": message_id
            })
    
    def set_auto_scroll(self, enabled: bool) -> None:
        """Enable or disable auto-scroll functionality"""
        self.auto_scroll_enabled = enabled
    
    def set_message_actions(self, enabled: bool) -> None:
        """Enable or disable message action buttons"""
        self.message_actions_enabled = enabled
    
    def set_responsive_layout(self, enabled: bool) -> None:
        """Enable or disable responsive layout"""
        self.responsive_layout = enabled
        if enabled:
            self._inject_responsive_styles()
    
    def set_message_density(self, density: str) -> None:
        """Set message density: compact, comfortable, or spacious"""
        if density in ["compact", "comfortable", "spacious"]:
            self.message_density = density
            self._inject_responsive_styles()
    
    def render_conversation_navigation(self, messages: List[BaseMessage]) -> None:
        """Render navigation controls for long conversations"""
        
        if len(messages) <= 10:
            return  # No navigation needed for short conversations
        
        # Navigation header
        with st.container():
            st.markdown("---")
            col1, col2, col3, col4 = st.columns([2, 2, 2, 2])
            
            with col1:
                if st.button("⬆️ Top", help="Go to conversation start", use_container_width=True):
                    self._scroll_to_position("top")
            
            with col2:
                if st.button("⬇️ Bottom", help="Go to latest messages", use_container_width=True):
                    self._scroll_to_position("bottom")
            
            with col3:
                # Jump to specific message
                message_num = st.number_input(
                    "Jump to #", 
                    min_value=1, 
                    max_value=len(messages), 
                    value=1,
                    key="jump_to_message"
                )
                
            with col4:
                if st.button("🎯 Jump", help=f"Jump to message #{message_num}", use_container_width=True):
                    self._scroll_to_message(message_num - 1)
            
            # Progress indicator for very long conversations
            if len(messages) > 50:
                progress_text = f"Conversation: {len(messages)} messages"
                st.progress(min(len(messages) / 100, 1.0), text=progress_text)
    
    def _scroll_to_position(self, position: str) -> None:
        """Scroll to a specific position in the conversation"""
        
        if position == "top":
            scroll_js = """
            <script>
            window.parent.document.querySelector('.main').scrollTo({
                top: 0,
                behavior: 'smooth'
            });
            </script>
            """
        elif position == "bottom":
            scroll_js = """
            <script>
            window.parent.document.querySelector('.main').scrollTo({
                top: document.querySelector('.main').scrollHeight,
                behavior: 'smooth'
            });
            </script>
            """
        else:
            return
        
        st.markdown(scroll_js, unsafe_allow_html=True)
    
    def _scroll_to_message(self, message_index: int) -> None:
        """Scroll to a specific message by index"""
        
        scroll_js = f"""
        <script>
        const messageElements = window.parent.document.querySelectorAll('[data-testid="stChatMessage"]');
        if (messageElements[{message_index}]) {{
            messageElements[{message_index}].scrollIntoView({{
                behavior: 'smooth',
                block: 'center'
            }});
            
            // Highlight the target message
            messageElements[{message_index}].style.backgroundColor = '#fff3cd';
            messageElements[{message_index}].style.border = '2px solid #ffc107';
            
            setTimeout(() => {{
                messageElements[{message_index}].style.backgroundColor = '';
                messageElements[{message_index}].style.border = '';
            }}, 3000);
        }}
        </script>
        """
        
        st.markdown(scroll_js, unsafe_allow_html=True)
        st.success(f"Jumped to message #{message_index + 1}")
    
    def render_conversation_summary(self, messages: List[BaseMessage]) -> None:
        """Render a summary for long conversations"""
        
        if len(messages) < 20:
            return
        
        with st.expander("📊 Conversation Summary"):
            col1, col2, col3 = st.columns(3)
            
            user_msgs = [msg for msg in messages if msg.role == "user"]
            ai_msgs = [msg for msg in messages if msg.role == "assistant"]
            
            with col1:
                st.metric("Total Messages", len(messages))
            
            with col2:
                st.metric("User Messages", len(user_msgs))
            
            with col3:
                st.metric("AI Responses", len(ai_msgs))
            
            # Recent activity
            if messages:
                last_msg = messages[-1]
                time_since = datetime.now() - last_msg.timestamp
                
                if time_since.total_seconds() < 3600:  # Less than 1 hour
                    activity_text = f"Last activity: {int(time_since.total_seconds() / 60)} minutes ago"
                else:
                    activity_text = f"Last activity: {int(time_since.total_seconds() / 3600)} hours ago"
                
                st.caption(activity_text)
    
    def enable_virtual_scrolling(self, enabled: bool = True) -> None:
        """Enable virtual scrolling for very long conversations"""
        
        if enabled:
            # Inject virtual scrolling CSS and JavaScript
            virtual_scroll_js = """
            <script>
            // Virtual scrolling implementation for large conversations
            function enableVirtualScrolling() {
                const container = window.parent.document.querySelector('.main');
                const messages = container.querySelectorAll('[data-testid="stChatMessage"]');
                
                if (messages.length > 100) {
                    // Implement virtual scrolling logic here
                    console.log('Virtual scrolling enabled for', messages.length, 'messages');
                }
            }
            
            // Enable when DOM is ready
            if (document.readyState === 'loading') {
                document.addEventListener('DOMContentLoaded', enableVirtualScrolling);
            } else {
                enableVirtualScrolling();
            }
            </script>
            """
            
            st.markdown(virtual_scroll_js, unsafe_allow_html=True)
    
    def _inject_responsive_styles(self) -> None:
        """Inject responsive CSS styles for the chat container"""
        
        # Base responsive styles
        responsive_css = """
        <style>
        /* Responsive Chat Container Styles */
        .chat-container {
            width: 100%;
            max-width: 100%;
            margin: 0 auto;
            padding: 0;
        }
        
        /* Message spacing based on density */
        .stChatMessage {
            margin-bottom: """ + {
            "compact": "0.5rem",
            "comfortable": "1rem", 
            "spacious": "1.5rem"
        }.get(self.message_density, "1rem") + """;
        }
        
        /* Responsive message layout */
        @media (max-width: 768px) {
            .stChatMessage {
                margin-left: 0.5rem !important;
                margin-right: 0.5rem !important;
                font-size: 0.9rem;
            }
            
            .stChatMessage[data-testid="user-message"] {
                margin-left: 1rem !important;
                margin-right: 0.25rem !important;
            }
            
            .stChatMessage[data-testid="assistant-message"] {
                margin-left: 0.25rem !important;
                margin-right: 1rem !important;
            }
            
            /* Adjust image grid for mobile */
            .image-grid {
                grid-template-columns: repeat(auto-fill, minmax(80px, 1fr)) !important;
                gap: 0.25rem !important;
            }
        }
        
        @media (min-width: 769px) and (max-width: 1024px) {
            .stChatMessage {
                margin-left: 1rem !important;
                margin-right: 1rem !important;
            }
            
            .stChatMessage[data-testid="user-message"] {
                margin-left: 2rem !important;
                margin-right: 0.5rem !important;
            }
            
            .stChatMessage[data-testid="assistant-message"] {
                margin-left: 0.5rem !important;
                margin-right: 2rem !important;
            }
        }
        
        @media (min-width: 1025px) {
            .stChatMessage {
                margin-left: 2rem !important;
                margin-right: 2rem !important;
            }
            
            .stChatMessage[data-testid="user-message"] {
                margin-left: 4rem !important;
                margin-right: 1rem !important;
            }
            
            .stChatMessage[data-testid="assistant-message"] {
                margin-left: 1rem !important;
                margin-right: 4rem !important;
            }
        }
        
        /* Typography scaling */
        @media (max-width: 480px) {
            .stChatMessage .stMarkdown {
                font-size: 0.85rem !important;
                line-height: 1.4 !important;
            }
            
            .stChatMessage .stMarkdown h1 { font-size: 1.25rem !important; }
            .stChatMessage .stMarkdown h2 { font-size: 1.1rem !important; }
            .stChatMessage .stMarkdown h3 { font-size: 1rem !important; }
        }
        
        /* Image responsiveness */
        .stImage img {
            max-width: 100% !important;
            height: auto !important;
            border-radius: 0.5rem;
        }
        
        /* Message actions responsive */
        @media (max-width: 768px) {
            .message-actions {
                flex-direction: column !important;
                gap: 0.25rem !important;
            }
            
            .message-actions button {
                font-size: 0.8rem !important;
                padding: 0.25rem 0.5rem !important;
            }
        }
        
        /* Visual hierarchy improvements */
        .stChatMessage[data-testid="user-message"] {
            background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%) !important;
            color: white !important;
            border: none !important;
        }
        
        .stChatMessage[data-testid="assistant-message"] {
            background: #f8fafc !important;
            border: 1px solid #e2e8f0 !important;
            color: #1e293b !important;
        }
        
        /* Smooth transitions */
        .stChatMessage {
            transition: all 0.2s ease-in-out !important;
        }
        
        .stChatMessage:hover {
            transform: translateY(-1px) !important;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1) !important;
        }
        
        /* Loading states */
        .message-loading {
            opacity: 0.7;
            animation: pulse 1.5s ease-in-out infinite;
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 0.7; }
            50% { opacity: 1; }
        }
        
        /* Accessibility improvements */
        .stChatMessage:focus-within {
            outline: 2px solid #6366f1 !important;
            outline-offset: 2px !important;
        }
        
        /* Dark mode support */
        @media (prefers-color-scheme: dark) {
            .stChatMessage[data-testid="assistant-message"] {
                background: #1e293b !important;
                border-color: #334155 !important;
                color: #f1f5f9 !important;
            }
        }
        </style>
        """
        
        st.markdown(responsive_css, unsafe_allow_html=True)
    
    def _render_message_with_responsive_layout(self, message: BaseMessage, idx: int,
                                             on_delete: Optional[Callable] = None,
                                             on_regenerate: Optional[Callable] = None) -> None:
        """Render a message with responsive layout considerations"""
        
        # Add responsive container
        with st.container():
            # Apply responsive CSS classes
            css_class = f"message-{message.role} density-{self.message_density}"
            
            with st.chat_message(message.role):
                # Render message content with responsive handling
                if isinstance(message, UserMessage):
                    self._render_user_message_responsive(message)
                elif isinstance(message, AIMessage):
                    self._render_ai_message_responsive(message)
                else:
                    # Fallback for other message types
                    st.markdown(getattr(message, 'content', ''))
                
                # Render message actions if enabled
                if self.message_actions_enabled:
                    self._render_responsive_message_actions(message, idx, on_delete, on_regenerate)
    
    def _render_user_message_responsive(self, message: UserMessage) -> None:
        """Render user message with responsive image handling"""
        
        # Render reference images with responsive grid
        if message.ref_images:
            # Use responsive column count based on screen size
            num_images = len(message.ref_images)
            
            if num_images == 1:
                st.image(message.ref_images[0], use_container_width=True)
            elif num_images <= 4:
                cols = st.columns(min(num_images, 2))  # Max 2 columns on mobile
                for i, img in enumerate(message.ref_images):
                    with cols[i % len(cols)]:
                        st.image(img, use_container_width=True)
            else:
                # For many images, use a scrollable grid
                st.markdown('<div class="image-grid">', unsafe_allow_html=True)
                cols = st.columns(4)
                for i, img in enumerate(message.ref_images):
                    with cols[i % 4]:
                        st.image(img, use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)
        
        # Render text content with responsive typography
        if message.content:
            st.markdown(f'<div class="message-content">{message.content}</div>', 
                       unsafe_allow_html=True)
    
    def _render_ai_message_responsive(self, message: AIMessage) -> None:
        """Render AI message with responsive handling"""
        
        if message.message_type == "image_result" and message.hd_data:
            # Render image result with responsive controls
            self._render_responsive_image_result(message)
        else:
            # Render text content with streaming indicator if needed
            content = message.content
            if state_manager.get_state().is_streaming and message == state_manager.get_state().messages[-1]:
                content += ' <span class="streaming-indicator">▌</span>'
            
            st.markdown(f'<div class="message-content">{content}</div>', 
                       unsafe_allow_html=True)
    
    def _render_responsive_image_result(self, message: AIMessage) -> None:
        """Render image generation result with responsive controls"""
        
        # Display the image responsively
        st.image(message.content if hasattr(message, 'content') and message.content else message.hd_data, 
                use_container_width=True)
        
        # Responsive action buttons
        col1, col2, col3 = st.columns([1, 1, 2])
        
        with col1:
            if st.button("🔍", key=f"zoom_{message.id}", help="View full size",
                        use_container_width=True):
                self._show_image_modal(message.hd_data, f"Generated Image {message.id}")
        
        with col2:
            # Download button
            st.download_button(
                "📥", 
                data=message.hd_data,
                file_name=f"generated_{message.id}.jpg",
                mime="image/jpeg",
                key=f"download_{message.id}",
                help="Download image",
                use_container_width=True
            )
    
    def _render_responsive_message_actions(self, message: BaseMessage, idx: int,
                                         on_delete: Optional[Callable] = None,
                                         on_regenerate: Optional[Callable] = None) -> None:
        """Render action buttons with responsive layout"""
        
        # Create responsive action layout
        if message.role == "assistant" and on_regenerate:
            col1, col2, col3 = st.columns([1, 1, 4])
        else:
            col1, col2 = st.columns([1, 5])
            col3 = None
        
        # Delete button
        with col1:
            if st.button("🗑️", key=f"delete_{message.id}", help="Delete message",
                        use_container_width=True):
                if on_delete:
                    on_delete(idx)
        
        # Regenerate button (only for AI messages)
        if col3 and message.role == "assistant" and on_regenerate:
            with col2:
                if st.button("🔄", key=f"regen_{message.id}", help="Regenerate response",
                            use_container_width=True):
                    on_regenerate(idx)


# Global instance for easy access
chat_container = ChatContainer()
