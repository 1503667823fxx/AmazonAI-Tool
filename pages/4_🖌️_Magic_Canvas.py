import streamlit as st
import replicate
from PIL import Image, ImageOps
import io
import sys
import os
import numpy as np
# 需要安装: pip install streamlit-drawable-canvas
from streamlit_drawable_canvas import st_canvas

# --- 0. 基础设置 ---
sys.path.append(os.path.abspath('.'))
try:
    import auth
    # 复用你之前写的 core_utils 来处理下载
    from core_utils import process_image_for_download 
except ImportError:
    pass 

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

tab_inp, tab_out = st.tabs(["🖌️ 交互式局部重绘", "↔️ 智能画幅扩展"])

# ==========================================
# Tab 1: 交互式重绘 (解决了用户不会做蒙版的痛点)
# ==========================================
with tab_inp:
    col_draw, col_result = st.columns([1.5, 1], gap="large")
    
    with col_draw:
        st.subheader("1. 涂抹修改区域")
        uploaded_file = st.file_uploader("上传原图", type=["png", "jpg", "jpeg"], key="canvas_upload")
        
        mask_data = None # 初始化
        
        if uploaded_file:
            # 获取图片尺寸，调整画布大小
            bg_image = Image.open(uploaded_file).convert("RGB")
            w, h = bg_image.size
            
            # 限制显示大小，防止画布撑破屏幕 (等比缩放)
            max_width = 700
            if w > max_width:
                ratio = max_width / w
                new_w = max_width
                new_h = int(h * ratio)
            else:
                new_w, new_h = w, h

            # 画笔工具栏
            stroke_width = st.slider("画笔大小", 10, 100, 30)
            
            # ★★★ 核心组件：交互式画布 ★★★
            canvas_result = st_canvas(
                fill_color="rgba(255, 255, 255, 0)",  # 透明填充
                stroke_width=stroke_width,
                stroke_color="#FFFFFF", # 白色画笔代表蒙版区域
                background_image=bg_image,
                update_streamlit=True,
                height=new_h,
                width=new_w,
                drawing_mode="freedraw",
                key="inpainting_canvas",
            )
            
            st.caption("💡 提示：用鼠标在左图中涂抹你想要修改的地方（涂白处将被重绘）。")

            # 处理蒙版数据
            if canvas_result.image_data is not None:
                # canvas_result.image_data 是 RGBA 数组
                # 我们需要提取 Alpha 通道或者绘制的白色笔触作为 Mask
                mask_data = canvas_result.image_data[:, :, :3] # 取 RGB
                # 简单的处理：有颜色的地方就是 Mask
                # 注意：这里简化了处理，实际可能需要转为灰度图
                
                # 临时保存 Mask 用于预览（调试用，可隐藏）
                # st.image(mask_data, caption="生成的蒙版数据 (Debug)", width=100)

        # 输入指令
        prompt = st.text_area("2. 修改指令", placeholder="例如：Change the shirt to a red silk dress...", height=80)
        
        if st.button("🚀 开始重绘 (Flux Fill)", type="primary"):
            if not uploaded_file or canvas_result.image_data is None or not prompt:
                st.warning("请先上传图片、涂抹区域并输入指令")
            else:
                with st.spinner("正在重绘..."):
                    try:
                        # 1. 准备原图
                        bg_image.seek(0) # 指针复位
                        img_byte_arr = io.BytesIO()
                        bg_image.save(img_byte_arr, format='PNG')
                        
                        # 2. 准备蒙版 (从 Canvas 数据生成)
                        # 将 numpy array 转为 PIL Image
                        # 这里的逻辑：Canvas 画的是白色，背景透明。Flux 需要蒙版区域为白，背景为黑。
                        mask_pil = Image.fromarray(canvas_result.image_data.astype('uint8'), mode="RGBA")
                        # 提取 Alpha 通道作为蒙版依据，或者直接用 RGB (如果是黑底白画笔)
                        # 简单做法：转灰度，二值化
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
                        # Flux Fill 的 Outpainting 逻辑
                        # 注意：Flux Fill Pro 的 API 调用方式可能需要具体的参数调整 (padding vs aspect_ratio)
                        # 这里使用 aspect_ratio 模式
                        out_res = replicate.run(
                            "black-forest-labs/flux-fill-pro",
                            input={
                                "image": out_img,
                                "prompt": out_prompt if out_prompt else "background texture",
                                "aspect_ratio": target_ar.replace(":", ":"), # 确保格式 16:9
                                "output_format": "jpg"
                            }
                        )
                        st.session_state["out_result"] = str(out_res)
                    except Exception as e:
                        st.error(f"扩展失败: {e}")
    
    with c2:
        if "out_result" in st.session_state:
            st.image(st.session_state["out_result"], caption="扩展结果", use_container_width=True)
