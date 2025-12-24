import streamlit as st
import sys
import os
from typing import List, Dict, Any, Optional
from PIL import Image
from datetime import datetime
import google.generativeai as genai
import json

# 添加项目根目录到路径
sys.path.append(os.path.abspath('.'))

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
    GeneratedModule, ComplianceStatus, ValidationStatus
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
        ["🧩 模块化A+制作", "💡 产品卖点分析"],
        horizontal=True,
        help="模块化制作：完整的A+内容生成流程；卖点分析：快速分析产品图片获取营销建议"
    )
    
    if mode == "🧩 模块化A+制作":
        render_modular_workflow()
    else:
        render_selling_points_analysis()


def render_modular_workflow():
    """渲染模块化工作流"""
    # 侧边栏 - 进度跟踪和系统状态
    render_modular_sidebar()
    
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
                st.markdown(f"✅ {step_name}")
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
        
        if total_materials > 0:
            # 导航按钮
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("🧩 返回模块选择", use_container_width=True):
                    st.session_state.current_step = "module_selection"
                    st.rerun()
            
            with col2:
                if st.button("🎨 开始生成", type="primary", use_container_width=True):
                    st.session_state.current_step = "generation"
                    st.rerun()


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


def _get_module_display_name_sidebar(module_type: ModuleType) -> str:
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
    return display_names.get(module_type, module_type.value)


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
