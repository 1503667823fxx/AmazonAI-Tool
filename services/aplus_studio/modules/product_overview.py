"""
产品概览模块生成器

创建英雄式产品展示，突出关键特性和竞争优势。
"""

import logging
from typing import Dict, Any, List, Optional
from PIL import Image, ImageDraw, ImageFont
import io

from .base_module import BaseModuleGenerator, ModuleGenerationError
from ..models import (
    ModuleType, MaterialSet, MaterialRequirements, MaterialRequirement,
    MaterialType, MaterialPriority, GeneratedModule, ComplianceStatus,
    ValidationStatus, AnalysisResult
)

logger = logging.getLogger(__name__)


class ProductOverviewGenerator(BaseModuleGenerator):
    """
    产品概览模块生成器
    
    生成英雄式产品展示，包括：
    - 大型产品图像展示
    - 关键功能标注
    - 规格亮点
    - 竞争优势强调
    """
    
    def __init__(self):
        super().__init__(ModuleType.PRODUCT_OVERVIEW)
        self.layout_templates = {
            "hero_showcase": {
                "main_product_area": (0.1, 0.1, 0.6, 0.9),  # 左侧60%用于产品图
                "features_area": (0.65, 0.1, 0.9, 0.5),     # 右上角功能区
                "specs_area": (0.65, 0.55, 0.9, 0.9)        # 右下角规格区
            },
            "centered_focus": {
                "main_product_area": (0.2, 0.2, 0.8, 0.8),  # 中央产品展示
                "features_overlay": (0.05, 0.05, 0.95, 0.15), # 顶部功能条
                "specs_overlay": (0.05, 0.85, 0.95, 0.95)     # 底部规格条
            }
        }
    
    def get_module_info(self) -> Dict[str, Any]:
        """获取模块信息"""
        return {
            "name": "产品概览",
            "description": "创建英雄式产品展示，突出产品的核心特性和竞争优势",
            "category": "professional",
            "recommended_use_cases": [
                "新品发布",
                "产品主页展示", 
                "核心卖点突出",
                "品牌形象建立"
            ],
            "layout_options": list(self.layout_templates.keys()),
            "generation_time_estimate": 45
        }
    
    def get_material_requirements(self) -> MaterialRequirements:
        """获取素材需求"""
        requirements = [
            MaterialRequirement(
                material_type=MaterialType.IMAGE,
                priority=MaterialPriority.REQUIRED,
                description="产品主图（高质量，多角度）",
                examples=["正面图", "侧面图", "细节图"],
                file_formats=["PNG", "JPG", "WEBP"],
                max_file_size=10 * 1024 * 1024,  # 10MB
                tooltip="至少需要1张高质量产品图片，建议提供2-3张不同角度"
            ),
            MaterialRequirement(
                material_type=MaterialType.TEXT,
                priority=MaterialPriority.REQUIRED,
                description="产品功能列表",
                examples=["核心功能1", "核心功能2", "核心功能3"],
                tooltip="列出产品的3-5个核心功能特性"
            ),
            MaterialRequirement(
                material_type=MaterialType.TEXT,
                priority=MaterialPriority.RECOMMENDED,
                description="产品规格信息",
                examples=["尺寸: 30x20x10cm", "重量: 2.5kg", "材质: 不锈钢"],
                tooltip="提供关键的产品规格参数"
            ),
            MaterialRequirement(
                material_type=MaterialType.TEXT,
                priority=MaterialPriority.RECOMMENDED,
                description="竞争优势描述",
                examples=["行业领先技术", "获奖设计", "专利保护"],
                tooltip="突出产品相比竞品的独特优势"
            ),
            MaterialRequirement(
                material_type=MaterialType.CUSTOM_PROMPT,
                priority=MaterialPriority.AI_GENERATED,
                description="布局风格偏好",
                examples=["现代简约", "专业商务", "温馨家居"],
                tooltip="AI将根据产品特性自动选择合适的展示风格"
            )
        ]
        
        return MaterialRequirements(
            module_type=self.module_type,
            requirements=requirements
        )
    
    async def generate_layout(self, materials: MaterialSet, analysis_result: AnalysisResult) -> Dict[str, Any]:
        """生成布局配置"""
        try:
            # 分析产品类型和风格
            product_style = self._analyze_product_style(analysis_result)
            
            # 选择合适的布局模板
            layout_template = self._select_layout_template(product_style, materials)
            
            # 提取关键功能
            key_features = self._extract_key_features(materials, analysis_result)
            
            # 提取规格信息
            specifications = self._extract_specifications(materials, analysis_result)
            
            # 确定竞争优势
            competitive_advantages = self._identify_competitive_advantages(materials, analysis_result)
            
            layout_config = {
                "template": layout_template,
                "product_style": product_style,
                "key_features": key_features[:5],  # 最多5个功能
                "specifications": specifications[:6],  # 最多6个规格
                "competitive_advantages": competitive_advantages[:3],  # 最多3个优势
                "color_scheme": self._determine_color_scheme(analysis_result),
                "typography": self._select_typography(product_style),
                "emphasis_level": "high"  # 产品概览需要高强调
            }
            
            self.logger.info(f"Generated layout config with {len(key_features)} features and {len(specifications)} specs")
            return layout_config
            
        except Exception as e:
            raise ModuleGenerationError(
                f"Failed to generate layout: {str(e)}",
                self.module_type,
                "LAYOUT_GENERATION_FAILED"
            ) from e
    
    async def generate_content(self, 
                             materials: MaterialSet, 
                             layout_config: Dict[str, Any],
                             analysis_result: AnalysisResult) -> GeneratedModule:
        """生成模块内容"""
        try:
            # 创建基础画布
            canvas = self._create_base_canvas()
            
            # 获取主要产品图像
            main_product_image = self._get_main_product_image(materials)
            
            # 应用布局模板
            template_name = layout_config["template"]
            template = self.layout_templates[template_name]
            
            # 放置产品图像
            canvas = self._place_product_image(canvas, main_product_image, template, layout_config)
            
            # 添加功能标注
            canvas = self._add_feature_annotations(canvas, layout_config, template)
            
            # 添加规格信息
            canvas = self._add_specifications(canvas, layout_config, template)
            
            # 添加竞争优势
            canvas = self._add_competitive_advantages(canvas, layout_config, template)
            
            # 应用品牌一致性
            canvas = self._apply_brand_consistency(canvas, analysis_result)
            
            # 转换为字节数据
            image_data = self._canvas_to_bytes(canvas)
            
            # 生成提示词记录
            prompt_used = self._generate_prompt_description(layout_config)
            
            # 创建生成结果
            generated_module = GeneratedModule(
                module_type=self.module_type,
                image_data=image_data,
                image_path=None,
                materials_used=materials,
                prompt_used=prompt_used,
                metadata={
                    "layout_template": template_name,
                    "features_count": len(layout_config["key_features"]),
                    "specs_count": len(layout_config["specifications"]),
                    "advantages_count": len(layout_config["competitive_advantages"]),
                    "product_style": layout_config["product_style"],
                    "color_scheme": layout_config["color_scheme"]
                }
            )
            
            self.logger.info("Successfully generated product overview module")
            return generated_module
            
        except Exception as e:
            raise ModuleGenerationError(
                f"Failed to generate content: {str(e)}",
                self.module_type,
                "CONTENT_GENERATION_FAILED"
            ) from e
    
    def _analyze_product_style(self, analysis_result: AnalysisResult) -> str:
        """分析产品风格"""
        if analysis_result.image_analysis and analysis_result.image_analysis.design_style:
            design_style = analysis_result.image_analysis.design_style.lower()
            
            if any(word in design_style for word in ["modern", "contemporary", "sleek"]):
                return "modern"
            elif any(word in design_style for word in ["professional", "business", "corporate"]):
                return "professional"
            elif any(word in design_style for word in ["luxury", "premium", "elegant"]):
                return "luxury"
            elif any(word in design_style for word in ["casual", "home", "friendly"]):
                return "casual"
        
        # 默认风格
        return "professional"
    
    def _select_layout_template(self, product_style: str, materials: MaterialSet) -> str:
        """选择布局模板"""
        # 根据产品风格和可用素材选择模板
        if len(materials.images) >= 2 and product_style in ["luxury", "professional"]:
            return "hero_showcase"
        else:
            return "centered_focus"
    
    def _extract_key_features(self, materials: MaterialSet, analysis_result: AnalysisResult) -> List[str]:
        """提取关键功能"""
        features = []
        
        # 从用户文本输入中提取
        if "features" in materials.text_inputs:
            user_features = materials.text_inputs["features"].split("\n")
            features.extend([f.strip() for f in user_features if f.strip()])
        
        # 从分析结果中提取
        if analysis_result.listing_analysis and analysis_result.listing_analysis.key_selling_points:
            features.extend(analysis_result.listing_analysis.key_selling_points[:3])
        
        # 如果没有足够的功能，生成默认功能
        if len(features) < 3:
            default_features = [
                "高品质材料制造",
                "人性化设计",
                "可靠耐用"
            ]
            features.extend(default_features[:3-len(features)])
        
        return features[:5]  # 最多返回5个功能
    
    def _extract_specifications(self, materials: MaterialSet, analysis_result: AnalysisResult) -> List[Dict[str, str]]:
        """提取规格信息"""
        specs = []
        
        # 从用户文本输入中提取
        if "specifications" in materials.text_inputs:
            spec_lines = materials.text_inputs["specifications"].split("\n")
            for line in spec_lines:
                if ":" in line:
                    key, value = line.split(":", 1)
                    specs.append({"key": key.strip(), "value": value.strip()})
        
        # 从分析结果中提取
        if analysis_result.listing_analysis and analysis_result.listing_analysis.technical_specifications:
            for key, value in analysis_result.listing_analysis.technical_specifications.items():
                specs.append({"key": key, "value": value})
        
        # 如果没有规格信息，生成默认规格
        if len(specs) == 0:
            specs = [
                {"key": "品质", "value": "优质材料"},
                {"key": "设计", "value": "专业设计"},
                {"key": "保修", "value": "质量保证"}
            ]
        
        return specs[:6]  # 最多返回6个规格
    
    def _identify_competitive_advantages(self, materials: MaterialSet, analysis_result: AnalysisResult) -> List[str]:
        """识别竞争优势"""
        advantages = []
        
        # 从用户输入中提取
        if "advantages" in materials.text_inputs:
            user_advantages = materials.text_inputs["advantages"].split("\n")
            advantages.extend([a.strip() for a in user_advantages if a.strip()])
        
        # 从分析结果中提取
        if analysis_result.listing_analysis and analysis_result.listing_analysis.competitive_advantages:
            advantages.extend(analysis_result.listing_analysis.competitive_advantages)
        
        # 默认优势
        if len(advantages) == 0:
            advantages = [
                "行业领先品质",
                "专业设计团队",
                "优质客户服务"
            ]
        
        return advantages[:3]  # 最多返回3个优势
    
    def _determine_color_scheme(self, analysis_result: AnalysisResult) -> Dict[str, str]:
        """确定配色方案"""
        # 基于图像分析结果确定配色
        if analysis_result.image_analysis and analysis_result.image_analysis.dominant_colors:
            primary_color = analysis_result.image_analysis.dominant_colors[0]
        else:
            primary_color = "#2C3E50"  # 默认深蓝色
        
        return {
            "primary": primary_color,
            "secondary": "#ECF0F1",  # 浅灰色
            "accent": "#E74C3C",     # 强调红色
            "text": "#2C3E50",       # 深色文字
            "background": "#FFFFFF"   # 白色背景
        }
    
    def _select_typography(self, product_style: str) -> Dict[str, Any]:
        """选择字体样式"""
        typography_styles = {
            "modern": {
                "title_size": 24,
                "subtitle_size": 16,
                "body_size": 12,
                "font_weight": "bold"
            },
            "professional": {
                "title_size": 22,
                "subtitle_size": 14,
                "body_size": 11,
                "font_weight": "medium"
            },
            "luxury": {
                "title_size": 26,
                "subtitle_size": 18,
                "body_size": 13,
                "font_weight": "light"
            },
            "casual": {
                "title_size": 20,
                "subtitle_size": 15,
                "body_size": 12,
                "font_weight": "regular"
            }
        }
        
        return typography_styles.get(product_style, typography_styles["professional"])
    
    def _create_base_canvas(self) -> Image.Image:
        """创建基础画布"""
        from ..models import APLUS_IMAGE_SPECS
        width, height = APLUS_IMAGE_SPECS["dimensions"]
        canvas = Image.new('RGB', (width, height), color='white')
        return canvas
    
    def _get_main_product_image(self, materials: MaterialSet) -> Optional[Image.Image]:
        """获取主要产品图像"""
        if materials.images and len(materials.images) > 0:
            first_image = materials.images[0]
            if isinstance(first_image.content, Image.Image):
                return first_image.content
        return None
    
    def _place_product_image(self, canvas: Image.Image, product_image: Optional[Image.Image], 
                           template: Dict[str, Any], layout_config: Dict[str, Any]) -> Image.Image:
        """放置产品图像"""
        if not product_image:
            return canvas
        
        # 获取产品图像区域
        if "main_product_area" in template:
            area = template["main_product_area"]
            x1 = int(area[0] * canvas.width)
            y1 = int(area[1] * canvas.height)
            x2 = int(area[2] * canvas.width)
            y2 = int(area[3] * canvas.height)
            
            # 调整产品图像大小
            area_width = x2 - x1
            area_height = y2 - y1
            resized_image = product_image.resize((area_width, area_height), Image.Resampling.LANCZOS)
            
            # 粘贴到画布
            canvas.paste(resized_image, (x1, y1))
        
        return canvas
    
    def _add_feature_annotations(self, canvas: Image.Image, layout_config: Dict[str, Any], 
                               template: Dict[str, Any]) -> Image.Image:
        """添加功能标注"""
        draw = ImageDraw.Draw(canvas)
        features = layout_config["key_features"]
        
        if "features_area" in template and features:
            area = template["features_area"]
            x1 = int(area[0] * canvas.width)
            y1 = int(area[1] * canvas.height)
            x2 = int(area[2] * canvas.width)
            y2 = int(area[3] * canvas.height)
            
            # 计算每个功能的位置
            feature_height = (y2 - y1) // len(features)
            
            for i, feature in enumerate(features):
                y_pos = y1 + i * feature_height
                
                # 绘制功能点
                draw.ellipse([x1, y_pos, x1+10, y_pos+10], 
                           fill=layout_config["color_scheme"]["accent"])
                
                # 绘制功能文字
                draw.text((x1 + 15, y_pos), feature, 
                         fill=layout_config["color_scheme"]["text"])
        
        return canvas
    
    def _add_specifications(self, canvas: Image.Image, layout_config: Dict[str, Any], 
                          template: Dict[str, Any]) -> Image.Image:
        """添加规格信息"""
        draw = ImageDraw.Draw(canvas)
        specs = layout_config["specifications"]
        
        if "specs_area" in template and specs:
            area = template["specs_area"]
            x1 = int(area[0] * canvas.width)
            y1 = int(area[1] * canvas.height)
            
            # 绘制规格标题
            draw.text((x1, y1), "产品规格", 
                     fill=layout_config["color_scheme"]["text"])
            
            # 绘制规格列表
            for i, spec in enumerate(specs[:4]):  # 最多显示4个规格
                y_pos = y1 + 20 + i * 15
                spec_text = f"{spec['key']}: {spec['value']}"
                draw.text((x1, y_pos), spec_text, 
                         fill=layout_config["color_scheme"]["text"])
        
        return canvas
    
    def _add_competitive_advantages(self, canvas: Image.Image, layout_config: Dict[str, Any], 
                                  template: Dict[str, Any]) -> Image.Image:
        """添加竞争优势"""
        # 在适当位置添加优势标识
        # 这里可以添加徽章、星标等视觉元素
        return canvas
    
    def _apply_brand_consistency(self, canvas: Image.Image, analysis_result: AnalysisResult) -> Image.Image:
        """应用品牌一致性"""
        # 应用品牌色彩和风格
        return canvas
    
    def _canvas_to_bytes(self, canvas: Image.Image) -> bytes:
        """将画布转换为字节数据"""
        buffer = io.BytesIO()
        canvas.save(buffer, format='PNG', optimize=True)
        return buffer.getvalue()
    
    def _generate_prompt_description(self, layout_config: Dict[str, Any]) -> str:
        """生成提示词描述"""
        return f"Product overview module with {layout_config['template']} layout, " \
               f"featuring {len(layout_config['key_features'])} key features and " \
               f"{len(layout_config['specifications'])} specifications in " \
               f"{layout_config['product_style']} style"