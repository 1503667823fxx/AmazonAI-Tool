"""
Property-based tests for Video Studio configuration hot reload
Tests configuration hot reload functionality without system restart
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app_utils.video_studio.config import (
    ConfigurationManager, VideoStudioConfig, ModelConfig, 
    StorageConfig, WorkflowConfig, RenderingConfig
)
import json
import tempfile
import time
from pathlib import Path
from typing import Dict, Any
import random
import string


def generate_random_string(min_length: int = 1, max_length: int = 50) -> str:
    """Generate a random string for testing."""
    length = random.randint(min_length, max_length)
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))


def generate_random_model_config() -> ModelConfig:
    """Generate a random valid ModelConfig for testing."""
    return ModelConfig(
        name=generate_random_string(3, 20),
        api_key=generate_random_string(10, 50),
        base_url=f"https://api.{generate_random_string(5, 15)}.com/v1",
        timeout=random.randint(30, 600),
        max_retries=random.randint(1, 10),
        rate_limit=random.randint(10, 1000) if random.choice([True, False]) else None,
        enabled=random.choice([True, False]),
        parameters={
            "temperature": random.uniform(0.1, 2.0),
            "max_tokens": random.randint(100, 4000)
        }
    )


def generate_random_storage_config() -> StorageConfig:
    """Generate a random valid StorageConfig for testing."""
    return StorageConfig(
        base_path=f"./test_assets_{generate_random_string(5, 10)}",
        temp_path=f"./test_temp_{generate_random_string(5, 10)}",
        max_file_size_mb=random.randint(10, 500),
        allowed_image_formats=random.sample(["jpg", "jpeg", "png", "webp", "gif"], k=random.randint(2, 4)),
        allowed_video_formats=random.sample(["mp4", "mov", "avi", "mkv"], k=random.randint(2, 3)),
        cleanup_interval_hours=random.randint(1, 72),
        max_storage_gb=random.randint(1, 100)
    )


def generate_random_workflow_config() -> WorkflowConfig:
    """Generate a random valid WorkflowConfig for testing."""
    return WorkflowConfig(
        max_concurrent_tasks=random.randint(1, 20),
        task_timeout_minutes=random.randint(5, 120),
        checkpoint_interval_seconds=random.randint(10, 300),
        auto_cleanup_completed_tasks=random.choice([True, False]),
        completed_task_retention_hours=random.randint(1, 168),
        enable_progress_notifications=random.choice([True, False])
    )


def generate_random_rendering_config() -> RenderingConfig:
    """Generate a random valid RenderingConfig for testing."""
    return RenderingConfig(
        default_quality=random.choice(["720p", "1080p", "4k"]),
        default_aspect_ratio=random.choice(["16:9", "9:16", "1:1"]),
        max_duration_seconds=random.randint(30, 600),
        default_fps=random.choice([24, 30, 60]),
        enable_hardware_acceleration=random.choice([True, False]),
        output_formats=random.sample(["mp4", "mov", "avi"], k=random.randint(1, 3)),
        compression_quality=random.choice(["low", "medium", "high"])
    )


def generate_random_video_studio_config() -> VideoStudioConfig:
    """Generate a random valid VideoStudioConfig for testing."""
    # Generate 1-5 random models
    models = {}
    for i in range(random.randint(1, 5)):
        model_name = f"model_{generate_random_string(3, 10)}"
        models[model_name] = generate_random_model_config()
    
    return VideoStudioConfig(
        models=models,
        storage=generate_random_storage_config(),
        workflow=generate_random_workflow_config(),
        rendering=generate_random_rendering_config(),
        debug_mode=random.choice([True, False]),
        log_level=random.choice(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
    )


def test_configuration_hot_reload():
    """
    **Feature: video-studio-redesign, Property 13: 配置热重载**
    **Validates: Requirements 4.5**
    
    Property: For any system configuration update, the system should support 
    hot reload without requiring restart, maintaining service continuity
    """
    print("Testing configuration hot reload...")
    
    # Run test with multiple random configurations
    for i in range(100):
        print(f"  Test iteration {i+1}/100")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "test_config.json"
            
            # Generate initial configuration
            initial_config = generate_random_video_studio_config()
            
            # Create configuration manager with test config file
            config_manager = ConfigurationManager(str(config_path))
            
            # Save initial configuration
            with open(config_path, 'w') as f:
                json.dump(initial_config.to_dict(), f, indent=2)
            
            # Load initial configuration
            loaded_config = config_manager.load_config()
            
            # Verify initial configuration is loaded correctly
            assert loaded_config.debug_mode == initial_config.debug_mode
            assert loaded_config.log_level == initial_config.log_level
            assert len(loaded_config.models) == len(initial_config.models)
            
            # Store initial state for comparison
            initial_model_count = len(loaded_config.models)
            initial_debug_mode = loaded_config.debug_mode
            initial_log_level = loaded_config.log_level
            initial_max_concurrent = loaded_config.workflow.max_concurrent_tasks
            
            # Generate modified configuration
            modified_config = generate_random_video_studio_config()
            
            # Ensure the modified config is actually different
            while (modified_config.debug_mode == initial_config.debug_mode and 
                   modified_config.log_level == initial_config.log_level and
                   len(modified_config.models) == len(initial_config.models)):
                modified_config = generate_random_video_studio_config()
            
            # Save modified configuration to file (simulating external config change)
            with open(config_path, 'w') as f:
                json.dump(modified_config.to_dict(), f, indent=2)
            
            # Perform hot reload
            reloaded_config = config_manager.reload_config()
            
            # Verify configuration was reloaded without restart
            assert reloaded_config.debug_mode == modified_config.debug_mode
            assert reloaded_config.log_level == modified_config.log_level
            assert len(reloaded_config.models) == len(modified_config.models)
            
            # Verify the configuration actually changed
            config_changed = (
                reloaded_config.debug_mode != initial_debug_mode or
                reloaded_config.log_level != initial_log_level or
                len(reloaded_config.models) != initial_model_count or
                reloaded_config.workflow.max_concurrent_tasks != initial_max_concurrent
            )
            assert config_changed, "Configuration should have changed after reload"
            
            # Verify configuration is still valid after reload
            is_valid, error_msg = reloaded_config.validate()
            assert is_valid, f"Reloaded configuration should be valid: {error_msg}"
    
    print("✓ Configuration hot reload tests passed")


def test_configuration_manager_reload_consistency():
    """
    Test that ConfigurationManager maintains consistency during reload operations
    """
    print("Testing ConfigurationManager reload consistency...")
    
    # Run test with multiple random configurations
    for i in range(50):
        print(f"  Test iteration {i+1}/50")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "test_config.json"
            
            # Generate initial configuration with at least one model
            initial_config = generate_random_video_studio_config()
            # Ensure at least one model is enabled
            if initial_config.models:
                first_model = list(initial_config.models.values())[0]
                first_model.enabled = True
            
            # Create configuration manager
            config_manager = ConfigurationManager(str(config_path))
            
            # Save and load initial configuration
            with open(config_path, 'w') as f:
                json.dump(initial_config.to_dict(), f, indent=2)
            
            loaded_config = config_manager.load_config()
            
            # Store initial state
            initial_enabled_models = config_manager.get_enabled_models()
            
            # Generate modified configuration
            modified_config = generate_random_video_studio_config()
            
            # Save modified configuration
            with open(config_path, 'w') as f:
                json.dump(modified_config.to_dict(), f, indent=2)
            
            # Reload configuration
            reloaded_config = config_manager.reload_config()
            
            # Verify configuration manager state is consistent
            current_enabled_models = config_manager.get_enabled_models()
            
            # Verify that enabled models list matches the reloaded configuration
            expected_enabled = [name for name, model in reloaded_config.models.items() if model.enabled]
            assert set(current_enabled_models) == set(expected_enabled)
            
            # Verify configuration manager methods work with reloaded config
            for model_name in reloaded_config.models:
                retrieved_config = config_manager.get_model_config(model_name)
                assert retrieved_config is not None
                assert retrieved_config.name == reloaded_config.models[model_name].name
    
    print("✓ ConfigurationManager reload consistency tests passed")


def test_model_config_hot_add_remove():
    """
    Test hot adding and removing model configurations
    """
    print("Testing model configuration hot add/remove...")
    
    # Run test with multiple scenarios
    for i in range(30):
        print(f"  Test iteration {i+1}/30")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "test_config.json"
            
            # Start with minimal configuration
            initial_config = VideoStudioConfig(
                models={},
                storage=generate_random_storage_config(),
                workflow=generate_random_workflow_config(),
                rendering=generate_random_rendering_config()
            )
            
            config_manager = ConfigurationManager(str(config_path))
            
            # Save and load initial configuration
            with open(config_path, 'w') as f:
                json.dump(initial_config.to_dict(), f, indent=2)
            
            config_manager.load_config()
            
            # Verify initial state has no models
            assert len(config_manager.config.models) == 0
            
            # Add a new model configuration
            new_model_name = f"test_model_{generate_random_string(5, 10)}"
            new_model_config = generate_random_model_config()
            
            # Update configuration with new model
            updated_config_dict = initial_config.to_dict()
            updated_config_dict["models"][new_model_name] = new_model_config.__dict__
            
            # Save updated configuration
            with open(config_path, 'w') as f:
                json.dump(updated_config_dict, f, indent=2)
            
            # Hot reload
            reloaded_config = config_manager.reload_config()
            
            # Verify model was added
            assert len(reloaded_config.models) == 1
            assert new_model_name in reloaded_config.models
            assert reloaded_config.models[new_model_name].name == new_model_config.name
            assert reloaded_config.models[new_model_name].api_key == new_model_config.api_key
            
            # Now remove the model
            empty_config_dict = initial_config.to_dict()
            
            # Save configuration without the model
            with open(config_path, 'w') as f:
                json.dump(empty_config_dict, f, indent=2)
            
            # Hot reload again
            final_config = config_manager.reload_config()
            
            # Verify model was removed
            assert len(final_config.models) == 0
            assert new_model_name not in final_config.models
    
    print("✓ Model configuration hot add/remove tests passed")


def test_config_validation_after_reload():
    """
    Test that configuration validation works correctly after hot reload
    """
    print("Testing configuration validation after reload...")
    
    # Run test with multiple scenarios
    for i in range(20):
        print(f"  Test iteration {i+1}/20")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "test_config.json"
            
            # Generate valid initial configuration
            initial_config = generate_random_video_studio_config()
            
            config_manager = ConfigurationManager(str(config_path))
            
            # Save and load initial configuration
            with open(config_path, 'w') as f:
                json.dump(initial_config.to_dict(), f, indent=2)
            
            loaded_config = config_manager.load_config()
            
            # Verify initial configuration is valid
            is_valid, error_msg = loaded_config.validate()
            assert is_valid, f"Initial configuration should be valid: {error_msg}"
            
            # Create an invalid configuration (negative timeout)
            invalid_config_dict = initial_config.to_dict()
            if invalid_config_dict["models"]:
                first_model_name = list(invalid_config_dict["models"].keys())[0]
                invalid_config_dict["models"][first_model_name]["timeout"] = -1
            
            # Save invalid configuration
            with open(config_path, 'w') as f:
                json.dump(invalid_config_dict, f, indent=2)
            
            # Attempt to reload invalid configuration should raise error
            try:
                config_manager.reload_config()
                assert False, "Should have raised ValueError for invalid configuration"
            except ValueError as e:
                assert "Invalid configuration" in str(e)
            
            # Restore valid configuration
            with open(config_path, 'w') as f:
                json.dump(initial_config.to_dict(), f, indent=2)
            
            # Reload should work again
            restored_config = config_manager.reload_config()
            is_valid, error_msg = restored_config.validate()
            assert is_valid, f"Restored configuration should be valid: {error_msg}"
    
    print("✓ Configuration validation after reload tests passed")


def run_all_property_tests():
    """Run all property-based tests for configuration hot reload"""
    print("Running Property-Based Tests for Video Studio Configuration Hot Reload")
    print("=" * 70)
    
    try:
        test_configuration_hot_reload()
        test_configuration_manager_reload_consistency()
        test_model_config_hot_add_remove()
        test_config_validation_after_reload()
        
        print("\n" + "=" * 70)
        print("✅ All property tests PASSED!")
        print("Property 13: 配置热重载 - VALIDATED")
        print("Requirements 4.5 - SATISFIED")
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
    if not success:
        sys.exit(1)