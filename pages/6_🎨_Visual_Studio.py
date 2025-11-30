import streamlit as st
import time

# ==============================================================================
# 1. 模块导入 (极致模块化设计)
# ==============================================================================
# 注意：这些模块我们稍后创建，这里先定义好接口规范
try:
    from services.visual_studio import prompt_service, image_service
    from app_utils.visual_studio import ui_layout, state_manager
except ImportError:
    # 首次运行时防止报错，提示用户还需要创建依赖文件
    st.error("⚠️ 核心依赖模块未找到。请确保 'services/visual_studio' 和 'app_utils/visual_studio' 已正确创建。")
    st.stop()

# ==============================================================================
# 2. 页面基础配置
# ==============================================================================
st.set_page_config(
    page_title="Visual Studio | Amazon AI",
    page_icon="🎨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 初始化 Session State (委托给工具包处理)
state_manager.init_visual_studio_state()

# ==============================================================================
# 3. 侧边栏：参数配置区
# ==============================================================================
# render_sidebar 返回用户配置的字典，例如 {'style': 'Cinematic', 'ratio': '9:16', ...}
user_config = ui_layout.render_sidebar()

# ==============================================================================
# 4. 主界面：业务逻辑流
# ==============================================================================
st.title("🎨 Visual Studio - AI 海报工坊")
st.markdown("##### 🚀 谷歌 Gemini 构思 + Flux 极致生图")

# --- 第一步：用户输入与提示词优化 (Prompt Engineering) ---
with st.container():
    col_input, col_opt_btn = st.columns([5, 1])
    
    with col_input:
        # 用户输入简单的中文描述
        raw_prompt = st.text_area(
            "📝 描述你的创意 (支持中文):",
            placeholder="例如：一个悬浮在太空中的透明发光运动鞋，赛博朋克风格，霓虹灯光...",
            height=100,
            key="vs_raw_input"
        )
    
    with col_opt_btn:
        st.write("") # 占位对齐
        st.write("") 
        # 调用 Gemini 优化
        if st.button("✨ AI 润色\n(Gemini)", use_container_width=True, type="primary"):
            if not raw_prompt:
                st.warning("请先输入描述！")
            else:
                try:
                    with st.spinner("🤖 Gemini Flash 正在构建画面细节..."):
                        # [Service调用] 获取优化后的英文 Prompt
                        optimized_text = prompt_service.optimize_prompt(
                            user_input=raw_prompt, 
                            style_preset=user_config['style']
                        )
                        # 更新状态
                        st.session_state['vs_final_prompt'] = optimized_text
                        st.success("优化完成！")
                except Exception as e:
                    st.error(f"优化失败: {str(e)}")

# --- 第二步：确认提示词与生图 (Generation) ---
# 显示/编辑最终的提示词
final_prompt = st.text_area(
    "🇺🇸 最终生图提示词 (英文，可手动微调):",
    value=st.session_state.get('vs_final_prompt', ''),
    height=120,
    help="Flux 模型对英文理解最好，这里显示的是 Gemini 翻译并扩写后的结果。"
)

# 生成按钮区
col_gen_btn, col_blank = st.columns([1, 4])
with col_gen_btn:
    if st.button("🎨 开始生图 (Flux)", type="primary", use_container_width=True):
        if not final_prompt:
            st.warning("提示词不能为空，请先输入描述或点击AI润色。")
        else:
            try:
                with st.spinner(f"⚡ Flux [{user_config['model_version']}] 正在绘制海报..."):
                    start_time = time.time()
                    
                    # [Service调用] 调用 Replicate 接口
                    image_url = image_service.generate_image_replicate(
                        prompt=final_prompt,
                        aspect_ratio=user_config['aspect_ratio'],
                        output_format=user_config['output_format'],
                        safety_tolerance=user_config['safety_tolerance'] # 预留高级参数
                    )
                    
                    # 存入状态
                    st.session_state['vs_current_image'] = image_url
                    st.toast(f"生成完毕！耗时 {round(time.time() - start_time, 2)}s", icon="✅")
            
            except Exception as e:
                st.error(f"生图服务异常: {str(e)}")

# ==============================================================================
# 5. 结果展示区
# ==============================================================================
st.divider()

# 委托给工具包渲染结果 (包括图片展示、下载按钮、历史记录保存逻辑)
if st.session_state.get('vs_current_image'):
   ui_layout.render_result_area(
        image_url=st.session_state['vs_current_image'],
        prompt_used=final_prompt
    )
else:
    st.info("👈 在上方输入描述并点击 'AI 润色' 开始创作。")

