import streamlit as st
import replicate
import google.generativeai as genai
from PIL import Image
import sys
import os

# --- 0. 引入门禁系统 ---
sys.path.append(os.path.abspath('.'))
try:
    import auth
except ImportError:
    pass 

# --- 1. 页面配置 ---
st.set_page_config(page_title="图片工场", page_icon="🎨", layout="wide")

# 安全检查
if 'auth' in sys.modules:
    if not auth.check_password():
        st.stop()

# --- 自定义 CSS ---
st.markdown("""
<style>
    .stButton button {width: 100%; border-radius: 8px;}
    .stImage {border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);}
</style>
""", unsafe_allow_html=True)

# --- 2. 验证 Keys ---
if "REPLICATE_API_TOKEN" not in st.secrets:
    st.error("❌ 未找到 Replicate API Token，请在 .streamlit/secrets.toml 中配置！")
    st.stop()

if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

# --- 3. 侧边栏：绘图参数 ---
with st.sidebar:
    st.title("📸 图片参数设置")
    st.info("当前模式：FLUX.1 Pro (顶级商业画质)")
    
    aspect_ratio_label = st.selectbox(
        "画幅比例",
        ["1:1 (主图/正方形)", "16:9 (Banner/电脑壁纸)", "9:16 (手机竖屏/海报)", "4:5 (Ins/小红书)", "3:2 (常规摄影)"]
    )
    target_ratio = aspect_ratio_label.split(" ")[0]
    
    output_format = st.radio("输出格式", ["jpg", "png"], horizontal=True)
    safety_tolerance = st.slider("安全过滤等级", 1, 5, 2)

# --- 4. 主界面 ---
st.title("🎨 亚马逊 AI 图片工场")
st.caption("Powered by FLUX.1 Pro | 专注高转化场景图")

col1, col2 = st.columns([4, 6])

with col1:
    st.subheader("1. 构思与指令")
    
    uploaded_file = st.file_uploader("上传参考图 (Gemini将提取产品特征)", type=["jpg", "png", "webp"])
    if uploaded_file:
        img = Image.open(uploaded_file)
        st.image(img, width=200)
        
    scene_desc = st.text_area("场景描述 (例如: 放在大理石台面上，晨光，旁边有咖啡)", height=100)
    
    if st.button("✨ Gemini 编写专业指令 (Magic Prompt)", type="secondary"):
        if not uploaded_file:
            st.warning("请先上传产品参考图！")
        else:
            with st.spinner("Gemini 正在观察产品并构思光影..."):
                try:
                    model = genai.GenerativeModel('gemini-3-pro-preview')
                    prompt = f"""
                    你是一个商业摄影师。请根据这张产品图和用户描述: "{scene_desc}"，写一个英文绘画Prompt。
                    要求：
                    1. 极其详细地描述产品外观（颜色、材质、形状）。
                    2. 设定高级的商业摄影光影 (Soft studio lighting, cinematic)。
                    3. 包含画质词: 8k, photorealistic, ultra-detailed.
                    4. 直接输出英文Prompt，不要解释。
                    """
                    response = model.generate_content([prompt, img])
                    st.session_state["flux_prompt"] = response.text
                    st.success("指令已生成！")
                except Exception as e:
                    st.error(f"Gemini 错误: {e}")

    final_prompt = st.text_area("最终生成指令 (英文)", value=st.session_state.get("flux_prompt", ""), height=150)

with col2:
    st.subheader("2. 渲染结果")
    if st.button("🚀 开始生成图片 (Run FLUX)", type="primary"):
        if not final_prompt:
            st.warning("指令不能为空")
        else:
            with st.spinner("🎨 FLUX 正在渲染... (约10-15秒)"):
                try:
                    output = replicate.run(
                        "black-forest-labs/flux-1.1-pro",
                        input={
                            "prompt": final_prompt,
                            "aspect_ratio": target_ratio,
                            "output_format": output_format,
                            "safety_tolerance": safety_tolerance
                        }
                    )
                    image_url = str(output)
                    st.image(image_url, use_column_width=True)
                    st.success("✅ 生成成功")
                    st.markdown(f"[📥 下载高清原图]({image_url})")
                except Exception as e:
                    st.error(f"生成失败: {e}")
