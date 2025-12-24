"""
模板引擎

一致布局渲染和A+合规的模板引擎，负责：
- 为所有模块类型创建布局模板系统
- 实现动态内容放置算法
- 添加亚马逊A+合规验证(尺寸、文件大小)
- 创建一致的样式和品牌系统
- 实现响应式布局调整
"""

import logging
import json
import os
from typing import Dict, List, Optional, Any, Tuple, Union
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum
import hashlib
import threading
from PIL import Image, ImageDraw, ImageFont
import io

from .models import (
    ModuleType, MaterialSet, GeneratedModule, ComplianceStatus,
    ValidationStatus, UploadedFile
)
from .text_service import TextLanguage, APlusTextService

logger = logging.getLogger(__name__)


class LayoutType(Enum):
    """布局类型枚举"""
    HERO = "hero"  # 英雄式布局
    COMPARISON = "comparison"  # 对比布局
    GRID = "grid"  # 网格布局
    STEP_BY_STEP = "step_by_step"  # 步骤式布局
    FEATURE_BREAKDOWN = "feature_breakdown"  # 功能分解布局
    SHOWCASE = "showcase"  # 展示布局


class ContentPlacement(Enum):
    """内容放置位置枚举"""
    TOP_LEFT = "top_left"
    TOP_CENTER = "top_center"
    TOP_RIGHT = "top_right"
    CENTER_LEFT = "center_left"
    CENTER = "center"
    CENTER_RIGHT = "center_right"
    BOTTOM_LEFT = "bottom_left"
    BOTTOM_CENTER = "bottom_center"
    BOTTOM_RIGHT = "bottom_right"


@dataclass
class TemplateConfig:
    """模板配置"""
    template_id: str
    module_type: ModuleType
    layout_type: LayoutType
    canvas_size: Tuple[int, int] = (600, 450)  # A+标准尺寸
    background_color: str = "#FFFFFF"
    primary_color: str = "#232F3E"  # Amazon品牌色
    secondary_color: str = "#FF9900"  # Amazon橙色
    text_color: str = "#0F1111"
    font_family: str = "Arial"
    font_sizes: Dict[str, int] = None
    margins: Dict[str, int] = None
    spacing: Dict[str, int] = None
    language: TextLanguage = TextLanguage.CHINESE  # 默认中文
    text_direction: str = "ltr"  # 文本方向：ltr (左到右) 或 rtl (右到左)
    
    def __post_init__(self):
        if self.font_sizes is None:
            # 根据语言调整字体大小
            base_sizes = {
                'title': 24,
                'subtitle': 18,
                'body': 14,
                'caption': 12
            }
            
            # 中文和日文需要稍大的字体
            if self.language in [TextLanguage.CHINESE, TextLanguage.JAPANESE]:
                self.font_sizes = {k: v + 2 for k, v in base_sizes.items()}
            else:
                self.font_sizes = base_sizes
        
        if self.margins is None:
            self.margins = {
                'top': 20,
                'bottom': 20,
                'left': 20,
                'right': 20
            }
        
        if self.spacing is None:
            # 根据语言调整间距
            if self.language in [TextLanguage.CHINESE, TextLanguage.JAPANESE, TextLanguage.KOREAN]:
                self.spacing = {
                    'section': 18,  # 亚洲语言需要更大间距
                    'element': 12,
                    'text_line': 6
                }
            else:
                self.spacing = {
                    'section': 15,
                    'element': 10,
                    'text_line': 5
                }


@dataclass
class ContentElement:
    """内容元素"""
    element_id: str
    element_type: str  # text, image, shape, icon
    content: Any
    position: Tuple[int, int]
    size: Tuple[int, int]
    style: Dict[str, Any] = None
    z_index: int = 0
    
    def __post_init__(self):
        if self.style is None:
            self.style = {}


@dataclass
class TemplateLayout:
    """模板布局"""
    layout_id: str
    template_config: TemplateConfig
    content_elements: List[ContentElement]
    content_regions: Dict[str, Dict[str, Any]]  # 内容区域定义
    validation_rules: List[str] = None
    
    def __post_init__(self):
        if self.validation_rules is None:
            self.validation_rules = []


class TemplateEngine:
    """
    模板引擎
    
    提供一致的布局渲染和A+合规的模板系统。
    """
    
    def __init__(self, 
                 template_dir: str = "templates/aplus",
                 cache_size: int = 100,
                 enable_cache: bool = True):
        """
        初始化模板引擎
        
        Args:
            template_dir: 模板文件目录
            cache_size: 缓存大小
            enable_cache: 是否启用缓存
        """
        self.template_dir = Path(template_dir)
        self.cache_size = cache_size
        self.enable_cache = enable_cache
        
        # 模板缓存
        self._template_cache: Dict[str, TemplateLayout] = {}
        self._render_cache: Dict[str, bytes] = {}
        self._cache_lock = threading.RLock()
        
        # 模板配置
        self._module_templates: Dict[ModuleType, List[TemplateConfig]] = {}
        self._default_configs: Dict[ModuleType, TemplateConfig] = {}
        
        # 多语言支持
        self._text_service = APlusTextService()
        self._language_fonts = {
            TextLanguage.CHINESE: ["SimHei", "Microsoft YaHei", "Arial Unicode MS"],
            TextLanguage.JAPANESE: ["MS Gothic", "Yu Gothic", "Arial Unicode MS"],
            TextLanguage.KOREAN: ["Malgun Gothic", "Dotum", "Arial Unicode MS"],
            TextLanguage.ENGLISH: ["Arial", "Helvetica", "sans-serif"],
            TextLanguage.SPANISH: ["Arial", "Helvetica", "sans-serif"],
            TextLanguage.FRENCH: ["Arial", "Helvetica", "sans-serif"],
            TextLanguage.GERMAN: ["Arial", "Helvetica", "sans-serif"],
            TextLanguage.PORTUGUESE: ["Arial", "Helvetica", "sans-serif"],
            TextLanguage.ITALIAN: ["Arial", "Helvetica", "sans-serif"],
            TextLanguage.RUSSIAN: ["Arial", "Helvetica", "sans-serif"]
        }
        
        # 渲染统计
        self._render_stats = {
            'total_renders': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'average_render_time': 0.0,
            'compliance_failures': 0,
            'language_distribution': {}  # 语言使用统计
        }
        
        # A+合规规则
        self._compliance_rules = {
            'max_file_size': 5 * 1024 * 1024,  # 5MB
            'required_dimensions': (600, 450),
            'allowed_formats': ['PNG', 'JPEG', 'JPG'],
            'color_space': 'sRGB',
            'min_dpi': 72,
            'max_text_density': 0.7,  # 最大文本密度
            'min_contrast_ratio': 4.5  # 最小对比度
        }
        
        # 确保目录存在
        self.template_dir.mkdir(parents=True, exist_ok=True)
        
        # 初始化模板系统
        self._initialize_templates()
    
    def _initialize_templates(self):
        """初始化模板系统"""
        try:
            # 为每个模块类型创建默认模板配置
            self._create_default_templates()
            
            # 加载自定义模板（如果存在）
            self._load_custom_templates()
            
            logger.info(f"Template engine initialized with {len(self._module_templates)} module templates")
            
        except Exception as e:
            logger.error(f"Failed to initialize templates: {str(e)}")
    
    def _create_default_templates(self):
        """创建默认模板配置"""
        try:
            # 产品概览模块 - 英雄式布局
            self._default_configs[ModuleType.PRODUCT_OVERVIEW] = TemplateConfig(
                template_id="product_overview_hero",
                module_type=ModuleType.PRODUCT_OVERVIEW,
                layout_type=LayoutType.HERO,
                primary_color="#232F3E",
                secondary_color="#FF9900"
            )
            
            # 问题解决模块 - 对比布局
            self._default_configs[ModuleType.PROBLEM_SOLUTION] = TemplateConfig(
                template_id="problem_solution_comparison",
                module_type=ModuleType.PROBLEM_SOLUTION,
                layout_type=LayoutType.COMPARISON,
                primary_color="#D13212",  # 问题用红色
                secondary_color="#00A652"  # 解决方案用绿色
            )
            
            # 功能解析模块 - 功能分解布局
            self._default_configs[ModuleType.FEATURE_ANALYSIS] = TemplateConfig(
                template_id="feature_analysis_breakdown",
                module_type=ModuleType.FEATURE_ANALYSIS,
                layout_type=LayoutType.FEATURE_BREAKDOWN,
                primary_color="#232F3E",
                secondary_color="#0073BB"  # 技术蓝色
            )
            
            # 规格对比模块 - 网格布局
            self._default_configs[ModuleType.SPECIFICATION_COMPARISON] = TemplateConfig(
                template_id="spec_comparison_grid",
                module_type=ModuleType.SPECIFICATION_COMPARISON,
                layout_type=LayoutType.GRID,
                primary_color="#232F3E",
                secondary_color="#FF9900"
            )
            
            # 使用场景模块 - 展示布局
            self._default_configs[ModuleType.USAGE_SCENARIOS] = TemplateConfig(
                template_id="usage_scenarios_showcase",
                module_type=ModuleType.USAGE_SCENARIOS,
                layout_type=LayoutType.SHOWCASE,
                primary_color="#232F3E",
                secondary_color="#FF9900"
            )
            
            # 安装指南模块 - 步骤式布局
            self._default_configs[ModuleType.INSTALLATION_GUIDE] = TemplateConfig(
                template_id="installation_guide_steps",
                module_type=ModuleType.INSTALLATION_GUIDE,
                layout_type=LayoutType.STEP_BY_STEP,
                primary_color="#232F3E",
                secondary_color="#00A652"  # 成功绿色
            )
            
            # 为其余6个模块创建默认配置
            remaining_modules = [
                ModuleType.SIZE_COMPATIBILITY,
                ModuleType.MAINTENANCE_CARE,
                ModuleType.MATERIAL_CRAFTSMANSHIP,
                ModuleType.QUALITY_ASSURANCE,
                ModuleType.CUSTOMER_REVIEWS,
                ModuleType.PACKAGE_CONTENTS
            ]
            
            for module_type in remaining_modules:
                self._default_configs[module_type] = TemplateConfig(
                    template_id=f"{module_type.value}_default",
                    module_type=module_type,
                    layout_type=LayoutType.SHOWCASE,
                    primary_color="#232F3E",
                    secondary_color="#FF9900"
                )
            
            logger.info(f"Created {len(self._default_configs)} default template configurations")
            
        except Exception as e:
            logger.error(f"Failed to create default templates: {str(e)}")
    
    def _load_custom_templates(self):
        """加载自定义模板"""
        try:
            template_files = list(self.template_dir.glob("*.json"))
            loaded_count = 0
            
            for template_file in template_files:
                try:
                    with open(template_file, 'r', encoding='utf-8') as f:
                        template_data = json.load(f)
                    
                    # 解析模板配置
                    config = self._parse_template_config(template_data)
                    if config:
                        module_type = config.module_type
                        if module_type not in self._module_templates:
                            self._module_templates[module_type] = []
                        
                        self._module_templates[module_type].append(config)
                        loaded_count += 1
                        
                except Exception as e:
                    logger.warning(f"Failed to load template {template_file}: {str(e)}")
            
            if loaded_count > 0:
                logger.info(f"Loaded {loaded_count} custom templates")
                
        except Exception as e:
            logger.error(f"Failed to load custom templates: {str(e)}")
    
    def render_module(self, 
                     module_type: ModuleType,
                     materials: MaterialSet,
                     template_id: Optional[str] = None,
                     custom_config: Optional[Dict[str, Any]] = None,
                     language: Optional[TextLanguage] = None) -> GeneratedModule:
        """
        渲染模块
        
        Args:
            module_type: 模块类型
            materials: 素材集合
            template_id: 指定模板ID（可选）
            custom_config: 自定义配置（可选）
            language: 目标语言（可选）
            
        Returns:
            生成的模块
        """
        try:
            start_time = datetime.now()
            
            # 获取模板配置
            template_config = self._get_template_config(module_type, template_id, custom_config, language)
            
            # 处理多语言文本
            if language and language != TextLanguage.CHINESE:
                materials = self._translate_materials(materials, language)
            
            # 创建布局
            layout = self._create_layout(template_config, materials)
            
            # 渲染图像
            image_data = self._render_layout(layout, materials)
            
            # 合规验证
            compliance_result = self._validate_compliance(image_data, layout)
            
            # 计算渲染时间
            render_time = (datetime.now() - start_time).total_seconds()
            
            # 更新统计
            self._update_render_stats(render_time, compliance_result['compliant'], template_config.language)
            
            # 创建生成结果
            result = GeneratedModule(
                module_type=module_type,
                image_data=image_data,
                image_path=None,  # 将由调用者设置
                compliance_status=compliance_result['status'],
                generation_timestamp=datetime.now(),
                materials_used=materials,
                quality_score=self._calculate_quality_score(layout, materials, compliance_result),
                validation_status=ValidationStatus.PASSED if compliance_result['compliant'] else ValidationStatus.FAILED,
                prompt_used=f"Template: {template_config.template_id}, Language: {template_config.language.value}",
                generation_time=render_time
            )
            
            logger.info(f"Rendered {module_type.value} in {template_config.language.value} in {render_time:.2f}s")
            return result
            
        except Exception as e:
            logger.error(f"Failed to render module {module_type.value}: {str(e)}")
            
            # 返回错误结果
            return GeneratedModule(
                module_type=module_type,
                image_data=None,
                image_path=None,
                compliance_status=ComplianceStatus.NON_COMPLIANT,
                generation_timestamp=datetime.now(),
                materials_used=materials,
                quality_score=0.0,
                validation_status=ValidationStatus.FAILED,
                prompt_used=f"Error: {str(e)}",
                generation_time=0.0
            )
    
    def _get_template_config(self, 
                           module_type: ModuleType,
                           template_id: Optional[str] = None,
                           custom_config: Optional[Dict[str, Any]] = None,
                           language: Optional[TextLanguage] = None) -> TemplateConfig:
        """获取模板配置"""
        try:
            # 使用指定模板
            if template_id:
                templates = self._module_templates.get(module_type, [])
                for template in templates:
                    if template.template_id == template_id:
                        config = template
                        break
                else:
                    # 未找到指定模板，使用默认
                    config = self._default_configs.get(module_type)
            else:
                # 使用默认模板
                config = self._default_configs.get(module_type)
            
            if not config:
                raise ValueError(f"No template found for module type {module_type.value}")
            
            # 设置语言
            if language:
                config.language = language
                config.text_direction = self._get_text_direction(language)
                # 根据语言调整字体
                config.font_family = self._get_language_font(language)
            
            # 应用自定义配置
            if custom_config:
                config = self._apply_custom_config(config, custom_config)
            
            return config
            
        except Exception as e:
            logger.error(f"Failed to get template config: {str(e)}")
            raise
    
    def _create_layout(self, config: TemplateConfig, materials: MaterialSet) -> TemplateLayout:
        """创建布局"""
        try:
            layout_id = f"{config.template_id}_{int(datetime.now().timestamp())}"
            
            # 根据布局类型创建内容元素
            content_elements = []
            content_regions = {}
            
            if config.layout_type == LayoutType.HERO:
                content_elements, content_regions = self._create_hero_layout(config, materials)
            elif config.layout_type == LayoutType.COMPARISON:
                content_elements, content_regions = self._create_comparison_layout(config, materials)
            elif config.layout_type == LayoutType.GRID:
                content_elements, content_regions = self._create_grid_layout(config, materials)
            elif config.layout_type == LayoutType.STEP_BY_STEP:
                content_elements, content_regions = self._create_step_layout(config, materials)
            elif config.layout_type == LayoutType.FEATURE_BREAKDOWN:
                content_elements, content_regions = self._create_feature_layout(config, materials)
            else:  # SHOWCASE
                content_elements, content_regions = self._create_showcase_layout(config, materials)
            
            # 创建布局对象
            layout = TemplateLayout(
                layout_id=layout_id,
                template_config=config,
                content_elements=content_elements,
                content_regions=content_regions,
                validation_rules=self._get_validation_rules(config.module_type)
            )
            
            return layout
            
        except Exception as e:
            logger.error(f"Failed to create layout: {str(e)}")
            raise
    
    def _create_hero_layout(self, config: TemplateConfig, materials: MaterialSet) -> Tuple[List[ContentElement], Dict[str, Any]]:
        """创建英雄式布局"""
        elements = []
        regions = {}
        
        canvas_width, canvas_height = config.canvas_size
        margin = config.margins['left']
        
        # 主产品图片区域（左侧）
        product_image_region = {
            'x': margin,
            'y': margin,
            'width': canvas_width // 2 - margin * 2,
            'height': canvas_height - margin * 2,
            'type': 'image',
            'priority': 1
        }
        regions['product_image'] = product_image_region
        
        # 如果有产品图片，添加图片元素
        if materials.images:
            main_image = materials.images[0]  # 使用第一张图片作为主图
            elements.append(ContentElement(
                element_id="hero_product_image",
                element_type="image",
                content=main_image,
                position=(product_image_region['x'], product_image_region['y']),
                size=(product_image_region['width'], product_image_region['height']),
                z_index=1
            ))
        
        # 文本内容区域（右侧）
        text_region = {
            'x': canvas_width // 2 + margin,
            'y': margin,
            'width': canvas_width // 2 - margin * 2,
            'height': canvas_height - margin * 2,
            'type': 'text',
            'priority': 2
        }
        regions['text_content'] = text_region
        
        # 添加标题
        if materials.text_inputs:
            title_text = materials.text_inputs[0] if materials.text_inputs else "产品标题"
            elements.append(ContentElement(
                element_id="hero_title",
                element_type="text",
                content=title_text,
                position=(text_region['x'], text_region['y']),
                size=(text_region['width'], config.font_sizes['title'] + 10),
                style={
                    'font_size': config.font_sizes['title'],
                    'font_weight': 'bold',
                    'color': config.primary_color,
                    'align': 'left'
                },
                z_index=2
            ))
        
        # 添加特性列表
        if len(materials.text_inputs) > 1:
            features_y = text_region['y'] + config.font_sizes['title'] + config.spacing['section']
            for i, feature in enumerate(materials.text_inputs[1:4]):  # 最多3个特性
                elements.append(ContentElement(
                    element_id=f"hero_feature_{i}",
                    element_type="text",
                    content=f"• {feature}",
                    position=(text_region['x'], features_y + i * (config.font_sizes['body'] + config.spacing['text_line'])),
                    size=(text_region['width'], config.font_sizes['body'] + 5),
                    style={
                        'font_size': config.font_sizes['body'],
                        'color': config.text_color,
                        'align': 'left'
                    },
                    z_index=2
                ))
        
        return elements, regions
    
    def _create_comparison_layout(self, config: TemplateConfig, materials: MaterialSet) -> Tuple[List[ContentElement], Dict[str, Any]]:
        """创建对比布局"""
        elements = []
        regions = {}
        
        canvas_width, canvas_height = config.canvas_size
        margin = config.margins['left']
        center_x = canvas_width // 2
        
        # 问题区域（左侧）
        problem_region = {
            'x': margin,
            'y': margin,
            'width': center_x - margin * 2,
            'height': canvas_height - margin * 2,
            'type': 'mixed',
            'priority': 1
        }
        regions['problem'] = problem_region
        
        # 解决方案区域（右侧）
        solution_region = {
            'x': center_x + margin,
            'y': margin,
            'width': center_x - margin * 2,
            'height': canvas_height - margin * 2,
            'type': 'mixed',
            'priority': 1
        }
        regions['solution'] = solution_region
        
        # 添加问题标题
        elements.append(ContentElement(
            element_id="problem_title",
            element_type="text",
            content="问题",
            position=(problem_region['x'], problem_region['y']),
            size=(problem_region['width'], config.font_sizes['subtitle'] + 10),
            style={
                'font_size': config.font_sizes['subtitle'],
                'font_weight': 'bold',
                'color': config.primary_color,
                'align': 'center'
            },
            z_index=2
        ))
        
        # 添加解决方案标题
        elements.append(ContentElement(
            element_id="solution_title",
            element_type="text",
            content="解决方案",
            position=(solution_region['x'], solution_region['y']),
            size=(solution_region['width'], config.font_sizes['subtitle'] + 10),
            style={
                'font_size': config.font_sizes['subtitle'],
                'font_weight': 'bold',
                'color': config.secondary_color,
                'align': 'center'
            },
            z_index=2
        ))
        
        # 添加对比箭头
        arrow_y = canvas_height // 2
        elements.append(ContentElement(
            element_id="comparison_arrow",
            element_type="shape",
            content="arrow_right",
            position=(center_x - 15, arrow_y - 10),
            size=(30, 20),
            style={
                'color': config.secondary_color,
                'stroke_width': 3
            },
            z_index=3
        ))
        
        return elements, regions
    
    def _create_grid_layout(self, config: TemplateConfig, materials: MaterialSet) -> Tuple[List[ContentElement], Dict[str, Any]]:
        """创建网格布局"""
        elements = []
        regions = {}
        
        canvas_width, canvas_height = config.canvas_size
        margin = config.margins['left']
        
        # 创建2x2网格
        grid_width = (canvas_width - margin * 3) // 2
        grid_height = (canvas_height - margin * 3) // 2
        
        grid_positions = [
            (margin, margin),  # 左上
            (margin + grid_width + margin, margin),  # 右上
            (margin, margin + grid_height + margin),  # 左下
            (margin + grid_width + margin, margin + grid_height + margin)  # 右下
        ]
        
        for i, (x, y) in enumerate(grid_positions):
            region_id = f"grid_cell_{i}"
            regions[region_id] = {
                'x': x,
                'y': y,
                'width': grid_width,
                'height': grid_height,
                'type': 'mixed',
                'priority': i + 1
            }
            
            # 如果有对应的图片或文本，添加元素
            if i < len(materials.images):
                elements.append(ContentElement(
                    element_id=f"grid_image_{i}",
                    element_type="image",
                    content=materials.images[i],
                    position=(x, y),
                    size=(grid_width, grid_height // 2),
                    z_index=1
                ))
            
            if i < len(materials.text_inputs):
                elements.append(ContentElement(
                    element_id=f"grid_text_{i}",
                    element_type="text",
                    content=materials.text_inputs[i],
                    position=(x, y + grid_height // 2),
                    size=(grid_width, grid_height // 2),
                    style={
                        'font_size': config.font_sizes['body'],
                        'color': config.text_color,
                        'align': 'center'
                    },
                    z_index=2
                ))
        
        return elements, regions
    
    def _create_step_layout(self, config: TemplateConfig, materials: MaterialSet) -> Tuple[List[ContentElement], Dict[str, Any]]:
        """创建步骤式布局"""
        elements = []
        regions = {}
        
        canvas_width, canvas_height = config.canvas_size
        margin = config.margins['left']
        
        # 计算步骤数量（最多4步）
        max_steps = min(4, len(materials.text_inputs) if materials.text_inputs else 2)
        step_height = (canvas_height - margin * (max_steps + 1)) // max_steps
        
        for i in range(max_steps):
            y_pos = margin + i * (step_height + margin)
            
            # 步骤区域
            step_region = {
                'x': margin,
                'y': y_pos,
                'width': canvas_width - margin * 2,
                'height': step_height,
                'type': 'mixed',
                'priority': i + 1
            }
            regions[f'step_{i}'] = step_region
            
            # 步骤编号
            elements.append(ContentElement(
                element_id=f"step_number_{i}",
                element_type="shape",
                content=str(i + 1),
                position=(margin, y_pos),
                size=(30, 30),
                style={
                    'shape': 'circle',
                    'background_color': config.secondary_color,
                    'text_color': 'white',
                    'font_size': config.font_sizes['body'],
                    'font_weight': 'bold'
                },
                z_index=3
            ))
            
            # 步骤文本
            if i < len(materials.text_inputs):
                elements.append(ContentElement(
                    element_id=f"step_text_{i}",
                    element_type="text",
                    content=materials.text_inputs[i],
                    position=(margin + 40, y_pos + 5),
                    size=(canvas_width - margin * 2 - 40, step_height - 10),
                    style={
                        'font_size': config.font_sizes['body'],
                        'color': config.text_color,
                        'align': 'left'
                    },
                    z_index=2
                ))
        
        return elements, regions
    
    def _create_feature_layout(self, config: TemplateConfig, materials: MaterialSet) -> Tuple[List[ContentElement], Dict[str, Any]]:
        """创建功能分解布局"""
        elements = []
        regions = {}
        
        canvas_width, canvas_height = config.canvas_size
        margin = config.margins['left']
        
        # 主图区域（上半部分）
        main_image_region = {
            'x': margin,
            'y': margin,
            'width': canvas_width - margin * 2,
            'height': canvas_height // 2 - margin,
            'type': 'image',
            'priority': 1
        }
        regions['main_image'] = main_image_region
        
        if materials.images:
            elements.append(ContentElement(
                element_id="feature_main_image",
                element_type="image",
                content=materials.images[0],
                position=(main_image_region['x'], main_image_region['y']),
                size=(main_image_region['width'], main_image_region['height']),
                z_index=1
            ))
        
        # 功能标注区域（下半部分）
        features_region = {
            'x': margin,
            'y': canvas_height // 2 + margin,
            'width': canvas_width - margin * 2,
            'height': canvas_height // 2 - margin * 2,
            'type': 'text',
            'priority': 2
        }
        regions['features'] = features_region
        
        # 添加功能列表
        if materials.text_inputs:
            feature_height = features_region['height'] // min(3, len(materials.text_inputs))
            for i, feature in enumerate(materials.text_inputs[:3]):
                y_pos = features_region['y'] + i * feature_height
                
                elements.append(ContentElement(
                    element_id=f"feature_item_{i}",
                    element_type="text",
                    content=f"▶ {feature}",
                    position=(features_region['x'], y_pos),
                    size=(features_region['width'], feature_height),
                    style={
                        'font_size': config.font_sizes['body'],
                        'color': config.text_color,
                        'align': 'left'
                    },
                    z_index=2
                ))
        
        return elements, regions
    
    def _create_showcase_layout(self, config: TemplateConfig, materials: MaterialSet) -> Tuple[List[ContentElement], Dict[str, Any]]:
        """创建展示布局"""
        elements = []
        regions = {}
        
        canvas_width, canvas_height = config.canvas_size
        margin = config.margins['left']
        
        # 标题区域
        title_region = {
            'x': margin,
            'y': margin,
            'width': canvas_width - margin * 2,
            'height': config.font_sizes['title'] + 20,
            'type': 'text',
            'priority': 1
        }
        regions['title'] = title_region
        
        # 主内容区域
        content_region = {
            'x': margin,
            'y': title_region['y'] + title_region['height'] + config.spacing['section'],
            'width': canvas_width - margin * 2,
            'height': canvas_height - title_region['height'] - margin * 3 - config.spacing['section'],
            'type': 'mixed',
            'priority': 2
        }
        regions['content'] = content_region
        
        # 添加标题
        if materials.text_inputs:
            elements.append(ContentElement(
                element_id="showcase_title",
                element_type="text",
                content=materials.text_inputs[0],
                position=(title_region['x'], title_region['y']),
                size=(title_region['width'], title_region['height']),
                style={
                    'font_size': config.font_sizes['title'],
                    'font_weight': 'bold',
                    'color': config.primary_color,
                    'align': 'center'
                },
                z_index=2
            ))
        
        # 添加主图片
        if materials.images:
            image_height = content_region['height'] * 2 // 3
            elements.append(ContentElement(
                element_id="showcase_image",
                element_type="image",
                content=materials.images[0],
                position=(content_region['x'], content_region['y']),
                size=(content_region['width'], image_height),
                z_index=1
            ))
            
            # 添加描述文本
            if len(materials.text_inputs) > 1:
                text_y = content_region['y'] + image_height + config.spacing['element']
                elements.append(ContentElement(
                    element_id="showcase_description",
                    element_type="text",
                    content=materials.text_inputs[1],
                    position=(content_region['x'], text_y),
                    size=(content_region['width'], content_region['height'] - image_height - config.spacing['element']),
                    style={
                        'font_size': config.font_sizes['body'],
                        'color': config.text_color,
                        'align': 'center'
                    },
                    z_index=2
                ))
        
        return elements, regions
    
    def _render_layout(self, layout: TemplateLayout, materials: MaterialSet) -> bytes:
        """渲染布局为图像"""
        try:
            config = layout.template_config
            canvas_width, canvas_height = config.canvas_size
            
            # 创建画布
            image = Image.new('RGB', (canvas_width, canvas_height), config.background_color)
            draw = ImageDraw.Draw(image)
            
            # 按z_index排序元素
            sorted_elements = sorted(layout.content_elements, key=lambda x: x.z_index)
            
            # 渲染每个元素
            for element in sorted_elements:
                self._render_element(image, draw, element, materials)
            
            # 转换为字节数据
            img_buffer = io.BytesIO()
            image.save(img_buffer, format='PNG', optimize=True, dpi=(72, 72))
            img_buffer.seek(0)
            
            return img_buffer.getvalue()
            
        except Exception as e:
            logger.error(f"Failed to render layout: {str(e)}")
            # 返回错误图像
            return self._create_error_image(config.canvas_size, str(e))
    
    def _render_element(self, image: Image.Image, draw: ImageDraw.Draw, 
                       element: ContentElement, materials: MaterialSet):
        """渲染单个元素"""
        try:
            if element.element_type == "text":
                self._render_text_element(draw, element)
            elif element.element_type == "image":
                self._render_image_element(image, element, materials)
            elif element.element_type == "shape":
                self._render_shape_element(draw, element)
            
        except Exception as e:
            logger.warning(f"Failed to render element {element.element_id}: {str(e)}")
    
    def _render_text_element(self, draw: ImageDraw.Draw, element: ContentElement):
        """渲染文本元素"""
        try:
            text = str(element.content)
            x, y = element.position
            width, height = element.size
            style = element.style or {}
            
            # 获取字体
            font_size = style.get('font_size', 14)
            try:
                # 尝试使用系统字体
                font = ImageFont.truetype("arial.ttf", font_size)
            except:
                # 使用默认字体
                font = ImageFont.load_default()
            
            # 获取文本颜色
            text_color = style.get('color', '#000000')
            
            # 文本对齐
            align = style.get('align', 'left')
            
            # 处理多行文本
            lines = self._wrap_text(text, font, width)
            line_height = font_size + style.get('line_spacing', 5)
            
            for i, line in enumerate(lines):
                line_y = y + i * line_height
                if line_y + line_height > y + height:
                    break  # 超出区域
                
                # 计算x位置
                if align == 'center':
                    bbox = draw.textbbox((0, 0), line, font=font)
                    text_width = bbox[2] - bbox[0]
                    line_x = x + (width - text_width) // 2
                elif align == 'right':
                    bbox = draw.textbbox((0, 0), line, font=font)
                    text_width = bbox[2] - bbox[0]
                    line_x = x + width - text_width
                else:  # left
                    line_x = x
                
                # 绘制文本
                draw.text((line_x, line_y), line, fill=text_color, font=font)
                
        except Exception as e:
            logger.error(f"Failed to render text element: {str(e)}")
    
    def _render_image_element(self, canvas: Image.Image, element: ContentElement, materials: MaterialSet):
        """渲染图像元素"""
        try:
            x, y = element.position
            width, height = element.size
            
            # 获取图像数据
            if isinstance(element.content, UploadedFile):
                image_data = element.content.file_content
            else:
                # 如果是其他类型，尝试从materials中找到对应图像
                if materials.images:
                    image_data = materials.images[0].file_content
                else:
                    return  # 没有图像数据
            
            # 加载图像
            source_image = Image.open(io.BytesIO(image_data))
            
            # 调整图像大小
            resized_image = source_image.resize((width, height), Image.Resampling.LANCZOS)
            
            # 确保图像模式兼容
            if resized_image.mode != 'RGB':
                resized_image = resized_image.convert('RGB')
            
            # 粘贴到画布
            canvas.paste(resized_image, (x, y))
            
        except Exception as e:
            logger.error(f"Failed to render image element: {str(e)}")
            # 绘制占位符
            draw = ImageDraw.Draw(canvas)
            draw.rectangle([x, y, x + width, y + height], outline='#CCCCCC', fill='#F0F0F0')
            draw.text((x + 10, y + 10), "图像加载失败", fill='#666666')
    
    def _render_shape_element(self, draw: ImageDraw.Draw, element: ContentElement):
        """渲染形状元素"""
        try:
            x, y = element.position
            width, height = element.size
            style = element.style or {}
            
            shape_type = style.get('shape', 'rectangle')
            fill_color = style.get('background_color', '#FFFFFF')
            outline_color = style.get('color', '#000000')
            stroke_width = style.get('stroke_width', 1)
            
            if shape_type == 'circle':
                # 绘制圆形
                draw.ellipse([x, y, x + width, y + height], 
                           fill=fill_color, outline=outline_color, width=stroke_width)
                
                # 如果有文本内容，在圆形中心绘制
                if element.content and str(element.content).strip():
                    text = str(element.content)
                    font_size = style.get('font_size', 14)
                    try:
                        font = ImageFont.truetype("arial.ttf", font_size)
                    except:
                        font = ImageFont.load_default()
                    
                    bbox = draw.textbbox((0, 0), text, font=font)
                    text_width = bbox[2] - bbox[0]
                    text_height = bbox[3] - bbox[1]
                    
                    text_x = x + (width - text_width) // 2
                    text_y = y + (height - text_height) // 2
                    
                    text_color = style.get('text_color', '#000000')
                    draw.text((text_x, text_y), text, fill=text_color, font=font)
            
            elif element.content == "arrow_right":
                # 绘制右箭头
                mid_y = y + height // 2
                points = [
                    (x, y),
                    (x + width - 10, y),
                    (x + width - 10, y - 5),
                    (x + width, mid_y),
                    (x + width - 10, y + height + 5),
                    (x + width - 10, y + height),
                    (x, y + height)
                ]
                draw.polygon(points, fill=fill_color, outline=outline_color)
            
            else:  # rectangle
                draw.rectangle([x, y, x + width, y + height], 
                             fill=fill_color, outline=outline_color, width=stroke_width)
                
        except Exception as e:
            logger.error(f"Failed to render shape element: {str(e)}")
    
    def _wrap_text(self, text: str, font, max_width: int) -> List[str]:
        """文本换行"""
        try:
            words = text.split()
            lines = []
            current_line = []
            
            for word in words:
                test_line = ' '.join(current_line + [word])
                bbox = ImageDraw.Draw(Image.new('RGB', (1, 1))).textbbox((0, 0), test_line, font=font)
                text_width = bbox[2] - bbox[0]
                
                if text_width <= max_width:
                    current_line.append(word)
                else:
                    if current_line:
                        lines.append(' '.join(current_line))
                        current_line = [word]
                    else:
                        # 单词太长，强制换行
                        lines.append(word)
            
            if current_line:
                lines.append(' '.join(current_line))
            
            return lines
            
        except Exception as e:
            logger.error(f"Failed to wrap text: {str(e)}")
            return [text]  # 返回原文本
    
    def _validate_compliance(self, image_data: bytes, layout: TemplateLayout) -> Dict[str, Any]:
        """验证A+合规性"""
        try:
            compliance_issues = []
            recommendations = []
            
            # 检查文件大小
            file_size = len(image_data)
            if file_size > self._compliance_rules['max_file_size']:
                compliance_issues.append(f"文件大小 {file_size / 1024 / 1024:.1f}MB 超过限制 {self._compliance_rules['max_file_size'] / 1024 / 1024}MB")
                recommendations.append("优化图像质量或减少内容复杂度")
            
            # 检查图像尺寸
            try:
                image = Image.open(io.BytesIO(image_data))
                width, height = image.size
                required_width, required_height = self._compliance_rules['required_dimensions']
                
                if (width, height) != (required_width, required_height):
                    compliance_issues.append(f"图像尺寸 {width}x{height} 不符合要求 {required_width}x{required_height}")
                    recommendations.append("调整画布尺寸为600x450像素")
                
                # 检查色彩空间
                if hasattr(image, 'info') and image.info.get('icc_profile'):
                    # 简化的色彩空间检查
                    pass
                
            except Exception as e:
                compliance_issues.append(f"无法验证图像属性: {str(e)}")
            
            # 检查文本密度
            text_elements = [e for e in layout.content_elements if e.element_type == "text"]
            total_text_area = sum(e.size[0] * e.size[1] for e in text_elements)
            canvas_area = layout.template_config.canvas_size[0] * layout.template_config.canvas_size[1]
            text_density = total_text_area / canvas_area if canvas_area > 0 else 0
            
            if text_density > self._compliance_rules['max_text_density']:
                compliance_issues.append(f"文本密度 {text_density:.2f} 超过建议值 {self._compliance_rules['max_text_density']}")
                recommendations.append("减少文本内容或增加图像比例")
            
            # 确定合规状态
            if not compliance_issues:
                status = ComplianceStatus.COMPLIANT
                compliant = True
            elif len(compliance_issues) <= 2:
                status = ComplianceStatus.NEEDS_OPTIMIZATION
                compliant = False
            else:
                status = ComplianceStatus.NON_COMPLIANT
                compliant = False
            
            return {
                'compliant': compliant,
                'status': status,
                'issues': compliance_issues,
                'recommendations': recommendations,
                'file_size': file_size,
                'text_density': text_density
            }
            
        except Exception as e:
            logger.error(f"Compliance validation failed: {str(e)}")
            return {
                'compliant': False,
                'status': ComplianceStatus.NON_COMPLIANT,
                'issues': [f"验证失败: {str(e)}"],
                'recommendations': ["请检查模板配置和素材"],
                'file_size': len(image_data) if image_data else 0,
                'text_density': 0.0
            }
    
    def _calculate_quality_score(self, layout: TemplateLayout, materials: MaterialSet, 
                               compliance_result: Dict[str, Any]) -> float:
        """计算质量分数"""
        try:
            score = 1.0
            
            # 合规性影响 (40%)
            if compliance_result['compliant']:
                compliance_score = 1.0
            elif compliance_result['status'] == ComplianceStatus.NEEDS_OPTIMIZATION:
                compliance_score = 0.7
            else:
                compliance_score = 0.3
            
            # 内容完整性影响 (30%)
            content_score = 0.5  # 基础分
            if materials.images:
                content_score += 0.3
            if materials.text_inputs:
                content_score += 0.2
            content_score = min(content_score, 1.0)
            
            # 布局复杂度影响 (20%)
            layout_score = min(len(layout.content_elements) / 10.0, 1.0)
            
            # 文件大小优化影响 (10%)
            file_size = compliance_result.get('file_size', 0)
            max_size = self._compliance_rules['max_file_size']
            size_ratio = file_size / max_size if max_size > 0 else 0
            size_score = max(0, 1.0 - size_ratio)
            
            # 加权计算最终分数
            final_score = (
                compliance_score * 0.4 +
                content_score * 0.3 +
                layout_score * 0.2 +
                size_score * 0.1
            )
            
            return round(final_score, 3)
            
        except Exception as e:
            logger.error(f"Failed to calculate quality score: {str(e)}")
            return 0.5
    
    def _create_error_image(self, canvas_size: Tuple[int, int], error_message: str) -> bytes:
        """创建错误图像"""
        try:
            width, height = canvas_size
            image = Image.new('RGB', (width, height), '#F0F0F0')
            draw = ImageDraw.Draw(image)
            
            # 绘制错误信息
            try:
                font = ImageFont.truetype("arial.ttf", 16)
            except:
                font = ImageFont.load_default()
            
            # 绘制边框
            draw.rectangle([10, 10, width-10, height-10], outline='#FF0000', width=2)
            
            # 绘制错误文本
            error_text = f"渲染错误:\n{error_message}"
            lines = error_text.split('\n')
            
            y_offset = height // 2 - len(lines) * 10
            for i, line in enumerate(lines):
                bbox = draw.textbbox((0, 0), line, font=font)
                text_width = bbox[2] - bbox[0]
                x_offset = (width - text_width) // 2
                draw.text((x_offset, y_offset + i * 20), line, fill='#FF0000', font=font)
            
            # 转换为字节
            img_buffer = io.BytesIO()
            image.save(img_buffer, format='PNG')
            img_buffer.seek(0)
            
            return img_buffer.getvalue()
            
        except Exception as e:
            logger.error(f"Failed to create error image: {str(e)}")
            # 返回最小错误图像
            return b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x02X\x00\x00\x01\xc2\x08\x02\x00\x00\x00'
    
    def _update_render_stats(self, render_time: float, compliant: bool, language: Optional[TextLanguage] = None):
        """更新渲染统计"""
        try:
            with self._cache_lock:
                self._render_stats['total_renders'] += 1
                
                # 更新平均渲染时间
                total_time = self._render_stats['average_render_time'] * (self._render_stats['total_renders'] - 1)
                self._render_stats['average_render_time'] = (total_time + render_time) / self._render_stats['total_renders']
                
                if not compliant:
                    self._render_stats['compliance_failures'] += 1
                
                # 更新语言使用统计
                if language:
                    lang_key = language.value
                    self._render_stats['language_distribution'][lang_key] = (
                        self._render_stats['language_distribution'].get(lang_key, 0) + 1
                    )
                    
        except Exception as e:
            logger.error(f"Failed to update render stats: {str(e)}")
    
    def _parse_template_config(self, template_data: Dict[str, Any]) -> Optional[TemplateConfig]:
        """解析模板配置"""
        try:
            return TemplateConfig(
                template_id=template_data['template_id'],
                module_type=ModuleType(template_data['module_type']),
                layout_type=LayoutType(template_data['layout_type']),
                canvas_size=tuple(template_data.get('canvas_size', [600, 450])),
                background_color=template_data.get('background_color', '#FFFFFF'),
                primary_color=template_data.get('primary_color', '#232F3E'),
                secondary_color=template_data.get('secondary_color', '#FF9900'),
                text_color=template_data.get('text_color', '#0F1111'),
                font_family=template_data.get('font_family', 'Arial'),
                font_sizes=template_data.get('font_sizes'),
                margins=template_data.get('margins'),
                spacing=template_data.get('spacing')
            )
            
        except Exception as e:
            logger.error(f"Failed to parse template config: {str(e)}")
            return None
    
    def _apply_custom_config(self, base_config: TemplateConfig, custom_config: Dict[str, Any]) -> TemplateConfig:
        """应用自定义配置"""
        try:
            # 创建配置副本
            config_dict = asdict(base_config)
            
            # 应用自定义设置
            for key, value in custom_config.items():
                if key in config_dict:
                    config_dict[key] = value
            
            # 重建配置对象
            return TemplateConfig(**config_dict)
            
        except Exception as e:
            logger.error(f"Failed to apply custom config: {str(e)}")
            return base_config
    
    def _get_validation_rules(self, module_type: ModuleType) -> List[str]:
        """获取模块验证规则"""
        base_rules = [
            "canvas_size_600x450",
            "max_file_size_5mb",
            "srgb_color_space",
            "min_dpi_72"
        ]
        
        # 根据模块类型添加特定规则
        if module_type == ModuleType.PRODUCT_OVERVIEW:
            base_rules.extend([
                "require_product_image",
                "require_title_text",
                "max_features_5"
            ])
        elif module_type == ModuleType.PROBLEM_SOLUTION:
            base_rules.extend([
                "require_problem_description",
                "require_solution_description",
                "visual_contrast_required"
            ])
        elif module_type == ModuleType.INSTALLATION_GUIDE:
            base_rules.extend([
                "require_step_sequence",
                "max_steps_6",
                "require_safety_warnings"
            ])
        
        return base_rules
    
    def get_available_templates(self, module_type: Optional[ModuleType] = None) -> List[Dict[str, Any]]:
        """获取可用模板列表"""
        try:
            templates = []
            
            # 获取指定模块类型的模板
            if module_type:
                module_types = [module_type]
            else:
                module_types = list(ModuleType)
            
            for mt in module_types:
                # 添加默认模板
                if mt in self._default_configs:
                    config = self._default_configs[mt]
                    templates.append({
                        'template_id': config.template_id,
                        'module_type': mt.value,
                        'layout_type': config.layout_type.value,
                        'name': f"{mt.value.replace('_', ' ').title()} 默认模板",
                        'description': f"适用于{mt.value}的标准布局模板",
                        'is_default': True,
                        'canvas_size': config.canvas_size,
                        'primary_color': config.primary_color,
                        'secondary_color': config.secondary_color
                    })
                
                # 添加自定义模板
                custom_templates = self._module_templates.get(mt, [])
                for config in custom_templates:
                    templates.append({
                        'template_id': config.template_id,
                        'module_type': mt.value,
                        'layout_type': config.layout_type.value,
                        'name': config.template_id.replace('_', ' ').title(),
                        'description': f"自定义{mt.value}模板",
                        'is_default': False,
                        'canvas_size': config.canvas_size,
                        'primary_color': config.primary_color,
                        'secondary_color': config.secondary_color
                    })
            
            return templates
            
        except Exception as e:
            logger.error(f"Failed to get available templates: {str(e)}")
            return []
    
    def get_render_statistics(self) -> Dict[str, Any]:
        """获取渲染统计信息"""
        try:
            with self._cache_lock:
                stats = self._render_stats.copy()
                
                # 计算成功率
                if stats['total_renders'] > 0:
                    stats['success_rate'] = (
                        (stats['total_renders'] - stats['compliance_failures']) / 
                        stats['total_renders'] * 100
                    )
                    stats['compliance_rate'] = (
                        (stats['total_renders'] - stats['compliance_failures']) / 
                        stats['total_renders'] * 100
                    )
                else:
                    stats['success_rate'] = 0.0
                    stats['compliance_rate'] = 0.0
                
                # 缓存统计
                stats['cache_hit_rate'] = (
                    stats['cache_hits'] / (stats['cache_hits'] + stats['cache_misses']) * 100
                    if (stats['cache_hits'] + stats['cache_misses']) > 0 else 0.0
                )
                
                return stats
                
        except Exception as e:
            logger.error(f"Failed to get render statistics: {str(e)}")
            return {}
    
    def clear_cache(self):
        """清理缓存"""
        try:
            with self._cache_lock:
                self._template_cache.clear()
                self._render_cache.clear()
                logger.info("Template engine cache cleared")
                
        except Exception as e:
            logger.error(f"Failed to clear cache: {str(e)}")
    
    def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        try:
            # 检查模板目录
            template_dir_accessible = self.template_dir.exists() and self.template_dir.is_dir()
            
            # 检查默认模板
            default_templates_count = len(self._default_configs)
            custom_templates_count = sum(len(templates) for templates in self._module_templates.values())
            
            # 检查缓存状态
            cache_usage = len(self._template_cache) + len(self._render_cache)
            
            # 获取统计信息
            stats = self.get_render_statistics()
            
            # 确定健康状态
            if not template_dir_accessible:
                status = 'error'
                message = 'Template directory not accessible'
            elif default_templates_count < len(ModuleType):
                status = 'warning'
                message = 'Some default templates missing'
            elif stats.get('compliance_rate', 100) < 80:
                status = 'warning'
                message = 'Low compliance rate'
            else:
                status = 'healthy'
                message = 'All systems operational'
            
            return {
                'status': status,
                'message': message,
                'template_dir_accessible': template_dir_accessible,
                'default_templates': default_templates_count,
                'custom_templates': custom_templates_count,
                'cache_usage': cache_usage,
                'cache_enabled': self.enable_cache,
                'statistics': stats,
                'compliance_rules': len(self._compliance_rules),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Template engine health check failed: {str(e)}")
            return {
                'status': 'error',
                'message': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def _translate_materials(self, materials: MaterialSet, target_language: TextLanguage) -> MaterialSet:
        """翻译素材文本内容"""
        try:
            if not materials.text_inputs and not materials.custom_prompts:
                return materials
            
            # 创建新的素材集合
            translated_materials = MaterialSet(
                images=materials.images,  # 图片不需要翻译
                documents=materials.documents,  # 文档保持原样
                text_inputs=[],
                custom_prompts=[]
            )
            
            # 翻译文本输入
            if materials.text_inputs:
                for text in materials.text_inputs:
                    try:
                        translated_text = self._text_service.translate_text(text, target_language)
                        translated_materials.text_inputs.append(translated_text)
                    except Exception as e:
                        logger.warning(f"Failed to translate text '{text[:50]}...': {str(e)}")
                        translated_materials.text_inputs.append(text)  # 使用原文
            
            # 翻译自定义提示
            if materials.custom_prompts:
                for prompt in materials.custom_prompts:
                    try:
                        translated_prompt = self._text_service.translate_text(prompt, target_language)
                        translated_materials.custom_prompts.append(translated_prompt)
                    except Exception as e:
                        logger.warning(f"Failed to translate prompt '{prompt[:50]}...': {str(e)}")
                        translated_materials.custom_prompts.append(prompt)  # 使用原文
            
            return translated_materials
            
        except Exception as e:
            logger.error(f"Failed to translate materials: {str(e)}")
            return materials  # 返回原素材
    
    def _get_text_direction(self, language: TextLanguage) -> str:
        """获取文本方向"""
        # 大多数语言都是从左到右
        # 如果需要支持阿拉伯语或希伯来语，可以在这里添加
        return "ltr"
    
    def _get_language_font(self, language: TextLanguage) -> str:
        """获取语言对应的字体"""
        try:
            fonts = self._language_fonts.get(language, ["Arial"])
            return fonts[0]  # 返回首选字体
        except Exception as e:
            logger.error(f"Failed to get language font: {str(e)}")
            return "Arial"
    
    def _adjust_layout_for_language(self, layout: TemplateLayout, language: TextLanguage) -> TemplateLayout:
        """根据语言调整布局"""
        try:
            # 根据语言特性调整布局
            if language in [TextLanguage.CHINESE, TextLanguage.JAPANESE, TextLanguage.KOREAN]:
                # 亚洲语言需要更多垂直空间
                for element in layout.content_elements:
                    if element.element_type == "text":
                        # 增加行高
                        if 'line_spacing' not in element.style:
                            element.style['line_spacing'] = 8
                        else:
                            element.style['line_spacing'] += 2
            
            elif language == TextLanguage.GERMAN:
                # 德语单词较长，可能需要调整文本区域
                for element in layout.content_elements:
                    if element.element_type == "text":
                        # 德语需要更多水平空间
                        width, height = element.size
                        element.size = (int(width * 1.1), height)
            
            return layout
            
        except Exception as e:
            logger.error(f"Failed to adjust layout for language: {str(e)}")
            return layout
    
    def _render_text_element_multilingual(self, draw: ImageDraw.Draw, element: ContentElement, language: TextLanguage):
        """多语言文本元素渲染"""
        try:
            text = str(element.content)
            x, y = element.position
            width, height = element.size
            style = element.style or {}
            
            # 获取语言特定字体
            font_size = style.get('font_size', 14)
            font_family = self._get_language_font(language)
            
            try:
                # 尝试使用语言特定字体
                font = ImageFont.truetype(f"{font_family}.ttf", font_size)
            except:
                try:
                    # 尝试系统字体
                    font = ImageFont.truetype(font_family, font_size)
                except:
                    # 使用默认字体
                    font = ImageFont.load_default()
            
            # 获取文本颜色
            text_color = style.get('color', '#000000')
            
            # 文本对齐
            align = style.get('align', 'left')
            
            # 根据语言调整文本处理
            if language in [TextLanguage.CHINESE, TextLanguage.JAPANESE, TextLanguage.KOREAN]:
                # 亚洲语言的特殊处理
                lines = self._wrap_text_asian(text, font, width)
            else:
                # 其他语言的标准处理
                lines = self._wrap_text(text, font, width)
            
            # 根据语言调整行高
            base_line_height = font_size + style.get('line_spacing', 5)
            if language in [TextLanguage.CHINESE, TextLanguage.JAPANESE, TextLanguage.KOREAN]:
                line_height = base_line_height + 3  # 亚洲语言需要更大行高
            else:
                line_height = base_line_height
            
            for i, line in enumerate(lines):
                line_y = y + i * line_height
                if line_y + line_height > y + height:
                    break  # 超出区域
                
                # 计算x位置
                if align == 'center':
                    bbox = draw.textbbox((0, 0), line, font=font)
                    text_width = bbox[2] - bbox[0]
                    line_x = x + (width - text_width) // 2
                elif align == 'right':
                    bbox = draw.textbbox((0, 0), line, font=font)
                    text_width = bbox[2] - bbox[0]
                    line_x = x + width - text_width
                else:  # left
                    line_x = x
                
                # 绘制文本
                draw.text((line_x, line_y), line, fill=text_color, font=font)
                
        except Exception as e:
            logger.error(f"Failed to render multilingual text element: {str(e)}")
            # 回退到标准文本渲染
            self._render_text_element(draw, element)
    
    def _wrap_text_asian(self, text: str, font, max_width: int) -> List[str]:
        """亚洲语言文本换行"""
        try:
            lines = []
            current_line = ""
            
            for char in text:
                test_line = current_line + char
                bbox = ImageDraw.Draw(Image.new('RGB', (1, 1))).textbbox((0, 0), test_line, font=font)
                text_width = bbox[2] - bbox[0]
                
                if text_width <= max_width:
                    current_line = test_line
                else:
                    if current_line:
                        lines.append(current_line)
                        current_line = char
                    else:
                        # 单个字符太宽，强制添加
                        lines.append(char)
            
            if current_line:
                lines.append(current_line)
            
            return lines
            
        except Exception as e:
            logger.error(f"Failed to wrap Asian text: {str(e)}")
            return [text]  # 返回原文本
    
    def get_supported_languages(self) -> List[Dict[str, str]]:
        """获取支持的语言列表"""
        try:
            languages = []
            for lang in TextLanguage:
                languages.append({
                    'code': lang.name.lower(),
                    'name': lang.value,
                    'font_family': self._get_language_font(lang),
                    'text_direction': self._get_text_direction(lang)
                })
            
            return languages
            
        except Exception as e:
            logger.error(f"Failed to get supported languages: {str(e)}")
            return []
    
    def set_language_preferences(self, language_config: Dict[TextLanguage, Dict[str, Any]]):
        """设置语言偏好配置"""
        try:
            for language, config in language_config.items():
                if 'fonts' in config:
                    self._language_fonts[language] = config['fonts']
                
                # 可以添加其他语言特定配置
                
            logger.info(f"Updated language preferences for {len(language_config)} languages")
            
        except Exception as e:
            logger.error(f"Failed to set language preferences: {str(e)}")
    
    def get_language_statistics(self) -> Dict[str, Any]:
        """获取语言使用统计"""
        try:
            stats = self._render_stats.get('language_distribution', {})
            total_renders = sum(stats.values()) if stats else 0
            
            # 计算百分比
            language_stats = {}
            for lang, count in stats.items():
                percentage = (count / total_renders * 100) if total_renders > 0 else 0
                language_stats[lang] = {
                    'count': count,
                    'percentage': round(percentage, 1)
                }
            
            return {
                'total_multilingual_renders': total_renders,
                'language_distribution': language_stats,
                'most_used_language': max(stats.items(), key=lambda x: x[1])[0] if stats else None,
                'supported_languages_count': len(TextLanguage)
            }
            
        except Exception as e:
            logger.error(f"Failed to get language statistics: {str(e)}")
            return {}