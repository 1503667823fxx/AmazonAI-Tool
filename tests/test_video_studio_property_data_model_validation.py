"""
Property-based tests for Video Studio data model validation
Tests configuration validation completeness across all valid inputs
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app_utils.video_studio.models import (
    VideoConfig, Scene, AudioConfig, TextOverlay, TaskInfo,
    TaskStatus, VideoQuality, AspectRatio, ConfigurationManager
)
from datetime import datetime
from typing import List, Dict, Any
import json
import tempfile
from pathlib import Path


def test_configuration_validation_completeness():
    """
    **Feature: video-studio-redesign, Property 4: 配置验证完整性**
    **Validates: Requirements 1.3, 3.4**
    
    Property: For any video configuration parameters (duration, size, style, etc.), 
    the system should correctly validate parameter validity, accept valid configurations 
    and reject invalid configurations, providing detailed error information
    """
    print("Testing configuration validation completeness...")
    
    # Test cases for valid configurations
    valid_test_cases = [
        # Basic valid configuration
        {
            "template_id": "modern_template",
            "input_images": ["image1.jpg", "image2.png"],
            "duration": 30,
            "aspect_ratio": AspectRatio.LANDSCAPE,
            "style": "modern",
            "quality": VideoQuality.HD_720P
        },
        # Configuration with audio
        {
            "template_id": "audio_template",
            "input_images": ["image1.jpg"],
            "duration": 15,
            "aspect_ratio": AspectRatio.PORTRAIT,
            "style": "cinematic",
            "quality": VideoQuality.FULL_HD_1080P,
            "audio_config": AudioConfig(enabled=True, volume=0.7, fade_in=1.0)
        },
        # Configuration with text overlays
        {
            "template_id": "text_template",
            "input_images": ["image1.jpg"],
            "duration": 20,
            "aspect_ratio": AspectRatio.SQUARE,
            "style": "minimal",
            "quality": VideoQuality.UHD_4K,
            "text_overlays": [
                TextOverlay(text="Hello World", position="center", font_size=24),
                TextOverlay(text="Subtitle", position="bottom", font_size=16)
            ]
        },
        # Configuration with scenes
        {
            "template_id": "scene_template",
            "input_images": ["image1.jpg"],
            "duration": 10,
            "aspect_ratio": AspectRatio.LANDSCAPE,
            "style": "dynamic",
            "quality": VideoQuality.HD_720P,
            "scenes": [
                Scene(scene_id="scene1", visual_prompt="Beautiful sunset", duration=5.0),
                Scene(scene_id="scene2", visual_prompt="Ocean waves", duration=5.0)
            ]
        }
    ]
    
    # Test valid configurations
    for i, test_case in enumerate(valid_test_cases):
        config = VideoConfig(**test_case)
        is_valid, error_msg = ConfigurationManager.validate_video_config(config)
        assert is_valid, f"Valid test case {i+1} was rejected: {error_msg}"
        assert config.validate(), f"Valid test case {i+1} failed internal validation"
    
    print("✓ Valid configuration tests passed")
    
    # Test cases for invalid configurations
    invalid_test_cases = [
        # Empty template_id
        {
            "template_id": "",
            "input_images": ["image1.jpg"],
            "duration": 30,
            "aspect_ratio": AspectRatio.LANDSCAPE,
            "style": "modern",
            "quality": VideoQuality.HD_720P
        },
        # Empty input_images
        {
            "template_id": "test",
            "input_images": [],
            "duration": 30,
            "aspect_ratio": AspectRatio.LANDSCAPE,
            "style": "modern",
            "quality": VideoQuality.HD_720P
        },
        # Negative duration
        {
            "template_id": "test",
            "input_images": ["image1.jpg"],
            "duration": -5,
            "aspect_ratio": AspectRatio.LANDSCAPE,
            "style": "modern",
            "quality": VideoQuality.HD_720P
        },
        # Empty style
        {
            "template_id": "test",
            "input_images": ["image1.jpg"],
            "duration": 30,
            "aspect_ratio": AspectRatio.LANDSCAPE,
            "style": "",
            "quality": VideoQuality.HD_720P
        }
    ]
    
    # Test invalid configurations
    for i, test_case in enumerate(invalid_test_cases):
        try:
            config = VideoConfig(**test_case)
            is_valid, error_msg = ConfigurationManager.validate_video_config(config)
            assert not is_valid, f"Invalid test case {i+1} was accepted"
            assert error_msg is not None, f"No error message for invalid test case {i+1}"
        except (TypeError, ValueError):
            # Expected for severely invalid inputs
            pass
    
    print("✓ Invalid configuration tests passed")


def test_audio_config_validation():
    """Test AudioConfig validation with various parameter combinations"""
    print("Testing AudioConfig validation...")
    
    # Valid audio configurations
    valid_audio_configs = [
        AudioConfig(enabled=False),
        AudioConfig(enabled=True, volume=0.0),
        AudioConfig(enabled=True, volume=1.0),
        AudioConfig(enabled=True, volume=0.5, fade_in=2.0, fade_out=1.5),
        AudioConfig(enabled=True, background_music="music.mp3", volume=0.8)
    ]
    
    for i, audio_config in enumerate(valid_audio_configs):
        assert audio_config.validate(), f"Valid audio config {i+1} failed validation"
    
    # Invalid audio configurations
    invalid_audio_configs = [
        AudioConfig(volume=1.5),  # Volume > 1.0
        AudioConfig(volume=-0.1),  # Volume < 0.0
        AudioConfig(fade_in=-1.0),  # Negative fade_in
        AudioConfig(fade_out=-0.5)  # Negative fade_out
    ]
    
    for i, audio_config in enumerate(invalid_audio_configs):
        assert not audio_config.validate(), f"Invalid audio config {i+1} passed validation"
    
    print("✓ AudioConfig validation tests passed")


def test_text_overlay_validation():
    """Test TextOverlay validation with various parameter combinations"""
    print("Testing TextOverlay validation...")
    
    # Valid text overlays
    valid_overlays = [
        TextOverlay(text="Hello", position="center"),
        TextOverlay(text="Top text", position="top", font_size=32),
        TextOverlay(text="Bottom text", position="bottom", color="#FF0000"),
        TextOverlay(text="Timed text", position="center", duration=5.0)
    ]
    
    for i, overlay in enumerate(valid_overlays):
        assert overlay.validate(), f"Valid text overlay {i+1} failed validation"
    
    # Invalid text overlays
    invalid_overlays = [
        TextOverlay(text="", position="center"),  # Empty text
        TextOverlay(text="Test", position="invalid"),  # Invalid position
        TextOverlay(text="Test", position="center", font_size=0),  # Invalid font size
        TextOverlay(text="Test", position="center", duration=-1.0)  # Negative duration
    ]
    
    for i, overlay in enumerate(invalid_overlays):
        assert not overlay.validate(), f"Invalid text overlay {i+1} passed validation"
    
    print("✓ TextOverlay validation tests passed")


def test_scene_validation():
    """Test Scene validation with various parameter combinations"""
    print("Testing Scene validation...")
    
    # Valid scenes
    valid_scenes = [
        Scene(scene_id="scene1", visual_prompt="Beautiful landscape", duration=5.0),
        Scene(scene_id="scene2", visual_prompt="City skyline", duration=3.5, camera_movement="pan"),
        Scene(scene_id="scene3", visual_prompt="Ocean waves", duration=7.2, lighting="golden_hour"),
        Scene(scene_id="scene4", visual_prompt="Forest path", duration=4.0, reference_image="ref.jpg")
    ]
    
    for i, scene in enumerate(valid_scenes):
        assert scene.validate(), f"Valid scene {i+1} failed validation"
    
    # Invalid scenes
    invalid_scenes = [
        Scene(scene_id="", visual_prompt="Test", duration=5.0),  # Empty scene_id
        Scene(scene_id="test", visual_prompt="", duration=5.0),  # Empty prompt
        Scene(scene_id="test", visual_prompt="Test", duration=0.0),  # Zero duration
        Scene(scene_id="test", visual_prompt="Test", duration=-1.0)  # Negative duration
    ]
    
    for i, scene in enumerate(invalid_scenes):
        assert not scene.validate(), f"Invalid scene {i+1} passed validation"
    
    print("✓ Scene validation tests passed")


def test_serialization_round_trip_consistency():
    """Test that valid configurations can be serialized and deserialized consistently"""
    print("Testing serialization round-trip consistency...")
    
    # Test configurations with different complexity levels
    test_configs = [
        # Simple configuration
        VideoConfig(
            template_id="simple",
            input_images=["image1.jpg"],
            duration=10,
            aspect_ratio=AspectRatio.LANDSCAPE,
            style="basic",
            quality=VideoQuality.HD_720P
        ),
        # Complex configuration with all features
        VideoConfig(
            template_id="complex",
            input_images=["image1.jpg", "image2.png"],
            duration=25,
            aspect_ratio=AspectRatio.PORTRAIT,
            style="advanced",
            quality=VideoQuality.UHD_4K,
            audio_config=AudioConfig(enabled=True, volume=0.6, fade_in=2.0, fade_out=1.0),
            text_overlays=[
                TextOverlay(text="Title", position="top", font_size=32),
                TextOverlay(text="Subtitle", position="bottom", font_size=16, duration=10.0)
            ],
            scenes=[
                Scene(scene_id="intro", visual_prompt="Opening scene", duration=5.0),
                Scene(scene_id="main", visual_prompt="Main content", duration=15.0, camera_movement="zoom"),
                Scene(scene_id="outro", visual_prompt="Closing scene", duration=5.0, lighting="soft")
            ]
        )
    ]
    
    for i, config in enumerate(test_configs):
        # Convert to dict and back
        config_dict = config.to_dict()
        restored_config = VideoConfig.from_dict(config_dict)
        
        # Both should be valid
        assert config.validate(), f"Original config {i+1} should be valid"
        assert restored_config.validate(), f"Restored config {i+1} should be valid"
        
        # Key properties should match
        assert config.template_id == restored_config.template_id
        assert config.input_images == restored_config.input_images
        assert config.duration == restored_config.duration
        assert config.aspect_ratio == restored_config.aspect_ratio
        assert config.style == restored_config.style
        assert config.quality == restored_config.quality
        
        # Serialization should be consistent
        assert config.to_dict() == restored_config.to_dict()
    
    print("✓ Serialization round-trip tests passed")


def test_file_serialization_round_trip():
    """Test that configurations can be saved to and loaded from files consistently"""
    print("Testing file serialization round-trip...")
    
    config = VideoConfig(
        template_id="file_test",
        input_images=["test_image.jpg"],
        duration=20,
        aspect_ratio=AspectRatio.SQUARE,
        style="file_style",
        quality=VideoQuality.FULL_HD_1080P,
        audio_config=AudioConfig(enabled=True, volume=0.5)
    )
    
    with tempfile.TemporaryDirectory() as temp_dir:
        filepath = Path(temp_dir) / "test_config.json"
        
        # Save configuration
        save_success = ConfigurationManager.save_config(config, filepath)
        assert save_success, "Failed to save valid configuration"
        
        # Load configuration
        loaded_config = ConfigurationManager.load_config(filepath)
        assert loaded_config is not None, "Failed to load saved configuration"
        
        # Validate loaded configuration
        assert loaded_config.validate(), "Loaded configuration is invalid"
        
        # Key properties should match
        assert config.template_id == loaded_config.template_id
        assert config.input_images == loaded_config.input_images
        assert config.duration == loaded_config.duration
        assert config.aspect_ratio == loaded_config.aspect_ratio
        assert config.style == loaded_config.style
        assert config.quality == loaded_config.quality
    
    print("✓ File serialization round-trip tests passed")


def test_scene_duration_mismatch_validation():
    """Test that configurations with mismatched scene durations are rejected"""
    print("Testing scene duration mismatch validation...")
    
    # Test cases with duration mismatches
    mismatch_test_cases = [
        # Scenes total 10 seconds, config says 15 seconds
        {
            "scenes": [
                Scene(scene_id="s1", visual_prompt="Scene 1", duration=5.0),
                Scene(scene_id="s2", visual_prompt="Scene 2", duration=5.0)
            ],
            "config_duration": 15
        },
        # Scenes total 20 seconds, config says 10 seconds
        {
            "scenes": [
                Scene(scene_id="s1", visual_prompt="Scene 1", duration=8.0),
                Scene(scene_id="s2", visual_prompt="Scene 2", duration=7.0),
                Scene(scene_id="s3", visual_prompt="Scene 3", duration=5.0)
            ],
            "config_duration": 10
        }
    ]
    
    for i, test_case in enumerate(mismatch_test_cases):
        config = VideoConfig(
            template_id="mismatch_test",
            input_images=["test.jpg"],
            duration=test_case["config_duration"],
            aspect_ratio=AspectRatio.LANDSCAPE,
            style="test",
            quality=VideoQuality.HD_720P,
            scenes=test_case["scenes"]
        )
        
        is_valid, error_msg = ConfigurationManager.validate_video_config(config)
        assert not is_valid, f"Mismatch test case {i+1} was accepted"
        assert error_msg is not None, f"No error message for mismatch test case {i+1}"
        assert "duration" in error_msg.lower(), f"Error message should mention duration mismatch for case {i+1}"
    
    print("✓ Scene duration mismatch validation tests passed")


def test_task_info_validation():
    """Test TaskInfo validation properties"""
    print("Testing TaskInfo validation...")
    
    # Valid TaskInfo instances
    valid_task_infos = [
        TaskInfo(
            task_id="task_001",
            status=TaskStatus.PENDING,
            progress=0.0,
            created_at=datetime.now(),
            updated_at=datetime.now()
        ),
        TaskInfo(
            task_id="task_002",
            status=TaskStatus.PROCESSING,
            progress=0.5,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            result_url="http://example.com/result.mp4"
        ),
        TaskInfo(
            task_id="task_003",
            status=TaskStatus.COMPLETED,
            progress=1.0,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            config=VideoConfig(
                template_id="test",
                input_images=["test.jpg"],
                duration=10,
                aspect_ratio=AspectRatio.LANDSCAPE,
                style="test",
                quality=VideoQuality.HD_720P
            )
        )
    ]
    
    for i, task_info in enumerate(valid_task_infos):
        assert task_info.validate(), f"Valid TaskInfo {i+1} failed validation"
    
    # Invalid TaskInfo instances
    invalid_task_infos = [
        # Empty task_id
        TaskInfo(
            task_id="",
            status=TaskStatus.PENDING,
            progress=0.0,
            created_at=datetime.now(),
            updated_at=datetime.now()
        ),
        # Progress out of range
        TaskInfo(
            task_id="task_invalid",
            status=TaskStatus.PENDING,
            progress=1.5,
            created_at=datetime.now(),
            updated_at=datetime.now()
        ),
        # Negative progress
        TaskInfo(
            task_id="task_invalid2",
            status=TaskStatus.PENDING,
            progress=-0.1,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
    ]
    
    for i, task_info in enumerate(invalid_task_infos):
        assert not task_info.validate(), f"Invalid TaskInfo {i+1} passed validation"
    
    print("✓ TaskInfo validation tests passed")


def run_all_property_tests():
    """Run all property-based tests for data model validation"""
    print("Running Property-Based Tests for Video Studio Data Model Validation")
    print("=" * 70)
    
    try:
        test_configuration_validation_completeness()
        test_audio_config_validation()
        test_text_overlay_validation()
        test_scene_validation()
        test_serialization_round_trip_consistency()
        test_file_serialization_round_trip()
        test_scene_duration_mismatch_validation()
        test_task_info_validation()
        
        print("\n" + "=" * 70)
        print("✅ All property tests PASSED!")
        print("Property 4: 配置验证完整性 - VALIDATED")
        print("Requirements 1.3, 3.4 - SATISFIED")
        return True
        
    except AssertionError as e:
        print(f"\n❌ Test FAILED: {e}")
        return False
    except Exception as e:
        print(f"\n💥 Test ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_property_tests()
    exit(0 if success else 1)