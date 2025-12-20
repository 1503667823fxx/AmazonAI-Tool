import streamlit as st
from PIL import Image, ImageSequence
import io
import sys
import os
import zipfile
import json
import traceback
from typing import Dict, Any, Optional

# 导入模板管理服务
sys.path.append(os.path.abspath('.'))

# 导入用户体验组件
try:
    from app_utils.aplus_studio.ui_components.feedback_system import (
        FeedbackSystem, PerformanceOptimizer, ResponsiveLayoutManager
    )
except ImportError:
    # 如果导入失败，创建简化版本
    class FeedbackSystem:
        def show_success_feedback(self, message, next_steps=None, auto_clear=True):
            st.success(f"✅ {message}")
            if next_steps:
                for i, step in enumerate(next_steps, 1):
                    st.info(f"{i}. {step}")
        
        def show_error_feedback(self, message, solutions=None, retry_action=None):
            st.error(f"❌ {message}")
            if solutions:
                for solution in solutions:
                    st.warning(f"💡 {solution}")
        
        def show_warning_feedback(self, message, actions=None):
            st.warning(f"⚠️ {message}")
            if actions:
                for action in actions:
                    if isinstance(action, dict) and "label" in action:
                        if st.button(action["label"]):
                            if "callback" in action:
                                action["callback"]()
        
        def show_tips_and_hints(self, tips):
            with st.expander("💡 使用提示", expanded=False):
                for tip in tips:
                    st.info(f"• {tip}")
        
        def show_step_guidance(self, current_step, total_steps, step_name, step_desc, completion_criteria=None):
            st.info(f"📍 步骤 {current_step}/{total_steps}: {step_name}")
            st.write(step_desc)
            if completion_criteria:
                with st.expander("完成标准", expanded=False):
                    for criteria in completion_criteria:
                        st.write(f"• {criteria}")
            return None
        
        def show_keyboard_shortcuts(self, shortcuts):
            with st.expander("⌨️ 键盘快捷键", expanded=False):
                for key, desc in shortcuts.items():
                    st.write(f"**{key}**: {desc}")
    
    class PerformanceOptimizer:
        def __init__(self): 
            self.metrics = {}
        
        def measure_operation_time(self, name): 
            def decorator(func): 
                return func
            return decorator
        
        def show_performance_metrics(self):
            if self.metrics:
                st.info("📊 性能指标: " + ", ".join([f"{k}: {v}" for k, v in self.metrics.items()]))
            else:
                st.info("📊 性能监控已启用")
    
    class ResponsiveLayoutManager:
        def __init__(self): pass
        
        def optimize_mobile_layout(self): 
            pass
        
        def create_responsive_columns(self, desktop_ratios=None, mobile_ratios=None):
            # 简化版本，直接返回标准列布局
            if desktop_ratios:
                return st.columns(desktop_ratios)
            else:
                return st.columns([1, 1, 1])

# 全局状态管理类
class APlusStudioState:
    """A+Studio应用状态管理器"""
    
    def __init__(self):
        self.initialize_session_state()
    
    def initialize_session_state(self):
        """初始化会话状态"""
        # 应用模式状态
        if 'aplus_interface_mode' not in st.session_state:
            st.session_state.aplus_interface_mode = "工作流模式"
        
        # 工作流状态
        if 'aplus_workflow_session_id' not in st.session_state:
            st.session_state.aplus_workflow_session_id = None
        
        if 'aplus_current_step' not in st.session_state:
            st.session_state.aplus_current_step = 0
        
        # 模板选择状态
        if 'aplus_selected_template_id' not in st.session_state:
            st.session_state.aplus_selected_template_id = None
        
        # 产品数据状态
        if 'aplus_product_data' not in st.session_state:
            st.session_state.aplus_product_data = None
        
        # AI处理状态
        if 'aplus_ai_processing' not in st.session_state:
            st.session_state.aplus_ai_processing = False
        
        # 错误状态
        if 'aplus_last_error' not in st.session_state:
            st.session_state.aplus_last_error = None
        
        # 成功消息状态
        if 'aplus_success_message' not in st.session_state:
            st.session_state.aplus_success_message = None
        
        # 用户体验优化状态
        if 'aplus_feedback_system' not in st.session_state:
            st.session_state.aplus_feedback_system = FeedbackSystem()
        
        if 'aplus_performance_optimizer' not in st.session_state:
            st.session_state.aplus_performance_optimizer = PerformanceOptimizer()
        
        if 'aplus_layout_manager' not in st.session_state:
            st.session_state.aplus_layout_manager = ResponsiveLayoutManager()
        
        # 操作历史
        if 'aplus_operation_history' not in st.session_state:
            st.session_state.aplus_operation_history = []
    
    def reset_workflow(self):
        """重置工作流状态"""
        st.session_state.aplus_workflow_session_id = None
        st.session_state.aplus_current_step = 0
        st.session_state.aplus_selected_template_id = None
        st.session_state.aplus_product_data = None
        st.session_state.aplus_ai_processing = False
        st.session_state.aplus_last_error = None
        st.session_state.aplus_success_message = None
    
    def set_error(self, error_message: str, solutions: list = None):
        """设置错误消息"""
        st.session_state.aplus_last_error = error_message
        st.session_state.aplus_success_message = None
        
        # 使用反馈系统显示错误
        feedback_system = st.session_state.get('aplus_feedback_system')
        if feedback_system:
            feedback_system.show_error_feedback(error_message, solutions)
    
    def set_success(self, success_message: str, next_steps: list = None):
        """设置成功消息"""
        st.session_state.aplus_success_message = success_message
        st.session_state.aplus_last_error = None
        
        # 使用反馈系统显示成功消息
        feedback_system = st.session_state.get('aplus_feedback_system')
        if feedback_system:
            feedback_system.show_success_feedback(success_message, next_steps)
    
    def clear_messages(self):
        """清除所有消息"""
        st.session_state.aplus_last_error = None
        st.session_state.aplus_success_message = None
    
    def add_operation_to_history(self, operation: str, result: str, timestamp: str = None):
        """添加操作到历史记录"""
        if timestamp is None:
            from datetime import datetime
            timestamp = datetime.now().isoformat()
        
        history_entry = {
            "operation": operation,
            "result": result,
            "timestamp": timestamp
        }
        
        st.session_state.aplus_operation_history.append(history_entry)
        
        # 限制历史记录数量
        if len(st.session_state.aplus_operation_history) > 50:
            st.session_state.aplus_operation_history = st.session_state.aplus_operation_history[-50:]

# 组件管理器
class ComponentManager:
    """组件管理器，负责初始化和管理所有系统组件"""
    
    def __init__(self):
        self.components = {}
        self.ui_components = {}
        self.initialized = False
        self.initialization_error = None
    
    def initialize_components(self):
        """初始化所有系统组件"""
        if self.initialized:
            return True
        
        try:
            # 导入核心组件
            from services.aplus_studio import (
                TemplateService, CategoryService, SearchService,
                WorkflowService, StepProcessorService,
                GeminiService, ImageCompositorService, FileService
            )
            
            # 导入UI组件
            from app_utils.aplus_studio.ui_components.template_library_ui import TemplateLibraryUI
            from app_utils.aplus_studio.ui_components.product_input_ui import ProductInputUI
            from app_utils.aplus_studio.ui_components.workflow_ui import WorkflowUI
            from app_utils.aplus_studio.ui_components.ai_status_ui import AIStatusUI
            
            # 初始化核心组件
            self.components['template_service'] = TemplateService()
            self.components['category_service'] = CategoryService()
            self.components['search_service'] = SearchService(
                self.components['template_service'], 
                self.components['category_service']
            )
            self.components['workflow_service'] = WorkflowService()
            self.components['step_processor_service'] = StepProcessorService()
            self.components['file_service'] = FileService()
            self.components['gemini_service'] = GeminiService()
            self.components['image_compositor_service'] = ImageCompositorService()
            
            # 初始化UI组件
            self.ui_components['template_ui'] = TemplateLibraryUI(
                self.components['template_service'], 
                self.components['search_service'], 
                self.components['category_service']
            )
            self.ui_components['product_ui'] = ProductInputUI(
                self.components['file_service']
            )
            self.ui_components['workflow_ui'] = WorkflowUI(
                self.components['workflow_service'], 
                self.components['step_processor_service']
            )
            self.ui_components['ai_status_ui'] = AIStatusUI(
                self.components['gemini_service'], 
                self.components['image_compositor_service']
            )
            
            self.initialized = True
            return True
            
        except ImportError as e:
            self.initialization_error = f"组件导入失败: {e}"
            return False
        except Exception as e:
            self.initialization_error = f"组件初始化失败: {e}"
            return False
    
    def get_component(self, name: str):
        """获取核心组件"""
        return self.components.get(name)
    
    def get_ui_component(self, name: str):
        """获取UI组件"""
        return self.ui_components.get(name)
    
    def is_ready(self) -> bool:
        """检查组件是否准备就绪"""
        return self.initialized and self.initialization_error is None

# 路由管理器
class RouteManager:
    """路由管理器，负责处理不同界面模式的路由"""
    
    def __init__(self, component_manager: ComponentManager, state_manager: APlusStudioState):
        self.component_manager = component_manager
        self.state_manager = state_manager
    
    def render_workflow_mode(self):
        """渲染工作流模式界面"""
        # 使用容器确保内容只渲染一次
        with st.container():
            # 添加调试信息
            if st.session_state.get('aplus_debug_mode', False):
                st.write("🔍 调试: 渲染工作流模式标题")
            
            st.subheader("🔄 A+页面制作工作流")
            
            # 显示进度指示和帮助提示
            # self._show_workflow_guidance()  # 暂时注释掉，测试是否有重复标题
            
            workflow_ui = self.component_manager.get_ui_component('workflow_ui')
            if not workflow_ui:
                self.state_manager.set_error(
                    "工作流UI组件未初始化", 
                    ["检查组件导入", "重新加载页面", "联系技术支持"]
                )
                return
            
            # 使用性能优化器测量渲染时间
            performance_optimizer = st.session_state.get('aplus_performance_optimizer')
            
            if performance_optimizer:
                @performance_optimizer.measure_operation_time("workflow_render")
                def render_workflow():
                    return workflow_ui.render()
            else:
                def render_workflow():
                    return workflow_ui.render()
            
            # 渲染工作流界面
            with st.spinner("正在加载工作流界面..."):
                workflow_result = render_workflow()
            
            # 处理工作流结果
            if workflow_result:
                self._handle_workflow_result(workflow_result)
            
            # 显示性能指标（开发模式）
            if st.session_state.get('aplus_debug_mode', False) and performance_optimizer:
                performance_optimizer.show_performance_metrics()
    
    def render_classic_mode(self):
        """渲染经典三列布局模式"""
        st.subheader("🎨 AI 驱动的模板定制工作流")
        
        # 显示使用提示
        feedback_system = st.session_state.get('aplus_feedback_system')
        if feedback_system:
            feedback_system.show_tips_and_hints([
                "选择与您产品风格匹配的模板",
                "填写详细的产品信息以获得更好的AI生成效果",
                "可以随时修改产品信息重新生成",
                "生成完成后可下载多种格式的文件"
            ])
        
        # 优化移动端布局
        layout_manager = st.session_state.get('aplus_layout_manager')
        if layout_manager:
            layout_manager.optimize_mobile_layout()
        
        # 使用响应式列布局
        if layout_manager:
            col_template, col_product, col_result = layout_manager.create_responsive_columns(
                desktop_ratios=[1, 1, 1.2],
                mobile_ratios=[1]  # 移动端单列布局
            )
        else:
            col_template, col_product, col_result = st.columns([1, 1, 1.2], gap="medium")
        
        with col_template:
            st.markdown("### 1️⃣ 智能模板选择")
            self._render_template_selection()
        
        with col_product:
            st.markdown("### 2️⃣ 产品信息")
            self._render_product_input()
        
        with col_result:
            st.markdown("### 3️⃣ 生成结果")
            self._render_generation_result()
    

    
    def _handle_workflow_result(self, workflow_result: Dict[str, Any]):
        """处理工作流结果"""
        current_step = workflow_result.get("current_step", 0)
        session_id = workflow_result.get("session_id")
        
        # 更新会话状态
        if session_id:
            st.session_state.aplus_workflow_session_id = session_id
        st.session_state.aplus_current_step = current_step
        
        # 根据当前步骤显示相应的UI组件
        if current_step == 0:
            # 模板选择步骤
            template_ui = self.component_manager.get_ui_component('template_ui')
            if template_ui:
                selected_template_id = template_ui.render()
                if selected_template_id:
                    st.session_state.aplus_selected_template_id = selected_template_id
        
        elif current_step == 1:
            # 产品信息步骤
            product_ui = self.component_manager.get_ui_component('product_ui')
            if product_ui:
                product_data = product_ui.render()
                if product_data:
                    st.session_state.aplus_product_data = product_data
                    # 更新工作流会话中的产品数据
                    self._update_workflow_session_data(session_id, product_data)
        
        elif current_step == 3:
            # AI处理步骤
            self._render_ai_processing_step(session_id)
    
    def _render_generation_result(self):
        """渲染生成结果区域"""
        if st.button("🚀 生成 A+ 页面", type="primary", use_container_width=True):
            selected_template_id = st.session_state.get('aplus_selected_template_id')
            product_data = st.session_state.get('aplus_product_data')
            
            if not selected_template_id or not product_data:
                self.state_manager.set_error("请先选择模板并完善产品信息")
            else:
                self._process_generation_request(selected_template_id, product_data)
    
    def _render_ai_processing_step(self, session_id: str):
        """渲染AI处理步骤"""
        workflow_service = self.component_manager.get_component('workflow_service')
        template_service = self.component_manager.get_component('template_service')
        ai_status_ui = self.component_manager.get_ui_component('ai_status_ui')
        
        if not all([workflow_service, template_service, ai_status_ui]):
            st.error("必要组件未初始化")
            return
        
        session = workflow_service.get_session(session_id)
        if session and session.product_data:
            template = template_service.load_template(session.template_id)
            if template:
                ai_result = ai_status_ui.render(
                    template, 
                    session.product_data, 
                    session.customization_options
                )
                
                if ai_result and ai_result.get("is_completed"):
                    self.state_manager.set_success("✅ A+ 页面生成完成！")
    
    def _process_generation_request(self, template_id: str, product_data: Any):
        """处理生成请求"""
        with st.spinner("AI 正在生成定制化 A+ 页面..."):
            try:
                template_service = self.component_manager.get_component('template_service')
                ai_status_ui = self.component_manager.get_ui_component('ai_status_ui')
                
                if not template_service or not ai_status_ui:
                    raise Exception("必要组件未初始化")
                
                # 加载模板
                template = template_service.load_template(template_id)
                if not template:
                    raise Exception("模板加载失败")
                
                # 使用AI状态UI处理生成
                customization_options = {
                    "color_scheme": "品牌色调",
                    "layout_style": "标准布局",
                    "ai_enhance_text": True,
                    "ai_enhance_layout": True,
                    "ai_background_gen": False
                }
                
                ai_result = ai_status_ui.render_compact(
                    template, 
                    product_data, 
                    customization_options
                )
                
                if ai_result and ai_result.get("is_completed"):
                    self.state_manager.set_success("✅ A+ 页面生成完成！")
                    self._render_download_options()
                else:
                    self.state_manager.set_error("AI处理未完成，请稍后重试")
                    
            except Exception as e:
                self.state_manager.set_error(f"生成失败: {e}")
                st.info("💡 这是演示版本，完整功能需要配置AI服务和模板文件")
    
    def _render_download_options(self):
        """渲染下载选项"""
        st.markdown("### 📥 下载选项")
        col_download1, col_download2, col_download3 = st.columns(3)
        
        with col_download1:
            st.download_button("📥 下载图片包", 
                             data=b"mock_zip_data", 
                             file_name="aplus_images.zip", 
                             mime="application/zip")
        
        with col_download2:
            st.download_button("📄 下载HTML代码", 
                             data="<html>Mock HTML</html>", 
                             file_name="aplus_page.html", 
                             mime="text/html")
        
        with col_download3:
            st.download_button("⚙️ 下载配置文件", 
                             data='{"config": "mock"}', 
                             file_name="aplus_config.json", 
                             mime="application/json")
    
    def _update_workflow_session_data(self, session_id: str, product_data: Any):
        """更新工作流会话数据"""
        if not session_id:
            return
        
        workflow_service = self.component_manager.get_component('workflow_service')
        if workflow_service:
            session = workflow_service.get_session(session_id)
            if session:
                session.product_data = product_data
                workflow_service.update_session(session)
    
    def _show_workflow_guidance(self):
        """显示工作流指引"""
        feedback_system = st.session_state.get('aplus_feedback_system')
        if feedback_system:
            # 显示当前步骤指引
            current_step = st.session_state.get('aplus_current_step', 0)
            
            step_info = {
                0: ("模板选择", "从模板库中选择适合您产品的A+页面模板"),
                1: ("产品信息", "上传产品图片并填写详细的产品信息"),
                2: ("自定义设置", "调整模板样式和AI生成选项"),
                3: ("AI处理", "AI正在智能合成您的A+页面"),
                4: ("完成下载", "查看生成结果并下载所需文件")
            }
            
            if current_step in step_info:
                step_name, step_desc = step_info[current_step]
                guidance_result = feedback_system.show_step_guidance(
                    current_step + 1, 5, step_name, step_desc,
                    completion_criteria=[
                        "确保所有必填信息已完成",
                        "检查预览效果是否满意",
                        "点击下一步继续流程"
                    ]
                )
                
                if guidance_result:
                    self._handle_step_navigation(guidance_result)
    
    def _handle_step_navigation(self, navigation_action: str):
        """处理步骤导航"""
        current_step = st.session_state.get('aplus_current_step', 0)
        
        if navigation_action == "next" and current_step < 4:
            st.session_state.aplus_current_step = current_step + 1
            st.rerun()
        elif navigation_action == "previous" and current_step > 0:
            st.session_state.aplus_current_step = current_step - 1
            st.rerun()
        elif navigation_action == "finish":
            self.state_manager.set_success(
                "工作流已完成！", 
                ["下载生成的文件", "开始新的项目", "分享您的作品"]
            )
    
    def _render_template_selection(self):
        """渲染模板选择区域"""
        template_ui = self.component_manager.get_ui_component('template_ui')
        if template_ui:
            with st.spinner("正在加载模板库..."):
                selected_template_id = template_ui.render_compact()
                
                if selected_template_id:
                    st.session_state.aplus_selected_template_id = selected_template_id
                    
                    # 显示选择成功反馈
                    feedback_system = st.session_state.get('aplus_feedback_system')
                    if feedback_system:
                        feedback_system.show_success_feedback(
                            "模板选择成功！",
                            ["现在可以填写产品信息", "预览模板效果", "开始AI生成"]
                        )
                    
                    # 记录操作历史
                    self.state_manager.add_operation_to_history(
                        "模板选择", f"选择了模板: {selected_template_id}"
                    )
        else:
            self.state_manager.set_error(
                "模板UI组件未初始化",
                ["刷新页面重试", "检查网络连接", "联系技术支持"]
            )
    
    def _render_product_input(self):
        """渲染产品信息输入区域"""
        product_ui = self.component_manager.get_ui_component('product_ui')
        if product_ui:
            product_data = product_ui.render_compact()
            
            if product_data:
                st.session_state.aplus_product_data = product_data
                
                # 显示数据验证反馈
                validation_result = self._validate_product_data(product_data)
                feedback_system = st.session_state.get('aplus_feedback_system')
                
                if validation_result["valid"]:
                    if feedback_system:
                        feedback_system.show_success_feedback(
                            "产品信息完整！",
                            ["可以开始生成A+页面", "检查模板选择", "调整生成选项"]
                        )
                else:
                    if feedback_system:
                        feedback_system.show_warning_feedback(
                            "产品信息不完整",
                            [
                                {
                                    "label": "查看缺失项",
                                    "callback": lambda: st.info(f"缺失: {', '.join(validation_result['missing_fields'])}")
                                }
                            ]
                        )
                
                # 记录操作历史
                self.state_manager.add_operation_to_history(
                    "产品信息输入", "产品信息已更新"
                )
        else:
            self.state_manager.set_error(
                "产品输入UI组件未初始化",
                ["刷新页面重试", "检查组件状态"]
            )
    
    def _validate_product_data(self, product_data: Dict[str, Any]) -> Dict[str, Any]:
        """验证产品数据完整性"""
        required_fields = ["product_name", "product_category", "features"]
        missing_fields = []
        
        for field in required_fields:
            if not product_data.get(field):
                missing_fields.append(field)
        
        return {
            "valid": len(missing_fields) == 0,
            "missing_fields": missing_fields,
            "completeness": (len(required_fields) - len(missing_fields)) / len(required_fields)
        }

# 初始化全局管理器
@st.cache_resource
def get_component_manager():
    """获取组件管理器单例"""
    return ComponentManager()

@st.cache_resource  
def get_state_manager():
    """获取状态管理器单例"""
    return APlusStudioState()

# --- 基础设置 ---
try:
    import auth
except ImportError:
    pass 

st.set_page_config(page_title="A+ Studio", page_icon="🧩", layout="wide")

# 主应用入口
def main():
    """主应用入口函数"""
    # 身份验证
    if 'auth' in sys.modules:
        if not auth.check_password():
            st.stop()

    # 应用标题
    st.title("🧩 A+ 创意工场 (APlus Studio)")
    st.caption("AI 驱动的亚马逊 A+ 页面智能生成工具")

    # 获取管理器实例
    component_manager = get_component_manager()
    state_manager = get_state_manager()
    
    # 显示系统状态消息
    _display_system_messages(state_manager)
    
    # 初始化组件
    if not component_manager.initialize_components():
        _render_fallback_interface(component_manager.initialization_error)
        return
    
    # 创建路由管理器
    route_manager = RouteManager(component_manager, state_manager)
    
    # 界面模式选择
    interface_mode = st.radio(
        "选择界面模式",
        ["工作流模式", "经典模式"],
        index=0,
        horizontal=True,
        help="工作流模式：分步引导式界面；经典模式：传统的三列布局",
        key="aplus_interface_mode"
    )
    
    # 添加系统控制按钮
    _render_system_controls(state_manager)
    
    # 根据选择的模式渲染界面
    try:
        if interface_mode == "工作流模式":
            route_manager.render_workflow_mode()
        elif interface_mode == "经典模式":
            route_manager.render_classic_mode()
    except Exception as e:
        st.error(f"界面渲染失败: {e}")
        st.error(f"错误详情: {traceback.format_exc()}")
        state_manager.set_error(f"界面渲染失败: {e}")

def _display_system_messages(state_manager: APlusStudioState):
    """显示系统状态消息"""
    # 显示错误消息
    if st.session_state.get('aplus_last_error'):
        st.error(st.session_state.aplus_last_error)
        if st.button("清除错误", key="clear_error"):
            state_manager.clear_messages()
            st.rerun()
    
    # 显示成功消息
    if st.session_state.get('aplus_success_message'):
        st.success(st.session_state.aplus_success_message)
        if st.button("清除消息", key="clear_success"):
            state_manager.clear_messages()
            st.rerun()

def _render_system_controls(state_manager: APlusStudioState):
    """渲染系统控制按钮"""
    with st.expander("🔧 系统控制", expanded=False):
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            if st.button("🔄 重置工作流", help="重置所有工作流状态"):
                state_manager.reset_workflow()
                feedback_system = st.session_state.get('aplus_feedback_system')
                if feedback_system:
                    feedback_system.show_success_feedback(
                        "工作流已重置",
                        ["可以开始新的项目", "选择新的模板", "重新输入产品信息"]
                    )
                st.rerun()
        
        with col2:
            if st.button("🧹 清除缓存", help="清除应用缓存"):
                st.cache_resource.clear()
                feedback_system = st.session_state.get('aplus_feedback_system')
                if feedback_system:
                    feedback_system.show_success_feedback(
                        "缓存已清除",
                        ["页面性能已优化", "组件将重新加载", "可能需要重新登录"]
                    )
                st.rerun()
        
        with col3:
            if st.button("📊 系统状态", help="显示系统状态信息"):
                _show_system_status()
        
        with col4:
            if st.button("📈 操作历史", help="查看操作历史记录"):
                _show_operation_history(state_manager)
        
        with col5:
            if st.button("❓ 帮助", help="显示使用帮助"):
                _show_help_info()
        
        # 调试模式开关
        debug_mode = st.checkbox("🐛 调试模式", 
                               value=st.session_state.get('aplus_debug_mode', False),
                               help="启用调试模式显示详细信息")
        st.session_state.aplus_debug_mode = debug_mode

def _show_system_status():
    """显示系统状态信息"""
    component_manager = get_component_manager()
    
    st.info("### 📊 系统状态")
    
    # 组件状态
    st.write("**组件状态:**")
    if component_manager.is_ready():
        st.success("✅ 所有组件已就绪")
        
        # 显示组件列表
        st.write("**已加载的核心组件:**")
        for name in component_manager.components.keys():
            st.write(f"- {name}")
        
        st.write("**已加载的UI组件:**")
        for name in component_manager.ui_components.keys():
            st.write(f"- {name}")
    else:
        st.error(f"❌ 组件初始化失败: {component_manager.initialization_error}")
    
    # 会话状态
    st.write("**会话状态:**")
    st.write(f"- 当前模式: {st.session_state.get('aplus_interface_mode', 'N/A')}")
    st.write(f"- 工作流会话ID: {st.session_state.get('aplus_workflow_session_id', 'N/A')}")
    st.write(f"- 当前步骤: {st.session_state.get('aplus_current_step', 'N/A')}")
    st.write(f"- 选中模板: {st.session_state.get('aplus_selected_template_id', 'N/A')}")
    st.write(f"- 产品数据: {'已设置' if st.session_state.get('aplus_product_data') else '未设置'}")

def _show_operation_history(state_manager: APlusStudioState):
    """显示操作历史"""
    st.info("### 📈 操作历史")
    
    history = st.session_state.get('aplus_operation_history', [])
    
    if history:
        # 显示最近的10条记录
        recent_history = history[-10:]
        
        for i, entry in enumerate(reversed(recent_history)):
            with st.expander(f"{entry['operation']} - {entry['timestamp'][:19]}"):
                st.write(f"**操作:** {entry['operation']}")
                st.write(f"**结果:** {entry['result']}")
                st.write(f"**时间:** {entry['timestamp']}")
        
        # 清除历史按钮
        if st.button("🗑️ 清除历史记录"):
            st.session_state.aplus_operation_history = []
            st.success("操作历史已清除")
            st.rerun()
    else:
        st.write("暂无操作历史记录")

def _show_help_info():
    """显示帮助信息"""
    st.info("### ❓ 使用帮助")
    
    # 使用标签页组织帮助内容
    tab1, tab2, tab3 = st.tabs(["🔄 工作流模式", "🎨 经典模式", "⚡ 快捷操作"])
    
    with tab1:
        st.markdown("""
        **工作流模式使用指南:**
        1. **模板选择** - 从模板库中选择适合的A+页面模板
        2. **产品信息** - 上传产品图片并填写详细信息
        3. **自定义设置** - 调整模板样式和AI生成选项
        4. **AI处理** - 等待AI智能合成您的A+页面
        5. **完成下载** - 查看生成结果并下载所需文件
        
        **提示:**
        - 每个步骤都有完成标准指引
        - 可以随时返回上一步修改
        - 系统会自动保存您的进度
        """)
    
    with tab2:
        st.markdown("""
        **经典模式使用指南:**
        - **左列：智能模板选择**
          - 使用搜索功能快速找到合适模板
          - 支持按类别和节日筛选
          - 查看模板预览和详细信息
        
        - **中列：产品信息输入**
          - 填写产品名称和类别
          - 上传产品图片（支持多张）
          - 输入产品卖点和品牌信息
        
        - **右列：生成和下载**
          - 一键生成A+页面
          - 预览生成结果
          - 下载多种格式文件
        """)
    
    with tab3:
        st.markdown("""
        **快捷操作:**
        - **Ctrl + R** - 刷新页面
        - **Ctrl + Shift + R** - 强制刷新缓存
        - **ESC** - 取消当前操作
        
        **系统控制:**
        - **重置工作流** - 清除所有进度，重新开始
        - **清除缓存** - 解决组件加载问题
        - **系统状态** - 查看当前系统运行状态
        - **操作历史** - 查看最近的操作记录
        - **调试模式** - 显示详细的系统信息
        """)
    
    # 显示键盘快捷键
    feedback_system = st.session_state.get('aplus_feedback_system')
    if feedback_system:
        feedback_system.show_keyboard_shortcuts({
            "Ctrl + R": "刷新页面",
            "Ctrl + Shift + R": "强制刷新缓存",
            "ESC": "取消当前操作",
            "F1": "显示帮助信息"
        })

def _render_fallback_interface(error_message: str):
    """渲染备用界面"""
    st.error(f"系统组件初始化失败: {error_message}")
    st.info("💡 正在使用备用界面模式")
    
    # 显示基础的备用界面
    st.subheader("🎨 基础模板工作流")
    
    col_template, col_product, col_result = st.columns([1, 1, 1.2], gap="medium")
    
    with col_template:
        st.markdown("### 1️⃣ 模板选择")
        template_options = {
            "科技现代风格": "tech_modern",
            "美妆优雅风格": "beauty_elegant", 
            "家居温馨风格": "home_cozy",
            "运动活力风格": "sports_dynamic"
        }
        selected_template = st.selectbox("选择模板", list(template_options.keys()))
        
        # 显示模板预览
        color_map = {
            "tech_modern": "2196F3",
            "beauty_elegant": "E91E63",
            "home_cozy": "FF9800", 
            "sports_dynamic": "4CAF50"
        }
        template_id = template_options[selected_template]
        color = color_map.get(template_id, "4CAF50")
        preview_url = f"https://via.placeholder.com/300x200/{color}/white?text={selected_template.replace(' ', '+')}"
        st.image(preview_url, caption=f"模板预览: {selected_template}")
    
    with col_product:
        st.markdown("### 2️⃣ 产品信息")
        product_name = st.text_input("产品名称", placeholder="例: 无线蓝牙耳机")
        product_category = st.selectbox("产品类别", ["电子产品", "美妆护肤", "家居用品", "运动户外"])
        
        # 产品特点
        features = []
        for i in range(3):
            feature = st.text_input(f"产品特点 {i+1}", key=f"fallback_feature_{i}")
            if feature.strip():
                features.append(feature)
        
        brand_name = st.text_input("品牌名称", placeholder="例: TechPro")
    
    with col_result:
        st.markdown("### 3️⃣ 生成结果")
        
        if st.button("🚀 生成 A+ 页面", type="primary", use_container_width=True):
            if not product_name or not features:
                st.error("请填写产品名称和至少一个特点")
            else:
                with st.spinner("正在生成..."):
                    import time
                    time.sleep(2)
                    
                    st.success("✅ 生成完成！")
                    
                    # 显示模拟结果
                    result_url = f"https://via.placeholder.com/600x400/{color}/white?text=Generated+APlus+Page"
                    st.image(result_url, caption="生成的A+页面预览")
                    
                    # 下载按钮
                    st.download_button(
                        "📥 下载结果",
                        data="Mock generated content",
                        file_name=f"aplus_{product_name.replace(' ', '_')}.html",
                        mime="text/html"
                    )

# 运行主应用
if __name__ == "__main__":
    main()
else:
    main()

