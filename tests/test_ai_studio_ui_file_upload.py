#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

def test_file_upload_feedback():
    """Test file upload feedback properties"""
    
    print("Starting file upload feedback tests...")
    
    try:
        print("Importing InputPanel...")
        from app_utils.ai_studio.components.input_panel import InputPanel
        
        print("Creating InputPanel instance...")
        input_panel = InputPanel()
        print(f"InputPanel created with max_files={input_panel.max_files}, supported_formats={input_panel.supported_formats}")
        
        print("Testing file upload feedback properties...")
        
        # Test 1: Basic validation
        class MockFile:
            def __init__(self, name: str, size: int):
                self.name = name
                self.size = size
                self.type = self._get_mime_type(name)
            
            def _get_mime_type(self, name: str) -> str:
                ext = name.split('.')[-1].lower()
                mime_types = {
                    'jpg': 'image/jpeg',
                    'jpeg': 'image/jpeg', 
                    'png': 'image/png',
                    'webp': 'image/webp',
                    'txt': 'text/plain',
                    'pdf': 'application/pdf'
                }
                return mime_types.get(ext, 'application/octet-stream')
        
        # Test valid file
        valid_file = MockFile("test.jpg", 1024)
        assert input_panel._validate_file(valid_file) == True, "Valid JPG file should pass validation"
        
        # Test invalid extension
        invalid_file = MockFile("test.txt", 1024)
        assert input_panel._validate_file(invalid_file) == False, "TXT file should fail validation"
        
        # Test oversized file
        large_file = MockFile("test.jpg", 50 * 1024 * 1024)  # 50MB
        assert input_panel._validate_file(large_file) == False, "Oversized file should fail validation"
        
        print("✓ File upload validation consistency test passed")
        
        # Test 2: Supported formats configuration
        original_formats = input_panel.supported_formats.copy()
        input_panel.supported_formats = ['jpg', 'png']
        
        jpg_file = MockFile("test.jpg", 1024)
        png_file = MockFile("test.png", 1024)
        webp_file = MockFile("test.webp", 1024)
        
        assert input_panel._validate_file(jpg_file) == True, "JPG should be valid when in supported formats"
        assert input_panel._validate_file(png_file) == True, "PNG should be valid when in supported formats"
        assert input_panel._validate_file(webp_file) == False, "WEBP should be invalid when not in supported formats"
        
        # Restore original formats
        input_panel.supported_formats = original_formats
        
        print("✓ Supported format configuration test passed")
        
        # Test 3: File size limits
        original_max_size = input_panel.max_file_size
        input_panel.max_file_size = 5 * 1024 * 1024  # 5MB
        
        small_file = MockFile("test.jpg", 1024)
        medium_file = MockFile("test.jpg", 3 * 1024 * 1024)  # 3MB
        large_file = MockFile("test.jpg", 10 * 1024 * 1024)  # 10MB
        
        assert input_panel._validate_file(small_file) == True, "Small file should pass size validation"
        assert input_panel._validate_file(medium_file) == True, "Medium file should pass size validation"
        assert input_panel._validate_file(large_file) == False, "Large file should fail size validation"
        
        # Restore original max size
        input_panel.max_file_size = original_max_size
        
        print("✓ File size limit consistency test passed")
        
        # Test 4: Multiple file handling
        original_max_files = input_panel.max_files
        input_panel.set_max_files(5)
        
        assert input_panel.max_files == 5, "Max files setting should be updated"
        
        # Create multiple valid files
        files = [MockFile(f"test_{i}.jpg", 1024) for i in range(3)]
        
        # All should validate individually
        for i, file in enumerate(files):
            assert input_panel._validate_file(file) == True, f"File {i} should be valid"
        
        # Restore original max files
        input_panel.max_files = original_max_files
        
        print("✓ Multiple file handling consistency test passed")
        
        # Test 5: Attachment creation
        import io
        
        class MockFileWithData:
            def __init__(self, name: str, data: bytes, file_type: str):
                self.name = name
                self.type = file_type
                self._data = data
                self._position = 0
            
            def read(self):
                return self._data
            
            def seek(self, position):
                self._position = position
        
        test_data = b"fake_image_data_for_testing"
        mock_file = MockFileWithData("test.jpg", test_data, "image/jpeg")
        
        attachment = input_panel.create_attachment(mock_file)
        
        assert attachment is not None, "Attachment should be created for valid file"
        assert attachment.filename == "test.jpg", "Attachment filename should match"
        assert attachment.file_type == "image/jpeg", "Attachment file type should match"
        assert attachment.size == len(test_data), "Attachment size should match data length"
        assert attachment.data == test_data, "Attachment data should match original"
        assert attachment.id.startswith("att_"), "Attachment ID should have proper prefix"
        
        print("✓ Attachment creation consistency test passed")
        
        print("All file upload feedback tests passed!")
        return True
        
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_file_upload_feedback()
    sys.exit(0 if success else 1)