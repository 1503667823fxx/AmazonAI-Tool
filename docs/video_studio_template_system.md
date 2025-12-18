# Video Studio Template System Documentation

## Overview

The Template System provides a comprehensive solution for managing video templates, including 5 preset video styles and support for custom template creation. This system addresses **Requirement 1.2** from the requirements document.

## Implementation Summary

### Task 7.1: 创建基础模板系统 ✅

**Completed Components:**

1. **Data Structures**
   - `TemplateMetadata`: Stores template information (name, description, category, tags, usage tracking)
   - `TemplateConfig`: Defines template configuration (duration, aspect ratio, quality, style, scenes)
   - `VideoTemplate`: Complete template definition combining metadata and configuration
   - `TemplateCategory`: Enum for categorizing templates (Product Showcase, Promotional, Social Media, etc.)
   - `VideoStyle`: Enum for video styles (Cinematic, Dynamic, Minimal, Energetic, Elegant, Modern, Vintage, Professional)

2. **Storage System**
   - File-based storage using JSON format
   - Configurable storage path (default: `./video_studio_templates`)
   - Automatic directory creation
   - Persistent storage for custom templates

3. **Five Preset Templates**

   a. **Product Cinematic** (`product_cinematic`)
      - Category: Product Showcase
      - Style: Cinematic
      - Duration: 15 seconds
      - Aspect Ratio: 16:9 (Landscape)
      - Quality: 1080p
      - Scenes: 3 scenes with dramatic lighting and slow camera movements
      - Features: Audio enabled, text overlays enabled

   b. **Social Dynamic** (`social_dynamic`)
      - Category: Social Media
      - Style: Dynamic
      - Duration: 10 seconds
      - Aspect Ratio: 9:16 (Portrait)
      - Quality: 1080p
      - Scenes: 4 fast-paced scenes with energetic movements
      - Features: Audio enabled, text overlays enabled

   c. **Minimal Elegant** (`minimal_elegant`)
      - Category: Product Showcase
      - Style: Minimal
      - Duration: 12 seconds
      - Aspect Ratio: 1:1 (Square)
      - Quality: 1080p
      - Scenes: 3 clean, minimalist scenes
      - Features: Text overlays enabled

   d. **Promotional Energetic** (`promo_energetic`)
      - Category: Promotional
      - Style: Energetic
      - Duration: 20 seconds
      - Aspect Ratio: 16:9 (Landscape)
      - Quality: 1080p
      - Scenes: 5 high-energy scenes with bold visuals
      - Features: Audio enabled, text overlays enabled

   e. **Professional Modern** (`professional_modern`)
      - Category: Educational
      - Style: Professional
      - Duration: 30 seconds
      - Aspect Ratio: 16:9 (Landscape)
      - Quality: 1080p
      - Scenes: 6 professional business-style scenes
      - Features: Audio enabled, text overlays enabled

### Task 7.2: 实现模板应用和自定义功能 ✅

**Completed Components:**

1. **Template Application Logic**
   - `apply_template()`: Converts template into VideoConfig for generation
   - Parameterization support for customizing template parameters
   - Scene generation from template definitions
   - Automatic prompt template substitution
   - Audio and text overlay configuration
   - Usage tracking for analytics

2. **Custom Template Management**
   - `create_custom_template()`: Create new custom templates
   - `update_template()`: Modify existing custom templates
   - `delete_template()`: Remove custom templates
   - Unique ID generation for custom templates
   - Validation of template configurations
   - Persistent storage of custom templates

3. **Template Discovery**
   - `list_templates()`: List all templates with optional category filtering
   - `get_template()`: Retrieve specific template by ID
   - `search_templates()`: Search by name, description, or tags
   - `get_template_categories()`: List all available categories
   - `get_template_styles()`: List all available styles

## API Reference

### TemplateManager Class

```python
class TemplateManager:
    def __init__(self, storage_path: Optional[str] = None)
    
    # Template Retrieval
    def get_template(self, template_id: str) -> Optional[VideoTemplate]
    def list_templates(self, category: Optional[TemplateCategory] = None) -> List[VideoTemplate]
    def search_templates(self, query: str) -> List[VideoTemplate]
    
    # Custom Template Management
    def create_custom_template(
        self,
        name: str,
        description: str,
        config: TemplateConfig,
        category: TemplateCategory = TemplateCategory.CUSTOM,
        scene_templates: Optional[List[Dict[str, Any]]] = None,
        tags: Optional[List[str]] = None
    ) -> str
    
    def update_template(self, template_id: str, updates: Dict[str, Any]) -> bool
    def delete_template(self, template_id: str) -> bool
    
    # Template Application
    def apply_template(
        self,
        template_id: str,
        input_images: List[str],
        custom_params: Optional[Dict[str, Any]] = None
    ) -> VideoConfig
    
    # Utility Methods
    def get_template_categories(self) -> List[str]
    def get_template_styles(self) -> List[str]
```

## Usage Examples

### Example 1: List All Templates

```python
from app_utils.video_studio import TemplateManager

manager = TemplateManager()
templates = manager.list_templates()

for template in templates:
    print(f"{template.template_id}: {template.metadata.name}")
    print(f"  Category: {template.metadata.category.value}")
    print(f"  Style: {template.config.style.value}")
    print(f"  Duration: {template.config.duration}s")
```

### Example 2: Apply a Preset Template

```python
from app_utils.video_studio import TemplateManager

manager = TemplateManager()

# Apply cinematic template to product images
video_config = manager.apply_template(
    template_id="product_cinematic",
    input_images=["asset_001", "asset_002", "asset_003"],
    custom_params={
        "product_name": "Premium Headphones",
        "audio_volume": 0.7,
        "duration": 18  # Override default duration
    }
)

# video_config is now ready for video generation
```

### Example 3: Create Custom Template

```python
from app_utils.video_studio import (
    TemplateManager,
    TemplateConfig,
    TemplateCategory,
    VideoStyle,
    AspectRatio,
    VideoQuality
)

manager = TemplateManager()

# Define custom template configuration
config = TemplateConfig(
    duration=25,
    aspect_ratio=AspectRatio.LANDSCAPE,
    quality=VideoQuality.FULL_HD_1080P,
    style=VideoStyle.MODERN,
    scene_count=5,
    default_scene_duration=5.0,
    camera_movements=["smooth_pan", "slow_zoom"],
    lighting_presets=["natural", "soft"],
    audio_enabled=True,
    text_overlays_enabled=True,
    transition_style="dissolve"
)

# Create custom template
template_id = manager.create_custom_template(
    name="My Brand Template",
    description="Custom template for brand videos",
    config=config,
    category=TemplateCategory.PROMOTIONAL,
    tags=["brand", "custom", "promotional"]
)

print(f"Created template: {template_id}")
```

## Integration with Video Studio

The Template System integrates seamlessly with the existing Video Studio components:

1. **WorkflowManager**: Uses templates to create video generation tasks
2. **GenerationEngine**: Processes video configs created from templates
3. **SceneGenerator**: Generates scenes based on template definitions
4. **AssetManager**: Manages input images referenced in templates

## Requirements Validation

**Requirement 1.2**: "WHEN 用户选择视频模板 THEN Template_System SHALL 提供至少5种不同风格的预设模板"

✅ **SATISFIED**: The system provides exactly 5 preset templates with distinct styles:
1. Cinematic Product Showcase
2. Dynamic Social Media
3. Minimal Elegant
4. Energetic Promotional
5. Professional Modern