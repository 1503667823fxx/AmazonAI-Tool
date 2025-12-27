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
        
        # 配置Gemini API
        api_key = st.secrets.get("GOOGLE_API_KEY") or st.secrets.get("GEMINI_API_KEY")
        if api_key:
            genai.configure(api_key=api_key)
        else:
            st.error("❌ 无法获取API密钥")
            return
            
    except Exception as e:
        st.error(f"❌ API配置失败: {str(e)}")
        return
    
    # 初始化状态管理器
    try:
        from app_utils.aplus_studio.intelligent_state_manager import IntelligentStateManager
        state_manager = IntelligentStateManager()
    except ImportError as e:
        st.error(f"❌ 状态管理器导入失败: {str(e)}")
        return
    
    # 渲染工作流导航
    try:
        from app_utils.aplus_studio.workflow_navigation_ui import WorkflowNavigationUI
        from services.aplus_studio.models import WorkflowState  # 确保导入WorkflowState
        
        # 创建导航UI实例
        nav_ui = WorkflowNavigationUI()
        
        # 渲染导航
        nav_ui.render_navigation(state_manager)
        
        # 获取当前状态
        current_state = state_manager.get_current_state()
        
        # 根据当前状态渲染对应的步骤
        if current_state == WorkflowState.PRODUCT_ANALYSIS:
            render_product_analysis_step(state_manager)
        elif current_state == WorkflowState.MODULE_RECOMMENDATION:
            render_module_recommendation_step(state_manager)
        elif current_state == WorkflowState.CONTENT_GENERATION:
            render_content_generation_step(state_manager)
        elif current_state == WorkflowState.CONTENT_EDITING:
            render_content_editing_step(state_manager)
        elif current_state == WorkflowState.STYLE_SELECTION:
            render_style_selection_step(state_manager)
        elif current_state == WorkflowState.IMAGE_GENERATION:
            render_image_generation_step(state_manager)
        elif current_state == WorkflowState.COMPLETED:
            render_workflow_completed_step(state_manager)
        else:
            st.error(f"❌ 未知的工作流状态: {current_state}")
            
    except ImportError as e:
        st.error(f"❌ 工作流组件导入失败: {str(e)}")
        st.info("🔄 正在使用简化版界面...")
        render_simplified_workflow(state_manager)
    except Exception as e:
        st.error(f"❌ 工作流渲染失败: {str(e)}")
        logger.error(f"Workflow rendering error: {str(e)}")


def render_simplified_workflow(state_manager):
    """渲染简化版工作流界面"""
    st.info("🔧 使用简化版工作流界面")
    
    # 简化的步骤选择
    steps = [
        ("product_analysis", "📊 产品分析"),
        ("module_recommendation", "🧩 模块推荐"),
        ("content_generation", "✍️ 内容生成"),
        ("content_editing", "📝 内容编辑"),
        ("style_selection", "🎨 风格选择"),
        ("image_generation", "🖼️ 图片生成"),
        ("completed", "✅ 完成")
    ]
    
    # 显示步骤
    cols = st.columns(len(steps))
    for i, (step_key, step_name) in enumerate(steps):
        with cols[i]:
            if st.button(step_name, key=f"step_{step_key}"):
                st.info(f"切换到: {step_name}")
                # 这里可以添加状态切换逻辑


def render_product_analysis_step(state_manager):
    """渲染产品分析步骤"""
    try:
        from app_utils.aplus_studio.product_analysis_ui import ProductAnalysisUI, create_product_analysis_ui
        
        # 使用新的UI创建函数
        analysis_ui = create_product_analysis_ui()
        
        # 渲染产品分析界面
        analysis_ui.render_analysis_interface(state_manager)
        
    except ImportError as e:
        st.error(f"❌ 产品分析UI导入失败: {str(e)}")
        render_simplified_product_analysis(state_manager)
    except Exception as e:
        st.error(f"❌ 产品分析渲染失败: {str(e)}")
        logger.error(f"Product analysis rendering error: {str(e)}")


def render_simplified_product_analysis(state_manager):
    """渲染简化版产品分析界面"""
    st.header("📊 产品分析")
    st.info("使用简化版产品分析界面")
    
    # 简化的产品信息输入
    product_name = st.text_input("产品名称", placeholder="请输入产品名称")
    product_description = st.text_area("产品描述", placeholder="请描述您的产品特点和优势")
    
    # 图片上传
    uploaded_files = st.file_uploader(
        "上传产品图片", 
        type=['png', 'jpg', 'jpeg'], 
        accept_multiple_files=True,
        help="支持PNG、JPG格式，最多上传5张图片"
    )
    
    if st.button("开始分析", type="primary"):
        if product_name and product_description:
            # 模拟分析过程
            with st.spinner("正在分析产品..."):
                time.sleep(2)
            
            # 模拟分析结果
            analysis_result = {
                'product_type': '电子产品',
                'selling_points': ['高质量', '性价比高', '功能丰富'],
                'target_audience': '科技爱好者',
                'recommended_modules': ['产品特性', '使用场景', '技术规格']
            }
            
            # 保存分析结果
            state_manager.set_analysis_result(analysis_result)
            st.success("✅ 产品分析完成！")
            
            # 显示分析结果
            st.json(analysis_result)
            
            if st.button("下一步：模块推荐"):
                # 切换到下一步
                session = state_manager.get_current_session()
                if session:
                    session.current_state = WorkflowState.MODULE_RECOMMENDATION
                    session.last_updated = datetime.now()
                    st.session_state.intelligent_workflow_session = session
                st.rerun()
        else:
            st.warning("⚠️ 请填写产品名称和描述")


def render_module_recommendation_step(state_manager):
    """渲染模块推荐步骤"""
    try:
        from app_utils.aplus_studio.module_recommendation_ui import ModuleRecommendationUI
        
        # 创建模块推荐UI实例
        recommendation_ui = ModuleRecommendationUI()
        
        # 渲染模块推荐界面
        recommendation_ui.render_recommendation_interface(state_manager)
        
    except ImportError as e:
        st.error(f"❌ 模块推荐UI导入失败: {str(e)}")
        render_simplified_module_recommendation(state_manager)
    except Exception as e:
        st.error(f"❌ 模块推荐渲染失败: {str(e)}")
        logger.error(f"Module recommendation rendering error: {str(e)}")


def render_simplified_module_recommendation(state_manager):
    """渲染简化版模块推荐界面"""
    st.header("🧩 模块推荐")
    st.info("使用简化版模块推荐界面")
    
    # 获取分析结果
    analysis_result = state_manager.get_analysis_result()
    
    if analysis_result:
        st.success("✅ 基于产品分析结果生成推荐")
        
        # 显示推荐的模块
        recommended_modules = [
            "产品特性展示",
            "使用场景介绍", 
            "技术规格说明",
            "用户评价展示",
            "品牌故事介绍"
        ]
        
        st.subheader("推荐模块")
        selected_modules = []
        
        for module in recommended_modules:
            if st.checkbox(module, value=True):
                selected_modules.append(module)
        
        if st.button("确认选择", type="primary"):
            if selected_modules:
                # 保存选择的模块
                state_manager.set_selected_modules(selected_modules)
                st.success(f"✅ 已选择 {len(selected_modules)} 个模块")
                
                if st.button("下一步：内容生成"):
                    # 切换到下一步
                    session = state_manager.get_current_session()
                    if session:
                        session.current_state = WorkflowState.CONTENT_GENERATION
                        session.last_updated = datetime.now()
                        st.session_state.intelligent_workflow_session = session
                    st.rerun()
            else:
                st.warning("⚠️ 请至少选择一个模块")
    else:
        st.warning("⚠️ 请先完成产品分析")
        if st.button("返回产品分析"):
            session = state_manager.get_current_session()
            if session:
                session.current_state = WorkflowState.PRODUCT_ANALYSIS
                session.last_updated = datetime.now()
                st.session_state.intelligent_workflow_session = session
            st.rerun()


def render_content_generation_step(state_manager):
    """渲染内容生成步骤"""
    st.header("✍️ 内容生成")
    
    # 获取选择的模块
    selected_modules = state_manager.get_selected_modules()
    analysis_result = state_manager.get_analysis_result()
    
    if not selected_modules:
        st.warning("⚠️ 请先选择模块")
        if st.button("返回模块推荐"):
            session = state_manager.get_current_session()
            if session:
                session.current_state = WorkflowState.MODULE_RECOMMENDATION
                session.last_updated = datetime.now()
                st.session_state.intelligent_workflow_session = session
            st.rerun()
        return
    
    st.info(f"为 {len(selected_modules)} 个模块生成内容")
    
    # 显示选择的模块
    for module in selected_modules:
        st.write(f"📝 {module}")
    
    if st.button("开始生成内容", type="primary"):
        # 模拟内容生成过程
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        generated_content = {}
        
        for i, module in enumerate(selected_modules):
            status_text.text(f"正在生成 {module} 内容...")
            progress_bar.progress((i + 1) / len(selected_modules))
            time.sleep(1)  # 模拟生成时间
            
            # 模拟生成的内容
            generated_content[module] = {
                'title': f"{module}标题",
                'description': f"这是{module}的详细描述内容...",
                'key_points': [f"{module}要点1", f"{module}要点2", f"{module}要点3"]
            }
        
        # 保存生成的内容
        state_manager.set_generated_content(generated_content)
        st.success("✅ 内容生成完成！")
        
        # 显示生成的内容
        for module, content in generated_content.items():
            with st.expander(f"📄 {module}", expanded=False):
                st.write(f"**标题**: {content['title']}")
                st.write(f"**描述**: {content['description']}")
                st.write("**要点**:")
                for point in content['key_points']:
                    st.write(f"• {point}")
        
        if st.button("下一步：内容编辑"):
            # 切换到下一步
            session = state_manager.get_current_session()
            if session:
                session.current_state = WorkflowState.CONTENT_EDITING
                session.last_updated = datetime.now()
                st.session_state.intelligent_workflow_session = session
            st.rerun()


def render_content_editing_step(state_manager):
    """渲染内容编辑步骤"""
    try:
        from app_utils.aplus_studio.content_editing_ui import ContentEditingUI
        
        # 创建内容编辑UI实例
        editing_ui = ContentEditingUI()
        
        # 渲染内容编辑界面
        editing_ui.render_editing_interface(state_manager)
        
    except ImportError as e:
        st.error(f"❌ 内容编辑UI导入失败: {str(e)}")
        render_simplified_content_editing(state_manager)
    except Exception as e:
        st.error(f"❌ 内容编辑渲染失败: {str(e)}")
        logger.error(f"Content editing rendering error: {str(e)}")


def render_simplified_content_editing(state_manager):
    """渲染简化版内容编辑界面"""
    st.header("📝 内容编辑")
    st.info("使用简化版内容编辑界面")
    
    generated_content = state_manager.get_generated_content()
    
    if not generated_content:
        st.warning("⚠️ 请先生成内容")
        if st.button("返回内容生成"):
            session = state_manager.get_current_session()
            if session:
                session.current_state = WorkflowState.CONTENT_GENERATION
                session.last_updated = datetime.now()
                st.session_state.intelligent_workflow_session = session
            st.rerun()
        return
    
    # 编辑内容
    edited_content = {}
    
    for module, content in generated_content.items():
        with st.expander(f"📝 编辑 {module}", expanded=True):
            title = st.text_input("标题", value=content.get('title', ''), key=f"title_{module}")
            description = st.text_area("描述", value=content.get('description', ''), key=f"desc_{module}")
            
            # 更新内容
            edited_content[module] = {
                'title': title,
                'description': description,
                'key_points': content.get('key_points', [])
            }
    
    if st.button("保存编辑", type="primary"):
        # 保存编辑后的内容
        state_manager.set_final_content(edited_content)
        st.success("✅ 内容编辑完成！")
        
        if st.button("下一步：风格选择"):
            # 切换到下一步
            session = state_manager.get_current_session()
            if session:
                session.current_state = WorkflowState.STYLE_SELECTION
                session.last_updated = datetime.now()
                st.session_state.intelligent_workflow_session = session
            st.rerun()


def render_style_selection_step(state_manager):
    """渲染风格选择步骤"""
    st.header("🎨 风格选择")
    
    final_content = state_manager.get_final_content()
    
    if not final_content:
        st.warning("⚠️ 请先完成内容编辑")
        if st.button("返回内容编辑"):
            session = state_manager.get_current_session()
            if session:
                session.current_state = WorkflowState.CONTENT_EDITING
                session.last_updated = datetime.now()
                st.session_state.intelligent_workflow_session = session
            st.rerun()
        return
    
    st.info("选择图片生成风格")
    
    # 风格选项
    styles = [
        ("现代简约", "简洁、清晰的现代设计风格"),
        ("商务专业", "专业、正式的商务风格"),
        ("时尚潮流", "时尚、年轻的潮流风格"),
        ("温馨自然", "温暖、自然的生活风格"),
        ("科技未来", "科技感、未来感的设计风格")
    ]
    
    selected_style = st.selectbox(
        "选择风格",
        options=[style[0] for style in styles],
        format_func=lambda x: f"{x} - {next(desc for name, desc in styles if name == x)}"
    )
    
    # 颜色主题
    color_themes = ["蓝色系", "绿色系", "橙色系", "紫色系", "灰色系"]
    selected_color = st.selectbox("选择颜色主题", color_themes)
    
    # 布局选项
    layout_options = ["左右布局", "上下布局", "居中布局", "网格布局"]
    selected_layout = st.selectbox("选择布局", layout_options)
    
    if st.button("确认风格选择", type="primary"):
        # 保存风格选择
        style_config = {
            'style': selected_style,
            'color_theme': selected_color,
            'layout': selected_layout
        }
        state_manager.set_style_config(style_config)
        st.success("✅ 风格选择完成！")
        
        if st.button("下一步：图片生成"):
            # 切换到下一步
            session = state_manager.get_current_session()
            if session:
                session.current_state = WorkflowState.IMAGE_GENERATION
                session.last_updated = datetime.now()
                st.session_state.intelligent_workflow_session = session
            st.rerun()


def render_image_generation_step(state_manager):
    """渲染图片生成步骤"""
    st.header("🖼️ 图片生成")
    
    final_content = state_manager.get_final_content()
    style_config = state_manager.get_style_config()
    
    if not final_content or not style_config:
        st.warning("⚠️ 请先完成前面的步骤")
        return
    
    st.info("准备生成图片")
    
    # 显示生成配置
    with st.expander("生成配置", expanded=False):
        st.write(f"**风格**: {style_config.get('style', '未选择')}")
        st.write(f"**颜色主题**: {style_config.get('color_theme', '未选择')}")
        st.write(f"**布局**: {style_config.get('layout', '未选择')}")
        st.write(f"**模块数量**: {len(final_content)}")
    
    if st.button("开始生成图片", type="primary"):
        # 尝试使用真实的图片生成服务
        try:
            from services.aplus_studio.enhanced_batch_image_service import EnhancedBatchImageService
            
            # 创建图片生成服务实例
            image_service = EnhancedBatchImageService()
            
            # 准备生成数据
            generation_data = []
            for module_name, content in final_content.items():
                generation_data.append({
                    'module_name': module_name,
                    'title': content.get('title', ''),
                    'description': content.get('description', ''),
                    'style_config': style_config
                })
            
            # 开始生成
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            status_text.text("正在初始化图片生成服务...")
            progress_bar.progress(0.1)
            
            # 批量生成图片
            status_text.text("正在生成图片...")
            progress_bar.progress(0.3)
            
            generated_images = image_service.generate_batch_images(generation_data)
            
            progress_bar.progress(1.0)
            status_text.text("图片生成完成！")
            
            # 保存生成结果
            state_manager.set_generated_images(generated_images)
            st.success("✅ 图片生成完成！")
            
            # 显示生成的图片（如果有的话）
            if generated_images:
                st.subheader("生成结果预览")
                for module_name, image_data in generated_images.items():
                    with st.expander(f"🖼️ {module_name}", expanded=False):
                        if 'image_path' in image_data:
                            st.write(f"图片路径: {image_data['image_path']}")
                        if 'generation_time' in image_data:
                            st.write(f"生成时间: {image_data['generation_time']:.2f}秒")
                        if 'quality_score' in image_data:
                            st.write(f"质量评分: {image_data['quality_score']:.2f}")
            
            if st.button("📊 查看生成结果", type="primary", use_container_width=True):
                # 使用URL参数强制状态转换（修复"查看结果"按钮问题）
                from services.aplus_studio.models import WorkflowState
                
                logger.info("User clicked '查看生成结果' button")
                
                # 获取当前状态信息用于调试
                current_session = state_manager.get_current_session()
                if current_session:
                    logger.info(f"Current session state before transition: {current_session.current_state.value}")
                
                # 设置URL参数强制跳转到完成状态
                timestamp = str(int(datetime.now().timestamp()))
                st.query_params.update({"step": "completed", "t": timestamp})
                
                # 同时更新session状态确保一致性
                session = state_manager.get_current_session()
                if session:
                    session.current_state = WorkflowState.COMPLETED
                    session.last_updated = datetime.now()
                    st.session_state.intelligent_workflow_session = session
                    
                    # 安全保存session
                    try:
                        state_manager._safe_save_session(session)
                        logger.info("Session saved successfully")
                    except Exception as backup_error:
                        logger.warning(f"Session backup failed: {backup_error}")
                        # 继续执行，不让备份失败影响主流程
                else:
                    logger.error("No current session found!")
                
                logger.info("Triggering page rerun...")
                st.success("✅ 正在跳转到结果页面...")
                st.rerun()
                
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
            
            # 保存生成结果
            state_manager.set_generated_images(generated_images)
            st.success("✅ 模拟生成完成！")
            
            if st.button("📊 查看生成结果", type="primary", use_container_width=True):
                # 使用URL参数强制状态转换（参考方案6的成功实现）
                from services.aplus_studio.models import WorkflowState
                
                logger.info("User clicked '查看生成结果' button (simulated)")
                
                # 获取当前状态信息用于调试
                current_session = state_manager.get_current_session()
                if current_session:
                    logger.info(f"Current session state before transition: {current_session.current_state.value}")
                
                # 设置URL参数强制跳转到完成状态
                timestamp = str(int(datetime.now().timestamp()))
                st.query_params.update({"step": "completed", "t": timestamp})
                
                # 同时更新session状态确保一致性
                session = state_manager.get_current_session()
                if session:
                    session.current_state = WorkflowState.COMPLETED
                    session.last_updated = datetime.now()
                    st.session_state.intelligent_workflow_session = session
                    
                    # 安全保存session
                    try:
                        state_manager._safe_save_session(session)
                        logger.info("Session saved successfully")
                    except Exception as backup_error:
                        logger.warning(f"Session backup failed: {backup_error}")
                        # 继续执行，不让备份失败影响主流程
                else:
                    logger.error("No current session found!")
                
                logger.info("Triggering page rerun...")
                st.success("✅ 正在跳转到结果页面...")
                st.rerun()


def render_workflow_completed_step(state_manager):
    """渲染工作流完成步骤"""
    st.header("✅ 工作流完成")
    st.success("🎉 恭喜！A+ 页面图片生成工作流已完成")
    
    # 获取生成结果
    generated_images = state_manager.get_generated_images()
    final_content = state_manager.get_final_content()
    style_config = state_manager.get_style_config()
    
    # 显示完成统计
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("生成模块数", len(generated_images) if generated_images else 0)
    
    with col2:
        total_time = sum(img.get('generation_time', 0) for img in generated_images.values()) if generated_images else 0
        st.metric("总生成时间", f"{total_time:.1f}秒")
    
    with col3:
        avg_quality = sum(img.get('quality_score', 0) for img in generated_images.values()) / len(generated_images) if generated_images else 0
        st.metric("平均质量评分", f"{avg_quality:.2f}")
    
    # 显示生成结果
    if generated_images:
        st.subheader("📊 生成结果详情")
        
        for module_name, image_data in generated_images.items():
            with st.expander(f"🖼️ {module_name}", expanded=True):
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    # 显示内容信息
                    if final_content and module_name in final_content:
                        content = final_content[module_name]
                        st.write(f"**标题**: {content.get('title', 'N/A')}")
                        st.write(f"**描述**: {content.get('description', 'N/A')}")
                    
                    # 显示图片信息
                    st.write(f"**图片路径**: {image_data.get('image_path', 'N/A')}")
                    if image_data.get('is_simulated'):
                        st.info("🔄 这是模拟生成的结果")
                
                with col2:
                    # 显示生成统计
                    st.write("**生成统计**")
                    st.write(f"生成时间: {image_data.get('generation_time', 0):.2f}秒")
                    st.write(f"质量评分: {image_data.get('quality_score', 0):.2f}")
    
    # 显示风格配置
    if style_config:
        st.subheader("🎨 使用的风格配置")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.write(f"**风格**: {style_config.get('style', 'N/A')}")
        
        with col2:
            st.write(f"**颜色主题**: {style_config.get('color_theme', 'N/A')}")
        
        with col3:
            st.write(f"**布局**: {style_config.get('layout', 'N/A')}")
    
    # 操作按钮
    st.subheader("🔄 后续操作")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🔄 重新开始", type="secondary", use_container_width=True):
            # 重置工作流
            state_manager.reset_workflow()
            st.success("✅ 工作流已重置")
            st.rerun()
    
    with col2:
        if st.button("📝 修改内容", type="secondary", use_container_width=True):
            # 返回内容编辑步骤
            session = state_manager.get_current_session()
            if session:
                session.current_state = WorkflowState.CONTENT_EDITING
                session.last_updated = datetime.now()
                st.session_state.intelligent_workflow_session = session
            st.rerun()
    
    with col3:
        if st.button("🎨 更换风格", type="secondary", use_container_width=True):
            # 返回风格选择步骤
            session = state_manager.get_current_session()
            if session:
                session.current_state = WorkflowState.STYLE_SELECTION
                session.last_updated = datetime.now()
                st.session_state.intelligent_workflow_session = session
            st.rerun()
    
    # 导出功能（未来扩展）
    st.subheader("📤 导出选项")
    st.info("🚧 导出功能正在开发中...")


# 智能推荐相关辅助函数
def _generate_intelligent_recommendation(analysis_result: Dict[str, Any], options: Dict[str, Any]) -> Dict[str, Any]:
    """生成智能模块推荐"""
    try:
        # 获取产品信息
        product_type = analysis_result.get('product_type', '未识别')
        selling_points = analysis_result.get('selling_points', [])
        target_audience = analysis_result.get('target_audience', '通用用户')
        
        # 基于产品类型的基础推荐
        base_recommendations = _get_base_recommendations_by_type(product_type)
        
        # 基于卖点的推荐
        selling_point_recommendations = _get_recommendations_by_selling_points(selling_points)
        
        # 基于目标受众的推荐
        audience_recommendations = _get_recommendations_by_audience(target_audience)
        
        # 合并推荐结果
        all_recommendations = []
        all_recommendations.extend(base_recommendations)
        all_recommendations.extend(selling_point_recommendations)
        all_recommendations.extend(audience_recommendations)
        
        # 去重并排序
        unique_recommendations = _deduplicate_and_rank_recommendations(all_recommendations)
        
        # 应用用户选项
        filtered_recommendations = _apply_user_options(unique_recommendations, options)
        
        return {
            'recommended_modules': filtered_recommendations[:8],  # 最多推荐8个模块
            'confidence_score': _calculate_confidence_score(analysis_result, filtered_recommendations),
            'reasoning': _generate_recommendation_reasoning(product_type, selling_points, target_audience)
        }
        
    except Exception as e:
        logger.error(f"Intelligent recommendation generation failed: {str(e)}")
        return _get_fallback_recommendations()


def _get_base_recommendations_by_type(product_type: str) -> List[Dict[str, Any]]:
    """根据产品类型获取基础推荐"""
    type_mapping = {
        '电子产品': [
            {'module': ModuleType.TECH_SPECS, 'priority': 9, 'reason': '电子产品需要详细技术规格'},
            {'module': ModuleType.PRODUCT_FEATURES, 'priority': 8, 'reason': '突出产品功能特性'},
            {'module': ModuleType.USE_CASES, 'priority': 7, 'reason': '展示使用场景'},
            {'module': ModuleType.COMPARISON, 'priority': 6, 'reason': '与竞品对比优势'}
        ],
        '服装': [
            {'module': ModuleType.PRODUCT_FEATURES, 'priority': 9, 'reason': '展示服装特色'},
            {'module': ModuleType.SIZE_GUIDE, 'priority': 8, 'reason': '尺码指导很重要'},
            {'module': ModuleType.MATERIAL_INFO, 'priority': 7, 'reason': '材质信息关键'},
            {'module': ModuleType.STYLE_GUIDE, 'priority': 6, 'reason': '搭配建议'}
        ],
        '家居用品': [
            {'module': ModuleType.PRODUCT_FEATURES, 'priority': 8, 'reason': '产品功能展示'},
            {'module': ModuleType.USE_CASES, 'priority': 7, 'reason': '家居使用场景'},
            {'module': ModuleType.DIMENSIONS, 'priority': 6, 'reason': '尺寸规格重要'},
            {'module': ModuleType.CARE_INSTRUCTIONS, 'priority': 5, 'reason': '保养说明'}
        ],
        '美妆护肤': [
            {'module': ModuleType.PRODUCT_FEATURES, 'priority': 9, 'reason': '成分功效展示'},
            {'module': ModuleType.BEFORE_AFTER, 'priority': 8, 'reason': '使用前后对比'},
            {'module': ModuleType.USAGE_GUIDE, 'priority': 7, 'reason': '使用方法指导'},
            {'module': ModuleType.INGREDIENTS, 'priority': 6, 'reason': '成分说明'}
        ]
    }
    
    return type_mapping.get(product_type, [
        {'module': ModuleType.PRODUCT_FEATURES, 'priority': 7, 'reason': '通用产品特性'},
        {'module': ModuleType.USE_CASES, 'priority': 6, 'reason': '使用场景展示'},
        {'module': ModuleType.QUALITY_ASSURANCE, 'priority': 5, 'reason': '质量保证'}
    ])


def _get_recommendations_by_selling_points(selling_points: List[str]) -> List[Dict[str, Any]]:
    """根据卖点获取推荐"""
    recommendations = []
    
    for point in selling_points:
        point_lower = point.lower()
        
        if any(keyword in point_lower for keyword in ['质量', '品质', '耐用']):
            recommendations.append({
                'module': ModuleType.QUALITY_ASSURANCE, 
                'priority': 8, 
                'reason': f'突出"{point}"卖点'
            })
        
        elif any(keyword in point_lower for keyword in ['技术', '科技', '创新']):
            recommendations.append({
                'module': ModuleType.TECH_SPECS, 
                'priority': 8, 
                'reason': f'展示"{point}"优势'
            })
        
        elif any(keyword in point_lower for keyword in ['性价比', '价格', '实惠']):
            recommendations.append({
                'module': ModuleType.COMPARISON, 
                'priority': 7, 
                'reason': f'通过对比突出"{point}"'
            })
        
        elif any(keyword in point_lower for keyword in ['环保', '绿色', '可持续']):
            recommendations.append({
                'module': ModuleType.SUSTAINABILITY, 
                'priority': 7, 
                'reason': f'强调"{point}"理念'
            })
    
    return recommendations


def _get_recommendations_by_audience(target_audience: str) -> List[Dict[str, Any]]:
    """根据目标受众获取推荐"""
    audience_lower = target_audience.lower()
    
    if any(keyword in audience_lower for keyword in ['专业', '技术', '工程师']):
        return [
            {'module': ModuleType.TECH_SPECS, 'priority': 9, 'reason': '专业用户需要详细技术信息'},
            {'module': ModuleType.COMPARISON, 'priority': 7, 'reason': '专业用户重视对比分析'}
        ]
    
    elif any(keyword in audience_lower for keyword in ['家庭', '家长', '儿童']):
        return [
            {'module': ModuleType.SAFETY_INFO, 'priority': 8, 'reason': '家庭用户关注安全'},
            {'module': ModuleType.USE_CASES, 'priority': 7, 'reason': '展示家庭使用场景'}
        ]
    
    elif any(keyword in audience_lower for keyword in ['年轻', '时尚', '潮流']):
        return [
            {'module': ModuleType.STYLE_GUIDE, 'priority': 8, 'reason': '年轻用户关注时尚'},
            {'module': ModuleType.SOCIAL_PROOF, 'priority': 7, 'reason': '社交认证很重要'}
        ]
    
    return [
        {'module': ModuleType.PRODUCT_FEATURES, 'priority': 6, 'reason': '通用受众推荐'},
        {'module': ModuleType.USE_CASES, 'priority': 5, 'reason': '使用场景展示'}
    ]


def _deduplicate_and_rank_recommendations(recommendations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """去重并排序推荐结果"""
    # 按模块类型去重，保留优先级最高的
    module_dict = {}
    
    for rec in recommendations:
        module = rec['module']
        if module not in module_dict or rec['priority'] > module_dict[module]['priority']:
            module_dict[module] = rec
    
    # 按优先级排序
    sorted_recommendations = sorted(module_dict.values(), key=lambda x: x['priority'], reverse=True)
    
    return sorted_recommendations


def _apply_user_options(recommendations: List[Dict[str, Any]], options: Dict[str, Any]) -> List[Dict[str, Any]]:
    """应用用户选项过滤推荐"""
    filtered = recommendations.copy()
    
    # 应用模块数量限制
    max_modules = options.get('max_modules', 8)
    filtered = filtered[:max_modules]
    
    # 应用优先级过滤
    min_priority = options.get('min_priority', 0)
    filtered = [rec for rec in filtered if rec['priority'] >= min_priority]
    
    # 应用模块类型过滤
    excluded_types = options.get('excluded_types', [])
    filtered = [rec for rec in filtered if rec['module'] not in excluded_types]
    
    return filtered


def _calculate_confidence_score(analysis_result: Dict[str, Any], recommendations: List[Dict[str, Any]]) -> float:
    """计算推荐置信度"""
    base_score = 0.7
    
    # 根据分析结果的完整性调整
    if analysis_result.get('product_type') != '未识别':
        base_score += 0.1
    
    if analysis_result.get('selling_points'):
        base_score += 0.1
    
    if analysis_result.get('target_audience') != '通用用户':
        base_score += 0.1
    
    # 根据推荐数量调整
    if len(recommendations) >= 5:
        base_score += 0.05
    
    return min(base_score, 1.0)


def _generate_recommendation_reasoning(product_type: str, selling_points: List[str], target_audience: str) -> str:
    """生成推荐理由"""
    reasoning_parts = []
    
    reasoning_parts.append(f"基于产品类型'{product_type}'的特点")
    
    if selling_points:
        reasoning_parts.append(f"结合主要卖点：{', '.join(selling_points[:3])}")
    
    if target_audience != '通用用户':
        reasoning_parts.append(f"针对目标受众'{target_audience}'的需求")
    
    return "，".join(reasoning_parts) + "，为您推荐以下模块组合。"


def _get_fallback_recommendations() -> Dict[str, Any]:
    """获取备用推荐"""
    return {
        'recommended_modules': [
            {'module': ModuleType.PRODUCT_FEATURES, 'priority': 7, 'reason': '产品特性展示'},
            {'module': ModuleType.USE_CASES, 'priority': 6, 'reason': '使用场景介绍'},
            {'module': ModuleType.QUALITY_ASSURANCE, 'priority': 5, 'reason': '质量保证说明'}
        ],
        'confidence_score': 0.5,
        'reasoning': '使用默认推荐模块组合'
    }


if __name__ == "__main__":
    main()
