"""
Advanced Task Scheduler for Video Studio.

This module provides sophisticated task scheduling capabilities including priority queues,
concurrent processing, load balancing, and resource management for video generation tasks.
"""

import asyncio
import heapq
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
import weakref
from collections import defaultdict, deque

from .models import TaskStatus, TaskPriority, TaskContext
from .logging_config import get_logger
from .error_handler import with_video_studio_error_handling, VideoStudioErrorType


class SchedulingStrategy(Enum):
    """Task scheduling strategies."""
    FIFO = "fifo"  # First In, First Out
    PRIORITY = "priority"  # Priority-based scheduling
    ROUND_ROBIN = "round_robin"  # Round-robin by priority
    SHORTEST_JOB_FIRST = "shortest_job_first"  # Estimated shortest duration first


@dataclass
class ScheduledTask:
    """Wrapper for tasks in the scheduler queue."""
    task_id: str
    priority: TaskPriority
    created_at: datetime
    estimated_duration: Optional[float] = None
    dependencies: Set[str] = field(default_factory=set)
    resource_requirements: Dict[str, Any] = field(default_factory=dict)
    
    def __lt__(self, other: 'ScheduledTask') -> bool:
        """Comparison for priority queue (higher priority first)."""
        if self.priority.value != other.priority.value:
            return self.priority.value > other.priority.value
        return self.created_at < other.created_at


class ResourceManager:
    """Manages system resources for task execution."""
    
    def __init__(self, max_memory_mb: int = 4096, max_gpu_memory_mb: int = 8192):
        """
        Initialize resource manager.
        
        Args:
            max_memory_mb: Maximum system memory in MB
            max_gpu_memory_mb: Maximum GPU memory in MB
        """
        self.max_memory_mb = max_memory_mb
        self.max_gpu_memory_mb = max_gpu_memory_mb
        
        self.allocated_memory_mb = 0
        self.allocated_gpu_memory_mb = 0
        
        self.resource_locks: Dict[str, asyncio.Lock] = {}
        self.logger = get_logger("resource_manager")
    
    async def acquire_resources(self, requirements: Dict[str, Any]) -> bool:
        """
        Try to acquire required resources for a task.
        
        Args:
            requirements: Dictionary of resource requirements
            
        Returns:
            True if resources were acquired, False otherwise
        """
        memory_needed = requirements.get('memory_mb', 512)
        gpu_memory_needed = requirements.get('gpu_memory_mb', 0)
        
        # Check if resources are available
        if (self.allocated_memory_mb + memory_needed > self.max_memory_mb or
            self.allocated_gpu_memory_mb + gpu_memory_needed > self.max_gpu_memory_mb):
            return False
        
        # Allocate resources
        self.allocated_memory_mb += memory_needed
        self.allocated_gpu_memory_mb += gpu_memory_needed
        
        self.logger.debug(f"Allocated resources: {memory_needed}MB RAM, {gpu_memory_needed}MB GPU")
        return True
    
    async def release_resources(self, requirements: Dict[str, Any]) -> None:
        """Release resources after task completion."""
        memory_to_release = requirements.get('memory_mb', 512)
        gpu_memory_to_release = requirements.get('gpu_memory_mb', 0)
        
        self.allocated_memory_mb = max(0, self.allocated_memory_mb - memory_to_release)
        self.allocated_gpu_memory_mb = max(0, self.allocated_gpu_memory_mb - gpu_memory_to_release)
        
        self.logger.debug(f"Released resources: {memory_to_release}MB RAM, {gpu_memory_to_release}MB GPU")
    
    def get_resource_usage(self) -> Dict[str, Any]:
        """Get current resource usage statistics."""
        return {
            'memory_usage_mb': self.allocated_memory_mb,
            'memory_usage_percent': (self.allocated_memory_mb / self.max_memory_mb) * 100,
            'gpu_memory_usage_mb': self.allocated_gpu_memory_mb,
            'gpu_memory_usage_percent': (self.allocated_gpu_memory_mb / self.max_gpu_memory_mb) * 100,
            'max_memory_mb': self.max_memory_mb,
            'max_gpu_memory_mb': self.max_gpu_memory_mb
        }


class TaskScheduler:
    """
    Advanced task scheduler with priority queues, resource management, and load balancing.
    """
    
    def __init__(
        self,
        max_concurrent_tasks: int = 5,
        strategy: SchedulingStrategy = SchedulingStrategy.PRIORITY,
        resource_manager: Optional[ResourceManager] = None
    ):
        """
        Initialize the task scheduler.
        
        Args:
            max_concurrent_tasks: Maximum number of concurrent tasks
            strategy: Scheduling strategy to use
            resource_manager: Optional resource manager instance
        """
        self.max_concurrent_tasks = max_concurrent_tasks
        self.strategy = strategy
        self.resource_manager = resource_manager or ResourceManager()
        
        # Task queues by priority
        self._priority_queues: Dict[TaskPriority, List[ScheduledTask]] = {
            priority: [] for priority in TaskPriority
        }
        
        # Round-robin state for priority queues
        self._round_robin_index = 0
        self._priority_order = list(TaskPriority)
        
        # Active tasks and dependencies
        self._active_tasks: Dict[str, asyncio.Task] = {}
        self._task_dependencies: Dict[str, Set[str]] = {}
        self._dependency_waiters: Dict[str, List[str]] = defaultdict(list)
        
        # Task execution callbacks
        self._task_processors: List[Callable] = []
        
        # Statistics
        self._stats = {
            'tasks_scheduled': 0,
            'tasks_completed': 0,
            'tasks_failed': 0,
            'average_wait_time': 0.0,
            'average_execution_time': 0.0
        }
        
        # Timing tracking
        self._task_timings: Dict[str, Dict[str, datetime]] = {}
        
        self.logger = get_logger("task_scheduler")
        self.logger.info(f"TaskScheduler initialized with strategy={strategy.value}, max_concurrent={max_concurrent_tasks}")
    
    def add_task_processor(self, processor: Callable) -> None:
        """Add a task processor function."""
        self._task_processors.append(processor)
    
    @with_video_studio_error_handling(VideoStudioErrorType.WORKFLOW_ERROR)
    async def schedule_task(
        self,
        task_id: str,
        priority: TaskPriority = TaskPriority.NORMAL,
        estimated_duration: Optional[float] = None,
        dependencies: Optional[Set[str]] = None,
        resource_requirements: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Schedule a task for execution.
        
        Args:
            task_id: Unique task identifier
            priority: Task priority level
            estimated_duration: Estimated execution time in seconds
            dependencies: Set of task IDs this task depends on
            resource_requirements: Resource requirements for the task
            
        Returns:
            True if task was scheduled successfully
        """
        dependencies = dependencies or set()
        resource_requirements = resource_requirements or {}
        
        # Check if dependencies are satisfied
        unsatisfied_deps = self._check_dependencies(dependencies)
        if unsatisfied_deps:
            self._task_dependencies[task_id] = dependencies
            for dep_id in unsatisfied_deps:
                self._dependency_waiters[dep_id].append(task_id)
            self.logger.info(f"Task {task_id} waiting for dependencies: {unsatisfied_deps}")
            return True
        
        # Create scheduled task
        scheduled_task = ScheduledTask(
            task_id=task_id,
            priority=priority,
            created_at=datetime.now(),
            estimated_duration=estimated_duration,
            dependencies=dependencies,
            resource_requirements=resource_requirements
        )
        
        # Add to appropriate queue based on strategy
        if self.strategy == SchedulingStrategy.SHORTEST_JOB_FIRST and estimated_duration:
            # Insert in order of estimated duration
            queue = self._priority_queues[priority]
            inserted = False
            for i, existing_task in enumerate(queue):
                if (existing_task.estimated_duration is None or 
                    estimated_duration < existing_task.estimated_duration):
                    queue.insert(i, scheduled_task)
                    inserted = True
                    break
            if not inserted:
                queue.append(scheduled_task)
        else:
            # Add to priority queue
            if self.strategy == SchedulingStrategy.PRIORITY:
                heapq.heappush(self._priority_queues[priority], scheduled_task)
            else:
                self._priority_queues[priority].append(scheduled_task)
        
        # Track timing
        self._task_timings[task_id] = {'scheduled_at': datetime.now()}
        
        self._stats['tasks_scheduled'] += 1
        self.logger.info(f"Scheduled task {task_id} with priority {priority.name}")
        
        # Try to start processing immediately
        await self._try_start_next_task()
        
        return True
    
    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a scheduled or running task."""
        # Check if task is currently running
        if task_id in self._active_tasks:
            task = self._active_tasks[task_id]
            if not task.done():
                task.cancel()
            self._active_tasks.pop(task_id, None)
            await self._release_task_resources(task_id)
            self.logger.info(f"Cancelled running task {task_id}")
            return True
        
        # Check if task is in queues
        for priority_queue in self._priority_queues.values():
            for i, scheduled_task in enumerate(priority_queue):
                if scheduled_task.task_id == task_id:
                    priority_queue.pop(i)
                    self.logger.info(f"Cancelled queued task {task_id}")
                    return True
        
        return False
    
    async def get_queue_status(self) -> Dict[str, Any]:
        """Get current queue status and statistics."""
        queue_sizes = {
            priority.name: len(queue) 
            for priority, queue in self._priority_queues.items()
        }
        
        total_queued = sum(queue_sizes.values())
        active_count = len(self._active_tasks)
        
        return {
            'queue_sizes': queue_sizes,
            'total_queued': total_queued,
            'active_tasks': active_count,
            'max_concurrent': self.max_concurrent_tasks,
            'strategy': self.strategy.value,
            'resource_usage': self.resource_manager.get_resource_usage(),
            'statistics': self._stats.copy()
        }
    
    async def _try_start_next_task(self) -> bool:
        """Try to start the next available task."""
        if len(self._active_tasks) >= self.max_concurrent_tasks:
            return False
        
        # Get next task based on strategy
        next_task = self._get_next_task()
        if not next_task:
            return False
        
        # Check resource availability
        if not await self.resource_manager.acquire_resources(next_task.resource_requirements):
            self.logger.debug(f"Insufficient resources for task {next_task.task_id}")
            return False
        
        # Start the task
        await self._start_task(next_task)
        return True
    
    def _get_next_task(self) -> Optional[ScheduledTask]:
        """Get the next task to execute based on scheduling strategy."""
        if self.strategy == SchedulingStrategy.FIFO:
            return self._get_fifo_task()
        elif self.strategy == SchedulingStrategy.PRIORITY:
            return self._get_priority_task()
        elif self.strategy == SchedulingStrategy.ROUND_ROBIN:
            return self._get_round_robin_task()
        elif self.strategy == SchedulingStrategy.SHORTEST_JOB_FIRST:
            return self._get_shortest_job_task()
        else:
            return self._get_priority_task()  # Default fallback
    
    def _get_fifo_task(self) -> Optional[ScheduledTask]:
        """Get next task using FIFO strategy."""
        earliest_task = None
        earliest_time = None
        source_queue = None
        
        for priority, queue in self._priority_queues.items():
            if queue:
                task = queue[0]
                if earliest_time is None or task.created_at < earliest_time:
                    earliest_task = task
                    earliest_time = task.created_at
                    source_queue = queue
        
        if earliest_task and source_queue is not None:
            source_queue.pop(0)
            return earliest_task
        
        return None
    
    def _get_priority_task(self) -> Optional[ScheduledTask]:
        """Get next task using priority strategy."""
        for priority in reversed(TaskPriority):  # Highest priority first
            queue = self._priority_queues[priority]
            if queue:
                if isinstance(queue, list) and queue:
                    return heapq.heappop(queue) if len(queue) > 1 else queue.pop(0)
        return None
    
    def _get_round_robin_task(self) -> Optional[ScheduledTask]:
        """Get next task using round-robin strategy."""
        attempts = 0
        while attempts < len(TaskPriority):
            priority = self._priority_order[self._round_robin_index]
            self._round_robin_index = (self._round_robin_index + 1) % len(TaskPriority)
            
            queue = self._priority_queues[priority]
            if queue:
                return queue.pop(0)
            
            attempts += 1
        
        return None
    
    def _get_shortest_job_task(self) -> Optional[ScheduledTask]:
        """Get next task using shortest job first strategy."""
        shortest_task = None
        shortest_duration = None
        source_queue = None
        
        for priority, queue in self._priority_queues.items():
            for task in queue:
                if task.estimated_duration is not None:
                    if shortest_duration is None or task.estimated_duration < shortest_duration:
                        shortest_task = task
                        shortest_duration = task.estimated_duration
                        source_queue = queue
        
        if shortest_task and source_queue is not None:
            source_queue.remove(shortest_task)
            return shortest_task
        
        # Fallback to priority if no estimated durations
        return self._get_priority_task()
    
    async def _start_task(self, scheduled_task: ScheduledTask) -> None:
        """Start executing a scheduled task."""
        task_id = scheduled_task.task_id
        
        # Record start time
        if task_id in self._task_timings:
            self._task_timings[task_id]['started_at'] = datetime.now()
        
        # Create and start the task
        async_task = asyncio.create_task(self._execute_task(scheduled_task))
        self._active_tasks[task_id] = async_task
        
        self.logger.info(f"Started executing task {task_id}")
    
    async def _execute_task(self, scheduled_task: ScheduledTask) -> None:
        """Execute a single task."""
        task_id = scheduled_task.task_id
        
        try:
            # Call all registered task processors
            for processor in self._task_processors:
                if asyncio.iscoroutinefunction(processor):
                    await processor(task_id, scheduled_task)
                else:
                    processor(task_id, scheduled_task)
            
            # Record completion
            self._stats['tasks_completed'] += 1
            
            # Update timing statistics
            if task_id in self._task_timings:
                timings = self._task_timings[task_id]
                timings['completed_at'] = datetime.now()
                
                if 'started_at' in timings:
                    execution_time = (timings['completed_at'] - timings['started_at']).total_seconds()
                    self._update_average_execution_time(execution_time)
                
                if 'scheduled_at' in timings:
                    wait_time = (timings['started_at'] - timings['scheduled_at']).total_seconds()
                    self._update_average_wait_time(wait_time)
            
            self.logger.info(f"Completed task {task_id}")
            
        except asyncio.CancelledError:
            self.logger.info(f"Task {task_id} was cancelled")
            raise
        except Exception as e:
            self.logger.error(f"Task {task_id} failed: {e}")
            self._stats['tasks_failed'] += 1
            raise
        finally:
            # Clean up
            self._active_tasks.pop(task_id, None)
            await self._release_task_resources(task_id)
            await self._handle_task_completion(task_id)
            
            # Try to start next task
            await self._try_start_next_task()
    
    async def _release_task_resources(self, task_id: str) -> None:
        """Release resources allocated to a task."""
        # Find the task's resource requirements
        for priority_queue in self._priority_queues.values():
            for task in priority_queue:
                if task.task_id == task_id:
                    await self.resource_manager.release_resources(task.resource_requirements)
                    return
    
    async def _handle_task_completion(self, completed_task_id: str) -> None:
        """Handle completion of a task and check for dependent tasks."""
        # Check if any tasks were waiting for this one
        waiting_tasks = self._dependency_waiters.pop(completed_task_id, [])
        
        for waiting_task_id in waiting_tasks:
            dependencies = self._task_dependencies.get(waiting_task_id, set())
            dependencies.discard(completed_task_id)
            
            # If all dependencies are satisfied, schedule the task
            if not dependencies:
                self._task_dependencies.pop(waiting_task_id, None)
                # The task should already be created, just need to move it to active scheduling
                self.logger.info(f"Dependencies satisfied for task {waiting_task_id}")
    
    def _check_dependencies(self, dependencies: Set[str]) -> Set[str]:
        """Check which dependencies are not yet satisfied."""
        unsatisfied = set()
        for dep_id in dependencies:
            # Check if dependency is still active or queued
            if (dep_id in self._active_tasks or 
                any(task.task_id == dep_id for queue in self._priority_queues.values() for task in queue)):
                unsatisfied.add(dep_id)
        return unsatisfied
    
    def _update_average_execution_time(self, execution_time: float) -> None:
        """Update the rolling average execution time."""
        current_avg = self._stats['average_execution_time']
        completed_count = self._stats['tasks_completed']
        
        if completed_count == 1:
            self._stats['average_execution_time'] = execution_time
        else:
            # Simple moving average
            self._stats['average_execution_time'] = (
                (current_avg * (completed_count - 1) + execution_time) / completed_count
            )
    
    def _update_average_wait_time(self, wait_time: float) -> None:
        """Update the rolling average wait time."""
        current_avg = self._stats['average_wait_time']
        completed_count = self._stats['tasks_completed']
        
        if completed_count == 1:
            self._stats['average_wait_time'] = wait_time
        else:
            # Simple moving average
            self._stats['average_wait_time'] = (
                (current_avg * (completed_count - 1) + wait_time) / completed_count
            )


# Global scheduler instance
_task_scheduler: Optional[TaskScheduler] = None


def get_task_scheduler(
    max_concurrent_tasks: int = 5,
    strategy: SchedulingStrategy = SchedulingStrategy.PRIORITY
) -> TaskScheduler:
    """Get or create the global task scheduler instance."""
    global _task_scheduler
    
    if _task_scheduler is None:
        _task_scheduler = TaskScheduler(max_concurrent_tasks, strategy)
    
    return _task_scheduler


async def schedule_task(
    task_id: str,
    priority: TaskPriority = TaskPriority.NORMAL,
    estimated_duration: Optional[float] = None,
    dependencies: Optional[Set[str]] = None,
    resource_requirements: Optional[Dict[str, Any]] = None
) -> bool:
    """Convenience function to schedule a task."""
    scheduler = get_task_scheduler()
    return await scheduler.schedule_task(
        task_id, priority, estimated_duration, dependencies, resource_requirements
    )