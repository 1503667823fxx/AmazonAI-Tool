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

# ==========================================
# 🛠️ 核心修复：兼容性补丁 (Monkey Patch)
# ==========================================
# 解决 Streamlit 1.35+ 移除了 image_to_url 导致画板背景不显示或报错的问题
import streamlit.elements.image
if not hasattr(streamlit.elements.image, "image_to_url"):
    try:
        from streamlit.elements.lib.image_utils import image_to_url
        streamlit.elements.image.image_to_url = image_to_url
    except ImportError:
        # 如果连 lib 都没有，尝试定义一个哑函数防止崩溃
        def image_to_url(image, width, clamp, channels, output_format, image_id, allow_emoji=False):
            return ""
        streamlit.elements.image.image_to_url = image_to_url

# --- 安全导入画布 ---
try:
    from streamlit_drawable_canvas import st_canvas
except ImportError:
    st_canvas = None

st.set_page_config(page_title="Magic Canvas", page_icon="🖌️", layout="wide")

if 'auth' in sys.modules:
    if not auth.check_password():
        st.stop()

if "REPLICATE_API_TOKEN" in st.secrets:
    os.environ["REPLICATE_API_TOKEN"] = st.secrets["REPLICATE_API_TOKEN"]
else:
    st.error("❌ 缺少 REPLICATE_API_TOKEN")
    st.stop()

st.title("🖌️ 魔术画布 (Magic Canvas)")
st.caption("交互式局部重绘 & 智能扩图工作台")

if st_canvas is None:
    st.error("❌ 缺少必要组件，请检查 requirements.txt")
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
        
        # --- 图片预处理逻辑 ---
        if uploaded_file:
            # 检查是否是新文件
            if st.session_state["original_upload"] != uploaded_file.name:
                try:
                    raw_image = Image.open(uploaded_file).convert("RGB")
                    
                    # 强制缩小图片，防止过大导致不显示
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
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"图片读取失败: {e}")

        # --- 画布渲染 ---
        if st.session_state.get("canvas_bg"):
            bg_img = st.session_state["canvas_bg"]
            
            # 调试区域：如果画布没图，点开这个看看 Session 里有没有图
            with st.expander("🖼️ 画布底层调试 (如果不显示请点此)", expanded=False):
                st.image(bg_img, caption=f"内存中的底图 ({bg_img.width}x{bg_img.height})", width=300)
                st.info("如果这里有图但下方画布是白的，请尝试刷新网页。")

            stroke_width = st.slider("画笔大小", 5, 50, 20)
            
            # 使用文件名作为 Key，确保换图时强制重绘
            dynamic_key = f"canvas_{st.session_state['original_upload']}"
            
            try:
                canvas_result = st_canvas(
                    fill_color="rgba(255, 255, 255, 0)",  
                    stroke_width=stroke_width,
                    stroke_color="#FFFFFF", 
                    background_image=bg_img, # 这里的 bg_img 必须是 RGB 模式的 PIL Image
                    update_streamlit=True,
                    height=bg_img.height,
                    width=bg_img.width,
                    drawing_mode="freedraw",
                    key=dynamic_key,
                    display_toolbar=True,
                )
                
                st.caption("💡 提示：在图片上涂抹白色区域，该区域将被 AI 重绘。")

            except Exception as e:
                st.error(f"画布加载出错: {e}")
                st.stop()

            # 输入指令
            prompt = st.text_area("2. 修改指令", placeholder="例如：Change to red silk dress...", height=80)
            
            if st.button("🚀 开始重绘", type="primary"):
                # 检查逻辑优化
                has_mask = False
                if canvas_result.image_data is not None:
                    # 检查是否有涂抹内容 (求和 > 0)
                    if np.sum(canvas_result.image_data) > 0:
                        has_mask = True
                
                if not has_mask or not prompt:
                    st.warning("请先涂抹区域并输入指令！(如果画布是空的，请刷新页面)")
                else:
                    with st.spinner("正在重绘 (Flux Fill Pro)..."):
                        try:
                            # 1. 准备原图
                            img_byte_arr = io.BytesIO()
                            st.session_state["canvas_bg"].save(img_byte_arr, format='PNG')
                            
                            # 2. 准备蒙版
                            mask_data = canvas_result.image_data.astype('uint8')
                            mask_pil = Image.fromarray(mask_data, mode="RGBA")
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
