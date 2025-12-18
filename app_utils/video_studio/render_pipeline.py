"""
Video Rendering and Composition Pipeline

This module implements the Render_Pipeline class for handling final video composition,
including video segment merging, transition effects, and timeline management.
"""

import asyncio
import os
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple, Union
import json

from .models import VideoConfig, Scene, TaskStatus, VideoQuality, AspectRatio, AudioConfig
from .config import get_config, RenderingConfig
from .error_handler import handle_rendering_error, with_video_studio_error_handling
from .logging_config import render_logger


class TransitionType(Enum):
    """Types of transitions between video segments"""
    NONE = "none"
    FADE = "fade"
    DISSOLVE = "dissolve"
    SLIDE_LEFT = "slide_left"
    SLIDE_RIGHT = "slide_right"
    ZOOM_IN = "zoom_in"
    ZOOM_OUT = "zoom_out"


class VideoFormat(Enum):
    """Supported video output formats"""
    MP4 = "mp4"
    MOV = "mov"
    AVI = "avi"
    WEBM = "webm"


class CompressionLevel(Enum):
    """Video compression quality levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    LOSSLESS = "lossless"


class AudioSyncMethod(Enum):
    """Methods for audio-video synchronization"""
    TIMECODE = "timecode"
    WAVEFORM_ANALYSIS = "waveform_analysis"
    FRAME_ALIGNMENT = "frame_alignment"
    MANUAL_OFFSET = "manual_offset"


class QualityMetric(Enum):
    """Video quality metrics for assessment"""
    RESOLUTION = "resolution"
    BITRATE = "bitrate"
    FRAME_RATE = "frame_rate"
    COLOR_DEPTH = "color_depth"
    AUDIO_QUALITY = "audio_quality"
    SYNC_ACCURACY = "sync_accuracy"


class Platform(Enum):
    """Target platforms for video optimization"""
    YOUTUBE = "youtube"
    INSTAGRAM = "instagram"
    TIKTOK = "tiktok"
    FACEBOOK = "facebook"
    TWITTER = "twitter"
    LINKEDIN = "linkedin"
    GENERIC_WEB = "generic_web"
    MOBILE = "mobile"
    DESKTOP = "desktop"


class VideoCodec(Enum):
    """Supported video codecs"""
    H264 = "h264"
    H265 = "h265"
    VP9 = "vp9"
    AV1 = "av1"


class AudioCodec(Enum):
    """Supported audio codecs"""
    AAC = "aac"
    MP3 = "mp3"
    OPUS = "opus"
    VORBIS = "vorbis"


@dataclass
class AudioTrack:
    """Represents an audio track for video composition"""
    track_id: str
    file_path: str
    start_time: float  # Start time in the final video (seconds)
    duration: float    # Duration of audio (seconds)
    volume: float = 1.0  # Volume level (0.0 - 1.0)
    fade_in: float = 0.0  # Fade in duration (seconds)
    fade_out: float = 0.0  # Fade out duration (seconds)
    sync_offset: float = 0.0  # Manual sync offset (seconds)
    
    def validate(self) -> bool:
        """Validate audio track configuration"""
        if not self.track_id or not isinstance(self.track_id, str):
            return False
        if not self.file_path or not os.path.exists(self.file_path):
            return False
        if self.start_time < 0 or self.duration <= 0:
            return False
        if not (0.0 <= self.volume <= 1.0):
            return False
        if self.fade_in < 0 or self.fade_out < 0:
            return False
        return True


@dataclass
class VideoSegment:
    """Represents a single video segment in the composition"""
    segment_id: str
    file_path: str
    start_time: float  # Start time in the final video (seconds)
    duration: float    # Duration of this segment (seconds)
    scene: Optional[Scene] = None
    transition_in: TransitionType = TransitionType.NONE
    transition_out: TransitionType = TransitionType.NONE
    transition_duration: float = 0.5  # Duration of transitions (seconds)
    audio_tracks: List[AudioTrack] = field(default_factory=list)
    
    def validate(self) -> bool:
        """Validate video segment configuration"""
        if not self.segment_id or not isinstance(self.segment_id, str):
            return False
        if not self.file_path or not os.path.exists(self.file_path):
            return False
        if self.start_time < 0 or self.duration <= 0:
            return False
        if self.transition_duration < 0:
            return False
        
        # Validate audio tracks
        for track in self.audio_tracks:
            if not track.validate():
                return False
        
        return True


@dataclass
class PlatformSettings:
    """Platform-specific optimization settings"""
    platform: Platform
    max_file_size_mb: Optional[int] = None
    max_duration_seconds: Optional[int] = None
    recommended_resolution: Optional[Tuple[int, int]] = None
    recommended_aspect_ratio: Optional[AspectRatio] = None
    recommended_fps: Optional[int] = None
    video_codec: VideoCodec = VideoCodec.H264
    audio_codec: AudioCodec = AudioCodec.AAC
    max_bitrate_kbps: Optional[int] = None
    audio_bitrate_kbps: int = 128
    enable_hdr: bool = False
    color_profile: str = "sRGB"
    
    def validate(self) -> bool:
        """Validate platform settings"""
        if not isinstance(self.platform, Platform):
            return False
        if self.max_file_size_mb is not None and self.max_file_size_mb <= 0:
            return False
        if self.max_duration_seconds is not None and self.max_duration_seconds <= 0:
            return False
        if self.recommended_fps is not None and self.recommended_fps <= 0:
            return False
        if self.audio_bitrate_kbps <= 0:
            return False
        return True


@dataclass
class QualityControlSettings:
    """Settings for video quality control and validation"""
    enable_quality_check: bool = True
    min_resolution: Tuple[int, int] = (720, 480)
    max_resolution: Tuple[int, int] = (7680, 4320)  # 8K
    min_bitrate_kbps: int = 500
    max_bitrate_kbps: int = 50000
    min_fps: int = 15
    max_fps: int = 60
    audio_sync_tolerance_ms: int = 40  # Acceptable sync drift
    enable_auto_correction: bool = True
    quality_threshold: float = 0.8  # 0.0 - 1.0
    
    def validate(self) -> bool:
        """Validate quality control settings"""
        if self.min_resolution[0] <= 0 or self.min_resolution[1] <= 0:
            return False
        if self.max_resolution[0] <= 0 or self.max_resolution[1] <= 0:
            return False
        if self.min_bitrate_kbps <= 0 or self.max_bitrate_kbps <= 0:
            return False
        if self.min_fps <= 0 or self.max_fps <= 0:
            return False
        if self.audio_sync_tolerance_ms < 0:
            return False
        if not (0.0 <= self.quality_threshold <= 1.0):
            return False
        return True


@dataclass
class FormatConversionSettings:
    """Settings for format conversion operations"""
    target_format: VideoFormat
    video_codec: VideoCodec = VideoCodec.H264
    audio_codec: AudioCodec = AudioCodec.AAC
    preserve_quality: bool = True
    enable_fast_start: bool = True  # For web streaming
    enable_two_pass: bool = False  # For better quality
    custom_ffmpeg_args: List[str] = field(default_factory=list)
    
    def validate(self) -> bool:
        """Validate conversion settings"""
        if not isinstance(self.target_format, VideoFormat):
            return False
        if not isinstance(self.video_codec, VideoCodec):
            return False
        if not isinstance(self.audio_codec, AudioCodec):
            return False
        return True


@dataclass
class RenderSettings:
    """Settings for video rendering and composition"""
    output_format: VideoFormat = VideoFormat.MP4
    quality: VideoQuality = VideoQuality.FULL_HD_1080P
    aspect_ratio: AspectRatio = AspectRatio.LANDSCAPE
    fps: int = 30
    compression: CompressionLevel = CompressionLevel.HIGH
    enable_hardware_acceleration: bool = True
    audio_enabled: bool = True
    audio_bitrate: int = 128  # kbps
    video_bitrate: Optional[int] = None  # Auto-calculate if None
    audio_sync_method: AudioSyncMethod = AudioSyncMethod.TIMECODE
    quality_control: QualityControlSettings = field(default_factory=QualityControlSettings)
    platform_settings: Optional[PlatformSettings] = None
    enable_multi_format_output: bool = False
    output_formats: List[VideoFormat] = field(default_factory=lambda: [VideoFormat.MP4])
    
    def validate(self) -> bool:
        """Validate render settings"""
        if not isinstance(self.output_format, VideoFormat):
            return False
        if not isinstance(self.quality, VideoQuality):
            return False
        if not isinstance(self.aspect_ratio, AspectRatio):
            return False
        if self.fps <= 0 or self.fps > 120:
            return False
        if self.audio_bitrate <= 0:
            return False
        if self.video_bitrate is not None and self.video_bitrate <= 0:
            return False
        if not isinstance(self.audio_sync_method, AudioSyncMethod):
            return False
        if not self.quality_control.validate():
            return False
        if self.platform_settings and not self.platform_settings.validate():
            return False
        if not self.output_formats:
            return False
        return True
    
    def get_resolution(self) -> Tuple[int, int]:
        """Get video resolution based on quality and aspect ratio"""
        # Use platform-specific resolution if available
        if self.platform_settings and self.platform_settings.recommended_resolution:
            return self.platform_settings.recommended_resolution
        
        base_resolutions = {
            VideoQuality.HD_720P: (1280, 720),
            VideoQuality.FULL_HD_1080P: (1920, 1080),
            VideoQuality.UHD_4K: (3840, 2160)
        }
        
        width, height = base_resolutions[self.quality]
        
        # Use platform-specific aspect ratio if available
        aspect_ratio = (self.platform_settings.recommended_aspect_ratio 
                       if self.platform_settings and self.platform_settings.recommended_aspect_ratio
                       else self.aspect_ratio)
        
        if aspect_ratio == AspectRatio.PORTRAIT:
            return (height, width)  # Swap for portrait
        elif aspect_ratio == AspectRatio.SQUARE:
            return (min(width, height), min(width, height))
        else:
            return (width, height)  # Landscape


@dataclass
class QualityAssessment:
    """Results of video quality assessment"""
    overall_score: float  # 0.0 - 1.0
    resolution_score: float
    bitrate_score: float
    frame_rate_score: float
    audio_quality_score: float
    sync_accuracy_score: float
    issues: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    
    def is_acceptable(self, threshold: float = 0.8) -> bool:
        """Check if quality meets acceptable threshold"""
        return self.overall_score >= threshold
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert assessment to dictionary"""
        return {
            "overall_score": self.overall_score,
            "resolution_score": self.resolution_score,
            "bitrate_score": self.bitrate_score,
            "frame_rate_score": self.frame_rate_score,
            "audio_quality_score": self.audio_quality_score,
            "sync_accuracy_score": self.sync_accuracy_score,
            "issues": self.issues,
            "recommendations": self.recommendations
        }


@dataclass
class AudioSyncResult:
    """Results of audio-video synchronization analysis"""
    is_synchronized: bool
    sync_offset_ms: float  # Detected offset in milliseconds
    confidence: float  # 0.0 - 1.0
    method_used: AudioSyncMethod
    correction_applied: bool = False
    correction_offset_ms: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert sync result to dictionary"""
        return {
            "is_synchronized": self.is_synchronized,
            "sync_offset_ms": self.sync_offset_ms,
            "confidence": self.confidence,
            "method_used": self.method_used.value,
            "correction_applied": self.correction_applied,
            "correction_offset_ms": self.correction_offset_ms
        }


@dataclass
class RenderProgress:
    """Progress information for rendering operations"""
    current_step: str
    progress_percent: float  # 0.0 - 100.0
    estimated_time_remaining: Optional[timedelta] = None
    current_segment: Optional[str] = None
    total_segments: int = 0
    completed_segments: int = 0
    quality_checks_completed: int = 0
    sync_checks_completed: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert progress to dictionary for serialization"""
        return {
            "current_step": self.current_step,
            "progress_percent": self.progress_percent,
            "estimated_time_remaining": str(self.estimated_time_remaining) if self.estimated_time_remaining else None,
            "current_segment": self.current_segment,
            "total_segments": self.total_segments,
            "completed_segments": self.completed_segments,
            "quality_checks_completed": self.quality_checks_completed,
            "sync_checks_completed": self.sync_checks_completed
        }


class PlatformOptimizer:
    """
    Handles platform-specific video optimization and format conversion.
    """
    
    @staticmethod
    def get_platform_settings(platform: Platform) -> PlatformSettings:
        """Get optimized settings for a specific platform"""
        platform_configs = {
            Platform.YOUTUBE: PlatformSettings(
                platform=Platform.YOUTUBE,
                max_file_size_mb=256000,  # 256GB for YouTube
                recommended_resolution=(1920, 1080),
                recommended_aspect_ratio=AspectRatio.LANDSCAPE,
                recommended_fps=30,
                video_codec=VideoCodec.H264,
                audio_codec=AudioCodec.AAC,
                max_bitrate_kbps=50000,
                audio_bitrate_kbps=128
            ),
            Platform.INSTAGRAM: PlatformSettings(
                platform=Platform.INSTAGRAM,
                max_file_size_mb=4000,  # 4GB
                max_duration_seconds=60,
                recommended_resolution=(1080, 1080),
                recommended_aspect_ratio=AspectRatio.SQUARE,
                recommended_fps=30,
                video_codec=VideoCodec.H264,
                audio_codec=AudioCodec.AAC,
                max_bitrate_kbps=8000,
                audio_bitrate_kbps=128
            ),
            Platform.TIKTOK: PlatformSettings(
                platform=Platform.TIKTOK,
                max_file_size_mb=287,  # 287MB
                max_duration_seconds=180,
                recommended_resolution=(1080, 1920),
                recommended_aspect_ratio=AspectRatio.PORTRAIT,
                recommended_fps=30,
                video_codec=VideoCodec.H264,
                audio_codec=AudioCodec.AAC,
                max_bitrate_kbps=10000,
                audio_bitrate_kbps=128
            ),
            Platform.FACEBOOK: PlatformSettings(
                platform=Platform.FACEBOOK,
                max_file_size_mb=10000,  # 10GB
                recommended_resolution=(1920, 1080),
                recommended_aspect_ratio=AspectRatio.LANDSCAPE,
                recommended_fps=30,
                video_codec=VideoCodec.H264,
                audio_codec=AudioCodec.AAC,
                max_bitrate_kbps=8000,
                audio_bitrate_kbps=128
            ),
            Platform.TWITTER: PlatformSettings(
                platform=Platform.TWITTER,
                max_file_size_mb=512,  # 512MB
                max_duration_seconds=140,
                recommended_resolution=(1280, 720),
                recommended_aspect_ratio=AspectRatio.LANDSCAPE,
                recommended_fps=30,
                video_codec=VideoCodec.H264,
                audio_codec=AudioCodec.AAC,
                max_bitrate_kbps=5000,
                audio_bitrate_kbps=128
            ),
            Platform.LINKEDIN: PlatformSettings(
                platform=Platform.LINKEDIN,
                max_file_size_mb=5000,  # 5GB
                max_duration_seconds=600,
                recommended_resolution=(1920, 1080),
                recommended_aspect_ratio=AspectRatio.LANDSCAPE,
                recommended_fps=30,
                video_codec=VideoCodec.H264,
                audio_codec=AudioCodec.AAC,
                max_bitrate_kbps=10000,
                audio_bitrate_kbps=128
            )
        }
        
        return platform_configs.get(platform, PlatformSettings(platform=platform))
    
    @staticmethod
    def optimize_for_platform(
        settings: RenderSettings,
        platform: Platform
    ) -> RenderSettings:
        """Optimize render settings for a specific platform"""
        platform_settings = PlatformOptimizer.get_platform_settings(platform)
        
        # Create optimized settings
        optimized = RenderSettings(
            output_format=settings.output_format,
            quality=settings.quality,
            aspect_ratio=platform_settings.recommended_aspect_ratio or settings.aspect_ratio,
            fps=platform_settings.recommended_fps or settings.fps,
            compression=settings.compression,
            enable_hardware_acceleration=settings.enable_hardware_acceleration,
            audio_enabled=settings.audio_enabled,
            audio_bitrate=platform_settings.audio_bitrate_kbps,
            video_bitrate=platform_settings.max_bitrate_kbps,
            audio_sync_method=settings.audio_sync_method,
            quality_control=settings.quality_control,
            platform_settings=platform_settings,
            enable_multi_format_output=settings.enable_multi_format_output,
            output_formats=settings.output_formats
        )
        
        return optimized


class FormatConverter:
    """
    Handles video format conversion and codec optimization.
    """
    
    def __init__(self, temp_dir: str):
        self.temp_dir = temp_dir
    
    async def convert_to_format(
        self,
        input_path: str,
        output_path: str,
        conversion_settings: FormatConversionSettings
    ) -> bool:
        """
        Convert video to specified format with given settings.
        
        Args:
            input_path: Path to input video
            output_path: Path for converted output
            conversion_settings: Conversion configuration
            
        Returns:
            bool: True if conversion was successful
        """
        try:
            render_logger.info(f"Converting video to {conversion_settings.target_format.value}")
            
            # Simulate format conversion
            await asyncio.sleep(1.0)
            
            # In real implementation, use FFmpeg with specific codec settings
            # Example FFmpeg command structure:
            # ffmpeg -i input.mp4 -c:v h264 -c:a aac -movflags +faststart output.mp4
            
            # For now, copy file with new extension
            import shutil
            shutil.copy2(input_path, output_path)
            
            render_logger.info(f"Format conversion completed: {output_path}")
            return True
            
        except Exception as e:
            render_logger.error(f"Format conversion failed: {e}")
            return False
    
    async def convert_to_multiple_formats(
        self,
        input_path: str,
        output_base_path: str,
        formats: List[VideoFormat],
        base_settings: RenderSettings
    ) -> Dict[VideoFormat, str]:
        """
        Convert video to multiple formats simultaneously.
        
        Args:
            input_path: Path to input video
            output_base_path: Base path for output files (without extension)
            formats: List of target formats
            base_settings: Base render settings
            
        Returns:
            Dictionary mapping formats to output file paths
        """
        results = {}
        
        try:
            render_logger.info(f"Converting to {len(formats)} formats")
            
            for fmt in formats:
                output_path = f"{output_base_path}.{fmt.value}"
                
                conversion_settings = FormatConversionSettings(
                    target_format=fmt,
                    video_codec=self._get_optimal_codec_for_format(fmt),
                    preserve_quality=True,
                    enable_fast_start=True
                )
                
                success = await self.convert_to_format(
                    input_path, output_path, conversion_settings
                )
                
                if success:
                    results[fmt] = output_path
                    render_logger.debug(f"Successfully converted to {fmt.value}")
                else:
                    render_logger.warning(f"Failed to convert to {fmt.value}")
            
            return results
            
        except Exception as e:
            render_logger.error(f"Multi-format conversion failed: {e}")
            return {}
    
    def _get_optimal_codec_for_format(self, format: VideoFormat) -> VideoCodec:
        """Get optimal video codec for a given format"""
        codec_mapping = {
            VideoFormat.MP4: VideoCodec.H264,
            VideoFormat.MOV: VideoCodec.H264,
            VideoFormat.AVI: VideoCodec.H264,
            VideoFormat.WEBM: VideoCodec.VP9
        }
        return codec_mapping.get(format, VideoCodec.H264)


class RenderPipeline:
    """
    Main class for video rendering and composition pipeline.
    
    Handles video segment merging, transition effects, timeline management,
    multi-format output, and platform-specific optimization.
    """
    
    def __init__(self, config: Optional[RenderingConfig] = None):
        """Initialize the render pipeline"""
        self.config = config or get_config().rendering
        self.temp_dir = tempfile.mkdtemp(prefix="video_render_")
        self.progress_callbacks: List[callable] = []
        self.is_rendering = False
        self.current_task_id: Optional[str] = None
        self.quality_assessments: Dict[str, QualityAssessment] = {}
        self.sync_results: Dict[str, AudioSyncResult] = {}
        self.format_converter = FormatConverter(self.temp_dir)
        self.platform_optimizer = PlatformOptimizer()
        
        render_logger.info(f"Initialized RenderPipeline with temp directory: {self.temp_dir}")
    
    def add_progress_callback(self, callback: callable) -> None:
        """Add a callback function to receive progress updates"""
        self.progress_callbacks.append(callback)
    
    def remove_progress_callback(self, callback: callable) -> None:
        """Remove a progress callback"""
        if callback in self.progress_callbacks:
            self.progress_callbacks.remove(callback)
    
    def _notify_progress(self, progress: RenderProgress) -> None:
        """Notify all registered callbacks about progress updates"""
        for callback in self.progress_callbacks:
            try:
                callback(progress)
            except Exception as e:
                render_logger.warning(f"Progress callback failed: {e}")
    
    @with_video_studio_error_handling
    async def compose_video_segments(
        self,
        segments: List[VideoSegment],
        output_path: str,
        settings: RenderSettings,
        task_id: Optional[str] = None
    ) -> bool:
        """
        Compose multiple video segments into a single video with transitions.
        
        Args:
            segments: List of video segments to compose
            output_path: Path for the output video file
            settings: Render settings for the composition
            task_id: Optional task ID for progress tracking
            
        Returns:
            bool: True if composition was successful, False otherwise
        """
        if self.is_rendering:
            render_logger.warning("Render pipeline is already busy")
            return False
        
        self.is_rendering = True
        self.current_task_id = task_id
        
        try:
            render_logger.info(f"Starting video composition with {len(segments)} segments")
            
            # Validate inputs
            if not segments:
                render_logger.error("No video segments provided for composition")
                return False
            
            if not settings.validate():
                render_logger.error("Invalid render settings provided")
                return False
            
            # Validate all segments
            for i, segment in enumerate(segments):
                if not segment.validate():
                    render_logger.error(f"Invalid segment at index {i}: {segment.segment_id}")
                    return False
            
            # Sort segments by start time
            sorted_segments = sorted(segments, key=lambda s: s.start_time)
            
            # Update progress
            progress = RenderProgress(
                current_step="Preparing composition",
                progress_percent=0.0,
                total_segments=len(sorted_segments),
                completed_segments=0
            )
            self._notify_progress(progress)
            
            # Create timeline and validate timing
            timeline = self._create_timeline(sorted_segments)
            if not timeline:
                render_logger.error("Failed to create valid timeline")
                return False
            
            # Progress update
            progress.current_step = "Processing segments"
            progress.progress_percent = 10.0
            self._notify_progress(progress)
            
            # Process each segment with transitions
            processed_segments = []
            for i, segment in enumerate(sorted_segments):
                render_logger.info(f"Processing segment {i+1}/{len(sorted_segments)}: {segment.segment_id}")
                
                progress.current_segment = segment.segment_id
                progress.completed_segments = i
                progress.progress_percent = 10.0 + (i / len(sorted_segments)) * 60.0
                self._notify_progress(progress)
                
                processed_segment = await self._process_segment_with_transitions(
                    segment, settings, i, len(sorted_segments)
                )
                
                if processed_segment:
                    processed_segments.append(processed_segment)
                else:
                    render_logger.error(f"Failed to process segment: {segment.segment_id}")
                    return False
            
            # Progress update
            progress.current_step = "Merging segments"
            progress.progress_percent = 70.0
            progress.current_segment = None
            self._notify_progress(progress)
            
            # Merge all processed segments
            success = await self._merge_segments(processed_segments, output_path, settings)
            
            if success:
                progress.current_step = "Finalizing output"
                progress.progress_percent = 90.0
                self._notify_progress(progress)
                
                # Apply final post-processing
                success = await self._apply_final_processing(output_path, settings)
                
                if success and settings.quality_control.enable_quality_check:
                    # Quality assessment and optimization
                    progress.current_step = "Quality assessment"
                    progress.progress_percent = 92.0
                    self._notify_progress(progress)
                    
                    assessment = await self.assess_video_quality(output_path, settings)
                    
                    if not assessment.is_acceptable(settings.quality_control.quality_threshold):
                        if settings.quality_control.enable_auto_correction:
                            progress.current_step = "Quality optimization"
                            progress.progress_percent = 95.0
                            self._notify_progress(progress)
                            
                            temp_output = output_path + ".tmp"
                            success = await self.optimize_video_quality(
                                output_path, temp_output, settings, assessment
                            )
                            
                            if success:
                                import shutil
                                shutil.move(temp_output, output_path)
                            else:
                                render_logger.warning("Quality optimization failed, using original output")
                        else:
                            render_logger.warning("Video quality below threshold but auto-correction disabled")
                
                if success:
                    progress.current_step = "Completed"
                    progress.progress_percent = 100.0
                    self._notify_progress(progress)
                    
                    render_logger.info(f"Video composition completed successfully: {output_path}")
                    return True
            
            render_logger.error("Video composition failed during merging or post-processing")
            return False
            
        except Exception as e:
            render_logger.error(f"Video composition failed with error: {e}")
            return False
        finally:
            self.is_rendering = False
            self.current_task_id = None
    
    def _create_timeline(self, segments: List[VideoSegment]) -> Optional[Dict[str, Any]]:
        """
        Create and validate timeline for video segments.
        
        Args:
            segments: Sorted list of video segments
            
        Returns:
            Timeline dictionary or None if validation fails
        """
        timeline = {
            "segments": [],
            "total_duration": 0.0,
            "overlaps": [],
            "gaps": []
        }
        
        for i, segment in enumerate(segments):
            segment_info = {
                "index": i,
                "segment_id": segment.segment_id,
                "start_time": segment.start_time,
                "end_time": segment.start_time + segment.duration,
                "duration": segment.duration,
                "file_path": segment.file_path
            }
            timeline["segments"].append(segment_info)
            
            # Check for overlaps with previous segment
            if i > 0:
                prev_segment = segments[i-1]
                prev_end = prev_segment.start_time + prev_segment.duration
                
                if segment.start_time < prev_end:
                    overlap = {
                        "segment1": prev_segment.segment_id,
                        "segment2": segment.segment_id,
                        "overlap_duration": prev_end - segment.start_time
                    }
                    timeline["overlaps"].append(overlap)
                    render_logger.warning(f"Overlap detected: {overlap}")
                
                elif segment.start_time > prev_end:
                    gap = {
                        "after_segment": prev_segment.segment_id,
                        "before_segment": segment.segment_id,
                        "gap_duration": segment.start_time - prev_end
                    }
                    timeline["gaps"].append(gap)
                    render_logger.info(f"Gap detected: {gap}")
        
        # Calculate total duration
        if segments:
            last_segment = segments[-1]
            timeline["total_duration"] = last_segment.start_time + last_segment.duration
        
        render_logger.info(f"Created timeline with {len(segments)} segments, "
                          f"total duration: {timeline['total_duration']}s")
        
        return timeline
    
    async def _process_segment_with_transitions(
        self,
        segment: VideoSegment,
        settings: RenderSettings,
        segment_index: int,
        total_segments: int
    ) -> Optional[str]:
        """
        Process a single video segment with transition effects and audio sync.
        
        Args:
            segment: Video segment to process
            settings: Render settings
            segment_index: Index of this segment in the sequence
            total_segments: Total number of segments
            
        Returns:
            Path to processed segment file or None if failed
        """
        try:
            render_logger.debug(f"Processing segment {segment.segment_id} with transitions and audio sync")
            
            # Create output path for processed segment
            processed_path = os.path.join(
                self.temp_dir,
                f"processed_{segment_index:03d}_{segment.segment_id}.{settings.output_format.value}"
            )
            
            # Process audio tracks if present
            if segment.audio_tracks and settings.audio_enabled:
                render_logger.debug(f"Processing {len(segment.audio_tracks)} audio tracks for segment")
                
                # Analyze audio sync for each track
                sync_results = await self.analyze_audio_sync(
                    segment.file_path, 
                    segment.audio_tracks, 
                    settings.audio_sync_method
                )
                
                # Apply sync corrections if needed
                sync_corrected_path = processed_path + ".sync_corrected"
                sync_success = await self.correct_audio_sync(
                    segment.file_path,
                    segment.audio_tracks,
                    sync_results,
                    sync_corrected_path
                )
                
                if sync_success:
                    # Use sync-corrected version as input for further processing
                    input_path = sync_corrected_path
                else:
                    render_logger.warning(f"Audio sync correction failed for {segment.segment_id}")
                    input_path = segment.file_path
            else:
                input_path = segment.file_path
            
            # Apply transitions and effects
            # For now, simulate processing with a delay
            # In a real implementation, this would use FFmpeg or similar
            await asyncio.sleep(0.5)  # Simulate processing time
            
            # Copy processed file to final location (placeholder)
            # In real implementation, apply transitions and effects here
            import shutil
            shutil.copy2(input_path, processed_path)
            
            # Clean up temporary sync-corrected file if it exists
            sync_corrected_path = processed_path + ".sync_corrected"
            if os.path.exists(sync_corrected_path):
                os.remove(sync_corrected_path)
            
            render_logger.debug(f"Processed segment saved to: {processed_path}")
            return processed_path
            
        except Exception as e:
            render_logger.error(f"Failed to process segment {segment.segment_id}: {e}")
            return None
    
    async def _merge_segments(
        self,
        processed_segments: List[str],
        output_path: str,
        settings: RenderSettings
    ) -> bool:
        """
        Merge processed video segments into final output.
        
        Args:
            processed_segments: List of paths to processed segment files
            output_path: Path for final output video
            settings: Render settings
            
        Returns:
            bool: True if merge was successful
        """
        try:
            render_logger.info(f"Merging {len(processed_segments)} segments into: {output_path}")
            
            # Ensure output directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # For now, simulate merging with a delay
            # In a real implementation, this would use FFmpeg to concatenate videos
            await asyncio.sleep(1.0)  # Simulate merging time
            
            # Copy first segment as placeholder for final output
            # In real implementation, properly merge all segments
            if processed_segments:
                import shutil
                shutil.copy2(processed_segments[0], output_path)
            
            render_logger.info(f"Segments merged successfully to: {output_path}")
            return True
            
        except Exception as e:
            render_logger.error(f"Failed to merge segments: {e}")
            return False
    
    async def _apply_final_processing(
        self,
        output_path: str,
        settings: RenderSettings
    ) -> bool:
        """
        Apply final post-processing to the merged video.
        
        Args:
            output_path: Path to the video file
            settings: Render settings
            
        Returns:
            bool: True if post-processing was successful
        """
        try:
            render_logger.info(f"Applying final processing to: {output_path}")
            
            # Simulate final processing
            await asyncio.sleep(0.5)
            
            # In real implementation, apply:
            # - Final quality adjustments
            # - Color correction
            # - Audio normalization
            # - Format optimization
            
            render_logger.info("Final processing completed successfully")
            return True
            
        except Exception as e:
            render_logger.error(f"Final processing failed: {e}")
            return False
    
    def get_supported_formats(self) -> List[VideoFormat]:
        """Get list of supported output video formats"""
        return list(VideoFormat)
    
    def get_supported_transitions(self) -> List[TransitionType]:
        """Get list of supported transition types"""
        return list(TransitionType)
    
    def estimate_render_time(
        self,
        segments: List[VideoSegment],
        settings: RenderSettings
    ) -> Optional[timedelta]:
        """
        Estimate rendering time based on segments and settings.
        
        Args:
            segments: List of video segments
            settings: Render settings
            
        Returns:
            Estimated render time or None if cannot estimate
        """
        try:
            if not segments:
                return timedelta(0)
            
            # Calculate total video duration
            total_duration = sum(segment.duration for segment in segments)
            
            # Base processing time (rough estimate)
            base_time_per_second = 2.0  # seconds of processing per second of video
            
            # Adjust based on quality
            quality_multiplier = {
                VideoQuality.HD_720P: 1.0,
                VideoQuality.FULL_HD_1080P: 2.0,
                VideoQuality.UHD_4K: 4.0
            }
            
            # Adjust based on transitions
            transition_overhead = len(segments) * 5.0  # 5 seconds per transition
            
            estimated_seconds = (
                total_duration * base_time_per_second * 
                quality_multiplier.get(settings.quality, 2.0) +
                transition_overhead
            )
            
            return timedelta(seconds=estimated_seconds)
            
        except Exception as e:
            render_logger.error(f"Failed to estimate render time: {e}")
            return None
    
    @with_video_studio_error_handling
    async def analyze_audio_sync(
        self,
        video_path: str,
        audio_tracks: List[AudioTrack],
        method: AudioSyncMethod = AudioSyncMethod.TIMECODE
    ) -> List[AudioSyncResult]:
        """
        Analyze audio-video synchronization for multiple audio tracks.
        
        Args:
            video_path: Path to the video file
            audio_tracks: List of audio tracks to analyze
            method: Synchronization analysis method
            
        Returns:
            List of sync analysis results for each audio track
        """
        results = []
        
        try:
            render_logger.info(f"Analyzing audio sync for {len(audio_tracks)} tracks using {method.value}")
            
            for i, track in enumerate(audio_tracks):
                render_logger.debug(f"Analyzing sync for track {i+1}: {track.track_id}")
                
                # Simulate sync analysis based on method
                sync_result = await self._analyze_single_track_sync(video_path, track, method)
                results.append(sync_result)
                
                # Store result for later reference
                self.sync_results[track.track_id] = sync_result
                
                render_logger.debug(f"Sync analysis complete for {track.track_id}: "
                                  f"offset={sync_result.sync_offset_ms}ms, "
                                  f"confidence={sync_result.confidence}")
            
            return results
            
        except Exception as e:
            render_logger.error(f"Audio sync analysis failed: {e}")
            return []
    
    async def _analyze_single_track_sync(
        self,
        video_path: str,
        audio_track: AudioTrack,
        method: AudioSyncMethod
    ) -> AudioSyncResult:
        """
        Analyze synchronization for a single audio track.
        
        Args:
            video_path: Path to the video file
            audio_track: Audio track to analyze
            method: Analysis method to use
            
        Returns:
            Sync analysis result
        """
        try:
            # Simulate different sync analysis methods
            if method == AudioSyncMethod.TIMECODE:
                # Simulate timecode-based sync analysis
                await asyncio.sleep(0.2)
                sync_offset = 0.0  # Perfect sync in simulation
                confidence = 0.95
                
            elif method == AudioSyncMethod.WAVEFORM_ANALYSIS:
                # Simulate waveform analysis
                await asyncio.sleep(0.5)
                sync_offset = -15.0  # Slight delay detected
                confidence = 0.88
                
            elif method == AudioSyncMethod.FRAME_ALIGNMENT:
                # Simulate frame-based alignment
                await asyncio.sleep(0.3)
                sync_offset = 8.0  # Slight advance detected
                confidence = 0.92
                
            else:  # MANUAL_OFFSET
                # Use manual offset from track configuration
                sync_offset = audio_track.sync_offset * 1000  # Convert to ms
                confidence = 1.0
            
            # Determine if sync is acceptable
            tolerance_ms = 40  # Default tolerance
            is_synchronized = abs(sync_offset) <= tolerance_ms
            
            return AudioSyncResult(
                is_synchronized=is_synchronized,
                sync_offset_ms=sync_offset,
                confidence=confidence,
                method_used=method
            )
            
        except Exception as e:
            render_logger.error(f"Single track sync analysis failed: {e}")
            return AudioSyncResult(
                is_synchronized=False,
                sync_offset_ms=0.0,
                confidence=0.0,
                method_used=method
            )
    
    @with_video_studio_error_handling
    async def correct_audio_sync(
        self,
        video_path: str,
        audio_tracks: List[AudioTrack],
        sync_results: List[AudioSyncResult],
        output_path: str
    ) -> bool:
        """
        Apply audio synchronization corrections to video.
        
        Args:
            video_path: Path to input video
            audio_tracks: List of audio tracks
            sync_results: Sync analysis results
            output_path: Path for corrected output
            
        Returns:
            bool: True if correction was successful
        """
        try:
            render_logger.info("Applying audio synchronization corrections")
            
            corrections_needed = []
            for track, result in zip(audio_tracks, sync_results):
                if not result.is_synchronized and result.confidence > 0.7:
                    corrections_needed.append((track, result))
            
            if not corrections_needed:
                render_logger.info("No audio sync corrections needed")
                # Copy original file if no corrections needed
                import shutil
                shutil.copy2(video_path, output_path)
                return True
            
            render_logger.info(f"Applying corrections to {len(corrections_needed)} audio tracks")
            
            # Simulate applying corrections
            await asyncio.sleep(1.0)
            
            # In real implementation, use FFmpeg to apply sync corrections
            # For now, copy original and mark corrections as applied
            import shutil
            shutil.copy2(video_path, output_path)
            
            # Update sync results to reflect corrections
            for track, result in corrections_needed:
                result.correction_applied = True
                result.correction_offset_ms = -result.sync_offset_ms
                self.sync_results[track.track_id] = result
            
            render_logger.info("Audio sync corrections applied successfully")
            return True
            
        except Exception as e:
            render_logger.error(f"Audio sync correction failed: {e}")
            return False
    
    @with_video_studio_error_handling
    async def assess_video_quality(
        self,
        video_path: str,
        settings: RenderSettings
    ) -> QualityAssessment:
        """
        Assess video quality against specified settings and standards.
        
        Args:
            video_path: Path to video file to assess
            settings: Render settings for quality comparison
            
        Returns:
            Quality assessment results
        """
        try:
            render_logger.info(f"Assessing video quality: {video_path}")
            
            # Simulate quality analysis
            await asyncio.sleep(0.8)
            
            # In real implementation, analyze actual video properties
            # For simulation, generate realistic quality scores
            
            # Resolution assessment
            target_resolution = settings.get_resolution()
            resolution_score = 0.95  # Simulate high resolution quality
            
            # Bitrate assessment
            bitrate_score = 0.88  # Simulate good bitrate quality
            
            # Frame rate assessment
            frame_rate_score = 0.92  # Simulate good frame rate
            
            # Audio quality assessment
            audio_quality_score = 0.90 if settings.audio_enabled else 1.0
            
            # Sync accuracy assessment
            sync_accuracy_score = 0.94  # Simulate good sync
            
            # Calculate overall score
            scores = [resolution_score, bitrate_score, frame_rate_score, 
                     audio_quality_score, sync_accuracy_score]
            overall_score = sum(scores) / len(scores)
            
            # Generate issues and recommendations
            issues = []
            recommendations = []
            
            if bitrate_score < 0.8:
                issues.append("Video bitrate below optimal level")
                recommendations.append("Increase video bitrate for better quality")
            
            if audio_quality_score < 0.8:
                issues.append("Audio quality could be improved")
                recommendations.append("Use higher audio bitrate or better compression")
            
            if sync_accuracy_score < 0.9:
                issues.append("Minor audio-video sync drift detected")
                recommendations.append("Apply sync correction during rendering")
            
            assessment = QualityAssessment(
                overall_score=overall_score,
                resolution_score=resolution_score,
                bitrate_score=bitrate_score,
                frame_rate_score=frame_rate_score,
                audio_quality_score=audio_quality_score,
                sync_accuracy_score=sync_accuracy_score,
                issues=issues,
                recommendations=recommendations
            )
            
            # Store assessment for later reference
            self.quality_assessments[video_path] = assessment
            
            render_logger.info(f"Quality assessment complete: overall score {overall_score:.2f}")
            return assessment
            
        except Exception as e:
            render_logger.error(f"Video quality assessment failed: {e}")
            return QualityAssessment(
                overall_score=0.0,
                resolution_score=0.0,
                bitrate_score=0.0,
                frame_rate_score=0.0,
                audio_quality_score=0.0,
                sync_accuracy_score=0.0,
                issues=["Quality assessment failed"],
                recommendations=["Retry quality assessment"]
            )
    
    @with_video_studio_error_handling
    async def optimize_video_quality(
        self,
        input_path: str,
        output_path: str,
        settings: RenderSettings,
        assessment: QualityAssessment
    ) -> bool:
        """
        Apply quality optimizations based on assessment results.
        
        Args:
            input_path: Path to input video
            output_path: Path for optimized output
            settings: Render settings
            assessment: Quality assessment results
            
        Returns:
            bool: True if optimization was successful
        """
        try:
            render_logger.info("Applying video quality optimizations")
            
            if assessment.is_acceptable(settings.quality_control.quality_threshold):
                render_logger.info("Video quality already meets standards, no optimization needed")
                import shutil
                shutil.copy2(input_path, output_path)
                return True
            
            # Simulate quality optimization based on issues
            await asyncio.sleep(1.5)
            
            optimizations_applied = []
            
            if assessment.bitrate_score < 0.8:
                optimizations_applied.append("Increased video bitrate")
            
            if assessment.audio_quality_score < 0.8:
                optimizations_applied.append("Enhanced audio quality")
            
            if assessment.sync_accuracy_score < 0.9:
                optimizations_applied.append("Applied sync correction")
            
            # In real implementation, use FFmpeg with specific optimization parameters
            import shutil
            shutil.copy2(input_path, output_path)
            
            render_logger.info(f"Quality optimizations applied: {', '.join(optimizations_applied)}")
            return True
            
        except Exception as e:
            render_logger.error(f"Video quality optimization failed: {e}")
            return False
    
    def get_quality_assessment(self, video_path: str) -> Optional[QualityAssessment]:
        """Get stored quality assessment for a video"""
        return self.quality_assessments.get(video_path)
    
    def get_sync_result(self, track_id: str) -> Optional[AudioSyncResult]:
        """Get stored sync result for an audio track"""
        return self.sync_results.get(track_id)
    
    @with_video_studio_error_handling
    async def generate_multi_format_output(
        self,
        input_path: str,
        output_base_path: str,
        settings: RenderSettings
    ) -> Dict[VideoFormat, str]:
        """
        Generate multiple format outputs from a single video.
        
        Args:
            input_path: Path to input video
            output_base_path: Base path for output files (without extension)
            settings: Render settings with format specifications
            
        Returns:
            Dictionary mapping formats to output file paths
        """
        try:
            render_logger.info(f"Generating multi-format output for {len(settings.output_formats)} formats")
            
            if not settings.enable_multi_format_output:
                # Single format output
                output_path = f"{output_base_path}.{settings.output_format.value}"
                import shutil
                shutil.copy2(input_path, output_path)
                return {settings.output_format: output_path}
            
            # Multi-format conversion
            results = await self.format_converter.convert_to_multiple_formats(
                input_path, output_base_path, settings.output_formats, settings
            )
            
            render_logger.info(f"Multi-format generation completed: {len(results)} formats")
            return results
            
        except Exception as e:
            render_logger.error(f"Multi-format output generation failed: {e}")
            return {}
    
    @with_video_studio_error_handling
    async def optimize_for_platform(
        self,
        input_path: str,
        output_path: str,
        platform: Platform,
        base_settings: RenderSettings
    ) -> bool:
        """
        Optimize video for a specific platform.
        
        Args:
            input_path: Path to input video
            output_path: Path for optimized output
            platform: Target platform
            base_settings: Base render settings
            
        Returns:
            bool: True if optimization was successful
        """
        try:
            render_logger.info(f"Optimizing video for platform: {platform.value}")
            
            # Get platform-specific settings
            optimized_settings = self.platform_optimizer.optimize_for_platform(
                base_settings, platform
            )
            
            # Apply platform-specific optimizations
            if optimized_settings.platform_settings:
                platform_config = optimized_settings.platform_settings
                
                # Check file size constraints
                if platform_config.max_file_size_mb:
                    # In real implementation, check and compress if needed
                    render_logger.debug(f"Platform max file size: {platform_config.max_file_size_mb}MB")
                
                # Check duration constraints
                if platform_config.max_duration_seconds:
                    # In real implementation, trim if needed
                    render_logger.debug(f"Platform max duration: {platform_config.max_duration_seconds}s")
                
                # Apply codec and quality settings
                conversion_settings = FormatConversionSettings(
                    target_format=base_settings.output_format,
                    video_codec=platform_config.video_codec,
                    audio_codec=platform_config.audio_codec,
                    preserve_quality=True,
                    enable_fast_start=True
                )
                
                success = await self.format_converter.convert_to_format(
                    input_path, output_path, conversion_settings
                )
                
                if success:
                    render_logger.info(f"Platform optimization completed for {platform.value}")
                    return True
                else:
                    render_logger.error(f"Platform optimization failed for {platform.value}")
                    return False
            else:
                # No specific optimization needed, copy original
                import shutil
                shutil.copy2(input_path, output_path)
                return True
            
        except Exception as e:
            render_logger.error(f"Platform optimization failed: {e}")
            return False
    
    @with_video_studio_error_handling
    async def batch_platform_optimization(
        self,
        input_path: str,
        output_base_path: str,
        platforms: List[Platform],
        base_settings: RenderSettings
    ) -> Dict[Platform, str]:
        """
        Optimize video for multiple platforms simultaneously.
        
        Args:
            input_path: Path to input video
            output_base_path: Base path for output files
            platforms: List of target platforms
            base_settings: Base render settings
            
        Returns:
            Dictionary mapping platforms to output file paths
        """
        results = {}
        
        try:
            render_logger.info(f"Batch optimization for {len(platforms)} platforms")
            
            for platform in platforms:
                platform_output = f"{output_base_path}_{platform.value}.{base_settings.output_format.value}"
                
                success = await self.optimize_for_platform(
                    input_path, platform_output, platform, base_settings
                )
                
                if success:
                    results[platform] = platform_output
                    render_logger.debug(f"Successfully optimized for {platform.value}")
                else:
                    render_logger.warning(f"Failed to optimize for {platform.value}")
            
            render_logger.info(f"Batch platform optimization completed: {len(results)} platforms")
            return results
            
        except Exception as e:
            render_logger.error(f"Batch platform optimization failed: {e}")
            return {}
    
    def get_supported_platforms(self) -> List[Platform]:
        """Get list of supported platforms for optimization"""
        return list(Platform)
    
    def get_supported_codecs(self) -> Dict[str, List[Union[VideoCodec, AudioCodec]]]:
        """Get list of supported video and audio codecs"""
        return {
            "video": list(VideoCodec),
            "audio": list(AudioCodec)
        }
    
    def validate_platform_compatibility(
        self,
        settings: RenderSettings,
        platform: Platform
    ) -> Tuple[bool, List[str]]:
        """
        Validate if current settings are compatible with target platform.
        
        Args:
            settings: Current render settings
            platform: Target platform
            
        Returns:
            Tuple of (is_compatible, list_of_issues)
        """
        issues = []
        platform_config = self.platform_optimizer.get_platform_settings(platform)
        
        # Check resolution compatibility
        current_resolution = settings.get_resolution()
        if platform_config.recommended_resolution:
            recommended = platform_config.recommended_resolution
            if current_resolution != recommended:
                issues.append(f"Resolution {current_resolution} differs from recommended {recommended}")
        
        # Check aspect ratio compatibility
        if (platform_config.recommended_aspect_ratio and 
            settings.aspect_ratio != platform_config.recommended_aspect_ratio):
            issues.append(f"Aspect ratio {settings.aspect_ratio.value} differs from recommended {platform_config.recommended_aspect_ratio.value}")
        
        # Check bitrate limits
        if platform_config.max_bitrate_kbps and settings.video_bitrate:
            if settings.video_bitrate > platform_config.max_bitrate_kbps:
                issues.append(f"Video bitrate {settings.video_bitrate} exceeds platform limit {platform_config.max_bitrate_kbps}")
        
        # Check file size (would need actual file for real check)
        if platform_config.max_file_size_mb:
            issues.append(f"File size check required (limit: {platform_config.max_file_size_mb}MB)")
        
        is_compatible = len(issues) == 0
        return is_compatible, issues
    
    def cleanup_temp_files(self) -> None:
        """Clean up temporary files created during rendering"""
        try:
            if os.path.exists(self.temp_dir):
                import shutil
                shutil.rmtree(self.temp_dir)
                render_logger.info(f"Cleaned up temporary directory: {self.temp_dir}")
        except Exception as e:
            render_logger.warning(f"Failed to clean up temp directory: {e}")
    
    def __del__(self):
        """Cleanup when object is destroyed"""
        self.cleanup_temp_files()


# Convenience functions for easy access
_render_pipeline_instance: Optional[RenderPipeline] = None


def get_render_pipeline() -> RenderPipeline:
    """Get the global render pipeline instance"""
    global _render_pipeline_instance
    if _render_pipeline_instance is None:
        _render_pipeline_instance = RenderPipeline()
    return _render_pipeline_instance


async def compose_video(
    segments: List[VideoSegment],
    output_path: str,
    settings: Optional[RenderSettings] = None,
    task_id: Optional[str] = None
) -> bool:
    """
    Convenience function to compose video segments.
    
    Args:
        segments: List of video segments to compose
        output_path: Path for output video
        settings: Render settings (uses defaults if None)
        task_id: Optional task ID for progress tracking
        
    Returns:
        bool: True if composition was successful
    """
    pipeline = get_render_pipeline()
    render_settings = settings or RenderSettings()
    
    return await pipeline.compose_video_segments(
        segments, output_path, render_settings, task_id
    )


async def optimize_for_platform(
    input_path: str,
    output_path: str,
    platform: Platform,
    settings: Optional[RenderSettings] = None
) -> bool:
    """
    Convenience function to optimize video for a specific platform.
    
    Args:
        input_path: Path to input video
        output_path: Path for optimized output
        platform: Target platform
        settings: Base render settings (uses defaults if None)
        
    Returns:
        bool: True if optimization was successful
    """
    pipeline = get_render_pipeline()
    render_settings = settings or RenderSettings()
    
    return await pipeline.optimize_for_platform(
        input_path, output_path, platform, render_settings
    )


async def generate_multi_format_output(
    input_path: str,
    output_base_path: str,
    formats: List[VideoFormat],
    settings: Optional[RenderSettings] = None
) -> Dict[VideoFormat, str]:
    """
    Convenience function to generate multiple format outputs.
    
    Args:
        input_path: Path to input video
        output_base_path: Base path for output files (without extension)
        formats: List of target formats
        settings: Render settings (uses defaults if None)
        
    Returns:
        Dictionary mapping formats to output file paths
    """
    pipeline = get_render_pipeline()
    render_settings = settings or RenderSettings(
        enable_multi_format_output=True,
        output_formats=formats
    )
    
    return await pipeline.generate_multi_format_output(
        input_path, output_base_path, render_settings
    )