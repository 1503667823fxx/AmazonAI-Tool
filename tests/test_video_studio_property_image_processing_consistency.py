"""
Property-based tests for Video Studio image processing consistency

Tests that image processing maintains consistency across different formats and operations
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import tempfile
import asyncio
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any
from io import BytesIO

try:
    from app_utils.video_studio.asset_manager import AssetManager, ImageProcessingOptions, AssetType, AssetStatus
    from app_utils.video_studio.config import StorageConfig
    PIL_AVAILABLE = True
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        PIL_AVAILABLE = False
except ImportError as e:
    print(f"Failed to import required modules: {e}")
    sys.exit(1)


class ImageProcessingConsistencyTester:
    """Test class for image processing consistency property"""
    
    def __init__(self):
        """Initialize the tester with a temporary asset manager"""
        # Create temporary directory for testing
        self.temp_dir = tempfile.mkdtemp()
        
        # Create asset manager with temporary storage
        storage_config = StorageConfig(
            base_path=self.temp_dir,
            temp_path=os.path.join(self.temp_dir, "temp"),
            max_file_size_mb=50,
            max_storage_gb=1,
            allowed_image_formats=["jpg", "jpeg", "png", "webp"],
            allowed_video_formats=["mp4", "mov"],
            cleanup_interval_hours=24
        )
        
        self.asset_manager = AssetManager(storage_config)
        self.test_images = []
    
    def cleanup(self):
        """Clean up temporary files"""
        import shutil
        try:
            shutil.rmtree(self.temp_dir)
        except Exception as e:
            print(f"Warning: Failed to cleanup temp directory: {e}")
    
    def create_test_image(self, width: int, height: int, format: str = "PNG", color: str = "red") -> bytes:
        """Create a test image with specified dimensions and format"""
        if not PIL_AVAILABLE:
            # Return minimal PNG data if PIL not available
            return b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\tpHYs\x00\x00\x0b\x13\x00\x00\x0b\x13\x01\x00\x9a\x9c\x18\x00\x00\x00\nIDATx\x9cc\xf8\x00\x00\x00\x01\x00\x01\x00\x00\x00\x00IEND\xaeB`\x82'
        
        # Create image with PIL
        img = Image.new('RGB', (width, height), color)
        
        # Add some pattern to make it more realistic
        draw = ImageDraw.Draw(img)
        draw.rectangle([width//4, height//4, 3*width//4, 3*height//4], fill="blue")
        draw.ellipse([width//3, height//3, 2*width//3, 2*height//3], fill="green")
        
        # Save to bytes
        buffer = BytesIO()
        img.save(buffer, format=format, quality=85 if format.upper() == 'JPEG' else None)
        return buffer.getvalue()
    
    def get_supported_formats(self) -> List[str]:
        """Get list of supported image formats for testing"""
        return ["jpg", "png", "webp"]
    
    def get_test_dimensions(self) -> List[Tuple[int, int]]:
        """Get list of test dimensions"""
        return [
            (100, 100),    # Square small
            (200, 150),    # Landscape small
            (150, 200),    # Portrait small
            (800, 600),    # Landscape medium
            (600, 800),    # Portrait medium
            (1920, 1080),  # HD landscape
            (1080, 1920),  # HD portrait
            (1, 1),        # Minimal size
            (50, 25),      # Very small
        ]
    
    async def test_upload_consistency_across_formats(self) -> bool:
        """
        Test that image upload works consistently across all supported formats
        """
        print("Testing upload consistency across formats...")
        
        formats = self.get_supported_formats()
        test_dimensions = [(200, 150), (400, 300)]  # Use smaller images for format testing
        
        for width, height in test_dimensions:
            for fmt in formats:
                try:
                    # Create test image
                    image_data = self.create_test_image(width, height, fmt.upper())
                    filename = f"test_{width}x{height}.{fmt}"
                    
                    # Upload image
                    asset_id = await self.asset_manager.upload_image(image_data, filename)
                    
                    # Verify upload success
                    assert asset_id is not None, f"Upload failed for {filename}"
                    
                    # Get metadata
                    metadata = self.asset_manager.get_asset_metadata(asset_id)
                    assert metadata is not None, f"No metadata for {filename}"
                    assert metadata.status == AssetStatus.READY, f"Asset not ready for {filename}"
                    assert metadata.asset_type == AssetType.IMAGE, f"Wrong asset type for {filename}"
                    
                    # Verify dimensions are captured
                    if PIL_AVAILABLE:
                        assert metadata.width is not None, f"Width not captured for {filename}"
                        assert metadata.height is not None, f"Height not captured for {filename}"
                    
                    # Verify file exists
                    asset_url = self.asset_manager.get_asset_url(asset_id)
                    assert asset_url is not None, f"No asset URL for {filename}"
                    assert Path(asset_url).exists(), f"Asset file missing for {filename}"
                    
                    print(f"✓ Upload successful: {filename} -> {asset_id}")
                    
                except Exception as e:
                    print(f"✗ Upload failed for {filename}: {e}")
                    return False
        
        return True
    
    async def test_processing_consistency_across_dimensions(self) -> bool:
        """
        Test that image processing works consistently across different dimensions
        """
        print("Testing processing consistency across dimensions...")
        
        dimensions = self.get_test_dimensions()
        
        for width, height in dimensions:
            try:
                # Create test image
                image_data = self.create_test_image(width, height, "PNG")
                filename = f"test_{width}x{height}.png"
                
                # Test with different processing options
                processing_options = ImageProcessingOptions(
                    resize=(min(width * 2, 800), min(height * 2, 600)),
                    maintain_aspect_ratio=True,
                    auto_orient=True,
                    create_thumbnail=True
                )
                
                # Upload and process
                asset_id = await self.asset_manager.upload_image(image_data, filename, processing_options)
                
                # Verify processing success
                assert asset_id is not None, f"Processing failed for {filename}"
                
                metadata = self.asset_manager.get_asset_metadata(asset_id)
                assert metadata is not None, f"No metadata for processed {filename}"
                assert metadata.status == AssetStatus.READY, f"Processed asset not ready for {filename}"
                
                # Verify thumbnail creation
                if PIL_AVAILABLE and processing_options.create_thumbnail:
                    assert metadata.thumbnail_path is not None, f"No thumbnail for {filename}"
                    assert Path(metadata.thumbnail_path).exists(), f"Thumbnail file missing for {filename}"
                
                print(f"✓ Processing successful: {filename} -> {asset_id}")
                
            except Exception as e:
                print(f"✗ Processing failed for {filename}: {e}")
                return False
        
        return True
    
    async def test_resize_maintains_aspect_ratio(self) -> bool:
        """
        Test that resize operations maintain aspect ratio when requested
        """
        print("Testing aspect ratio maintenance during resize...")
        
        test_cases = [
            (400, 300, (200, 150)),  # Exact scale down
            (100, 200, (50, 100)),   # Portrait scale down
            (300, 100, (150, 50)),   # Landscape scale down
            (50, 50, (100, 100)),    # Square scale up
        ]
        
        for orig_w, orig_h, target_size in test_cases:
            try:
                # Create test image
                image_data = self.create_test_image(orig_w, orig_h, "PNG")
                filename = f"aspect_test_{orig_w}x{orig_h}.png"
                
                # Upload with resize
                processing_options = ImageProcessingOptions(
                    resize=target_size,
                    maintain_aspect_ratio=True
                )
                
                asset_id = await self.asset_manager.upload_image(image_data, filename, processing_options)
                
                # Verify aspect ratio maintenance
                metadata = self.asset_manager.get_asset_metadata(asset_id)
                assert metadata is not None, f"No metadata for {filename}"
                
                if PIL_AVAILABLE and metadata.width and metadata.height:
                    original_ratio = orig_w / orig_h
                    processed_ratio = metadata.width / metadata.height
                    
                    # Allow small floating point differences
                    ratio_diff = abs(original_ratio - processed_ratio)
                    assert ratio_diff < 0.01, f"Aspect ratio not maintained for {filename}: {original_ratio} vs {processed_ratio}"
                
                print(f"✓ Aspect ratio maintained: {filename}")
                
            except Exception as e:
                print(f"✗ Aspect ratio test failed for {filename}: {e}")
                return False
        
        return True
    
    async def test_quality_consistency(self) -> bool:
        """
        Test that image quality settings are applied consistently
        """
        print("Testing quality consistency...")
        
        # Test different quality settings
        quality_levels = [50, 75, 85, 95]
        
        for quality in quality_levels:
            try:
                # Create test image
                image_data = self.create_test_image(400, 300, "JPEG")
                filename = f"quality_test_{quality}.jpg"
                
                # Upload with specific quality
                processing_options = ImageProcessingOptions(
                    quality=quality,
                    optimize=True
                )
                
                asset_id = await self.asset_manager.upload_image(image_data, filename, processing_options)
                
                # Verify upload success
                metadata = self.asset_manager.get_asset_metadata(asset_id)
                assert metadata is not None, f"No metadata for quality test {quality}"
                assert metadata.status == AssetStatus.READY, f"Asset not ready for quality {quality}"
                
                # Verify file exists and has reasonable size
                asset_path = Path(metadata.file_path)
                assert asset_path.exists(), f"Asset file missing for quality {quality}"
                
                file_size = asset_path.stat().st_size
                assert file_size > 0, f"Empty file for quality {quality}"
                
                print(f"✓ Quality {quality} processed successfully: {file_size} bytes")
                
            except Exception as e:
                print(f"✗ Quality test failed for {quality}: {e}")
                return False
        
        return True
    
    async def test_error_handling_consistency(self) -> bool:
        """
        Test that error handling is consistent for invalid inputs
        """
        print("Testing error handling consistency...")
        
        # Test invalid file formats
        invalid_formats = ["txt", "exe", "pdf"]
        
        for fmt in invalid_formats:
            try:
                filename = f"invalid.{fmt}"
                image_data = b"invalid image data"
                
                # This should raise an exception
                try:
                    asset_id = await self.asset_manager.upload_image(image_data, filename)
                    # If we get here, the test failed
                    assert False, f"Invalid format {fmt} was accepted"
                except (ValueError, RuntimeError) as e:
                    # Expected error
                    assert "format" in str(e).lower() or "unsupported" in str(e).lower(), f"Unexpected error message for {fmt}: {e}"
                    print(f"✓ Invalid format {fmt} correctly rejected")
                
            except AssertionError:
                raise
            except Exception as e:
                print(f"✗ Error handling test failed for {fmt}: {e}")
                return False
        
        # Test oversized files
        try:
            # Create a filename that would exceed size limits
            filename = "oversized.jpg"
            oversized_data = b"x" * (100 * 1024 * 1024)  # 100MB
            
            try:
                asset_id = await self.asset_manager.upload_image(oversized_data, filename)
                assert False, "Oversized file was accepted"
            except (ValueError, RuntimeError) as e:
                assert "size" in str(e).lower(), f"Unexpected error for oversized file: {e}"
                print("✓ Oversized file correctly rejected")
                
        except AssertionError:
            raise
        except Exception as e:
            print(f"✗ Oversized file test failed: {e}")
            return False
        
        return True
    
    async def test_concurrent_processing_consistency(self) -> bool:
        """
        Test that concurrent image processing maintains consistency
        """
        print("Testing concurrent processing consistency...")
        
        # Create multiple images for concurrent processing
        concurrent_tasks = []
        
        for i in range(5):
            image_data = self.create_test_image(200 + i * 50, 150 + i * 30, "PNG")
            filename = f"concurrent_test_{i}.png"
            
            # Create upload task
            task = self.asset_manager.upload_image(image_data, filename)
            concurrent_tasks.append((task, filename))
        
        # Execute all tasks concurrently
        try:
            results = await asyncio.gather(*[task for task, _ in concurrent_tasks], return_exceptions=True)
            
            # Verify all uploads succeeded
            for i, (result, (_, filename)) in enumerate(zip(results, concurrent_tasks)):
                if isinstance(result, Exception):
                    print(f"✗ Concurrent upload failed for {filename}: {result}")
                    return False
                
                # Verify asset was created
                asset_id = result
                metadata = self.asset_manager.get_asset_metadata(asset_id)
                assert metadata is not None, f"No metadata for concurrent upload {filename}"
                assert metadata.status == AssetStatus.READY, f"Asset not ready for concurrent upload {filename}"
                
                print(f"✓ Concurrent upload successful: {filename} -> {asset_id}")
            
            return True
            
        except Exception as e:
            print(f"✗ Concurrent processing test failed: {e}")
            return False


async def test_image_processing_consistency():
    """
    **Feature: video-studio-redesign, Property 1: 图片处理一致性**
    **Validates: Requirements 1.1, 6.2**
    
    Property: For any valid image file (JPG, PNG, WebP formats), the system should 
    successfully upload, preprocess, and intelligently crop and scale according to 
    target dimensions while maintaining image quality and proportions
    """
    print("=" * 70)
    print("Testing Property 1: Image Processing Consistency")
    print("=" * 70)
    
    tester = ImageProcessingConsistencyTester()
    
    try:
        # Run all consistency tests
        tests = [
            ("Upload consistency across formats", tester.test_upload_consistency_across_formats()),
            ("Processing consistency across dimensions", tester.test_processing_consistency_across_dimensions()),
            ("Aspect ratio maintenance", tester.test_resize_maintains_aspect_ratio()),
            ("Quality consistency", tester.test_quality_consistency()),
            ("Error handling consistency", tester.test_error_handling_consistency()),
            ("Concurrent processing consistency", tester.test_concurrent_processing_consistency()),
        ]
        
        all_passed = True
        
        for test_name, test_coro in tests:
            print(f"\n--- {test_name} ---")
            try:
                result = await test_coro
                if result:
                    print(f"✅ {test_name} PASSED")
                else:
                    print(f"❌ {test_name} FAILED")
                    all_passed = False
            except Exception as e:
                print(f"💥 {test_name} ERROR: {e}")
                import traceback
                traceback.print_exc()
                all_passed = False
        
        return all_passed
        
    finally:
        # Always cleanup
        tester.cleanup()


def run_all_property_tests():
    """Run all property-based tests for image processing consistency"""
    print("Running Property-Based Tests for Video Studio Image Processing Consistency")
    print("=" * 75)
    
    try:
        # Run the main property test
        success = asyncio.run(test_image_processing_consistency())
        
        if success:
            print("\n" + "=" * 75)
            print("✅ All property tests PASSED!")
            print("Property 1: 图片处理一致性 - VALIDATED")
            print("Requirements 1.1, 6.2 - SATISFIED")
            return True
        else:
            print("\n" + "=" * 75)
            print("❌ Some property tests FAILED!")
            return False
            
    except Exception as e:
        print(f"\n💥 Property test ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_property_tests()
    exit(0 if success else 1)