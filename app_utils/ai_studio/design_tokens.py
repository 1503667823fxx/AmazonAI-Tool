"""
Design tokens and modern CSS styling system for AI Studio
Provides consistent design language and theming capabilities
"""

from typing import Dict, Any
import streamlit as st


class DesignTokens:
    """Design tokens for consistent styling"""
    
    # Color palette
    COLORS = {
        # Primary colors
        "primary": "#1f2937",
        "primary_light": "#374151",
        "primary_dark": "#111827",
        
        # Secondary colors
        "secondary": "#6366f1",
        "secondary_light": "#818cf8",
        "secondary_dark": "#4f46e5",
        
        # Neutral colors
        "neutral_50": "#f9fafb",
        "neutral_100": "#f3f4f6",
        "neutral_200": "#e5e7eb",
        "neutral_300": "#d1d5db",
        "neutral_400": "#9ca3af",
        "neutral_500": "#6b7280",
        "neutral_600": "#4b5563",
        "neutral_700": "#374151",
        "neutral_800": "#1f2937",
        "neutral_900": "#111827",
        
        # Semantic colors
        "success": "#10b981",
        "warning": "#f59e0b",
        "error": "#ef4444",
        "info": "#3b82f6",
        
        # Background colors
        "bg_primary": "#ffffff",
        "bg_secondary": "#f9fafb",
        "bg_tertiary": "#f3f4f6",
        
        # Text colors
        "text_primary": "#111827",
        "text_secondary": "#6b7280",
        "text_tertiary": "#9ca3af",
        
        # Border colors
        "border_light": "#e5e7eb",
        "border_medium": "#d1d5db",
        "border_dark": "#9ca3af",
    }
    
    # Typography
    TYPOGRAPHY = {
        "font_family": "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
        "font_size_xs": "0.75rem",
        "font_size_sm": "0.875rem",
        "font_size_base": "1rem",
        "font_size_lg": "1.125rem",
        "font_size_xl": "1.25rem",
        "font_size_2xl": "1.5rem",
        "font_size_3xl": "1.875rem",
        
        "font_weight_normal": "400",
        "font_weight_medium": "500",
        "font_weight_semibold": "600",
        "font_weight_bold": "700",
        
        "line_height_tight": "1.25",
        "line_height_normal": "1.5",
        "line_height_relaxed": "1.75",
    }
    
    # Spacing
    SPACING = {
        "xs": "0.25rem",
        "sm": "0.5rem",
        "md": "1rem",
        "lg": "1.5rem",
        "xl": "2rem",
        "2xl": "3rem",
        "3xl": "4rem",
    }
    
    # Border radius
    RADIUS = {
        "none": "0",
        "sm": "0.25rem",
        "md": "0.375rem",
        "lg": "0.5rem",
        "xl": "0.75rem",
        "2xl": "1rem",
        "full": "9999px",
    }
    
    # Shadows
    SHADOWS = {
        "sm": "0 1px 2px 0 rgba(0, 0, 0, 0.05)",
        "md": "0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)",
        "lg": "0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)",
        "xl": "0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)",
    }
    
    # Transitions
    TRANSITIONS = {
        "fast": "150ms ease-in-out",
        "normal": "250ms ease-in-out",
        "slow": "350ms ease-in-out",
    }


class ModernCSSInjector:
    """Modern CSS injection system with design tokens"""
    
    def __init__(self, tokens: DesignTokens = None):
        self.tokens = tokens or DesignTokens()
    
    def inject_base_styles(self):
        """Inject base styles and CSS variables"""
        css_vars = self._generate_css_variables()
        base_styles = self._generate_base_styles()
        
        st.markdown(f"""
        <style>
        {css_vars}
        {base_styles}
        </style>
        """, unsafe_allow_html=True)
    
    def inject_chat_styles(self):
        """Inject chat-specific styles"""
        chat_styles = self._generate_chat_styles()
        
        st.markdown(f"""
        <style>
        {chat_styles}
        </style>
        """, unsafe_allow_html=True)
    
    def inject_input_styles(self):
        """Inject input panel styles"""
        input_styles = self._generate_input_styles()
        
        st.markdown(f"""
        <style>
        {input_styles}
        </style>
        """, unsafe_allow_html=True)
    
    def inject_all_styles(self):
        """Inject all styles at once"""
        self.inject_base_styles()
        self.inject_chat_styles()
        self.inject_input_styles()
    
    def _generate_css_variables(self) -> str:
        """Generate CSS custom properties from design tokens"""
        css_vars = [":root {"]
        
        # Colors
        for name, value in self.tokens.COLORS.items():
            css_vars.append(f"  --color-{name.replace('_', '-')}: {value};")
        
        # Typography
        for name, value in self.tokens.TYPOGRAPHY.items():
            css_vars.append(f"  --{name.replace('_', '-')}: {value};")
        
        # Spacing
        for name, value in self.tokens.SPACING.items():
            css_vars.append(f"  --spacing-{name}: {value};")
        
        # Border radius
        for name, value in self.tokens.RADIUS.items():
            css_vars.append(f"  --radius-{name}: {value};")
        
        # Shadows
        for name, value in self.tokens.SHADOWS.items():
            css_vars.append(f"  --shadow-{name}: {value};")
        
        # Transitions
        for name, value in self.tokens.TRANSITIONS.items():
            css_vars.append(f"  --transition-{name}: {value};")
        
        css_vars.append("}")
        return "\n".join(css_vars)
    
    def _generate_base_styles(self) -> str:
        """Generate base application styles"""
        return """
        /* Base styles */
        .block-container {
            padding-bottom: 120px !important;
            font-family: var(--font-family);
        }
        
        /* Hide Streamlit branding */
        footer {
            visibility: hidden;
        }
        
        .stApp > header {
            background-color: transparent;
        }
        
        /* Smooth scrolling */
        html {
            scroll-behavior: smooth;
        }
        
        /* Focus styles */
        *:focus {
            outline: 2px solid var(--color-secondary);
            outline-offset: 2px;
        }
        
        /* Custom scrollbar */
        ::-webkit-scrollbar {
            width: 8px;
        }
        
        ::-webkit-scrollbar-track {
            background: var(--color-neutral-100);
        }
        
        ::-webkit-scrollbar-thumb {
            background: var(--color-neutral-300);
            border-radius: var(--radius-full);
        }
        
        ::-webkit-scrollbar-thumb:hover {
            background: var(--color-neutral-400);
        }
        """
    
    def _generate_chat_styles(self) -> str:
        """Generate chat interface styles"""
        return """
        /* Chat message styles */
        .stChatMessage {
            border-radius: var(--radius-lg);
            margin-bottom: var(--spacing-md);
            box-shadow: var(--shadow-sm);
            transition: all var(--transition-normal);
        }
        
        .stChatMessage:hover {
            box-shadow: var(--shadow-md);
        }
        
        /* User message styling */
        .stChatMessage[data-testid="user-message"] {
            background-color: var(--color-secondary);
            color: white;
            margin-left: var(--spacing-xl);
        }
        
        /* Assistant message styling */
        .stChatMessage[data-testid="assistant-message"] {
            background-color: var(--color-bg-secondary);
            border: 1px solid var(--color-border-light);
            margin-right: var(--spacing-xl);
        }
        
        /* Message content */
        .stChatMessage .stMarkdown {
            font-size: var(--font-size-base);
            line-height: var(--line-height-normal);
        }
        
        /* Message actions */
        .message-actions {
            display: flex;
            gap: var(--spacing-sm);
            margin-top: var(--spacing-sm);
            opacity: 0;
            transition: opacity var(--transition-normal);
        }
        
        .stChatMessage:hover .message-actions {
            opacity: 1;
        }
        
        /* Image display */
        .stImage {
            border-radius: var(--radius-md);
            overflow: hidden;
            box-shadow: var(--shadow-sm);
        }
        
        /* Streaming indicator */
        .streaming-indicator {
            display: inline-block;
            width: 8px;
            height: 8px;
            background-color: var(--color-secondary);
            border-radius: var(--radius-full);
            animation: pulse 1.5s ease-in-out infinite;
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        """
    
    def _generate_input_styles(self) -> str:
        """Generate input panel styles"""
        return """
        /* File upload popover */
        div[data-testid="stPopover"] {
            position: fixed !important;
            bottom: 75px !important;
            left: 30px !important;
            z-index: 2147483647 !important;
            width: 48px !important;
            height: 48px !important;
        }
        
        div[data-testid="stPopover"] > div > button {
            border-radius: var(--radius-full) !important;
            width: 48px !important;
            height: 48px !important;
            background-color: var(--color-bg-primary) !important;
            box-shadow: var(--shadow-lg) !important;
            border: 1px solid var(--color-border-light) !important;
            color: var(--color-text-primary) !important;
            font-size: var(--font-size-lg) !important;
            padding: 0 !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            transition: all var(--transition-normal) !important;
        }
        
        div[data-testid="stPopover"] > div > button:hover {
            transform: scale(1.05);
            box-shadow: var(--shadow-xl) !important;
            border-color: var(--color-secondary) !important;
            color: var(--color-secondary) !important;
        }
        
        /* Chat input styling */
        .stChatInput {
            border-radius: var(--radius-lg);
            border: 2px solid var(--color-border-light);
            transition: border-color var(--transition-normal);
        }
        
        .stChatInput:focus-within {
            border-color: var(--color-secondary);
            box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1);
        }
        
        /* File upload area */
        .upload-area {
            border: 2px dashed var(--color-border-medium);
            border-radius: var(--radius-lg);
            padding: var(--spacing-xl);
            text-align: center;
            transition: all var(--transition-normal);
            background-color: var(--color-bg-secondary);
        }
        
        .upload-area:hover,
        .upload-area.drag-over {
            border-color: var(--color-secondary);
            background-color: rgba(99, 102, 241, 0.05);
        }
        
        /* Image grid */
        .image-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
            gap: var(--spacing-sm);
            margin-top: var(--spacing-md);
        }
        
        .image-thumbnail {
            position: relative;
            border-radius: var(--radius-md);
            overflow: hidden;
            aspect-ratio: 1;
            background-color: var(--color-bg-tertiary);
        }
        
        .image-thumbnail img {
            width: 100%;
            height: 100%;
            object-fit: cover;
        }
        
        .image-remove {
            position: absolute;
            top: 4px;
            right: 4px;
            background-color: var(--color-error);
            color: white;
            border: none;
            border-radius: var(--radius-full);
            width: 20px;
            height: 20px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 12px;
            cursor: pointer;
            opacity: 0;
            transition: opacity var(--transition-normal);
        }
        
        .image-thumbnail:hover .image-remove {
            opacity: 1;
        }
        
        /* Button styles */
        .stButton > button {
            border-radius: var(--radius-md);
            font-weight: var(--font-weight-medium);
            transition: all var(--transition-normal);
            border: 1px solid var(--color-border-light);
        }
        
        .stButton > button:hover {
            transform: translateY(-1px);
            box-shadow: var(--shadow-md);
        }
        
        /* Primary button */
        .stButton.primary > button {
            background-color: var(--color-secondary);
            color: white;
            border-color: var(--color-secondary);
        }
        
        .stButton.primary > button:hover {
            background-color: var(--color-secondary-dark);
            border-color: var(--color-secondary-dark);
        }
        
        /* Loading states */
        .loading {
            opacity: 0.6;
            pointer-events: none;
        }
        
        .spinner {
            display: inline-block;
            width: 16px;
            height: 16px;
            border: 2px solid var(--color-neutral-200);
            border-radius: var(--radius-full);
            border-top-color: var(--color-secondary);
            animation: spin 1s ease-in-out infinite;
        }
        
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
        """


# Global instance
css_injector = ModernCSSInjector()


def inject_modern_styles():
    """Convenience function to inject all modern styles"""
    css_injector.inject_all_styles()