"""
A+ Studio 预览和管理界面

为生成的模块提供预览、管理和导出功能。
"""

import streamlit as st
from typing import List, Dict, Any, Optional
from PIL import Image
import io
import zipfile
from datetime import datetime
from services.aplus_studio.models import (
    ModuleType, GeneratedModule, ComplianceStatus, ValidationStatus
)


def render_preview_interface(generated_modules: Dict[ModuleType, GeneratedModule]) -> Dict[str, Any]:
    """
    渲染预览和管理界面
    
    Args:
        generated_modules: 已生成的模块字典
        
    Returns:
        用户操作结果
    """
    if not generated_modules:
        st.info("还没有生成的模块，请先完成模块生成")
        return {}
    
    st.header("🖼️ 模块预览")
    st.markdown(f"共生成了 {len(generated_modules)} 个模块")
    
    # 预览模式选择
    view_mode = st.radio(
        "预览模式",
        ["网格视图", "列表视图", "对比视图"],
        horizontal=True
    )
    
    # 筛选和排序选项
    col1, col2, col3 = st.columns(3)
    
    with col1:
        quality_filter = st.selectbox(
            "质量筛选",
            ["全部", "高质量 (>0.8)", "中等质量 (0.6-0.8)", "需要改进 (<0.6)"]
        )
    
    with col2:
        compliance_filter = st.selectbox(
            "合规筛选",
            ["全部", "已合规", "需要优化", "不合规"]
        )
    
    with col3:
        sort_by = st.selectbox(
            "排序方式",
            ["生成时间", "质量分数", "模块类型", "合规状态"]
        )
    
    # 筛选模块
    filtered_modules = _filter_modules(generated_modules, quality_filter, compliance_filter)
    sorted_modules = _sort_modules(filtered_modules, sort_by)
    
    # 根据视图模式渲染
    if view_mode == "网格视图":
        action = _render_grid_view(sorted_modules)
    elif view_mode == "列表视图":
        action = _render_list_view(sorted_modules)
    else:  # 对比视图
        action = _render_comparison_view(sorted_modules)
    
    # 批量操作区域
    st.markdown("---")
    batch_action = _render_batch_operations(sorted_modules)
    
    # 合并操作结果
    result = {}
    if action:
        result.update(action)
    if batch_action:
        result.update(batch_action)
    
    return result


def _render_grid_view(modules: Dict[ModuleType, GeneratedModule]) -> Dict[str, Any]:
    """渲染网格视图"""
    st.subheader("📱 网格视图")
    
    # 创建网格布局 (3列)
    cols = st.columns(3)
    selected_modules = []
    
    for i, (module_type, module) in enumerate(modules.items()):
        col_idx = i % 3
        
        with cols[col_idx]:
            # 模块卡片
            with st.container():
                # 卡片头部
                display_name = _get_module_display_name(module_type)
                st.markdown(f"### {display_name}")
                
                # 图片预览
                if module.image_data:
                    image = Image.open(io.BytesIO(module.image_data))
                    st.image(image, use_column_width=True)
                else:
                    st.info("无图片数据")
                
                # 模块信息
                col_a, col_b = st.columns(2)
                
                with col_a:
                    # 质量分数
                    quality_color = _get_quality_color(module.quality_score)
                    st.markdown(f"**质量**: <span style='color:{quality_color}'>{module.quality_score:.2f}</span>", 
                              unsafe_allow_html=True)
                
                with col_b:
                    # 合规状态
                    compliance_icon = _get_compliance_icon(module.compliance_status)
                    st.markdown(f"**合规**: {compliance_icon}")
                
                # 操作按钮
                col_c, col_d = st.columns(2)
                
                with col_c:
                    if st.button("🔍 查看", key=f"view_{module_type.value}"):
                        return {"action": "view_detail", "module_type": module_type}
                
                with col_d:
                    select_key = f"select_{module_type.value}"
                    if st.checkbox("选择", key=select_key):
                        selected_modules.append(module_type)
                
                # 生成时间
                st.caption(f"生成于: {module.generation_timestamp.strftime('%m-%d %H:%M')}")
                
                st.markdown("---")
    
    # 保存选择状态
    if selected_modules:
        st.session_state['selected_modules_for_batch'] = selected_modules
    
    return {}


def _render_list_view(modules: Dict[ModuleType, GeneratedModule]) -> Dict[str, Any]:
    """渲染列表视图"""
    st.subheader("📋 列表视图")
    
    for module_type, module in modules.items():
        with st.expander(f"📄 {_get_module_display_name(module_type)}", expanded=False):
            col1, col2 = st.columns([1, 2])
            
            with col1:
                # 缩略图
                if module.image_data:
                    image = Image.open(io.BytesIO(module.image_data))
                    st.image(image, width=200)
                else:
                    st.info("无图片")
            
            with col2:
                # 详细信息
                st.write(f"**质量分数**: {module.quality_score:.2f}")
                st.write(f"**合规状态**: {_get_compliance_text(module.compliance_status)}")
                st.write(f"**验证状态**: {module.validation_status.value}")
                st.write(f"**生成时间**: {module.generation_timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
                st.write(f"**生成耗时**: {module.generation_time:.1f}秒")
                
                # 元数据
                if module.metadata:
                    with st.expander("📊 元数据", expanded=False):
                        st.json(module.metadata)
                
                # 操作按钮
                col_a, col_b, col_c = st.columns(3)
                
                with col_a:
                    if st.button("🔍 详细查看", key=f"detail_{module_type.value}"):
                        return {"action": "view_detail", "module_type": module_type}
                
                with col_b:
                    if st.button("📥 下载", key=f"download_{module_type.value}"):
                        return {"action": "download", "module_type": module_type}
                
                with col_c:
                    if st.button("🔄 重新生成", key=f"regen_{module_type.value}"):
                        return {"action": "regenerate", "module_type": module_type}
    
    return {}


def _render_comparison_view(modules: Dict[ModuleType, GeneratedModule]) -> Dict[str, Any]:
    """渲染对比视图"""
    st.subheader("⚖️ 对比视图")
    
    if len(modules) < 2:
        st.info("至少需要2个模块才能进行对比")
        return {}
    
    # 选择要对比的模块
    module_list = list(modules.keys())
    
    col1, col2 = st.columns(2)
    
    with col1:
        module1 = st.selectbox(
            "选择模块1",
            module_list,
            format_func=_get_module_display_name,
            key="compare_module1"
        )
    
    with col2:
        module2 = st.selectbox(
            "选择模块2", 
            [m for m in module_list if m != module1],
            format_func=_get_module_display_name,
            key="compare_module2"
        )
    
    if module1 and module2:
        # 并排显示对比
        col_a, col_b = st.columns(2)
        
        with col_a:
            _render_module_comparison_card(module1, modules[module1], "A")
        
        with col_b:
            _render_module_comparison_card(module2, modules[module2], "B")
        
        # 对比分析
        st.markdown("---")
        st.subheader("📊 对比分析")
        
        _render_comparison_analysis(modules[module1], modules[module2])
    
    return {}


def _render_module_comparison_card(module_type: ModuleType, module: GeneratedModule, label: str) -> None:
    """渲染模块对比卡片"""
    st.markdown(f"### {label}. {_get_module_display_name(module_type)}")
    
    # 图片
    if module.image_data:
        image = Image.open(io.BytesIO(module.image_data))
        st.image(image, use_column_width=True)
    
    # 指标
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric("质量分数", f"{module.quality_score:.2f}")
        st.metric("生成时间", f"{module.generation_time:.1f}s")
    
    with col2:
        st.write(f"**合规**: {_get_compliance_text(module.compliance_status)}")
        st.write(f"**验证**: {module.validation_status.value}")


def _render_comparison_analysis(module1: GeneratedModule, module2: GeneratedModule) -> None:
    """渲染对比分析"""
    col1, col2, col3 = st.columns(3)
    
    with col1:
        quality_diff = module1.quality_score - module2.quality_score
        if quality_diff > 0:
            st.success(f"模块A质量更高 (+{quality_diff:.2f})")
        elif quality_diff < 0:
            st.warning(f"模块B质量更高 (+{abs(quality_diff):.2f})")
        else:
            st.info("质量分数相同")
    
    with col2:
        time_diff = module1.generation_time - module2.generation_time
        if time_diff > 0:
            st.info(f"模块B生成更快 (-{time_diff:.1f}s)")
        elif time_diff < 0:
            st.info(f"模块A生成更快 (-{abs(time_diff):.1f}s)")
        else:
            st.info("生成时间相同")
    
    with col3:
        # 合规对比
        if module1.compliance_status == module2.compliance_status:
            st.info("合规状态相同")
        else:
            st.warning("合规状态不同")


def _render_batch_operations(modules: Dict[ModuleType, GeneratedModule]) -> Dict[str, Any]:
    """渲染批量操作区域"""
    st.subheader("🔧 批量操作")
    
    # 获取选中的模块
    selected_modules = st.session_state.get('selected_modules_for_batch', [])
    
    if not selected_modules:
        st.info("请在上方选择要操作的模块")
        return {}
    
    st.write(f"已选择 {len(selected_modules)} 个模块")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("📥 批量下载", use_container_width=True):
            return {"action": "batch_download", "modules": selected_modules}
    
    with col2:
        if st.button("🔄 批量重生成", use_container_width=True):
            return {"action": "batch_regenerate", "modules": selected_modules}
    
    with col3:
        if st.button("📊 质量分析", use_container_width=True):
            return {"action": "quality_analysis", "modules": selected_modules}
    
    with col4:
        if st.button("🗑️ 批量删除", use_container_width=True):
            return {"action": "batch_delete", "modules": selected_modules}
    
    # 导出选项
    st.markdown("**📤 导出选项**")
    
    col_a, col_b = st.columns(2)
    
    with col_a:
        export_format = st.selectbox(
            "导出格式",
            ["PNG", "JPG", "PDF报告", "ZIP压缩包"]
        )
    
    with col_b:
        include_metadata = st.checkbox("包含元数据", value=True)
    
    if st.button("🚀 开始导出", type="primary", use_container_width=True):
        return {
            "action": "export",
            "modules": selected_modules,
            "format": export_format,
            "include_metadata": include_metadata
        }
    
    return {}


def render_module_detail_modal(module_type: ModuleType, module: GeneratedModule) -> None:
    """渲染模块详细信息模态框"""
    st.modal(f"🔍 {_get_module_display_name(module_type)} - 详细信息")
    
    # 图片显示
    if module.image_data:
        image = Image.open(io.BytesIO(module.image_data))
        st.image(image, caption="生成的图片", use_column_width=True)
    
    # 基本信息
    st.subheader("📋 基本信息")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write(f"**模块类型**: {_get_module_display_name(module_type)}")
        st.write(f"**质量分数**: {module.quality_score:.2f}")
        st.write(f"**生成时间**: {module.generation_time:.1f}秒")
    
    with col2:
        st.write(f"**合规状态**: {_get_compliance_text(module.compliance_status)}")
        st.write(f"**验证状态**: {module.validation_status.value}")
        st.write(f"**生成时间**: {module.generation_timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 使用的提示词
    if module.prompt_used:
        st.subheader("🎯 生成提示词")
        st.text_area("", value=module.prompt_used, height=150, disabled=True)
    
    # 元数据
    if module.metadata:
        st.subheader("📊 详细元数据")
        st.json(module.metadata)
    
    # 使用的素材
    if module.materials_used:
        st.subheader("📁 使用的素材")
        
        if module.materials_used.images:
            st.write(f"**图片**: {len(module.materials_used.images)} 张")
        
        if module.materials_used.documents:
            st.write(f"**文档**: {len(module.materials_used.documents)} 个")
        
        if module.materials_used.text_inputs:
            st.write(f"**文本输入**: {len(module.materials_used.text_inputs)} 项")
        
        if module.materials_used.custom_prompts:
            st.write(f"**自定义提示**: {len(module.materials_used.custom_prompts)} 项")
    
    # 操作按钮
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📥 下载图片", use_container_width=True):
            _download_module_image(module_type, module)
    
    with col2:
        if st.button("🔄 重新生成", use_container_width=True):
            st.session_state['regenerate_module'] = module_type
            st.rerun()
    
    with col3:
        if st.button("❌ 关闭", use_container_width=True):
            st.session_state['show_detail_modal'] = False
            st.rerun()


def _filter_modules(modules: Dict[ModuleType, GeneratedModule], 
                   quality_filter: str, compliance_filter: str) -> Dict[ModuleType, GeneratedModule]:
    """筛选模块"""
    filtered = {}
    
    for module_type, module in modules.items():
        # 质量筛选
        if quality_filter == "高质量 (>0.8)" and module.quality_score <= 0.8:
            continue
        elif quality_filter == "中等质量 (0.6-0.8)" and not (0.6 <= module.quality_score <= 0.8):
            continue
        elif quality_filter == "需要改进 (<0.6)" and module.quality_score >= 0.6:
            continue
        
        # 合规筛选
        if compliance_filter == "已合规" and module.compliance_status != ComplianceStatus.COMPLIANT:
            continue
        elif compliance_filter == "需要优化" and module.compliance_status != ComplianceStatus.NEEDS_OPTIMIZATION:
            continue
        elif compliance_filter == "不合规" and module.compliance_status != ComplianceStatus.NON_COMPLIANT:
            continue
        
        filtered[module_type] = module
    
    return filtered


def _sort_modules(modules: Dict[ModuleType, GeneratedModule], sort_by: str) -> Dict[ModuleType, GeneratedModule]:
    """排序模块"""
    if sort_by == "质量分数":
        sorted_items = sorted(modules.items(), key=lambda x: x[1].quality_score, reverse=True)
    elif sort_by == "生成时间":
        sorted_items = sorted(modules.items(), key=lambda x: x[1].generation_timestamp, reverse=True)
    elif sort_by == "模块类型":
        sorted_items = sorted(modules.items(), key=lambda x: x[0].value)
    else:  # 合规状态
        compliance_order = {
            ComplianceStatus.COMPLIANT: 0,
            ComplianceStatus.NEEDS_OPTIMIZATION: 1,
            ComplianceStatus.NON_COMPLIANT: 2,
            ComplianceStatus.PENDING_REVIEW: 3
        }
        sorted_items = sorted(modules.items(), key=lambda x: compliance_order.get(x[1].compliance_status, 4))
    
    return dict(sorted_items)


def _get_module_display_name(module_type: ModuleType) -> str:
    """获取模块显示名称"""
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


def _get_quality_color(quality_score: float) -> str:
    """获取质量分数对应的颜色"""
    if quality_score >= 0.8:
        return "#4CAF50"  # 绿色
    elif quality_score >= 0.6:
        return "#FF9800"  # 橙色
    else:
        return "#F44336"  # 红色


def _get_compliance_icon(compliance_status: ComplianceStatus) -> str:
    """获取合规状态图标"""
    icons = {
        ComplianceStatus.COMPLIANT: "✅",
        ComplianceStatus.NEEDS_OPTIMIZATION: "⚠️",
        ComplianceStatus.NON_COMPLIANT: "❌",
        ComplianceStatus.PENDING_REVIEW: "⏳"
    }
    return icons.get(compliance_status, "❓")


def _get_compliance_text(compliance_status: ComplianceStatus) -> str:
    """获取合规状态文本"""
    texts = {
        ComplianceStatus.COMPLIANT: "已合规",
        ComplianceStatus.NEEDS_OPTIMIZATION: "需要优化",
        ComplianceStatus.NON_COMPLIANT: "不合规",
        ComplianceStatus.PENDING_REVIEW: "待审核"
    }
    return texts.get(compliance_status, "未知")


def _download_module_image(module_type: ModuleType, module: GeneratedModule) -> None:
    """下载模块图片"""
    if module.image_data:
        filename = f"{_get_module_display_name(module_type)}_{datetime.now().strftime('%m%d_%H%M')}.png"
        
        st.download_button(
            "📥 下载图片",
            data=module.image_data,
            file_name=filename,
            mime="image/png"
        )