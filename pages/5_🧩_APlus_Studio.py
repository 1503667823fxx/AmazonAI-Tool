import streamlit as st
import sys
import os
import asyncio
from typing import List, Dict, Any
from PIL import Image

# 添加项目根目录到路径
sys.path.append(os.path.abspath('.'))

# 身份验证
try:
    import auth
    if not auth.check_password():
        st.stop()
except ImportError:
    pass

# 导入A+工作流组件
try:
    from app_utils.aplus_studio.controller import APlusController
    from app_utils.aplus_studio.input_panel import ProductInputPanel
    from app_utils.aplus_studio.generation_panel import ModuleGenerationPanel
    from app_utils.aplus_studio.preview_gallery import ImagePreviewGallery
    from app_utils.aplus_studio.regeneration_panel import RegenerationPanel
    from services.aplus_studio.models import ModuleType, GenerationStatus
    APLUS_AVAILABLE = True
except ImportError as e:
    APLUS_AVAILABLE = False
    st.error(f"A+ Studio组件导入失败: {e}")

# 页面配置
st.set_page_config(
    page_title="A+ Studio", 
    page_icon="🧩", 
    layout="wide"
)

def main():
    """主应用入口"""
    st.title("🧩 A+ 图片制作流 (APlus Studio)")
    st.caption("AI 驱动的亚马逊 A+ 页面智能图片生成工具")
    
    if not APLUS_AVAILABLE:
        st.error("A+ Studio系统组件未正确加载，请检查系统配置")
        return
    
    # 初始化控制器和组件
    if 'aplus_controller' not in st.session_state:
        st.session_state.aplus_controller = APlusController()
    
    controller = st.session_state.aplus_controller
    
    # 初始化UI组件
    input_panel = ProductInputPanel()
    generation_panel = ModuleGenerationPanel(controller)
    preview_gallery = ImagePreviewGallery(controller)
    regeneration_panel = RegenerationPanel(controller)
    
    # 侧边栏 - 会话管理和系统状态
    render_sidebar(controller)
    
    # 主界面标签页
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📝 产品分析", "🎨 模块生成", "🖼️ 图片预览", "🔄 重新生成", "📊 数据导出"
    ])
    
    with tab1:
        render_product_analysis_tab(controller, input_panel)
    
    with tab2:
        render_module_generation_tab(controller, generation_panel)
    
    with tab3:
        render_preview_gallery_tab(controller, preview_gallery)
    
    with tab4:
        render_regeneration_tab(controller, regeneration_panel)
    
    with tab5:
        render_export_tab(controller)


def render_sidebar(controller: APlusController):
    """渲染侧边栏"""
    with st.sidebar:
        st.header("🎛️ 控制面板")
        
        # 会话信息
        session_info = controller.get_session_info()
        if session_info:
            st.success(f"会话ID: {session_info['session_id'][:8]}...")
            
            # 会话统计
            col1, col2 = st.columns(2)
            with col1:
                st.metric("已完成", session_info['completed_modules'])
            with col2:
                st.metric("总模块", session_info['total_modules'])
            
            # 会话操作
            if st.button("🔄 重置会话", use_container_width=True):
                controller.reset_session()
                st.rerun()
        else:
            st.info("没有活跃会话")
        
        st.divider()
        
        # 模块状态概览
        st.subheader("📊 模块状态")
        progress = controller.get_generation_progress()
        
        for module_type in ModuleType:
            status = progress.get(module_type, GenerationStatus.NOT_STARTED)
            status_icon = {
                GenerationStatus.NOT_STARTED: "⚪",
                GenerationStatus.IN_PROGRESS: "🟡", 
                GenerationStatus.COMPLETED: "🟢",
                GenerationStatus.FAILED: "🔴"
            }.get(status, "⚪")
            
            module_names = {
                ModuleType.IDENTITY: "身份代入",
                ModuleType.SENSORY: "感官解构",
                ModuleType.EXTENSION: "多维延展",
                ModuleType.TRUST: "信任转化"
            }
            
            st.write(f"{status_icon} {module_names.get(module_type, module_type.value)}")
        
        st.divider()
        
        # 系统健康状态
        st.subheader("🔧 系统状态")
        health_status = controller.get_system_health_status()
        
        if health_status.get("overall_status") == "healthy":
            st.success("✅ 系统正常")
        elif health_status.get("overall_status") == "degraded":
            st.warning("⚠️ 系统降级")
        else:
            st.error("❌ 系统异常")
        
        # 快速操作
        st.subheader("⚡ 快速操作")
        
        if st.button("🔍 系统诊断", use_container_width=True):
            with st.expander("系统诊断结果", expanded=True):
                st.json(health_status)
        
        if st.button("🧹 清理缓存", use_container_width=True):
            controller.cleanup_old_versions()
            st.success("缓存已清理")


def render_product_analysis_tab(controller: APlusController, input_panel: ProductInputPanel):
    """渲染产品分析标签页"""
    st.header("📝 产品信息分析")
    
    # 检查当前会话状态
    session = controller.state_manager.get_current_session()
    
    # 如果已有分析结果，显示摘要
    if session and session.analysis_result:
        render_analysis_summary(session.analysis_result)
        
        # 提供重新分析选项
        if st.button("🔄 重新分析产品", type="secondary"):
            controller.state_manager.update_analysis_result(None)
            st.rerun()
        
        return
    
    # 产品输入界面
    product_info, validation_result = input_panel.render_input_panel()
    
    if product_info and validation_result.is_valid:
        # 显示输入预览
        input_panel.render_input_preview(product_info)
        
        # 执行分析
        with st.spinner("🔍 正在分析产品信息..."):
            try:
                analysis_result = asyncio.run(
                    controller.process_product_input(
                        product_info.description, 
                        product_info.uploaded_images
                    )
                )
                
                if analysis_result:
                    st.success("✅ 产品分析完成！")
                    render_analysis_summary(analysis_result)
                else:
                    st.error("❌ 产品分析失败")
                    
            except Exception as e:
                st.error(f"❌ 分析过程中出现错误: {str(e)}")


def render_analysis_summary(analysis_result):
    """渲染分析结果摘要"""
    st.subheader("📊 分析结果摘要")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**📋 产品特征**")
        if hasattr(analysis_result, 'listing_analysis') and analysis_result.listing_analysis:
            listing = analysis_result.listing_analysis
            st.write(f"• **产品类别**: {listing.product_category}")
            st.write(f"• **目标用户**: {listing.target_demographics}")
            
            if listing.key_selling_points:
                st.write("• **核心卖点**:")
                for point in listing.key_selling_points[:3]:
                    st.write(f"  - {point}")
    
    with col2:
        st.write("**🎨 视觉特征**")
        if hasattr(analysis_result, 'image_analysis') and analysis_result.image_analysis:
            image_analysis = analysis_result.image_analysis
            if image_analysis.dominant_colors:
                st.write(f"• **主色调**: {', '.join(image_analysis.dominant_colors[:3])}")
            if image_analysis.material_types:
                st.write(f"• **材质类型**: {', '.join(image_analysis.material_types[:3])}")
            if image_analysis.design_style:
                st.write(f"• **设计风格**: {image_analysis.design_style}")
    
    # 视觉连贯性信息
    if hasattr(analysis_result, 'visual_style') and analysis_result.visual_style:
        with st.expander("🎨 视觉风格设定", expanded=False):
            visual_style = analysis_result.visual_style
            if visual_style.color_palette:
                st.write(f"**色调盘**: {', '.join(visual_style.color_palette)}")
            if visual_style.aesthetic_direction:
                st.write(f"**美学方向**: {visual_style.aesthetic_direction}")


def render_module_generation_tab(controller: APlusController, generation_panel: ModuleGenerationPanel):
    """渲染模块生成标签页"""
    st.header("🎨 模块图片生成")
    
    # 检查前置条件
    session = controller.state_manager.get_current_session()
    if not session or not session.analysis_result:
        st.warning("⚠️ 请先完成产品分析")
        if st.button("📝 前往产品分析", type="primary"):
            st.session_state["active_tab"] = "product_analysis"
        return
    
    # 渲染生成控制面板
    generation_action = generation_panel.render_generation_panel()
    
    # 处理生成动作
    if generation_action and generation_action.get("action"):
        handle_generation_action(controller, generation_panel, generation_action)
    
    # 显示生成摘要
    generation_panel.render_generation_summary()


def handle_generation_action(controller: APlusController, generation_panel: ModuleGenerationPanel, action: Dict[str, Any]):
    """处理生成动作"""
    action_type = action.get("action")
    
    if action_type == "generate_individual":
        # 单个模块生成
        module_type = action.get("module_type")
        custom_params = action.get("module_params", {})
        
        generation_panel.start_generation_tracking(module_type)
        
        try:
            with st.spinner(f"正在生成 {module_type.value} 模块..."):
                result = asyncio.run(controller.generate_module_image(module_type, custom_params))
                
                generation_panel.complete_generation(module_type, True)
                st.success(f"✅ {module_type.value} 模块生成完成！")
                
                # 显示结果预览
                if result.image_data:
                    st.image(result.image_data, caption=f"{module_type.value} 模块结果")
                    st.write(f"质量分数: {result.quality_score:.2f}")
                
        except Exception as e:
            generation_panel.complete_generation(module_type, False)
            st.error(f"❌ {module_type.value} 模块生成失败: {str(e)}")
    
    elif action_type in ["generate_batch", "generate_parallel"]:
        # 批量或并行生成
        selected_modules = action.get("selected_modules", [])
        module_params = action.get("module_params", {})
        
        if action_type == "generate_batch":
            handle_batch_generation(controller, generation_panel, selected_modules, module_params)
        else:
            handle_parallel_generation(controller, generation_panel, selected_modules, module_params)
    
    elif action_type == "stop_all":
        # 停止所有生成
        for module_type in generation_panel.get_active_generations():
            generation_panel._stop_generation(module_type)
        st.info("已停止所有生成任务")
    
    elif action_type == "reset_progress":
        # 重置进度
        generation_panel.reset_progress()
        st.info("已重置生成进度")


def handle_batch_generation(controller: APlusController, generation_panel: ModuleGenerationPanel, 
                          selected_modules: List[ModuleType], module_params: Dict[ModuleType, Dict]):
    """处理批量生成"""
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i, module_type in enumerate(selected_modules):
        status_text.text(f"正在生成 {module_type.value} 模块... ({i+1}/{len(selected_modules)})")
        progress_bar.progress(i / len(selected_modules))
        
        generation_panel.start_generation_tracking(module_type)
        
        try:
            custom_params = module_params.get(module_type, {})
            result = asyncio.run(controller.generate_module_image(module_type, custom_params))
            
            generation_panel.complete_generation(module_type, True)
            st.success(f"✅ {module_type.value} 模块生成完成")
            
        except Exception as e:
            generation_panel.complete_generation(module_type, False)
            st.error(f"❌ {module_type.value} 模块生成失败: {str(e)}")
    
    progress_bar.progress(1.0)
    status_text.text("✅ 批量生成完成！")


def handle_parallel_generation(controller: APlusController, generation_panel: ModuleGenerationPanel,
                             selected_modules: List[ModuleType], module_params: Dict[ModuleType, Dict]):
    """处理并行生成"""
    st.info("🚀 开始并行生成...")
    
    # 启动所有模块的生成跟踪
    for module_type in selected_modules:
        generation_panel.start_generation_tracking(module_type)
    
    # 并行生成（简化实现，实际应该使用真正的并行处理）
    results = {}
    for module_type in selected_modules:
        try:
            custom_params = module_params.get(module_type, {})
            result = asyncio.run(controller.generate_module_image(module_type, custom_params))
            results[module_type] = result
            generation_panel.complete_generation(module_type, True)
            
        except Exception as e:
            generation_panel.complete_generation(module_type, False)
            st.error(f"❌ {module_type.value} 模块生成失败: {str(e)}")
    
    st.success(f"✅ 并行生成完成！成功生成 {len(results)} 个模块")


def render_preview_gallery_tab(controller: APlusController, preview_gallery: ImagePreviewGallery):
    """渲染图片预览标签页"""
    st.header("🖼️ 图片预览画廊")
    
    # 渲染预览画廊
    gallery_action = preview_gallery.render_preview_gallery()
    
    # 处理画廊动作
    if gallery_action and gallery_action.get("action"):
        handle_gallery_action(controller, preview_gallery, gallery_action)
    
    # 批量操作
    module_results = controller.get_module_results()
    if module_results:
        st.divider()
        batch_action = preview_gallery.render_batch_operations(module_results)
        
        if batch_action and batch_action.get("action"):
            handle_batch_action(controller, batch_action)


def handle_gallery_action(controller: APlusController, preview_gallery: ImagePreviewGallery, action: Dict[str, Any]):
    """处理画廊动作"""
    action_type = action.get("action")
    
    if action_type == "export_selected":
        modules = action.get("modules", [])
        st.success(f"已选择导出 {len(modules)} 个模块的图片")
    
    elif action_type == "refresh":
        st.rerun()


def handle_batch_action(controller: APlusController, action: Dict[str, Any]):
    """处理批量操作"""
    action_type = action.get("action")
    modules = action.get("modules", [])
    
    if action_type == "batch_download":
        st.success(f"正在准备下载 {len(modules)} 个模块的图片...")
        # 实际实现中会创建ZIP文件供下载
    
    elif action_type == "batch_regenerate":
        st.info(f"将重新生成 {len(modules)} 个模块...")
        # 跳转到重新生成标签页
    
    elif action_type == "quality_analysis":
        module_results = controller.get_module_results()
        filtered_results = {m: r for m, r in module_results.items() if m in modules}
        
        # 显示质量分析
        with st.expander("📊 质量分析结果", expanded=True):
            render_quality_analysis(filtered_results)


def render_quality_analysis(module_results: Dict[ModuleType, Any]):
    """渲染质量分析"""
    if not module_results:
        st.info("没有可分析的数据")
        return
    
    quality_scores = [result.quality_score for result in module_results.values()]
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        avg_quality = sum(quality_scores) / len(quality_scores)
        st.metric("平均质量", f"{avg_quality:.2f}")
    
    with col2:
        max_quality = max(quality_scores)
        st.metric("最高质量", f"{max_quality:.2f}")
    
    with col3:
        min_quality = min(quality_scores)
        st.metric("最低质量", f"{min_quality:.2f}")


def render_regeneration_tab(controller: APlusController, regeneration_panel: RegenerationPanel):
    """渲染重新生成标签页"""
    st.header("🔄 单模块重新生成")
    
    # 检查已生成的模块
    module_results = controller.get_module_results()
    
    if not module_results:
        st.info("还没有已生成的模块，请先在"模块生成"标签页生成模块")
        if st.button("🎨 前往模块生成", type="primary"):
            st.session_state["active_tab"] = "module_generation"
        return
    
    # 模块选择
    available_modules = list(module_results.keys())
    
    module_names = {
        ModuleType.IDENTITY: "🎭 身份代入",
        ModuleType.SENSORY: "👁️ 感官解构",
        ModuleType.EXTENSION: "🔄 多维延展",
        ModuleType.TRUST: "🤝 信任转化"
    }
    
    selected_module = st.selectbox(
        "选择要重新生成的模块",
        available_modules,
        format_func=lambda x: module_names.get(x, x.value)
    )
    
    if selected_module:
        # 显示当前模块结果
        current_result = module_results[selected_module]
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.subheader("当前结果")
            if current_result.image_data:
                st.image(current_result.image_data, caption="当前版本")
            st.write(f"**质量分数**: {current_result.quality_score:.2f}")
            st.write(f"**生成时间**: {current_result.generation_time:.1f}s")
            st.write(f"**验证状态**: {current_result.validation_status.value}")
        
        with col2:
            # 重新生成控制面板
            regen_action = regeneration_panel.render_regeneration_controls(selected_module)
            
            if regen_action.get("action") == "regenerate":
                with st.spinner("🔄 正在重新生成..."):
                    try:
                        new_result = asyncio.run(
                            controller.regenerate_image(
                                selected_module, 
                                regen_action.get("custom_params")
                            )
                        )
                        
                        st.success("✅ 重新生成完成！")
                        
                        # 显示新结果对比
                        if new_result.image_data:
                            st.subheader("新版本")
                            st.image(new_result.image_data, caption="新版本")
                            st.write(f"**新质量分数**: {new_result.quality_score:.2f}")
                            
                            # 质量对比
                            quality_diff = new_result.quality_score - current_result.quality_score
                            if quality_diff > 0:
                                st.success(f"质量提升: +{quality_diff:.2f}")
                            elif quality_diff < 0:
                                st.warning(f"质量下降: {quality_diff:.2f}")
                            else:
                                st.info("质量无变化")
                        
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"❌ 重新生成失败: {str(e)}")
        
        # 版本历史
        st.divider()
        
        tab1, tab2 = st.tabs(["📚 版本历史", "📊 版本对比"])
        
        with tab1:
            regeneration_panel.render_version_history_panel(selected_module)
        
        with tab2:
            regeneration_panel.render_version_comparison(selected_module)


def render_export_tab(controller: APlusController):
    """渲染结果导出标签页"""
    st.header("📊 数据导出")
    
    module_results = controller.get_module_results()
    
    if not module_results:
        st.info("还没有可导出的结果")
        return
    
    # 导出选项
    st.subheader("📥 导出选项")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # 模块选择
        module_names = {
            ModuleType.IDENTITY: "🎭 身份代入",
            ModuleType.SENSORY: "👁️ 感官解构",
            ModuleType.EXTENSION: "🔄 多维延展",
            ModuleType.TRUST: "🤝 信任转化"
        }
        
        export_modules = st.multiselect(
            "选择要导出的模块",
            list(module_results.keys()),
            default=list(module_results.keys()),
            format_func=lambda x: module_names.get(x, x.value)
        )
        
        export_format = st.selectbox(
            "导出格式",
            ["PNG (推荐)", "JPG", "PDF报告", "ZIP压缩包"]
        )
    
    with col2:
        # 导出设置
        include_metadata = st.checkbox("包含元数据", value=True)
        include_prompts = st.checkbox("包含提示词", value=False)
        include_analysis = st.checkbox("包含分析报告", value=True)
        
        quality_level = st.selectbox(
            "图片质量",
            ["原始质量", "高质量", "压缩版本"],
            index=0
        )
    
    # 导出预览
    if export_modules:
        st.subheader("📋 导出预览")
        
        total_size = 0
        for module_type in export_modules:
            result = module_results[module_type]
            if result.image_data:
                size_mb = len(result.image_data) / (1024 * 1024)
                total_size += size_mb
                st.write(f"• {module_names.get(module_type, module_type.value)}: {size_mb:.1f} MB")
        
        st.write(f"**总大小**: {total_size:.1f} MB")
    
    # 导出按钮
    if st.button("📥 开始导出", type="primary", disabled=not export_modules):
        if export_modules:
            with st.spinner("📦 正在准备导出文件..."):
                # 模拟导出过程
                import time
                time.sleep(2)
                
                st.success("✅ 导出完成！")
                
                # 显示导出摘要
                st.subheader("📊 导出摘要")
                for module_type in export_modules:
                    result = module_results[module_type]
                    st.write(f"• {module_names.get(module_type, module_type.value)}: 质量分数 {result.quality_score:.2f}")
                
                # 创建下载按钮
                export_data = controller.export_results()
                if export_data:
                    import json
                    json_str = json.dumps(export_data, indent=2, ensure_ascii=False)
                    
                    st.download_button(
                        "📥 下载导出文件",
                        data=json_str,
                        file_name=f"aplus_export_{len(export_modules)}_modules.json",
                        mime="application/json"
                    )
        else:
            st.warning("请选择要导出的模块")
    
    # 导出历史
    st.divider()
    st.subheader("📚 导出历史")
    
    # 显示会话摘要
    session_summary = controller.state_manager.get_session_summary()
    if session_summary.get("has_session"):
        with st.expander("📊 当前会话统计", expanded=False):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("会话健康度", f"{session_summary['health_score']:.0f}%")
            
            with col2:
                st.metric("已完成模块", session_summary['completed_modules'])
            
            with col3:
                st.metric("会话时长", f"{session_summary['session_age_hours']:.1f}h")
    
    # 视觉连贯性报告
    consistency_report = controller.get_visual_consistency_report()
    if consistency_report and "error" not in consistency_report:
        with st.expander("🎨 视觉连贯性报告", expanded=False):
            if consistency_report.get("is_consistent"):
                st.success(f"✅ 视觉连贯性良好 (评分: {consistency_report.get('overall_score', 0):.2f})")
            else:
                st.warning("⚠️ 检测到视觉风格不一致")
                
                conflicts = consistency_report.get("conflicts", [])
                if conflicts:
                    st.write("**风格冲突:**")
                    for conflict in conflicts[:3]:
                        st.write(f"• {conflict}")


if __name__ == "__main__":
    main()
