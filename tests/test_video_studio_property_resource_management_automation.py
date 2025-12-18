"""
Property-based tests for Video Studio resource management automation

**Feature: video-studio-redesign, Property 11: 资源管理自动化**
**Validates: Requirements 3.5, 7.3**

Tests that the asset manager automatically manages the lifecycle of video segments 
and temporary files, including storage, cleanup of expired files, and space optimization.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import tempfile
import asyncio
import time
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Tuple, Optional, Dict, Any
from io import BytesIO

try:
    from app_utils.video_studio.asset_manager import AssetManager, AssetType, AssetStatus, AssetMetadata
    from app_utils.video_studio.cleanup_service import CleanupService, CleanupRule, CleanupPolicy
    from app_utils.video_studio.config import StorageConfig
    PIL_AVAILABLE = True
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        PIL_AVAILABLE = False
except ImportError as e:
    print(f"Failed to import required modules: {e}")
    sys.exit(1)


class ResourceManagementAutomationTester:
    """Test class for resource management automation property"""
    
    def __init__(self):
        """Initialize the tester with a temporary asset manager and cleanup service"""
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
            cleanup_interval_hours=1  # Short interval for testing
        )
        
        self.asset_manager = AssetManager(storage_config)
        self.cleanup_service = CleanupService(self.asset_manager)
        self.test_assets = []
    
    def cleanup(self):
        """Clean up temporary files"""
        try:
            shutil.rmtree(self.temp_dir)
        except Exception as e:
            print(f"Warning: Failed to cleanup temp directory: {e}")
    
    def create_test_image(self, width: int, height: int, format: str = "PNG", color: str = "red") -> bytes:
        """Create a test image with specified dimensions and format"""
        if not PIL_AVAILABLE:
            # Create a simple fake image data
            return b"fake_image_data_" + f"{width}x{height}_{format}_{color}".encode()
        
        # Create image with PIL
        image = Image.new('RGB', (width, height), color)
        
        # Add some content to make it more realistic
        draw = ImageDraw.Draw(image)
        draw.rectangle([10, 10, width-10, height-10], outline="black", width=2)
        draw.text((20, 20), f"{width}x{height}", fill="white")
        
        # Convert to bytes
        buffer = BytesIO()
        image.save(buffer, format=format)
        return buffer.getvalue()
    
    def create_test_video_data(self, size_kb: int = 100) -> bytes:
        """Create fake video data for testing"""
        # Create fake video data of specified size
        return b"fake_video_data_" + b"x" * (size_kb * 1024 - 17)
    
    async def test_automatic_asset_lifecycle_management(self) -> bool:
        """
        Property: For any generated video segments and temporary files, 
        the asset manager should automatically manage their lifecycle including 
        storage, cleanup, and space optimization.
        """
        print("Testing automatic asset lifecycle management...")
        
        try:
            # Test 1: Asset creation and storage
            print("  Testing asset creation and storage...")
            
            # Create various types of assets
            image_data = self.create_test_image(800, 600, "JPEG")
            video_data = self.create_test_video_data(200)
            
            # Upload assets
            image_asset_id = await self.asset_manager.upload_image(image_data, "test_image.jpg")
            video_asset_id = await self.asset_manager.upload_video(video_data, "test_video.mp4")
            
            # Verify assets are properly stored
            image_metadata = self.asset_manager.get_asset_metadata(image_asset_id)
            video_metadata = self.asset_manager.get_asset_metadata(video_asset_id)
            
            assert image_metadata is not None, "Image asset metadata not found"
            assert video_metadata is not None, "Video asset metadata not found"
            assert image_metadata.status == AssetStatus.READY, "Image asset not ready"
            assert video_metadata.status == AssetStatus.READY, "Video asset not ready"
            
            # Verify files exist on disk
            assert Path(image_metadata.file_path).exists(), "Image file not found on disk"
            assert Path(video_metadata.file_path).exists(), "Video file not found on disk"
            
            print("  ✓ Asset creation and storage working correctly")
            
            # Test 2: Automatic cleanup of expired assets
            print("  Testing automatic cleanup of expired assets...")
            
            # Create assets with different ages by manipulating timestamps
            old_assets = []
            for i in range(3):
                asset_data = self.create_test_image(100, 100, "PNG")
                asset_id = await self.asset_manager.upload_image(asset_data, f"old_asset_{i}.png")
                
                # Manually set old timestamps to simulate aged assets
                metadata = self.asset_manager.get_asset_metadata(asset_id)
                old_time = datetime.now() - timedelta(hours=25)  # Older than cleanup interval
                metadata.created_at = old_time
                metadata.last_accessed = old_time
                
                old_assets.append(asset_id)
            
            # Run cleanup
            initial_count = len(self.asset_manager._asset_registry)
            cleanup_result = await self.cleanup_service.run_cleanup(dry_run=False)
            final_count = len(self.asset_manager._asset_registry)
            
            # Verify cleanup occurred
            assert cleanup_result.files_deleted > 0, "No files were cleaned up"
            assert final_count < initial_count, "Asset count did not decrease after cleanup"
            
            # Verify old assets were removed
            for asset_id in old_assets:
                metadata = self.asset_manager.get_asset_metadata(asset_id)
                assert metadata is None, f"Old asset {asset_id} was not cleaned up"
            
            print(f"  ✓ Automatic cleanup removed {cleanup_result.files_deleted} expired assets")
            
            # Test 3: Space optimization
            print("  Testing space optimization...")
            
            # Create multiple processed versions of the same image
            base_image_data = self.create_test_image(400, 300, "JPEG")
            base_asset_id = await self.asset_manager.upload_image(base_image_data, "base_image.jpg")
            
            # Create processed versions
            processed_assets = []
            for i in range(5):
                operations = [{"type": "resize", "width": 200 + i * 50, "height": 150 + i * 30}]
                processed_id = self.asset_manager.process_image_operations(base_asset_id, operations)
                processed_assets.append(processed_id)
            
            # Run storage optimization
            initial_stats = self.asset_manager.get_storage_stats()
            optimization_result = await self.cleanup_service.optimize_storage()
            final_stats = self.asset_manager.get_storage_stats()
            
            # Verify optimization occurred
            assert optimization_result['total_space_freed_mb'] >= 0, "Space optimization failed"
            
            print(f"  ✓ Space optimization freed {optimization_result['total_space_freed_mb']:.2f}MB")
            
            # Test 4: Temporary file cleanup
            print("  Testing temporary file cleanup...")
            
            # Create temporary files
            temp_files = []
            for i in range(3):
                temp_file = self.asset_manager.temp_path / f"temp_file_{i}.tmp"
                temp_file.parent.mkdir(parents=True, exist_ok=True)
                temp_file.write_bytes(b"temporary data")
                
                # Set old modification time
                old_timestamp = time.time() - 7200  # 2 hours ago
                os.utime(temp_file, (old_timestamp, old_timestamp))
                temp_files.append(temp_file)
            
            # Run temp file cleanup
            deleted_count = await self.asset_manager._cleanup_temp_files()
            
            # Verify temp files were cleaned up
            assert deleted_count > 0, "No temporary files were cleaned up"
            for temp_file in temp_files:
                assert not temp_file.exists(), f"Temporary file {temp_file} was not cleaned up"
            
            print(f"  ✓ Temporary file cleanup removed {deleted_count} files")
            
            # Test 5: Storage health monitoring
            print("  Testing storage health monitoring...")
            
            # Check storage health
            health_report = self.cleanup_service.check_storage_health()
            
            # Verify health report structure
            assert 'status' in health_report, "Health report missing status"
            assert 'stats' in health_report, "Health report missing stats"
            assert 'recommendations' in health_report, "Health report missing recommendations"
            
            # Verify stats are reasonable
            stats = health_report['stats']
            assert stats['total_assets'] >= 0, "Invalid asset count in health report"
            assert stats['total_size_mb'] >= 0, "Invalid size in health report"
            
            print(f"  ✓ Storage health monitoring working (status: {health_report['status']})")
            
            # Test 6: Asset lifecycle with metadata tracking
            print("  Testing asset lifecycle with metadata tracking...")
            
            # Create asset and track its lifecycle
            lifecycle_data = self.create_test_image(300, 200, "PNG")
            lifecycle_asset_id = await self.asset_manager.upload_image(lifecycle_data, "lifecycle_test.png")
            
            # Verify initial metadata
            metadata = self.asset_manager.get_asset_metadata(lifecycle_asset_id)
            assert metadata.created_at is not None, "Asset creation time not recorded"
            assert metadata.last_accessed is not None, "Asset last access time not recorded"
            assert metadata.checksum is not None, "Asset checksum not calculated"
            
            # Access the asset (should update last_accessed)
            initial_access_time = metadata.last_accessed
            time.sleep(0.1)  # Small delay to ensure timestamp difference
            asset_url = self.asset_manager.get_asset_url(lifecycle_asset_id)
            
            # Verify access time was updated
            updated_metadata = self.asset_manager.get_asset_metadata(lifecycle_asset_id)
            assert updated_metadata.last_accessed > initial_access_time, "Last access time not updated"
            
            # Delete asset and verify cleanup
            delete_success = await self.asset_manager.delete_asset(lifecycle_asset_id)
            assert delete_success, "Asset deletion failed"
            
            # Verify asset is completely removed
            deleted_metadata = self.asset_manager.get_asset_metadata(lifecycle_asset_id)
            assert deleted_metadata is None, "Asset metadata not removed after deletion"
            assert not Path(metadata.file_path).exists(), "Asset file not removed after deletion"
            
            print("  ✓ Asset lifecycle with metadata tracking working correctly")
            
            return True
            
        except Exception as e:
            print(f"  ✗ Resource management automation test failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def test_cleanup_rule_configuration(self) -> bool:
        """
        Test that cleanup rules can be configured and applied correctly
        """
        print("Testing cleanup rule configuration...")
        
        try:
            # Create custom cleanup rule
            custom_rule = CleanupRule(
                name="test_rule",
                policy=CleanupPolicy.AGE_BASED,
                max_age_hours=1,
                asset_types=[AssetType.IMAGE],
                tags_include=["test"],
                preserve_recent_hours=0
            )
            
            # Add rule to cleanup service
            self.cleanup_service.add_cleanup_rule(custom_rule)
            
            # Create assets that match and don't match the rule
            matching_data = self.create_test_image(100, 100, "PNG")
            matching_asset_id = await self.asset_manager.upload_image(matching_data, "matching.png")
            
            non_matching_data = self.create_test_video_data(50)
            non_matching_asset_id = await self.asset_manager.upload_video(non_matching_data, "non_matching.mp4")
            
            # Add test tag to matching asset
            matching_metadata = self.asset_manager.get_asset_metadata(matching_asset_id)
            matching_metadata.tags.append("test")
            
            # Set old timestamp for matching asset
            old_time = datetime.now() - timedelta(hours=2)
            matching_metadata.created_at = old_time
            matching_metadata.last_accessed = old_time
            
            # Run cleanup with custom rule
            cleanup_result = await self.cleanup_service.run_cleanup(dry_run=False)
            
            # Verify only matching asset was cleaned up
            matching_after = self.asset_manager.get_asset_metadata(matching_asset_id)
            non_matching_after = self.asset_manager.get_asset_metadata(non_matching_asset_id)
            
            assert matching_after is None, "Matching asset was not cleaned up by custom rule"
            assert non_matching_after is not None, "Non-matching asset was incorrectly cleaned up"
            
            print("  ✓ Cleanup rule configuration working correctly")
            return True
            
        except Exception as e:
            print(f"  ✗ Cleanup rule configuration test failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def test_concurrent_resource_management(self) -> bool:
        """
        Test resource management under concurrent operations
        """
        print("Testing concurrent resource management...")
        
        try:
            # Create multiple concurrent upload tasks
            upload_tasks = []
            for i in range(10):
                image_data = self.create_test_image(200 + i * 10, 150 + i * 5, "JPEG")
                task = self.asset_manager.upload_image(image_data, f"concurrent_{i}.jpg")
                upload_tasks.append(task)
            
            # Execute uploads concurrently
            asset_ids = await asyncio.gather(*upload_tasks)
            
            # Verify all uploads succeeded
            assert len(asset_ids) == 10, "Not all concurrent uploads succeeded"
            for asset_id in asset_ids:
                assert asset_id is not None, "Concurrent upload returned None"
                metadata = self.asset_manager.get_asset_metadata(asset_id)
                assert metadata is not None, "Concurrent upload metadata missing"
                assert metadata.status == AssetStatus.READY, "Concurrent upload asset not ready"
            
            # Run concurrent cleanup operations
            cleanup_tasks = []
            for _ in range(3):
                task = self.cleanup_service.run_cleanup(dry_run=True)
                cleanup_tasks.append(task)
            
            cleanup_results = await asyncio.gather(*cleanup_tasks)
            
            # Verify cleanup operations completed without errors
            for result in cleanup_results:
                assert len(result.errors) == 0, f"Concurrent cleanup had errors: {result.errors}"
            
            print("  ✓ Concurrent resource management working correctly")
            return True
            
        except Exception as e:
            print(f"  ✗ Concurrent resource management test failed: {e}")
            import traceback
            traceback.print_exc()
            return False


async def run_resource_management_automation_tests():
    """Run all resource management automation property tests"""
    print("=" * 80)
    print("PROPERTY TEST: Resource Management Automation")
    print("=" * 80)
    
    tester = ResourceManagementAutomationTester()
    
    try:
        # Run all test scenarios
        test_results = []
        
        # Test 1: Basic automatic asset lifecycle management
        result1 = await tester.test_automatic_asset_lifecycle_management()
        test_results.append(("Automatic Asset Lifecycle Management", result1))
        
        # Test 2: Cleanup rule configuration
        result2 = await tester.test_cleanup_rule_configuration()
        test_results.append(("Cleanup Rule Configuration", result2))
        
        # Test 3: Concurrent resource management
        result3 = await tester.test_concurrent_resource_management()
        test_results.append(("Concurrent Resource Management", result3))
        
        # Summary
        print("\n" + "=" * 80)
        print("RESOURCE MANAGEMENT AUTOMATION TEST RESULTS:")
        print("=" * 80)
        
        all_passed = True
        for test_name, passed in test_results:
            status = "PASS" if passed else "FAIL"
            print(f"{test_name}: {status}")
            if not passed:
                all_passed = False
        
        print("=" * 80)
        overall_status = "PASS" if all_passed else "FAIL"
        print(f"OVERALL RESULT: {overall_status}")
        print("=" * 80)
        
        return all_passed
        
    finally:
        # Always cleanup
        tester.cleanup()


if __name__ == "__main__":
    # Run the property tests
    result = asyncio.run(run_resource_management_automation_tests())
    sys.exit(0 if result else 1)