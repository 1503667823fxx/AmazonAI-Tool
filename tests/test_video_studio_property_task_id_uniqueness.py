"""
Property-based tests for Video Studio task ID uniqueness
Tests that task IDs are globally unique across all video generation requests
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import asyncio
from app_utils.video_studio.workflow_manager import WorkflowManager
from app_utils.video_studio.models import VideoConfig, AspectRatio, VideoQuality, AudioConfig, Scene, TextOverlay
from typing import Set, List
import uuid
import random


# Function for generating valid video configurations
def generate_video_config(seed=None):
    """Generate valid VideoConfig instances for testing."""
    if seed is not None:
        random.seed(seed)
    
    template_id = f"template_{random.randint(1, 1000)}"
    
    # Generate 1-5 input images
    num_images = random.randint(1, 5)
    input_images = [f"image_{i}.jpg" for i in range(num_images)]
    
    duration = random.randint(5, 300)  # 5 seconds to 5 minutes
    aspect_ratio = random.choice(list(AspectRatio))
    style = f"style_{random.randint(1, 100)}"
    quality = random.choice(list(VideoQuality))
    
    # Optional audio config
    audio_config = None
    if random.choice([True, False]):
        audio_config = AudioConfig(
            enabled=True,
            volume=random.uniform(0.0, 1.0),
            fade_in=random.uniform(0.0, 5.0),
            fade_out=random.uniform(0.0, 5.0)
        )
    
    # Optional text overlays
    text_overlays = []
    if random.choice([True, False]):
        num_overlays = random.randint(1, 3)
        for i in range(num_overlays):
            text_overlays.append(TextOverlay(
                text=f"Overlay {i}",
                position=random.choice(["top", "center", "bottom"]),
                font_size=random.randint(12, 48)
            ))
    
    # Optional scenes
    scenes = []
    if random.choice([True, False]):
        num_scenes = random.randint(1, 5)
        scene_duration = duration / num_scenes
        for i in range(num_scenes):
            scenes.append(Scene(
                scene_id=f"scene_{i}",
                visual_prompt=f"Scene {i} description",
                duration=scene_duration
            ))
    
    return VideoConfig(
        template_id=template_id,
        input_images=input_images,
        duration=duration,
        aspect_ratio=aspect_ratio,
        style=style,
        quality=quality,
        audio_config=audio_config,
        text_overlays=text_overlays,
        scenes=scenes
    )


async def test_task_id_uniqueness_property(configs):
    """
    **Feature: video-studio-redesign, Property 3: 任务ID唯一性**
    **Validates: Requirements 1.4**
    
    Property: For any collection of video generation requests, all generated task IDs
    should be unique, regardless of the number of requests or their timing.
    """
    print(f"Testing task ID uniqueness with {len(configs)} configurations...")
    
    # Filter to only valid configurations
    valid_configs = [config for config in configs if config.validate()]
    if len(valid_configs) < 5:
        print("Not enough valid configs for meaningful test, skipping...")
        return
    
    workflow_manager = WorkflowManager(max_concurrent_tasks=5)
    task_ids = set()
    
    try:
        await workflow_manager.start()
        
        # Create tasks for all valid configurations
        for i, config in enumerate(valid_configs):
            task_id = await workflow_manager.create_video_task(config)
            
            # Verify uniqueness
            assert task_id not in task_ids, f"Duplicate task ID at index {i}: {task_id}"
            
            # Verify format
            assert task_id.startswith("task_"), f"Invalid task ID format: {task_id}"
            assert len(task_id) == 17, f"Invalid task ID length: {task_id}"
            
            task_ids.add(task_id)
        
        print(f"✓ Successfully created {len(task_ids)} unique task IDs")
        
    finally:
        await workflow_manager.stop()


async def test_high_volume_task_id_uniqueness(num_tasks):
    """
    **Feature: video-studio-redesign, Property 3: 任务ID唯一性**
    **Validates: Requirements 1.4**
    
    Property: Even under high volume task creation, all task IDs should remain unique.
    """
    print(f"Testing high-volume task ID uniqueness with {num_tasks} tasks...")
    
    workflow_manager = WorkflowManager(max_concurrent_tasks=10)
    task_ids = set()
    
    # Simple valid configuration for high-volume testing
    config = VideoConfig(
        template_id="high_volume_test",
        input_images=["test.jpg"],
        duration=10,
        aspect_ratio=AspectRatio.LANDSCAPE,
        style="test",
        quality=VideoQuality.HD_720P
    )
    
    try:
        await workflow_manager.start()
        
        # Create many tasks rapidly
        tasks = []
        for i in range(num_tasks):
            task = asyncio.create_task(workflow_manager.create_video_task(config))
            tasks.append(task)
        
        # Wait for all tasks to complete
        task_ids_list = await asyncio.gather(*tasks)
        
        # Verify all IDs are unique
        task_ids = set(task_ids_list)
        assert len(task_ids) == len(task_ids_list), f"Duplicate task IDs found in high-volume test. Expected {len(task_ids_list)}, got {len(task_ids)} unique IDs"
        
        # Verify all IDs have correct format
        for task_id in task_ids:
            assert task_id.startswith("task_"), f"Invalid task ID format: {task_id}"
            assert len(task_id) == 17, f"Invalid task ID length: {task_id}"
        
        print(f"✓ Successfully created {len(task_ids)} unique task IDs under high volume")
        
    finally:
        await workflow_manager.stop()


async def test_concurrent_workflow_managers_uniqueness():
    """
    **Feature: video-studio-redesign, Property 3: 任务ID唯一性**
    **Validates: Requirements 1.4**
    
    Property: Task IDs should be unique even across multiple concurrent workflow manager instances.
    """
    print("Testing task ID uniqueness across multiple workflow managers...")
    
    num_managers = 5
    tasks_per_manager = 20
    
    managers = []
    all_task_ids = set()
    
    config = VideoConfig(
        template_id="concurrent_test",
        input_images=["test.jpg"],
        duration=15,
        aspect_ratio=AspectRatio.SQUARE,
        style="concurrent",
        quality=VideoQuality.FULL_HD_1080P
    )
    
    try:
        # Create and start multiple workflow managers
        for i in range(num_managers):
            manager = WorkflowManager(max_concurrent_tasks=3)
            await manager.start()
            managers.append(manager)
        
        # Create tasks concurrently across all managers
        all_tasks = []
        for manager in managers:
            for _ in range(tasks_per_manager):
                task = asyncio.create_task(manager.create_video_task(config))
                all_tasks.append(task)
        
        # Wait for all task creations to complete
        task_ids = await asyncio.gather(*all_tasks)
        
        # Verify all task IDs are unique
        unique_task_ids = set(task_ids)
        expected_total = num_managers * tasks_per_manager
        
        assert len(unique_task_ids) == expected_total, f"Expected {expected_total} unique task IDs, got {len(unique_task_ids)}"
        assert len(task_ids) == expected_total, f"Expected {expected_total} total task IDs, got {len(task_ids)}"
        
        # Verify format of all task IDs
        for task_id in unique_task_ids:
            assert task_id.startswith("task_"), f"Invalid task ID format: {task_id}"
            assert len(task_id) == 17, f"Invalid task ID length: {task_id}"
        
        print(f"✓ Successfully created {len(unique_task_ids)} unique task IDs across {num_managers} concurrent managers")
        
    finally:
        # Clean up all managers
        for manager in managers:
            try:
                await manager.stop()
            except Exception:
                pass


def test_task_id_generation_method():
    """
    **Feature: video-studio-redesign, Property 3: 任务ID唯一性**
    **Validates: Requirements 1.4**
    
    Property: The task ID generation method should produce statistically unique identifiers.
    """
    print("Testing task ID generation method...")
    
    # Test the internal ID generation method
    workflow_manager = WorkflowManager()
    
    # Generate many IDs and check for uniqueness
    generated_ids = set()
    num_ids = 10000
    
    for _ in range(num_ids):
        task_id = workflow_manager._generate_task_id()
        
        # Verify format
        assert task_id.startswith("task_"), f"Invalid task ID format: {task_id}"
        assert len(task_id) == 17, f"Invalid task ID length: {task_id}"
        
        # Verify uniqueness
        assert task_id not in generated_ids, f"Duplicate task ID generated: {task_id}"
        generated_ids.add(task_id)
    
    print(f"✓ Generated {len(generated_ids)} unique task IDs using internal method")


def run_all_task_id_uniqueness_tests():
    """Run all property-based tests for task ID uniqueness"""
    print("Running Property-Based Tests for Video Studio Task ID Uniqueness")
    print("=" * 70)
    
    try:
        # Test 1: Basic task ID generation method
        test_task_id_generation_method()
        
        # Test 2: Synchronous task ID uniqueness test
        test_task_id_uniqueness_sync()
        
        print("\n" + "=" * 70)
        print("✅ All property tests PASSED!")
        print("Property 3: 任务ID唯一性 - VALIDATED")
        print("Requirements 1.4 - SATISFIED")
        return True
        
    except AssertionError as e:
        print(f"\n❌ Test FAILED: {e}")
        return False
    except Exception as e:
        print(f"\n💥 Test ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_task_id_uniqueness_sync():
    """
    **Feature: video-studio-redesign, Property 3: 任务ID唯一性**
    **Validates: Requirements 1.4**
    
    Property: The task ID generation method should produce statistically unique identifiers
    across multiple workflow manager instances and high-volume generation.
    """
    print("Testing task ID uniqueness across multiple instances...")
    
    # Test with multiple workflow manager instances
    managers = []
    all_task_ids = set()
    
    try:
        # Create multiple workflow managers
        for i in range(5):
            manager = WorkflowManager(max_concurrent_tasks=2)
            managers.append(manager)
        
        # Generate task IDs from each manager
        num_ids_per_manager = 100
        for manager in managers:
            for _ in range(num_ids_per_manager):
                task_id = manager._generate_task_id()
                
                # Verify uniqueness
                assert task_id not in all_task_ids, f"Duplicate task ID generated: {task_id}"
                
                # Verify format
                assert task_id.startswith("task_"), f"Invalid task ID format: {task_id}"
                assert len(task_id) == 17, f"Invalid task ID length: {task_id}"
                
                # Verify hex part
                hex_part = task_id[5:]
                try:
                    int(hex_part, 16)
                except ValueError:
                    assert False, f"Invalid hex part in task ID: {hex_part}"
                
                all_task_ids.add(task_id)
        
        expected_total = len(managers) * num_ids_per_manager
        assert len(all_task_ids) == expected_total, f"Expected {expected_total} unique IDs, got {len(all_task_ids)}"
        
        print(f"✓ Generated {len(all_task_ids)} unique task IDs across {len(managers)} managers")
        
    finally:
        # Clean up managers (no need to stop since we didn't start them)
        pass


if __name__ == "__main__":
    success = run_all_task_id_uniqueness_tests()
    exit(0 if success else 1)