"""
Configuration management for A+ Studio system.

This module handles API configurations, authentication, and system settings
for the A+ image workflow system.
"""

import os
import streamlit as st
from typing import Optional
from .models import GeminiConfig


class APlusConfig:
    """A+ Studio 系统配置管理"""
    
    def __init__(self):
        self._gemini_config: Optional[GeminiConfig] = None
        self._load_config()
    
    def _load_config(self):
        """加载配置信息"""
        # 尝试从环境变量或Streamlit secrets获取API密钥
        api_key = self._get_api_key()
        
        if api_key:
            self._gemini_config = GeminiConfig(
                api_key=api_key,
                text_model=os.getenv("GEMINI_TEXT_MODEL", "gemini-1.5-pro"),
                image_model=os.getenv("GEMINI_IMAGE_MODEL", "gemini-1.5-pro-vision-latest"),
                max_tokens=int(os.getenv("GEMINI_MAX_TOKENS", "4096")),
                temperature=float(os.getenv("GEMINI_TEMPERATURE", "0.7")),
                timeout=int(os.getenv("GEMINI_TIMEOUT", "30"))
            )
    
    def _get_api_key(self) -> Optional[str]:
        """获取Gemini API密钥"""
        # 优先从环境变量获取
        api_key = os.getenv("GEMINI_API_KEY")
        
        if not api_key:
            # 尝试从环境变量获取GOOGLE_API_KEY（兼容性）
            api_key = os.getenv("GOOGLE_API_KEY")
        
        if not api_key:
            # 尝试从Streamlit secrets获取
            try:
                if hasattr(st, 'secrets'):
                    # 优先尝试GEMINI_API_KEY
                    if 'GEMINI_API_KEY' in st.secrets:
                        api_key = st.secrets["GEMINI_API_KEY"]
                    # 兼容GOOGLE_API_KEY
                    elif 'GOOGLE_API_KEY' in st.secrets:
                        api_key = st.secrets["GOOGLE_API_KEY"]
            except Exception:
                pass
        
        return api_key
    
    @property
    def gemini_config(self) -> Optional[GeminiConfig]:
        """获取Gemini配置"""
        return self._gemini_config
    
    @property
    def is_configured(self) -> bool:
        """检查是否已正确配置"""
        return self._gemini_config is not None and bool(self._gemini_config.api_key)
    
    def update_api_key(self, api_key: str):
        """更新API密钥"""
        if self._gemini_config:
            self._gemini_config.api_key = api_key
        else:
            self._gemini_config = GeminiConfig(api_key=api_key)
    
    def get_image_generation_params(self) -> dict:
        """获取图片生成参数"""
        return {
            "model": self._gemini_config.image_model if self._gemini_config else "gemini-1.5-pro-vision-latest",
            "max_tokens": self._gemini_config.max_tokens if self._gemini_config else 4096,
            "temperature": self._gemini_config.temperature if self._gemini_config else 0.7,
            "timeout": self._gemini_config.timeout if self._gemini_config else 30
        }
    
    def get_text_analysis_params(self) -> dict:
        """获取文本分析参数"""
        return {
            "model": self._gemini_config.text_model if self._gemini_config else "gemini-1.5-pro",
            "max_tokens": self._gemini_config.max_tokens if self._gemini_config else 4096,
            "temperature": self._gemini_config.temperature if self._gemini_config else 0.7,
            "timeout": self._gemini_config.timeout if self._gemini_config else 30
        }


# 全局配置实例
aplus_config = APlusConfig()


# A+ 图片规范配置
APLUS_GENERATION_CONFIG = {
    "default_dimensions": (600, 450),
    "aspect_ratio": "4:3",
    "quality_settings": {
        "high": {"dpi": 300, "quality": 95},
        "medium": {"dpi": 150, "quality": 85},
        "web": {"dpi": 72, "quality": 80}
    },
    "style_presets": {
        "north_american": {
            "lighting": "golden_hour",
            "composition": "rule_of_thirds",
            "color_temperature": "warm",
            "aesthetic": "aspirational_lifestyle"
        },
        "premium_product": {
            "lighting": "studio_professional",
            "composition": "centered_hero",
            "color_temperature": "neutral",
            "aesthetic": "luxury_minimal"
        }
    }
}


# 模块特定配置
MODULE_CONFIGS = {
    "identity": {
        "focus": "lifestyle_integration",
        "lighting_preference": "golden_hour",
        "scene_type": "north_american_middle_class",
        "text_elements": ["value_slogan", "trust_indicator"]
    },
    "sensory": {
        "focus": "material_details",
        "lighting_preference": "high_contrast",
        "viewing_angle": "three_quarter",
        "emphasis": ["durability", "craftsmanship"]
    },
    "extension": {
        "format": "carousel_four_slides",
        "dimensions": ["lifestyle", "pain_point", "performance", "inside_out"],
        "navigation_style": "professional_terminology"
    },
    "trust": {
        "layout": "image_with_text",
        "ratio_options": ["1:1", "2:3"],
        "content_structure": "bullet_points",
        "elements": ["parameters", "guarantees", "cta"]
    }
}
