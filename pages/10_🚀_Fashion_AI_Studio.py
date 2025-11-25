import streamlit as st
import google.generativeai as genai
from PIL import Image, ImageOps
import io
import sys
import os
import base64

# --- 0. 引入门禁系统 ---
sys.path.append(os.path.abspath('.'))
try:
    import auth
    if not auth.check_password(): st.stop()
except ImportError:
    pass 

# --- 1. 页面配置 ---
st.set_page_config(page_title="Fashion AI Studio", page_icon="🚀", layout="wide")

# 自定义 CSS (复刻 React App 的暗色调风格)
st.markdown("""
<style>
    .stApp {
        background-color: #0f0f13;
        color: #e2e8f0;
    }
    .stButton button {
        width: 100%; 
        border-radius: 12px; 
        font-weight: bold;
        background-image: linear-gradient(to right, #4f46e5, #9333ea);
        border: none;
        color: white;
        padding: 12px;
    }
    .stButton button:hover {
        background-image: linear-gradient(to right, #4338ca, #7e22ce);
        color: white;
    }
    .stTextInput input, .stTextArea textarea {
        background-color: #1e293b;
        color: white;
        border: 1px solid #334155;
        border-radius: 8px;
    }
    .step-card {
        background-color: #1e293b;
        padding: 20px;
        border-radius: 16px;
        border: 1px solid #334155;
        margin-bottom: 20px;
    }
    h1, h2, h3 { color: #f8fafc !important; }
    .mode-btn-selected { border: 2px solid #6366f1; background-color: #312e81; color: white; padding: 10px; border-radius: 8px; text-align: center; cursor: pointer; }
    .mode-btn { border: 1px solid #334155; background-color: #1e293b; color: #94a3b8; padding: 10px; border-radius: 8px; text-align: center; cursor: pointer; }
</style>
""", unsafe_allow_html=True)

# --- 2. 配置 ---
if "GOOGLE_API_KEY" not in st.secrets:
    st.error("❌ 请配置 GOOGLE_API_KEY")
    st.stop()

genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

# TS 代码中使用的模型 (经过验证可用的模型)
MODEL_NAME = "gemini-2.5-flash-image"

# --- 3. 核心逻辑复刻 (Porting geminiService.ts) ---

def pil_to_bytes(img: Image.Image, format="PNG") -> bytes:
    """将 PIL 图片转为字节流"""
    buf = io.BytesIO()
    img.save(buf, format=format)
    return buf.getvalue()

def resize_for_context(img: Image.Image, max_dim=2048) -> Image.Image:
    """
    复刻 TS: resizeForContext
    限制图片最大尺寸，保持比例
    """
    w, h = img.size
    if w > max_dim or h > max_dim:
        ratio = min(max_dim / w, max_dim / h)
        new_w = int(w * ratio)
        new_h = int(h * ratio)
        return img.resize((new_w, new_h), Image.Resampling.LANCZOS)
    return img

def extract_texture_patch(img: Image.Image) -> Image.Image:
    """
    复刻 TS: extractTexturePatch (核心技术!)
    提取图片中心 50% 区域作为纹理锚点
    """
    w, h = img.size
    crop_w = int(w * 0.5)
    crop_h = int(h * 0.5)
    
    left = (w - crop_w) // 2
    top = (h - crop_h) // 2
    right = left + crop_w
    bottom = top + crop_h
    
    return img.crop((left, top, right, bottom))

def invert_mask_image(mask_img: Image.Image) -> Image.Image:
    """
    复刻 TS: invertMask
    反转蒙版颜色 (如果你上传的是黑底白主体，需要反转)
    """
    # 确保是灰度或RGB
    if mask_img.mode == 'RGBA':
        r, g, b, a = mask_img.split()
        mask_img = a # 使用 alpha 通道作为蒙版
    
    return ImageOps.invert(mask_img.convert("L"))

def generate_image(
    original_img: Image.Image,
    prompt: str, # Changed string to str
    mode: str,
    image_count: int = 1,
    secondary_img: Image.Image = None,
    inpainting_region: str = 'inside',
    negative_prompt: str = '' # Changed string to str
):
    """
    复刻 TS: editImage 核心逻辑
    """
    
    # 1. 预处理：纹理锚定 (Texture Anchoring)
    # TS: const texturePatch = extractTexturePatch(sourceImgObj);
    texture_patch = extract_texture_patch(original_img)
    
    # TS: const cleanSource = await processImageStandard(originalImage, 2560, useHD);
    clean_source = resize_for_context(original_img, 2560)
    
    parts = []
    final_prompt = prompt
    
    # 组装 Negative Prompt
    if negative_prompt:
        final_prompt += f"\n\nNEGATIVE CONSTRAINT (Do NOT include): {negative_prompt}."

    # 根据模式构建 Payload
    if mode == 'inpainting' and secondary_img:
        # 复刻 Inpainting 逻辑
        final_mask = secondary_img
        if inpainting_region == 'outside':
            final_mask = invert_mask_image(secondary_img)
        
        final_mask = resize_for_context(final_mask, 2560) # 确保尺寸一致

        task_prompt = f"""Task: High-Fidelity Inpainting with TEXTURE ANCHORING.
Input 1: Source Image.
Input 2: Mask (White=Edit).
Input 3: TEXTURE PATCH (Ground Truth).

Instructions:
1. Modify ONLY the white areas of the mask according to: "{prompt}".
2. TEXTURE CONSISTENCY: Use Input 3 to understand the grain, sharpness, and material quality of the original image. The generated area MUST match this texture.
3. Do not produce smooth "plastic" skin or flat fabrics.
4. Keep black areas pixel-perfect.
{f'AVOID: {negative_prompt}' if negative_prompt else ''}"""

        parts.append({"text": task_prompt})
        parts.append({"inline_data": {"mime_type": "image/png", "data": base64.b64encode(pil_to_bytes(clean_source)).decode('utf-8')}})
        parts.append({"inline_data": {"mime_type": "image/png", "data": base64.b64encode(pil_to_bytes(final_mask)).decode('utf-8')}})
        parts.append({"inline_data": {"mime_type": "image/png", "data": base64.b64encode(pil_to_bytes(texture_patch)).decode('utf-8')}})

    elif mode == 'pose' and secondary_img:
        # 复刻 Pose 逻辑
        clean_ref = resize_for_context(secondary_img, 2560)
        
        task_prompt = f"""Task: Pose Transfer with MATERIAL PRESERVATION.
Input 1: Character (Source).
Input 2: Pose Skeleton.
Input 3: TEXTURE PATCH (Fabric/Skin Detail).

Instructions:
1. Render the character from Input 1 in the pose of Input 2.
2. MATERIAL LOCK: Input 3 proves the exact material of the clothing. You MUST preserve this specific material physics.
3. Do not hallucinate generic clothing. Use the texture from Input 3.
4. Style/Lighting: "{prompt}".
{f'AVOID: {negative_prompt}' if negative_prompt else ''}"""

        parts.append({"text": task_prompt})
        parts.append({"inline_data": {"mime_type": "image/png", "data": base64.b64encode(pil_to_bytes(clean_source)).decode('utf-8')}})
        parts.append({"inline_data": {"mime_type": "image/png", "data": base64.b64encode(pil_to_bytes(clean_ref)).decode('utf-8')}})
        parts.append({"inline_data": {"mime_type": "image/png", "data": base64.b64encode(pil_to_bytes(texture_patch)).decode('utf-8')}})

    elif mode == 'general':
        # 复刻 Fusion / General Edit 逻辑
        task_prompt = ""
        
        if secondary_img:
            # Fusion Mode
            clean_ref = resize_for_context(secondary_img, 2560)
            task_prompt = f"""Task: High-Fidelity Image Fusion with TEXTURE ANCHORING.
Input 1: Primary Source (Subject Context).
Input 2: Secondary Source (Background/Style).
Input 3: TEXTURE PATCH (Ground Truth - DO NOT IGNORE).

CRITICAL INSTRUCTION:
1. ANCHORING: Input 3 represents the exact pixel quality and material texture you MUST output.
2. MATERIALITY: Preserve specular highlights. Do not flatten metallic textures.
3. FUSION: Combine Input 1's Subject with Input 2's Style, but enforce Input 3's Texture quality.

Prompt: {prompt}
{f'NEGATIVE CONSTRAINTS: {negative_prompt}' if negative_prompt else ''}"""
            
            parts.append({"text": task_prompt})
            parts.append({"inline_data": {"mime_type": "image/png", "data": base64.b64encode(pil_to_bytes(clean_source)).decode('utf-8')}})
            parts.append({"inline_data": {"mime_type": "image/png", "data": base64.b64encode(pil_to_bytes(clean_ref)).decode('utf-8')}})
            parts.append({"inline_data": {"mime_type": "image/png", "data": base64.b64encode(pil_to_bytes(texture_patch)).decode('utf-8')}})
            
        else:
            # Standard Edit
            task_prompt = f"""Edit instruction: {prompt}. Maintain photorealism.
{f'AVOID: {negative_prompt}' if negative_prompt else ''}"""
            parts.append({"text": task_prompt})
            parts.append({"inline_data": {"mime_type": "image/png", "data": base64.b64encode(pil_to_bytes(clean_source)).decode('utf-8')}})

    # 调用 Gemini API
    model = genai.GenerativeModel(MODEL_NAME)
    
    generated_images = []
    
    # 模拟 Batch (Python SDK 不支持一次返回多张，需要循环调用)
    for _ in range(image_count):
        response = model.generate_content(
            parts,
            generation_config={"response_modalities": ["IMAGE"], "temperature": 0.4}
        )
        
        # 解析结果
        if response.candidates and response.candidates[0].content.parts:
            part = response.candidates[0].content.parts[0]
            if part.inline_data:
                generated_images.append(part.inline_data.data) # Base64 bytes
            else:
                raise Exception("API 返回了文本而非图片 (可能是拒绝处理)")
        else:
            raise Exception("API 未返回有效内容")
            
    return generated_images

# --- 4. UI 界面 (复刻 App.tsx) ---

st.title("🚀 Fashion AI Studio (Python Port)")
st.caption(f"Powered by {MODEL_NAME} | Logic Ported from geminiService.ts")

# 初始化 Session State
if "generated_results" not in st.session_state:
    st.session_state["generated_results"] = []

# Mode Selector
mode_cols = st.columns(4)
modes = [
    ("general", "Global / Fusion"),
    ("inpainting", "Inpainting"),
    ("pose", "Pose Control"),
    ("upscale", "Upscale HD (TBD)")
]

# 简单的模式选择 UI
selected_mode = st.radio("选择模式 (Mode)", [m[1] for m in modes], horizontal=True)
current_mode_key = [m[0] for m in modes if m[1] == selected_mode][0]

col1, col2 = st.columns([5, 5])

with col1:
    st.markdown('<div class="step-card">', unsafe_allow_html=True)
    st.subheader("1. 输入 (Inputs)")
    
    # 主图上传
    source_file = st.file_uploader("上传主图 (Source)", type=["jpg", "png", "webp"], key="src")
    source_img = None
    if source_file:
        source_img = Image.open(source_file).convert("RGB")
        st.image(source_img, caption="Source Image", width=200)

    # 辅助图上传 (根据模式)
    secondary_img = None
    if current_mode_key == 'inpainting':
        st.markdown("---")
        mask_file = st.file_uploader("上传蒙版 (Mask)", type=["jpg", "png", "webp"], key="mask")
        if mask_file:
            secondary_img = Image.open(mask_file).convert("L") # 转灰度
            st.image(secondary_img, caption="Mask", width=200)
            
        inpainting_region = st.radio("重绘区域", ["inside (蒙版内部)", "outside (蒙版外部/背景)"], index=0)
        
    elif current_mode_key == 'pose':
        st.markdown("---")
        pose_file = st.file_uploader("上传骨架图 (Pose)", type=["jpg", "png", "webp"], key="pose")
        if pose_file:
            secondary_img = Image.open(pose_file).convert("RGB")
            st.image(secondary_img, caption="Pose Skeleton", width=200)
            
    elif current_mode_key == 'general':
        st.markdown("---")
        ref_file = st.file_uploader("参考图 (Reference - 可选)", type=["jpg", "png", "webp"], key="ref")
        if ref_file:
            secondary_img = Image.open(ref_file).convert("RGB")
            st.image(secondary_img, caption="Reference Image", width=200)
            
    st.markdown('</div>', unsafe_allow_html=True)

    # Prompt 区域
    st.markdown('<div class="step-card">', unsafe_allow_html=True)
    st.subheader("2. 指令 (Instruction)")
    
    prompt_input = st.text_area(
        "提示词 (Prompt)", 
        value="Replace the background with a high-end studio setting. KEEP the metallic texture exactly as is.", 
        height=120
    )
    
    negative_input = st.text_input("负向提示词 (Negative)", value="blur, bad anatomy, text, watermark")
    
    img_count = st.slider("生成数量", 1, 4, 1)
    
    generate_btn = st.button("🚀 开始生成 (Generate)", type="primary")
    st.markdown('</div>', unsafe_allow_html=True)

with col2:
    st.subheader("3. 结果 (Result)")
    
    if generate_btn:
        if not source_img:
            st.warning("请先上传主图！")
        else:
            with st.spinner(f"正在调用 {MODEL_NAME} 进行生成... (纹理锚定已启用)"):
                try:
                    # 转换 inpainting_region 参数格式
                    region_param = 'inside' if 'inside' in (locals().get('inpainting_region', '')) else 'outside'
                    
                    results = generate_image(
                        original_img=source_img,
                        prompt=prompt_input,
                        mode=current_mode_key,
                        image_count=img_count,
                        secondary_img=secondary_img,
                        inpainting_region=region_param,
                        negative_prompt=negative_input
                    )
                    
                    st.session_state["generated_results"] = results
                    st.success(f"成功生成 {len(results)} 张图片！")
                    
                except Exception as e:
                    st.error(f"生成失败: {e}")
                    st.error("请检查 API Key 权限或尝试简化 Prompt。")

    # 展示结果
    if st.session_state["generated_results"]:
        for i, b64_data in enumerate(st.session_state["generated_results"]):
            try:
                img_data = base64.b64decode(b64_data)
                st.image(img_data, caption=f"Result {i+1}", use_column_width=True)
                
                # 下载按钮
                st.download_button(
                    f"📥 下载 Result {i+1}",
                    data=img_data,
                    file_name=f"fashion_ai_result_{i+1}.png",
                    mime="image/png"
                )
            except Exception as e:
                st.error(f"结果 {i+1} 显示失败: {e}")
