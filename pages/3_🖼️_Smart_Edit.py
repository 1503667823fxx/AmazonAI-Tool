import streamlit as st
import replicate
import google.generativeai as genai
from PIL import Image, ImageOps
import io
import sys
import os
import requests
import time

# --- 0. 引入门禁系统 ---
sys.path.append(os.path.abspath('.'))
try:
    import auth
except ImportError:
    pass 

# --- 1. 页面配置 ---
st.set_page_config(page_title="智能图生图", page_icon="🖼️", layout="wide")

# 安全检查
if 'auth' in sys.modules:
    if not auth.check_password():
        st.stop()

# --- 自定义 CSS ---
st.markdown("""
<style>
    .stButton button {width: 100%; border-radius: 8px;}
    .step-card {
        background-color: #f0f8ff;
        padding: 15px;
        border-radius: 8px;
        border-left: 5px solid #0068c9;
        margin-bottom: 15px;
    }
    .info-box {
        background-color: #fff3cd;
        padding: 10px;
        border-radius: 5px;
        font-size: 14px;
        color: #856404;
        margin-bottom: 10px;
    }
</style>
""", unsafe_allow_html=True)

# --- 2. 验证 Keys ---
if "REPLICATE_API_TOKEN" not in st.secrets:
    st.error("❌ 未找到 Replicate API Token")
    st.stop()
if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

# --- 3. 常量 ---
UNIVERSAL_QUALITY_PROMPT = ", commercial photography, 8k resolution, photorealistic, highly detailed, cinematic lighting, depth of field, masterpiece, sharp focus"

# --- 4. 辅助函数 ---
def download_image(url, filename):
    st.markdown(f"### [📥 点击下载 {filename}]({url})")

def get_pro_vision_model():
    """使用 3.0 Pro 进行深度构思"""
    return genai.GenerativeModel('gemini-3-pro-preview') 

def process_rembg_mask(image_file):
    """
    核心函数：调用 Rembg 抠图并生成反向蒙版 (用于 Flux Fill)
    Flux Fill 逻辑: 白色 = 重绘区域(背景), 黑色 = 保护区域(主体)
    """
    try:
        # 1. 调用抠图
        output_url = replicate.run("cjwbw/rembg:1.4", input={"image": image_file})
        response = requests.get(str(output_url))
        no_bg_image = Image.open(io.BytesIO(response.content))
        
        # 2. 提取 Alpha 通道
        if no_bg_image.mode == 'RGBA':
            alpha = no_bg_image.split()[-1]
        else:
            alpha = Image.new("L", no_bg_image.size, 255)
            
        # 3. 反转 Alpha (主体变黑，背景变白)
        # Rembg 默认: 主体255(白), 背景0(黑)
        # 我们需要: 主体0(黑/保护), 背景255(白/重绘)
        mask = ImageOps.invert(alpha)
        
        return no_bg_image, mask
    except Exception as e:
        st.error(f"抠图处理失败: {e}")
        return None, None

# --- 5. 主界面 ---
st.title("🖼️ 智能场景变换 (Smart Scene Swap)")
st.info("🔥 **Pro 模式**：系统会自动锁定产品/模特像素，只重绘背景，确保 **产品 100% 不变**。")

# 初始化 Session
if "hybrid_instruction" not in st.session_state:
    st.session_state["hybrid_instruction"] = ""
if "generated_image_urls" not in st.session_state:
    st.session_state["generated_image_urls"] = []

col1, col2 = st.columns([5, 5])

# === 左侧：构思 (Brain) ===
with col1:
    st.markdown('<div class="step-card">Step 1: 上传与构思</div>', unsafe_allow_html=True)
    ref_img = st.file_uploader("上传原图", type=["jpg", "png", "webp"], key="smart_up")
    
    if ref_img:
        st.image(ref_img, width=200, caption="原图")
        
        # 任务类型
        task_type = st.radio(
            "生成方向", 
            ["🏡 场景图 (Lifestyle)", "✨ 展示图 (Creative)", "🔍 创意变体 (Variation)"], 
            horizontal=True
        )
        
        # 用户想法
        user_idea = st.text_area(
            "您的具体想法 (支持中文)", 
            height=80, 
            placeholder="例如：把背景改成温馨的圣诞节客厅，壁炉在燃烧，给产品打暖色光..."
        )
        
        # 生成指令
        if st.button("🧠 Gemini 编写指令", type="secondary"):
            if not user_idea:
                st.warning("请先写下您的想法！")
            else:
                with st.spinner("Gemini 3.0 Pro 正在深度分析..."):
                    try:
                        img_obj = Image.open(ref_img)
                        # 缩图加速
                        img_small = img_obj.copy()
                        img_small.thumbnail((1024, 1024))
                        
                        model = get_pro_vision_model()
                        prompt = f"""
                        你是一个世界顶级的商业摄影提示词专家。
                        
                        【任务】
                        我们即将使用 "Inpainting" (局部重绘) 技术，保留产品主体，只替换背景。
                        请基于用户需求："{user_idea}"，写一段专注于**描述新背景和光影**的英文 Prompt。
                        
                        【注意】
                        1. **不要**过多描述产品本身（因为产品会被蒙版保护起来）。
                        2. **重点描述**：背景环境、材质、氛围、光线方向（如何打在产品上）。
                        3. **风格**：8k分辨率、超写实商业摄影。
                        
                        【输出】
                        直接输出一段完整的英文 Prompt。
                        """
                        
                        response = model.generate_content([prompt, img_small])
                        st.session_state["hybrid_instruction"] = response.text
                        st.success("✅ 指令已生成！请在右侧确认。")
                        # 强制刷新
                        time.sleep(0.1)
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"Gemini 分析失败: {e}")

# === 右侧：生成 (Hands) ===
with col2:
    st.markdown('<div class="step-card">Step 2: 生成与精修</div>', unsafe_allow_html=True)
    
    # 指令确认
    final_prompt = st.text_area(
        "最终绘画指令 (英文)", 
        value=st.session_state["hybrid_instruction"], 
        height=150,
        help="Flux Fill 将根据这段话填充背景。"
    )
    
    st.markdown('<div class="info-box">💡 提示：系统将自动抠图并保护主体。如果生成结果边缘不干净，请尝试上传更清晰的白底图。</div>', unsafe_allow_html=True)

    # 生成按钮
    if st.button("🚀 开始生成 (Lock Subject & Fill Background)", type="primary"):
        if not ref_img or not final_prompt:
            st.warning("请先生成指令！")
        else:
            status_box = st.empty()
            try:
                # 1. 自动抠图
                status_box.info("✂️ 正在自动抠图，锁定产品主体...")
                ref_img.seek(0)
                _, mask_img = process_rembg_mask(ref_img)
                
                if not mask_img:
                    st.error("抠图失败，无法识别主体。")
                    st.stop()
                
                # 准备上传数据 (Bytes)
                ref_img.seek(0)
                img_bytes = io.BytesIO()
                # 转换为 RGB 避免格式兼容问题
                Image.open(ref_img).convert("RGB").save(img_bytes, format="PNG")
                
                mask_bytes = io.BytesIO()
                mask_img.save(mask_bytes, format="PNG")
                
                # 2. 调用 Flux Fill (填充模型)
                status_box.info("🎨 Flux Fill Pro 正在重绘背景 (主体已保护)...")
                
                output = replicate.run(
                    "black-forest-labs/flux-fill-pro", 
                    input={
                        "image": img_bytes,
                        "mask": mask_bytes, # 传入蒙版
                        "prompt": final_prompt + UNIVERSAL_QUALITY_PROMPT,
                        "output_format": "jpg",
                        "output_quality": 100,
                        "steps": 50, # 提高步数保证质量
                        "guidance": 60 # 提高引导值，让AI更听Prompt的话
                    }
                )
                
                # 强制转换为字符串列表
                if isinstance(output, list):
                    st.session_state["generated_image_urls"] = [str(url) for url in output]
                else:
                    st.session_state["generated_image_urls"] = [str(output)]
                    
                status_box.success("✅ 生成完成！")
                
            except Exception as e:
                status_box.error(f"Flux 生成失败: {e}")

    # 结果展示
    if st.session_state["generated_image_urls"]:
        st.divider()
        st.markdown("#### 🎉 生成结果")
        for i, url in enumerate(st.session_state["generated_image_urls"]):
            st.image(url, caption=f"结果 {i+1} (主体像素 100% 保留)", use_column_width=True)
            download_image(url, f"result_{i+1}.jpg")
