# pages/9_🔍_HD_Upscale.py
import streamlit as st
import auth
import requests
from io import BytesIO
from PIL import Image

# [核心] 引用专属模块
from services.hd_upscale.upscale_engine import UpscaleEngine
from app_utils.hd_upscale.ui_components import render_upscale_sidebar, render_comparison_result

# 1. 页面配置
st.set_page_config(page_title="Amazon AI - HD Upscale", page_icon="🔍", layout="wide")

# 2. 门禁系统
if not auth.check_password():
    st.stop()

st.title("🔍 图片极致高清化 (HD Upscale)")
st.markdown("使用 **Real-ESRGAN** SOTA 模型对电商图片进行无损放大与细节修复。")

# --- 辅助函数 ---
def download_and_convert_to_jpg(url):
    """下载图片并转换为最高质量的 JPEG 二进制数据"""
    try:
        # 如果 url 是列表（旧缓存残留），强行取第一个
        if isinstance(url, list):
            url = url[0]
            
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        img = Image.open(BytesIO(response.content))
        
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
            
        buf = BytesIO()
        img.save(buf, format="JPEG", quality=100, subsampling=0)
        return buf.getvalue()
    except Exception as e:
        # 记录错误但不弹窗干扰
        print(f"转换失败: {e}")
        return None

# --- [增强] 缓存清理与初始化 ---
# 检查缓存是否被污染（例如 result_url 是列表而不是字符串），如果是，直接清空
if "upscale_result_url" in st.session_state:
    if isinstance(st.session_state["upscale_result_url"], list):
        st.session_state["upscale_result_url"] = None
        st.session_state["upscale_image_bytes"] = None

if "upscale_result_url" not in st.session_state:
    st.session_state["upscale_result_url"] = None
if "upscale_image_bytes" not in st.session_state:
    st.session_state["upscale_image_bytes"] = None

# 3. 初始化引擎
engine = UpscaleEngine()

# 4. 侧边栏
scale_factor, enable_face_enhance = render_upscale_sidebar()

# 5. 主界面
uploaded_file = st.file_uploader("📤 请上传需要放大的图片 (支持 JPG/PNG)", type=["jpg", "jpeg", "png"])

if uploaded_file:
    # 换图清理缓存
    if "last_uploaded_name" not in st.session_state or st.session_state["last_uploaded_name"] != uploaded_file.name:
        st.session_state["upscale_result_url"] = None
        st.session_state["upscale_image_bytes"] = None
        st.session_state["last_uploaded_name"] = uploaded_file.name

    with st.expander("👁️ 预览原图", expanded=False):
        st.image(uploaded_file, width=300)

    # 6. 执行逻辑
    if st.session_state["upscale_result_url"] is None:
        btn = st.button("🚀 开始高清放大 (Start Upscaling)", type="primary", use_container_width=True)
        
        if btn:
            if not engine.client:
                st.error("API Key 配置缺失，无法运行。")
            else:
                try:
                    with st.spinner(f"正在云端进行 {scale_factor}x 极速放大，请稍候..."):
                        # 调用 API
                        result_url = engine.process_image(
                            image_file=uploaded_file,
                            scale=scale_factor,
                            face_enhance=enable_face_enhance
                        )
                        
                        # 下载并转码
                        if result_url:
                            # 兼容性处理：再次确保拿到的是字符串
                            final_url = result_url[0] if isinstance(result_url, list) else result_url
                            
                            jpg_bytes = download_and_convert_to_jpg(final_url)
                            
                            st.session_state["upscale_result_url"] = final_url
                            st.session_state["upscale_image_bytes"] = jpg_bytes
                            st.rerun()
                            
                except Exception as e:
                    st.error(f"处理错误: {e}")

    # 7. 展示结果
    if st.session_state["upscale_image_bytes"]:
        render_comparison_result(
            original_file=uploaded_file,
            result_url=st.session_state["upscale_result_url"],
            download_data=st.session_state["upscale_image_bytes"]
        )
        
        if st.button("🔄 处理下一张图片"):
            st.session_state["upscale_result_url"] = None
            st.session_state["upscale_image_bytes"] = None
            st.rerun()
