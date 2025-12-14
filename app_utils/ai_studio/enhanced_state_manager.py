"""
Enhanced state management for AI Studio
Provides centralized state management with persistence and data model integration
"""

import streamlit as st
import json
import pickle
from datetime import datetime
from typing import Dict, Any, Optional, List
from .models import (
    ConversationState, UISettings, BaseMessage, UserMessage, AIMessage,
    create_user_message, create_ai_message, convert_legacy_message
)
from services.ai_studio.vision_service import StudioVisionService
from .error_handler import handle_ui_error, handle_api_error, ErrorType, with_error_handling


class EnhancedStateManager:
    """Enhanced state manager with persistence and data model support"""
    
    def __init__(self):
        self.state_key = "ai_studio_enhanced_state"
        self.legacy_keys = ["studio_msgs", "msg_uid", "uploader_key_id", "system_prompt_val"]
    
    def initialize_state(self) -> ConversationState:
        """Initialize or restore conversation state"""
        if self.state_key not in st.session_state:
            # Check for legacy state and migrate if needed
            if self._has_legacy_state():
                st.session_state[self.state_key] = self._migrate_legacy_state()
            else:
                st.session_state[self.state_key] = ConversationState()
        
        # Initialize vision service if not present
        if "studio_vision_svc" not in st.session_state:
            try:
                api_key = st.secrets.get("GOOGLE_API_KEY")
                if not api_key:
                    st.warning("⚠️ Google API key not found. Image generation will not be available.")
                st.session_state.studio_vision_svc = StudioVisionService(api_key)
            except Exception as e:
                st.error(f"❌ Failed to initialize vision service: {e}")
                # Create a minimal dummy service to prevent crashes
                class DummyVisionService:
                    def resolve_reference_image(self, *args, **kwargs):
                        return None, "❌ Vision service initialization failed"
                    def generate_image_with_progress(self, *args, **kwargs):
                        from services.ai_studio.vision_service import ImageGenerationResult
                        result = ImageGenerationResult()
                        result.error = "Vision service initialization failed"
                        return result
                st.session_state.studio_vision_svc = DummyVisionService()
        
        return st.session_state[self.state_key]
    
    def get_state(self) -> ConversationState:
        """Get current conversation state"""
        return st.session_state.get(self.state_key, ConversationState())
    
    def update_state(self, state: ConversationState) -> None:
        """Update conversation state"""
        st.session_state[self.state_key] = state
    
    def _has_legacy_state(self) -> bool:
        """Check if legacy state exists"""
        return any(key in st.session_state for key in self.legacy_keys)
    
    def _migrate_legacy_state(self) -> ConversationState:
        """Migrate legacy state to new data model"""
        state = ConversationState()
        
        # Migrate messages
        if "studio_msgs" in st.session_state:
            legacy_messages = st.session_state["studio_msgs"]
            for legacy_msg in legacy_messages:
                try:
                    new_msg = convert_legacy_message(legacy_msg)
                    state.messages.append(new_msg)
                except Exception as e:
                    print(f"Error migrating message: {e}")
        
        # Migrate other state
        state.msg_uid = st.session_state.get("msg_uid", 0)
        state.uploader_key_id = st.session_state.get("uploader_key_id", 0)
        state.system_prompt = st.session_state.get("system_prompt_val", state.system_prompt)
        
        # Clean up legacy state
        for key in self.legacy_keys:
            if key in st.session_state:
                del st.session_state[key]
        
        return state
    
    @with_error_handling(ErrorType.UI_ERROR)
    def add_user_message(self, content: str, ref_images: List = None) -> str:
        """Add a user message to the conversation"""
        try:
            state = self.get_state()
            state.msg_uid += 1
            message_id = str(state.msg_uid)
            
            message = create_user_message(content, message_id, ref_images or [])
            state.add_message(message)
            self.update_state(state)
            
            return message_id
        except Exception as e:
            handle_ui_error(e, {"operation": "add_user_message", "content_length": len(content)})
            return None
    
    @with_error_handling(ErrorType.UI_ERROR)
    def add_ai_message(self, content: str, model_used: str, 
                      message_type: str = "text", hd_data: bytes = None) -> str:
        """Add an AI message to the conversation"""
        try:
            state = self.get_state()
            state.msg_uid += 1
            message_id = str(state.msg_uid)
            
            message = create_ai_message(content, message_id, model_used, message_type, hd_data)
            state.add_message(message)
            self.update_state(state)
            
            return message_id
        except Exception as e:
            handle_ui_error(e, {"operation": "add_ai_message", "model": model_used, "type": message_type})
            return None
    
    def delete_message(self, message_id: str) -> bool:
        """Delete a message by ID"""
        state = self.get_state()
        success = state.remove_message(message_id)
        if success:
            self.update_state(state)
        return success
    
    def clear_conversation(self) -> None:
        """Clear all messages"""
        state = self.get_state()
        state.clear_messages()
        state.uploader_key_id += 1  # Reset uploader to clear file cache
        self.update_state(state)
    
    def undo_last_turn(self) -> bool:
        """Undo the last user-assistant exchange"""
        state = self.get_state()
        success = state.undo_last_turn()
        if success:
            self.update_state(state)
        return success
    
    def update_model(self, model_name: str) -> None:
        """Update the current model"""
        state = self.get_state()
        state.current_model = model_name
        self.update_state(state)
    
    def update_system_prompt(self, prompt: str) -> None:
        """Update the system prompt"""
        state = self.get_state()
        state.system_prompt = prompt
        self.update_state(state)
    
    def update_ui_settings(self, settings: UISettings) -> None:
        """Update UI settings"""
        state = self.get_state()
        state.ui_settings = settings
        self.update_state(state)
    
    @with_error_handling(ErrorType.UI_ERROR)
    def set_streaming_state(self, is_streaming: bool) -> None:
        """Set streaming state"""
        try:
            state = self.get_state()
            state.is_streaming = is_streaming
            self.update_state(state)
        except Exception as e:
            handle_ui_error(e, {"operation": "set_streaming_state", "streaming": is_streaming})
    
    def get_messages_for_api(self) -> List[Dict[str, Any]]:
        """Convert messages to API format for backward compatibility"""
        state = self.get_state()
        api_messages = []
        
        for msg in state.messages:
            if isinstance(msg, UserMessage):
                api_msg = {
                    "role": "user",
                    "content": msg.content,
                    "ref_images": msg.ref_images,
                    "id": int(msg.id) if msg.id.isdigit() else 0
                }
            elif isinstance(msg, AIMessage):
                api_msg = {
                    "role": "model",
                    "content": msg.content,
                    "type": msg.message_type,
                    "id": int(msg.id) if msg.id.isdigit() else 0
                }
                if msg.hd_data:
                    api_msg["hd_data"] = msg.hd_data
            else:
                # Fallback for other message types
                api_msg = {
                    "role": msg.role,
                    "content": getattr(msg, 'content', ''),
                    "id": int(msg.id) if msg.id.isdigit() else 0
                }
            
            api_messages.append(api_msg)
        
        return api_messages
    
    def save_state_to_file(self, filename: str) -> bool:
        """Save conversation state to file"""
        try:
            state = self.get_state()
            with open(filename, 'wb') as f:
                pickle.dump(state, f)
            return True
        except Exception as e:
            print(f"Error saving state: {e}")
            return False
    
    def load_state_from_file(self, filename: str) -> bool:
        """Load conversation state from file"""
        try:
            with open(filename, 'rb') as f:
                state = pickle.load(f)
            self.update_state(state)
            return True
        except Exception as e:
            print(f"Error loading state: {e}")
            return False
    
    def export_conversation_json(self) -> str:
        """Export conversation to JSON format"""
        state = self.get_state()
        export_data = {
            "messages": [],
            "metadata": {
                "model": state.current_model,
                "system_prompt": state.system_prompt,
                "export_time": datetime.now().isoformat(),
                "message_count": len(state.messages),
                "conversation_stats": self.get_conversation_statistics()
            }
        }
        
        for msg in state.messages:
            msg_data = {
                "id": msg.id,
                "timestamp": msg.timestamp.isoformat(),
                "role": msg.role,
                "content": getattr(msg, 'content', '')
            }
            
            if isinstance(msg, AIMessage):
                msg_data["model_used"] = msg.model_used
                msg_data["message_type"] = msg.message_type
            
            export_data["messages"].append(msg_data)
        
        return json.dumps(export_data, indent=2)
    
    def get_conversation_statistics(self) -> Dict[str, Any]:
        """Get detailed conversation statistics"""
        state = self.get_state()
        
        if not state.messages:
            return {
                "total_messages": 0,
                "user_messages": 0,
                "ai_messages": 0,
                "total_characters": 0,
                "average_message_length": 0,
                "conversation_duration": "0 minutes"
            }
        
        user_messages = [msg for msg in state.messages if msg.role == "user"]
        ai_messages = [msg for msg in state.messages if msg.role == "assistant"]
        
        total_chars = sum(len(getattr(msg, 'content', '')) for msg in state.messages)
        avg_length = total_chars / len(state.messages) if state.messages else 0
        
        # Calculate conversation duration
        if len(state.messages) >= 2:
            start_time = state.messages[0].timestamp
            end_time = state.messages[-1].timestamp
            duration = end_time - start_time
            duration_minutes = int(duration.total_seconds() / 60)
        else:
            duration_minutes = 0
        
        return {
            "total_messages": len(state.messages),
            "user_messages": len(user_messages),
            "ai_messages": len(ai_messages),
            "total_characters": total_chars,
            "average_message_length": round(avg_length, 1),
            "conversation_duration": f"{duration_minutes} minutes"
        }
    
    def search_messages(self, query: str, case_sensitive: bool = False) -> List[Dict[str, Any]]:
        """Search messages for a specific query"""
        state = self.get_state()
        results = []
        
        search_query = query if case_sensitive else query.lower()
        
        for i, msg in enumerate(state.messages):
            content = getattr(msg, 'content', '')
            search_content = content if case_sensitive else content.lower()
            
            if search_query in search_content:
                results.append({
                    "index": i,
                    "message": msg,
                    "preview": content[:200] + "..." if len(content) > 200 else content
                })
        
        return results
    
    def get_message_by_index(self, index: int) -> Optional[BaseMessage]:
        """Get a message by its index in the conversation"""
        state = self.get_state()
        
        if 0 <= index < len(state.messages):
            return state.messages[index]
        
        return None
    
    def get_conversation_context(self, message_index: int, context_size: int = 3) -> List[BaseMessage]:
        """Get conversation context around a specific message"""
        state = self.get_state()
        
        if not (0 <= message_index < len(state.messages)):
            return []
        
        start_idx = max(0, message_index - context_size)
        end_idx = min(len(state.messages), message_index + context_size + 1)
        
        return state.messages[start_idx:end_idx]
    
    def delete_messages_batch(self, message_ids: List[str]) -> int:
        """Delete multiple messages in batch"""
        state = self.get_state()
        deleted_count = 0
        
        for message_id in message_ids:
            if state.remove_message(message_id):
                deleted_count += 1
        
        if deleted_count > 0:
            self.update_state(state)
        
        return deleted_count
    
    def trim_conversation(self, max_messages: int) -> int:
        """Trim conversation to maximum number of messages, keeping the most recent"""
        state = self.get_state()
        
        if len(state.messages) <= max_messages:
            return 0
        
        messages_to_remove = len(state.messages) - max_messages
        
        # Remove oldest messages
        for _ in range(messages_to_remove):
            if state.messages:
                state.messages.pop(0)
        
        self.update_state(state)
        return messages_to_remove
    
    def backup_conversation(self, backup_name: str = None) -> str:
        """Create a backup of the current conversation"""
        if backup_name is None:
            backup_name = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        backup_data = {
            "backup_name": backup_name,
            "backup_time": datetime.now().isoformat(),
            "conversation_data": self.export_conversation_json()
        }
        
        return json.dumps(backup_data, indent=2)


# Global instance for easy access
state_manager = EnhancedStateManager()


# Convenience functions for backward compatibility
def init_enhanced_session_state():
    """Initialize enhanced session state"""
    return state_manager.initialize_state()


def get_conversation_state() -> ConversationState:
    """Get current conversation state"""
    return state_manager.get_state()


def clear_enhanced_history():
    """Clear conversation history"""
    state_manager.clear_conversation()
    st.rerun()


def undo_enhanced_last_turn():
    """Undo last turn"""
    if state_manager.undo_last_turn():
        st.rerun()
