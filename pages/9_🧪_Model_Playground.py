import streamlit as st
import google.generativeai as genai
from PIL import Image
import io
import sys
import os

# --- 0. 基础设置 ---
sys.path.append(os.path.abspath('.'))
# 页面宽屏模式，方便看大图
st.set_page_config(page_title="Google 生图测试台", page_icon="🧪", layout="wide")

# --- 1. 鉴权配置 ---
if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
else:
    st.error("❌ 未找到 GOOGLE_API_KEY，请检查 secrets.toml")
    st.stop()

# --- 2. 核心功能：获取能画图的模型 ---
@st.cache_data(ttl=3600)
def get_image_generation_models():
    """
    自动检索支持 'generateImages' 的 Google 模型。
    注意：Imagen 3 目前可能是白名单或 Beta 状态，如果没有检索到，
    我们会手动把已知可用的模型名称加进去。
    """
    try:
        image_models = []
        # 尝试从 API 列表里找
        for m in genai.list_models():
            # 检查是否支持生图方法
            if 'generateImages' in m.supported_generation_methods:
                image_models.append(m.name)
        
        # ⚠️ 强制补充：因为 API 有时隐藏 Imagen 3，手动补全最新的
        known_models = [
            "models/imagen-3.0-generate-001",  # Google 最强生图模型
            "models/imagen-2.0"
        ]
        
        # 合并列表并去重
        final_list = list(set(image_models + known_models))
        return sorted(final_list, reverse=True)
    except Exception as e:
        # 如果报错，返回保底列表
        return ["models/imagen-3.0-generate-001"]

# --- 3. 界面布局 ---
st.title("🧪 Google Imagen 专项测试")
st.caption("独立模块：专门用于测试 Google 原生生图能力，解决数据解析报错问题。")

# 左侧控制栏，右侧显示图
col_ctrl, col_show = st.columns([1, 2])

with col_ctrl:
    st.subheader("⚙️ 参数设置")
    
    # 1. 模型选择
    available_models = get_image_generation_models()
    selected_model = st.selectbox(
        "选择 Google 生图模型", 
        available_models,
        index=0
    )
    st.info(f"当前选中: `{selected_model}`")
    
    # 2. 提示词
    prompt = st.text_area(
        "生图提示词 (Prompt)", 
        height=150,
        placeholder="例如：A futuristic fashion photoshoot of a model wearing a glowing cyber-punk jacket, commercial lighting, 8k..."
    )
    
    # 3. 数量和比例
    num_images = st.slider("生成数量", 1, 4, 1)
    aspect_ratio = st.selectbox("图片比例", ["1:1", "16:9", "9:16", "4:3"], index=0)

    # 4. 生成按钮
    btn_generate = st.button("🚀 调用 Google 生成", type="primary")

# --- 4. 生成逻辑与解析修复 ---
with col_show:
    st.subheader("🖼️ 结果展示")
    
    if btn_generate:
        if not prompt:
            st.warning("请先输入提示词！")
        else:
            with st.spinner("Google Imagen 正在绘制 (通常比 Flux 慢一点)..."):
                try:
                    # 实例化生图模型 (这是专门针对 Google Imagen 的写法)
                    # 注意：Gemini 用 GenerativeModel，Imagen 用 ImageGenerationModel
                    # 这种细微区别是导致报错的主要原因
                    
                    # 尝试用通用入口（最新版 SDK 推荐）
                    # 如果你的 SDK 版本较旧，这里可能会有差异，但 try-catch 会捕获
                    
                    # 准备参数
                    generation_config = {
                        "number_of_images": num_images,
                        "aspect_ratio": aspect_ratio.replace(":", "/"), # 某些版本需要 16/9 格式
                        "safety_filter_level": "block_only_high"
                    }
                    
                    # ⚠️ 关键调用
                    # 现在的 Google SDK 并没有统一的入口，这里用最底层的调用方式防止出错
                    from google.generativeai.types import ImageGenerationModel
                    
                    # 必须去掉 'models/' 前缀才能实例化 ImageGenerationModel
                    clean_model_name = selected_model.replace("models/", "")
                    model_instance = ImageGenerationModel(clean_model_name)
                    
                    response = model_instance.generate_images(
                        prompt=prompt,
                        number_of_images=num_images,
                    )
                    
                    # --- 5. 关键修复：如何解析返回的数据 ---
                    # Google 返回的 response.images 是一个 PIL.Image 对象列表
                    # 之前报错是因为你可能试图用 .content 或 .text 去读它
                    
                    if response.images:
                        st.success(f"成功生成 {len(response.images)} 张图片！")
                        
                        cols = st.columns(len(response.images))
                        for idx, img in enumerate(response.images):
                            with cols[idx]:
                                # img 已经是 PIL Image 对象了，可以直接显示
                                st.image(img, caption=f"Result {idx+1}", use_column_width=True)
                                
                                # 为了提供下载，我们需要把它转回 bytes
                                buf = io.BytesIO()
                                img.save(buf, format="PNG")
                                byte_im = buf.getvalue()
                                
                                st.download_button(
                                    label=f"📥 下载图片 {idx+1}",
                                    data=byte_im,
                                    file_name=f"google_imagen_{idx+1}.png",
                                    mime="image/png"
                                )
                    else:
                        st.error("API 返回了空结果，可能是触发了安全拦截 (Safety Filter)。")

                except Exception as e:
                    st.error(f"❌ 生成失败: {str(e)}")
                    st.markdown("""
                    **排查建议：**
                    1. 确保你的 Google API Key 有 **Imagen 3** 的权限 (AI Studio 中需开通)。
                    2. 报错 `404 Not Found`? 说明你选的模型名称不对，请在左侧切换模型试试。
                    3. 报错 `AttributeError`? 可能是你的 `google-generativeai` 库版本太低。
                       尝试在终端运行: `pip install -U google-generativeai`
                    """)

