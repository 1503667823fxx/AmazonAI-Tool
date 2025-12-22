"""
A+ Studio Image Preview Gallery Component
Provides interface for previewing, managing and regenerating A+ module images
"""

import streamlit as st
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import io
import base64
from PIL import Image
from services.aplus_studio.models import ModuleType, GenerationResult, GenerationStatus


@dataclass
class ImageVersion:
    """Image version information"""
    version_id: str
    image_data: bytes
    generation_time: float
    quality_score: float
    prompt_used: str
    parameters: Dict[str, Any]
    created_at: str
    is_current: bool = False


class ViewMode(Enum):
    """Gallery view modes"""
    GRID = "grid"           # Grid layout
    LIST = "list"           # List layout  
    COMPARISON = "comparison" # Side-by-side comparison
    SLIDESHOW = "slideshow"  # Slideshow mode


class ImagePreviewGallery:
    """Image preview and management gallery for A+ Studio"""
    
    def __init__(self, controller):
        self.controller = controller
        self.view_mode = ViewMode.GRID
        self.selected_modules: List[ModuleType] = []
        self.comparison_versions: Dict[ModuleType, List[str]] = {}
        
        # Gallery configurations
        self.grid_columns = 2
        self.thumbnail_size = (300, 225)  # Maintain 4:3 aspect ratio
        self.max_versions_display = 5
    
    def render_preview_gallery(self) -> Dict[str, Any]:
        """
        Render the complete image preview gallery
        
        Returns:
            Dict containing gallery actions and selections
        """
        st.subheader("🖼️ 图片预览画廊")
        
        # Get module results
        module_results = self.controller.get_module_results()
        
        if not module_results:
            self._render_empty_gallery()
            return {"action": None}
        
        # Gallery controls
        gallery_action = self._render_gallery_controls(module_results)
        
        # Main gallery display
        self._render_gallery_display(module_results)
        
        return gallery_action
    
    def _render_empty_gallery(self) -> None:
        """Render empty gallery state"""
        
        st.info("📷 还没有生成的图片")
        
        with st.container():
            st.markdown("""
            ### 开始生成您的A+图片
            
            1. 🔍 **完成产品分析** - 上传产品信息和图片
            2. 🎨 **选择模块** - 选择要生成的A+模块
            3. 🚀 **开始生成** - 生成您的专业A+图片
            4. 📋 **预览管理** - 在这里查看和管理生成结果
            """)
            
            if st.button("🎯 前往模块生成", type="primary"):
                # This would navigate to generation tab
                st.session_state["active_tab"] = "module_generation"
    
    def _render_gallery_controls(self, module_results: Dict[ModuleType, GenerationResult]) -> Dict[str, Any]:
        """Render gallery control interface"""
        
        col1, col2, col3, col4 = st.columns([2, 2, 2, 2])
        
        with col1:
            # View mode selection
            view_mode_options = {
                "网格视图": ViewMode.GRID,
                "列表视图": ViewMode.LIST,
                "对比视图": ViewMode.COMPARISON,
                "幻灯片": ViewMode.SLIDESHOW
            }
            
            selected_view = st.selectbox(
                "视图模式",
                list(view_mode_options.keys()),
                key="gallery_view_mode"
            )
            self.view_mode = view_mode_options[selected_view]
        
        with col2:
            # Module filter
            available_modules = list(module_results.keys())
            selected_modules = st.multiselect(
                "筛选模块",
                available_modules,
                default=available_modules,
                format_func=lambda x: self._get_module_display_name(x),
                key="gallery_module_filter"
            )
            self.selected_modules = selected_modules
        
        with col3:
            # Sort options
            sort_options = ["生成时间", "质量分数", "模块类型", "文件大小"]
            sort_by = st.selectbox("排序方式", sort_options, key="gallery_sort")
        
        with col4:
            # Gallery actions
            action = None
            
            if st.button("📥 导出选中", key="export_selected"):
                action = {"action": "export_selected", "modules": selected_modules}
            
            if st.button("🔄 刷新画廊", key="refresh_gallery"):
                action = {"action": "refresh"}
        
        return action or {"action": None}
    
    def _render_gallery_display(self, module_results: Dict[ModuleType, GenerationResult]) -> None:
        """Render main gallery display based on view mode"""
        
        # Filter results based on selected modules
        filtered_results = {
            module: result for module, result in module_results.items()
            if not self.selected_modules or module in self.selected_modules
        }
        
        if not filtered_results:
            st.info("没有符合筛选条件的图片")
            return
        
        if self.view_mode == ViewMode.GRID:
            self._render_grid_view(filtered_results)
        elif self.view_mode == ViewMode.LIST:
            self._render_list_view(filtered_results)
        elif self.view_mode == ViewMode.COMPARISON:
            self._render_comparison_view(filtered_results)
        elif self.view_mode == ViewMode.SLIDESHOW:
            self._render_slideshow_view(filtered_results)
    
    def _render_grid_view(self, module_results: Dict[ModuleType, GenerationResult]) -> None:
        """Render grid view of images"""
        
        # Calculate grid layout
        modules = list(module_results.keys())
        rows = (len(modules) + self.grid_columns - 1) // self.grid_columns
        
        for row in range(rows):
            cols = st.columns(self.grid_columns)
            
            for col_idx in range(self.grid_columns):
                module_idx = row * self.grid_columns + col_idx
                
                if module_idx < len(modules):
                    module_type = modules[module_idx]
                    result = module_results[module_type]
                    
                    with cols[col_idx]:
                        self._render_image_card(module_type, result)
    
    def _render_image_card(self, module_type: ModuleType, result: GenerationResult) -> None:
        """Render individual image card"""
        
        # Card container
        with st.container():
            # Module header
            col1, col2, col3 = st.columns([2, 1, 1])
            
            with col1:
                module_name = self._get_module_display_name(module_type)
                st.write(f"**{module_name}**")
            
            with col2:
                # Quality indicator
                quality_color = self._get_quality_color(result.quality_score)
                st.markdown(f"<span style='color: {quality_color}'>⭐ {result.quality_score:.1f}</span>", 
                           unsafe_allow_html=True)
            
            with col3:
                # Action menu
                if st.button("⋮", key=f"menu_{module_type.value}", help="更多操作"):
                    self._show_image_menu(module_type)
            
            # Image display
            if result.image_data:
                st.image(
                    result.image_data,
                    use_container_width=True,
                    caption=f"生成时间: {result.generation_time:.1f}s"
                )
            else:
                st.error("图片数据不可用")
            
            # Image info
            self._render_image_info(result)
            
            # Action buttons
            self._render_image_actions(module_type, result)
            
            st.divider()
    
    def _render_image_info(self, result: GenerationResult) -> None:
        """Render image information"""
        
        with st.expander("📊 图片信息", expanded=False):
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**生成信息**")
                st.write(f"• 质量分数: {result.quality_score:.2f}")
                st.write(f"• 生成时间: {result.generation_time:.1f}秒")
                st.write(f"• 验证状态: {result.validation_status.value}")
            
            with col2:
                st.write("**技术信息**")
                if result.metadata:
                    st.write(f"• 尺寸: {result.metadata.get('dimensions', '600x450')}")
                    st.write(f"• 格式: {result.metadata.get('format', 'PNG')}")
                    st.write(f"• 文件大小: {result.metadata.get('file_size', 'N/A')}")
            
            # Prompt information
            if result.prompt_used:
                st.write("**使用的提示词**")
                st.code(result.prompt_used[:200] + "..." if len(result.prompt_used) > 200 else result.prompt_used)
    
    def _render_image_actions(self, module_type: ModuleType, result: GenerationResult) -> None:
        """Render image action buttons"""
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🔄 重新生成", key=f"preview_regen_{module_type.value}", use_container_width=True):
                st.session_state[f"regenerate_{module_type.value}"] = True
        
        with col2:
            if st.button("📥 下载", key=f"download_{module_type.value}", use_container_width=True):
                self._download_image(module_type, result)
        
        with col3:
            if st.button("📋 复制", key=f"copy_{module_type.value}", use_container_width=True):
                self._copy_image_info(module_type, result)
    
    def _render_list_view(self, module_results: Dict[ModuleType, GenerationResult]) -> None:
        """Render list view of images"""
        
        for module_type, result in module_results.items():
            with st.container():
                col1, col2 = st.columns([1, 2])
                
                with col1:
                    # Image thumbnail
                    if result.image_data:
                        st.image(result.image_data, width=200)
                
                with col2:
                    # Image details
                    module_name = self._get_module_display_name(module_type)
                    st.write(f"**{module_name}**")
                    
                    st.write(f"质量分数: {result.quality_score:.2f}")
                    st.write(f"生成时间: {result.generation_time:.1f}秒")
                    st.write(f"验证状态: {result.validation_status.value}")
                    
                    # Action buttons
                    self._render_image_actions(module_type, result)
                
                st.divider()
    
    def _render_comparison_view(self, module_results: Dict[ModuleType, GenerationResult]) -> None:
        """Render comparison view of images"""
        
        st.write("**图片对比**")
        
        # Module selection for comparison
        available_modules = list(module_results.keys())
        
        if len(available_modules) < 2:
            st.info("需要至少2个模块才能进行对比")
            return
        
        col1, col2 = st.columns(2)
        
        with col1:
            module1 = st.selectbox(
                "选择模块1",
                available_modules,
                format_func=lambda x: self._get_module_display_name(x),
                key="compare_module1"
            )
        
        with col2:
            module2 = st.selectbox(
                "选择模块2", 
                available_modules,
                format_func=lambda x: self._get_module_display_name(x),
                key="compare_module2"
            )
        
        if module1 != module2:
            # Display comparison
            col1, col2 = st.columns(2)
            
            with col1:
                st.write(f"**{self._get_module_display_name(module1)}**")
                result1 = module_results[module1]
                if result1.image_data:
                    st.image(result1.image_data, use_container_width=True)
                st.write(f"质量分数: {result1.quality_score:.2f}")
                st.write(f"生成时间: {result1.generation_time:.1f}s")
            
            with col2:
                st.write(f"**{self._get_module_display_name(module2)}**")
                result2 = module_results[module2]
                if result2.image_data:
                    st.image(result2.image_data, use_container_width=True)
                st.write(f"质量分数: {result2.quality_score:.2f}")
                st.write(f"生成时间: {result2.generation_time:.1f}s")
    
    def _render_slideshow_view(self, module_results: Dict[ModuleType, GenerationResult]) -> None:
        """Render slideshow view of images"""
        
        modules = list(module_results.keys())
        
        if not modules:
            return
        
        # Slideshow controls
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col1:
            if st.button("⬅️ 上一张", key="slideshow_prev"):
                if "slideshow_index" not in st.session_state:
                    st.session_state.slideshow_index = 0
                st.session_state.slideshow_index = (st.session_state.slideshow_index - 1) % len(modules)
        
        with col2:
            # Current slide indicator
            current_index = getattr(st.session_state, "slideshow_index", 0)
            st.write(f"**{current_index + 1} / {len(modules)}**")
        
        with col3:
            if st.button("➡️ 下一张", key="slideshow_next"):
                if "slideshow_index" not in st.session_state:
                    st.session_state.slideshow_index = 0
                st.session_state.slideshow_index = (st.session_state.slideshow_index + 1) % len(modules)
        
        # Display current image
        current_module = modules[current_index]
        current_result = module_results[current_module]
        
        st.write(f"**{self._get_module_display_name(current_module)}**")
        
        if current_result.image_data:
            st.image(current_result.image_data, use_container_width=True)
        
        # Image details
        self._render_image_info(current_result)
        self._render_image_actions(current_module, current_result)
    
    def _get_module_display_name(self, module_type: ModuleType) -> str:
        """Get display name for module type"""
        
        display_names = {
            ModuleType.IDENTITY: "🎭 身份代入",
            ModuleType.SENSORY: "👁️ 感官解构", 
            ModuleType.EXTENSION: "🔄 多维延展",
            ModuleType.TRUST: "🤝 信任转化"
        }
        
        return display_names.get(module_type, module_type.value)
    
    def _get_quality_color(self, quality_score: float) -> str:
        """Get color for quality score display"""
        
        if quality_score >= 0.8:
            return "#28a745"  # Green
        elif quality_score >= 0.6:
            return "#ffc107"  # Yellow
        else:
            return "#dc3545"  # Red
    
    def _show_image_menu(self, module_type: ModuleType) -> None:
        """Show image action menu"""
        
        # This would typically show a dropdown menu
        # For now, we'll use session state to track menu visibility
        menu_key = f"show_menu_{module_type.value}"
        
        if menu_key not in st.session_state:
            st.session_state[menu_key] = False
        
        st.session_state[menu_key] = not st.session_state[menu_key]
    
    def _download_image(self, module_type: ModuleType, result: GenerationResult) -> None:
        """Handle image download"""
        
        if result.image_data:
            # Create download button
            filename = f"aplus_{module_type.value}_{int(result.generation_time)}.png"
            
            st.download_button(
                label="📥 下载图片",
                data=result.image_data,
                file_name=filename,
                mime="image/png",
                key=f"download_btn_{module_type.value}"
            )
    
    def _copy_image_info(self, module_type: ModuleType, result: GenerationResult) -> None:
        """Copy image information to clipboard"""
        
        info_text = f"""
模块: {self._get_module_display_name(module_type)}
质量分数: {result.quality_score:.2f}
生成时间: {result.generation_time:.1f}秒
验证状态: {result.validation_status.value}
提示词: {result.prompt_used[:100]}...
        """.strip()
        
        # In a real implementation, this would copy to clipboard
        st.success("图片信息已复制到剪贴板")
        st.code(info_text)
    
    def render_version_history(self, module_type: ModuleType) -> None:
        """Render version history for a specific module"""
        
        st.subheader(f"📚 {self._get_module_display_name(module_type)} 版本历史")
        
        # Get version history from controller
        versions = self.controller.get_module_versions(module_type)
        
        if not versions:
            st.info("暂无版本历史")
            return
        
        # Display versions
        for i, version in enumerate(versions):
            with st.expander(f"版本 {i+1} - {version.created_at}", expanded=i==0):
                col1, col2 = st.columns([1, 2])
                
                with col1:
                    if version.image_data:
                        st.image(version.image_data, width=200)
                
                with col2:
                    st.write(f"**质量分数:** {version.quality_score:.2f}")
                    st.write(f"**生成时间:** {version.generation_time:.1f}秒")
                    st.write(f"**当前版本:** {'是' if version.is_current else '否'}")
                    
                    if st.button(f"恢复此版本", key=f"restore_{version.version_id}"):
                        self._restore_version(module_type, version)
                    
                    if st.button(f"删除版本", key=f"delete_{version.version_id}"):
                        self._delete_version(module_type, version)
    
    def render_batch_operations(self, module_results: Dict[ModuleType, GenerationResult]) -> Dict[str, Any]:
        """Render batch operations interface"""
        
        st.subheader("🔧 批量操作")
        
        # Module selection
        selected_modules = st.multiselect(
            "选择模块",
            list(module_results.keys()),
            format_func=lambda x: self._get_module_display_name(x),
            key="batch_module_selection"
        )
        
        if not selected_modules:
            st.info("请选择要操作的模块")
            return {"action": None}
        
        # Batch operations
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
            if st.button("🗑️ 批量删除", use_container_width=True):
                return {"action": "batch_delete", "modules": selected_modules}
        
        return {"action": None}
    
    def render_quality_analysis(self, module_results: Dict[ModuleType, GenerationResult]) -> None:
        """Render quality analysis dashboard"""
        
        st.subheader("📊 质量分析")
        
        if not module_results:
            st.info("没有可分析的图片")
            return
        
        # Overall statistics
        quality_scores = [result.quality_score for result in module_results.values()]
        generation_times = [result.generation_time for result in module_results.values()]
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            avg_quality = sum(quality_scores) / len(quality_scores)
            st.metric("平均质量", f"{avg_quality:.2f}")
        
        with col2:
            max_quality = max(quality_scores)
            st.metric("最高质量", f"{max_quality:.2f}")
        
        with col3:
            avg_time = sum(generation_times) / len(generation_times)
            st.metric("平均生成时间", f"{avg_time:.1f}s")
        
        with col4:
            total_images = len(module_results)
            st.metric("图片总数", total_images)
        
        # Quality distribution
        st.write("**质量分布**")
        
        quality_ranges = {
            "优秀 (0.8+)": len([q for q in quality_scores if q >= 0.8]),
            "良好 (0.6-0.8)": len([q for q in quality_scores if 0.6 <= q < 0.8]),
            "一般 (0.4-0.6)": len([q for q in quality_scores if 0.4 <= q < 0.6]),
            "较差 (<0.4)": len([q for q in quality_scores if q < 0.4])
        }
        
        for range_name, count in quality_ranges.items():
            percentage = (count / len(quality_scores)) * 100 if quality_scores else 0
            st.write(f"• {range_name}: {count} 张 ({percentage:.1f}%)")
    
    def _restore_version(self, module_type: ModuleType, version: ImageVersion) -> None:
        """Restore a specific version as current"""
        
        # This would call the controller to restore the version
        success = self.controller.restore_module_version(module_type, version.version_id)
        
        if success:
            st.success(f"已恢复 {self._get_module_display_name(module_type)} 到版本 {version.version_id}")
            st.rerun()
        else:
            st.error("版本恢复失败")
    
    def _delete_version(self, module_type: ModuleType, version: ImageVersion) -> None:
        """Delete a specific version"""
        
        # Confirm deletion
        if st.button(f"确认删除版本 {version.version_id}", key=f"confirm_delete_{version.version_id}"):
            success = self.controller.delete_module_version(module_type, version.version_id)
            
            if success:
                st.success("版本已删除")
                st.rerun()
            else:
                st.error("版本删除失败")
    
    def set_view_mode(self, mode: ViewMode) -> None:
        """Set gallery view mode"""
        self.view_mode = mode
    
    def set_grid_columns(self, columns: int) -> None:
        """Set number of columns for grid view"""
        self.grid_columns = max(1, min(4, columns))
    
    def get_selected_modules(self) -> List[ModuleType]:
        """Get currently selected modules"""
        return self.selected_modules.copy()
    
    def clear_selection(self) -> None:
        """Clear module selection"""
        self.selected_modules.clear()
    
    def select_all_modules(self, available_modules: List[ModuleType]) -> None:
        """Select all available modules"""
        self.selected_modules = available_modules.copy()


# Global instance for easy access  
image_preview_gallery = ImagePreviewGallery
