"""
A+ Studio 模块选择界面

提供12个专业模块的选择界面，支持模块筛选、批量选择和预览功能。
"""

import streamlit as st
from typing import List, Dict, Any, Optional
from services.aplus_studio.models import ModuleType, get_new_professional_modules
from services.aplus_studio.modules import ModuleRegistry

def render_module_selector() -> Dict[str, Any]:
    """
    渲染模块选择界面
    
    Returns:
        包含选中模块和配置的字典
    """
    st.header("🧩 选择A+模块")
    st.markdown("从12个专业模块中选择您需要的模块类型")
    
    # 获取模块注册表
    registry = ModuleRegistry()
    available_modules = get_new_professional_modules()
    
    # 初始化会话状态
    if 'selected_modules' not in st.session_state:
        st.session_state.selected_modules = []
    
    # 模块筛选和搜索
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        search_term = st.text_input("🔍 搜索模块", placeholder="输入模块名称或用途...")
    
    with col2:
        category_filter = st.selectbox("📂 分类筛选", ["全部", "核心模块", "次要模块"])
    
    with col3:
        st.write("")  # 空白占位
        if st.button("🔄 重置选择"):
            st.session_state.selected_modules = []
            st.rerun()
    
    # 批量操作按钮
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("✅ 全选"):
            st.session_state.selected_modules = [m.value for m in available_modules]
            st.rerun()
    
    with col2:
        if st.button("❌ 清除全部"):
            st.session_state.selected_modules = []
            st.rerun()
    
    with col3:
        if st.button("⭐ 推荐组合"):
            # 选择推荐的核心模块组合
            recommended = [
                ModuleType.PRODUCT_OVERVIEW.value,
                ModuleType.FEATURE_ANALYSIS.value,
                ModuleType.SPECIFICATION_COMPARISON.value,
                ModuleType.USAGE_SCENARIOS.value
            ]
            st.session_state.selected_modules = recommended
            st.rerun()
    
    with col4:
        if st.button("🎯 基础套装"):
            # 选择基础模块套装
            basic = [
                ModuleType.PRODUCT_OVERVIEW.value,
                ModuleType.PROBLEM_SOLUTION.value,
                ModuleType.QUALITY_ASSURANCE.value
            ]
            st.session_state.selected_modules = basic
            st.rerun()
    
    # 筛选模块
    filtered_modules = _filter_modules(available_modules, search_term, category_filter)
    
    # 模块网格展示 (3x4布局)
    st.markdown("---")
    st.subheader("📋 可用模块")
    
    # 创建3列布局
    cols = st.columns(3)
    
    for i, module_type in enumerate(filtered_modules):
        col_idx = i % 3
        
        with cols[col_idx]:
            _render_module_card(module_type, registry)
    
    # 选择摘要
    st.markdown("---")
    _render_selection_summary()
    
    # 返回选择结果
    return {
        'selected_modules': [ModuleType(m) for m in st.session_state.selected_modules],
        'total_selected': len(st.session_state.selected_modules),
        'estimated_time': _calculate_estimated_time(st.session_state.selected_modules)
    }


def _filter_modules(modules: List[ModuleType], search_term: str, category_filter: str) -> List[ModuleType]:
    """筛选模块"""
    filtered = modules.copy()
    
    # 搜索筛选
    if search_term:
        search_lower = search_term.lower()
        filtered = [
            m for m in filtered 
            if search_lower in m.value.lower() or search_lower in _get_module_display_name(m).lower()
        ]
    
    # 分类筛选
    if category_filter == "核心模块":
        core_modules = [
            ModuleType.PRODUCT_OVERVIEW, ModuleType.PROBLEM_SOLUTION,
            ModuleType.FEATURE_ANALYSIS, ModuleType.SPECIFICATION_COMPARISON,
            ModuleType.USAGE_SCENARIOS, ModuleType.INSTALLATION_GUIDE
        ]
        filtered = [m for m in filtered if m in core_modules]
    elif category_filter == "次要模块":
        secondary_modules = [
            ModuleType.SIZE_COMPATIBILITY, ModuleType.MAINTENANCE_CARE,
            ModuleType.MATERIAL_CRAFTSMANSHIP, ModuleType.QUALITY_ASSURANCE,
            ModuleType.CUSTOMER_REVIEWS, ModuleType.PACKAGE_CONTENTS
        ]
        filtered = [m for m in filtered if m in secondary_modules]
    
    return filtered


def _render_module_card(module_type: ModuleType, registry) -> None:
    """渲染单个模块卡片"""
    # 获取模块信息
    module_info = _get_module_info(module_type, registry)
    display_name = _get_module_display_name(module_type)
    
    # 检查是否已选中
    is_selected = module_type.value in st.session_state.selected_modules
    
    # 创建卡片容器
    with st.container():
        # 卡片样式
        card_style = """
        <div style="
            border: 2px solid {};
            border-radius: 10px;
            padding: 15px;
            margin: 10px 0;
            background-color: {};
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        ">
        """.format(
            "#4CAF50" if is_selected else "#ddd",
            "#f0f8f0" if is_selected else "#ffffff"
        )
        
        st.markdown(card_style, unsafe_allow_html=True)
        
        # 模块标题和图标
        icon = "✅" if is_selected else "⬜"
        st.markdown(f"### {icon} {display_name}")
        
        # 模块描述
        st.markdown(f"**描述**: {module_info['description']}")
        
        # 推荐用例
        if module_info.get('recommended_use_cases'):
            use_cases = ", ".join(module_info['recommended_use_cases'][:2])
            st.markdown(f"**适用**: {use_cases}")
        
        # 预估时间
        est_time = module_info.get('generation_time_estimate', 60)
        st.markdown(f"**预估时间**: ~{est_time}秒")
        
        # 选择按钮
        button_text = "取消选择" if is_selected else "选择此模块"
        button_type = "secondary" if is_selected else "primary"
        
        if st.button(button_text, key=f"btn_{module_type.value}", type=button_type):
            if is_selected:
                st.session_state.selected_modules.remove(module_type.value)
            else:
                st.session_state.selected_modules.append(module_type.value)
            st.rerun()
        
        st.markdown("</div>", unsafe_allow_html=True)


def _render_selection_summary() -> None:
    """渲染选择摘要"""
    selected_count = len(st.session_state.selected_modules)
    
    if selected_count == 0:
        st.info("💡 请选择您需要的模块开始制作A+内容")
        return
    
    st.subheader("📊 选择摘要")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("已选择模块", f"{selected_count}/12")
    
    with col2:
        estimated_time = _calculate_estimated_time(st.session_state.selected_modules)
        st.metric("预估总时间", f"~{estimated_time//60}分{estimated_time%60}秒")
    
    with col3:
        completion_rate = (selected_count / 12) * 100
        st.metric("完成度", f"{completion_rate:.0f}%")
    
    # 已选择的模块列表
    if selected_count > 0:
        st.markdown("**已选择的模块:**")
        selected_names = [_get_module_display_name(ModuleType(m)) for m in st.session_state.selected_modules]
        st.markdown("• " + " • ".join(selected_names))
    
    # 进度条
    progress = selected_count / 12
    st.progress(progress)
    
    # 继续按钮
    if selected_count > 0:
        st.markdown("---")
        if st.button("🚀 开始制作", type="primary", use_container_width=True):
            st.session_state.current_step = "material_upload"
            st.rerun()


def _get_module_info(module_type: ModuleType, registry: ModuleRegistry) -> Dict[str, Any]:
    """获取模块信息"""
    try:
        generator_class = registry.get_generator_class(module_type)
        if generator_class:
            # 创建临时实例获取模块信息
            temp_instance = generator_class()
            return {
                'description': temp_instance.get_description(),
                'recommended_use_cases': temp_instance.get_recommended_use_cases(),
                'generation_time_estimate': temp_instance.get_estimated_generation_time()
            }
    except Exception:
        pass
    
    # 返回默认信息
    return {
        'description': f'{_get_module_display_name(module_type)}模块',
        'recommended_use_cases': ['通用用途'],
        'generation_time_estimate': 60
    }


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


def _calculate_estimated_time(selected_modules: List[str]) -> int:
    """计算预估总时间（秒）"""
    # 每个模块的预估时间
    module_times = {
        ModuleType.PRODUCT_OVERVIEW.value: 45,
        ModuleType.PROBLEM_SOLUTION.value: 50,
        ModuleType.FEATURE_ANALYSIS.value: 60,
        ModuleType.SPECIFICATION_COMPARISON.value: 55,
        ModuleType.USAGE_SCENARIOS.value: 50,
        ModuleType.INSTALLATION_GUIDE.value: 60,
        ModuleType.SIZE_COMPATIBILITY.value: 50,
        ModuleType.MAINTENANCE_CARE.value: 45,
        ModuleType.MATERIAL_CRAFTSMANSHIP.value: 50,
        ModuleType.QUALITY_ASSURANCE.value: 40,
        ModuleType.CUSTOMER_REVIEWS.value: 45,
        ModuleType.PACKAGE_CONTENTS.value: 40
    }
    
    total_time = sum(module_times.get(module, 60) for module in selected_modules)
    return total_time