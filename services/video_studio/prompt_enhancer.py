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
                    
                    1. 描述图片中的主要元素（人物、物体、场景、色彩、光线等）
                    2. 基于图片内容，为8秒视频设计合适的动作和镜头运动
                    3. 保持图片的视觉风格和氛围
                    4. 确保生成的视频提示词能够很好地延续图片的故事
                    """)
                except Exception:
                    # 如果图片处理失败，使用文本优化
                    inputs.append(f"""
                    【用户提示词优化任务】
                    用户输入："{user_prompt}"
                    
                    请优化这个提示词，使其更适合8秒视频生成。
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
你是一位专业的视频制作AI助手，专门为Google Veo 3.1视频生成模型优化提示词。

【任务目标】
为{duration}秒的短视频生成优化专业的提示词，确保生成高质量、有吸引力的视频内容。

【技术规格】
- 视频时长：{duration}秒
- 宽高比：{aspect_ratio}
- 风格偏好：{style_preference}
- 目标模型：Google Veo 3.1

【优化原则】
1. **动作设计**：为{duration}秒时长设计合适的动作序列，确保动作流畅自然
2. **镜头语言**：使用专业的镜头术语（如特写、中景、远景、推拉摇移等）
3. **视觉细节**：增加光线、色彩、质感等视觉描述
4. **情感氛围**：营造符合内容的情感氛围和故事感
5. **技术质量**：确保提示词有助于生成高质量、清晰的视频

【输出格式】
请按以下格式输出：

【分析】
- 对原始提示词的理解和分析
- 识别的关键元素（主体、动作、场景等）
- 为{duration}秒视频设计的改进建议

【优化提示词】
[在这里输出优化后的完整提示词，一段连续的英文描述]

【优化说明】
- 解释主要的优化点
- 说明为什么这样的描述更适合视频生成

记住：你的目标是创造一个能够生成引人入胜、视觉效果出色的{duration}秒视频的提示词。
"""
    
    def _extract_enhanced_prompt(self, response_text: str, fallback: str) -> str:
        """从响应中提取增强后的提示词"""
        try:
            # 查找【优化提示词】标签
            if "【优化提示词】" in response_text:
                start_idx = response_text.find("【优化提示词】") + len("【优化提示词】")
                end_idx = response_text.find("【优化说明】", start_idx)
                
                if end_idx == -1:
                    # 如果没有找到结束标签，取到文本末尾
                    enhanced = response_text[start_idx:].strip()
                else:
                    enhanced = response_text[start_idx:end_idx].strip()
                
                # 清理格式
                enhanced = enhanced.replace("\n", " ").strip()
                if enhanced:
                    return enhanced
            
            # 如果没有找到标签，尝试提取第一段连续的英文描述
            lines = response_text.split('\n')
            for line in lines:
                line = line.strip()
                if len(line) > 20 and not line.startswith('【') and not line.startswith('-'):
                    return line
            
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
