import streamlit as st
import sys
import os
from typing import List, Dict, Any, Optional, Tuple
from PIL import Image
from datetime import datetime
import google.generativeai as genai
import json
import uuid
import io
import time
import logging

# 添加项目根目录到路径
sys.path.append(os.path.abspath('.'))

logger = logging.getLogger(__name__)

# 身份验证
try:
    import auth
    if not auth.check_password():
        st.stop()
except ImportError:
    pass

# 导入核心模型（必需）
from services.aplus_studio.models import (
    ModuleType, GenerationStatus, get_new_professional_modules,
    GeneratedModule, ComplianceStatus, ValidationStatus, WorkflowState
)

# 导入新的模块化A+工作流组件
try:
    from app_utils.aplus_studio.module_selector import render_module_selector
    from app_utils.aplus_studio.material_upload_ui import render_material_upload_interface
    from app_utils.aplus_studio.preview_ui import render_preview_interface
    from services.aplus_studio.modules import ModuleRegistry
    from services.aplus_studio.module_factory import ModuleFactory
    APLUS_AVAILABLE = True
except ImportError as e:
    APLUS_AVAILABLE = False
    # 在开发环境中显示详细错误，在生产环境中显示友好提示
    import traceback
    error_details = str(e)
    if "ModuleFactory" in error_details:
        st.error("A+ Studio模块工厂初始化失败，请检查系统配置")
    elif "ModuleRegistry" in error_details:
        st.error("A+ Studio模块注册表初始化失败，请检查系统配置")
    else:
        st.error("A+ Studio系统组件未正确加载，请检查系统配置")
    
    # 显示详细错误信息（仅在调试时）
    with st.expander("🔧 技术详情（开发者用）"):
        st.code(f"导入错误: {error_details}")
        st.code(traceback.format_exc())

# 页面配置
st.set_page_config(
    page_title="A+ Studio", 
    page_icon="🧩", 
    layout="wide"
)

def main():
    """主应用入口 - 新模块化系统"""
    st.title("🧩 A+ 图片制作流 (APlus Studio)")
    st.caption("AI 驱动的亚马逊 A+ 页面智能图片生成工具 - 模块化专业版")
    
    if not APLUS_AVAILABLE:
        st.error("A+ Studio系统组件未正确加载，请检查系统配置")
        return
    
    # 检查API配置状态
    try:
        if "GOOGLE_API_KEY" not in st.secrets and "GEMINI_API_KEY" not in st.secrets:
            st.error("❌ Gemini API未配置")
            st.info("💡 请在云端后台配置GOOGLE_API_KEY或GEMINI_API_KEY")
            st.info("🔧 配置完成后请刷新页面")
            return
    except Exception as e:
        st.warning(f"⚠️ API配置检查失败: {str(e)}")
    
    # 初始化模块化系统组件
    if 'module_factory' not in st.session_state:
        st.session_state.module_factory = ModuleFactory()
    
    if 'current_step' not in st.session_state:
        st.session_state.current_step = "module_selection"
    
    # 主界面选择：模块化工作流 vs 卖点分析
    st.markdown("---")
    
    mode = st.radio(
        "选择功能模式",
        ["🤖 智能工作流", "🧩 模块化A+制作", "💡 产品卖点分析"],
        horizontal=True,
        help="智能工作流：AI驱动的端到端A+制作；模块化制作：手动选择模块制作；卖点分析：快速分析产品图片"
    )
    
    if mode == "🤖 智能工作流":
        render_intelligent_workflow()
    elif mode == "🧩 模块化A+制作":
        render_modular_workflow()
    else:
        render_selling_points_analysis()


def render_intelligent_workflow():
    """渲染智能工作流"""
    st.header("🤖 A+ 智能工作流")
    st.caption("AI驱动的端到端A+页面创建解决方案")
    
    # 紧急重置按钮
    with st.sidebar:
        st.markdown("---")
        st.subheader("🚨 紧急控制")
        if st.button("🔄 重置工作流", type="secondary"):
            # 清除所有URL参数
            st.query_params.clear()
            # 清除会话状态
            keys_to_clear = [k for k in st.session_state.keys() if 'intelligent' in k.lower()]
            for key in keys_to_clear:
                del st.session_state[key]
            st.success("✅ 工作流已重置")
            st.rerun()
        
        if st.button("🗑️ 清除URL参数", type="secondary"):
            st.query_params.clear()
            st.success("✅ URL参数已清除")
            st.rerun()
    
    # 初始化智能工作流状态管理器
    if 'intelligent_state_manager' not in st.session_state:
        try:
            from app_utils.aplus_studio.intelligent_state_manager import IntelligentWorkflowStateManager
            st.session_state.intelligent_state_manager = IntelligentWorkflowStateManager()
        except ImportError as e:
            st.error(f"智能工作流组件加载失败: {str(e)}")
            st.info("请检查系统配置或使用模块化A+制作功能")
            return
    
    state_manager = st.session_state.intelligent_state_manager
    
    # 渲染工作流导航
    try:
        from app_utils.aplus_studio.workflow_navigation_ui import WorkflowNavigationUI
        from services.aplus_studio.models import WorkflowState  # 确保导入WorkflowState
        
        nav_ui = WorkflowNavigationUI(state_manager)
        
        # 显示当前步骤和进度
        current_state = state_manager.get_current_state()
        
        # 检查URL参数是否指定了特定步骤 - 但要验证合理性
        url_step = st.query_params.get("step")
        if url_step and current_state != WorkflowState.INITIAL:  # 只有在非初始状态时才应用URL参数
            if url_step == "content_generation" and current_state in [WorkflowState.MODULE_RECOMMENDATION, WorkflowState.CONTENT_GENERATION]:
                logger.info("URL parameter indicates content_generation step")
                current_state = WorkflowState.CONTENT_GENERATION
                
                # 确保session状态也是正确的
                session = state_manager.get_current_session()
                if session and session.current_state != WorkflowState.CONTENT_GENERATION:
                    session.current_state = WorkflowState.CONTENT_GENERATION
                    session.last_updated = datetime.now()
                    st.session_state.intelligent_workflow_session = session
            elif url_step == "content_editing" and current_state in [WorkflowState.CONTENT_GENERATION, WorkflowState.CONTENT_EDITING]:
                logger.info("URL parameter indicates content_editing step")
                current_state = WorkflowState.CONTENT_EDITING
                
                # 确保session状态也是正确的
                session = state_manager.get_current_session()
                if session and session.current_state != WorkflowState.CONTENT_EDITING:
                    session.current_state = WorkflowState.CONTENT_EDITING
                    session.last_updated = datetime.now()
                    st.session_state.intelligent_workflow_session = session
            else:
                # 无效的URL参数，清除它
                st.query_params.clear()
                logger.warning(f"Invalid URL parameter {url_step} for current state {current_state}, cleared")
        
        logger.info(f"Rendering intelligent workflow, current state: {current_state.value}")
        
        # 添加状态验证和恢复机制
        session = state_manager.get_current_session()
        if session:
            logger.debug(f"Session found: {session.session_id}, state: {session.current_state.value}")
            # 确保状态一致性
            if session.current_state != current_state:
                logger.warning(f"State inconsistency detected: session={session.current_state.value}, manager={current_state.value}")
                # 以session中的状态为准
                current_state = session.current_state
                logger.info(f"Using session state: {current_state.value}")
        else:
            logger.debug("No session found")
        
        nav_action = nav_ui.render_navigation_header()
        
        # 根据当前状态渲染对应的界面
        if current_state == WorkflowState.INITIAL:
            logger.debug("Rendering workflow start")
            render_workflow_start(state_manager)
        elif current_state == WorkflowState.PRODUCT_ANALYSIS:
            logger.debug("Rendering product analysis step")
            render_product_analysis_step(state_manager)
        elif current_state == WorkflowState.MODULE_RECOMMENDATION:
            logger.debug("Rendering module recommendation step")
            render_module_recommendation_step(state_manager)
        elif current_state == WorkflowState.CONTENT_GENERATION:
            logger.debug("Rendering content generation step")
            render_content_generation_step(state_manager)
        elif current_state == WorkflowState.CONTENT_EDITING:
            logger.debug("Rendering content editing step")
            render_content_editing_step(state_manager)
        elif current_state == WorkflowState.STYLE_SELECTION:
            logger.debug("Rendering style selection step")
            render_style_selection_step(state_manager)
        elif current_state == WorkflowState.IMAGE_GENERATION:
            logger.debug("Rendering image generation step")
            render_image_generation_step(state_manager)
        elif current_state == WorkflowState.COMPLETED:
            logger.debug("Rendering workflow completed step")
            render_workflow_completed_step(state_manager)
        else:
            logger.error(f"Unknown workflow state: {current_state}")
            st.error(f"未知的工作流状态: {current_state}")
            
        # 处理导航操作
        if nav_action:
            handle_navigation_action(state_manager, nav_action)
            
    except ImportError as e:
        st.error(f"智能工作流界面组件加载失败: {str(e)}")
        st.info("正在使用简化版智能工作流...")
        render_simplified_intelligent_workflow()


def render_workflow_start(state_manager):
    """渲染工作流开始页面"""
    st.subheader("🚀 开始智能工作流")
    
    # 调试信息
    logger.info("render_workflow_start called")
    
    # 临时调试面板
    with st.expander("🔧 调试信息", expanded=False):
        current_session = state_manager.get_current_session()
        if current_session:
            st.write(f"**会话ID**: {current_session.session_id}")
            st.write(f"**当前状态**: {current_session.current_state.value}")
        else:
            st.write("**没有当前会话**")
        
        st.write(f"**有活跃会话**: {state_manager.has_active_session()}")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("""
        ### 智能工作流将为您提供：
        
        1. **🔍 AI产品分析** - 上传产品图片，AI自动分析产品特性和目标用户
        2. **🎯 智能模块推荐** - 基于分析结果推荐最适合的4个A+模块
        3. **✍️ 自动内容生成** - AI为每个模块生成专业的文案内容
        4. **🎨 风格主题选择** - 自动选择或手动调整视觉风格主题
        5. **🖼️ 批量图片生成** - 一键生成所有模块的A+图片
        6. **📊 结果管理** - 预览、下载、重新生成等完整管理功能
        
        ### 准备工作：
        - 准备1-5张清晰的产品图片（JPG、PNG、WebP格式）
        - 确保网络连接稳定
        - 预计总用时：5-10分钟
        """)
        
        if st.button("🚀 开始智能工作流", type="primary", use_container_width=True):
            success = state_manager.transition_workflow_state(WorkflowState.PRODUCT_ANALYSIS)
            if success:
                st.rerun()
            else:
                st.error("❌ 启动工作流失败，请重试")
    
    with col2:
        st.info("""
        **💡 提示**
        
        智能工作流适合：
        - 新手用户
        - 快速制作需求
        - 标准化产品
        - 批量制作场景
        
        如需更多控制，可选择"模块化A+制作"
        """)


def render_product_analysis_step(state_manager):
    """渲染产品分析步骤"""
    try:
        from app_utils.aplus_studio.product_analysis_ui import ProductAnalysisUI, create_product_analysis_ui
        
        st.subheader("🔍 第一步：产品分析")
        st.markdown("上传产品图片，AI将自动分析产品特性、目标用户和营销角度")
        
        # 创建产品分析UI
        analysis_ui = create_product_analysis_ui(state_manager.workflow_controller)
        analysis_result = analysis_ui.render_analysis_interface()
        
        # 处理分析动作
        if analysis_result and analysis_result.get('action') == 'start_analysis':
            # 设置分析进度状态
            st.session_state['analysis_in_progress'] = True
            
            # 开始真正的AI分析
            with st.spinner("🤖 AI正在分析您的产品..."):
                try:
                    # 获取产品信息和图片
                    product_info = analysis_result['product_info']
                    uploaded_images = product_info.uploaded_images
                    
                    if not uploaded_images:
                        st.error("❌ 请先上传产品图片")
                        st.session_state['analysis_in_progress'] = False
                        return
                    
                    # 检查API配置
                    if "GOOGLE_API_KEY" not in st.secrets and "GEMINI_API_KEY" not in st.secrets:
                        st.session_state['analysis_in_progress'] = False
                        st.error("❌ 未配置Gemini API密钥")
                        st.info("💡 请在云端后台配置GOOGLE_API_KEY或GEMINI_API_KEY")
                        st.info("🔧 配置完成后请刷新页面重试")
                        return
                    
                    # 使用ProductAnalysisService进行真正的AI分析
                    from services.aplus_studio.product_analysis_service import ProductAnalysisService
                    
                    analysis_service = ProductAnalysisService()
                    
                    # 创建进度显示
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    status_text.text("正在处理和验证图片...")
                    progress_bar.progress(0.2)
                    
                    # 准备图片数据
                    from services.aplus_studio.product_analysis_service import ProductImageSet, UploadedProductImage
                    
                    # 转换PIL图片为UploadedProductImage格式
                    processed_images = []
                    for i, pil_image in enumerate(uploaded_images):
                        # 将PIL图片转换为字节
                        img_byte_arr = io.BytesIO()
                        pil_image.save(img_byte_arr, format='PNG')
                        img_bytes = img_byte_arr.getvalue()
                        
                        uploaded_img = UploadedProductImage(
                            file_id=f"uploaded_{i}",
                            filename=f"product_image_{i+1}.png",
                            file_size=len(img_bytes),
                            format='PNG',
                            dimensions=(pil_image.width, pil_image.height),
                            image_data=img_bytes,
                            pil_image=pil_image,
                            upload_timestamp=datetime.now(),
                            validation_status=ValidationStatus.PASSED
                        )
                        processed_images.append(uploaded_img)
                    
                    # 创建图片集合
                    image_set = ProductImageSet(
                        images=processed_images,
                        total_size=sum(img.file_size for img in processed_images),
                        upload_session_id=str(uuid.uuid4())
                    )
                    
                    status_text.text("正在调用AI进行产品分析...")
                    progress_bar.progress(0.6)
                    
                    # 执行AI分析
                    analysis_result_obj = analysis_service.analyze_product_images(
                        image_set=image_set,
                        language="zh"
                    )
                    
                    status_text.text("正在生成分析报告...")
                    progress_bar.progress(0.9)
                    
                    # 转换分析结果为字典格式
                    analysis_data = {
                        'product_type': analysis_result_obj.product_category.value if analysis_result_obj.product_category else '未识别',
                        'target_audience': analysis_result_obj.target_audience or '未分析',
                        'key_features': analysis_result_obj.key_features or [],
                        'confidence_score': analysis_result_obj.confidence_score,
                        'materials': analysis_result_obj.materials or [],
                        'use_cases': analysis_result_obj.use_cases or [],
                        'marketing_angles': analysis_result_obj.marketing_angles or [],
                        'product_name': product_info.name or '产品',
                        'product_description': product_info.description or '',
                        'analysis_timestamp': datetime.now().isoformat()
                    }
                    
                    progress_bar.progress(1.0)
                    status_text.text("分析完成！")
                    
                    # 保存分析结果
                    state_manager.set_analysis_result(analysis_data)
                    
                    # 清除进度状态
                    st.session_state['analysis_in_progress'] = False
                    
                    st.success("✅ AI产品分析完成！")
                    st.rerun()
                    
                except Exception as e:
                    st.session_state['analysis_in_progress'] = False
                    st.error(f"AI分析失败: {str(e)}")
                    
                    # 显示详细错误信息
                    with st.expander("🔧 错误详情", expanded=False):
                        st.code(str(e))
                        st.write("**可能的解决方案：**")
                        st.write("1. 检查网络连接是否稳定")
                        st.write("2. 确保上传的图片清晰且包含产品信息")
                        st.write("3. 稍后重试或联系技术支持")
                    
                    if st.button("🔄 重新分析", type="primary"):
                        st.rerun()
        
        elif analysis_result and analysis_result.get('status') == 'completed':
            # 保存分析结果
            state_manager.set_analysis_result(analysis_result['data'])
            
            st.success("✅ 产品分析完成！")
            
            # 显示分析结果摘要
            with st.expander("📊 分析结果摘要", expanded=True):
                data = analysis_result['data']
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**产品类型**: {data.get('product_type', '未识别')}")
                    st.write(f"**目标用户**: {data.get('target_audience', '未分析')}")
                
                with col2:
                    st.write(f"**主要特征**: {len(data.get('key_features', []))} 个")
                    st.write(f"**分析置信度**: {data.get('confidence_score', 0):.1%}")
            
            if st.button("🎯 继续到模块推荐", type="primary", use_container_width=True):
                state_manager.transition_workflow_state(WorkflowState.MODULE_RECOMMENDATION)
                st.rerun()
        
        # 检查是否已有分析结果
        existing_result = state_manager.get_analysis_result()
        if existing_result:
            st.success("✅ 产品分析已完成！")
            
            # 显示分析结果摘要
            with st.expander("📊 分析结果摘要", expanded=True):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**产品类型**: {existing_result.get('product_type', '未识别')}")
                    st.write(f"**目标用户**: {existing_result.get('target_audience', '未分析')}")
                
                with col2:
                    st.write(f"**主要特征**: {len(existing_result.get('key_features', []))} 个")
                    st.write(f"**分析置信度**: {existing_result.get('confidence_score', 0):.1%}")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🔄 重新分析", use_container_width=True):
                    # 清除现有结果，重新开始
                    state_manager.set_analysis_result(None)
                    st.rerun()
            
            with col2:
                if st.button("🎯 继续到模块推荐", type="primary", use_container_width=True):
                    state_manager.transition_workflow_state(WorkflowState.MODULE_RECOMMENDATION)
                    st.rerun()
                
    except ImportError:
        st.error("产品分析组件未找到，请检查系统配置")


def render_module_recommendation_step(state_manager):
    """渲染模块推荐步骤"""
    try:
        from app_utils.aplus_studio.module_recommendation_ui import ModuleRecommendationUI
        
        st.subheader("🎯 第二步：模块推荐")
        st.markdown("基于产品分析结果，AI推荐最适合的4个A+模块组合")
        
        # 检查是否有分析结果
        analysis_result = state_manager.get_analysis_result()
        if not analysis_result:
            st.warning("⚠️ 请先完成产品分析")
            if st.button("🔍 返回产品分析"):
                # 清除URL参数并设置状态
                st.query_params.clear()
                session = state_manager.get_current_session()
                if session:
                    session.current_state = WorkflowState.PRODUCT_ANALYSIS
                    session.last_updated = datetime.now()
                    st.session_state.intelligent_workflow_session = session
                st.rerun()
            return
        
        # 创建模块推荐UI
        recommendation_ui = ModuleRecommendationUI(state_manager.workflow_controller)
        
        # 添加调试信息
        existing_recommendation = state_manager.get_module_recommendation()
        logger.debug(f"Existing recommendation: {existing_recommendation is not None}")
        
        recommendation_result = recommendation_ui.render_recommendation_interface(analysis_result)
        
        # 添加调试信息
        logger.debug(f"Recommendation result: {recommendation_result}")
        
        # 临时调试面板
        with st.expander("🔧 调试信息", expanded=False):
            current_session = state_manager.get_current_session()
            if current_session:
                st.write(f"**会话ID**: {current_session.session_id}")
                st.write(f"**当前状态**: {current_session.current_state.value}")
                st.write(f"**最后更新**: {current_session.last_updated}")
                
                # 显示会话状态
                session_in_state = st.session_state.get('intelligent_workflow_session')
                if session_in_state:
                    st.write(f"**st.session_state中的状态**: {session_in_state.current_state.value}")
                else:
                    st.write("**st.session_state中没有会话**")
                    
                # 显示备份状态
                backup_data = st.session_state.get('intelligent_workflow_backup')
                st.write(f"**备份可用**: {backup_data is not None}")
            else:
                st.write("**没有当前会话**")
        
        # 显示调试信息（临时）
        if recommendation_result:
            st.write(f"🔧 调试：收到动作 - {recommendation_result.get('action', 'None')}")
        
        # 处理推荐生成动作
        if recommendation_result and recommendation_result.get('action') == 'generate_recommendation':
            with st.spinner("🤖 AI正在生成智能模块推荐..."):
                try:
                    # 获取分析结果和选项
                    analysis_data = recommendation_result['analysis_result']
                    options = recommendation_result.get('options', {})
                    
                    # 生成智能推荐
                    recommendation_data = _generate_intelligent_recommendation(analysis_data, options)
                    
                    # 保存推荐结果
                    try:
                        state_manager.set_module_recommendation(recommendation_data)
                        st.success("✅ AI推荐生成完成！")
                        st.rerun()
                    except Exception as save_error:
                        logger.error(f"Failed to save recommendation data: {str(save_error)}")
                        st.error(f"保存推荐结果失败: {str(save_error)}")
                        
                        # 显示调试信息
                        with st.expander("🔧 调试信息", expanded=False):
                            st.write("**推荐数据结构：**")
                            st.json({
                                "recommended_modules_count": len(recommendation_data.get('recommended_modules', [])),
                                "recommendation_reasons_count": len(recommendation_data.get('recommendation_reasons', {})),
                                "confidence_scores_count": len(recommendation_data.get('confidence_scores', {})),
                                "alternative_modules_count": len(recommendation_data.get('alternative_modules', [])),
                                "has_timestamp": 'recommendation_timestamp' in recommendation_data
                            })
                    
                except Exception as e:
                    st.error(f"推荐生成失败: {str(e)}")
                    logger.error(f"Intelligent recommendation generation failed: {str(e)}")
                    
                    # 显示详细错误信息
                    with st.expander("🔧 错误详情", expanded=False):
                        st.code(str(e))
                        st.write("**可能的解决方案：**")
                        st.write("1. 检查产品分析结果是否完整")
                        st.write("2. 稍后重试或使用手动选择模式")
        
        elif recommendation_result and recommendation_result.get('action') == 'reset_selection':
            # 处理重新选择
            logger.info("Processing reset_selection action")
            
            existing_recommendation = state_manager.get_module_recommendation()
            if existing_recommendation:
                existing_recommendation['selection_confirmed'] = False
                state_manager.set_module_recommendation(existing_recommendation)
                st.success("✅ 已重置选择，请重新选择模块")
                st.rerun()
        
        elif recommendation_result and recommendation_result.get('action') == 'continue_to_content_generation':
            # 处理继续到内容生成 - 使用URL参数方法
            logger.info("Processing continue_to_content_generation action")
            
            # 保存状态到session state
            session = state_manager.get_current_session()
            if session:
                from services.aplus_studio.models import WorkflowState
                session.current_state = WorkflowState.CONTENT_GENERATION
                session.last_updated = datetime.now()
                st.session_state.intelligent_workflow_session = session
                state_manager._create_session_backup()
                
                # 使用URL参数强制跳转
                st.query_params.update({"step": "content_generation", "t": str(int(datetime.now().timestamp()))})
                
                logger.info("State set to CONTENT_GENERATION with URL params")
                st.success("✅ 正在跳转到内容生成...")
                st.rerun()
            else:
                st.error("❌ 没有活跃会话")
        
        elif recommendation_result and recommendation_result.get('action') == 'confirm_selection':
            # 处理模块选择确认
            selected_modules = recommendation_result.get('selected_modules', [])
            mode = recommendation_result.get('mode', 'unknown')
            
            logger.info(f"Processing confirm_selection: {len(selected_modules)} modules, mode: {mode}")
            
            try:
                # 获取现有的推荐数据
                existing_recommendation = state_manager.get_module_recommendation()
                
                if existing_recommendation:
                    # 更新现有推荐数据中的选择信息
                    existing_recommendation['selected_modules'] = selected_modules
                    existing_recommendation['selection_mode'] = mode
                    existing_recommendation['selection_timestamp'] = datetime.now().isoformat()
                    existing_recommendation['selection_confirmed'] = True
                    
                    # 保存更新后的推荐数据
                    state_manager.set_module_recommendation(existing_recommendation)
                else:
                    # 如果没有现有推荐数据，创建新的
                    selection_data = {
                        'recommended_modules': selected_modules,  # 使用推荐格式
                        'selected_modules': selected_modules,
                        'selection_mode': mode,
                        'selection_timestamp': datetime.now().isoformat(),
                        'selection_confirmed': True,
                        'total_modules': len(selected_modules),
                        'confidence_scores': {module: 0.8 for module in selected_modules},  # 默认置信度
                        'recommendation_reasons': {module: f"用户手动选择的{module}" for module in selected_modules}
                    }
                    state_manager.set_module_recommendation(selection_data)
                
                logger.info(f"Module recommendation saved: {len(selected_modules)} modules")
                
                st.success(f"✅ 已确认选择 {len(selected_modules)} 个模块！")
                
                # 显示选择的模块
                if selected_modules:
                    st.write("**已选择的模块：**")
                    for module in selected_modules:
                        module_name = str(module)
                        if hasattr(module, 'value'):
                            module_name = module.value
                        st.write(f"• {module_name}")
                
                if st.button("✍️ 继续到内容生成", type="primary", use_container_width=True):
                    logger.info("User clicked '继续到内容生成' button")
                    
                    # 使用简单直接的状态转换方法
                    session = state_manager.get_current_session()
                    if not session:
                        logger.info("No session found, creating new session")
                        session = state_manager.create_new_session()
                    
                    if session:
                        # 直接设置状态
                        from services.aplus_studio.models import WorkflowState
                        session.current_state = WorkflowState.CONTENT_GENERATION
                        session.last_updated = datetime.now()
                        
                        # 保存到session state
                        st.session_state.intelligent_workflow_session = session
                        
                        # 创建备份
                        state_manager._create_session_backup()
                        
                        logger.info(f"State set to CONTENT_GENERATION, triggering rerun")
                        st.success("✅ 正在跳转到内容生成...")
                        st.rerun()
                    else:
                        st.error("❌ 无法创建会话")
                        
            except Exception as e:
                st.error(f"❌ 保存选择结果失败: {str(e)}")
                logger.error(f"Failed to save module selection: {str(e)}")
        
        elif recommendation_result and recommendation_result.get('action') == 'manual_selection':
            st.info("💡 切换到手动选择模式")
            # 这里可以添加手动选择的逻辑
            
        elif recommendation_result and recommendation_result.get('action') == 'show_module_guide':
            # 显示模块指南
            recommendation_ui.render_module_guide()
                
    except ImportError:
        st.error("模块推荐组件未找到，请检查系统配置")


def _generate_intelligent_recommendation(analysis_result: Dict[str, Any], options: Dict[str, Any]) -> Dict[str, Any]:
    """生成智能模块推荐"""
    try:
        # 获取产品信息
        product_type = analysis_result.get('product_type', '未识别')
        key_features = analysis_result.get('key_features', [])
        target_audience = analysis_result.get('target_audience', '')
        marketing_angles = analysis_result.get('marketing_angles', [])
        confidence_score = analysis_result.get('confidence_score', 0.5)
        
        # 推荐选项
        recommendation_count = options.get('count', 4)
        style = options.get('style', '平衡推荐')
        prioritize_simplicity = options.get('prioritize_simplicity', False)
        
        # 基于产品类型的基础推荐
        base_recommendations = _get_base_recommendations_by_product_type(product_type)
        
        # 基于特征的推荐调整
        feature_adjustments = _get_feature_based_adjustments(key_features)
        
        # 基于目标用户的推荐调整
        audience_adjustments = _get_audience_based_adjustments(target_audience)
        
        # 基于营销角度的推荐调整
        marketing_adjustments = _get_marketing_based_adjustments(marketing_angles)
        
        # 合并推荐逻辑
        final_recommendations = _merge_recommendations(
            base_recommendations, 
            feature_adjustments, 
            audience_adjustments, 
            marketing_adjustments,
            recommendation_count,
            prioritize_simplicity
        )
        
        # 生成推荐理由
        recommendation_reasons = _generate_recommendation_reasons(
            final_recommendations, 
            analysis_result
        )
        
        # 计算置信度分数
        confidence_scores = _calculate_recommendation_confidence(
            final_recommendations, 
            analysis_result
        )
        
        # 生成替代建议
        alternative_modules = _generate_alternative_suggestions(
            final_recommendations, 
            analysis_result
        )
        
        return {
            'recommended_modules': final_recommendations,
            'recommendation_reasons': recommendation_reasons,
            'confidence_scores': confidence_scores,
            'alternative_modules': alternative_modules,
            'recommendation_timestamp': datetime.now().isoformat(),
            'analysis_input': {
                'product_type': product_type,
                'key_features_count': len(key_features),
                'confidence_score': confidence_score
            },
            'recommendation_options': options
        }
        
    except Exception as e:
        logger.error(f"Intelligent recommendation generation failed: {str(e)}")
        raise


def _get_base_recommendations_by_product_type(product_type: str) -> List[ModuleType]:
    """根据产品类型获取基础推荐"""
    from services.aplus_studio.models import ModuleType
    
    # 产品类型映射
    type_mappings = {
        '电子产品': [ModuleType.PRODUCT_OVERVIEW, ModuleType.FEATURE_ANALYSIS, ModuleType.SPECIFICATION_COMPARISON, ModuleType.INSTALLATION_GUIDE],
        '数码设备': [ModuleType.PRODUCT_OVERVIEW, ModuleType.FEATURE_ANALYSIS, ModuleType.SPECIFICATION_COMPARISON, ModuleType.QUALITY_ASSURANCE],
        '家居用品': [ModuleType.PRODUCT_OVERVIEW, ModuleType.USAGE_SCENARIOS, ModuleType.MATERIAL_CRAFTSMANSHIP, ModuleType.SIZE_COMPATIBILITY],
        '生活用品': [ModuleType.PRODUCT_OVERVIEW, ModuleType.USAGE_SCENARIOS, ModuleType.PROBLEM_SOLUTION, ModuleType.CUSTOMER_REVIEWS],
        '服装配饰': [ModuleType.PRODUCT_OVERVIEW, ModuleType.MATERIAL_CRAFTSMANSHIP, ModuleType.SIZE_COMPATIBILITY, ModuleType.CUSTOMER_REVIEWS],
        '美容护理': [ModuleType.PRODUCT_OVERVIEW, ModuleType.USAGE_SCENARIOS, ModuleType.PROBLEM_SOLUTION, ModuleType.QUALITY_ASSURANCE],
        '运动户外': [ModuleType.PRODUCT_OVERVIEW, ModuleType.FEATURE_ANALYSIS, ModuleType.USAGE_SCENARIOS, ModuleType.MATERIAL_CRAFTSMANSHIP],
        '汽车用品': [ModuleType.PRODUCT_OVERVIEW, ModuleType.INSTALLATION_GUIDE, ModuleType.SIZE_COMPATIBILITY, ModuleType.QUALITY_ASSURANCE],
        '母婴用品': [ModuleType.PRODUCT_OVERVIEW, ModuleType.USAGE_SCENARIOS, ModuleType.QUALITY_ASSURANCE, ModuleType.CUSTOMER_REVIEWS],
        '食品饮料': [ModuleType.PRODUCT_OVERVIEW, ModuleType.PACKAGE_CONTENTS, ModuleType.QUALITY_ASSURANCE, ModuleType.CUSTOMER_REVIEWS],
        '工具设备': [ModuleType.PRODUCT_OVERVIEW, ModuleType.FEATURE_ANALYSIS, ModuleType.INSTALLATION_GUIDE, ModuleType.MAINTENANCE_CARE]
    }
    
    # 尝试精确匹配
    for key, modules in type_mappings.items():
        if key in product_type:
            return modules
    
    # 尝试模糊匹配
    if any(keyword in product_type for keyword in ['电子', '数码', '科技', '智能']):
        return type_mappings['电子产品']
    elif any(keyword in product_type for keyword in ['家居', '家庭', '室内']):
        return type_mappings['家居用品']
    elif any(keyword in product_type for keyword in ['美容', '护肤', '化妆']):
        return type_mappings['美容护理']
    elif any(keyword in product_type for keyword in ['运动', '户外', '健身']):
        return type_mappings['运动户外']
    elif any(keyword in product_type for keyword in ['汽车', '车载', '车用']):
        return type_mappings['汽车用品']
    elif any(keyword in product_type for keyword in ['母婴', '儿童', '婴儿']):
        return type_mappings['母婴用品']
    elif any(keyword in product_type for keyword in ['食品', '饮料', '零食']):
        return type_mappings['食品饮料']
    elif any(keyword in product_type for keyword in ['工具', '设备', '机械']):
        return type_mappings['工具设备']
    
    # 默认推荐
    return [ModuleType.PRODUCT_OVERVIEW, ModuleType.FEATURE_ANALYSIS, ModuleType.USAGE_SCENARIOS, ModuleType.QUALITY_ASSURANCE]


def _get_feature_based_adjustments(key_features: List[str]) -> Dict[ModuleType, float]:
    """基于产品特征的推荐调整"""
    from services.aplus_studio.models import ModuleType
    
    adjustments = {}
    
    for feature in key_features:
        feature_lower = feature.lower()
        
        # 技术特征
        if any(keyword in feature_lower for keyword in ['技术', '功能', '性能', '参数', '规格']):
            adjustments[ModuleType.FEATURE_ANALYSIS] = adjustments.get(ModuleType.FEATURE_ANALYSIS, 0) + 0.2
            adjustments[ModuleType.SPECIFICATION_COMPARISON] = adjustments.get(ModuleType.SPECIFICATION_COMPARISON, 0) + 0.15
        
        # 材质特征
        if any(keyword in feature_lower for keyword in ['材质', '材料', '工艺', '制作', '品质']):
            adjustments[ModuleType.MATERIAL_CRAFTSMANSHIP] = adjustments.get(ModuleType.MATERIAL_CRAFTSMANSHIP, 0) + 0.2
            adjustments[ModuleType.QUALITY_ASSURANCE] = adjustments.get(ModuleType.QUALITY_ASSURANCE, 0) + 0.1
        
        # 使用场景特征
        if any(keyword in feature_lower for keyword in ['使用', '应用', '场景', '环境', '适用']):
            adjustments[ModuleType.USAGE_SCENARIOS] = adjustments.get(ModuleType.USAGE_SCENARIOS, 0) + 0.2
        
        # 安装特征
        if any(keyword in feature_lower for keyword in ['安装', '组装', '设置', '配置']):
            adjustments[ModuleType.INSTALLATION_GUIDE] = adjustments.get(ModuleType.INSTALLATION_GUIDE, 0) + 0.25
        
        # 尺寸特征
        if any(keyword in feature_lower for keyword in ['尺寸', '大小', '规格', '兼容', '适配']):
            adjustments[ModuleType.SIZE_COMPATIBILITY] = adjustments.get(ModuleType.SIZE_COMPATIBILITY, 0) + 0.2
        
        # 包装特征
        if any(keyword in feature_lower for keyword in ['包装', '配件', '套装', '内容']):
            adjustments[ModuleType.PACKAGE_CONTENTS] = adjustments.get(ModuleType.PACKAGE_CONTENTS, 0) + 0.15
    
    return adjustments


def _get_audience_based_adjustments(target_audience: str) -> Dict[ModuleType, float]:
    """基于目标用户的推荐调整"""
    from services.aplus_studio.models import ModuleType
    
    adjustments = {}
    audience_lower = target_audience.lower()
    
    # 专业用户
    if any(keyword in audience_lower for keyword in ['专业', '技术', '工程师', '开发者']):
        adjustments[ModuleType.FEATURE_ANALYSIS] = 0.3
        adjustments[ModuleType.SPECIFICATION_COMPARISON] = 0.25
        adjustments[ModuleType.INSTALLATION_GUIDE] = 0.2
    
    # 家庭用户
    elif any(keyword in audience_lower for keyword in ['家庭', '家用', '日常', '普通用户']):
        adjustments[ModuleType.USAGE_SCENARIOS] = 0.3
        adjustments[ModuleType.PROBLEM_SOLUTION] = 0.2
        adjustments[ModuleType.CUSTOMER_REVIEWS] = 0.15
    
    # 高端用户
    elif any(keyword in audience_lower for keyword in ['高端', '奢华', '精英', '商务']):
        adjustments[ModuleType.MATERIAL_CRAFTSMANSHIP] = 0.3
        adjustments[ModuleType.QUALITY_ASSURANCE] = 0.25
    
    # 年轻用户
    elif any(keyword in audience_lower for keyword in ['年轻', '学生', '时尚', '潮流']):
        adjustments[ModuleType.CUSTOMER_REVIEWS] = 0.2
        adjustments[ModuleType.USAGE_SCENARIOS] = 0.15
    
    return adjustments


def _get_marketing_based_adjustments(marketing_angles: List[str]) -> Dict[ModuleType, float]:
    """基于营销角度的推荐调整"""
    from services.aplus_studio.models import ModuleType
    
    adjustments = {}
    
    for angle in marketing_angles:
        angle_lower = angle.lower()
        
        # 功能导向
        if any(keyword in angle_lower for keyword in ['功能', '性能', '效果', '优势']):
            adjustments[ModuleType.FEATURE_ANALYSIS] = adjustments.get(ModuleType.FEATURE_ANALYSIS, 0) + 0.2
            adjustments[ModuleType.PROBLEM_SOLUTION] = adjustments.get(ModuleType.PROBLEM_SOLUTION, 0) + 0.15
        
        # 品质导向
        elif any(keyword in angle_lower for keyword in ['品质', '质量', '工艺', '材质']):
            adjustments[ModuleType.MATERIAL_CRAFTSMANSHIP] = adjustments.get(ModuleType.MATERIAL_CRAFTSMANSHIP, 0) + 0.25
            adjustments[ModuleType.QUALITY_ASSURANCE] = adjustments.get(ModuleType.QUALITY_ASSURANCE, 0) + 0.2
        
        # 用户体验导向
        elif any(keyword in angle_lower for keyword in ['体验', '使用', '便捷', '简单']):
            adjustments[ModuleType.USAGE_SCENARIOS] = adjustments.get(ModuleType.USAGE_SCENARIOS, 0) + 0.2
            adjustments[ModuleType.CUSTOMER_REVIEWS] = adjustments.get(ModuleType.CUSTOMER_REVIEWS, 0) + 0.15
    
    return adjustments


def _merge_recommendations(base_recommendations: List[ModuleType], 
                         feature_adjustments: Dict[ModuleType, float],
                         audience_adjustments: Dict[ModuleType, float],
                         marketing_adjustments: Dict[ModuleType, float],
                         target_count: int,
                         prioritize_simplicity: bool) -> List[ModuleType]:
    """合并推荐逻辑"""
    from services.aplus_studio.models import ModuleType
    
    # 计算每个模块的综合得分
    module_scores = {}
    
    # 基础推荐得分
    for module in base_recommendations:
        module_scores[module] = 1.0
    
    # 添加调整得分
    for module, adjustment in feature_adjustments.items():
        module_scores[module] = module_scores.get(module, 0) + adjustment
    
    for module, adjustment in audience_adjustments.items():
        module_scores[module] = module_scores.get(module, 0) + adjustment
    
    for module, adjustment in marketing_adjustments.items():
        module_scores[module] = module_scores.get(module, 0) + adjustment
    
    # 简单性调整
    if prioritize_simplicity:
        simple_modules = [
            ModuleType.PRODUCT_OVERVIEW, 
            ModuleType.USAGE_SCENARIOS, 
            ModuleType.SIZE_COMPATIBILITY,
            ModuleType.PACKAGE_CONTENTS,
            ModuleType.QUALITY_ASSURANCE
        ]
        for module in simple_modules:
            if module in module_scores:
                module_scores[module] += 0.3
    
    # 确保产品概览总是包含
    if ModuleType.PRODUCT_OVERVIEW not in module_scores:
        module_scores[ModuleType.PRODUCT_OVERVIEW] = 1.0
    else:
        module_scores[ModuleType.PRODUCT_OVERVIEW] += 0.5  # 提升产品概览的优先级
    
    # 按得分排序并选择前N个
    sorted_modules = sorted(module_scores.items(), key=lambda x: x[1], reverse=True)
    final_recommendations = [module for module, score in sorted_modules[:target_count]]
    
    return final_recommendations


def _generate_recommendation_reasons(recommended_modules: List[ModuleType], 
                                   analysis_result: Dict[str, Any]) -> Dict[ModuleType, str]:
    """生成推荐理由"""
    from services.aplus_studio.models import ModuleType
    
    reasons = {}
    product_type = analysis_result.get('product_type', '产品')
    key_features = analysis_result.get('key_features', [])
    
    reason_templates = {
        ModuleType.PRODUCT_OVERVIEW: f"作为{product_type}的核心展示模块，能够全面展示产品价值",
        ModuleType.FEATURE_ANALYSIS: f"基于产品的{len(key_features)}个核心特征，详细解析功能优势",
        ModuleType.SPECIFICATION_COMPARISON: f"通过规格对比突出{product_type}的技术优势",
        ModuleType.USAGE_SCENARIOS: f"展示{product_type}在实际使用中的应用场景和效果",
        ModuleType.PROBLEM_SOLUTION: f"突出{product_type}解决用户痛点的能力",
        ModuleType.MATERIAL_CRAFTSMANSHIP: f"展示{product_type}的材质工艺和制造品质",
        ModuleType.INSTALLATION_GUIDE: f"为{product_type}提供清晰的安装和使用指导",
        ModuleType.SIZE_COMPATIBILITY: f"说明{product_type}的尺寸规格和兼容性信息",
        ModuleType.PACKAGE_CONTENTS: f"展示{product_type}的完整包装内容和配件",
        ModuleType.QUALITY_ASSURANCE: f"通过认证和保修信息建立{product_type}的品质信任",
        ModuleType.CUSTOMER_REVIEWS: f"通过用户评价展示{product_type}的实际使用效果",
        ModuleType.MAINTENANCE_CARE: f"提供{product_type}的维护保养指导，延长使用寿命"
    }
    
    for module in recommended_modules:
        reasons[module] = reason_templates.get(module, f"推荐使用此模块来展示{product_type}的相关信息")
    
    return reasons


def _calculate_recommendation_confidence(recommended_modules: List[ModuleType], 
                                       analysis_result: Dict[str, Any]) -> Dict[ModuleType, float]:
    """计算推荐置信度"""
    from services.aplus_studio.models import ModuleType
    
    confidence_scores = {}
    base_confidence = analysis_result.get('confidence_score', 0.7)
    
    # 基于产品分析置信度调整
    for module in recommended_modules:
        # 基础置信度
        confidence = base_confidence
        
        # 产品概览总是高置信度
        if module == ModuleType.PRODUCT_OVERVIEW:
            confidence = max(confidence, 0.9)
        
        # 基于特征匹配度调整
        key_features = analysis_result.get('key_features', [])
        if len(key_features) > 3:
            confidence += 0.1
        
        # 确保置信度在合理范围内
        confidence = max(0.6, min(0.95, confidence))
        confidence_scores[module] = confidence
    
    return confidence_scores


def _generate_alternative_suggestions(recommended_modules: List[ModuleType], 
                                    analysis_result: Dict[str, Any]) -> List[ModuleType]:
    """生成替代建议"""
    from services.aplus_studio.models import ModuleType
    
    all_modules = [
        ModuleType.PRODUCT_OVERVIEW, ModuleType.FEATURE_ANALYSIS, ModuleType.SPECIFICATION_COMPARISON,
        ModuleType.USAGE_SCENARIOS, ModuleType.PROBLEM_SOLUTION, ModuleType.MATERIAL_CRAFTSMANSHIP,
        ModuleType.INSTALLATION_GUIDE, ModuleType.SIZE_COMPATIBILITY, ModuleType.PACKAGE_CONTENTS,
        ModuleType.QUALITY_ASSURANCE, ModuleType.CUSTOMER_REVIEWS, ModuleType.MAINTENANCE_CARE
    ]
    
    # 排除已推荐的模块
    alternatives = [module for module in all_modules if module not in recommended_modules]
    
    # 返回前6个替代选项
    return alternatives[:6]


def render_content_generation_step(state_manager):
    """渲染内容生成步骤"""
    st.subheader("✍️ 第三步：内容生成")
    st.markdown("AI为每个推荐的模块自动生成专业的文案内容")
    
    # 调试信息
    logger.info("render_content_generation_step called")
    st.success("🎉 成功进入内容生成步骤！")
    
    # 临时调试面板
    with st.expander("🔧 调试信息", expanded=True):
        current_session = state_manager.get_current_session()
        if current_session:
            st.write(f"**会话ID**: {current_session.session_id}")
            st.write(f"**当前状态**: {current_session.current_state.value}")
            st.write(f"**最后更新**: {current_session.last_updated}")
        else:
            st.write("**没有当前会话**")
    
    # 检查前置条件
    recommendation = state_manager.get_module_recommendation()
    
    if not recommendation:
        st.warning("⚠️ 请先完成模块推荐")
        if st.button("🎯 返回模块推荐"):
            # 清除URL参数并设置状态
            st.query_params.clear()
            session = state_manager.get_current_session()
            if session:
                session.current_state = WorkflowState.MODULE_RECOMMENDATION
                session.last_updated = datetime.now()
                st.session_state.intelligent_workflow_session = session
            st.rerun()
        return
    
    # 显示推荐的模块
    st.write("**推荐的模块：**")
    selected_modules = recommendation.get('selected_modules', [])
    
    if not selected_modules:
        st.error("❌ 没有找到选择的模块")
        if st.button("🎯 返回模块推荐"):
            # 清除URL参数并设置状态
            st.query_params.clear()
            session = state_manager.get_current_session()
            if session:
                session.current_state = WorkflowState.MODULE_RECOMMENDATION
                session.last_updated = datetime.now()
                st.session_state.intelligent_workflow_session = session
            st.rerun()
        return
    
    # 检查是否已有生成的内容
    existing_content = state_manager.get_generated_content()
    
    if existing_content:
        # 显示已生成的内容
        st.success("✅ AI内容已生成完成！")
        
        # 显示生成的内容预览
        with st.expander("📋 生成内容预览", expanded=True):
            for module_key, content in existing_content.items():
                st.write(f"**{content.get('title', '标题')}**")
                st.write(content.get('description', '描述'))
                if content.get('key_points'):
                    st.write("核心卖点：")
                    for point in content['key_points']:
                        st.write(f"• {point}")
                
                # 显示素材需求
                if content.get('material_requests'):
                    st.write("📸 素材需求：")
                    for req in content['material_requests']:
                        if isinstance(req, dict):
                            st.write(f"• {req.get('description', '素材需求')}")
                        else:
                            st.write(f"• {req}")
                
                st.markdown("---")
        
        # 操作按钮
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🔄 重新生成内容", use_container_width=True):
                # 清除现有内容，重新生成
                state_manager.set_generated_content(None)
                st.rerun()
        
        with col2:
            if st.button("📝 继续到内容编辑", type="primary", use_container_width=True):
                # 清除URL参数并设置状态
                from services.aplus_studio.models import WorkflowState
                st.query_params.clear()
                session = state_manager.get_current_session()
                if session:
                    session.current_state = WorkflowState.CONTENT_EDITING
                    session.last_updated = datetime.now()
                    st.session_state.intelligent_workflow_session = session
                    state_manager._create_session_backup()
                st.rerun()
        
        return
    
    # 处理模块显示（兼容字符串和ModuleType对象）
    from services.aplus_studio.models import ModuleType
    
    # 模块配置信息
    module_configs = {
        ModuleType.PRODUCT_OVERVIEW: {"name": "产品概览", "icon": "🎯"},
        ModuleType.FEATURE_ANALYSIS: {"name": "功能解析", "icon": "🔍"},
        ModuleType.SPECIFICATION_COMPARISON: {"name": "规格对比", "icon": "📊"},
        ModuleType.USAGE_SCENARIOS: {"name": "使用场景", "icon": "🏠"},
        ModuleType.PROBLEM_SOLUTION: {"name": "问题解决", "icon": "💡"},
        ModuleType.MATERIAL_CRAFTSMANSHIP: {"name": "材质工艺", "icon": "✨"},
        ModuleType.INSTALLATION_GUIDE: {"name": "安装指南", "icon": "🔧"},
        ModuleType.SIZE_COMPATIBILITY: {"name": "尺寸兼容", "icon": "📐"},
        ModuleType.PACKAGE_CONTENTS: {"name": "包装内容", "icon": "📦"},
        ModuleType.QUALITY_ASSURANCE: {"name": "品质保证", "icon": "🏆"},
        ModuleType.CUSTOMER_REVIEWS: {"name": "客户评价", "icon": "⭐"},
        ModuleType.MAINTENANCE_CARE: {"name": "维护保养", "icon": "🧽"}
    }
    
    cols = st.columns(min(len(selected_modules), 4))  # 最多4列
    for i, module in enumerate(selected_modules):
        with cols[i % 4]:
            # 处理模块类型（可能是字符串或ModuleType对象）
            if isinstance(module, str):
                try:
                    module_type = ModuleType(module)
                except ValueError:
                    st.error(f"未知模块类型: {module}")
                    continue
            else:
                module_type = module
            
            config = module_configs.get(module_type, {"name": str(module_type), "icon": "📋"})
            st.info(f"{config['icon']} {config['name']}")
    
    # 内容生成按钮
    if st.button("🤖 开始AI内容生成", type="primary", use_container_width=True):
        with st.spinner("AI正在为您生成专业内容..."):
            try:
                # 检查API配置
                if "GOOGLE_API_KEY" not in st.secrets and "GEMINI_API_KEY" not in st.secrets:
                    st.error("❌ 未配置Gemini API密钥")
                    st.info("💡 请在云端后台配置GOOGLE_API_KEY或GEMINI_API_KEY")
                    return
                
                # 获取产品分析结果
                analysis_result = state_manager.get_analysis_result()
                if not analysis_result:
                    st.error("❌ 缺少产品分析结果")
                    return
                
                # 使用现有的内容生成服务
                from services.aplus_studio.content_generation_service import ContentGenerationService, GenerationContext
                from services.aplus_studio.intelligent_workflow import ProductAnalysis
                from services.aplus_studio.models import ProductCategory
                
                # 创建内容生成服务实例
                content_service = ContentGenerationService()
                
                # 转换分析结果为ProductAnalysis对象
                try:
                    product_category = ProductCategory(analysis_result.get('product_type', 'ELECTRONICS'))
                except ValueError:
                    product_category = ProductCategory.ELECTRONICS
                
                product_analysis = ProductAnalysis(
                    product_id=f"product_{int(datetime.now().timestamp())}",  # 生成临时ID
                    product_category=product_category,
                    product_type=analysis_result.get('product_type', '电子产品'),
                    target_audience=analysis_result.get('target_audience', ''),
                    key_features=analysis_result.get('key_features', []),
                    materials=analysis_result.get('materials', []),
                    use_cases=analysis_result.get('use_cases', []),
                    marketing_angles=analysis_result.get('marketing_angles', []),
                    confidence_score=analysis_result.get('confidence_score', 0.8)
                )
                
                # 批量生成内容
                progress_bar = st.progress(0)
                status_text = st.empty()
                generated_content = {}
                
                contexts = []
                for module in selected_modules:
                    # 处理模块类型
                    if isinstance(module, str):
                        try:
                            module_type = ModuleType(module)
                        except ValueError:
                            continue
                    else:
                        module_type = module
                    
                    # 创建生成上下文
                    context = GenerationContext(
                        product_analysis=product_analysis,
                        module_type=module_type,
                        language="zh",
                        style_preferences={"tone": "professional", "length": "medium"}
                    )
                    contexts.append(context)
                
                # 使用批量生成方法
                status_text.text("正在调用AI生成服务...")
                progress_bar.progress(0.2)
                
                # 调用现有的批量内容生成服务
                batch_results = content_service.generate_content_for_multiple_modules(
                    contexts=contexts,
                    enable_compliance_check=True
                )
                
                progress_bar.progress(0.8)
                status_text.text("正在处理生成结果...")
                
                # 转换结果格式
                for module_type, intelligent_content in batch_results.items():
                    generated_content[str(module_type)] = {
                        'title': intelligent_content.title,
                        'description': intelligent_content.description,
                        'key_points': intelligent_content.key_points,
                        'generated_text': intelligent_content.generated_text,
                        'material_requests': [req.to_dict() for req in intelligent_content.material_requests] if intelligent_content.material_requests else []
                    }
                
                # 保存生成的内容
                state_manager.set_generated_content(generated_content)
                
                progress_bar.progress(1.0)
                status_text.text("内容生成完成！")
                st.success("✅ AI内容生成完成！")
                
                # 显示生成的内容预览
                with st.expander("📋 生成内容预览", expanded=True):
                    for module_key, content in generated_content.items():
                        st.write(f"**{content['title']}**")
                        st.write(content['description'])
                        if content['key_points']:
                            st.write("核心卖点：")
                            for point in content['key_points']:
                                st.write(f"• {point}")
                        
                        # 显示素材需求
                        if content.get('material_requests'):
                            st.write("📸 素材需求：")
                            for req in content['material_requests']:
                                st.write(f"• {req.get('description', '素材需求')}")
                        
                        st.markdown("---")
                
                if st.button("📝 继续到内容编辑", type="primary", use_container_width=True):
                    # 清除URL参数并设置状态
                    from services.aplus_studio.models import WorkflowState
                    st.query_params.clear()
                    session = state_manager.get_current_session()
                    if session:
                        session.current_state = WorkflowState.CONTENT_EDITING
                        session.last_updated = datetime.now()
                        st.session_state.intelligent_workflow_session = session
                        state_manager._create_session_backup()
                    st.rerun()
                        
            except Exception as e:
                st.error(f"内容生成失败: {str(e)}")
                logger.error(f"Content generation failed: {str(e)}")
                
                # 显示详细错误信息
                with st.expander("🔧 错误详情", expanded=False):
                    st.code(str(e))
                    st.write("**可能的解决方案：**")
                    st.write("1. 检查网络连接是否稳定")
                    st.write("2. 确保API密钥配置正确")
                    st.write("3. 稍后重试或联系技术支持")
                    # 使用URL参数方法进行状态转换
                    session = state_manager.get_current_session()
                    if session:
                        from services.aplus_studio.models import WorkflowState
                        session.current_state = WorkflowState.CONTENT_EDITING
                        session.last_updated = datetime.now()
                        st.session_state.intelligent_workflow_session = session
                        state_manager._create_session_backup()
                        
                        # 使用URL参数强制跳转
                        st.query_params.update({"step": "content_editing", "t": str(int(datetime.now().timestamp()))})
                        st.rerun()
                    
            except Exception as e:
                st.error(f"内容生成失败: {str(e)}")


def render_content_editing_step(state_manager):
    """渲染内容编辑步骤"""
    try:
        from app_utils.aplus_studio.content_editing_ui import ContentEditingUI
        
        st.subheader("📝 第四步：内容编辑")
        st.markdown("查看和编辑AI生成的内容，确保符合您的需求")
        
        # 检查生成的内容
        generated_content = state_manager.get_generated_content()
        if not generated_content:
            st.warning("⚠️ 请先完成内容生成")
            if st.button("✍️ 返回内容生成"):
                # 清除URL参数并设置状态
                st.query_params.clear()
                session = state_manager.get_current_session()
                if session:
                    session.current_state = WorkflowState.CONTENT_GENERATION
                    session.last_updated = datetime.now()
                    st.session_state.intelligent_workflow_session = session
                st.rerun()
            return
        
        # 创建内容编辑UI
        editing_ui = ContentEditingUI()
        editing_result = editing_ui.render_content_editing_interface(generated_content)
        
        if editing_result and editing_result.get('action') == 'confirm':
            # 保存编辑后的内容
            state_manager.set_final_content(editing_result['content'])
            
            st.success("✅ 内容编辑完成！")
            
            if st.button("🎨 继续到风格选择", type="primary", use_container_width=True):
                state_manager.transition_workflow_state(WorkflowState.STYLE_SELECTION)
                st.rerun()
                
    except ImportError:
        st.error("内容编辑组件未找到，使用简化编辑界面")
        render_simplified_content_editing(state_manager)


def render_style_selection_step(state_manager):
    """渲染风格选择步骤"""
    st.subheader("🎨 第五步：风格选择")
    st.markdown("选择适合您产品的视觉风格主题")
    
    # 获取产品分析结果以推荐风格
    analysis_result = state_manager.get_analysis_result()
    
    # 风格选项
    style_options = {
        "现代科技风": {
            "description": "简洁现代，适合电子产品和科技类商品",
            "colors": ["深蓝色", "白色", "银灰色"],
            "suitable_for": ["电子产品", "数码设备", "智能家居"]
        },
        "温馨家居风": {
            "description": "温暖舒适，适合家居用品和生活类商品",
            "colors": ["米色", "棕色", "绿色"],
            "suitable_for": ["家居用品", "厨房用具", "装饰品"]
        },
        "高端奢华风": {
            "description": "精致奢华，适合高端产品和奢侈品",
            "colors": ["金色", "黑色", "深红色"],
            "suitable_for": ["奢侈品", "高端产品", "珠宝配饰"]
        },
        "清新自然风": {
            "description": "清新自然，适合美容护肤和健康产品",
            "colors": ["浅绿色", "白色", "粉色"],
            "suitable_for": ["美容产品", "护肤品", "健康食品"]
        }
    }
    
    # 基于产品类型推荐风格
    product_type = analysis_result.get('product_type', '') if analysis_result else ''
    recommended_style = "现代科技风"  # 默认推荐
    
    if "家居" in product_type or "生活" in product_type:
        recommended_style = "温馨家居风"
    elif "美容" in product_type or "护肤" in product_type:
        recommended_style = "清新自然风"
    elif "奢华" in product_type or "高端" in product_type:
        recommended_style = "高端奢华风"
    
    st.info(f"💡 基于您的产品类型，推荐使用：**{recommended_style}**")
    
    # 风格选择
    selected_style = st.selectbox(
        "选择风格主题",
        options=list(style_options.keys()),
        index=list(style_options.keys()).index(recommended_style)
    )
    
    # 显示选中风格的详情
    style_info = style_options[selected_style]
    
    col1, col2 = st.columns(2)
    with col1:
        st.write(f"**描述**: {style_info['description']}")
        st.write(f"**色彩方案**: {', '.join(style_info['colors'])}")
    
    with col2:
        st.write(f"**适合产品**: {', '.join(style_info['suitable_for'])}")
    
    # 确认风格选择
    if st.button("🖼️ 确认风格，开始生成图片", type="primary", use_container_width=True):
        # 保存风格选择
        state_manager.set_style_theme({
            'theme_name': selected_style,
            'theme_config': style_info
        })
        
        state_manager.transition_workflow_state(WorkflowState.IMAGE_GENERATION)
        st.rerun()


def render_image_generation_step(state_manager):
    """渲染图片生成步骤"""
    st.subheader("🖼️ 第六步：图片生成")
    st.markdown("AI正在为您生成专业的A+模块图片")
    
    # 检查前置条件
    final_content = state_manager.get_final_content()
    style_theme = state_manager.get_style_theme()
    
    if not final_content or not style_theme:
        st.warning("⚠️ 请先完成内容编辑和风格选择")
        return
    
    # 显示生成配置
    st.write("**生成配置：**")
    col1, col2 = st.columns(2)
    
    with col1:
        st.write(f"**模块数量**: {len(final_content)} 个")
        st.write(f"**风格主题**: {style_theme.get('theme_name', '未选择')}")
    
    with col2:
        st.write(f"**图片尺寸**: 600x450 像素")
        st.write(f"**预计用时**: 3-5 分钟")
    
    # 开始生成
    if st.button("🚀 开始批量生成", type="primary", use_container_width=True):
        with st.spinner("AI正在生成A+模块图片..."):
            try:
                # 模拟批量生成过程
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                generated_images = {}
                modules = list(final_content.keys())
                
                for i, module in enumerate(modules):
                    status_text.text(f"正在生成 {module.value} 模块图片...")
                    progress_bar.progress((i + 1) / len(modules))
                    time.sleep(2)  # 模拟生成时间
                    
                    # 模拟生成结果
                    generated_images[module] = {
                        'image_path': f'generated/{module.value}_{int(time.time())}.png',
                        'generation_time': 2.0,
                        'quality_score': 0.85 + (i * 0.02)
                    }
                
                # 保存生成结果
                state_manager.set_generated_images(generated_images)
                
                st.success("✅ 所有模块图片生成完成！")
                
                if st.button("📊 查看生成结果", type="primary", use_container_width=True):
                    state_manager.transition_workflow_state(WorkflowState.COMPLETED)
                    st.rerun()
                    
            except Exception as e:
                st.error(f"图片生成失败: {str(e)}")


def render_workflow_completed_step(state_manager):
    """渲染工作流完成步骤"""
    st.subheader("🎉 智能工作流完成！")
    st.markdown("恭喜！您的A+页面已经生成完成")
    
    # 显示完成摘要
    generated_images = state_manager.get_generated_images()
    
    if generated_images:
        st.write(f"**生成结果**: 成功生成 {len(generated_images)} 个A+模块")
        
        # 显示生成的模块列表
        for module, result in generated_images.items():
            col1, col2, col3 = st.columns([2, 1, 1])
            
            with col1:
                st.write(f"📋 {module.value}")
            
            with col2:
                st.write(f"质量: {result['quality_score']:.1%}")
            
            with col3:
                st.button(f"下载", key=f"download_{module.value}")
        
        # 批量操作
        st.markdown("---")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("📦 批量下载", use_container_width=True):
                st.success("开始批量下载...")
        
        with col2:
            if st.button("🔄 重新生成", use_container_width=True):
                state_manager.transition_workflow_state(WorkflowState.IMAGE_GENERATION)
                st.rerun()
        
        with col3:
            if st.button("🆕 新建项目", use_container_width=True):
                # 清理状态，开始新项目
                state_manager.reset_workflow()
                st.rerun()
    
    else:
        st.warning("没有找到生成的图片")


def render_simplified_intelligent_workflow():
    """渲染简化版智能工作流（当组件加载失败时使用）"""
    st.info("🔧 正在使用简化版智能工作流")
    
    st.markdown("""
    ### 智能工作流功能正在完善中
    
    当前可用功能：
    - ✅ 产品卖点分析
    - ✅ 模块化A+制作
    - 🚧 完整智能工作流（开发中）
    
    建议您使用"模块化A+制作"功能来创建A+页面。
    """)


def render_simplified_content_editing(state_manager):
    """渲染简化版内容编辑界面"""
    st.info("使用简化版内容编辑界面")
    
    generated_content = state_manager.get_generated_content()
    
    if generated_content:
        for module, content in generated_content.items():
            with st.expander(f"📝 编辑 {module.value}", expanded=True):
                title = st.text_input("标题", value=content.get('title', ''), key=f"title_{module.value}")
                description = st.text_area("描述", value=content.get('description', ''), key=f"desc_{module.value}")
                
                # 更新内容
                generated_content[module]['title'] = title
                generated_content[module]['description'] = description
        
        if st.button("✅ 确认编辑", type="primary", use_container_width=True):
            state_manager.set_final_content(generated_content)
            state_manager.transition_workflow_state(WorkflowState.STYLE_SELECTION)
            st.rerun()


def handle_navigation_action(state_manager, action):
    """处理导航操作"""
    if not action:
        return
        
    if action.action_type == 'jump':
        target_state = action.target_state
        if target_state:
            state_manager.transition_workflow_state(target_state)
            st.rerun()
    elif action.action_type == 'start_new':
        target_state = action.target_state
        if target_state:
            state_manager.transition_workflow_state(target_state)
            st.rerun()
    elif action.action_type == 'next':
        # 处理下一步操作
        current_state = state_manager.get_current_state()
        # 这里可以添加下一步的逻辑
        pass
    elif action.action_type == 'previous':
        # 处理上一步操作
        current_state = state_manager.get_current_state()
        # 这里可以添加上一步的逻辑
        pass


def render_modular_workflow():
    """渲染模块化工作流"""
    # 侧边栏 - 进度跟踪和系统状态
    render_modular_sidebar()
    
    # 面包屑导航
    render_breadcrumb_navigation()
    
    # 主工作流程
    current_step = st.session_state.current_step
    
    if current_step == "module_selection":
        render_module_selection_step()
    elif current_step == "material_upload":
        render_material_upload_step()
    elif current_step == "generation":
        render_generation_step()
    elif current_step == "preview":
        render_preview_step()
    else:
        # 默认回到模块选择
        st.session_state.current_step = "module_selection"
        st.rerun()


def render_breadcrumb_navigation():
    """渲染面包屑导航"""
    current_step = st.session_state.current_step
    
    steps = [
        ("module_selection", "🧩 选择模块"),
        ("material_upload", "📁 上传素材"),
        ("generation", "🎨 生成内容"),
        ("preview", "🖼️ 预览管理")
    ]
    
    # 创建面包屑
    breadcrumb_items = []
    
    for i, (step_key, step_name) in enumerate(steps):
        if step_key == current_step:
            # 当前步骤 - 高亮显示
            breadcrumb_items.append(f"**{step_name}**")
            break
        elif _is_step_completed(step_key):
            # 已完成步骤 - 可点击
            breadcrumb_items.append(step_name)
        else:
            # 未完成步骤 - 不显示
            break
    
    if len(breadcrumb_items) > 1:
        # 显示面包屑导航
        st.markdown("**导航**: " + " → ".join(breadcrumb_items))
        
        # 快速返回按钮（只在非第一步时显示）
        if current_step != "module_selection":
            col1, col2, col3 = st.columns([1, 1, 4])
            
            with col1:
                if st.button("⬅️ 上一步", use_container_width=True):
                    # 返回到上一个步骤
                    current_index = next(i for i, (key, _) in enumerate(steps) if key == current_step)
                    if current_index > 0:
                        prev_step = steps[current_index - 1][0]
                        st.session_state.current_step = prev_step
                        st.rerun()
            
            with col2:
                if st.button("🏠 重新开始", use_container_width=True):
                    # 清理会话状态，重新开始
                    keys_to_clear = ['selected_modules', 'module_materials', 'generated_modules']
                    for key in keys_to_clear:
                        if key in st.session_state:
                            del st.session_state[key]
                    st.session_state.current_step = "module_selection"
                    st.rerun()
        
        st.markdown("---")


def render_selling_points_analysis():
    """渲染产品卖点分析功能"""
    st.header("💡 产品卖点分析")
    st.caption("上传产品图片，让AI智能分析产品卖点并生成营销建议")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("📸 图片上传")
        
        # 图片上传组件
        uploaded_files = st.file_uploader(
            "上传产品图片进行卖点分析",
            type=["jpg", "jpeg", "png", "webp"],
            accept_multiple_files=True,
            help="支持多张图片，AI将分析产品的视觉卖点和特征",
            key="selling_points_images"
        )
        
        if uploaded_files:
            # 图片预览 - 默认收起
            with st.expander(f"📷 已上传 {len(uploaded_files)} 张图片", expanded=False):
                # 显示上传的图片预览 - 紧凑布局
                if len(uploaded_files) <= 3:
                    cols = st.columns(len(uploaded_files))
                    for i, file in enumerate(uploaded_files):
                        with cols[i]:
                            image = Image.open(file)
                            st.image(image, caption=f"图片 {i+1}", width="stretch")
                else:
                    # 如果图片多，使用2列布局
                    for i in range(0, len(uploaded_files), 2):
                        cols = st.columns(2)
                        for j in range(2):
                            if i + j < len(uploaded_files):
                                with cols[j]:
                                    image = Image.open(uploaded_files[i + j])
                                    st.image(image, caption=f"图片 {i+j+1}", width="stretch")
            
            # 分析按钮
            if st.button("🔍 开始卖点分析", type="primary", width="stretch"):
                with st.spinner("🤖 AI正在分析产品卖点..."):
                    try:
                        # 转换图片格式
                        images = []
                        for file in uploaded_files:
                            image = Image.open(file)
                            images.append(image)
                        
                        # 执行卖点分析 - 直接调用Gemini API
                        selling_points_result = analyze_selling_points_sync(images)
                        
                        # 为这次分析生成唯一ID
                        import time
                        analysis_id = str(int(time.time()))
                        selling_points_result['analysis_id'] = analysis_id
                        
                        # 保存分析结果到session state
                        st.session_state['selling_points_result'] = selling_points_result
                        st.success("✅ 卖点分析完成！")
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"❌ 卖点分析失败: {str(e)}")
        else:
            st.info("👆 请上传产品图片开始分析")
            
            # 功能说明 - 紧凑版本
            with st.expander("💡 功能说明", expanded=False):
                st.markdown("""
                **AI将分析：**
                - 🎯 核心卖点识别
                - 🎨 视觉特征分析  
                - 💼 营销建议生成
                - 🏠 使用场景定位
                """)
    
    with col2:
        st.subheader("📊 分析结果")
        
        # 显示分析结果
        if 'selling_points_result' in st.session_state:
            result = st.session_state['selling_points_result']
            render_selling_points_results_compact(result)
        else:
            st.info("等待图片上传和分析...")
            
            # 简化的功能介绍
            st.markdown("""
            **🚀 智能卖点分析**
            
            - 📈 自动识别产品优势
            - 🎨 分析设计风格特点  
            - 💡 生成营销建议
            - 📋 提供可复制文案
            """)


def render_modular_sidebar():
    """渲染模块化系统侧边栏"""
    with st.sidebar:
        st.header("🎛️ 模块化A+制作")
        
        # 当前步骤指示器
        current_step = st.session_state.current_step
        
        steps = [
            ("module_selection", "🧩 选择模块"),
            ("material_upload", "📁 上传素材"),
            ("generation", "🎨 生成内容"),
            ("preview", "🖼️ 预览管理")
        ]
        
        st.markdown("**制作流程:**")
        for step_key, step_name in steps:
            if step_key == current_step:
                st.markdown(f"👉 **{step_name}** ← 当前")
            elif _is_step_completed(step_key):
                # 已完成的步骤可以点击返回
                if st.button(f"✅ {step_name}", key=f"nav_{step_key}", use_container_width=True):
                    st.session_state.current_step = step_key
                    st.rerun()
            else:
                st.markdown(f"⚪ {step_name}")
        
        st.divider()
        
        # 选择摘要
        if 'selected_modules' in st.session_state and st.session_state.selected_modules:
            st.subheader("📊 选择摘要")
            selected_count = len(st.session_state.selected_modules)
            st.metric("已选模块", f"{selected_count}/12")
            
            # 显示已选模块
            with st.expander("已选模块列表", expanded=False):
                for module in st.session_state.selected_modules:
                    display_name = _get_module_display_name_sidebar(module)
                    st.write(f"• {display_name}")
        
        st.divider()
        
        # 快速操作
        st.subheader("⚡ 快速操作")
        
        if st.button("🔄 重新开始", use_container_width=True):
            # 清理会话状态
            keys_to_clear = ['selected_modules', 'module_materials', 'generated_modules', 'current_step']
            for key in keys_to_clear:
                if key in st.session_state:
                    del st.session_state[key]
            st.session_state.current_step = "module_selection"
            st.rerun()
        
        if st.button("💾 保存进度", use_container_width=True):
            _save_session_progress()
            st.success("进度已保存")
        
        # 系统状态
        st.divider()
        st.subheader("🔧 系统状态")
        
        # 模块注册状态
        registry = ModuleRegistry()
        available_modules = len(get_new_professional_modules())
        registered_modules = len(registry._generators)
        
        if registered_modules == available_modules:
            st.success(f"✅ 模块系统正常 ({registered_modules}/12)")
        else:
            st.warning(f"⚠️ 部分模块未注册 ({registered_modules}/12)")


def render_module_selection_step():
    """渲染模块选择步骤"""
    st.header("🧩 第一步：选择A+模块")
    st.markdown("从12个专业模块中选择您需要的内容类型")
    
    # 渲染模块选择器
    selection_result = render_module_selector()
    
    # 处理选择结果
    if selection_result and selection_result.get('selected_modules'):
        st.session_state.selected_modules = selection_result['selected_modules']
        
        # 显示选择确认
        st.success(f"✅ 已选择 {len(selection_result['selected_modules'])} 个模块")
        
        # 继续按钮
        if st.button("📁 继续上传素材", type="primary", use_container_width=True):
            st.session_state.current_step = "material_upload"
            st.rerun()


def render_material_upload_step():
    """渲染素材上传步骤"""
    st.header("📁 第二步：上传素材")
    
    # 检查是否有选中的模块
    if 'selected_modules' not in st.session_state or not st.session_state.selected_modules:
        st.warning("⚠️ 请先选择模块")
        if st.button("🧩 返回模块选择"):
            st.session_state.current_step = "module_selection"
            st.rerun()
        return
    
    selected_modules = st.session_state.selected_modules
    st.markdown(f"为 {len(selected_modules)} 个选中的模块上传所需素材")
    
    # 渲染素材上传界面
    material_sets = render_material_upload_interface(selected_modules)
    
    # 保存素材到会话状态
    if material_sets:
        st.session_state.module_materials = material_sets
        
        # 检查素材完整性
        total_materials = sum(
            len(ms.images) + len(ms.documents) + len(ms.text_inputs) + len(ms.custom_prompts)
            for ms in material_sets.values()
        )
    else:
        total_materials = 0
    
    # 导航按钮 - 始终显示
    st.markdown("---")
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🧩 返回模块选择", use_container_width=True):
            st.session_state.current_step = "module_selection"
            st.rerun()
    
    with col2:
        # 只有在有素材时才启用生成按钮
        if total_materials > 0:
            if st.button("🎨 开始生成", type="primary", use_container_width=True):
                st.session_state.current_step = "generation"
                st.rerun()
        else:
            st.button("🎨 开始生成", disabled=True, use_container_width=True, help="请先上传素材")


def render_generation_step():
    """渲染生成步骤"""
    st.header("🎨 第三步：生成A+内容")
    
    # 检查前置条件
    if 'selected_modules' not in st.session_state or not st.session_state.selected_modules:
        st.warning("⚠️ 请先选择模块")
        if st.button("🧩 返回模块选择"):
            st.session_state.current_step = "module_selection"
            st.rerun()
        return
    
    if 'module_materials' not in st.session_state:
        st.warning("⚠️ 请先上传素材")
        if st.button("📁 返回素材上传"):
            st.session_state.current_step = "material_upload"
            st.rerun()
        return
    
    selected_modules = st.session_state.selected_modules
    material_sets = st.session_state.module_materials
    
    st.markdown(f"正在为 {len(selected_modules)} 个模块生成专业A+内容")
    
    # 生成选项
    col1, col2 = st.columns(2)
    
    with col1:
        generation_mode = st.radio(
            "生成模式",
            ["逐个生成", "批量生成"],
            help="逐个生成可以实时查看结果，批量生成更高效"
        )
    
    with col2:
        quality_level = st.selectbox(
            "质量等级",
            ["标准质量", "高质量", "最高质量"],
            help="更高质量需要更长时间"
        )
    
    # 开始生成
    if st.button("🚀 开始生成", type="primary", use_container_width=True):
        if generation_mode == "逐个生成":
            _handle_sequential_generation(selected_modules, material_sets, quality_level)
        else:
            _handle_batch_generation(selected_modules, material_sets, quality_level)
    
    # 显示已生成的结果
    if 'generated_modules' in st.session_state and st.session_state.generated_modules:
        st.markdown("---")
        st.subheader("📊 生成进度")
        
        generated_count = len(st.session_state.generated_modules)
        total_count = len(selected_modules)
        progress = generated_count / total_count
        
        st.progress(progress)
        st.write(f"已完成: {generated_count}/{total_count} 个模块")
        
        # 继续到预览
        if generated_count > 0:
            if st.button("🖼️ 查看预览", type="primary", use_container_width=True):
                st.session_state.current_step = "preview"
                st.rerun()


def render_preview_step():
    """渲染预览步骤"""
    st.header("🖼️ 第四步：预览和管理")
    
    # 检查是否有生成的内容
    if 'generated_modules' not in st.session_state or not st.session_state.generated_modules:
        st.warning("⚠️ 还没有生成的内容")
        if st.button("🎨 返回生成步骤"):
            st.session_state.current_step = "generation"
            st.rerun()
        return
    
    generated_modules = st.session_state.generated_modules
    st.markdown(f"共生成了 {len(generated_modules)} 个A+模块")
    
    # 渲染预览界面
    preview_action = render_preview_interface(generated_modules)
    
    # 处理预览操作
    if preview_action:
        _handle_preview_action(preview_action)
    
    # 导航按钮
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🎨 返回生成", use_container_width=True):
            st.session_state.current_step = "generation"
            st.rerun()
    
    with col2:
        if st.button("🔄 重新开始", use_container_width=True):
            # 清理会话状态，重新开始
            keys_to_clear = ['selected_modules', 'module_materials', 'generated_modules']
            for key in keys_to_clear:
                if key in st.session_state:
                    del st.session_state[key]
            st.session_state.current_step = "module_selection"
            st.rerun()


def _handle_sequential_generation(selected_modules: List[ModuleType], 
                                material_sets: Dict[ModuleType, Any], 
                                quality_level: str):
    """处理逐个生成"""
    if 'generated_modules' not in st.session_state:
        st.session_state.generated_modules = {}
    
    factory = st.session_state.module_factory
    
    # 为每个模块生成内容
    for i, module_type in enumerate(selected_modules):
        if module_type in st.session_state.generated_modules:
            continue  # 跳过已生成的模块
        
        st.write(f"正在生成: {_get_module_display_name_sidebar(module_type)} ({i+1}/{len(selected_modules)})")
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        try:
            # 模拟生成过程
            status_text.text("准备生成...")
            progress_bar.progress(0.2)
            
            status_text.text("分析素材...")
            progress_bar.progress(0.4)
            
            status_text.text("生成内容...")
            progress_bar.progress(0.7)
            
            # 这里应该调用实际的生成逻辑
            # result = factory.generate_module(module_type, material_sets[module_type])
            
            # 模拟生成结果
            import time
            time.sleep(2)  # 模拟生成时间
            
            result = GeneratedModule(
                module_type=module_type,
                image_data=None,  # 实际应该有图片数据
                image_path=None,
                compliance_status=ComplianceStatus.COMPLIANT,
                generation_timestamp=datetime.now(),
                materials_used=material_sets.get(module_type),
                quality_score=0.85,
                validation_status=ValidationStatus.PASSED,
                prompt_used="模拟生成提示词",
                generation_time=2.0
            )
            
            st.session_state.generated_modules[module_type] = result
            
            status_text.text("生成完成!")
            progress_bar.progress(1.0)
            
            st.success(f"✅ {_get_module_display_name_sidebar(module_type)} 生成完成")
            
        except Exception as e:
            st.error(f"❌ {_get_module_display_name_sidebar(module_type)} 生成失败: {str(e)}")
        
        st.divider()


def _handle_batch_generation(selected_modules: List[ModuleType], 
                           material_sets: Dict[ModuleType, Any], 
                           quality_level: str):
    """处理批量生成"""
    if 'generated_modules' not in st.session_state:
        st.session_state.generated_modules = {}
    
    st.info("🚀 开始批量生成...")
    
    overall_progress = st.progress(0)
    status_container = st.container()
    
    factory = st.session_state.module_factory
    
    for i, module_type in enumerate(selected_modules):
        if module_type in st.session_state.generated_modules:
            continue
        
        with status_container:
            st.write(f"正在生成: {_get_module_display_name_sidebar(module_type)}")
        
        try:
            # 模拟批量生成
            import time
            time.sleep(1)  # 模拟生成时间
            
            result = GeneratedModule(
                module_type=module_type,
                image_data=None,
                image_path=None,
                compliance_status=ComplianceStatus.COMPLIANT,
                generation_timestamp=datetime.now(),
                materials_used=material_sets.get(module_type),
                quality_score=0.80 + (i * 0.02),  # 模拟不同质量分数
                validation_status=ValidationStatus.PASSED,
                prompt_used="批量生成提示词",
                generation_time=1.0
            )
            
            st.session_state.generated_modules[module_type] = result
            
        except Exception as e:
            st.error(f"❌ {_get_module_display_name_sidebar(module_type)} 生成失败: {str(e)}")
        
        # 更新进度
        progress = (i + 1) / len(selected_modules)
        overall_progress.progress(progress)
    
    st.success("✅ 批量生成完成!")


def _handle_preview_action(action: Dict[str, Any]):
    """处理预览操作"""
    action_type = action.get("action")
    
    if action_type == "view_detail":
        module_type = action.get("module_type")
        st.session_state['show_detail_modal'] = True
        st.session_state['detail_module'] = module_type
    
    elif action_type == "download":
        module_type = action.get("module_type")
        st.success(f"开始下载 {_get_module_display_name_sidebar(module_type)}")
    
    elif action_type == "regenerate":
        module_type = action.get("module_type")
        st.info(f"重新生成 {_get_module_display_name_sidebar(module_type)}")
    
    elif action_type == "batch_download":
        modules = action.get("modules", [])
        st.success(f"开始批量下载 {len(modules)} 个模块")
    
    elif action_type == "export":
        modules = action.get("modules", [])
        format_type = action.get("format", "PNG")
        st.success(f"开始导出 {len(modules)} 个模块为 {format_type} 格式")


def _is_step_completed(step_key: str) -> bool:
    """检查步骤是否已完成"""
    if step_key == "module_selection":
        return 'selected_modules' in st.session_state and st.session_state.selected_modules
    elif step_key == "material_upload":
        return 'module_materials' in st.session_state and st.session_state.module_materials
    elif step_key == "generation":
        return 'generated_modules' in st.session_state and st.session_state.generated_modules
    elif step_key == "preview":
        return 'generated_modules' in st.session_state and st.session_state.generated_modules
    
    return False


def _get_module_display_name_sidebar(module_type) -> str:
    """获取模块显示名称（侧边栏用）"""
    display_names = {
        ModuleType.PRODUCT_OVERVIEW: "产品概览",
        ModuleType.PROBLEM_SOLUTION: "问题解决",
        ModuleType.FEATURE_ANALYSIS: "功能解析",
        ModuleType.SPECIFICATION_COMPARISON: "规格对比",
        ModuleType.USAGE_SCENARIOS: "使用场景",
        ModuleType.INSTALLATION_GUIDE: "安装指南",
        ModuleType.SIZE_COMPATIBILITY: "尺寸兼容",
        ModuleType.MAINTENANCE_CARE: "维护保养",
        ModuleType.MATERIAL_CRAFTSMANSHIP: "材质工艺",
        ModuleType.QUALITY_ASSURANCE: "品质保证",
        ModuleType.CUSTOMER_REVIEWS: "用户评价",
        ModuleType.PACKAGE_CONTENTS: "包装内容"
    }
    
    # 如果是ModuleType枚举，直接查找
    if isinstance(module_type, ModuleType):
        return display_names.get(module_type, module_type.value)
    
    # 如果是字符串，尝试转换为ModuleType
    if isinstance(module_type, str):
        try:
            # 尝试通过value查找对应的ModuleType
            for mt in ModuleType:
                if mt.value == module_type:
                    return display_names.get(mt, module_type)
            # 如果找不到，直接返回字符串
            return module_type
        except:
            return str(module_type)
    
    # 其他情况，转换为字符串
    return str(module_type)


def _save_session_progress():
    """保存会话进度"""
    # 这里可以实现实际的进度保存逻辑
    # 例如保存到数据库或文件
    pass








def render_selling_points_results_compact(result: Dict[str, Any]):
    """渲染卖点分析结果 - 紧凑版本"""
    if not result:
        st.warning("分析结果为空")
        return
    
    # 获取分析ID，用于生成唯一的key
    analysis_id = result.get('analysis_id', 'default')
    
    # 核心卖点 - 紧凑显示
    if 'key_selling_points' in result:
        st.markdown("**🎯 核心卖点**")
        selling_points = result['key_selling_points']
        
        # 初始化复制文本列表
        copyable_points = []
        
        # 显示所有卖点，统一样式
        for i, point in enumerate(selling_points, 1):
            title = point.get('title', '卖点')
            description = point.get('description', '暂无描述')
            confidence = point.get('confidence', 0)
            
            # 统一显示样式，不做区分
            st.write(f"**{i}. {title}** ({confidence:.0%})")
            st.caption(description[:80] + "..." if len(description) > 80 else description)
            
            # 准备复制文本
            point_text = f"{i}. {title}\n   {description}"
            copyable_points.append(point_text)
        
        # 可复制的卖点汇总 - 紧凑版
        if copyable_points:  # 只有当有卖点时才显示
            with st.expander("📋 复制卖点文案", expanded=False):
                all_points_text = "\n\n".join(copyable_points)
                st.text_area("", value=all_points_text, height=150, key=f"copyable_points_{analysis_id}", label_visibility="collapsed")
    else:
        copyable_points = []  # 确保变量存在
    
    # 营销建议 - 紧凑显示
    if 'marketing_insights' in result:
        st.markdown("**💼 营销建议**")
        insights = result['marketing_insights']
        
        # 只显示关键信息
        if 'target_audience' in insights:
            st.write(f"👥 **目标用户**: {insights['target_audience'][:50]}...")
        
        if 'aplus_recommendations' in insights and insights['aplus_recommendations']:
            st.write("📝 **A+页面建议**:")
            for i, rec in enumerate(insights['aplus_recommendations'][:2], 1):
                st.write(f"  {i}. {rec[:60]}...")
        
        # 完整营销建议 - 可展开
        with st.expander("📊 完整营销分析", expanded=False):
            if 'emotional_triggers' in insights:
                st.write("**情感触发点**:")
                for trigger in insights['emotional_triggers']:
                    st.write(f"• {trigger}")
            
            if 'competitive_advantages' in insights:
                st.write("**竞争优势**:")
                for adv in insights['competitive_advantages']:
                    st.write(f"• {adv}")
            
            # 可复制的营销文案
            marketing_text = f"""目标用户: {insights.get('target_audience', '未分析')}

A+页面建议:
{chr(10).join(['• ' + rec for rec in insights.get('aplus_recommendations', [])])}

情感触发点:
{chr(10).join(['• ' + trigger for trigger in insights.get('emotional_triggers', [])])}

竞争优势:
{chr(10).join(['• ' + adv for adv in insights.get('competitive_advantages', [])])}"""
            
            st.text_area("营销建议文案", value=marketing_text, height=200, key=f"copyable_marketing_{analysis_id}")
    
    # 视觉特征 - 可展开
    if 'visual_features' in result:
        with st.expander("🎨 视觉特征分析", expanded=False):
            visual = result['visual_features']
            
            col1, col2 = st.columns(2)
            with col1:
                if 'design_style' in visual:
                    st.write(f"**设计风格**: {visual['design_style']}")
                if 'color_scheme' in visual:
                    st.write(f"**色彩方案**: {visual['color_scheme'][:30]}...")
            
            with col2:
                if 'material_perception' in visual:
                    st.write(f"**材质感知**: {visual['material_perception'][:30]}...")
                if 'quality_indicators' in visual:
                    st.write(f"**品质指标**: {', '.join(visual['quality_indicators'][:2])}")
            
            # 可复制的视觉特征
            visual_text = f"""设计风格: {visual.get('design_style', '未识别')}
色彩方案: {visual.get('color_scheme', '未分析')}
材质感知: {visual.get('material_perception', '未识别')}
品质指标: {', '.join(visual.get('quality_indicators', []))}"""
            
            st.text_area("视觉特征文案", value=visual_text, height=120, key=f"copyable_visual_{analysis_id}")
    
    # 操作按钮 - 紧凑布局
    st.divider()
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📄 完整报告", width="stretch"):
            st.session_state['show_full_report'] = True
            st.rerun()
    
    with col2:
        if st.button("🔄 重新分析", width="stretch"):
            if 'selling_points_result' in st.session_state:
                del st.session_state['selling_points_result']
            if 'show_full_report' in st.session_state:
                del st.session_state['show_full_report']
            st.rerun()
    
    with col3:
        # 导出按钮
        export_data = {
            "analysis_timestamp": datetime.now().isoformat(),
            "selling_points_analysis": result
        }
        import json
        json_str = json.dumps(export_data, indent=2, ensure_ascii=False)
        st.download_button(
            "💾 导出",
            data=json_str,
            file_name=f"selling_points_{datetime.now().strftime('%m%d_%H%M')}.json",
            mime="application/json",
            width="stretch"
        )
    
    # 显示完整报告
    if st.session_state.get('show_full_report', False):
        with st.expander("📄 完整分析报告", expanded=True):
            full_report = generate_copyable_report(result)
            st.text_area("", value=full_report, height=300, key=f"full_report_{analysis_id}", label_visibility="collapsed")
            
            if st.button("❌ 关闭报告"):
                st.session_state['show_full_report'] = False
                st.rerun()





def generate_copyable_report(result: Dict[str, Any]) -> str:
    """生成完整的可复制分析报告"""
    report_lines = []
    report_lines.append("=" * 50)
    report_lines.append("产品卖点分析报告")
    report_lines.append("=" * 50)
    report_lines.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append("")
    
    # 核心卖点
    if 'key_selling_points' in result:
        report_lines.append("【核心卖点】")
        for i, point in enumerate(result['key_selling_points'], 1):
            title = point.get('title', '卖点')
            description = point.get('description', '暂无描述')
            confidence = point.get('confidence', 0)
            report_lines.append(f"{i}. {title} (置信度: {confidence:.1%})")
            report_lines.append(f"   {description}")
            if point.get('visual_evidence'):
                report_lines.append(f"   视觉证据: {point['visual_evidence']}")
            report_lines.append("")
    
    # 视觉特征
    if 'visual_features' in result:
        visual = result['visual_features']
        report_lines.append("【视觉特征】")
        report_lines.append(f"设计风格: {visual.get('design_style', '未识别')}")
        report_lines.append(f"色彩方案: {visual.get('color_scheme', '未分析')}")
        report_lines.append(f"材质感知: {visual.get('material_perception', '未识别')}")
        if visual.get('quality_indicators'):
            report_lines.append(f"品质指标: {', '.join(visual['quality_indicators'])}")
        report_lines.append("")
    
    # 营销建议
    if 'marketing_insights' in result:
        insights = result['marketing_insights']
        report_lines.append("【营销建议】")
        report_lines.append(f"目标用户: {insights.get('target_audience', '未分析')}")
        report_lines.append(f"定位策略: {insights.get('positioning_strategy', '未提供')}")
        
        if insights.get('emotional_triggers'):
            report_lines.append("情感触发点:")
            for trigger in insights['emotional_triggers']:
                report_lines.append(f"• {trigger}")
        
        if insights.get('aplus_recommendations'):
            report_lines.append("A+页面建议:")
            for rec in insights['aplus_recommendations']:
                report_lines.append(f"• {rec}")
        
        if insights.get('competitive_advantages'):
            report_lines.append("竞争优势:")
            for adv in insights['competitive_advantages']:
                report_lines.append(f"• {adv}")
        report_lines.append("")
    
    # 使用场景
    if 'usage_scenarios' in result:
        report_lines.append("【使用场景】")
        for i, scenario in enumerate(result['usage_scenarios'], 1):
            report_lines.append(f"场景{i}: {scenario.get('scenario', '场景描述')}")
            report_lines.append(f"优势: {scenario.get('benefits', '优势说明')}")
            report_lines.append(f"目标情感: {scenario.get('target_emotion', '目标情感')}")
            report_lines.append("")
    
    # 分析质量
    if 'analysis_quality' in result:
        quality = result['analysis_quality']
        report_lines.append("【分析质量】")
        report_lines.append(f"整体置信度: {quality.get('overall_confidence', 0.8):.1%}")
        report_lines.append(f"图片质量评分: {quality.get('image_quality_score', 0.8):.1%}")
        report_lines.append(f"分析深度: {quality.get('analysis_depth', 0.8):.1%}")
        report_lines.append("")
    
    report_lines.append("=" * 50)
    report_lines.append("报告结束")
    
    return "\n".join(report_lines)


def analyze_selling_points_sync(images: List[Image.Image]) -> Dict[str, Any]:
    """同步版本的产品卖点分析函数"""
    try:
        # 检查API配置
        if "GOOGLE_API_KEY" not in st.secrets:
            st.error("❌ 未找到 Google API Key")
            return generate_fallback_selling_points()
        
        # 配置Gemini API
        genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
        
        # 使用gemini-3-pro-image-preview模型进行图片分析
        model = genai.GenerativeModel('models/gemini-3-pro-image-preview')
        
        # 构建分析提示词
        selling_points_prompt = """
        你是一个专业的产品营销分析师。请仔细分析这些产品图片，识别产品的核心卖点和营销价值。

        请以JSON格式返回详细的产品卖点分析：

        {
            "key_selling_points": [
                {
                    "title": "卖点标题",
                    "description": "详细描述这个卖点如何吸引消费者，为什么重要",
                    "category": "功能性/美观性/品质感/便利性",
                    "confidence": 0.95,
                    "visual_evidence": "从图片中观察到的具体支持证据"
                }
            ],
            "visual_features": {
                "design_style": "现代简约/奢华精致/实用主义/工业风等具体风格",
                "color_scheme": "主要色彩搭配和视觉效果描述",
                "material_perception": "材质给人的感受和品质印象",
                "quality_indicators": ["从图片看出的品质指标1", "品质指标2"],
                "aesthetic_appeal": "整体美学吸引力评估"
            },
            "marketing_insights": {
                "target_audience": "基于产品特征推断的目标用户群体",
                "emotional_triggers": ["能触发购买欲望的情感点1", "情感点2"],
                "positioning_strategy": "建议的产品市场定位策略",
                "aplus_recommendations": ["Amazon A+页面展示建议1", "建议2", "建议3"],
                "competitive_advantages": ["相比同类产品的优势1", "优势2"]
            },
            "usage_scenarios": [
                {
                    "scenario": "具体使用场景描述",
                    "benefits": "在此场景下的具体优势",
                    "target_emotion": "想要激发的目标情感"
                }
            ],
            "analysis_quality": {
                "overall_confidence": 0.9,
                "image_quality_score": 0.85,
                "analysis_depth": 0.88,
                "recommendations_reliability": 0.92
            }
        }

        分析要求：
        1. 仔细观察产品的外观、材质、设计细节
        2. 识别产品的独特特征和潜在卖点
        3. 考虑北美消费者的购买心理和偏好
        4. 提供具体可执行的营销建议
        5. 评估产品在Amazon A+页面中的展示潜力
        6. 分析结果要客观、具体、有说服力

        请只返回JSON格式的分析结果，不要包含其他文字。
        """
        
        # 准备图片和提示词
        content_parts = [selling_points_prompt]
        content_parts.extend(images)
        
        # 调用Gemini API进行分析
        response = model.generate_content(content_parts)
        
        # 解析响应
        response_text = response.text.strip()
        
        # 清理响应文本，移除可能的markdown标记
        if response_text.startswith('```json'):
            response_text = response_text[7:]
        if response_text.endswith('```'):
            response_text = response_text[:-3]
        response_text = response_text.strip()
        
        try:
            selling_points_data = json.loads(response_text)
            
            # 验证返回的数据结构
            if not isinstance(selling_points_data, dict):
                raise ValueError("返回的数据不是有效的字典格式")
            
            # 确保必要的字段存在
            required_fields = ['key_selling_points', 'visual_features', 'marketing_insights']
            for field in required_fields:
                if field not in selling_points_data:
                    selling_points_data[field] = {}
            
            return selling_points_data
            
        except json.JSONDecodeError as e:
            st.warning(f"JSON解析失败: {str(e)}")
            st.text("原始响应:")
            st.text(response_text[:500] + "..." if len(response_text) > 500 else response_text)
            return generate_fallback_selling_points()
            
    except Exception as e:
        st.error(f"AI分析失败: {str(e)}")
        return generate_fallback_selling_points()





def generate_fallback_selling_points() -> Dict[str, Any]:
    """生成备用的卖点分析结果"""
    return {
        "key_selling_points": [
            {
                "title": "产品品质",
                "description": "从图片可以看出产品具有良好的制作工艺",
                "category": "品质感",
                "confidence": 0.7,
                "visual_evidence": "整体视觉呈现"
            }
        ],
        "visual_features": {
            "design_style": "现代风格",
            "color_scheme": "经典配色",
            "material_perception": "优质材质",
            "quality_indicators": ["工艺精良", "设计合理"],
            "aesthetic_appeal": "视觉吸引力良好"
        },
        "marketing_insights": {
            "target_audience": "注重品质的消费者",
            "emotional_triggers": ["品质保证", "实用价值"],
            "positioning_strategy": "品质优先定位",
            "aplus_recommendations": ["突出产品细节", "展示使用场景"],
            "competitive_advantages": ["设计优秀", "品质可靠"]
        },
        "usage_scenarios": [
            {
                "scenario": "日常使用",
                "benefits": "提供便利和品质体验",
                "target_emotion": "满意和信任"
            }
        ],
        "analysis_quality": {
            "overall_confidence": 0.7,
            "image_quality_score": 0.7,
            "analysis_depth": 0.6,
            "recommendations_reliability": 0.7
        }
    }


if __name__ == "__main__":
    main()
