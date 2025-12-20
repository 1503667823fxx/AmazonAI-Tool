"""
工作流界面组件
实现分步工作流界面和进度显示功能
"""

import streamlit as st
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
import time

from ..interfaces import IWorkflowEngine, IStepProcessor
from ..models.core_models import WorkflowSession, WorkflowStatus, ProductData, Template


class WorkflowUI:
    """工作流界面组件"""
    
    def __init__(self, 
                 workflow_engine: IWorkflowEngine,
                 step_processor: IStepProcessor):
        """
        初始化工作流界面
        
        Args:
            workflow_engine: 工作流引擎
            step_processor: 步骤处理器
        """
        self.workflow_engine = workflow_engine
        self.step_processor = step_processor
        
        # 定义工作流步骤
        self.steps = [
            {"name": "选择模板", "description": "选择合适的A+页面模板"},
            {"name": "产品信息", "description": "输入产品详细信息"},
            {"name": "自定义设置", "description": "配置个性化选项"},
            {"name": "AI处理", "description": "AI智能合成处理"},
            {"name": "预览确认", "description": "预览并确认最终结果"}
        ]
    
    def render(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        渲染工作流界面
        
        Args:
            session_id: 工作流会话ID，如果为None则创建新会话
            
        Returns:
            工作流状态信息
        """
        # 不在这里显示标题，由调用方负责显示
        
        # 获取或创建工作流会话
        session = self._get_or_create_session(session_id)
        
        if not session:
            st.error("工作流会话创建失败")
            return {"status": "error"}
        
        # 渲染进度条
        self._render_progress_bar(session)
        
        # 渲染步骤导航
        self._render_step_navigation(session)
        
        # 渲染当前步骤内容
        step_result = self._render_current_step(session)
        
        # 渲染控制按钮
        control_result = self._render_control_buttons(session)
        
        # 处理步骤结果
        if step_result.get("next_step"):
            self._handle_next_step(session)
        elif step_result.get("previous_step"):
            self._handle_previous_step(session)
        
        return {
            "status": "success",
            "session_id": session.session_id,
            "current_step": session.current_step,
            "workflow_status": session.status.value,
            "step_result": step_result
        }
    
    def _get_or_create_session(self, session_id: Optional[str]) -> Optional[WorkflowSession]:
        """获取或创建工作流会话"""
        try:
            if session_id:
                session = self.workflow_engine.get_session(session_id)
                if session:
                    return session
            
            # 创建新会话
            user_id = st.session_state.get('user_id', 'anonymous')
            template_id = st.session_state.get('selected_template_id', 'default')
            
            session = self.workflow_engine.create_session(user_id, template_id)
            st.session_state.workflow_session_id = session.session_id
            
            return session
            
        except Exception as e:
            st.error(f"工作流会话处理失败: {e}")
            return None
    
    def _render_progress_bar(self, session: WorkflowSession):
        """渲染进度条"""
        progress = session.current_step / session.total_steps
        
        # 进度条
        st.progress(progress)
        
        # 进度信息
        col_progress, col_status = st.columns([2, 1])
        
        with col_progress:
            st.caption(f"进度: {session.current_step}/{session.total_steps} 步骤")
        
        with col_status:
            status_color = {
                WorkflowStatus.NOT_STARTED: "🔵",
                WorkflowStatus.IN_PROGRESS: "🟡", 
                WorkflowStatus.PAUSED: "🟠",
                WorkflowStatus.COMPLETED: "🟢",
                WorkflowStatus.FAILED: "🔴"
            }
            
            status_text = {
                WorkflowStatus.NOT_STARTED: "未开始",
                WorkflowStatus.IN_PROGRESS: "进行中",
                WorkflowStatus.PAUSED: "已暂停", 
                WorkflowStatus.COMPLETED: "已完成",
                WorkflowStatus.FAILED: "失败"
            }
            
            st.caption(f"{status_color.get(session.status, '⚪')} {status_text.get(session.status, '未知')}")
    
    def _render_step_navigation(self, session: WorkflowSession):
        """渲染步骤导航"""
        st.markdown("**工作流步骤:**")
        
        cols = st.columns(len(self.steps))
        
        for i, step_info in enumerate(self.steps):
            with cols[i]:
                # 步骤状态
                if i < session.current_step:
                    status_icon = "✅"
                    status_class = "completed"
                elif i == session.current_step:
                    status_icon = "🔄"
                    status_class = "current"
                else:
                    status_icon = "⭕"
                    status_class = "pending"
                
                # 步骤卡片
                with st.container():
                    st.markdown(f"**{i+1}. {step_info['name']}**")
                    st.caption(step_info['description'])
                    st.markdown(f"{status_icon}")
                    
                    # 如果是已完成的步骤，允许点击返回
                    if i < session.current_step:
                        if st.button(f"返回步骤{i+1}", key=f"goto_step_{i}"):
                            self._goto_step(session, i)
    
    def _render_current_step(self, session: WorkflowSession) -> Dict[str, Any]:
        """渲染当前步骤内容"""
        current_step = session.current_step
        
        if current_step >= len(self.steps):
            return self._render_completion_step(session)
        
        step_info = self.steps[current_step]
        
        st.markdown(f"### 步骤 {current_step + 1}: {step_info['name']}")
        st.info(f"📋 {step_info['description']}")
        
        # 根据步骤类型渲染不同内容
        if current_step == 0:  # 选择模板
            return self._render_template_selection_step(session)
        elif current_step == 1:  # 产品信息
            return self._render_product_info_step(session)
        elif current_step == 2:  # 自定义设置
            return self._render_customization_step(session)
        elif current_step == 3:  # AI处理
            return self._render_ai_processing_step(session)
        elif current_step == 4:  # 预览确认
            return self._render_preview_step(session)
        else:
            return {"error": "未知步骤"}
    
    def _render_template_selection_step(self, session: WorkflowSession) -> Dict[str, Any]:
        """渲染模板选择步骤"""
        st.markdown("**请选择一个模板开始制作:**")
        
        # 检查是否已有选中的模板
        selected_template_id = session.step_data.get("template_id") or st.session_state.get('selected_template_id')
        
        if selected_template_id:
            st.success(f"✅ 已选择模板: {selected_template_id}")
            
            # 显示模板信息
            with st.expander("模板详情", expanded=False):
                st.info("模板详细信息将在这里显示")
            
            # 更改模板选项
            if st.button("重新选择模板"):
                session.step_data.pop("template_id", None)
                if 'selected_template_id' in st.session_state:
                    del st.session_state.selected_template_id
                st.rerun()
            
            return {"can_proceed": True, "template_id": selected_template_id}
        else:
            st.warning("请先在模板库中选择一个模板")
            return {"can_proceed": False}
    
    def _render_product_info_step(self, session: WorkflowSession) -> Dict[str, Any]:
        """渲染产品信息步骤"""
        st.markdown("**请完善产品信息:**")
        
        # 检查是否已有产品数据
        if session.product_data:
            st.success("✅ 产品信息已完善")
            
            # 显示产品信息摘要
            with st.expander("产品信息摘要", expanded=False):
                st.write(f"**产品名称:** {session.product_data.name}")
                st.write(f"**品牌:** {session.product_data.brand_name}")
                st.write(f"**类别:** {session.product_data.category}")
                st.write(f"**卖点数量:** {len(session.product_data.features)}")
                st.write(f"**图片数量:** {len(session.product_data.images)}")
            
            # 修改信息选项
            if st.button("修改产品信息"):
                session.product_data = None
                st.rerun()
            
            return {"can_proceed": True}
        else:
            st.warning("请在产品信息区域完善产品详情")
            return {"can_proceed": False}
    
    def _render_customization_step(self, session: WorkflowSession) -> Dict[str, Any]:
        """渲染自定义设置步骤"""
        st.markdown("**个性化定制选项:**")
        
        # 配色方案
        color_scheme = st.selectbox(
            "配色方案",
            ["原始配色", "品牌色调", "暖色调", "冷色调", "黑白简约"],
            index=0
        )
        
        # 布局风格
        layout_style = st.selectbox(
            "布局风格", 
            ["标准布局", "紧凑型", "宽松型", "创意型"],
            index=0
        )
        
        # AI增强选项
        st.markdown("**AI增强选项:**")
        ai_enhance_text = st.checkbox("AI优化文案", value=True)
        ai_enhance_layout = st.checkbox("AI智能排版", value=True)
        ai_background_gen = st.checkbox("AI生成背景元素", value=False)
        
        # 保存自定义选项
        customization_options = {
            "color_scheme": color_scheme,
            "layout_style": layout_style,
            "ai_enhance_text": ai_enhance_text,
            "ai_enhance_layout": ai_enhance_layout,
            "ai_background_gen": ai_background_gen
        }
        
        session.customization_options = customization_options
        
        return {"can_proceed": True, "customization": customization_options}
    
    def _render_ai_processing_step(self, session: WorkflowSession) -> Dict[str, Any]:
        """渲染AI处理步骤"""
        st.markdown("**AI智能处理中...**")
        
        # 检查处理状态
        processing_status = session.step_data.get("ai_processing_status", "not_started")
        
        if processing_status == "not_started":
            if st.button("🚀 开始AI处理", type="primary"):
                session.step_data["ai_processing_status"] = "processing"
                session.step_data["processing_start_time"] = time.time()
                st.rerun()
            
            return {"can_proceed": False}
        
        elif processing_status == "processing":
            # 显示处理进度
            start_time = session.step_data.get("processing_start_time", time.time())
            elapsed_time = time.time() - start_time
            
            # 模拟处理进度
            progress = min(elapsed_time / 10.0, 1.0)  # 假设10秒完成
            
            st.progress(progress)
            st.info(f"⏳ 处理中... {progress*100:.0f}%")
            
            # 处理步骤说明
            if progress < 0.3:
                st.caption("🔍 分析模板结构...")
            elif progress < 0.6:
                st.caption("🎨 处理产品图片...")
            elif progress < 0.9:
                st.caption("✨ AI智能合成...")
            else:
                st.caption("🎯 优化最终效果...")
            
            # 自动刷新
            if progress < 1.0:
                time.sleep(1)
                st.rerun()
            else:
                session.step_data["ai_processing_status"] = "completed"
                st.rerun()
            
            return {"can_proceed": False}
        
        elif processing_status == "completed":
            st.success("✅ AI处理完成！")
            return {"can_proceed": True}
        
        else:
            st.error("❌ 处理失败，请重试")
            if st.button("重新处理"):
                session.step_data["ai_processing_status"] = "not_started"
                st.rerun()
            return {"can_proceed": False}
    
    def _render_preview_step(self, session: WorkflowSession) -> Dict[str, Any]:
        """渲染预览确认步骤"""
        st.markdown("**预览最终结果:**")
        
        # 显示生成结果预览
        st.info("🎨 A+页面预览")
        
        # 模拟显示生成的模块
        modules = [
            "产品展示模块",
            "功能特性模块", 
            "使用场景模块",
            "品牌保证模块"
        ]
        
        for i, module_name in enumerate(modules):
            with st.expander(f"📋 {module_name}", expanded=i==0):
                # 显示模拟的预览图
                preview_url = f"https://via.placeholder.com/800x300/4CAF50/white?text={module_name.replace(' ', '+')}"
                st.image(preview_url, caption=module_name, use_container_width=True)
        
        # 确认选项
        st.markdown("**确认操作:**")
        col_confirm, col_regenerate = st.columns(2)
        
        with col_confirm:
            if st.button("✅ 确认并下载", type="primary"):
                return {"can_proceed": True, "action": "confirm"}
        
        with col_regenerate:
            if st.button("🔄 重新生成"):
                # 返回AI处理步骤
                session.step_data["ai_processing_status"] = "not_started"
                return {"action": "regenerate", "goto_step": 3}
        
        return {"can_proceed": False}
    
    def _render_completion_step(self, session: WorkflowSession) -> Dict[str, Any]:
        """渲染完成步骤"""
        st.success("🎉 A+页面制作完成！")
        
        # 显示完成信息
        st.balloons()
        
        # 下载选项
        st.markdown("**下载选项:**")
        
        col_download1, col_download2, col_download3 = st.columns(3)
        
        with col_download1:
            st.download_button(
                "📥 下载图片包",
                data=b"mock_zip_data",
                file_name="aplus_images.zip",
                mime="application/zip"
            )
        
        with col_download2:
            st.download_button(
                "📄 下载HTML代码",
                data="<html>Mock HTML</html>",
                file_name="aplus_page.html",
                mime="text/html"
            )
        
        with col_download3:
            st.download_button(
                "⚙️ 下载配置文件",
                data='{"config": "mock"}',
                file_name="aplus_config.json",
                mime="application/json"
            )
        
        # 新建工作流选项
        if st.button("🆕 制作新的A+页面"):
            return {"action": "new_workflow"}
        
        return {"completed": True}
    
    def _render_control_buttons(self, session: WorkflowSession) -> Dict[str, Any]:
        """渲染控制按钮"""
        st.markdown("---")
        
        col_prev, col_save, col_next = st.columns([1, 1, 1])
        
        with col_prev:
            if session.current_step > 0:
                if st.button("⬅️ 上一步"):
                    return {"action": "previous"}
        
        with col_save:
            if st.button("💾 保存进度"):
                self.workflow_engine.save_progress(session.session_id)
                st.success("进度已保存")
        
        with col_next:
            # 检查当前步骤是否可以继续
            can_proceed = self._can_proceed_to_next_step(session)
            
            if can_proceed and session.current_step < len(self.steps):
                if st.button("➡️ 下一步", type="primary"):
                    return {"action": "next"}
            elif not can_proceed:
                st.button("➡️ 下一步", disabled=True, help="请完成当前步骤")
        
        return {}
    
    def _can_proceed_to_next_step(self, session: WorkflowSession) -> bool:
        """检查是否可以进入下一步"""
        current_step = session.current_step
        
        if current_step == 0:  # 模板选择
            return bool(session.step_data.get("template_id") or st.session_state.get('selected_template_id'))
        elif current_step == 1:  # 产品信息
            return session.product_data is not None
        elif current_step == 2:  # 自定义设置
            return bool(session.customization_options)
        elif current_step == 3:  # AI处理
            return session.step_data.get("ai_processing_status") == "completed"
        elif current_step == 4:  # 预览确认
            return True
        
        return False
    
    def _handle_next_step(self, session: WorkflowSession):
        """处理下一步操作"""
        try:
            success = self.workflow_engine.next_step(session.session_id)
            if success:
                st.rerun()
            else:
                st.error("进入下一步失败")
        except Exception as e:
            st.error(f"步骤切换失败: {e}")
    
    def _handle_previous_step(self, session: WorkflowSession):
        """处理上一步操作"""
        try:
            success = self.workflow_engine.previous_step(session.session_id)
            if success:
                st.rerun()
            else:
                st.error("返回上一步失败")
        except Exception as e:
            st.error(f"步骤切换失败: {e}")
    
    def _goto_step(self, session: WorkflowSession, step_number: int):
        """跳转到指定步骤"""
        try:
            session.current_step = step_number
            self.workflow_engine.update_session(session)
            st.rerun()
        except Exception as e:
            st.error(f"步骤跳转失败: {e}")
    
    def render_compact(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        渲染紧凑版工作流界面
        
        Returns:
            工作流状态信息
        """
        session = self._get_or_create_session(session_id)
        
        if not session:
            return {"status": "error"}
        
        # 简化的进度显示
        progress = session.current_step / session.total_steps
        st.progress(progress)
        st.caption(f"步骤 {session.current_step + 1}/{session.total_steps}")
        
        # 当前步骤名称
        if session.current_step < len(self.steps):
            step_name = self.steps[session.current_step]["name"]
            st.markdown(f"**当前: {step_name}**")
        
        return {
            "session_id": session.session_id,
            "current_step": session.current_step,
            "status": session.status.value
        }
