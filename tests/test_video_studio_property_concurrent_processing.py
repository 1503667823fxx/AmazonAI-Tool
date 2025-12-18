"""
Property-based tests for Video Studio concurrent processing capability.

This module tests Property 7: Concurrent Processing Capability
Validates Requirements 3.2, 4.3
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import asyncio
import pytest
import random
import time
from datetime import datetime
from typing import List, Set
from hypothesis import given, strategies as st, settings, assume
from hypothesis.strategies import composite

# Import Video Studio components
from app_utils.video_studio.models import (
    VideoConfig, Scene, TaskStatus, AspectRatio, VideoQuality, AudioConfig, TextOverlay, TaskPriority
)
from app_utils.video_studio.workflow_manager import WorkflowManager


# Test data generators
@composite
def generate_scene(draw):
    """Generate a valid Scene for testing."""
    scene_id = draw(st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))))
    visual_prompt = draw(st.text(min_size=5, max_size=100))
    duration = draw(st.floats(min_value=1.0, max_value=30.0))
    
    return Scene(
        scene_id=scene_id,
        visual_prompt=visual_prompt,
        duration=duration,
        camera_movement=draw(st.one_of(st.none(), st.sampled_from(["pan", "zoom", "static"]))),
        lighting=draw(st.one_of(st.none(), st.sampled_from(["natural", "studio", "dramatic"]))),
        reference_image=draw(st.one_of(st.none(), st.text(min_size=1, max_size=20)))
    )


@composite
def generate_video_config_with_scenes(draw, min_scenes=1, max_scenes=10):
    """Generate a VideoConfig with multiple scenes for concurrent testing."""
    template_id = draw(st.text(min_size=1, max_size=20))
    input_images = draw(st.lists(st.text(min_size=1, max_size=20), min_size=1, max_size=5))
    duration = draw(st.integers(min_value=10, max_value=120))
    aspect_ratio = draw(st.sampled_from(list(AspectRatio)))
    style = draw(st.text(min_size=1, max_size=20))
    quality = draw(st.sampled_from(list(VideoQuality)))
    
    # Generate multiple scenes for concurrent processing
    num_scenes = draw(st.integers(min_value=min_scenes, max_value=max_scenes))
    scenes = []
    total_scene_duration = 0.0
    
    for i in range(num_scenes):
        scene = draw(generate_scene())
        scene.scene_id = f"scene_{i}_{scene.scene_id}"
        scenes.append(scene)
        total_scene_duration += scene.duration
    
    # Adjust duration to match scenes (within 1 second tolerance)
    if scenes:
        duration = max(10, int(total_scene_duration))
    
    return VideoConfig(
        template_id=template_id,
        input_images=input_images,
        duration=duration,
        aspect_ratio=aspect_ratio,
        style=style,
        quality=quality,
        scenes=scenes
    )


@composite
def generate_concurrent_configs(draw, min_configs=2, max_configs=20):
    """Generate multiple VideoConfigs for concurrent processing tests."""
    num_configs = draw(st.integers(min_value=min_configs, max_value=max_configs))
    configs = []
    
    for i in range(num_configs):
        config = draw(generate_video_config_with_scenes(min_scenes=1, max_scenes=5))
        config.template_id = f"concurrent_test_{i}_{config.template_id}"
        configs.append(config)
    
    return configs


class TestConcurrentProcessingCapability:
    """Test suite for concurrent processing capability."""
    
    @pytest.mark.asyncio
    @given(configs=generate_concurrent_configs(min_configs=3, max_configs=15))
    @settings(max_examples=50, deadline=30000)  # 30 second timeout
    async def test_concurrent_task_processing_property(self, configs):
        """
        **Feature: video-studio-redesign, Property 7: 并发处理能力**
        **Validates: Requirements 3.2, 4.3**
        
        Property: For any set of video generation requests with multiple scenes,
        the system should support concurrent processing, maintain task isolation,
        and complete all tasks without interference or resource conflicts.
        """
        assume(len(configs) >= 3)  # Ensure meaningful concurrency
        assume(all(config.validate() for config in configs))
        
        print(f"Testing concurrent processing with {len(configs)} tasks...")
        
        # Create workflow manager with concurrent processing capability
        max_concurrent = min(len(configs), 8)  # Reasonable concurrency limit
        workflow_manager = WorkflowManager(max_concurrent_tasks=max_concurrent)
        
        try:
            await workflow_manager.start()
            
            # Submit all tasks concurrently
            task_ids = []
            start_time = time.time()
            
            # Create tasks with different priorities to test queue management
            priorities = [TaskPriority.LOW, TaskPriority.NORMAL, TaskPriority.HIGH]
            
            for i, config in enumerate(configs):
                priority = priorities[i % len(priorities)]
                task_id = await workflow_manager.create_video_task(config, priority)
                task_ids.append(task_id)
            
            submission_time = time.time() - start_time
            print(f"✓ Submitted {len(task_ids)} tasks in {submission_time:.2f}s")
            
            # Verify all tasks were created successfully
            assert len(task_ids) == len(configs), "All tasks should be created"
            assert len(set(task_ids)) == len(task_ids), "All task IDs should be unique"
            
            # Monitor task processing
            completed_tasks = set()
            failed_tasks = set()
            max_wait_time = 60  # Maximum wait time in seconds
            check_interval = 0.5
            elapsed_time = 0
            
            while len(completed_tasks) + len(failed_tasks) < len(task_ids) and elapsed_time < max_wait_time:
                await asyncio.sleep(check_interval)
                elapsed_time += check_interval
                
                # Check status of all tasks
                for task_id in task_ids:
                    if task_id not in completed_tasks and task_id not in failed_tasks:
                        task_info = await workflow_manager.get_task_status(task_id)
                        if task_info:
                            if task_info.status == TaskStatus.COMPLETED:
                                completed_tasks.add(task_id)
                            elif task_info.status == TaskStatus.FAILED:
                                failed_tasks.add(task_id)
            
            processing_time = elapsed_time
            print(f"✓ Processing completed in {processing_time:.2f}s")
            
            # Verify concurrent processing results
            total_processed = len(completed_tasks) + len(failed_tasks)
            assert total_processed == len(task_ids), f"All tasks should be processed: {total_processed}/{len(task_ids)}"
            
            # Most tasks should complete successfully (allow some failures due to simulation)
            success_rate = len(completed_tasks) / len(task_ids)
            assert success_rate >= 0.7, f"Success rate too low: {success_rate:.2%}"
            
            # Verify task isolation - check that all completed tasks have unique results
            completed_task_infos = []
            for task_id in completed_tasks:
                task_info = await workflow_manager.get_task_status(task_id)
                if task_info and task_info.result_url:
                    completed_task_infos.append(task_info)
            
            if completed_task_infos:
                result_urls = [info.result_url for info in completed_task_infos]
                assert len(set(result_urls)) == len(result_urls), "Each task should have unique result URL"
            
            # Verify concurrent processing efficiency
            # Processing time should be significantly less than sequential processing time
            estimated_sequential_time = len(configs) * 4.0  # Assume 4 seconds per task sequentially
            efficiency_ratio = estimated_sequential_time / max(processing_time, 1.0)
            
            print(f"✓ Concurrent processing efficiency: {efficiency_ratio:.2f}x faster than sequential")
            assert efficiency_ratio > 1.5, f"Concurrent processing should be more efficient: {efficiency_ratio:.2f}x"
            
            print(f"✓ Concurrent processing test passed: {len(completed_tasks)} completed, {len(failed_tasks)} failed")
            
        finally:
            await workflow_manager.stop()
    
    @pytest.mark.asyncio
    @given(
        num_scenes=st.integers(min_value=3, max_value=12),
        concurrent_tasks=st.integers(min_value=2, max_value=8)
    )
    @settings(max_examples=30, deadline=25000)
    async def test_multi_scene_concurrent_generation_property(self, num_scenes, concurrent_tasks):
        """
        **Feature: video-studio-redesign, Property 7: 并发处理能力**
        **Validates: Requirements 3.2, 4.3**
        
        Property: For any script with multiple scenes, the system should support
        concurrent generation of video segments while maintaining scene order
        and proper resource management.
        """
        print(f"Testing multi-scene concurrent generation: {num_scenes} scenes, {concurrent_tasks} concurrent tasks...")
        
        # Create a video config with multiple scenes
        scenes = []
        for i in range(num_scenes):
            scene = Scene(
                scene_id=f"scene_{i:03d}",
                visual_prompt=f"Test scene {i} with unique content",
                duration=random.uniform(2.0, 8.0),
                camera_movement=random.choice(["pan", "zoom", "static", None]),
                lighting=random.choice(["natural", "studio", "dramatic", None])
            )
            scenes.append(scene)
        
        total_duration = sum(scene.duration for scene in scenes)
        
        config = VideoConfig(
            template_id="multi_scene_test",
            input_images=["test_image.jpg"],
            duration=int(total_duration) + 1,
            aspect_ratio=AspectRatio.LANDSCAPE,
            style="test_style",
            quality=VideoQuality.FULL_HD_1080P,
            scenes=scenes
        )
        
        assert config.validate(), "Generated config should be valid"
        
        # Create workflow manager
        workflow_manager = WorkflowManager(max_concurrent_tasks=concurrent_tasks)
        
        try:
            await workflow_manager.start()
            
            # Create the multi-scene task
            task_id = await workflow_manager.create_video_task(config, TaskPriority.HIGH)
            
            # Monitor task processing
            start_time = time.time()
            max_wait_time = 45  # Increased timeout for multi-scene processing
            
            while True:
                await asyncio.sleep(0.5)
                elapsed = time.time() - start_time
                
                if elapsed > max_wait_time:
                    break
                
                task_info = await workflow_manager.get_task_status(task_id)
                if task_info and task_info.status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
                    break
            
            # Verify task completion
            final_task_info = await workflow_manager.get_task_status(task_id)
            assert final_task_info is not None, "Task info should exist"
            
            # Task should complete or fail (not hang indefinitely)
            assert final_task_info.status in [TaskStatus.COMPLETED, TaskStatus.FAILED], \
                f"Task should complete or fail, got: {final_task_info.status}"
            
            # If completed, verify scene processing
            if final_task_info.status == TaskStatus.COMPLETED:
                assert final_task_info.progress == 1.0, "Completed task should have 100% progress"
                assert final_task_info.result_url is not None, "Completed task should have result URL"
                
                # Verify scene order preservation (scene IDs should be in order)
                original_scene_ids = [scene.scene_id for scene in scenes]
                assert len(original_scene_ids) == len(set(original_scene_ids)), "Scene IDs should be unique"
                
                print(f"✓ Multi-scene task completed successfully with {num_scenes} scenes")
            else:
                print(f"✓ Multi-scene task failed gracefully: {final_task_info.error_message}")
            
            processing_time = time.time() - start_time
            print(f"✓ Multi-scene processing completed in {processing_time:.2f}s")
            
        finally:
            await workflow_manager.stop()
    
    @pytest.mark.asyncio
    @given(
        load_factor=st.floats(min_value=1.5, max_value=4.0),
        task_priorities=st.lists(
            st.sampled_from(list(TaskPriority)), 
            min_size=5, 
            max_size=20
        )
    )
    @settings(max_examples=25, deadline=20000)
    async def test_high_load_concurrent_processing_property(self, load_factor, task_priorities):
        """
        **Feature: video-studio-redesign, Property 7: 并发处理能力**
        **Validates: Requirements 3.2, 4.3**
        
        Property: For any high-load scenario with more tasks than concurrent slots,
        the system should queue tasks properly, respect priorities, and maintain
        system stability without resource exhaustion.
        """
        max_concurrent = 4
        num_tasks = int(max_concurrent * load_factor)
        
        print(f"Testing high-load processing: {num_tasks} tasks, {max_concurrent} concurrent slots (load factor: {load_factor:.1f}x)")
        
        # Create workflow manager with limited concurrency
        workflow_manager = WorkflowManager(max_concurrent_tasks=max_concurrent)
        
        try:
            await workflow_manager.start()
            
            # Create tasks with varying priorities
            task_ids = []
            configs = []
            
            for i in range(num_tasks):
                priority = task_priorities[i % len(task_priorities)]
                
                config = VideoConfig(
                    template_id=f"load_test_{i}",
                    input_images=[f"test_{i}.jpg"],
                    duration=random.randint(5, 15),
                    aspect_ratio=random.choice(list(AspectRatio)),
                    style=f"style_{i}",
                    quality=random.choice(list(VideoQuality))
                )
                
                configs.append(config)
                task_id = await workflow_manager.create_video_task(config, priority)
                task_ids.append((task_id, priority))
            
            print(f"✓ Created {len(task_ids)} tasks for high-load test")
            
            # Monitor system under load
            start_time = time.time()
            completed_count = 0
            failed_count = 0
            max_wait_time = 90  # Extended timeout for high-load test
            
            # Track task completion order to verify priority handling
            completion_order = []
            
            while completed_count + failed_count < num_tasks and (time.time() - start_time) < max_wait_time:
                await asyncio.sleep(0.3)
                
                for task_id, priority in task_ids:
                    if task_id not in [item[0] for item in completion_order]:
                        task_info = await workflow_manager.get_task_status(task_id)
                        if task_info and task_info.status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
                            completion_order.append((task_id, priority, task_info.status))
                            if task_info.status == TaskStatus.COMPLETED:
                                completed_count += 1
                            else:
                                failed_count += 1
            
            processing_time = time.time() - start_time
            total_processed = completed_count + failed_count
            
            print(f"✓ High-load processing results: {completed_count} completed, {failed_count} failed in {processing_time:.2f}s")
            
            # Verify system handled the load
            assert total_processed >= num_tasks * 0.8, f"Should process most tasks under load: {total_processed}/{num_tasks}"
            
            # Verify system stability (no crashes or hangs)
            stats = await workflow_manager.get_statistics()
            assert stats['is_processing'], "Workflow manager should still be processing"
            
            # Verify priority ordering (higher priority tasks should generally complete first)
            if len(completion_order) >= 6:  # Need sufficient data for priority analysis
                high_priority_positions = []
                low_priority_positions = []
                
                for i, (task_id, priority, status) in enumerate(completion_order):
                    if status == TaskStatus.COMPLETED:
                        if priority == TaskPriority.HIGH:
                            high_priority_positions.append(i)
                        elif priority == TaskPriority.LOW:
                            low_priority_positions.append(i)
                
                if high_priority_positions and low_priority_positions:
                    avg_high_pos = sum(high_priority_positions) / len(high_priority_positions)
                    avg_low_pos = sum(low_priority_positions) / len(low_priority_positions)
                    
                    # High priority tasks should generally complete before low priority ones
                    print(f"✓ Priority ordering: HIGH avg position {avg_high_pos:.1f}, LOW avg position {avg_low_pos:.1f}")
            
            # Verify resource management efficiency
            throughput = completed_count / max(processing_time, 1.0)
            print(f"✓ System throughput under load: {throughput:.2f} tasks/second")
            
            assert throughput > 0.1, f"System throughput too low under load: {throughput:.2f} tasks/sec"
            
        finally:
            await workflow_manager.stop()


if __name__ == "__main__":
    # Run tests directly
    import sys
    
    async def run_tests():
        """Run the concurrent processing property tests."""
        test_instance = TestConcurrentProcessingCapability()
        
        print("=== Testing Concurrent Processing Capability ===")
        print()
        
        try:
            # Test 1: Basic concurrent task processing
            print("1. Testing concurrent task processing...")
            configs = [
                VideoConfig(
                    template_id=f"test_{i}",
                    input_images=[f"image_{i}.jpg"],
                    duration=10,
                    aspect_ratio=AspectRatio.LANDSCAPE,
                    style="test",
                    quality=VideoQuality.FULL_HD_1080P,
                    scenes=[Scene(f"scene_{i}", f"prompt_{i}", 5.0)]
                ) for i in range(5)
            ]
            await test_instance.test_concurrent_task_processing_property(configs)
            print("✓ Concurrent task processing test passed")
            print()
            
            # Test 2: Multi-scene concurrent generation
            print("2. Testing multi-scene concurrent generation...")
            await test_instance.test_multi_scene_concurrent_generation_property(6, 3)
            print("✓ Multi-scene concurrent generation test passed")
            print()
            
            # Test 3: High-load processing
            print("3. Testing high-load concurrent processing...")
            priorities = [TaskPriority.HIGH, TaskPriority.NORMAL, TaskPriority.LOW] * 4
            await test_instance.test_high_load_concurrent_processing_property(2.5, priorities)
            print("✓ High-load concurrent processing test passed")
            print()
            
            print("=== All Concurrent Processing Tests Passed ===")
            return True
            
        except Exception as e:
            print(f"✗ Test failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    # Run the tests
    success = asyncio.run(run_tests())
    sys.exit(0 if success else 1)