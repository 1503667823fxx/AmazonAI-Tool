import streamlit as st
import replicate
import google.generativeai as genai
from PIL import Image
import io
import sys
import os
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
UNIVERSAL_NEGATIVE_PROMPT = "blurry, low quality, distorted, ugly, pixelated, watermark, text, signature, bad anatomy, deformed, lowres, bad hands, mutation"

# --- 4. 辅助函数 ---
def download_image(url, filename):
    st.markdown(f"### [📥 点击下载 {filename}]({url})")

def get_pro_vision_model():
    """使用 3.0 Pro 进行深度构思"""
    return genai.GenerativeModel('gemini-3-pro-preview') 

# --- 5. 主界面 ---
st.title("🖼️ 智能场景变换 (Smart Scene Swap)")
st.info("工作流：Gemini 3.0 Pro (构思指令) ➡ Flux.1 Pro (光影重绘)")

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
                        请观察图片主体，结合用户需求："{user_idea}" 和任务类型："{task_type}"。
                        
                        【任务】
                        写一段用于 FLUX AI 绘画模型的英文提示词。
                        
                        【要求】
                        1. **Subject**: 准确描述产品主体（保留其核心特征）。
                        2. **Environment**: 详细描述新的背景环境。
                        3. **Style**: 8k分辨率、超写实商业摄影。
                        
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
        help="Flux 将根据这段话进行绘制。"
    )
    
    # 参数
    col_p1, col_p2 = st.columns(2)
    with col_p1:
        strength = st.slider("重绘幅度 (Strength)", 0.1, 1.0, 0.75, help="0.75 适合换背景。数值越低越像原图。")
    with col_p2:
        num_outputs = st.number_input("生成数量", 1, 4, 1)

    # 生成按钮
    if st.button("🚀 开始生成 (Run Flux)", type="primary"):
        if not ref_img or not final_prompt:
            st.warning("请先生成指令！")
        else:
            with st.spinner("🎨 Flux 正在重绘..."):
                try:
                    ref_img.seek(0)
                    
                    output = replicate.run(
                        "black-forest-labs/flux-dev", 
                        input={
                            "prompt": final_prompt + UNIVERSAL_QUALITY_PROMPT,
                            "image": ref_img,
                            "prompt_strength": 1 - strength,
                            "go_fast": True,
                            "num_outputs": num_outputs,
                            "output_format": "jpg",
                            "output_quality": 100,
                            "negative_prompt": UNIVERSAL_NEGATIVE_PROMPT
                        }
                    )
                    
                    # 【关键修复】强制转换为字符串列表
                    # Replicate 返回的是对象，Streamlit 直接读会报错 AttributeError
                    if isinstance(output, list):
                        st.session_state["generated_image_urls"] = [str(url) for url in output]
                    else:
                        st.session_state["generated_image_urls"] = [str(output)]
                        
                    st.success("✅ 生成完成！")
                    
                except Exception as e:
                    st.error(f"Flux 生成失败: {e}")

    # 结果展示
    if st.session_state["generated_image_urls"]:
        st.divider()
        st.markdown("#### 🎉 生成结果")
        for i, url in enumerate(st.session_state["generated_image_urls"]):
            # 这里的 url 已经是纯字符串了，不会再报 AttributeError
            st.image(url, caption=f"结果 {i+1}", use_column_width=True)
            download_image(url, f"result_{i+1}.jpg")
