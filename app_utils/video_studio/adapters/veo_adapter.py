"""
Google Veo 3.1 Adapter for Video Studio

This module provides the adapter implementation for Google Veo 3.1 Generate Preview API,
enabling text-to-video and image-to-video generation through the unified model adapter interface.
"""

import asyncio
import aiohttp
import json
import base64
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

try:
    import streamlit as st
    HAS_STREAMLIT = True
except ImportError:
    HAS_STREAMLIT = False

try:
    from google.auth.transport.requests import Request
    from google.oauth2 import service_account
    import google.auth
    HAS_GOOGLE_AUTH = True
except ImportError:
    HAS_GOOGLE_AUTH = False


class VeoAdapter(ModelAdapter):
    """
    Adapter for Google Veo 3.1 Generate Preview API.
    
    Provides text-to-video and image-to-video generation capabilities with support for
    various aspect ratios, durations, and reference images.
    """
    
    def __init__(self, config: ModelConfig, error_handler: VideoStudioErrorHandler):
        """Initialize Veo adapter with configuration."""
        super().__init__(config, error_handler)
        
        # Google Cloud configuration
        self.project_id = self._get_project_id()
        self.location = "us-central1"  # Default location for Veo
        self.model_id = "veo-3.1-generate-preview"
        
        # Build API endpoint
        self.base_url = f"https://{self.location}-aiplatform.googleapis.com/v1/projects/{self.project_id}/locations/{self.location}/publishers/google/models/{self.model_id}"
        
        self.session: Optional[aiohttp.ClientSession] = None
        self._access_token: Optional[str] = None
        self._token_expiry: Optional[datetime] = None
    
    def _get_project_id(self) -> str:
        """Get Google Cloud project ID from configuration or environment."""
        # Try to get from config first
        project_id = self.config.parameters.get("project_id")
        if project_id:
            return project_id
        
        # Try to get from Streamlit secrets
        if HAS_STREAMLIT:
            try:
                project_id = st.secrets.get("GOOGLE_CLOUD_PROJECT_ID")
                if project_id:
                    return project_id
            except:
                pass
        
        # Try to get from environment
        import os
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("GOOGLE_CLOUD_PROJECT_ID")
        if project_id:
            return project_id
        
        # Default fallback - this should be configured properly
        raise ValueError("Google Cloud Project ID not configured. Please set GOOGLE_CLOUD_PROJECT_ID in secrets or config.")
    
    async def _get_access_token(self) -> str:
        """Get Google Cloud access token."""
        # Check if we have a valid cached token
        if self._access_token and self._token_expiry and datetime.now() < self._token_expiry:
            return self._access_token
        
        if not HAS_GOOGLE_AUTH:
            raise RuntimeError("Google Auth libraries not available. Please install google-auth and google-auth-oauthlib.")
        
        try:
            # Try to get default credentials
            credentials, project = google.auth.default(
                scopes=['https://www.googleapis.com/auth/cloud-platform']
            )
            
            # Refresh the credentials
            request = Request()
            credentials.refresh(request)
            
            self._access_token = credentials.token
            # Set expiry to 50 minutes from now (tokens typically last 1 hour)
            self._token_expiry = datetime.now() + timedelta(minutes=50)
            
            return self._access_token
            
        except Exception as e:
            # Fallback: try to use gcloud auth if available
            try:
                import subprocess
                result = subprocess.run(
                    ['gcloud', 'auth', 'print-access-token'],
                    capture_output=True,
                    text=True,
                    check=True
                )
                token = result.stdout.strip()
                self._access_token = token
                self._token_expiry = datetime.now() + timedelta(minutes=50)
                return token
            except Exception as gcloud_error:
                raise RuntimeError(f"Failed to get access token: {str(e)}. Gcloud fallback also failed: {str(gcloud_error)}")
    
    @property
    def capabilities(self) -> List[ModelCapability]:
        """Return capabilities supported by Veo 3.1."""
        return [
            ModelCapability.TEXT_TO_VIDEO,
            ModelCapability.IMAGE_TO_VIDEO,
            ModelCapability.REFERENCE_IMAGES,
            ModelCapability.ASPECT_RATIO_CONTROL,
            ModelCapability.DURATION_CONTROL
        ]
    
    @property
    def supported_aspect_ratios(self) -> List[str]:
        """Return supported aspect ratios."""
        return ["16:9", "9:16"]
    
    @property
    def supported_qualities(self) -> List[str]:
        """Return supported video qualities."""
        return ["720p", "1080p"]
    
    @property
    def max_duration(self) -> float:
        """Return maximum supported duration in seconds."""
        return 8.0  # Veo 3.1 supports up to 8 seconds
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session with authentication."""
        if self.session is None or self.session.closed:
            access_token = await self._get_access_token()
            headers = {
                "Authorization": f"Bearer {access_token}",
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
        Make HTTP request to Veo API with error handling and retries.
        
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
        url = f"{self.base_url}{endpoint}"
        
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
                        # Token might be expired, refresh and retry
                        self._access_token = None
                        self._token_expiry = None
                        if attempt < self.config.max_retries:
                            session = await self._get_session()  # This will refresh the token
                            continue
                        else:
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
    
    def _encode_image_to_base64(self, image_path: str) -> tuple[str, str]:
        """
        Encode image file to base64 and determine MIME type.
        
        Args:
            image_path: Path to image file
            
        Returns:
            Tuple of (base64_encoded_data, mime_type)
        """
        import mimetypes
        
        # Determine MIME type
        mime_type, _ = mimetypes.guess_type(image_path)
        if not mime_type or not mime_type.startswith('image/'):
            mime_type = 'image/jpeg'  # Default fallback
        
        # Read and encode image
        with open(image_path, 'rb') as image_file:
            image_data = image_file.read()
            base64_data = base64.b64encode(image_data).decode('utf-8')
        
        return base64_data, mime_type
    
    def _convert_config_to_veo_params(self, config: GenerationConfig) -> Dict[str, Any]:
        """
        Convert GenerationConfig to Veo API parameters.
        
        Args:
            config: Generation configuration
            
        Returns:
            Dictionary of Veo API parameters
        """
        # Build instances
        instance = {
            "prompt": config.prompt
        }
        
        # Add reference image if provided
        if config.reference_image:
            try:
                base64_data, mime_type = self._encode_image_to_base64(config.reference_image)
                instance["image"] = {
                    "bytesBase64Encoded": base64_data,
                    "mimeType": mime_type
                }
            except Exception as e:
                # If image encoding fails, continue without reference image
                print(f"Warning: Failed to encode reference image: {e}")
        
        # Add reference images if provided in custom parameters
        reference_images = config.custom_parameters.get("reference_images", [])
        if reference_images:
            instance["referenceImages"] = []
            for ref_img in reference_images[:3]:  # Max 3 reference images
                try:
                    if isinstance(ref_img, dict) and "path" in ref_img:
                        base64_data, mime_type = self._encode_image_to_base64(ref_img["path"])
                        instance["referenceImages"].append({
                            "image": {
                                "bytesBase64Encoded": base64_data,
                                "mimeType": mime_type
                            },
                            "referenceType": ref_img.get("type", "ASSET")
                        })
                except Exception as e:
                    print(f"Warning: Failed to encode reference image: {e}")
        
        # Build parameters
        parameters = {
            "aspectRatio": config.aspect_ratio,
            "durationSeconds": int(config.duration or 4),
            "sampleCount": 1,  # Generate one video
            "resolution": "1080p" if config.quality == "1080p" else "720p"
        }
        
        # Add optional parameters
        if config.custom_parameters.get("negative_prompt"):
            parameters["negativePrompt"] = config.custom_parameters["negative_prompt"]
        
        if config.custom_parameters.get("seed"):
            parameters["seed"] = config.custom_parameters["seed"]
        
        if config.custom_parameters.get("generate_audio", False):
            parameters["generateAudio"] = True
        
        return {
            "instances": [instance],
            "parameters": parameters
        }
    
    def _convert_veo_status(self, operation_data: Dict[str, Any]) -> JobStatus:
        """
        Convert Veo operation status to JobStatus enum.
        
        Args:
            operation_data: Operation data from Veo API
            
        Returns:
            Corresponding JobStatus
        """
        if operation_data.get("done", False):
            if "error" in operation_data:
                return JobStatus.FAILED
            else:
                return JobStatus.COMPLETED
        else:
            # Operation is still running
            return JobStatus.PROCESSING
    
    async def generate(self, config: GenerationConfig) -> GenerationResult:
        """
        Start video generation with Veo 3.1.
        
        Args:
            config: Generation configuration
            
        Returns:
            GenerationResult with operation_id and initial status
        """
        # Validate configuration
        is_valid, error_msg = self.validate_config(config)
        if not is_valid:
            raise ValueError(f"Invalid configuration: {error_msg}")
        
        try:
            # Convert config to Veo parameters
            veo_params = self._convert_config_to_veo_params(config)
            
            # Make generation request
            response = await self._make_request("POST", ":predictLongRunning", veo_params)
            
            # Extract operation information
            operation_name = response.get("name")
            if not operation_name:
                raise RuntimeError("No operation name returned from Veo API")
            
            # Extract operation ID from the full name
            operation_id = operation_name.split("/")[-1]
            
            # Estimate completion time (Veo typically takes 3-10 minutes)
            estimated_completion = datetime.now() + timedelta(minutes=5)
            
            return GenerationResult(
                job_id=operation_id,
                status=JobStatus.PROCESSING,
                progress=0.0,
                estimated_completion=estimated_completion,
                metadata={
                    "model": "veo-3.1-generate-preview",
                    "operation_name": operation_name,
                    "aspect_ratio": config.aspect_ratio,
                    "duration": config.duration,
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
        Get the current status of a Veo generation operation.
        
        Args:
            job_id: Veo operation identifier
            
        Returns:
            GenerationResult with current status and progress
        """
        try:
            # Build operation name from job_id
            operation_name = f"projects/{self.project_id}/locations/{self.location}/operations/{job_id}"
            
            # Get operation status
            response = await self._make_request("GET", f"/../operations/{job_id}")
            
            status = self._convert_veo_status(response)
            
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
            if status == JobStatus.COMPLETED and "response" in response:
                predictions = response.get("response", {}).get("predictions", [])
                if predictions and len(predictions) > 0:
                    # Veo returns video as base64 or GCS URI
                    video_data = predictions[0].get("video", {})
                    if "gcsUri" in video_data:
                        video_url = video_data["gcsUri"]
                    elif "bytesBase64Encoded" in video_data:
                        # For base64 encoded videos, we'd need to save them locally
                        # This is a simplified approach - in production you'd want proper handling
                        video_url = f"data:video/mp4;base64,{video_data['bytesBase64Encoded']}"
            
            # Extract error message if failed
            error_message = None
            if status == JobStatus.FAILED and "error" in response:
                error_info = response["error"]
                error_message = error_info.get("message", "Generation failed")
            
            return GenerationResult(
                job_id=job_id,
                status=status,
                video_url=video_url,
                progress=progress,
                error_message=error_message,
                metadata={
                    "model": "veo-3.1-generate-preview",
                    "operation_name": response.get("name"),
                    "done": response.get("done", False)
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
        Cancel a Veo generation operation.
        
        Args:
            job_id: Veo operation identifier
            
        Returns:
            True if cancellation was successful
        """
        try:
            # Check current status first
            result = await self.get_status(job_id)
            
            if result.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
                return False  # Already finished, can't cancel
            
            # Cancel the operation
            await self._make_request("POST", f"/../operations/{job_id}:cancel", {})
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
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self.close())
            except RuntimeError:
                pass