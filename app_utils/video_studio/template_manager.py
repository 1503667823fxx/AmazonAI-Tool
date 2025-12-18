"""
Template Management System for Video Studio

This module provides template management functionality including preset video styles,
custom template creation, and template application logic.
"""

import json
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum

from .models import (
    VideoConfig, Scene, AudioConfig, TextOverlay,
    AspectRatio, VideoQuality
)


class TemplateCategory(Enum):
    """Categories for video templates"""
    PRODUCT_SHOWCASE = "product_showcase"
    PROMOTIONAL = "promotional"
    SOCIAL_MEDIA = "social_media"
    STORYTELLING = "storytelling"
    EDUCATIONAL = "educational"
    CUSTOM = "custom"


class VideoStyle(Enum):
    """Predefined video styles"""
    CINEMATIC = "cinematic"
    DYNAMIC = "dynamic"
    MINIMAL = "minimal"
    ENERGETIC = "energetic"
    ELEGANT = "elegant"
    MODERN = "modern"
    VINTAGE = "vintage"
    PROFESSIONAL = "professional"


@dataclass
class TemplateMetadata:
    """Metadata for video templates"""
    name: str
    description: str
    category: TemplateCategory
    tags: List[str] = field(default_factory=list)
    author: str = "system"
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    usage_count: int = 0
    is_custom: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metadata to dictionary"""
        return {
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "tags": self.tags,
            "author": self.author,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "usage_count": self.usage_count,
            "is_custom": self.is_custom
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TemplateMetadata':
        """Create metadata from dictionary"""
        return cls(
            name=data["name"],
            description=data["description"],
            category=TemplateCategory(data["category"]),
            tags=data.get("tags", []),
            author=data.get("author", "system"),
            created_at=datetime.fromisoformat(data.get("created_at", datetime.now().isoformat())),
            updated_at=datetime.fromisoformat(data.get("updated_at", datetime.now().isoformat())),
            usage_count=data.get("usage_count", 0),
            is_custom=data.get("is_custom", False)
        )


@dataclass
class TemplateConfig:
    """Configuration for a video template"""
    duration: int
    aspect_ratio: AspectRatio
    quality: VideoQuality
    style: VideoStyle
    scene_count: int
    default_scene_duration: float
    camera_movements: List[str] = field(default_factory=list)
    lighting_presets: List[str] = field(default_factory=list)
    audio_enabled: bool = False
    text_overlays_enabled: bool = False
    transition_style: str = "fade"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary"""
        return {
            "duration": self.duration,
            "aspect_ratio": self.aspect_ratio.value,
            "quality": self.quality.value,
            "style": self.style.value,
            "scene_count": self.scene_count,
            "default_scene_duration": self.default_scene_duration,
            "camera_movements": self.camera_movements,
            "lighting_presets": self.lighting_presets,
            "audio_enabled": self.audio_enabled,
            "text_overlays_enabled": self.text_overlays_enabled,
            "transition_style": self.transition_style
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TemplateConfig':
        """Create config from dictionary"""
        return cls(
            duration=data["duration"],
            aspect_ratio=AspectRatio(data["aspect_ratio"]),
            quality=VideoQuality(data["quality"]),
            style=VideoStyle(data["style"]),
            scene_count=data["scene_count"],
            default_scene_duration=data["default_scene_duration"],
            camera_movements=data.get("camera_movements", []),
            lighting_presets=data.get("lighting_presets", []),
            audio_enabled=data.get("audio_enabled", False),
            text_overlays_enabled=data.get("text_overlays_enabled", False),
            transition_style=data.get("transition_style", "fade")
        )


@dataclass
class VideoTemplate:
    """Complete video template definition"""
    template_id: str
    metadata: TemplateMetadata
    config: TemplateConfig
    scene_templates: List[Dict[str, Any]] = field(default_factory=list)
    
    def validate(self) -> bool:
        """Validate template configuration"""
        if not self.template_id or not isinstance(self.template_id, str):
            return False
        if self.config.duration <= 0:
            return False
        if self.config.scene_count <= 0:
            return False
        if self.config.default_scene_duration <= 0:
            return False
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert template to dictionary"""
        return {
            "template_id": self.template_id,
            "metadata": self.metadata.to_dict(),
            "config": self.config.to_dict(),
            "scene_templates": self.scene_templates
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'VideoTemplate':
        """Create template from dictionary"""
        return cls(
            template_id=data["template_id"],
            metadata=TemplateMetadata.from_dict(data["metadata"]),
            config=TemplateConfig.from_dict(data["config"]),
            scene_templates=data.get("scene_templates", [])
        )


class TemplateManager:
    """Manages video templates including presets and custom templates"""
    
    def __init__(self, storage_path: Optional[str] = None):
        """
        Initialize template manager
        
        Args:
            storage_path: Path to store custom templates
        """
        self.storage_path = Path(storage_path or "./video_studio_templates")
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        self._templates: Dict[str, VideoTemplate] = {}
        self._initialize_preset_templates()
    
    def _initialize_preset_templates(self):
        """Initialize preset video templates"""
        # Template 1: Product Showcase - Cinematic
        self._templates["product_cinematic"] = VideoTemplate(
            template_id="product_cinematic",
            metadata=TemplateMetadata(
                name="Cinematic Product Showcase",
                description="Professional cinematic style for premium product presentations",
                category=TemplateCategory.PRODUCT_SHOWCASE,
                tags=["cinematic", "premium", "professional", "product"]
            ),
            config=TemplateConfig(
                duration=15,
                aspect_ratio=AspectRatio.LANDSCAPE,
                quality=VideoQuality.FULL_HD_1080P,
                style=VideoStyle.CINEMATIC,
                scene_count=3,
                default_scene_duration=5.0,
                camera_movements=["slow_zoom", "pan_right", "orbit"],
                lighting_presets=["dramatic", "soft_key", "rim_light"],
                audio_enabled=True,
                text_overlays_enabled=True,
                transition_style="fade"
            ),
            scene_templates=[
                {
                    "order": 1,
                    "prompt_template": "Cinematic reveal of {product}, dramatic lighting, slow zoom in",
                    "camera_movement": "slow_zoom",
                    "lighting": "dramatic"
                },
                {
                    "order": 2,
                    "prompt_template": "{product} rotating slowly, soft key lighting, professional studio setup",
                    "camera_movement": "orbit",
                    "lighting": "soft_key"
                },
                {
                    "order": 3,
                    "prompt_template": "Close-up details of {product}, rim lighting, elegant presentation",
                    "camera_movement": "pan_right",
                    "lighting": "rim_light"
                }
            ]
        )
        
        # Template 2: Social Media - Dynamic
        self._templates["social_dynamic"] = VideoTemplate(
            template_id="social_dynamic",
            metadata=TemplateMetadata(
                name="Dynamic Social Media",
                description="Fast-paced, energetic style perfect for social media platforms",
                category=TemplateCategory.SOCIAL_MEDIA,
                tags=["social", "dynamic", "energetic", "short-form"]
            ),
            config=TemplateConfig(
                duration=10,
                aspect_ratio=AspectRatio.PORTRAIT,
                quality=VideoQuality.FULL_HD_1080P,
                style=VideoStyle.DYNAMIC,
                scene_count=4,
                default_scene_duration=2.5,
                camera_movements=["quick_zoom", "shake", "spin"],
                lighting_presets=["bright", "colorful", "high_contrast"],
                audio_enabled=True,
                text_overlays_enabled=True,
                transition_style="cut"
            ),
            scene_templates=[
                {
                    "order": 1,
                    "prompt_template": "Eye-catching reveal of {product}, bright colorful lighting",
                    "camera_movement": "quick_zoom",
                    "lighting": "colorful"
                },
                {
                    "order": 2,
                    "prompt_template": "{product} in action, dynamic movement, high energy",
                    "camera_movement": "shake",
                    "lighting": "bright"
                },
                {
                    "order": 3,
                    "prompt_template": "Multiple angles of {product}, fast cuts, vibrant colors",
                    "camera_movement": "spin",
                    "lighting": "high_contrast"
                },
                {
                    "order": 4,
                    "prompt_template": "Final showcase of {product}, bold presentation",
                    "camera_movement": "quick_zoom",
                    "lighting": "bright"
                }
            ]
        )
        
        # Template 3: Minimal Elegant
        self._templates["minimal_elegant"] = VideoTemplate(
            template_id="minimal_elegant",
            metadata=TemplateMetadata(
                name="Minimal Elegant",
                description="Clean, minimalist design with elegant transitions",
                category=TemplateCategory.PRODUCT_SHOWCASE,
                tags=["minimal", "elegant", "clean", "sophisticated"]
            ),
            config=TemplateConfig(
                duration=12,
                aspect_ratio=AspectRatio.SQUARE,
                quality=VideoQuality.FULL_HD_1080P,
                style=VideoStyle.MINIMAL,
                scene_count=3,
                default_scene_duration=4.0,
                camera_movements=["static", "slow_pan", "gentle_zoom"],
                lighting_presets=["soft", "natural", "clean"],
                audio_enabled=False,
                text_overlays_enabled=True,
                transition_style="dissolve"
            ),
            scene_templates=[
                {
                    "order": 1,
                    "prompt_template": "{product} on clean white background, soft natural lighting",
                    "camera_movement": "static",
                    "lighting": "natural"
                },
                {
                    "order": 2,
                    "prompt_template": "Elegant view of {product}, minimalist composition, soft shadows",
                    "camera_movement": "slow_pan",
                    "lighting": "soft"
                },
                {
                    "order": 3,
                    "prompt_template": "Final presentation of {product}, clean aesthetic, gentle focus",
                    "camera_movement": "gentle_zoom",
                    "lighting": "clean"
                }
            ]
        )
        
        # Template 4: Promotional Energetic
        self._templates["promo_energetic"] = VideoTemplate(
            template_id="promo_energetic",
            metadata=TemplateMetadata(
                name="Energetic Promotional",
                description="High-energy promotional video with bold visuals",
                category=TemplateCategory.PROMOTIONAL,
                tags=["promotional", "energetic", "bold", "attention-grabbing"]
            ),
            config=TemplateConfig(
                duration=20,
                aspect_ratio=AspectRatio.LANDSCAPE,
                quality=VideoQuality.FULL_HD_1080P,
                style=VideoStyle.ENERGETIC,
                scene_count=5,
                default_scene_duration=4.0,
                camera_movements=["fast_zoom", "whip_pan", "dolly"],
                lighting_presets=["dramatic", "colorful", "high_energy"],
                audio_enabled=True,
                text_overlays_enabled=True,
                transition_style="wipe"
            ),
            scene_templates=[
                {
                    "order": 1,
                    "prompt_template": "Explosive reveal of {product}, dramatic lighting, high impact",
                    "camera_movement": "fast_zoom",
                    "lighting": "dramatic"
                },
                {
                    "order": 2,
                    "prompt_template": "{product} features highlighted, dynamic angles, bold colors",
                    "camera_movement": "whip_pan",
                    "lighting": "colorful"
                },
                {
                    "order": 3,
                    "prompt_template": "Action shots of {product}, energetic movement",
                    "camera_movement": "dolly",
                    "lighting": "high_energy"
                },
                {
                    "order": 4,
                    "prompt_template": "Benefits showcase of {product}, impactful presentation",
                    "camera_movement": "fast_zoom",
                    "lighting": "dramatic"
                },
                {
                    "order": 5,
                    "prompt_template": "Call to action with {product}, powerful finale",
                    "camera_movement": "dolly",
                    "lighting": "colorful"
                }
            ]
        )
        
        # Template 5: Professional Modern
        self._templates["professional_modern"] = VideoTemplate(
            template_id="professional_modern",
            metadata=TemplateMetadata(
                name="Professional Modern",
                description="Contemporary professional style for business presentations",
                category=TemplateCategory.EDUCATIONAL,
                tags=["professional", "modern", "business", "corporate"]
            ),
            config=TemplateConfig(
                duration=30,
                aspect_ratio=AspectRatio.LANDSCAPE,
                quality=VideoQuality.FULL_HD_1080P,
                style=VideoStyle.PROFESSIONAL,
                scene_count=6,
                default_scene_duration=5.0,
                camera_movements=["smooth_pan", "slow_zoom", "track"],
                lighting_presets=["professional", "balanced", "studio"],
                audio_enabled=True,
                text_overlays_enabled=True,
                transition_style="slide"
            ),
            scene_templates=[
                {
                    "order": 1,
                    "prompt_template": "Introduction to {product}, professional studio lighting",
                    "camera_movement": "smooth_pan",
                    "lighting": "professional"
                },
                {
                    "order": 2,
                    "prompt_template": "Overview of {product} features, balanced composition",
                    "camera_movement": "slow_zoom",
                    "lighting": "balanced"
                },
                {
                    "order": 3,
                    "prompt_template": "Detailed view of {product} functionality, clear presentation",
                    "camera_movement": "track",
                    "lighting": "studio"
                },
                {
                    "order": 4,
                    "prompt_template": "{product} in professional context, modern aesthetic",
                    "camera_movement": "smooth_pan",
                    "lighting": "professional"
                },
                {
                    "order": 5,
                    "prompt_template": "Benefits and advantages of {product}, clear messaging",
                    "camera_movement": "slow_zoom",
                    "lighting": "balanced"
                },
                {
                    "order": 6,
                    "prompt_template": "Conclusion and summary of {product}, professional finish",
                    "camera_movement": "track",
                    "lighting": "studio"
                }
            ]
        )
    
    def get_template(self, template_id: str) -> Optional[VideoTemplate]:
        """
        Get a template by ID
        
        Args:
            template_id: Unique template identifier
            
        Returns:
            VideoTemplate if found, None otherwise
        """
        # Check in-memory templates
        if template_id in self._templates:
            return self._templates[template_id]
        
        # Try to load from storage
        template = self._load_template_from_storage(template_id)
        if template:
            self._templates[template_id] = template
        
        return template
    
    def list_templates(self, category: Optional[TemplateCategory] = None) -> List[VideoTemplate]:
        """
        List all available templates, optionally filtered by category
        
        Args:
            category: Optional category filter
            
        Returns:
            List of templates
        """
        # Load all custom templates from storage
        self._load_all_custom_templates()
        
        templates = list(self._templates.values())
        
        if category:
            templates = [t for t in templates if t.metadata.category == category]
        
        return templates
    
    def create_custom_template(
        self,
        name: str,
        description: str,
        config: TemplateConfig,
        category: TemplateCategory = TemplateCategory.CUSTOM,
        scene_templates: Optional[List[Dict[str, Any]]] = None,
        tags: Optional[List[str]] = None
    ) -> str:
        """
        Create a custom template
        
        Args:
            name: Template name
            description: Template description
            config: Template configuration
            category: Template category
            scene_templates: Optional scene template definitions
            tags: Optional tags for categorization
            
        Returns:
            Template ID of the created template
        """
        template_id = f"custom_{uuid.uuid4().hex[:8]}"
        
        metadata = TemplateMetadata(
            name=name,
            description=description,
            category=category,
            tags=tags or [],
            is_custom=True
        )
        
        template = VideoTemplate(
            template_id=template_id,
            metadata=metadata,
            config=config,
            scene_templates=scene_templates or []
        )
        
        # Validate template
        if not template.validate():
            raise ValueError("Invalid template configuration")
        
        # Store in memory and persist to disk
        self._templates[template_id] = template
        self._save_template_to_storage(template)
        
        return template_id
    
    def update_template(self, template_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update an existing template
        
        Args:
            template_id: Template to update
            updates: Dictionary of updates to apply
            
        Returns:
            True if successful, False otherwise
        """
        template = self.get_template(template_id)
        if not template:
            return False
        
        # Only allow updating custom templates
        if not template.metadata.is_custom:
            return False
        
        # Apply updates
        if "name" in updates:
            template.metadata.name = updates["name"]
        if "description" in updates:
            template.metadata.description = updates["description"]
        if "tags" in updates:
            template.metadata.tags = updates["tags"]
        
        template.metadata.updated_at = datetime.now()
        
        # Save changes
        self._save_template_to_storage(template)
        
        return True
    
    def delete_template(self, template_id: str) -> bool:
        """
        Delete a custom template
        
        Args:
            template_id: Template to delete
            
        Returns:
            True if successful, False otherwise
        """
        template = self.get_template(template_id)
        if not template or not template.metadata.is_custom:
            return False
        
        # Remove from memory
        del self._templates[template_id]
        
        # Remove from storage
        template_file = self.storage_path / f"{template_id}.json"
        if template_file.exists():
            template_file.unlink()
        
        return True
    
    def apply_template(
        self,
        template_id: str,
        input_images: List[str],
        custom_params: Optional[Dict[str, Any]] = None
    ) -> VideoConfig:
        """
        Apply a template to create a video configuration
        
        Args:
            template_id: Template to apply
            input_images: List of input image asset IDs
            custom_params: Optional custom parameters to override template defaults
            
        Returns:
            VideoConfig ready for video generation
        """
        template = self.get_template(template_id)
        if not template:
            raise ValueError(f"Template not found: {template_id}")
        
        # Increment usage count
        template.metadata.usage_count += 1
        if template.metadata.is_custom:
            self._save_template_to_storage(template)
        
        # Build scenes from template
        scenes = []
        for i, scene_template in enumerate(template.scene_templates):
            scene = Scene(
                scene_id=f"scene_{i+1}",
                visual_prompt=scene_template.get("prompt_template", "").format(
                    product=custom_params.get("product_name", "product") if custom_params else "product"
                ),
                duration=template.config.default_scene_duration,
                camera_movement=scene_template.get("camera_movement"),
                lighting=scene_template.get("lighting"),
                reference_image=input_images[i % len(input_images)] if input_images else None
            )
            scenes.append(scene)
        
        # Build audio config if enabled
        audio_config = None
        if template.config.audio_enabled:
            audio_config = AudioConfig(
                enabled=True,
                background_music=custom_params.get("background_music") if custom_params else None,
                volume=custom_params.get("audio_volume", 0.5) if custom_params else 0.5
            )
        
        # Build text overlays if enabled
        text_overlays = []
        if template.config.text_overlays_enabled and custom_params and "text_overlays" in custom_params:
            for overlay_data in custom_params["text_overlays"]:
                text_overlays.append(TextOverlay(**overlay_data))
        
        # Create video config
        video_config = VideoConfig(
            template_id=template_id,
            input_images=input_images,
            duration=custom_params.get("duration", template.config.duration) if custom_params else template.config.duration,
            aspect_ratio=custom_params.get("aspect_ratio", template.config.aspect_ratio) if custom_params else template.config.aspect_ratio,
            style=template.config.style.value,
            quality=custom_params.get("quality", template.config.quality) if custom_params else template.config.quality,
            audio_config=audio_config,
            text_overlays=text_overlays,
            scenes=scenes
        )
        
        return video_config
    
    def _save_template_to_storage(self, template: VideoTemplate) -> bool:
        """Save template to storage"""
        try:
            template_file = self.storage_path / f"{template.template_id}.json"
            with open(template_file, 'w', encoding='utf-8') as f:
                json.dump(template.to_dict(), f, indent=2, ensure_ascii=False)
            return True
        except Exception:
            return False
    
    def _load_template_from_storage(self, template_id: str) -> Optional[VideoTemplate]:
        """Load template from storage"""
        try:
            template_file = self.storage_path / f"{template_id}.json"
            if not template_file.exists():
                return None
            
            with open(template_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            return VideoTemplate.from_dict(data)
        except Exception:
            return None
    
    def _load_all_custom_templates(self):
        """Load all custom templates from storage"""
        try:
            for template_file in self.storage_path.glob("custom_*.json"):
                template_id = template_file.stem
                if template_id not in self._templates:
                    template = self._load_template_from_storage(template_id)
                    if template:
                        self._templates[template_id] = template
        except Exception:
            pass
    
    def get_template_categories(self) -> List[str]:
        """Get list of all template categories"""
        return [category.value for category in TemplateCategory]
    
    def get_template_styles(self) -> List[str]:
        """Get list of all available styles"""
        return [style.value for style in VideoStyle]
    
    def search_templates(self, query: str) -> List[VideoTemplate]:
        """
        Search templates by name, description, or tags
        
        Args:
            query: Search query string
            
        Returns:
            List of matching templates
        """
        self._load_all_custom_templates()
        
        query_lower = query.lower()
        results = []
        
        for template in self._templates.values():
            # Search in name
            if query_lower in template.metadata.name.lower():
                results.append(template)
                continue
            
            # Search in description
            if query_lower in template.metadata.description.lower():
                results.append(template)
                continue
            
            # Search in tags
            if any(query_lower in tag.lower() for tag in template.metadata.tags):
                results.append(template)
                continue
        
        return results
