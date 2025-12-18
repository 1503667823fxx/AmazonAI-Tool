"""
Property-based tests for Video Studio video quality consistency

Tests that video rendering produces consistent quality output for identical inputs
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import tempfile
import asyncio
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass
import json

try:
    from app_utils.video_studio.render_pipeline import (
        RenderPipeline, RenderSettings, VideoSegment, AudioTrack, QualityAssessment,
        VideoFormat, VideoQuality, AspectRatio, CompressionLevel, AudioSyncMethod,
        QualityControlSettings, Platform, PlatformSettings
    )
    from app_utils.video_studio.models import Scene, VideoConfig
    from app_utils.video_studio.config import RenderingConfig
except ImportError as e:
    print(f"Failed to import required modules: {e}")
    sys.exit(1)


@dataclass
class QualityTestResult:
    """Results from a quality consistency test"""
    test_name: str
    input_hash: str
    quality_score: float
    resolution_score: float
    bitrate_score: float
    frame_rate_score: float
    audio_quality_score: float
    sync_accuracy_score: float
    issues: List[str]
    success: bool
    error_message: Optional[str] = None


class VideoQualityConsistencyTester:
    """Test class for video quality consistency property"""
    
    def __init__(self):
        """Initialize the tester with a temporary render pipeline"""
        # Create temporary directory for testing
        self.temp_dir = tempfile.mkdtemp()
        
        # Create render pipeline with test configuration
        self.render_pipeline = RenderPipeline()
        self.test_results: Dict[str, List[QualityTestResult]] = {}
        
        # Create test video segments
        self.test_segments = self._create_test_segments()
    
    def cleanup(self):
        """Clean up temporary files"""
        import shutil
        try:
            shutil.rmtree(self.temp_dir)
        except Exception as e:
            print(f"Warning: Failed to cleanup temp directory: {e}")
    
    def _create_test_segments(self) -> List[VideoSegment]:
        """Create test video segments for quality testing"""
        segments = []
        
        # Create mock video files for testing
        for i in range(3):
            segment_path = os.path.join(self.temp_dir, f"test_segment_{i}.mp4")
            
            # Create empty file as placeholder
            with open(segment_path, 'wb') as f:
                f.write(b"mock video data " * 100)  # Simple mock data
            
            # Create audio track
            audio_path = os.path.join(self.temp_dir, f"test_audio_{i}.wav")
            with open(audio_path, 'wb') as f:
                f.write(b"mock audio data " * 50)
            
            audio_track = AudioTrack(
                track_id=f"audio_{i}",
                file_path=audio_path,
                start_time=0.0,
                duration=5.0,
                volume=1.0
            )
            
            segment = VideoSegment(
                segment_id=f"segment_{i}",
                file_path=segment_path,
                start_time=i * 5.0,
                duration=5.0,
                audio_tracks=[audio_track]
            )
            
            segments.append(segment)
        
        return segments
    
    def _create_render_settings_variants(self) -> List[Tuple[str, RenderSettings]]:
        """Create different render settings for testing"""
        variants = []
        
        # Base settings
        base_settings = RenderSettings(
            output_format=VideoFormat.MP4,
            quality=VideoQuality.FULL_HD_1080P,
            aspect_ratio=AspectRatio.LANDSCAPE,
            fps=30,
            compression=CompressionLevel.HIGH,
            audio_enabled=True,
            audio_bitrate=128
        )
        variants.append(("base_1080p", base_settings))
        
        # HD settings
        hd_settings = RenderSettings(
            output_format=VideoFormat.MP4,
            quality=VideoQuality.HD_720P,
            aspect_ratio=AspectRatio.LANDSCAPE,
            fps=30,
            compression=CompressionLevel.HIGH,
            audio_enabled=True,
            audio_bitrate=128
        )
        variants.append(("hd_720p", hd_settings))
        
        # 4K settings
        uhd_settings = RenderSettings(
            output_format=VideoFormat.MP4,
            quality=VideoQuality.UHD_4K,
            aspect_ratio=AspectRatio.LANDSCAPE,
            fps=30,
            compression=CompressionLevel.HIGH,
            audio_enabled=True,
            audio_bitrate=256
        )
        variants.append(("uhd_4k", uhd_settings))
        
        # Portrait settings
        portrait_settings = RenderSettings(
            output_format=VideoFormat.MP4,
            quality=VideoQuality.FULL_HD_1080P,
            aspect_ratio=AspectRatio.PORTRAIT,
            fps=30,
            compression=CompressionLevel.HIGH,
            audio_enabled=True,
            audio_bitrate=128
        )
        variants.append(("portrait_1080p", portrait_settings))
        
        # High frame rate settings
        high_fps_settings = RenderSettings(
            output_format=VideoFormat.MP4,
            quality=VideoQuality.FULL_HD_1080P,
            aspect_ratio=AspectRatio.LANDSCAPE,
            fps=60,
            compression=CompressionLevel.HIGH,
            audio_enabled=True,
            audio_bitrate=128
        )
        variants.append(("high_fps_60", high_fps_settings))
        
        return variants
    
    def _calculate_input_hash(self, segments: List[VideoSegment], settings: RenderSettings) -> str:
        """Calculate a hash representing the input configuration"""
        import hashlib
        
        # Create a string representation of the input
        input_data = {
            "segments": [
                {
                    "segment_id": seg.segment_id,
                    "duration": seg.duration,
                    "start_time": seg.start_time,
                    "audio_tracks": len(seg.audio_tracks)
                }
                for seg in segments
            ],
            "settings": {
                "format": settings.output_format.value,
                "quality": settings.quality.value,
                "aspect_ratio": settings.aspect_ratio.value,
                "fps": settings.fps,
                "compression": settings.compression.value,
                "audio_enabled": settings.audio_enabled,
                "audio_bitrate": settings.audio_bitrate
            }
        }
        
        input_str = json.dumps(input_data, sort_keys=True)
        return hashlib.md5(input_str.encode()).hexdigest()[:8]
    
    async def test_identical_inputs_produce_consistent_quality(self) -> bool:
        """
        Test that identical inputs produce consistent quality scores
        """
        print("Testing identical inputs produce consistent quality...")
        
        settings_variants = self._create_render_settings_variants()
        
        for variant_name, settings in settings_variants:
            print(f"\nTesting variant: {variant_name}")
            
            input_hash = self._calculate_input_hash(self.test_segments, settings)
            
            # Run the same rendering multiple times
            quality_results = []
            
            for run in range(3):  # Test 3 runs for consistency
                try:
                    output_path = os.path.join(self.temp_dir, f"output_{variant_name}_run_{run}.mp4")
                    
                    # Compose video
                    success = await self.render_pipeline.compose_video_segments(
                        self.test_segments,
                        output_path,
                        settings
                    )
                    
                    if not success:
                        print(f"✗ Composition failed for {variant_name} run {run}")
                        return False
                    
                    # Assess quality
                    assessment = await self.render_pipeline.assess_video_quality(output_path, settings)
                    
                    result = QualityTestResult(
                        test_name=f"{variant_name}_run_{run}",
                        input_hash=input_hash,
                        quality_score=assessment.overall_score,
                        resolution_score=assessment.resolution_score,
                        bitrate_score=assessment.bitrate_score,
                        frame_rate_score=assessment.frame_rate_score,
                        audio_quality_score=assessment.audio_quality_score,
                        sync_accuracy_score=assessment.sync_accuracy_score,
                        issues=assessment.issues,
                        success=True
                    )
                    
                    quality_results.append(result)
                    print(f"  Run {run}: Quality score {assessment.overall_score:.3f}")
                    
                except Exception as e:
                    result = QualityTestResult(
                        test_name=f"{variant_name}_run_{run}",
                        input_hash=input_hash,
                        quality_score=0.0,
                        resolution_score=0.0,
                        bitrate_score=0.0,
                        frame_rate_score=0.0,
                        audio_quality_score=0.0,
                        sync_accuracy_score=0.0,
                        issues=[],
                        success=False,
                        error_message=str(e)
                    )
                    quality_results.append(result)
                    print(f"✗ Run {run} failed: {e}")
                    return False
            
            # Store results for analysis
            self.test_results[variant_name] = quality_results
            
            # Check consistency across runs
            if not self._verify_quality_consistency(quality_results, variant_name):
                return False
        
        return True
    
    def _verify_quality_consistency(self, results: List[QualityTestResult], variant_name: str) -> bool:
        """Verify that quality scores are consistent across runs"""
        if len(results) < 2:
            return True
        
        # Calculate consistency metrics
        quality_scores = [r.quality_score for r in results if r.success]
        resolution_scores = [r.resolution_score for r in results if r.success]
        bitrate_scores = [r.bitrate_score for r in results if r.success]
        
        if not quality_scores:
            print(f"✗ No successful runs for {variant_name}")
            return False
        
        # Check variance in quality scores (should be very low for identical inputs)
        quality_variance = self._calculate_variance(quality_scores)
        resolution_variance = self._calculate_variance(resolution_scores)
        bitrate_variance = self._calculate_variance(bitrate_scores)
        
        # Tolerance for consistency (very small variance allowed)
        max_variance = 0.01  # 1% variance allowed
        
        if quality_variance > max_variance:
            print(f"✗ Quality variance too high for {variant_name}: {quality_variance:.4f}")
            return False
        
        if resolution_variance > max_variance:
            print(f"✗ Resolution variance too high for {variant_name}: {resolution_variance:.4f}")
            return False
        
        if bitrate_variance > max_variance:
            print(f"✗ Bitrate variance too high for {variant_name}: {bitrate_variance:.4f}")
            return False
        
        print(f"✓ Quality consistency verified for {variant_name}")
        print(f"  Quality variance: {quality_variance:.4f}")
        print(f"  Resolution variance: {resolution_variance:.4f}")
        print(f"  Bitrate variance: {bitrate_variance:.4f}")
        
        return True
    
    def _calculate_variance(self, values: List[float]) -> float:
        """Calculate variance of a list of values"""
        if len(values) <= 1:
            return 0.0
        
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        return variance
    
    async def test_quality_meets_minimum_thresholds(self) -> bool:
        """
        Test that video quality meets minimum acceptable thresholds
        """
        print("Testing quality meets minimum thresholds...")
        
        settings_variants = self._create_render_settings_variants()
        
        # Define minimum quality thresholds
        min_thresholds = {
            "overall_score": 0.7,
            "resolution_score": 0.8,
            "bitrate_score": 0.7,
            "frame_rate_score": 0.8,
            "audio_quality_score": 0.7,
            "sync_accuracy_score": 0.8
        }
        
        for variant_name, settings in settings_variants:
            try:
                output_path = os.path.join(self.temp_dir, f"threshold_test_{variant_name}.mp4")
                
                # Compose video
                success = await self.render_pipeline.compose_video_segments(
                    self.test_segments,
                    output_path,
                    settings
                )
                
                if not success:
                    print(f"✗ Composition failed for threshold test {variant_name}")
                    return False
                
                # Assess quality
                assessment = await self.render_pipeline.assess_video_quality(output_path, settings)
                
                # Check each threshold
                quality_metrics = {
                    "overall_score": assessment.overall_score,
                    "resolution_score": assessment.resolution_score,
                    "bitrate_score": assessment.bitrate_score,
                    "frame_rate_score": assessment.frame_rate_score,
                    "audio_quality_score": assessment.audio_quality_score,
                    "sync_accuracy_score": assessment.sync_accuracy_score
                }
                
                for metric_name, actual_value in quality_metrics.items():
                    min_threshold = min_thresholds[metric_name]
                    
                    if actual_value < min_threshold:
                        print(f"✗ {variant_name} {metric_name} below threshold: {actual_value:.3f} < {min_threshold}")
                        return False
                
                print(f"✓ {variant_name} meets all quality thresholds")
                
            except Exception as e:
                print(f"✗ Threshold test failed for {variant_name}: {e}")
                return False
        
        return True
    
    async def test_audio_video_sync_consistency(self) -> bool:
        """
        Test that audio-video synchronization is consistent
        """
        print("Testing audio-video sync consistency...")
        
        # Test different sync methods
        sync_methods = [
            AudioSyncMethod.TIMECODE,
            AudioSyncMethod.WAVEFORM_ANALYSIS,
            AudioSyncMethod.FRAME_ALIGNMENT
        ]
        
        base_settings = RenderSettings(
            output_format=VideoFormat.MP4,
            quality=VideoQuality.FULL_HD_1080P,
            aspect_ratio=AspectRatio.LANDSCAPE,
            fps=30,
            audio_enabled=True
        )
        
        for sync_method in sync_methods:
            try:
                settings = RenderSettings(
                    output_format=base_settings.output_format,
                    quality=base_settings.quality,
                    aspect_ratio=base_settings.aspect_ratio,
                    fps=base_settings.fps,
                    audio_enabled=base_settings.audio_enabled,
                    audio_sync_method=sync_method
                )
                
                # Test sync analysis
                sync_results = await self.render_pipeline.analyze_audio_sync(
                    self.test_segments[0].file_path,
                    self.test_segments[0].audio_tracks,
                    sync_method
                )
                
                # Verify sync results
                for i, result in enumerate(sync_results):
                    if result.confidence < 0.5:
                        print(f"✗ Low confidence sync result for method {sync_method.value}: {result.confidence}")
                        return False
                    
                    # Check sync tolerance
                    if abs(result.sync_offset_ms) > 100:  # 100ms tolerance
                        print(f"✗ Sync offset too large for method {sync_method.value}: {result.sync_offset_ms}ms")
                        return False
                
                print(f"✓ Sync consistency verified for method {sync_method.value}")
                
            except Exception as e:
                print(f"✗ Sync test failed for method {sync_method.value}: {e}")
                return False
        
        return True
    
    async def test_platform_optimization_consistency(self) -> bool:
        """
        Test that platform-specific optimizations maintain quality consistency
        """
        print("Testing platform optimization consistency...")
        
        platforms = [Platform.YOUTUBE, Platform.INSTAGRAM, Platform.TIKTOK]
        
        base_settings = RenderSettings(
            output_format=VideoFormat.MP4,
            quality=VideoQuality.FULL_HD_1080P,
            fps=30,
            audio_enabled=True
        )
        
        for platform in platforms:
            try:
                input_path = os.path.join(self.temp_dir, "platform_test_input.mp4")
                output_path = os.path.join(self.temp_dir, f"platform_test_{platform.value}.mp4")
                
                # Create input video
                success = await self.render_pipeline.compose_video_segments(
                    self.test_segments[:1],  # Use single segment for platform test
                    input_path,
                    base_settings
                )
                
                if not success:
                    print(f"✗ Failed to create input for platform {platform.value}")
                    return False
                
                # Optimize for platform
                success = await self.render_pipeline.optimize_for_platform(
                    input_path,
                    output_path,
                    platform,
                    base_settings
                )
                
                if not success:
                    print(f"✗ Platform optimization failed for {platform.value}")
                    return False
                
                # Assess optimized quality
                assessment = await self.render_pipeline.assess_video_quality(output_path, base_settings)
                
                # Platform-optimized videos should still meet basic quality standards
                if assessment.overall_score < 0.6:  # Lower threshold for platform optimization
                    print(f"✗ Platform-optimized quality too low for {platform.value}: {assessment.overall_score}")
                    return False
                
                print(f"✓ Platform optimization maintains quality for {platform.value}: {assessment.overall_score:.3f}")
                
            except Exception as e:
                print(f"✗ Platform optimization test failed for {platform.value}: {e}")
                return False
        
        return True
    
    async def test_multi_format_quality_consistency(self) -> bool:
        """
        Test that multi-format output maintains consistent quality
        """
        print("Testing multi-format quality consistency...")
        
        formats = [VideoFormat.MP4, VideoFormat.MOV, VideoFormat.WEBM]
        
        base_settings = RenderSettings(
            quality=VideoQuality.FULL_HD_1080P,
            fps=30,
            audio_enabled=True,
            enable_multi_format_output=True,
            output_formats=formats
        )
        
        try:
            input_path = os.path.join(self.temp_dir, "multi_format_input.mp4")
            output_base = os.path.join(self.temp_dir, "multi_format_output")
            
            # Create input video
            success = await self.render_pipeline.compose_video_segments(
                self.test_segments[:2],  # Use two segments
                input_path,
                base_settings
            )
            
            if not success:
                print("✗ Failed to create input for multi-format test")
                return False
            
            # Generate multi-format output
            format_outputs = await self.render_pipeline.generate_multi_format_output(
                input_path,
                output_base,
                base_settings
            )
            
            if len(format_outputs) != len(formats):
                print(f"✗ Expected {len(formats)} formats, got {len(format_outputs)}")
                return False
            
            # Assess quality for each format
            quality_scores = {}
            
            for fmt, output_path in format_outputs.items():
                assessment = await self.render_pipeline.assess_video_quality(output_path, base_settings)
                quality_scores[fmt] = assessment.overall_score
                
                print(f"  {fmt.value}: Quality score {assessment.overall_score:.3f}")
            
            # Check quality consistency across formats
            scores = list(quality_scores.values())
            variance = self._calculate_variance(scores)
            
            if variance > 0.05:  # 5% variance allowed across formats
                print(f"✗ Quality variance across formats too high: {variance:.4f}")
                return False
            
            print(f"✓ Multi-format quality consistency verified (variance: {variance:.4f})")
            return True
            
        except Exception as e:
            print(f"✗ Multi-format quality test failed: {e}")
            return False


async def test_video_quality_consistency():
    """
    **Feature: video-studio-redesign, Property 9: 视频质量一致性**
    **Validates: Requirements 6.1, 6.3, 6.4**
    
    Property: For any same input parameters and configuration, the generation engine 
    should produce consistent quality video output, maintaining image clarity, 
    color accuracy, and audio-video synchronization
    """
    print("=" * 70)
    print("Testing Property 9: Video Quality Consistency")
    print("=" * 70)
    
    tester = VideoQualityConsistencyTester()
    
    try:
        # Run all quality consistency tests
        tests = [
            ("Identical inputs produce consistent quality", tester.test_identical_inputs_produce_consistent_quality()),
            ("Quality meets minimum thresholds", tester.test_quality_meets_minimum_thresholds()),
            ("Audio-video sync consistency", tester.test_audio_video_sync_consistency()),
            ("Platform optimization consistency", tester.test_platform_optimization_consistency()),
            ("Multi-format quality consistency", tester.test_multi_format_quality_consistency()),
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
    """Run all property-based tests for video quality consistency"""
    print("Running Property-Based Tests for Video Studio Video Quality Consistency")
    print("=" * 75)
    
    try:
        # Run the main property test
        success = asyncio.run(test_video_quality_consistency())
        
        if success:
            print("\n" + "=" * 75)
            print("✅ All property tests PASSED!")
            print("Property 9: 视频质量一致性 - VALIDATED")
            print("Requirements 6.1, 6.3, 6.4 - SATISFIED")
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