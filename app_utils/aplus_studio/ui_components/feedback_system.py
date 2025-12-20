"""
用户体验反馈系统
提供操作完成反馈和下一步指引功能
"""

import streamlit as st
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime
import time


class FeedbackSystem:
    """用户体验反馈系统"""
    
    def __init__(self):
        self.feedback_history = []
        self.current_operation = None
        self.operation_start_time = None
    
    def show_success_feedback(self, message: str, next_steps: List[str] = None, auto_clear: bool = True):
        """显示成功反馈和下一步指引"""
        st.success(f"✅ {message}")
        
        if next_steps:
            st.info("### 🎯 下一步操作建议:")
            for i, step in enumerate(next_steps, 1):
                st.write(f"{i}. {step}")
        
        # 记录反馈历史
        self._record_feedback("success", message, next_steps)
        
        # 自动清除反馈（可选）
        if auto_clear:
            self._schedule_auto_clear()
    
    def show_error_feedback(self, message: str, solutions: List[str] = None, retry_action: Callable = None):
        """显示错误反馈和解决建议"""
        st.error(f"❌ {message}")
        
        if solutions:
            st.warning("### 💡 解决建议:")
            for i, solution in enumerate(solutions, 1):
                st.write(f"{i}. {solution}")
        
        # 提供重试按钮
        if retry_action:
            if st.button("🔄 重试", key=f"retry_{int(time.time())}"):
                retry_action()
        
        # 记录反馈历史
        self._record_feedback("error", message, solutions)
    
    def show_warning_feedback(self, message: str, actions: List[Dict[str, Any]] = None):
        """显示警告反馈和可选操作"""
        st.warning(f"⚠️ {message}")
        
        if actions:
            st.info("### 🔧 可选操作:")
            cols = st.columns(len(actions))
            
            for i, action in enumerate(actions):
                with cols[i]:
                    if st.button(action["label"], key=f"action_{i}_{int(time.time())}"):
                        if "callback" in action:
                            action["callback"]()
        
        # 记录反馈历史
        self._record_feedback("warning", message, actions)
    
    def show_info_feedback(self, message: str, details: str = None):
        """显示信息反馈"""
        st.info(f"ℹ️ {message}")
        
        if details:
            with st.expander("📋 详细信息"):
                st.write(details)
        
        # 记录反馈历史
        self._record_feedback("info", message, details)
    
    def start_operation(self, operation_name: str, estimated_time: int = None):
        """开始操作，显示进度指示"""
        self.current_operation = operation_name
        self.operation_start_time = time.time()
        
        progress_text = f"正在执行: {operation_name}"
        if estimated_time:
            progress_text += f" (预计 {estimated_time} 秒)"
        
        return st.spinner(progress_text)
    
    def update_operation_progress(self, progress: float, status_text: str = None):
        """更新操作进度"""
        if self.current_operation:
            elapsed_time = time.time() - self.operation_start_time if self.operation_start_time else 0
            
            # 显示进度条
            st.progress(progress)
            
            # 显示状态文本
            if status_text:
                st.caption(f"📊 {status_text} | 已用时: {elapsed_time:.1f}秒")
    
    def complete_operation(self, success: bool, message: str, next_steps: List[str] = None):
        """完成操作"""
        elapsed_time = time.time() - self.operation_start_time if self.operation_start_time else 0
        
        if success:
            completion_message = f"{message} (耗时: {elapsed_time:.1f}秒)"
            self.show_success_feedback(completion_message, next_steps)
        else:
            self.show_error_feedback(f"{message} (耗时: {elapsed_time:.1f}秒)")
        
        # 重置操作状态
        self.current_operation = None
        self.operation_start_time = None
    
    def show_step_guidance(self, current_step: int, total_steps: int, step_name: str, 
                          step_description: str, completion_criteria: List[str] = None):
        """显示步骤指引"""
        # 进度指示器
        progress = current_step / total_steps
        st.progress(progress)
        
        # 步骤信息
        st.markdown(f"### 步骤 {current_step}/{total_steps}: {step_name}")
        st.info(f"📝 {step_description}")
        
        # 完成标准
        if completion_criteria:
            with st.expander("✅ 完成标准"):
                for criterion in completion_criteria:
                    st.write(f"• {criterion}")
        
        # 导航按钮
        col_prev, col_next = st.columns(2)
        
        with col_prev:
            if current_step > 1:
                if st.button("⬅️ 上一步", key=f"prev_step_{current_step}"):
                    return "previous"
        
        with col_next:
            if current_step < total_steps:
                if st.button("➡️ 下一步", key=f"next_step_{current_step}"):
                    return "next"
            else:
                if st.button("🏁 完成", key=f"finish_{current_step}"):
                    return "finish"
        
        return None
    
    def show_loading_state(self, message: str, show_spinner: bool = True, show_progress: bool = False):
        """显示加载状态"""
        if show_spinner:
            with st.spinner(message):
                if show_progress:
                    progress_bar = st.progress(0)
                    for i in range(100):
                        time.sleep(0.01)  # 模拟加载过程
                        progress_bar.progress(i + 1)
        else:
            st.info(f"⏳ {message}")
    
    def show_confirmation_dialog(self, title: str, message: str, 
                               confirm_label: str = "确认", cancel_label: str = "取消") -> bool:
        """显示确认对话框"""
        st.warning(f"### {title}")
        st.write(message)
        
        col_confirm, col_cancel = st.columns(2)
        
        with col_confirm:
            if st.button(confirm_label, type="primary", key=f"confirm_{int(time.time())}"):
                return True
        
        with col_cancel:
            if st.button(cancel_label, key=f"cancel_{int(time.time())}"):
                return False
        
        return None
    
    def show_quick_actions(self, actions: List[Dict[str, Any]], title: str = "快速操作"):
        """显示快速操作按钮"""
        st.markdown(f"### 🚀 {title}")
        
        # 计算列数（最多4列）
        num_cols = min(len(actions), 4)
        cols = st.columns(num_cols)
        
        for i, action in enumerate(actions):
            col_index = i % num_cols
            with cols[col_index]:
                button_key = f"quick_action_{i}_{int(time.time())}"
                
                if st.button(
                    action["label"], 
                    key=button_key,
                    help=action.get("help", ""),
                    use_container_width=True
                ):
                    if "callback" in action:
                        action["callback"]()
                    return action.get("action_id")
        
        return None
    
    def show_tips_and_hints(self, tips: List[str], title: str = "💡 使用提示"):
        """显示使用提示和帮助"""
        with st.expander(title):
            for i, tip in enumerate(tips, 1):
                st.write(f"{i}. {tip}")
    
    def show_keyboard_shortcuts(self, shortcuts: Dict[str, str]):
        """显示键盘快捷键"""
        with st.expander("⌨️ 键盘快捷键"):
            for shortcut, description in shortcuts.items():
                st.write(f"**{shortcut}**: {description}")
    
    def get_feedback_history(self) -> List[Dict[str, Any]]:
        """获取反馈历史"""
        return self.feedback_history
    
    def clear_feedback_history(self):
        """清除反馈历史"""
        self.feedback_history.clear()
    
    def _record_feedback(self, feedback_type: str, message: str, additional_data: Any = None):
        """记录反馈历史"""
        feedback_entry = {
            "type": feedback_type,
            "message": message,
            "timestamp": datetime.now().isoformat(),
            "additional_data": additional_data
        }
        
        self.feedback_history.append(feedback_entry)
        
        # 限制历史记录数量
        if len(self.feedback_history) > 100:
            self.feedback_history = self.feedback_history[-100:]
    
    def _schedule_auto_clear(self, delay: int = 5):
        """安排自动清除反馈（在实际应用中可能需要不同的实现）"""
        # 在Streamlit中，这个功能可能需要通过session state和定时器来实现
        # 这里只是一个占位符实现
        pass


class PerformanceOptimizer:
    """性能优化器"""
    
    def __init__(self):
        self.cache_stats = {}
        self.performance_metrics = {}
    
    def optimize_image_loading(self, image_urls: List[str], lazy_load: bool = True):
        """优化图片加载"""
        if lazy_load:
            # 实现懒加载逻辑
            for i, url in enumerate(image_urls):
                if i < 3:  # 只预加载前3张图片
                    st.image(url, use_container_width=True)
                else:
                    # 懒加载其余图片
                    if st.button(f"加载图片 {i+1}", key=f"lazy_load_{i}"):
                        st.image(url, use_container_width=True)
        else:
            # 正常加载所有图片
            for url in image_urls:
                st.image(url, use_container_width=True)
    
    def optimize_data_loading(self, data_loader: Callable, cache_key: str = None):
        """优化数据加载"""
        if cache_key:
            # 使用缓存
            if cache_key not in self.cache_stats:
                start_time = time.time()
                data = data_loader()
                load_time = time.time() - start_time
                
                self.cache_stats[cache_key] = {
                    "data": data,
                    "load_time": load_time,
                    "cached_at": datetime.now()
                }
                
                return data
            else:
                return self.cache_stats[cache_key]["data"]
        else:
            return data_loader()
    
    def show_performance_metrics(self):
        """显示性能指标"""
        if self.cache_stats or self.performance_metrics:
            with st.expander("📊 性能指标"):
                if self.cache_stats:
                    st.write("**缓存统计:**")
                    for key, stats in self.cache_stats.items():
                        st.write(f"- {key}: 加载时间 {stats['load_time']:.2f}秒")
                
                if self.performance_metrics:
                    st.write("**性能指标:**")
                    for metric, value in self.performance_metrics.items():
                        st.write(f"- {metric}: {value}")
    
    def measure_operation_time(self, operation_name: str):
        """测量操作时间的装饰器"""
        def decorator(func):
            def wrapper(*args, **kwargs):
                start_time = time.time()
                result = func(*args, **kwargs)
                end_time = time.time()
                
                execution_time = end_time - start_time
                self.performance_metrics[operation_name] = f"{execution_time:.2f}秒"
                
                return result
            return wrapper
        return decorator


class ResponsiveLayoutManager:
    """响应式布局管理器"""
    
    def __init__(self):
        self.layout_cache = {}
    
    def create_responsive_columns(self, desktop_ratios: List[float], 
                                mobile_ratios: List[float] = None, 
                                breakpoint_width: int = 768):
        """创建响应式列布局"""
        # 在Streamlit中，我们可以根据容器宽度调整列比例
        # 这里提供一个简化的实现
        
        # 检测是否为移动设备（简化实现）
        is_mobile = st.session_state.get('is_mobile', False)
        
        if is_mobile and mobile_ratios:
            return st.columns(mobile_ratios)
        else:
            return st.columns(desktop_ratios)
    
    def create_adaptive_grid(self, items: List[Any], items_per_row: int = 3, 
                           mobile_items_per_row: int = 1):
        """创建自适应网格布局"""
        is_mobile = st.session_state.get('is_mobile', False)
        current_items_per_row = mobile_items_per_row if is_mobile else items_per_row
        
        # 分组显示项目
        for i in range(0, len(items), current_items_per_row):
            cols = st.columns(current_items_per_row)
            for j, item in enumerate(items[i:i+current_items_per_row]):
                with cols[j]:
                    # 渲染项目（这里需要根据实际项目类型来实现）
                    if isinstance(item, dict) and "render" in item:
                        item["render"]()
                    else:
                        st.write(item)
    
    def optimize_mobile_layout(self):
        """优化移动端布局"""
        # 检测移动设备的简化方法
        # 在实际应用中，可能需要使用JavaScript来检测屏幕尺寸
        
        # 添加移动端优化的CSS
        mobile_css = """
        <style>
        @media (max-width: 768px) {
            .stColumns > div {
                min-width: 100% !important;
                margin-bottom: 1rem;
            }
            
            .stButton > button {
                width: 100% !important;
            }
            
            .stSelectbox > div {
                width: 100% !important;
            }
        }
        </style>
        """
        
        st.markdown(mobile_css, unsafe_allow_html=True)


# 全局实例
feedback_system = FeedbackSystem()
performance_optimizer = PerformanceOptimizer()
layout_manager = ResponsiveLayoutManager()