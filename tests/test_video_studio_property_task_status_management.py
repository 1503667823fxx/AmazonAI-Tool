"""
Property-based tests for Video Studio task status management consistency
Tests that task status management provides real-time updates, error notifications, and detailed status information
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import asyncio
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any, Set
from unittest.mock import AsyncMock, MagicMock

from app_utils.video_studio.workflow_manager import WorkflowManager
from app_utils.video_studio.models import (
    VideoConfig, AspectRatio, VideoQuality, AudioConfig, Scene, TextOverlay,
    TaskInfo, TaskStatus, TaskPriority, TaskContext
)
from app_utils.video_studio.notification_system import (
    NotificationSystem, NotificationType, NotificationChannel, NotificationMessage
)


def generate_valid_video_config(seed=None):
    """Generate valid VideoConfig instances for testing."""
    if seed is not None:
        random.seed(seed)
    
    template_id = f"template_{random.randint(1, 1000)}"
    input_images = [f"image_{i}.jpg" for i in range(random.randint(1, 3))]
    duration = random.randint(5, 60)  # 5 seconds to 1 minute
    aspect_ratio = random.choice(list(AspectRatio))
    style = f"style_{random.randint(1, 50)}"
    quality = random.choice(list(VideoQuality))
    
    # Optional audio config
    audio_config = None
    if random.choice([True, False]):
        audio_config = AudioConfig(
            enabled=True,
            volume=random.uniform(0.1, 1.0),
            fade_in=random.uniform(0.0, 2.0),
            fade_out=random.uniform(0.0, 2.0)
        )
    
    return VideoConfig(
        template_id=template_id,
        input_images=input_images,
        duration=duration,
        aspect_ratio=aspect_ratio,
        style=style,
        quality=quality,
        audio_config=audio_config
    )


async def test_real_time_progress_updates_property():
    """
    **Feature: video-studio-redesign, Property 8: 任务状态管理一致性**
    **Validates: Requirements 5.1**
    
    Property: For any video generation task, the workflow manager should provide
    real-time progress updates that are monotonically increasing and accurate.
    """
    print("Testing real-time progress updates property...")
    
    workflow_manager = WorkflowManager(max_concurrent_tasks=3)
    progress_updates = []
    
    # Mock notification system to capture progress updates
    original_notify_progress = workflow_manager.notification_system.notify_task_progress
    
    async def capture_progress(task_info):
        progress_updates.append({
            'task_id': task_info.task_id,
            'progress': task_info.progress,
            'status': task_info.status,
            'timestamp': task_info.updated_at
        })
        await original_notify_progress(task_info)
    
    workflow_manager.notification_system.notify_task_progress = capture_progress
    
    try:
        await workflow_manager.start()
        
        # Create multiple tasks with different configurations
        configs = [generate_valid_video_config(seed=i) for i in range(5)]
        valid_configs = [config for config in configs if config.validate()]
        
        if len(valid_configs) < 3:
            print("Not enough valid configs, skipping test...")
            return
        
        task_ids = []
        for config in valid_configs[:3]:  # Test with 3 tasks
            task_id = await workflow_manager.create_video_task(config)
            task_ids.append(task_id)
        
        # Wait for some processing to occur
        await asyncio.sleep(3.0)
        
        # Verify progress updates properties
        task_progress_by_id = {}
        for update in progress_updates:
            task_id = update['task_id']
            if task_id not in task_progress_by_id:
                task_progress_by_id[task_id] = []
            task_progress_by_id[task_id].append(update)
        
        for task_id, updates in task_progress_by_id.items():
            if len(updates) < 2:
                continue  # Need at least 2 updates to test monotonicity
            
            # Sort by timestamp
            updates.sort(key=lambda x: x['timestamp'])
            
            # Verify monotonic progress increase
            for i in range(1, len(updates)):
                prev_progress = updates[i-1]['progress']
                curr_progress = updates[i]['progress']
                
                assert curr_progress >= prev_progress, \
                    f"Progress decreased for task {task_id}: {prev_progress} -> {curr_progress}"
                
                # Verify progress is within valid range
                assert 0.0 <= curr_progress <= 1.0, \
                    f"Invalid progress value for task {task_id}: {curr_progress}"
            
            # Verify timestamps are increasing
            for i in range(1, len(updates)):
                prev_time = updates[i-1]['timestamp']
                curr_time = updates[i]['timestamp']
                
                assert curr_time >= prev_time, \
                    f"Timestamp decreased for task {task_id}: {prev_time} -> {curr_time}"
        
        print(f"✓ Verified monotonic progress updates for {len(task_progress_by_id)} tasks")
        
    finally:
        await workflow_manager.stop()


async def test_immediate_error_notifications_property():
    """
    **Feature: video-studio-redesign, Property 8: 任务状态管理一致性**
    **Validates: Requirements 5.2**
    
    Property: For any task that encounters an error during processing, the system
    should immediately notify users and provide error information.
    """
    print("Testing immediate error notifications property...")
    
    workflow_manager = WorkflowManager(max_concurrent_tasks=2)
    error_notifications = []
    
    # Mock notification system to capture error notifications
    original_notify_failed = workflow_manager.notification_system.notify_task_failed
    
    async def capture_error_notification(task_info):
        error_notifications.append({
            'task_id': task_info.task_id,
            'error_message': task_info.error_message,
            'status': task_info.status,
            'timestamp': task_info.updated_at
        })
        await original_notify_failed(task_info)
    
    workflow_manager.notification_system.notify_task_failed = capture_error_notification
    
    # Mock the task processing to simulate errors
    original_process_single_task = workflow_manager._process_single_task
    
    async def mock_process_with_error(task_id):
        """Mock task processing that fails for certain tasks."""
        try:
            # Simulate some processing
            await asyncio.sleep(0.1)
            
            # Fail tasks with specific patterns to test error handling
            if "error" in task_id or random.random() < 0.5:  # 50% failure rate
                raise Exception(f"Simulated processing error for task {task_id}")
            
            # Otherwise process normally (but shortened)
            await workflow_manager._update_task_status(task_id, TaskStatus.PROCESSING, progress=0.5)
            await asyncio.sleep(0.1)
            await workflow_manager._update_task_status(task_id, TaskStatus.COMPLETED, progress=1.0)
            
        except Exception as e:
            await workflow_manager._update_task_status(
                task_id, TaskStatus.FAILED, error_message=str(e)
            )
    
    workflow_manager._process_single_task = mock_process_with_error
    
    try:
        await workflow_manager.start()
        
        # Create tasks that will trigger errors
        configs = [generate_valid_video_config(seed=i) for i in range(8)]
        valid_configs = [config for config in configs if config.validate()]
        
        if len(valid_configs) < 4:
            print("Not enough valid configs, skipping test...")
            return
        
        task_ids = []
        for config in valid_configs[:6]:  # Create 6 tasks
            task_id = await workflow_manager.create_video_task(config)
            task_ids.append(task_id)
        
        # Wait for processing to complete
        await asyncio.sleep(2.0)
        
        # Verify error notifications were sent
        assert len(error_notifications) > 0, "No error notifications were captured"
        
        for notification in error_notifications:
            # Verify error notification properties
            assert notification['status'] == TaskStatus.FAILED, \
                f"Error notification has wrong status: {notification['status']}"
            
            assert notification['error_message'] is not None, \
                f"Error notification missing error message for task {notification['task_id']}"
            
            assert isinstance(notification['error_message'], str), \
                f"Error message is not a string: {type(notification['error_message'])}"
            
            assert len(notification['error_message']) > 0, \
                f"Error message is empty for task {notification['task_id']}"
            
            # Verify timestamp is recent (within last few seconds)
            time_diff = datetime.now() - notification['timestamp']
            assert time_diff.total_seconds() < 10, \
                f"Error notification timestamp too old: {time_diff.total_seconds()}s"
        
        print(f"✓ Verified immediate error notifications for {len(error_notifications)} failed tasks")
        
    finally:
        await workflow_manager.stop()


async def test_detailed_task_status_information_property():
    """
    **Feature: video-studio-redesign, Property 8: 任务状态管理一致性**
    **Validates: Requirements 5.4**
    
    Property: For any task status query, the system should return detailed and
    accurate task information including status, progress, timestamps, and configuration.
    """
    print("Testing detailed task status information property...")
    
    workflow_manager = WorkflowManager(max_concurrent_tasks=3)
    
    try:
        await workflow_manager.start()
        
        # Create tasks with various configurations
        configs = [generate_valid_video_config(seed=i) for i in range(10)]
        valid_configs = [config for config in configs if config.validate()]
        
        if len(valid_configs) < 5:
            print("Not enough valid configs, skipping test...")
            return
        
        created_tasks = []
        for config in valid_configs[:5]:
            task_id = await workflow_manager.create_video_task(config)
            created_tasks.append((task_id, config))
        
        # Allow some processing time
        await asyncio.sleep(1.0)
        
        # Test detailed status information for each task
        for task_id, original_config in created_tasks:
            task_info = await workflow_manager.get_task_status(task_id)
            
            # Verify task info is returned
            assert task_info is not None, f"No task info returned for task {task_id}"
            
            # Verify required fields are present and valid
            assert task_info.task_id == task_id, \
                f"Task ID mismatch: expected {task_id}, got {task_info.task_id}"
            
            assert isinstance(task_info.status, TaskStatus), \
                f"Invalid status type: {type(task_info.status)}"
            
            assert 0.0 <= task_info.progress <= 1.0, \
                f"Invalid progress value: {task_info.progress}"
            
            assert isinstance(task_info.created_at, datetime), \
                f"Invalid created_at type: {type(task_info.created_at)}"
            
            assert isinstance(task_info.updated_at, datetime), \
                f"Invalid updated_at type: {type(task_info.updated_at)}"
            
            # Verify timestamps are logical
            assert task_info.updated_at >= task_info.created_at, \
                f"Updated timestamp before created timestamp for task {task_id}"
            
            # Verify configuration is preserved
            if task_info.config:
                assert task_info.config.template_id == original_config.template_id, \
                    f"Template ID mismatch for task {task_id}"
                
                assert task_info.config.duration == original_config.duration, \
                    f"Duration mismatch for task {task_id}"
                
                assert task_info.config.quality == original_config.quality, \
                    f"Quality mismatch for task {task_id}"
            
            # Verify task info validation passes
            assert task_info.validate(), f"Task info validation failed for task {task_id}"
        
        # Test querying all tasks
        all_tasks = await workflow_manager.get_all_tasks()
        assert len(all_tasks) >= len(created_tasks), \
            f"Not all tasks returned: expected at least {len(created_tasks)}, got {len(all_tasks)}"
        
        # Test querying by status
        for status in TaskStatus:
            tasks_by_status = await workflow_manager.get_tasks_by_status(status)
            
            # Verify all returned tasks have the correct status
            for task_info in tasks_by_status:
                assert task_info.status == status, \
                    f"Task {task_info.task_id} has wrong status: expected {status}, got {task_info.status}"
        
        print(f"✓ Verified detailed status information for {len(created_tasks)} tasks")
        
    finally:
        await workflow_manager.stop()


async def test_multi_channel_completion_notifications_property():
    """
    **Feature: video-studio-redesign, Property 8: 任务状态管理一致性**
    **Validates: Requirements 5.5**
    
    Property: For any completed task, the system should notify users through
    multiple channels (WebSocket, email, etc.) as configured.
    """
    print("Testing multi-channel completion notifications property...")
    
    workflow_manager = WorkflowManager(max_concurrent_tasks=2)
    
    # Track notifications by channel
    notifications_by_channel = {
        NotificationChannel.WEBSOCKET: [],
        NotificationChannel.EMAIL: [],
        NotificationChannel.WEBHOOK: []
    }
    
    # Mock notification handlers to capture notifications
    original_send_notification = workflow_manager.notification_system.send_notification
    
    async def capture_notifications(notification_type, title, message, task_id=None, channels=None, metadata=None):
        """Capture notifications sent through different channels."""
        result = await original_send_notification(
            notification_type, title, message, task_id, channels, metadata
        )
        
        # Record the notification
        if notification_type == NotificationType.TASK_COMPLETED:
            target_channels = channels or list(workflow_manager.notification_system.handlers.keys())
            for channel in target_channels:
                notifications_by_channel[channel].append({
                    'task_id': task_id,
                    'title': title,
                    'message': message,
                    'metadata': metadata,
                    'timestamp': datetime.now()
                })
        
        return result
    
    workflow_manager.notification_system.send_notification = capture_notifications
    
    # Mock task processing to complete quickly
    original_process_single_task = workflow_manager._process_single_task
    
    async def mock_quick_completion(task_id):
        """Mock task processing that completes quickly."""
        try:
            await workflow_manager._update_task_status(task_id, TaskStatus.PROCESSING, progress=0.1)
            await asyncio.sleep(0.1)
            await workflow_manager._update_task_status(task_id, TaskStatus.GENERATING, progress=0.5)
            await asyncio.sleep(0.1)
            
            # Complete the task
            result_url = f"/results/{task_id}.mp4"
            await workflow_manager._update_task_status(
                task_id, TaskStatus.COMPLETED, progress=1.0, result_url=result_url
            )
            
        except Exception as e:
            await workflow_manager._update_task_status(
                task_id, TaskStatus.FAILED, error_message=str(e)
            )
    
    workflow_manager._process_single_task = mock_quick_completion
    
    try:
        await workflow_manager.start()
        
        # Create tasks that will complete
        configs = [generate_valid_video_config(seed=i) for i in range(6)]
        valid_configs = [config for config in configs if config.validate()]
        
        if len(valid_configs) < 3:
            print("Not enough valid configs, skipping test...")
            return
        
        task_ids = []
        for config in valid_configs[:4]:  # Create 4 tasks
            task_id = await workflow_manager.create_video_task(config)
            task_ids.append(task_id)
        
        # Wait for tasks to complete
        await asyncio.sleep(1.5)
        
        # Verify completion notifications were sent
        total_notifications = sum(len(notifications) for notifications in notifications_by_channel.values())
        assert total_notifications > 0, "No completion notifications were captured"
        
        # Verify notifications for completed tasks
        completed_task_ids = set()
        for channel, notifications in notifications_by_channel.items():
            for notification in notifications:
                task_id = notification['task_id']
                completed_task_ids.add(task_id)
                
                # Verify notification content
                assert task_id in task_ids, f"Notification for unknown task: {task_id}"
                
                assert "completed" in notification['title'].lower() or "completed" in notification['message'].lower(), \
                    f"Completion notification doesn't mention completion: {notification['title']}"
                
                # Verify timestamp is recent
                time_diff = datetime.now() - notification['timestamp']
                assert time_diff.total_seconds() < 10, \
                    f"Completion notification timestamp too old: {time_diff.total_seconds()}s"
                
                # Verify metadata contains result URL if available
                if notification['metadata'] and 'result_url' in notification['metadata']:
                    result_url = notification['metadata']['result_url']
                    assert result_url.endswith('.mp4'), f"Invalid result URL format: {result_url}"
        
        # Verify that completed tasks actually have completed status
        for task_id in completed_task_ids:
            task_info = await workflow_manager.get_task_status(task_id)
            if task_info:
                assert task_info.status == TaskStatus.COMPLETED, \
                    f"Task {task_id} notified as completed but has status {task_info.status}"
                
                assert task_info.progress == 1.0, \
                    f"Completed task {task_id} has progress {task_info.progress}, expected 1.0"
        
        print(f"✓ Verified multi-channel completion notifications for {len(completed_task_ids)} tasks")
        
    finally:
        await workflow_manager.stop()


async def test_task_status_consistency_under_load():
    """
    **Feature: video-studio-redesign, Property 8: 任务状态管理一致性**
    **Validates: Requirements 5.1, 5.2, 5.4, 5.5**
    
    Property: Under high load with many concurrent tasks, status management
    should remain consistent and accurate.
    """
    print("Testing task status consistency under load...")
    
    workflow_manager = WorkflowManager(max_concurrent_tasks=10)
    
    # Track all status changes
    status_changes = []
    original_update_status = workflow_manager._update_task_status
    
    async def track_status_changes(task_id, status, progress=None, error_message=None, result_url=None):
        """Track all status changes for consistency verification."""
        status_changes.append({
            'task_id': task_id,
            'status': status,
            'progress': progress,
            'timestamp': datetime.now()
        })
        await original_update_status(task_id, status, progress, error_message, result_url)
    
    workflow_manager._update_task_status = track_status_changes
    
    try:
        await workflow_manager.start()
        
        # Create many tasks rapidly
        num_tasks = 20
        configs = [generate_valid_video_config(seed=i) for i in range(num_tasks)]
        valid_configs = [config for config in configs if config.validate()]
        
        if len(valid_configs) < 10:
            print("Not enough valid configs, skipping test...")
            return
        
        # Create tasks concurrently
        create_tasks = []
        for config in valid_configs[:15]:  # Create 15 tasks
            task = asyncio.create_task(workflow_manager.create_video_task(config))
            create_tasks.append(task)
        
        task_ids = await asyncio.gather(*create_tasks)
        
        # Wait for processing
        await asyncio.sleep(3.0)
        
        # Verify status consistency
        task_status_sequences = {}
        for change in status_changes:
            task_id = change['task_id']
            if task_id not in task_status_sequences:
                task_status_sequences[task_id] = []
            task_status_sequences[task_id].append(change)
        
        # Verify each task follows valid status transitions
        valid_transitions = {
            TaskStatus.PENDING: [TaskStatus.PROCESSING, TaskStatus.CANCELLED],
            TaskStatus.PROCESSING: [TaskStatus.GENERATING, TaskStatus.FAILED, TaskStatus.CANCELLED],
            TaskStatus.GENERATING: [TaskStatus.RENDERING, TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED],
            TaskStatus.RENDERING: [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED],
            TaskStatus.COMPLETED: [],  # Terminal state
            TaskStatus.FAILED: [],     # Terminal state
            TaskStatus.CANCELLED: []   # Terminal state
        }
        
        for task_id, sequence in task_status_sequences.items():
            if len(sequence) < 2:
                continue  # Need at least 2 status changes to verify transitions
            
            # Sort by timestamp
            sequence.sort(key=lambda x: x['timestamp'])
            
            # Verify valid status transitions
            for i in range(1, len(sequence)):
                prev_status = sequence[i-1]['status']
                curr_status = sequence[i]['status']
                
                assert curr_status in valid_transitions.get(prev_status, [curr_status]), \
                    f"Invalid status transition for task {task_id}: {prev_status} -> {curr_status}"
            
            # Verify progress consistency
            for i in range(1, len(sequence)):
                prev_progress = sequence[i-1]['progress']
                curr_progress = sequence[i]['progress']
                
                if prev_progress is not None and curr_progress is not None:
                    # Progress should not decrease (unless task is reset/retried)
                    prev_status = sequence[i-1]['status']
                    curr_status = sequence[i]['status']
                    
                    if curr_status != TaskStatus.PENDING:  # Allow reset to pending
                        assert curr_progress >= prev_progress, \
                            f"Progress decreased for task {task_id}: {prev_progress} -> {curr_progress}"
        
        # Verify final task states are consistent
        for task_id in task_ids:
            task_info = await workflow_manager.get_task_status(task_id)
            if task_info:
                # Verify task info is internally consistent
                assert task_info.validate(), f"Task info validation failed for {task_id}"
                
                # Verify status matches last recorded change
                if task_id in task_status_sequences:
                    last_change = task_status_sequences[task_id][-1]
                    assert task_info.status == last_change['status'], \
                        f"Status mismatch for task {task_id}: info={task_info.status}, last_change={last_change['status']}"
        
        print(f"✓ Verified status consistency under load for {len(task_ids)} tasks")
        
    finally:
        await workflow_manager.stop()


def run_all_task_status_management_tests():
    """Run all property-based tests for task status management consistency"""
    print("Running Property-Based Tests for Video Studio Task Status Management")
    print("=" * 75)
    
    async def run_async_tests():
        try:
            # Test 1: Real-time progress updates
            await test_real_time_progress_updates_property()
            print()
            
            # Test 2: Immediate error notifications
            await test_immediate_error_notifications_property()
            print()
            
            # Test 3: Detailed task status information
            await test_detailed_task_status_information_property()
            print()
            
            # Test 4: Multi-channel completion notifications
            await test_multi_channel_completion_notifications_property()
            print()
            
            # Test 5: Status consistency under load
            await test_task_status_consistency_under_load()
            print()
            
            print("=" * 75)
            print("✅ All property tests PASSED!")
            print("Property 8: 任务状态管理一致性 - VALIDATED")
            print("Requirements 5.1, 5.2, 5.4, 5.5 - SATISFIED")
            return True
            
        except AssertionError as e:
            print(f"\n❌ Test FAILED: {e}")
            return False
        except Exception as e:
            print(f"\n💥 Test ERROR: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    return asyncio.run(run_async_tests())


if __name__ == "__main__":
    success = run_all_task_status_management_tests()
    exit(0 if success else 1)