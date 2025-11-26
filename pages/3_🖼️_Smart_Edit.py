import streamlit as st
import replicate
import google.generativeai as genai
from PIL import Image
import io
import sys
import os
import time

# --- 0. 基础设置与门禁系统 ---
sys.path.append(os.path.abspath('.'))
try:
    import auth
except ImportError:
    pass 

# 页面配置
st.set_page_config(page_title="Fashion AI Studio", page_icon="🚀", layout="wide")

# 安全检查
if 'auth' in sys.modules:
    if not auth.check_password():
        st.stop()

# --- 1. 关键修复：API 密钥配置 ---
if "REPLICATE_API_TOKEN" in st.secrets:
    os.environ["REPLICATE_API_TOKEN"] = st.secrets["REPLICATE_API_TOKEN"]
else:
    st.error("❌ 错误：未在 secrets.toml 中找到 REPLICATE_API_TOKEN")
    st.stop()

if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
else:
    st.warning("⚠️ 警告：未找到 GOOGLE_API_KEY，AI 构思功能将不可用。")

# --- 2. 样式与常量 ---
st.markdown("""
<style>
    .stButton button {width: 100%; border-radius: 8px; font-weight: bold;}
    .step-card {
        background-color: #f8f9fa;
        padding: 20px;
        border-radius: 10px;
        border-left: 5px solid #ff4b4b;
        margin-bottom: 20px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
</style>
""", unsafe_allow_html=True)

UNIVERSAL_QUALITY_PROMPT = ", commercial photography, 8k resolution, photorealistic, highly detailed, cinematic lighting, depth of field, masterpiece, sharp focus"
UNIVERSAL_NEGATIVE_PROMPT = "blurry, low quality, distorted, ugly, pixelated, watermark, text, signature, bad anatomy, deformed, lowres, bad hands, mutation"

# --- 3. 新增功能：自动获取可用模型 ---
@st.cache_data(ttl=3600) # 缓存1小时，避免每次刷新都去请求谷歌
def get_available_gemini_models():
    """
    自动去问 Google：你现在有哪些模型可以用？
    只返回支持 generateContent (生成内容) 的模型
    """
    try:
        models = []
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                # 过滤掉一些太老的模型，只保留 gemini 系列
                if 'gemini' in m.name:
                    models.append(m.name)
        # 如果获取成功但列表为空，给个保底
        if not models:
            return ["models/gemini-1.5-flash-latest", "models/gemini-pro"]
        return sorted(models, reverse=True) # 让最新的模型排前面
    except Exception as e:
        # 如果报错（比如网络不通），返回一个最稳的默认列表
        return ["models/gemini-1.5-flash", "models/gemini-1.0-pro"]

# --- 4. 主界面逻辑 ---
st.title("🚀 Fashion AI Studio")
st.caption("双核驱动：Google Gemini (大脑) + Flux Pro (画笔)")

# 初始化 Session State
if "hybrid_instruction" not in st.session_state:
    st.session_state["hybrid_instruction"] = ""
if "generated_image_urls" not in st.session_state:
    st.session_state["generated_image_urls"] = []

col1, col2 = st.columns([1, 1], gap="large")

# === 左侧：上传与构思 (Gemini) ===
with col1:
    st.markdown('<div class="step-card">Step 1: 上传与 AI 构思</div>', unsafe_allow_html=True)
    
    # --- 新增：模型选择器 ---
    with st.expander("⚙️ Gemini 模型设置 (点此切换模型)", expanded=False):
        available_models = get_available_gemini_models()
        # 默认选中第一个
        selected_model_name = st.selectbox(
            "选择 Google 模型 (报错404请换一个)", 
            available_models,
            index=0 if available_models else 0
        )
        st.caption(f"当前使用: {selected_model_name}")

    ref_img = st.file_uploader("📤 上传原始图片", type=["jpg", "png", "webp"], key="upload_main")
    
    if ref_img:
        st.image(ref_img, width=300, caption="当前原图")
        
        task_type = st.radio("✨ 选择模式", ["换背景 (Scene Swap)", "创意重绘 (Creative)", "画质增强 (Upscale)"], horizontal=True)
        user_idea = st.text_area("💡 你的想法 (可选)", height=80, placeholder="例如：把背景改成极简主义风格的白色摄影棚，光线要柔和...")

        # 调用 Gemini 生成指令
        if st.button("🧠 让 Gemini 编写绘画指令", type="secondary"):
            with st.spinner(f"正在使用 {selected_model_name} 分析图片..."):
                try:
                    # 准备图片数据
                    ref_img.seek(0)
                    img_obj = Image.open(ref_img)
                    
                    # 使用用户选择的模型
                    model = genai.GenerativeModel(selected_model_name)
                    
                    prompt_req = f"""
                    你是一个商业摄影指导。请基于这张图片和用户需求："{user_idea}"，
                    写一段用于 FLUX 生图模型的英文提示词 (Prompt)。
                    
                    要求：
                    1. 描述主体(Subject)要忠实于原图。
                    2. 描述环境(Environment)要符合模式："{task_type}"。
                    3. 风格为 8k 超写实摄影。
                    
                    请直接输出英文 Prompt，不要包含任何解释或Markdown符号。
                    """
                    
                    # 调用 Google API
                    response = model.generate_content([prompt_req, img_obj])
                    
                    if response.text:
                        st.session_state["hybrid_instruction"] = response.text.strip()
                        st.success("✅ 指令已生成！")
                        time.sleep(0.5)
                        st.rerun()
                except Exception as e:
                    st.error(f"Gemini 调用失败: {e}")
                    st.info("💡 建议：点击上方的 '⚙️ Gemini 模型设置' 换一个模型试试 (推荐 gemini-1.5-flash)。")

# === 右侧：生成与结果 (Flux) ===
with col2:
    st.markdown('<div class="step-card">Step 2: Flux 极速绘图</div>', unsafe_allow_html=True)
    
    # 显示/编辑指令
    final_prompt = st.text_area(
        "🎨 最终绘画指令 (英文)", 
        value=st.session_state["hybrid_instruction"], 
        height=120,
        help="Flux 模型将严格按照这段文字进行绘制"
    )

    col_p1, col_p2 = st.columns(2)
    with col_p1:
        strength = st.slider("⚡ 重绘幅度 (Strength)", 0.1, 1.0, 0.80, help="数值越大，变化越大。0.8适合换背景，0.3适合微调。")
    with col_p2:
        num_outputs = st.number_input("🖼️ 生成数量", 1, 4, 1)

    # 调用 Replicate (Flux)
    if st.button("🚀 立即生成图片", type="primary"):
        if not ref_img or not final_prompt:
            st.warning("⚠️ 请先上传图片并生成指令！")
        else:
            with st.spinner("🎨 Flux 正在绘制中 (通常需要 5-10秒)..."):
                try:
                    ref_img.seek(0) # 关键：重置文件指针
                    
                    output = replicate.run(
                        "black-forest-labs/flux-dev",
                        input={
                            "prompt": final_prompt + UNIVERSAL_QUALITY_PROMPT,
                            "image": ref_img, 
                            "prompt_strength": strength, 
                            "go_fast": True,
                            "num_outputs": num_outputs,
                            "output_format": "jpg",
                            "output_quality": 100,
                            "negative_prompt": UNIVERSAL_NEGATIVE_PROMPT
                        }
                    )
                    
                    urls = []
                    if isinstance(output, list):
                        urls = [str(url) for url in output]
                    else:
                        urls = [str(output)]
                    
                    st.session_state["generated_image_urls"] = urls
                    st.success("🎉 生成成功！")
                    
                except Exception as e:
                    st.error(f"Flux 生成失败: {str(e)}")
                    st.info("💡 如果显示 401 Unauthorized，请检查 .streamlit/secrets.toml 里的 REPLICATE_API_TOKEN")

    # 展示结果
    if st.session_state["generated_image_urls"]:
        st.divider()
        st.subheader("👀 生成结果")
        for i, url in enumerate(st.session_state["generated_image_urls"]):
            st.image(url, caption=f"Result {i+1}", use_column_width=True)
            st.markdown(f"[📥 点击下载大图]({url})")
