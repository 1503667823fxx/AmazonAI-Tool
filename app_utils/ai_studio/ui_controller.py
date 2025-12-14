"""
UI Controller for AI Studio Enhancement
Coordinates all UI components and manages complex interactions
"""

import streamlit as st
from typing import Dict, Any, Optional, Callable
from .models import ConversationState
from .enhanced_state_manager import state_manager
from .components.chat_container import chat_container
from .components.input_panel import input_panel
from .components.model_selector import model_selector
from .design_tokens import inject_modern_styles


class UIController:
    """Central controller for AI Studio UI components and interactions"""
    
    def __init__(self):
        self.initialized = False
        self.callbacks = {}
        self.streaming_active = False
    
    def initialize(self) -> None:
        """Initialize the UI controller and all components"""
        
        if not self.initialized:
            # Initialize state management
            state_manager.initialize_state()
            
            # Inject modern CSS styles
            inject_modern_styles()
            
            # Set up default callbacks
            self._setup_default_callbacks()
            
            self.initialized = True
    
    def render_main_interface(self) -> None:
        """Render the complete AI Studio interface"""
        
        # Ensure initialization
        self.initialize()
        
        # Get current state
        state = state_manager.get_state()
        
        # Render sidebar with model selection and controls
        self._render_sidebar()
        
        # Render main chat area
        self._render_chat_area(state)
        
        # Render input area first (always show unless explicitly streaming)
        if not state.is_streaming:
            self._render_input_area()
        
        # Handle inference if triggered (after input area is rendered)
        if st.session_state.get("trigger_inference", False):
            self._handle_inference()
    
    def _render_sidebar(self) -> None:
        """Render the sidebar with model selection and controls"""
        
        with st.sidebar:
            st.title("🧪 AI 工作台")
            
            # Model selection
            current_model, is_image_mode = model_selector.render_model_selector()
            
            st.divider()
            
            # System prompt editor (for non-image models)
            if not is_image_mode:
                model_selector.render_system_prompt_editor(current_model)
            
            st.divider()
            
            # Conversation controls
            self._render_conversation_controls()
            
            # Optional: Model comparison
            model_selector.render_model_comparison()
    
    def _render_conversation_controls(self) -> None:
        """Render enhanced conversation management controls"""
        
        st.subheader("💬 对话管理")
        
        state = state_manager.get_state()
        
        # Primary controls
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🧹 Clear", help="Clear conversation history", use_container_width=True):
                self._handle_clear_conversation_with_confirmation()
        
        with col2:
            if st.button("↩️ Undo", help="Undo last exchange", use_container_width=True):
                self._handle_undo_last_turn()
        
        # Advanced controls for longer conversations
        if len(state.messages) > 10:
            st.divider()
            st.caption("📊 Navigation")
            
            # Conversation navigation for long conversations
            col3, col4 = st.columns(2)
            
            with col3:
                if st.button("⬆️ Top", help="Scroll to conversation start", use_container_width=True):
                    self._handle_scroll_to_top()
            
            with col4:
                if st.button("⬇️ Bottom", help="Scroll to latest messages", use_container_width=True):
                    self._handle_scroll_to_bottom()
            
            # Message search for very long conversations
            if len(state.messages) > 20:
                search_query = st.text_input("🔍 Search messages", placeholder="Search in conversation...")
                if search_query:
                    self._handle_message_search(search_query)
        
        # Message count and statistics
        if state.messages:
            user_count = len([msg for msg in state.messages if msg.role == "user"])
            ai_count = len([msg for msg in state.messages if msg.role == "assistant"])
            
            st.caption(f"Messages: {len(state.messages)} ({user_count} user, {ai_count} AI)")
            
            # Performance indicator for large conversations
            if len(state.messages) > 50:
                st.info("💡 Large conversation detected. Consider exporting or clearing old messages for better performance.")
        
        # Export conversation
        if state.messages:
            with st.expander("📤 Export & Backup"):
                col5, col6 = st.columns(2)
                
                with col5:
                    if st.button("Export JSON", use_container_width=True):
                        json_data = state_manager.export_conversation_json()
                        st.download_button(
                            "Download JSON",
                            data=json_data,
                            file_name="conversation.json",
                            mime="application/json"
                        )
                
                with col6:
                    if st.button("Save Backup", help="Save conversation backup", use_container_width=True):
                        self._handle_save_conversation_backup()
    
    def _render_chat_area(self, state: ConversationState) -> None:
        """Render the main chat conversation area"""
        
        # Render conversation using chat container
        chat_container.render_conversation(
            messages=state.messages,
            on_delete=self._handle_message_delete,
            on_regenerate=self._handle_message_regenerate
        )
    
    def _render_input_area(self) -> None:
        """Render the input area for user messages"""
        
        state = state_manager.get_state()
        
        # Check if input should be disabled
        input_disabled = state.is_streaming
        
        # Render input interface
        user_input, uploaded_images = input_panel.render_input_interface(disabled=input_disabled)
        
        # Handle user input
        if user_input:
            self._handle_user_input(user_input, uploaded_images)
    
    def _handle_user_input(self, user_input: str, uploaded_images: list) -> None:
        """Handle new user input"""
        
        # Add user message to conversation
        message_id = state_manager.add_user_message(user_input, uploaded_images)
        
        # Reset file uploader to clear uploaded files from UI
        if uploaded_images:  # Only reset if there were uploaded images
            state = state_manager.get_state()
            state.uploader_key_id += 1
            state_manager.update_state(state)
        
        # Trigger inference without clearing input (Streamlit handles this automatically)
        st.session_state.trigger_inference = True
        st.rerun()
    
    def _handle_inference(self) -> None:
        """Handle AI inference process"""
        
        # Clear trigger flag
        st.session_state.trigger_inference = False
        
        # Get current state
        state = state_manager.get_state()
        
        if not state.messages:
            st.rerun()
            return
        
        last_message = state.messages[-1]
        
        if last_message.role != "user":
            st.rerun()
            return
        
        try:
            # Set streaming state
            state_manager.set_streaming_state(True)
            
            # Get current model and check if it's image mode
            current_model = state.current_model
            is_image_mode = "image-preview" in current_model
            
            # Handle inference based on mode
            if is_image_mode:
                self._handle_image_generation(last_message, current_model)
            else:
                self._handle_text_generation(last_message, current_model)
                
        except Exception as e:
            st.error(f"Inference Error: {e}")
        finally:
            # Always clear streaming state, even if an error occurs
            state_manager.set_streaming_state(False)
    
    def _handle_image_generation(self, user_message, model_name: str) -> None:
        """Enhanced image generation with better progress indicators and error handling"""
        
        with st.chat_message("assistant"):
            # Create progress container
            progress_container = st.container()
            status_container = st.container()
            
            with status_container:
                status = st.status("🎨 Preparing image generation...", expanded=True)
            
            # Import vision service with safety check
            if "studio_vision_svc" not in st.session_state:
                # Initialize vision service if missing
                from services.ai_studio.vision_service import StudioVisionService
                api_key = st.secrets.get("GOOGLE_API_KEY")
                st.session_state.studio_vision_svc = StudioVisionService(api_key)
            
            vision_svc = st.session_state.studio_vision_svc
            
            # Get conversation state
            state = state_manager.get_state()
            api_messages = state_manager.get_messages_for_api()
            
            # Progress tracking
            progress_bar = progress_container.progress(0)
            progress_text = progress_container.empty()
            
            def update_progress(message: str, value: float):
                """Update progress indicators"""
                progress_bar.progress(value)
                progress_text.text(message)
                status.update(label=f"🎨 {message}", state="running")
            
            try:
                # Step 1: Resolve reference image
                update_progress("Resolving reference images...", 0.1)
                
                target_ref_img, info_text = vision_svc.resolve_reference_image(
                    api_messages[-1], api_messages[:-1]
                )
                
                if info_text:
                    with status:
                        if "error" in info_text.lower() or "❌" in info_text:
                            st.error(info_text)
                        elif "⚠️" in info_text:
                            st.warning(info_text)
                        else:
                            st.info(info_text)
                
                # Step 2: Generate image with enhanced progress tracking
                update_progress("Starting image generation...", 0.2)
                
                result = vision_svc.generate_image_with_progress(
                    prompt=user_message.content,
                    model_name=model_name,
                    ref_image=target_ref_img,
                    progress_callback=update_progress
                )
                
                if result.success and result.image_data:
                    # Step 3: Process successful result
                    update_progress("Processing generated image...", 0.9)
                    
                    # Get image metadata for user feedback
                    metadata = vision_svc.get_image_metadata(result.image_data)
                    
                    # Create high-quality preview
                    preview_data = vision_svc.create_high_quality_preview(result.image_data)
                    
                    # Display generation info
                    with status:
                        st.success(f"✅ Image generated successfully!")
                        
                        # Show generation details
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Generation Time", f"{result.generation_time:.1f}s" if result.generation_time else "N/A")
                        with col2:
                            st.metric("Image Size", f"{metadata.get('size', 'Unknown')}")
                        with col3:
                            st.metric("File Size", f"{metadata.get('file_size_mb', 0):.1f} MB")
                        
                        if result.reference_indicator:
                            st.info(result.reference_indicator)
                    
                    # Add AI message with enhanced image result
                    state_manager.add_ai_message(
                        content=f"Generated image from prompt: {user_message.content[:100]}{'...' if len(user_message.content) > 100 else ''}",
                        model_used=model_name,
                        message_type="image_result",
                        hd_data=result.image_data,
                        metadata={
                            'generation_time': result.generation_time,
                            'image_metadata': metadata,
                            'reference_used': target_ref_img is not None,
                            'reference_indicator': result.reference_indicator
                        }
                    )
                    
                    # Final progress update
                    update_progress("Image generation complete!", 1.0)
                    status.update(label="✅ Image generation complete!", state="complete")
                    
                    # Clear progress indicators after a moment
                    import time
                    time.sleep(1)
                    progress_container.empty()
                    
                    st.rerun()
                    
                else:
                    # Handle generation failure
                    error_msg = result.error or "Unknown generation error"
                    
                    with status:
                        st.error(f"❌ Image generation failed: {error_msg}")
                        
                        # Provide helpful suggestions based on error type
                        if "api key" in error_msg.lower():
                            st.info("💡 Please check your API key configuration in Streamlit secrets.")
                        elif "prompt" in error_msg.lower():
                            st.info("💡 Try using a more detailed prompt (minimum 3 characters).")
                        elif "validation" in error_msg.lower():
                            st.info("💡 Check that your reference image is in a supported format (JPEG, PNG, WEBP).")
                        elif "retry" in error_msg.lower():
                            st.info("💡 The service may be temporarily unavailable. Please try again in a moment.")
                        else:
                            st.info("💡 Please try again with a different prompt or check your internet connection.")
                    
                    progress_bar.progress(0)
                    progress_text.text("Generation failed")
                    status.update(label="❌ Image generation failed", state="error")
                    
            except Exception as e:
                # Handle unexpected errors
                error_msg = f"Unexpected error during image generation: {str(e)}"
                
                with status:
                    st.error(f"❌ {error_msg}")
                    st.info("💡 Please try again or contact support if the issue persists.")
                
                progress_bar.progress(0)
                progress_text.text("Error occurred")
                status.update(label="❌ Generation error", state="error")
                
                # Log error for debugging
                st.write(f"Debug info: {str(e)}")
    
    def _display_image_generation_capabilities(self) -> None:
        """Display current image generation capabilities to user"""
        vision_svc = st.session_state.get('studio_vision_svc')
        if vision_svc:
            capabilities = vision_svc.get_generation_capabilities()
            
            with st.expander("🎨 Image Generation Capabilities", expanded=False):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write("**Features:**")
                    st.write(f"• Reference Images: {'✅' if capabilities.get('supports_reference_images') else '❌'}")
                    st.write(f"• Iterative Editing: {'✅' if capabilities.get('supports_iterative_editing') else '❌'}")
                    st.write(f"• Progress Tracking: {'✅' if capabilities.get('supports_progress_tracking') else '❌'}")
                    st.write(f"• High-Quality Preview: {'✅' if capabilities.get('supports_high_quality_preview') else '❌'}")
                
                with col2:
                    st.write("**Limits:**")
                    st.write(f"• Max Image Size: {capabilities.get('max_image_size_mb', 'Unknown')} MB")
                    st.write(f"• Supported Formats: {', '.join(capabilities.get('supported_formats', []))}")
                    st.write(f"• Max Retries: {capabilities.get('max_retries', 'Unknown')}")
                    st.write(f"• Auto-retry: ✅ with exponential backoff")
    
    def _handle_text_generation(self, user_message, model_name: str) -> None:
        """Handle text generation inference"""
        
        with st.chat_message("assistant"):
            placeholder = st.empty()
            full_response = ""
            
            try:
                # Import chat service
                from services.ai_studio.chat_service import StudioChatService
                
                # Get API key
                api_key = st.secrets.get("GOOGLE_API_KEY")
                
                # Create chat service
                state = state_manager.get_state()
                chat_svc = StudioChatService(
                    api_key=api_key,
                    model_name=model_name,
                    system_instruction=state.system_prompt
                )
                
                # Get conversation history for API
                api_messages = state_manager.get_messages_for_api()
                history_msgs = api_messages[:-1]  # All except last message
                
                # Create chat session
                chat_session = chat_svc.create_chat_session(history_msgs)
                
                # Prepare current message payload
                current_payload = []
                if hasattr(user_message, 'ref_images') and user_message.ref_images:
                    current_payload.extend(user_message.ref_images)
                if user_message.content:
                    current_payload.append(user_message.content)
                
                # Send message and stream response
                response = chat_session.send_message(current_payload, stream=True)
                
                for chunk in response:
                    # Check if chunk has text content
                    if hasattr(chunk, 'text') and chunk.text:
                        full_response += chunk.text
                        placeholder.markdown(full_response + "▌")
                    elif hasattr(chunk, 'parts') and chunk.parts:
                        # Handle parts-based response
                        for part in chunk.parts:
                            if hasattr(part, 'text') and part.text:
                                full_response += part.text
                                placeholder.markdown(full_response + "▌")
                
                # Finalize response
                if full_response.strip():
                    placeholder.markdown(full_response)
                else:
                    # Handle empty response
                    full_response = "抱歉，我无法生成回复。请重试。"
                    placeholder.markdown(full_response)
                
                # Add AI message to conversation
                state_manager.add_ai_message(
                    content=full_response,
                    model_used=model_name,
                    message_type="text"
                )
                
                st.rerun()
                
            except Exception as e:
                st.error(f"Chat Error: {e}")
    
    def _handle_message_delete(self, message_index: int) -> None:
        """Handle message deletion with confirmation"""
        
        state = state_manager.get_state()
        if 0 <= message_index < len(state.messages):
            message = state.messages[message_index]
            
            # Show confirmation dialog
            @st.dialog("🗑️ Delete Message")
            def confirm_delete():
                st.write("Are you sure you want to delete this message?")
                
                # Show message preview
                with st.container():
                    st.markdown(f"**{message.role.title()}:** {message.content[:100]}{'...' if len(message.content) > 100 else ''}")
                
                st.warning("This action cannot be undone and may affect conversation coherence.")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    if st.button("Cancel", use_container_width=True):
                        st.rerun()
                
                with col2:
                    if st.button("Delete", type="primary", use_container_width=True):
                        if state_manager.delete_message(message.id):
                            st.success("Message deleted successfully!")
                            st.rerun()
                        else:
                            st.error("Failed to delete message.")
            
            confirm_delete()
    
    def _handle_message_regenerate(self, message_index: int) -> None:
        """Handle message regeneration with confirmation"""
        
        state = state_manager.get_state()
        if 0 <= message_index < len(state.messages):
            message = state.messages[message_index]
            if message.role == "assistant":
                
                # Show confirmation dialog
                @st.dialog("🔄 Regenerate Response")
                def confirm_regenerate():
                    st.write("Regenerate this AI response?")
                    
                    # Show message preview
                    with st.container():
                        st.markdown(f"**Current response:** {message.content[:150]}{'...' if len(message.content) > 150 else ''}")
                    
                    st.info("The AI will generate a new response to the previous user message.")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        if st.button("Cancel", use_container_width=True):
                            st.rerun()
                    
                    with col2:
                        if st.button("Regenerate", type="primary", use_container_width=True):
                            # Delete the AI message and trigger regeneration
                            if state_manager.delete_message(message.id):
                                st.session_state.trigger_inference = True
                                st.success("Regenerating response...")
                                st.rerun()
                            else:
                                st.error("Failed to regenerate message.")
                
                confirm_regenerate()
    
    def _handle_clear_conversation_with_confirmation(self) -> None:
        """Handle conversation clearing with confirmation dialog"""
        
        state = state_manager.get_state()
        message_count = len(state.messages)
        
        if message_count == 0:
            st.info("No messages to clear.")
            return
        
        # Show confirmation dialog for non-empty conversations
        @st.dialog("🧹 Clear Conversation")
        def confirm_clear():
            st.write(f"Are you sure you want to clear all {message_count} messages?")
            st.warning("This action cannot be undone.")
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("Cancel", use_container_width=True):
                    st.rerun()
            
            with col2:
                if st.button("Clear All", type="primary", use_container_width=True):
                    state_manager.clear_conversation()
                    st.success("Conversation cleared successfully!")
                    st.rerun()
        
        confirm_clear()
    
    def _handle_clear_conversation(self) -> None:
        """Handle conversation clearing (legacy method)"""
        
        state_manager.clear_conversation()
        st.rerun()
    
    def _handle_undo_last_turn(self) -> None:
        """Handle undo last turn with enhanced feedback"""
        
        state = state_manager.get_state()
        
        if len(state.messages) == 0:
            st.info("No messages to undo.")
            return
        
        if state_manager.undo_last_turn():
            st.success("Last exchange undone successfully!")
            st.rerun()
        else:
            st.warning("Nothing to undo.")
    
    def _handle_scroll_to_top(self) -> None:
        """Handle scrolling to conversation top"""
        
        # Use JavaScript to scroll to top
        scroll_js = """
        <script>
        window.parent.document.querySelector('.main').scrollTo({
            top: 0,
            behavior: 'smooth'
        });
        </script>
        """
        st.markdown(scroll_js, unsafe_allow_html=True)
    
    def _handle_scroll_to_bottom(self) -> None:
        """Handle scrolling to conversation bottom"""
        
        # Use JavaScript to scroll to bottom
        scroll_js = """
        <script>
        window.parent.document.querySelector('.main').scrollTo({
            top: document.querySelector('.main').scrollHeight,
            behavior: 'smooth'
        });
        </script>
        """
        st.markdown(scroll_js, unsafe_allow_html=True)
    
    def _handle_message_search(self, query: str) -> None:
        """Handle message search functionality"""
        
        state = state_manager.get_state()
        
        if not query.strip():
            return
        
        # Search through messages
        matching_messages = []
        for i, msg in enumerate(state.messages):
            if query.lower() in msg.content.lower():
                matching_messages.append((i, msg))
        
        if matching_messages:
            st.success(f"Found {len(matching_messages)} matching messages:")
            
            # Display search results
            for i, (msg_idx, msg) in enumerate(matching_messages[:5]):  # Show first 5 results
                with st.expander(f"Result {i+1}: {msg.role.title()} message #{msg_idx+1}"):
                    # Highlight the search term
                    highlighted_content = msg.content.replace(
                        query, f"**{query}**"
                    )
                    st.markdown(highlighted_content)
                    
                    if st.button(f"Jump to message", key=f"jump_{msg_idx}"):
                        self._handle_jump_to_message(msg_idx)
            
            if len(matching_messages) > 5:
                st.info(f"... and {len(matching_messages) - 5} more results")
        else:
            st.warning(f"No messages found containing '{query}'")
    
    def _handle_jump_to_message(self, message_index: int) -> None:
        """Handle jumping to a specific message"""
        
        # This would ideally scroll to the specific message
        # For now, we'll show a success message
        st.success(f"Jumped to message #{message_index + 1}")
        
        # In a real implementation, this would use JavaScript to scroll to the specific message
        jump_js = f"""
        <script>
        // Find the message element and scroll to it
        const messageElements = window.parent.document.querySelectorAll('[data-testid="stChatMessage"]');
        if (messageElements[{message_index}]) {{
            messageElements[{message_index}].scrollIntoView({{
                behavior: 'smooth',
                block: 'center'
            }});
            // Highlight the message briefly
            messageElements[{message_index}].style.backgroundColor = '#fff3cd';
            setTimeout(() => {{
                messageElements[{message_index}].style.backgroundColor = '';
            }}, 2000);
        }}
        </script>
        """
        st.markdown(jump_js, unsafe_allow_html=True)
    
    def _handle_save_conversation_backup(self) -> None:
        """Handle saving conversation backup"""
        
        state = state_manager.get_state()
        
        if not state.messages:
            st.info("No messages to backup.")
            return
        
        try:
            # Generate backup filename with timestamp
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"conversation_backup_{timestamp}.json"
            
            # Export conversation data
            backup_data = state_manager.export_conversation_json()
            
            # Offer download
            st.download_button(
                "📥 Download Backup",
                data=backup_data,
                file_name=backup_filename,
                mime="application/json",
                help="Download conversation backup file"
            )
            
            st.success("Backup prepared! Click the download button above.")
            
        except Exception as e:
            st.error(f"Failed to create backup: {e}")
    
    def _setup_default_callbacks(self) -> None:
        """Set up default callback functions"""
        
        self.callbacks = {
            'on_message_delete': self._handle_message_delete,
            'on_message_regenerate': self._handle_message_regenerate,
            'on_clear_conversation': self._handle_clear_conversation,
            'on_undo_turn': self._handle_undo_last_turn,
            'on_user_input': self._handle_user_input,
        }
    
    def register_callback(self, event: str, callback: Callable) -> None:
        """Register a custom callback for an event"""
        
        self.callbacks[event] = callback
    
    def get_callback(self, event: str) -> Optional[Callable]:
        """Get a registered callback"""
        
        return self.callbacks.get(event)
    
    def set_streaming_state(self, streaming: bool) -> None:
        """Set the streaming state"""
        
        self.streaming_active = streaming
        state_manager.set_streaming_state(streaming)


# Global instance for easy access
ui_controller = UIController()
