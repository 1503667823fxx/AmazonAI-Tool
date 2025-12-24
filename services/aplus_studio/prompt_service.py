"""
Prompt Generation Service for A+ Studio system.

This service generates customized prompts for each A+ module based on 
product analysis results and visual consistency requirements.
"""

from typing import List, Dict, Any
from .models import (
    AnalysisResult, ModuleType, ModulePrompt, ExtensionPrompts, 
    CarouselSlide, PROFESSIONAL_NAVIGATION_TERMS, GenerationResult,
    VisualStyle
)
from .config import MODULE_CONFIGS
from .visual_sop_processor import VisualSOPProcessor


class PromptGenerationService:
    """提示词生成服务 - 为每个模块生成定制化提示词"""
    
    def __init__(self):
        self.module_configs = MODULE_CONFIGS
        self.visual_sop_processor = VisualSOPProcessor()
        self._locked_palette = None
    
    def generate_identity_prompt(self, analysis):
        """生成身份代入模块提示词 - 强调北美中产使用产品的生活场景"""
        listing = analysis.listing_analysis
        visual = analysis.visual_style
        
        # 构建北美中产生活场景的详细描述
        lifestyle_elements = [
            "现代美式家居环境",
            "中产阶级品质生活标志",
            "家庭温馨氛围营造",
            "品味与实用性并重的空间设计"
        ]
        
        # 情感触发点整合
        emotional_triggers = listing.emotional_triggers if hasattr(listing, 'emotional_triggers') else []
        
        base_prompt = f"""
        创建一个600x450像素的Full Image全屏视效图片，展现北美中产家庭使用{listing.product_category}的理想生活场景。

        产品特征：{', '.join(listing.key_selling_points)}
        目标用户：{listing.target_demographics}
        情感触发：{', '.join(emotional_triggers)}
        
        北美中产生活场景要求：
        - {', '.join(lifestyle_elements)}
        - 黄金时段（Golden Hour）自然采光效果
        - 体现社会地位和生活品质的环境细节
        - 强调阶级场景代入而非单纯结果导向
        
        视觉风格：
        - 色调盘：{', '.join(visual.color_palette)}
        - 光照风格：{visual.lighting_style}
        - 构图规则：{', '.join(visual.composition_rules)}
        - 美学方向：{visual.aesthetic_direction}
        
        文字要素集成：
        - 一句价值观Slogan体现产品理念和生活态度
        - 一个信任背书短语增强品牌可信度
        - 文字与场景自然融合，不突兀
        
        整体目标：让消费者产生"这就是我想要的生活"的强烈认同感和向往
        """
        
        return ModulePrompt(
            module_type=ModuleType.IDENTITY,
            base_prompt=base_prompt,
            style_modifiers=[
                "golden_hour_lighting",
                "north_american_aesthetic", 
                "aspirational_lifestyle",
                "middle_class_setting",
                "emotional_resonance",
                "lifestyle_integration"
            ],
            technical_requirements=[
                "600x450_pixels",
                "full_image_layout",
                "text_overlay_support",
                "high_quality_rendering",
                "lifestyle_authenticity"
            ]
        )
    
    def generate_sensory_prompt(self, analysis):
        """生成感官解构模块提示词 - 突出3/4视角和材质细节"""
        listing = analysis.listing_analysis
        image_analysis = analysis.image_analysis
        
        # 工艺细节展示要素
        craftsmanship_details = [
            "金属拉丝纹理和光泽",
            "皮革缝线的精密工艺",
            "精密接口的配合度",
            "表面处理的质感细节",
            "结构连接的工程美学"
        ]
        
        base_prompt = f"""
        创建一个600x450像素的Premium Hotspots高级热点图，展示{listing.product_category}的材质细节和工业设计感。

        产品材质特征：{', '.join(image_analysis.material_types)}
        设计风格：{image_analysis.design_style}
        现有光照条件：{image_analysis.lighting_conditions}
        
        3/4视角展示要求：
        - 采用专业产品摄影的3/4视角（three-quarter angle）
        - 最佳展示产品的立体感和空间感
        - 突出产品的主要功能面和细节面
        - 避免正面平视，增强视觉深度
        
        材质细节渲染：
        - {', '.join(craftsmanship_details)}
        - 微观纹理的真实还原
        - 材质质感的触觉暗示
        
        光影处理要求：
        - 高反差明暗对比增强立体感
        - 阴影强调产品轮廓和结构
        - 专业摄影级别的光影效果
        - 突出材质的光泽和质感
        
        耐用性特征展示：
        - 强调Durability耐用性视觉暗示
        - 展示坚固的结构设计
        - 体现高品质制造标准
        - 传达长期使用价值
        
        整体目标：让消费者感受到产品的高品质、精工制造和专业级工艺水准
        """
        
        return ModulePrompt(
            module_type=ModuleType.SENSORY,
            base_prompt=base_prompt,
            style_modifiers=[
                "three_quarter_angle",
                "high_contrast_lighting",
                "material_emphasis",
                "premium_quality_focus",
                "craftsmanship_details",
                "durability_indicators"
            ],
            technical_requirements=[
                "600x450_pixels",
                "hotspots_layout",
                "detail_highlighting",
                "professional_photography_style",
                "material_texture_rendering",
                "shadow_emphasis"
            ]
        )
    
    def generate_extension_prompts(self, analysis):
        """生成多维延展模块的四维度轮播内容"""
        listing = analysis.listing_analysis
        
        # 从专业导航术语中选择合适的标签
        nav_terms = PROFESSIONAL_NAVIGATION_TERMS
        
        # Lifestyle场景 - 典型美国生活场景
        lifestyle_slide = CarouselSlide(
            slide_type="lifestyle",
            title="Real World Application",
            content_focus="典型美国生活场景中的产品使用",
            navigation_label=nav_terms["lifestyle"][0],  # "Field Tested"
            prompt=f"""
            创建600x450像素的Lifestyle场景图片，展示{listing.product_category}在典型美国家庭生活中的自然使用场景。
            
            美国生活场景要求：
            - 真实的美国家庭环境（郊区住宅、现代公寓等）
            - 体现美式生活方式和价值观
            - 自然的产品使用状态，非摆拍感
            - 强调便利性和实用性在日常生活中的体现
            - 展现产品融入美国家庭生活的和谐感
            
            场景细节：
            - 符合目标用户群体：{listing.target_demographics}
            - 体现产品核心价值：{', '.join(listing.key_selling_points[:2])}
            - 生活化的使用环境和时机
            
            专业导航标签：{nav_terms["lifestyle"][0]}
            """
        )
        
        # Pain Point解决方案 - 针对竞品槽点提供解决方案展示
        pain_point_slide = CarouselSlide(
            slide_type="pain_point",
            title="Problem Solution",
            content_focus="针对竞品槽点的解决方案展示",
            navigation_label=nav_terms["pain_point"][1],  # "Smart Solution"
            prompt=f"""
            创建600x450像素的Pain Point解决方案图片，展示{listing.product_category}如何解决用户痛点。
            
            解决方案展示重点：
            - 对比传统解决方案的不足和局限性
            - 突出产品的创新解决方案和差异化优势
            - 视觉化展示改进效果和用户体验提升
            - 强调竞争优势：{', '.join(listing.competitive_advantages)}
            
            视觉对比策略：
            - 问题场景 vs 解决方案场景
            - 传统方式 vs 创新方式
            - 痛点体验 vs 优化体验
            
            专业导航标签：{nav_terms["pain_point"][1]}
            """
        )
        
        # Extreme Performance - 展示压力测试场景
        performance_slide = CarouselSlide(
            slide_type="extreme_performance", 
            title="Performance Testing",
            content_focus="压力测试和极限性能展示",
            navigation_label=nav_terms["performance"][0],  # "The Specs"
            prompt=f"""
            创建600x450像素的Extreme Performance图片，展示{listing.product_category}的极限性能和耐用性。
            
            压力测试场景设计：
            - 极限使用条件和环境挑战
            - 性能数据的可视化展示
            - 耐久性验证的测试场景
            - 技术规格的直观体现
            
            性能展示要素：
            - 核心技术参数：{', '.join(f"{k}: {v}" for k, v in list(listing.technical_specifications.items())[:3])}
            - 压力测试的真实场景
            - 性能极限的视觉化表达
            - 可靠性和稳定性的证明
            
            专业导航标签：{nav_terms["performance"][0]}
            """
        )
        
        # Inside Out细节 - 展示结构工艺细节和保修承诺
        inside_out_slide = CarouselSlide(
            slide_type="inside_out",
            title="Quality Craftsmanship", 
            content_focus="内部结构工艺和保修承诺",
            navigation_label=nav_terms["inside_out"][0],  # "Inside Look"
            prompt=f"""
            创建600x450像素的Inside Out图片，展示{listing.product_category}的内部结构和制造工艺。
            
            内部结构展示：
            - 产品内部构造的剖析视图
            - 制造工艺细节的特写展示
            - 质量控制标准的可视化
            - 精密制造过程的体现
            
            工艺品质要素：
            - 材料选择的高标准
            - 装配工艺的精密度
            - 质检流程的严格性
            - 品质保证的承诺展示
            
            保修服务承诺：
            - 质保期限和覆盖范围
            - 售后服务的专业性
            - 品牌信誉的背书
            
            专业导航标签：{nav_terms["inside_out"][0]}
            """
        )
        
        return ExtensionPrompts(
            lifestyle_slide=lifestyle_slide,
            pain_point_slide=pain_point_slide,
            performance_slide=performance_slide,
            inside_out_slide=inside_out_slide
        )
    
    def generate_trust_prompt(self, analysis):
        """生成信任转化模块提示词 - 优化信息密度和CTA引导"""
        listing = analysis.listing_analysis
        
        # 构建核心参数汇总
        tech_specs = listing.technical_specifications
        core_params = list(tech_specs.items())[:5]  # 取前5个核心参数
        
        # 服务保障要素
        service_guarantees = [
            "产品质量保证",
            "售后服务承诺", 
            "退换货政策",
            "技术支持服务",
            "品牌信誉背书"
        ]
        
        # CTA引导要素
        cta_elements = [
            "购买决策支持信息",
            "立即行动的激励因素",
            "风险降低的保证措施",
            "价值主张的最终强化"
        ]
        
        base_prompt = f"""
        创建一个600x450像素的Premium Image with Text布局，提供完整的{listing.product_category}信息和购买引导。

        黄金比例布局设计：
        - 采用黄金比例1:1或2:3的左右结构分配
        - 左侧视觉区域：人与产品合影或产品全家福配件图
        - 右侧信息区域：清单式Bullet Points信息排版
        - 视觉与文字的平衡协调
        
        核心信息内容组织：
        
        1. 核心参数汇总：
        {chr(10).join([f"   • {k}: {v}" for k, v in core_params])}
        
        2. 服务保障展示：
        {chr(10).join([f"   • {guarantee}" for guarantee in service_guarantees])}
        
        3. CTA引导要素：
        {chr(10).join([f"   • {cta}" for cta in cta_elements])}
        
        信息密度优化策略：
        - 分段组织提高信息易读性
        - 加粗标题突出关键信息点
        - 视觉层次清晰的信息架构
        - 合理的留白和间距设计
        - 重要信息的视觉强调处理
        
        视觉区域内容：
        - 展示产品在真实使用环境中的效果
        - 人物与产品的自然互动场景
        - 产品全系列或配件的完整展示
        - 传达品质感和专业性的视觉元素
        
        购买引导优化：
        - 建立信任感的视觉和文字元素
        - 降低购买风险的保证信息
        - 强化产品价值的关键信息
        - 促进立即行动的激励因素
        
        整体目标：提供完整信息支持购买决策，建立强烈的信任感和购买欲望
        """
        
        return ModulePrompt(
            module_type=ModuleType.TRUST,
            base_prompt=base_prompt,
            style_modifiers=[
                "golden_ratio_layout",
                "bullet_points_format",
                "information_hierarchy",
                "trust_building_elements",
                "cta_optimization",
                "readability_enhancement"
            ],
            technical_requirements=[
                "600x450_pixels",
                "image_with_text_layout",
                "readable_typography",
                "cta_integration",
                "information_density_optimization",
                "visual_text_balance"
            ]
        )
    
    def apply_visual_consistency(self, prompts, visual_style):
        """应用视觉连贯性到所有提示词 - 确保模块间视觉风格统一"""
        
        # 构建详细的视觉连贯性指导
        consistency_additions = f"""
        
        === 视觉连贯性协议 (Visual SOP) ===
        
        色调盘锁定：
        - 主色调：{', '.join(visual_style.color_palette[:3])}
        - 辅助色调：{', '.join(visual_style.color_palette[3:] if len(visual_style.color_palette) > 3 else ['保持主色调和谐'])}
        - 色彩关系：保持一致或渐变关系，避免突兀对比
        
        光照风格统一：
        - 光照类型：{visual_style.lighting_style}
        - 光线方向和强度保持一致性
        - 阴影处理风格统一
        - 色温保持协调
        
        构图规则遵循：
        - 构图原则：{', '.join(visual_style.composition_rules)}
        - 视觉重心的一致性处理
        - 元素布局的协调性
        
        美学方向统一：
        - 整体美学：{visual_style.aesthetic_direction}
        - 风格调性保持一致
        - 视觉语言的统一性
        
        一致性检查要点：
        {chr(10).join([f"• {guideline}: {detail}" for guideline, detail in visual_style.consistency_guidelines.items()])}
        
        风格冲突预防：
        - 避免不同模块出现风格不一致
        - 确保从模块1到模块4的视觉连贯性
        - 维持品牌视觉识别的统一性
        - 保证整体A+页面的专业性和协调性
        """
        
        enhanced_prompts = []
        for prompt in prompts:
            # 为每个模块添加特定的一致性要求
            module_specific_consistency = self._get_module_specific_consistency(prompt.module_type)
            
            enhanced_prompt = ModulePrompt(
                module_type=prompt.module_type,
                base_prompt=prompt.base_prompt + consistency_additions + module_specific_consistency,
                style_modifiers=prompt.style_modifiers + [
                    "visual_consistency", 
                    "style_coherence",
                    "brand_unity",
                    "professional_coordination"
                ],
                technical_requirements=prompt.technical_requirements + [
                    "style_coherence",
                    "visual_harmony",
                    "brand_consistency"
                ],
                aspect_ratio=prompt.aspect_ratio,
                quality_settings=prompt.quality_settings
            )
            enhanced_prompts.append(enhanced_prompt)
        
        return enhanced_prompts
    
    def _get_module_specific_consistency(self, module_type):
        """获取模块特定的一致性要求"""
        consistency_map = {
            ModuleType.IDENTITY: """
            
            身份代入模块一致性要求：
            - 与其他模块保持相同的色调基础
            - 光照风格需与感官解构模块协调
            - 生活场景的真实感与信任转化模块呼应
            """,
            
            ModuleType.SENSORY: """
            
            感官解构模块一致性要求：
            - 材质展示的光影与身份代入模块光照协调
            - 产品细节的色彩与整体色调盘保持一致
            - 专业摄影风格与多维延展模块统一
            """,
            
            ModuleType.EXTENSION: """
            
            多维延展模块一致性要求：
            - 四张轮播图之间保持视觉连贯性
            - 与前两个模块的色调和光照风格保持一致
            - 场景设置与身份代入模块的环境协调
            """,
            
            ModuleType.TRUST: """
            
            信任转化模块一致性要求：
            - 图文布局的视觉风格与前三个模块协调
            - 产品展示角度与感官解构模块呼应
            - 整体色调作为四个模块的视觉总结
            """
        }
        
        return consistency_map.get(module_type, "")
    
    def generate_all_module_prompts(self, analysis):
        """生成所有模块的提示词"""
        prompts = {}
        
        # 初始化视觉连贯性协议
        self._locked_palette = self.visual_sop_processor.lock_color_palette(analysis)
        
        # 生成各模块基础提示词
        prompts[ModuleType.IDENTITY] = self.generate_identity_prompt(analysis)
        prompts[ModuleType.SENSORY] = self.generate_sensory_prompt(analysis)
        prompts[ModuleType.TRUST] = self.generate_trust_prompt(analysis)
        
        # Extension模块需要特殊处理（四张图片）
        extension_prompts = self.generate_extension_prompts(analysis)
        # 这里暂时只返回第一张作为代表，实际实现中需要处理四张图片
        prompts[ModuleType.EXTENSION] = ModulePrompt(
            module_type=ModuleType.EXTENSION,
            base_prompt=extension_prompts.lifestyle_slide.prompt,
            style_modifiers=["carousel_format", "multi_dimensional"],
            technical_requirements=["600x450_pixels", "four_slide_carousel"]
        )
        
        # 应用视觉连贯性
        prompt_list = list(prompts.values())
        enhanced_prompts = self.apply_visual_consistency(prompt_list, analysis.visual_style)
        
        # 重新组织为字典
        result = {}
        for i, module_type in enumerate([ModuleType.IDENTITY, ModuleType.SENSORY, ModuleType.TRUST, ModuleType.EXTENSION]):
            result[module_type] = enhanced_prompts[i]
        
        return result
    
    def generate_coherent_module_prompt(self, 
                                      target_module,
                                      analysis,
                                      existing_results=None):
        """生成与现有模块连贯的提示词"""
        
        # 如果没有锁定的色调盘，先创建一个
        if self._locked_palette is None:
            self._locked_palette = self.visual_sop_processor.lock_color_palette(analysis)
        
        # 获取连贯性要求
        coherence_requirements = self.visual_sop_processor.ensure_module_coherence(
            target_module, existing_results or {}, self._locked_palette
        )
        
        # 生成基础提示词
        if target_module == ModuleType.IDENTITY:
            base_prompt = self.generate_identity_prompt(analysis)
        elif target_module == ModuleType.SENSORY:
            base_prompt = self.generate_sensory_prompt(analysis)
        elif target_module == ModuleType.TRUST:
            base_prompt = self.generate_trust_prompt(analysis)
        elif target_module == ModuleType.EXTENSION:
            extension_prompts = self.generate_extension_prompts(analysis)
            base_prompt = ModulePrompt(
                module_type=ModuleType.EXTENSION,
                base_prompt=extension_prompts.lifestyle_slide.prompt,
                style_modifiers=["carousel_format", "multi_dimensional"],
                technical_requirements=["600x450_pixels", "four_slide_carousel"]
            )
        else:
            raise ValueError(f"Unknown module type: {target_module}")
        
        # 应用连贯性约束
        coherent_prompt = self._apply_coherence_constraints(base_prompt, coherence_requirements)
        
        return coherent_prompt
    
    def validate_visual_consistency(self, module_results, visual_style=None):
        """验证模块间的视觉一致性"""
        if self._locked_palette is None:
            return {
                'error': 'No locked palette available. Generate analysis first.',
                'consistency_score': 0.0
            }
        
        consistency_metrics = self.visual_sop_processor.validate_visual_consistency(
            module_results, self._locked_palette
        )
        
        return {
            'consistency_metrics': consistency_metrics,
            'overall_score': consistency_metrics.overall_coherence_score,
            'conflicts': consistency_metrics.detected_conflicts,
            'suggestions': consistency_metrics.improvement_suggestions,
            'is_consistent': consistency_metrics.overall_coherence_score >= 0.7
        }
    
    def detect_and_resolve_conflicts(self, module_results):
        """检测并提供解决风格冲突的建议"""
        if self._locked_palette is None:
            return ['No visual consistency baseline established']
        
        conflicts = self.visual_sop_processor.detect_style_conflicts(
            module_results, self._locked_palette
        )
        
        return conflicts
    
    def get_locked_palette_info(self):
        """获取当前锁定的色调盘信息"""
        return self._locked_palette or {}
    
    def _apply_coherence_constraints(self, 
                                   base_prompt, 
                                   coherence_requirements):
        """应用连贯性约束到提示词"""
        
        # 构建连贯性约束文本
        coherence_text = "\n\n=== 视觉连贯性约束 ===\n"
        
        # 色彩约束
        color_constraints = coherence_requirements.get('color_constraints', {})
        if color_constraints:
            coherence_text += "\n色彩连贯性要求：\n"
            if 'target_color_temperature' in color_constraints:
                temp = color_constraints['target_color_temperature']
                tolerance = color_constraints.get('temperature_tolerance', 500)
                coherence_text += f"- 色温范围：{temp-tolerance:.0f}K - {temp+tolerance:.0f}K\n"
            
            if 'harmony_range' in color_constraints:
                min_h, max_h = color_constraints['harmony_range']
                coherence_text += f"- 色彩和谐度：{min_h:.2f} - {max_h:.2f}\n"
        
        # 光照约束
        lighting_constraints = coherence_requirements.get('lighting_constraints', {})
        if lighting_constraints:
            coherence_text += "\n光照连贯性要求：\n"
            if 'target_brightness_distribution' in lighting_constraints:
                brightness = lighting_constraints['target_brightness_distribution']
                coherence_text += f"- 亮度分布：低{brightness['low']:.2f} 中{brightness['mid']:.2f} 高{brightness['high']:.2f}\n"
        
        # 构图约束
        composition_constraints = coherence_requirements.get('composition_constraints', {})
        if composition_constraints:
            coherence_text += "\n构图连贯性要求：\n"
            if 'target_saturation_distribution' in composition_constraints:
                saturation = composition_constraints['target_saturation_distribution']
                coherence_text += f"- 饱和度分布：低{saturation['low']:.2f} 中{saturation['mid']:.2f} 高{saturation['high']:.2f}\n"
        
        # 模块特定调整
        module_adjustments = coherence_requirements.get('module_specific_adjustments', {})
        if module_adjustments:
            coherence_text += "\n模块特定要求：\n"
            for key, value in module_adjustments.items():
                coherence_text += f"- {key}: {value}\n"
        
        # 创建增强的提示词
        enhanced_prompt = ModulePrompt(
            module_type=base_prompt.module_type,
            base_prompt=base_prompt.base_prompt + coherence_text,
            style_modifiers=base_prompt.style_modifiers + [
                "visual_coherence_enforced",
                "consistency_constraints_applied"
            ],
            technical_requirements=base_prompt.technical_requirements + [
                "coherence_validation",
                "style_consistency_check"
            ],
            aspect_ratio=base_prompt.aspect_ratio,
            quality_settings=base_prompt.quality_settings
        )
        
        return enhanced_prompt