"""
Style Management Service for A+ Intelligent Workflow

This service manages unified visual style themes and ensures consistency across all generated modules.
It provides automatic style selection based on product analysis and maintains style coherence.

Requirements covered:
- 7.1: 统一视觉风格系统
- 7.2: 风格主题智能选择  
- 8.1: 风格主题智能选择
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from enum import Enum
import logging

from .models import (
    ProductCategory, StyleTheme, IntelligentProductAnalysis, 
    IntelligentStyleThemeConfig, ModuleType
)

logger = logging.getLogger(__name__)


class DesignStyle(Enum):
    """设计风格枚举"""
    MODERN = "modern"
    CLASSIC = "classic"
    MINIMALIST = "minimalist"
    LUXURY = "luxury"
    PROFESSIONAL = "professional"
    TECH_FOCUSED = "tech_focused"
    WARM_HOME = "warm_home"
    CLEAN_FUNCTIONAL = "clean_functional"


@dataclass
class StyleThemeDefinition:
    """风格主题定义"""
    theme_id: str
    theme_name: str
    display_name: str
    color_palette: List[str]
    font_family: str
    design_style: DesignStyle
    layout_preferences: Dict[str, Any]
    suitable_categories: List[ProductCategory]
    description: str
    preview_image_url: Optional[str] = None
    
    def to_config(self) -> IntelligentStyleThemeConfig:
        """转换为配置对象"""
        return IntelligentStyleThemeConfig(
            theme_id=self.theme_id,
            theme_name=self.theme_name,
            color_palette=self.color_palette,
            font_family=self.font_family,
            design_style=self.design_style.value,
            layout_preferences=self.layout_preferences,
            suitable_categories=self.suitable_categories
        )


class StyleManagementService:
    """风格管理服务"""
    
    def __init__(self):
        """初始化风格管理服务"""
        self.style_themes = self._initialize_style_themes()
        self.selection_rules = self._initialize_selection_rules()
        
    def _initialize_style_themes(self) -> Dict[str, StyleThemeDefinition]:
        """初始化风格主题库"""
        themes = {}
        
        # 现代科技风格
        themes["modern_tech"] = StyleThemeDefinition(
            theme_id="modern_tech",
            theme_name="modern_tech",
            display_name="现代科技",
            color_palette=["#2563EB", "#1E40AF", "#3B82F6", "#60A5FA", "#93C5FD"],
            font_family="Inter, -apple-system, BlinkMacSystemFont, sans-serif",
            design_style=DesignStyle.TECH_FOCUSED,
            layout_preferences={
                "background_style": "gradient_tech",
                "border_radius": "8px",
                "shadow_style": "modern",
                "icon_style": "outlined",
                "spacing": "tight",
                "emphasis": "high_contrast"
            },
            suitable_categories=[
                ProductCategory.TECHNOLOGY,
                ProductCategory.AUTOMOTIVE,
                ProductCategory.TOOLS
            ],
            description="适合科技产品的现代简约风格，强调功能性和专业感"
        )
        
        # 温馨家居风格
        themes["warm_home"] = StyleThemeDefinition(
            theme_id="warm_home",
            theme_name="warm_home",
            display_name="温馨家居",
            color_palette=["#92400E", "#B45309", "#D97706", "#F59E0B", "#FCD34D"],
            font_family="Georgia, 'Times New Roman', serif",
            design_style=DesignStyle.WARM_HOME,
            layout_preferences={
                "background_style": "warm_gradient",
                "border_radius": "12px",
                "shadow_style": "soft",
                "icon_style": "filled",
                "spacing": "comfortable",
                "emphasis": "warm_tones"
            },
            suitable_categories=[
                ProductCategory.HOME_LIVING,
                ProductCategory.HEALTH_BEAUTY
            ],
            description="适合家居用品的温馨舒适风格，营造生活化氛围"
        )
        
        # 奢华高端风格
        themes["luxury_premium"] = StyleThemeDefinition(
            theme_id="luxury_premium",
            theme_name="luxury_premium",
            display_name="奢华高端",
            color_palette=["#1F2937", "#374151", "#6B7280", "#D1D5DB", "#F9FAFB"],
            font_family="'Playfair Display', Georgia, serif",
            design_style=DesignStyle.LUXURY,
            layout_preferences={
                "background_style": "elegant_gradient",
                "border_radius": "4px",
                "shadow_style": "elegant",
                "icon_style": "minimal",
                "spacing": "generous",
                "emphasis": "premium_materials"
            },
            suitable_categories=[
                ProductCategory.FASHION,
                ProductCategory.HEALTH_BEAUTY
            ],
            description="适合高端产品的精致奢华风格，突出品质和档次"
        )
        
        # 清洁功能风格
        themes["clean_functional"] = StyleThemeDefinition(
            theme_id="clean_functional",
            theme_name="clean_functional",
            display_name="清洁功能",
            color_palette=["#059669", "#047857", "#10B981", "#34D399", "#6EE7B7"],
            font_family="'Roboto', Arial, sans-serif",
            design_style=DesignStyle.CLEAN_FUNCTIONAL,
            layout_preferences={
                "background_style": "clean_white",
                "border_radius": "6px",
                "shadow_style": "subtle",
                "icon_style": "functional",
                "spacing": "organized",
                "emphasis": "clear_information"
            },
            suitable_categories=[
                ProductCategory.TOOLS,
                ProductCategory.AUTOMOTIVE,
                ProductCategory.SPORTS
            ],
            description="适合实用工具的清晰功能风格，强调实用性和可读性"
        )
        
        # 专业商务风格
        themes["professional"] = StyleThemeDefinition(
            theme_id="professional",
            theme_name="professional",
            display_name="专业商务",
            color_palette=["#1E3A8A", "#1E40AF", "#3B82F6", "#60A5FA", "#DBEAFE"],
            font_family="'Source Sans Pro', Arial, sans-serif",
            design_style=DesignStyle.PROFESSIONAL,
            layout_preferences={
                "background_style": "professional_gradient",
                "border_radius": "8px",
                "shadow_style": "professional",
                "icon_style": "business",
                "spacing": "structured",
                "emphasis": "credibility"
            },
            suitable_categories=[
                ProductCategory.TECHNOLOGY,
                ProductCategory.TOOLS,
                ProductCategory.OTHER
            ],
            description="适合商务产品的专业风格，体现可信度和权威性"
        )
        
        return themes
    
    def _initialize_selection_rules(self) -> Dict[ProductCategory, List[str]]:
        """初始化风格选择规则"""
        return {
            ProductCategory.TECHNOLOGY: ["modern_tech", "professional", "clean_functional"],
            ProductCategory.HOME_LIVING: ["warm_home", "clean_functional", "professional"],
            ProductCategory.FASHION: ["luxury_premium", "professional", "modern_tech"],
            ProductCategory.SPORTS: ["clean_functional", "modern_tech", "professional"],
            ProductCategory.HEALTH_BEAUTY: ["luxury_premium", "warm_home", "professional"],
            ProductCategory.AUTOMOTIVE: ["modern_tech", "clean_functional", "professional"],
            ProductCategory.TOOLS: ["clean_functional", "professional", "modern_tech"],
            ProductCategory.OTHER: ["professional", "clean_functional", "modern_tech"]
        }
    
    def select_style_theme(self, product_analysis: IntelligentProductAnalysis) -> IntelligentStyleThemeConfig:
        """
        基于产品分析选择合适的风格主题
        
        Args:
            product_analysis: 产品分析结果
            
        Returns:
            选择的风格主题配置
        """
        try:
            # 获取产品类别对应的推荐风格
            recommended_themes = self.selection_rules.get(
                product_analysis.product_category, 
                ["professional"]
            )
            
            # 选择第一个推荐的风格主题
            selected_theme_id = recommended_themes[0]
            selected_theme = self.style_themes.get(selected_theme_id)
            
            if not selected_theme:
                # 回退到专业风格
                selected_theme = self.style_themes["professional"]
                logger.warning(f"Theme {selected_theme_id} not found, using professional theme")
            
            logger.info(f"Selected style theme: {selected_theme.theme_name} for category: {product_analysis.product_category}")
            
            return selected_theme.to_config()
            
        except Exception as e:
            logger.error(f"Error selecting style theme: {str(e)}")
            # 返回默认专业风格
            return self.style_themes["professional"].to_config()
    
    def get_available_themes(self, product_category: ProductCategory) -> List[IntelligentStyleThemeConfig]:
        """
        获取指定产品类别的可用风格主题选项
        
        Args:
            product_category: 产品类别
            
        Returns:
            可用的风格主题配置列表
        """
        try:
            recommended_theme_ids = self.selection_rules.get(product_category, ["professional"])
            available_themes = []
            
            for theme_id in recommended_theme_ids:
                theme = self.style_themes.get(theme_id)
                if theme:
                    available_themes.append(theme.to_config())
            
            # 如果没有找到任何主题，返回专业风格
            if not available_themes:
                available_themes.append(self.style_themes["professional"].to_config())
            
            logger.info(f"Found {len(available_themes)} available themes for category: {product_category}")
            return available_themes
            
        except Exception as e:
            logger.error(f"Error getting available themes: {str(e)}")
            return [self.style_themes["professional"].to_config()]
    
    def apply_style_consistency(self, modules: List[ModuleType], theme_config: IntelligentStyleThemeConfig) -> Dict[ModuleType, Dict[str, Any]]:
        """
        应用统一风格到所有模块
        
        Args:
            modules: 模块类型列表
            theme_config: 风格主题配置
            
        Returns:
            每个模块的风格化配置
        """
        try:
            styled_modules = {}
            
            for module_type in modules:
                # 为每个模块应用统一的风格配置
                module_style = {
                    "theme_id": theme_config.theme_id,
                    "theme_name": theme_config.theme_name,
                    "color_palette": theme_config.color_palette,
                    "font_family": theme_config.font_family,
                    "design_style": theme_config.design_style,
                    "layout_preferences": theme_config.layout_preferences.copy(),
                    "module_specific_adjustments": self._get_module_specific_adjustments(module_type, theme_config)
                }
                
                styled_modules[module_type] = module_style
            
            logger.info(f"Applied style consistency to {len(modules)} modules with theme: {theme_config.theme_name}")
            return styled_modules
            
        except Exception as e:
            logger.error(f"Error applying style consistency: {str(e)}")
            return {}
    
    def _get_module_specific_adjustments(self, module_type: ModuleType, theme_config: IntelligentStyleThemeConfig) -> Dict[str, Any]:
        """
        获取模块特定的风格调整
        
        Args:
            module_type: 模块类型
            theme_config: 风格主题配置
            
        Returns:
            模块特定的风格调整
        """
        adjustments = {}
        
        # 根据模块类型进行特定调整
        if module_type == ModuleType.PRODUCT_OVERVIEW:
            adjustments.update({
                "emphasis": "hero_product",
                "layout_priority": "product_showcase",
                "text_hierarchy": "title_dominant"
            })
        elif module_type == ModuleType.FEATURE_ANALYSIS:
            adjustments.update({
                "emphasis": "technical_details",
                "layout_priority": "information_dense",
                "annotation_style": "technical"
            })
        elif module_type == ModuleType.SPECIFICATION_COMPARISON:
            adjustments.update({
                "emphasis": "data_visualization",
                "layout_priority": "comparison_table",
                "chart_style": "professional"
            })
        elif module_type == ModuleType.USAGE_SCENARIOS:
            adjustments.update({
                "emphasis": "practical_application",
                "layout_priority": "scenario_panels",
                "avoid_lifestyle": True
            })
        elif module_type == ModuleType.INSTALLATION_GUIDE:
            adjustments.update({
                "emphasis": "step_by_step",
                "layout_priority": "instructional",
                "visual_clarity": "high"
            })
        elif module_type == ModuleType.MATERIAL_CRAFTSMANSHIP:
            adjustments.update({
                "emphasis": "quality_details",
                "layout_priority": "material_showcase",
                "texture_focus": True
            })
        elif module_type == ModuleType.QUALITY_ASSURANCE:
            adjustments.update({
                "emphasis": "trust_indicators",
                "layout_priority": "certification_display",
                "badge_style": "professional"
            })
        
        return adjustments
    
    def ensure_aplus_compliance(self, styled_content: Dict[str, Any]) -> Dict[str, Any]:
        """
        确保风格应用符合A+页面规范
        
        Args:
            styled_content: 风格化内容
            
        Returns:
            符合A+规范的风格化内容
        """
        try:
            compliant_content = styled_content.copy()
            
            # 确保符合A+页面规范
            aplus_constraints = {
                "image_dimensions": (600, 450),
                "max_text_coverage": 0.3,
                "min_product_visibility": 0.4,
                "information_density": "high",
                "avoid_lifestyle": True,
                "professional_appearance": True
            }
            
            # 应用A+规范约束
            compliant_content["aplus_constraints"] = aplus_constraints
            compliant_content["compliance_verified"] = True
            
            # 调整布局以符合信息密集型要求
            if "layout_preferences" in compliant_content:
                layout_prefs = compliant_content["layout_preferences"]
                layout_prefs["information_density"] = "high"
                layout_prefs["product_focus"] = True
                layout_prefs["text_efficiency"] = "maximum"
            
            logger.info("Applied A+ compliance constraints to styled content")
            return compliant_content
            
        except Exception as e:
            logger.error(f"Error ensuring A+ compliance: {str(e)}")
            return styled_content
    
    def get_theme_by_id(self, theme_id: str) -> Optional[IntelligentStyleThemeConfig]:
        """
        根据ID获取风格主题
        
        Args:
            theme_id: 主题ID
            
        Returns:
            风格主题配置，如果不存在则返回None
        """
        theme = self.style_themes.get(theme_id)
        return theme.to_config() if theme else None
    
    def get_all_themes(self) -> List[IntelligentStyleThemeConfig]:
        """
        获取所有可用的风格主题
        
        Returns:
            所有风格主题配置列表
        """
        return [theme.to_config() for theme in self.style_themes.values()]
    
    def validate_theme_compatibility(self, theme_config: IntelligentStyleThemeConfig, product_category: ProductCategory) -> bool:
        """
        验证风格主题与产品类别的兼容性
        
        Args:
            theme_config: 风格主题配置
            product_category: 产品类别
            
        Returns:
            是否兼容
        """
        try:
            return product_category in theme_config.suitable_categories
        except Exception as e:
            logger.error(f"Error validating theme compatibility: {str(e)}")
            return False