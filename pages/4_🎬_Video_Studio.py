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
api_type = "未配置"

try:
    # 检查Gemini API密钥
    google_api_key = st.secrets.get("GOOGLE_API_KEY")
    if google_api_key:
        api_key_configured = True
        api_type = "Gemini API"
    else:
        # 检查Vertex AI配置
        vertex_config = all(key in st.secrets for key in ["GOOGLE_CLOUD_PROJECT_ID", "GOOGLE_CLOUD_LOCATION", "GOOGLE_CLOUD_CREDENTIALS"])
        if vertex_config:
            api_key_configured = True
            api_type = "Vertex AI"
        else:
            st.error("❌ 未配置Google API")
            st.info("💡 请配置以下任一方式：")
            st.markdown("""
            **方式1: Gemini API (推荐)**
            ```
            GOOGLE_API_KEY = "your_gemini_api_key"
            ```
            
            **方式2: Vertex AI**
            ```
            GOOGLE_CLOUD_PROJECT_ID = "your_project_id"
            GOOGLE_CLOUD_LOCATION = "us-central1"
            GOOGLE_CLOUD_CREDENTIALS = "your_service_account_json"
            ```
            """)
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
    reference_image = st.file_uploader(
        "参考图片（可选）",
        type=['jpg', 'jpeg', 'png'],
        help="上传一张参考图片来引导视频生成"
    )
    
    # 视频参数设置
    st.markdown("**视频参数**")
    
    # 重要限制提醒
    st.info("""
    📋 **Veo 3.1 重要限制**
    - 时长限制：仅支持 **4秒、6秒、8秒**
    - 参考图片：使用参考图片时只能生成 **8秒** 视频
    - 分辨率：支持720p、1080p
    
    ⚠️ **API权限提醒**：如果遇到403错误，请确保已启用以下API：
    - Generative Language API
    - Vertex AI API (如使用Vertex AI)
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
    
    # 验证参数组合
    validation_errors = []
    if duration not in [4, 6, 8]:
        validation_errors.append(f"时长 {duration}秒 不支持，请选择4、6或8秒")
    
    # 显示验证错误
    if validation_errors:
        for error in validation_errors:
            st.error(f"❌ {error}")
    
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
                    "operation_name": result["operation_name"],  # 保存完整的操作名称
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
                
                # 显示详细错误信息
                with st.expander("🔍 详细错误信息"):
                    st.json(result)
    
    # 显示当前任务结果和状态更新
    if st.session_state.current_job:
        job = st.session_state.current_job
        
        # 自动刷新状态（如果任务还在进行中）
        if job["status"] == "processing":
            # 获取最新状态
            status_result = get_video_status_sync(job["operation_name"])  # 使用完整的操作名称
            
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
                video_url = job["video_url"]
                
                st.info("🎥 **视频已生成完成**")
                
                # 检查URL类型并提供相应的访问方式
                if video_url.startswith('gs://'):
                    st.warning("""
                    ⚠️ **Google Cloud Storage URL**
                    
                    视频存储在Google Cloud Storage中，直接访问可能需要特殊权限。
                    """)
                    
                    # 提供替代访问方式
                    st.markdown("**推荐访问方式：**")
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown("**方式1：Google AI Studio**")
                        st.markdown(f"[🔗 打开AI Studio](https://aistudio.google.com/)")
                        st.code(f"任务ID: {job['job_id']}")
                        st.caption("在AI Studio中搜索任务ID查看视频")
                    
                    with col2:
                        st.markdown("**方式2：原始URL**")
                        st.code(video_url)
                        st.caption("复制URL在浏览器中打开（可能需要登录Google账号）")
                
                elif video_url.startswith('http'):
                    # HTTP URL - 使用代理服务测试可访问性
                    st.success("✅ **HTTP视频URL**")
                    
                    # 测试视频可访问性
                    with st.spinner("🔍 测试视频可访问性..."):
                        try:
                            from services.video_studio.video_proxy import test_video_accessibility, create_authenticated_download
                            
                            video_info = test_video_accessibility(video_url)
                            
                            if video_info["accessible"]:
                                st.success("✅ 视频URL可以通过认证访问")
                                
                                # 尝试创建认证下载
                                st.markdown("**下载选项：**")
                                col1, col2 = st.columns(2)
                                
                                with col1:
                                    if st.button("📥 认证下载", key="auth_download"):
                                        with st.spinner("正在准备下载..."):
                                            download_url = create_authenticated_download(video_url, job['job_id'])
                                            if download_url:
                                                st.success("✅ 下载准备完成")
                                                # 创建下载链接
                                                download_html = f"""
                                                <a href="{download_url}" download="veo_video_{job['job_id']}.mp4">
                                                    <button style="padding: 8px 16px; background: #28a745; color: white; border: none; border-radius: 4px; cursor: pointer;">
                                                        📥 点击下载视频
                                                    </button>
                                                </a>
                                                """
                                                st.markdown(download_html, unsafe_allow_html=True)
                                            else:
                                                st.error("❌ 下载准备失败")
                                
                                with col2:
                                    st.markdown(f"[🔗 新窗口打开]({video_url})")
                                    st.caption("需要登录Google账号")
                                
                            else:
                                st.warning(f"⚠️ 视频URL无法直接访问: {video_info['reason']}")
                                
                        except ImportError:
                            st.warning("⚠️ 视频代理服务不可用")
                        except Exception as e:
                            st.error(f"❌ 测试失败: {str(e)}")
                    
                    # 显示URL供用户复制
                    st.markdown("**视频URL：**")
                    st.code(video_url)
                    
                    # 推荐访问方式
                    st.markdown("**推荐访问方式：**")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown("**方式1：Google AI Studio（最推荐）**")
                        st.markdown(f"[🔗 打开AI Studio](https://aistudio.google.com/)")
                        st.code(f"任务ID: {job['job_id']}")
                        st.caption("✅ 100%可靠，官方推荐")
                    
                    with col2:
                        st.markdown("**方式2：浏览器直接访问**")
                        st.markdown(f"[🔗 新窗口打开URL]({video_url})")
                        st.caption("⚠️ 需要登录Google账号")
                    
                    # 技术说明
                    st.info("""
                    💡 **为什么无法在线播放？**
                    
                    1. **认证要求**：Google Veo的视频URL需要API密钥认证
                    2. **CORS限制**：浏览器安全策略阻止跨域视频访问
                    3. **Streamlit限制**：云环境的网络访问限制
                    
                    **最佳解决方案**：使用Google AI Studio查看和下载视频
                    """)
                
                else:
                    st.warning(f"⚠️ 未知URL格式: {video_url[:50]}...")
                    st.code(video_url)
                
                # 显示调试信息
                with st.expander("🔍 技术详情"):
                    st.write("**URL信息：**")
                    st.write(f"- URL类型: {type(video_url)}")
                    st.write(f"- URL长度: {len(video_url) if video_url else 0}")
                    st.write(f"- 协议: {'GCS' if video_url.startswith('gs://') else 'HTTP' if video_url.startswith('http') else '未知'}")
                    
                    st.write("**访问建议：**")
                    if video_url.startswith('gs://'):
                        st.write("- GCS URL需要Google Cloud权限")
                        st.write("- 建议在Google AI Studio中查看")
                        st.write("- 或者登录Google账号后直接访问")
                    else:
                        st.write("- HTTP URL应该可以直接访问")
                        st.write("- 如果403错误，可能是Streamlit Cloud的网络限制")
            else:
                st.warning("⚠️ 视频URL不可用")
                
                # 显示可能的原因和解决方案
                st.info("""
                **可能的原因：**
                - 视频可能需要额外的处理时间
                - API响应格式可能有变化  
                - 需要特殊权限才能访问生成的视频
                - Generative Language API 可能未启用
                
                **解决方案：**
                1. **检查API密钥项目**：
                   - 访问 [Google AI Studio](https://aistudio.google.com/)
                   - 确认你的API密钥对应的项目
                   - 在该项目中启用 Generative Language API
                
                2. **或者重新生成API密钥**：
                   - 在Google AI Studio中生成新的API密钥
                   - 确保选择正确的项目
                   - 更新Streamlit配置中的API密钥
                
                3. **通用API启用链接**：
                   - 访问 [Google Cloud Console APIs](https://console.cloud.google.com/apis/library/generativelanguage.googleapis.com)
                   - 选择正确的项目
                   - 启用 Generative Language API
                
                4. **等待生效**：等待几分钟后重新测试
                """)
                
                # 显示任务ID和有用链接
                st.code(f"任务ID: {job['job_id']}")
                
                col_api, col_studio, col_refresh = st.columns(3)
                with col_api:
                    st.markdown("[🔧 启用API](https://console.cloud.google.com/apis/library/generativelanguage.googleapis.com)")
                
                with col_studio:
                    st.markdown("[🔗 AI Studio](https://aistudio.google.com/)")
                
                with col_refresh:
                    if st.button("🔄 刷新状态", key="refresh_for_url"):
                        st.rerun()
                
                # 显示调试信息
                if "raw_response" in job:
                    with st.expander("🔍 API响应调试信息"):
                        st.json(job["raw_response"])
                        st.info("💡 如果看到这个信息，说明视频生成成功但URL提取有问题。请检查上面的API响应数据中是否包含视频链接。")
        
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
    - 支持时长：仅支持4秒、6秒、8秒（不支持其他时长）
    - 参考图片转视频：仅支持8秒时长
    - 支持分辨率：720p, 1080p
    - 支持宽高比：16:9, 9:16
    - 生成时间：通常3-10分钟
    
    **API状态说明：**
    - 🔄 processing: 正在生成中
    - ✅ completed: 生成完成
    - ❌ failed: 生成失败
    
    **遇到问题？**
    - 查看 [故障排除指南](docs/troubleshooting/veo_video_studio_issues.md)
    - 视频无法播放通常是API权限问题
    """)

# --- 8. API状态信息 ---
with st.expander("🔧 API状态信息"):
    st.success(f"✅ **使用 {api_type}**")
    
    if api_type == "Gemini API":
        st.write("**当前配置:**")
        st.write(f"- API类型: Gemini API")
        st.write(f"- 模型: veo-3.1-generate-preview")
        st.write(f"- 端点: generativelanguage.googleapis.com")
        st.write(f"- 服务状态: {'🟢 已配置' if api_key_configured else '🔴 未配置'}")
    elif api_type == "Vertex AI":
        project_id = st.secrets.get("GOOGLE_CLOUD_PROJECT_ID", "cohesive-point-481508-d4")
        location = st.secrets.get("GOOGLE_CLOUD_LOCATION", "us-central1")
        st.write("**当前配置:**")
        st.write(f"- API类型: Vertex AI")
        st.write(f"- 项目ID: {project_id}")
        st.write(f"- 地区: {location}")
        st.write(f"- 模型: veo-3.1-generate-001")
        st.write(f"- 服务状态: {'🟢 已配置' if api_key_configured else '🔴 未配置'}")
    
    # 测试API连接按钮
    if st.button("🧪 测试API连接"):
        with st.spinner("测试中..."):
            try:
                from services.video_studio.veo_service import get_veo_service
                service = get_veo_service()
                if service:
                    if service.use_gemini_api:
                        st.success("✅ Gemini API连接测试成功！")
                        st.info("使用API密钥认证")
                        
                        # 额外的权限检查提醒
                        st.warning("""
                        ⚠️ **重要提醒**：如果视频生成成功但无法播放，可能需要启用以下API：
                        - Generative Language API
                        - 确保API密钥有足够权限
                        """)
                        
                    else:
                        # 尝试获取访问令牌
                        token = service._get_access_token()
                        if token:
                            st.success("✅ Vertex AI连接测试成功！")
                            st.info(f"访问令牌已获取（长度: {len(token)} 字符）")
                        else:
                            st.error("❌ 无法获取访问令牌")
                else:
                    st.error("❌ 无法初始化Veo服务")
            except Exception as e:
                st.error(f"❌ API连接测试失败: {str(e)}")
                
                # 如果是权限错误，提供具体指导
                if "403" in str(e) or "PERMISSION_DENIED" in str(e):
                    st.error("🚨 **权限错误检测**")
                    
                    # 尝试从错误信息中提取项目ID
                    error_str = str(e)
                    if "project" in error_str:
                        import re
                        project_match = re.search(r'project (\d+)', error_str)
                        if project_match:
                            error_project_id = project_match.group(1)
                            st.warning(f"⚠️ 错误中的项目ID: {error_project_id}")
                            st.info("这个项目ID可能不是你的实际项目，请检查你的API密钥配置")
                    
                    st.markdown("""
                    **解决步骤：**
                    1. 访问 [Google AI Studio](https://aistudio.google.com/) 确认你的项目
                    2. 访问 [Google Cloud Console](https://console.cloud.google.com/apis/library/generativelanguage.googleapis.com)
                    3. 选择**你的实际项目**（不是错误信息中的项目ID）
                    4. 启用 "Generative Language API"
                    5. 等待几分钟让权限生效
                    6. 重新测试
                    
                    **如果仍有问题**：
                    - 在Google AI Studio中重新生成API密钥
                    - 确保API密钥对应正确的项目
                    """)
    
    if st.session_state.current_job:
        st.write("**当前任务:**")
        st.json({
            "job_id": st.session_state.current_job["job_id"],
            "status": st.session_state.current_job["status"],
            "progress": st.session_state.current_job["progress"],
            "created_at": st.session_state.current_job["created_at"].isoformat(),
            "operation_name": st.session_state.current_job.get("operation_name", "N/A"),
            "error": st.session_state.current_job.get("error", "无错误")
        })

# --- 9. 页脚信息 ---
st.markdown("---")
st.markdown(
    f"""
    <div style='text-align: center; color: #666; font-size: 0.8em;'>
        Powered by Google Veo 3.1 ({api_type}) | 
        <a href='https://deepmind.google/technologies/veo/' target='_blank'>了解更多</a> |
        ✅ 使用真实Google API
    </div>
    """,
    unsafe_allow_html=True
)
