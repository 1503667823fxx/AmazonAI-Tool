import streamlit as st
import replicate
from PIL import Image, ImageOps
import io
import sys
import os
import numpy as np

# --- 0. 基础设置 ---
sys.path.append(os.path.abspath('.'))
try:
    import auth
    from core_utils import process_image_for_download 
except ImportError:
    pass 

# --- 安全导入画布组件 ---
try:
    from streamlit_drawable_canvas import st_canvas
except ImportError:
    st_canvas = None

st.set_page_config(page_title="Magic Canvas", page_icon="🖌️", layout="wide")

if 'auth' in sys.modules:
    if not auth.check_password():
        st.stop()

# API Check
if "REPLICATE_API_TOKEN" in st.secrets:
    os.environ["REPLICATE_API_TOKEN"] = st.secrets["REPLICATE_API_TOKEN"]
else:
    st.error("❌ 缺少 REPLICATE_API_TOKEN")
    st.stop()

st.title("🖌️ 魔术画布 (Magic Canvas)")
st.caption("交互式局部重绘 & 智能扩图工作台")

# --- 组件检查 ---
if st_canvas is None:
    st.error("❌ 缺少必要组件：streamlit-drawable-canvas")
    st.info("请在 requirements.txt 中添加：streamlit-drawable-canvas>=0.9.5 并重启应用。")
    st.stop()

tab_inp, tab_out = st.tabs(["🖌️ 交互式局部重绘", "↔️ 智能画幅扩展"])

# ==========================================
# Tab 1: 交互式重绘
# ==========================================
with tab_inp:
    col_draw, col_result = st.columns([1.5, 1], gap="large")
    
    with col_draw:
        st.subheader("1. 涂抹修改区域")
        uploaded_file = st.file_uploader("上传原图", type=["png", "jpg", "jpeg"], key="canvas_upload")
        
        mask_data = None 
        
        if uploaded_file:
            bg_image = Image.open(uploaded_file).convert("RGB")
            w, h = bg_image.size
            
            # 限制显示大小
            max_width = 700
            if w > max_width:
                ratio = max_width / w
                new_w = max_width
                new_h = int(h * ratio)
            else:
                new_w, new_h = w, h

            stroke_width = st.slider("画笔大小", 10, 100, 30)
            
            # ★★★ 核心组件：带防崩保护 ★★★
            try:
                canvas_result = st_canvas(
                    fill_color="rgba(255, 255, 255, 0)", 
                    stroke_width=stroke_width,
                    stroke_color="#FFFFFF", 
                    background_image=bg_image,
                    update_streamlit=True,
                    height=new_h,
                    width=new_w,
                    drawing_mode="freedraw",
                    key="inpainting_canvas",
                )
                
                st.caption("💡 提示：涂白处将被重绘。")

                if canvas_result.image_data is not None:
                    mask_data = canvas_result.image_data[:, :, :3]

            except AttributeError:
                st.error("⚠️ **组件版本不兼容**")
                st.warning("""
                检测到 `AttributeError`。这通常是因为 `streamlit-drawable-canvas` 版本过低。
                
                **解决方法：**
                1. 打开 `requirements.txt` 文件。
                2. 将 `streamlit-drawable-canvas` 修改为 `streamlit-drawable-canvas>=0.9.5`。
                3. 如果在 Cloud 运行，请点击右下角 "Manage app" -> "Reboot app"。
                """)
                st.stop()
            except Exception as e:
                st.error(f"画布加载失败: {e}")
                st.stop()

        # 输入指令
        prompt = st.text_area("2. 修改指令", placeholder="例如：Change the shirt to a red silk dress...", height=80)
        
        if st.button("🚀 开始重绘 (Flux Fill)", type="primary"):
            # 这里的 canvas_result 可能会因为上面的报错而未定义，加个检查
            if not uploaded_file or 'canvas_result' not in locals() or canvas_result.image_data is None or not prompt:
                st.warning("请先上传图片、涂抹区域并输入指令")
            else:
                with st.spinner("正在重绘..."):
                    try:
                        # 1. 准备原图
                        bg_image.seek(0) 
                        img_byte_arr = io.BytesIO()
                        bg_image.save(img_byte_arr, format='PNG')
                        
                        # 2. 准备蒙版
                        mask_pil = Image.fromarray(canvas_result.image_data.astype('uint8'), mode="RGBA")
                        mask_pil = mask_pil.split()[3] # 取 Alpha 通道
                        
                        mask_byte_arr = io.BytesIO()
                        mask_pil.save(mask_byte_arr, format='PNG')
                        
                        # 3. 调用 API
                        output = replicate.run(
                            "black-forest-labs/flux-fill-pro",
                            input={
                                "image": img_byte_arr,
                                "mask": mask_byte_arr,
                                "prompt": prompt,
                                "output_format": "jpg",
                                "output_quality": 95
                            }
                        )
                        st.session_state["magic_result"] = str(output)
                        
                    except Exception as e:
                        st.error(f"重绘失败: {e}")

    with col_result:
        st.subheader("🖼️ 结果展示")
        if "magic_result" in st.session_state:
            st.image(st.session_state["magic_result"], caption="重绘结果", use_container_width=True)
        else:
            st.info("等待生成...")

# ==========================================
# Tab 2: 画幅扩展 (Flux Fill)
# ==========================================
with tab_out:
    st.info("↔️ 此功能将自动填充图片四周的空白区域，实现无损扩图。")
    c1, c2 = st.columns([1, 1])
    with c1:
        out_img = st.file_uploader("上传原图", key="out_img")
        target_ar = st.selectbox("扩展至目标比例", ["16:9", "9:16", "4:3", "3:4", "1:1"], index=0)
        out_prompt = st.text_input("环境描述 (留空则自动推断)", placeholder="Modern living room background...")
        
        if st.button("🚀 开始扩展"):
            if out_img:
                with st.spinner("正在扩展画幅..."):
                    try:
                        out_res = replicate.run(
                            "black-forest-labs/flux-fill-pro",
                            input={
                                "image": out_img,
                                "prompt": out_prompt if out_prompt else "background texture",
                                "aspect_ratio": target_ar.replace(":", ":"), 
                                "output_format": "jpg"
                            }
                        )
                        st.session_state["out_result"] = str(out_res)
                    except Exception as e:
                        st.error(f"扩展失败: {e}")
    
    with c2:
        if "out_result" in st.session_state:
            st.image(st.session_state["out_result"], caption="扩展结果", use_container_width=True)
