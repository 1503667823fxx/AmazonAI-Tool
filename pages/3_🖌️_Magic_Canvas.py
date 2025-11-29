import streamlit as st
from PIL import Image, ImageOps
import io
import numpy as np
from streamlit_drawable_canvas import st_canvas

# --- 1. 环境与依赖设置 ---
import sys
import os

# 确保路径正确
current_script_path = os.path.abspath(__file__)
pages_dir = os.path.dirname(current_script_path)
root_dir = os.path.dirname(pages_dir)
if root_dir not in sys.path:
    sys.path.append(root_dir)

try:
    import auth
    from services.image_engine import ImageGenEngine # 复用你的通用生图引擎
except ImportError as e:
    st.error(f"❌ 核心模块丢失: {e}")
    st.stop()

st.set_page_config(page_title="Magic Canvas", page_icon="🖌️", layout="wide")

# --- 2. 鉴权 ---
if 'auth' in sys.modules and not auth.check_password():
    st.stop()

# --- 3. 初始化服务 ---
if "magic_engine" not in st.session_state:
    api_key = st.secrets.get("GOOGLE_API_KEY")
    st.session_state.magic_engine = ImageGenEngine(api_key)

# --- 4. 辅助函数：处理画布返回的 Mask ---
def process_canvas_data(canvas_result, original_img):
    """
    将画布的绘制数据转换为 AI 能看懂的黑白 Mask
    """
    if canvas_result.image_data is not None:
        # 1. 获取画布数据 (RGBA)
        mask_data = canvas_result.image_data
        
        # 2. 转为 numpy 数组
        mask_np = np.array(mask_data)
        
        # 3. 提取 Alpha 通道 (透明度)，有涂抹的地方 Alpha > 0
        # 我们需要：涂抹区域=255 (白), 背景=0 (黑)
        # mask_np[:, :, 3] 是 Alpha 通道
        mask_alpha = mask_np[:, :, 3]
        
        # 4. 二值化处理：只要有涂抹，就设为全白
        mask_final = np.where(mask_alpha > 0, 255, 0).astype(np.uint8)
        
        # 5. 转回 PIL Image
        mask_img = Image.fromarray(mask_final)
        
        # 6. 确保尺寸一致 (防止缩放导致的错位)
        if mask_img.size != original_img.size:
            mask_img = mask_img.resize(original_img.size, resample=Image.NEAREST)
            
        return mask_img
    return None

# --- 5. 页面布局 ---
st.title("🖌️ Magic Canvas (手动模式)")
st.caption("无需任何插件，直接涂抹你想修改的区域，AI 帮你实现魔法。")

col_tools, col_canvas = st.columns([1, 2])

# 初始化状态
if "uploaded_image" not in st.session_state:
    st.session_state.uploaded_image = None

with col_tools:
    st.subheader("🛠️ 工具栏")
    
    # A. 上传
    uploaded_file = st.file_uploader("1. 上传原图", type=["png", "jpg", "webp"])
    if uploaded_file:
        # 读取图片并统一转为 RGB
        image = Image.open(uploaded_file).convert("RGB")
        # 限制最大尺寸，防止画布卡顿
        image.thumbnail((800, 800)) 
        st.session_state.uploaded_image = image
    
    st.divider()

    # B. 画笔设置
    brush_size = st.slider("🖊️ 画笔大小", 5, 100, 30)
    st.info("💡 操作指南：\n1. 在右侧图片上涂抹你要修改的区域。\n2. 涂抹区域会变成半透明颜色。\n3. 在下方输入指令并生成。")
    
    # C. 创意指令
    prompt = st.text_area("2. 魔法指令", height=100, placeholder="例如：给模特戴上一副红色墨镜")
    
    # D. 执行按钮
    run_btn = st.button("🚀 开始施法", type="primary", use_container_width=True)

with col_canvas:
    if st.session_state.uploaded_image:
        st.subheader("🎨 绘图区")
        
        # 核心组件：Drawable Canvas
        # 这里的 key 很重要，换图片时需要重置画布
        canvas_result = st_canvas(
            fill_color="rgba(255, 0, 0, 0.3)",  # 涂抹时的填充色 (半透明红)
            stroke_width=brush_size,
            stroke_color="rgba(255, 0, 0, 0.3)", # 画笔颜色
            background_image=st.session_state.uploaded_image,
            update_streamlit=True,
            height=st.session_state.uploaded_image.height,
            width=st.session_state.uploaded_image.width,
            drawing_mode="freedraw", # 自由涂抹模式
            key="magic_canvas_v1",
        )
        
        # 处理逻辑
        if run_btn:
            if not prompt:
                st.toast("⚠️ 请输入魔法指令！")
            elif canvas_result.image_data is None:
                st.toast("⚠️ 请先在图片上涂抹修改区域！")
            else:
                with st.status("🔮 正在施展魔法...", expanded=True):
                    # 1. 提取 Mask
                    st.write("🔍 正在解析涂抹区域...")
                    mask_img = process_canvas_data(canvas_result, st.session_state.uploaded_image)
                    
                    if mask_img:
                        # 调试：显示一下 Mask 确保没问题 (可选)
                        # st.image(mask_img, caption="生成的 Mask", width=200)
                        
                        # 2. 调用生图引擎 (这里我们用 Gemini 的 edit 功能，如果不支持则退化为生图)
                        # 注意：目前的 ImageGenEngine 是基础版，我们在这里做一个简单的适配
                        st.write("🎨 AI 正在重绘...")
                        
                        try:
                            # ⚠️ 这里假设你的 image_engine 还没有 edit 功能
                            # 正常来说应该调用 engine.edit(image, mask, prompt)
                            # 为了演示不报错，我们这里先用“图生图”代替，或者你需要去 services/image_engine.py 补充 edit 方法
                            # 下面是伪代码，如果你有 edit 接口请替换：
                            
                            # 临时方案：调用 Gemini 生图 (带原图参考)
                            # 实际上 Gemini Pro Vision 目前的 Edit API 还在白名单阶段
                            # 如果你没有 edit 权限，这里可以提示用户
                            
                            st.warning("⚠️ 提示：您的 Image Engine 可能尚未解锁 'Inpainting/Edit' 权限。")
                            st.info("当前为您展示：基于原图和Prompt的重绘 (可能会改变全图)")
                            
                            # 调用现有的 generate (当作图生图用)
                            result_bytes = st.session_state.magic_engine.generate(
                                prompt=prompt,
                                model_name="models/gemini-3-pro-image-preview", # 使用支持图像的模型
                                ref_image=st.session_state.uploaded_image
                            )
                            
                            if result_bytes:
                                st.success("✨ 魔法完成！")
                                st.image(result_bytes, caption="生成结果")
                            else:
                                st.error("生成失败，请检查 Prompt 或 API Key。")
                                
                        except Exception as e:
                            st.error(f"处理出错: {e}")
                    else:
                        st.error("无法生成有效的 Mask，请重试涂抹。")

    else:
        # 占位符
        st.info("👈 请先在左侧上传一张图片。")
        st.markdown(
            '<div style="border: 2px dashed #ddd; height: 500px; display: flex; align-items: center; justify-content: center; color: #888;">画布空白</div>', 
            unsafe_allow_html=True
        )
