"""
Enhanced data models for AI Studio
Provides structured data classes for messages, state management, and UI settings
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Literal, Any, Dict
from PIL import Image
import io


@dataclass
class BaseMessage:
    """Base class for all message types"""
    id: str
    timestamp: datetime
    role: Literal["user", "assistant"]
    
    def __post_init__(self):
        if isinstance(self.timestamp, str):
            # Handle string timestamps for backward compatibility
            self.timestamp = datetime.fromisoformat(self.timestamp)


@dataclass
class Attachment:
    """File attachment data structure"""
    id: str
    filename: str
    file_type: str
    size: int
    data: bytes
    thumbnail: Optional[bytes] = None


@dataclass
class UploadedFile:
    """Uploaded file with status tracking"""
    file: Attachment
    status: Literal["uploading", "ready", "error"]
    error_message: Optional[str] = None


@dataclass
class GenerationInfo:
    """Information about AI response generation"""
    model_used: str
    generation_time: Optional[float] = None
    token_count: Optional[int] = None
    safety_ratings: Optional[Dict[str, Any]] = None


@dataclass
class TextMessage(BaseMessage):
    """Text-based message"""
    content: str
    
    def __post_init__(self):
        super().__post_init__()


@dataclass
class ImageMessage(BaseMessage):
    """Image message with thumbnail support"""
    image_data: bytes
    thumbnail: bytes
    caption: Optional[str] = None
    
    def __post_init__(self):
        super().__post_init__()
        
    def get_pil_image(self) -> Image.Image:
        """Convert image data to PIL Image"""
        return Image.open(io.BytesIO(self.image_data))
    
    def get_thumbnail_image(self) -> Image.Image:
        """Convert thumbnail data to PIL Image"""
        return Image.open(io.BytesIO(self.thumbnail))


@dataclass
class UserMessage(BaseMessage):
    """User message with optional attachments"""
    content: str
    attachments: List[Attachment] = field(default_factory=list)
    ref_images: List[Image.Image] = field(default_factory=list)
    edited: bool = False
    edit_timestamp: Optional[datetime] = None
    original_content: Optional[str] = None
    
    def __post_init__(self):
        super().__post_init__()
        self.role = "user"


@dataclass
class AIMessage(BaseMessage):
    """AI assistant message with generation metadata"""
    content: str
    model_used: str
    generation_info: Optional[GenerationInfo] = None
    message_type: Literal["text", "image_result", "text_interrupted", "image_interrupted"] = "text"
    hd_data: Optional[bytes] = None  # For image results
    
    def __post_init__(self):
        super().__post_init__()
        self.role = "assistant"


@dataclass
class UISettings:
    """User interface configuration settings"""
    theme: str = "light"
    message_density: str = "comfortable"
    auto_scroll: bool = True
    show_timestamps: bool = False
    enable_animations: bool = True
    max_image_width: int = 800
    enable_streaming: bool = True


@dataclass
class ConversationState:
    """Complete conversation state management"""
    messages: List[BaseMessage] = field(default_factory=list)
    current_model: str = "models/gemini-3-flash-preview"
    system_prompt: str = "You are a helpful AI assistant for Amazon E-commerce sellers."
    is_streaming: bool = False
    generation_interrupted: bool = False
    interrupt_reason: str = ""
    upload_queue: List[UploadedFile] = field(default_factory=list)
    ui_settings: UISettings = field(default_factory=UISettings)
    msg_uid: int = 0
    uploader_key_id: int = 0
    
    def add_message(self, message: BaseMessage) -> None:
        """Add a message to the conversation"""
        self.messages.append(message)
        self.msg_uid += 1
    
    def remove_message(self, message_id: str) -> bool:
        """Remove a message by ID"""
        for i, msg in enumerate(self.messages):
            if msg.id == message_id:
                self.messages.pop(i)
                return True
        return False
    
    def get_last_message(self) -> Optional[BaseMessage]:
        """Get the most recent message"""
        return self.messages[-1] if self.messages else None
    
    def get_messages_by_role(self, role: str) -> List[BaseMessage]:
        """Get all messages from a specific role"""
        return [msg for msg in self.messages if msg.role == role]
    
    def clear_messages(self) -> None:
        """Clear all messages"""
        self.messages.clear()
        self.msg_uid = 0
    
    def undo_last_turn(self) -> bool:
        """Remove the last user-assistant exchange"""
        if not self.messages:
            return False
            
        # Remove last message
        self.messages.pop()
        
        # If the remaining last message is from user, remove it too
        if self.messages and self.messages[-1].role == "user":
            self.messages.pop()
            
        return True


def create_user_message(content: str, message_id: str, ref_images: List[Image.Image] = None) -> UserMessage:
    """Factory function to create a user message"""
    return UserMessage(
        id=message_id,
        timestamp=datetime.now(),
        role="user",
        content=content,
        ref_images=ref_images or []
    )


def create_ai_message(content: str, message_id: str, model_used: str, 
                     message_type: str = "text", hd_data: bytes = None) -> AIMessage:
    """Factory function to create an AI message"""
    return AIMessage(
        id=message_id,
        timestamp=datetime.now(),
        role="assistant",
        content=content,
        model_used=model_used,
        message_type=message_type,
        hd_data=hd_data
    )


def convert_legacy_message(legacy_msg: Dict[str, Any]) -> BaseMessage:
    """Convert legacy message format to new data model"""
    msg_id = str(legacy_msg.get("id", 0))
    timestamp = datetime.now()  # Legacy messages don't have timestamps
    
    if legacy_msg["role"] == "user":
        return UserMessage(
            id=msg_id,
            timestamp=timestamp,
            role="user",
            content=legacy_msg.get("content", ""),
            ref_images=legacy_msg.get("ref_images", [])
        )
    else:  # assistant/model
        return AIMessage(
            id=msg_id,
            timestamp=timestamp,
            role="assistant",
            content=legacy_msg.get("content", ""),
            model_used="unknown",
            message_type=legacy_msg.get("type", "text"),
            hd_data=legacy_msg.get("hd_data")
        )
