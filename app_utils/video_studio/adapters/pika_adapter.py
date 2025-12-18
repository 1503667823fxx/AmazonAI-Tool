"""
Pika Labs Adapter for Video Studio

This module provides the adapter implementation for Pika Labs API,
enabling creative video generation with unique artistic styles and effects.
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


class PikaAdapter(ModelAdapter):
    """
    Adapter for Pika Labs API.
    
    Provides creative video generation with artistic styles, effects,
    and unique visual transformations.
    """
    
    def __init__(self, config: ModelConfig, error_handler: VideoStudioErrorHandler):
        """Initialize Pika adapter with configuration."""
        super().__init__(config, error_handler)
        self.base_url = config.base_url or "https://api.pika.art/v1"
        self.session: Optional[aiohttp.ClientSession] = None
    
    @property
    def capabilities(self) -> List[ModelCapability]:
        """Return capabilities supported by Pika Labs."""
        return [
            ModelCapability.IMAGE_TO_VIDEO,
            ModelCapability.TEXT_TO_VIDEO,
            ModelCapability.STYLE_TRANSFER,
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
        return 3.0  # Pika typically supports up to 3 seconds
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session."""
        if self.session is None or self.session.closed:
            headers = {
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json",
                "X-Pika-Client": "VideoStudio/1.0"
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
        Make HTTP request to Pika API with error handling and retries.
        
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
                            wait_time = 2 ** attempt  # Exponential backoff
                            await asyncio.sleep(wait_time)
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
    
    def _convert_config_to_pika_params(self, config: GenerationConfig) -> Dict[str, Any]:
        """
        Convert GenerationConfig to Pika API parameters.
        
        Args:
            config: Generation configuration
            
        Returns:
            Dictionary of Pika API parameters
        """
        params = {
            "prompt": config.prompt,
            "aspectRatio": config.aspect_ratio,
            "options": {
                "frameRate": 24,
                "motion": int(config.motion_strength * 4),  # Pika uses 1-4 scale
                "boomerang": False,
                "loop": False
            }
        }
        
        # Add reference image if provided
        if config.reference_image:
            params["image"] = config.reference_image
            params["promptStrength"] = 0.8  # How much to follow the prompt vs image
        
        # Add style if specified
        if config.style:
            style_mapping = {
                "anime": "anime",
                "realistic": "photorealistic", 
                "cartoon": "cartoon",
                "artistic": "artistic",
                "cinematic": "cinematic",
                "vintage": "vintage",
                "cyberpunk": "cyberpunk",
                "fantasy": "fantasy"
            }
            if config.style.lower() in style_mapping:
                params["options"]["style"] = style_mapping[config.style.lower()]
        
        # Add camera movement effects
        if config.camera_movement:
            camera_effects = {
                "zoom_in": {"camera": "zoom", "direction": "in"},
                "zoom_out": {"camera": "zoom", "direction": "out"},
                "pan_left": {"camera": "pan", "direction": "left"},
                "pan_right": {"camera": "pan", "direction": "right"},
                "rotate_cw": {"camera": "rotate", "direction": "clockwise"},
                "rotate_ccw": {"camera": "rotate", "direction": "counterclockwise"}
            }
            if config.camera_movement in camera_effects:
                params["options"].update(camera_effects[config.camera_movement])
        
        # Add seed for reproducibility
        if config.seed:
            params["options"]["seed"] = config.seed
        
        # Add quality settings
        if config.quality == "1080p":
            params["options"]["hd"] = True
        
        # Add custom parameters
        if config.custom_parameters:
            params["options"].update(config.custom_parameters)
        
        return params
    
    def _convert_pika_status(self, pika_status: str) -> JobStatus:
        """
        Convert Pika API status to JobStatus enum.
        
        Args:
            pika_status: Status from Pika API
            
        Returns:
            Corresponding JobStatus
        """
        status_mapping = {
            "pending": JobStatus.PENDING,
            "queued": JobStatus.QUEUED,
            "generating": JobStatus.PROCESSING,
            "completed": JobStatus.COMPLETED,
            "failed": JobStatus.FAILED,
            "cancelled": JobStatus.CANCELLED,
            "error": JobStatus.FAILED
        }
        return status_mapping.get(pika_status.lower(), JobStatus.PENDING)
    
    async def generate(self, config: GenerationConfig) -> GenerationResult:
        """
        Start video generation with Pika Labs.
        
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
            # Convert config to Pika parameters
            pika_params = self._convert_config_to_pika_params(config)
            
            # Make generation request
            response = await self._make_request("POST", "/generate", pika_params)
            
            # Extract job information
            job_id = response.get("id") or response.get("jobId")
            if not job_id:
                raise RuntimeError("No job ID returned from Pika API")
            
            status = self._convert_pika_status(response.get("status", "pending"))
            
            # Estimate completion time (Pika typically takes 1-2 minutes)
            estimated_completion = datetime.now() + timedelta(minutes=1.5)
            
            return GenerationResult(
                job_id=job_id,
                status=status,
                progress=0.0,
                estimated_completion=estimated_completion,
                metadata={
                    "model": "pika-labs",
                    "created_at": response.get("createdAt"),
                    "aspect_ratio": config.aspect_ratio,
                    "prompt": config.prompt,
                    "style": config.style
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
        Get the current status of a Pika generation job.
        
        Args:
            job_id: Pika job identifier
            
        Returns:
            GenerationResult with current status and progress
        """
        try:
            response = await self._make_request("GET", f"/jobs/{job_id}")
            
            status = self._convert_pika_status(response.get("status", "pending"))
            
            # Calculate progress
            progress = 0.0
            if "progress" in response:
                progress = float(response["progress"]) / 100.0
            else:
                # Fallback progress mapping
                progress_mapping = {
                    JobStatus.PENDING: 0.0,
                    JobStatus.QUEUED: 0.1,
                    JobStatus.PROCESSING: 0.6,
                    JobStatus.COMPLETED: 1.0,
                    JobStatus.FAILED: 0.0,
                    JobStatus.CANCELLED: 0.0
                }
                progress = progress_mapping.get(status, 0.0)
            
            # Extract video URL if completed
            video_url = None
            thumbnail_url = None
            if status == JobStatus.COMPLETED:
                result = response.get("result", {})
                video_url = result.get("videoUrl") or result.get("url")
                thumbnail_url = result.get("thumbnailUrl") or result.get("thumbnail")
            
            # Extract error message if failed
            error_message = None
            if status == JobStatus.FAILED:
                error_message = response.get("error", {}).get("message", "Generation failed")
            
            return GenerationResult(
                job_id=job_id,
                status=status,
                video_url=video_url,
                thumbnail_url=thumbnail_url,
                progress=progress,
                error_message=error_message,
                metadata={
                    "model": "pika-labs",
                    "status": response.get("status"),
                    "created_at": response.get("createdAt"),
                    "updated_at": response.get("updatedAt"),
                    "generation_time": response.get("generationTime")
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
        Cancel a Pika generation job.
        
        Args:
            job_id: Pika job identifier
            
        Returns:
            True if cancellation was successful
        """
        try:
            # Check current status first
            result = await self.get_status(job_id)
            
            if result.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
                return False  # Already finished, can't cancel
            
            # Make cancel request
            await self._make_request("DELETE", f"/jobs/{job_id}")
            return True
            
        except Exception as e:
            await self.error_handler.handle_error(
                VideoStudioErrorType.MODEL_ADAPTER_ERROR,
                str(e),
                {"model": self.name, "job_id": job_id}
            )
            return False
    
    async def get_styles(self) -> List[Dict[str, Any]]:
        """
        Get available styles from Pika Labs.
        
        Returns:
            List of available styles with metadata
        """
        try:
            response = await self._make_request("GET", "/styles")
            return response.get("styles", [])
        except Exception as e:
            await self.error_handler.handle_error(
                VideoStudioErrorType.MODEL_ADAPTER_ERROR,
                str(e),
                {"model": self.name, "operation": "get_styles"}
            )
            return []
    
    async def get_usage_stats(self) -> Dict[str, Any]:
        """
        Get usage statistics for the account.
        
        Returns:
            Dictionary containing usage information
        """
        try:
            response = await self._make_request("GET", "/account/usage")
            return {
                "generations_used": response.get("generationsUsed", 0),
                "generations_limit": response.get("generationsLimit", 0),
                "reset_date": response.get("resetDate"),
                "plan_type": response.get("planType", "free")
            }
        except Exception as e:
            await self.error_handler.handle_error(
                VideoStudioErrorType.MODEL_ADAPTER_ERROR,
                str(e),
                {"model": self.name, "operation": "get_usage_stats"}
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