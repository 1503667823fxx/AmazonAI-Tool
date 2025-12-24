"""
尺寸兼容模块生成器

创建尺寸精度和兼容性展示，突出产品的尺寸规格和兼容性信息。
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


class SizeCompatibilityGenerator(BaseModuleGenerator):
    """
    尺寸兼容模块生成器
    
    生成尺寸精度和兼容性展示，包括：
    - 尺寸图表展示
    - 测量精度验证
    - 兼容性检查逻辑
    - 比例指示器系统
    """
    
    def __init__(self):
        super().__init__(ModuleType.SIZE_COMPATIBILITY)
        self.layout_templates = {
            "dimension_charts": {
                "main_diagram_area": (0.1, 0.2, 0.6, 0.8),
                "dimensions_list_area": (0.65, 0.2, 0.9, 0.6),
                "compatibility_area": (0.65, 0.65, 0.9, 0.8),
                "title_area": (0.1, 0.05, 0.9, 0.15)
            },
            "scale_comparison": {
                "scale_area": (0.1, 0.3, 0.9, 0.7),
                "measurements_area": (0.1, 0.75, 0.9, 0.9),
                "title_area": (0.1, 0.05, 0.9, 0.25)
            }
        }
    
    def get_module_info(self) -> Dict[str, Any]:
        """获取模块信息"""
        return {
            "name": "尺寸兼容",
            "description": "展示产品的精确尺寸信息和兼容性标准",
            "category": "professional",
            "recommended_use_cases": [
                "尺寸规格展示",
                "兼容性说明",
                "安装空间要求",
                "标准符合性"
            ],
            "layout_options": list(self.layout_templates.keys()),
            "generation_time_estimate": 50
        }
    
    def get_material_requirements(self) -> MaterialRequirements:
        """获取素材需求"""
        requirements = [
            MaterialRequirement(
                material_type=MaterialType.TEXT,
                priority=MaterialPriority.REQUIRED,
                description="产品尺寸数据",
                examples=["长: 30cm", "宽: 20cm", "高: 10cm", "重量: 2.5kg"],
                tooltip="提供详细的产品尺寸和重量信息"
            ),
            MaterialRequirement(
                material_type=MaterialType.TEXT,
                priority=MaterialPriority.RECOMMENDED,
                description="兼容性标准",
                examples=["符合国际标准", "适配标准接口", "通用尺寸规格"],
                tooltip="说明产品符合的标准和兼容性信息"
            ),
            MaterialRequirement(
                material_type=MaterialType.IMAGE,
                priority=MaterialPriority.RECOMMENDED,
                description="技术图纸或尺寸图",
                examples=["产品图纸", "尺寸标注图", "安装示意图"],
                file_formats=["PNG", "JPG", "WEBP"],
                max_file_size=10 * 1024 * 1024,
                tooltip="展示产品尺寸的技术图纸或标注图"
            ),
            MaterialRequirement(
                material_type=MaterialType.CUSTOM_PROMPT,
                priority=MaterialPriority.AI_GENERATED,
                description="尺寸展示风格",
                examples=["技术图表", "比例展示", "兼容性对比"],
                tooltip="AI将选择最适合的尺寸展示方式"
            )
        ]
        
        return MaterialRequirements(
            module_type=self.module_type,
            requirements=requirements
        )
    
    async def generate_layout(self, materials: MaterialSet, analysis_result: AnalysisResult) -> Dict[str, Any]:
        """生成布局配置"""
        try:
            # 提取尺寸数据
            dimensions = self._extract_dimensions(materials, analysis_result)
            
            # 提取兼容性信息
            compatibility_info = self._extract_compatibility_info(materials, analysis_result)
            
            # 选择布局模板
            layout_template = self._select_layout_template(dimensions, materials)
            
            # 生成比例指示器
            scale_indicators = self._generate_scale_indicators(dimensions)
            
            layout_config = {
                "template": layout_template,
                "dimensions": dimensions,
                "compatibility_info": compatibility_info,
                "scale_indicators": scale_indicators,
                "measurement_units": self._determine_measurement_units(dimensions),
                "color_scheme": self._determine_color_scheme(analysis_result),
                "precision_level": "high"
            }
            
            self.logger.info(f"Generated layout config with {len(dimensions)} dimensions")
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
            canvas = self._create_base_canvas()
            template_name = layout_config["template"]
            template = self.layout_templates[template_name]
            
            # 绘制尺寸图表
            canvas = self._draw_dimension_diagram(canvas, layout_config, template, materials)
            
            # 添加尺寸标注
            canvas = self._add_dimension_labels(canvas, layout_config, template)
            
            # 添加兼容性信息
            canvas = self._add_compatibility_info(canvas, layout_config, template)
            
            # 添加比例指示器
            canvas = self._add_scale_indicators(canvas, layout_config, template)
            
            # 添加标题
            canvas = self._add_title(canvas, layout_config, template)
            
            image_data = self._canvas_to_bytes(canvas)
            prompt_used = self._generate_prompt_description(layout_config)
            
            generated_module = GeneratedModule(
                module_type=self.module_type,
                image_data=image_data,
                image_path=None,
                materials_used=materials,
                prompt_used=prompt_used,
                metadata={
                    "layout_template": template_name,
                    "dimensions_count": len(layout_config["dimensions"]),
                    "compatibility_items": len(layout_config["compatibility_info"]),
                    "precision_level": layout_config["precision_level"]
                }
            )
            
            return generated_module
            
        except Exception as e:
            raise ModuleGenerationError(
                f"Failed to generate content: {str(e)}",
                self.module_type,
                "CONTENT_GENERATION_FAILED"
            ) from e
    
    def _extract_dimensions(self, materials: MaterialSet, analysis_result: AnalysisResult) -> List[Dict[str, Any]]:
        """提取尺寸数据"""
        dimensions = []
        
        if "dimensions" in materials.text_inputs:
            dim_lines = materials.text_inputs["dimensions"].split("\n")
            for line in dim_lines:
                if ":" in line:
                    key, value = line.split(":", 1)
                    dimensions.append({
                        "parameter": key.strip(),
                        "value": value.strip(),
                        "unit": self._extract_unit(value.strip()),
                        "numeric_value": self._extract_numeric_value(value.strip()),
                        "tolerance": self._extract_tolerance(value.strip())
                    })
        
        # 默认尺寸
        if len(dimensions) == 0:
            dimensions = [
                {"parameter": "长度", "value": "30cm", "unit": "cm", "numeric_value": 30, "tolerance": "±1mm"},
                {"parameter": "宽度", "value": "20cm", "unit": "cm", "numeric_value": 20, "tolerance": "±1mm"},
                {"parameter": "高度", "value": "10cm", "unit": "cm", "numeric_value": 10, "tolerance": "±1mm"},
                {"parameter": "重量", "value": "2.5kg", "unit": "kg", "numeric_value": 2.5, "tolerance": "±50g"}
            ]
        
        return dimensions
    
    def _extract_compatibility_info(self, materials: MaterialSet, analysis_result: AnalysisResult) -> List[str]:
        """提取兼容性信息"""
        compatibility = []
        
        if "compatibility" in materials.text_inputs:
            comp_lines = materials.text_inputs["compatibility"].split("\n")
            compatibility.extend([c.strip() for c in comp_lines if c.strip()])
        
        # 默认兼容性信息
        if len(compatibility) == 0:
            compatibility = [
                "符合国际标准尺寸",
                "兼容标准安装接口",
                "适配常见规格要求"
            ]
        
        return compatibility
    
    def _select_layout_template(self, dimensions: List[Dict[str, Any]], materials: MaterialSet) -> str:
        """选择布局模板"""
        if len(materials.images) > 0:
            return "dimension_charts"
        else:
            return "scale_comparison"
    
    def _generate_scale_indicators(self, dimensions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """生成比例指示器"""
        indicators = []
        
        for dim in dimensions:
            if dim["numeric_value"] is not None:
                indicators.append({
                    "parameter": dim["parameter"],
                    "scale_ratio": min(dim["numeric_value"] / 100, 1.0),  # 标准化比例
                    "reference": "标准参考"
                })
        
        return indicators
    
    def _determine_measurement_units(self, dimensions: List[Dict[str, Any]]) -> Dict[str, str]:
        """确定测量单位"""
        units = {}
        for dim in dimensions:
            units[dim["parameter"]] = dim["unit"]
        return units
    
    def _extract_unit(self, value: str) -> str:
        """提取单位"""
        units = ["mm", "cm", "m", "kg", "g", "inch", "ft"]
        for unit in units:
            if unit in value:
                return unit
        return ""
    
    def _extract_numeric_value(self, value: str) -> Optional[float]:
        """提取数值"""
        import re
        numbers = re.findall(r'\d+\.?\d*', value)
        if numbers:
            try:
                return float(numbers[0])
            except ValueError:
                pass
        return None
    
    def _extract_tolerance(self, value: str) -> str:
        """提取公差"""
        if "±" in value:
            return value.split("±")[1] if "±" in value else "±1%"
        return "±1%"
    
    def _determine_color_scheme(self, analysis_result: AnalysisResult) -> Dict[str, str]:
        """确定配色方案"""
        return {
            "dimension": "#3498DB",    # 蓝色 - 尺寸
            "compatibility": "#27AE60", # 绿色 - 兼容性
            "tolerance": "#E67E22",    # 橙色 - 公差
            "text": "#2C3E50",         # 深色文字
            "background": "#FFFFFF"    # 白色背景
        }
    
    def _create_base_canvas(self) -> Image.Image:
        """创建基础画布"""
        from ..models import APLUS_IMAGE_SPECS
        width, height = APLUS_IMAGE_SPECS["dimensions"]
        return Image.new('RGB', (width, height), color='white')
    
    def _draw_dimension_diagram(self, canvas: Image.Image, layout_config: Dict[str, Any], 
                               template: Dict[str, Any], materials: MaterialSet) -> Image.Image:
        """绘制尺寸图表"""
        draw = ImageDraw.Draw(canvas)
        
        if "main_diagram_area" in template:
            area = template["main_diagram_area"]
            x1 = int(area[0] * canvas.width)
            y1 = int(area[1] * canvas.height)
            x2 = int(area[2] * canvas.width)
            y2 = int(area[3] * canvas.height)
            
            # 绘制主要图表区域
            draw.rectangle([x1, y1, x2, y2], 
                         outline=layout_config["color_scheme"]["dimension"], 
                         width=3)
            
            # 如果有产品图片，放置在此区域
            if materials.images and len(materials.images) > 0:
                product_image = materials.images[0].content
                if isinstance(product_image, Image.Image):
                    area_width = x2 - x1 - 20
                    area_height = y2 - y1 - 20
                    resized_image = product_image.resize((area_width, area_height), Image.Resampling.LANCZOS)
                    canvas.paste(resized_image, (x1 + 10, y1 + 10))
            else:
                # 绘制简单的产品轮廓
                center_x = (x1 + x2) // 2
                center_y = (y1 + y2) // 2
                draw.rectangle([center_x - 50, center_y - 30, center_x + 50, center_y + 30],
                             outline=layout_config["color_scheme"]["dimension"], width=2)
        
        return canvas
    
    def _add_dimension_labels(self, canvas: Image.Image, layout_config: Dict[str, Any], 
                            template: Dict[str, Any]) -> Image.Image:
        """添加尺寸标注"""
        draw = ImageDraw.Draw(canvas)
        dimensions = layout_config["dimensions"]
        
        if "dimensions_list_area" in template:
            area = template["dimensions_list_area"]
            x1 = int(area[0] * canvas.width)
            y1 = int(area[1] * canvas.height)
            
            # 添加尺寸列表标题
            draw.text((x1, y1), "产品尺寸", 
                     fill=layout_config["color_scheme"]["dimension"])
            
            # 添加尺寸列表
            for i, dim in enumerate(dimensions[:6]):  # 最多6个尺寸
                y_pos = y1 + 25 + i * 20
                dim_text = f"{dim['parameter']}: {dim['value']}"
                if dim.get('tolerance'):
                    dim_text += f" ({dim['tolerance']})"
                
                draw.text((x1, y_pos), dim_text, 
                         fill=layout_config["color_scheme"]["text"])
        
        return canvas
    
    def _add_compatibility_info(self, canvas: Image.Image, layout_config: Dict[str, Any], 
                              template: Dict[str, Any]) -> Image.Image:
        """添加兼容性信息"""
        draw = ImageDraw.Draw(canvas)
        compatibility = layout_config["compatibility_info"]
        
        if "compatibility_area" in template:
            area = template["compatibility_area"]
            x1 = int(area[0] * canvas.width)
            y1 = int(area[1] * canvas.height)
            
            # 添加兼容性标题
            draw.text((x1, y1), "兼容性", 
                     fill=layout_config["color_scheme"]["compatibility"])
            
            # 添加兼容性列表
            for i, comp in enumerate(compatibility[:3]):  # 最多3个兼容性项目
                y_pos = y1 + 25 + i * 20
                
                # 绘制兼容性图标（绿色勾选）
                draw.text((x1, y_pos), "✓", 
                         fill=layout_config["color_scheme"]["compatibility"])
                
                # 绘制兼容性文字
                draw.text((x1 + 15, y_pos), comp, 
                         fill=layout_config["color_scheme"]["text"])
        
        return canvas
    
    def _add_scale_indicators(self, canvas: Image.Image, layout_config: Dict[str, Any], 
                            template: Dict[str, Any]) -> Image.Image:
        """添加比例指示器"""
        # 在适当位置添加比例指示器
        return canvas
    
    def _add_title(self, canvas: Image.Image, layout_config: Dict[str, Any], 
                  template: Dict[str, Any]) -> Image.Image:
        """添加标题"""
        draw = ImageDraw.Draw(canvas)
        
        if "title_area" in template:
            area = template["title_area"]
            x1 = int(area[0] * canvas.width)
            y1 = int(area[1] * canvas.height)
            
            draw.text((x1, y1), "尺寸兼容性", 
                     fill=layout_config["color_scheme"]["text"])
        
        return canvas
    
    def _canvas_to_bytes(self, canvas: Image.Image) -> bytes:
        """将画布转换为字节数据"""
        buffer = io.BytesIO()
        canvas.save(buffer, format='PNG', optimize=True)
        return buffer.getvalue()
    
    def _generate_prompt_description(self, layout_config: Dict[str, Any]) -> str:
        """生成提示词描述"""
        return f"Size compatibility module showing {len(layout_config['dimensions'])} dimensions and {len(layout_config['compatibility_info'])} compatibility items"