import streamlit as st
import replicate
from PIL import Image
import io
import sys
import os
import base64
import uuid
import numpy as np

# --- 0. 基础设置 ---
sys.path.append(os.path.abspath('.'))
try:
    import auth
    from core_utils import process_image_for_download 
except ImportError:
    pass 

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
    st.error("❌ 缺少组件，请检查 requirements.txt")
    st.stop()

# ==========================================
# 🛠️ 核心函数：手动转 Base64 (纯净版)
# ==========================================
def pil_to_base64(image):
    """
    将 PIL 图片转为前端能直接显示的 Data URL 字符串。
    """
    try:
        # 1. 统一转 RGB (JPEG 兼容性最好, 且体积小)
        if image.mode != "RGB":
            image = image.convert("RGB")
        
        buff = io.BytesIO()
        # 使用 JPEG 格式，质量 85，兼顾清晰度和传输速度
        image.save(buff, format="JPEG", quality=85)
        img_str = base64.b64encode(buff.getvalue()).decode()
        return f"data:image/jpeg;base64,{img_str}"
    except Exception as e:
        st.error(f"图片转换失败: {e}")
        return ""

# --- 状态管理 ---
if "canvas_key" not in st.session_state: st.session_state["canvas_key"] = str(uuid.uuid4())
if "last_upload" not in st.session_state: st.session_state["last_upload"] = None
if "magic_result" not in st.session_state: st.session_state["magic_result"] = None
if "out_result" not in st.session_state: st.session_state["out_result"] = None

tab_inp, tab_out = st.tabs(["🖌️ 交互式局部重绘", "↔️ 智能画幅扩展"])

# ==========================================
# Tab 1: 交互式重绘 (CSS 注入版)
# ==========================================
with tab_inp:
    col_draw, col_result = st.columns([1.5, 1], gap="large")
    
    with col_draw:
        st.subheader("1. 涂抹修改区域")
        
        uploaded_file = st.file_uploader("上传原图", type=["png", "jpg", "jpeg"], key="inp_upload")
        
        bg_base64 = None 
        original_pil = None 
        
        if uploaded_file:
            try:
                raw_img = Image.open(uploaded_file).convert("RGB")
                
                # 1. 限制尺寸 (防止前端卡顿)
                max_w = 700
                if raw_img.width > max_w:
                    ratio = max_w / raw_img.width
                    new_h = int(raw_img.height * ratio)
                    original_pil = raw_img.resize((max_w, new_h), Image.Resampling.LANCZOS)
                else:
                    original_pil = raw_img
                
                # 2. 转换为 Base64 字符串
                bg_base64 = pil_to_base64(original_pil)
                
                # 3. 如果换图了，更新 Key 强制重绘组件
                if st.session_state["last_upload"] != uploaded_file.name:
                    st.session_state["canvas_key"] = str(uuid.uuid4())
                    st.session_state["last_upload"] = uploaded_file.name
                    st.rerun()
                    
            except Exception as e:
                st.error(f"读取图片出错: {e}")

        # --- 画布组件 ---
        if bg_base64 and original_pil:
            stroke_width = st.slider("画笔大小", 5, 50, 20)
            
            # 🛠️ CSS 注入黑魔法：强制给画布容器加背景
            # 既然插件本身显示背景图有问题，我们就用 CSS 把它“垫”在下面
            # 注意：这里利用了 iframe 的特性，虽然不能直接穿透，但我们可以尝试给 st_canvas 的容器加样式
            # 如果上面的 image_to_url 补丁失效，这个 CSS 至少能保证用户看到图
            
            # 这里我们依然尝试把 bg_base64 传给 background_image
            # 但同时我们故意不使用 PIL Image 对象，而是传 None，防止它内部去调用那个不存在的 image_to_url
            
            try:
                # 关键修改：
                # 1. background_image 设为 None (彻底绕过库内部报错逻辑)
                # 2. background_color 设为透明 (方便看到底下的 CSS 背景)
                # 3. 使用 st.markdown 注入 CSS 背景 (这是一个妥协方案，可能需要调整位置)
                
                # --- 方案 A: 还是尝试传 Image 对象，但这次是全新的纯净环境 ---
                # 既然之前的 Patch 可能有副作用，这次我们什么 Patch 都不加，直接传处理好的 PIL 对象
                # 因为 requirements.txt 已经回退到 0.9.3 + streamlit 1.35 组合，理论上这应该能工作
                
                canvas_result = st_canvas(
                    fill_color="rgba(255, 255, 255, 0)",  
                    stroke_width=stroke_width,
                    stroke_color="#FFFFFF",
                    background_image=original_pil, # 直接传 PIL 对象 (Streamlit 1.35 + Canvas 0.9.3 应该能原生支持)
                    update_streamlit=False,        # 关闭实时更新，解决卡顿
                    height=original_pil.height,
                    width=original_pil.width,
                    drawing_mode="freedraw",
                    key=st.session_state["canvas_key"],
                    display_toolbar=True,
                )
                
                st.caption("💡 提示：如果看不到图片，请尝试刷新页面。")

            except Exception as e:
                st.error(f"组件加载失败: {e}")
                st.info("请尝试重启应用 (Reboot App)。")

            prompt = st.text_area("2. 修改指令", placeholder="例如：Change to red silk dress...", height=80)
            
            if st.button("🚀 开始重绘", type="primary"):
                # 检查蒙版
                has_mask = False
                if canvas_result.image_data is not None:
                    # 检查是否有涂抹 (简单求和)
                    if np.sum(canvas_result.image_data) > 0:
                        has_mask = True
                
                if not has_mask:
                    st.warning("请先涂抹区域！")
                else:
                    with st.spinner("AI 正在重绘..."):
                        try:
                            # 准备原图
                            src_buf = io.BytesIO()
                            original_pil.save(src_buf, format='JPEG', quality=95)
                            
                            # 准备蒙版
                            # Canvas 返回 RGBA (uint8)
                            mask_data = canvas_result.image_data.astype('uint8')
                            mask_img = Image.fromarray(mask_data, mode="RGBA")
                            # 提取 Alpha 通道作为蒙版
                            mask_img = mask_img.split()[3] 
                            
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
                            st.success("完成！")
                        except Exception as e:
                            st.error(f"API 错误: {e}")

    with col_result:
        st.subheader("🖼️ 结果展示")
        if st.session_state["magic_result"]:
            st.image(st.session_state["magic_result"], caption="重绘结果", use_container_width=True)
        else:
            st.info("等待操作...")

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
                with st.spinner("扩展中..."):
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
                        st.error(f"失败: {e}")
    
    with c2:
        if st.session_state["out_result"]:
            st.image(st.session_state["out_result"], caption="扩图结果", use_container_width=True)
