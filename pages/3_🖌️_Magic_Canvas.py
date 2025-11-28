import streamlit as st
from PIL import Image, ImageOps
import numpy as np
import io
import sys
import os
import time

# --- 路径环境设置 ---
current_script_path = os.path.abspath(__file__)
pages_dir = os.path.dirname(current_script_path)
root_dir = os.path.dirname(pages_dir)
if root_dir not in sys.path:
    sys.path.append(root_dir)

try:
    import auth
    from streamlit_drawable_canvas import st_canvas
    from app_utils.history_manager import HistoryManager
    from app_utils.ui_components import render_history_sidebar
    from app_utils.image_processing import process_image_for_download
    from services.flux_engine import FluxInpaintEngine
except ImportError as e:
    st.error(f"❌ 核心模块导入失败: {e}")
    st.stop()

# --- 1. 页面配置 ---
st.set_page_config(page_title="Magic Canvas", page_icon="🖌️", layout="wide")

# --- 2. 初始化 ---
if 'auth' in sys.modules and not auth.check_password():
    st.stop()

if "flux_service_ready" not in st.session_state:
    st.session_state.flux_engine = FluxInpaintEngine()
    st.session_state.history = HistoryManager()
    st.session_state.flux_result = None
    st.session_state.processed_img = None # 存储缩放后的底图
    st.session_state.flux_service_ready = True

flux_engine = st.session_state.flux_engine
history = st.session_state.history

# --- 3. 侧边栏 ---
with st.sidebar:
    st.title("🗂️ 重绘历史")
    render_history_sidebar(history)
    st.divider()
    st.info("💡 **提示**：\n涂抹区域建议略大于物体边缘，以保证融合更自然。")

# --- 4. 主逻辑区 ---
st.title("🖌️ Magic Canvas (局部重绘)")

if not flux_engine.is_ready():
    st.warning("⚠️ 请配置 REPLICATE_API_TOKEN 以使用 Flux 引擎。", icon="🔑")
    st.stop()

c_canvas, c_ctrl = st.columns([1.5, 1], gap="large")

with c_canvas:
    st.subheader("🎨 交互画布")
    
    uploaded_file = st.file_uploader("上传底图", type=["jpg", "png", "webp"], key="inp_uploader")
    
    # === 关键修复逻辑：图片预处理 ===
    if uploaded_file:
        file_id = f"{uploaded_file.name}-{uploaded_file.size}"
        
        # 只有当上传了新文件时，才重新处理
        if st.session_state.get("last_file_id") != file_id:
            raw_img = Image.open(uploaded_file).convert("RGB") # 强制转 RGB，防止显示为空
            
            # 1. 计算缩放比例，固定宽度为 700px (最佳交互宽度)
            base_width = 700
            w_percent = (base_width / float(raw_img.size[0]))
            h_size = int((float(raw_img.size[1]) * float(w_percent)))
            
            # 2. 缩放图片
            resized_img = raw_img.resize((base_width, h_size), Image.Resampling.LANCZOS)
            
            # 3. 更新 Session State
            st.session_state.processed_img = resized_img
            st.session_state.last_file_id = file_id
            st.session_state.canvas_key = f"canvas_{int(time.time())}" # 强制重置画布

    # Canvas 配置栏
    t_col1, t_col2 = st.columns([1, 2])
    brush_size = t_col1.slider("🖊️ 画笔大小", 5, 50, 20)
    
    # === 核心 Canvas 组件 ===
    if st.session_state.processed_img:
        # 获取处理后的准确宽高
        img_w, img_h = st.session_state.processed_img.size
        
        canvas_result = st_canvas(
            fill_color="rgba(255, 255, 255, 1.0)", # 涂抹颜色：纯白不透明
            stroke_width=brush_size,
            stroke_color="#FFFFFF",
            background_image=st.session_state.processed_img, # 传入缩放后的 RGB 图片
            update_streamlit=True,
            height=img_h, # 显式指定高度，解决对不齐的问题
            width=img_w,  # 显式指定宽度
            drawing_mode="freedraw",
            key=st.session_state.canvas_key, # 动态 Key
        )
    else:
        st.info("👈 请上传图片，系统会自动优化尺寸以获得最佳流畅度。")
        canvas_result = None

with c_ctrl:
    st.subheader("🛠️ 魔术控制台")
    
    prompt = st.text_area("✨ 咒语 (Prompt)", height=120, placeholder="描述涂抹区域要变成什么...")
    
    with st.expander("⚙️ 高级设置"):
        guidance = st.slider("指令遵循度", 2.0, 50.0, 30.0)
        seed_input = st.number_input("Seed (-1 随机)", value=-1)
    
    generate_btn = st.button("🪄 施展魔法", type="primary", use_container_width=True, disabled=(not st.session_state.processed_img))

    st.divider()
    
    if generate_btn:
        if canvas_result is None or canvas_result.image_data is None:
            st.error("请先涂抹区域！")
        elif canvas_result.image_data[:, :, 3].sum() == 0:
            st.warning("⚠️ 未检测到涂抹痕迹！")
        else:
            with st.status("🔮 Flux 正在重绘...", expanded=True) as status:
                try:
                    # 提取 Mask (Alpha 通道)
                    mask_data = canvas_result.image_data[:, :, 3].astype(np.uint8)
                    mask_image = Image.fromarray(mask_data, mode="L")
                    
                    # 再次确保 Mask 和底图尺寸完全一致 (双重保险)
                    if mask_image.size != st.session_state.processed_img.size:
                        mask_image = mask_image.resize(st.session_state.processed_img.size)

                    res_bytes = flux_engine.generate_fill(
                        image_input=st.session_state.processed_img,
                        mask_input=mask_image,
                        prompt=prompt,
                        guidance_scale=guidance,
                        seed=None if seed_input == -1 else int(seed_input)
                    )
                    
                    if res_bytes:
                        st.session_state.flux_result = res_bytes
                        history.add(res_bytes, "Inpaint", prompt)
                        status.update(label="🎉 完成！", state="complete", expanded=False)
                    else:
                        st.error("生成失败，请检查 Replicate 额度。")
                except Exception as e:
                    st.error(f"Error: {e}")

    # 显示结果
    if st.session_state.flux_result:
        st.subheader("🖼️ 最终效果")
        st.image(st.session_state.flux_result, use_container_width=True)
        final_bytes, mime = process_image_for_download(st.session_state.flux_result, "JPEG")
        st.download_button("📥 下载结果", data=final_bytes, file_name="magic_canvas.jpg", mime=mime, use_container_width=True)
