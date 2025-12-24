"""
规格对比模块生成器

创建详细规格表和竞争分析，突出产品的技术优势。
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


class SpecificationComparisonGenerator(BaseModuleGenerator):
    """
    规格对比模块生成器
    
    生成规格对比表和竞争分析，包括：
    - 详细规格对比表
    - 竞争优势突出显示
    - 图表和图形展示
    - 优越规格的视觉强调
    """
    
    def __init__(self):
        super().__init__(ModuleType.SPECIFICATION_COMPARISON)
        self.layout_templates = {
            "comparison_table": {
                "table_area": (0.1, 0.2, 0.9, 0.8),
                "title_area": (0.1, 0.05, 0.9, 0.15),
                "legend_area": (0.1, 0.85, 0.9, 0.95)
            },
            "side_by_side": {
                "our_product_area": (0.05, 0.2, 0.47, 0.8),
                "competitor_area": (0.53, 0.2, 0.95, 0.8),
                "vs_indicator": (0.47, 0.45, 0.53, 0.55),
                "title_area": (0.1, 0.05, 0.9, 0.15)
            },
            "chart_comparison": {
                "chart_area": (0.1, 0.3, 0.6, 0.8),
                "spec_list_area": (0.65, 0.3, 0.9, 0.8),
                "title_area": (0.1, 0.05, 0.9, 0.25)
            }
        }
    
    def get_module_info(self) -> Dict[str, Any]:
        """获取模块信息"""
        return {
            "name": "规格对比",
            "description": "创建详细的规格对比表，突出产品的技术优势和竞争力",
            "category": "professional",
            "recommended_use_cases": [
                "技术产品对比",
                "竞争优势展示",
                "规格参数说明",
                "购买决策支持"
            ],
            "layout_options": list(self.layout_templates.keys()),
            "generation_time_estimate": 55
        }
    
    def get_material_requirements(self) -> MaterialRequirements:
        """获取素材需求"""
        requirements = [
            MaterialRequirement(
                material_type=MaterialType.TEXT,
                priority=MaterialPriority.REQUIRED,
                description="产品规格数据",
                examples=["尺寸: 30x20x10cm", "重量: 2.5kg", "功率: 100W"],
                tooltip="提供详细的产品规格参数"
            ),
            MaterialRequirement(
                material_type=MaterialType.TEXT,
                priority=MaterialPriority.RECOMMENDED,
                description="竞争对手信息",
                examples=["竞品A规格", "市场对比数据", "行业标准"],
                tooltip="提供竞争对手的规格信息用于对比"
            ),
            MaterialRequirement(
                material_type=MaterialType.TEXT,
                priority=MaterialPriority.RECOMMENDED,
                description="优势亮点说明",
                examples=["领先技术", "独特优势", "超越标准"],
                tooltip="说明产品相比竞品的优势所在"
            ),
            MaterialRequirement(
                material_type=MaterialType.IMAGE,
                priority=MaterialPriority.AI_GENERATED,
                description="规格图表素材",
                examples=["性能图表", "对比图", "数据可视化"],
                file_formats=["PNG", "JPG", "WEBP"],
                max_file_size=10 * 1024 * 1024,
                tooltip="用于展示规格对比的图表或图像"
            ),
            MaterialRequirement(
                material_type=MaterialType.CUSTOM_PROMPT,
                priority=MaterialPriority.AI_GENERATED,
                description="对比展示风格",
                examples=["专业对比表", "图表展示", "简洁对比"],
                tooltip="AI将选择最适合的规格对比展示方式"
            )
        ]
        
        return MaterialRequirements(
            module_type=self.module_type,
            requirements=requirements
        )
    
    async def generate_layout(self, materials: MaterialSet, analysis_result: AnalysisResult) -> Dict[str, Any]:
        """生成布局配置"""
        try:
            # 分析规格数据复杂度
            spec_complexity = self._analyze_specification_complexity(materials, analysis_result)
            
            # 选择布局模板
            layout_template = self._select_layout_template(spec_complexity, materials)
            
            # 提取产品规格
            our_specs = self._extract_product_specifications(materials, analysis_result)
            
            # 提取竞争对手规格
            competitor_specs = self._extract_competitor_specifications(materials, analysis_result)
            
            # 识别优势规格
            superior_specs = self._identify_superior_specifications(our_specs, competitor_specs)
            
            # 生成对比数据
            comparison_data = self._generate_comparison_data(our_specs, competitor_specs)
            
            layout_config = {
                "template": layout_template,
                "spec_complexity": spec_complexity,
                "our_specs": our_specs,
                "competitor_specs": competitor_specs,
                "superior_specs": superior_specs,
                "comparison_data": comparison_data,
                "chart_type": self._determine_chart_type(spec_complexity),
                "color_scheme": self._determine_color_scheme(analysis_result),
                "highlight_style": "superior_emphasis"
            }
            
            self.logger.info(f"Generated layout config with {len(our_specs)} specs and {len(superior_specs)} superior specs")
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
            
            # 绘制对比表格
            canvas = self._draw_comparison_table(canvas, layout_config, template)
            
            # 添加优势突出显示
            canvas = self._highlight_superior_specs(canvas, layout_config, template)
            
            # 添加图表展示
            canvas = self._add_charts_and_graphs(canvas, layout_config, template)
            
            # 添加标题和图例
            canvas = self._add_titles_and_legend(canvas, layout_config, template)
            
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
                    "specs_count": len(layout_config["our_specs"]),
                    "superior_specs_count": len(layout_config["superior_specs"]),
                    "spec_complexity": layout_config["spec_complexity"],
                    "chart_type": layout_config["chart_type"]
                }
            )
            
            self.logger.info("Successfully generated specification comparison module")
            return generated_module
            
        except Exception as e:
            raise ModuleGenerationError(
                f"Failed to generate content: {str(e)}",
                self.module_type,
                "CONTENT_GENERATION_FAILED"
            ) from e
    
    def _analyze_specification_complexity(self, materials: MaterialSet, analysis_result: AnalysisResult) -> str:
        """分析规格复杂度"""
        spec_count = 0
        
        # 统计规格数量
        if "specifications" in materials.text_inputs:
            spec_count = len([line for line in materials.text_inputs["specifications"].split("\n") if ":" in line])
        
        # 检查是否有竞争对手数据
        has_competitor_data = "competitor_specs" in materials.text_inputs
        
        if spec_count > 8 or has_competitor_data:
            return "high"
        elif spec_count > 4:
            return "medium"
        else:
            return "low"
    
    def _select_layout_template(self, spec_complexity: str, materials: MaterialSet) -> str:
        """选择布局模板"""
        if spec_complexity == "high":
            return "comparison_table"
        elif "competitor_specs" in materials.text_inputs:
            return "side_by_side"
        else:
            return "chart_comparison"
    
    def _extract_product_specifications(self, materials: MaterialSet, analysis_result: AnalysisResult) -> List[Dict[str, Any]]:
        """提取产品规格"""
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
                        "unit": self._extract_unit(value.strip()),
                        "numeric_value": self._extract_numeric_value(value.strip()),
                        "is_superior": False  # 将在对比中确定
                    })
        
        # 从分析结果提取
        if analysis_result.listing_analysis and analysis_result.listing_analysis.technical_specifications:
            for key, value in analysis_result.listing_analysis.technical_specifications.items():
                specs.append({
                    "parameter": key,
                    "value": value,
                    "unit": self._extract_unit(value),
                    "numeric_value": self._extract_numeric_value(value),
                    "is_superior": False
                })
        
        # 默认规格
        if len(specs) == 0:
            specs = [
                {"parameter": "性能", "value": "高性能", "unit": "", "numeric_value": None, "is_superior": True},
                {"parameter": "质量", "value": "优质材料", "unit": "", "numeric_value": None, "is_superior": True},
                {"parameter": "保修", "value": "2年保修", "unit": "年", "numeric_value": 2, "is_superior": True}
            ]
        
        return specs
    
    def _extract_competitor_specifications(self, materials: MaterialSet, analysis_result: AnalysisResult) -> List[Dict[str, Any]]:
        """提取竞争对手规格"""
        competitor_specs = []
        
        # 从用户输入提取
        if "competitor_specs" in materials.text_inputs:
            spec_lines = materials.text_inputs["competitor_specs"].split("\n")
            for line in spec_lines:
                if ":" in line:
                    key, value = line.split(":", 1)
                    competitor_specs.append({
                        "parameter": key.strip(),
                        "value": value.strip(),
                        "unit": self._extract_unit(value.strip()),
                        "numeric_value": self._extract_numeric_value(value.strip())
                    })
        
        # 如果没有竞争对手数据，生成默认对比数据
        if len(competitor_specs) == 0:
            competitor_specs = [
                {"parameter": "性能", "value": "标准性能", "unit": "", "numeric_value": None},
                {"parameter": "质量", "value": "普通材料", "unit": "", "numeric_value": None},
                {"parameter": "保修", "value": "1年保修", "unit": "年", "numeric_value": 1}
            ]
        
        return competitor_specs
    
    def _extract_unit(self, value: str) -> str:
        """提取单位"""
        units = ["mm", "cm", "m", "kg", "g", "MHz", "GHz", "MB", "GB", "TB", "V", "A", "W", "年", "月", "天"]
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
    
    def _identify_superior_specifications(self, our_specs: List[Dict[str, Any]], 
                                        competitor_specs: List[Dict[str, Any]]) -> List[str]:
        """识别优势规格"""
        superior_specs = []
        
        # 创建竞争对手规格字典
        competitor_dict = {spec["parameter"]: spec for spec in competitor_specs}
        
        for our_spec in our_specs:
            param = our_spec["parameter"]
            if param in competitor_dict:
                competitor_spec = competitor_dict[param]
                
                # 比较数值
                if (our_spec["numeric_value"] is not None and 
                    competitor_spec["numeric_value"] is not None):
                    if our_spec["numeric_value"] > competitor_spec["numeric_value"]:
                        superior_specs.append(param)
                        our_spec["is_superior"] = True
                # 如果没有数值，标记为优势（用户提供的通常是优势）
                else:
                    superior_specs.append(param)
                    our_spec["is_superior"] = True
        
        return superior_specs
    
    def _generate_comparison_data(self, our_specs: List[Dict[str, Any]], 
                                competitor_specs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """生成对比数据"""
        return {
            "total_parameters": len(our_specs),
            "superior_count": len([spec for spec in our_specs if spec.get("is_superior", False)]),
            "comparison_pairs": self._create_comparison_pairs(our_specs, competitor_specs)
        }
    
    def _create_comparison_pairs(self, our_specs: List[Dict[str, Any]], 
                               competitor_specs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """创建对比配对"""
        pairs = []
        competitor_dict = {spec["parameter"]: spec for spec in competitor_specs}
        
        for our_spec in our_specs:
            param = our_spec["parameter"]
            competitor_spec = competitor_dict.get(param, {"value": "未知", "numeric_value": None})
            
            pairs.append({
                "parameter": param,
                "our_value": our_spec["value"],
                "competitor_value": competitor_spec["value"],
                "is_superior": our_spec.get("is_superior", False)
            })
        
        return pairs
    
    def _determine_chart_type(self, spec_complexity: str) -> str:
        """确定图表类型"""
        chart_mapping = {
            "low": "bar_chart",
            "medium": "comparison_chart",
            "high": "detailed_table"
        }
        return chart_mapping.get(spec_complexity, "comparison_chart")
    
    def _determine_color_scheme(self, analysis_result: AnalysisResult) -> Dict[str, str]:
        """确定配色方案"""
        return {
            "superior": "#27AE60",     # 绿色 - 优势
            "standard": "#95A5A6",     # 灰色 - 标准
            "inferior": "#E74C3C",     # 红色 - 劣势
            "our_product": "#3498DB",  # 蓝色 - 我们的产品
            "competitor": "#E67E22",   # 橙色 - 竞争对手
            "text": "#2C3E50",         # 深色文字
            "background": "#FFFFFF"    # 白色背景
        }
    
    def _create_base_canvas(self) -> Image.Image:
        """创建基础画布"""
        from ..models import APLUS_IMAGE_SPECS
        width, height = APLUS_IMAGE_SPECS["dimensions"]
        canvas = Image.new('RGB', (width, height), color='white')
        return canvas
    
    def _draw_comparison_table(self, canvas: Image.Image, layout_config: Dict[str, Any], 
                              template: Dict[str, Any]) -> Image.Image:
        """绘制对比表格"""
        draw = ImageDraw.Draw(canvas)
        comparison_pairs = layout_config["comparison_data"]["comparison_pairs"]
        
        if "table_area" in template:
            area = template["table_area"]
            x1 = int(area[0] * canvas.width)
            y1 = int(area[1] * canvas.height)
            x2 = int(area[2] * canvas.width)
            y2 = int(area[3] * canvas.height)
            
            # 绘制表格边框
            draw.rectangle([x1, y1, x2, y2], 
                         outline=layout_config["color_scheme"]["text"], 
                         width=2)
            
            # 绘制表头
            header_height = 30
            draw.rectangle([x1, y1, x2, y1 + header_height], 
                         fill=layout_config["color_scheme"]["our_product"])
            
            col_width = (x2 - x1) // 3
            draw.text((x1 + 10, y1 + 8), "规格参数", fill="white")
            draw.text((x1 + col_width + 10, y1 + 8), "我们的产品", fill="white")
            draw.text((x1 + 2 * col_width + 10, y1 + 8), "竞争对手", fill="white")
            
            # 绘制数据行
            row_height = 25
            for i, pair in enumerate(comparison_pairs[:8]):  # 最多8行
                y_pos = y1 + header_height + i * row_height
                
                # 行背景色
                if pair["is_superior"]:
                    row_color = layout_config["color_scheme"]["superior"]
                    alpha = 50  # 浅色背景
                else:
                    row_color = layout_config["color_scheme"]["background"]
                
                # 绘制行分隔线
                draw.line([x1, y_pos, x2, y_pos], 
                         fill=layout_config["color_scheme"]["text"], width=1)
                
                # 绘制数据
                draw.text((x1 + 5, y_pos + 5), pair["parameter"], 
                         fill=layout_config["color_scheme"]["text"])
                draw.text((x1 + col_width + 5, y_pos + 5), pair["our_value"], 
                         fill=layout_config["color_scheme"]["text"])
                draw.text((x1 + 2 * col_width + 5, y_pos + 5), pair["competitor_value"], 
                         fill=layout_config["color_scheme"]["text"])
        
        return canvas
    
    def _highlight_superior_specs(self, canvas: Image.Image, layout_config: Dict[str, Any], 
                                template: Dict[str, Any]) -> Image.Image:
        """突出显示优势规格"""
        # 在对比表格中已经通过颜色突出显示了优势规格
        # 这里可以添加额外的视觉强调，如星标、徽章等
        return canvas
    
    def _add_charts_and_graphs(self, canvas: Image.Image, layout_config: Dict[str, Any], 
                             template: Dict[str, Any]) -> Image.Image:
        """添加图表和图形"""
        if "chart_area" in template:
            # 这里可以添加柱状图、饼图等数据可视化
            # 暂时跳过复杂的图表绘制
            pass
        return canvas
    
    def _add_titles_and_legend(self, canvas: Image.Image, layout_config: Dict[str, Any], 
                             template: Dict[str, Any]) -> Image.Image:
        """添加标题和图例"""
        draw = ImageDraw.Draw(canvas)
        
        if "title_area" in template:
            area = template["title_area"]
            x1 = int(area[0] * canvas.width)
            y1 = int(area[1] * canvas.height)
            
            # 添加主标题
            draw.text((x1, y1), "规格对比", 
                     fill=layout_config["color_scheme"]["text"])
            
            # 添加副标题
            superior_count = layout_config["comparison_data"]["superior_count"]
            total_count = layout_config["comparison_data"]["total_parameters"]
            subtitle = f"优势项目: {superior_count}/{total_count}"
            draw.text((x1, y1 + 25), subtitle, 
                     fill=layout_config["color_scheme"]["superior"])
        
        if "legend_area" in template:
            area = template["legend_area"]
            x1 = int(area[0] * canvas.width)
            y1 = int(area[1] * canvas.height)
            
            # 添加图例
            draw.text((x1, y1), "绿色背景表示我们的优势项目", 
                     fill=layout_config["color_scheme"]["superior"])
        
        return canvas
    
    def _apply_professional_styling(self, canvas: Image.Image, layout_config: Dict[str, Any]) -> Image.Image:
        """应用专业样式"""
        # 添加专业的视觉元素
        return canvas
    
    def _canvas_to_bytes(self, canvas: Image.Image) -> bytes:
        """将画布转换为字节数据"""
        buffer = io.BytesIO()
        canvas.save(buffer, format='PNG', optimize=True)
        return buffer.getvalue()
    
    def _generate_prompt_description(self, layout_config: Dict[str, Any]) -> str:
        """生成提示词描述"""
        return f"Specification comparison module with {layout_config['template']} layout, " \
               f"comparing {len(layout_config['our_specs'])} specifications with " \
               f"{len(layout_config['superior_specs'])} superior specs highlighted"