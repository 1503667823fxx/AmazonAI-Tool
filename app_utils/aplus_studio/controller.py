"""
A+ Studio Main Controller.

This controller coordinates all module interactions and manages the overall
A+ image generation workflow with comprehensive error handling and recovery mechanisms.
"""

import asyncio
import logging
from typing import List, Dict, Optional, Any
from PIL import Image
import streamlit as st
from datetime import datetime, timedelta

from services.aplus_studio.analysis_service import ProductAnalysisService
from services.aplus_studio.prompt_service import PromptGenerationService
from services.aplus_studio.image_service import APlusImageService
from services.aplus_studio.validation_service import ValidationService
from services.aplus_studio.visual_sop_processor import VisualSOPProcessor
from services.aplus_studio.identity_generator import IdentityModuleGenerator
from services.aplus_studio.sensory_generator import SensoryModuleGenerator
from services.aplus_studio.extension_generator import ExtensionModuleGenerator
from services.aplus_studio.trust_generator import TrustModuleGenerator
from services.aplus_studio.regeneration_service import RegenerationService
from services.aplus_studio.models import (
    ProductInfo, AnalysisResult, ModuleType, GenerationResult,
    APlusSession, GenerationStatus, ValidationStatus
)
from .state_manager import APlusStateManager

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class APlusController:
    """A+ Studio主控制器 - 协调所有模块的交互和状态管理"""
    
    def __init__(self):
        try:
            self.state_manager = APlusStateManager()
            
            # 获取API密钥并传递给所有需要的服务
            api_key = None
            try:
                if hasattr(st, 'secrets') and 'GOOGLE_API_KEY' in st.secrets:
                    api_key = st.secrets["GOOGLE_API_KEY"]
                elif hasattr(st, 'secrets') and 'GEMINI_API_KEY' in st.secrets:
                    api_key = st.secrets["GEMINI_API_KEY"]
            except Exception:
                pass
            
            # 调试：检查ProductAnalysisService的签名
            import inspect
            try:
                sig = inspect.signature(ProductAnalysisService.__init__)
                logger.info(f"ProductAnalysisService.__init__ signature: {sig}")
            except Exception as e:
                logger.warning(f"Could not inspect ProductAnalysisService signature: {e}")
            
            # 传递API密钥给分析服务和图片服务
            # 使用try-catch处理可能的参数不匹配问题
            try:
                self.analysis_service = ProductAnalysisService(api_key)
                logger.info("ProductAnalysisService initialized with API key")
            except TypeError as e:
                logger.warning(f"ProductAnalysisService does not accept api_key parameter: {e}")
                # 回退到无参数初始化
                try:
                    self.analysis_service = ProductAnalysisService()
                    logger.info("ProductAnalysisService initialized without parameters")
                    # 尝试手动设置API密钥
                    if hasattr(self.analysis_service, 'api_key'):
                        self.analysis_service.api_key = api_key
                        logger.info("API key set manually on ProductAnalysisService")
                    elif hasattr(self.analysis_service, '_setup_gemini'):
                        # 如果有_setup_gemini方法，尝试重新设置
                        self.analysis_service.api_key = api_key
                        self.analysis_service._setup_gemini()
                        logger.info("API key set and Gemini re-configured")
                    else:
                        logger.warning("ProductAnalysisService does not have api_key attribute or _setup_gemini method")
                except Exception as fallback_error:
                    logger.error(f"Failed to initialize ProductAnalysisService even without parameters: {fallback_error}")
                    raise Exception(f"ProductAnalysisService initialization failed: {fallback_error}")
            
            self.prompt_service = PromptGenerationService()
            self.image_service = APlusImageService(api_key)
            self.validation_service = ValidationService()
            self.visual_sop_processor = VisualSOPProcessor()
            self.regeneration_service = RegenerationService()
            
            # 初始化模块生成器
            self.identity_generator = IdentityModuleGenerator(
                self.image_service, 
                self.prompt_service
            )
            self.sensory_generator = SensoryModuleGenerator(
                self.image_service,
                self.prompt_service
            )
            self.extension_generator = ExtensionModuleGenerator(
                self.image_service,
                self.prompt_service
            )
            self.trust_generator = TrustModuleGenerator(
                self.image_service,
                self.prompt_service
            )
            
            # 错误恢复配置
            self.max_retry_attempts = 3
            self.retry_delay = 1.0  # seconds
            self.error_recovery_enabled = True
            
            # 初始化会话
            self._ensure_session()
            
            logger.info("APlusController initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize APlusController: {str(e)}")
            st.error(f"控制器初始化失败：{str(e)}")
            raise
    
    def _ensure_session(self):
        """确保存在有效的会话，包含错误恢复机制"""
        try:
            if not self.state_manager.has_active_session():
                logger.info("Creating new session as no active session found")
                self.state_manager.create_new_session()
            else:
                # 验证现有会话的完整性
                session = self.state_manager.get_current_session()
                if session and self._validate_session_integrity(session):
                    logger.info(f"Active session validated: {session.session_id}")
                else:
                    logger.warning("Session integrity check failed, creating new session")
                    self.state_manager.create_new_session()
        except Exception as e:
            logger.error(f"Error ensuring session: {str(e)}")
            # 强制创建新会话作为恢复机制
            try:
                self.state_manager.create_new_session()
                logger.info("Recovery: Created new session after error")
            except Exception as recovery_error:
                logger.critical(f"Failed to create recovery session: {str(recovery_error)}")
                st.error("会话管理出现严重错误，请刷新页面")
    
    def _validate_session_integrity(self, session: APlusSession) -> bool:
        """验证会话完整性"""
        try:
            # 检查基本属性
            if not session.session_id or not session.creation_time:
                return False
            
            # 检查会话是否过期（24小时）
            if datetime.now() - session.creation_time > timedelta(hours=24):
                logger.info(f"Session {session.session_id} expired")
                return False
            
            # 检查生成状态的完整性
            expected_modules = set(ModuleType)
            actual_modules = set(session.generation_status.keys())
            if expected_modules != actual_modules:
                logger.warning(f"Session {session.session_id} has incomplete module status")
                # 修复缺失的模块状态
                for module_type in expected_modules - actual_modules:
                    session.generation_status[module_type] = GenerationStatus.NOT_STARTED
            
            return True
            
        except Exception as e:
            logger.error(f"Session integrity validation failed: {str(e)}")
            return False
    
    async def process_product_input(
        self, 
        listing_text: str, 
        product_images: List[Any]
    ) -> AnalysisResult:
        """处理产品输入并进行分析，包含重试和错误恢复机制"""
        attempt = 0
        last_error = None
        
        while attempt < self.max_retry_attempts:
            try:
                logger.info(f"Processing product input, attempt {attempt + 1}")
                
                # 输入验证
                if not listing_text or not listing_text.strip():
                    raise ValueError("产品listing文本不能为空")
                
                if len(listing_text.strip()) < 10:
                    raise ValueError("产品listing文本过短，请提供更详细的产品描述")
                
                # 创建产品信息对象
                product_info = ProductInfo(
                    name="待提取",
                    category="待分析",
                    description=listing_text,
                    key_features=[],
                    target_audience="待分析",
                    price_range="待分析",
                    uploaded_images=product_images
                )
                
                # 更新会话中的产品信息
                self.state_manager.update_product_info(product_info)
                
                # 执行产品分析
                with st.spinner("正在分析产品信息..."):
                    analysis_result = await self.analysis_service.analyze_product(product_info)
                
                # 验证分析结果
                if not self._validate_analysis_result(analysis_result):
                    raise ValueError("产品分析结果不完整，请重试")
                
                # 保存分析结果
                self.state_manager.update_analysis_result(analysis_result)
                
                logger.info("Product analysis completed successfully")
                return analysis_result
                
            except Exception as e:
                attempt += 1
                last_error = e
                logger.error(f"Product analysis attempt {attempt} failed: {str(e)}")
                
                if attempt < self.max_retry_attempts:
                    st.warning(f"分析失败，正在重试... (尝试 {attempt}/{self.max_retry_attempts})")
                    await asyncio.sleep(self.retry_delay * attempt)  # 指数退避
                else:
                    logger.error(f"Product analysis failed after {self.max_retry_attempts} attempts")
                    st.error(f"产品分析失败：{str(last_error)}")
                    
                    # 错误恢复：尝试使用简化分析
                    if self.error_recovery_enabled:
                        try:
                            recovery_result = await self._recovery_product_analysis(listing_text, product_images)
                            if recovery_result:
                                st.warning("使用简化分析模式完成了产品分析")
                                return recovery_result
                        except Exception as recovery_error:
                            logger.error(f"Recovery analysis also failed: {str(recovery_error)}")
                    
                    raise last_error
        
        raise last_error or Exception("产品分析失败")
    
    def _validate_analysis_result(self, analysis_result: AnalysisResult) -> bool:
        """验证分析结果的完整性"""
        try:
            if not analysis_result:
                return False
            
            # 检查必需的分析组件
            required_components = ['listing_analysis', 'image_analysis']
            for component in required_components:
                if not hasattr(analysis_result, component) or getattr(analysis_result, component) is None:
                    logger.warning(f"Analysis result missing component: {component}")
                    return False
            
            # 检查listing分析的关键字段
            listing_analysis = analysis_result.listing_analysis
            if not listing_analysis.product_category or not listing_analysis.key_selling_points:
                logger.warning("Listing analysis incomplete")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Analysis result validation failed: {str(e)}")
            return False
    
    async def _recovery_product_analysis(self, listing_text: str, product_images: List[Any]) -> Optional[AnalysisResult]:
        """错误恢复：简化的产品分析"""
        try:
            logger.info("Attempting recovery product analysis")
            
            # 创建简化的产品信息
            simplified_product_info = ProductInfo(
                name="产品",
                category="通用",
                description=listing_text[:500],  # 限制长度
                key_features=["待分析"],
                target_audience="消费者",
                price_range="中等",
                uploaded_images=product_images[:3] if product_images else []  # 限制图片数量
            )
            
            # 尝试简化分析
            recovery_result = await self.analysis_service.analyze_product_simplified(simplified_product_info)
            
            if recovery_result:
                self.state_manager.update_analysis_result(recovery_result)
                logger.info("Recovery analysis completed")
                return recovery_result
            
        except Exception as e:
            logger.error(f"Recovery analysis failed: {str(e)}")
        
        return None
    
    async def generate_module_image(
        self, 
        module_type: ModuleType, 
        custom_params: Optional[Dict[str, Any]] = None
    ) -> GenerationResult:
        """生成指定模块的图片，包含完整的错误处理和恢复机制"""
        attempt = 0
        last_error = None
        
        while attempt < self.max_retry_attempts:
            try:
                logger.info(f"Generating {module_type.value} module, attempt {attempt + 1}")
                
                # 获取当前会话和分析结果
                session = self.state_manager.get_current_session()
                if not session or not session.analysis_result:
                    raise ValueError("请先完成产品分析")
                
                # 更新生成状态
                self.state_manager.update_generation_status(module_type, GenerationStatus.IN_PROGRESS)
                
                # 根据模块类型使用专门的生成器
                generation_result = await self._execute_module_generation_with_recovery(
                    module_type, session, custom_params, attempt
                )
                
                # 验证生成结果
                if not self._validate_generation_result(generation_result, module_type):
                    error_msg = f"{module_type.value}模块生成结果验证失败"
                    raise ValueError(error_msg)
                
                # 保存结果
                self.state_manager.update_module_result(module_type, generation_result)
                self.state_manager.update_generation_status(module_type, GenerationStatus.COMPLETED)
                
                # 初始化重新生成历史记录
                await self._initialize_regeneration_history(session, module_type, generation_result, custom_params)
                
                logger.info(f"{module_type.value} module generation completed successfully")
                return generation_result
                
            except Exception as e:
                attempt += 1
                last_error = e
                # 确保错误消息是字符串格式
                error_msg = str(e)
                if "ModuleType.TRUST" in error_msg:
                    error_msg = "Trust module generation failed due to configuration error"
                logger.error(f"{module_type.value} module generation attempt {attempt} failed: {error_msg}")
                
                if attempt < self.max_retry_attempts:
                    st.warning(f"{module_type.value}模块生成失败，正在重试... (尝试 {attempt}/{self.max_retry_attempts})")
                    await asyncio.sleep(self.retry_delay * attempt)
                else:
                    logger.error(f"{module_type.value} module generation failed after {self.max_retry_attempts} attempts")
                    self.state_manager.update_generation_status(module_type, GenerationStatus.FAILED)
                    
                    # 错误恢复：尝试使用备用生成方法
                    if self.error_recovery_enabled:
                        try:
                            recovery_result = await self._recovery_module_generation(module_type, session, custom_params)
                            if recovery_result:
                                st.warning(f"使用备用方法完成了{module_type.value}模块生成")
                                self.state_manager.update_module_result(module_type, recovery_result)
                                self.state_manager.update_generation_status(module_type, GenerationStatus.COMPLETED)
                                return recovery_result
                        except Exception as recovery_error:
                            logger.error(f"Recovery generation also failed: {str(recovery_error)}")
                    
                    st.error(f"{module_type.value}模块生成失败：{str(last_error)}")
                    raise last_error
        
        # 确保最终异常消息是字符串
        final_error_msg = f"{module_type.value}模块生成失败"
        if last_error:
            error_str = str(last_error)
            if "ModuleType.TRUST" in error_str:
                final_error_msg = "Trust模块生成失败：配置错误"
            else:
                final_error_msg = f"{module_type.value}模块生成失败：{error_str}"
        
        raise Exception(final_error_msg)
    
    async def _execute_module_generation_with_recovery(
        self, 
        module_type: ModuleType, 
        session: APlusSession, 
        custom_params: Optional[Dict[str, Any]], 
        attempt: int
    ) -> GenerationResult:
        """执行模块生成，包含重试逻辑"""
        
        # 根据重试次数调整参数
        adjusted_params = self._adjust_params_for_retry(custom_params, attempt)
        
        if module_type == ModuleType.IDENTITY:
            with st.spinner("正在生成身份代入模块图片..."):
                # 验证分析结果
                if not session.analysis_result:
                    raise ValueError("产品分析结果为空，请先完成产品分析")
                
                logger.info(f"Starting identity generation with analysis result: {bool(session.analysis_result)}")
                return await self.identity_generator.generate_identity_image(
                    session.analysis_result, adjusted_params
                )
        elif module_type == ModuleType.SENSORY:
            with st.spinner("正在生成感官解构模块图片..."):
                return await self.sensory_generator.generate_sensory_image(
                    session.analysis_result, adjusted_params
                )
        elif module_type == ModuleType.EXTENSION:
            with st.spinner("正在生成多维延展模块轮播图..."):
                carousel_results = await self.extension_generator.generate_extension_carousel(
                    session.analysis_result, adjusted_params
                )
                if not carousel_results:
                    raise ValueError("Extension carousel generation returned no results")
                
                generation_result = carousel_results[0]
                generation_result.metadata["carousel_results"] = carousel_results
                return generation_result
        elif module_type == ModuleType.TRUST:
            with st.spinner("正在生成信任转化模块图片..."):
                return await self.trust_generator.generate_trust_image(
                    session.analysis_result, adjusted_params
                )
        else:
            # 通用生成流程
            with st.spinner(f"正在生成{module_type.value}模块提示词..."):
                all_prompts = self.prompt_service.generate_all_module_prompts(session.analysis_result)
                prompt = all_prompts[module_type]
            
            # 应用自定义参数
            if adjusted_params:
                prompt = self._apply_custom_params(prompt, adjusted_params)
            
            # 生成图片
            with st.spinner(f"正在生成{module_type.value}模块图片..."):
                reference_images = self._get_reference_images(session)
                return await self.image_service.generate_aplus_image(prompt, reference_images)
    
    def _adjust_params_for_retry(self, custom_params: Optional[Dict[str, Any]], attempt: int) -> Optional[Dict[str, Any]]:
        """根据重试次数调整参数"""
        if not custom_params:
            custom_params = {}
        
        # 在重试时降低质量要求以提高成功率
        if attempt > 0:
            adjusted_params = custom_params.copy()
            adjusted_params['retry_attempt'] = attempt
            adjusted_params['quality_tolerance'] = max(0.6, 0.9 - (attempt * 0.1))
            return adjusted_params
        
        return custom_params
    
    def _validate_generation_result(self, result: GenerationResult, module_type: ModuleType) -> bool:
        """验证生成结果的完整性"""
        try:
            if not result:
                return False
            
            # 检查基本属性
            if result.module_type != module_type:
                logger.warning(f"Module type mismatch: expected {module_type}, got {result.module_type}")
                return False
            
            # 检查图片数据
            if not result.image_data and not result.image_path:
                logger.warning("Generation result has no image data")
                return False
            
            # 检查验证状态
            if result.validation_status == ValidationStatus.FAILED:
                logger.warning("Generation result failed validation")
                return False
            
            # 模块特定验证
            if module_type == ModuleType.EXTENSION:
                carousel_results = result.metadata.get("carousel_results", [])
                if len(carousel_results) < 4:
                    logger.warning(f"Extension module should have 4 carousel images, got {len(carousel_results)}")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Generation result validation failed: {str(e)}")
            return False
    
    async def _recovery_module_generation(
        self, 
        module_type: ModuleType, 
        session: APlusSession, 
        custom_params: Optional[Dict[str, Any]]
    ) -> Optional[GenerationResult]:
        """错误恢复：简化的模块生成"""
        try:
            logger.info(f"Attempting recovery generation for {module_type.value}")
            
            # 使用简化参数
            recovery_params = {
                'simplified_mode': True,
                'quality_tolerance': 0.5,
                'timeout_seconds': 30
            }
            
            if custom_params:
                recovery_params.update(custom_params)
            
            # 尝试简化生成
            if module_type == ModuleType.IDENTITY:
                return await self.identity_generator.generate_identity_image_simplified(
                    session.analysis_result, recovery_params
                )
            elif module_type == ModuleType.SENSORY:
                return await self.sensory_generator.generate_sensory_image_simplified(
                    session.analysis_result, recovery_params
                )
            elif module_type == ModuleType.EXTENSION:
                carousel_results = await self.extension_generator.generate_extension_carousel_simplified(
                    session.analysis_result, recovery_params
                )
                if carousel_results:
                    result = carousel_results[0]
                    result.metadata["carousel_results"] = carousel_results
                    return result
            elif module_type == ModuleType.TRUST:
                return await self.trust_generator.generate_trust_image_simplified(
                    session.analysis_result, recovery_params
                )
            
        except Exception as e:
            logger.error(f"Recovery generation failed: {str(e)}")
        
        return None
    
    def _get_reference_images(self, session: APlusSession) -> List[Image.Image]:
        """获取参考图片"""
        reference_images = []
        if session.product_info and session.product_info.uploaded_images:
            for img in session.product_info.uploaded_images:
                if isinstance(img, Image.Image):
                    reference_images.append(img)
        return reference_images
    
    async def _initialize_regeneration_history(
        self, 
        session: APlusSession, 
        module_type: ModuleType, 
        generation_result: GenerationResult, 
        custom_params: Optional[Dict[str, Any]]
    ):
        """初始化重新生成历史记录"""
        try:
            from services.aplus_studio.regeneration_service import RegenerationParameters
            initial_params = RegenerationParameters(
                module_type=module_type,
                original_prompt=generation_result.prompt_used,
                custom_modifications=custom_params or {},
                preserve_visual_consistency=True
            )
            
            self.regeneration_service.initialize_module_history(
                session.session_id, module_type, generation_result, initial_params
            )
        except Exception as e:
            logger.warning(f"Failed to initialize regeneration history: {str(e)}")
            # 不阻断主流程
    
    async def regenerate_image(
        self, 
        module_type: ModuleType, 
        custom_params: Optional[Dict[str, Any]] = None
    ) -> GenerationResult:
        """重新生成指定模块的图片"""
        try:
            session = self.state_manager.get_current_session()
            if not session:
                raise ValueError("没有活跃的会话")
            
            # 准备重新生成参数
            regen_params = self.regeneration_service.prepare_regeneration_parameters(
                session.session_id, module_type, custom_params
            )
            
            # 更新生成状态
            self.state_manager.update_generation_status(module_type, GenerationStatus.IN_PROGRESS)
            
            # 执行重新生成
            generation_result = await self._execute_module_generation(
                module_type, regen_params, session
            )
            
            # 添加到版本历史
            version_id = self.regeneration_service.add_generation_version(
                session.session_id, module_type, generation_result, regen_params
            )
            
            # 更新会话状态
            self.state_manager.update_module_result(module_type, generation_result)
            self.state_manager.update_generation_status(module_type, GenerationStatus.COMPLETED)
            
            return generation_result
            
        except Exception as e:
            self.state_manager.update_generation_status(module_type, GenerationStatus.FAILED)
            st.error(f"{module_type.value}模块重新生成失败：{str(e)}")
            raise
    
    async def _execute_module_generation(
        self, 
        module_type: ModuleType, 
        regen_params, 
        session: APlusSession
    ) -> GenerationResult:
        """执行模块生成（支持重新生成参数）"""
        # 应用参数修改到提示词
        if module_type == ModuleType.IDENTITY:
            generation_result = await self.identity_generator.generate_identity_image(
                session.analysis_result, regen_params.custom_modifications
            )
        elif module_type == ModuleType.SENSORY:
            generation_result = await self.sensory_generator.generate_sensory_image(
                session.analysis_result, regen_params.custom_modifications
            )
        elif module_type == ModuleType.EXTENSION:
            carousel_results = await self.extension_generator.generate_extension_carousel(
                session.analysis_result, regen_params.custom_modifications
            )
            generation_result = carousel_results[0] if carousel_results else GenerationResult(
                module_type=ModuleType.EXTENSION,
                image_data=None,
                image_path=None,
                prompt_used="",
                generation_time=0.0,
                quality_score=0.0,
                validation_status=ValidationStatus.FAILED,
                metadata={"error": "Extension carousel generation failed"}
            )
            generation_result.metadata["carousel_results"] = carousel_results
        elif module_type == ModuleType.TRUST:
            generation_result = await self.trust_generator.generate_trust_image(
                session.analysis_result, regen_params.custom_modifications
            )
        else:
            # 通用生成流程
            all_prompts = self.prompt_service.generate_all_module_prompts(session.analysis_result)
            prompt = all_prompts[module_type]
            
            # 应用重新生成参数修改
            modified_prompt = self.regeneration_service.apply_parameter_modifications(
                prompt.base_prompt, regen_params
            )
            
            # 获取参考图片
            reference_images = []
            if session.product_info and session.product_info.uploaded_images:
                for img in session.product_info.uploaded_images:
                    if isinstance(img, Image.Image):
                        reference_images.append(img)
            
            generation_result = await self.image_service.generate_aplus_image(
                modified_prompt, reference_images
            )
        
        return generation_result
    
    async def generate_all_modules(
        self, 
        selected_modules: Optional[List[ModuleType]] = None
    ) -> Dict[ModuleType, GenerationResult]:
        """生成所有选定模块的图片"""
        if selected_modules is None:
            selected_modules = list(ModuleType)
        
        results = {}
        
        # 顺序生成各模块（可以改为并发）
        for module_type in selected_modules:
            try:
                result = await self.generate_module_image(module_type)
                results[module_type] = result
            except Exception as e:
                st.error(f"{module_type.value}模块生成失败：{str(e)}")
                # 继续生成其他模块
                continue
        
        return results
    
    def _apply_custom_params(self, prompt, custom_params: Dict[str, Any]):
        """应用自定义参数到提示词"""
        # 这里应该实现提示词的自定义修改逻辑
        # 暂时返回原始提示词
        return prompt
    
    def get_generation_progress(self) -> Dict[ModuleType, GenerationStatus]:
        """获取所有模块的生成进度"""
        session = self.state_manager.get_current_session()
        if session:
            return session.generation_status
        return {}
    
    def get_module_results(self) -> Dict[ModuleType, GenerationResult]:
        """获取所有模块的生成结果"""
        session = self.state_manager.get_current_session()
        if session:
            return session.module_results
        return {}
    
    def validate_visual_consistency(self) -> Optional[Dict[str, Any]]:
        """验证所有模块的视觉连贯性"""
        session = self.state_manager.get_current_session()
        if not session or not session.module_results:
            return None
        
        try:
            # 只验证已生成的模块
            completed_results = {
                module_type: result 
                for module_type, result in session.module_results.items()
                if result.validation_status != ValidationStatus.FAILED
            }
            
            if len(completed_results) < 2:
                return {"message": "需要至少两个模块完成生成才能验证视觉连贯性"}
            
            # 使用Visual SOP处理器进行连贯性验证
            consistency_result = self.prompt_service.validate_visual_consistency(completed_results)
            
            return {
                "is_consistent": consistency_result.get('is_consistent', False),
                "overall_score": consistency_result.get('overall_score', 0.0),
                "consistency_metrics": consistency_result.get('consistency_metrics'),
                "conflicts": consistency_result.get('conflicts', []),
                "suggestions": consistency_result.get('suggestions', []),
                "locked_palette_info": self.prompt_service.get_locked_palette_info()
            }
            
        except Exception as e:
            return {"error": f"视觉连贯性验证失败：{str(e)}"}
    
    def detect_style_conflicts(self) -> List[str]:
        """检测当前模块间的风格冲突"""
        session = self.state_manager.get_current_session()
        if not session or not session.module_results:
            return ["没有可用的模块结果进行冲突检测"]
        
        try:
            completed_results = {
                module_type: result 
                for module_type, result in session.module_results.items()
                if result.validation_status != ValidationStatus.FAILED
            }
            
            if len(completed_results) < 2:
                return ["需要至少两个模块完成生成才能检测风格冲突"]
            
            conflicts = self.prompt_service.detect_and_resolve_conflicts(completed_results)
            return conflicts
            
        except Exception as e:
            return [f"风格冲突检测失败：{str(e)}"]
    
    def get_visual_consistency_report(self) -> Dict[str, Any]:
        """获取详细的视觉连贯性报告"""
        session = self.state_manager.get_current_session()
        if not session:
            return {"error": "没有活动会话"}
        
        report = {
            "session_info": {
                "session_id": session.session_id,
                "modules_generated": len(session.module_results),
                "analysis_available": session.analysis_result is not None
            },
            "visual_consistency": self.validate_visual_consistency(),
            "style_conflicts": self.detect_style_conflicts(),
            "locked_palette": self.prompt_service.get_locked_palette_info(),
            "module_status": {}
        }
        
        # 添加每个模块的状态信息
        for module_type, result in session.module_results.items():
            report["module_status"][module_type.value] = {
                "validation_status": result.validation_status.value,
                "quality_score": result.quality_score,
                "has_image": result.image_data is not None,
                "generation_time": result.generation_time
            }
        
        return report
    
    def ensure_module_coherence(self, target_module: ModuleType) -> Dict[str, Any]:
        """确保目标模块与现有模块的连贯性"""
        session = self.state_manager.get_current_session()
        if not session or not session.analysis_result:
            return {"error": "需要先完成产品分析"}
        
        try:
            # 获取现有的模块结果
            existing_results = {
                module_type: result 
                for module_type, result in session.module_results.items()
                if result.validation_status != ValidationStatus.FAILED
            }
            
            # 使用Visual SOP处理器确保连贯性
            locked_palette = self.prompt_service.get_locked_palette_info()
            if not locked_palette:
                # 如果没有锁定的色调盘，先创建一个
                locked_palette = self.visual_sop_processor.lock_color_palette(session.analysis_result)
            
            coherence_requirements = self.visual_sop_processor.ensure_module_coherence(
                target_module, existing_results, locked_palette
            )
            
            return {
                "target_module": target_module.value,
                "coherence_requirements": coherence_requirements,
                "existing_modules": list(existing_results.keys()),
                "recommendations": self._generate_coherence_recommendations(
                    target_module, coherence_requirements
                )
            }
            
        except Exception as e:
            return {"error": f"连贯性确保失败：{str(e)}"}
    
    def _generate_coherence_recommendations(self, 
                                          target_module: ModuleType, 
                                          coherence_requirements: Dict[str, Any]) -> List[str]:
        """基于连贯性要求生成建议"""
        recommendations = []
        
        # 色彩建议
        color_constraints = coherence_requirements.get('color_constraints', {})
        if 'target_color_temperature' in color_constraints:
            temp = color_constraints['target_color_temperature']
            recommendations.append(f"保持色温在{temp:.0f}K左右以确保与现有模块一致")
        
        # 光照建议
        lighting_constraints = coherence_requirements.get('lighting_constraints', {})
        if 'target_brightness_distribution' in lighting_constraints:
            recommendations.append("保持与现有模块相似的亮度分布")
        
        # 模块特定建议
        module_adjustments = coherence_requirements.get('module_specific_adjustments', {})
        if module_adjustments:
            for key, value in module_adjustments.items():
                recommendations.append(f"{target_module.value}模块特别注意：{key} - {value}")
        
        return recommendations
    
    def export_results(self) -> Optional[Dict[str, Any]]:
        """导出生成结果"""
        session = self.state_manager.get_current_session()
        if not session:
            return None
        
        export_data = {
            "session_id": session.session_id,
            "product_info": {
                "name": session.product_info.name if session.product_info else "未知",
                "description": session.product_info.description if session.product_info else ""
            },
            "generation_summary": {},
            "quality_metrics": {}
        }
        
        # 添加各模块的生成摘要
        for module_type, result in session.module_results.items():
            export_data["generation_summary"][module_type.value] = {
                "status": result.validation_status.value,
                "quality_score": result.quality_score,
                "generation_time": result.generation_time
            }
        
        # 添加整体统计
        if session.module_results:
            stats = self.image_service.get_generation_stats(session.module_results)
            export_data["quality_metrics"] = stats
        
        return export_data
    
    def reset_session(self):
        """重置当前会话"""
        self.state_manager.create_new_session()
    
    def get_session_info(self) -> Optional[Dict[str, Any]]:
        """获取当前会话信息"""
        session = self.state_manager.get_current_session()
        if not session:
            return None
        
        return {
            "session_id": session.session_id,
            "creation_time": session.creation_time.isoformat(),
            "last_updated": session.last_updated.isoformat(),
            "has_product_info": session.product_info is not None,
            "has_analysis": session.analysis_result is not None,
            "completed_modules": len([
                r for r in session.module_results.values() 
                if r.validation_status != ValidationStatus.FAILED
            ]),
            "total_modules": len(ModuleType)
        }
    
    def get_identity_scene_options(self) -> Dict[str, List[str]]:
        """获取身份代入模块的场景选项"""
        return self.identity_generator.get_identity_scene_options()
    
    def validate_identity_module(self, generation_result: GenerationResult) -> Dict[str, Any]:
        """验证身份代入模块特定要求"""
        return self.identity_generator.validate_identity_requirements(generation_result)
    
    def get_sensory_configuration_options(self) -> Dict[str, Any]:
        """获取感官解构模块的配置选项"""
        return self.sensory_generator.get_sensory_configuration_options()
    
    def validate_sensory_module(self, generation_result: GenerationResult) -> Dict[str, Any]:
        """验证感官解构模块特定要求"""
        return self.sensory_generator.validate_sensory_requirements(generation_result)
    
    def get_extension_configuration_options(self) -> Dict[str, Any]:
        """获取多维延展模块的配置选项"""
        return self.extension_generator.get_extension_configuration_options()
    
    def validate_extension_module(self, carousel_results: List[GenerationResult]) -> Dict[str, Any]:
        """验证多维延展模块特定要求"""
        return self.extension_generator.validate_extension_requirements(carousel_results)
    
    def get_trust_configuration_options(self) -> Dict[str, Any]:
        """获取信任转化模块的配置选项"""
        return self.trust_generator.get_trust_configuration_options()
    
    def validate_trust_module(self, generation_result: GenerationResult) -> Dict[str, Any]:
        """验证信任转化模块特定要求"""
        return self.trust_generator.validate_trust_requirements(generation_result)
    
    # Regeneration Management Methods
    
    def get_module_history(self, module_type: ModuleType) -> Optional[Dict[str, Any]]:
        """获取模块的版本历史"""
        session = self.state_manager.get_current_session()
        if not session:
            return None
        
        module_history = self.regeneration_service.get_module_history(session.session_id, module_type)
        if not module_history:
            return None
        
        return {
            "module_type": module_type.value,
            "total_versions": len(module_history.versions),
            "active_version_id": module_history.active_version_id,
            "original_version_id": module_history.original_version_id,
            "versions": [
                {
                    "version_id": v.version_id,
                    "creation_time": v.creation_timestamp.isoformat(),
                    "quality_score": v.generation_result.quality_score,
                    "validation_status": v.generation_result.validation_status.value,
                    "generation_time": v.generation_result.generation_time,
                    "user_rating": v.user_rating,
                    "user_notes": v.user_notes,
                    "is_active": v.is_active,
                    "is_original": v.version_id == module_history.original_version_id
                }
                for v in sorted(module_history.versions, key=lambda x: x.creation_timestamp, reverse=True)
            ]
        }
    
    def compare_versions(self, module_type: ModuleType, version_ids: List[str]) -> Dict[str, Any]:
        """比较模块的不同版本"""
        session = self.state_manager.get_current_session()
        if not session:
            return {"error": "没有活跃的会话"}
        
        return self.regeneration_service.get_version_comparison(
            session.session_id, module_type, version_ids
        )
    
    def set_active_version(self, module_type: ModuleType, version_id: str) -> bool:
        """设置模块的活跃版本"""
        session = self.state_manager.get_current_session()
        if not session:
            return False
        
        success = self.regeneration_service.set_active_version(
            session.session_id, module_type, version_id
        )
        
        if success:
            # 更新会话状态中的模块结果
            module_history = self.regeneration_service.get_module_history(session.session_id, module_type)
            if module_history:
                active_version = module_history.get_active_version()
                if active_version:
                    self.state_manager.update_module_result(module_type, active_version.generation_result)
        
        return success
    
    def rate_version(self, module_type: ModuleType, version_id: str, rating: float, notes: Optional[str] = None) -> bool:
        """为版本评分"""
        session = self.state_manager.get_current_session()
        if not session:
            return False
        
        return self.regeneration_service.rate_version(
            session.session_id, module_type, version_id, rating, notes
        )
    
    def get_regeneration_suggestions(self, module_type: ModuleType) -> List[Dict[str, Any]]:
        """获取重新生成建议"""
        session = self.state_manager.get_current_session()
        if not session:
            return []
        
        return self.regeneration_service.get_regeneration_suggestions(session.session_id, module_type)
    
    def export_module_history(self, module_type: ModuleType) -> Optional[Dict[str, Any]]:
        """导出模块历史记录"""
        session = self.state_manager.get_current_session()
        if not session:
            return None
        
        return self.regeneration_service.export_module_history(session.session_id, module_type)
    
    def cleanup_old_versions(self, days_to_keep: int = 7):
        """清理旧版本"""
        session = self.state_manager.get_current_session()
        if session:
            self.regeneration_service.cleanup_old_versions(session.session_id, days_to_keep)
    
    # Error Handling and Recovery Methods
    
    def handle_critical_error(self, error: Exception, context: str = ""):
        """处理关键错误"""
        error_msg = f"Critical error in {context}: {str(error)}"
        logger.critical(error_msg)
        
        # 尝试保存当前状态
        try:
            self.state_manager.emergency_save()
        except Exception as save_error:
            logger.error(f"Failed to emergency save state: {str(save_error)}")
        
        # 显示用户友好的错误信息
        st.error("系统遇到严重错误，正在尝试恢复...")
        
        # 尝试恢复到安全状态
        if self.error_recovery_enabled:
            try:
                self.recover_to_safe_state()
                st.success("系统已恢复到安全状态")
            except Exception as recovery_error:
                logger.error(f"Failed to recover to safe state: {str(recovery_error)}")
                st.error("系统恢复失败，请刷新页面重新开始")
    
    def recover_to_safe_state(self):
        """恢复到安全状态"""
        try:
            # 重置所有进行中的生成状态
            session = self.state_manager.get_current_session()
            if session:
                for module_type, status in session.generation_status.items():
                    if status == GenerationStatus.IN_PROGRESS:
                        session.generation_status[module_type] = GenerationStatus.NOT_STARTED
                        logger.info(f"Reset {module_type.value} status from IN_PROGRESS to NOT_STARTED")
                
                self.state_manager._save_session(session)
            
            logger.info("Successfully recovered to safe state")
            
        except Exception as e:
            logger.error(f"Failed to recover to safe state: {str(e)}")
            raise
    
    def get_system_health_status(self) -> Dict[str, Any]:
        """获取系统健康状态"""
        try:
            session = self.state_manager.get_current_session()
            
            health_status = {
                "overall_status": "healthy",
                "session_status": "active" if session else "inactive",
                "services_status": {},
                "error_recovery_enabled": self.error_recovery_enabled,
                "last_check": datetime.now().isoformat()
            }
            
            # 检查各个服务的状态
            services = [
                ("analysis_service", self.analysis_service),
                ("prompt_service", self.prompt_service),
                ("image_service", self.image_service),
                ("validation_service", self.validation_service)
            ]
            
            for service_name, service in services:
                try:
                    # 简单的健康检查
                    if hasattr(service, 'health_check'):
                        health_status["services_status"][service_name] = service.health_check()
                    else:
                        health_status["services_status"][service_name] = "available"
                except Exception as e:
                    health_status["services_status"][service_name] = f"error: {str(e)}"
                    health_status["overall_status"] = "degraded"
            
            # 检查会话完整性
            if session:
                integrity_check = self._validate_session_integrity(session)
                health_status["session_integrity"] = "valid" if integrity_check else "invalid"
                if not integrity_check:
                    health_status["overall_status"] = "degraded"
            
            return health_status
            
        except Exception as e:
            logger.error(f"Health status check failed: {str(e)}")
            return {
                "overall_status": "error",
                "error": str(e),
                "last_check": datetime.now().isoformat()
            }
    
    def enable_error_recovery(self, enabled: bool = True):
        """启用或禁用错误恢复"""
        self.error_recovery_enabled = enabled
        logger.info(f"Error recovery {'enabled' if enabled else 'disabled'}")
    
    def set_retry_configuration(self, max_attempts: int = 3, delay: float = 1.0):
        """设置重试配置"""
        self.max_retry_attempts = max(1, min(10, max_attempts))  # 限制在1-10之间
        self.retry_delay = max(0.1, min(10.0, delay))  # 限制在0.1-10秒之间
        logger.info(f"Retry configuration updated: max_attempts={self.max_retry_attempts}, delay={self.retry_delay}")
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """获取错误统计信息"""
        # 这里可以实现错误统计逻辑
        # 暂时返回基本信息
        return {
            "retry_configuration": {
                "max_attempts": self.max_retry_attempts,
                "retry_delay": self.retry_delay
            },
            "error_recovery_enabled": self.error_recovery_enabled,
            "system_uptime": datetime.now().isoformat()
        }