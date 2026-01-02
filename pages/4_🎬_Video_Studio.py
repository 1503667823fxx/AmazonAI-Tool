import streamlit as st
import asyncio
import time
import json
import os
from typing import Optional, Dict, Any, List
from datetime import datetime

from auth import check_password  # 引入门禁系统
from services.video_studio.veo_service import generate_video_sync, get_video_status_sync
from services.video_studio.prompt_enhancer import enhance_video_prompt, get_prompt_enhancer

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
    prompt_mode = st.radio(
        "提示词模式",
        ["简单模式", "专业模式"],
        help="简单模式：直接输入描述；专业模式：结构化构建提示词"
    )
    
    # 参考图片上传（放在提示词输入之前，确保变量可用）
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
    
    # 初始化prompt变量
    prompt = ""
    
    if prompt_mode == "简单模式":
        prompt = st.text_area(
            "视频描述",
            placeholder="描述你想要生成的视频内容，例如：一只可爱的小猫在花园里玩耍，阳光明媚，画面温馨",
            height=100,
            help="详细描述视频内容，包括场景、动作、风格等",
            key="simple_prompt_input"
        )
        
        # AI润色功能
        st.markdown("**🤖 AI智能润色**")
        st.info("💡 AI会分析你的描述和参考图片，自动生成专业的中文提示词")
        
        # 润色按钮
        enhancer = get_prompt_enhancer()
        enhance_button = st.button(
            "✨ AI润色提示词",
            type="secondary",
            help="使用AI优化你的提示词，生成专业的中文描述",
            disabled=not prompt.strip() or not enhancer,
            use_container_width=True
        )
        
        if not enhancer:
            st.info("💡 AI润色服务未配置，需要Google API密钥")
        
        # 执行AI润色
        if enhance_button and prompt.strip():
            if enhancer:
                with st.spinner("🤖 AI正在分析和优化你的提示词..."):
                    # 获取参考图片（如果有的话）
                    reference_image_for_enhance = None
                    if reference_image is not None:
                        # 重置文件指针到开始位置
                        reference_image.seek(0)
                        reference_image_for_enhance = reference_image.read()
                        # 再次重置文件指针，以便后续使用
                        reference_image.seek(0)
                    
                    # 调用AI润色（让AI自动判断风格，不需要用户选择）
                    enhancement_result = enhance_video_prompt(
                        user_prompt=prompt,
                        reference_image=reference_image_for_enhance,
                        duration=8,  # 默认8秒，适合大多数场景
                        aspect_ratio="16:9",  # 默认16:9宽高比，最常用
                        style_preference="auto"  # 让AI自动判断最适合的风格
                    )
                    
                    if enhancement_result["success"]:
                        st.success("✅ AI润色完成！")
                        
                        # 显示AI润色结果
                        st.markdown("**🎨 AI优化的提示词**")
                        enhanced_prompt_display = enhancement_result["enhanced_prompt"]
                        
                        # 使用代码块显示，方便复制
                        st.code(enhanced_prompt_display, language=None)
                        
                        # 便捷复制按钮
                        col_copy1, col_copy2 = st.columns(2)
                        
                        with col_copy1:
                            # 使用streamlit的复制功能
                            st.text_input(
                                "点击选中全部文本，然后Ctrl+C复制：",
                                value=enhanced_prompt_display,
                                key="enhanced_prompt_copy",
                                help="选中文本后使用Ctrl+C复制到剪贴板"
                            )
                        
                        with col_copy2:
                            st.markdown("**💡 使用提示**")
                            st.info("选中上方文本框中的内容，使用 Ctrl+C 复制，然后粘贴到需要的地方")
                        
                        # 显示AI分析（可选展开）
                        with st.expander("🤖 查看AI分析详情"):
                            st.markdown(enhancement_result["analysis"])
                    else:
                        st.error(f"❌ AI润色失败: {enhancement_result['error']}")
                        st.info("💡 将继续使用原始提示词")
            else:
                st.error("❌ AI润色服务未配置")
        
        # 检查是否有需要复制的增强提示词（移除这个功能，因为现在使用直接复制）
        # 显示当前提示词状态
        if prompt and prompt.strip():
            st.markdown("**📋 当前提示词**")
            st.info(f"💬 {prompt}")
    else:
        st.markdown("**🎬 专业提示词构建器**")
        st.info("💡 通过结构化输入构建专业级视频提示词，每个选项都有中文说明帮助理解")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**📝 基础内容**")
            subject = st.text_input("主体", placeholder="例如：一只橙色小猫")
            action = st.text_input("动作", placeholder="例如：在草地上追逐蝴蝶")
            scene = st.text_input("场景", placeholder="例如：阳光明媚的花园")
            
        with col2:
            st.markdown("**🎥 镜头设置**")
            camera_angle = st.selectbox("镜头角度", [
                "None - 无特定角度",
                "Eye-Level Shot - 平视角度", 
                "Low-Angle Shot - 低角度仰拍", 
                "High-Angle Shot - 高角度俯拍", 
                "Close-Up - 特写镜头",
                "Medium Shot - 中景镜头", 
                "Wide Shot - 远景镜头", 
                "Over-the-Shoulder Shot - 过肩镜头"
            ], help="选择拍摄角度，影响视觉效果和情感表达")
            
            camera_movement = st.selectbox("镜头运动", [
                "None - 静止镜头",
                "Static Shot - 固定镜头", 
                "Pan (left) - 向左平移", 
                "Pan (right) - 向右平移", 
                "Zoom (In) - 推进放大",
                "Zoom (Out) - 拉远缩小", 
                "Dolly (In) - 推轨进入", 
                "Dolly (Out) - 推轨退出"
            ], help="镜头运动方式，增加动态效果")
            
            style = st.selectbox("视觉风格", [
                "None - 无特定风格",
                "Photorealistic - 照片写实风格", 
                "Cinematic - 电影风格", 
                "Vintage - 复古风格", 
                "Japanese anime style - 日式动漫风格",
                "Film noir style - 黑色电影风格", 
                "Golden hour glow - 黄金时刻光效"
            ], help="选择视觉风格，决定画面的整体感觉")
        
        # 音频设置
        st.markdown("**🔊 音频效果**")
        sound_effects = st.selectbox("音效", [
            "None - 无音效",
            "Soft house sounds - 轻柔室内声", 
            "City traffic - 城市交通声", 
            "Waves crashing - 海浪拍打声", 
            "Ticking clock - 时钟滴答声",
            "Water splashing - 水花飞溅声"
        ], help="选择背景音效，增强视频氛围")
        
        dialogue = st.text_input("对话", placeholder="可选：角色说的话，用引号包围")
        
        # 添加快速示例按钮
        st.markdown("**🚀 快速示例**")
        col_ex1, col_ex2, col_ex3 = st.columns(3)
        
        with col_ex1:
            if st.button("🐱 可爱动物"):
                subject = "一只橙色小猫"
                action = "在花园中追逐蝴蝶"
                scene = "阳光明媚的后院"
                st.success("✅ 已应用可爱动物示例")
        
        with col_ex2:
            if st.button("🎬 电影风格"):
                subject = "一位侦探"
                action = "在昏暗房间中查看证据"
                scene = "深夜的办公室"
                st.success("✅ 已应用电影风格示例")
        
        with col_ex3:
            if st.button("🌆 城市风光"):
                subject = "繁华都市"
                action = "霓虹灯闪烁，车流穿梭"
                scene = "夜晚的市中心"
                st.success("✅ 已应用城市风光示例")
        
        # 自动构建提示词
        if st.button("🤖 自动构建提示词"):
            keywords = []
            if subject: keywords.append(subject)
            if action: keywords.append(action)
            if scene: keywords.append(scene)
            
            # 提取英文部分用于API
            if camera_angle != "None - 无特定角度": 
                keywords.append(camera_angle.split(" - ")[0])
            if camera_movement != "None - 静止镜头": 
                keywords.append(camera_movement.split(" - ")[0])
            if style != "None - 无特定风格": 
                keywords.append(style.split(" - ")[0])
            if sound_effects != "None - 无音效": 
                keywords.append(sound_effects.split(" - ")[0])
            if dialogue: keywords.append(f'"{dialogue}"')
            
            if keywords:
                prompt = ", ".join(keywords)
                st.success("✅ 提示词已自动构建")
            else:
                prompt = ""
                st.warning("⚠️ 请至少填写主体、动作或场景")
        else:
            prompt = ""
        
        # 显示构建的提示词
        if prompt:
            st.text_area("构建的提示词", value=prompt, height=80, disabled=True)
        
        # 添加选项说明
        with st.expander("📖 选项说明指南"):
            st.markdown("""
            **🎥 镜头角度说明：**
            - **平视角度**: 与主体同高度，自然视角
            - **低角度仰拍**: 从下往上拍，显得主体高大威严
            - **高角度俯拍**: 从上往下拍，显得主体渺小或可爱
            - **特写镜头**: 聚焦细节，情感表达强烈
            - **中景镜头**: 显示主体和部分环境
            - **远景镜头**: 展现完整场景和环境
            - **过肩镜头**: 从一个角色肩膀后看向另一个角色
            
            **🎬 镜头运动说明：**
            - **固定镜头**: 静止不动，稳定画面
            - **平移**: 水平移动，跟随主体或展现环境
            - **推进放大**: 向主体靠近，增强紧张感
            - **拉远缩小**: 远离主体，展现更大场景
            - **推轨**: 摄像机整体移动，更平滑的运动效果
            
            **🎨 视觉风格说明：**
            - **照片写实**: 接近真实照片的效果
            - **电影风格**: 具有电影质感的画面
            - **复古风格**: 怀旧、老式的视觉效果
            - **日式动漫**: 动漫风格的画面
            - **黑色电影**: 高对比度，戏剧性光影
            - **黄金时刻**: 温暖的金色光线效果
            """)
    
    # 模型选择
    st.markdown("**模型选择**")
    model_type = st.selectbox(
        "生成模型",
        ["标准版 (高质量)", "快速版 (低延迟)"],
        help="标准版质量更高但生成时间较长，快速版生成更快但质量略低"
    )
    
    if model_type == "快速版 (低延迟)":
        st.info("🚀 快速版模型：生成时间约1-3分钟，适合快速预览")
    else:
        st.info("🎨 标准版模型：生成时间约3-10分钟，质量最佳")
    
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
        
        # Person Generation 设置
        person_generation = st.selectbox(
            "人物生成设置",
            ["allow_adult - 允许生成成人", "dont_allow - 不生成人物"],
            index=0,
            help="allow_adult: 允许生成成人；dont_allow: 不生成人物"
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
                # 重置文件指针到开始位置
                reference_image.seek(0)
                reference_image_bytes = reference_image.read()
                # 再次重置文件指针，以便后续使用
                reference_image.seek(0)
            
            # 调用真正的API
            result = generate_video_sync(
                prompt=prompt,
                duration=duration,
                aspect_ratio=aspect_ratio,
                quality=quality,
                reference_image=reference_image_bytes,
                negative_prompt=negative_prompt if negative_prompt.strip() else None,
                seed=seed,
                model_type="fast" if model_type == "快速版 (低延迟)" else "standard",
                person_generation=person_generation.split(" - ")[0]  # 提取英文部分
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
                    "generate_audio": False,  # 固定为False，因为音频是自动包含的
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
            
            # 智能刷新 - 根据任务时间调整刷新间隔
            task_age = time.time() - job.get("created_at", datetime.now()).timestamp() if isinstance(job.get("created_at"), datetime) else 0
            
            # 前3分钟每10秒检查一次，之后每30秒检查一次
            refresh_interval = 10 if task_age < 180 else 30
            
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
            
            # 如果仍在处理中，使用智能刷新
            if job["status"] == "processing":
                st.info(f"⏳ 视频生成中，页面将在{refresh_interval}秒后自动刷新...")
                
                # 创建一个占位符用于倒计时
                countdown_placeholder = st.empty()
                for i in range(refresh_interval, 0, -1):
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
            
            # 显示视频（优化版本 - 使用缓存和流式处理）
            if job.get("video_bytes"):
                try:
                    import base64
                    import tempfile
                    import os
                    import hashlib
                    
                    # 生成视频缓存键
                    video_cache_key = f"video_{job['job_id']}"
                    
                    # 检查是否已有临时文件缓存
                    if 'temp_video_files' not in st.session_state:
                        st.session_state.temp_video_files = {}
                    
                    # 如果已有缓存的临时文件且文件存在，直接使用
                    if (video_cache_key in st.session_state.temp_video_files and 
                        os.path.exists(st.session_state.temp_video_files[video_cache_key])):
                        
                        cached_path = st.session_state.temp_video_files[video_cache_key]
                        st.video(cached_path)
                        
                        # 提供下载选项
                        with open(cached_path, 'rb') as f:
                            video_data = f.read()
                        
                        st.download_button(
                            label="📥 下载视频",
                            data=video_data,
                            file_name=f"veo_video_{job['job_id']}.mp4",
                            mime="video/mp4"
                        )
                    else:
                        # 解码并创建新的临时文件
                        video_bytes = base64.b64decode(job["video_bytes"])
                        
                        # 创建持久化临时文件（不立即删除）
                        temp_dir = tempfile.gettempdir()
                        temp_filename = f"veo_video_{job['job_id']}.mp4"
                        tmp_file_path = os.path.join(temp_dir, temp_filename)
                        
                        # 写入文件
                        with open(tmp_file_path, 'wb') as f:
                            f.write(video_bytes)
                        
                        # 缓存文件路径
                        st.session_state.temp_video_files[video_cache_key] = tmp_file_path
                        
                        # 显示视频
                        st.video(tmp_file_path)
                        
                        # 提供下载选项
                        st.download_button(
                            label="📥 下载视频",
                            data=video_bytes,
                            file_name=f"veo_video_{job['job_id']}.mp4",
                            mime="video/mp4"
                        )
                        
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
            # 清理临时文件
            if 'temp_video_files' in st.session_state:
                for file_path in st.session_state.temp_video_files.values():
                    try:
                        if os.path.exists(file_path):
                            os.unlink(file_path)
                    except:
                        pass
                st.session_state.temp_video_files = {}
            
            # 清理视频缓存
            if 'video_cache' in st.session_state:
                st.session_state.video_cache = {}
            
            # 清空历史记录
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
                # 显示历史视频（优化版本 - 使用缓存）
                if task.get("video_bytes"):
                    try:
                        import base64
                        import tempfile
                        import os
                        
                        # 生成历史视频缓存键
                        history_cache_key = f"history_video_{task['job_id']}"
                        
                        # 检查缓存
                        if 'temp_video_files' not in st.session_state:
                            st.session_state.temp_video_files = {}
                        
                        # 如果已有缓存且文件存在，直接使用
                        if (history_cache_key in st.session_state.temp_video_files and 
                            os.path.exists(st.session_state.temp_video_files[history_cache_key])):
                            
                            cached_path = st.session_state.temp_video_files[history_cache_key]
                            st.video(cached_path)
                            
                            # 下载按钮
                            with open(cached_path, 'rb') as f:
                                video_data = f.read()
                            
                            st.download_button(
                                label="📥 下载视频",
                                data=video_data,
                                file_name=f"veo_history_{task['job_id']}.mp4",
                                mime="video/mp4",
                                key=f"download_{i}"
                            )
                        else:
                            # 创建新的缓存文件
                            video_bytes = base64.b64decode(task["video_bytes"])
                            
                            temp_dir = tempfile.gettempdir()
                            temp_filename = f"veo_history_{task['job_id']}.mp4"
                            tmp_file_path = os.path.join(temp_dir, temp_filename)
                            
                            with open(tmp_file_path, 'wb') as f:
                                f.write(video_bytes)
                            
                            # 缓存文件路径
                            st.session_state.temp_video_files[history_cache_key] = tmp_file_path
                            
                            st.video(tmp_file_path)
                            
                            # 下载按钮
                            st.download_button(
                                label="📥 下载视频",
                                data=video_bytes,
                                file_name=f"veo_history_{task['job_id']}.mp4",
                                mime="video/mp4",
                                key=f"download_{i}"
                            )
                            
                    except Exception as e:
                        st.error(f"历史视频加载失败: {str(e)}")
                else:
                    st.info("视频数据不可用")

# --- 7. 使用提示 ---
st.markdown("---")
with st.expander("💡 使用提示"):
    st.markdown("""
    **🤖 AI智能润色功能：**
    
    **✨ 简化的润色流程：**
    - **智能分析**: AI自动分析你的提示词和参考图片
    - **自动风格**: AI根据内容自动选择最适合的风格，无需手动选择
    - **中文优化**: 生成专业的中文提示词，便于理解和使用
    - **便捷复制**: 优化后的提示词显示在可选择的文本框中，方便复制
    - **完全可选**: 不影响原有的视频生成流程
    
    **🎯 使用流程：**
    1. 在"视频描述"中输入你的基本想法
    2. 如果有参考图片，先上传图片
    3. 点击"AI润色提示词"按钮
    4. 查看AI生成的中文优化版本
    5. 选中文本框中的内容，使用Ctrl+C复制
    6. 粘贴到需要使用的地方（如其他应用或文档）
    7. 继续设置其他参数并生成视频
    
    **🎬 专业提示词构建器使用说明：**
    
    **📝 基础内容：**
    - **主体**: 视频的核心对象（人物、动物、物品等）
    - **动作**: 描述主体的具体行为和动作
    - **场景**: 环境背景和时间设定
    
    **🎥 镜头技巧：**
    - **角度**: 影响视觉冲击力和情感表达
    - **运动**: 增加动态效果和观看体验
    - **风格**: 决定整体视觉感受和氛围
    
    **🔊 音频增强：**
    - 选择合适的背景音效增强沉浸感
    - 可添加角色对话增加故事性
    
    **🚀 快速开始：**
    1. 选择"专业模式"
    2. 点击快速示例按钮获得灵感
    3. 根据需要调整各项参数
    4. 点击"自动构建提示词"
    5. 开始生成视频
    
    **性能优化说明：**
    - ✅ 视频缓存：已启用智能缓存，重复播放更快
    - ✅ 流式下载：大文件分块下载，减少内存占用
    - ✅ 智能刷新：根据任务时间调整检查频率
    - ✅ 临时文件复用：避免重复创建临时文件
    - ✅ 快速模式：支持Veo 3 Fast模型，生成更快
    - ✅ AI增强：自动优化提示词，提升视频质量
    - ✅ 专业构建器：结构化提示词，提升成功率
    
    **最佳实践提示词示例：**
    
    **🎬 电影风格：**
    - "一位侦探在昏暗的审讯室中审问嫌疑人，低角度拍摄，电影风格，紧张的背景音乐"
    - "城市夜景中霓虹灯闪烁，镜头缓慢推进，赛博朋克风格，雨声和车流声"
    
    **🌟 生活场景：**
    - "一只橙色小猫在阳光花园中追逐蝴蝶，特写镜头，温馨画面，鸟鸣声"
    - "咖啡师在咖啡店制作拿铁艺术，俯视角度，温暖灯光，轻柔爵士乐"
    
    **🎨 艺术风格：**
    - "梵高风格的向日葵田在微风中摇摆，画面色彩饱和，印象派风格"
    - "日式动漫风格的樱花飘落，少女在树下阅读，柔和粉色调"
    
    **🚀 快速模式提示：**
    - 适合快速预览和测试想法
    - 生成时间约1-3分钟
    - 质量略低但足够预览使用
    
    **当前功能状态：**
    - ✅ 文本到视频：完全可用
    - ✅ 图片到视频：完全可用
    - ✅ 音频：自动包含，无需设置
    - ✅ 双模型：标准版和快速版
    - ✅ AI增强：自动优化提示词
    - ✅ 专业模式：结构化提示词构建
    
    **分辨率和时长限制：**
    - 🔸 **720p**: 支持 4秒、6秒、8秒
    - 🔸 **1080p**: 仅支持 8秒时长
    - 🔸 **自动调整**: 不兼容组合会自动调整为720p
    - 🔸 **宽高比**: 16:9（横屏）、9:16（竖屏）
    - 🔸 **生成时间**: 标准版3-10分钟，快速版1-3分钟
    
    **API状态说明：**
    - 🔄 processing: 正在生成中
    - ✅ completed: 生成完成
    - ❌ failed: 生成失败
    
    **性能提示：**
    - 🚀 首次播放可能较慢，后续播放会使用缓存
    - 💾 历史视频会保存在临时缓存中，重启应用后清除
    - 🔄 状态检查频率会根据任务时间智能调整
    - 📱 建议在稳定网络环境下使用
    - ⚡ 使用快速模式可显著减少等待时间
    - 🎯 专业模式可提升生成成功率和质量
    
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
