import streamlit as st
from PIL import Image
import sys
import os
import time
import random

# --- 路径环境设置 ---
current_script_path = os.path.abspath(__file__)
pages_dir = os.path.dirname(current_script_path)
root_dir = os.path.dirname(pages_dir)
if root_dir not in sys.path:
    sys.path.append(root_dir)

try:
    import auth
    from app_utils.history_manager import HistoryManager
    from app_utils.ui_components import render_history_sidebar
    from app_utils.image_processing import create_preview_thumbnail, process_image_for_download
    
    # 引入服务引擎
    from services.image_engine import ImageGenEngine
    # 只需要生图引擎，批量变体不需要复杂的 LLM 推理，靠 Prompt 即可
except ImportError as e:
    st.error(f"❌ 核心模块导入失败: {e}")
    st.stop()

# --- 1. 页面配置 ---
st.set_page_config(page_title="Batch Variant Factory", page_icon="🔄", layout="wide")

# --- CSS: 优化网格显示 ---
st.markdown("""
    <style>
    div[data-testid="column"] img {
        border-radius: 8px;
        transition: transform 0.2s;
    }
    div[data-testid="column"] img:hover {
        transform: scale(1.02);
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    }
    </style>
""", unsafe_allow_html=True)

# --- 2. 初始化 ---
if 'auth' in sys.modules and not auth.check_password():
    st.stop()

if "batch_service_ready" not in st.session_state:
    api_key = st.secrets.get("GOOGLE_API_KEY")
    if not api_key:
        st.error("❌ 未找到 GOOGLE_API_KEY")
        st.stop()
    st.session_state.img_gen = ImageGenEngine(api_key)
    st.session_state.history = HistoryManager()
    st.session_state.batch_results = [] # 存储批量结果
    st.session_state.batch_service_ready = True

img_gen = st.session_state.img_gen
history = st.session_state.history

# --- 3. 常量定义 ---
# 批量模式专属模型列表，默认 Flash 在第一位
BATCH_MODELS = [
    "models/gemini-2.5-flash-image",         # 🚀 默认：极速、便宜、适合批量
    "models/gemini-3-pro-image-preview",  # 🎨 Pro：高质量，但慢且贵
]

# 比例映射
RATIO_MAP = {
    "Original (原图比例)": "",
    "1:1 (Square)": ", crop to 1:1 square aspect ratio",
    "4:3 (Landscape)": ", 4:3 landscape aspect ratio", 
    "16:9 (Wide)": ", 16:9 cinematic aspect ratio",
    "9:16 (Portrait)": ", 9:16 portrait aspect ratio"
}

# --- 4. 侧边栏 ---
with st.sidebar:
    st.title("🗂️ 变体历史")
    render_history_sidebar(history)

# --- 5. 主逻辑区 ---
st.title("🔄 批量变体工厂 (Batch Factory)")
st.caption("专为电商打造的快速裂变工具。上传一张产品图，快速生成最多 20 张不同背景/细节的变体。")

c_config, c_view = st.columns([1, 1.5], gap="large")

with c_config:
    st.subheader("🛠️ 生产线配置")
    
    # A. 核心输入
    uploaded_file = st.file_uploader("上传产品原图", type=["jpg", "png", "webp"], help="仅支持单张图片进行批量裂变")
    
    ref_image = None
    if uploaded_file:
        ref_image = Image.open(uploaded_file)
        # 显示小图预览
        st.image(ref_image, width=200, caption="Base Product")

    # B. 变体指令
    prompt_direction = st.text_area(
        "变体改造指令", 
        height=100,
        placeholder="例如：把背景换成不同的家居室内场景，保持沙发主体不变，光线柔和。",
        help="告诉 AI 你希望哪些地方发生变化。未提及的部分 AI 会尽量保持原状。"
    )

    # C. 参数控制
    st.markdown("#### ⚙️ 生产参数")
    
    col_m1, col_m2 = st.columns(2)
    selected_model = col_m1.selectbox(
        "⚡️ 选择模型", 
        BATCH_MODELS, 
        index=0, 
        help="默认使用 Flash 模型以获得最快的生成速度。"
    )
    
    selected_ratio = col_m2.selectbox(
        "📐 输出比例", 
        list(RATIO_MAP.keys()),
        index=0
    )

    # --- ⚠️ 核心逻辑：Flash 模型比例警告 ---
    is_flash = "flash" in selected_model
    is_safe_ratio = selected_ratio.startswith("Original") or selected_ratio.startswith("1:1")
    
    if is_flash and not is_safe_ratio:
        st.warning("⚠️ **兼容性警告**：\nFlash 模型目前仅支持 'Original' 或 '1:1' 比例。选择其他比例可能会导致画面拉伸或忽略比例指令。\n建议切换到 Pro 模型或使用 1:1。", icon="🚧")

    col_p1, col_p2 = st.columns(2)
    batch_count = col_p1.slider("🔢 生成数量", 1, 20, 4, help="一次性生成的变体数量，最大 20 张。")
    # 变体差异度控制 Temperature
    variance = col_p2.select_slider(
        "🔀 变体差异度", 
        options=["微调 (Low)", "标准 (Med)", "脑洞 (High)"], 
        value="标准 (Med)",
        help="控制每张图之间的区别大小。\n- 微调：几乎一样，仅光影微变。\n- 脑洞：背景和构图变化巨大。"
    )
    
    # 映射 Temperature
    temp_map = {"微调 (Low)": 0.3, "标准 (Med)": 0.65, "脑洞 (High)": 0.95}
    temperature = temp_map[variance]

    # D. 执行
    btn_disabled = not (uploaded_file and prompt_direction)
    if st.button("🚀 启动批量生产", type="primary", disabled=btn_disabled, use_container_width=True):
        st.session_state.batch_results = [] # 清空
        
        # 准备进度条
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # 准备图片数据
        ref_image.seek(0)
        
        # 批次处理逻辑
        for i in range(batch_count):
            status_text.text(f"正在生产变体 {i+1} / {batch_count} ...")
            
            # 💡 核心技巧：通过随机 Seed 强制产生变体
            # 即使 Prompt 一样，不同的 Seed + High Temperature 也会产生不同结果
            random_seed = random.randint(1, 1000000)
            
            # 构建差异化 Prompt (可选：可以在 Prompt 里注入一点噪声)
            # 比如 "Variation {i}" 这种没什么实际意义的词有时候能打破缓存
            final_prompt = f"{prompt_direction}"
            
            try:
                # 调用生图接口
                img_bytes = img_gen.generate(
                    prompt=final_prompt,
                    model_name=selected_model,
                    ref_image=ref_image,
                    ratio_suffix=RATIO_MAP[selected_ratio],
                    seed=random_seed,
                    creativity=temperature, # 使用差异度控制
                    safety_level="Standard"
                )
                
                if img_bytes:
                    st.session_state.batch_results.append(img_bytes)
                    # 自动保存到历史
                    history.add(img_bytes, f"Batch-{i+1}", prompt_direction[:20])
                else:
                    st.warning(f"第 {i+1} 张生成失败 (可能被安全拦截)")
                    
            except Exception as e:
                st.error(f"Error on image {i+1}: {e}")
            
            # 更新进度
            progress_bar.progress((i + 1) / batch_count)
            # ⚠️ 简单的限流：如果是 Flash 模型，跑得太快可能会 429，这里稍微 sleep 一下
            # Pro 模型本来就慢，通常不需要 sleep
            if "flash" in selected_model:
                time.sleep(1.5) 
        
        status_text.text("✅ 批量生产完成！")
        time.sleep(1)
        status_text.empty()
        st.rerun()

# --- 右侧：网格预览区 ---
with c_view:
    st.subheader(f"📦 产出结果 ({len(st.session_state.batch_results)})")
    
    if not st.session_state.batch_results:
        st.info("👈 在左侧配置并启动生产线，结果将以网格形式展示在这里。")
        st.markdown(
            '<div style="border: 2px dashed #ddd; height: 400px; display: flex; align-items: center; justify-content: center; color: #888;">Production Line Idle...</div>', 
            unsafe_allow_html=True
        )
    else:
        # 网格布局：每行 3 张 (宽屏下效果好)
        cols = st.columns(3)
        for idx, img_bytes in enumerate(st.session_state.batch_results):
            col = cols[idx % 3] # 循环放入列中
            with col:
                thumb = create_preview_thumbnail(img_bytes, 400)
                st.image(thumb, use_container_width=True, caption=f"Variant {idx+1}")
                
                # 单图下载
                final_bytes, mime = process_image_for_download(img_bytes, "JPEG")
                st.download_button(
                    "📥", 
                    data=final_bytes, 
                    file_name=f"variant_{idx+1}.jpg", 
                    mime=mime, 
                    key=f"b_dl_{idx}",
                    help="下载此变体"
                )
