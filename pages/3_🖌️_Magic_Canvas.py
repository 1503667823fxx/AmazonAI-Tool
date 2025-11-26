import streamlit as st
import replicate
from PIL import Image
import io
import sys
import os
import numpy as np
import base64
import uuid

# --- 0. 基础设置 ---
sys.path.append(os.path.abspath('.'))
try:
    import auth
    from core_utils import process_image_for_download 
except ImportError:
    pass 

# ==========================================
# 🛠️ 核心修复：Base64 强力注入补丁 (V4.0)
# ==========================================
# 这是一个“核弹级”补丁，它强制拦截所有图片转换请求
# 并将其转化为浏览器绝对能看懂的 Base64 编码
def force_base64_patch(image, width=None, clamp=False, channels='RGB', output_format='auto', image_id=None, allow_emoji=False):
    try:
        # 1. 兼容 Numpy
        if isinstance(image, np.ndarray):
            image = Image.fromarray(image)
        
        # 2. 强制转 RGB (JPEG 不支持透明)
        if image.mode != "RGB":
            image = image.convert("RGB")
            
        # 3. 转换
        buffered = io.BytesIO()
        # ⚠️ 关键优化：强制使用 JPEG 格式 + 85% 质量
        # 这能将数据量从 5MB 压到 200KB，解决 iframe 传输失败的问题
        image.save(buffered, format="JPEG", quality=85)
        img_str = base64.b64encode(buffered.getvalue()).decode()
        return f"data:image/jpeg;base64,{img_str}"
    except Exception as e:
        print(f"Patch Failed: {e}")
        return ""

# 注入到 Streamlit 核心
import streamlit.elements.image
import streamlit.elements.lib.image_utils as image_utils
streamlit.elements.image.image_to_url = force_base64_patch
image_utils.image_to_url = force_base64_patch

# --- 导入画布 ---
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

st.title("🖌️ 魔术画布 V4.0 (Speed Mode)")
st.caption("交互式局部重绘 & 智能扩图工作台")

if st_canvas is None:
    st.error("❌ 缺少组件，请检查 requirements.txt")
    st.stop()

# --- 状态管理 ---
if "magic_result" not in st.session_state: st.session_state["magic_result"] = None
if "out_result" not in st.session_state: st.session_state["out_result"] = None
if "canvas_key" not in st.session_state: st.session_state["canvas_key"] = str(uuid.uuid4())

tab_inp, tab_out = st.tabs(["🖌️ 交互式局部重绘", "↔️ 智能画幅扩展"])

# ==========================================
# Tab 1: 交互式重绘
# ==========================================
with tab_inp:
    col_draw, col_result = st.columns([1.5, 1], gap="large")
    
    with col_draw:
        st.markdown("### 1. 涂抹区域")
        
        uploaded_file = st.file_uploader("上传原图", type=["png", "jpg", "jpeg"], key="inp_upload")
        
        bg_image = None
        
        if uploaded_file:
            try:
                # 1. 读取并强制压缩
                # 限制为 600px 宽，这是为了保证 Cloud 端不卡顿的黄金尺寸
                raw = Image.open(uploaded_file).convert("RGB")
                max_w = 600 
                
                if raw.width > max_w:
                    ratio = max_w / raw.width
                    new_h = int(raw.height * ratio)
                    bg_image = raw.resize((max_w, new_h), Image.Resampling.LANCZOS)
                else:
                    bg_image = raw
                
            except Exception as e:
                st.error(f"图片错误: {e}")

        # 画布逻辑
        if bg_image:
            b_width = st.slider("画笔粗细", 5, 50, 20)
            
            # 如果换了图，更新 key 强制重绘
            if "last_file" not in st.session_state or st.session_state["last_file"] != uploaded_file.name:
                st.session_state["canvas_key"] = str(uuid.uuid4())
                st.session_state["last_file"] = uploaded_file.name
                st.rerun()

            # ★★★ 画布组件 ★★★
            try:
                canvas_result = st_canvas(
                    fill_color="rgba(255, 255, 255, 0)",
                    stroke_width=b_width,
                    stroke_color="#FFFFFF",
                    background_image=bg_image, # 这里的图片会被上面的 Patch 转成 Base64
                    update_streamlit=False,    # 🚀 核心优化：关闭实时更新，解决卡顿！
                    height=bg_image.height,
                    width=bg_image.width,
                    drawing_mode="freedraw",
                    key=st.session_state["canvas_key"],
                    display_toolbar=True,
                )
                st.caption("✅ 提示：画笔已就绪。请在图上涂抹（松开鼠标后生效）。")
                
            except Exception as e:
                st.error(f"画布加载失败: {e}")

            # 调试信息 (如果还不显示，请把 width 调得更小)
            # st.write(f"Canvas Size: {bg_image.width}x{bg_image.height}")

            prompt = st.text_area("2. 修改指令", placeholder="例如：Change to red silk dress...", height=80)
            
            if st.button("🚀 开始重绘", type="primary"):
                # 检查是否有涂抹
                has_mask = False
                if canvas_result.image_data is not None:
                    # 简单的求和检查
                    if np.sum(canvas_result.image_data) > 0:
                        has_mask = True
                
                if not has_mask:
                    st.warning("⚠️ 请先在图片上涂抹白色区域！(如果没有显示笔迹，请刷新页面)")
                elif not prompt:
                    st.warning("⚠️ 请输入修改指令")
                else:
                    with st.spinner("正在发送给 Flux Pro (约 15s)..."):
                        try:
                            # 准备原图 (JPEG)
                            src_buf = io.BytesIO()
                            bg_image.save(src_buf, format='JPEG', quality=95)
                            
                            # 准备蒙版 (PNG Alpha)
                            mask_data = canvas_result.image_data.astype('uint8')
                            mask_img = Image.fromarray(mask_data, mode="RGBA")
                            mask_img = mask_img.split()[3] # 提取 Alpha 通道
                            
                            mask_buf = io.BytesIO()
                            mask_img.save(mask_buf, format='PNG')
                            
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
