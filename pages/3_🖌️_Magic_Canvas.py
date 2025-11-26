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

if st_canvas is None:
    st.error("❌ 缺少必要组件：streamlit-drawable-canvas")
    st.info("请检查 requirements.txt 配置。")
    st.stop()

# --- 状态初始化 ---
if "canvas_bg" not in st.session_state:
    st.session_state["canvas_bg"] = None 
if "original_upload" not in st.session_state:
    st.session_state["original_upload"] = None

tab_inp, tab_out = st.tabs(["🖌️ 交互式局部重绘", "↔️ 智能画幅扩展"])

# ==========================================
# Tab 1: 交互式重绘 (修复版)
# ==========================================
with tab_inp:
    col_draw, col_result = st.columns([1.5, 1], gap="large")
    
    with col_draw:
        st.subheader("1. 涂抹修改区域")
        
        uploaded_file = st.file_uploader("上传原图", type=["png", "jpg", "jpeg"], key="inp_upload")
        
        # --- 图片预处理 ---
        if uploaded_file:
            # 只有当上传了新文件时才处理
            if st.session_state["original_upload"] != uploaded_file.name:
                try:
                    raw_image = Image.open(uploaded_file).convert("RGB")
                    
                    # 【优化】最大宽度限制为 700px，提升流畅度
                    max_canvas_width = 700
                    if raw_image.width > max_canvas_width:
                        ratio = max_canvas_width / raw_image.width
                        new_h = int(raw_image.height * ratio)
                        resized_image = raw_image.resize((max_canvas_width, new_h), Image.Resampling.LANCZOS)
                    else:
                        resized_image = raw_image
                    
                    # 存入 Session
                    st.session_state["canvas_bg"] = resized_image
                    st.session_state["original_upload"] = uploaded_file.name
                    # 强制刷新页面以更新 canvas key
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"图片读取失败: {e}")

        # --- 画布渲染 ---
        if st.session_state.get("canvas_bg"):
            bg_img = st.session_state["canvas_bg"]
            
            stroke_width = st.slider("画笔大小", 5, 50, 20)
            
            # 【核心修复】使用动态 Key，确保换图时画布彻底重置
            # 如果没有这个，换图后画布可能还是显示旧图或空白
            dynamic_key = f"canvas_{st.session_state['original_upload']}"
            
            try:
                canvas_result = st_canvas(
                    fill_color="rgba(255, 255, 255, 0)",  
                    stroke_width=stroke_width,
                    stroke_color="#FFFFFF", 
                    background_image=bg_img, 
                    update_streamlit=True,
                    height=bg_img.height,
                    width=bg_img.width,
                    drawing_mode="freedraw",
                    key=dynamic_key, # 使用动态 Key
                    display_toolbar=True,
                )
                
                st.caption("💡 提示：在左图涂抹要修改的区域（白色）。")

            except Exception as e:
                st.error(f"画布加载出错: {e}")
                st.stop()

            # 输入指令
            prompt = st.text_area("2. 修改指令", placeholder="例如：Change to red silk dress...", height=80)
            
            if st.button("🚀 开始重绘", type="primary"):
                if not canvas_result.image_data is not None or not prompt:
                    st.warning("请先涂抹区域并输入指令")
                else:
                    with st.spinner("正在重绘 (Flux Fill Pro)..."):
                        try:
                            # 1. 准备原图
                            img_byte_arr = io.BytesIO()
                            st.session_state["canvas_bg"].save(img_byte_arr, format='PNG')
                            
                            # 2. 准备蒙版
                            mask_data = canvas_result.image_data.astype('uint8')
                            mask_pil = Image.fromarray(mask_data, mode="RGBA")
                            # 提取 Alpha 通道 (涂抹部分)
                            mask_pil = mask_pil.split()[3] 
                            
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
                                    "output_quality": 100
                                }
                            )
                            st.session_state["magic_result"] = str(output)
                            st.success("完成！")
                            
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
    st.info("↔️ 上传图片，AI 自动填充四周空白，扩展视野。")
    c1, c2 = st.columns([1, 1])
    with c1:
        out_img = st.file_uploader("上传原图", key="out_img_up")
        target_ar = st.selectbox("扩展至目标比例", ["16:9", "9:16", "4:3", "3:4", "1:1"], index=0)
        out_prompt = st.text_input("环境描述 (留空自动推断)", placeholder="Modern living room background...")
        
        if st.button("🚀 开始扩展"):
            if out_img:
                with st.spinner("正在扩展..."):
                    try:
                        out_res = replicate.run(
                            "black-forest-labs/flux-fill-pro",
                            input={
                                "image": out_img,
                                "prompt": out_prompt if out_prompt else "background texture",
                                "aspect_ratio": target_ar,
                                "output_format": "jpg"
                            }
                        )
                        st.session_state["out_result"] = str(out_res)
                    except Exception as e:
                        st.error(f"扩展失败: {e}")
    
    with c2:
        if "out_result" in st.session_state:
            st.image(st.session_state["out_result"], caption="扩展结果", use_container_width=True)
    with c2:
        if "out_result" in st.session_state:
            st.image(st.session_state["out_result"], caption="扩展结果", use_container_width=True)
