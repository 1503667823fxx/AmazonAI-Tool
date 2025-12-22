"""
Identity Module Generator for A+ Studio system.

This module implements the Identity (身份代入) module generator that creates
Full Image full-screen visual effects with North American middle-class aesthetic
elements, value proposition slogans, and trust endorsements.
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
class IdentitySceneElements:
    """身份代入场景元素配置"""
    lifestyle_setting: str
    lighting_condition: str
    social_indicators: List[str]
    emotional_triggers: List[str]
    value_slogan: str
    trust_endorsement: str


@dataclass
class NorthAmericanAesthetic:
    """北美中产审美标准配置"""
    home_environments: List[str]
    lifestyle_markers: List[str]
    quality_indicators: List[str]
    aspirational_elements: List[str]


class IdentityModuleGenerator:
    """身份代入模块生成器 - 实现Full Image全屏视效生成"""
    
    def __init__(self, image_service: APlusImageService, prompt_service: PromptGenerationService):
        self.image_service = image_service
        self.prompt_service = prompt_service
        
        # 北美中产审美标准配置
        self.north_american_aesthetic = NorthAmericanAesthetic(
            home_environments=[
                "现代郊区住宅客厅，开放式布局",
                "精装修公寓，简约现代风格",
                "家庭办公室，专业而温馨",
                "厨房岛台区域，社交中心",
                "主卧室，舒适私密空间",
                "后院露台，休闲娱乐区域"
            ],
            lifestyle_markers=[
                "品质家具和装饰品",
                "整洁有序的生活空间",
                "现代化家电和设备",
                "绿植和自然元素",
                "艺术品和个人收藏",
                "家庭照片和纪念品"
            ],
            quality_indicators=[
                "高品质材料和工艺",
                "注重细节的设计",
                "功能性与美观并重",
                "可持续和环保理念",
                "品牌认知和信任",
                "长期价值投资"
            ],
            aspirational_elements=[
                "成功人士的生活方式",
                "家庭和谐与幸福",
                "个人成就和品味",
                "社会地位的体现",
                "未来生活的憧憬",
                "品质生活的追求"
            ]
        )
        
        # 黄金时段光照效果配置
        self.golden_hour_settings = {
            "morning": {
                "time": "早晨7-9点",
                "characteristics": "温暖柔和的晨光，从窗户斜射进入",
                "mood": "清新、希望、新开始",
                "color_temperature": "暖白色调，3000-3500K"
            },
            "afternoon": {
                "time": "下午4-6点",
                "characteristics": "金黄色夕阳光线，营造温馨氛围",
                "mood": "温暖、舒适、家庭团聚",
                "color_temperature": "金黄色调，2500-3000K"
            },
            "evening": {
                "time": "傍晚时分",
                "characteristics": "柔和的室内灯光与自然光融合",
                "mood": "放松、惬意、品质生活",
                "color_temperature": "暖黄色调，2200-2700K"
            }
        }
    
    async def generate_identity_image(
        self, 
        analysis: AnalysisResult,
        custom_params: Optional[Dict[str, Any]] = None
    ) -> GenerationResult:
        """生成身份代入模块图片 - Full Image全屏视效"""
        
        try:
            # 添加详细的调试信息
            import logging
            logger = logging.getLogger(__name__)
            logger.info("Starting identity module generation")
            
            # 验证输入参数
            if not analysis:
                raise ValueError("Analysis result is None")
            
            if not analysis.listing_analysis:
                raise ValueError("Listing analysis is missing from analysis result")
            
            logger.info(f"Analysis result valid, product category: {analysis.listing_analysis.product_category}")
            
            # 1. 分析产品特征，构建场景元素
            logger.info("Building scene elements...")
            scene_elements = self._build_scene_elements(analysis)
            logger.info(f"Scene elements built: {scene_elements.lifestyle_setting}")
            
            # 2. 选择合适的北美中产生活场景
            logger.info("Selecting lifestyle scene...")
            lifestyle_scene = self._select_lifestyle_scene(analysis, scene_elements)
            logger.info(f"Lifestyle scene selected: {lifestyle_scene}")
            
            # 3. 构建完整的身份代入提示词
            logger.info("Building identity prompt...")
            identity_prompt = self._build_identity_prompt(
                analysis, scene_elements, lifestyle_scene, custom_params
            )
            logger.info(f"Identity prompt built, length: {len(str(identity_prompt))}")
            
            # 4. 生成图片
            logger.info("Calling image service for generation...")
            reference_images = self._get_reference_images(analysis)
            logger.info(f"Reference images found: {len(reference_images) if reference_images else 0}")
            
            generation_result = await self.image_service.generate_aplus_image(
                identity_prompt,
                reference_images=reference_images
            )
            logger.info(f"Image generation completed, result: {generation_result.validation_status}")
            
            # 5. 后处理和优化
            if generation_result.image_data:
                logger.info("Starting post-processing...")
                generation_result = await self._post_process_identity_image(generation_result)
                logger.info("Post-processing completed")
            
            logger.info("Identity module generation completed successfully")
            return generation_result
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Identity module generation failed with error: {str(e)}")
            logger.error(f"Error type: {type(e).__name__}")
            
            # 确保错误信息不包含ModuleType对象
            error_message = str(e)
            if "ModuleType" in error_message:
                error_message = f"Identity module generation failed: {error_message}"
            
            return GenerationResult(
                module_type=ModuleType.IDENTITY,
                image_data=None,
                image_path=None,
                prompt_used="",
                generation_time=0.0,
                quality_score=0.0,
                validation_status=ValidationStatus.FAILED,
                metadata={"error": error_message, "original_error": str(e)}
            )
    
    def _build_scene_elements(self, analysis: AnalysisResult) -> IdentitySceneElements:
        """构建身份代入场景元素"""
        listing = analysis.listing_analysis
        visual = analysis.visual_style
        
        # 根据产品类别选择合适的生活场景设置
        lifestyle_setting = self._select_lifestyle_setting(listing.product_category)
        
        # 选择黄金时段光照条件
        lighting_condition = self._select_golden_hour_lighting(visual.lighting_style)
        
        # 构建社会地位指标
        social_indicators = self._build_social_indicators(listing.target_demographics)
        
        # 提取情感触发点
        emotional_triggers = getattr(listing, 'emotional_triggers', [])
        if not emotional_triggers:
            emotional_triggers = self._generate_emotional_triggers(listing)
        
        # 生成价值观Slogan
        value_slogan = self._generate_value_slogan(listing, emotional_triggers)
        
        # 生成信任背书
        trust_endorsement = self._generate_trust_endorsement(listing)
        
        return IdentitySceneElements(
            lifestyle_setting=lifestyle_setting,
            lighting_condition=lighting_condition,
            social_indicators=social_indicators,
            emotional_triggers=emotional_triggers,
            value_slogan=value_slogan,
            trust_endorsement=trust_endorsement
        )
    
    def _select_lifestyle_setting(self, product_category: str) -> str:
        """根据产品类别选择生活场景设置"""
        category_mapping = {
            "家居用品": self.north_american_aesthetic.home_environments[0],  # 客厅
            "厨房用具": self.north_american_aesthetic.home_environments[3],  # 厨房
            "办公用品": self.north_american_aesthetic.home_environments[2],  # 办公室
            "卧室用品": self.north_american_aesthetic.home_environments[4],  # 卧室
            "户外用品": self.north_american_aesthetic.home_environments[5],  # 后院
            "电子产品": self.north_american_aesthetic.home_environments[1],  # 公寓
        }
        
        # 默认使用现代客厅设置
        return category_mapping.get(
            product_category, 
            self.north_american_aesthetic.home_environments[0]
        )
    
    def _select_golden_hour_lighting(self, lighting_style: str) -> str:
        """选择黄金时段光照效果"""
        if "morning" in lighting_style.lower() or "dawn" in lighting_style.lower():
            return self.golden_hour_settings["morning"]["characteristics"]
        elif "evening" in lighting_style.lower() or "dusk" in lighting_style.lower():
            return self.golden_hour_settings["evening"]["characteristics"]
        else:
            # 默认使用下午黄金时段
            return self.golden_hour_settings["afternoon"]["characteristics"]
    
    def _build_social_indicators(self, target_demographics: str) -> List[str]:
        """构建社会地位指标"""
        base_indicators = [
            "高品质家居装饰",
            "现代化生活设备",
            "整洁有序的环境"
        ]
        
        # 根据目标人群添加特定指标
        if "professional" in target_demographics.lower() or "专业" in target_demographics:
            base_indicators.extend([
                "专业办公环境",
                "高端电子设备",
                "商务风格装饰"
            ])
        
        if "family" in target_demographics.lower() or "家庭" in target_demographics:
            base_indicators.extend([
                "家庭温馨氛围",
                "儿童友好环境",
                "多功能生活空间"
            ])
        
        return base_indicators[:5]  # 限制为5个主要指标
    
    def _generate_emotional_triggers(self, listing: 'ListingAnalysis') -> List[str]:
        """生成情感触发点"""
        base_triggers = [
            "品质生活的向往",
            "成功人士的认同",
            "家庭幸福的追求"
        ]
        
        # 根据产品卖点添加特定触发点
        for selling_point in listing.key_selling_points:
            if "quality" in selling_point.lower() or "品质" in selling_point:
                base_triggers.append("对高品质的追求")
            elif "convenience" in selling_point.lower() or "便利" in selling_point:
                base_triggers.append("便利生活的渴望")
            elif "style" in selling_point.lower() or "风格" in selling_point:
                base_triggers.append("个人品味的展现")
        
        return list(set(base_triggers))  # 去重
    
    def _generate_value_slogan(self, listing: 'ListingAnalysis', emotional_triggers: List[str]) -> str:
        """生成价值观Slogan"""
        # 基于产品特征和情感触发点生成Slogan
        primary_benefit = listing.key_selling_points[0] if listing.key_selling_points else "品质生活"
        primary_emotion = emotional_triggers[0] if emotional_triggers else "品质追求"
        
        slogan_templates = [
            f"让{primary_benefit}成为生活的标准",
            f"品质生活，从{primary_benefit}开始",
            f"选择{primary_benefit}，选择更好的自己",
            f"因为{primary_benefit}，生活更有品质",
            f"追求{primary_benefit}，享受品质人生"
        ]
        
        # 选择最合适的模板
        return slogan_templates[0]
    
    def _generate_trust_endorsement(self, listing: 'ListingAnalysis') -> str:
        """生成信任背书短语"""
        endorsement_templates = [
            "千万用户的信赖选择",
            "专业品质，值得信赖",
            "行业领先，品质保证",
            "用户好评，口碑之选",
            "专业认证，安心之选"
        ]
        
        # 根据竞争优势选择合适的背书
        if listing.competitive_advantages:
            advantage = listing.competitive_advantages[0]
            if "quality" in advantage.lower() or "品质" in advantage:
                return "专业品质，值得信赖"
            elif "popular" in advantage.lower() or "受欢迎" in advantage:
                return "千万用户的信赖选择"
            elif "certified" in advantage.lower() or "认证" in advantage:
                return "专业认证，安心之选"
        
        return endorsement_templates[0]  # 默认选择
    
    def _select_lifestyle_scene(
        self, 
        analysis: AnalysisResult, 
        scene_elements: IdentitySceneElements
    ) -> Dict[str, str]:
        """选择合适的北美中产生活场景"""
        listing = analysis.listing_analysis
        
        scene_config = {
            "environment": scene_elements.lifestyle_setting,
            "lighting": scene_elements.lighting_condition,
            "atmosphere": "温馨、舒适、有品质感的家庭环境",
            "people": "北美中产家庭成员，自然使用产品的状态",
            "props": ", ".join(scene_elements.social_indicators),
            "mood": "轻松愉悦，体现生活品质和家庭和谐"
        }
        
        # 根据产品类别调整场景细节
        if "kitchen" in listing.product_category.lower() or "厨房" in listing.product_category:
            scene_config["activity"] = "家庭烹饪或聚餐场景"
            scene_config["interaction"] = "家人围绕产品进行日常活动"
        elif "office" in listing.product_category.lower() or "办公" in listing.product_category:
            scene_config["activity"] = "居家办公或学习场景"
            scene_config["interaction"] = "专业人士高效使用产品"
        else:
            scene_config["activity"] = "日常生活休闲场景"
            scene_config["interaction"] = "自然融入生活的产品使用"
        
        return scene_config
    
    def _build_identity_prompt(
        self,
        analysis: AnalysisResult,
        scene_elements: IdentitySceneElements,
        lifestyle_scene: Dict[str, str],
        custom_params: Optional[Dict[str, Any]] = None
    ) -> ModulePrompt:
        """构建完整的身份代入提示词"""
        
        listing = analysis.listing_analysis
        visual = analysis.visual_style
        
        # 构建详细的场景描述
        scene_description = f"""
        环境设置：{lifestyle_scene['environment']}
        光照效果：{lifestyle_scene['lighting']}
        氛围营造：{lifestyle_scene['atmosphere']}
        人物设定：{lifestyle_scene['people']}
        场景道具：{lifestyle_scene['props']}
        整体情绪：{lifestyle_scene['mood']}
        活动内容：{lifestyle_scene['activity']}
        产品互动：{lifestyle_scene['interaction']}
        """
        
        # 构建文字要素集成
        text_elements = f"""
        价值观Slogan："{scene_elements.value_slogan}"
        信任背书："{scene_elements.trust_endorsement}"
        
        文字集成要求：
        - Slogan位置：图片上方或中心显眼位置，字体优雅现代
        - 背书位置：图片下方或角落，字体较小但清晰可读
        - 文字颜色：与整体色调协调，确保可读性
        - 文字效果：轻微阴影或描边，增强视觉层次
        - 整体融合：文字与场景自然融合，不突兀不抢夺视觉焦点
        """
        
        # 构建北美审美要求
        aesthetic_requirements = f"""
        北美中产审美标准：
        - 空间设计：开放式布局，简约现代风格
        - 色彩搭配：中性色调为主，温暖色彩点缀
        - 材质选择：天然材料与现代材料结合
        - 装饰风格：简洁大方，注重功能性
        - 生活方式：体现品质、便利、舒适的生活理念
        
        社会地位指标：
        {chr(10).join([f"- {indicator}" for indicator in scene_elements.social_indicators])}
        
        情感共鸣要素：
        {chr(10).join([f"- {trigger}" for trigger in scene_elements.emotional_triggers])}
        """
        
        # 应用自定义参数
        custom_adjustments = ""
        if custom_params:
            if "lighting_adjustment" in custom_params:
                custom_adjustments += f"\n光照调整：{custom_params['lighting_adjustment']}"
            if "scene_focus" in custom_params:
                custom_adjustments += f"\n场景重点：{custom_params['scene_focus']}"
            if "emotional_emphasis" in custom_params:
                custom_adjustments += f"\n情感强调：{custom_params['emotional_emphasis']}"
        
        # 构建完整提示词
        full_prompt = f"""
        创建一个600x450像素的Full Image全屏视效图片，展现北美中产家庭使用{listing.product_category}的理想生活场景。

        === 产品信息 ===
        产品类别：{listing.product_category}
        核心卖点：{', '.join(listing.key_selling_points)}
        目标用户：{listing.target_demographics}
        竞争优势：{', '.join(listing.competitive_advantages)}

        === 场景构建 ===
        {scene_description}

        === 视觉风格 ===
        色调盘：{', '.join(visual.color_palette)}
        光照风格：{visual.lighting_style}
        构图规则：{', '.join(visual.composition_rules)}
        美学方向：{visual.aesthetic_direction}

        === 北美中产审美 ===
        {aesthetic_requirements}

        === 文字要素集成 ===
        {text_elements}

        === 技术规格 ===
        - 尺寸：600x450像素（4:3宽高比）
        - 格式：高质量PNG，适合电商展示
        - 色彩空间：sRGB
        - 分辨率：最低72 DPI
        - 文件大小：5MB以内

        === 质量标准 ===
        - 专业电商级别的视觉质量
        - 清晰的产品可见性和吸引力
        - 适合在线零售环境展示
        - 优化客户转化效果
        - 简洁不杂乱的构图
        - 高视觉冲击力的产品营销效果

        === 核心目标 ===
        让消费者产生"这就是我想要的生活"的强烈认同感和向往，通过阶级场景代入而非单纯结果导向，建立情感连接和购买欲望。

        {custom_adjustments}
        """
        
        return ModulePrompt(
            module_type=ModuleType.IDENTITY,
            base_prompt=full_prompt.strip(),
            style_modifiers=[
                "full_image_layout",
                "golden_hour_lighting",
                "north_american_aesthetic",
                "aspirational_lifestyle",
                "middle_class_setting",
                "emotional_resonance",
                "lifestyle_integration",
                "text_overlay_support",
                "brand_storytelling"
            ],
            technical_requirements=[
                "600x450_pixels",
                "4_3_aspect_ratio",
                "full_screen_visual_effect",
                "text_overlay_capability",
                "high_quality_rendering",
                "lifestyle_authenticity",
                "emotional_engagement",
                "social_status_indicators"
            ],
            aspect_ratio="600x450",
            quality_settings={
                "resolution": "high",
                "color_depth": "24bit",
                "compression": "lossless",
                "text_rendering": "crisp",
                "lighting_quality": "professional"
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
    
    async def _post_process_identity_image(self, generation_result: GenerationResult) -> GenerationResult:
        """后处理身份代入图片"""
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
                "optimization_applied": True,
                "quality_assessment": quality_assessment,
                "validation_details": {
                    "is_valid": validation_result.is_valid,
                    "issues": validation_result.issues,
                    "suggestions": validation_result.suggestions
                }
            })
            
            return generation_result
            
        except Exception as e:
            generation_result.metadata["post_processing_error"] = str(e)
            return generation_result
    
    def get_identity_scene_options(self) -> Dict[str, List[str]]:
        """获取身份代入场景选项 - 供用户自定义选择"""
        return {
            "home_environments": self.north_american_aesthetic.home_environments,
            "lifestyle_markers": self.north_american_aesthetic.lifestyle_markers,
            "quality_indicators": self.north_american_aesthetic.quality_indicators,
            "aspirational_elements": self.north_american_aesthetic.aspirational_elements,
            "lighting_options": list(self.golden_hour_settings.keys())
        }
    
    def validate_identity_requirements(self, generation_result: GenerationResult) -> Dict[str, Any]:
        """验证身份代入模块特定要求"""
        validation_results = {
            "meets_identity_requirements": True,
            "issues": [],
            "suggestions": [],
            "identity_specific_metrics": {}
        }
        
        try:
            if not generation_result.image_data:
                validation_results["meets_identity_requirements"] = False
                validation_results["issues"].append("No image data available for validation")
                return validation_results
            
            # 1. 检查尺寸规格
            image = Image.open(io.BytesIO(generation_result.image_data))
            expected_size = APLUS_IMAGE_SPECS["dimensions"]
            
            if image.size != expected_size:
                validation_results["issues"].append(
                    f"Image size {image.size} does not match required {expected_size}"
                )
                validation_results["meets_identity_requirements"] = False
            
            # 2. 检查宽高比（4:3）
            aspect_ratio = image.size[0] / image.size[1] if image.size[1] > 0 else 1.0
            expected_ratio = 4/3
            
            if abs(aspect_ratio - expected_ratio) > 0.01:
                validation_results["issues"].append(
                    f"Aspect ratio {aspect_ratio:.3f} does not match required 4:3 ratio"
                )
                validation_results["meets_identity_requirements"] = False
            
            # 3. 身份代入特定验证
            validation_results["identity_specific_metrics"] = {
                "image_dimensions": image.size,
                "aspect_ratio": aspect_ratio,
                "file_size_mb": len(generation_result.image_data) / (1024 * 1024),
                "color_mode": image.mode,
                "has_full_image_layout": True,  # 假设满足，实际需要图像分析
                "lifestyle_authenticity_score": generation_result.quality_score
            }
            
            # 4. 添加改进建议
            if generation_result.quality_score < 0.8:
                validation_results["suggestions"].append(
                    "Consider regenerating with enhanced lifestyle scene parameters"
                )
            
            if len(generation_result.image_data) > APLUS_IMAGE_SPECS["max_file_size"]:
                validation_results["suggestions"].append(
                    "Optimize image compression to reduce file size"
                )
            
        except Exception as e:
            validation_results["meets_identity_requirements"] = False
            validation_results["issues"].append(f"Validation error: {str(e)}")
        
        return validation_results
    
    async def generate_identity_image_simplified(
        self, 
        analysis: AnalysisResult,
        custom_params: Optional[Dict[str, Any]] = None
    ) -> GenerationResult:
        """简化的身份代入模块图片生成，用于错误恢复"""
        
        try:
            # 使用简化的提示词模板
            simplified_prompt = ModulePrompt(
                module_type=ModuleType.IDENTITY,
                base_prompt=f"""
                Create a lifestyle image showing a product in a modern North American home setting.
                Product category: {analysis.listing_analysis.product_category}
                
                Style requirements:
                - Clean, modern aesthetic
                - Natural lighting
                - 600x450 pixels (4:3 aspect ratio)
                - Professional quality
                - Lifestyle context
                
                Include subtle text overlay with value proposition.
                """,
                style_modifiers=["modern", "clean", "lifestyle"],
                technical_requirements=["600x450", "4:3_ratio", "high_quality"],
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
            generation_result.module_type = ModuleType.IDENTITY
            
            return generation_result
            
        except Exception as e:
            return GenerationResult(
                module_type=ModuleType.IDENTITY,
                image_data=None,
                image_path=None,
                prompt_used="Simplified identity generation failed",
                generation_time=0.0,
                quality_score=0.0,
                validation_status=ValidationStatus.FAILED,
                metadata={"error": f"Simplified identity generation failed: {str(e)}"}
            )
