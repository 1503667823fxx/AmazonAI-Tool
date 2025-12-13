"""
Enhanced Model Selector Component
Provides intelligent model selection with context preservation and validation
"""

import streamlit as st
from typing import Dict, List, Optional, Tuple
from ..models import ConversationState
from ..enhanced_state_manager import state_manager


class ModelSelector:
    """Intelligent model selection interface with enhanced capabilities"""
    
    def __init__(self):
        self.model_map = {
            "⚡ Gemini Flash (快速)": "models/gemini-flash-latest",
            "🎨 Gemini 3 图像 (图像生成)": "models/gemini-3-pro-image-preview", 
            "🧠 Gemini 3 Pro (推理)": "models/gemini-3-pro-preview",
        }
        
        self.model_capabilities = {
            "models/gemini-flash-latest": {
                "supports_vision": True,
                "supports_image_gen": False,
                "max_tokens": 8192,
                "speed": "fast",
                "description": "快速高效的通用对话模型"
            },
            "models/gemini-3-pro-image-preview": {
                "supports_vision": True,
                "supports_image_gen": True,
                "max_tokens": 8192,
                "speed": "medium",
                "description": "具备图像生成能力的高级模型"
            },
            "models/gemini-3-pro-preview": {
                "supports_vision": True,
                "supports_image_gen": False,
                "max_tokens": 32768,
                "speed": "slow",
                "description": "最强大的复杂推理任务模型"
            }
        }
    
    def render_model_selector(self) -> Tuple[str, bool]:
        """
        Render the enhanced model selection interface
        
        Returns:
            Tuple of (selected_model_id, is_image_mode)
        """
        
        # Get current state
        state = state_manager.get_state()
        current_model = state.current_model
        
        # Find current selection in model map
        current_label = None
        for label, model_id in self.model_map.items():
            if model_id == current_model:
                current_label = label
                break
        
        # If current model not in map, add it
        if current_label is None:
            custom_label = f"🔧 Custom ({current_model})"
            self.model_map[custom_label] = current_model
            current_label = custom_label
        
        # Enhanced model selection header with status
        col1, col2 = st.columns([3, 1])
        with col1:
            st.subheader("🤖 AI 模型选择")
        with col2:
            # Show current model status
            caps = self.model_capabilities.get(current_model, {})
            if caps.get('supports_image_gen'):
                st.success("🎨 图像模式")
            else:
                st.info("💬 对话模式")
        
        # Enhanced model selector with better UX
        selected_label = st.selectbox(
            "选择 AI 模型",
            list(self.model_map.keys()),
            index=list(self.model_map.keys()).index(current_label) if current_label else 0,
            key="enhanced_model_selector",
            help="选择最适合您任务需求的 AI 模型"
        )
        
        selected_model_id = self.model_map[selected_label]
        
        # Handle model switching with enhanced feedback
        if selected_model_id != current_model:
            self._handle_enhanced_model_switch(current_model, selected_model_id)
        
        # Enhanced model information display
        self._render_enhanced_model_info(selected_model_id)
        
        # Show model comparison if multiple models available
        if len(self.model_map) > 1:
            with st.expander("📊 Compare Models", expanded=False):
                self._render_model_comparison_table()
        
        # Determine if this is image generation mode
        is_image_mode = self._is_image_generation_mode(selected_model_id)
        
        return selected_model_id, is_image_mode
    
    def _handle_enhanced_model_switch(self, old_model: str, new_model: str) -> None:
        """Handle model switching with enhanced context preservation and feedback"""
        
        # Check if context preservation is needed
        state = state_manager.get_state()
        
        if len(state.messages) > 0:
            # Show enhanced context preservation info
            old_caps = self.model_capabilities.get(old_model, {})
            new_caps = self.model_capabilities.get(new_model, {})
            
            # Check compatibility
            compatibility_issues = self._check_model_compatibility(old_caps, new_caps)
            
            if compatibility_issues:
                with st.expander("⚠️ Model Switch Impact Analysis", expanded=True):
                    st.warning("**Context Preservation Notice**")
                    st.write("Switching models may affect your conversation. Here's what will change:")
                    
                    for issue in compatibility_issues:
                        st.write(f"• {issue}")
                    
                    # Show what will be preserved
                    st.info("**What will be preserved:**")
                    st.write("• All conversation messages and history")
                    st.write("• Current conversation context")
                    if not new_caps.get('supports_image_gen', False):
                        st.write("• System prompt settings")
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        if st.button("✅ Continue Switch", type="primary"):
                            self._perform_model_switch(old_model, new_model)
                            st.success(f"Successfully switched to {self._get_model_display_name(new_model)}")
                            st.rerun()
                    with col2:
                        if st.button("❌ Cancel"):
                            st.rerun()
                    with col3:
                        if st.button("📊 Compare Models"):
                            st.session_state.show_model_comparison = True
                            st.rerun()
                    return
            else:
                # No compatibility issues, show simple confirmation
                st.info(f"Switching from {self._get_model_display_name(old_model)} to {self._get_model_display_name(new_model)}")
        
        # Proceed with model switch
        self._perform_model_switch(old_model, new_model)
        st.success(f"Model updated to {self._get_model_display_name(new_model)}")
    
    def _perform_model_switch(self, old_model: str, new_model: str) -> None:
        """Perform the actual model switch with proper state management"""
        
        # Update model in state
        state_manager.update_model(new_model)
        
        # Log the switch for analytics (if needed)
        state = state_manager.get_state()
        
        # Update UI settings if needed based on new model capabilities
        new_caps = self.model_capabilities.get(new_model, {})
        if new_caps.get('supports_image_gen'):
            # Switching to image generation mode
            ui_settings = state.ui_settings
            ui_settings.enable_streaming = False  # Image gen doesn't use streaming
            state_manager.update_ui_settings(ui_settings)
    
    def _get_model_display_name(self, model_id: str) -> str:
        """Get user-friendly display name for a model"""
        for label, mid in self.model_map.items():
            if mid == model_id:
                return label
        return model_id
    
    def _check_model_compatibility(self, old_caps: Dict, new_caps: Dict) -> List[str]:
        """Check compatibility between old and new model"""
        
        issues = []
        
        # Check image generation capability
        if old_caps.get("supports_image_gen") and not new_caps.get("supports_image_gen"):
            issues.append("New model doesn't support image generation")
        
        # Check token limits
        old_tokens = old_caps.get("max_tokens", 0)
        new_tokens = new_caps.get("max_tokens", 0)
        if new_tokens < old_tokens:
            issues.append(f"New model has lower token limit ({new_tokens} vs {old_tokens})")
        
        # Check vision support
        if old_caps.get("supports_vision") and not new_caps.get("supports_vision"):
            issues.append("New model doesn't support vision/image input")
        
        return issues
    
    def _render_enhanced_model_info(self, model_id: str) -> None:
        """Render enhanced information about the selected model"""
        
        caps = self.model_capabilities.get(model_id, {})
        
        if caps:
            # Always show key model info in a compact format
            col1, col2, col3 = st.columns(3)
            
            with col1:
                speed = caps.get('speed', 'unknown')
                speed_map = {"fast": "快速", "medium": "中等", "slow": "较慢"}
                speed_text = speed_map.get(speed, "未知")
                speed_color = {"fast": "🟢", "medium": "🟡", "slow": "🔴"}.get(speed, "⚪")
                st.metric("速度", f"{speed_color} {speed_text}")
            
            with col2:
                tokens = caps.get('max_tokens', 0)
                st.metric("最大令牌", f"{tokens:,}")
            
            with col3:
                capabilities = []
                if caps.get('supports_vision'):
                    capabilities.append("👁️ 视觉")
                if caps.get('supports_image_gen'):
                    capabilities.append("🎨 图像生成")
                
                cap_text = " • ".join(capabilities) if capabilities else "💬 纯文本"
                st.metric("功能", cap_text)
            
            # Detailed info in expandable section
            with st.expander("📋 Detailed Model Information", expanded=False):
                st.write(f"**Description:** {caps.get('description', 'No description available')}")
                
                # Feature matrix
                st.write("**Feature Support:**")
                features = [
                    ("Text Conversations", "✅", "All models support text-based conversations"),
                    ("Vision/Image Input", "✅" if caps.get('supports_vision') else "❌", 
                     "Can analyze and understand images" if caps.get('supports_vision') else "Text-only input"),
                    ("Image Generation", "✅" if caps.get('supports_image_gen') else "❌",
                     "Can create and generate images" if caps.get('supports_image_gen') else "Cannot generate images"),
                    ("Streaming Responses", "✅" if not caps.get('supports_image_gen') else "❌",
                     "Real-time response streaming" if not caps.get('supports_image_gen') else "Batch processing for images")
                ]
                
                for feature, status, description in features:
                    col_a, col_b, col_c = st.columns([2, 1, 3])
                    with col_a:
                        st.write(f"**{feature}**")
                    with col_b:
                        st.write(status)
                    with col_c:
                        st.write(f"*{description}*")
                
                # Performance characteristics
                st.write("**Performance Characteristics:**")
                perf_data = {
                    "Response Speed": caps.get('speed', 'Unknown').title(),
                    "Token Limit": f"{caps.get('max_tokens', 'Unknown'):,}",
                    "Best Use Cases": self._get_use_cases(caps)
                }
                
                for key, value in perf_data.items():
                    st.write(f"• **{key}:** {value}")
    
    def _get_use_cases(self, capabilities: Dict) -> str:
        """Get recommended use cases for a model based on its capabilities"""
        
        use_cases = []
        
        if capabilities.get('supports_image_gen'):
            use_cases.extend(["Product image creation", "Visual content generation", "Creative design"])
        
        if capabilities.get('supports_vision'):
            use_cases.extend(["Image analysis", "Visual content review", "Product photo optimization"])
        
        speed = capabilities.get('speed', '').lower()
        if speed == 'fast':
            use_cases.extend(["Quick questions", "Real-time chat", "Rapid prototyping"])
        elif speed == 'slow':
            use_cases.extend(["Complex analysis", "Detailed reasoning", "In-depth research"])
        
        tokens = capabilities.get('max_tokens', 0)
        if tokens > 20000:
            use_cases.extend(["Long document analysis", "Detailed content creation"])
        
        return ", ".join(use_cases[:4]) if use_cases else "General purpose conversations"
    
    def _is_image_generation_mode(self, model_id: str) -> bool:
        """Check if the model supports image generation"""
        
        caps = self.model_capabilities.get(model_id, {})
        return caps.get('supports_image_gen', False)
    
    def render_system_prompt_editor(self, model_id: str) -> None:
        """Public method to render system prompt editor"""
        self._render_enhanced_system_prompt_editor(model_id)
    
    def render_model_comparison(self) -> None:
        """Public method to render model comparison"""
        if len(self.model_map) > 1:
            with st.expander("📊 Compare Models", expanded=False):
                self._render_model_comparison_table()
    
    def _render_enhanced_system_prompt_editor(self, model_id: str) -> None:
        """Render enhanced system prompt editor with validation and presets"""
        
        if self._is_image_generation_mode(model_id):
            return  # Don't show system prompt for image generation models
        
        st.subheader("🎭 系统角色与指令")
        
        state = state_manager.get_state()
        current_prompt = state.system_prompt
        
        # Preset prompts for quick selection
        col1, col2 = st.columns([3, 1])
        
        with col2:
            preset_prompts = {
                "默认助手": "你是一个专为亚马逊电商卖家服务的AI助手。",
                "电商专家": "你是亚马逊电商专家，专精于产品listing、SEO优化和卖家策略。请提供详细、可操作的建议。",
                "创意文案": "你是专门为电商撰写引人注目的产品描述和营销内容的创意文案专家。",
                "数据分析师": "你是数据分析专家，帮助解读业务指标、销售数据和电商业务的市场趋势。",
                "客服专家": "你是客户服务专家，帮助创建专业、有同理心的回复并有效解决客户问题。",
                "自定义": ""
            }
            
            selected_preset = st.selectbox(
                "快速预设",
                list(preset_prompts.keys()),
                key="system_prompt_presets",
                help="选择一个预设或选择'自定义'来编写您自己的指令"
            )
        
        with col1:
            # Determine initial value based on preset selection
            if selected_preset != "自定义":
                initial_prompt = preset_prompts[selected_preset]
            else:
                initial_prompt = current_prompt
            
            new_prompt = st.text_area(
                "系统指令",
                value=initial_prompt,
                height=100,
                help="定义AI的行为和回应方式。请具体说明语调、专业程度和回应风格。",
                key="enhanced_system_prompt_editor",
                placeholder="输入AI行为和个性的自定义指令..."
            )
        
        # Real-time validation feedback
        validation_result = self._validate_system_prompt(new_prompt)
        prompt_length = len(new_prompt)
        
        # Show validation status
        col_a, col_b, col_c = st.columns([2, 1, 1])
        
        with col_a:
            if validation_result:
                st.success("✅ Valid system prompt")
            else:
                st.error("❌ Invalid system prompt - contains restricted patterns")
        
        with col_b:
            color = "normal" if prompt_length <= 5000 else "inverse" if prompt_length <= 8000 else "off"
            st.metric("Length", f"{prompt_length:,}/10,000", delta=None)
        
        with col_c:
            if st.button("💾 Apply Prompt", disabled=not validation_result or new_prompt == current_prompt):
                if self._apply_system_prompt_with_confirmation(new_prompt):
                    st.success("System prompt updated successfully!")
                    st.rerun()
        
        # Show prompt preview
        if new_prompt and new_prompt != current_prompt:
            with st.expander("👀 Preview Changes", expanded=False):
                st.write("**Current Prompt:**")
                st.code(current_prompt if current_prompt else "(No system prompt set)")
                st.write("**New Prompt:**")
                st.code(new_prompt)
                
                # Show what will change
                if not current_prompt and new_prompt:
                    st.info("This will set your first system prompt.")
                elif current_prompt and not new_prompt:
                    st.warning("This will remove your current system prompt.")
                else:
                    st.info("This will update your system prompt.")
    
    def _apply_system_prompt_with_confirmation(self, new_prompt: str) -> bool:
        """Apply system prompt with proper validation and confirmation"""
        
        if not self._validate_system_prompt(new_prompt):
            st.error("Cannot apply invalid system prompt.")
            return False
        
        try:
            state_manager.update_system_prompt(new_prompt)
            return True
        except Exception as e:
            st.error(f"Failed to update system prompt: {str(e)}")
            return False
    
    def _validate_system_prompt(self, prompt: str) -> bool:
        """Validate system prompt"""
        
        # Basic validation rules
        if len(prompt) > 10000:  # Too long
            return False
        
        # Check for potentially harmful content (basic check)
        harmful_patterns = ["ignore previous", "forget instructions", "act as if"]
        prompt_lower = prompt.lower()
        
        for pattern in harmful_patterns:
            if pattern in prompt_lower:
                return False
        
        return True
    
    def add_custom_model(self, label: str, model_id: str, capabilities: Dict) -> None:
        """Add a custom model to the selector"""
        
        self.model_map[label] = model_id
        self.model_capabilities[model_id] = capabilities
    
    def remove_model(self, model_id: str) -> bool:
        """Remove a model from the selector"""
        
        # Find and remove from model_map
        label_to_remove = None
        for label, mid in self.model_map.items():
            if mid == model_id:
                label_to_remove = label
                break
        
        if label_to_remove:
            del self.model_map[label_to_remove]
            if model_id in self.model_capabilities:
                del self.model_capabilities[model_id]
            return True
        
        return False
    
    def get_model_capabilities(self, model_id: str) -> Dict:
        """Get capabilities for a specific model"""
        
        return self.model_capabilities.get(model_id, {})
    
    def get_available_models(self) -> List[str]:
        """Get list of available model IDs"""
        
        return list(self.model_map.values())
    
    def get_model_status_summary(self) -> Dict[str, any]:
        """Get a summary of current model status and capabilities"""
        
        state = state_manager.get_state()
        current_model = state.current_model
        caps = self.model_capabilities.get(current_model, {})
        
        return {
            "current_model": current_model,
            "display_name": self._get_model_display_name(current_model),
            "capabilities": caps,
            "is_image_mode": self._is_image_generation_mode(current_model),
            "conversation_length": len(state.messages),
            "system_prompt_set": bool(state.system_prompt.strip())
        }
    
    def suggest_optimal_model(self, task_description: str = "") -> str:
        """Suggest the optimal model based on task description and context"""
        
        task_lower = task_description.lower()
        state = state_manager.get_state()
        
        # Image-related tasks
        if any(keyword in task_lower for keyword in ['image', 'picture', 'visual', 'generate', 'create', 'design']):
            return "models/gemini-3-pro-image-preview"
        
        # Complex reasoning tasks
        if any(keyword in task_lower for keyword in ['analyze', 'complex', 'detailed', 'research', 'strategy']):
            return "models/gemini-3-pro-preview"
        
        # Quick tasks or if conversation is short
        if any(keyword in task_lower for keyword in ['quick', 'fast', 'simple']) or len(state.messages) < 3:
            return "models/gemini-flash-latest"
        
        # Default to current model if no clear preference
        return state.current_model
    
    def export_model_configuration(self) -> Dict[str, any]:
        """Export current model configuration for backup/sharing"""
        
        state = state_manager.get_state()
        
        return {
            "model_id": state.current_model,
            "system_prompt": state.system_prompt,
            "ui_settings": {
                "theme": state.ui_settings.theme,
                "auto_scroll": state.ui_settings.auto_scroll,
                "enable_streaming": state.ui_settings.enable_streaming
            },
            "export_timestamp": state_manager.get_state().messages[-1].timestamp.isoformat() if state.messages else None
        }
    
    def import_model_configuration(self, config: Dict[str, any]) -> bool:
        """Import model configuration from backup"""
        
        try:
            if "model_id" in config:
                state_manager.update_model(config["model_id"])
            
            if "system_prompt" in config:
                if self._validate_system_prompt(config["system_prompt"]):
                    state_manager.update_system_prompt(config["system_prompt"])
            
            if "ui_settings" in config:
                state = state_manager.get_state()
                ui_settings = state.ui_settings
                
                for key, value in config["ui_settings"].items():
                    if hasattr(ui_settings, key):
                        setattr(ui_settings, key, value)
                
                state_manager.update_ui_settings(ui_settings)
            
            return True
            
        except Exception as e:
            st.error(f"Failed to import configuration: {str(e)}")
            return False
    
    def _render_model_comparison_table(self) -> None:
        """Render an enhanced comparison table of available models"""
        
        # Create enhanced comparison data
        comparison_data = []
        for label, model_id in self.model_map.items():
            caps = self.model_capabilities.get(model_id, {})
            
            # Speed with visual indicator
            speed = caps.get('speed', 'unknown').title()
            speed_indicator = {"Fast": "🟢", "Medium": "🟡", "Slow": "🔴"}.get(speed, "⚪")
            
            comparison_data.append({
                "Model": label,
                "Speed": f"{speed_indicator} {speed}",
                "Max Tokens": f"{caps.get('max_tokens', 0):,}",
                "Vision": "✅" if caps.get('supports_vision') else "❌",
                "Image Gen": "✅" if caps.get('supports_image_gen') else "❌",
                "Best For": self._get_use_cases(caps)[:50] + "..." if len(self._get_use_cases(caps)) > 50 else self._get_use_cases(caps)
            })
        
        # Display as enhanced table
        if comparison_data:
            st.dataframe(
                comparison_data,
                use_container_width=True,
                hide_index=True
            )
            
            # Add recommendation based on current conversation
            state = state_manager.get_state()
            if len(state.messages) > 0:
                st.write("**💡 Smart Recommendations:**")
                recommendations = self._get_model_recommendations(state)
                for rec in recommendations:
                    st.write(f"• {rec}")
    
    def _get_model_recommendations(self, state) -> List[str]:
        """Get intelligent model recommendations based on conversation context"""
        
        recommendations = []
        
        # Analyze conversation for patterns
        has_images = any(hasattr(msg, 'ref_images') and msg.ref_images for msg in state.messages)
        has_long_messages = any(len(getattr(msg, 'content', '')) > 1000 for msg in state.messages)
        message_count = len(state.messages)
        
        # Generate recommendations
        if has_images:
            recommendations.append("🎨 **Gemini 3 Image** - Best for image analysis and generation tasks")
        
        if has_long_messages or message_count > 20:
            recommendations.append("🧠 **Gemini 3 Pro** - Best for complex, long-form conversations")
        
        if message_count < 5 and not has_images:
            recommendations.append("⚡ **Gemini Flash** - Best for quick questions and fast responses")
        
        if not recommendations:
            recommendations.append("💬 Current model selection looks good for your conversation type")
        
        return recommendations


# Global instance for easy access
model_selector = ModelSelector()
