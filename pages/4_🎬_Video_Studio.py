import streamlit as st
import replicate
import time
import sys
import os

# --- 0. 引入门禁系统 ---
sys.path.append(os.path.abspath('.'))
try:
    import auth
except ImportError:
    pass 

# --- 1. 页面配置 ---
st.set_page_config(page_title="视频工场", page_icon="🎬", layout="wide")

# 安全检查
if 'auth' in sys.modules:
    if not auth.check_password():
        st.stop()

# --- 2. 验证 Keys ---
if "REPLICATE_API_TOKEN" not in st.secrets:
    st.error("❌ 未找到 Replicate API Token")
    st.stop()

# --- 3. 侧边栏：视频参数 ---
with st.sidebar:
    st.title("🎬 视频参数")
    st.info("当前引擎: Minimax Video-01 (商业级)")
    
    st.warning("⚠️ 成本预警：视频生成较贵 (约 $0.5/次)，且耗时较长 (2-3分钟)。")
    
    # 视频模型参数
    fps = st.slider("帧率 (FPS)", 24, 30, 25)
    motion_bucket = st.slider("运动幅度 (Motion)", 1, 10, 5, help="数值越大，画面动得越厉害，但也更容易变形。")

# --- 4. 主界面 ---
st.title("🎬 亚马逊 AI 视频工场 (Beta)")
st.caption("上传静态产品图 -> 生成 5-6秒 4K 商业展示视频")

col1, col2 = st.columns([4, 6])

with col1:
    st.subheader("1. 导演控制台")
    
    # 上传首帧图
    uploaded_file = st.file_uploader("上传首帧图片 (视频将从这张图开始)", type=["jpg", "png", "webp"])
    
    if uploaded_file:
        st.image(uploaded_file, caption="首帧预览", use_column_width=True)
    
    # 运镜提示词
    prompt = st.text_area(
        "运镜与动作描述 (英文)",
        placeholder="例如: The camera slowly zooms in on the product, cinematic lighting, 4k, high quality...",
        height=120,
        help="告诉 AI 镜头怎么动，或者是产品怎么动（比如'旋转'、'有烟雾缭绕'）。"
    )

with col2:
    st.subheader("2. 样片监视器")
    
    generate_btn = st.button("🎥 Action! 开始生成视频", type="primary")
    
    if generate_btn:
        if not uploaded_file:
            st.warning("请先上传一张首帧图片！")
        elif not prompt:
            st.warning("请填写动作描述！")
        else:
            with st.spinner("🎬 正在拍摄中... 这可能需要几分钟，请耐心等待..."):
                try:
                    # 调用 Minimax Video (通过 Replicate)
                    # 注意：模型名称可能会更新，这里使用目前可用的版本
                    output = replicate.run(
                        "minimax/video-01",
                        input={
                            "prompt": prompt,
                            "first_frame_image": uploaded_file,
                            "fps": fps,
                            "motion_bucket_id": motion_bucket * 12 # 简单映射
                        }
                    )
                    
                    # Minimax 返回的是视频 URL
                    video_url = str(output)
                    
                    st.success("✅ 视频生成完成！")
                    st.video(video_url)
                    st.markdown(f"### [📥 点击下载视频文件]({video_url})")
                    
                except Exception as e:
                    st.error(f"生成失败: {e}")
                    st.info("💡 提示：如果是模型报错，可能是图片比例不被支持，试着上传 16:9 或 1:1 的标准图片。")

st.markdown("---")
with st.expander("📋 视频生成技巧"):
    st.markdown("""
    1. **首帧图很重要**：视频的质量很大程度上取决于你上传的那张图。建议先在“图片工场”生成一张完美的主图，再拿来这里做视频。
    2. **动作幅度**：不要贪心。描述微小的动作（如“缓慢变焦”、“光影扫过”、“轻微旋转”）效果最好。剧烈的动作容易让产品变形。
    3. **耐心**：视频生成是算力密集型任务，如果网页卡住，请不要频繁刷新。
    """)
