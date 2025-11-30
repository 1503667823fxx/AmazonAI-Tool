# pages/9_🔍_HD_Upscale.py
import streamlit as st
import auth  # [新增] 引用根目录的 auth.py
import requests
from io import BytesIO
from PIL import Image

# [核心] 引用专属模块
from services.hd_upscale.upscale_engine import UpscaleEngine
from app_utils.hd_upscale.ui_components import render_upscale_sidebar, render_comparison_result

# 1. 页面配置
st.set_page_config(page_title="Amazon AI - HD Upscale", page_icon="🔍", layout="wide")

# 2. [新增] 门禁系统检查
if not auth.check_password():
    st.stop()  # 如果密码不对，直接停止运行后续代码

st.title("🔍 图片极致高清化 (HD Upscale)")
st.markdown("""
使用 **Real-ESRGAN** SOTA 模型对电商图片进行无损放大与细节修复。
""")

# --- 辅助函数：提前处理图片下载和格式转换 ---
def download_and_convert_to_jpg(url):
    """下载图片并转换为最高质量的 JPEG 二进制数据"""
    try:
        response = requests.get(url)
        response.raise_for_status()
        img = Image.open(BytesIO(response.content))
        
        # 转换为 RGB (防止 PNG 透明通道转 JPG 报错)
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
            
        # 转为 Bytes
        buf = BytesIO()
        # quality=100 保证高清，subsampling=0 保证色彩无损
        img.save(buf, format="JPEG", quality=100, subsampling=0)
        return buf.getvalue()
    except Exception as e:
        st.error(f"图片转换失败: {e}")
        return None

# --- 初始化 Session State (缓存) ---
if "upscale_result_url" not in st.session_state:
    st.session_state["upscale_result_url"] = None
if "upscale_image_bytes" not in st.session_state:
    st.session_state["upscale_image_bytes"] = None

# 3. 初始化服务引擎
engine = UpscaleEngine()

# 4. 侧边栏设置
scale_factor, enable_face_enhance = render_upscale_sidebar()

# 5. 主界面：上传区域
uploaded_file = st.file_uploader("📤 请上传需要放大的图片 (支持 JPG/PNG)", type=["jpg", "jpeg", "png"])

if uploaded_file:
    # 每次上传新文件，如果文件名变了，清除旧缓存
    if "last_uploaded_name" not in st.session_state or st.session_state["last_uploaded_name"] != uploaded_file.name:
        st.session_state["upscale_result_url"] = None
        st.session_state["upscale_image_bytes"] = None
        st.session_state["last_uploaded_name"] = uploaded_file.name

    with st.expander("👁️ 预览原图", expanded=False):
        st.image(uploaded_file, width=300)

    # 6. 执行逻辑
    # 只有当没有缓存结果时，才显示“开始放大”按钮
    if st.session_state["upscale_result_url"] is None:
        btn = st.button("🚀 开始高清放大 (Start Upscaling)", type="primary", use_container_width=True)
        
        if btn:
            if not engine.client:
                st.error("API Key 配置缺失，无法运行。")
            else:
                try:
                    with st.spinner(f"正在云端进行 {scale_factor}x 极速放大，请稍候..."):
                        # A. 调用 API
                        result_url = engine.process_image(
                            image_file=uploaded_file,
                            scale=scale_factor,
                            face_enhance=enable_face_enhance
                        )
                        
                        # B. 成功后，立即下载并转换格式存入缓存
                        if result_url:
                            jpg_bytes = download_and_convert_to_jpg(result_url)
                            
                            # 存入 Session State
                            st.session_state["upscale_result_url"] = result_url
                            st.session_state["upscale_image_bytes"] = jpg_bytes
                            
                            # 强制刷新页面以显示结果
                            st.rerun()
                            
                except Exception as e:
                    st.error(f"处理过程中发生错误: {e}")

    # 7. 展示结果 (从缓存读取)
    if st.session_state["upscale_result_url"] and st.session_state["upscale_image_bytes"]:
        # 调用组件展示，并传入已经准备好的二进制数据
        render_comparison_result(
            original_file=uploaded_file,
            result_url=st.session_state["upscale_result_url"],
            download_data=st.session_state["upscale_image_bytes"]
        )
        
        # 提供一个“重置”按钮
        if st.button("🔄 处理下一张图片"):
            st.session_state["upscale_result_url"] = None
            st.session_state["upscale_image_bytes"] = None
            st.rerun()
