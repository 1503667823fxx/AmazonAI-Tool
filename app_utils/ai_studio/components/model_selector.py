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
        
        # 简化的模型选择标题
        st.subheader("🤖 模型选择")
        
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
        
        # 简化的模型信息显示 - 只显示基本状态
        self._render_simple_model_status(selected_model_id)
        
        # Determine if this is image generation mode
        is_image_mode = self._is_image_generation_mode(selected_model_id)
        
        # Add aspect ratio selector for image generation models
        if is_image_mode:
            self._render_aspect_ratio_selector()
        
        return selected_model_id, is_image_mode
    
    def _handle_enhanced_model_switch(self, old_model: str, new_model: str) -> None:
        """简化的模型切换处理"""
        
        # 直接切换模型，不显示冗余提示
        self._perform_model_switch(old_model, new_model)
        
        # 只在有对话历史时显示简单提示
        state = state_manager.get_state()
        if len(state.messages) > 0:
            st.info(f"已切换到 {self._get_model_display_name(new_model)}，对话历史已保留")
    
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
    
    def _render_simple_model_status(self, model_id: str) -> None:
        """渲染简化的模型状态信息"""
        
        caps = self.model_capabilities.get(model_id, {})
        
        if caps:
            # 只显示最基本的信息
            if caps.get('supports_image_gen'):
                st.info("🎨 当前模式：图像生成")
            else:
                st.info("💬 当前模式：文本对话")
            
            # 可选：显示一个简单的功能提醒（只显示一次）
            if not st.session_state.get("model_tip_shown", False):
                if caps.get('supports_image_gen'):
                    st.success("💡 提示：可以上传参考图片来生成相似风格的图像")
                else:
                    st.success("💡 提示：可以上传图片让AI分析内容")
                st.session_state.model_tip_shown = True
    
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
        """渲染简化的系统提示编辑器"""
        
        if self._is_image_generation_mode(model_id):
            return  # 图像生成模式不显示系统提示
        
        st.subheader("🎭 系统提示")
        
        state = state_manager.get_state()
        current_prompt = state.system_prompt
        
        # 简化的系统提示编辑器
        new_prompt = st.text_area(
            "系统指令",
            value=current_prompt,
            height=80,
            help="定义AI的行为方式",
            key="simple_system_prompt_editor",
            placeholder="例如：你是专业的电商助手..."
        )
        
        # 简单的应用按钮
        if new_prompt != current_prompt:
            if st.button("💾 应用", type="primary"):
                if self._apply_system_prompt_with_confirmation(new_prompt):
                    st.success("系统提示已更新！")
                    st.rerun()
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

    def _render_aspect_ratio_selector(self) -> None:
        """Render aspect ratio selector for image generation models"""
        
        st.markdown("---")  # Add separator
        st.subheader("📐 图片比例设置")
        
        # Define aspect ratio options
        aspect_ratios = {
            "1:1 (正方形)": "1:1 square aspect ratio",
            "4:3 (横向)": "4:3 landscape aspect ratio", 
            "3:4 (竖向)": "3:4 portrait aspect ratio",
            "16:9 (宽屏)": "16:9 cinematic widescreen aspect ratio",
            "9:16 (手机竖屏)": "9:16 mobile portrait aspect ratio",
            "21:9 (超宽屏)": "21:9 ultrawide cinematic aspect ratio"
        }
        
        # Get current selection from session state
        current_ratio = st.session_state.get('ai_studio_aspect_ratio', "1:1 (正方形)")
        
        # Create two columns for better layout
        col1, col2 = st.columns([2, 1])
        
        with col1:
            selected_ratio = st.selectbox(
                "选择图片比例",
                list(aspect_ratios.keys()),
                index=list(aspect_ratios.keys()).index(current_ratio) if current_ratio in aspect_ratios else 0,
                key="aspect_ratio_selector",
                help="选择生成图片的宽高比例"
            )
        
        with col2:
            # Show visual preview of the aspect ratio
            ratio_preview = self._get_aspect_ratio_preview(selected_ratio)
            st.markdown(f"**预览:** {ratio_preview}")
        
        # Store selection in session state
        st.session_state['ai_studio_aspect_ratio'] = selected_ratio
        st.session_state['ai_studio_aspect_ratio_prompt'] = aspect_ratios[selected_ratio]
        
        # Show helpful tips
        with st.expander("💡 比例选择建议", expanded=False):
            st.markdown("""
            **推荐用途：**
            - **1:1 (正方形)**: 社交媒体头像、产品展示图
            - **4:3 (横向)**: 传统照片、产品详情图
            - **3:4 (竖向)**: 手机壁纸、竖版海报
            - **16:9 (宽屏)**: 横幅广告、网站头图
            - **9:16 (手机竖屏)**: 短视频封面、手机广告
            - **21:9 (超宽屏)**: 电影风格、全景图片
            """)
    
    def _get_aspect_ratio_preview(self, ratio_name: str) -> str:
        """Get a visual preview representation of the aspect ratio"""
        
        previews = {
            "1:1 (正方形)": "⬜",
            "4:3 (横向)": "▭", 
            "3:4 (竖向)": "▯",
            "16:9 (宽屏)": "▬",
            "9:16 (手机竖屏)": "▮",
            "21:9 (超宽屏)": "▰"
        }
        
        return previews.get(ratio_name, "⬜")
    
    def get_current_aspect_ratio_prompt(self) -> str:
        """Get the current aspect ratio prompt for image generation"""
        
        return st.session_state.get('ai_studio_aspect_ratio_prompt', "1:1 square aspect ratio")


# Global instance for easy access
model_selector = ModelSelector()
