"""
Scene Generator for Video Studio redesign.

This module handles JSON script parsing, scene validation, and batch scene generation
for the video generation workflow. It provides comprehensive validation and error
reporting for structured video scripts.
"""

import json
import asyncio
from typing import List, Dict, Any, Optional, Tuple, Union
from dataclasses import dataclass
from pathlib import Path
import logging
from datetime import datetime

from .models import Scene, VideoConfig, TaskStatus
from .error_handler import ErrorHandler


@dataclass
class ValidationError:
    """Represents a validation error with detailed information."""
    field: str
    message: str
    value: Any = None
    line_number: Optional[int] = None


@dataclass
class ScriptValidationResult:
    """Result of script validation with detailed error information."""
    is_valid: bool
    errors: List[ValidationError]
    warnings: List[str]
    parsed_scenes: List[Scene]
    
    def get_error_summary(self) -> str:
        """Get a formatted summary of all validation errors."""
        if not self.errors:
            return "No errors found"
        
        summary = f"Found {len(self.errors)} validation error(s):\n"
        for i, error in enumerate(self.errors, 1):
            line_info = f" (line {error.line_number})" if error.line_number else ""
            summary += f"{i}. {error.field}: {error.message}{line_info}\n"
        
        if self.warnings:
            summary += f"\nWarnings ({len(self.warnings)}):\n"
            for i, warning in enumerate(self.warnings, 1):
                summary += f"{i}. {warning}\n"
        
        return summary.strip()


class SceneGenerator:
    """
    Handles JSON script parsing, validation, and scene generation for video workflows.
    
    This class provides comprehensive validation of video scripts, detailed error reporting,
    and batch processing capabilities for multiple scenes.
    """
    
    def __init__(self, error_handler: Optional[ErrorHandler] = None):
        """Initialize the scene generator with optional error handler."""
        self.error_handler = error_handler or ErrorHandler()
        self.logger = logging.getLogger(__name__)
        
        # Define required fields for scene validation
        self.required_scene_fields = {
            'scene_id': str,
            'visual_prompt': str,
            'duration': (int, float)
        }
        
        # Define optional fields with their expected types
        self.optional_scene_fields = {
            'camera_movement': str,
            'lighting': str,
            'reference_image': str
        }
    
    def parse_json_script(self, script_content: Union[str, Dict[str, Any]]) -> ScriptValidationResult:
        """
        Parse and validate a JSON video script.
        
        Args:
            script_content: JSON string or dictionary containing the video script
            
        Returns:
            ScriptValidationResult with validation status and detailed error information
        """
        errors = []
        warnings = []
        parsed_scenes = []
        
        try:
            # Parse JSON if string provided
            if isinstance(script_content, str):
                try:
                    script_data = json.loads(script_content)
                except json.JSONDecodeError as e:
                    errors.append(ValidationError(
                        field="json_format",
                        message=f"Invalid JSON format: {str(e)}",
                        line_number=getattr(e, 'lineno', None)
                    ))
                    return ScriptValidationResult(False, errors, warnings, [])
            else:
                script_data = script_content
            
            # Validate root structure
            if not isinstance(script_data, dict):
                errors.append(ValidationError(
                    field="root",
                    message="Script must be a JSON object"
                ))
                return ScriptValidationResult(False, errors, warnings, [])
            
            # Check for scenes array
            if 'scenes' not in script_data:
                errors.append(ValidationError(
                    field="scenes",
                    message="Script must contain a 'scenes' array"
                ))
                return ScriptValidationResult(False, errors, warnings, [])
            
            scenes_data = script_data['scenes']
            if not isinstance(scenes_data, list):
                errors.append(ValidationError(
                    field="scenes",
                    message="'scenes' must be an array"
                ))
                return ScriptValidationResult(False, errors, warnings, [])
            
            if not scenes_data:
                warnings.append("Script contains no scenes")
                return ScriptValidationResult(True, [], warnings, [])
            
            # Validate each scene
            scene_ids = set()
            for i, scene_data in enumerate(scenes_data):
                scene_errors, scene_warnings, scene = self._validate_scene(scene_data, i)
                errors.extend(scene_errors)
                warnings.extend(scene_warnings)
                
                if scene:
                    # Check for duplicate scene IDs
                    if scene.scene_id in scene_ids:
                        errors.append(ValidationError(
                            field=f"scenes[{i}].scene_id",
                            message=f"Duplicate scene ID: {scene.scene_id}"
                        ))
                    else:
                        scene_ids.add(scene.scene_id)
                        parsed_scenes.append(scene)
            
            # Validate script-level constraints
            if parsed_scenes:
                total_duration = sum(scene.duration for scene in parsed_scenes)
                if total_duration > 300:  # 5 minutes max
                    warnings.append(f"Total script duration ({total_duration}s) exceeds recommended maximum (300s)")
                
                if len(parsed_scenes) > 50:  # Max scenes limit
                    warnings.append(f"Script contains {len(parsed_scenes)} scenes, which exceeds recommended maximum (50)")
            
            is_valid = len(errors) == 0
            return ScriptValidationResult(is_valid, errors, warnings, parsed_scenes)
            
        except Exception as e:
            self.logger.error(f"Unexpected error during script parsing: {str(e)}")
            errors.append(ValidationError(
                field="parsing",
                message=f"Unexpected parsing error: {str(e)}"
            ))
            return ScriptValidationResult(False, errors, warnings, [])
    
    def _validate_scene(self, scene_data: Any, index: int) -> Tuple[List[ValidationError], List[str], Optional[Scene]]:
        """
        Validate a single scene object.
        
        Args:
            scene_data: Scene data to validate
            index: Index of the scene in the array
            
        Returns:
            Tuple of (errors, warnings, parsed_scene)
        """
        errors = []
        warnings = []
        
        if not isinstance(scene_data, dict):
            errors.append(ValidationError(
                field=f"scenes[{index}]",
                message="Scene must be an object"
            ))
            return errors, warnings, None
        
        # Validate required fields
        scene_values = {}
        for field, expected_type in self.required_scene_fields.items():
            if field not in scene_data:
                errors.append(ValidationError(
                    field=f"scenes[{index}].{field}",
                    message=f"Required field '{field}' is missing"
                ))
                continue
            
            value = scene_data[field]
            if not isinstance(value, expected_type):
                type_name = expected_type.__name__ if hasattr(expected_type, '__name__') else str(expected_type)
                errors.append(ValidationError(
                    field=f"scenes[{index}].{field}",
                    message=f"Field '{field}' must be of type {type_name}",
                    value=value
                ))
                continue
            
            # Additional validation for specific fields
            if field == 'scene_id':
                if not value.strip():
                    errors.append(ValidationError(
                        field=f"scenes[{index}].{field}",
                        message="Scene ID cannot be empty"
                    ))
                    continue
                if len(value) > 100:
                    errors.append(ValidationError(
                        field=f"scenes[{index}].{field}",
                        message="Scene ID cannot exceed 100 characters"
                    ))
                    continue
            
            elif field == 'visual_prompt':
                if not value.strip():
                    errors.append(ValidationError(
                        field=f"scenes[{index}].{field}",
                        message="Visual prompt cannot be empty"
                    ))
                    continue
                if len(value) > 1000:
                    warnings.append(f"Scene {index}: Visual prompt is very long ({len(value)} characters)")
            
            elif field == 'duration':
                if value <= 0:
                    errors.append(ValidationError(
                        field=f"scenes[{index}].{field}",
                        message="Duration must be positive"
                    ))
                    continue
                if value > 60:
                    warnings.append(f"Scene {index}: Duration ({value}s) exceeds recommended maximum (60s)")
            
            scene_values[field] = value
        
        # Validate optional fields
        for field, expected_type in self.optional_scene_fields.items():
            if field in scene_data:
                value = scene_data[field]
                if value is not None and not isinstance(value, expected_type):
                    type_name = expected_type.__name__
                    errors.append(ValidationError(
                        field=f"scenes[{index}].{field}",
                        message=f"Field '{field}' must be of type {type_name}",
                        value=value
                    ))
                else:
                    scene_values[field] = value
        
        # Check for unknown fields
        known_fields = set(self.required_scene_fields.keys()) | set(self.optional_scene_fields.keys())
        unknown_fields = set(scene_data.keys()) - known_fields
        if unknown_fields:
            warnings.append(f"Scene {index}: Unknown fields ignored: {', '.join(unknown_fields)}")
        
        # Create scene object if no errors
        if not errors:
            try:
                scene = Scene(
                    scene_id=scene_values['scene_id'],
                    visual_prompt=scene_values['visual_prompt'],
                    duration=scene_values['duration'],
                    camera_movement=scene_values.get('camera_movement'),
                    lighting=scene_values.get('lighting'),
                    reference_image=scene_values.get('reference_image')
                )
                
                # Final validation using the Scene's validate method
                if not scene.validate():
                    errors.append(ValidationError(
                        field=f"scenes[{index}]",
                        message="Scene failed internal validation"
                    ))
                    return errors, warnings, None
                
                return errors, warnings, scene
            except Exception as e:
                errors.append(ValidationError(
                    field=f"scenes[{index}]",
                    message=f"Failed to create scene object: {str(e)}"
                ))
        
        return errors, warnings, None
    
    def validate_script_file(self, file_path: Path) -> ScriptValidationResult:
        """
        Validate a JSON script file.
        
        Args:
            file_path: Path to the JSON script file
            
        Returns:
            ScriptValidationResult with validation status and error information
        """
        try:
            if not file_path.exists():
                return ScriptValidationResult(
                    False,
                    [ValidationError("file", f"Script file not found: {file_path}")],
                    [],
                    []
                )
            
            if not file_path.is_file():
                return ScriptValidationResult(
                    False,
                    [ValidationError("file", f"Path is not a file: {file_path}")],
                    [],
                    []
                )
            
            with open(file_path, 'r', encoding='utf-8') as f:
                script_content = f.read()
            
            return self.parse_json_script(script_content)
            
        except Exception as e:
            self.logger.error(f"Error reading script file {file_path}: {str(e)}")
            return ScriptValidationResult(
                False,
                [ValidationError("file", f"Error reading file: {str(e)}")],
                [],
                []
            )
    
    def create_sample_script(self, num_scenes: int = 3) -> Dict[str, Any]:
        """
        Create a sample JSON script for testing and demonstration.
        
        Args:
            num_scenes: Number of scenes to include in the sample
            
        Returns:
            Dictionary representing a valid JSON script
        """
        scenes = []
        for i in range(num_scenes):
            scene = {
                "scene_id": f"scene_{i+1}",
                "visual_prompt": f"A beautiful product showcase scene {i+1} with professional lighting",
                "duration": 5.0,
                "camera_movement": "slow_zoom_in" if i % 2 == 0 else "pan_left",
                "lighting": "soft_studio_lighting",
                "reference_image": f"asset_id_{i+1}" if i < 2 else None
            }
            scenes.append(scene)
        
        return {
            "title": "Sample Video Script",
            "description": "A sample script for product video generation",
            "created_at": datetime.now().isoformat(),
            "scenes": scenes
        }
    
    def get_validation_schema(self) -> Dict[str, Any]:
        """
        Get the JSON schema for script validation.
        
        Returns:
            JSON schema dictionary for script validation
        """
        return {
            "type": "object",
            "required": ["scenes"],
            "properties": {
                "title": {"type": "string"},
                "description": {"type": "string"},
                "created_at": {"type": "string"},
                "scenes": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["scene_id", "visual_prompt", "duration"],
                        "properties": {
                            "scene_id": {
                                "type": "string",
                                "minLength": 1,
                                "maxLength": 100
                            },
                            "visual_prompt": {
                                "type": "string",
                                "minLength": 1,
                                "maxLength": 1000
                            },
                            "duration": {
                                "type": "number",
                                "minimum": 0.1,
                                "maximum": 60
                            },
                            "camera_movement": {"type": "string"},
                            "lighting": {"type": "string"},
                            "reference_image": {"type": "string"}
                        },
                        "additionalProperties": False
                    }
                }
            },
            "additionalProperties": True
        }


@dataclass
class ScenePreview:
    """Represents a scene preview with generated content and metadata."""
    scene_id: str
    preview_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    estimated_tokens: int = 0
    estimated_cost: float = 0.0
    generation_time: Optional[float] = None
    status: str = "pending"  # pending, generating, ready, error
    error_message: Optional[str] = None


class ScenePreviewManager:
    """
    Manages scene preview generation and real-time editing capabilities.
    
    This class provides functionality for generating scene previews, managing
    scene parameters dynamically, and providing real-time feedback for scene editing.
    """
    
    def __init__(self, scene_generator: SceneGenerator):
        """Initialize the preview manager with a scene generator."""
        self.scene_generator = scene_generator
        self.logger = logging.getLogger(__name__)
        self._preview_cache: Dict[str, ScenePreview] = {}
        self._active_previews: Dict[str, asyncio.Task] = {}
    
    async def generate_scene_preview(self, scene: Scene, force_regenerate: bool = False) -> ScenePreview:
        """
        Generate a preview for a single scene.
        
        Args:
            scene: Scene object to generate preview for
            force_regenerate: Whether to force regeneration even if cached
            
        Returns:
            ScenePreview object with preview information
        """
        # Check cache first
        if not force_regenerate and scene.scene_id in self._preview_cache:
            cached_preview = self._preview_cache[scene.scene_id]
            if cached_preview.status == "ready":
                return cached_preview
        
        # Cancel any existing preview generation for this scene
        if scene.scene_id in self._active_previews:
            self._active_previews[scene.scene_id].cancel()
        
        # Create initial preview object
        preview = ScenePreview(
            scene_id=scene.scene_id,
            status="generating"
        )
        self._preview_cache[scene.scene_id] = preview
        
        # Start preview generation task
        task = asyncio.create_task(self._generate_preview_async(scene, preview))
        self._active_previews[scene.scene_id] = task
        
        try:
            await task
        except asyncio.CancelledError:
            preview.status = "cancelled"
        except Exception as e:
            preview.status = "error"
            preview.error_message = str(e)
            self.logger.error(f"Error generating preview for scene {scene.scene_id}: {str(e)}")
        finally:
            if scene.scene_id in self._active_previews:
                del self._active_previews[scene.scene_id]
        
        return preview
    
    async def _generate_preview_async(self, scene: Scene, preview: ScenePreview) -> None:
        """
        Asynchronously generate preview content for a scene.
        
        Args:
            scene: Scene to generate preview for
            preview: Preview object to update
        """
        start_time = datetime.now()
        
        try:
            # Simulate preview generation (in real implementation, this would call AI services)
            await asyncio.sleep(0.5)  # Simulate processing time
            
            # Estimate tokens and cost based on prompt length and duration
            prompt_tokens = len(scene.visual_prompt.split()) * 1.3  # Rough token estimation
            duration_multiplier = scene.duration / 5.0  # Base 5-second duration
            preview.estimated_tokens = int(prompt_tokens * duration_multiplier)
            preview.estimated_cost = preview.estimated_tokens * 0.001  # $0.001 per token estimate
            
            # Generate mock URLs (in real implementation, these would be actual preview URLs)
            preview.preview_url = f"https://preview.example.com/scene_{scene.scene_id}.mp4"
            preview.thumbnail_url = f"https://preview.example.com/thumb_{scene.scene_id}.jpg"
            
            # Calculate generation time
            end_time = datetime.now()
            preview.generation_time = (end_time - start_time).total_seconds()
            
            preview.status = "ready"
            
        except Exception as e:
            preview.status = "error"
            preview.error_message = str(e)
            raise
    
    async def batch_generate_previews(self, scenes: List[Scene], max_concurrent: int = 3) -> List[ScenePreview]:
        """
        Generate previews for multiple scenes concurrently.
        
        Args:
            scenes: List of scenes to generate previews for
            max_concurrent: Maximum number of concurrent preview generations
            
        Returns:
            List of ScenePreview objects
        """
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def generate_with_semaphore(scene: Scene) -> ScenePreview:
            async with semaphore:
                return await self.generate_scene_preview(scene)
        
        tasks = [generate_with_semaphore(scene) for scene in scenes]
        previews = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle any exceptions
        result_previews = []
        for i, preview in enumerate(previews):
            if isinstance(preview, Exception):
                error_preview = ScenePreview(
                    scene_id=scenes[i].scene_id,
                    status="error",
                    error_message=str(preview)
                )
                result_previews.append(error_preview)
            else:
                result_previews.append(preview)
        
        return result_previews
    
    def update_scene_parameter(self, scene_id: str, parameter: str, value: Any) -> Tuple[bool, Optional[str]]:
        """
        Update a scene parameter and validate the change.
        
        Args:
            scene_id: ID of the scene to update
            parameter: Parameter name to update
            value: New value for the parameter
            
        Returns:
            Tuple of (success, error_message)
        """
        try:
            # Validate parameter name
            valid_parameters = {
                'visual_prompt', 'duration', 'camera_movement', 
                'lighting', 'reference_image'
            }
            
            if parameter not in valid_parameters:
                return False, f"Invalid parameter: {parameter}"
            
            # Validate parameter value based on type
            if parameter == 'visual_prompt':
                if not isinstance(value, str) or not value.strip():
                    return False, "Visual prompt must be a non-empty string"
                if len(value) > 1000:
                    return False, "Visual prompt cannot exceed 1000 characters"
            
            elif parameter == 'duration':
                if not isinstance(value, (int, float)) or value <= 0:
                    return False, "Duration must be a positive number"
                if value > 60:
                    return False, "Duration cannot exceed 60 seconds"
            
            elif parameter in ['camera_movement', 'lighting', 'reference_image']:
                if value is not None and not isinstance(value, str):
                    return False, f"{parameter} must be a string or null"
            
            # Invalidate preview cache for this scene
            if scene_id in self._preview_cache:
                del self._preview_cache[scene_id]
            
            return True, None
            
        except Exception as e:
            return False, f"Error updating parameter: {str(e)}"
    
    def get_scene_preview_status(self, scene_id: str) -> Optional[ScenePreview]:
        """
        Get the current preview status for a scene.
        
        Args:
            scene_id: ID of the scene
            
        Returns:
            ScenePreview object if exists, None otherwise
        """
        return self._preview_cache.get(scene_id)
    
    def cancel_preview_generation(self, scene_id: str) -> bool:
        """
        Cancel ongoing preview generation for a scene.
        
        Args:
            scene_id: ID of the scene
            
        Returns:
            True if cancellation was successful, False otherwise
        """
        if scene_id in self._active_previews:
            task = self._active_previews[scene_id]
            task.cancel()
            return True
        return False
    
    def clear_preview_cache(self, scene_ids: Optional[List[str]] = None) -> None:
        """
        Clear preview cache for specified scenes or all scenes.
        
        Args:
            scene_ids: List of scene IDs to clear, or None to clear all
        """
        if scene_ids is None:
            self._preview_cache.clear()
        else:
            for scene_id in scene_ids:
                if scene_id in self._preview_cache:
                    del self._preview_cache[scene_id]
    
    def get_preview_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about current preview cache and active generations.
        
        Returns:
            Dictionary with preview statistics
        """
        total_previews = len(self._preview_cache)
        ready_previews = sum(1 for p in self._preview_cache.values() if p.status == "ready")
        error_previews = sum(1 for p in self._preview_cache.values() if p.status == "error")
        active_generations = len(self._active_previews)
        
        total_estimated_cost = sum(
            p.estimated_cost for p in self._preview_cache.values() 
            if p.estimated_cost > 0
        )
        
        return {
            "total_previews": total_previews,
            "ready_previews": ready_previews,
            "error_previews": error_previews,
            "active_generations": active_generations,
            "total_estimated_cost": total_estimated_cost,
            "cache_hit_rate": ready_previews / total_previews if total_previews > 0 else 0
        }


@dataclass
class BatchGenerationResult:
    """Result of batch scene generation with detailed status information."""
    total_scenes: int
    successful_scenes: int
    failed_scenes: int
    generation_time: float
    scene_results: Dict[str, Any]  # scene_id -> result data
    errors: List[str]


class BatchSceneProcessor:
    """
    Handles batch processing and concurrent generation of multiple video scenes.
    
    This class integrates with the workflow manager and generation engine to process
    multiple scenes efficiently with proper resource management and error handling.
    """
    
    def __init__(self, scene_generator: SceneGenerator, workflow_manager=None, generation_engine=None):
        """
        Initialize the batch processor.
        
        Args:
            scene_generator: SceneGenerator instance for validation
            workflow_manager: WorkflowManager instance for task coordination
            generation_engine: GenerationEngine instance for video generation
        """
        self.scene_generator = scene_generator
        self.workflow_manager = workflow_manager
        self.generation_engine = generation_engine
        self.logger = logging.getLogger(__name__)
        
        # Configuration for batch processing
        self.max_concurrent_scenes = 5
        self.max_retries = 3
        self.retry_delay = 2.0
        self.timeout_per_scene = 300  # 5 minutes per scene
    
    async def process_batch_scenes(
        self, 
        scenes: List[Scene], 
        config: VideoConfig,
        progress_callback: Optional[callable] = None
    ) -> BatchGenerationResult:
        """
        Process multiple scenes concurrently with proper resource management.
        
        Args:
            scenes: List of Scene objects to process
            config: VideoConfig for the batch generation
            progress_callback: Optional callback for progress updates
            
        Returns:
            BatchGenerationResult with detailed processing information
        """
        start_time = datetime.now()
        scene_results = {}
        errors = []
        successful_count = 0
        
        try:
            # Validate all scenes first
            validation_errors = []
            valid_scenes = []
            
            for scene in scenes:
                if not scene.validate():
                    validation_errors.append(f"Scene {scene.scene_id}: Invalid scene configuration")
                else:
                    valid_scenes.append(scene)
            
            if validation_errors:
                errors.extend(validation_errors)
                if not valid_scenes:
                    return BatchGenerationResult(
                        total_scenes=len(scenes),
                        successful_scenes=0,
                        failed_scenes=len(scenes),
                        generation_time=0,
                        scene_results={},
                        errors=errors
                    )
            
            # Create semaphore for concurrent processing
            semaphore = asyncio.Semaphore(self.max_concurrent_scenes)
            
            # Process scenes concurrently
            tasks = []
            for i, scene in enumerate(valid_scenes):
                task = asyncio.create_task(
                    self._process_single_scene_with_semaphore(
                        scene, config, semaphore, i, len(valid_scenes), progress_callback
                    )
                )
                tasks.append(task)
            
            # Wait for all tasks to complete
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            for i, result in enumerate(results):
                scene = valid_scenes[i]
                if isinstance(result, Exception):
                    error_msg = f"Scene {scene.scene_id}: {str(result)}"
                    errors.append(error_msg)
                    scene_results[scene.scene_id] = {
                        "status": "failed",
                        "error": str(result)
                    }
                else:
                    successful_count += 1
                    scene_results[scene.scene_id] = result
            
            end_time = datetime.now()
            total_time = (end_time - start_time).total_seconds()
            
            return BatchGenerationResult(
                total_scenes=len(scenes),
                successful_scenes=successful_count,
                failed_scenes=len(scenes) - successful_count,
                generation_time=total_time,
                scene_results=scene_results,
                errors=errors
            )
            
        except Exception as e:
            self.logger.error(f"Error in batch scene processing: {str(e)}")
            errors.append(f"Batch processing error: {str(e)}")
            
            end_time = datetime.now()
            total_time = (end_time - start_time).total_seconds()
            
            return BatchGenerationResult(
                total_scenes=len(scenes),
                successful_scenes=successful_count,
                failed_scenes=len(scenes) - successful_count,
                generation_time=total_time,
                scene_results=scene_results,
                errors=errors
            )
    
    async def _process_single_scene_with_semaphore(
        self,
        scene: Scene,
        config: VideoConfig,
        semaphore: asyncio.Semaphore,
        scene_index: int,
        total_scenes: int,
        progress_callback: Optional[callable]
    ) -> Dict[str, Any]:
        """
        Process a single scene with semaphore control and retry logic.
        
        Args:
            scene: Scene to process
            config: Video configuration
            semaphore: Semaphore for concurrency control
            scene_index: Index of current scene
            total_scenes: Total number of scenes
            progress_callback: Optional progress callback
            
        Returns:
            Dictionary with scene processing result
        """
        async with semaphore:
            return await self._process_single_scene_with_retry(
                scene, config, scene_index, total_scenes, progress_callback
            )
    
    async def _process_single_scene_with_retry(
        self,
        scene: Scene,
        config: VideoConfig,
        scene_index: int,
        total_scenes: int,
        progress_callback: Optional[callable]
    ) -> Dict[str, Any]:
        """
        Process a single scene with retry logic.
        
        Args:
            scene: Scene to process
            config: Video configuration
            scene_index: Index of current scene
            total_scenes: Total number of scenes
            progress_callback: Optional progress callback
            
        Returns:
            Dictionary with scene processing result
        """
        last_error = None
        
        for attempt in range(self.max_retries + 1):
            try:
                # Update progress
                if progress_callback:
                    progress = (scene_index + attempt / (self.max_retries + 1)) / total_scenes
                    await progress_callback(progress, f"Processing scene {scene.scene_id} (attempt {attempt + 1})")
                
                # Process the scene
                result = await self._generate_scene_video(scene, config)
                
                # Update final progress for this scene
                if progress_callback:
                    progress = (scene_index + 1) / total_scenes
                    await progress_callback(progress, f"Completed scene {scene.scene_id}")
                
                return {
                    "status": "success",
                    "scene_id": scene.scene_id,
                    "result": result,
                    "attempts": attempt + 1,
                    "processing_time": result.get("processing_time", 0)
                }
                
            except Exception as e:
                last_error = e
                self.logger.warning(f"Attempt {attempt + 1} failed for scene {scene.scene_id}: {str(e)}")
                
                if attempt < self.max_retries:
                    # Wait before retry with exponential backoff
                    delay = self.retry_delay * (2 ** attempt)
                    await asyncio.sleep(delay)
                else:
                    # Final attempt failed
                    raise last_error
        
        # This should never be reached, but just in case
        raise last_error or Exception("Unknown error in scene processing")
    
    async def _generate_scene_video(self, scene: Scene, config: VideoConfig) -> Dict[str, Any]:
        """
        Generate video for a single scene using the generation engine.
        
        Args:
            scene: Scene to generate video for
            config: Video configuration
            
        Returns:
            Dictionary with generation result
        """
        start_time = datetime.now()
        
        try:
            # If we have a generation engine, use it
            if self.generation_engine:
                # Create generation config from scene and video config
                generation_config = {
                    "prompt": scene.visual_prompt,
                    "duration": scene.duration,
                    "aspect_ratio": config.aspect_ratio.value,
                    "quality": config.quality.value,
                    "camera_movement": scene.camera_movement,
                    "lighting": scene.lighting,
                    "reference_image": scene.reference_image
                }
                
                # Generate video using the engine
                result = await self.generation_engine.generate_video(
                    scene.visual_prompt, 
                    generation_config
                )
                
                end_time = datetime.now()
                processing_time = (end_time - start_time).total_seconds()
                
                return {
                    "video_url": result.get("video_url"),
                    "thumbnail_url": result.get("thumbnail_url"),
                    "processing_time": processing_time,
                    "model_used": result.get("model_used"),
                    "generation_id": result.get("generation_id")
                }
            else:
                # Simulate video generation for testing
                await asyncio.sleep(2.0)  # Simulate processing time
                
                end_time = datetime.now()
                processing_time = (end_time - start_time).total_seconds()
                
                return {
                    "video_url": f"https://generated.example.com/video_{scene.scene_id}.mp4",
                    "thumbnail_url": f"https://generated.example.com/thumb_{scene.scene_id}.jpg",
                    "processing_time": processing_time,
                    "model_used": "mock_model",
                    "generation_id": f"gen_{scene.scene_id}_{int(start_time.timestamp())}"
                }
                
        except asyncio.TimeoutError:
            raise Exception(f"Scene generation timed out after {self.timeout_per_scene} seconds")
        except Exception as e:
            raise Exception(f"Scene generation failed: {str(e)}")
    
    async def create_workflow_task(self, scenes: List[Scene], config: VideoConfig) -> Optional[str]:
        """
        Create a workflow task for batch scene processing.
        
        Args:
            scenes: List of scenes to process
            config: Video configuration
            
        Returns:
            Task ID if workflow manager is available, None otherwise
        """
        if not self.workflow_manager:
            self.logger.warning("No workflow manager available for task creation")
            return None
        
        try:
            # Create a task in the workflow manager
            task_id = await self.workflow_manager.create_video_task(config)
            
            # Log the batch processing request
            self.logger.info(f"Created workflow task {task_id} for {len(scenes)} scenes")
            
            return task_id
            
        except Exception as e:
            self.logger.error(f"Failed to create workflow task: {str(e)}")
            return None
    
    def configure_batch_settings(
        self,
        max_concurrent: Optional[int] = None,
        max_retries: Optional[int] = None,
        retry_delay: Optional[float] = None,
        timeout_per_scene: Optional[int] = None
    ) -> None:
        """
        Configure batch processing settings.
        
        Args:
            max_concurrent: Maximum concurrent scene processing
            max_retries: Maximum retry attempts per scene
            retry_delay: Base delay between retries in seconds
            timeout_per_scene: Timeout per scene in seconds
        """
        if max_concurrent is not None:
            self.max_concurrent_scenes = max(1, min(max_concurrent, 20))
        if max_retries is not None:
            self.max_retries = max(0, min(max_retries, 10))
        if retry_delay is not None:
            self.retry_delay = max(0.1, min(retry_delay, 60.0))
        if timeout_per_scene is not None:
            self.timeout_per_scene = max(30, min(timeout_per_scene, 1800))
    
    def get_batch_statistics(self) -> Dict[str, Any]:
        """
        Get current batch processing configuration and statistics.
        
        Returns:
            Dictionary with batch processing information
        """
        return {
            "max_concurrent_scenes": self.max_concurrent_scenes,
            "max_retries": self.max_retries,
            "retry_delay": self.retry_delay,
            "timeout_per_scene": self.timeout_per_scene,
            "has_workflow_manager": self.workflow_manager is not None,
            "has_generation_engine": self.generation_engine is not None
        }