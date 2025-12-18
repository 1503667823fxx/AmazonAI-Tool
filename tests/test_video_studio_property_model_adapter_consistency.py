"""
Property-based tests for Video Studio Model Adapter Interface Consistency
Tests that all model adapters implement unified interface specifications and support hot-pluggable integration
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import asyncio
import random
import string
from typing import List, Dict, Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta

from app_utils.video_studio.model_adapter import (
    ModelAdapter, GenerationConfig, GenerationResult, JobStatus, 
    ModelCapability, ModelAdapterRegistry, model_registry
)
from app_utils.video_studio.adapters.luma_adapter import LumaAdapter
from app_utils.video_studio.adapters.runway_adapter import RunwayAdapter
from app_utils.video_studio.adapters.pika_adapter import PikaAdapter
from app_utils.video_studio.config import ModelConfig
from app_utils.video_studio.error_handler import VideoStudioErrorHandler


# Test data generators using random
def generate_random_string(min_length=1, max_length=50):
    """Generate a random string."""
    length = random.randint(min_length, max_length)
    return ''.join(random.choices(string.ascii_letters + string.digits + ' ', k=length)).strip() or 'test'


def generate_generation_config():
    """Generate valid GenerationConfig instances for testing."""
    return GenerationConfig(
        prompt=generate_random_string(1, 200),
        reference_image=random.choice([None, generate_random_string(1, 100)]),
        duration=random.uniform(0.1, 300.0),
        aspect_ratio=random.choice(["16:9", "9:16", "1:1"]),
        quality=random.choice(["720p", "1080p", "4k"]),
        style=random.choice([None, generate_random_string(1, 50)]),
        camera_movement=random.choice([None, "zoom_in", "zoom_out", "pan_left", "pan_right", "tilt_up", "tilt_down"]),
        motion_strength=random.uniform(0.0, 1.0),
        seed=random.choice([None, random.randint(0, 2**31-1)])
    )


def generate_model_config(name=None):
    """Generate valid ModelConfig instances for testing."""
    return ModelConfig(
        name=name or generate_random_string(1, 50),
        api_key=generate_random_string(10, 100),
        base_url=random.choice([None, f"https://{generate_random_string(5, 20)}.com"]),
        timeout=random.uniform(1.0, 300.0),
        max_retries=random.randint(0, 10),
        rate_limit=random.randint(1, 1000),
        enabled=random.choice([True, False])
    )


class MockModelAdapter(ModelAdapter):
    """Mock model adapter for testing interface consistency."""
    
    def __init__(self, config: ModelConfig, error_handler: VideoStudioErrorHandler):
        super().__init__(config, error_handler)
        self._capabilities = [ModelCapability.IMAGE_TO_VIDEO, ModelCapability.TEXT_TO_VIDEO]
        self._supported_aspect_ratios = ["16:9", "9:16", "1:1"]
        self._supported_qualities = ["720p", "1080p"]
        self._max_duration = 10.0
        
        # Mock async methods
        self.generate = AsyncMock()
        self.get_status = AsyncMock()
        self.cancel_job = AsyncMock()
    
    @property
    def capabilities(self) -> List[ModelCapability]:
        return self._capabilities
    
    @property
    def supported_aspect_ratios(self) -> List[str]:
        return self._supported_aspect_ratios
    
    @property
    def supported_qualities(self) -> List[str]:
        return self._supported_qualities
    
    @property
    def max_duration(self) -> float:
        return self._max_duration


def create_test_adapters() -> List[ModelAdapter]:
    """Create test adapter instances with mocked HTTP sessions."""
    error_handler = VideoStudioErrorHandler()
    
    adapters = []
    
    # Create mock configs for each adapter
    configs = [
        ModelConfig(name="luma", api_key="test_luma_key", enabled=True),
        ModelConfig(name="runway", api_key="test_runway_key", enabled=True),
        ModelConfig(name="pika", api_key="test_pika_key", enabled=True),
        ModelConfig(name="mock", api_key="test_mock_key", enabled=True)
    ]
    
    # Create adapters with mocked network calls
    with patch('aiohttp.ClientSession'):
        luma = LumaAdapter(configs[0], error_handler)
        runway = RunwayAdapter(configs[1], error_handler)
        pika = PikaAdapter(configs[2], error_handler)
        mock = MockModelAdapter(configs[3], error_handler)
        
        adapters.extend([luma, runway, pika, mock])
    
    return adapters


def test_adapter_interface_consistency_validation():
    """
    **Feature: video-studio-redesign, Property 2: 模型适配器接口一致性**
    **Validates: Requirements 2.1, 2.2, 2.4**
    
    Property: For any registered AI model adapter, they should implement unified interface 
    specifications, support hot-pluggable integration, and model switching should not 
    affect core business logic
    """
    print("Testing adapter interface consistency validation...")
    
    # Run test with multiple random configurations
    for i in range(100):
        config = generate_generation_config()
        adapters = create_test_adapters()
        
        # Test 1: All adapters must implement the same interface methods
        required_methods = ['generate', 'get_status', 'cancel_job', 'validate_config']
        required_properties = ['capabilities', 'supported_aspect_ratios', 'supported_qualities', 'max_duration']
        
        for adapter in adapters:
            # Check required methods exist and are callable
            for method_name in required_methods:
                assert hasattr(adapter, method_name), f"Adapter {adapter.name} missing method {method_name}"
                method = getattr(adapter, method_name)
                assert callable(method), f"Adapter {adapter.name} method {method_name} is not callable"
            
            # Check required properties exist
            for prop_name in required_properties:
                assert hasattr(adapter, prop_name), f"Adapter {adapter.name} missing property {prop_name}"
                prop_value = getattr(adapter, prop_name)
                assert prop_value is not None, f"Adapter {adapter.name} property {prop_name} is None"
    
    print("✓ Interface consistency validation tests passed")


def test_adapter_validation_consistency():
    """
    Test that all adapters provide consistent validation behavior.
    """
    print("Testing adapter validation consistency...")
    
    # Run test with multiple random configurations
    for i in range(50):
        config = generate_generation_config()
        adapters = create_test_adapters()
        
        for adapter in adapters:
            # Test validation method signature and return type
            is_valid, error_msg = adapter.validate_config(config)
            
            # Validation should return a tuple of (bool, Optional[str])
            assert isinstance(is_valid, bool), f"Adapter {adapter.name} validate_config should return bool as first element"
            assert error_msg is None or isinstance(error_msg, str), f"Adapter {adapter.name} validate_config should return Optional[str] as second element"
            
            # If invalid, error message should be provided
            if not is_valid:
                assert error_msg is not None and error_msg.strip(), f"Adapter {adapter.name} should provide error message when validation fails"
    
    print("✓ Validation consistency tests passed")


def test_adapter_capabilities_consistency():
    """
    Test that adapter capabilities are consistently defined and accessible.
    """
    print("Testing adapter capabilities consistency...")
    
    # Run test with multiple random configurations
    for i in range(30):
        config = generate_generation_config()
        adapters = create_test_adapters()
        
        for adapter in adapters:
            capabilities = adapter.capabilities
            
            # Capabilities should be a list of ModelCapability enums
            assert isinstance(capabilities, list), f"Adapter {adapter.name} capabilities should be a list"
            assert len(capabilities) > 0, f"Adapter {adapter.name} should have at least one capability"
            
            for cap in capabilities:
                assert isinstance(cap, ModelCapability), f"Adapter {adapter.name} capability {cap} should be ModelCapability enum"
            
            # Supported aspect ratios should be consistent
            aspect_ratios = adapter.supported_aspect_ratios
            assert isinstance(aspect_ratios, list), f"Adapter {adapter.name} supported_aspect_ratios should be a list"
            assert len(aspect_ratios) > 0, f"Adapter {adapter.name} should support at least one aspect ratio"
            
            for ratio in aspect_ratios:
                assert isinstance(ratio, str), f"Adapter {adapter.name} aspect ratio should be string"
                assert ":" in ratio, f"Adapter {adapter.name} aspect ratio {ratio} should be in format 'width:height'"
            
            # Supported qualities should be consistent
            qualities = adapter.supported_qualities
            assert isinstance(qualities, list), f"Adapter {adapter.name} supported_qualities should be a list"
            assert len(qualities) > 0, f"Adapter {adapter.name} should support at least one quality"
            
            # Max duration should be positive
            max_duration = adapter.max_duration
            assert isinstance(max_duration, (int, float)), f"Adapter {adapter.name} max_duration should be numeric"
            assert max_duration > 0, f"Adapter {adapter.name} max_duration should be positive"
    
    print("✓ Capabilities consistency tests passed")


def test_adapter_registry_hot_pluggable_integration():
    """
    Test that adapters can be registered and unregistered without affecting core logic.
    """
    # Create a fresh registry for testing
    test_registry = ModelAdapterRegistry()
    adapters = create_test_adapters()
    
    # Test registration
    for adapter in adapters:
        # Should be able to register without errors
        test_registry.register(adapter)
        
        # Should be able to retrieve the adapter
        retrieved = test_registry.get_adapter(adapter.name)
        assert retrieved is not None, f"Failed to retrieve registered adapter {adapter.name}"
        assert retrieved.name == adapter.name, f"Retrieved adapter name mismatch for {adapter.name}"
    
    # Test listing
    adapter_names = test_registry.list_adapters()
    assert len(adapter_names) == len(adapters), "Registry should contain all registered adapters"
    
    for adapter in adapters:
        assert adapter.name in adapter_names, f"Adapter {adapter.name} should be in registry list"
    
    # Test unregistration
    for adapter in adapters:
        success = test_registry.unregister(adapter.name)
        assert success, f"Failed to unregister adapter {adapter.name}"
        
        # Should no longer be retrievable
        retrieved = test_registry.get_adapter(adapter.name)
        assert retrieved is None, f"Adapter {adapter.name} should not be retrievable after unregistration"
    
    # Registry should be empty
    assert len(test_registry.list_adapters()) == 0, "Registry should be empty after unregistering all adapters"


def test_adapter_model_info_consistency():
    """
    Test that all adapters provide consistent model information.
    """
    print("Testing adapter model info consistency...")
    
    # Run test with multiple random configurations
    for i in range(20):
        config = generate_generation_config()
        adapters = create_test_adapters()
        
        for adapter in adapters:
            model_info = adapter.get_model_info()
            
            # Model info should be a dictionary
            assert isinstance(model_info, dict), f"Adapter {adapter.name} get_model_info should return dict"
            
            # Required fields in model info
            required_fields = ['name', 'enabled', 'capabilities', 'supported_aspect_ratios', 
                              'supported_qualities', 'max_duration', 'config']
            
            for field in required_fields:
                assert field in model_info, f"Adapter {adapter.name} model_info missing field {field}"
            
            # Verify field types and values
            assert isinstance(model_info['name'], str), f"Adapter {adapter.name} model_info name should be string"
            assert isinstance(model_info['enabled'], bool), f"Adapter {adapter.name} model_info enabled should be bool"
            assert isinstance(model_info['capabilities'], list), f"Adapter {adapter.name} model_info capabilities should be list"
            assert isinstance(model_info['supported_aspect_ratios'], list), f"Adapter {adapter.name} model_info supported_aspect_ratios should be list"
            assert isinstance(model_info['supported_qualities'], list), f"Adapter {adapter.name} model_info supported_qualities should be list"
            assert isinstance(model_info['max_duration'], (int, float)), f"Adapter {adapter.name} model_info max_duration should be numeric"
            assert isinstance(model_info['config'], dict), f"Adapter {adapter.name} model_info config should be dict"
    
    print("✓ Model info consistency tests passed")


def test_adapter_string_representation_consistency():
    """
    Test that all adapters provide consistent string representations.
    """
    adapters = create_test_adapters()
    
    for adapter in adapters:
        # Test __str__ method
        str_repr = str(adapter)
        assert isinstance(str_repr, str), f"Adapter {adapter.name} __str__ should return string"
        assert adapter.name in str_repr, f"Adapter {adapter.name} __str__ should contain adapter name"
        
        # Test __repr__ method
        repr_str = repr(adapter)
        assert isinstance(repr_str, str), f"Adapter {adapter.name} __repr__ should return string"
        assert adapter.name in repr_str, f"Adapter {adapter.name} __repr__ should contain adapter name"


def test_adapter_configuration_validation_edge_cases():
    """
    Test adapter configuration validation with edge cases.
    """
    print("Testing adapter configuration validation edge cases...")
    
    # Run test with multiple random configurations
    for i in range(20):
        config = generate_generation_config()
        adapters = create_test_adapters()
        
        # Test with extreme values
        extreme_configs = [
            # Very short duration
            GenerationConfig(prompt="test", duration=0.01),
            # Very long duration
            GenerationConfig(prompt="test", duration=1000.0),
            # Empty prompt (should be invalid)
            GenerationConfig(prompt="", duration=5.0),
            # Very long prompt
            GenerationConfig(prompt="x" * 10000, duration=5.0),
            # Invalid aspect ratio
            GenerationConfig(prompt="test", aspect_ratio="invalid:ratio", duration=5.0),
            # Invalid quality
            GenerationConfig(prompt="test", quality="invalid_quality", duration=5.0),
            # Motion strength out of bounds
            GenerationConfig(prompt="test", motion_strength=2.0, duration=5.0),
            GenerationConfig(prompt="test", motion_strength=-0.5, duration=5.0)
        ]
        
        for adapter in adapters:
            for j, extreme_config in enumerate(extreme_configs):
                try:
                    is_valid, error_msg = adapter.validate_config(extreme_config)
                    
                    # Most extreme configs should be invalid
                    if not is_valid:
                        assert error_msg is not None, f"Adapter {adapter.name} should provide error message for extreme config {j}"
                        assert isinstance(error_msg, str), f"Adapter {adapter.name} error message should be string for extreme config {j}"
                        assert len(error_msg.strip()) > 0, f"Adapter {adapter.name} error message should not be empty for extreme config {j}"
                    
                except Exception as e:
                    # Some extreme values might raise exceptions, which is acceptable
                    assert isinstance(e, (ValueError, TypeError)), f"Adapter {adapter.name} should raise ValueError or TypeError for extreme config {j}, got {type(e)}"
    
    print("✓ Edge case validation tests passed")


def test_adapter_registry_capability_filtering():
    """
    Test that registry can filter adapters by capabilities correctly.
    """
    test_registry = ModelAdapterRegistry()
    adapters = create_test_adapters()
    
    # Register all adapters
    for adapter in adapters:
        test_registry.register(adapter)
    
    # Test filtering by each capability
    for capability in ModelCapability:
        filtered_adapters = test_registry.get_adapters_by_capability(capability)
        
        # Should return a list
        assert isinstance(filtered_adapters, list), f"get_adapters_by_capability should return list for {capability}"
        
        # All returned adapters should have the requested capability and be enabled
        for adapter in filtered_adapters:
            assert capability in adapter.capabilities, f"Adapter {adapter.name} should have capability {capability}"
            assert adapter.enabled, f"Adapter {adapter.name} should be enabled"


def test_adapter_best_match_selection():
    """
    Test that registry can select the best adapter for a given configuration.
    """
    print("Testing adapter best match selection...")
    
    # Run test with multiple random configurations
    for i in range(10):
        config = generate_generation_config()
        test_registry = ModelAdapterRegistry()
        adapters = create_test_adapters()
        
        # Register all adapters
        for adapter in adapters:
            test_registry.register(adapter)
        
        # Test best adapter selection
        best_adapter = test_registry.get_best_adapter_for_config(config)
        
        if best_adapter is not None:
            # Best adapter should be enabled
            assert best_adapter.enabled, f"Best adapter {best_adapter.name} should be enabled"
            
            # Best adapter should validate the config
            is_valid, _ = best_adapter.validate_config(config)
            assert is_valid, f"Best adapter {best_adapter.name} should validate the given config"
    
    print("✓ Best adapter selection tests passed")


def run_all_property_tests():
    """Run all property-based tests for model adapter consistency"""
    print("Running Property-Based Tests for Video Studio Model Adapter Consistency")
    print("=" * 80)
    
    try:
        # Run property-based tests with random generation
        test_adapter_interface_consistency_validation()
        test_adapter_validation_consistency()
        test_adapter_capabilities_consistency()
        
        # Run deterministic tests
        print("Testing hot-pluggable integration...")
        test_adapter_registry_hot_pluggable_integration()
        print("✓ Hot-pluggable integration tests passed")
        
        test_adapter_model_info_consistency()
        test_adapter_string_representation_consistency()
        test_adapter_configuration_validation_edge_cases()
        test_adapter_registry_capability_filtering()
        test_adapter_best_match_selection()
        
        print("\n" + "=" * 80)
        print("✅ All property tests PASSED!")
        print("Property 2: 模型适配器接口一致性 - VALIDATED")
        print("Requirements 2.1, 2.2, 2.4 - SATISFIED")
        return True
        
    except Exception as e:
        print(f"\n❌ Test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_property_tests()
    exit(0 if success else 1)