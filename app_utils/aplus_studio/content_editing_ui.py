"""
A+ 智能工作流内容编辑确认界面组件

该模块提供内容编辑确认阶段的用户界面，包括生成内容的列表展示、
内容编辑和实时保存功能、素材需求提示和上传等功能。
"""

import streamlit as st
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import json
import time
from datetime import datetime
import logging

from services.aplus_studio.models import ModuleType, ModuleContent, MaterialRequest, Priority
from services.aplus_studio.content_generation_service import ContentGenerationService
from services.aplus_studio.material_requirement_service import MaterialRequirementService
from services.aplus_studio.amazon_compliance_service import AmazonComplianceService
from services.aplus_studio.intelligent_workflow import IntelligentWorkflowController

logger = logging.getLogger(__name__)


@dataclass
class ContentEditState:
    """内容编辑状态"""
    module_type: ModuleType
    original_content: ModuleContent
    edited_content: ModuleContent
    is_modified: bool = False
    last_saved: Optional[datetime] = None
    validation_status: str = "pending"


class EditMode(Enum):
    """编辑模式"""
    VIEW_ONLY = "view_only"      # 仅查看
    EDIT_MODE = "edit_mode"      # 编辑模式
    REVIEW_MODE = "review_mode"  # 审核模式


class ContentEditingUI:
    """内容编辑确认界面组件"""
    
    def __init__(self, workflow_controller: IntelligentWorkflowController):
        self.workflow_controller = workflow_controller
        self.content_service = ContentGenerationService()
        self.material_service = MaterialRequirementService()
        self.compliance_service = AmazonComplianceService()
        
        # 编辑状态管理
        self.edit_states: Dict[ModuleType, ContentEditState] = {}
        self.auto_save_interval = 30  # 30秒自动保存
        
        # 内容类型配置
        self.content_types = {
            "title": {"name": "标题", "max_length": 100, "required": True},
            "subtitle": {"name": "副标题", "max_length": 150, "required": False},
            "description": {"name": "描述", "max_length": 500, "required": True},
            "key_points": {"name": "关键卖点", "max_length": 80, "required": True, "is_list": True},
            "technical_specs": {"name": "技术规格", "max_length": 200, "required": False, "is_list": True},
            "usage_instructions": {"name": "使用说明", "max_length": 300, "required": False},
            "call_to_action": {"name": "行动号召", "max_length": 50, "required": False}
        }
    
    def render_content_editing_interface(self) -> Dict[str, Any]:
        """
        渲染完整的内容编辑确认界面
        
        Returns:
            Dict: 包含用户操作和编辑结果的字典
        """
        st.subheader("📝 内容编辑确认")
        
        # 检查前置条件
        session = self.workflow_controller.state_manager.get_current_session()
        
        if not session or not session.selected_modules:
            st.warning("⚠️ 请先完成模块选择")
            return {"action": None}
        
        # 如果内容还未生成，显示生成界面
        if not session.module_contents or len(session.module_contents) == 0:
            return self._render_content_generation_interface()
        
        # 显示内容编辑界面
        return self._render_content_editing_interface()
    
    def _render_content_generation_interface(self) -> Dict[str, Any]:
        """渲染内容生成界面"""
        
        st.write("**🤖 AI正在为您的模块生成内容...**")
        
        session = self.workflow_controller.state_manager.get_current_session()
        selected_modules = session.selected_modules
        
        # 显示选定模块
        st.write("**选定模块：**")
        
        for i, module_type in enumerate(selected_modules, 1):
            module_name = self._get_module_display_name(module_type)
            st.write(f"{i}. {module_name}")
        
        # 内容生成选项
        with st.expander("⚙️ 内容生成选项", expanded=False):
            col1, col2 = st.columns(2)
            
            with col1:
                content_language = st.selectbox(
                    "内容语言",
                    ["中文", "English", "Español", "Français", "Deutsch", "日本語"],
                    index=0,
                    help="生成内容的主要语言"
                )
                
                content_style = st.selectbox(
                    "内容风格",
                    ["专业正式", "友好亲切", "简洁明了", "详细全面"],
                    index=0,
                    help="内容的表达风格"
                )
            
            with col2:
                target_audience = st.selectbox(
                    "目标受众",
                    ["通用消费者", "专业用户", "年轻群体", "高端客户", "企业用户"],
                    index=0,
                    help="内容针对的主要受众群体"
                )
                
                include_technical_details = st.checkbox(
                    "包含技术细节",
                    value=True,
                    help="在内容中包含详细的技术规格和参数"
                )
        
        # 生成按钮
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            if st.button("🚀 开始生成内容", type="primary", use_container_width=True):
                return {
                    "action": "generate_content",
                    "options": {
                        "language": content_language,
                        "style": content_style,
                        "target_audience": target_audience,
                        "include_technical_details": include_technical_details
                    }
                }
        
        with col2:
            if st.button("📋 使用模板", use_container_width=True):
                return {"action": "use_template"}
        
        with col3:
            if st.button("✍️ 手动编写", use_container_width=True):
                return {"action": "manual_writing"}
        
        return {"action": None}
    
    def _render_content_editing_interface(self) -> Dict[str, Any]:
        """渲染内容编辑界面"""
        
        session = self.workflow_controller.state_manager.get_current_session()
        module_contents = session.module_contents
        
        # 编辑模式选择
        edit_mode = self._render_edit_mode_selection()
        
        # 内容概览
        self._render_content_overview(module_contents)
        
        # 主要编辑区域
        if edit_mode == EditMode.VIEW_ONLY:
            return self._render_view_only_mode(module_contents)
        elif edit_mode == EditMode.EDIT_MODE:
            return self._render_edit_mode(module_contents)
        else:  # REVIEW_MODE
            return self._render_review_mode(module_contents)
    
    def _render_edit_mode_selection(self) -> EditMode:
        """渲染编辑模式选择"""
        
        mode_options = {
            "👀 预览模式": EditMode.VIEW_ONLY,
            "✏️ 编辑模式": EditMode.EDIT_MODE,
            "🔍 审核模式": EditMode.REVIEW_MODE
        }
        
        selected_mode = st.radio(
            "选择模式",
            list(mode_options.keys()),
            horizontal=True,
            help="预览：查看生成内容\n编辑：修改和完善内容\n审核：检查合规性和质量",
            label_visibility="collapsed"
        )
        
        return mode_options[selected_mode]
    
    def _render_content_overview(self, module_contents: Dict[ModuleType, ModuleContent]) -> None:
        """渲染内容概览"""
        
        st.write("**📊 内容概览**")
        
        # 统计信息
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("模块数量", len(module_contents))
        
        with col2:
            total_words = sum(self._count_content_words(content) for content in module_contents.values())
            st.metric("总字数", total_words)
        
        with col3:
            completed_count = sum(1 for content in module_contents.values() if self._is_content_complete(content))
            st.metric("完成度", f"{completed_count}/{len(module_contents)}")
        
        with col4:
            # 合规检查状态
            compliance_issues = sum(1 for content in module_contents.values() if self._has_compliance_issues(content))
            if compliance_issues == 0:
                st.metric("合规状态", "✅ 通过")
            else:
                st.metric("合规状态", f"⚠️ {compliance_issues}个问题")
        
        # 模块状态列表
        with st.expander("📋 模块状态详情", expanded=False):
            for module_type, content in module_contents.items():
                module_name = self._get_module_display_name(module_type)
                
                col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
                
                with col1:
                    st.write(f"**{module_name}**")
                
                with col2:
                    word_count = self._count_content_words(content)
                    st.write(f"{word_count} 字")
                
                with col3:
                    if self._is_content_complete(content):
                        st.success("完整")
                    else:
                        st.warning("待完善")
                
                with col4:
                    if self._has_compliance_issues(content):
                        st.error("需检查")
                    else:
                        st.success("合规")
    
    def _render_view_only_mode(self, module_contents: Dict[ModuleType, ModuleContent]) -> Dict[str, Any]:
        """渲染仅查看模式"""
        
        st.write("**👀 内容预览**")
        
        # 模块选择器
        selected_module = st.selectbox(
            "选择要预览的模块",
            list(module_contents.keys()),
            format_func=lambda x: self._get_module_display_name(x),
            key="preview_module_selector"
        )
        
        if selected_module:
            content = module_contents[selected_module]
            
            # 显示内容预览
            self._render_content_preview(selected_module, content)
            
            # 素材需求显示
            if hasattr(content, 'material_requests') and content.material_requests:
                self._render_material_requirements_preview(content.material_requests)
        
        # 操作按钮
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            if st.button("✏️ 开始编辑", type="primary", use_container_width=True):
                return {"action": "switch_to_edit_mode"}
        
        with col2:
            if st.button("📥 导出内容", use_container_width=True):
                return {"action": "export_content"}
        
        with col3:
            if st.button("🔄 重新生成", use_container_width=True):
                return {"action": "regenerate_content"}
        
        return {"action": None}
    
    def _render_edit_mode(self, module_contents: Dict[ModuleType, ModuleContent]) -> Dict[str, Any]:
        """渲染编辑模式"""
        
        st.write("**✏️ 内容编辑**")
        
        # 模块选择器
        selected_module = st.selectbox(
            "选择要编辑的模块",
            list(module_contents.keys()),
            format_func=lambda x: self._get_module_display_name(x),
            key="edit_module_selector"
        )
        
        if selected_module:
            content = module_contents[selected_module]
            
            # 编辑表单
            edited_content = self._render_content_editor(selected_module, content)
            
            # 实时保存状态
            self._render_save_status(selected_module)
            
            # 素材需求编辑
            if hasattr(content, 'material_requests') and content.material_requests:
                self._render_material_requirements_editor(selected_module, content.material_requests)
            
            # 合规检查
            self._render_compliance_checker(selected_module, edited_content)
            
            return {"action": "content_edited", "module": selected_module, "content": edited_content}
        
        return {"action": None}
    
    def _render_review_mode(self, module_contents: Dict[ModuleType, ModuleContent]) -> Dict[str, Any]:
        """渲染审核模式"""
        
        st.write("**🔍 内容审核**")
        
        # 全局审核统计
        self._render_review_summary(module_contents)
        
        # 逐个模块审核
        for module_type, content in module_contents.items():
            module_name = self._get_module_display_name(module_type)
            
            with st.expander(f"📋 {module_name} 审核", expanded=False):
                self._render_module_review(module_type, content)
        
        # 最终确认
        st.write("**最终确认**")
        
        all_approved = st.checkbox(
            "我已审核所有内容，确认无误",
            value=False,
            help="确认所有模块内容都已审核完成且符合要求"
        )
        
        if all_approved:
            col1, col2, col3 = st.columns([2, 1, 1])
            
            with col1:
                if st.button("✅ 确认并继续", type="primary", use_container_width=True):
                    return {"action": "approve_all_content"}
            
            with col2:
                if st.button("📝 继续编辑", use_container_width=True):
                    return {"action": "continue_editing"}
            
            with col3:
                if st.button("💾 保存草稿", use_container_width=True):
                    return {"action": "save_draft"}
        
        return {"action": None}
    
    def _render_content_preview(self, module_type: ModuleType, content: ModuleContent) -> None:
        """渲染内容预览"""
        
        module_name = self._get_module_display_name(module_type)
        
        st.write(f"**{module_name} 内容预览**")
        
        # 基本信息
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**基本信息**")
            st.write(f"• 模块类型: {module_name}")
            st.write(f"• 语言: {getattr(content, 'language', '中文')}")
            st.write(f"• 生成时间: {getattr(content, 'generation_timestamp', '未知')}")
        
        with col2:
            st.write("**内容统计**")
            word_count = self._count_content_words(content)
            st.write(f"• 总字数: {word_count}")
            st.write(f"• 卖点数量: {len(getattr(content, 'key_points', []))}")
            st.write(f"• 完整度: {'完整' if self._is_content_complete(content) else '待完善'}")
        
        # 内容展示
        if hasattr(content, 'title') and content.title:
            st.write("**标题**")
            st.info(content.title)
        
        if hasattr(content, 'description') and content.description:
            st.write("**描述**")
            st.write(content.description)
        
        if hasattr(content, 'key_points') and content.key_points:
            st.write("**关键卖点**")
            for i, point in enumerate(content.key_points, 1):
                st.write(f"{i}. {point}")
        
        # 其他生成内容
        if hasattr(content, 'generated_text') and content.generated_text:
            st.write("**其他内容**")
            for key, value in content.generated_text.items():
                if value:
                    st.write(f"**{self.content_types.get(key, {}).get('name', key)}:**")
                    if isinstance(value, list):
                        for item in value:
                            st.write(f"• {item}")
                    else:
                        st.write(value)
    
    def _render_content_editor(self, module_type: ModuleType, content: ModuleContent) -> ModuleContent:
        """渲染内容编辑器"""
        
        module_name = self._get_module_display_name(module_type)
        
        st.write(f"**编辑 {module_name} 内容**")
        
        # 创建编辑表单
        with st.form(f"edit_form_{module_type.value}", clear_on_submit=False):
            edited_content = ModuleContent(
                module_type=module_type,
                title="",
                description="",
                key_points=[],
                generated_text={},
                material_requests=getattr(content, 'material_requests', []),
                language=getattr(content, 'language', '中文'),
                generation_timestamp=getattr(content, 'generation_timestamp', datetime.now())
            )
            
            # 标题编辑
            title_config = self.content_types["title"]
            edited_content.title = st.text_input(
                title_config["name"],
                value=getattr(content, 'title', ''),
                max_chars=title_config["max_length"],
                help=f"最多 {title_config['max_length']} 字符"
            )
            
            # 描述编辑
            desc_config = self.content_types["description"]
            edited_content.description = st.text_area(
                desc_config["name"],
                value=getattr(content, 'description', ''),
                max_chars=desc_config["max_length"],
                height=100,
                help=f"最多 {desc_config['max_length']} 字符"
            )
            
            # 关键卖点编辑
            st.write("**关键卖点**")
            
            existing_points = getattr(content, 'key_points', [])
            edited_points = []
            
            # 显示现有卖点的编辑框
            for i in range(max(len(existing_points), 3)):  # 至少显示3个输入框
                point_value = existing_points[i] if i < len(existing_points) else ""
                
                point = st.text_input(
                    f"卖点 {i+1}",
                    value=point_value,
                    max_chars=self.content_types["key_points"]["max_length"],
                    key=f"point_{module_type.value}_{i}",
                    placeholder=f"输入第{i+1}个关键卖点..."
                )
                
                if point.strip():
                    edited_points.append(point.strip())
            
            edited_content.key_points = edited_points
            
            # 其他内容字段编辑
            st.write("**其他内容**")
            
            generated_text = {}
            existing_generated = getattr(content, 'generated_text', {})
            
            # 副标题
            if "subtitle" in self.content_types:
                subtitle_config = self.content_types["subtitle"]
                subtitle = st.text_input(
                    subtitle_config["name"],
                    value=existing_generated.get("subtitle", ""),
                    max_chars=subtitle_config["max_length"],
                    help="可选字段"
                )
                if subtitle:
                    generated_text["subtitle"] = subtitle
            
            # 技术规格
            if "technical_specs" in self.content_types:
                st.write("**技术规格**")
                existing_specs = existing_generated.get("technical_specs", [])
                specs = []
                
                for i in range(max(len(existing_specs), 2)):
                    spec_value = existing_specs[i] if i < len(existing_specs) else ""
                    spec = st.text_input(
                        f"规格 {i+1}",
                        value=spec_value,
                        max_chars=self.content_types["technical_specs"]["max_length"],
                        key=f"spec_{module_type.value}_{i}",
                        placeholder=f"输入技术规格..."
                    )
                    if spec.strip():
                        specs.append(spec.strip())
                
                if specs:
                    generated_text["technical_specs"] = specs
            
            # 使用说明
            if "usage_instructions" in self.content_types:
                usage_config = self.content_types["usage_instructions"]
                usage = st.text_area(
                    usage_config["name"],
                    value=existing_generated.get("usage_instructions", ""),
                    max_chars=usage_config["max_length"],
                    height=80,
                    help="可选字段"
                )
                if usage:
                    generated_text["usage_instructions"] = usage
            
            # 行动号召
            if "call_to_action" in self.content_types:
                cta_config = self.content_types["call_to_action"]
                cta = st.text_input(
                    cta_config["name"],
                    value=existing_generated.get("call_to_action", ""),
                    max_chars=cta_config["max_length"],
                    help="可选字段，如：立即购买、了解更多等"
                )
                if cta:
                    generated_text["call_to_action"] = cta
            
            edited_content.generated_text = generated_text
            
            # 保存按钮
            col1, col2, col3 = st.columns([2, 1, 1])
            
            with col1:
                if st.form_submit_button("💾 保存修改", type="primary", use_container_width=True):
                    self._save_content_edit(module_type, edited_content)
                    st.success("内容已保存")
            
            with col2:
                if st.form_submit_button("🔄 重置", use_container_width=True):
                    st.rerun()
            
            with col3:
                if st.form_submit_button("🔍 预览", use_container_width=True):
                    self._show_content_preview(module_type, edited_content)
        
        return edited_content
    
    def _render_material_requirements_preview(self, material_requests: List[MaterialRequest]) -> None:
        """渲染素材需求预览"""
        
        if not material_requests:
            return
        
        st.write("**📎 素材需求**")
        
        for i, request in enumerate(material_requests, 1):
            with st.expander(f"素材需求 {i}: {request.description}", expanded=False):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write("**需求信息**")
                    st.write(f"• 类型: {request.material_type.value}")
                    st.write(f"• 重要性: {request.importance.value}")
                    st.write(f"• 描述: {request.description}")
                
                with col2:
                    st.write("**帮助信息**")
                    if request.example:
                        st.write(f"• 示例: {request.example}")
                    if request.help_text:
                        st.write(f"• 说明: {request.help_text}")
    
    def _render_material_requirements_editor(self, module_type: ModuleType, 
                                           material_requests: List[MaterialRequest]) -> None:
        """渲染素材需求编辑器"""
        
        if not material_requests:
            return
        
        st.write("**📎 素材需求管理**")
        
        for i, request in enumerate(material_requests):
            with st.expander(f"素材 {i+1}: {request.description}", expanded=False):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write("**需求详情**")
                    st.write(f"类型: {request.material_type.value}")
                    st.write(f"重要性: {request.importance.value}")
                    st.write(request.description)
                    
                    if request.help_text:
                        st.info(request.help_text)
                
                with col2:
                    st.write("**素材上传**")
                    
                    if request.material_type.value == "IMAGE":
                        uploaded_file = st.file_uploader(
                            "上传图片",
                            type=["jpg", "jpeg", "png", "webp"],
                            key=f"material_{module_type.value}_{i}_image"
                        )
                        
                        if uploaded_file:
                            st.image(uploaded_file, width=200)
                            st.success("图片已上传")
                    
                    elif request.material_type.value == "TEXT":
                        text_input = st.text_area(
                            "输入文本内容",
                            placeholder="请输入相关文本内容...",
                            key=f"material_{module_type.value}_{i}_text"
                        )
                        
                        if text_input:
                            st.success("文本已输入")
                    
                    elif request.material_type.value == "DOCUMENT":
                        uploaded_doc = st.file_uploader(
                            "上传文档",
                            type=["pdf", "doc", "docx", "txt"],
                            key=f"material_{module_type.value}_{i}_doc"
                        )
                        
                        if uploaded_doc:
                            st.success("文档已上传")
                    
                    # 跳过选项
                    skip_material = st.checkbox(
                        "跳过此素材",
                        key=f"skip_material_{module_type.value}_{i}",
                        help="如果暂时无法提供此素材，可以选择跳过"
                    )
                    
                    if skip_material:
                        st.warning("此素材将被跳过，可能影响最终效果")
    
    def _render_compliance_checker(self, module_type: ModuleType, content: ModuleContent) -> None:
        """渲染合规检查器"""
        
        st.write("**🔍 亚马逊合规检查**")
        
        # 执行合规检查
        compliance_result = self.compliance_service.check_content_compliance(content.title + " " + content.description)
        
        if compliance_result.is_compliant:
            st.success("✅ 内容符合亚马逊政策要求")
        else:
            st.error("❌ 发现合规问题，需要修改")
            
            # 显示具体问题
            for issue in compliance_result.flagged_issues:
                with st.expander(f"⚠️ {issue.issue_type} 问题", expanded=True):
                    st.write(f"**问题文本:** {issue.flagged_text}")
                    st.write(f"**严重程度:** {issue.severity}")
                    st.write(f"**说明:** {issue.explanation}")
                    
                    if issue.suggested_alternatives:
                        st.write("**建议替换:**")
                        for alt in issue.suggested_alternatives:
                            if st.button(f"使用: {alt}", key=f"alt_{module_type.value}_{issue.flagged_text}_{alt}"):
                                self._apply_compliance_fix(module_type, issue.flagged_text, alt)
        
        # 合规评分
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("合规评分", f"{compliance_result.compliance_score:.0%}")
        
        with col2:
            st.metric("问题数量", len(compliance_result.flagged_issues))
        
        with col3:
            if compliance_result.flagged_issues:
                high_severity = sum(1 for issue in compliance_result.flagged_issues if issue.severity == "HIGH")
                st.metric("高风险问题", high_severity)
    
    def _render_save_status(self, module_type: ModuleType) -> None:
        """渲染保存状态"""
        
        edit_state = self.edit_states.get(module_type)
        
        if edit_state:
            col1, col2, col3 = st.columns([2, 1, 1])
            
            with col1:
                if edit_state.is_modified:
                    st.warning("⚠️ 有未保存的修改")
                else:
                    st.success("✅ 所有修改已保存")
            
            with col2:
                if edit_state.last_saved:
                    st.caption(f"上次保存: {edit_state.last_saved.strftime('%H:%M:%S')}")
            
            with col3:
                if st.button("💾 立即保存", key=f"save_{module_type.value}"):
                    self._save_content_edit(module_type, edit_state.edited_content)
    
    def _render_review_summary(self, module_contents: Dict[ModuleType, ModuleContent]) -> None:
        """渲染审核摘要"""
        
        st.write("**📊 审核摘要**")
        
        # 统计信息
        total_modules = len(module_contents)
        complete_modules = sum(1 for content in module_contents.values() if self._is_content_complete(content))
        compliant_modules = sum(1 for content in module_contents.values() if not self._has_compliance_issues(content))
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("总模块数", total_modules)
        
        with col2:
            completion_rate = (complete_modules / total_modules) * 100 if total_modules > 0 else 0
            st.metric("完成率", f"{completion_rate:.0f}%")
        
        with col3:
            compliance_rate = (compliant_modules / total_modules) * 100 if total_modules > 0 else 0
            st.metric("合规率", f"{compliance_rate:.0f}%")
        
        with col4:
            if complete_modules == total_modules and compliant_modules == total_modules:
                st.success("✅ 准备就绪")
            else:
                st.warning("⚠️ 需要完善")
    
    def _render_module_review(self, module_type: ModuleType, content: ModuleContent) -> None:
        """渲染单个模块审核"""
        
        module_name = self._get_module_display_name(module_type)
        
        # 内容完整性检查
        is_complete = self._is_content_complete(content)
        has_compliance_issues = self._has_compliance_issues(content)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**内容检查**")
            
            # 必填字段检查
            required_fields = ["title", "description", "key_points"]
            for field in required_fields:
                field_value = getattr(content, field, None)
                if field_value and (not isinstance(field_value, list) or len(field_value) > 0):
                    st.success(f"✅ {self.content_types.get(field, {}).get('name', field)}")
                else:
                    st.error(f"❌ {self.content_types.get(field, {}).get('name', field)} 缺失")
            
            # 字数统计
            word_count = self._count_content_words(content)
            if word_count >= 50:
                st.success(f"✅ 字数充足 ({word_count} 字)")
            else:
                st.warning(f"⚠️ 字数较少 ({word_count} 字)")
        
        with col2:
            st.write("**合规检查**")
            
            if not has_compliance_issues:
                st.success("✅ 合规检查通过")
            else:
                st.error("❌ 存在合规问题")
                
                # 显示具体问题
                compliance_result = self.compliance_service.check_content_compliance(
                    content.title + " " + content.description
                )
                
                for issue in compliance_result.flagged_issues[:3]:  # 显示前3个问题
                    st.write(f"• {issue.issue_type}: {issue.flagged_text}")
        
        # 审核操作
        col1, col2, col3 = st.columns(3)
        
        with col1:
            approved = st.checkbox(
                "审核通过",
                key=f"approve_{module_type.value}",
                disabled=not is_complete or has_compliance_issues
            )
        
        with col2:
            if st.button("编辑", key=f"edit_from_review_{module_type.value}"):
                st.session_state[f"edit_module_{module_type.value}"] = True
        
        with col3:
            if st.button("预览", key=f"preview_from_review_{module_type.value}"):
                self._show_content_preview(module_type, content)
    
    def _get_module_display_name(self, module_type: ModuleType) -> str:
        """获取模块显示名称"""
        
        display_names = {
            ModuleType.PRODUCT_OVERVIEW: "🎯 产品概览",
            ModuleType.FEATURE_ANALYSIS: "🔍 功能解析",
            ModuleType.SPECIFICATION_COMPARISON: "📊 规格对比",
            ModuleType.USAGE_SCENARIOS: "🏠 使用场景",
            ModuleType.PROBLEM_SOLUTION: "💡 问题解决",
            ModuleType.MATERIAL_CRAFTSMANSHIP: "✨ 材质工艺",
            ModuleType.INSTALLATION_GUIDE: "🔧 安装指南",
            ModuleType.SIZE_COMPATIBILITY: "📐 尺寸兼容",
            ModuleType.PACKAGE_CONTENTS: "📦 包装内容",
            ModuleType.QUALITY_ASSURANCE: "🏆 品质保证",
            ModuleType.CUSTOMER_REVIEWS: "⭐ 客户评价",
            ModuleType.MAINTENANCE_CARE: "🧽 维护保养"
        }
        
        return display_names.get(module_type, module_type.value)
    
    def _count_content_words(self, content: ModuleContent) -> int:
        """统计内容字数"""
        
        total_words = 0
        
        # 标题和描述
        if hasattr(content, 'title') and content.title:
            total_words += len(content.title)
        
        if hasattr(content, 'description') and content.description:
            total_words += len(content.description)
        
        # 关键卖点
        if hasattr(content, 'key_points') and content.key_points:
            total_words += sum(len(point) for point in content.key_points)
        
        # 其他生成内容
        if hasattr(content, 'generated_text') and content.generated_text:
            for value in content.generated_text.values():
                if isinstance(value, str):
                    total_words += len(value)
                elif isinstance(value, list):
                    total_words += sum(len(str(item)) for item in value)
        
        return total_words
    
    def _is_content_complete(self, content: ModuleContent) -> bool:
        """检查内容是否完整"""
        
        # 检查必填字段
        if not hasattr(content, 'title') or not content.title:
            return False
        
        if not hasattr(content, 'description') or not content.description:
            return False
        
        if not hasattr(content, 'key_points') or not content.key_points or len(content.key_points) == 0:
            return False
        
        # 检查最小字数要求
        word_count = self._count_content_words(content)
        if word_count < 50:
            return False
        
        return True
    
    def _has_compliance_issues(self, content: ModuleContent) -> bool:
        """检查是否有合规问题"""
        
        try:
            # 组合所有文本内容进行检查
            text_to_check = ""
            
            if hasattr(content, 'title') and content.title:
                text_to_check += content.title + " "
            
            if hasattr(content, 'description') and content.description:
                text_to_check += content.description + " "
            
            if hasattr(content, 'key_points') and content.key_points:
                text_to_check += " ".join(content.key_points)
            
            if not text_to_check.strip():
                return False
            
            # 执行合规检查
            compliance_result = self.compliance_service.check_content_compliance(text_to_check)
            
            return not compliance_result.is_compliant
            
        except Exception as e:
            logger.error(f"Compliance check failed: {str(e)}")
            return False
    
    def _save_content_edit(self, module_type: ModuleType, content: ModuleContent) -> None:
        """保存内容编辑"""
        
        try:
            # 更新会话中的内容
            session = self.workflow_controller.state_manager.get_current_session()
            if session:
                session.module_contents[module_type] = content
                self.workflow_controller.state_manager._save_session(session)
            
            # 更新编辑状态
            if module_type in self.edit_states:
                self.edit_states[module_type].edited_content = content
                self.edit_states[module_type].is_modified = False
                self.edit_states[module_type].last_saved = datetime.now()
            else:
                self.edit_states[module_type] = ContentEditState(
                    module_type=module_type,
                    original_content=content,
                    edited_content=content,
                    is_modified=False,
                    last_saved=datetime.now()
                )
            
            logger.info(f"Content saved for module {module_type.value}")
            
        except Exception as e:
            logger.error(f"Failed to save content edit: {str(e)}")
            st.error("保存失败，请重试")
    
    def _show_content_preview(self, module_type: ModuleType, content: ModuleContent) -> None:
        """显示内容预览"""
        
        # 在实际实现中，这可能会打开一个模态框或新页面
        # 这里我们使用session state来标记显示预览
        st.session_state[f"show_preview_{module_type.value}"] = True
        st.session_state[f"preview_content_{module_type.value}"] = content
    
    def _apply_compliance_fix(self, module_type: ModuleType, original_text: str, replacement: str) -> None:
        """应用合规修复"""
        
        try:
            session = self.workflow_controller.state_manager.get_current_session()
            if session and module_type in session.module_contents:
                content = session.module_contents[module_type]
                
                # 替换标题中的文本
                if hasattr(content, 'title') and original_text in content.title:
                    content.title = content.title.replace(original_text, replacement)
                
                # 替换描述中的文本
                if hasattr(content, 'description') and original_text in content.description:
                    content.description = content.description.replace(original_text, replacement)
                
                # 替换关键卖点中的文本
                if hasattr(content, 'key_points') and content.key_points:
                    for i, point in enumerate(content.key_points):
                        if original_text in point:
                            content.key_points[i] = point.replace(original_text, replacement)
                
                # 保存修改
                self._save_content_edit(module_type, content)
                st.success(f"已将 '{original_text}' 替换为 '{replacement}'")
                st.rerun()
                
        except Exception as e:
            logger.error(f"Failed to apply compliance fix: {str(e)}")
            st.error("应用修复失败")
    
    def get_content_editing_summary(self) -> Dict[str, Any]:
        """获取内容编辑摘要"""
        
        session = self.workflow_controller.state_manager.get_current_session()
        
        if not session or not session.module_contents:
            return {"has_content": False}
        
        module_contents = session.module_contents
        
        total_modules = len(module_contents)
        complete_modules = sum(1 for content in module_contents.values() if self._is_content_complete(content))
        compliant_modules = sum(1 for content in module_contents.values() if not self._has_compliance_issues(content))
        total_words = sum(self._count_content_words(content) for content in module_contents.values())
        
        return {
            "has_content": True,
            "total_modules": total_modules,
            "complete_modules": complete_modules,
            "compliant_modules": compliant_modules,
            "completion_rate": (complete_modules / total_modules) * 100 if total_modules > 0 else 0,
            "compliance_rate": (compliant_modules / total_modules) * 100 if total_modules > 0 else 0,
            "total_words": total_words,
            "ready_for_generation": complete_modules == total_modules and compliant_modules == total_modules
        }
    
    def auto_save_content(self) -> None:
        """自动保存内容"""
        
        try:
            for module_type, edit_state in self.edit_states.items():
                if edit_state.is_modified:
                    self._save_content_edit(module_type, edit_state.edited_content)
                    logger.info(f"Auto-saved content for module {module_type.value}")
        
        except Exception as e:
            logger.error(f"Auto-save failed: {str(e)}")
    
    def export_content_data(self) -> Optional[Dict[str, Any]]:
        """导出内容数据"""
        
        try:
            session = self.workflow_controller.state_manager.get_current_session()
            
            if not session or not session.module_contents:
                return None
            
            export_data = {
                "export_timestamp": datetime.now().isoformat(),
                "session_id": session.session_id,
                "modules": {}
            }
            
            for module_type, content in session.module_contents.items():
                export_data["modules"][module_type.value] = {
                    "title": getattr(content, 'title', ''),
                    "description": getattr(content, 'description', ''),
                    "key_points": getattr(content, 'key_points', []),
                    "generated_text": getattr(content, 'generated_text', {}),
                    "language": getattr(content, 'language', '中文'),
                    "word_count": self._count_content_words(content),
                    "is_complete": self._is_content_complete(content),
                    "is_compliant": not self._has_compliance_issues(content)
                }
            
            return export_data
            
        except Exception as e:
            logger.error(f"Failed to export content data: {str(e)}")
            return None


# 全局实例，便于访问
def create_content_editing_ui(workflow_controller: IntelligentWorkflowController) -> ContentEditingUI:
    """创建内容编辑UI实例"""
    return ContentEditingUI(workflow_controller)