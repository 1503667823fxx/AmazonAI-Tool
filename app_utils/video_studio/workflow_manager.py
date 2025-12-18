"""
Workflow Manager for Video Studio redesign.

This module implements the core workflow management system that coordinates the entire
video generation process, manages task lifecycles, and provides real-time progress tracking.
"""

import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any, Set
from dataclasses import dataclass, field
from enum import Enum
import json
from pathlib import Path

from .models import VideoConfig, TaskInfo, TaskStatus, Scene, TaskPriority, TaskContext
from .logging_config import get_logger
from .error_handler import with_video_studio_error_handling, VideoStudioErrorType
from .task_scheduler import TaskScheduler, SchedulingStrategy, ResourceManager
from .notification_system import get_notification_system





class WorkflowManager:
    """
    Core workflow manager that coordinates video generation tasks.
    
    Manages task creation, status tracking, progress updates, and provides
    a unified interface for the entire video generation workflow.
    """
    
    def __init__(
        self, 
        max_concurrent_tasks: int = 5,
        scheduling_strategy: SchedulingStrategy = SchedulingStrategy.PRIORITY,
        resource_manager: Optional[ResourceManager] = None
    ):
        """
        Initialize the workflow manager.
        
        Args:
            max_concurrent_tasks: Maximum number of concurrent tasks to process
            scheduling_strategy: Task scheduling strategy
            resource_manager: Optional resource manager instance
        """
        self.logger = get_logger("workflow")
        self.max_concurrent_tasks = max_concurrent_tasks
        
        # Initialize task scheduler
        self.task_scheduler = TaskScheduler(
            max_concurrent_tasks=max_concurrent_tasks,
            strategy=scheduling_strategy,
            resource_manager=resource_manager
        )
        
        # Register task processor with scheduler
        self.task_scheduler.add_task_processor(self._process_scheduled_task)
        
        # Initialize notification system
        self.notification_system = get_notification_system()
        
        # Task storage and tracking
        self._tasks: Dict[str, TaskContext] = {}
        self._active_tasks: Dict[str, asyncio.Task] = {}
        
        # Task processing control
        self._processing_tasks = False
        
        # Statistics and monitoring
        self._task_stats = {
            'total_created': 0,
            'total_completed': 0,
            'total_failed': 0,
            'total_cancelled': 0
        }
        
        self.logger.info(f"WorkflowManager initialized with max_concurrent_tasks={max_concurrent_tasks}, strategy={scheduling_strategy.value}")
    
    async def start(self) -> None:
        """Start the workflow manager and begin processing tasks."""
        if self._processing_tasks:
            self.logger.warning("WorkflowManager is already running")
            return
        
        self._processing_tasks = True
        self._processor_task = asyncio.create_task(self._process_task_queue())
        self.logger.info("WorkflowManager started")
    
    async def stop(self) -> None:
        """Stop the workflow manager and cancel all active tasks."""
        self._processing_tasks = False
        
        # Cancel all active tasks
        for task_id, task in self._active_tasks.items():
            if not task.done():
                task.cancel()
                await self._update_task_status(task_id, TaskStatus.CANCELLED)
        
        # Wait for processor to finish
        if self._processor_task and not self._processor_task.done():
            self._processor_task.cancel()
            try:
                await self._processor_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("WorkflowManager stopped")
    
    @with_video_studio_error_handling(VideoStudioErrorType.WORKFLOW_ERROR)
    async def create_video_task(
        self, 
        config: VideoConfig, 
        priority: TaskPriority = TaskPriority.NORMAL,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create a new video generation task.
        
        Args:
            config: Video configuration for the task
            priority: Task priority level
            metadata: Additional metadata for the task
            
        Returns:
            Unique task ID
            
        Raises:
            ValueError: If configuration is invalid
        """
        # Validate configuration
        if not config.validate():
            raise ValueError("Invalid video configuration provided")
        
        # Generate unique task ID
        task_id = self._generate_task_id()
        
        # Create task info
        now = datetime.now()
        task_info = TaskInfo(
            task_id=task_id,
            status=TaskStatus.PENDING,
            progress=0.0,
            created_at=now,
            updated_at=now,
            config=config
        )
        
        # Create task context
        task_context = TaskContext(
            task_info=task_info,
            priority=priority,
            metadata=metadata or {}
        )
        
        # Store task
        self._tasks[task_id] = task_context
        
        # Schedule task with the scheduler
        resource_requirements = {
            'memory_mb': 1024,  # Default memory requirement
            'gpu_memory_mb': 2048 if config.quality.value == '4k' else 1024
        }
        
        estimated_duration = self._estimate_task_duration(config)
        
        await self.task_scheduler.schedule_task(
            task_id=task_id,
            priority=priority,
            estimated_duration=estimated_duration,
            resource_requirements=resource_requirements
        )
        
        # Update statistics
        self._task_stats['total_created'] += 1
        
        # Send notification
        await self.notification_system.notify_task_created(task_info)
        
        self.logger.info(f"Created video task {task_id} with priority {priority.name}")
        return task_id
    
    async def get_task_status(self, task_id: str) -> Optional[TaskInfo]:
        """
        Get the current status of a task.
        
        Args:
            task_id: Unique task identifier
            
        Returns:
            TaskInfo object or None if task not found
        """
        task_context = self._tasks.get(task_id)
        if not task_context:
            return None
        
        return task_context.task_info
    
    async def get_all_tasks(self) -> List[TaskInfo]:
        """Get status of all tasks."""
        return [context.task_info for context in self._tasks.values()]
    
    async def get_tasks_by_status(self, status: TaskStatus) -> List[TaskInfo]:
        """Get all tasks with a specific status."""
        return [
            context.task_info 
            for context in self._tasks.values() 
            if context.task_info.status == status
        ]
    
    @with_video_studio_error_handling(VideoStudioErrorType.WORKFLOW_ERROR)
    async def cancel_task(self, task_id: str) -> bool:
        """
        Cancel a task.
        
        Args:
            task_id: Unique task identifier
            
        Returns:
            True if task was cancelled, False if not found or already completed
        """
        task_context = self._tasks.get(task_id)
        if not task_context:
            self.logger.warning(f"Task {task_id} not found for cancellation")
            return False
        
        current_status = task_context.task_info.status
        
        # Can only cancel pending or processing tasks
        if current_status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
            self.logger.warning(f"Cannot cancel task {task_id} with status {current_status}")
            return False
        
        # Cancel task in scheduler
        await self.task_scheduler.cancel_task(task_id)
        
        # Update status
        await self._update_task_status(task_id, TaskStatus.CANCELLED)
        self._task_stats['total_cancelled'] += 1
        
        self.logger.info(f"Cancelled task {task_id}")
        return True
    
    @with_video_studio_error_handling(VideoStudioErrorType.WORKFLOW_ERROR)
    async def retry_failed_task(self, task_id: str) -> bool:
        """
        Retry a failed task.
        
        Args:
            task_id: Unique task identifier
            
        Returns:
            True if task was queued for retry, False otherwise
        """
        task_context = self._tasks.get(task_id)
        if not task_context:
            self.logger.warning(f"Task {task_id} not found for retry")
            return False
        
        if task_context.task_info.status != TaskStatus.FAILED:
            self.logger.warning(f"Cannot retry task {task_id} with status {task_context.task_info.status}")
            return False
        
        if task_context.retry_count >= task_context.max_retries:
            self.logger.warning(f"Task {task_id} has exceeded maximum retries ({task_context.max_retries})")
            return False
        
        # Reset task status and increment retry count
        task_context.retry_count += 1
        await self._update_task_status(task_id, TaskStatus.PENDING, progress=0.0)
        
        # Re-schedule task
        config = task_context.task_info.config
        resource_requirements = {
            'memory_mb': 1024,
            'gpu_memory_mb': 2048 if config.quality.value == '4k' else 1024
        }
        
        estimated_duration = self._estimate_task_duration(config)
        
        await self.task_scheduler.schedule_task(
            task_id=task_id,
            priority=task_context.priority,
            estimated_duration=estimated_duration,
            resource_requirements=resource_requirements
        )
        
        self.logger.info(f"Queued task {task_id} for retry (attempt {task_context.retry_count})")
        return True
    
    async def update_task_progress(self, task_id: str, progress: float, status: Optional[TaskStatus] = None) -> bool:
        """
        Update task progress and optionally status.
        
        Args:
            task_id: Unique task identifier
            progress: Progress value between 0.0 and 1.0
            status: Optional new status
            
        Returns:
            True if update was successful, False otherwise
        """
        if not (0.0 <= progress <= 1.0):
            raise ValueError("Progress must be between 0.0 and 1.0")
        
        task_context = self._tasks.get(task_id)
        if not task_context:
            return False
        
        # Update progress
        task_context.task_info.progress = progress
        task_context.task_info.updated_at = datetime.now()
        
        # Update status if provided
        if status:
            task_context.task_info.status = status
        
        # Send progress notification
        await self.notification_system.notify_task_progress(task_context.task_info)
        
        # Execute callbacks
        for callback in task_context.callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(task_context.task_info)
                else:
                    callback(task_context.task_info)
            except Exception as e:
                self.logger.error(f"Error executing callback for task {task_id}: {e}")
        
        return True
    
    def add_task_callback(self, task_id: str, callback: Callable) -> bool:
        """
        Add a callback function to be called when task status/progress updates.
        
        Args:
            task_id: Unique task identifier
            callback: Callback function that accepts TaskInfo
            
        Returns:
            True if callback was added, False if task not found
        """
        task_context = self._tasks.get(task_id)
        if not task_context:
            return False
        
        task_context.callbacks.append(callback)
        return True
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get workflow manager statistics."""
        scheduler_status = await self.task_scheduler.get_queue_status()
        
        return {
            **self._task_stats,
            'scheduler_status': scheduler_status,
            'max_concurrent': self.max_concurrent_tasks,
            'is_processing': self._processing_tasks
        }
    
    def _generate_task_id(self) -> str:
        """Generate a unique task ID."""
        # Use UUID4 for guaranteed uniqueness
        return f"task_{uuid.uuid4().hex[:12]}"
    
    async def _update_task_status(
        self, 
        task_id: str, 
        status: TaskStatus, 
        progress: Optional[float] = None,
        error_message: Optional[str] = None,
        result_url: Optional[str] = None
    ) -> None:
        """Internal method to update task status."""
        task_context = self._tasks.get(task_id)
        if not task_context:
            return
        
        task_context.task_info.status = status
        task_context.task_info.updated_at = datetime.now()
        
        if progress is not None:
            task_context.task_info.progress = progress
        
        if error_message is not None:
            task_context.task_info.error_message = error_message
        
        if result_url is not None:
            task_context.task_info.result_url = result_url
        
        # Send status notifications
        if status == TaskStatus.PROCESSING:
            await self.notification_system.notify_task_started(task_context.task_info)
        elif status == TaskStatus.COMPLETED:
            await self.notification_system.notify_task_completed(task_context.task_info)
            self._task_stats['total_completed'] += 1
        elif status == TaskStatus.FAILED:
            await self.notification_system.notify_task_failed(task_context.task_info)
            self._task_stats['total_failed'] += 1
        elif status == TaskStatus.CANCELLED:
            await self.notification_system.notify_task_cancelled(task_context.task_info)
    
    async def _process_scheduled_task(self, task_id: str, scheduled_task) -> None:
        """Process a task scheduled by the task scheduler."""
        try:
            task_context = self._tasks.get(task_id)
            if not task_context:
                self.logger.warning(f"Task context not found for scheduled task {task_id}")
                return
            
            # Start processing the task
            processing_task = asyncio.create_task(self._process_single_task(task_id))
            self._active_tasks[task_id] = processing_task
            
            # Wait for completion
            await processing_task
            
        except Exception as e:
            self.logger.error(f"Error processing scheduled task {task_id}: {e}")
            await self._update_task_status(task_id, TaskStatus.FAILED, error_message=str(e))
        finally:
            # Clean up
            self._active_tasks.pop(task_id, None)
    
    async def _process_single_task(self, task_id: str) -> None:
        """Process a single task."""
        try:
            task_context = self._tasks.get(task_id)
            if not task_context:
                return
            
            self.logger.info(f"Starting processing of task {task_id}")
            
            # Update status to processing
            await self._update_task_status(task_id, TaskStatus.PROCESSING, progress=0.1)
            
            # Simulate video generation process
            # In real implementation, this would call the generation engine
            config = task_context.task_info.config
            
            # Simulate processing stages
            stages = [
                ("Preparing assets", 0.2),
                ("Generating scenes", 0.5),
                ("Rendering video", 0.8),
                ("Finalizing output", 1.0)
            ]
            
            for stage_name, progress in stages:
                self.logger.debug(f"Task {task_id}: {stage_name}")
                await self.update_task_progress(task_id, progress, TaskStatus.GENERATING)
                
                # Simulate processing time
                await asyncio.sleep(1.0)
            
            # Mark as completed
            result_url = f"/results/{task_id}.mp4"
            await self._update_task_status(
                task_id, 
                TaskStatus.COMPLETED, 
                progress=1.0,
                result_url=result_url
            )
            
            self.logger.info(f"Completed processing of task {task_id}")
            
        except asyncio.CancelledError:
            self.logger.info(f"Task {task_id} was cancelled")
            await self._update_task_status(task_id, TaskStatus.CANCELLED)
            raise
        except Exception as e:
            self.logger.error(f"Error processing task {task_id}: {e}")
            await self._update_task_status(
                task_id, 
                TaskStatus.FAILED, 
                error_message=str(e)
            )
        finally:
            # Remove from active tasks
            self._active_tasks.pop(task_id, None)
    
    def _estimate_task_duration(self, config: VideoConfig) -> float:
        """Estimate task duration based on configuration."""
        base_duration = 30.0  # Base 30 seconds
        
        # Adjust for video duration
        duration_factor = config.duration / 10.0  # 10 seconds as baseline
        
        # Adjust for quality
        quality_multiplier = {
            '720p': 1.0,
            '1080p': 1.5,
            '4k': 3.0
        }.get(config.quality.value, 1.0)
        
        # Adjust for number of scenes
        scene_factor = len(config.scenes) * 0.5 if config.scenes else 1.0
        
        return base_duration * duration_factor * quality_multiplier * scene_factor
    
    async def _cleanup_completed_tasks(self) -> None:
        """Clean up completed active tasks."""
        completed_tasks = []
        for task_id, task in self._active_tasks.items():
            if task.done():
                completed_tasks.append(task_id)
        
        for task_id in completed_tasks:
            self._active_tasks.pop(task_id, None)


# Global workflow manager instance
_workflow_manager: Optional[WorkflowManager] = None


async def get_workflow_manager(max_concurrent_tasks: int = 5) -> WorkflowManager:
    """Get or create the global workflow manager instance."""
    global _workflow_manager
    
    if _workflow_manager is None:
        _workflow_manager = WorkflowManager(max_concurrent_tasks)
        await _workflow_manager.start()
    
    return _workflow_manager


async def create_video_task(config: VideoConfig, priority: TaskPriority = TaskPriority.NORMAL) -> str:
    """Convenience function to create a video task."""
    manager = await get_workflow_manager()
    return await manager.create_video_task(config, priority)


async def get_task_status(task_id: str) -> Optional[TaskInfo]:
    """Convenience function to get task status."""
    manager = await get_workflow_manager()
    return await manager.get_task_status(task_id)


async def cancel_task(task_id: str) -> bool:
    """Convenience function to cancel a task."""
    manager = await get_workflow_manager()
    return await manager.cancel_task(task_id)