import streamlit as st
import replicate
from PIL import Image
import io
import sys
import os
import numpy as np
import base64

# --- 0. 基础设置 ---
sys.path.append(os.path.abspath('.'))
try:
    import auth
    from core_utils import process_image_for_download 
except ImportError:
    pass 

st.set_page_config(page_title="Magic Canvas", page_icon="🖌️", layout="wide")

if 'auth' in sys.modules:
    if not auth.check_password():
        st.stop()

if "REPLICATE_API_TOKEN" in st.secrets:
    os.environ["REPLICATE_API_TOKEN"] = st.secrets["REPLICATE_API_TOKEN"]
else:
    st.error("❌ 缺少 REPLICATE_API_TOKEN")
    st.stop()

# ==========================================
# 🛠️ 终极补丁：强制让画布显示图片
# ==========================================
# 既然插件找不到 image_to_url，我们就造一个给它，并且放在它能找到的任何地方
def local_image_to_url(image, width=None, clamp=False, channels='RGB', output_format='auto', image_id=None, allow_emoji=False):
    """将 PIL 图片直接转换为浏览器可读的 Base64 字符串"""
    try:
        if isinstance(image, np.ndarray):
            image = Image.fromarray(image)
        
        # 统一转 RGB，避免 PNG 透明度导致的保存错误
        if image.mode != "RGB":
            image = image.convert("RGB")
            
        buffered = io.BytesIO()
        image.save(buffered, format="JPEG", quality=90)
        img_str = base64.b64encode(buffered.getvalue()).decode()
        return f"data:image/jpeg;base64,{img_str}"
    except Exception:
        return ""

# 暴力注入到 streamlit 的各个模块中，确保旧插件能引用到
import streamlit.elements.image
import streamlit.elements.lib.image_utils as image_utils

streamlit.elements.image.image_to_url = local_image_to_url
image_utils.image_to_url = local_image_to_url

# --- 导入画布 ---
try:
    from streamlit_drawable_canvas import st_canvas
except ImportError:
    st_canvas = None

st.title("🖌️ 魔术画布 V3.0")
st.caption("交互式局部重绘 & 智能扩图工作台")

if st_canvas is None:
    st.error("❌ 缺少组件，请检查 requirements.txt")
    st.stop()

# --- 状态管理 ---
if "magic_result" not in st.session_state: st.session_state["magic_result"] = None
if "out_result" not in st.session_state: st.session_state["out_result"] = None

tab_inp, tab_out = st.tabs(["🖌️ 交互式局部重绘", "↔️ 智能画幅扩展"])

# ==========================================
# Tab 1: 交互式重绘 (极速版)
# ==========================================
with tab_inp:
    col_draw, col_result = st.columns([1.5, 1], gap="large")
    
    with col_draw:
        st.markdown("### 1. 涂抹区域")
        
        uploaded_file = st.file_uploader("上传图片 (建议 < 2MB)", type=["png", "jpg", "jpeg"], key="inp_upload")
        
        bg_image = None
        if uploaded_file:
            try:
                # 预处理：限制图片尺寸，防止浏览器卡死
                raw_img = Image.open(uploaded_file).convert("RGB")
                max_w = 700
                if raw_img.width > max_w:
                    ratio = max_w / raw_img.width
                    new_h = int(raw_img.height * ratio)
                    bg_image = raw_img.resize((max_w, new_h))
                else:
                    bg_image = raw_img
            except:
                st.error("图片无法读取")

        # 画布逻辑
        if bg_image:
            # 画笔设置
            b_width = st.slider("画笔粗细", 5, 50, 25)
            
            # 动态 Key：确保换图时画布刷新
            canvas_key = f"canvas_{uploaded_file.name}_{uploaded_file.size}"
            
            # ★★★ 关键优化：update_streamlit=False ★★★
            # 这会让画布只在鼠标松开时才发送数据，而不是移动时一直发，极大解决卡顿
            canvas_result = st_canvas(
                fill_color="rgba(255, 255, 255, 0)",
                stroke_width=b_width,
                stroke_color="#FFFFFF",
                background_image=bg_image,
                update_streamlit=False,  # 🚀 解决卡顿的核心参数
                height=bg_image.height,
                width=bg_image.width,
                drawing_mode="freedraw",
                key=canvas_key,
            )
            
            st.caption("💡 提示：涂抹完成后，画布会自动保存状态。")

            prompt = st.text_area("2. 修改指令", placeholder="例如：Change background to beach...", height=80)
            
            if st.button("🚀 开始重绘", type="primary"):
                if canvas_result.image_data is None:
                    st.warning("请先在图片上涂抹！")
                else:
                    with st.spinner("正在发送给 AI (Flux Fill)..."):
                        try:
                            # 1. 处理原图
                            src_buf = io.BytesIO()
                            bg_image.save(src_buf, format='PNG')
                            
                            # 2. 处理蒙版
                            # Canvas 返回 RGBA，取 Alpha 通道作为蒙版
                            mask_data = canvas_result.image_data.astype('uint8')
                            mask_img = Image.fromarray(mask_data, mode="RGBA")
                            mask_img = mask_img.split()[3] # 提取 Alpha
                            
                            mask_buf = io.BytesIO()
                            mask_img.save(mask_buf, format='PNG')
                            
                            # 3. 调用 Replicate
                            output = replicate.run(
                                "black-forest-labs/flux-fill-pro",
                                input={
                                    "image": src_buf,
                                    "mask": mask_buf,
                                    "prompt": prompt,
                                    "output_format": "jpg",
                                    "output_quality": 95
                                }
                            )
                            st.session_state["magic_result"] = str(output)
                            st.success("重绘成功！")
                            
                        except Exception as e:
                            st.error(f"API 调用失败: {e}")

    with col_result:
        st.markdown("### 🖼️ 结果")
        if st.session_state["magic_result"]:
            st.image(st.session_state["magic_result"], caption="AI 重绘结果", use_container_width=True)
        else:
            st.info("👈 请在左侧操作")

# ==========================================
# Tab 2: 画幅扩展 (Flux Fill)
# ==========================================
with tab_out:
    st.markdown("### ↔️ 智能扩图")
    c1, c2 = st.columns([1, 1])
    with c1:
        out_img = st.file_uploader("上传原图", key="out_img_up")
        target_ar = st.selectbox("扩展比例", ["16:9", "9:16", "4:3", "1:1"], index=0)
        out_prompt = st.text_input("环境描述", placeholder="Modern background...")
        
        if st.button("🚀 开始扩展"):
            if out_img:
                with st.spinner("AI 正在脑补画面..."):
                    try:
                        out_res = replicate.run(
                            "black-forest-labs/flux-fill-pro",
                            input={
                                "image": out_img,
                                "prompt": out_prompt if out_prompt else "high quality background",
                                "aspect_ratio": target_ar,
                                "output_format": "jpg"
                            }
                        )
                        st.session_state["out_result"] = str(out_res)
                    except Exception as e:
                        st.error(f"扩展失败: {e}")
    
    with c2:
        if st.session_state["out_result"]:
            st.image(st.session_state["out_result"], caption="扩图结果", use_container_width=True)
