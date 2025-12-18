"""
Video Resource Management for Video Studio

This module provides specialized video resource management functionality,
including video processing, metadata extraction, and lifecycle management.
"""

import os
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union, BinaryIO
from dataclasses import dataclass
import logging

try:
    import cv2
    import numpy as np
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

try:
    import ffmpeg
    FFMPEG_AVAILABLE = True
except ImportError:
    FFMPEG_AVAILABLE = False

from .asset_manager import AssetManager, AssetType, AssetStatus, AssetMetadata
from .config import get_config
from .error_handler import VideoStudioErrorHandler


@dataclass
class VideoProcessingOptions:
    """Options for video processing operations"""
    resize: Optional[Tuple[int, int]] = None
    crop: Optional[Tuple[int, int, int, int]] = None  # (x, y, width, height)
    trim: Optional[Tuple[float, float]] = None  # (start_time, end_time) in seconds
    fps: Optional[int] = None
    quality: Optional[str] = None  # 'low', 'medium', 'high'
    format: Optional[str] = None  # Output format
    bitrate: Optional[str] = None  # e.g., '1M', '500k'
    audio_enabled: bool = True
    create_preview: bool = True


@dataclass
class VideoMetadata:
    """Extended video metadata"""
    duration: float
    fps: float
    width: int
    height: int
    bitrate: Optional[int] = None
    codec: Optional[str] = None
    audio_codec: Optional[str] = None
    audio_channels: Optional[int] = None
    audio_sample_rate: Optional[int] = None
    frame_count: int = 0
    file_size: int = 0
    aspect_ratio: Optional[str] = None


class VideoManager:
    """
    Specialized video resource management system.
    
    Provides advanced video processing, metadata extraction, and lifecycle management
    capabilities built on top of the AssetManager.
    """
    
    def __init__(self, asset_manager: Optional[AssetManager] = None):
        """Initialize VideoManager"""
        self.asset_manager = asset_manager or AssetManager()
        self.error_handler = VideoStudioErrorHandler()
        self.logger = logging.getLogger(__name__)
        self.config = get_config()
        
        # Video processing settings
        self.supported_formats = ['mp4', 'mov', 'avi', 'mkv', 'webm']
        self.quality_presets = {
            'low': {'crf': 28, 'preset': 'fast'},
            'medium': {'crf': 23, 'preset': 'medium'},
            'high': {'crf': 18, 'preset': 'slow'}
        }
    
    async def upload_video(self, file_data: Union[bytes, BinaryIO], filename: str,
                          processing_options: Optional[VideoProcessingOptions] = None) -> str:
        """
        Upload and process a video file.
        
        Args:
            file_data: Video file data
            filename: Original filename
            processing_options: Video processing options
            
        Returns:
            Asset ID of the uploaded video
        """
        # Upload video using asset manager
        asset_id = await self.asset_manager.upload_video(file_data, filename)
        
        # Apply processing if specified
        if processing_options:
            try:
                processed_asset_id = await self.process_video(asset_id, processing_options)
                return processed_asset_id
            except Exception as e:
                self.logger.warning(f"Video processing failed for {asset_id}: {e}")
                # Return original asset if processing fails
                return asset_id
        
        return asset_id
    
    async def process_video(self, asset_id: str, options: VideoProcessingOptions) -> str:
        """
        Process a video with specified options.
        
        Args:
            asset_id: Source video asset ID
            options: Processing options
            
        Returns:
            Asset ID of processed video
        """
        if not FFMPEG_AVAILABLE:
            raise RuntimeError("FFmpeg not available for video processing")
        
        metadata = self.asset_manager.get_asset_metadata(asset_id)
        if not metadata or metadata.asset_type != AssetType.VIDEO:
            raise ValueError(f"Video asset {asset_id} not found")
        
        if metadata.status != AssetStatus.READY:
            raise ValueError(f"Asset {asset_id} is not ready for processing")
        
        try:
            # Generate output path
            new_asset_id = self.asset_manager._generate_asset_id()
            ext = options.format or Path(metadata.original_filename).suffix.lstrip('.')
            output_filename = f"{new_asset_id}_processed.{ext}"
            output_path = self.asset_manager.base_path / "videos" / output_filename
            
            # Build FFmpeg command
            input_stream = ffmpeg.input(metadata.file_path)
            
            # Apply video filters
            video_filters = []
            
            if options.resize:
                width, height = options.resize
                video_filters.append(f'scale={width}:{height}')
            
            if options.crop:
                x, y, w, h = options.crop
                video_filters.append(f'crop={w}:{h}:{x}:{y}')
            
            # Apply filters to stream
            if video_filters:
                input_stream = input_stream.video.filter(','.join(video_filters))
            
            # Set output options
            output_options = {}
            
            if options.fps:
                output_options['r'] = options.fps
            
            if options.quality and options.quality in self.quality_presets:
                preset = self.quality_presets[options.quality]
                output_options['crf'] = preset['crf']
                output_options['preset'] = preset['preset']
            
            if options.bitrate:
                output_options['b:v'] = options.bitrate
            
            if not options.audio_enabled:
                output_options['an'] = None
            
            # Apply trimming
            if options.trim:
                start_time, end_time = options.trim
                output_options['ss'] = start_time
                output_options['t'] = end_time - start_time
            
            # Run FFmpeg
            output_stream = ffmpeg.output(input_stream, str(output_path), **output_options)
            await asyncio.create_subprocess_exec(
                *ffmpeg.compile(output_stream, overwrite_output=True),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Create new asset metadata
            file_size = output_path.stat().st_size
            new_metadata = AssetMetadata(
                asset_id=new_asset_id,
                original_filename=f"processed_{metadata.original_filename}",
                asset_type=AssetType.VIDEO,
                file_size=file_size,
                mime_type=metadata.mime_type,
                created_at=datetime.now(),
                last_accessed=datetime.now(),
                status=AssetStatus.READY,
                file_path=str(output_path),
                checksum=self.asset_manager._calculate_checksum(output_path),
                tags=['processed'],
                metadata={'source_asset_id': asset_id, 'processing_options': options.__dict__}
            )
            
            # Extract metadata for processed video
            if CV2_AVAILABLE:
                video_metadata = await self._extract_detailed_metadata(str(output_path))
                if video_metadata:
                    new_metadata.width = video_metadata.width
                    new_metadata.height = video_metadata.height
                    new_metadata.duration = video_metadata.duration
                    new_metadata.metadata.update({
                        'fps': video_metadata.fps,
                        'frame_count': video_metadata.frame_count,
                        'codec': video_metadata.codec,
                        'bitrate': video_metadata.bitrate
                    })
            
            # Create preview/thumbnail if requested
            if options.create_preview:
                thumbnail_path = await self._create_video_thumbnail(str(output_path), new_asset_id)
                new_metadata.thumbnail_path = thumbnail_path
            
            # Register new asset
            self.asset_manager._asset_registry[new_asset_id] = new_metadata
            self.asset_manager._save_asset_registry()
            
            self.logger.info(f"Successfully processed video: {asset_id} -> {new_asset_id}")
            return new_asset_id
            
        except Exception as e:
            error_msg = f"Failed to process video {asset_id}: {str(e)}"
            self.logger.error(error_msg)
            raise RuntimeError(error_msg) from e
    
    async def _extract_detailed_metadata(self, video_path: str) -> Optional[VideoMetadata]:
        """Extract detailed metadata from video file"""
        try:
            if FFMPEG_AVAILABLE:
                # Use ffprobe for detailed metadata
                probe = ffmpeg.probe(video_path)
                video_stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'video'), None)
                audio_stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'audio'), None)
                
                if video_stream:
                    duration = float(video_stream.get('duration', 0))
                    fps = eval(video_stream.get('r_frame_rate', '0/1'))
                    width = int(video_stream.get('width', 0))
                    height = int(video_stream.get('height', 0))
                    
                    metadata = VideoMetadata(
                        duration=duration,
                        fps=fps,
                        width=width,
                        height=height,
                        codec=video_stream.get('codec_name'),
                        bitrate=int(video_stream.get('bit_rate', 0)) if video_stream.get('bit_rate') else None,
                        frame_count=int(duration * fps) if duration and fps else 0,
                        file_size=os.path.getsize(video_path),
                        aspect_ratio=f"{width}:{height}" if width and height else None
                    )
                    
                    if audio_stream:
                        metadata.audio_codec = audio_stream.get('codec_name')
                        metadata.audio_channels = int(audio_stream.get('channels', 0))
                        metadata.audio_sample_rate = int(audio_stream.get('sample_rate', 0))
                    
                    return metadata
            
            elif CV2_AVAILABLE:
                # Fallback to OpenCV
                cap = cv2.VideoCapture(video_path)
                if cap.isOpened():
                    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                    fps = cap.get(cv2.CAP_PROP_FPS)
                    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                    duration = frame_count / fps if fps > 0 else 0
                    
                    cap.release()
                    
                    return VideoMetadata(
                        duration=duration,
                        fps=fps,
                        width=width,
                        height=height,
                        frame_count=frame_count,
                        file_size=os.path.getsize(video_path),
                        aspect_ratio=f"{width}:{height}" if width and height else None
                    )
        
        except Exception as e:
            self.logger.warning(f"Failed to extract video metadata: {e}")
        
        return None
    
    async def _create_video_thumbnail(self, video_path: str, asset_id: str) -> str:
        """Create thumbnail from video"""
        thumbnail_path = self.asset_manager.base_path / "thumbnails" / f"{asset_id}_thumb.jpg"
        
        try:
            if FFMPEG_AVAILABLE:
                # Use FFmpeg to extract frame
                (
                    ffmpeg
                    .input(video_path, ss=1)  # Extract frame at 1 second
                    .output(str(thumbnail_path), vframes=1, format='image2', vcodec='mjpeg')
                    .overwrite_output()
                    .run(quiet=True)
                )
            elif CV2_AVAILABLE:
                # Fallback to OpenCV
                cap = cv2.VideoCapture(video_path)
                if cap.isOpened():
                    # Seek to 1 second or 10% of video
                    fps = cap.get(cv2.CAP_PROP_FPS)
                    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                    target_frame = min(int(fps), frame_count // 10) if fps > 0 else 0
                    
                    cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
                    ret, frame = cap.read()
                    
                    if ret:
                        cv2.imwrite(str(thumbnail_path), frame)
                    
                    cap.release()
            
            return str(thumbnail_path)
            
        except Exception as e:
            self.logger.warning(f"Failed to create video thumbnail: {e}")
            return ""
    
    def get_video_info(self, asset_id: str) -> Optional[Dict[str, any]]:
        """
        Get detailed video information.
        
        Args:
            asset_id: Video asset ID
            
        Returns:
            Video information dictionary
        """
        metadata = self.asset_manager.get_asset_metadata(asset_id)
        if not metadata or metadata.asset_type != AssetType.VIDEO:
            return None
        
        info = {
            'asset_id': metadata.asset_id,
            'filename': metadata.original_filename,
            'file_size': metadata.file_size,
            'file_size_mb': metadata.file_size / (1024 * 1024),
            'mime_type': metadata.mime_type,
            'created_at': metadata.created_at.isoformat(),
            'last_accessed': metadata.last_accessed.isoformat(),
            'status': metadata.status.value,
            'file_path': metadata.file_path,
            'thumbnail_path': metadata.thumbnail_path,
            'width': metadata.width,
            'height': metadata.height,
            'duration': metadata.duration,
            'duration_formatted': self._format_duration(metadata.duration) if metadata.duration else None,
            'aspect_ratio': f"{metadata.width}:{metadata.height}" if metadata.width and metadata.height else None,
            'checksum': metadata.checksum,
            'tags': metadata.tags,
            'metadata': metadata.metadata
        }
        
        return info
    
    def _format_duration(self, duration: float) -> str:
        """Format duration in seconds to HH:MM:SS"""
        hours = int(duration // 3600)
        minutes = int((duration % 3600) // 60)
        seconds = int(duration % 60)
        
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes:02d}:{seconds:02d}"
    
    def list_videos(self, limit: Optional[int] = None) -> List[Dict[str, any]]:
        """
        List all video assets.
        
        Args:
            limit: Maximum number of results
            
        Returns:
            List of video information dictionaries
        """
        assets = self.asset_manager.list_assets(
            asset_type=AssetType.VIDEO,
            status=AssetStatus.READY,
            limit=limit
        )
        
        return [self.get_video_info(asset.asset_id) for asset in assets]
    
    async def delete_video(self, asset_id: str) -> bool:
        """
        Delete a video asset.
        
        Args:
            asset_id: Video asset ID
            
        Returns:
            True if successfully deleted
        """
        return await self.asset_manager.delete_asset(asset_id)
    
    async def convert_video_format(self, asset_id: str, target_format: str,
                                  quality: str = 'medium') -> str:
        """
        Convert video to different format.
        
        Args:
            asset_id: Source video asset ID
            target_format: Target format (mp4, mov, webm, etc.)
            quality: Quality preset ('low', 'medium', 'high')
            
        Returns:
            Asset ID of converted video
        """
        options = VideoProcessingOptions(
            format=target_format,
            quality=quality,
            create_preview=True
        )
        
        return await self.process_video(asset_id, options)
    
    async def resize_video(self, asset_id: str, width: int, height: int,
                          maintain_aspect_ratio: bool = True) -> str:
        """
        Resize a video.
        
        Args:
            asset_id: Source video asset ID
            width: Target width
            height: Target height
            maintain_aspect_ratio: Whether to maintain aspect ratio
            
        Returns:
            Asset ID of resized video
        """
        if maintain_aspect_ratio:
            # Calculate aspect ratio preserving dimensions
            metadata = self.asset_manager.get_asset_metadata(asset_id)
            if metadata and metadata.width and metadata.height:
                original_ratio = metadata.width / metadata.height
                target_ratio = width / height
                
                if original_ratio > target_ratio:
                    # Fit to width
                    height = int(width / original_ratio)
                else:
                    # Fit to height
                    width = int(height * original_ratio)
        
        options = VideoProcessingOptions(
            resize=(width, height),
            create_preview=True
        )
        
        return await self.process_video(asset_id, options)
    
    async def trim_video(self, asset_id: str, start_time: float, end_time: float) -> str:
        """
        Trim a video to specified time range.
        
        Args:
            asset_id: Source video asset ID
            start_time: Start time in seconds
            end_time: End time in seconds
            
        Returns:
            Asset ID of trimmed video
        """
        options = VideoProcessingOptions(
            trim=(start_time, end_time),
            create_preview=True
        )
        
        return await self.process_video(asset_id, options)
    
    def get_video_statistics(self) -> Dict[str, any]:
        """
        Get video storage statistics.
        
        Returns:
            Video statistics dictionary
        """
        video_assets = self.asset_manager.list_assets(asset_type=AssetType.VIDEO)
        
        total_size = sum(asset.file_size for asset in video_assets)
        total_duration = sum(asset.duration or 0 for asset in video_assets)
        
        # Group by status
        status_counts = {}
        for asset in video_assets:
            status = asset.status.value
            status_counts[status] = status_counts.get(status, 0) + 1
        
        # Group by format
        format_counts = {}
        for asset in video_assets:
            ext = Path(asset.original_filename).suffix.lower().lstrip('.')
            format_counts[ext] = format_counts.get(ext, 0) + 1
        
        return {
            'total_videos': len(video_assets),
            'total_size_bytes': total_size,
            'total_size_mb': total_size / (1024 * 1024),
            'total_duration_seconds': total_duration,
            'total_duration_formatted': self._format_duration(total_duration),
            'average_file_size_mb': (total_size / len(video_assets) / (1024 * 1024)) if video_assets else 0,
            'status_breakdown': status_counts,
            'format_breakdown': format_counts
        }
    
    async def cleanup_processed_videos(self, keep_original: bool = True) -> int:
        """
        Clean up processed video files, optionally keeping originals.
        
        Args:
            keep_original: Whether to keep original uploaded videos
            
        Returns:
            Number of videos cleaned up
        """
        video_assets = self.asset_manager.list_assets(asset_type=AssetType.VIDEO)
        deleted_count = 0
        
        for asset in video_assets:
            # Skip if we want to keep originals and this is not a processed video
            if keep_original and 'processed' not in asset.tags:
                continue
            
            # Delete old processed videos (older than 7 days)
            age = datetime.now() - asset.created_at
            if age > timedelta(days=7):
                if await self.delete_video(asset.asset_id):
                    deleted_count += 1
        
        return deleted_count


# Global video manager instance
_video_manager = None


def get_video_manager() -> VideoManager:
    """Get global VideoManager instance"""
    global _video_manager
    if _video_manager is None:
        _video_manager = VideoManager()
    return _video_manager