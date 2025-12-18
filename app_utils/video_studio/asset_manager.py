"""
Asset Management System for Video Studio

This module provides comprehensive asset management functionality including:
- Image upload, validation, and preprocessing
- Video resource management and storage
- Automatic cleanup and space optimization
- Asset lifecycle management
"""

import os
import uuid
import hashlib
import shutil
import asyncio

try:
    import aiofiles
    AIOFILES_AVAILABLE = True
except ImportError:
    AIOFILES_AVAILABLE = False
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union, BinaryIO
from dataclasses import dataclass, field
from enum import Enum
import json
import logging

try:
    from PIL import Image, ImageOps, ImageFilter
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    import cv2
    import numpy as np
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

from .config import get_config, StorageConfig
from .models import TaskStatus
from .error_handler import VideoStudioErrorHandler


class AssetType(Enum):
    """Types of assets supported by the system"""
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    DOCUMENT = "document"
    TEMP = "temp"


class AssetStatus(Enum):
    """Asset processing status"""
    UPLOADING = "uploading"
    PROCESSING = "processing"
    READY = "ready"
    ERROR = "error"
    EXPIRED = "expired"


@dataclass
class AssetMetadata:
    """Metadata for asset files"""
    asset_id: str
    original_filename: str
    asset_type: AssetType
    file_size: int
    mime_type: str
    created_at: datetime
    last_accessed: datetime
    status: AssetStatus
    file_path: str
    thumbnail_path: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    duration: Optional[float] = None
    checksum: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, any]:
        """Convert metadata to dictionary for serialization"""
        return {
            "asset_id": self.asset_id,
            "original_filename": self.original_filename,
            "asset_type": self.asset_type.value,
            "file_size": self.file_size,
            "mime_type": self.mime_type,
            "created_at": self.created_at.isoformat(),
            "last_accessed": self.last_accessed.isoformat(),
            "status": self.status.value,
            "file_path": self.file_path,
            "thumbnail_path": self.thumbnail_path,
            "width": self.width,
            "height": self.height,
            "duration": self.duration,
            "checksum": self.checksum,
            "tags": self.tags,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, any]) -> 'AssetMetadata':
        """Create AssetMetadata from dictionary"""
        return cls(
            asset_id=data["asset_id"],
            original_filename=data["original_filename"],
            asset_type=AssetType(data["asset_type"]),
            file_size=data["file_size"],
            mime_type=data["mime_type"],
            created_at=datetime.fromisoformat(data["created_at"]),
            last_accessed=datetime.fromisoformat(data["last_accessed"]),
            status=AssetStatus(data["status"]),
            file_path=data["file_path"],
            thumbnail_path=data.get("thumbnail_path"),
            width=data.get("width"),
            height=data.get("height"),
            duration=data.get("duration"),
            checksum=data.get("checksum"),
            tags=data.get("tags", []),
            metadata=data.get("metadata", {})
        )


@dataclass
class ImageProcessingOptions:
    """Options for image processing operations"""
    resize: Optional[Tuple[int, int]] = None
    crop: Optional[Tuple[int, int, int, int]] = None  # (left, top, right, bottom)
    quality: int = 85
    format: Optional[str] = None
    maintain_aspect_ratio: bool = True
    auto_orient: bool = True
    optimize: bool = True
    create_thumbnail: bool = True
    thumbnail_size: Tuple[int, int] = (256, 256)


class AssetManager:
    """
    Comprehensive asset management system for Video Studio.
    
    Handles upload, processing, storage, and lifecycle management of all asset types
    including images, videos, and temporary files.
    """
    
    def __init__(self, storage_config: Optional[StorageConfig] = None):
        """Initialize AssetManager with configuration"""
        self.config = storage_config or get_config().storage
        self.error_handler = VideoStudioErrorHandler()
        self.logger = logging.getLogger(__name__)
        
        # Initialize storage directories
        self.base_path = Path(self.config.base_path)
        self.temp_path = Path(self.config.temp_path)
        self.metadata_path = self.base_path / "metadata"
        
        # Create directory structure
        self._initialize_directories()
        
        # Asset registry for in-memory tracking
        self._asset_registry: Dict[str, AssetMetadata] = {}
        self._load_asset_registry()
        
        # Supported formats
        self.supported_image_formats = set(self.config.allowed_image_formats)
        self.supported_video_formats = set(self.config.allowed_video_formats)
        
        # MIME type mappings
        self.mime_mappings = {
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'png': 'image/png',
            'webp': 'image/webp',
            'gif': 'image/gif',
            'mp4': 'video/mp4',
            'mov': 'video/quicktime',
            'avi': 'video/x-msvideo',
            'mkv': 'video/x-matroska'
        }
    
    def _initialize_directories(self) -> None:
        """Create necessary directory structure"""
        directories = [
            self.base_path,
            self.temp_path,
            self.metadata_path,
            self.base_path / "images",
            self.base_path / "videos",
            self.base_path / "thumbnails",
            self.base_path / "processed"
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
    
    def _load_asset_registry(self) -> None:
        """Load asset registry from metadata files"""
        try:
            registry_file = self.metadata_path / "registry.json"
            if registry_file.exists():
                with open(registry_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for asset_id, metadata_dict in data.items():
                        self._asset_registry[asset_id] = AssetMetadata.from_dict(metadata_dict)
        except Exception as e:
            self.logger.warning(f"Failed to load asset registry: {e}")
            self._asset_registry = {}
    
    def _save_asset_registry(self) -> None:
        """Save asset registry to metadata file"""
        try:
            registry_file = self.metadata_path / "registry.json"
            data = {
                asset_id: metadata.to_dict() 
                for asset_id, metadata in self._asset_registry.items()
            }
            with open(registry_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"Failed to save asset registry: {e}")
    
    def _generate_asset_id(self) -> str:
        """Generate unique asset ID"""
        return str(uuid.uuid4())
    
    def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate MD5 checksum of file"""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    
    def _get_file_extension(self, filename: str) -> str:
        """Get file extension in lowercase"""
        return Path(filename).suffix.lower().lstrip('.')
    
    def _get_mime_type(self, filename: str) -> str:
        """Get MIME type from filename"""
        ext = self._get_file_extension(filename)
        return self.mime_mappings.get(ext, 'application/octet-stream')
    
    def _determine_asset_type(self, filename: str) -> AssetType:
        """Determine asset type from filename"""
        ext = self._get_file_extension(filename)
        
        if ext in self.supported_image_formats:
            return AssetType.IMAGE
        elif ext in self.supported_video_formats:
            return AssetType.VIDEO
        else:
            return AssetType.DOCUMENT
    
    def validate_file_upload(self, filename: str, file_size: int) -> Tuple[bool, Optional[str]]:
        """
        Validate file for upload.
        
        Args:
            filename: Name of the file
            file_size: Size of the file in bytes
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check file size
        max_size_bytes = self.config.max_file_size_mb * 1024 * 1024
        if file_size > max_size_bytes:
            return False, f"File size ({file_size / 1024 / 1024:.1f}MB) exceeds maximum allowed size ({self.config.max_file_size_mb}MB)"
        
        # Check file extension
        ext = self._get_file_extension(filename)
        if not ext:
            return False, "File must have a valid extension"
        
        all_supported = self.supported_image_formats | self.supported_video_formats
        if ext not in all_supported:
            return False, f"Unsupported file format: {ext}. Supported formats: {', '.join(sorted(all_supported))}"
        
        # Check filename
        if not filename or len(filename) > 255:
            return False, "Invalid filename"
        
        return True, None
    
    async def upload_image(self, file_data: Union[bytes, BinaryIO], filename: str, 
                          processing_options: Optional[ImageProcessingOptions] = None) -> str:
        """
        Upload and process an image file.
        
        Args:
            file_data: Image file data (bytes or file-like object)
            filename: Original filename
            processing_options: Image processing options
            
        Returns:
            Asset ID of the uploaded image
            
        Raises:
            ValueError: If file validation fails
            RuntimeError: If processing fails
        """
        # Validate file
        if isinstance(file_data, bytes):
            file_size = len(file_data)
        else:
            # For file-like objects, seek to end to get size
            current_pos = file_data.tell()
            file_data.seek(0, 2)
            file_size = file_data.tell()
            file_data.seek(current_pos)
        
        is_valid, error_msg = self.validate_file_upload(filename, file_size)
        if not is_valid:
            raise ValueError(error_msg)
        
        # Generate asset ID and paths
        asset_id = self._generate_asset_id()
        ext = self._get_file_extension(filename)
        asset_filename = f"{asset_id}.{ext}"
        asset_path = self.base_path / "images" / asset_filename
        
        try:
            # Create metadata
            metadata = AssetMetadata(
                asset_id=asset_id,
                original_filename=filename,
                asset_type=AssetType.IMAGE,
                file_size=file_size,
                mime_type=self._get_mime_type(filename),
                created_at=datetime.now(),
                last_accessed=datetime.now(),
                status=AssetStatus.UPLOADING,
                file_path=str(asset_path)
            )
            
            # Save file
            if isinstance(file_data, bytes):
                if AIOFILES_AVAILABLE:
                    async with aiofiles.open(asset_path, 'wb') as f:
                        await f.write(file_data)
                else:
                    with open(asset_path, 'wb') as f:
                        f.write(file_data)
            else:
                # For file-like objects
                with open(asset_path, 'wb') as f:
                    if hasattr(file_data, 'read'):
                        shutil.copyfileobj(file_data, f)
                    else:
                        f.write(file_data)
            
            # Update status
            metadata.status = AssetStatus.PROCESSING
            self._asset_registry[asset_id] = metadata
            
            # Process image
            await self._process_image(asset_id, processing_options or ImageProcessingOptions())
            
            # Calculate checksum
            metadata.checksum = self._calculate_checksum(asset_path)
            metadata.status = AssetStatus.READY
            metadata.last_accessed = datetime.now()
            
            # Save registry
            self._save_asset_registry()
            
            self.logger.info(f"Successfully uploaded image: {filename} -> {asset_id}")
            return asset_id
            
        except Exception as e:
            # Cleanup on error
            if asset_path.exists():
                asset_path.unlink()
            if asset_id in self._asset_registry:
                del self._asset_registry[asset_id]
            
            error_msg = f"Failed to upload image {filename}: {str(e)}"
            self.logger.error(error_msg)
            raise RuntimeError(error_msg) from e
    
    async def _process_image(self, asset_id: str, options: ImageProcessingOptions) -> None:
        """
        Process uploaded image according to options.
        
        Args:
            asset_id: ID of the asset to process
            options: Processing options
        """
        if not PIL_AVAILABLE:
            self.logger.warning("PIL not available, skipping image processing")
            return
        
        metadata = self._asset_registry.get(asset_id)
        if not metadata:
            raise ValueError(f"Asset {asset_id} not found")
        
        asset_path = Path(metadata.file_path)
        if not asset_path.exists():
            raise FileNotFoundError(f"Asset file not found: {asset_path}")
        
        try:
            # Open and process image
            with Image.open(asset_path) as img:
                # Auto-orient based on EXIF data
                if options.auto_orient:
                    img = ImageOps.exif_transpose(img)
                
                # Store original dimensions
                metadata.width, metadata.height = img.size
                
                # Convert to RGB if necessary
                if img.mode in ('RGBA', 'LA', 'P'):
                    # Create white background for transparency
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
                    img = background
                elif img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Apply cropping
                if options.crop:
                    left, top, right, bottom = options.crop
                    img = img.crop((left, top, right, bottom))
                
                # Apply resizing
                if options.resize:
                    target_width, target_height = options.resize
                    if options.maintain_aspect_ratio:
                        img.thumbnail((target_width, target_height), Image.Resampling.LANCZOS)
                    else:
                        img = img.resize((target_width, target_height), Image.Resampling.LANCZOS)
                
                # Save processed image
                save_format = options.format or metadata.original_filename.split('.')[-1].upper()
                if save_format.upper() == 'JPG':
                    save_format = 'JPEG'
                
                save_kwargs = {
                    'format': save_format,
                    'optimize': options.optimize
                }
                
                if save_format == 'JPEG':
                    save_kwargs['quality'] = options.quality
                
                # Save to processed directory if modifications were made
                if any([options.resize, options.crop, options.format]):
                    processed_path = self.base_path / "processed" / f"{asset_id}_processed.{save_format.lower()}"
                    img.save(processed_path, **save_kwargs)
                    metadata.file_path = str(processed_path)
                
                # Create thumbnail
                if options.create_thumbnail:
                    thumbnail_path = self._create_thumbnail(img, asset_id, options.thumbnail_size)
                    metadata.thumbnail_path = thumbnail_path
                
                # Update metadata with final dimensions
                metadata.width, metadata.height = img.size
                
        except Exception as e:
            self.logger.error(f"Failed to process image {asset_id}: {e}")
            raise RuntimeError(f"Image processing failed: {str(e)}") from e
    
    def _create_thumbnail(self, img: Image.Image, asset_id: str, size: Tuple[int, int]) -> str:
        """Create thumbnail for image"""
        thumbnail_path = self.base_path / "thumbnails" / f"{asset_id}_thumb.jpg"
        
        # Create thumbnail
        img_copy = img.copy()
        img_copy.thumbnail(size, Image.Resampling.LANCZOS)
        
        # Save thumbnail
        img_copy.save(thumbnail_path, format='JPEG', quality=85, optimize=True)
        
        return str(thumbnail_path)
    def get_asset_url(self, asset_id: str) -> Optional[str]:
        """
        Get URL/path for accessing an asset.
        
        Args:
            asset_id: ID of the asset
            
        Returns:
            File path or URL to the asset, None if not found
        """
        metadata = self._asset_registry.get(asset_id)
        if not metadata or metadata.status != AssetStatus.READY:
            return None
        
        # Update last accessed time
        metadata.last_accessed = datetime.now()
        self._save_asset_registry()
        
        return metadata.file_path
    
    def get_asset_metadata(self, asset_id: str) -> Optional[AssetMetadata]:
        """
        Get metadata for an asset.
        
        Args:
            asset_id: ID of the asset
            
        Returns:
            Asset metadata or None if not found
        """
        metadata = self._asset_registry.get(asset_id)
        if metadata:
            # Update last accessed time
            metadata.last_accessed = datetime.now()
            self._save_asset_registry()
        
        return metadata
    
    def list_assets(self, asset_type: Optional[AssetType] = None, 
                   status: Optional[AssetStatus] = None,
                   limit: Optional[int] = None) -> List[AssetMetadata]:
        """
        List assets with optional filtering.
        
        Args:
            asset_type: Filter by asset type
            status: Filter by status
            limit: Maximum number of results
            
        Returns:
            List of asset metadata
        """
        assets = list(self._asset_registry.values())
        
        # Apply filters
        if asset_type:
            assets = [a for a in assets if a.asset_type == asset_type]
        
        if status:
            assets = [a for a in assets if a.status == status]
        
        # Sort by creation time (newest first)
        assets.sort(key=lambda a: a.created_at, reverse=True)
        
        # Apply limit
        if limit:
            assets = assets[:limit]
        
        return assets
    
    async def delete_asset(self, asset_id: str) -> bool:
        """
        Delete an asset and its associated files.
        
        Args:
            asset_id: ID of the asset to delete
            
        Returns:
            True if successfully deleted, False otherwise
        """
        metadata = self._asset_registry.get(asset_id)
        if not metadata:
            return False
        
        try:
            # Delete main file
            main_path = Path(metadata.file_path)
            if main_path.exists():
                main_path.unlink()
            
            # Delete thumbnail if exists
            if metadata.thumbnail_path:
                thumb_path = Path(metadata.thumbnail_path)
                if thumb_path.exists():
                    thumb_path.unlink()
            
            # Remove from registry
            del self._asset_registry[asset_id]
            self._save_asset_registry()
            
            self.logger.info(f"Successfully deleted asset: {asset_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to delete asset {asset_id}: {e}")
            return False
    
    def process_image_operations(self, asset_id: str, operations: List[Dict[str, any]]) -> str:
        """
        Apply a series of image operations to create a new processed asset.
        
        Args:
            asset_id: ID of the source asset
            operations: List of operations to apply
            
        Returns:
            Asset ID of the processed image
            
        Raises:
            ValueError: If asset not found or operations invalid
            RuntimeError: If processing fails
        """
        if not PIL_AVAILABLE:
            raise RuntimeError("PIL not available for image processing")
        
        metadata = self._asset_registry.get(asset_id)
        if not metadata or metadata.asset_type != AssetType.IMAGE:
            raise ValueError(f"Image asset {asset_id} not found")
        
        if metadata.status != AssetStatus.READY:
            raise ValueError(f"Asset {asset_id} is not ready for processing")
        
        try:
            # Open source image
            with Image.open(metadata.file_path) as img:
                # Apply operations
                for operation in operations:
                    op_type = operation.get('type')
                    
                    if op_type == 'resize':
                        width = operation.get('width')
                        height = operation.get('height')
                        maintain_aspect = operation.get('maintain_aspect_ratio', True)
                        
                        if maintain_aspect:
                            img.thumbnail((width, height), Image.Resampling.LANCZOS)
                        else:
                            img = img.resize((width, height), Image.Resampling.LANCZOS)
                    
                    elif op_type == 'crop':
                        left = operation.get('left', 0)
                        top = operation.get('top', 0)
                        right = operation.get('right', img.width)
                        bottom = operation.get('bottom', img.height)
                        img = img.crop((left, top, right, bottom))
                    
                    elif op_type == 'rotate':
                        angle = operation.get('angle', 0)
                        img = img.rotate(angle, expand=True)
                    
                    elif op_type == 'flip':
                        direction = operation.get('direction', 'horizontal')
                        if direction == 'horizontal':
                            img = img.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
                        elif direction == 'vertical':
                            img = img.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
                    
                    elif op_type == 'blur':
                        radius = operation.get('radius', 1)
                        img = img.filter(ImageFilter.GaussianBlur(radius=radius))
                    
                    elif op_type == 'sharpen':
                        img = img.filter(ImageFilter.SHARPEN)
                
                # Save processed image
                new_asset_id = self._generate_asset_id()
                ext = self._get_file_extension(metadata.original_filename)
                processed_filename = f"{new_asset_id}_processed.{ext}"
                processed_path = self.base_path / "processed" / processed_filename
                
                # Ensure processed directory exists
                processed_path.parent.mkdir(exist_ok=True)
                
                # Save image
                save_format = ext.upper()
                if save_format == 'JPG':
                    save_format = 'JPEG'
                
                img.save(processed_path, format=save_format, quality=85, optimize=True)
                
                # Create new metadata
                new_metadata = AssetMetadata(
                    asset_id=new_asset_id,
                    original_filename=f"processed_{metadata.original_filename}",
                    asset_type=AssetType.IMAGE,
                    file_size=processed_path.stat().st_size,
                    mime_type=metadata.mime_type,
                    created_at=datetime.now(),
                    last_accessed=datetime.now(),
                    status=AssetStatus.READY,
                    file_path=str(processed_path),
                    width=img.width,
                    height=img.height,
                    checksum=self._calculate_checksum(processed_path),
                    tags=['processed'],
                    metadata={'source_asset_id': asset_id, 'operations': operations}
                )
                
                # Create thumbnail
                thumbnail_path = self._create_thumbnail(img, new_asset_id, (256, 256))
                new_metadata.thumbnail_path = thumbnail_path
                
                # Register new asset
                self._asset_registry[new_asset_id] = new_metadata
                self._save_asset_registry()
                
                self.logger.info(f"Successfully processed image: {asset_id} -> {new_asset_id}")
                return new_asset_id
                
        except Exception as e:
            error_msg = f"Failed to process image operations for {asset_id}: {str(e)}"
            self.logger.error(error_msg)
            raise RuntimeError(error_msg) from e
    
    async def upload_video(self, file_data: Union[bytes, BinaryIO], filename: str) -> str:
        """
        Upload a video file.
        
        Args:
            file_data: Video file data
            filename: Original filename
            
        Returns:
            Asset ID of the uploaded video
        """
        # Validate file
        if isinstance(file_data, bytes):
            file_size = len(file_data)
        else:
            current_pos = file_data.tell()
            file_data.seek(0, 2)
            file_size = file_data.tell()
            file_data.seek(current_pos)
        
        is_valid, error_msg = self.validate_file_upload(filename, file_size)
        if not is_valid:
            raise ValueError(error_msg)
        
        # Generate asset ID and paths
        asset_id = self._generate_asset_id()
        ext = self._get_file_extension(filename)
        asset_filename = f"{asset_id}.{ext}"
        asset_path = self.base_path / "videos" / asset_filename
        
        try:
            # Create metadata
            metadata = AssetMetadata(
                asset_id=asset_id,
                original_filename=filename,
                asset_type=AssetType.VIDEO,
                file_size=file_size,
                mime_type=self._get_mime_type(filename),
                created_at=datetime.now(),
                last_accessed=datetime.now(),
                status=AssetStatus.UPLOADING,
                file_path=str(asset_path)
            )
            
            # Save file
            if isinstance(file_data, bytes):
                if AIOFILES_AVAILABLE:
                    async with aiofiles.open(asset_path, 'wb') as f:
                        await f.write(file_data)
                else:
                    with open(asset_path, 'wb') as f:
                        f.write(file_data)
            else:
                with open(asset_path, 'wb') as f:
                    if hasattr(file_data, 'read'):
                        shutil.copyfileobj(file_data, f)
                    else:
                        f.write(file_data)
            
            # Update status
            metadata.status = AssetStatus.PROCESSING
            self._asset_registry[asset_id] = metadata
            
            # Extract video metadata if OpenCV is available
            if CV2_AVAILABLE:
                await self._extract_video_metadata(asset_id)
            
            # Calculate checksum
            metadata.checksum = self._calculate_checksum(asset_path)
            metadata.status = AssetStatus.READY
            metadata.last_accessed = datetime.now()
            
            # Save registry
            self._save_asset_registry()
            
            self.logger.info(f"Successfully uploaded video: {filename} -> {asset_id}")
            return asset_id
            
        except Exception as e:
            # Cleanup on error
            if asset_path.exists():
                asset_path.unlink()
            if asset_id in self._asset_registry:
                del self._asset_registry[asset_id]
            
            error_msg = f"Failed to upload video {filename}: {str(e)}"
            self.logger.error(error_msg)
            raise RuntimeError(error_msg) from e
    
    async def _extract_video_metadata(self, asset_id: str) -> None:
        """Extract metadata from video file using OpenCV"""
        metadata = self._asset_registry.get(asset_id)
        if not metadata:
            return
        
        try:
            cap = cv2.VideoCapture(metadata.file_path)
            
            if cap.isOpened():
                # Get video properties
                width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                fps = cap.get(cv2.CAP_PROP_FPS)
                frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                
                if fps > 0:
                    duration = frame_count / fps
                    metadata.duration = duration
                
                metadata.width = width
                metadata.height = height
                metadata.metadata.update({
                    'fps': fps,
                    'frame_count': frame_count,
                    'codec': cap.get(cv2.CAP_PROP_FOURCC)
                })
                
                # Create video thumbnail (first frame)
                ret, frame = cap.read()
                if ret:
                    thumbnail_path = self.base_path / "thumbnails" / f"{asset_id}_thumb.jpg"
                    cv2.imwrite(str(thumbnail_path), frame)
                    metadata.thumbnail_path = str(thumbnail_path)
            
            cap.release()
            
        except Exception as e:
            self.logger.warning(f"Failed to extract video metadata for {asset_id}: {e}")
    
    def get_storage_stats(self) -> Dict[str, any]:
        """
        Get storage statistics.
        
        Returns:
            Dictionary with storage statistics
        """
        stats = {
            'total_assets': len(self._asset_registry),
            'assets_by_type': {},
            'assets_by_status': {},
            'total_size_bytes': 0,
            'total_size_mb': 0,
            'storage_path': str(self.base_path),
            'temp_path': str(self.temp_path)
        }
        
        # Calculate statistics
        for metadata in self._asset_registry.values():
            # Count by type
            asset_type = metadata.asset_type.value
            stats['assets_by_type'][asset_type] = stats['assets_by_type'].get(asset_type, 0) + 1
            
            # Count by status
            status = metadata.status.value
            stats['assets_by_status'][status] = stats['assets_by_status'].get(status, 0) + 1
            
            # Sum file sizes
            stats['total_size_bytes'] += metadata.file_size
        
        stats['total_size_mb'] = stats['total_size_bytes'] / (1024 * 1024)
        
        # Check available disk space
        try:
            disk_usage = shutil.disk_usage(self.base_path)
            stats['disk_total_bytes'] = disk_usage.total
            stats['disk_free_bytes'] = disk_usage.free
            stats['disk_used_bytes'] = disk_usage.used
            stats['disk_free_mb'] = disk_usage.free / (1024 * 1024)
            stats['disk_usage_percent'] = (disk_usage.used / disk_usage.total) * 100
        except Exception as e:
            self.logger.warning(f"Failed to get disk usage: {e}")
        
        return stats
    
    async def cleanup_expired_assets(self, max_age_hours: Optional[int] = None) -> int:
        """
        Clean up expired assets based on last access time.
        
        Args:
            max_age_hours: Maximum age in hours (uses config default if None)
            
        Returns:
            Number of assets cleaned up
        """
        if max_age_hours is None:
            max_age_hours = self.config.cleanup_interval_hours
        
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        expired_assets = []
        
        # Find expired assets
        for asset_id, metadata in self._asset_registry.items():
            if (metadata.last_accessed < cutoff_time and 
                metadata.status in [AssetStatus.READY, AssetStatus.ERROR]):
                expired_assets.append(asset_id)
        
        # Delete expired assets
        deleted_count = 0
        for asset_id in expired_assets:
            if await self.delete_asset(asset_id):
                deleted_count += 1
        
        # Clean up empty directories
        await self._cleanup_empty_directories()
        
        self.logger.info(f"Cleaned up {deleted_count} expired assets")
        return deleted_count
    
    async def _cleanup_empty_directories(self) -> None:
        """Remove empty directories in the asset storage"""
        try:
            for root, dirs, files in os.walk(self.base_path, topdown=False):
                for directory in dirs:
                    dir_path = Path(root) / directory
                    try:
                        if not any(dir_path.iterdir()):
                            dir_path.rmdir()
                    except OSError:
                        pass  # Directory not empty or permission error
        except Exception as e:
            self.logger.warning(f"Failed to cleanup empty directories: {e}")
    
    async def optimize_storage(self) -> Dict[str, any]:
        """
        Optimize storage by cleaning up temporary files and expired assets.
        
        Returns:
            Dictionary with optimization results
        """
        results = {
            'expired_assets_deleted': 0,
            'temp_files_deleted': 0,
            'space_freed_mb': 0,
            'errors': []
        }
        
        try:
            # Get initial storage stats
            initial_stats = self.get_storage_stats()
            initial_size = initial_stats['total_size_mb']
            
            # Clean up expired assets
            results['expired_assets_deleted'] = await self.cleanup_expired_assets()
            
            # Clean up temporary files
            temp_files_deleted = await self._cleanup_temp_files()
            results['temp_files_deleted'] = temp_files_deleted
            
            # Get final storage stats
            final_stats = self.get_storage_stats()
            final_size = final_stats['total_size_mb']
            
            results['space_freed_mb'] = initial_size - final_size
            
            self.logger.info(f"Storage optimization completed: {results}")
            
        except Exception as e:
            error_msg = f"Storage optimization failed: {str(e)}"
            results['errors'].append(error_msg)
            self.logger.error(error_msg)
        
        return results
    
    async def _cleanup_temp_files(self) -> int:
        """Clean up temporary files"""
        deleted_count = 0
        
        try:
            if self.temp_path.exists():
                for file_path in self.temp_path.rglob('*'):
                    if file_path.is_file():
                        try:
                            # Delete files older than 1 hour
                            file_age = datetime.now() - datetime.fromtimestamp(file_path.stat().st_mtime)
                            if file_age > timedelta(hours=1):
                                file_path.unlink()
                                deleted_count += 1
                        except Exception as e:
                            self.logger.warning(f"Failed to delete temp file {file_path}: {e}")
        
        except Exception as e:
            self.logger.error(f"Failed to cleanup temp files: {e}")
        
        return deleted_count
    
    def check_storage_limits(self) -> Dict[str, any]:
        """
        Check if storage is approaching limits and return warnings.
        
        Returns:
            Dictionary with storage limit information and warnings
        """
        stats = self.get_storage_stats()
        warnings = []
        
        # Check disk space
        if 'disk_usage_percent' in stats:
            if stats['disk_usage_percent'] > 90:
                warnings.append("Disk usage is above 90%")
            elif stats['disk_usage_percent'] > 80:
                warnings.append("Disk usage is above 80%")
        
        # Check configured storage limit
        max_storage_bytes = self.config.max_storage_gb * 1024 * 1024 * 1024
        if stats['total_size_bytes'] > max_storage_bytes:
            warnings.append(f"Asset storage exceeds configured limit of {self.config.max_storage_gb}GB")
        
        # Check number of assets
        if stats['total_assets'] > 10000:
            warnings.append("Large number of assets may impact performance")
        
        return {
            'stats': stats,
            'warnings': warnings,
            'needs_cleanup': len(warnings) > 0
        }


# Convenience functions for common operations
async def upload_image_file(file_path: str, asset_manager: Optional[AssetManager] = None) -> str:
    """
    Upload an image file from local filesystem.
    
    Args:
        file_path: Path to the image file
        asset_manager: AssetManager instance (creates new if None)
        
    Returns:
        Asset ID of uploaded image
    """
    if asset_manager is None:
        asset_manager = AssetManager()
    
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    with open(file_path, 'rb') as f:
        return await asset_manager.upload_image(f, file_path.name)


async def upload_video_file(file_path: str, asset_manager: Optional[AssetManager] = None) -> str:
    """
    Upload a video file from local filesystem.
    
    Args:
        file_path: Path to the video file
        asset_manager: AssetManager instance (creates new if None)
        
    Returns:
        Asset ID of uploaded video
    """
    if asset_manager is None:
        asset_manager = AssetManager()
    
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    with open(file_path, 'rb') as f:
        return await asset_manager.upload_video(f, file_path.name)
