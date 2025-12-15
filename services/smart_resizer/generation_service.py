import streamlit as st
import google.generativeai as genai
from PIL import Image
import io

# 初始化 API
API_KEY = st.secrets.get("GOOGLE_API_KEY") or st.secrets["google"]["api_key"]
genai.configure(api_key=API_KEY)

def analyze_image_composition(image: Image.Image) -> dict:
    """
    使用Gemini分析图片构图和主体位置
    """
    try:
        model = genai.GenerativeModel('models/gemini-1.5-pro')
        
        analysis_prompt = """Analyze this product image composition and provide detailed information:

1. Main subject identification:
   - What is the main product/subject in the image?
   - Where is it positioned (center, left, right, top, bottom)?
   - What percentage of the image does it occupy?

2. Background analysis:
   - What type of background (solid color, gradient, textured, scene)?
   - What colors are dominant in the background?
   - Is the background simple or complex?

3. Composition recommendations:
   - For different aspect ratios (1:1, 4:3, 21:9), how should the subject be repositioned?
   - What background extension would work best?
   - Should the subject be scaled or just repositioned?

Please provide a structured analysis in JSON format with keys: subject_position, subject_size_percent, background_type, background_colors, composition_recommendations."""
        
        response = model.generate_content([analysis_prompt, image])
        
        if response.text:
            # 尝试解析JSON响应，如果失败则返回基本分析
            try:
                import json
                analysis = json.loads(response.text)
                return analysis
            except:
                # 如果JSON解析失败，返回文本分析
                return {"analysis_text": response.text}
        
        return {"error": "No analysis received"}
        
    except Exception as e:
        st.warning(f"图片分析失败: {str(e)}")
        return {"error": str(e)}

def fill_image(image: Image.Image, mask: Image.Image, prompt: str, use_gemini: bool = True, target_ratio: tuple = None, test_mode: bool = False, composition_mode: str = "智能分析", quality_level: str = "标准", background_handling: str = "智能延续") -> Image.Image:
    """
    智能的Gemini画幅重构 - 考虑主体位置和构图优化
    """
    try:
        if target_ratio:
            ratio_w, ratio_h = target_ratio
            target_ratio_val = ratio_w / ratio_h
            orig_w, orig_h = image.size
            orig_ratio = orig_w / orig_h
            
            # 首先分析图片构图
            st.write("🔍 正在分析图片构图...")
            composition_analysis = analyze_image_composition(image)
            
            # 根据分析结果调整提示词
            model = genai.GenerativeModel('models/gemini-1.5-pro-vision-latest')
            
            # 根据用户选择构建智能提示词
            if target_ratio_val > orig_ratio:
                expansion_direction = "horizontally (width)"
                positioning_advice = "reposition the main subject optimally for wider composition"
            elif target_ratio_val < orig_ratio:
                expansion_direction = "vertically (height)"
                positioning_advice = "maintain subject prominence while adding appropriate vertical content"
            else:
                expansion_direction = "minimally"
                positioning_advice = "optimize the composition slightly"
            
            # 构图模式指令
            composition_instructions = {
                "智能分析": "Analyze the subject position and reposition it optimally for the new aspect ratio. The subject should be placed where it looks most natural and balanced.",
                "保持居中": "Keep the main subject centered in the new composition.",
                "自定义位置": "Position the subject according to the rule of thirds for professional composition."
            }
            
            # 质量级别指令
            quality_instructions = {
                "快速": "Generate efficiently while maintaining good quality.",
                "标准": "Balance quality and processing time for professional results.",
                "高质量": "Prioritize maximum quality, detail preservation, and seamless blending."
            }
            
            # 背景处理指令
            background_instructions = {
                "智能延续": "Intelligently extend the existing background patterns, textures, and colors naturally.",
                "模糊延续": "Extend the background with a subtle blur effect to create depth.",
                "纯色填充": "Fill new areas with a clean, solid color that complements the existing background."
            }
            
            smart_prompt = f"""Transform this product image to {ratio_w}:{ratio_h} aspect ratio with intelligent recomposition:

TASK: Smart image recomposition and outpainting
- Target aspect ratio: {ratio_w}:{ratio_h} (expand {expansion_direction})
- Current ratio: {orig_ratio:.2f} → Target: {target_ratio_val:.2f}

COMPOSITION STRATEGY:
{composition_instructions[composition_mode]}

BACKGROUND HANDLING:
{background_instructions[background_handling]}

QUALITY LEVEL:
{quality_instructions[quality_level]}

CORE REQUIREMENTS:
1. PRESERVE the main product/subject completely - no cropping
2. INTELLIGENTLY REPOSITION the subject for optimal composition in new aspect ratio
3. SCALE the subject appropriately if beneficial (slightly larger for wider formats)
4. EXTEND background areas seamlessly and naturally
5. {positioning_advice}
6. Maintain original lighting, shadows, and depth
7. Ensure the subject remains the clear focal point
8. Create professional, commercial-grade quality

CRITICAL: The subject should be repositioned and potentially resized to look natural and well-composed in the {ratio_w}:{ratio_h} format, not just placed in expanded canvas."""
            
            st.write(f"🎨 正在进行智能重构 (目标比例: {ratio_w}:{ratio_h})...")
            
            response = model.generate_content([smart_prompt, image])
            
            if response.parts:
                for part in response.parts:
                    if hasattr(part, "inline_data") and part.inline_data:
                        img_data = part.inline_data.data
                        result_image = Image.open(io.BytesIO(img_data))
                        
                        # 验证结果
                        gen_w, gen_h = result_image.size
                        gen_ratio = gen_w / gen_h
                        
                        # 检查比例是否接近目标
                        ratio_diff = abs(gen_ratio - target_ratio_val)
                        if ratio_diff < 0.1:  # 允许10%的误差
                            st.success(f"✅ 智能重构成功！")
                            st.info(f"📏 尺寸变化: {orig_w}×{orig_h} → {gen_w}×{gen_h}")
                            st.info(f"📐 比例变化: {orig_ratio:.2f} → {gen_ratio:.2f} (目标: {target_ratio_val:.2f})")
                            
                            # 显示构图分析结果
                            if "analysis_text" in composition_analysis:
                                with st.expander("🎯 构图分析"):
                                    st.text(composition_analysis["analysis_text"])
                            
                            return result_image
                        else:
                            st.warning(f"⚠️ 比例偏差较大: 生成比例 {gen_ratio:.2f}, 目标比例 {target_ratio_val:.2f}")
                            return result_image
            
            # 检查文本响应
            if response.text:
                st.warning(f"Gemini返回文本响应: {response.text}")
        
        # 如果失败，返回原图
        st.error("智能重构失败，返回原图")
        return image
        
    except Exception as e:
        st.error(f"处理失败: {str(e)}")
        return image
