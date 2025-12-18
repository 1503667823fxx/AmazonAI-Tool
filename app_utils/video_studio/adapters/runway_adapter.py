"""
Runway ML Adapter for Video Studio

This module provides the adapter implementation for Runway ML Gen-2 API,
enabling advanced video generation with motion control and style transfer capabilities.
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


class RunwayAdapter(ModelAdapter):
    """
    Adapter for Runway ML Gen-2 API.
    
    Provides advanced video generation capabilities including text-to-video,
    image-to-video, and sophisticated motion control features.
    """
    
    def __init__(self, config: ModelConfig, error_handler: VideoStudioErrorHandler):
        """Initialize Runway adapter with configuration."""
        super().__init__(config, error_handler)
        self.base_url = config.base_url or "https://api.runwayml.com/v1"
        self.session: Optional[aiohttp.ClientSession] = None
    
    @property
    def capabilities(self) -> List[ModelCapability]:
        """Return capabilities supported by Runway ML."""
        return [
            ModelCapability.IMAGE_TO_VIDEO,
            ModelCapability.TEXT_TO_VIDEO,
            ModelCapability.VIDEO_EXTENSION,
            ModelCapability.STYLE_TRANSFER,
            ModelCapability.CAMERA_CONTROL,
            ModelCapability.MOTION_CONTROL
        ]
    
    @property
    def supported_aspect_ratios(self) -> List[str]:
        """Return supported aspect ratios."""
        return ["16:9", "9:16", "1:1", "4:3", "3:4"]
    
    @property
    def supported_qualities(self) -> List[str]:
        """Return supported video qualities."""
        return ["720p", "1080p", "4k"]
    
    @property
    def max_duration(self) -> float:
        """Return maximum supported duration in seconds."""
        return 18.0  # Runway Gen-2 supports up to 18 seconds
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session."""
        if self.session is None or self.session.closed:
            headers = {
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json",
                "X-Runway-Version": "2024-09-13"  # API version
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
        Make HTTP request to Runway API with error handling and retries.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint
            data: Request payload
            
        Returns:
            Response data as dictionary
        """
        session = await self._get_session()
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        for attempt in range(self.config.max_retries + 1):
            try:
                async with session.request(method, url, json=data) as response:
                    response_data = await response.json()
                    
                    if response.status == 200 or response.status == 201:
                        return response_data
                    elif response.status == 429:  # Rate limit
                        if attempt < self.config.max_retries:
                            # Runway provides retry-after header
                            retry_after = int(response.headers.get('Retry-After', 2 ** attempt))
                            await asyncio.sleep(retry_after)
                            continue
                        else:
                            raise RuntimeError(f"Rate limit exceeded: {response_data}")
                    elif response.status == 401:
                        raise RuntimeError(f"Authentication failed: {response_data}")
                    elif response.status == 400:
                        raise ValueError(f"Invalid request: {response_data}")
                    elif response.status == 402:
                        raise RuntimeError(f"Insufficient credits: {response_data}")
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
    
    def _convert_config_to_runway_params(self, config: GenerationConfig) -> Dict[str, Any]:
        """
        Convert GenerationConfig to Runway API parameters.
        
        Args:
            config: Generation configuration
            
        Returns:
            Dictionary of Runway API parameters
        """
        # Determine generation mode based on inputs
        if config.reference_image:
            mode = "gen2"  # Image-to-video
            params = {
                "model": "gen2",
                "promptText": config.prompt,
                "init_image": config.reference_image,
                "motion_score": int(config.motion_strength * 10),  # 0-10 scale
            }
        else:
            mode = "gen2"  # Text-to-video
            params = {
                "model": "gen2",
                "promptText": config.prompt,
                "motion_score": int(config.motion_strength * 10),
            }
        
        # Add duration (Runway uses seconds)
        params["duration"] = min(config.duration, self.max_duration)
        
        # Add aspect ratio
        aspect_ratio_mapping = {
            "16:9": "1920:1080",
            "9:16": "1080:1920", 
            "1:1": "1080:1080",
            "4:3": "1440:1080",
            "3:4": "1080:1440"
        }
        params["resolution"] = aspect_ratio_mapping.get(config.aspect_ratio, "1920:1080")
        
        # Add quality settings
        if config.quality == "4k":
            params["upscale"] = True
        
        # Add camera movement if specified
        if config.camera_movement:
            camera_controls = {
                "zoom_in": {"zoom": 1.2},
                "zoom_out": {"zoom": 0.8},
                "pan_left": {"pan": -0.3},
                "pan_right": {"pan": 0.3},
                "tilt_up": {"tilt": 0.3},
                "tilt_down": {"tilt": -0.3}
            }
            if config.camera_movement in camera_controls:
                params["camera_motion"] = camera_controls[config.camera_movement]
        
        # Add seed for reproducibility
        if config.seed:
            params["seed"] = config.seed
        
        # Add style if specified
        if config.style:
            params["style"] = config.style
        
        # Add custom parameters
        params.update(config.custom_parameters)
        
        return params
    
    def _convert_runway_status(self, runway_status: str) -> JobStatus:
        """
        Convert Runway API status to JobStatus enum.
        
        Args:
            runway_status: Status from Runway API
            
        Returns:
            Corresponding JobStatus
        """
        status_mapping = {
            "PENDING": JobStatus.PENDING,
            "RUNNING": JobStatus.PROCESSING,
            "SUCCEEDED": JobStatus.COMPLETED,
            "FAILED": JobStatus.FAILED,
            "CANCELLED": JobStatus.CANCELLED,
            "THROTTLED": JobStatus.QUEUED
        }
        return status_mapping.get(runway_status.upper(), JobStatus.PENDING)
    
    async def generate(self, config: GenerationConfig) -> GenerationResult:
        """
        Start video generation with Runway ML.
        
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
            # Convert config to Runway parameters
            runway_params = self._convert_config_to_runway_params(config)
            
            # Make generation request
            response = await self._make_request("POST", "/image-to-video", runway_params)
            
            # Extract job information
            job_id = response.get("id")
            if not job_id:
                raise RuntimeError("No job ID returned from Runway API")
            
            status = self._convert_runway_status(response.get("status", "PENDING"))
            
            # Estimate completion time (Runway typically takes 1-3 minutes)
            estimated_completion = datetime.now() + timedelta(minutes=2)
            
            return GenerationResult(
                job_id=job_id,
                status=status,
                progress=0.0,
                estimated_completion=estimated_completion,
                metadata={
                    "model": "runway-gen2",
                    "created_at": response.get("createdAt"),
                    "aspect_ratio": config.aspect_ratio,
                    "prompt": config.prompt,
                    "duration": config.duration
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
        Get the current status of a Runway generation job.
        
        Args:
            job_id: Runway job identifier
            
        Returns:
            GenerationResult with current status and progress
        """
        try:
            response = await self._make_request("GET", f"/tasks/{job_id}")
            
            status = self._convert_runway_status(response.get("status", "PENDING"))
            
            # Calculate progress based on status and progress field
            progress = 0.0
            if "progress" in response:
                progress = float(response["progress"]) / 100.0
            else:
                # Fallback progress mapping
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
                output = response.get("output", [])
                if output:
                    video_url = output[0] if isinstance(output, list) else output
                
                # Runway sometimes provides thumbnail
                if "thumbnailUrl" in response:
                    thumbnail_url = response["thumbnailUrl"]
            
            # Extract error message if failed
            error_message = None
            if status == JobStatus.FAILED:
                error_message = response.get("failure", {}).get("reason", "Generation failed")
            
            return GenerationResult(
                job_id=job_id,
                status=status,
                video_url=video_url,
                thumbnail_url=thumbnail_url,
                progress=progress,
                error_message=error_message,
                metadata={
                    "model": "runway-gen2",
                    "status": response.get("status"),
                    "created_at": response.get("createdAt"),
                    "updated_at": response.get("updatedAt"),
                    "progress_detail": response.get("progressText")
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
        Cancel a Runway generation job.
        
        Args:
            job_id: Runway job identifier
            
        Returns:
            True if cancellation was successful
        """
        try:
            # Check current status first
            result = await self.get_status(job_id)
            
            if result.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
                return False  # Already finished, can't cancel
            
            # Make cancel request
            await self._make_request("POST", f"/tasks/{job_id}/cancel")
            return True
            
        except Exception as e:
            await self.error_handler.handle_error(
                VideoStudioErrorType.MODEL_ADAPTER_ERROR,
                str(e),
                {"model": self.name, "job_id": job_id}
            )
            return False
    
    async def get_account_info(self) -> Dict[str, Any]:
        """
        Get account information including credits and usage.
        
        Returns:
            Dictionary containing account information
        """
        try:
            response = await self._make_request("GET", "/account")
            return {
                "credits_remaining": response.get("creditsRemaining", 0),
                "credits_used": response.get("creditsUsed", 0),
                "plan": response.get("plan", "unknown"),
                "usage_limit": response.get("usageLimit", 0)
            }
        except Exception as e:
            await self.error_handler.handle_error(
                VideoStudioErrorType.MODEL_ADAPTER_ERROR,
                str(e),
                {"model": self.name, "operation": "get_account_info"}
            )
            return {}
    
    async def close(self):
        """Close the HTTP session."""
        if self.session and not self.session.closed:
            await self.session.close()
    
    def __del__(self):
        """Cleanup when adapter is destroyed."""
        if self.session and not self.session.closed:
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self.close())
            except RuntimeError:
                pass