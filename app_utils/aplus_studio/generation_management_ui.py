"""
A+ 智能工作流生成管理界面组件

该模块提供生成管理阶段的用户界面，包括批量生成进度跟踪、
结果预览和管理功能、下载和导出选项等功能。
"""

import streamlit as st
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import time
import io
import zipfile
import base64
from datetime import datetime
from PIL import Image
import logging

from services.aplus_studio.models import ModuleType, GenerationResult, GenerationStatus
from services.aplus_studio.intelligent_workflow import IntelligentWorkflowController

logger = logging.getLogger(__name__)


@dataclass
class GenerationProgress:
    """生成进度信息"""
    module_type: ModuleType
    status: GenerationStatus
    progress: float  # 0.0 to 1.0
    message: str
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    estimated_remaining: Optional[float] = None
    error_message: Optional[str] = None


@dataclass
class BatchGenerationConfig:
    """批量生成配置"""
    selected_modules: List[ModuleType]
    generation_mode: str  # "sequential", "parallel"
    quality_level: str
    style_consistency: bool
    auto_retry: bool
    max_retries: int = 3
    timeout_seconds: int = 120


class GenerationView(Enum):
    """生成视图模式"""
    PROGRESS = "progress"      # 进度视图
    RESULTS = "results"        # 结果视图
    MANAGEMENT = "management"  # 管理视图


class GenerationManagementUI:
    """生成管理界面组件"""
    
    def __init__(self, workflow_controller: IntelligentWorkflowController):
        self.workflow_controller = workflow_controller
        
        # 生成进度跟踪
        self.generation_progress: Dict[ModuleType, GenerationProgress] = {}
        self.batch_config: Optional[BatchGenerationConfig] = None
        self.active_generations: List[ModuleType] = []
        
        # 模块配置
        self.module_configs = {
            ModuleType.PRODUCT_OVERVIEW: {
                "name": "产品概览", "icon": "🎯", "estimated_time": 25,
                "description": "展示产品整体外观和核心特性"
            },
            ModuleType.FEATURE_ANALYSIS: {
                "name": "功能解析", "icon": "🔍", "estimated_time": 35,
                "description": "详细展示产品功能和技术特性"
            },
            ModuleType.SPECIFICATION_COMPARISON: {
                "name": "规格对比", "icon": "📊", "estimated_time": 30,
                "description": "对比展示产品规格优势"
            },
            ModuleType.USAGE_SCENARIOS: {
                "name": "使用场景", "icon": "🏠", "estimated_time": 30,
                "description": "展示产品实际使用环境"
            },
            ModuleType.PROBLEM_SOLUTION: {
                "name": "问题解决", "icon": "💡", "estimated_time": 35,
                "description": "展示产品解决的用户痛点"
            },
            ModuleType.MATERIAL_CRAFTSMANSHIP: {
                "name": "材质工艺", "icon": "✨", "estimated_time": 40,
                "description": "突出产品材质和制造工艺"
            },
            ModuleType.INSTALLATION_GUIDE: {
                "name": "安装指南", "icon": "🔧", "estimated_time": 45,
                "description": "提供详细的安装步骤指导"
            },
            ModuleType.SIZE_COMPATIBILITY: {
                "name": "尺寸兼容", "icon": "📐", "estimated_time": 25,
                "description": "展示产品尺寸和兼容性信息"
            },
            ModuleType.PACKAGE_CONTENTS: {
                "name": "包装内容", "icon": "📦", "estimated_time": 20,
                "description": "展示产品包装内容和配件"
            },
            ModuleType.QUALITY_ASSURANCE: {
                "name": "品质保证", "icon": "🏆", "estimated_time": 25,
                "description": "展示产品认证和品质保证"
            },
            ModuleType.CUSTOMER_REVIEWS: {
                "name": "客户评价", "icon": "⭐", "estimated_time": 30,
                "description": "展示客户评价和使用反馈"
            },
            ModuleType.MAINTENANCE_CARE: {
                "name": "维护保养", "icon": "🧽", "estimated_time": 35,
                "description": "提供产品维护保养指导"
            }
        }
    
    def render_generation_management_interface(self) -> Dict[str, Any]:
        """
        渲染完整的生成管理界面
        
        Returns:
            Dict: 包含用户操作和生成结果的字典
        """
        st.subheader("🎨 生成管理")
        
        # 检查前置条件
        session = self.workflow_controller.state_manager.get_current_session()
        
        if not session or not session.selected_modules:
            st.warning("⚠️ 请先完成模块选择和内容编辑")
            return {"action": None}
        
        # 检查内容是否准备就绪
        if not session.module_contents or len(session.module_contents) == 0:
            st.warning("⚠️ 请先完成内容生成和编辑")
            return {"action": None}
        
        # 视图模式选择
        view_mode = self._render_view_mode_selection()
        
        if view_mode == GenerationView.PROGRESS:
            return self._render_progress_view()
        elif view_mode == GenerationView.RESULTS:
            return self._render_results_view()
        else:  # MANAGEMENT
            return self._render_management_view()
    
    def _render_view_mode_selection(self) -> GenerationView:
        """渲染视图模式选择"""
        
        # 检查当前状态来决定默认视图
        session = self.workflow_controller.state_manager.get_current_session()
        has_active_generation = len(self.active_generations) > 0
        has_results = session and session.generation_results and len(session.generation_results) > 0
        
        view_options = {
            "🔄 生成进度": GenerationView.PROGRESS,
            "🖼️ 结果预览": GenerationView.RESULTS,
            "📊 管理面板": GenerationView.MANAGEMENT
        }
        
        # 根据状态设置默认选择
        if has_active_generation:
            default_index = 0  # 进度视图
        elif has_results:
            default_index = 1  # 结果视图
        else:
            default_index = 2  # 管理面板
        
        selected_view = st.radio(
            "选择视图",
            list(view_options.keys()),
            index=default_index,
            horizontal=True,
            help="进度：查看生成进度\n结果：预览生成结果\n管理：配置和管理生成",
            label_visibility="collapsed"
        )
        
        return view_options[selected_view]
    
    def _render_progress_view(self) -> Dict[str, Any]:
        """渲染进度视图"""
        
        st.write("**🔄 生成进度跟踪**")
        
        # 如果没有活跃的生成任务，显示启动界面
        if not self.active_generations and not self.generation_progress:
            return self._render_generation_startup()
        
        # 显示总体进度
        self._render_overall_progress()
        
        # 显示各模块详细进度
        self._render_module_progress_details()
        
        # 进度控制按钮
        return self._render_progress_controls()
    
    def _render_generation_startup(self) -> Dict[str, Any]:
        """渲染生成启动界面"""
        
        st.write("**🚀 准备开始生成A+图片**")
        
        session = self.workflow_controller.state_manager.get_current_session()
        selected_modules = session.selected_modules
        
        # 显示准备生成的模块
        st.write("**待生成模块：**")
        
        total_estimated_time = 0
        
        for i, module_type in enumerate(selected_modules, 1):
            config = self.module_configs[module_type]
            total_estimated_time += config["estimated_time"]
            
            col1, col2, col3 = st.columns([1, 3, 1])
            
            with col1:
                st.write(f"{config['icon']}")
            
            with col2:
                st.write(f"**{i}. {config['name']}**")
                st.caption(config["description"])
            
            with col3:
                st.caption(f"{config['estimated_time']}分钟")
        
        # 生成配置
        with st.expander("⚙️ 生成配置", expanded=True):
            col1, col2 = st.columns(2)
            
            with col1:
                generation_mode = st.selectbox(
                    "生成模式",
                    ["sequential", "parallel"],
                    format_func=lambda x: "顺序生成" if x == "sequential" else "并行生成",
                    index=1,  # 默认并行
                    help="顺序生成：逐个生成，可实时查看\n并行生成：同时生成，速度更快"
                )
                
                quality_level = st.selectbox(
                    "质量等级",
                    ["standard", "high", "premium"],
                    format_func=lambda x: {"standard": "标准质量", "high": "高质量", "premium": "超高质量"}[x],
                    index=1,  # 默认高质量
                    help="更高质量需要更长生成时间"
                )
            
            with col2:
                style_consistency = st.checkbox(
                    "强制风格一致性",
                    value=True,
                    help="确保所有模块保持统一的视觉风格"
                )
                
                auto_retry = st.checkbox(
                    "自动重试",
                    value=True,
                    help="生成失败时自动重试"
                )
        
        # 时间估算
        if generation_mode == "parallel":
            estimated_time = max(self.module_configs[m]["estimated_time"] for m in selected_modules)
        else:
            estimated_time = total_estimated_time
        
        st.info(f"⏱️ 预计生成时间: {estimated_time} 分钟 ({len(selected_modules)} 个模块)")
        
        # 启动按钮
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            if st.button("🚀 开始生成", type="primary", use_container_width=True):
                # 创建批量生成配置
                self.batch_config = BatchGenerationConfig(
                    selected_modules=selected_modules,
                    generation_mode=generation_mode,
                    quality_level=quality_level,
                    style_consistency=style_consistency,
                    auto_retry=auto_retry
                )
                
                return {
                    "action": "start_batch_generation",
                    "config": self.batch_config
                }
        
        with col2:
            if st.button("⚙️ 高级设置", use_container_width=True):
                return {"action": "show_advanced_settings"}
        
        with col3:
            if st.button("📋 预览内容", use_container_width=True):
                return {"action": "preview_content"}
        
        return {"action": None}
    
    def _render_overall_progress(self) -> None:
        """渲染总体进度"""
        
        if not self.generation_progress:
            return
        
        # 计算总体进度
        total_modules = len(self.generation_progress)
        completed_modules = sum(1 for p in self.generation_progress.values() 
                              if p.status == GenerationStatus.COMPLETED)
        failed_modules = sum(1 for p in self.generation_progress.values() 
                           if p.status == GenerationStatus.FAILED)
        in_progress_modules = sum(1 for p in self.generation_progress.values() 
                                if p.status == GenerationStatus.IN_PROGRESS)
        
        overall_progress = completed_modules / total_modules if total_modules > 0 else 0
        
        # 显示总体进度条
        st.progress(overall_progress, text=f"总体进度: {completed_modules}/{total_modules} 模块完成")
        
        # 显示统计信息
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("已完成", completed_modules, delta=None)
        
        with col2:
            st.metric("进行中", in_progress_modules, delta=None)
        
        with col3:
            st.metric("失败", failed_modules, delta=None)
        
        with col4:
            # 预计剩余时间
            if in_progress_modules > 0:
                avg_remaining = sum(p.estimated_remaining or 0 for p in self.generation_progress.values() 
                                  if p.status == GenerationStatus.IN_PROGRESS) / in_progress_modules
                st.metric("预计剩余", f"{avg_remaining:.0f}秒")
            else:
                st.metric("预计剩余", "0秒")
    
    def _render_module_progress_details(self) -> None:
        """渲染模块进度详情"""
        
        st.write("**模块生成详情**")
        
        for module_type, progress in self.generation_progress.items():
            config = self.module_configs[module_type]
            
            with st.container():
                # 模块头部
                col1, col2, col3, col4 = st.columns([1, 3, 2, 1])
                
                with col1:
                    # 状态图标
                    status_icon = self._get_status_icon(progress.status)
                    st.write(f"{config['icon']} {status_icon}")
                
                with col2:
                    st.write(f"**{config['name']}**")
                    st.caption(progress.message)
                
                with col3:
                    # 进度条或状态
                    if progress.status == GenerationStatus.IN_PROGRESS:
                        st.progress(progress.progress, text=f"{progress.progress*100:.0f}%")
                    else:
                        status_text = self._get_status_text(progress.status)
                        if progress.status == GenerationStatus.COMPLETED:
                            st.success(status_text)
                        elif progress.status == GenerationStatus.FAILED:
                            st.error(status_text)
                        else:
                            st.info(status_text)
                
                with col4:
                    # 时间信息
                    if progress.start_time and progress.end_time:
                        duration = progress.end_time - progress.start_time
                        st.caption(f"{duration:.1f}s")
                    elif progress.estimated_remaining:
                        st.caption(f"剩余 {progress.estimated_remaining:.0f}s")
                
                # 错误信息
                if progress.status == GenerationStatus.FAILED and progress.error_message:
                    st.error(f"错误: {progress.error_message}")
                
                # 操作按钮
                if progress.status == GenerationStatus.FAILED:
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("🔄 重试", key=f"retry_{module_type.value}"):
                            return {"action": "retry_module", "module": module_type}
                    with col2:
                        if st.button("⏭️ 跳过", key=f"skip_{module_type.value}"):
                            return {"action": "skip_module", "module": module_type}
                
                elif progress.status == GenerationStatus.IN_PROGRESS:
                    if st.button("⏹️ 停止", key=f"stop_{module_type.value}"):
                        return {"action": "stop_module", "module": module_type}
                
                st.divider()
    
    def _render_progress_controls(self) -> Dict[str, Any]:
        """渲染进度控制按钮"""
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if self.active_generations and st.button("⏸️ 暂停全部", use_container_width=True):
                return {"action": "pause_all"}
        
        with col2:
            if st.button("⏹️ 停止全部", use_container_width=True):
                return {"action": "stop_all"}
        
        with col3:
            if st.button("🔄 刷新状态", use_container_width=True):
                return {"action": "refresh_status"}
        
        with col4:
            if st.button("📊 查看结果", use_container_width=True):
                return {"action": "view_results"}
        
        return {"action": None}
    
    def _render_results_view(self) -> Dict[str, Any]:
        """渲染结果视图"""
        
        st.write("**🖼️ 生成结果预览**")
        
        session = self.workflow_controller.state_manager.get_current_session()
        
        if not session or not session.generation_results:
            st.info("暂无生成结果")
            return {"action": None}
        
        generation_results = session.generation_results
        
        # 结果概览
        self._render_results_overview(generation_results)
        
        # 结果展示模式选择
        display_mode = st.radio(
            "显示模式",
            ["网格视图", "列表视图", "对比视图"],
            horizontal=True,
            label_visibility="collapsed"
        )
        
        if display_mode == "网格视图":
            return self._render_grid_results(generation_results)
        elif display_mode == "列表视图":
            return self._render_list_results(generation_results)
        else:  # 对比视图
            return self._render_comparison_results(generation_results)
    
    def _render_results_overview(self, generation_results: Dict[ModuleType, GenerationResult]) -> None:
        """渲染结果概览"""
        
        # 统计信息
        total_results = len(generation_results)
        successful_results = sum(1 for result in generation_results.values() 
                               if result.generation_status == GenerationStatus.COMPLETED)
        avg_quality = sum(result.quality_score for result in generation_results.values()) / total_results if total_results > 0 else 0
        total_generation_time = sum(result.generation_time for result in generation_results.values())
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("生成结果", f"{successful_results}/{total_results}")
        
        with col2:
            st.metric("平均质量", f"{avg_quality:.2f}")
        
        with col3:
            st.metric("总生成时间", f"{total_generation_time:.1f}秒")
        
        with col4:
            # 文件大小统计
            total_size = sum(len(result.image_data) if result.image_data else 0 
                           for result in generation_results.values())
            st.metric("总文件大小", f"{total_size / (1024*1024):.1f}MB")
    
    def _render_grid_results(self, generation_results: Dict[ModuleType, GenerationResult]) -> Dict[str, Any]:
        """渲染网格结果视图"""
        
        # 按行显示结果
        cols_per_row = 2
        modules = list(generation_results.keys())
        rows = (len(modules) + cols_per_row - 1) // cols_per_row
        
        for row in range(rows):
            cols = st.columns(cols_per_row)
            
            for col_idx in range(cols_per_row):
                module_idx = row * cols_per_row + col_idx
                
                if module_idx < len(modules):
                    module_type = modules[module_idx]
                    result = generation_results[module_type]
                    
                    with cols[col_idx]:
                        self._render_result_card(module_type, result)
        
        # 批量操作
        return self._render_batch_result_operations(generation_results)
    
    def _render_list_results(self, generation_results: Dict[ModuleType, GenerationResult]) -> Dict[str, Any]:
        """渲染列表结果视图"""
        
        for module_type, result in generation_results.items():
            config = self.module_configs[module_type]
            
            with st.container():
                col1, col2 = st.columns([1, 2])
                
                with col1:
                    # 图片预览
                    if result.image_data:
                        st.image(result.image_data, width=200, caption=config["name"])
                    else:
                        st.error("图片数据不可用")
                
                with col2:
                    # 结果详情
                    st.write(f"**{config['icon']} {config['name']}**")
                    
                    # 质量和时间信息
                    col2_1, col2_2, col2_3 = st.columns(3)
                    
                    with col2_1:
                        quality_color = self._get_quality_color(result.quality_score)
                        st.markdown(f"<span style='color: {quality_color}'>质量: {result.quality_score:.2f}</span>", 
                                  unsafe_allow_html=True)
                    
                    with col2_2:
                        st.write(f"时间: {result.generation_time:.1f}s")
                    
                    with col2_3:
                        st.write(f"状态: {self._get_status_text(result.generation_status)}")
                    
                    # 操作按钮
                    self._render_result_actions(module_type, result)
                
                st.divider()
        
        return self._render_batch_result_operations(generation_results)
    
    def _render_comparison_results(self, generation_results: Dict[ModuleType, GenerationResult]) -> Dict[str, Any]:
        """渲染对比结果视图"""
        
        modules = list(generation_results.keys())
        
        if len(modules) < 2:
            st.info("需要至少2个结果才能进行对比")
            return {"action": None}
        
        # 选择对比的模块
        col1, col2 = st.columns(2)
        
        with col1:
            module1 = st.selectbox(
                "选择模块1",
                modules,
                format_func=lambda x: self.module_configs[x]["name"],
                key="compare_module1"
            )
        
        with col2:
            module2 = st.selectbox(
                "选择模块2",
                modules,
                format_func=lambda x: self.module_configs[x]["name"],
                key="compare_module2"
            )
        
        if module1 != module2:
            # 显示对比
            col1, col2 = st.columns(2)
            
            with col1:
                result1 = generation_results[module1]
                self._render_comparison_card(module1, result1, "A")
            
            with col2:
                result2 = generation_results[module2]
                self._render_comparison_card(module2, result2, "B")
            
            # 对比分析
            self._render_comparison_analysis(result1, result2)
        
        return {"action": None}
    
    def _render_result_card(self, module_type: ModuleType, result: GenerationResult) -> None:
        """渲染结果卡片"""
        
        config = self.module_configs[module_type]
        
        # 卡片头部
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            st.write(f"**{config['icon']} {config['name']}**")
        
        with col2:
            quality_color = self._get_quality_color(result.quality_score)
            st.markdown(f"<span style='color: {quality_color}'>⭐ {result.quality_score:.1f}</span>", 
                       unsafe_allow_html=True)
        
        with col3:
            if st.button("⋮", key=f"menu_{module_type.value}", help="更多操作"):
                st.session_state[f"show_menu_{module_type.value}"] = True
        
        # 图片显示
        if result.image_data:
            st.image(result.image_data, use_container_width=True, 
                    caption=f"生成时间: {result.generation_time:.1f}s")
        else:
            st.error("图片数据不可用")
        
        # 结果信息
        with st.expander("📊 详细信息", expanded=False):
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**生成信息**")
                st.write(f"• 质量分数: {result.quality_score:.2f}")
                st.write(f"• 生成时间: {result.generation_time:.1f}秒")
                st.write(f"• 状态: {self._get_status_text(result.generation_status)}")
            
            with col2:
                st.write("**技术信息**")
                if hasattr(result, 'metadata') and result.metadata:
                    st.write(f"• 尺寸: {result.metadata.get('dimensions', '600x450')}")
                    st.write(f"• 格式: {result.metadata.get('format', 'PNG')}")
                    st.write(f"• 文件大小: {len(result.image_data) // 1024 if result.image_data else 0}KB")
        
        # 操作按钮
        self._render_result_actions(module_type, result)
    
    def _render_result_actions(self, module_type: ModuleType, result: GenerationResult) -> None:
        """渲染结果操作按钮"""
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("📥 下载", key=f"download_{module_type.value}", use_container_width=True):
                self._download_result(module_type, result)
        
        with col2:
            if st.button("🔄 重新生成", key=f"regen_{module_type.value}", use_container_width=True):
                return {"action": "regenerate_module", "module": module_type}
        
        with col3:
            if st.button("👁️ 全屏预览", key=f"preview_{module_type.value}", use_container_width=True):
                self._show_fullscreen_preview(module_type, result)
    
    def _render_comparison_card(self, module_type: ModuleType, result: GenerationResult, label: str) -> None:
        """渲染对比卡片"""
        
        config = self.module_configs[module_type]
        
        st.write(f"**{label}. {config['icon']} {config['name']}**")
        
        if result.image_data:
            st.image(result.image_data, use_container_width=True)
        
        # 对比信息
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("质量分数", f"{result.quality_score:.2f}")
        
        with col2:
            st.metric("生成时间", f"{result.generation_time:.1f}s")
    
    def _render_comparison_analysis(self, result1: GenerationResult, result2: GenerationResult) -> None:
        """渲染对比分析"""
        
        st.write("**📊 对比分析**")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            quality_diff = result1.quality_score - result2.quality_score
            if abs(quality_diff) < 0.1:
                st.info("质量相近")
            elif quality_diff > 0:
                st.success(f"A质量更高 (+{quality_diff:.2f})")
            else:
                st.success(f"B质量更高 (+{-quality_diff:.2f})")
        
        with col2:
            time_diff = result1.generation_time - result2.generation_time
            if abs(time_diff) < 5:
                st.info("生成时间相近")
            elif time_diff > 0:
                st.info(f"A用时更长 (+{time_diff:.1f}s)")
            else:
                st.info(f"B用时更长 (+{-time_diff:.1f}s)")
        
        with col3:
            # 文件大小对比
            size1 = len(result1.image_data) if result1.image_data else 0
            size2 = len(result2.image_data) if result2.image_data else 0
            size_diff = (size1 - size2) / 1024  # KB
            
            if abs(size_diff) < 50:
                st.info("文件大小相近")
            elif size_diff > 0:
                st.info(f"A文件更大 (+{size_diff:.0f}KB)")
            else:
                st.info(f"B文件更大 (+{-size_diff:.0f}KB)")
    
    def _render_batch_result_operations(self, generation_results: Dict[ModuleType, GenerationResult]) -> Dict[str, Any]:
        """渲染批量结果操作"""
        
        st.write("**批量操作**")
        
        # 模块选择
        selected_modules = st.multiselect(
            "选择模块",
            list(generation_results.keys()),
            format_func=lambda x: self.module_configs[x]["name"],
            key="batch_operation_modules"
        )
        
        if selected_modules:
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                if st.button("📥 批量下载", use_container_width=True):
                    return {"action": "batch_download", "modules": selected_modules}
            
            with col2:
                if st.button("🔄 批量重新生成", use_container_width=True):
                    return {"action": "batch_regenerate", "modules": selected_modules}
            
            with col3:
                if st.button("📊 质量分析", use_container_width=True):
                    return {"action": "quality_analysis", "modules": selected_modules}
            
            with col4:
                if st.button("📤 导出报告", use_container_width=True):
                    return {"action": "export_report", "modules": selected_modules}
        
        return {"action": None}
    
    def _render_management_view(self) -> Dict[str, Any]:
        """渲染管理视图"""
        
        st.write("**📊 生成管理面板**")
        
        # 管理统计
        self._render_management_statistics()
        
        # 生成历史
        self._render_generation_history()
        
        # 系统设置
        self._render_system_settings()
        
        # 管理操作
        return self._render_management_operations()
    
    def _render_management_statistics(self) -> None:
        """渲染管理统计"""
        
        st.write("**📈 统计信息**")
        
        session = self.workflow_controller.state_manager.get_current_session()
        
        # 基本统计
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            total_modules = len(session.selected_modules) if session and session.selected_modules else 0
            st.metric("选定模块", total_modules)
        
        with col2:
            completed_results = len(session.generation_results) if session and session.generation_results else 0
            st.metric("已生成", completed_results)
        
        with col3:
            success_rate = (completed_results / total_modules * 100) if total_modules > 0 else 0
            st.metric("成功率", f"{success_rate:.0f}%")
        
        with col4:
            # 平均质量
            if session and session.generation_results:
                avg_quality = sum(r.quality_score for r in session.generation_results.values()) / len(session.generation_results)
                st.metric("平均质量", f"{avg_quality:.2f}")
            else:
                st.metric("平均质量", "N/A")
    
    def _render_generation_history(self) -> None:
        """渲染生成历史"""
        
        with st.expander("📚 生成历史", expanded=False):
            # 这里可以显示历史生成记录
            st.info("生成历史功能开发中...")
    
    def _render_system_settings(self) -> None:
        """渲染系统设置"""
        
        with st.expander("⚙️ 系统设置", expanded=False):
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**生成设置**")
                
                default_quality = st.selectbox(
                    "默认质量等级",
                    ["standard", "high", "premium"],
                    format_func=lambda x: {"standard": "标准", "high": "高质量", "premium": "超高质量"}[x],
                    index=1
                )
                
                auto_save_results = st.checkbox(
                    "自动保存结果",
                    value=True,
                    help="生成完成后自动保存到本地"
                )
            
            with col2:
                st.write("**界面设置**")
                
                default_view = st.selectbox(
                    "默认视图模式",
                    ["progress", "results", "management"],
                    format_func=lambda x: {"progress": "进度视图", "results": "结果视图", "management": "管理面板"}[x],
                    index=0
                )
                
                show_advanced_options = st.checkbox(
                    "显示高级选项",
                    value=False,
                    help="在界面中显示高级配置选项"
                )
    
    def _render_management_operations(self) -> Dict[str, Any]:
        """渲染管理操作"""
        
        st.write("**管理操作**")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if st.button("🧹 清理缓存", use_container_width=True):
                return {"action": "clear_cache"}
        
        with col2:
            if st.button("📤 导出设置", use_container_width=True):
                return {"action": "export_settings"}
        
        with col3:
            if st.button("📥 导入设置", use_container_width=True):
                return {"action": "import_settings"}
        
        with col4:
            if st.button("🔄 重置系统", use_container_width=True):
                return {"action": "reset_system"}
        
        return {"action": None}
    
    def _get_status_icon(self, status: GenerationStatus) -> str:
        """获取状态图标"""
        
        status_icons = {
            GenerationStatus.NOT_STARTED: "⚪",
            GenerationStatus.IN_PROGRESS: "🟡",
            GenerationStatus.COMPLETED: "🟢",
            GenerationStatus.FAILED: "🔴",
            GenerationStatus.CANCELLED: "⚫"
        }
        
        return status_icons.get(status, "❓")
    
    def _get_status_text(self, status: GenerationStatus) -> str:
        """获取状态文本"""
        
        status_texts = {
            GenerationStatus.NOT_STARTED: "未开始",
            GenerationStatus.IN_PROGRESS: "生成中",
            GenerationStatus.COMPLETED: "已完成",
            GenerationStatus.FAILED: "失败",
            GenerationStatus.CANCELLED: "已取消"
        }
        
        return status_texts.get(status, "未知")
    
    def _get_quality_color(self, quality_score: float) -> str:
        """获取质量分数颜色"""
        
        if quality_score >= 0.8:
            return "#28a745"  # 绿色
        elif quality_score >= 0.6:
            return "#ffc107"  # 黄色
        else:
            return "#dc3545"  # 红色
    
    def _download_result(self, module_type: ModuleType, result: GenerationResult) -> None:
        """下载单个结果"""
        
        if result.image_data:
            config = self.module_configs[module_type]
            filename = f"aplus_{module_type.value}_{int(time.time())}.png"
            
            st.download_button(
                label=f"📥 下载 {config['name']}",
                data=result.image_data,
                file_name=filename,
                mime="image/png",
                key=f"download_btn_{module_type.value}"
            )
    
    def _show_fullscreen_preview(self, module_type: ModuleType, result: GenerationResult) -> None:
        """显示全屏预览"""
        
        # 在实际实现中，这可能会打开一个模态框
        st.session_state[f"fullscreen_preview_{module_type.value}"] = True
        st.session_state[f"preview_result_{module_type.value}"] = result
    
    def start_generation_tracking(self, module_type: ModuleType) -> None:
        """开始生成跟踪"""
        
        self.generation_progress[module_type] = GenerationProgress(
            module_type=module_type,
            status=GenerationStatus.IN_PROGRESS,
            progress=0.0,
            message="准备生成...",
            start_time=time.time()
        )
        
        if module_type not in self.active_generations:
            self.active_generations.append(module_type)
    
    def update_generation_progress(self, module_type: ModuleType, progress: float, message: str) -> None:
        """更新生成进度"""
        
        if module_type in self.generation_progress:
            self.generation_progress[module_type].progress = progress
            self.generation_progress[module_type].message = message
            
            # 估算剩余时间
            if progress > 0:
                elapsed = time.time() - self.generation_progress[module_type].start_time
                estimated_total = elapsed / progress
                estimated_remaining = estimated_total - elapsed
                self.generation_progress[module_type].estimated_remaining = max(0, estimated_remaining)
    
    def complete_generation(self, module_type: ModuleType, success: bool = True, error_message: str = None) -> None:
        """完成生成"""
        
        if module_type in self.generation_progress:
            self.generation_progress[module_type].status = (
                GenerationStatus.COMPLETED if success else GenerationStatus.FAILED
            )
            self.generation_progress[module_type].progress = 1.0
            self.generation_progress[module_type].end_time = time.time()
            self.generation_progress[module_type].message = (
                "生成完成" if success else "生成失败"
            )
            
            if error_message:
                self.generation_progress[module_type].error_message = error_message
        
        if module_type in self.active_generations:
            self.active_generations.remove(module_type)
    
    def get_generation_summary(self) -> Dict[str, Any]:
        """获取生成摘要"""
        
        session = self.workflow_controller.state_manager.get_current_session()
        
        if not session:
            return {"has_session": False}
        
        return {
            "has_session": True,
            "selected_modules_count": len(session.selected_modules) if session.selected_modules else 0,
            "generated_results_count": len(session.generation_results) if session.generation_results else 0,
            "active_generations_count": len(self.active_generations),
            "has_active_generation": len(self.active_generations) > 0,
            "overall_progress": len(session.generation_results) / len(session.selected_modules) if session.selected_modules else 0
        }
    
    def create_batch_download(self, selected_modules: List[ModuleType]) -> Optional[bytes]:
        """创建批量下载ZIP文件"""
        
        try:
            session = self.workflow_controller.state_manager.get_current_session()
            
            if not session or not session.generation_results:
                return None
            
            # 创建ZIP文件
            zip_buffer = io.BytesIO()
            
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                for module_type in selected_modules:
                    if module_type in session.generation_results:
                        result = session.generation_results[module_type]
                        
                        if result.image_data:
                            config = self.module_configs[module_type]
                            filename = f"{config['name']}_{module_type.value}.png"
                            zip_file.writestr(filename, result.image_data)
            
            zip_buffer.seek(0)
            return zip_buffer.getvalue()
            
        except Exception as e:
            logger.error(f"Failed to create batch download: {str(e)}")
            return None
    
    def export_generation_report(self, selected_modules: List[ModuleType]) -> Optional[Dict[str, Any]]:
        """导出生成报告"""
        
        try:
            session = self.workflow_controller.state_manager.get_current_session()
            
            if not session:
                return None
            
            report = {
                "export_timestamp": datetime.now().isoformat(),
                "session_id": session.session_id,
                "selected_modules": [m.value for m in selected_modules],
                "results": {}
            }
            
            for module_type in selected_modules:
                if module_type in session.generation_results:
                    result = session.generation_results[module_type]
                    config = self.module_configs[module_type]
                    
                    report["results"][module_type.value] = {
                        "name": config["name"],
                        "status": result.generation_status.value,
                        "quality_score": result.quality_score,
                        "generation_time": result.generation_time,
                        "file_size": len(result.image_data) if result.image_data else 0,
                        "metadata": getattr(result, 'metadata', {})
                    }
            
            return report
            
        except Exception as e:
            logger.error(f"Failed to export generation report: {str(e)}")
            return None


# 全局实例，便于访问
def create_generation_management_ui(workflow_controller: IntelligentWorkflowController) -> GenerationManagementUI:
    """创建生成管理UI实例"""
    return GenerationManagementUI(workflow_controller)