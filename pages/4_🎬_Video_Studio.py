import streamlit as st
import asyncio
import time
import json
from typing import Optional, Dict, Any, List
from datetime import datetime

from auth import check_password  # 引入门禁系统
from services.video_studio.veo_service import generate_video_sync, get_video_status_sync

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
        # 真正的API调用
        with st.spinner("🚀 正在调用Google Veo API..."):
            # 处理参考图片
            reference_image_bytes = None
            if reference_image is not None:
                reference_image_bytes = reference_image.read()
            
            # 调用真正的API
            result = generate_video_sync(
                prompt=prompt,
                duration=duration,
                aspect_ratio=aspect_ratio,
                quality=quality,
                reference_image=reference_image_bytes,
                negative_prompt=negative_prompt if negative_prompt.strip() else None,
                seed=seed,
                generate_audio=generate_audio
            )
            
            if result["success"]:
                # 创建任务信息
                task_info = {
                    "job_id": result["job_id"],
                    "prompt": prompt,
                    "duration": duration,
                    "aspect_ratio": aspect_ratio,
                    "quality": quality,
                    "seed": seed,
                    "negative_prompt": negative_prompt,
                    "generate_audio": generate_audio,
                    "status": "processing",
                    "created_at": datetime.now(),
                    "progress": 0,
                    "video_url": None
                }
                
                st.session_state.current_job = task_info
                st.session_state.generation_history.insert(0, task_info)
                
                st.success(f"✅ {result['message']}")
                st.info(f"任务ID: {result['job_id']}")
                st.info("⏳ 视频生成通常需要3-10分钟，请耐心等待...")
                st.rerun()
            else:
                st.error(f"❌ 生成失败: {result['error']}")
    
    # 显示当前任务结果和状态更新
    if st.session_state.current_job:
        job = st.session_state.current_job
        
        # 自动刷新状态（如果任务还在进行中）
        if job["status"] == "processing":
            # 获取最新状态
            status_result = get_video_status_sync(job["job_id"])
            
            # 更新任务状态
            job["status"] = status_result["status"]
            job["progress"] = status_result["progress"]
            
            if "video_url" in status_result:
                job["video_url"] = status_result["video_url"]
            
            if "error" in status_result:
                job["error"] = status_result["error"]
        
        # 显示状态
        if job["status"] == "processing":
            st.info("🔄 正在生成中...")
            progress_bar = st.progress(job["progress"] / 100)
            st.write(f"进度: {job['progress']}%")
            
            # 手动刷新按钮
            if st.button("🔄 刷新状态"):
                st.rerun()
            
            st.info("💡 点击'刷新状态'按钮查看最新进度")
            
        elif job["status"] == "completed":
            st.success("✅ 生成完成")
            
            # 显示视频信息
            st.info(f"""
            **视频信息**
            - 时长: {job['duration']}秒
            - 分辨率: {job['quality']}
            - 宽高比: {job['aspect_ratio']}
            - 任务ID: {job['job_id']}
            """)
            
            # 显示视频（如果有URL）
            if job.get("video_url"):
                st.video(job["video_url"])
                
                # 下载按钮
                col_download, col_share = st.columns(2)
                with col_download:
                    st.markdown(f"[📥 下载视频]({job['video_url']})")
                
                with col_share:
                    if st.button("🔗 复制链接"):
                        st.code(job["video_url"])
                        st.success("链接已显示，请手动复制")
            else:
                st.warning("⚠️ 视频URL不可用")
        
        elif job["status"] == "failed":
            st.error("❌ 生成失败")
            if "error" in job:
                st.error(f"错误信息: {job['error']}")
            
            # 重试按钮
            if st.button("🔄 重新生成"):
                st.session_state.current_job = None
                st.rerun()
        
        else:
            st.warning(f"⚠️ 未知状态: {job['status']}")

# --- 6. 生成历史 ---
if st.session_state.generation_history:
    st.markdown("---")
    st.subheader("📚 生成历史")
    
    # 显示最近的5个任务
    for i, task in enumerate(st.session_state.generation_history[:5]):
        with st.expander(f"任务 {i+1}: {task['prompt'][:50]}..."):
            col_info, col_action = st.columns([3, 1])
            
            with col_info:
                status_emoji = {
                    "completed": "✅",
                    "processing": "🔄", 
                    "failed": "❌"
                }.get(task["status"], "❓")
                
                st.write(f"**状态**: {status_emoji} {task['status']}")
                st.write(f"**时长**: {task['duration']}秒")
                st.write(f"**分辨率**: {task['quality']}")
                st.write(f"**创建时间**: {task['created_at'].strftime('%Y-%m-%d %H:%M')}")
                st.write(f"**任务ID**: {task['job_id']}")
            
            with col_action:
                if task['status'] == 'completed' and task.get('video_url'):
                    st.markdown(f"[📥 下载]({task['video_url']})")
                
                if st.button(f"🔄 重新生成", key=f"regenerate_{i}"):
                    # 重新填充参数并清除当前任务
                    st.session_state.current_job = None
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
    
    **API状态说明：**
    - 🔄 processing: 正在生成中
    - ✅ completed: 生成完成
    - ❌ failed: 生成失败
    """)

# --- 8. API状态信息 ---
with st.expander("🔧 API状态信息"):
    st.warning("⚠️ **重要说明**: 当前使用模拟API端点，因为Google Veo 3.1 API尚未公开发布")
    
    st.write("**当前配置:**")
    st.write(f"- API密钥: {'✅ 已配置' if api_key_configured else '❌ 未配置'}")
    st.write(f"- 服务状态: {'🟡 模拟模式' if api_key_configured else '🔴 不可用'}")
    st.write("- API端点: 模拟端点（等待官方发布）")
    
    st.info("""
    **关于真实API:**
    - Google Veo 3.1目前仍处于预览阶段
    - 官方API端点和文档尚未公开
    - 当前实现提供完整的UI和框架
    - 一旦官方API发布，只需更新端点即可启用真实功能
    """)
    
    if st.session_state.current_job:
        st.write("**当前任务:**")
        st.json({
            "job_id": st.session_state.current_job["job_id"],
            "status": st.session_state.current_job["status"],
            "progress": st.session_state.current_job["progress"],
            "created_at": st.session_state.current_job["created_at"].isoformat(),
            "note": "模拟任务 - 非真实API调用"
        })

# --- 9. 页脚信息 ---
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #666; font-size: 0.8em;'>
        Powered by Google Veo 3.1 | 
        <a href='https://deepmind.google/technologies/veo/' target='_blank'>了解更多</a> |
        ⚠️ 注意：当前使用模拟API端点，实际部署需要配置正确的Google Veo API
    </div>
    """,
    unsafe_allow_html=True
)
