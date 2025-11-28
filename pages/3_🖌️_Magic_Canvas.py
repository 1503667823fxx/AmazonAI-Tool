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
    
    # 引入我们刚写的 Flux 引擎
    from services.flux_engine import FluxInpaintEngine
except ImportError as e:
    st.error(f"❌ 核心模块导入失败: {e}。请确保安装了 'streamlit-drawable-canvas' 和 'replicate'。")
    st.stop()

# --- 1. 页面配置 ---
st.set_page_config(page_title="Magic Canvas", page_icon="🖌️", layout="wide")

# --- CSS 优化 Canvas 显示 ---
st.markdown("""
<style>
    /* 简单的卡片样式 */
    .css-1r6slb0 {border: 1px solid #ddd; padding: 20px; border-radius: 10px;}
</style>
""", unsafe_allow_html=True)

# --- 2. 初始化 ---
if 'auth' in sys.modules and not auth.check_password():
    st.stop()

if "flux_service_ready" not in st.session_state:
    st.session_state.flux_engine = FluxInpaintEngine()
    st.session_state.history = HistoryManager()
    st.session_state.flux_result = None # 存储结果
    st.session_state.flux_service_ready = True

flux_engine = st.session_state.flux_engine
history = st.session_state.history

# --- 3. 侧边栏 ---
with st.sidebar:
    st.title("🗂️ 重绘历史")
    render_history_sidebar(history)
    
    st.divider()
    st.markdown("### 💡 使用指南")
    st.info("""
    1. **上传** 需要修改的图片。
    2. 使用 **画笔** 涂抹你想要改变的区域（例如涂抹衣服上的Logo，或者涂抹模特手中的产品）。
    3. 在右侧输入 **Prompt** 描述你希望这里变成什么。
    4. 点击生成，**Flux Fill** 会无缝融合新内容。
    """)

# --- 4. 主逻辑区 ---
st.title("🖌️ Magic Canvas (局部重绘)")

# 检查 API Token
if not flux_engine.is_ready():
    st.warning("⚠️ 未检测到 `REPLICATE_API_TOKEN`。请在 Secrets 中配置以使用 Flux 引擎。", icon="🔑")
    st.stop()

# 布局：左 1.5 (画布) | 右 1 (控制)
c_canvas, c_ctrl = st.columns([1.5, 1], gap="large")

# 状态管理：我们需要记住上传的文件，否则 Canvas 刷新会丢失
if "canvas_bg_img" not in st.session_state:
    st.session_state.canvas_bg_img = None

with c_canvas:
    st.subheader("🎨 交互画布")
    
    uploaded_file = st.file_uploader("上传底图", type=["jpg", "png", "webp"], key="inp_uploader")
    
    if uploaded_file:
        # 更新底图
        image = Image.open(uploaded_file).convert("RGB")
        # 限制图片大小防止 Canvas 卡顿 (Flux 推荐 1024 左右)
        if image.width > 1024 or image.height > 1024:
            image.thumbnail((1024, 1024))
        st.session_state.canvas_bg_img = image

    # Canvas 配置栏
    t_col1, t_col2 = st.columns([1, 2])
    brush_size = t_col1.slider("🖊️ 画笔大小", 10, 100, 40)
    stroke_color = "#FFFFFF" # 蒙版颜色（白色）
    
    # 核心 Canvas 组件
    if st.session_state.canvas_bg_img:
        # 计算合适的 Canvas 高度
        w, h = st.session_state.canvas_bg_img.size
        # 这里的 key 很重要，如果底图变了，Canvas 需要重绘
        canvas_result = st_canvas(
            fill_color="rgba(255, 255, 255, 0.0)",  # 填充色透明
            stroke_width=brush_size,
            stroke_color=stroke_color,
            background_image=st.session_state.canvas_bg_img,
            update_streamlit=True,
            height=h,
            width=w,
            drawing_mode="freedraw",
            key="magic_canvas_editor",
        )
    else:
        st.info("👈 请先上传图片开始创作")
        canvas_result = None

with c_ctrl:
    st.subheader("🛠️ 魔术控制台")
    
    prompt = st.text_area(
        "✨ 咒语 (Prompt)", 
        height=120,
        placeholder="在这里描述涂抹区域应该变成什么...\n例如：'a red leather handbag', 'holding a cup of coffee', 'clean skin texture'",
        help="Flux Fill 对自然语言的理解非常好，请直接描述最终效果。"
    )
    
    with st.expander("⚙️ 高级设置", expanded=False):
        guidance = st.slider("指令遵循度 (Guidance)", 2.0, 50.0, 30.0, help="值越高，AI 越严格遵守你的 Prompt；值越低，AI 越自由发挥。")
        seed_input = st.number_input("Seed (-1 随机)", value=-1)
    
    generate_btn = st.button("🪄 施展魔法 (Generate)", type="primary", use_container_width=True, disabled=(not st.session_state.canvas_bg_img))

    # --- 结果展示区 ---
    st.divider()
    
    if generate_btn:
        # 1. 检查 Mask
        if canvas_result is None or canvas_result.image_data is None:
            st.error("请在左侧图片上涂抹要修改的区域！")
        else:
            # 2. 提取 Mask
            # canvas_result.image_data 是 RGBA numpy array
            mask_data = canvas_result.image_data
            
            # 检查用户是否真的画了东西 (Alpha 通道求和 > 0)
            if mask_data[:, :, 3].sum() == 0:
                st.warning("⚠️ 你还没有涂抹任何区域！请在左侧图上用画笔画出蒙版。")
            else:
                with st.status("🔮 Flux 正在重绘现实...", expanded=True) as status:
                    try:
                        # 处理 Mask: 提取 Alpha 通道作为 Mask
                        # Alpha通道中，有笔触的地方是255，无笔触是0
                        # 需要转成 PIL Image (L mode)
                        alpha_channel = mask_data[:, :, 3].astype(np.uint8)
                        mask_image = Image.fromarray(alpha_channel, mode="L")
                        
                        # 简单的形态学膨胀 (可选，防止白边) - 这里简单处理，直接传 Mask
                        # Flux Fill 比较强，通常不需要过度处理 Mask
                        
                        st.write("📤 正在上传数据到云端...")
                        
                        # 调用后端
                        res_bytes = flux_engine.generate_fill(
                            image_input=st.session_state.canvas_bg_img,
                            mask_input=mask_image,
                            prompt=prompt,
                            guidance_scale=guidance,
                            seed=None if seed_input == -1 else int(seed_input)
                        )
                        
                        if res_bytes:
                            st.session_state.flux_result = res_bytes
                            # 保存历史
                            history.add(res_bytes, "Inpaint-Task", prompt)
                            status.update(label="🎉 重绘完成！", state="complete", expanded=False)
                        else:
                            st.error("生成返回空数据，请检查 API 配额或日志。")

                    except Exception as e:
                        st.error(f"生成出错: {e}")

    # 显示结果
    if st.session_state.flux_result:
        st.subheader("🖼️ 最终效果")
        st.image(st.session_state.flux_result, use_container_width=True)
        
        # 下载
        final_bytes, mime = process_image_for_download(st.session_state.flux_result, "JPEG")
        st.download_button(
            "📥 下载结果", 
            data=final_bytes, 
            file_name=f"magic_canvas_{int(time.time())}.jpg", 
            mime=mime, 
            type="primary",
            use_container_width=True
        )
