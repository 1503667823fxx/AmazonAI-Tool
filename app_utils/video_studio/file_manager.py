"""
File Manager for Video Studio

This module provides a simplified interface to the AssetManager for backward compatibility
and common file operations.
"""

from typing import Optional, List, Dict, Any, Union, BinaryIO
from pathlib import Path
import asyncio

from .asset_manager import AssetManager, AssetType, AssetStatus, ImageProcessingOptions
from .config import get_config


class FileManager:
    """
    Simplified file management interface for Video Studio.
    
    This class provides a backward-compatible interface to the new AssetManager
    while maintaining the existing API for file operations.
    """
    
    def __init__(self):
        """Initialize FileManager with AssetManager"""
        self.asset_manager = AssetManager()
    
    async def upload_file(self, file_data: Union[bytes, BinaryIO], filename: str) -> str:
        """
        Upload a file (image or video) and return asset ID.
        
        Args:
            file_data: File data
            filename: Original filename
            
        Returns:
            Asset ID of uploaded file
        """
        # Determine file type and route to appropriate method
        ext = Path(filename).suffix.lower().lstrip('.')
        
        if ext in self.asset_manager.supported_image_formats:
            return await self.asset_manager.upload_image(file_data, filename)
        elif ext in self.asset_manager.supported_video_formats:
            return await self.asset_manager.upload_video(file_data, filename)
        else:
            raise ValueError(f"Unsupported file format: {ext}")
    
    def get_file_path(self, asset_id: str) -> Optional[str]:
        """
        Get file path for an asset.
        
        Args:
            asset_id: Asset ID
            
        Returns:
            File path or None if not found
        """
        return self.asset_manager.get_asset_url(asset_id)
    
    def get_file_info(self, asset_id: str) -> Optional[Dict[str, Any]]:
        """
        Get file information.
        
        Args:
            asset_id: Asset ID
            
        Returns:
            File information dictionary or None if not found
        """
        metadata = self.asset_manager.get_asset_metadata(asset_id)
        if not metadata:
            return None
        
        return {
            'asset_id': metadata.asset_id,
            'filename': metadata.original_filename,
            'file_size': metadata.file_size,
            'mime_type': metadata.mime_type,
            'created_at': metadata.created_at.isoformat(),
            'file_path': metadata.file_path,
            'thumbnail_path': metadata.thumbnail_path,
            'width': metadata.width,
            'height': metadata.height,
            'duration': metadata.duration,
            'status': metadata.status.value
        }
    
    def list_files(self, file_type: Optional[str] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        List uploaded files.
        
        Args:
            file_type: Filter by file type ('image', 'video', or None for all)
            limit: Maximum number of results
            
        Returns:
            List of file information dictionaries
        """
        asset_type = None
        if file_type == 'image':
            asset_type = AssetType.IMAGE
        elif file_type == 'video':
            asset_type = AssetType.VIDEO
        
        assets = self.asset_manager.list_assets(
            asset_type=asset_type,
            status=AssetStatus.READY,
            limit=limit
        )
        
        return [
            {
                'asset_id': asset.asset_id,
                'filename': asset.original_filename,
                'file_size': asset.file_size,
                'mime_type': asset.mime_type,
                'created_at': asset.created_at.isoformat(),
                'file_path': asset.file_path,
                'thumbnail_path': asset.thumbnail_path,
                'width': asset.width,
                'height': asset.height,
                'duration': asset.duration,
                'status': asset.status.value
            }
            for asset in assets
        ]
    
    async def delete_file(self, asset_id: str) -> bool:
        """
        Delete a file.
        
        Args:
            asset_id: Asset ID to delete
            
        Returns:
            True if successfully deleted
        """
        return await self.asset_manager.delete_asset(asset_id)
    
    def validate_file(self, filename: str, file_size: int) -> tuple[bool, Optional[str]]:
        """
        Validate file for upload.
        
        Args:
            filename: Filename to validate
            file_size: File size in bytes
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        return self.asset_manager.validate_file_upload(filename, file_size)
    
    def get_storage_info(self) -> Dict[str, Any]:
        """
        Get storage information and statistics.
        
        Returns:
            Storage information dictionary
        """
        return self.asset_manager.get_storage_stats()
    
    async def cleanup_old_files(self, max_age_hours: int = 24) -> int:
        """
        Clean up old files.
        
        Args:
            max_age_hours: Maximum age in hours
            
        Returns:
            Number of files cleaned up
        """
        return await self.asset_manager.cleanup_expired_assets(max_age_hours)
    
    def process_image(self, asset_id: str, operations: List[Dict[str, Any]]) -> str:
        """
        Process an image with specified operations.
        
        Args:
            asset_id: Source image asset ID
            operations: List of operations to apply
            
        Returns:
            Asset ID of processed image
        """
        return self.asset_manager.process_image_operations(asset_id, operations)
    
    async def resize_image(self, asset_id: str, width: int, height: int, 
                          maintain_aspect_ratio: bool = True) -> str:
        """
        Resize an image.
        
        Args:
            asset_id: Source image asset ID
            width: Target width
            height: Target height
            maintain_aspect_ratio: Whether to maintain aspect ratio
            
        Returns:
            Asset ID of resized image
        """
        operations = [{
            'type': 'resize',
            'width': width,
            'height': height,
            'maintain_aspect_ratio': maintain_aspect_ratio
        }]
        
        return self.process_image(asset_id, operations)
    
    async def crop_image(self, asset_id: str, left: int, top: int, 
                        right: int, bottom: int) -> str:
        """
        Crop an image.
        
        Args:
            asset_id: Source image asset ID
            left: Left coordinate
            top: Top coordinate
            right: Right coordinate
            bottom: Bottom coordinate
            
        Returns:
            Asset ID of cropped image
        """
        operations = [{
            'type': 'crop',
            'left': left,
            'top': top,
            'right': right,
            'bottom': bottom
        }]
        
        return self.process_image(asset_id, operations)


# Global file manager instance for backward compatibility
_file_manager = None


def get_file_manager() -> FileManager:
    """Get global FileManager instance"""
    global _file_manager
    if _file_manager is None:
        _file_manager = FileManager()
    return _file_manager


# Convenience functions for common operations
async def upload_file(file_data: Union[bytes, BinaryIO], filename: str) -> str:
    """Upload a file and return asset ID"""
    return await get_file_manager().upload_file(file_data, filename)


def get_file_path(asset_id: str) -> Optional[str]:
    """Get file path for asset ID"""
    return get_file_manager().get_file_path(asset_id)


def get_file_info(asset_id: str) -> Optional[Dict[str, Any]]:
    """Get file information for asset ID"""
    return get_file_manager().get_file_info(asset_id)


def list_files(file_type: Optional[str] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """List uploaded files"""
    return get_file_manager().list_files(file_type, limit)


async def delete_file(asset_id: str) -> bool:
    """Delete a file"""
    return await get_file_manager().delete_file(asset_id)


def validate_file(filename: str, file_size: int) -> tuple[bool, Optional[str]]:
    """Validate file for upload"""
    return get_file_manager().validate_file(filename, file_size)


def get_storage_info() -> Dict[str, Any]:
    """Get storage information"""
    return get_file_manager().get_storage_info()


async def cleanup_old_files(max_age_hours: int = 24) -> int:
    """Clean up old files"""
    return await get_file_manager().cleanup_old_files(max_age_hours)