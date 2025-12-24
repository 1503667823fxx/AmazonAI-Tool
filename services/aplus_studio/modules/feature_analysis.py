"""
功能解析模块生成器

创建技术图表和功能分解展示，突出产品的技术特性和功能细节。
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


class FeatureAnalysisGenerator(BaseModuleGenerator):
    """
    功能解析模块生成器
    
    生成技术图表和功能分解，包括：
    - 技术规格图表
    - 功能分解说明
    - 标注和注释系统
    - 逐步解释布局
    """
    
    def __init__(self):
        super().__init__(ModuleType.FEATURE_ANALYSIS)
        self.layout_templates = {
            "technical_diagram": {
                "main_diagram_area": (0.1, 0.15, 0.6, 0.85),
                "feature_list_area": (0.65, 0.15, 0.95, 0.85),
                "title_area": (0.1, 0.05, 0.9, 0.12)
            },
            "step_by_step": {
                "step_areas": [
                    (0.05, 0.15, 0.48, 0.45),
                    (0.52, 0.15, 0.95, 0.45),
                    (0.05, 0.55, 0.48, 0.85),
                    (0.52, 0.55, 0.95, 0.85)
                ],
                "title_area": (0.1, 0.05, 0.9, 0.12)
            },
            "annotated_breakdown": {
                "product_area": (0.1, 0.2, 0.5, 0.8),
                "annotation_areas": [
                    (0.55, 0.2, 0.9, 0.35),
                    (0.55, 0.4, 0.9, 0.55),
                    (0.55, 0.6, 0.9, 0.75)
                ]
            }
        }
    
    def get_module_info(self) -> Dict[str, Any]:
        """获取模块信息"""
        return {
            "name": "功能解析",
            "description": "创建技术图表和功能分解，详细展示产品的技术特性",
            "category": "professional",
            "recommended_use_cases": [
                "技术产品展示",
                "功能详细说明",
                "复杂产品解析",
                "专业技术文档"
            ],
            "layout_options": list(self.layout_templates.keys()),
            "generation_time_estimate": 60
        }
    
    def get_material_requirements(self) -> MaterialRequirements:
        """获取素材需求"""
        requirements = [
            MaterialRequirement(
                material_type=MaterialType.TEXT,
                priority=MaterialPriority.REQUIRED,
                description="功能特性列表",
                examples=["智能控制", "高效节能", "安全防护"],
                tooltip="列出产品的主要功能特性"
            ),
            MaterialRequirement(
                material_type=MaterialType.TEXT,
                priority=MaterialPriority.RECOMMENDED,
                description="技术规格参数",
                examples=["处理器: ARM Cortex", "内存: 8GB", "接口: USB-C"],
                tooltip="提供详细的技术规格和参数"
            ),
            MaterialRequirement(
                material_type=MaterialType.IMAGE,
                priority=MaterialPriority.RECOMMENDED,
                description="产品技术图片",
                examples=["内部结构图", "技术细节图", "组件图"],
                file_formats=["PNG", "JPG", "WEBP"],
                max_file_size=10 * 1024 * 1024,
                tooltip="展示产品技术细节的高清图片"
            ),
            MaterialRequirement(
                material_type=MaterialType.DOCUMENT,
                priority=MaterialPriority.AI_GENERATED,
                description="技术文档",
                examples=["规格书", "技术手册", "说明书"],
                file_formats=["PDF", "DOC", "DOCX"],
                max_file_size=20 * 1024 * 1024,
                tooltip="包含技术信息的文档资料"
            ),
            MaterialRequirement(
                material_type=MaterialType.CUSTOM_PROMPT,
                priority=MaterialPriority.AI_GENERATED,
                description="技术展示风格",
                examples=["专业技术", "简洁明了", "详细解析"],
                tooltip="AI将选择最适合的技术展示风格"
            )
        ]
        
        return MaterialRequirements(
            module_type=self.module_type,
            requirements=requirements
        )
    
    async def generate_layout(self, materials: MaterialSet, analysis_result: AnalysisResult) -> Dict[str, Any]:
        """生成布局配置"""
        try:
            # 分析技术复杂度
            complexity_level = self._analyze_technical_complexity(materials, analysis_result)
            
            # 选择布局模板
            layout_template = self._select_layout_template(complexity_level, materials)
            
            # 提取功能特性
            features = self._extract_features(materials, analysis_result)
            
            # 提取技术规格
            specifications = self._extract_technical_specs(materials, analysis_result)
            
            # 生成标注系统
            annotations = self._generate_annotations(features, specifications)
            
            layout_config = {
                "template": layout_template,
                "complexity_level": complexity_level,
                "features": features[:6],  # 最多6个功能
                "specifications": specifications[:8],  # 最多8个规格
                "annotations": annotations,
                "diagram_style": self._determine_diagram_style(complexity_level),
                "color_scheme": self._determine_color_scheme(analysis_result),
                "annotation_style": "callouts_and_labels"
            }
            
            self.logger.info(f"Generated layout config with {len(features)} features and {len(specifications)} specs")
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
            
            # 应用布局模板
            template_name = layout_config["template"]
            template = self.layout_templates[template_name]
            
            # 绘制主要技术图表
            canvas = self._draw_technical_diagram(canvas, layout_config, template, materials)
            
            # 添加功能标注
            canvas = self._add_feature_annotations(canvas, layout_config, template)
            
            # 添加技术规格
            canvas = self._add_technical_specifications(canvas, layout_config, template)
            
            # 添加标题和说明
            canvas = self._add_titles_and_explanations(canvas, layout_config, template)
            
            # 应用专业样式
            canvas = self._apply_professional_styling(canvas, layout_config)
            
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
                    "features_count": len(layout_config["features"]),
                    "specs_count": len(layout_config["specifications"]),
                    "complexity_level": layout_config["complexity_level"],
                    "diagram_style": layout_config["diagram_style"]
                }
            )
            
            self.logger.info("Successfully generated feature analysis module")
            return generated_module
            
        except Exception as e:
            raise ModuleGenerationError(
                f"Failed to generate content: {str(e)}",
                self.module_type,
                "CONTENT_GENERATION_FAILED"
            ) from e
    
    def _analyze_technical_complexity(self, materials: MaterialSet, analysis_result: AnalysisResult) -> str:
        """分析技术复杂度"""
        complexity_indicators = 0
        
        # 检查技术规格数量
        if "specifications" in materials.text_inputs:
            spec_count = len(materials.text_inputs["specifications"].split("\n"))
            if spec_count > 10:
                complexity_indicators += 2
            elif spec_count > 5:
                complexity_indicators += 1
        
        # 检查功能数量
        if "features" in materials.text_inputs:
            feature_count = len(materials.text_inputs["features"].split("\n"))
            if feature_count > 8:
                complexity_indicators += 2
            elif feature_count > 4:
                complexity_indicators += 1
        
        # 检查技术文档
        if len(materials.documents) > 0:
            complexity_indicators += 1
        
        if complexity_indicators >= 4:
            return "high"
        elif complexity_indicators >= 2:
            return "medium"
        else:
            return "low"
    
    def _select_layout_template(self, complexity_level: str, materials: MaterialSet) -> str:
        """选择布局模板"""
        if complexity_level == "high":
            return "step_by_step"
        elif len(materials.images) > 0:
            return "annotated_breakdown"
        else:
            return "technical_diagram"
    
    def _extract_features(self, materials: MaterialSet, analysis_result: AnalysisResult) -> List[Dict[str, str]]:
        """提取功能特性"""
        features = []
        
        # 从用户输入提取
        if "features" in materials.text_inputs:
            feature_lines = materials.text_inputs["features"].split("\n")
            for line in feature_lines:
                if line.strip():
                    features.append({
                        "name": line.strip(),
                        "description": f"{line.strip()}功能说明",
                        "importance": "high"
                    })
        
        # 从分析结果提取
        if analysis_result.listing_analysis and analysis_result.listing_analysis.key_selling_points:
            for point in analysis_result.listing_analysis.key_selling_points[:3]:
                features.append({
                    "name": point,
                    "description": f"{point}详细说明",
                    "importance": "medium"
                })
        
        # 默认功能
        if len(features) == 0:
            features = [
                {"name": "智能控制", "description": "先进的智能控制系统", "importance": "high"},
                {"name": "高效性能", "description": "卓越的性能表现", "importance": "high"},
                {"name": "安全可靠", "description": "多重安全保护机制", "importance": "medium"}
            ]
        
        return features[:6]
    
    def _extract_technical_specs(self, materials: MaterialSet, analysis_result: AnalysisResult) -> List[Dict[str, str]]:
        """提取技术规格"""
        specs = []
        
        # 从用户输入提取
        if "specifications" in materials.text_inputs:
            spec_lines = materials.text_inputs["specifications"].split("\n")
            for line in spec_lines:
                if ":" in line:
                    key, value = line.split(":", 1)
                    specs.append({
                        "parameter": key.strip(),
                        "value": value.strip(),
                        "unit": self._extract_unit(value.strip())
                    })
        
        # 从分析结果提取
        if analysis_result.listing_analysis and analysis_result.listing_analysis.technical_specifications:
            for key, value in analysis_result.listing_analysis.technical_specifications.items():
                specs.append({
                    "parameter": key,
                    "value": value,
                    "unit": self._extract_unit(value)
                })
        
        # 默认规格
        if len(specs) == 0:
            specs = [
                {"parameter": "处理器", "value": "高性能芯片", "unit": ""},
                {"parameter": "内存", "value": "大容量存储", "unit": ""},
                {"parameter": "接口", "value": "多种连接方式", "unit": ""}
            ]
        
        return specs[:8]
    
    def _extract_unit(self, value: str) -> str:
        """提取单位"""
        units = ["mm", "cm", "m", "kg", "g", "MHz", "GHz", "MB", "GB", "V", "A", "W"]
        for unit in units:
            if unit in value:
                return unit
        return ""
    
    def _generate_annotations(self, features: List[Dict[str, str]], 
                            specifications: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """生成标注系统"""
        annotations = []
        
        # 为重要功能生成标注
        for i, feature in enumerate(features[:4]):
            if feature["importance"] == "high":
                annotations.append({
                    "type": "feature_callout",
                    "text": feature["name"],
                    "position": f"feature_{i+1}",
                    "style": "highlight"
                })
        
        # 为关键规格生成标注
        for i, spec in enumerate(specifications[:3]):
            annotations.append({
                "type": "spec_label",
                "text": f"{spec['parameter']}: {spec['value']}",
                "position": f"spec_{i+1}",
                "style": "technical"
            })
        
        return annotations
    
    def _determine_diagram_style(self, complexity_level: str) -> str:
        """确定图表风格"""
        style_mapping = {
            "low": "simple_diagram",
            "medium": "detailed_diagram",
            "high": "comprehensive_breakdown"
        }
        return style_mapping.get(complexity_level, "detailed_diagram")
    
    def _determine_color_scheme(self, analysis_result: AnalysisResult) -> Dict[str, str]:
        """确定配色方案"""
        return {
            "primary": "#2C3E50",      # 深蓝色 - 专业
            "secondary": "#3498DB",    # 蓝色 - 技术
            "accent": "#E67E22",       # 橙色 - 强调
            "feature": "#27AE60",      # 绿色 - 功能
            "spec": "#8E44AD",         # 紫色 - 规格
            "text": "#2C3E50",         # 深色文字
            "background": "#FFFFFF"    # 白色背景
        }
    
    def _create_base_canvas(self) -> Image.Image:
        """创建基础画布"""
        from ..models import APLUS_IMAGE_SPECS
        width, height = APLUS_IMAGE_SPECS["dimensions"]
        canvas = Image.new('RGB', (width, height), color='white')
        return canvas
    
    def _draw_technical_diagram(self, canvas: Image.Image, layout_config: Dict[str, Any], 
                               template: Dict[str, Any], materials: MaterialSet) -> Image.Image:
        """绘制技术图表"""
        draw = ImageDraw.Draw(canvas)
        
        if "main_diagram_area" in template:
            area = template["main_diagram_area"]
            x1 = int(area[0] * canvas.width)
            y1 = int(area[1] * canvas.height)
            x2 = int(area[2] * canvas.width)
            y2 = int(area[3] * canvas.height)
            
            # 绘制主要图表区域
            draw.rectangle([x1, y1, x2, y2], 
                         outline=layout_config["color_scheme"]["primary"], 
                         width=3)
            
            # 如果有产品图片，放置在此区域
            if materials.images and len(materials.images) > 0:
                product_image = materials.images[0].content
                if isinstance(product_image, Image.Image):
                    # 调整图片大小适应区域
                    area_width = x2 - x1 - 20
                    area_height = y2 - y1 - 20
                    resized_image = product_image.resize((area_width, area_height), Image.Resampling.LANCZOS)
                    canvas.paste(resized_image, (x1 + 10, y1 + 10))
        
        return canvas
    
    def _add_feature_annotations(self, canvas: Image.Image, layout_config: Dict[str, Any], 
                               template: Dict[str, Any]) -> Image.Image:
        """添加功能标注"""
        draw = ImageDraw.Draw(canvas)
        features = layout_config["features"]
        
        if "feature_list_area" in template:
            area = template["feature_list_area"]
            x1 = int(area[0] * canvas.width)
            y1 = int(area[1] * canvas.height)
            
            # 绘制功能列表标题
            draw.text((x1, y1), "核心功能", 
                     fill=layout_config["color_scheme"]["primary"])
            
            # 绘制功能列表
            for i, feature in enumerate(features):
                y_pos = y1 + 25 + i * 30
                
                # 绘制功能点
                draw.ellipse([x1, y_pos, x1+8, y_pos+8], 
                           fill=layout_config["color_scheme"]["feature"])
                
                # 绘制功能名称
                draw.text((x1 + 15, y_pos-2), feature["name"], 
                         fill=layout_config["color_scheme"]["text"])
                
                # 绘制功能描述（小字）
                draw.text((x1 + 15, y_pos+12), feature["description"][:30] + "...", 
                         fill=layout_config["color_scheme"]["text"])
        
        return canvas
    
    def _add_technical_specifications(self, canvas: Image.Image, layout_config: Dict[str, Any], 
                                    template: Dict[str, Any]) -> Image.Image:
        """添加技术规格"""
        draw = ImageDraw.Draw(canvas)
        specs = layout_config["specifications"]
        
        # 在功能列表下方添加规格信息
        if "feature_list_area" in template:
            area = template["feature_list_area"]
            x1 = int(area[0] * canvas.width)
            y1 = int(area[1] * canvas.height) + 200  # 在功能列表下方
            
            # 绘制规格标题
            draw.text((x1, y1), "技术规格", 
                     fill=layout_config["color_scheme"]["primary"])
            
            # 绘制规格列表
            for i, spec in enumerate(specs[:4]):  # 最多显示4个规格
                y_pos = y1 + 25 + i * 20
                spec_text = f"{spec['parameter']}: {spec['value']}"
                draw.text((x1, y_pos), spec_text, 
                         fill=layout_config["color_scheme"]["spec"])
        
        return canvas
    
    def _add_titles_and_explanations(self, canvas: Image.Image, layout_config: Dict[str, Any], 
                                   template: Dict[str, Any]) -> Image.Image:
        """添加标题和说明"""
        draw = ImageDraw.Draw(canvas)
        
        if "title_area" in template:
            area = template["title_area"]
            x1 = int(area[0] * canvas.width)
            y1 = int(area[1] * canvas.height)
            
            # 添加主标题
            draw.text((x1, y1), "功能解析", 
                     fill=layout_config["color_scheme"]["primary"])
        
        return canvas
    
    def _apply_professional_styling(self, canvas: Image.Image, layout_config: Dict[str, Any]) -> Image.Image:
        """应用专业样式"""
        # 添加专业的视觉元素，如网格线、边框等
        return canvas
    
    def _canvas_to_bytes(self, canvas: Image.Image) -> bytes:
        """将画布转换为字节数据"""
        buffer = io.BytesIO()
        canvas.save(buffer, format='PNG', optimize=True)
        return buffer.getvalue()
    
    def _generate_prompt_description(self, layout_config: Dict[str, Any]) -> str:
        """生成提示词描述"""
        return f"Feature analysis module with {layout_config['template']} layout, " \
               f"showing {len(layout_config['features'])} features and " \
               f"{len(layout_config['specifications'])} specifications in " \
               f"{layout_config['complexity_level']} complexity level"