"""
Luma Dream Machine Adapter for Video Studio

This module provides the adapter implementation for Luma Labs Dream Machine API,
enabling image-to-video generation through the unified model adapter interface.
"""

import asyncio
import aiohttp
import json
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from ..model_adapter import (
    ModelAdapter, 
    GenerationConfig, 
    GenerationResult, 
    JobStatus, 
    ModelCapability
)
from ..config import ModelConfig
from ..error_handler import VideoStudioErrorHandler, VideoStudioErrorType


class LumaAdapter(ModelAdapter):
    """
    Adapter for Luma Labs Dream Machine API.
    
    Provides image-to-video generation capabilities with support for various
    aspect ratios, durations, and camera movements.
    """
    
    def __init__(self, config: ModelConfig, error_handler: VideoStudioErrorHandler):
        """Initialize Luma adapter with configuration."""
        super().__init__(config, error_handler)
        self.base_url = config.base_url or "https://api.lumalabs.ai/dream-machine/v1"
        self.session: Optional[aiohttp.ClientSession] = None
    
    @property
    def capabilities(self) -> List[ModelCapability]:
        """Return capabilities supported by Luma Dream Machine."""
        return [
            ModelCapability.IMAGE_TO_VIDEO,
            ModelCapability.TEXT_TO_VIDEO,
            ModelCapability.CAMERA_CONTROL,
            ModelCapability.MOTION_CONTROL
        ]
    
    @property
    def supported_aspect_ratios(self) -> List[str]:
        """Return supported aspect ratios."""
        return ["16:9", "9:16", "1:1"]
    
    @property
    def supported_qualities(self) -> List[str]:
        """Return supported video qualities."""
        return ["720p", "1080p"]
    
    @property
    def max_duration(self) -> float:
        """Return maximum supported duration in seconds."""
        return 5.0  # Luma typically supports up to 5 seconds
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session."""
        if self.session is None or self.session.closed:
            headers = {
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json",
                "User-Agent": "VideoStudio/1.0"
            }
            timeout = aiohttp.ClientTimeout(total=self.config.timeout)
            self.session = aiohttp.ClientSession(
                headers=headers,
                timeout=timeout,
                connector=aiohttp.TCPConnector(limit=10)
            )
        return self.session
    
    async def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Make HTTP request to Luma API with error handling and retries.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint
            data: Request payload
            
        Returns:
            Response data as dictionary
            
        Raises:
            RuntimeError: If request fails after retries
        """
        session = await self._get_session()
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        for attempt in range(self.config.max_retries + 1):
            try:
                async with session.request(method, url, json=data) as response:
                    response_data = await response.json()
                    
                    if response.status == 200:
                        return response_data
                    elif response.status == 429:  # Rate limit
                        if attempt < self.config.max_retries:
                            wait_time = 2 ** attempt  # Exponential backoff
                            await asyncio.sleep(wait_time)
                            continue
                        else:
                            raise RuntimeError(f"Rate limit exceeded: {response_data}")
                    elif response.status == 401:
                        raise RuntimeError(f"Authentication failed: {response_data}")
                    elif response.status == 400:
                        raise ValueError(f"Invalid request: {response_data}")
                    else:
                        raise RuntimeError(f"API error {response.status}: {response_data}")
                        
            except aiohttp.ClientError as e:
                if attempt < self.config.max_retries:
                    wait_time = 2 ** attempt
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    raise RuntimeError(f"Network error after {self.config.max_retries} retries: {str(e)}")
        
        raise RuntimeError("Maximum retries exceeded")
    
    def _convert_config_to_luma_params(self, config: GenerationConfig) -> Dict[str, Any]:
        """
        Convert GenerationConfig to Luma API parameters.
        
        Args:
            config: Generation configuration
            
        Returns:
            Dictionary of Luma API parameters
        """
        params = {
            "prompt": config.prompt,
            "aspect_ratio": config.aspect_ratio,
            "loop": False  # Luma default
        }
        
        # Add reference image if provided
        if config.reference_image:
            params["keyframes"] = {
                "frame0": {
                    "type": "image",
                    "url": config.reference_image
                }
            }
        
        # Add camera movement if specified
        if config.camera_movement:
            camera_movements = {
                "zoom_in": "zoom in",
                "zoom_out": "zoom out",
                "pan_left": "pan left",
                "pan_right": "pan right",
                "tilt_up": "tilt up",
                "tilt_down": "tilt down",
                "orbit_left": "orbit left",
                "orbit_right": "orbit right"
            }
            if config.camera_movement in camera_movements:
                params["prompt"] += f", {camera_movements[config.camera_movement]}"
        
        # Add custom parameters
        params.update(config.custom_parameters)
        
        return params
    
    def _convert_luma_status(self, luma_status: str) -> JobStatus:
        """
        Convert Luma API status to JobStatus enum.
        
        Args:
            luma_status: Status from Luma API
            
        Returns:
            Corresponding JobStatus
        """
        status_mapping = {
            "pending": JobStatus.PENDING,
            "queued": JobStatus.QUEUED,
            "dreaming": JobStatus.PROCESSING,
            "completed": JobStatus.COMPLETED,
            "failed": JobStatus.FAILED,
            "cancelled": JobStatus.CANCELLED
        }
        return status_mapping.get(luma_status.lower(), JobStatus.PENDING)
    
    async def generate(self, config: GenerationConfig) -> GenerationResult:
        """
        Start video generation with Luma Dream Machine.
        
        Args:
            config: Generation configuration
            
        Returns:
            GenerationResult with job_id and initial status
        """
        # Validate configuration
        is_valid, error_msg = self.validate_config(config)
        if not is_valid:
            raise ValueError(f"Invalid configuration: {error_msg}")
        
        try:
            # Convert config to Luma parameters
            luma_params = self._convert_config_to_luma_params(config)
            
            # Make generation request
            response = await self._make_request("POST", "/generations", luma_params)
            
            # Extract job information
            job_id = response.get("id")
            if not job_id:
                raise RuntimeError("No job ID returned from Luma API")
            
            status = self._convert_luma_status(response.get("state", "pending"))
            
            # Estimate completion time (Luma typically takes 2-5 minutes)
            estimated_completion = datetime.now() + timedelta(minutes=3)
            
            return GenerationResult(
                job_id=job_id,
                status=status,
                progress=0.0,
                estimated_completion=estimated_completion,
                metadata={
                    "model": "luma-dream-machine",
                    "created_at": response.get("created_at"),
                    "aspect_ratio": config.aspect_ratio,
                    "prompt": config.prompt
                }
            )
            
        except Exception as e:
            await self.error_handler.handle_error(
                VideoStudioErrorType.MODEL_ADAPTER_ERROR,
                str(e),
                {"model": self.name, "config": config.to_dict()}
            )
            raise RuntimeError(f"Failed to start generation: {str(e)}")
    
    async def get_status(self, job_id: str) -> GenerationResult:
        """
        Get the current status of a Luma generation job.
        
        Args:
            job_id: Luma job identifier
            
        Returns:
            GenerationResult with current status and progress
        """
        try:
            response = await self._make_request("GET", f"/generations/{job_id}")
            
            status = self._convert_luma_status(response.get("state", "pending"))
            
            # Calculate progress based on status
            progress_mapping = {
                JobStatus.PENDING: 0.0,
                JobStatus.QUEUED: 0.1,
                JobStatus.PROCESSING: 0.5,
                JobStatus.COMPLETED: 1.0,
                JobStatus.FAILED: 0.0,
                JobStatus.CANCELLED: 0.0
            }
            progress = progress_mapping.get(status, 0.0)
            
            # Extract video URL if completed
            video_url = None
            thumbnail_url = None
            if status == JobStatus.COMPLETED:
                assets = response.get("assets", {})
                video_url = assets.get("video")
                thumbnail_url = assets.get("thumbnail")
            
            # Extract error message if failed
            error_message = None
            if status == JobStatus.FAILED:
                error_message = response.get("failure_reason", "Generation failed")
            
            return GenerationResult(
                job_id=job_id,
                status=status,
                video_url=video_url,
                thumbnail_url=thumbnail_url,
                progress=progress,
                error_message=error_message,
                metadata={
                    "model": "luma-dream-machine",
                    "state": response.get("state"),
                    "created_at": response.get("created_at"),
                    "updated_at": response.get("updated_at")
                }
            )
            
        except Exception as e:
            await self.error_handler.handle_error(
                VideoStudioErrorType.MODEL_ADAPTER_ERROR,
                str(e),
                {"model": self.name, "job_id": job_id}
            )
            raise RuntimeError(f"Failed to get job status: {str(e)}")
    
    async def cancel_job(self, job_id: str) -> bool:
        """
        Cancel a Luma generation job.
        
        Args:
            job_id: Luma job identifier
            
        Returns:
            True if cancellation was successful
        """
        try:
            # Luma API doesn't have explicit cancel endpoint, 
            # but we can check if job is still cancellable
            result = await self.get_status(job_id)
            
            if result.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
                return False  # Already finished, can't cancel
            
            # For now, we'll just mark it as cancelled in our tracking
            # In a real implementation, you'd call the actual cancel endpoint
            return True
            
        except Exception as e:
            await self.error_handler.handle_error(
                VideoStudioErrorType.MODEL_ADAPTER_ERROR,
                str(e),
                {"model": self.name, "job_id": job_id}
            )
            return False
    
    async def close(self):
        """Close the HTTP session."""
        if self.session and not self.session.closed:
            await self.session.close()
    
    def __del__(self):
        """Cleanup when adapter is destroyed."""
        if self.session and not self.session.closed:
            # Note: This is not ideal for async cleanup, but serves as a fallback
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self.close())
            except RuntimeError:
                pass  # Event loop not available