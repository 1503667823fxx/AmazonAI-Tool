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
    GeneratedModule, ValidationStatus, WorkflowState
)

# 页面配置
st.set_page_config(
    page_title="A+ Studio", 
    page_icon="🧩", 
    layout="wide"
)

def main():
    """主应用入口 - 智能工作流专用版"""
    st.title("🧩 A+ 智能工作流 (APlus Studio)")
    st.caption("AI 驱动的亚马逊 A+ 页面智能图片生成工具")
    
    # 检查API配置状态
    try:
        if "GOOGLE_API_KEY" not in st.secrets and "GEMINI_API_KEY" not in st.secrets:
            st.error("❌ Gemini API未配置")
            st.info("💡 请在云端后台配置GOOGLE_API_KEY或GEMINI_API_KEY")
            st.info("🔧 配置完成后请刷新页面")
            return
    except Exception as e:
        st.warning(f"⚠️ API配置检查失败: {str(e)}")
    
    # 直接渲染智能工作流，移除其他功能选择
    render_intelligent_workflow()


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
            # 清除生成的图片数据
            if 'generated_images_data' in st.session_state:
                del st.session_state['generated_images_data']
            st.success("✅ 工作流已重置")
            st.rerun()
        
        if st.button("🗑️ 清除URL参数", type="secondary"):
            st.query_params.clear()
            st.success("✅ URL参数已清除")
            st.rerun()
        
        # 🎯 快速测试按钮 - 基于bug报告中的成功模式
        st.markdown("---")
        st.subheader("⚡ 快速测试")
        if st.button("⚡ 快速测试完成页面", type="primary"):
            # 创建虚拟的生成结果数据，包含4个模块
            mock_generated_images = {
                'PRODUCT_OVERVIEW': {
                    'image_path': 'mock/product_overview.png',
                    'generation_time': 2.3,
                    'quality_score': 0.92,
                    'success': True,
                    'has_image_data': True,
                    'module_name': 'Product Overview',
                    'generated_at': datetime.now().isoformat(),
                    'is_mock': True
                },
                'PROBLEM_SOLUTION': {
                    'image_path': 'mock/problem_solution.png',
                    'generation_time': 1.8,
                    'quality_score': 0.88,
                    'success': True,
                    'has_image_data': True,
                    'module_name': 'Problem Solution',
                    'generated_at': datetime.now().isoformat(),
                    'is_mock': True
                },
                'USAGE_SCENARIOS': {
                    'image_path': 'mock/usage_scenarios.png',
                    'generation_time': 2.1,
                    'quality_score': 0.85,
                    'success': True,
                    'has_image_data': True,
                    'module_name': 'Usage Scenarios',
                    'generated_at': datetime.now().isoformat(),
                    'is_mock': True
                },
                'QUALITY_ASSURANCE': {
                    'image_path': 'mock/quality_assurance.png',
                    'generation_time': 1.9,
                    'quality_score': 0.90,
                    'success': True,
                    'has_image_data': True,
                    'module_name': 'Quality Assurance',
                    'generated_at': datetime.now().isoformat(),
                    'is_mock': True
                }
            }
            
            # 直接保存到session state（使用成功的简化模式）
            st.session_state.generated_images_data = mock_generated_images
            st.session_state.generation_completed = True
            st.session_state.generation_timestamp = datetime.now().isoformat()
            
            # 设置URL参数跳转到完成状态
            from services.aplus_studio.models import WorkflowState
            timestamp = str(int(datetime.now().timestamp()))
            st.query_params.update({"step": "completed", "t": timestamp})
            
            st.success("✅ 快速测试数据已创建，正在跳转...")
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
        if url_step:  # 🎯 简化条件：只要有URL参数就处理
            logger.info(f"URL parameter detected: {url_step}, current_state: {current_state.value}")
            
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
            elif url_step == "completed":
                # 🎯 无条件强制跳转到COMPLETED状态
                logger.info(f"🎯 URL parameter indicates completed step, FORCING transition from {current_state.value}")
                current_state = WorkflowState.COMPLETED
                
                # 确保session状态也是正确的
                session = state_manager.get_current_session()
                if session:
                    session.current_state = WorkflowState.COMPLETED
                    session.last_updated = datetime.now()
                    st.session_state.intelligent_workflow_session = session
                    logger.info(f"Session state FORCED to COMPLETED")
                else:
                    # 如果没有session，创建一个新的
                    logger.info("No session found, creating new session for COMPLETED state")
                    session = state_manager.create_new_session()
                    session.current_state = WorkflowState.COMPLETED
                    session.last_updated = datetime.now()
                    st.session_state.intelligent_workflow_session = session
            else:
                # 只有在URL参数完全无效时才清除
                logger.warning(f"Invalid URL parameter {url_step} for current state {current_state.value}")
                # 不要清除completed参数，给状态转换更多机会
                if url_step not in ["content_generation", "content_editing", "completed"]:
                    st.query_params.clear()
                    logger.warning(f"Cleared invalid URL parameter: {url_step}")
                else:
                    # 对于已知的有效参数，保留它们
                    logger.info(f"Keeping valid URL parameter: {url_step}")
        
        logger.info(f"Rendering intelligent workflow, current state: {current_state.value}")
        
        # 临时调试面板 - 帮助诊断状态转换问题
        with st.expander("🔧 状态调试信息", expanded=False):
            st.write(f"**当前状态**: {current_state.value}")
            st.write(f"**URL参数**: {dict(st.query_params)}")
            
            session = state_manager.get_current_session()
            if session:
                st.write(f"**Session状态**: {session.current_state.value}")
                st.write(f"**Session ID**: {session.session_id}")
                st.write(f"**最后更新**: {session.last_updated}")
                
                # 显示生成的图片信息
                generated_images = state_manager.get_generated_images()
                simple_images = st.session_state.get('generated_images_data')
                
                st.write(f"**State Manager 图片**: {'有数据' if generated_images else '无数据'}")
                st.write(f"**Session State 图片**: {'有数据' if simple_images else '无数据'}")
            else:
                st.write("**Session**: 不存在")
        
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
        
        # 处理导航操作
        if nav_action:
            nav_ui.handle_navigation_action(nav_action)
        
        # 渲染导航操作按钮并处理
        nav_button_action = nav_ui.render_navigation_actions()
        if nav_button_action:
            nav_ui.handle_navigation_action(nav_button_action)
        
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
            
    except ImportError as e:
        st.error(f"智能工作流界面组件加载失败: {str(e)}")
        st.info("💡 请检查相关组件是否正确安装")
        st.stop()


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
            # 清除URL参数并设置状态
            from services.aplus_studio.models import WorkflowState
            st.query_params.clear()
            session = state_manager.get_current_session()
            if session:
                session.current_state = WorkflowState.PRODUCT_ANALYSIS
                session.last_updated = datetime.now()
                st.session_state.intelligent_workflow_session = session
                state_manager._create_session_backup()
                st.rerun()
            else:
                # 如果没有session，尝试创建新的工作流
                try:
                    success = state_manager.transition_workflow_state(WorkflowState.PRODUCT_ANALYSIS)
                    if success:
                        st.rerun()
                    else:
                        st.error("❌ 启动工作流失败，请重试")
                except Exception as e:
                    st.error(f"❌ 启动工作流失败：{str(e)}")
    
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
                # 清除URL参数并设置状态
                from services.aplus_studio.models import WorkflowState
                st.query_params.clear()
                session = state_manager.get_current_session()
                if session:
                    session.current_state = WorkflowState.MODULE_RECOMMENDATION
                    session.last_updated = datetime.now()
                    st.session_state.intelligent_workflow_session = session
                    state_manager._create_session_backup()
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
                    # 清除URL参数并设置状态
                    from services.aplus_studio.models import WorkflowState
                    st.query_params.clear()
                    session = state_manager.get_current_session()
                    if session:
                        session.current_state = WorkflowState.MODULE_RECOMMENDATION
                        session.last_updated = datetime.now()
                        st.session_state.intelligent_workflow_session = session
                        state_manager._create_session_backup()
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
                    
                    # 清除URL参数并设置状态
                    from services.aplus_studio.models import WorkflowState
                    st.query_params.clear()
                    session = state_manager.get_current_session()
                    if session:
                        session.current_state = WorkflowState.CONTENT_GENERATION
                        session.last_updated = datetime.now()
                        st.session_state.intelligent_workflow_session = session
                        state_manager._create_session_backup()
                    st.rerun()
                    
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
                    contexts=contexts
                )
                
                progress_bar.progress(0.8)
                status_text.text("正在处理生成结果...")
                
                # 转换结果格式并保存到session.module_contents
                session = state_manager.get_current_session()
                if session:
                    from services.aplus_studio.intelligent_workflow import ModuleContent, MaterialRequest
                    from services.aplus_studio.models import Priority
                    
                    # 确保selected_modules包含所有生成内容的模块
                    if not session.selected_modules:
                        session.selected_modules = list(batch_results.keys())
                    
                    successful_conversions = 0
                    for module_type, intelligent_content in batch_results.items():
                        try:
                            # 转换为页面显示格式
                            generated_content[str(module_type)] = {
                                'title': intelligent_content.title,
                                'description': intelligent_content.description,
                                'key_points': intelligent_content.key_points,
                                'generated_text': intelligent_content.generated_text,
                                'material_requests': [req.to_dict() for req in intelligent_content.material_requests] if intelligent_content.material_requests else []
                            }
                            
                            # 转换为ModuleContent并保存到session
                            material_requests = []
                            if intelligent_content.material_requests:
                                for req in intelligent_content.material_requests:
                                    try:
                                        material_requests.append(MaterialRequest(
                                            request_id=req.request_id,
                                            material_type=req.material_type,
                                            description=req.description,
                                            importance=req.importance,
                                            example=req.example,
                                            help_text=req.help_text
                                        ))
                                    except Exception as req_error:
                                        logger.warning(f"Failed to convert material request: {req_error}")
                                        # 创建一个简单的MaterialRequest
                                        material_requests.append(MaterialRequest(
                                            request_id=f"req_{len(material_requests)}",
                                            material_type="IMAGE",
                                            description=getattr(req, 'description', '素材需求'),
                                            importance=getattr(req, 'importance', Priority.MEDIUM),
                                            example=getattr(req, 'example', None),
                                            help_text=getattr(req, 'help_text', '')
                                        ))
                            
                            module_content = ModuleContent(
                                module_type=module_type,
                                title=intelligent_content.title,
                                description=intelligent_content.description,
                                key_points=intelligent_content.key_points,
                                generated_text=intelligent_content.generated_text,
                                material_requests=material_requests,
                                language=intelligent_content.language
                            )
                            
                            # 保存到session.module_contents
                            session.module_contents[module_type] = module_content
                            successful_conversions += 1
                            logger.info(f"Successfully saved content for module: {module_type.value}")
                            
                        except Exception as module_error:
                            logger.error(f"Failed to convert content for {module_type.value}: {module_error}")
                            # 创建一个基本的ModuleContent
                            basic_content = ModuleContent(
                                module_type=module_type,
                                title=f"{module_type.value} 内容",
                                description="AI生成的内容",
                                key_points=["功能特点", "产品优势", "使用便利"],
                                generated_text={"main_content": "产品介绍内容"},
                                material_requests=[],
                                language="zh"
                            )
                            session.module_contents[module_type] = basic_content
                            successful_conversions += 1
                    
                    # 更新session - 但要避免序列化问题
                    # 临时清空可能导致序列化问题的复杂对象
                    temp_module_contents = session.module_contents.copy()
                    temp_generation_results = session.generation_results.copy()
                    
                    # 清空这些字段以避免序列化问题
                    session.module_contents.clear()
                    session.generation_results.clear()
                    
                    try:
                        # 保存简化的session
                        state_manager._save_session(session)
                        logger.info(f"Session updated with {len(temp_module_contents)} modules (simplified for serialization)")
                    except Exception as save_error:
                        logger.error(f"Failed to save session: {save_error}")
                    finally:
                        # 恢复数据到内存中的session对象
                        session.module_contents.update(temp_module_contents)
                        session.generation_results.update(temp_generation_results)
                else:
                    st.error("❌ 无法获取当前session，数据保存失败")
                
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
        editing_ui = ContentEditingUI(state_manager.workflow_controller)
        
        # 检查是否需要切换到编辑模式（第一阶段）
        if 'switch_to_edit_mode' in st.session_state and st.session_state.switch_to_edit_mode:
            st.session_state.content_editing_mode = 'edit'
            st.session_state.switch_to_edit_mode = False  # 重置标志
            st.success("✅ 已切换到编辑模式")
            st.rerun()
        
        editing_result = editing_ui.render_content_editing_interface()
        
        if editing_result and editing_result.get('action'):
            action = editing_result.get('action')
            
            if action == 'switch_to_edit_mode':
                # 设置切换标志，下次运行时会切换模式（第二阶段）
                st.session_state.switch_to_edit_mode = True
                st.info("🔄 正在切换到编辑模式...")
                st.rerun()
                
            elif action == 'approve_all_content':
                # 审核通过，继续到下一步
                st.success("✅ 内容审核通过！")
                
                # 保存最终内容
                try:
                    session = state_manager.get_current_session()
                    if session and session.module_contents:
                        # 将module_contents转换为final_content格式并保存
                        final_content = {}
                        for module_type, content in session.module_contents.items():
                            # 转换MaterialRequest对象为字典
                            material_requests = []
                            if hasattr(content, 'material_requests') and content.material_requests:
                                for req in content.material_requests:
                                    if hasattr(req, '__dict__'):
                                        # 如果是对象，转换为字典
                                        req_dict = {
                                            'request_id': getattr(req, 'request_id', ''),
                                            'material_type': getattr(req, 'material_type', ''),
                                            'description': getattr(req, 'description', ''),
                                            'importance': getattr(req, 'importance', ''),
                                            'help_text': getattr(req, 'help_text', ''),
                                            'example': getattr(req, 'example', '')
                                        }
                                        # 处理枚举类型
                                        if hasattr(req.material_type, 'value'):
                                            req_dict['material_type'] = req.material_type.value
                                        if hasattr(req.importance, 'value'):
                                            req_dict['importance'] = req.importance.value
                                        material_requests.append(req_dict)
                                    else:
                                        # 如果已经是字典，直接使用
                                        material_requests.append(req)
                            
                            final_content[module_type.value] = {
                                'title': getattr(content, 'title', ''),
                                'description': getattr(content, 'description', ''),
                                'key_points': getattr(content, 'key_points', []),
                                'generated_text': getattr(content, 'generated_text', {}),
                                'material_requests': material_requests
                            }
                        
                        state_manager.set_final_content(final_content)
                        logger.info(f"Final content saved with {len(final_content)} modules")
                    else:
                        st.error("❌ 没有找到内容数据")
                        return
                except Exception as e:
                    st.error(f"❌ 保存最终内容失败：{str(e)}")
                    logger.error(f"Failed to save final content: {str(e)}")
                    return
                
                # 清除URL参数并设置状态
                from services.aplus_studio.models import WorkflowState
                st.query_params.clear()
                session = state_manager.get_current_session()
                if session:
                    session.current_state = WorkflowState.STYLE_SELECTION
                    session.last_updated = datetime.now()
                    st.session_state.intelligent_workflow_session = session
                    state_manager._create_session_backup()
                st.rerun()
                
            elif action == 'continue_editing':
                # 继续编辑，切换到编辑模式
                st.session_state.switch_to_edit_mode = True
                st.info("🔄 正在切换到编辑模式...")
                st.rerun()
                
            elif action == 'save_draft':
                # 保存草稿
                try:
                    session = state_manager.get_current_session()
                    if session:
                        state_manager._create_session_backup()
                        st.success("✅ 草稿已保存")
                    else:
                        st.error("❌ 保存失败：无活跃会话")
                except Exception as e:
                    st.error(f"❌ 保存失败：{str(e)}")
                    
            elif action == 'content_edited':
                # 内容已编辑，自动保存
                try:
                    module = editing_result.get('module')
                    content = editing_result.get('content')
                    if module and content:
                        session = state_manager.get_current_session()
                        if session:
                            session.module_contents[module] = content
                            
                            # 避免序列化问题的安全保存
                            temp_module_contents = session.module_contents.copy()
                            temp_generation_results = session.generation_results.copy()
                            
                            session.module_contents.clear()
                            session.generation_results.clear()
                            
                            try:
                                state_manager._save_session(session)
                                st.success(f"✅ {editing_ui._get_module_display_name(module)} 内容已保存")
                            except Exception as save_error:
                                st.error(f"❌ 保存失败：{str(save_error)}")
                            finally:
                                session.module_contents.update(temp_module_contents)
                                session.generation_results.update(temp_generation_results)
                except Exception as e:
                    st.error(f"❌ 保存失败：{str(e)}")
                    
            elif action == 'confirm':
                # 保存编辑后的内容
                state_manager.set_final_content(editing_result['content'])
                
                st.success("✅ 内容编辑完成！")
                
                if st.button("🎨 继续到风格选择", type="primary", use_container_width=True):
                    # 清除URL参数并设置状态
                    from services.aplus_studio.models import WorkflowState
                    st.query_params.clear()
                    session = state_manager.get_current_session()
                    if session:
                        session.current_state = WorkflowState.STYLE_SELECTION
                        session.last_updated = datetime.now()
                        st.session_state.intelligent_workflow_session = session
                        state_manager._create_session_backup()
                    st.rerun()
                    
            elif action == 'export_content':
                st.info("� 导出功能开发开中...")
                
            elif action == 'regenerate_content':
                st.info("🔄 重新生成功能开发中...")
                
    except ImportError:
        st.error("内容编辑组件未找到")
        st.info("💡 请检查 app_utils.aplus_studio.content_editing_ui 模块是否存在")
        st.stop()


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
        
        # 清除URL参数并设置状态
        from services.aplus_studio.models import WorkflowState
        st.query_params.clear()
        session = state_manager.get_current_session()
        if session:
            session.current_state = WorkflowState.IMAGE_GENERATION
            session.last_updated = datetime.now()
            st.session_state.intelligent_workflow_session = session
            state_manager._create_session_backup()
        st.rerun()


def render_image_generation_step(state_manager):
    """渲染图片生成步骤"""
    st.subheader("🖼️ 第六步：图片生成")
    st.markdown("AI正在为您生成专业的A+模块图片")
    
    # 添加调试信息
    with st.expander("🔍 调试信息", expanded=False):
        session = state_manager.get_current_session()
        if session:
            st.write(f"**Session ID**: {session.session_id}")
            st.write(f"**当前状态**: {session.current_state}")
            st.write(f"**Module Contents**: {len(session.module_contents) if session.module_contents else 0} 个模块")
            if session.module_contents:
                for module_type, content in session.module_contents.items():
                    st.write(f"  - {module_type.value}: {getattr(content, 'title', 'No title')}")
            
            final_content = state_manager.get_final_content()
            st.write(f"**Final Content**: {'存在' if final_content else '不存在'}")
            if final_content:
                st.write(f"  - 模块数量: {len(final_content)}")
            
            style_theme = state_manager.get_style_theme()
            st.write(f"**Style Theme**: {'存在' if style_theme else '不存在'}")
            if style_theme:
                st.write(f"  - 主题名称: {style_theme.get('theme_name', 'Unknown')}")
        else:
            st.write("**Session**: 不存在")
    
    # 检查前置条件
    final_content = state_manager.get_final_content()
    style_theme = state_manager.get_style_theme()
    
    # 如果没有final_content但有module_contents，尝试自动转换
    if not final_content:
        try:
            session = state_manager.get_current_session()
            if session and session.module_contents:
                st.info("🔄 正在准备内容数据...")
                
                # 将module_contents转换为final_content格式
                final_content = {}
                for module_type, content in session.module_contents.items():
                    # 转换MaterialRequest对象为字典
                    material_requests = []
                    if hasattr(content, 'material_requests') and content.material_requests:
                        for req in content.material_requests:
                            if hasattr(req, '__dict__'):
                                # 如果是对象，转换为字典
                                req_dict = {
                                    'request_id': getattr(req, 'request_id', ''),
                                    'material_type': getattr(req, 'material_type', ''),
                                    'description': getattr(req, 'description', ''),
                                    'importance': getattr(req, 'importance', ''),
                                    'help_text': getattr(req, 'help_text', ''),
                                    'example': getattr(req, 'example', '')
                                }
                                # 处理枚举类型
                                if hasattr(req.material_type, 'value'):
                                    req_dict['material_type'] = req.material_type.value
                                if hasattr(req.importance, 'value'):
                                    req_dict['importance'] = req.importance.value
                                material_requests.append(req_dict)
                            else:
                                # 如果已经是字典，直接使用
                                material_requests.append(req)
                    
                    final_content[module_type.value] = {
                        'title': getattr(content, 'title', ''),
                        'description': getattr(content, 'description', ''),
                        'key_points': getattr(content, 'key_points', []),
                        'generated_text': getattr(content, 'generated_text', {}),
                        'material_requests': material_requests
                    }
                
                # 保存转换后的final_content
                state_manager.set_final_content(final_content)
                st.success(f"✅ 内容数据已准备完成 ({len(final_content)} 个模块)")
                logger.info(f"Auto-converted module_contents to final_content with {len(final_content)} modules")
            else:
                st.warning("⚠️ 请先完成内容编辑")
                if st.button("🔙 返回内容编辑"):
                    # 返回内容编辑步骤
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
        except Exception as e:
            st.error(f"❌ 内容数据转换失败：{str(e)}")
            logger.error(f"Failed to convert module_contents to final_content: {str(e)}")
            return
    
    # 检查风格主题
    if not style_theme:
        st.warning("⚠️ 请先完成风格选择")
        if st.button("🔙 返回风格选择"):
            # 返回风格选择步骤
            from services.aplus_studio.models import WorkflowState
            st.query_params.clear()
            session = state_manager.get_current_session()
            if session:
                session.current_state = WorkflowState.STYLE_SELECTION
                session.last_updated = datetime.now()
                st.session_state.intelligent_workflow_session = session
                state_manager._create_session_backup()
            st.rerun()
        return
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
                # 导入真实的批量图片生成服务
                # 使用增强版批量生成服务 - 结合先进技术但完全兼容当前架构
                from services.aplus_studio.enhanced_batch_image_service import EnhancedAPlusBatchService, BatchGenerationMode
                
                # 创建增强批量生成服务
                batch_service = EnhancedAPlusBatchService()
                
                # 创建进度显示
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                # 进度回调函数 - 兼容增强服务的接口
                def update_progress(module_name, progress):
                    progress_bar.progress(progress)
                    status_text.text(f"正在生成 {module_name} 模块图片... ({int(progress * 100)}%)")
                
                # 生成模式选择（可选的高级配置）
                generation_mode = BatchGenerationMode.PARALLEL  # 默认并行模式
                max_parallel_jobs = 3  # 限制并发数避免API限制
                retry_attempts = 2     # 重试次数
                quality_threshold = 0.7  # 质量阈值
                
                # 显示生成配置信息
                with st.expander("🔧 生成配置", expanded=False):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.info(f"生成模式: {generation_mode.value}")
                        st.info(f"并行任务数: {max_parallel_jobs}")
                    with col2:
                        st.info(f"重试次数: {retry_attempts}")
                        st.info(f"质量阈值: {quality_threshold:.1%}")
                
                # 估算生成时间
                estimated_time = batch_service.estimate_batch_time(final_content)
                st.info(f"⏱️ 预计生成时间: {estimated_time:.0f} 秒")
                
                # 执行增强批量生成 - 使用当前数据格式，但功能完整
                batch_results = batch_service.generate_batch_sync(
                    final_content=final_content,  # 直接使用当前格式
                    style_theme=style_theme,      # 直接使用当前格式
                    progress_callback=update_progress,
                    generation_mode=generation_mode,
                    max_parallel_jobs=max_parallel_jobs,
                    retry_attempts=retry_attempts,
                    quality_threshold=quality_threshold
                )
                
                # 处理生成结果 - 结果已经是期望的格式
                generated_images = {}
                success_count = 0
                failure_count = 0
                total_time = 0.0
                total_quality = 0.0
                
                for module_key, result in batch_results.items():
                    generated_images[module_key] = result
                    
                    if result.get('success', False):
                        success_count += 1
                        total_quality += result.get('quality_score', 0.0)
                    else:
                        failure_count += 1
                    
                    total_time += result.get('generation_time', 0.0)
                
                # 保存生成结果 - 使用简单直接的方式，避免复杂序列化
                logger.info(f"Saving generated images (real generation): {len(generated_images)} modules")
                
                # 🎯 混合策略：保留复杂设计的优点，同时解决序列化问题
                logger.info(f"Saving generated images (real generation): {len(generated_images)} modules")
                
                # 🎯 根本问题修复：采用简化数据存储模式（基于测试页面的成功经验）
                # 问题根源：复杂的数据结构和序列化过程导致数据在页面重新加载时丢失
                # 解决方案：使用简单的字典结构，直接存储到session state，确保完全可序列化
                
                # 创建简化的数据结构（移除所有bytes数据和复杂对象）
                simple_generated_images = {}
                for module_key, result in generated_images.items():
                    simple_generated_images[str(module_key)] = {
                        'image_path': result.get('image_path', ''),
                        'generation_time': result.get('generation_time', 0.0),
                        'quality_score': result.get('quality_score', 0.0),
                        'success': result.get('success', False),
                        'has_image_data': result.get('success', False),
                        'module_name': str(module_key).replace('_', ' ').title(),
                        'generated_at': datetime.now().isoformat()
                    }
                
                # 主要保存：直接保存到session state（可靠）
                st.session_state.generated_images_data = simple_generated_images
                st.session_state.generation_completed = True
                st.session_state.generation_timestamp = datetime.now().isoformat()
                
                # 备用保存：尝试保存到state_manager（可选，失败不影响主流程）
                try:
                    state_manager.set_generated_images(generated_images)
                    logger.info("Successfully saved to state_manager as backup")
                except Exception as sm_error:
                    logger.warning(f"State_manager backup save failed (not critical): {sm_error}")
                
                logger.info(f"Simplified data save completed: {len(simple_generated_images)} modules saved to session_state")
                
                # 计算统计信息
                total_modules = len(batch_results)
                success_rate = success_count / total_modules if total_modules > 0 else 0
                avg_quality = total_quality / success_count if success_count > 0 else 0
                
                # 显示生成摘要
                st.success(f"✅ 批量生成完成！成功: {success_count}, 失败: {failure_count}")
                
                if failure_count > 0:
                    st.warning(f"⚠️ {failure_count} 个模块生成失败，请检查详细信息")
                
                # 显示质量统计
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("成功率", f"{success_rate:.1%}")
                with col2:
                    st.metric("平均质量", f"{avg_quality:.1%}")
                with col3:
                    st.metric("总用时", f"{total_time:.1f}s")
                
                # 显示生成统计详情 - 增强版统计信息
                stats = batch_service.get_generation_stats()
                with st.expander("📊 详细生成统计", expanded=False):
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("总生成数", stats["total_modules"])
                        st.metric("成功生成", stats["successful_generations"])
                        st.metric("平均质量", f"{stats.get('average_quality_score', 0):.1%}")
                    with col2:
                        st.metric("失败生成", stats["failed_generations"])
                        st.metric("平均用时", f"{stats['average_generation_time']:.1f}s")
                        st.metric("总批次数", stats["total_batches"])
                    with col3:
                        st.metric("整体成功率", f"{stats['success_rate']:.1%}")
                        st.metric("总用时", f"{stats['total_generation_time']:.1f}s")
                        
                        # 显示模块复杂度信息
                        complexity_info = batch_service.get_module_complexity_info()
                        complex_modules = sum(1 for k in final_content.keys() if complexity_info.get(k) == "complex")
                        st.metric("复杂模块数", complex_modules)
                
                # 显示质量分析
                if success_count > 0:
                    quality_scores = [result.get('quality_score', 0.0) for result in batch_results.values() if result.get('success', False)]
                    if quality_scores:
                        with st.expander("🎯 质量分析", expanded=False):
                            col1, col2 = st.columns(2)
                            with col1:
                                st.metric("最高质量", f"{max(quality_scores):.1%}")
                                st.metric("最低质量", f"{min(quality_scores):.1%}")
                            with col2:
                                high_quality_count = sum(1 for score in quality_scores if score >= quality_threshold)
                                st.metric("高质量模块", f"{high_quality_count}/{len(quality_scores)}")
                                st.metric("质量达标率", f"{high_quality_count/len(quality_scores):.1%}")
                
                # 显示生成时间分析
                generation_times = [result.get('generation_time', 0.0) for result in batch_results.values()]
                if generation_times:
                    with st.expander("⏱️ 性能分析", expanded=False):
                        col1, col2 = st.columns(2)
                        with col1:
                            st.metric("最快生成", f"{min(generation_times):.1f}s")
                            st.metric("最慢生成", f"{max(generation_times):.1f}s")
                        with col2:
                            avg_time = sum(generation_times) / len(generation_times)
                            st.metric("平均时间", f"{avg_time:.1f}s")
                            efficiency = len(generation_times) / total_time if total_time > 0 else 0
                            st.metric("生成效率", f"{efficiency:.2f} 模块/秒")
                
                if st.button("📊 查看生成结果", type="primary", use_container_width=True):
                    # 🎯 关键修复：确保简化数据存在于session state中
                    from services.aplus_studio.models import WorkflowState
                    
                    logger.info("User clicked '查看生成结果' button")
                    
                    # 首先确保简化数据存在于session state中
                    if 'generated_images_data' not in st.session_state:
                        logger.warning("No simplified data in session_state, creating from complex data")
                        
                        # 从复杂数据创建简化数据
                        generated_images = state_manager.get_generated_images()
                        if generated_images:
                            simple_generated_images = {}
                            for module_key, result in generated_images.items():
                                simple_generated_images[str(module_key)] = {
                                    'image_path': result.get('image_path', ''),
                                    'generation_time': result.get('generation_time', 0.0),
                                    'quality_score': result.get('quality_score', 0.0),
                                    'success': result.get('success', False),
                                    'has_image_data': result.get('success', False),
                                    'module_name': str(module_key).replace('_', ' ').title(),
                                    'generated_at': datetime.now().isoformat()
                                }
                            
                            # 保存到session state
                            st.session_state.generated_images_data = simple_generated_images
                            st.session_state.generation_completed = True
                            st.session_state.generation_timestamp = datetime.now().isoformat()
                            logger.info(f"Created simplified data for {len(simple_generated_images)} modules")
                        else:
                            logger.error("No complex data available to create simplified data from")
                            st.error("❌ 没有找到生成的图片数据，请重新生成")
                            return
                    else:
                        logger.info("Simplified data already exists in session_state")
                    
                    # 设置URL参数强制跳转到完成状态
                    timestamp = str(int(datetime.now().timestamp()))
                    st.query_params.update({"step": "completed", "t": timestamp})
                    logger.info(f"Set URL params: step=completed, t={timestamp}")
                    
                    # 显示调试信息给用户
                    st.info("🔄 正在跳转到结果页面...")
                    logger.info("Triggering page rerun...")
                    
                    # 触发页面重新加载
                    st.rerun()
                
                # 临时测试按钮 - 直接跳转方案
                st.markdown("---")
                st.markdown("**🧪 测试区域**")
                col1, col2 = st.columns(2)
                
                with col1:
                    if st.button("🔧 直接跳转 (测试)", type="secondary"):
                        # 直接设置状态，不使用URL参数
                        from services.aplus_studio.models import WorkflowState
                        session = state_manager.get_current_session()
                        if session:
                            session.current_state = WorkflowState.COMPLETED
                            session.last_updated = datetime.now()
                            st.session_state.intelligent_workflow_session = session
                            st.success("✅ 状态已设置为COMPLETED")
                            st.rerun()
                        else:
                            st.error("❌ 没有找到当前会话")
                
                with col2:
                    if st.button("🔍 检查数据", type="secondary"):
                        # 检查生成的图片数据
                        generated_images = state_manager.get_generated_images()
                        if generated_images:
                            st.success(f"✅ 找到 {len(generated_images)} 个生成的图片")
                        else:
                            st.error("❌ 没有找到生成的图片数据")
                    
            except ImportError as e:
                st.error(f"❌ 图片生成服务导入失败: {str(e)}")
                st.info("🔄 使用模拟生成模式...")
                
                # 回退到模拟生成
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                generated_images = {}
                modules = list(final_content.keys())
                
                for i, module in enumerate(modules):
                    status_text.text(f"正在生成 {module} 模块图片...")
                    progress_bar.progress((i + 1) / len(modules))
                    time.sleep(2)  # 模拟生成时间
                    
                    # 模拟生成结果
                    generated_images[module] = {
                        'image_path': f'generated/{module}_{int(time.time())}.png',
                        'generation_time': 2.0,
                        'quality_score': 0.85 + (i * 0.02),
                        'is_simulated': True
                    }
                
                # 保存生成结果 - 使用简单直接的方式，避免复杂序列化
                logger.info(f"Saving generated images (simulated): {len(generated_images)} modules")
                
                # 🎯 混合策略：保留复杂设计的优点，同时解决序列化问题
                logger.info(f"Saving generated images (simulated): {len(generated_images)} modules")
                
                # 🎯 根本问题修复：采用简化数据存储模式（基于测试页面的成功经验）
                # 创建简化的数据结构（移除所有bytes数据和复杂对象）
                simple_generated_images = {}
                for module_key, result in generated_images.items():
                    simple_generated_images[str(module_key)] = {
                        'image_path': result.get('image_path', ''),
                        'generation_time': result.get('generation_time', 0.0),
                        'quality_score': result.get('quality_score', 0.0),
                        'success': True,  # 模拟生成总是成功
                        'has_image_data': True,  # 模拟有数据
                        'module_name': str(module_key).replace('_', ' ').title(),
                        'generated_at': datetime.now().isoformat(),
                        'is_simulated': True
                    }
                
                # 主要保存：直接保存到session state（可靠）
                st.session_state.generated_images_data = simple_generated_images
                st.session_state.generation_completed = True
                st.session_state.generation_timestamp = datetime.now().isoformat()
                
                # 备用保存：尝试保存到state_manager（可选，失败不影响主流程）
                try:
                    state_manager.set_generated_images(generated_images)
                    logger.info("Successfully saved mock data to state_manager as backup")
                except Exception as sm_error:
                    logger.warning(f"State_manager backup save failed (not critical): {sm_error}")
                
                logger.info(f"Simplified mock data save completed: {len(simple_generated_images)} modules saved to session_state")
                
                logger.info("Generated images saved successfully with enhanced persistence (simulated)")
                st.success("✅ 模拟生成完成！")
                
                if st.button("📊 查看生成结果", type="primary", use_container_width=True):
                    # 🎯 关键修复：确保简化数据存在于session state中
                    from services.aplus_studio.models import WorkflowState
                    
                    logger.info("User clicked '查看生成结果' button (simulated)")
                    
                    # 首先确保简化数据存在于session state中
                    if 'generated_images_data' not in st.session_state:
                        logger.warning("No simplified data in session_state, creating from complex data (simulated)")
                        
                        # 从复杂数据创建简化数据
                        generated_images = state_manager.get_generated_images()
                        if generated_images:
                            simple_generated_images = {}
                            for module_key, result in generated_images.items():
                                simple_generated_images[str(module_key)] = {
                                    'image_path': result.get('image_path', ''),
                                    'generation_time': result.get('generation_time', 0.0),
                                    'quality_score': result.get('quality_score', 0.0),
                                    'success': True,  # 模拟生成总是成功
                                    'has_image_data': True,  # 模拟有数据
                                    'module_name': str(module_key).replace('_', ' ').title(),
                                    'generated_at': datetime.now().isoformat(),
                                    'is_simulated': True
                                }
                            
                            # 保存到session state
                            st.session_state.generated_images_data = simple_generated_images
                            st.session_state.generation_completed = True
                            st.session_state.generation_timestamp = datetime.now().isoformat()
                            logger.info(f"Created simplified data for {len(simple_generated_images)} modules (simulated)")
                        else:
                            logger.error("No complex data available to create simplified data from (simulated)")
                            st.error("❌ 没有找到生成的图片数据，请重新生成")
                            return
                    else:
                        logger.info("Simplified data already exists in session_state (simulated)")
                    
                    # 设置URL参数强制跳转到完成状态
                    timestamp = str(int(datetime.now().timestamp()))
                    st.query_params.update({"step": "completed", "t": timestamp})
                    logger.info(f"Set URL params: step=completed, t={timestamp}")
                    
                    # 显示调试信息给用户
                    st.info("🔄 正在跳转到结果页面...")
                    logger.info("Triggering page rerun...")
                    
                    # 触发页面重新加载
                    st.rerun()
                
                # 临时测试按钮 - 模拟生成版本
                st.markdown("---")
                st.markdown("**🧪 测试区域 (模拟生成)**")
                col1, col2 = st.columns(2)
                
                with col1:
                    if st.button("🔧 直接跳转 (模拟)", type="secondary", key="sim_direct_jump"):
                        # 直接设置状态，不使用URL参数
                        from services.aplus_studio.models import WorkflowState
                        session = state_manager.get_current_session()
                        if session:
                            session.current_state = WorkflowState.COMPLETED
                            session.last_updated = datetime.now()
                            st.session_state.intelligent_workflow_session = session
                            st.success("✅ 状态已设置为COMPLETED")
                            st.rerun()
                        else:
                            st.error("❌ 没有找到当前会话")
                
                with col2:
                    if st.button("🔍 检查数据 (模拟)", type="secondary", key="sim_check_data"):
                        # 检查生成的图片数据
                        generated_images = state_manager.get_generated_images()
                        if generated_images:
                            st.success(f"✅ 找到 {len(generated_images)} 个生成的图片")
                        else:
                            st.error("❌ 没有找到生成的图片数据")
                    
            except Exception as e:
                st.error(f"❌ 图片生成失败: {str(e)}")
                logger.error(f"Image generation failed: {str(e)}")
                
                # 显示详细错误信息
                with st.expander("🔧 错误详情", expanded=False):
                    st.code(str(e))
                    st.write("**可能的解决方案：**")
                    st.write("1. 检查API密钥配置是否正确")
                    st.write("2. 确保网络连接稳定")
                    st.write("3. 检查图片生成服务是否正常运行")
                    st.write("4. 稍后重试或联系技术支持")


def render_workflow_completed_step(state_manager):
    """渲染工作流完成步骤"""
    st.subheader("🎉 智能工作流完成！")
    st.markdown("恭喜！您的A+页面已经生成完成")
    
    # 调试信息
    logger.info("Rendering workflow completed step")
    
    # 🎯 关键修复：优先从简单的session state获取数据
    generated_images = st.session_state.get('generated_images_data')
    logger.info(f"Retrieved generated images from session state: {generated_images is not None}")
    
    # 如果session state中没有，再尝试从state_manager获取
    if not generated_images:
        logger.info("No data in session state, trying state_manager")
        generated_images = state_manager.get_generated_images()
        logger.info(f"Retrieved generated images from state_manager: {generated_images is not None}")
    
    # 如果还是没有，尝试从session中恢复
    if not generated_images:
        session = state_manager.get_current_session()
        if session:
            logger.info("Attempting to recover generated images from session")
            
            # 尝试从workflow_metadata恢复
            if hasattr(session, 'workflow_metadata') and session.workflow_metadata.get('generated_images'):
                backup_images = session.workflow_metadata['generated_images']
                logger.info(f"Found backup images in workflow_metadata: {len(backup_images)}")
                generated_images = backup_images
            
            # 尝试从_temp_generated_images恢复
            elif hasattr(session, '_temp_generated_images') and session._temp_generated_images:
                logger.info("Found temp generated images in session")
                generated_images = session._temp_generated_images
            
            # 尝试从generation_results恢复
            elif hasattr(session, 'generation_results') and session.generation_results:
                logger.info("Attempting to reconstruct from generation_results")
                reconstructed_images = {}
                for module_type, result in session.generation_results.items():
                    if hasattr(result, 'image_data') and result.image_data:
                        reconstructed_images[str(module_type)] = {
                            'image_data': result.image_data,
                            'quality_score': getattr(result, 'quality_score', 0.8),
                            'has_image_data': True
                        }
                if reconstructed_images:
                    generated_images = reconstructed_images
                    logger.info(f"Reconstructed {len(reconstructed_images)} images from generation_results")
    
    # 显示调试信息
    with st.expander("🔧 数据恢复调试信息", expanded=False):
        session = state_manager.get_current_session()
        if session:
            st.write(f"**会话ID**: {session.session_id}")
            st.write(f"**当前状态**: {session.current_state.value}")
            st.write(f"**生成图片数据**: {'存在' if generated_images else '不存在'}")
            if generated_images:
                st.write(f"**图片数量**: {len(generated_images)}")
            
            # 显示各种数据源的状态
            st.write("**数据源检查**:")
            st.write(f"- st.session_state.generated_images_data: {'有数据' if st.session_state.get('generated_images_data') else '无数据'}")
            st.write(f"- state_manager.get_generated_images(): {'有数据' if state_manager.get_generated_images() else '无数据'}")
            st.write(f"- session.workflow_metadata.generated_images: {'有数据' if hasattr(session, 'workflow_metadata') and session.workflow_metadata.get('generated_images') else '无数据'}")
            st.write(f"- session._temp_generated_images: {'有数据' if hasattr(session, '_temp_generated_images') and session._temp_generated_images else '无数据'}")
            st.write(f"- session.generation_results: {'有数据' if hasattr(session, 'generation_results') and session.generation_results else '无数据'}")
            
            # 显示生成时间信息
            generation_time = st.session_state.get('generation_timestamp')
            if generation_time:
                st.write(f"- 生成时间: {generation_time}")
            st.write(f"- 生成完成标志: {st.session_state.get('generation_completed', False)}")
        else:
            st.write("**没有找到会话**")
    
    if generated_images:
        logger.info(f"Found {len(generated_images)} generated images")
        st.success(f"**生成结果**: 成功生成 {len(generated_images)} 个A+模块")
        
        # 显示生成的模块列表
        for module_key, result in generated_images.items():
            col1, col2, col3 = st.columns([2, 1, 1])
            
            with col1:
                # 处理module_key，可能是字符串或ModuleType对象
                if hasattr(module_key, 'value'):
                    display_name = module_key.value.replace('_', ' ').title()
                else:
                    display_name = str(module_key).replace('_', ' ').title()
                st.write(f"📋 {display_name}")
            
            with col2:
                quality_score = result.get('quality_score', 0.0) if isinstance(result, dict) else 0.0
                st.write(f"质量: {quality_score:.1%}")
            
            with col3:
                # 使用字符串形式的module_key作为按钮key
                button_key = str(module_key) if hasattr(module_key, 'value') else module_key
                if st.button(f"下载", key=f"download_{button_key}"):
                    # 检查是否有图片数据
                    if isinstance(result, dict) and (result.get('has_image_data') or result.get('image_data')):
                        st.success(f"开始下载 {display_name}")
                    else:
                        st.warning("图片数据不可用")
        
        # 批量操作
        st.markdown("---")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("📦 批量下载", use_container_width=True):
                st.success("开始批量下载...")
        
        with col2:
            if st.button("🔄 重新生成", use_container_width=True):
                # 清除URL参数并设置状态
                from services.aplus_studio.models import WorkflowState
                st.query_params.clear()
                session = state_manager.get_current_session()
                if session:
                    session.current_state = WorkflowState.IMAGE_GENERATION
                    session.last_updated = datetime.now()
                    st.session_state.intelligent_workflow_session = session
                    
                    # 安全的session备份
                    try:
                        state_manager._create_session_backup()
                    except Exception as backup_error:
                        logger.warning(f"Session backup failed: {backup_error}")
                st.rerun()
        
        with col3:
            if st.button("🆕 新建项目", use_container_width=True):
                # 清理状态，开始新项目
                state_manager.reset_workflow()
                st.rerun()
        
        # 🎯 添加调试和恢复功能
        st.markdown("---")
        st.markdown("**🔧 调试和恢复工具**")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🔍 检查所有数据源", use_container_width=True):
                st.info("**数据源检查结果：**")
                session = state_manager.get_current_session()
                
                # 检查各种数据源
                sources = {
                    "Session State": st.session_state.get('generated_images_data'),
                    "State Manager": state_manager.get_generated_images(),
                    "Session Metadata": session.workflow_metadata.get('generated_images') if session and hasattr(session, 'workflow_metadata') else None,
                    "Session Temp": getattr(session, '_temp_generated_images', None) if session else None,
                    "Generation Results": getattr(session, 'generation_results', None) if session else None
                }
                
                for source_name, data in sources.items():
                    if data:
                        count = len(data) if isinstance(data, (dict, list)) else "存在"
                        st.success(f"✅ {source_name}: {count}")
                    else:
                        st.error(f"❌ {source_name}: 无数据")
        
        with col2:
            if st.button("🔄 强制恢复数据", use_container_width=True):
                # 尝试从任何可用源恢复数据
                session = state_manager.get_current_session()
                recovered = False
                
                # 尝试各种恢复方法
                if st.session_state.get('generated_images_data'):
                    st.success("✅ 从Session State恢复数据")
                    recovered = True
                elif state_manager.get_generated_images():
                    st.success("✅ 从State Manager恢复数据")
                    recovered = True
                elif session and hasattr(session, 'workflow_metadata') and session.workflow_metadata.get('generated_images'):
                    backup_data = session.workflow_metadata['generated_images']
                    st.session_state.generated_images_data = backup_data
                    st.success("✅ 从Session Metadata恢复数据")
                    recovered = True
                elif session and hasattr(session, '_temp_generated_images') and session._temp_generated_images:
                    st.session_state.generated_images_data = session._temp_generated_images
                    st.success("✅ 从临时数据恢复")
                    recovered = True
                
                if recovered:
                    st.rerun()
                else:
                    st.error("❌ 无法恢复数据，请重新生成")
    
    else:
        logger.warning("No generated images found after all recovery attempts")
        st.error("❌ 没有找到生成的图片数据")
        
        # 显示详细的调试信息
        st.warning("**可能的原因：**")
        st.write("1. 图片生成过程中出现错误")
        st.write("2. 页面刷新导致数据丢失")
        st.write("3. Session状态管理问题")
        
        # 调试信息：显示当前会话状态
        session = state_manager.get_current_session()
        if session:
            st.info(f"当前会话状态: {session.current_state.value}")
            if hasattr(session, 'workflow_metadata'):
                metadata_keys = list(session.workflow_metadata.keys())
                st.info(f"工作流元数据键: {metadata_keys}")
            if hasattr(session, '_temp_generated_images'):
                st.info(f"临时图片数据: {session._temp_generated_images is not None}")
        
        st.info("请返回上一步重新生成图片")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🔙 返回图片生成", use_container_width=True):
                # 返回图片生成步骤
                from services.aplus_studio.models import WorkflowState
                st.query_params.clear()
                session = state_manager.get_current_session()
                if session:
                    session.current_state = WorkflowState.IMAGE_GENERATION
                    session.last_updated = datetime.now()
                    st.session_state.intelligent_workflow_session = session
                    
                    # 安全的session备份
                    try:
                        state_manager._create_session_backup()
                    except Exception as backup_error:
                        logger.warning(f"Session backup failed: {backup_error}")
                st.rerun()
        
        with col2:
            if st.button("🔄 尝试恢复数据", use_container_width=True):
                # 简化的恢复尝试
                session = state_manager.get_current_session()
                if session:
                    # 检查是否有任何可恢复的数据
                    if hasattr(session, 'workflow_metadata') and session.workflow_metadata.get('generated_images'):
                        backup_images = session.workflow_metadata['generated_images']
                        state_manager.set_generated_images(backup_images)
                        st.success("✅ 从备份恢复了图片数据")
                        st.rerun()
                    else:
                        st.warning("⚠️ 没有找到可恢复的数据")
                else:
                    st.error("❌ 没有找到会话数据")


if __name__ == "__main__":
    main()
