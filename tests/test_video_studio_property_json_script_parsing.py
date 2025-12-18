"""
Property-based tests for Video Studio JSON script parsing consistency
Tests JSON script parsing and validation across all valid and invalid inputs
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app_utils.video_studio.scene_generator import SceneGenerator, ScriptValidationResult, ValidationError
from app_utils.video_studio.models import Scene
from app_utils.video_studio.error_handler import ErrorHandler
import json
import tempfile
from pathlib import Path
from typing import Dict, Any, List
import random
import string


def generate_valid_scene_data(scene_id: str = None) -> Dict[str, Any]:
    """Generate a valid scene data dictionary for testing."""
    if scene_id is None:
        scene_id = f"scene_{random.randint(1, 1000)}"
    
    return {
        "scene_id": scene_id,
        "visual_prompt": f"A beautiful scene with {random.choice(['mountains', 'ocean', 'forest', 'city'])}",
        "duration": round(random.uniform(1.0, 30.0), 1),
        "camera_movement": random.choice([None, "pan_left", "pan_right", "zoom_in", "zoom_out", "static"]),
        "lighting": random.choice([None, "natural", "studio", "golden_hour", "blue_hour"]),
        "reference_image": random.choice([None, f"asset_{random.randint(1, 100)}"])
    }


def generate_valid_script_data(num_scenes: int = None) -> Dict[str, Any]:
    """Generate a valid script data dictionary for testing."""
    if num_scenes is None:
        num_scenes = random.randint(1, 10)
    
    scenes = []
    for i in range(num_scenes):
        scenes.append(generate_valid_scene_data(f"scene_{i+1}"))
    
    return {
        "title": f"Test Script {random.randint(1, 1000)}",
        "description": "A test script for property testing",
        "scenes": scenes
    }


def generate_invalid_json_string() -> str:
    """Generate various types of invalid JSON strings."""
    invalid_types = [
        '{"scenes": [}',  # Invalid JSON syntax
        '{"scenes": [{"scene_id": "test", "visual_prompt": "test", "duration": 5.0,}]}',  # Trailing comma
        '{"scenes": [{"scene_id": "test" "visual_prompt": "test", "duration": 5.0}]}',  # Missing comma
        '{scenes: [{"scene_id": "test", "visual_prompt": "test", "duration": 5.0}]}',  # Unquoted key
        '{"scenes": [{"scene_id": "test", "visual_prompt": "test", "duration": 5.0}]',  # Missing closing brace
        'not json at all',  # Not JSON
        '',  # Empty string
        'null',  # Valid JSON but not an object
        '[]',  # Valid JSON array but not object
        '"string"'  # Valid JSON string but not object
    ]
    return random.choice(invalid_types)


def generate_invalid_scene_data() -> Dict[str, Any]:
    """Generate invalid scene data for testing."""
    invalid_types = [
        # Missing required fields
        {"visual_prompt": "test", "duration": 5.0},  # Missing scene_id
        {"scene_id": "test", "duration": 5.0},  # Missing visual_prompt
        {"scene_id": "test", "visual_prompt": "test"},  # Missing duration
        
        # Invalid field types
        {"scene_id": 123, "visual_prompt": "test", "duration": 5.0},  # scene_id not string
        {"scene_id": "test", "visual_prompt": 123, "duration": 5.0},  # visual_prompt not string
        {"scene_id": "test", "visual_prompt": "test", "duration": "5.0"},  # duration not number
        
        # Invalid field values
        {"scene_id": "", "visual_prompt": "test", "duration": 5.0},  # Empty scene_id
        {"scene_id": "test", "visual_prompt": "", "duration": 5.0},  # Empty visual_prompt
        {"scene_id": "test", "visual_prompt": "test", "duration": 0.0},  # Zero duration
        {"scene_id": "test", "visual_prompt": "test", "duration": -1.0},  # Negative duration
        
        # Invalid optional field types
        {"scene_id": "test", "visual_prompt": "test", "duration": 5.0, "camera_movement": 123},
        {"scene_id": "test", "visual_prompt": "test", "duration": 5.0, "lighting": []},
        {"scene_id": "test", "visual_prompt": "test", "duration": 5.0, "reference_image": True}
    ]
    return random.choice(invalid_types)


def test_json_script_parsing_consistency():
    """
    **Feature: video-studio-redesign, Property 5: JSON脚本解析一致性**
    **Validates: Requirements 3.1, 3.4**
    
    Property: For any structured JSON video script, the scene generator should correctly 
    parse valid JSON formats and provide accurate validation error information for 
    format errors in scripts
    """
    print("Testing JSON script parsing consistency...")
    
    scene_generator = SceneGenerator()
    
    # Test 1: Valid JSON scripts should be parsed successfully
    print("  Testing valid JSON script parsing...")
    for i in range(20):  # Test multiple valid scripts
        script_data = generate_valid_script_data()
        script_json = json.dumps(script_data)
        
        # Test parsing from JSON string
        result = scene_generator.parse_json_script(script_json)
        assert result.is_valid, f"Valid script {i+1} was rejected: {result.get_error_summary()}"
        assert len(result.parsed_scenes) == len(script_data["scenes"]), f"Scene count mismatch for script {i+1}"
        
        # Test parsing from dictionary
        result_dict = scene_generator.parse_json_script(script_data)
        assert result_dict.is_valid, f"Valid script dict {i+1} was rejected: {result_dict.get_error_summary()}"
        assert len(result_dict.parsed_scenes) == len(script_data["scenes"]), f"Scene count mismatch for script dict {i+1}"
        
        # Results should be equivalent
        assert result.is_valid == result_dict.is_valid
        assert len(result.parsed_scenes) == len(result_dict.parsed_scenes)
    
    print("  ✓ Valid JSON script parsing tests passed")
    
    # Test 2: Invalid JSON strings should be rejected with proper error messages
    print("  Testing invalid JSON string handling...")
    for i in range(15):  # Test multiple invalid JSON strings
        invalid_json = generate_invalid_json_string()
        
        result = scene_generator.parse_json_script(invalid_json)
        assert not result.is_valid, f"Invalid JSON {i+1} was accepted: '{invalid_json}'"
        assert len(result.errors) > 0, f"No errors reported for invalid JSON {i+1}: '{invalid_json}'"
        assert len(result.parsed_scenes) == 0, f"Scenes were parsed from invalid JSON {i+1}: '{invalid_json}'"
        
        # Error message should be informative
        error_summary = result.get_error_summary()
        assert len(error_summary) > 0, f"Empty error summary for invalid JSON {i+1}"
    
    print("  ✓ Invalid JSON string handling tests passed")
    
    # Test 3: Scripts with invalid scene data should be rejected
    print("  Testing invalid scene data handling...")
    for i in range(20):  # Test multiple invalid scene configurations
        invalid_scene = generate_invalid_scene_data()
        script_data = {
            "title": "Invalid Scene Test",
            "scenes": [invalid_scene]
        }
        
        result = scene_generator.parse_json_script(script_data)
        assert not result.is_valid, f"Invalid scene data {i+1} was accepted: {invalid_scene}"
        assert len(result.errors) > 0, f"No errors reported for invalid scene {i+1}: {invalid_scene}"
        
        # Should have specific field-level error information
        has_field_error = any("scene" in error.field.lower() for error in result.errors)
        assert has_field_error, f"No scene-specific error for invalid scene {i+1}: {invalid_scene}"
    
    print("  ✓ Invalid scene data handling tests passed")
    
    # Test 4: Scripts with duplicate scene IDs should be rejected
    print("  Testing duplicate scene ID detection...")
    for i in range(10):
        duplicate_id = f"duplicate_scene_{i}"
        script_data = {
            "scenes": [
                generate_valid_scene_data(duplicate_id),
                generate_valid_scene_data(duplicate_id),  # Duplicate ID
                generate_valid_scene_data(f"unique_scene_{i}")
            ]
        }
        
        result = scene_generator.parse_json_script(script_data)
        assert not result.is_valid, f"Duplicate scene ID {duplicate_id} was accepted"
        
        # Should have specific duplicate ID error
        has_duplicate_error = any("duplicate" in error.message.lower() for error in result.errors)
        assert has_duplicate_error, f"No duplicate ID error for scene {duplicate_id}"
    
    print("  ✓ Duplicate scene ID detection tests passed")
    
    # Test 5: Edge cases and boundary conditions
    print("  Testing edge cases and boundary conditions...")
    
    # Empty scenes array
    empty_script = {"scenes": []}
    result = scene_generator.parse_json_script(empty_script)
    assert result.is_valid, "Empty scenes array should be valid"
    assert len(result.warnings) > 0, "Empty scenes should generate a warning"
    
    # Missing scenes key
    no_scenes_script = {"title": "No scenes"}
    result = scene_generator.parse_json_script(no_scenes_script)
    assert not result.is_valid, "Script without scenes key should be invalid"
    
    # Non-array scenes
    invalid_scenes_script = {"scenes": "not an array"}
    result = scene_generator.parse_json_script(invalid_scenes_script)
    assert not result.is_valid, "Script with non-array scenes should be invalid"
    
    # Very long script (boundary testing)
    large_script = generate_valid_script_data(50)  # 50 scenes
    result = scene_generator.parse_json_script(large_script)
    assert result.is_valid, "Large valid script should be accepted"
    if len(result.warnings) > 0:
        # Should warn about large number of scenes
        has_size_warning = any("scene" in warning.lower() for warning in result.warnings)
        assert has_size_warning, "Large script should generate size warning"
    
    print("  ✓ Edge cases and boundary conditions tests passed")


def test_json_script_round_trip_consistency():
    """
    Test that valid scripts can be parsed and the parsed scenes can be used to reconstruct equivalent scripts.
    This tests the round-trip consistency of the parsing process.
    """
    print("Testing JSON script round-trip consistency...")
    
    scene_generator = SceneGenerator()
    
    for i in range(15):  # Test multiple round trips
        # Generate original script
        original_script = generate_valid_script_data()
        
        # Parse the script
        result = scene_generator.parse_json_script(original_script)
        assert result.is_valid, f"Round-trip test {i+1}: Original script should be valid"
        
        # Reconstruct script from parsed scenes
        reconstructed_script = {
            "title": original_script.get("title", "Reconstructed Script"),
            "scenes": [scene.to_dict() for scene in result.parsed_scenes]
        }
        
        # Parse the reconstructed script
        reconstructed_result = scene_generator.parse_json_script(reconstructed_script)
        assert reconstructed_result.is_valid, f"Round-trip test {i+1}: Reconstructed script should be valid"
        
        # Key properties should be preserved
        assert len(result.parsed_scenes) == len(reconstructed_result.parsed_scenes), f"Round-trip test {i+1}: Scene count mismatch"
        
        # Scene properties should match
        for orig_scene, recon_scene in zip(result.parsed_scenes, reconstructed_result.parsed_scenes):
            assert orig_scene.scene_id == recon_scene.scene_id, f"Round-trip test {i+1}: Scene ID mismatch"
            assert orig_scene.visual_prompt == recon_scene.visual_prompt, f"Round-trip test {i+1}: Visual prompt mismatch"
            assert abs(orig_scene.duration - recon_scene.duration) < 0.01, f"Round-trip test {i+1}: Duration mismatch"
            assert orig_scene.camera_movement == recon_scene.camera_movement, f"Round-trip test {i+1}: Camera movement mismatch"
            assert orig_scene.lighting == recon_scene.lighting, f"Round-trip test {i+1}: Lighting mismatch"
            assert orig_scene.reference_image == recon_scene.reference_image, f"Round-trip test {i+1}: Reference image mismatch"
    
    print("  ✓ JSON script round-trip consistency tests passed")


def test_file_based_script_parsing():
    """
    Test parsing JSON scripts from files, including file I/O error handling.
    """
    print("Testing file-based script parsing...")
    
    scene_generator = SceneGenerator()
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Test 1: Valid script file
        valid_script = generate_valid_script_data()
        valid_file = temp_path / "valid_script.json"
        
        with open(valid_file, 'w', encoding='utf-8') as f:
            json.dump(valid_script, f, indent=2)
        
        result = scene_generator.validate_script_file(valid_file)
        assert result.is_valid, f"Valid script file was rejected: {result.get_error_summary()}"
        assert len(result.parsed_scenes) == len(valid_script["scenes"]), "Scene count mismatch from file"
        
        # Test 2: Invalid JSON file
        invalid_file = temp_path / "invalid_script.json"
        with open(invalid_file, 'w', encoding='utf-8') as f:
            f.write('{"scenes": [}')  # Invalid JSON
        
        result = scene_generator.validate_script_file(invalid_file)
        assert not result.is_valid, "Invalid JSON file was accepted"
        assert len(result.errors) > 0, "No errors for invalid JSON file"
        
        # Test 3: Non-existent file
        nonexistent_file = temp_path / "nonexistent.json"
        result = scene_generator.validate_script_file(nonexistent_file)
        assert not result.is_valid, "Non-existent file was accepted"
        assert any("not found" in error.message.lower() for error in result.errors), "No file not found error"
        
        # Test 4: Directory instead of file
        directory_path = temp_path / "directory"
        directory_path.mkdir()
        result = scene_generator.validate_script_file(directory_path)
        assert not result.is_valid, "Directory was accepted as file"
        assert any("not a file" in error.message.lower() for error in result.errors), "No 'not a file' error"
    
    print("  ✓ File-based script parsing tests passed")


def test_error_message_quality():
    """
    Test that error messages are informative and help users understand what went wrong.
    """
    print("Testing error message quality...")
    
    scene_generator = SceneGenerator()
    
    # Test specific error scenarios and verify error message quality
    error_test_cases = [
        {
            "name": "Missing scene_id",
            "script": {"scenes": [{"visual_prompt": "test", "duration": 5.0}]},
            "expected_keywords": ["scene_id", "missing", "required"]
        },
        {
            "name": "Invalid duration type",
            "script": {"scenes": [{"scene_id": "test", "visual_prompt": "test", "duration": "not_a_number"}]},
            "expected_keywords": ["duration", "type"]
        },
        {
            "name": "Empty visual prompt",
            "script": {"scenes": [{"scene_id": "test", "visual_prompt": "", "duration": 5.0}]},
            "expected_keywords": ["visual_prompt", "empty"]
        },
        {
            "name": "Negative duration",
            "script": {"scenes": [{"scene_id": "test", "visual_prompt": "test", "duration": -1.0}]},
            "expected_keywords": ["duration", "positive"]
        }
    ]
    
    for test_case in error_test_cases:
        result = scene_generator.parse_json_script(test_case["script"])
        assert not result.is_valid, f"Error test case '{test_case['name']}' was accepted"
        
        error_summary = result.get_error_summary().lower()
        for keyword in test_case["expected_keywords"]:
            assert keyword.lower() in error_summary, f"Error message for '{test_case['name']}' missing keyword '{keyword}': {error_summary}"
    
    print("  ✓ Error message quality tests passed")


def test_warning_generation():
    """
    Test that appropriate warnings are generated for potentially problematic but valid scripts.
    """
    print("Testing warning generation...")
    
    scene_generator = SceneGenerator()
    
    # Test cases that should generate warnings
    warning_test_cases = [
        {
            "name": "Very long visual prompt",
            "script": {"scenes": [{"scene_id": "test", "visual_prompt": "x" * 1500, "duration": 5.0}]},
            "expected_warning_keywords": ["prompt", "long"]
        },
        {
            "name": "Very long scene duration",
            "script": {"scenes": [{"scene_id": "test", "visual_prompt": "test", "duration": 120.0}]},
            "expected_warning_keywords": ["duration", "exceed"]
        },
        {
            "name": "Unknown fields in scene",
            "script": {"scenes": [{"scene_id": "test", "visual_prompt": "test", "duration": 5.0, "unknown_field": "value"}]},
            "expected_warning_keywords": ["unknown", "field"]
        }
    ]
    
    for test_case in warning_test_cases:
        result = scene_generator.parse_json_script(test_case["script"])
        assert result.is_valid, f"Warning test case '{test_case['name']}' should be valid"
        assert len(result.warnings) > 0, f"No warnings generated for '{test_case['name']}'"
        
        warnings_text = " ".join(result.warnings).lower()
        for keyword in test_case["expected_warning_keywords"]:
            assert keyword.lower() in warnings_text, f"Warning for '{test_case['name']}' missing keyword '{keyword}': {warnings_text}"
    
    print("  ✓ Warning generation tests passed")


def run_all_property_tests():
    """Run all property-based tests for JSON script parsing consistency"""
    print("Running Property-Based Tests for Video Studio JSON Script Parsing")
    print("=" * 70)
    
    try:
        test_json_script_parsing_consistency()
        test_json_script_round_trip_consistency()
        test_file_based_script_parsing()
        test_error_message_quality()
        test_warning_generation()
        
        print("\n" + "=" * 70)
        print("✅ All property tests PASSED!")
        print("Property 5: JSON脚本解析一致性 - VALIDATED")
        print("Requirements 3.1, 3.4 - SATISFIED")
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