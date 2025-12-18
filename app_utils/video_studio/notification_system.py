"""
Real-time Notification System for Video Studio.

This module provides comprehensive notification capabilities including WebSocket connections,
email notifications, and multi-channel status updates for video generation tasks.
"""

import asyncio
import json
import smtplib
from datetime import datetime
from typing import Dict, List, Optional, Callable, Any, Set, Union
from dataclasses import dataclass, field
from enum import Enum
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import weakref
from abc import ABC, abstractmethod

from .models import TaskInfo, TaskStatus
from .logging_config import get_logger
from .error_handler import with_video_studio_error_handling, VideoStudioErrorType


class NotificationType(Enum):
    """Types of notifications that can be sent."""
    TASK_CREATED = "task_created"
    TASK_STARTED = "task_started"
    TASK_PROGRESS = "task_progress"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    TASK_CANCELLED = "task_cancelled"
    SYSTEM_ALERT = "system_alert"
    RESOURCE_WARNING = "resource_warning"


class NotificationChannel(Enum):
    """Available notification channels."""
    WEBSOCKET = "websocket"
    EMAIL = "email"
    WEBHOOK = "webhook"
    IN_APP = "in_app"


@dataclass
class NotificationMessage:
    """Represents a notification message."""
    notification_type: NotificationType
    title: str
    message: str
    task_id: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert notification to dictionary for serialization."""
        return {
            'type': self.notification_type.value,
            'title': self.title,
            'message': self.message,
            'task_id': self.task_id,
            'timestamp': self.timestamp.isoformat(),
            'metadata': self.metadata
        }


class NotificationHandler(ABC):
    """Abstract base class for notification handlers."""
    
    @abstractmethod
    async def send_notification(self, message: NotificationMessage) -> bool:
        """Send a notification message."""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if the notification handler is available."""
        pass


class WebSocketConnection:
    """Represents a WebSocket connection for real-time updates."""
    
    def __init__(self, connection_id: str, websocket, user_id: Optional[str] = None):
        """
        Initialize WebSocket connection.
        
        Args:
            connection_id: Unique connection identifier
            websocket: WebSocket connection object
            user_id: Optional user identifier
        """
        self.connection_id = connection_id
        self.websocket = websocket
        self.user_id = user_id
        self.connected_at = datetime.now()
        self.last_ping = datetime.now()
        self.subscribed_tasks: Set[str] = set()
        self.subscribed_types: Set[NotificationType] = set()
    
    async def send_message(self, message: Dict[str, Any]) -> bool:
        """Send a message through the WebSocket connection."""
        try:
            await self.websocket.send(json.dumps(message))
            return True
        except Exception:
            return False
    
    def is_connected(self) -> bool:
        """Check if the WebSocket connection is still active."""
        try:
            return not self.websocket.closed
        except AttributeError:
            return False


class WebSocketNotificationHandler(NotificationHandler):
    """Handles notifications via WebSocket connections."""
    
    def __init__(self):
        """Initialize WebSocket notification handler."""
        self.connections: Dict[str, WebSocketConnection] = {}
        self.logger = get_logger("websocket_notifications")
    
    def add_connection(self, connection: WebSocketConnection) -> None:
        """Add a new WebSocket connection."""
        self.connections[connection.connection_id] = connection
        self.logger.info(f"Added WebSocket connection {connection.connection_id}")
    
    def remove_connection(self, connection_id: str) -> None:
        """Remove a WebSocket connection."""
        if connection_id in self.connections:
            del self.connections[connection_id]
            self.logger.info(f"Removed WebSocket connection {connection_id}")
    
    def subscribe_to_task(self, connection_id: str, task_id: str) -> bool:
        """Subscribe a connection to task updates."""
        connection = self.connections.get(connection_id)
        if connection:
            connection.subscribed_tasks.add(task_id)
            return True
        return False
    
    def subscribe_to_type(self, connection_id: str, notification_type: NotificationType) -> bool:
        """Subscribe a connection to notification type updates."""
        connection = self.connections.get(connection_id)
        if connection:
            connection.subscribed_types.add(notification_type)
            return True
        return False
    
    async def send_notification(self, message: NotificationMessage) -> bool:
        """Send notification to relevant WebSocket connections."""
        if not self.connections:
            return True
        
        message_dict = message.to_dict()
        sent_count = 0
        failed_connections = []
        
        for connection_id, connection in self.connections.items():
            if not connection.is_connected():
                failed_connections.append(connection_id)
                continue
            
            # Check if connection should receive this notification
            should_send = (
                not connection.subscribed_tasks and not connection.subscribed_types or
                (message.task_id and message.task_id in connection.subscribed_tasks) or
                message.notification_type in connection.subscribed_types
            )
            
            if should_send:
                if await connection.send_message(message_dict):
                    sent_count += 1
                else:
                    failed_connections.append(connection_id)
        
        # Clean up failed connections
        for connection_id in failed_connections:
            self.remove_connection(connection_id)
        
        self.logger.debug(f"Sent WebSocket notification to {sent_count} connections")
        return sent_count > 0
    
    def is_available(self) -> bool:
        """Check if WebSocket handler is available."""
        return len(self.connections) > 0
    
    async def broadcast_system_status(self, status: Dict[str, Any]) -> None:
        """Broadcast system status to all connections."""
        message = {
            'type': 'system_status',
            'status': status,
            'timestamp': datetime.now().isoformat()
        }
        
        for connection in list(self.connections.values()):
            if connection.is_connected():
                await connection.send_message(message)


class EmailNotificationHandler(NotificationHandler):
    """Handles notifications via email."""
    
    def __init__(
        self,
        smtp_server: str,
        smtp_port: int = 587,
        username: Optional[str] = None,
        password: Optional[str] = None,
        use_tls: bool = True
    ):
        """
        Initialize email notification handler.
        
        Args:
            smtp_server: SMTP server address
            smtp_port: SMTP server port
            username: SMTP username
            password: SMTP password
            use_tls: Whether to use TLS encryption
        """
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.use_tls = use_tls
        self.logger = get_logger("email_notifications")
        
        # Email templates
        self.templates = {
            NotificationType.TASK_COMPLETED: {
                'subject': 'Video Generation Completed - Task {task_id}',
                'body': 'Your video generation task {task_id} has been completed successfully.\n\nYou can download your video from: {result_url}'
            },
            NotificationType.TASK_FAILED: {
                'subject': 'Video Generation Failed - Task {task_id}',
                'body': 'Your video generation task {task_id} has failed.\n\nError: {error_message}\n\nPlease try again or contact support.'
            }
        }
    
    async def send_notification(self, message: NotificationMessage) -> bool:
        """Send notification via email."""
        try:
            # Get email template
            template = self.templates.get(message.notification_type)
            if not template:
                return False  # No email template for this notification type
            
            # Format email content
            subject = template['subject'].format(
                task_id=message.task_id or 'Unknown',
                **message.metadata
            )
            body = template['body'].format(
                task_id=message.task_id or 'Unknown',
                **message.metadata
            )
            
            # Create email message
            msg = MIMEMultipart()
            msg['Subject'] = subject
            msg['From'] = self.username
            msg['To'] = message.metadata.get('email', '')
            
            if not msg['To']:
                return False  # No recipient email
            
            msg.attach(MIMEText(body, 'plain'))
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                if self.use_tls:
                    server.starttls()
                if self.username and self.password:
                    server.login(self.username, self.password)
                server.send_message(msg)
            
            self.logger.info(f"Sent email notification for {message.notification_type.value}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to send email notification: {e}")
            return False
    
    def is_available(self) -> bool:
        """Check if email handler is available."""
        return bool(self.smtp_server and self.username)


class WebhookNotificationHandler(NotificationHandler):
    """Handles notifications via HTTP webhooks."""
    
    def __init__(self, webhook_urls: List[str]):
        """
        Initialize webhook notification handler.
        
        Args:
            webhook_urls: List of webhook URLs to send notifications to
        """
        self.webhook_urls = webhook_urls
        self.logger = get_logger("webhook_notifications")
    
    async def send_notification(self, message: NotificationMessage) -> bool:
        """Send notification via webhooks."""
        if not self.webhook_urls:
            return False
        
        import aiohttp
        
        payload = message.to_dict()
        success_count = 0
        
        async with aiohttp.ClientSession() as session:
            for url in self.webhook_urls:
                try:
                    async with session.post(url, json=payload, timeout=10) as response:
                        if response.status == 200:
                            success_count += 1
                        else:
                            self.logger.warning(f"Webhook {url} returned status {response.status}")
                except Exception as e:
                    self.logger.error(f"Failed to send webhook to {url}: {e}")
        
        return success_count > 0
    
    def is_available(self) -> bool:
        """Check if webhook handler is available."""
        return len(self.webhook_urls) > 0


class NotificationSystem:
    """
    Comprehensive notification system for real-time status updates.
    """
    
    def __init__(self):
        """Initialize the notification system."""
        self.logger = get_logger("notification_system")
        
        # Notification handlers
        self.handlers: Dict[NotificationChannel, NotificationHandler] = {}
        
        # Subscription management
        self.user_subscriptions: Dict[str, Set[NotificationType]] = {}
        self.task_subscribers: Dict[str, Set[str]] = {}  # task_id -> set of user_ids
        
        # Message history for debugging
        self.message_history: List[NotificationMessage] = []
        self.max_history_size = 1000
        
        # Statistics
        self.stats = {
            'total_sent': 0,
            'sent_by_type': {nt.value: 0 for nt in NotificationType},
            'sent_by_channel': {nc.value: 0 for nc in NotificationChannel}
        }
        
        self.logger.info("NotificationSystem initialized")
    
    def add_handler(self, channel: NotificationChannel, handler: NotificationHandler) -> None:
        """Add a notification handler for a specific channel."""
        self.handlers[channel] = handler
        self.logger.info(f"Added {channel.value} notification handler")
    
    def remove_handler(self, channel: NotificationChannel) -> None:
        """Remove a notification handler."""
        if channel in self.handlers:
            del self.handlers[channel]
            self.logger.info(f"Removed {channel.value} notification handler")
    
    @with_video_studio_error_handling(VideoStudioErrorType.WORKFLOW_ERROR)
    async def send_notification(
        self,
        notification_type: NotificationType,
        title: str,
        message: str,
        task_id: Optional[str] = None,
        channels: Optional[List[NotificationChannel]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[NotificationChannel, bool]:
        """
        Send a notification through specified channels.
        
        Args:
            notification_type: Type of notification
            title: Notification title
            message: Notification message
            task_id: Optional task ID
            channels: Channels to send through (all if None)
            metadata: Additional metadata
            
        Returns:
            Dictionary mapping channels to success status
        """
        notification = NotificationMessage(
            notification_type=notification_type,
            title=title,
            message=message,
            task_id=task_id,
            metadata=metadata or {}
        )
        
        # Add to history
        self._add_to_history(notification)
        
        # Determine channels to use
        target_channels = channels or list(self.handlers.keys())
        
        # Send through each channel
        results = {}
        for channel in target_channels:
            handler = self.handlers.get(channel)
            if handler and handler.is_available():
                try:
                    success = await handler.send_notification(notification)
                    results[channel] = success
                    
                    if success:
                        self.stats['sent_by_channel'][channel.value] += 1
                    
                except Exception as e:
                    self.logger.error(f"Error sending notification via {channel.value}: {e}")
                    results[channel] = False
            else:
                results[channel] = False
        
        # Update statistics
        self.stats['total_sent'] += 1
        self.stats['sent_by_type'][notification_type.value] += 1
        
        self.logger.debug(f"Sent {notification_type.value} notification: {title}")
        return results
    
    async def notify_task_created(self, task_info: TaskInfo) -> None:
        """Send notification when a task is created."""
        await self.send_notification(
            NotificationType.TASK_CREATED,
            f"Task Created: {task_info.task_id}",
            f"Video generation task has been created and queued for processing.",
            task_id=task_info.task_id,
            metadata={'task_info': task_info.to_dict()}
        )
    
    async def notify_task_started(self, task_info: TaskInfo) -> None:
        """Send notification when a task starts processing."""
        await self.send_notification(
            NotificationType.TASK_STARTED,
            f"Task Started: {task_info.task_id}",
            f"Video generation has begun for your task.",
            task_id=task_info.task_id,
            metadata={'task_info': task_info.to_dict()}
        )
    
    async def notify_task_progress(self, task_info: TaskInfo) -> None:
        """Send notification for task progress updates."""
        progress_percent = int(task_info.progress * 100)
        await self.send_notification(
            NotificationType.TASK_PROGRESS,
            f"Task Progress: {task_info.task_id}",
            f"Video generation is {progress_percent}% complete.",
            task_id=task_info.task_id,
            channels=[NotificationChannel.WEBSOCKET],  # Only real-time for progress
            metadata={'task_info': task_info.to_dict(), 'progress_percent': progress_percent}
        )
    
    async def notify_task_completed(self, task_info: TaskInfo) -> None:
        """Send notification when a task completes successfully."""
        await self.send_notification(
            NotificationType.TASK_COMPLETED,
            f"Task Completed: {task_info.task_id}",
            f"Your video has been generated successfully!",
            task_id=task_info.task_id,
            metadata={
                'task_info': task_info.to_dict(),
                'result_url': task_info.result_url
            }
        )
    
    async def notify_task_failed(self, task_info: TaskInfo) -> None:
        """Send notification when a task fails."""
        await self.send_notification(
            NotificationType.TASK_FAILED,
            f"Task Failed: {task_info.task_id}",
            f"Video generation failed: {task_info.error_message or 'Unknown error'}",
            task_id=task_info.task_id,
            metadata={
                'task_info': task_info.to_dict(),
                'error_message': task_info.error_message
            }
        )
    
    async def notify_task_cancelled(self, task_info: TaskInfo) -> None:
        """Send notification when a task is cancelled."""
        await self.send_notification(
            NotificationType.TASK_CANCELLED,
            f"Task Cancelled: {task_info.task_id}",
            f"Video generation task has been cancelled.",
            task_id=task_info.task_id,
            metadata={'task_info': task_info.to_dict()}
        )
    
    async def notify_system_alert(self, title: str, message: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Send a system alert notification."""
        await self.send_notification(
            NotificationType.SYSTEM_ALERT,
            title,
            message,
            metadata=metadata
        )
    
    def subscribe_user_to_task(self, user_id: str, task_id: str) -> None:
        """Subscribe a user to task notifications."""
        if task_id not in self.task_subscribers:
            self.task_subscribers[task_id] = set()
        self.task_subscribers[task_id].add(user_id)
    
    def unsubscribe_user_from_task(self, user_id: str, task_id: str) -> None:
        """Unsubscribe a user from task notifications."""
        if task_id in self.task_subscribers:
            self.task_subscribers[task_id].discard(user_id)
            if not self.task_subscribers[task_id]:
                del self.task_subscribers[task_id]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get notification system statistics."""
        return {
            **self.stats,
            'active_handlers': list(self.handlers.keys()),
            'message_history_size': len(self.message_history),
            'active_subscriptions': len(self.task_subscribers)
        }
    
    def get_recent_notifications(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent notifications from history."""
        recent = self.message_history[-limit:] if limit > 0 else self.message_history
        return [msg.to_dict() for msg in recent]
    
    def _add_to_history(self, notification: NotificationMessage) -> None:
        """Add notification to history with size limit."""
        self.message_history.append(notification)
        if len(self.message_history) > self.max_history_size:
            self.message_history.pop(0)


# Global notification system instance
_notification_system: Optional[NotificationSystem] = None


def get_notification_system() -> NotificationSystem:
    """Get or create the global notification system instance."""
    global _notification_system
    
    if _notification_system is None:
        _notification_system = NotificationSystem()
    
    return _notification_system


async def send_notification(
    notification_type: NotificationType,
    title: str,
    message: str,
    task_id: Optional[str] = None,
    channels: Optional[List[NotificationChannel]] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[NotificationChannel, bool]:
    """Convenience function to send a notification."""
    system = get_notification_system()
    return await system.send_notification(
        notification_type, title, message, task_id, channels, metadata
    )