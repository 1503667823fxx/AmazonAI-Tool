import streamlit as st
from services.visual_studio import gemini_optimizer, flux_generator
from app_utils.visual_studio import ui_layout, state_manager

# 1. 页面配置
st.set_page_config(page_title="Visual Studio", layout="wide")

# 2. 初始化状态
state_manager.init_visual_studio_state()

# 3. 渲染侧边栏并获取用户配置
user_config = ui_layout.render_sidebar()

# 4. 主界面逻辑
st.title("🎨 Visual Studio - AI Poster Generator")

# 用户输入区
user_input = st.text_area("描述你想要的海报内容...", height=100)

# 按钮逻辑区
col1, col2 = st.columns([1, 4])
with col1:
    if st.button("✨ 优化提示词 (Gemini)"):
        with st.spinner("Gemini Flash 正在思考构图..."):
            # 调用 Service 层
            optimized_text = gemini_optimizer.optimize_prompt_logic(
                user_input, user_config['style']
            )
            st.session_state['vs_optimized_prompt'] = optimized_text
            st.rerun()

# 展示优化后的提示词（允许用户二次修改）
final_prompt = st.text_area(
    "最终生图提示词 (可修改)", 
    value=st.session_state.get('vs_optimized_prompt', ''),
    height=150
)

if st.button("🚀 开始生成海报 (Flux)"):
    if not final_prompt:
        st.warning("请先输入描述或优化提示词")
    else:
        with st.spinner("Flux 正在绘制海报..."):
            # 调用 Service 层
            image_url = flux_generator.generate_image_logic(
                final_prompt, user_config['aspect_ratio']
            )
            st.session_state['vs_generated_image'] = image_url

# 5. 渲染结果区
ui_layout.render_output_area(
    st.session_state.get('vs_generated_image'),
    final_prompt
)
