"""
A+ Studio Module Generation Control Panel
Provides interface for controlling the generation of individual A+ modules
"""

import streamlit as st
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from enum import Enum
import asyncio
import time
from services.aplus_studio.models import ModuleType, GenerationResult, GenerationStatus


@dataclass
class GenerationProgress:
    """Progress tracking for module generation"""
    module_type: ModuleType
    status: GenerationStatus
    progress: float  # 0.0 to 1.0
    message: str
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    estimated_remaining: Optional[float] = None


class GenerationMode(Enum):
    """Generation modes"""
    INDIVIDUAL = "individual"  # Generate one module at a time
    BATCH = "batch"           # Generate multiple modules in sequence
    PARALLEL = "parallel"     # Generate multiple modules simultaneously


class ModuleGenerationPanel:
    """Control panel for A+ module generation"""
    
    def __init__(self, controller):
        self.controller = controller
        self.generation_progress: Dict[ModuleType, GenerationProgress] = {}
        self.active_generations: List[ModuleType] = []
        
        # Module configurations
        self.module_configs = {
            ModuleType.IDENTITY: {
                "name": "身份代入模块",
                "icon": "🎭",
                "description": "生成Full Image全屏视效图片，强调北美中产使用场景",
                "output_type": "单张图片 (600×450)",
                "estimated_time": 30,
                "requirements": ["产品分析完成"]
            },
            ModuleType.SENSORY: {
                "name": "感官解构模块", 
                "icon": "👁️",
                "description": "生成Premium Hotspots高级热点图，突出材质细节",
                "output_type": "单张图片 (600×450)",
                "estimated_time": 35,
                "requirements": ["产品分析完成"]
            },
            ModuleType.EXTENSION: {
                "name": "多维延展模块",
                "icon": "🔄", 
                "description": "生成Premium Navigation Carousel四张轮播图",
                "output_type": "四张轮播图 (600×450)",
                "estimated_time": 60,
                "requirements": ["产品分析完成"]
            },
            ModuleType.TRUST: {
                "name": "信任转化模块",
                "icon": "🤝",
                "description": "生成Premium Image with Text图文内容",
                "output_type": "单张图片 (600×450)",
                "estimated_time": 40,
                "requirements": ["产品分析完成"]
            }
        }
    
    def render_generation_panel(self) -> Dict[str, Any]:
        """
        Render the complete module generation control panel
        
        Returns:
            Dict containing generation actions and parameters
        """
        st.subheader("🎨 模块生成控制")
        
        # Check prerequisites
        session = self.controller.state_manager.get_current_session()
        if not session or not session.analysis_result:
            st.warning("⚠️ 请先完成产品分析")
            return {"action": None}
        
        # Generation mode selection
        generation_mode = self._render_mode_selection()
        
        # Module selection and configuration
        selected_modules, module_params = self._render_module_selection()
        
        if not selected_modules:
            st.info("请选择至少一个模块进行生成")
            return {"action": None}
        
        # Generation options
        generation_options = self._render_generation_options(selected_modules)
        
        # Progress tracking
        self._render_progress_tracking()
        
        # Generation controls
        action = self._render_generation_controls(
            selected_modules, 
            generation_mode, 
            generation_options,
            module_params
        )
        
        return action
    
    def _render_mode_selection(self) -> GenerationMode:
        """Render generation mode selection"""
        
        st.write("**生成模式**")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            individual_selected = st.radio(
                "选择生成模式",
                ["逐个生成", "批量生成", "并行生成"],
                help="逐个生成：实时查看结果\n批量生成：按顺序生成所有模块\n并行生成：同时生成多个模块（更快）",
                horizontal=True,
                label_visibility="collapsed"
            )
        
        mode_mapping = {
            "逐个生成": GenerationMode.INDIVIDUAL,
            "批量生成": GenerationMode.BATCH,
            "并行生成": GenerationMode.PARALLEL
        }
        
        return mode_mapping[individual_selected]
    
    def _render_module_selection(self) -> tuple[List[ModuleType], Dict[ModuleType, Dict]]:
        """Render module selection interface"""
        
        st.write("**选择生成模块**")
        
        selected_modules = []
        module_params = {}
        
        # Get current generation status
        current_progress = self.controller.get_generation_progress()
        
        # Create module selection grid
        col1, col2 = st.columns(2)
        
        modules_left = [ModuleType.IDENTITY, ModuleType.SENSORY]
        modules_right = [ModuleType.EXTENSION, ModuleType.TRUST]
        
        for col, modules in [(col1, modules_left), (col2, modules_right)]:
            with col:
                for module_type in modules:
                    config = self.module_configs[module_type]
                    status = current_progress.get(module_type, GenerationStatus.NOT_STARTED)
                    
                    # Module card
                    with st.container():
                        # Module header
                        module_col1, module_col2, module_col3 = st.columns([1, 3, 1])
                        
                        with module_col1:
                            # Status indicator
                            status_icon = self._get_status_icon(status)
                            st.write(f"{config['icon']} {status_icon}")
                        
                        with module_col2:
                            # Module selection checkbox
                            is_selected = st.checkbox(
                                config["name"],
                                key=f"select_{module_type.value}",
                                disabled=status == GenerationStatus.IN_PROGRESS
                            )
                            
                            if is_selected:
                                selected_modules.append(module_type)
                        
                        with module_col3:
                            # Quick info button
                            if st.button("ℹ️", key=f"info_{module_type.value}", help="模块详情"):
                                self._show_module_details(module_type)
                        
                        # Module description
                        st.caption(config["description"])
                        
                        # Module parameters (if selected)
                        if is_selected:
                            params = self._render_module_parameters(module_type)
                            module_params[module_type] = params
                        
                        st.divider()
        
        return selected_modules, module_params
    
    def _render_module_parameters(self, module_type: ModuleType) -> Dict[str, Any]:
        """Render parameters for specific module"""
        
        params = {}
        
        with st.expander(f"⚙️ {self.module_configs[module_type]['name']} 参数", expanded=False):
            
            if module_type == ModuleType.IDENTITY:
                # Identity module specific parameters
                params["scene_style"] = st.selectbox(
                    "场景风格",
                    ["北美中产家庭", "现代简约", "温馨居家", "专业办公", "户外生活"],
                    key=f"identity_scene_style"
                )
                
                params["lighting"] = st.selectbox(
                    "光线效果",
                    ["黄金时段", "自然采光", "温暖室内", "明亮清晰"],
                    key=f"identity_lighting"
                )
                
                params["include_text"] = st.checkbox(
                    "包含文字要素",
                    value=True,
                    help="包含价值观Slogan和信任背书",
                    key=f"identity_text"
                )
            
            elif module_type == ModuleType.SENSORY:
                # Sensory module specific parameters
                params["view_angle"] = st.selectbox(
                    "视角选择",
                    ["3/4视角", "正面视角", "侧面视角", "多角度组合"],
                    key=f"sensory_angle"
                )
                
                params["detail_focus"] = st.multiselect(
                    "细节重点",
                    ["材质纹理", "工艺接缝", "表面处理", "结构细节", "品质标识"],
                    default=["材质纹理", "工艺接缝"],
                    key=f"sensory_details"
                )
                
                params["lighting_contrast"] = st.slider(
                    "明暗对比度",
                    min_value=0.3,
                    max_value=1.0,
                    value=0.7,
                    step=0.1,
                    key=f"sensory_contrast"
                )
            
            elif module_type == ModuleType.EXTENSION:
                # Extension module specific parameters
                params["carousel_themes"] = st.multiselect(
                    "轮播主题",
                    ["Lifestyle生活场景", "Pain Point痛点解决", "Extreme Performance极限性能", "Inside Out内部结构"],
                    default=["Lifestyle生活场景", "Pain Point痛点解决", "Extreme Performance极限性能", "Inside Out内部结构"],
                    key=f"extension_themes"
                )
                
                params["navigation_style"] = st.selectbox(
                    "导航风格",
                    ["专业术语", "通俗易懂", "技术导向", "用户友好"],
                    key=f"extension_nav"
                )
                
                params["layout_style"] = st.selectbox(
                    "布局风格",
                    ["经典轮播", "网格展示", "时间线", "对比展示"],
                    key=f"extension_layout"
                )
            
            elif module_type == ModuleType.TRUST:
                # Trust module specific parameters
                params["layout_ratio"] = st.selectbox(
                    "图文比例",
                    ["1:1 (正方形)", "2:3 (黄金比例)", "3:2 (宽屏)", "自适应"],
                    key=f"trust_ratio"
                )
                
                params["content_density"] = st.slider(
                    "信息密度",
                    min_value=0.3,
                    max_value=1.0,
                    value=0.7,
                    step=0.1,
                    help="信息密度越高，包含的产品信息越多",
                    key=f"trust_density"
                )
                
                params["include_cta"] = st.checkbox(
                    "包含CTA引导",
                    value=True,
                    help="包含购买引导和行动号召",
                    key=f"trust_cta"
                )
        
        return params
    
    def _render_generation_options(self, selected_modules: List[ModuleType]) -> Dict[str, Any]:
        """Render global generation options"""
        
        st.write("**生成选项**")
        
        col1, col2 = st.columns(2)
        
        with col1:
            quality_level = st.selectbox(
                "质量等级",
                ["标准质量", "高质量", "超高质量"],
                index=1,
                help="更高质量需要更长生成时间"
            )
            
            visual_consistency = st.checkbox(
                "强制视觉一致性",
                value=True,
                help="确保所有模块保持统一的视觉风格"
            )
        
        with col2:
            auto_retry = st.checkbox(
                "自动重试",
                value=True,
                help="生成失败时自动重试"
            )
            
            save_intermediate = st.checkbox(
                "保存中间结果",
                value=False,
                help="保存生成过程中的中间图片"
            )
        
        # Advanced options
        with st.expander("🔧 高级选项", expanded=False):
            seed_value = st.number_input(
                "随机种子",
                min_value=0,
                max_value=999999,
                value=0,
                help="设置固定种子可以获得可重现的结果，0表示随机"
            )
            
            batch_size = st.slider(
                "批处理大小",
                min_value=1,
                max_value=len(selected_modules),
                value=min(2, len(selected_modules)),
                help="并行生成时的批处理大小"
            )
            
            timeout_seconds = st.number_input(
                "超时时间 (秒)",
                min_value=30,
                max_value=300,
                value=120,
                help="单个模块的最大生成时间"
            )
        
        return {
            "quality_level": quality_level,
            "visual_consistency": visual_consistency,
            "auto_retry": auto_retry,
            "save_intermediate": save_intermediate,
            "seed_value": seed_value if seed_value > 0 else None,
            "batch_size": batch_size,
            "timeout_seconds": timeout_seconds
        }
    
    def _render_progress_tracking(self) -> None:
        """Render progress tracking interface"""
        
        if not self.generation_progress and not self.active_generations:
            return
        
        st.write("**生成进度**")
        
        # Overall progress
        if self.active_generations:
            total_modules = len(self.generation_progress)
            completed_modules = sum(1 for p in self.generation_progress.values() 
                                  if p.status == GenerationStatus.COMPLETED)
            
            overall_progress = completed_modules / total_modules if total_modules > 0 else 0
            
            st.progress(overall_progress, text=f"总体进度: {completed_modules}/{total_modules}")
        
        # Individual module progress
        for module_type, progress in self.generation_progress.items():
            config = self.module_configs[module_type]
            
            col1, col2, col3, col4 = st.columns([2, 2, 1, 1])
            
            with col1:
                st.write(f"{config['icon']} {config['name']}")
            
            with col2:
                if progress.status == GenerationStatus.IN_PROGRESS:
                    st.progress(progress.progress, text=progress.message)
                else:
                    status_text = self._get_status_text(progress.status)
                    st.write(status_text)
            
            with col3:
                if progress.start_time and progress.end_time:
                    duration = progress.end_time - progress.start_time
                    st.caption(f"{duration:.1f}s")
                elif progress.start_time and progress.estimated_remaining:
                    st.caption(f"剩余 {progress.estimated_remaining:.0f}s")
            
            with col4:
                if progress.status == GenerationStatus.IN_PROGRESS:
                    if st.button("⏹️", key=f"stop_{module_type.value}", help="停止生成"):
                        self._stop_generation(module_type)
    
    def _render_generation_controls(self, selected_modules: List[ModuleType], 
                                  generation_mode: GenerationMode,
                                  generation_options: Dict[str, Any],
                                  module_params: Dict[ModuleType, Dict]) -> Dict[str, Any]:
        """Render generation control buttons"""
        
        st.write("**生成控制**")
        
        # Estimate total time
        total_time = sum(self.module_configs[module]['estimated_time'] 
                        for module in selected_modules)
        
        if generation_mode == GenerationMode.PARALLEL:
            # Parallel generation is faster
            total_time = max(self.module_configs[module]['estimated_time'] 
                           for module in selected_modules)
        
        st.info(f"⏱️ 预计生成时间: {total_time} 秒")
        
        # Generation buttons
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            if generation_mode == GenerationMode.INDIVIDUAL:
                # Individual generation - show buttons for each module
                for module_type in selected_modules:
                    config = self.module_configs[module_type]
                    
                    if st.button(
                        f"🚀 生成 {config['name']}",
                        key=f"gen_individual_{module_type.value}",
                        type="primary" if len(selected_modules) == 1 else "secondary",
                        use_container_width=True
                    ):
                        return {
                            "action": "generate_individual",
                            "module_type": module_type,
                            "generation_options": generation_options,
                            "module_params": module_params.get(module_type, {})
                        }
            
            else:
                # Batch or parallel generation
                action_text = "🚀 开始批量生成" if generation_mode == GenerationMode.BATCH else "🚀 开始并行生成"
                
                if st.button(
                    action_text,
                    type="primary",
                    use_container_width=True,
                    disabled=len(self.active_generations) > 0
                ):
                    return {
                        "action": "generate_batch" if generation_mode == GenerationMode.BATCH else "generate_parallel",
                        "selected_modules": selected_modules,
                        "generation_options": generation_options,
                        "module_params": module_params
                    }
        
        with col2:
            # Stop all button
            if self.active_generations and st.button(
                "⏹️ 停止全部",
                type="secondary",
                use_container_width=True
            ):
                return {"action": "stop_all"}
        
        with col3:
            # Reset progress button
            if self.generation_progress and st.button(
                "🔄 重置",
                type="secondary", 
                use_container_width=True
            ):
                return {"action": "reset_progress"}
        
        return {"action": None}
    
    def _show_module_details(self, module_type: ModuleType) -> None:
        """Show detailed information about a module"""
        
        config = self.module_configs[module_type]
        
        # This would typically show in a modal or expander
        # For now, we'll use session state to show details
        st.session_state[f"show_details_{module_type.value}"] = True
    
    def _get_status_icon(self, status: GenerationStatus) -> str:
        """Get status icon for display"""
        
        status_icons = {
            GenerationStatus.NOT_STARTED: "⚪",
            GenerationStatus.IN_PROGRESS: "🟡",
            GenerationStatus.COMPLETED: "🟢", 
            GenerationStatus.FAILED: "🔴",
            GenerationStatus.CANCELLED: "⚫"
        }
        
        return status_icons.get(status, "❓")
    
    def _get_status_text(self, status: GenerationStatus) -> str:
        """Get status text for display"""
        
        status_texts = {
            GenerationStatus.NOT_STARTED: "未开始",
            GenerationStatus.IN_PROGRESS: "生成中...",
            GenerationStatus.COMPLETED: "已完成",
            GenerationStatus.FAILED: "生成失败",
            GenerationStatus.CANCELLED: "已取消"
        }
        
        return status_texts.get(status, "未知状态")
    
    def start_generation_tracking(self, module_type: ModuleType) -> None:
        """Start tracking generation progress for a module"""
        
        self.generation_progress[module_type] = GenerationProgress(
            module_type=module_type,
            status=GenerationStatus.IN_PROGRESS,
            progress=0.0,
            message="准备生成...",
            start_time=time.time()
        )
        
        if module_type not in self.active_generations:
            self.active_generations.append(module_type)
    
    def update_generation_progress(self, module_type: ModuleType, 
                                 progress: float, message: str) -> None:
        """Update generation progress for a module"""
        
        if module_type in self.generation_progress:
            self.generation_progress[module_type].progress = progress
            self.generation_progress[module_type].message = message
            
            # Estimate remaining time
            if progress > 0:
                elapsed = time.time() - self.generation_progress[module_type].start_time
                estimated_total = elapsed / progress
                estimated_remaining = estimated_total - elapsed
                self.generation_progress[module_type].estimated_remaining = max(0, estimated_remaining)
    
    def complete_generation(self, module_type: ModuleType, success: bool = True) -> None:
        """Mark generation as completed"""
        
        if module_type in self.generation_progress:
            self.generation_progress[module_type].status = (
                GenerationStatus.COMPLETED if success else GenerationStatus.FAILED
            )
            self.generation_progress[module_type].progress = 1.0
            self.generation_progress[module_type].end_time = time.time()
            self.generation_progress[module_type].message = (
                "生成完成" if success else "生成失败"
            )
        
        if module_type in self.active_generations:
            self.active_generations.remove(module_type)
    
    def _stop_generation(self, module_type: ModuleType) -> None:
        """Stop generation for a specific module"""
        
        if module_type in self.generation_progress:
            self.generation_progress[module_type].status = GenerationStatus.CANCELLED
            self.generation_progress[module_type].message = "已取消"
        
        if module_type in self.active_generations:
            self.active_generations.remove(module_type)
    
    def reset_progress(self) -> None:
        """Reset all generation progress"""
        
        self.generation_progress.clear()
        self.active_generations.clear()
    
    def get_generation_summary(self) -> Dict[str, Any]:
        """Get summary of generation results"""
        
        if not self.generation_progress:
            return {"total": 0, "completed": 0, "failed": 0, "in_progress": 0}
        
        summary = {
            "total": len(self.generation_progress),
            "completed": 0,
            "failed": 0,
            "in_progress": 0,
            "cancelled": 0
        }
        
        for progress in self.generation_progress.values():
            if progress.status == GenerationStatus.COMPLETED:
                summary["completed"] += 1
            elif progress.status == GenerationStatus.FAILED:
                summary["failed"] += 1
            elif progress.status == GenerationStatus.IN_PROGRESS:
                summary["in_progress"] += 1
            elif progress.status == GenerationStatus.CANCELLED:
                summary["cancelled"] += 1
        
        return summary
    
    def render_generation_summary(self) -> None:
        """Render generation summary"""
        
        summary = self.get_generation_summary()
        
        if summary["total"] == 0:
            return
        
        st.write("**生成摘要**")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("已完成", summary["completed"])
        
        with col2:
            st.metric("进行中", summary["in_progress"])
        
        with col3:
            st.metric("失败", summary["failed"])
        
        with col4:
            st.metric("已取消", summary["cancelled"])
    
    def is_generation_active(self) -> bool:
        """Check if any generation is currently active"""
        
        return len(self.active_generations) > 0
    
    def get_active_generations(self) -> List[ModuleType]:
        """Get list of currently active generations"""
        
        return self.active_generations.copy()
    
    def can_start_generation(self, module_type: ModuleType) -> tuple[bool, str]:
        """Check if generation can be started for a module"""
        
        # Check if analysis is complete
        session = self.controller.state_manager.get_current_session()
        if not session or not session.analysis_result:
            return False, "产品分析未完成"
        
        # Check if module is already being generated
        if module_type in self.active_generations:
            return False, "模块正在生成中"
        
        # Check if module is already completed
        if (module_type in self.generation_progress and 
            self.generation_progress[module_type].status == GenerationStatus.COMPLETED):
            return True, "模块已完成，可以重新生成"
        
        return True, "可以开始生成"


# Global instance for easy access
module_generation_panel = ModuleGenerationPanel