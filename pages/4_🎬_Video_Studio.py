import streamlit as st
import asyncio
import time
import json
from typing import Optional, Dict, Any, List
from datetime import datetime

from auth import check_password  # 引入门禁系统

# --- 1. 门禁检查 ---
if not check_password():
    st.stop()

# --- 2. 页面配置 ---
st.set_page_config(
    page_title="Google Veo 3.1 视频生成器",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="collapsed"  # 隐藏侧边栏
)

st.title("🎬 Google Veo 3.1 AI视频生成器")
st.caption("从文字描述到高质量短视频，最长8秒，支持720p/1080p")

# --- 3. 检查API配置 ---
api_key_configured = False
try:
    google_api_key = st.secrets.get("GOOGLE_API_KEY")
    if google_api_key:
        api_key_configured = True
    else:
        st.error("❌ 未配置Google API密钥")
        st.info("💡 请在Streamlit Secrets中配置 GOOGLE_API_KEY")
        st.code('GOOGLE_API_KEY = "your_google_api_key"')
        st.stop()
except Exception as e:
    st.error("❌ 无法读取API配置")
    st.info("💡 请在Streamlit Secrets中配置 GOOGLE_API_KEY")
    st.stop()

# --- 4. Session State 初始化 ---
if 'generation_history' not in st.session_state:
    st.session_state.generation_history = []
if 'current_job' not in st.session_state:
    st.session_state.current_job = None

# --- 5. 主界面 ---
st.markdown("---")

# 创建两列布局
col_input, col_output = st.columns([1, 1])

with col_input:
    st.subheader("📝 视频生成设置")
    
    # 提示词输入
    prompt = st.text_area(
        "视频描述",
        placeholder="描述你想要生成的视频内容，例如：一只可爱的小猫在花园里玩耍，阳光明媚，画面温馨",
        height=100,
        help="详细描述视频内容，包括场景、动作、风格等"
    )
    
    # 参考图片上传
    reference_image = st.file_uploader(
        "参考图片（可选）",
        type=['jpg', 'jpeg', 'png'],
        help="上传一张参考图片来引导视频生成"
    )
    
    # 视频参数设置
    st.markdown("**视频参数**")
    
    col_duration, col_ratio = st.columns(2)
    with col_duration:
        duration = st.slider("时长（秒）", 1, 8, 4, help="Veo 3.1最大支持8秒")
    
    with col_ratio:
        aspect_ratio = st.selectbox(
            "宽高比",
            ["16:9", "9:16"],
            help="16:9适合横屏，9:16适合竖屏"
        )
    
    col_quality, col_seed = st.columns(2)
    with col_quality:
        quality = st.selectbox("分辨率", ["720p", "1080p"], index=1)
    
    with col_seed:
        use_seed = st.checkbox("固定种子")
        seed = st.number_input("种子值", 0, 999999, 42) if use_seed else None
    
    # 高级选项
    with st.expander("🔧 高级选项"):
        negative_prompt = st.text_area(
            "负面提示词（可选）",
            placeholder="描述不希望出现在视频中的内容",
            height=60
        )
        
        generate_audio = st.checkbox("生成音频", help="为视频生成配套音频")
    
    # 生成按钮
    st.markdown("---")
    generate_btn = st.button(
        "🎬 生成视频",
        type="primary",
        use_container_width=True,
        disabled=not prompt.strip()
    )
    
    if not prompt.strip():
        st.warning("⚠️ 请输入视频描述")

with col_output:
    st.subheader("🎥 生成结果")
    
    if generate_btn and prompt.strip():
        # 模拟生成过程
        with st.spinner("🚀 正在生成视频..."):
            # 创建任务
            job_id = f"veo_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # 保存任务信息
            task_info = {
                "job_id": job_id,
                "prompt": prompt,
                "duration": duration,
                "aspect_ratio": aspect_ratio,
                "quality": quality,
                "seed": seed,
                "negative_prompt": negative_prompt,
                "generate_audio": generate_audio,
                "status": "processing",
                "created_at": datetime.now(),
                "progress": 0
            }
            
            st.session_state.current_job = task_info
            st.session_state.generation_history.insert(0, task_info)
            
            # 显示进度
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # 模拟进度更新
            for i in range(101):
                progress_bar.progress(i)
                if i < 30:
                    status_text.text("🔄 正在处理提示词...")
                elif i < 60:
                    status_text.text("🎨 正在生成视频帧...")
                elif i < 90:
                    status_text.text("🎞️ 正在合成视频...")
                else:
                    status_text.text("✅ 生成完成！")
                
                time.sleep(0.05)  # 模拟处理时间
            
            # 更新任务状态
            st.session_state.current_job["status"] = "completed"
            st.session_state.current_job["progress"] = 100
            st.session_state.current_job["video_url"] = "https://example.com/mock_video.mp4"
            
            st.success("🎉 视频生成完成！")
            st.rerun()
    
    # 显示当前任务结果
    if st.session_state.current_job:
        job = st.session_state.current_job
        
        if job["status"] == "completed":
            st.success("✅ 生成完成")
            
            # 显示视频信息
            st.info(f"""
            **视频信息**
            - 时长: {job['duration']}秒
            - 分辨率: {job['quality']}
            - 宽高比: {job['aspect_ratio']}
            - 任务ID: {job['job_id']}
            """)
            
            # 模拟视频预览
            st.video("https://sample-videos.com/zip/10/mp4/SampleVideo_1280x720_1mb.mp4")
            
            # 下载按钮
            col_download, col_share = st.columns(2)
            with col_download:
                st.download_button(
                    "📥 下载视频",
                    data=b"mock_video_data",  # 实际应该是视频文件
                    file_name=f"{job['job_id']}.mp4",
                    mime="video/mp4"
                )
            
            with col_share:
                if st.button("🔗 复制链接"):
                    st.success("链接已复制到剪贴板")
        
        elif job["status"] == "processing":
            st.info("🔄 正在生成中...")
            st.progress(job["progress"] / 100)

# --- 6. 生成历史 ---
if st.session_state.generation_history:
    st.markdown("---")
    st.subheader("📚 生成历史")
    
    # 显示最近的5个任务
    for i, task in enumerate(st.session_state.generation_history[:5]):
        with st.expander(f"任务 {i+1}: {task['prompt'][:50]}..."):
            col_info, col_action = st.columns([3, 1])
            
            with col_info:
                st.write(f"**状态**: {'✅ 完成' if task['status'] == 'completed' else '🔄 处理中'}")
                st.write(f"**时长**: {task['duration']}秒")
                st.write(f"**分辨率**: {task['quality']}")
                st.write(f"**创建时间**: {task['created_at'].strftime('%Y-%m-%d %H:%M')}")
            
            with col_action:
                if task['status'] == 'completed':
                    if st.button(f"重新生成", key=f"regenerate_{i}"):
                        # 重新填充参数
                        st.session_state.regenerate_params = task
                        st.rerun()

# --- 7. 使用提示 ---
st.markdown("---")
with st.expander("💡 使用提示"):
    st.markdown("""
    **最佳实践：**
    - 使用清晰、具体的描述
    - 描述动作和场景细节
    - 考虑8秒时长限制
    - 16:9适合横屏观看，9:16适合手机竖屏
    
    **示例提示词：**
    - "一只橙色的小猫在绿色草地上追逐蝴蝶，阳光透过树叶洒下斑驳光影"
    - "城市夜景中霓虹灯闪烁，车流如光河般流淌，现代都市风格"
    - "海浪轻柔地拍打着沙滩，夕阳西下，天空呈现橙红色渐变"
    
    **技术限制：**
    - 最大时长：8秒
    - 支持分辨率：720p, 1080p
    - 支持宽高比：16:9, 9:16
    - 生成时间：通常3-10分钟
    """)

# --- 8. 页脚信息 ---
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #666; font-size: 0.8em;'>
        Powered by Google Veo 3.1 | 
        <a href='https://deepmind.google/technologies/veo/' target='_blank'>了解更多</a>
    </div>
    """,
    unsafe_allow_html=True
)
