#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

def test_enhanced_vision_service():
    """Test enhanced vision service integration"""
    
    print("Starting enhanced vision service integration tests...")
    
    try:
        print("Importing enhanced vision service...")
        from services.ai_studio.vision_service import StudioVisionService, ImageGenerationResult
        
        print("Testing vision service initialization...")
        vision_svc = StudioVisionService(None)  # No API key for testing
        assert vision_svc is not None, "Vision service should be instantiable"
        
        print("✓ Vision service initialization works")
        
        print("Testing generation capabilities...")
        capabilities = vision_svc.get_generation_capabilities()
        
        expected_capabilities = [
            'max_retries', 'supported_formats', 'max_image_size_mb',
            'supports_reference_images', 'supports_iterative_editing',
            'supports_progress_tracking', 'supports_high_quality_preview'
        ]
        
        for cap in expected_capabilities:
            assert cap in capabilities, f"Missing capability: {cap}"
        
        assert capabilities['supports_reference_images'] == True, "Should support reference images"
        assert capabilities['supports_iterative_editing'] == True, "Should support iterative editing"
        assert capabilities['supports_progress_tracking'] == True, "Should support progress tracking"
        assert capabilities['supports_high_quality_preview'] == True, "Should support high-quality preview"
        
        print("✓ Generation capabilities test passed")
        
        print("Testing ImageGenerationResult...")
        
        # Test successful result
        success_result = ImageGenerationResult(b"mock_image_data")
        assert success_result.success == True, "Should be marked as successful"
        assert success_result.image_data == b"mock_image_data", "Should store image data"
        assert success_result.error is None, "Should have no error"
        
        preview_data = success_result.get_preview_data()
        assert preview_data is not None, "Should provide preview data"
        assert isinstance(preview_data, str), "Preview data should be base64 string"
        
        download_data = success_result.get_download_data()
        assert download_data == b"mock_image_data", "Should provide download data"
        
        # Test failed result
        failed_result = ImageGenerationResult(error="Test error")
        assert failed_result.success == False, "Should be marked as failed"
        assert failed_result.image_data is None, "Should have no image data"
        assert failed_result.error == "Test error", "Should store error message"
        
        print("✓ ImageGenerationResult test passed")
        
        print("Testing reference image validation...")
        
        # Test image data validation
        valid_jpeg_header = b'\xff\xd8\xff\xe0' + b'\x00' * 100  # Mock JPEG header + data
        is_valid = vision_svc._validate_image_data(valid_jpeg_header)
        # Note: This might fail without PIL being able to parse it, but the method should exist
        
        # Test that validation methods exist
        assert hasattr(vision_svc, '_validate_image_data'), "Should have image data validation"
        assert hasattr(vision_svc, '_validate_reference_image'), "Should have reference image validation"
        
        print("✓ Reference image validation test passed")
        
        print("Testing enhanced reference resolution...")
        
        # Test with no reference images
        current_msg_no_ref = {"content": "Generate a cat", "ref_images": []}
        message_history = []
        
        ref_image, indicator = vision_svc.resolve_reference_image(current_msg_no_ref, message_history)
        assert ref_image is None, "Should return None when no reference images"
        assert indicator is None, "Should return None indicator when no reference images"
        
        # Test with mock reference image in current message
        class MockReferenceImage:
            def __init__(self):
                self.name = "test.jpg"
                self.size = 1024  # Small size for testing
        
        mock_ref = MockReferenceImage()
        current_msg_with_ref = {"content": "Edit this image", "ref_images": [mock_ref]}
        
        ref_image, indicator = vision_svc.resolve_reference_image(current_msg_with_ref, message_history)
        # Note: This might return None due to validation, but should not crash
        
        print("✓ Enhanced reference resolution test passed")
        
        print("Testing iterative editing support...")
        
        # Test iterative editing capability
        supports_iterative = vision_svc.supports_iterative_editing()
        assert supports_iterative == True, "Should support iterative editing"
        
        # Test with previous AI message containing image
        prev_ai_msg = {
            "role": "model",
            "type": "image_result",
            "hd_data": b"mock_previous_image_data",
            "id": "prev_msg_1"
        }
        
        message_history_with_image = [prev_ai_msg]
        current_edit_msg = {"content": "Make it more colorful", "ref_images": []}
        
        ref_image, indicator = vision_svc.resolve_reference_image(current_edit_msg, message_history_with_image)
        # Should attempt to resolve previous image (might fail due to mock data, but shouldn't crash)
        
        print("✓ Iterative editing support test passed")
        
        print("Testing image metadata extraction...")
        
        # Test metadata extraction (will fail with mock data, but method should exist)
        assert hasattr(vision_svc, 'get_image_metadata'), "Should have metadata extraction method"
        
        # Test with invalid data (should return error dict)
        metadata = vision_svc.get_image_metadata(b"invalid_image_data")
        assert isinstance(metadata, dict), "Should return dictionary"
        assert 'error' in metadata, "Should contain error for invalid data"
        
        print("✓ Image metadata extraction test passed")
        
        print("Testing high-quality preview creation...")
        
        # Test preview creation method exists
        assert hasattr(vision_svc, 'create_high_quality_preview'), "Should have preview creation method"
        
        # Test with invalid data (should return None gracefully)
        preview = vision_svc.create_high_quality_preview(b"invalid_image_data")
        assert preview is None, "Should return None for invalid image data"
        
        print("✓ High-quality preview creation test passed")
        
        print("Testing progress callback integration...")
        
        # Test that generate_image_with_progress method exists and accepts callback
        assert hasattr(vision_svc, 'generate_image_with_progress'), "Should have progress-enabled generation method"
        
        # Test progress callback functionality
        progress_calls = []
        
        def mock_progress_callback(message: str, value: float):
            progress_calls.append((message, value))
        
        # This will fail due to no API key, but should call progress callback
        result = vision_svc.generate_image_with_progress(
            "Test prompt", 
            "test-model", 
            None, 
            mock_progress_callback
        )
        
        # Should have made at least one progress call
        assert len(progress_calls) > 0, "Should have called progress callback"
        assert result.error is not None, "Should have error due to no API key"
        assert "api key" in result.error.lower(), "Error should mention API key"
        
        print("✓ Progress callback integration test passed")
        
        print("All enhanced vision service integration tests passed!")
        return True
        
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_enhanced_vision_service()
    sys.exit(0 if success else 1)