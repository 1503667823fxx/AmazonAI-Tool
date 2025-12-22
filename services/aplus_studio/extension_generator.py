"""
Extension Module Generator for A+ Studio system.

This module implements the Extension (多维延展) module generator that creates
Premium Navigation Carousel with four dimensional slides: Lifestyle, Pain Point,
Extreme Performance, and Inside Out, each with professional navigation terminology.
"""

from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from PIL import Image
import io
import asyncio

from .models import (
    AnalysisResult, ModulePrompt, GenerationResult, ModuleType,
    ValidationStatus, APLUS_IMAGE_SPECS, CarouselSlide, ExtensionPrompts,
    PROFESSIONAL_NAVIGATION_TERMS
)
from .image_service import APlusImageService
from .prompt_service import PromptGenerationService


@dataclass
class LifestyleScenario:
    """典型美国生活场景配置"""
    setting: str
    activities: List[str]
    social_context: str
    emotional_tone: str
    visual_elements: List[str]


@dataclass
class PainPointSolution:
    """竞品槽点解决方案配置"""
    common_problems: List[str]
    solution_approach: str
    demonstration_method: str
    benefit_emphasis: List[str]


@dataclass
class PerformanceTest:
    """极限性能测试配置"""
    test_scenarios: List[str]
    stress_conditions: List[str]
    performance_metrics: List[str]
    durability_indicators: List[str]


@dataclass
class InsideOutDetails:
    """结构工艺细节配置"""
    internal_structure: List[str]
    craftsmanship_features: List[str]
    quality_assurance: List[str]
    warranty_highlights: List[str]


class ExtensionModuleGenerator:
    """多维延展模块生成器 - 实现Premium Navigation Carousel四张轮播图生成"""
    
    def __init__(self, image_service: APlusImageService, prompt_service: PromptGenerationService):
        self.image_service = image_service
        self.prompt_service = prompt_service
        
        # 典型美国生活场景配置
        self.lifestyle_scenarios = {
            "home": LifestyleScenario(
                setting="现代美式家庭环境",
                activities=["家庭聚餐", "休闲娱乐", "日常生活", "朋友聚会"],
                social_context="中产家庭的品质生活",
                emotional_tone="温馨、舒适、有归属感",
                visual_elements=["开放式厨房", "舒适客厅", "家庭成员互动", "宠物陪伴", "自然光线"]
            ),
            "outdoor": LifestyleScenario(
                setting="美式后院或户外空间",
                activities=["BBQ聚会", "户外运动", "园艺活动", "休闲时光"],
                social_context="邻里社交和家庭活动",
                emotional_tone="自由、活力、享受自然",
                visual_elements=["绿色草坪", "户外家具", "阳光明媚", "社交聚会", "运动设备"]
            ),
            "workplace": LifestyleScenario(
                setting="现代办公环境或居家办公",
                activities=["专业工作", "视频会议", "创意思考", "效率提升"],
                social_context="职业成功和工作效率",
                emotional_tone="专业、高效、有成就感",
                visual_elements=["现代办公桌", "专业设备", "整洁环境", "科技感", "专注状态"]
            ),
            "leisure": LifestyleScenario(
                setting="休闲娱乐场所",
                activities=["健身运动", "兴趣爱好", "学习充电", "放松休息"],
                social_context="个人成长和生活品质",
                emotional_tone="积极、向上、自我实现",
                visual_elements=["健身房", "图书角", "音乐空间", "艺术作品", "个人收藏"]
            )
        }
        
        # 竞品槽点解决方案配置
        self.pain_point_solutions = {
            "quality_issues": PainPointSolution(
                common_problems=["易损坏", "质量不稳定", "使用寿命短", "材料劣质"],
                solution_approach="高品质材料和工艺展示",
                demonstration_method="对比展示和质量测试",
                benefit_emphasis=["持久耐用", "品质保证", "长期价值", "可靠性能"]
            ),
            "usability_problems": PainPointSolution(
                common_problems=["操作复杂", "使用不便", "学习成本高", "功能缺失"],
                solution_approach="简化设计和人性化功能",
                demonstration_method="使用流程演示和功能对比",
                benefit_emphasis=["简单易用", "直观操作", "快速上手", "功能完善"]
            ),
            "performance_gaps": PainPointSolution(
                common_problems=["性能不足", "效率低下", "功能单一", "适应性差"],
                solution_approach="性能优势和多功能展示",
                demonstration_method="性能测试和功能演示",
                benefit_emphasis=["卓越性能", "高效便捷", "多功能集成", "适应性强"]
            ),
            "value_concerns": PainPointSolution(
                common_problems=["性价比低", "隐藏成本", "维护费用高", "升级困难"],
                solution_approach="价值优势和成本效益分析",
                demonstration_method="成本对比和价值展示",
                benefit_emphasis=["超值性价比", "透明定价", "低维护成本", "长期投资"]
            )
        }
        
        # 极限性能测试配置
        self.performance_tests = {
            "durability": PerformanceTest(
                test_scenarios=["跌落测试", "压力测试", "温度测试", "湿度测试"],
                stress_conditions=["极端温度", "高湿环境", "重压负载", "频繁使用"],
                performance_metrics=["抗冲击性", "承重能力", "温度适应", "防水等级"],
                durability_indicators=["使用寿命", "故障率", "维护频率", "性能稳定性"]
            ),
            "efficiency": PerformanceTest(
                test_scenarios=["速度测试", "精度测试", "连续运行", "多任务处理"],
                stress_conditions=["高负载", "长时间运行", "多并发", "复杂任务"],
                performance_metrics=["处理速度", "精确度", "稳定性", "响应时间"],
                durability_indicators=["效率保持", "性能衰减", "可靠性", "一致性"]
            ),
            "compatibility": PerformanceTest(
                test_scenarios=["兼容性测试", "适配测试", "集成测试", "环境测试"],
                stress_conditions=["不同环境", "多种配置", "各类设备", "复杂场景"],
                performance_metrics=["兼容范围", "适配程度", "集成效果", "稳定运行"],
                durability_indicators=["通用性", "适应性", "扩展性", "未来兼容"]
            )
        }
        
        # 结构工艺细节配置
        self.inside_out_details = {
            "internal_structure": [
                "精密内部结构设计",
                "优化的组件布局",
                "高效的散热系统",
                "模块化设计理念",
                "智能电路设计"
            ],
            "craftsmanship": [
                "精密制造工艺",
                "严格质量控制",
                "专业装配技术",
                "表面处理工艺",
                "细节打磨完善"
            ],
            "quality_assurance": [
                "多重质量检测",
                "严格测试标准",
                "品质认证体系",
                "持续改进机制",
                "用户反馈优化"
            ],
            "warranty": [
                "全面质保服务",
                "快速响应支持",
                "专业维修网络",
                "延保服务选项",
                "终身技术支持"
            ]
        }
    
    async def generate_extension_carousel(
        self, 
        analysis: AnalysisResult,
        custom_params: Optional[Dict[str, Any]] = None
    ) -> List[GenerationResult]:
        """生成多维延展模块的四张轮播图"""
        
        try:
            # 1. 构建四个维度的提示词
            extension_prompts = self._build_extension_prompts(analysis, custom_params)
            
            # 2. 并行生成四张轮播图
            generation_tasks = []
            for slide in extension_prompts.get_all_slides():
                task = self._generate_single_slide(slide, analysis)
                generation_tasks.append(task)
            
            # 3. 等待所有生成任务完成
            results = await asyncio.gather(*generation_tasks, return_exceptions=True)
            
            # 4. 处理生成结果
            carousel_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    # 处理异常情况
                    error_result = GenerationResult(
                        module_type=ModuleType.EXTENSION,
                        image_data=None,
                        image_path=None,
                        prompt_used="",
                        generation_time=0.0,
                        quality_score=0.0,
                        validation_status=ValidationStatus.FAILED,
                        metadata={
                            "error": f"Slide {i+1} generation failed: {str(result)}",
                            "slide_type": extension_prompts.get_all_slides()[i].slide_type
                        }
                    )
                    carousel_results.append(error_result)
                else:
                    carousel_results.append(result)
            
            return carousel_results
            
        except Exception as e:
            # 返回四个失败结果
            error_results = []
            slide_types = ["lifestyle", "pain_point", "extreme_performance", "inside_out"]
            
            for slide_type in slide_types:
                error_result = GenerationResult(
                    module_type=ModuleType.EXTENSION,
                    image_data=None,
                    image_path=None,
                    prompt_used="",
                    generation_time=0.0,
                    quality_score=0.0,
                    validation_status=ValidationStatus.FAILED,
                    metadata={
                        "error": f"Extension carousel generation failed: {str(e)}",
                        "slide_type": slide_type
                    }
                )
                error_results.append(error_result)
            
            return error_results
    
    def _build_extension_prompts(
        self, 
        analysis: AnalysisResult, 
        custom_params: Optional[Dict[str, Any]] = None
    ) -> ExtensionPrompts:
        """构建四个维度的轮播图提示词"""
        
        listing = analysis.listing_analysis
        visual = analysis.visual_style
        
        # 1. Lifestyle场景轮播图
        lifestyle_scenario = self._select_lifestyle_scenario(listing.product_category, listing.target_demographics)
        lifestyle_slide = CarouselSlide(
            slide_type="lifestyle",
            title="Lifestyle - 典型美国生活场景",
            content_focus=lifestyle_scenario.setting,
            navigation_label=self._select_navigation_term("lifestyle"),
            prompt=self._build_lifestyle_prompt(analysis, lifestyle_scenario, custom_params)
        )
        
        # 2. Pain Point解决方案轮播图
        pain_solution = self._identify_pain_point_solution(listing.competitive_advantages)
        pain_point_slide = CarouselSlide(
            slide_type="pain_point",
            title="Pain Point - 竞品槽点解决方案",
            content_focus=pain_solution.solution_approach,
            navigation_label=self._select_navigation_term("pain_point"),
            prompt=self._build_pain_point_prompt(analysis, pain_solution, custom_params)
        )
        
        # 3. Extreme Performance压力测试轮播图
        performance_test = self._select_performance_test(listing.key_selling_points)
        performance_slide = CarouselSlide(
            slide_type="extreme_performance",
            title="Extreme Performance - 压力测试场景",
            content_focus=performance_test.test_scenarios[0],
            navigation_label=self._select_navigation_term("performance"),
            prompt=self._build_performance_prompt(analysis, performance_test, custom_params)
        )
        
        # 4. Inside Out结构工艺轮播图
        inside_out_slide = CarouselSlide(
            slide_type="inside_out",
            title="Inside Out - 结构工艺细节",
            content_focus="内部结构和工艺展示",
            navigation_label=self._select_navigation_term("inside_out"),
            prompt=self._build_inside_out_prompt(analysis, custom_params)
        )
        
        return ExtensionPrompts(
            lifestyle_slide=lifestyle_slide,
            pain_point_slide=pain_point_slide,
            performance_slide=performance_slide,
            inside_out_slide=inside_out_slide
        )
    
    def _select_lifestyle_scenario(self, product_category: str, target_demographics: str) -> LifestyleScenario:
        """根据产品类别和目标用户选择生活场景"""
        category_lower = product_category.lower()
        demographics_lower = target_demographics.lower()
        
        if any(cat in category_lower for cat in ['home', '家居', 'kitchen', '厨房', 'furniture', '家具']):
            return self.lifestyle_scenarios["home"]
        elif any(cat in category_lower for cat in ['outdoor', '户外', 'sports', '运动', 'garden', '园艺']):
            return self.lifestyle_scenarios["outdoor"]
        elif any(cat in category_lower for cat in ['office', '办公', 'work', '工作', 'business', '商务']):
            return self.lifestyle_scenarios["workplace"]
        elif any(demo in demographics_lower for demo in ['professional', '专业', 'business', '商务']):
            return self.lifestyle_scenarios["workplace"]
        elif any(demo in demographics_lower for demo in ['family', '家庭', 'parent', '父母']):
            return self.lifestyle_scenarios["home"]
        else:
            return self.lifestyle_scenarios["leisure"]  # 默认休闲场景
    
    def _identify_pain_point_solution(self, competitive_advantages: List[str]) -> PainPointSolution:
        """根据竞争优势识别主要解决的痛点"""
        advantages_text = " ".join(competitive_advantages).lower()
        
        if any(quality in advantages_text for quality in ['quality', '品质', 'durable', '耐用', 'reliable', '可靠']):
            return self.pain_point_solutions["quality_issues"]
        elif any(usability in advantages_text for usability in ['easy', '简单', 'convenient', '便利', 'user-friendly', '易用']):
            return self.pain_point_solutions["usability_problems"]
        elif any(performance in advantages_text for performance in ['fast', '快速', 'efficient', '高效', 'powerful', '强大']):
            return self.pain_point_solutions["performance_gaps"]
        elif any(value in advantages_text for value in ['affordable', '实惠', 'value', '价值', 'cost-effective', '性价比']):
            return self.pain_point_solutions["value_concerns"]
        else:
            return self.pain_point_solutions["quality_issues"]  # 默认质量问题
    
    def _select_performance_test(self, key_selling_points: List[str]) -> PerformanceTest:
        """根据核心卖点选择性能测试类型"""
        selling_points_text = " ".join(key_selling_points).lower()
        
        if any(durability in selling_points_text for durability in ['durable', '耐用', 'strong', '坚固', 'tough', '强韧']):
            return self.performance_tests["durability"]
        elif any(efficiency in selling_points_text for efficiency in ['fast', '快速', 'efficient', '高效', 'quick', '迅速']):
            return self.performance_tests["efficiency"]
        elif any(compatibility in selling_points_text for compatibility in ['compatible', '兼容', 'universal', '通用', 'versatile', '多用途']):
            return self.performance_tests["compatibility"]
        else:
            return self.performance_tests["durability"]  # 默认耐用性测试
    
    def _select_navigation_term(self, slide_type: str) -> str:
        """选择专业导航术语"""
        terms = PROFESSIONAL_NAVIGATION_TERMS.get(slide_type, ["Professional"])
        # 选择第一个术语，实际应用中可以根据产品特征智能选择
        return terms[0]
    
    def _build_lifestyle_prompt(
        self, 
        analysis: AnalysisResult, 
        scenario: LifestyleScenario,
        custom_params: Optional[Dict[str, Any]] = None
    ) -> str:
        """构建Lifestyle场景提示词"""
        
        listing = analysis.listing_analysis
        visual = analysis.visual_style
        
        # 应用自定义参数
        custom_adjustments = ""
        if custom_params and "lifestyle_focus" in custom_params:
            custom_adjustments = f"\n场景重点：{custom_params['lifestyle_focus']}"
        
        prompt = f"""
        创建一个600x450像素的Premium Navigation Carousel轮播图 - Lifestyle维度展示。

        === 产品信息 ===
        产品类别：{listing.product_category}
        核心卖点：{', '.join(listing.key_selling_points)}
        目标用户：{listing.target_demographics}

        === Lifestyle场景设计 ===
        场景设置：{scenario.setting}
        主要活动：{', '.join(scenario.activities)}
        社会背景：{scenario.social_context}
        情感基调：{scenario.emotional_tone}
        视觉元素：{', '.join(scenario.visual_elements)}

        === 典型美国生活场景要求 ===
        - 展现真实的美式家庭生活场景
        - 体现中产阶级的生活品质和价值观
        - 突出产品在日常生活中的自然融入
        - 营造温馨、舒适、有品质感的氛围
        - 展示多元化的家庭成员和生活方式

        === 视觉风格 ===
        色调盘：{', '.join(visual.color_palette)}
        光照风格：{visual.lighting_style}
        构图规则：{', '.join(visual.composition_rules)}
        美学方向：{visual.aesthetic_direction}

        === 导航标签集成 ===
        专业术语："{self._select_navigation_term('lifestyle')}"
        标签位置：图片下方或角落，清晰可读
        字体风格：现代、专业、与整体设计协调

        === 技术规格 ===
        - 尺寸：600x450像素（4:3宽高比）
        - 格式：高质量PNG，适合轮播展示
        - 色彩空间：sRGB
        - 分辨率：最低72 DPI
        - 文件大小：5MB以内

        === 核心目标 ===
        让消费者看到产品如何完美融入他们向往的美式生活方式，建立情感共鸣和生活方式认同。

        {custom_adjustments}
        """
        
        return prompt.strip()
    
    def _build_pain_point_prompt(
        self, 
        analysis: AnalysisResult, 
        solution: PainPointSolution,
        custom_params: Optional[Dict[str, Any]] = None
    ) -> str:
        """构建Pain Point解决方案提示词"""
        
        listing = analysis.listing_analysis
        visual = analysis.visual_style
        
        # 应用自定义参数
        custom_adjustments = ""
        if custom_params and "pain_point_focus" in custom_params:
            custom_adjustments = f"\n解决方案重点：{custom_params['pain_point_focus']}"
        
        prompt = f"""
        创建一个600x450像素的Premium Navigation Carousel轮播图 - Pain Point解决方案维度展示。

        === 产品信息 ===
        产品类别：{listing.product_category}
        竞争优势：{', '.join(listing.competitive_advantages)}
        核心卖点：{', '.join(listing.key_selling_points)}

        === 痛点解决方案设计 ===
        常见问题：{', '.join(solution.common_problems)}
        解决方案：{solution.solution_approach}
        展示方法：{solution.demonstration_method}
        优势强调：{', '.join(solution.benefit_emphasis)}

        === 竞品槽点针对性展示 ===
        - 明确展示竞品的常见问题和不足
        - 突出本产品的解决方案和优势
        - 使用对比展示或前后对比的方式
        - 强调用户痛点的彻底解决
        - 体现产品的创新性和实用性

        === 视觉表现要求 ===
        - 清晰的问题-解决方案对比
        - 直观的功能演示或效果展示
        - 专业的产品特写和细节展现
        - 用户使用场景的真实还原
        - 突出产品优势的视觉强调

        === 视觉风格 ===
        色调盘：{', '.join(visual.color_palette)}
        光照风格：{visual.lighting_style}
        构图规则：{', '.join(visual.composition_rules)}
        美学方向：{visual.aesthetic_direction}

        === 导航标签集成 ===
        专业术语："{self._select_navigation_term('pain_point')}"
        标签位置：图片下方或角落，清晰可读
        字体风格：现代、专业、与整体设计协调

        === 技术规格 ===
        - 尺寸：600x450像素（4:3宽高比）
        - 格式：高质量PNG，适合轮播展示
        - 色彩空间：sRGB
        - 分辨率：最低72 DPI
        - 文件大小：5MB以内

        === 核心目标 ===
        让消费者清楚地看到产品如何解决他们的实际问题，建立对产品解决方案的信任和购买信心。

        {custom_adjustments}
        """
        
        return prompt.strip()
    
    def _build_performance_prompt(
        self, 
        analysis: AnalysisResult, 
        test: PerformanceTest,
        custom_params: Optional[Dict[str, Any]] = None
    ) -> str:
        """构建Extreme Performance压力测试提示词"""
        
        listing = analysis.listing_analysis
        visual = analysis.visual_style
        
        # 应用自定义参数
        custom_adjustments = ""
        if custom_params and "performance_focus" in custom_params:
            custom_adjustments = f"\n性能重点：{custom_params['performance_focus']}"
        
        prompt = f"""
        创建一个600x450像素的Premium Navigation Carousel轮播图 - Extreme Performance压力测试维度展示。

        === 产品信息 ===
        产品类别：{listing.product_category}
        核心卖点：{', '.join(listing.key_selling_points)}
        技术规格：{', '.join(f"{k}: {v}" for k, v in list(listing.technical_specifications.items())[:3])}

        === 极限性能测试设计 ===
        测试场景：{', '.join(test.test_scenarios)}
        压力条件：{', '.join(test.stress_conditions)}
        性能指标：{', '.join(test.performance_metrics)}
        耐用性指标：{', '.join(test.durability_indicators)}

        === 压力测试场景展示 ===
        - 展现产品在极限条件下的表现
        - 突出产品的卓越性能和可靠性
        - 使用专业测试环境和设备
        - 展示量化的性能数据和指标
        - 体现产品的工程品质和技术实力

        === 视觉表现要求 ===
        - 专业的测试环境和设备展示
        - 清晰的性能数据和指标显示
        - 产品在压力测试中的稳定表现
        - 科技感和专业感的视觉效果
        - 突出产品超越标准的卓越性能

        === 视觉风格 ===
        色调盘：{', '.join(visual.color_palette)}
        光照风格：{visual.lighting_style}
        构图规则：{', '.join(visual.composition_rules)}
        美学方向：{visual.aesthetic_direction}

        === 导航标签集成 ===
        专业术语："{self._select_navigation_term('performance')}"
        标签位置：图片下方或角落，清晰可读
        字体风格：现代、专业、与整体设计协调

        === 技术规格 ===
        - 尺寸：600x450像素（4:3宽高比）
        - 格式：高质量PNG，适合轮播展示
        - 色彩空间：sRGB
        - 分辨率：最低72 DPI
        - 文件大小：5MB以内

        === 核心目标 ===
        让消费者看到产品在极限条件下的卓越表现，建立对产品性能和可靠性的绝对信心。

        {custom_adjustments}
        """
        
        return prompt.strip()
    
    def _build_inside_out_prompt(
        self, 
        analysis: AnalysisResult,
        custom_params: Optional[Dict[str, Any]] = None
    ) -> str:
        """构建Inside Out结构工艺提示词"""
        
        listing = analysis.listing_analysis
        visual = analysis.visual_style
        
        # 应用自定义参数
        custom_adjustments = ""
        if custom_params and "inside_out_focus" in custom_params:
            custom_adjustments = f"\n工艺重点：{custom_params['inside_out_focus']}"
        
        prompt = f"""
        创建一个600x450像素的Premium Navigation Carousel轮播图 - Inside Out结构工艺维度展示。

        === 产品信息 ===
        产品类别：{listing.product_category}
        核心卖点：{', '.join(listing.key_selling_points)}
        技术规格：{', '.join(f"{k}: {v}" for k, v in list(listing.technical_specifications.items())[:3])}

        === 结构工艺细节展示 ===
        内部结构：{', '.join(self.inside_out_details['internal_structure'])}
        工艺特色：{', '.join(self.inside_out_details['craftsmanship'])}
        质量保证：{', '.join(self.inside_out_details['quality_assurance'])}
        保修承诺：{', '.join(self.inside_out_details['warranty'])}

        === Inside Out展示要求 ===
        - 展现产品的内部结构和设计理念
        - 突出精密制造工艺和质量控制
        - 展示关键组件和技术创新
        - 体现品质保证和服务承诺
        - 传达专业制造和长期价值

        === 视觉表现要求 ===
        - 透视或剖面图展示内部结构
        - 精密组件和工艺细节特写
        - 质量检测和认证标识展示
        - 专业制造环境和设备
        - 保修服务和支持体系可视化

        === 视觉风格 ===
        色调盘：{', '.join(visual.color_palette)}
        光照风格：{visual.lighting_style}
        构图规则：{', '.join(visual.composition_rules)}
        美学方向：{visual.aesthetic_direction}

        === 导航标签集成 ===
        专业术语："{self._select_navigation_term('inside_out')}"
        标签位置：图片下方或角落，清晰可读
        字体风格：现代、专业、与整体设计协调

        === 技术规格 ===
        - 尺寸：600x450像素（4:3宽高比）
        - 格式：高质量PNG，适合轮播展示
        - 色彩空间：sRGB
        - 分辨率：最低72 DPI
        - 文件大小：5MB以内

        === 核心目标 ===
        让消费者看到产品的内在品质和制造工艺，建立对产品质量和服务的长期信任。

        {custom_adjustments}
        """
        
        return prompt.strip()
    
    async def _generate_single_slide(self, slide: CarouselSlide, analysis: AnalysisResult) -> GenerationResult:
        """生成单张轮播图"""
        try:
            # 构建模块提示词
            module_prompt = ModulePrompt(
                module_type=ModuleType.EXTENSION,
                base_prompt=slide.prompt,
                style_modifiers=[
                    "premium_navigation_carousel",
                    f"{slide.slide_type}_dimension",
                    "professional_navigation_labels",
                    "carousel_optimized_layout",
                    "dimensional_storytelling"
                ],
                technical_requirements=[
                    "600x450_pixels",
                    "4_3_aspect_ratio",
                    "carousel_navigation_support",
                    "professional_terminology_integration",
                    "dimensional_content_focus",
                    "navigation_label_placement"
                ],
                aspect_ratio="600x450",
                quality_settings={
                    "resolution": "high",
                    "color_depth": "24bit",
                    "compression": "lossless",
                    "carousel_optimization": True,
                    "navigation_clarity": "professional"
                }
            )
            
            # 生成图片
            generation_result = await self.image_service.generate_aplus_image(
                module_prompt,
                reference_images=self._get_reference_images(analysis)
            )
            
            # 更新元数据
            generation_result.metadata.update({
                "slide_type": slide.slide_type,
                "slide_title": slide.title,
                "content_focus": slide.content_focus,
                "navigation_label": slide.navigation_label,
                "dimension": slide.slide_type
            })
            
            # 后处理
            if generation_result.image_data:
                generation_result = await self._post_process_extension_image(generation_result)
            
            return generation_result
            
        except Exception as e:
            return GenerationResult(
                module_type=ModuleType.EXTENSION,
                image_data=None,
                image_path=None,
                prompt_used=slide.prompt,
                generation_time=0.0,
                quality_score=0.0,
                validation_status=ValidationStatus.FAILED,
                metadata={
                    "error": f"Single slide generation failed: {str(e)}",
                    "slide_type": slide.slide_type
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
    
    async def _post_process_extension_image(self, generation_result: GenerationResult) -> GenerationResult:
        """后处理多维延展图片"""
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
            
            # 4. 更新元数据
            generation_result.metadata.update({
                "post_processed": True,
                "extension_optimization_applied": True,
                "quality_assessment": quality_assessment,
                "validation_details": {
                    "is_valid": validation_result.is_valid,
                    "issues": validation_result.issues,
                    "suggestions": validation_result.suggestions
                },
                "extension_specific_metrics": {
                    "carousel_compatibility": True,
                    "navigation_label_integrated": True,
                    "dimensional_content_focus": generation_result.metadata.get("slide_type", "unknown")
                }
            })
            
            return generation_result
            
        except Exception as e:
            generation_result.metadata["post_processing_error"] = str(e)
            return generation_result
    
    def get_extension_configuration_options(self) -> Dict[str, Any]:
        """获取多维延展配置选项 - 供用户自定义选择"""
        return {
            "lifestyle_scenarios": {
                scenario_type: {
                    "setting": scenario.setting,
                    "activities": scenario.activities,
                    "emotional_tone": scenario.emotional_tone
                }
                for scenario_type, scenario in self.lifestyle_scenarios.items()
            },
            "pain_point_solutions": {
                solution_type: {
                    "problems": solution.common_problems,
                    "approach": solution.solution_approach,
                    "benefits": solution.benefit_emphasis
                }
                for solution_type, solution in self.pain_point_solutions.items()
            },
            "performance_tests": {
                test_type: {
                    "scenarios": test.test_scenarios,
                    "metrics": test.performance_metrics
                }
                for test_type, test in self.performance_tests.items()
            },
            "navigation_terms": PROFESSIONAL_NAVIGATION_TERMS,
            "carousel_dimensions": [
                "lifestyle", "pain_point", "extreme_performance", "inside_out"
            ]
        }
    
    def validate_extension_requirements(self, carousel_results: List[GenerationResult]) -> Dict[str, Any]:
        """验证多维延展模块特定要求"""
        validation_results = {
            "meets_extension_requirements": True,
            "issues": [],
            "suggestions": [],
            "extension_specific_metrics": {},
            "carousel_completeness": {}
        }
        
        try:
            # 1. 检查轮播图数量
            expected_slides = 4
            actual_slides = len(carousel_results)
            
            if actual_slides != expected_slides:
                validation_results["meets_extension_requirements"] = False
                validation_results["issues"].append(
                    f"Expected {expected_slides} carousel slides, got {actual_slides}"
                )
            
            # 2. 检查每张轮播图的要求
            slide_types = ["lifestyle", "pain_point", "extreme_performance", "inside_out"]
            slide_validation = {}
            
            for i, result in enumerate(carousel_results):
                slide_type = slide_types[i] if i < len(slide_types) else f"slide_{i+1}"
                slide_validation[slide_type] = {
                    "has_image_data": result.image_data is not None,
                    "validation_status": result.validation_status.value,
                    "quality_score": result.quality_score,
                    "meets_requirements": True
                }
                
                if not result.image_data:
                    slide_validation[slide_type]["meets_requirements"] = False
                    validation_results["issues"].append(f"{slide_type} slide has no image data")
                
                # 检查尺寸规格
                if result.image_data:
                    try:
                        image = Image.open(io.BytesIO(result.image_data))
                        expected_size = APLUS_IMAGE_SPECS["dimensions"]
                        
                        if image.size != expected_size:
                            slide_validation[slide_type]["meets_requirements"] = False
                            validation_results["issues"].append(
                                f"{slide_type} slide size {image.size} does not match required {expected_size}"
                            )
                        
                        slide_validation[slide_type]["actual_size"] = image.size
                        slide_validation[slide_type]["aspect_ratio"] = image.size[0] / image.size[1] if image.size[1] > 0 else 1.0
                        
                    except Exception as e:
                        slide_validation[slide_type]["meets_requirements"] = False
                        validation_results["issues"].append(f"{slide_type} slide image validation error: {str(e)}")
            
            validation_results["carousel_completeness"] = slide_validation
            
            # 3. 检查专业导航术语集成
            navigation_terms_used = []
            for result in carousel_results:
                if "navigation_label" in result.metadata:
                    navigation_terms_used.append(result.metadata["navigation_label"])
            
            validation_results["extension_specific_metrics"] = {
                "total_slides": actual_slides,
                "expected_slides": expected_slides,
                "carousel_complete": actual_slides == expected_slides,
                "navigation_terms_used": navigation_terms_used,
                "professional_terminology": len(navigation_terms_used) > 0,
                "dimensional_coverage": {
                    slide_type: any(
                        result.metadata.get("slide_type") == slide_type 
                        for result in carousel_results
                    )
                    for slide_type in slide_types
                }
            }
            
            # 4. 添加改进建议
            failed_slides = sum(1 for result in carousel_results if result.validation_status == ValidationStatus.FAILED)
            if failed_slides > 0:
                validation_results["suggestions"].append(
                    f"Regenerate {failed_slides} failed carousel slides for complete coverage"
                )
            
            low_quality_slides = sum(1 for result in carousel_results if result.quality_score < 0.7)
            if low_quality_slides > 0:
                validation_results["suggestions"].append(
                    f"Improve quality for {low_quality_slides} carousel slides with enhanced parameters"
                )
            
            # 5. 最终验证状态
            if validation_results["issues"]:
                validation_results["meets_extension_requirements"] = False
            
        except Exception as e:
            validation_results["meets_extension_requirements"] = False
            validation_results["issues"].append(f"Extension validation error: {str(e)}")
        
        return validation_results
    
    async def generate_extension_carousel_simplified(
        self, 
        analysis: AnalysisResult,
        custom_params: Optional[Dict[str, Any]] = None
    ) -> List[GenerationResult]:
        """简化的多维延展模块轮播图生成，用于错误恢复"""
        
        try:
            carousel_results = []
            
            # 简化的四个维度配置
            simplified_dimensions = [
                {
                    "type": "lifestyle",
                    "prompt": f"Lifestyle scene with {analysis.listing_analysis.product_category} in use",
                    "label": "Lifestyle"
                },
                {
                    "type": "pain_point", 
                    "prompt": f"Problem-solving demonstration for {analysis.listing_analysis.product_category}",
                    "label": "Solution"
                },
                {
                    "type": "extreme_performance",
                    "prompt": f"Performance testing of {analysis.listing_analysis.product_category}",
                    "label": "Performance"
                },
                {
                    "type": "inside_out",
                    "prompt": f"Internal structure and quality of {analysis.listing_analysis.product_category}",
                    "label": "Quality"
                }
            ]
            
            # 生成每个维度的轮播图
            for i, dimension in enumerate(simplified_dimensions):
                try:
                    simplified_prompt = ModulePrompt(
                        module_type=ModuleType.EXTENSION,
                        base_prompt=f"""
                        Create a carousel slide for: {dimension['prompt']}
                        
                        Style requirements:
                        - Professional navigation carousel format
                        - 600x450 pixels (4:3 aspect ratio)
                        - Clear visual hierarchy
                        - Navigation label: {dimension['label']}
                        
                        Focus on {dimension['type']} aspects.
                        """,
                        style_modifiers=["carousel", "professional", dimension['type']],
                        technical_requirements=["600x450", "4:3_ratio", "navigation_ready"],
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
                    
                    # 设置模块类型和元数据
                    generation_result.module_type = ModuleType.EXTENSION
                    generation_result.metadata.update({
                        "slide_type": dimension['type'],
                        "navigation_label": dimension['label'],
                        "slide_index": i,
                        "simplified_mode": True
                    })
                    
                    carousel_results.append(generation_result)
                    
                except Exception as e:
                    # 为失败的轮播图创建占位符
                    failed_result = GenerationResult(
                        module_type=ModuleType.EXTENSION,
                        image_data=None,
                        image_path=None,
                        prompt_used=f"Simplified {dimension['type']} generation failed",
                        generation_time=0.0,
                        quality_score=0.0,
                        validation_status=ValidationStatus.FAILED,
                        metadata={
                            "error": f"Simplified {dimension['type']} generation failed: {str(e)}",
                            "slide_type": dimension['type'],
                            "navigation_label": dimension['label'],
                            "slide_index": i
                        }
                    )
                    carousel_results.append(failed_result)
            
            return carousel_results
            
        except Exception as e:
            # 返回空的轮播图结果
            return [
                GenerationResult(
                    module_type=ModuleType.EXTENSION,
                    image_data=None,
                    image_path=None,
                    prompt_used="Simplified extension carousel generation failed",
                    generation_time=0.0,
                    quality_score=0.0,
                    validation_status=ValidationStatus.FAILED,
                    metadata={"error": f"Simplified extension carousel generation failed: {str(e)}"}
                )
            ]
