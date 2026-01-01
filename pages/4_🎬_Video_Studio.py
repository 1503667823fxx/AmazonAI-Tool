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

# --- 3. SDK状态检查 ---
try:
    from services.video_studio.veo_service import get_veo_service
    service = get_veo_service()
    if not service:
        st.error("⚠️ Veo服务初始化失败")
        st.info("💡 可能的原因：")
        st.markdown("""
        - Google GenAI SDK 未安装：`pip install google-genai`
        - API密钥未配置：检查 GOOGLE_API_KEY
        - 云端环境限制：某些包可能无法在云端正确安装
        """)
        st.stop()
except Exception as e:
    st.error(f"⚠️ 导入Veo服务失败: {str(e)}")
    st.info("💡 这通常表示依赖包未正确安装")
    st.stop()

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
    st.error(f"错误详情: {str(e)}")
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
    st.markdown("**参考图片**")
    
    reference_image = st.file_uploader(
        "参考图片（可选）",
        type=['jpg', 'jpeg', 'png', 'webp'],
        help="上传一张参考图片来引导视频生成，支持JPG、PNG、WEBP格式"
    )
    
    # 验证图片
    if reference_image is not None:
        from services.video_studio import validate_uploaded_image
        
        image_bytes = reference_image.read()
        validation = validate_uploaded_image(image_bytes)
        
        if validation["valid"]:
            st.success("✅ 图片验证通过")
            col_img, col_info = st.columns([1, 1])
            
            with col_img:
                st.image(reference_image, caption="参考图片", use_container_width=True)
            
            with col_info:
                st.info(f"""
                **图片信息**
                - 格式: {validation['format']}
                - 尺寸: {validation['size'][0]} x {validation['size'][1]}
                - 文件大小: {validation['file_size']/1024:.1f} KB
                """)
                
                st.info("""
                📋 **图片到视频说明**
                - 使用官方Google示例方法
                - 时长: 固定8秒
                - 质量: 推荐720p
                - 处理时间: 5-15分钟
                """)
        else:
            st.error(f"❌ 图片验证失败: {validation['error']}")
            reference_image = None
    
    # 视频参数设置
    st.markdown("**视频参数**")
    
    # 重要限制提醒
    st.info("""
    📋 **Veo 3.1 重要限制**
    - **分辨率和时长组合限制：**
      - 🔸 **720p**: 支持 4秒、6秒、8秒
      - 🔸 **1080p**: 仅支持 8秒
    - **参考图片**: 使用参考图片时只能生成 **8秒** 视频
    - **自动调整**: 如果选择不兼容的组合，系统会自动调整为720p
    """)
    
    col_duration, col_ratio = st.columns(2)
    with col_duration:
        # 如果有参考图片，显示固定值而不是滑块
        if reference_image is not None:
            st.markdown("**时长（秒）**")
            duration = 8
            st.info("💡 使用参考图片时，时长固定为8秒")
            st.markdown(f"<div style='padding: 10px; background-color: #f0f2f6; border-radius: 5px; text-align: center; font-size: 18px; font-weight: bold;'>{duration} 秒</div>", unsafe_allow_html=True)
        else:
            duration = st.slider("时长（秒）", 4, 8, 4, step=2, help="Veo 3.1支持4、6、8秒")
        
        # 添加时长限制提醒
        if duration not in [4, 6, 8]:
            st.warning("⚠️ Veo 3.1仅支持4秒、6秒或8秒时长")
    
    with col_ratio:
        aspect_ratio = st.selectbox(
            "宽高比",
            ["16:9", "9:16"],
            help="16:9适合横屏，9:16适合竖屏"
        )
    
    col_quality, col_seed = st.columns(2)
    with col_quality:
        quality = st.selectbox("分辨率", ["720p", "1080p"], index=0)  # 默认选择720p
        
        # 动态显示分辨率限制
        if quality == "1080p":
            if duration != 8:
                st.warning("⚠️ 1080p分辨率仅支持8秒时长，系统将自动调整为720p")
            else:
                st.success("✅ 1080p + 8秒 - 兼容组合")
        else:  # 720p
            st.info(f"✅ 720p + {duration}秒 - 兼容组合")
    
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
    
    # 生成按钮
    st.markdown("---")
    
    # 验证参数组合
    validation_errors = []
    warnings = []
    
    if duration not in [4, 6, 8]:
        validation_errors.append(f"时长 {duration}秒 不支持，请选择4、6或8秒")
    
    # 检查分辨率和时长组合
    if quality == "1080p" and duration != 8:
        warnings.append(f"1080p分辨率需要8秒时长，系统将自动调整为720p")
    
    # 显示验证错误和警告
    if validation_errors:
        for error in validation_errors:
            st.error(f"❌ {error}")
    
    if warnings:
        for warning in warnings:
            st.warning(f"⚠️ {warning}")
    
    generate_btn = st.button(
        "🎬 生成视频",
        type="primary",
        use_container_width=True,
        disabled=not prompt.strip() or len(validation_errors) > 0
    )
    
    if not prompt.strip():
        st.warning("⚠️ 请输入视频描述")
    elif validation_errors:
        st.warning("⚠️ 请修正上述参数问题")
    elif warnings:
        st.info("💡 系统将自动调整参数以确保兼容性")

with col_output:
    st.subheader("🎥 生成结果")
    
    if generate_btn and prompt.strip():
        # 真正的API调用
        with st.spinner("🚀 正在调用Google Veo API..."):
            # 处理参考图片
            reference_image_bytes = None
            if reference_image is not None:
                # 重新读取图片数据（因为之前验证时已经读取过）
                reference_image.seek(0)  # 重置文件指针
                reference_image_bytes = reference_image.read()
            
            # 调用真正的API
            result = generate_video_sync(
                prompt=prompt,
                duration=duration,
                aspect_ratio=aspect_ratio,
                quality=quality,
                reference_image=reference_image_bytes,
                negative_prompt=negative_prompt if negative_prompt.strip() else None,
                seed=seed
            )
            
            if result["success"]:
                # 创建任务信息
                task_info = {
                    "job_id": result["job_id"],
                    "operation_name": result["operation_name"],  # 保存完整的操作名称
                    "prompt": prompt,
                    "duration": duration,
                    "aspect_ratio": aspect_ratio,
                    "quality": quality,
                    "seed": seed,
                    "negative_prompt": negative_prompt,
                    "generate_audio": generate_audio,
                    "status": "processing",
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),  # 添加timestamp
                    "created_at": datetime.now(),
                    "progress": 0,
                    "video_url": None,
                    "video_bytes": None
                }
                
                st.session_state.current_job = task_info
                st.session_state.generation_history.insert(0, task_info)
                
                st.success(f"✅ {result['message']}")
                st.info(f"任务ID: {result['job_id']}")
                st.info("⏳ 视频生成通常需要3-10分钟，请耐心等待...")
                st.rerun()
            else:
                st.error(f"❌ 生成失败: {result['error']}")
                
                # 显示详细错误信息
                with st.expander("🔍 详细错误信息"):
                    st.json(result)
    
    # 显示当前任务结果和状态更新
    if st.session_state.current_job:
        job = st.session_state.current_job
        
        # 自动刷新状态（如果任务还在进行中）
        if job["status"] == "processing":
            # 显示进度状态
            st.info("🔄 正在生成中...")
            progress_bar = st.progress(job["progress"] / 100)
            st.write(f"进度: {job['progress']}%")
            
            # 获取最新状态
            with st.spinner("检查生成状态..."):
                try:
                    status_result = get_video_status_sync(job["operation_name"])
                except Exception as e:
                    st.error(f"状态查询失败: {str(e)}")
                    status_result = {
                        "status": "error",
                        "progress": 0,
                        "error": f"状态查询异常: {str(e)}"
                    }
            
            # 更新任务状态
            job["status"] = status_result["status"]
            job["progress"] = status_result["progress"]
            
            if "video_bytes" in status_result:
                job["video_bytes"] = status_result["video_bytes"]
            if "video_url" in status_result:
                job["video_url"] = status_result["video_url"]
            if "raw_response" in status_result:
                job["raw_response"] = status_result["raw_response"]
            
            if "error" in status_result:
                job["error"] = status_result["error"]
            
            # 如果仍在处理中，使用自动刷新
            if job["status"] == "processing":
                st.info("⏳ 视频生成中，页面将在5秒后自动刷新...")
                
                # 创建一个占位符用于倒计时
                countdown_placeholder = st.empty()
                for i in range(5, 0, -1):
                    countdown_placeholder.info(f"⏳ {i}秒后自动刷新...")
                    time.sleep(1)
                
                countdown_placeholder.empty()
                st.rerun()
            else:
                # 状态已改变，立即显示结果
                st.success("🎉 状态更新，正在显示结果...")
                time.sleep(1)  # 短暂延迟让用户看到状态变化
                st.rerun()
        
        # 显示最终状态
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
            
            # 显示视频（只使用字节数据）
            if job.get("video_bytes"):
                try:
                    import base64
                    import tempfile
                    import os
                    
                    # 解码base64视频数据
                    video_bytes = base64.b64decode(job["video_bytes"])
                    
                    # 创建临时文件
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp_file:
                        tmp_file.write(video_bytes)
                        tmp_file_path = tmp_file.name
                    
                    # 显示视频
                    st.video(tmp_file_path)
                    
                    # 提供下载选项
                    st.download_button(
                        label="📥 下载视频",
                        data=video_bytes,
                        file_name=f"veo_video_{job['job_id']}.mp4",
                        mime="video/mp4"
                    )
                    
                    # 清理临时文件
                    try:
                        os.unlink(tmp_file_path)
                    except:
                        pass
                        
                except Exception as e:
                    st.error(f"视频处理失败: {str(e)}")
                    
                    # 显示调试信息
                    with st.expander("🔍 调试信息"):
                        st.write(f"任务ID: {job['job_id']}")
                        if "raw_response" in job:
                            st.json(job["raw_response"])
            else:
                st.error("⚠️ 视频数据不可用")
                st.info("💡 视频生成成功但无法获取视频数据，请检查SDK配置")
                
                # 显示任务ID
                st.code(f"任务ID: {job['job_id']}")
                
                # 显示调试信息
                with st.expander("🔍 调试信息"):
                    st.write(f"任务ID: {job['job_id']}")
                    st.write(f"操作名称: {job.get('operation_name', 'N/A')}")
                    
                    if "raw_response" in job:
                        st.write("**API原始响应:**")
                        st.json(job["raw_response"])
                    else:
                        st.write("无原始响应数据")
            # 添加操作按钮
            st.markdown("---")
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("🆕 生成新视频", type="primary"):
                    st.session_state.current_job = None
                    st.rerun()
            
            with col2:
                if st.button("📋 保存到历史"):
                    # 更新当前任务的完成状态
                    if job.get("video_bytes") or job.get("video_url"):
                        # 任务已经在历史记录中，只需要更新状态
                        for i, history_item in enumerate(st.session_state.generation_history):
                            if history_item.get("job_id") == job.get("job_id"):
                                # 更新历史记录中的任务状态
                                st.session_state.generation_history[i].update({
                                    "status": "completed",
                                    "video_bytes": job.get("video_bytes"),
                                    "video_url": job.get("video_url"),
                                    "completed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                })
                                break
                        else:
                            # 如果历史记录中没有找到，创建新的记录
                            history_item = {
                                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                "prompt": job.get("prompt", "未知"),
                                "duration": job.get("duration", 0),
                                "quality": job.get("quality", "未知"),
                                "aspect_ratio": job.get("aspect_ratio", "未知"),
                                "job_id": job.get("job_id", "未知"),
                                "status": "completed",
                                "video_bytes": job.get("video_bytes"),
                                "video_url": job.get("video_url")
                            }
                            st.session_state.generation_history.insert(0, history_item)
                        
                        # 只保留最近10个
                        if len(st.session_state.generation_history) > 10:
                            st.session_state.generation_history = st.session_state.generation_history[:10]
                        
                        st.success("✅ 已更新历史记录")
                    else:
                        st.warning("⚠️ 视频数据不完整，无法保存到历史")
                    
                    time.sleep(1)
                    st.rerun()
        
        elif job["status"] == "failed":
            st.error("❌ 生成失败")
            if "error" in job:
                st.error(f"错误信息: {job['error']}")
            
            # 重试按钮
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🔄 重新生成", type="primary"):
                    st.session_state.current_job = None
                    st.rerun()
            
            with col2:
                if st.button("🗑️ 清除任务"):
                    st.session_state.current_job = None
                    st.rerun()
        
        else:
            st.warning(f"⚠️ 未知状态: {job['status']}")
            # 显示详细错误信息
            if "error" in job:
                st.error(f"错误详情: {job['error']}")
            
            # 显示完整的任务信息用于调试
            with st.expander("🔍 调试信息"):
                st.json(job)

# --- 6. 生成历史 ---
if st.session_state.generation_history:
    st.markdown("---")
    st.subheader("📚 生成历史")
    
    # 添加清理按钮
    col_title, col_clear = st.columns([3, 1])
    with col_clear:
        if st.button("🗑️ 清空历史"):
            st.session_state.generation_history = []
            st.rerun()
    
    # 过滤和清理历史记录
    valid_history = []
    for task in st.session_state.generation_history:
        if isinstance(task, dict):
            valid_history.append(task)
    
    # 更新历史记录
    st.session_state.generation_history = valid_history
    
    # 显示最近的5个任务
    for i, task in enumerate(st.session_state.generation_history[:5]):
        # 安全获取任务标题
        task_title = ""
        if task.get('prompt'):
            task_title = f"任务 {i+1}: {task['prompt'][:50]}..."
        elif task.get('timestamp'):
            task_title = f"任务 {i+1}: {task['timestamp']}"
        else:
            task_title = f"任务 {i+1}"
            
        with st.expander(task_title):
            col_info, col_video = st.columns([1, 2])
            
            with col_info:
                # 安全显示任务信息
                st.write(f"**时间**: {task.get('timestamp', '未知')}")
                st.write(f"**时长**: {task.get('duration', '未知')}秒")
                st.write(f"**分辨率**: {task.get('quality', '未知')}")
                st.write(f"**宽高比**: {task.get('aspect_ratio', '未知')}")
                st.write(f"**任务ID**: {task.get('job_id', '未知')}")
                
                # 重新生成按钮
                if st.button(f"🔄 重新生成", key=f"regenerate_{i}"):
                    st.session_state.current_job = None
                    st.rerun()
            
            with col_video:
                # 显示历史视频（只使用字节数据）
                if task.get("video_bytes"):
                    try:
                        import base64
                        import tempfile
                        import os
                        
                        video_bytes = base64.b64decode(task["video_bytes"])
                        
                        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp_file:
                            tmp_file.write(video_bytes)
                            tmp_file_path = tmp_file.name
                        
                        st.video(tmp_file_path)
                        
                        # 下载按钮
                        st.download_button(
                            label="📥 下载视频",
                            data=video_bytes,
                            file_name=f"veo_history_{task['job_id']}.mp4",
                            mime="video/mp4",
                            key=f"download_{i}"
                        )
                        
                        try:
                            os.unlink(tmp_file_path)
                        except:
                            pass
                            
                    except Exception as e:
                        st.error(f"历史视频加载失败: {str(e)}")
                else:
                    st.info("视频数据不可用")

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
    
    **当前功能状态：**
    - ✅ 文本到视频：完全可用
    - ✅ 图片到视频：完全可用
    - ✅ 音频：自动包含，无需设置
    
    **分辨率和时长限制：**
    - 🔸 **720p**: 支持 4秒、6秒、8秒
    - 🔸 **1080p**: 仅支持 8秒时长
    - 🔸 **自动调整**: 不兼容组合会自动调整为720p
    - 🔸 **宽高比**: 16:9（横屏）、9:16（竖屏）
    - 🔸 **生成时间**: 通常3-10分钟
    
    **API状态说明：**
    - 🔄 processing: 正在生成中
    - ✅ completed: 生成完成
    - ❌ failed: 生成失败
    
    **遇到问题？**
    - 查看 [故障排除指南](docs/troubleshooting/veo_video_studio_issues.md)
    - 视频无法播放通常是API权限问题
    """)

# --- 8. 页脚信息 ---
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #666; font-size: 0.8em;'>
        Powered by Google Veo 3.1 (Gemini API) | 
        <a href='https://deepmind.google/technologies/veo/' target='_blank'>了解更多</a>
    </div>
    """,
    unsafe_allow_html=True
)
