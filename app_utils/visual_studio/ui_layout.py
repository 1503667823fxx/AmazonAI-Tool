import streamlit as st

def render_sidebar():
    """
    渲染 Visual Studio 的侧边栏配置区。
    
    Returns:
        dict: 包含用户所有配置项的字典 (aspect_ratio, style, model_version 等)
    """
    with st.sidebar:
        st.header("⚙️ 参数设置")
        
        # 1. 模型选择 (Flux 有不同版本)
        st.subheader("1. 模型版本")
        model_version = st.selectbox(
            "选择 Flux 模型",
            options=["black-forest-labs/flux-schnell"],
            index=0,
            help="fast 速度快成本低；pro 细节更丰富但稍慢。"
        )
        # 映射回 API 能够识别的字符串标识 (稍后在 service 层会用到)
        model_code = "schnell" if "schnell" in model_version else "dev"

        st.divider()

        # 2. 画幅比例
        st.subheader("2. 图片比例")
        aspect_ratio = st.radio(
            "选择画幅",
            options=["1:1", "4:3", "21:9"],
            index=1,
            horizontal=True
        )

        st.divider()

        # 3. 风格预设 (用于 Gemini 提示词优化)
        st.subheader("3. 艺术风格")
        style_preset = st.selectbox(
            "提示词优化风格",
            options=[
                "Cinematic (电影质感)", 
                "Photographic (写实摄影)", 
                "Anime (日系动漫)", 
                "3D Model (3D模型)", 
                "Neon Punk (赛博霓虹)", 
                "Minimalist (极简主义)",
                "None (保持原意)"
            ],
            index=0
        )

        st.divider()

        # 4. 高级设置 (折叠)
        with st.expander("🛠️ 高级设置"):
            output_format = st.selectbox("输出格式", ["png", "jpg", "webp"])
            safety_tolerance = st.slider("安全过滤等级", 1, 5, 2, help="等级越高过滤越严格")

        # 返回配置字典
        return {
            "model_version": model_code,
            "aspect_ratio": aspect_ratio,
            "style": style_preset,
            "output_format": output_format,
            "safety_tolerance": safety_tolerance
        }

def render_result_area(image_url: str, prompt_used: str):
    """
    渲染生图结果展示区，包含图片展示和下载按钮。
    """
    if image_url:
        st.success("🎉 生成成功！")
        
        # 显示图片
        st.image(image_url, caption="Flux Generated Output", use_container_width=True)
        
        # 操作按钮区
        col1, col2 = st.columns([1, 1])
        with col1:
            # Streamlit 原生不方便直接下载 URL 图片为文件，通常只提供链接
            # 这里做一个简单的链接跳转，或者你可以后续在 Service 层把图下载下来再用 st.download_button
            st.link_button("⬇️ 在浏览器中打开原图", image_url)
        
        with col2:
            with st.expander("查看完整 Prompt"):
                st.code(prompt_used, language="text")
