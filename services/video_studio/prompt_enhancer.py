"""
Video Studio 提示词增强服务
基于 Gemini 3 Flash Preview 模型，专门为 8秒视频生成优化提示词
"""

import streamlit as st
from typing import Optional, Dict, Any, List
from PIL import Image
import io
import base64

# 尝试导入Google GenAI
try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    try:
        # 尝试备用导入
        from google import genai
        GENAI_AVAILABLE = True
    except ImportError:
        GENAI_AVAILABLE = False
        genai = None

class VideoPromptEnhancer:
    """
    视频提示词增强器
    专门为 Google Veo 3.1 的 8秒视频生成优化提示词
    """
    
    def __init__(self, api_key: Optional[str] = None):
        if not GENAI_AVAILABLE:
            self.valid = False
            return
            
        self.api_key = api_key or st.secrets.get("GOOGLE_API_KEY")
        if self.api_key:
            genai.configure(api_key=self.api_key)
            self.valid = True
        else:
            self.valid = False
    
    def _get_model(self):
        """获取 Gemini 3 Flash Preview 模型"""
        if not GENAI_AVAILABLE or not genai:
            return None
        return genai.GenerativeModel("models/gemini-3-flash-preview")
    
    def enhance_prompt(
        self, 
        user_prompt: str, 
        reference_image: Optional[bytes] = None,
        duration: int = 8,
        aspect_ratio: str = "16:9",
        style_preference: str = "cinematic"
    ) -> Dict[str, Any]:
        """
        增强用户输入的视频提示词
        
        Args:
            user_prompt: 用户原始提示词
            reference_image: 参考图片（可选）
            duration: 视频时长（秒）
            aspect_ratio: 宽高比
            style_preference: 风格偏好
            
        Returns:
            包含增强后提示词和分析的字典
        """
        if not self.valid or not GENAI_AVAILABLE:
            return {
                "success": False,
                "error": "Gemini API 未配置或不可用",
                "enhanced_prompt": user_prompt,
                "analysis": "API未配置，返回原始提示词"
            }
        
        try:
            # 构建系统提示词
            system_prompt = self._build_system_prompt(duration, aspect_ratio, style_preference)
            
            # 准备输入内容
            inputs = [system_prompt]
            
            # 如果有参考图片，添加图片分析
            if reference_image:
                try:
                    # 转换图片格式
                    image = Image.open(io.BytesIO(reference_image))
                    inputs.append(image)
                    inputs.append(f"""
                    【参考图片分析任务】
                    请分析上传的参考图片，并结合用户提示词："{user_prompt}"
                    
                    要求：
                    1. 在【优化提示词】部分只输出纯净的视频描述，不要任何解释
                    2. 基于图片内容设计8秒视频的动作和镜头
                    3. 保持图片的视觉风格和氛围
                    4. 描述要完整专业，可直接用于视频生成
                    """)
                except Exception:
                    # 如果图片处理失败，使用文本优化
                    inputs.append(f"""
                    【用户提示词优化任务】
                    用户输入："{user_prompt}"
                    
                    请将这个描述优化为专业的视频生成提示词。
                    
                    要求：
                    1. 在【优化提示词】部分只输出纯净的视频描述，不要任何解释
                    2. 描述要完整、专业，可直接用于视频生成
                    3. 包含主体、动作、场景、镜头、光线等元素
                    4. 适合8秒视频的节奏和内容
                    """)
            else:
                inputs.append(f"""
                【用户提示词优化任务】
                用户输入："{user_prompt}"
                
                请优化这个提示词，使其更适合8秒视频生成。
                """)
            
            # 调用 Gemini API
            model = self._get_model()
            if not model:
                return {
                    "success": False,
                    "error": "无法获取Gemini模型",
                    "enhanced_prompt": user_prompt,
                    "analysis": "模型不可用，返回原始提示词"
                }
                
            config = genai.types.GenerationConfig(
                temperature=0.7,
                candidate_count=1,
                max_output_tokens=1000
            )
            
            response = model.generate_content(inputs, generation_config=config)
            
            if response and response.text:
                # 解析响应
                enhanced_text = response.text.strip()
                
                # 提取增强后的提示词（假设在【优化提示词】标签后）
                enhanced_prompt = self._extract_enhanced_prompt(enhanced_text, user_prompt)
                
                return {
                    "success": True,
                    "enhanced_prompt": enhanced_prompt,
                    "analysis": enhanced_text,
                    "original_prompt": user_prompt,
                    "has_reference_image": reference_image is not None
                }
            else:
                return {
                    "success": False,
                    "error": "API响应为空",
                    "enhanced_prompt": user_prompt,
                    "analysis": "API响应为空，返回原始提示词"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"API调用失败: {str(e)}",
                "enhanced_prompt": user_prompt,
                "analysis": f"处理失败: {str(e)}"
            }
    
    def _build_system_prompt(self, duration: int, aspect_ratio: str, style_preference: str) -> str:
        """构建系统提示词"""
        return f"""
你是专业的视频提示词优化专家，专门为Google Veo 3.1优化{duration}秒视频的提示词。

【核心任务】
将用户的简单描述转换为专业的视频生成提示词，直接可用于视频生成。

【输出要求】
1. 主要输出：一段完整的、可直接使用的中文视频描述
2. 描述要包含：主体、动作、场景、镜头、光线、氛围
3. 适合{duration}秒视频的动作节奏
4. 语言简洁专业，避免冗余

【输出格式】
【分析】
简要分析用户输入的核心元素和适合的风格

【优化提示词】
[输出一段完整的中文视频描述，可直接复制使用]

【优化说明】
简要说明优化的关键点

【重要】优化提示词部分必须是完整的、可直接使用的视频描述，不要包含任何解释性文字或标记符号。
"""
    
    def _extract_enhanced_prompt(self, response_text: str, fallback: str) -> str:
        """从响应中提取增强后的提示词"""
        try:
            # 查找【优化提示词】标签
            if "【优化提示词】" in response_text:
                start_idx = response_text.find("【优化提示词】") + len("【优化提示词】")
                end_idx = response_text.find("【优化说明】", start_idx)
                
                if end_idx == -1:
                    # 如果没有找到结束标签，查找下一个【标签或文本末尾
                    next_section = response_text.find("【", start_idx)
                    if next_section != -1:
                        enhanced = response_text[start_idx:next_section].strip()
                    else:
                        enhanced = response_text[start_idx:].strip()
                else:
                    enhanced = response_text[start_idx:end_idx].strip()
                
                # 清理格式 - 移除多余的换行和空格，但保持基本结构
                enhanced = enhanced.replace("\n\n", " ").replace("\n", " ").strip()
                
                # 移除可能的标记符号
                enhanced = enhanced.lstrip("- ").lstrip("• ").lstrip("* ")
                
                if enhanced and len(enhanced) > 10:
                    return enhanced
            
            # 如果没有找到标签，尝试提取最长的连续描述段落
            lines = response_text.split('\n')
            best_line = ""
            for line in lines:
                line = line.strip()
                # 寻找不是标题、不是分析内容的描述性文字
                if (len(line) > len(best_line) and 
                    len(line) > 20 and 
                    not line.startswith('【') and 
                    not line.startswith('-') and
                    not line.startswith('•') and
                    not line.startswith('*') and
                    not line.startswith('以下是') and
                    not line.startswith('你好') and
                    '分析' not in line and
                    '建议' not in line):
                    best_line = line
            
            if best_line:
                return best_line
            
            return fallback
            
        except Exception:
            return fallback
    
    def get_style_suggestions(self) -> List[Dict[str, str]]:
        """获取风格建议"""
        return [
            {
                "name": "cinematic",
                "display": "🎬 电影风格",
                "description": "电影级画面质量，专业镜头语言"
            },
            {
                "name": "documentary", 
                "display": "📹 纪录片风格",
                "description": "真实自然，生活化场景"
            },
            {
                "name": "artistic",
                "display": "🎨 艺术风格", 
                "description": "创意视觉，艺术化表达"
            },
            {
                "name": "commercial",
                "display": "📺 商业广告风格",
                "description": "商业化，产品展示导向"
            },
            {
                "name": "lifestyle",
                "display": "🌟 生活方式风格",
                "description": "温馨日常，生活化场景"
            }
        ]

# 全局服务实例
_prompt_enhancer: Optional[VideoPromptEnhancer] = None

def get_prompt_enhancer() -> Optional[VideoPromptEnhancer]:
    """获取提示词增强器实例"""
    global _prompt_enhancer
    
    try:
        if not GENAI_AVAILABLE:
            return None
            
        if "GOOGLE_API_KEY" not in st.secrets:
            return None
        
        if _prompt_enhancer is None:
            _prompt_enhancer = VideoPromptEnhancer()
        
        return _prompt_enhancer
    except Exception as e:
        st.error(f"⚠️ 创建提示词增强器失败: {str(e)}")
        return None

def enhance_video_prompt(
    user_prompt: str,
    reference_image: Optional[bytes] = None,
    duration: int = 8,
    aspect_ratio: str = "16:9",
    style_preference: str = "cinematic"
) -> Dict[str, Any]:
    """
    增强视频提示词的便捷函数
    """
    enhancer = get_prompt_enhancer()
    if not enhancer:
        return {
            "success": False,
            "error": "提示词增强器未配置",
            "enhanced_prompt": user_prompt,
            "analysis": "服务未配置，返回原始提示词"
        }
    
    return enhancer.enhance_prompt(
        user_prompt=user_prompt,
        reference_image=reference_image,
        duration=duration,
        aspect_ratio=aspect_ratio,
        style_preference=style_preference
    )
