"""
A+ Studio Regeneration Panel.

This module provides UI components for managing single module regeneration,
version history, and parameter customization.
"""

import streamlit as st
from typing import Dict, List, Optional, Any
from datetime import datetime

from services.aplus_studio.models import ModuleType
from .controller import APlusController


class RegenerationPanel:
    """重新生成面板 - 管理单模块重新生成和版本历史的UI组件"""
    
    def __init__(self, controller: APlusController):
        self.controller = controller
    
    def render_regeneration_controls(self, module_type: ModuleType) -> Dict[str, Any]:
        """渲染重新生成控制面板"""
        st.subheader(f"{module_type.value} 模块重新生成")
        
        # 获取模块历史
        module_history = self.controller.get_module_history(module_type)
        
        if not module_history:
            st.warning("该模块尚未生成，请先完成初始生成")
            return {"action": None}
        
        # 创建两列布局
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # 参数自定义区域
            st.write("**自定义参数**")
            custom_params = self._render_parameter_customization(module_type)
            
            # 重新生成按钮
            if st.button(f"重新生成 {module_type.value} 模块", key=f"regen_panel_{module_type.value}"):
                return {
                    "action": "regenerate",
                    "module_type": module_type,
                    "custom_params": custom_params
                }
        
        with col2:
            # 版本历史和建议
            self._render_version_summary(module_history)
            self._render_regeneration_suggestions(module_type)
        
        return {"action": None}
    
    def _render_parameter_customization(self, module_type: ModuleType) -> Dict[str, Any]:
        """渲染参数自定义界面"""
        custom_params = {}
        
        st.write("调整生成参数以获得不同效果：")
        
        # 通用参数
        with st.expander("通用设置", expanded=True):
            # 光照调整
            lighting_options = ["保持原设置", "golden hour", "soft natural", "dramatic", "studio lighting"]
            lighting = st.selectbox(
                "光照效果", 
                lighting_options,
                key=f"lighting_{module_type.value}"
            )
            if lighting != "保持原设置":
                custom_params["lighting_adjustment"] = lighting
            
            # 色彩偏好
            color_options = ["保持原设置", "warm tones", "cool tones", "vibrant", "muted", "monochrome"]
            color_pref = st.selectbox(
                "色彩偏好",
                color_options,
                key=f"color_{module_type.value}"
            )
            if color_pref != "保持原设置":
                custom_params["color_preference"] = color_pref
            
            # 构图调整
            composition_text = st.text_input(
                "构图调整",
                placeholder="例如：更紧密的构图、增加空白空间等",
                key=f"composition_{module_type.value}"
            )
            if composition_text:
                custom_params["composition_adjustment"] = composition_text
        
        # 模块特定参数
        with st.expander("模块特定设置"):
            if module_type == ModuleType.IDENTITY:
                # 身份代入特定参数
                scene_elements = st.text_input(
                    "场景元素",
                    placeholder="添加特定的生活场景元素",
                    key=f"scene_{module_type.value}"
                )
                if scene_elements:
                    custom_params["additional_elements"] = scene_elements
                
                mood_options = ["保持原设置", "cozy", "luxurious", "minimalist", "family-oriented"]
                mood = st.selectbox("氛围调整", mood_options, key=f"mood_{module_type.value}")
                if mood != "保持原设置":
                    custom_params["mood_adjustment"] = mood
            
            elif module_type == ModuleType.SENSORY:
                # 感官解构特定参数
                detail_level = st.slider(
                    "细节层次",
                    min_value=1, max_value=5, value=3,
                    key=f"detail_{module_type.value}"
                )
                if detail_level != 3:
                    custom_params["detail_level"] = ["minimal", "low", "medium", "high", "ultra"][detail_level-1]
                
                contrast_level = st.slider(
                    "对比度",
                    min_value=1, max_value=5, value=3,
                    key=f"contrast_{module_type.value}"
                )
                if contrast_level != 3:
                    custom_params["contrast_level"] = ["soft", "low", "medium", "high", "dramatic"][contrast_level-1]
            
            elif module_type == ModuleType.EXTENSION:
                # 多维延展特定参数
                focus_dimension = st.selectbox(
                    "重点维度",
                    ["平衡所有维度", "Lifestyle", "Pain Point", "Extreme Performance", "Inside Out"],
                    key=f"focus_{module_type.value}"
                )
                if focus_dimension != "平衡所有维度":
                    custom_params["focus_dimension"] = focus_dimension
            
            elif module_type == ModuleType.TRUST:
                # 信任转化特定参数
                layout_ratio = st.selectbox(
                    "布局比例",
                    ["保持原设置", "1:1 (正方形)", "2:3 (横向)", "3:2 (纵向)"],
                    key=f"layout_{module_type.value}"
                )
                if layout_ratio != "保持原设置":
                    custom_params["layout_ratio"] = layout_ratio
                
                info_density = st.selectbox(
                    "信息密度",
                    ["保持原设置", "简洁", "标准", "详细"],
                    key=f"density_{module_type.value}"
                )
                if info_density != "保持原设置":
                    custom_params["info_density"] = info_density
        
        # 风格调整
        with st.expander("风格微调"):
            saturation = st.slider(
                "饱和度",
                min_value=1, max_value=5, value=3,
                key=f"saturation_{module_type.value}"
            )
            if saturation != 3:
                custom_params["saturation_level"] = ["very low", "low", "normal", "high", "very high"][saturation-1]
            
            style_emphasis = st.text_input(
                "风格强调",
                placeholder="例如：更现代、更温馨、更专业等",
                key=f"style_{module_type.value}"
            )
            if style_emphasis:
                custom_params["style_emphasis"] = style_emphasis
        
        return custom_params
    
    def _render_version_summary(self, module_history: Dict[str, Any]):
        """渲染版本摘要"""
        st.write("**版本历史**")
        
        total_versions = module_history.get("total_versions", 0)
        st.metric("总版本数", total_versions)
        
        if total_versions > 0:
            versions = module_history.get("versions", [])
            latest_version = versions[0] if versions else None
            
            if latest_version:
                st.write(f"**当前版本**")
                st.write(f"质量分数: {latest_version['quality_score']:.2f}")
                st.write(f"生成时间: {latest_version['generation_time']:.1f}s")
                
                if latest_version.get('user_rating'):
                    st.write(f"用户评分: {latest_version['user_rating']:.1f}/5.0")
    
    def _render_regeneration_suggestions(self, module_type: ModuleType):
        """渲染重新生成建议"""
        suggestions = self.controller.get_regeneration_suggestions(module_type)
        
        if suggestions:
            st.write("**生成建议**")
            for suggestion in suggestions[:3]:  # 显示前3个建议
                with st.expander(suggestion.get("message", "建议"), expanded=False):
                    if "parameters" in suggestion:
                        st.json(suggestion["parameters"])
                    
                    if st.button(
                        "应用此建议", 
                        key=f"apply_{module_type.value}_{suggestion.get('type', 'suggestion')}"
                    ):
                        # 这里可以自动填充参数
                        st.success("建议已应用到参数设置中")
    
    def render_version_history_panel(self, module_type: ModuleType):
        """渲染完整的版本历史面板"""
        st.subheader(f"{module_type.value} 模块版本历史")
        
        module_history = self.controller.get_module_history(module_type)
        
        if not module_history:
            st.info("该模块尚未生成版本历史")
            return
        
        versions = module_history.get("versions", [])
        
        if not versions:
            st.info("没有可用的版本历史")
            return
        
        # 版本列表
        st.write("**所有版本**")
        
        for i, version in enumerate(versions):
            with st.expander(
                f"版本 {i+1} - {version['creation_time'][:19]} "
                f"{'(当前)' if version['is_active'] else ''}"
                f"{'(原始)' if version['is_original'] else ''}",
                expanded=version['is_active']
            ):
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("质量分数", f"{version['quality_score']:.2f}")
                    st.write(f"状态: {version['validation_status']}")
                
                with col2:
                    st.metric("生成时间", f"{version['generation_time']:.1f}s")
                    if version.get('user_rating'):
                        st.write(f"用户评分: {version['user_rating']:.1f}/5.0")
                
                with col3:
                    # 版本操作
                    if not version['is_active']:
                        if st.button(
                            "设为当前版本", 
                            key=f"activate_{version['version_id']}"
                        ):
                            success = self.controller.set_active_version(
                                module_type, version['version_id']
                            )
                            if success:
                                st.success("版本已切换")
                                st.rerun()
                            else:
                                st.error("版本切换失败")
                    
                    # 评分
                    rating = st.slider(
                        "评分",
                        min_value=0.0, max_value=5.0, 
                        value=version.get('user_rating', 3.0),
                        step=0.1,
                        key=f"rating_{version['version_id']}"
                    )
                    
                    notes = st.text_area(
                        "备注",
                        value=version.get('user_notes', ''),
                        key=f"notes_{version['version_id']}"
                    )
                    
                    if st.button(
                        "保存评分", 
                        key=f"save_rating_{version['version_id']}"
                    ):
                        success = self.controller.rate_version(
                            module_type, version['version_id'], rating, notes
                        )
                        if success:
                            st.success("评分已保存")
                        else:
                            st.error("评分保存失败")
    
    def render_version_comparison(self, module_type: ModuleType):
        """渲染版本对比界面"""
        st.subheader(f"{module_type.value} 模块版本对比")
        
        module_history = self.controller.get_module_history(module_type)
        
        if not module_history:
            st.info("该模块尚未生成版本历史")
            return
        
        versions = module_history.get("versions", [])
        
        if len(versions) < 2:
            st.info("需要至少2个版本才能进行对比")
            return
        
        # 版本选择
        version_options = [
            f"版本 {i+1} - {v['creation_time'][:19]} (质量: {v['quality_score']:.2f})"
            for i, v in enumerate(versions)
        ]
        
        selected_versions = st.multiselect(
            "选择要对比的版本（最多选择3个）",
            version_options,
            default=version_options[:2] if len(version_options) >= 2 else version_options,
            max_selections=3
        )
        
        if len(selected_versions) >= 2:
            # 获取选中版本的ID
            selected_indices = [version_options.index(v) for v in selected_versions]
            selected_version_ids = [versions[i]['version_id'] for i in selected_indices]
            
            # 执行对比
            comparison_result = self.controller.compare_versions(module_type, selected_version_ids)
            
            if "error" not in comparison_result:
                self._render_comparison_results(comparison_result)
            else:
                st.error(comparison_result["error"])
    
    def _render_comparison_results(self, comparison_result: Dict[str, Any]):
        """渲染对比结果"""
        st.write("**对比结果**")
        
        versions = comparison_result.get("versions", [])
        metrics = comparison_result.get("comparison_metrics", {})
        
        # 版本对比表格
        if versions:
            import pandas as pd
            
            df_data = []
            for version in versions:
                df_data.append({
                    "版本": "当前" if version["is_active"] else ("原始" if version["is_original"] else "历史"),
                    "创建时间": version["creation_time"][:19],
                    "质量分数": version["quality_score"],
                    "生成时间(s)": version["generation_time"],
                    "验证状态": version["validation_status"],
                    "用户评分": version.get("user_rating", "未评分")
                })
            
            df = pd.DataFrame(df_data)
            st.dataframe(df, use_container_width=True)
        
        # 统计指标
        if metrics:
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**质量分数统计**")
                quality_range = metrics.get("quality_range", {})
                st.write(f"最高: {quality_range.get('max', 0):.2f}")
                st.write(f"最低: {quality_range.get('min', 0):.2f}")
                st.write(f"平均: {quality_range.get('avg', 0):.2f}")
            
            with col2:
                st.write("**生成时间统计**")
                time_range = metrics.get("generation_time_range", {})
                st.write(f"最快: {time_range.get('min', 0):.1f}s")
                st.write(f"最慢: {time_range.get('max', 0):.1f}s")
                st.write(f"平均: {time_range.get('avg', 0):.1f}s")
            
            # 改进趋势
            trend = metrics.get("improvement_trend", "unknown")
            trend_text = {
                "improving": "📈 质量呈上升趋势",
                "declining": "📉 质量呈下降趋势",
                "stable": "📊 质量保持稳定",
                "insufficient_data": "📋 数据不足"
            }.get(trend, "未知趋势")
            
            st.info(f"**趋势分析**: {trend_text}")
    
    def render_batch_regeneration_panel(self, selected_modules: List[ModuleType]):
        """渲染批量重新生成面板"""
        st.subheader("批量重新生成")
        
        if not selected_modules:
            st.info("请先选择要重新生成的模块")
            return
        
        st.write(f"选中的模块: {', '.join([m.value for m in selected_modules])}")
        
        # 批量参数设置
        with st.expander("批量参数设置", expanded=True):
            # 通用参数
            apply_lighting = st.checkbox("统一光照效果")
            if apply_lighting:
                batch_lighting = st.selectbox(
                    "光照效果",
                    ["golden hour", "soft natural", "dramatic", "studio lighting"]
                )
            
            apply_color = st.checkbox("统一色彩风格")
            if apply_color:
                batch_color = st.selectbox(
                    "色彩风格",
                    ["warm tones", "cool tones", "vibrant", "muted", "monochrome"]
                )
            
            preserve_consistency = st.checkbox("保持视觉连贯性", value=True)
        
        # 批量重新生成按钮
        if st.button("开始批量重新生成", type="primary"):
            batch_params = {}
            
            if apply_lighting:
                batch_params["lighting_adjustment"] = batch_lighting
            if apply_color:
                batch_params["color_preference"] = batch_color
            
            return {
                "action": "batch_regenerate",
                "modules": selected_modules,
                "params": batch_params,
                "preserve_consistency": preserve_consistency
            }
        
        return {"action": None}
