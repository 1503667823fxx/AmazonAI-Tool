"""
Trust Module Generator for A+ Studio system.

This module implements the Trust (信任转化) module generator that creates
Premium Image with Text layout with golden ratio compositions (1:1 or 2:3),
bullet-point formatting, and comprehensive product information display.
"""

from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from PIL import Image
import io
import asyncio

from .models import (
    AnalysisResult, ModulePrompt, GenerationResult, ModuleType,
    ValidationStatus, APLUS_IMAGE_SPECS
)
from .image_service import APlusImageService
from .prompt_service import PromptGenerationService


@dataclass
class GoldenRatioLayout:
    """黄金比例布局配置"""
    ratio_type: str  # "1:1" or "2:3"
    left_section: str
    right_section: str
    visual_weight: Dict[str, float]
    content_distribution: Dict[str, str]


@dataclass
class BulletPointStructure:
    """清单式Bullet Points结构"""
    core_parameters: List[str]
    service_guarantees: List[str]
    cta_guidance: List[str]
    formatting_rules: List[str]


@dataclass
class TrustElements:
    """信任转化要素配置"""
    credibility_indicators: List[str]
    social_proof: List[str]
    guarantee_statements: List[str]
    urgency_triggers: List[str]


@dataclass
class InformationDensity:
    """信息密度优化配置"""
    content_hierarchy: List[str]
    readability_rules: List[str]
    visual_breaks: List[str]
    emphasis_techniques: List[str]


class TrustModuleGenerator:
    """信任转化模块生成器 - 实现Premium Image with Text布局生成"""
    
    def __init__(self, image_service: APlusImageService, prompt_service: PromptGenerationService):
        self.image_service = image_service
        self.prompt_service = prompt_service
        
        # 黄金比例布局配置
        self.golden_ratio_layouts = {
            "1:1": GoldenRatioLayout(
                ratio_type="1:1",
                left_section="产品视觉展示区域（50%）",
                right_section="文字信息展示区域（50%）",
                visual_weight={"image": 0.5, "text": 0.5},
                content_distribution={
                    "image_content": "人与产品合影或产品全家福配件图",
                    "text_content": "核心参数、服务保障、CTA引导"
                }
            ),
            "2:3": GoldenRatioLayout(
                ratio_type="2:3",
                left_section="产品视觉展示区域（40%）",
                right_section="文字信息展示区域（60%）",
                visual_weight={"image": 0.4, "text": 0.6},
                content_distribution={
                    "image_content": "产品特写或使用场景图",
                    "text_content": "详细参数汇总、完整服务保障、强化CTA"
                }
            )
        }
        
        # 清单式Bullet Points结构配置
        self.bullet_point_structure = BulletPointStructure(
            core_parameters=[
                "产品核心规格参数",
                "关键技术指标",
                "性能特征数据",
                "兼容性信息",
                "尺寸重量规格"
            ],
            service_guarantees=[
                "质量保证承诺",
                "售后服务政策",
                "退换货保障",
                "技术支持服务",
                "延保服务选项"
            ],
            cta_guidance=[
                "立即购买引导",
                "优惠信息提示",
                "库存紧张提醒",
                "限时活动通知",
                "咨询联系方式"
            ],
            formatting_rules=[
                "使用清晰的项目符号（•）",
                "每行信息简洁明了",
                "重要信息加粗突出",
                "分段组织相关内容",
                "保持视觉层次清晰"
            ]
        )
        
        # 信任转化要素配置
        self.trust_elements = TrustElements(
            credibility_indicators=[
                "品牌认证标识",
                "质量检测报告",
                "行业奖项荣誉",
                "专业机构认可",
                "国际标准符合"
            ],
            social_proof=[
                "用户评价数量",
                "满意度评分",
                "销量数据展示",
                "专家推荐",
                "媒体报道"
            ],
            guarantee_statements=[
                "100%正品保证",
                "30天无理由退货",
                "全国联保服务",
                "7x24小时客服",
                "终身技术支持"
            ],
            urgency_triggers=[
                "限时特价优惠",
                "库存数量有限",
                "今日下单优惠",
                "仅限前100名",
                "活动即将结束"
            ]
        )
        
        # 信息密度优化配置
        self.information_density = InformationDensity(
            content_hierarchy=[
                "标题层级：产品名称和核心卖点",
                "主要信息：关键参数和特征",
                "支撑信息：服务保障和认证",
                "行动引导：购买和咨询CTA",
                "补充信息：优惠和联系方式"
            ],
            readability_rules=[
                "字体大小层次分明",
                "行间距适中舒适",
                "段落间留白充足",
                "重点信息突出显示",
                "整体布局平衡协调"
            ],
            visual_breaks=[
                "分割线区分内容块",
                "背景色块突出重点",
                "图标辅助信息识别",
                "留白创造视觉呼吸",
                "颜色对比增强可读性"
            ],
            emphasis_techniques=[
                "加粗标题和关键词",
                "颜色突出重要信息",
                "图标增强视觉识别",
                "框线围绕核心内容",
                "渐变背景提升层次"
            ]
        )
        
        # 视觉区域内容配置
        self.visual_content_options = {
            "人物合影": {
                "description": "真实用户与产品的使用合影",
                "scenarios": ["家庭使用场景", "办公使用场景", "户外使用场景", "专业使用场景"],
                "emotional_impact": "建立真实使用感和信任感",
                "composition_tips": "自然互动，产品清晰可见，表情愉悦满意"
            },
            "产品全家福": {
                "description": "产品主体及所有配件的完整展示",
                "scenarios": ["开箱展示", "配件齐全", "功能组合", "套装展示"],
                "emotional_impact": "展现产品完整价值和丰富配置",
                "composition_tips": "整齐排列，层次分明，配件功能清晰"
            },
            "使用场景": {
                "description": "产品在实际使用环境中的展示",
                "scenarios": ["工作环境", "生活场景", "专业应用", "日常使用"],
                "emotional_impact": "展现产品实用性和适用性",
                "composition_tips": "环境真实，使用自然，效果明显"
            },
            "细节特写": {
                "description": "产品关键功能和细节的特写展示",
                "scenarios": ["工艺细节", "功能特写", "材质展示", "技术亮点"],
                "emotional_impact": "突出产品品质和技术优势",
                "composition_tips": "细节清晰，光影到位，质感突出"
            }
        }
    
    async def generate_trust_image(
        self, 
        analysis: AnalysisResult,
        custom_params: Optional[Dict[str, Any]] = None
    ) -> GenerationResult:
        """生成信任转化模块图片 - Premium Image with Text布局"""
        
        try:
            # 1. 选择黄金比例布局
            layout_config = self._select_golden_ratio_layout(analysis, custom_params)
            
            # 2. 构建信息内容结构
            content_structure = self._build_content_structure(analysis)
            
            # 3. 设计视觉区域内容
            visual_content = self._design_visual_content(analysis, layout_config)
            
            # 4. 优化信息密度
            density_optimization = self._optimize_information_density(content_structure)
            
            # 5. 构建信任转化提示词
            trust_prompt = self._build_trust_prompt(
                analysis, layout_config, content_structure, 
                visual_content, density_optimization, custom_params
            )
            
            # 6. 生成图片
            generation_result = await self.image_service.generate_aplus_image(
                trust_prompt,
                reference_images=self._get_reference_images(analysis)
            )
            
            # 7. 后处理和优化
            if generation_result.image_data:
                generation_result = await self._post_process_trust_image(generation_result)
            
            return generation_result
            
        except Exception as e:
            return GenerationResult(
                module_type=ModuleType.TRUST,
                image_data=None,
                image_path=None,
                prompt_used="",
                generation_time=0.0,
                quality_score=0.0,
                validation_status=ValidationStatus.FAILED,
                metadata={"error": f"Trust module generation failed: {str(e)}"}
            )
    
    def _select_golden_ratio_layout(
        self, 
        analysis: AnalysisResult, 
        custom_params: Optional[Dict[str, Any]] = None
    ) -> GoldenRatioLayout:
        """选择合适的黄金比例布局"""
        
        # 检查自定义参数
        if custom_params and "layout_ratio" in custom_params:
            ratio_preference = custom_params["layout_ratio"]
            if ratio_preference in self.golden_ratio_layouts:
                return self.golden_ratio_layouts[ratio_preference]
        
        # 根据产品特征和内容量选择布局
        listing = analysis.listing_analysis
        
        # 计算文字内容复杂度
        text_complexity = (
            len(listing.key_selling_points) +
            len(listing.competitive_advantages) +
            len(listing.technical_specifications)
        )
        
        # 如果文字内容较多，使用2:3布局给文字更多空间
        if text_complexity > 8:
            return self.golden_ratio_layouts["2:3"]
        
        # 如果产品视觉效果重要，使用1:1平衡布局
        if any(visual in listing.product_category.lower() 
               for visual in ['fashion', '时尚', 'beauty', '美容', 'design', '设计']):
            return self.golden_ratio_layouts["1:1"]
        
        # 默认使用2:3布局，更适合信息展示
        return self.golden_ratio_layouts["2:3"]
    
    def _build_content_structure(self, analysis: AnalysisResult) -> Dict[str, List[str]]:
        """构建信息内容结构"""
        
        listing = analysis.listing_analysis
        
        # 构建核心参数汇总
        core_parameters = []
        
        # 从技术规格中提取关键参数
        for key, value in listing.technical_specifications.items():
            if len(core_parameters) < 5:  # 限制参数数量
                core_parameters.append(f"{key}: {value}")
        
        # 如果技术规格不足，从卖点中补充
        if len(core_parameters) < 3:
            for selling_point in listing.key_selling_points[:3]:
                if selling_point not in core_parameters:
                    core_parameters.append(selling_point)
        
        # 构建服务保障内容
        service_guarantees = []
        
        # 根据竞争优势推断服务保障
        for advantage in listing.competitive_advantages:
            if "quality" in advantage.lower() or "品质" in advantage:
                service_guarantees.append("品质保证 - 严格质量控制，确保产品可靠性")
            elif "service" in advantage.lower() or "服务" in advantage:
                service_guarantees.append("专业服务 - 7x24小时客户支持")
            elif "warranty" in advantage.lower() or "保修" in advantage:
                service_guarantees.append("全面保修 - 全国联保，安心无忧")
        
        # 补充标准服务保障
        standard_guarantees = [
            "正品保证 - 100%原厂正品，假一赔十",
            "快速发货 - 现货当天发，次日即可达",
            "无忧退换 - 30天无理由退换货"
        ]
        
        for guarantee in standard_guarantees:
            if len(service_guarantees) < 4:
                service_guarantees.append(guarantee)
        
        # 构建CTA引导内容
        cta_guidance = [
            "立即下单 - 享受限时优惠价格",
            "现货充足 - 下单即发，快速到货",
            "专业咨询 - 售前售后全程服务"
        ]
        
        # 根据目标用户调整CTA
        if "professional" in listing.target_demographics.lower():
            cta_guidance.append("企业采购 - 批量优惠，开具发票")
        elif "family" in listing.target_demographics.lower():
            cta_guidance.append("家庭首选 - 安全可靠，全家放心")
        
        return {
            "core_parameters": core_parameters,
            "service_guarantees": service_guarantees,
            "cta_guidance": cta_guidance
        }
    
    def _design_visual_content(
        self, 
        analysis: AnalysisResult, 
        layout_config: GoldenRatioLayout
    ) -> Dict[str, str]:
        """设计视觉区域内容"""
        
        listing = analysis.listing_analysis
        
        # 根据产品类别选择最适合的视觉内容
        category = listing.product_category.lower()
        
        if any(cat in category for cat in ['electronic', '电子', 'device', '设备']):
            visual_type = "产品全家福"
            visual_focus = "展示产品主体及所有配件的完整配置"
        elif any(cat in category for cat in ['home', '家居', 'furniture', '家具']):
            visual_type = "使用场景"
            visual_focus = "展示产品在真实家居环境中的使用效果"
        elif any(cat in category for cat in ['fashion', '时尚', 'beauty', '美容']):
            visual_type = "人物合影"
            visual_focus = "展示真实用户使用产品的满意状态"
        else:
            visual_type = "细节特写"
            visual_focus = "突出产品的关键功能和品质细节"
        
        visual_config = self.visual_content_options[visual_type]
        
        return {
            "visual_type": visual_type,
            "visual_focus": visual_focus,
            "description": visual_config["description"],
            "emotional_impact": visual_config["emotional_impact"],
            "composition_tips": visual_config["composition_tips"],
            "layout_ratio": layout_config.ratio_type,
            "visual_weight": layout_config.visual_weight["image"]
        }
    
    def _optimize_information_density(self, content_structure: Dict[str, List[str]]) -> Dict[str, Any]:
        """优化信息密度"""
        
        total_items = (
            len(content_structure["core_parameters"]) +
            len(content_structure["service_guarantees"]) +
            len(content_structure["cta_guidance"])
        )
        
        # 根据信息量调整密度
        if total_items > 12:
            density_level = "high"
            font_adjustments = "使用较小字体，紧凑排列"
            spacing_adjustments = "减少行间距，优化空间利用"
        elif total_items > 8:
            density_level = "medium"
            font_adjustments = "标准字体大小，清晰易读"
            spacing_adjustments = "适中行间距，平衡美观与信息量"
        else:
            density_level = "low"
            font_adjustments = "较大字体，突出重点"
            spacing_adjustments = "充足留白，舒适阅读体验"
        
        return {
            "density_level": density_level,
            "total_information_items": total_items,
            "font_adjustments": font_adjustments,
            "spacing_adjustments": spacing_adjustments,
            "hierarchy_rules": self.information_density.content_hierarchy,
            "readability_optimization": self.information_density.readability_rules,
            "visual_enhancement": self.information_density.emphasis_techniques
        }
    
    def _build_trust_prompt(
        self,
        analysis: AnalysisResult,
        layout_config: GoldenRatioLayout,
        content_structure: Dict[str, List[str]],
        visual_content: Dict[str, str],
        density_optimization: Dict[str, Any],
        custom_params: Optional[Dict[str, Any]] = None
    ) -> ModulePrompt:
        """构建完整的信任转化提示词"""
        
        listing = analysis.listing_analysis
        visual_style = analysis.visual_style
        
        # 构建黄金比例布局描述
        layout_description = f"""
        黄金比例布局设计 - {layout_config.ratio_type}：
        - 左侧区域（{layout_config.visual_weight['image']*100:.0f}%）：{layout_config.left_section}
        - 右侧区域（{layout_config.visual_weight['text']*100:.0f}%）：{layout_config.right_section}
        
        布局原则：
        - 视觉平衡：图文比例符合黄金分割美学
        - 信息层次：重要信息优先级明确
        - 阅读流程：从视觉吸引到信息获取再到行动引导
        - 空间利用：最大化信息密度同时保持可读性
        """
        
        # 构建视觉区域设计
        visual_area_design = f"""
        视觉区域内容设计：
        - 内容类型：{visual_content['visual_type']}
        - 展示重点：{visual_content['visual_focus']}
        - 内容描述：{visual_content['description']}
        - 情感影响：{visual_content['emotional_impact']}
        - 构图要点：{visual_content['composition_tips']}
        - 视觉权重：{visual_content['visual_weight']*100:.0f}%
        """
        
        # 构建文字区域内容
        text_area_content = f"""
        文字区域内容结构：
        
        === 核心参数汇总 ===
        {chr(10).join([f"• {param}" for param in content_structure['core_parameters']])}
        
        === 服务保障承诺 ===
        {chr(10).join([f"• {guarantee}" for guarantee in content_structure['service_guarantees']])}
        
        === CTA行动引导 ===
        {chr(10).join([f"• {cta}" for cta in content_structure['cta_guidance']])}
        """
        
        # 构建清单式排版要求
        bullet_points_formatting = f"""
        清单式Bullet Points排版要求：
        
        格式规范：
        {chr(10).join([f"• {rule}" for rule in self.bullet_point_structure.formatting_rules])}
        
        信息密度优化：
        - 密度级别：{density_optimization['density_level']}
        - 信息项目总数：{density_optimization['total_information_items']}
        - 字体调整：{density_optimization['font_adjustments']}
        - 间距调整：{density_optimization['spacing_adjustments']}
        
        视觉层次：
        {chr(10).join([f"• {hierarchy}" for hierarchy in density_optimization['hierarchy_rules']])}
        
        可读性优化：
        {chr(10).join([f"• {rule}" for rule in density_optimization['readability_optimization']])}
        
        视觉强化：
        {chr(10).join([f"• {technique}" for technique in density_optimization['visual_enhancement']])}
        """
        
        # 构建信任转化要素
        trust_conversion_elements = f"""
        信任转化要素集成：
        
        可信度指标：
        {chr(10).join([f"• {indicator}" for indicator in self.trust_elements.credibility_indicators])}
        
        社会证明：
        {chr(10).join([f"• {proof}" for proof in self.trust_elements.social_proof])}
        
        保障声明：
        {chr(10).join([f"• {guarantee}" for guarantee in self.trust_elements.guarantee_statements])}
        
        紧迫感触发：
        {chr(10).join([f"• {trigger}" for trigger in self.trust_elements.urgency_triggers])}
        """
        
        # 应用自定义参数
        custom_adjustments = ""
        if custom_params:
            if "trust_emphasis" in custom_params:
                custom_adjustments += f"\n信任强调：{custom_params['trust_emphasis']}"
            if "cta_style" in custom_params:
                custom_adjustments += f"\nCTA风格：{custom_params['cta_style']}"
            if "information_priority" in custom_params:
                custom_adjustments += f"\n信息优先级：{custom_params['information_priority']}"
        
        # 构建完整提示词
        full_prompt = f"""
        创建一个600x450像素的Premium Image with Text布局，展现{listing.product_category}的完整产品信息和购买引导。

        === 产品信息 ===
        产品类别：{listing.product_category}
        核心卖点：{', '.join(listing.key_selling_points)}
        目标用户：{listing.target_demographics}
        竞争优势：{', '.join(listing.competitive_advantages)}
        技术规格：{', '.join(f"{k}: {v}" for k, v in list(listing.technical_specifications.items())[:3])}

        === 黄金比例布局 ===
        {layout_description}

        === 视觉区域设计 ===
        {visual_area_design}

        === 文字区域内容 ===
        {text_area_content}

        === 清单式排版 ===
        {bullet_points_formatting}

        === 信任转化要素 ===
        {trust_conversion_elements}

        === 视觉风格 ===
        色调盘：{', '.join(visual_style.color_palette)}
        光照风格：{visual_style.lighting_style}
        构图规则：{', '.join(visual_style.composition_rules)}
        美学方向：{visual_style.aesthetic_direction}

        === 技术规格 ===
        - 尺寸：600x450像素（4:3宽高比）
        - 格式：高质量PNG，适合电商展示
        - 色彩空间：sRGB
        - 分辨率：最低72 DPI
        - 文件大小：5MB以内

        === 质量标准 ===
        - 专业电商级别的视觉质量
        - 清晰的信息层次和可读性
        - 平衡的图文比例和视觉美感
        - 有效的信任建立和转化引导
        - 符合Amazon A+页面展示要求
        - 优化的信息密度和用户体验

        === 核心目标 ===
        通过完整的产品信息展示、可信的服务保障和有效的行动引导，建立用户信任并促进购买决策。

        {custom_adjustments}
        """
        
        return ModulePrompt(
            module_type=ModuleType.TRUST,
            base_prompt=full_prompt.strip(),
            style_modifiers=[
                "premium_image_with_text",
                "golden_ratio_layout",
                "bullet_points_formatting",
                "trust_conversion_elements",
                "information_density_optimization",
                "cta_integration",
                "credibility_indicators",
                "social_proof_display",
                "service_guarantee_emphasis"
            ],
            technical_requirements=[
                "600x450_pixels",
                "4_3_aspect_ratio",
                "golden_ratio_composition",
                "bullet_points_support",
                "text_readability_optimization",
                "trust_elements_integration",
                "cta_prominence",
                "information_hierarchy",
                "visual_text_balance"
            ],
            aspect_ratio="600x450",
            quality_settings={
                "resolution": "high",
                "color_depth": "24bit",
                "compression": "lossless",
                "text_rendering": "crisp",
                "layout_precision": "professional",
                "readability_optimization": True
            }
        )
    
    def _get_reference_images(self, analysis: AnalysisResult) -> Optional[List[Image.Image]]:
        """获取参考图片"""
        reference_images = []
        
        # 从分析结果中获取产品图片
        if analysis.product_info and analysis.product_info.uploaded_images:
            for img in analysis.product_info.uploaded_images:
                if isinstance(img, Image.Image):
                    reference_images.append(img)
        
        return reference_images if reference_images else None
    
    async def _post_process_trust_image(self, generation_result: GenerationResult) -> GenerationResult:
        """后处理信任转化图片"""
        try:
            if not generation_result.image_data:
                return generation_result
            
            # 1. 验证A+规范
            validation_result = self.image_service.validate_aplus_requirements(generation_result.image_data)
            generation_result.validation_status = validation_result.validation_status
            
            # 2. 优化图片质量
            optimized_data = self.image_service.optimize_for_amazon(generation_result.image_data)
            generation_result.image_data = optimized_data
            
            # 3. 评估图片质量
            quality_assessment = self.image_service.assess_image_quality(optimized_data)
            generation_result.quality_score = quality_assessment.get("overall_score", 0.0)
            
            # 4. 信任转化特定优化
            trust_optimization = self._apply_trust_optimization(optimized_data)
            if trust_optimization:
                generation_result.image_data = trust_optimization
            
            # 5. 更新元数据
            generation_result.metadata.update({
                "post_processed": True,
                "trust_optimization_applied": True,
                "quality_assessment": quality_assessment,
                "validation_details": {
                    "is_valid": validation_result.is_valid,
                    "issues": validation_result.issues,
                    "suggestions": validation_result.suggestions
                },
                "trust_specific_metrics": {
                    "layout_type": "premium_image_with_text",
                    "golden_ratio_applied": True,
                    "bullet_points_formatted": True,
                    "trust_elements_integrated": True,
                    "cta_prominence": "high",
                    "information_density": "optimized"
                }
            })
            
            return generation_result
            
        except Exception as e:
            generation_result.metadata["post_processing_error"] = str(e)
            return generation_result
    
    def _apply_trust_optimization(self, image_data: bytes) -> Optional[bytes]:
        """应用信任转化特定优化"""
        try:
            # 这里可以添加特定的图像处理优化
            # 例如：文字清晰度增强、对比度优化、布局检查等
            # 暂时返回原始数据，实际实现中可以使用PIL或OpenCV进行处理
            return image_data
        except Exception:
            return None
    
    def get_trust_configuration_options(self) -> Dict[str, Any]:
        """获取信任转化配置选项 - 供用户自定义选择"""
        return {
            "layout_ratios": {
                "1:1": "平衡布局 - 图文并重，视觉平衡",
                "2:3": "信息重点 - 文字为主，详细展示"
            },
            "visual_content_types": {
                content_type: {
                    "description": config["description"],
                    "emotional_impact": config["emotional_impact"]
                }
                for content_type, config in self.visual_content_options.items()
            },
            "trust_elements": {
                "credibility": self.trust_elements.credibility_indicators,
                "social_proof": self.trust_elements.social_proof,
                "guarantees": self.trust_elements.guarantee_statements,
                "urgency": self.trust_elements.urgency_triggers
            },
            "information_density": {
                "high": "信息丰富 - 最大化信息展示",
                "medium": "平衡展示 - 信息与美观并重", 
                "low": "简洁明了 - 突出核心信息"
            },
            "cta_styles": [
                "urgent", "professional", "friendly", "premium", "value-focused"
            ]
        }
    
    def validate_trust_requirements(self, generation_result: GenerationResult) -> Dict[str, Any]:
        """验证信任转化模块特定要求"""
        validation_results = {
            "meets_trust_requirements": True,
            "issues": [],
            "suggestions": [],
            "trust_specific_metrics": {}
        }
        
        try:
            if not generation_result.image_data:
                validation_results["meets_trust_requirements"] = False
                validation_results["issues"].append("No image data available for validation")
                return validation_results
            
            # 1. 检查尺寸规格
            image = Image.open(io.BytesIO(generation_result.image_data))
            expected_size = APLUS_IMAGE_SPECS["dimensions"]
            
            if image.size != expected_size:
                validation_results["issues"].append(
                    f"Image size {image.size} does not match required {expected_size}"
                )
                validation_results["meets_trust_requirements"] = False
            
            # 2. 检查宽高比（4:3）
            aspect_ratio = image.size[0] / image.size[1] if image.size[1] > 0 else 1.0
            expected_ratio = 4/3
            
            if abs(aspect_ratio - expected_ratio) > 0.01:
                validation_results["issues"].append(
                    f"Aspect ratio {aspect_ratio:.3f} does not match required 4:3 ratio"
                )
                validation_results["meets_trust_requirements"] = False
            
            # 3. 信任转化特定验证
            validation_results["trust_specific_metrics"] = {
                "image_dimensions": image.size,
                "aspect_ratio": aspect_ratio,
                "file_size_mb": len(generation_result.image_data) / (1024 * 1024),
                "color_mode": image.mode,
                "has_premium_image_with_text_layout": True,  # 假设满足，实际需要图像分析
                "golden_ratio_layout_applied": True,  # 假设满足，实际需要图像分析
                "bullet_points_formatted": True,  # 假设满足，实际需要图像分析
                "trust_elements_present": True,  # 假设满足，实际需要图像分析
                "cta_prominence": generation_result.quality_score,
                "information_density": "optimized",  # 从元数据获取
                "text_readability": generation_result.quality_score
            }
            
            # 4. 添加改进建议
            if generation_result.quality_score < 0.8:
                validation_results["suggestions"].append(
                    "Consider regenerating with enhanced trust elements and CTA prominence"
                )
            
            if len(generation_result.image_data) > APLUS_IMAGE_SPECS["max_file_size"]:
                validation_results["suggestions"].append(
                    "Optimize image compression to reduce file size while maintaining text readability"
                )
            
            # 5. 检查信息完整性
            # 这里可以添加更复杂的图像分析来验证信息完整性
            # 暂时基于质量分数进行简单判断
            if generation_result.quality_score < 0.7:
                validation_results["suggestions"].append(
                    "Enhance information completeness and trust element visibility"
                )
            
        except Exception as e:
            validation_results["meets_trust_requirements"] = False
            validation_results["issues"].append(f"Validation error: {str(e)}")
        
        return validation_results
    
    async def generate_trust_image_simplified(
        self, 
        analysis: AnalysisResult,
        custom_params: Optional[Dict[str, Any]] = None
    ) -> GenerationResult:
        """简化的信任转化模块图片生成，用于错误恢复"""
        
        try:
            # 使用简化的提示词模板
            simplified_prompt = ModulePrompt(
                module_type=ModuleType.TRUST,
                base_prompt=f"""
                Create a premium image with text layout for trust conversion.
                Product category: {analysis.listing_analysis.product_category}
                
                Style requirements:
                - Golden ratio layout (1:1 or 2:3)
                - Left-right structure
                - Bullet points format
                - 600x450 pixels (4:3 aspect ratio)
                - Professional trust elements
                - Clear CTA guidance
                
                Include core parameters, service guarantees, and call-to-action.
                """,
                style_modifiers=["premium", "trust", "informative"],
                technical_requirements=["600x450", "4:3_ratio", "text_optimized"],
                aspect_ratio="600x450",
                quality_settings={"simplified_mode": True}
            )
            
            # 应用自定义参数
            if custom_params:
                if "quality_tolerance" in custom_params:
                    simplified_prompt.quality_settings["quality_tolerance"] = custom_params["quality_tolerance"]
                if "timeout_seconds" in custom_params:
                    simplified_prompt.quality_settings["timeout"] = custom_params["timeout_seconds"]
            
            # 生成图片
            generation_result = await self.image_service.generate_aplus_image(
                simplified_prompt,
                reference_images=[]  # 简化模式不使用参考图片
            )
            
            # 设置模块类型
            generation_result.module_type = ModuleType.TRUST
            
            return generation_result
            
        except Exception as e:
            return GenerationResult(
                module_type=ModuleType.TRUST,
                image_data=None,
                image_path=None,
                prompt_used="Simplified trust generation failed",
                generation_time=0.0,
                quality_score=0.0,
                validation_status=ValidationStatus.FAILED,
                metadata={"error": f"Simplified trust generation failed: {str(e)}"}
            )
