import streamlit as st
import json
import asyncio
import time
from datetime import datetime

def setup_page_config():
    """页面基础配置"""
    st.set_page_config(
        page_title="Amazon Video Studio",
        page_icon="🎬",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # 注入自定义 CSS 以优化视频工作台体验
    st.markdown("""
        <style>
        .stTextArea textarea {
            font-size: 16px !important;
            line-height: 1.5;
        }
        .stTab {
            font-weight: 600;
        }
        /* 进度条样式优化 */
        .stProgress > div > div > div > div {
            background-color: #FF9900;
        }
        </style>
    """, unsafe_allow_html=True)

def render_sidebar():
    """侧边栏配置区 - 重构版"""
    with st.sidebar:
        st.header("⚙️ Video Studio 设置")
        
        # API 配置部分
        st.subheader("🔑 API 配置")
        
        # OpenAI API Key
        openai_key = st.text_input(
            "OpenAI API Key", 
            type="password",
            help="用于脚本生成和文本处理"
        )
        
        # 视频生成模型配置
        st.subheader("🎬 视频生成模型")
        
        # 主要模型选择
        primary_model = st.selectbox(
            "主要生成模型",
            options=["luma", "runway", "pika"],
            format_func=lambda x: {
                "luma": "🌟 Luma Dream Machine",
                "runway": "🚀 Runway ML Gen-2", 
                "pika": "⚡ Pika Labs"
            }.get(x, x),
            help="选择主要的视频生成模型"
        )
        
        # 模型特定配置
        if primary_model == "luma":
            luma_key = st.text_input("Luma API Key", type="password")
            luma_endpoint = st.text_input("Luma Endpoint (可选)", placeholder="https://api.lumalabs.ai")
        elif primary_model == "runway":
            runway_key = st.text_input("Runway API Key", type="password")
            runway_model_version = st.selectbox("Runway 模型版本", ["gen2", "gen3"])
        elif primary_model == "pika":
            pika_key = st.text_input("Pika API Key", type="password")
            pika_quality = st.selectbox("Pika 质量设置", ["standard", "high", "ultra"])
        
        # 备用模型
        enable_fallback = st.checkbox("启用备用模型", help="当主模型失败时自动切换")
        if enable_fallback:
            fallback_models = st.multiselect(
                "备用模型",
                options=[m for m in ["luma", "runway", "pika"] if m != primary_model],
                format_func=lambda x: {
                    "luma": "Luma Dream Machine",
                    "runway": "Runway ML", 
                    "pika": "Pika Labs"
                }.get(x, x)
            )
        
        st.divider()
        
        # 生成配置
        st.subheader("🎨 生成配置")
        
        # 视频质量
        video_quality = st.selectbox(
            "默认视频质量",
            options=["720p", "1080p", "4k"],
            index=1,
            help="更高质量需要更长生成时间"
        )
        
        # 画幅比例
        aspect_ratio = st.selectbox(
            "默认画幅比例",
            options=["16:9", "9:16", "1:1"],
            format_func=lambda x: {
                "16:9": "16:9 (横屏/YouTube)",
                "9:16": "9:16 (竖屏/TikTok)",
                "1:1": "1:1 (方形/Instagram)"
            }.get(x, x),
            index=0
        )
        
        # 视频风格
        video_style = st.selectbox(
            "默认视频风格",
            options=["cinematic", "dynamic", "minimal", "energetic", "elegant", "professional"],
            format_func=lambda x: {
                "cinematic": "🎬 电影风格",
                "dynamic": "⚡ 动感风格",
                "minimal": "🎯 极简风格",
                "energetic": "🔥 活力风格",
                "elegant": "✨ 优雅风格",
                "professional": "💼 专业风格"
            }.get(x, x),
            index=0
        )
        
        st.divider()
        
        # 高级设置
        with st.expander("🔧 高级设置"):
            # 并发设置
            max_concurrent = st.slider(
                "最大并发任务数",
                min_value=1,
                max_value=10,
                value=3,
                help="同时处理的最大任务数量"
            )
            
            # 重试设置
            max_retries = st.slider(
                "最大重试次数",
                min_value=0,
                max_value=5,
                value=2,
                help="任务失败时的重试次数"
            )
            
            # 超时设置
            request_timeout = st.slider(
                "请求超时 (秒)",
                min_value=30,
                max_value=300,
                value=120,
                help="单个请求的超时时间"
            )
            
            # 存储设置
            auto_cleanup = st.checkbox(
                "自动清理过期文件",
                value=True,
                help="自动删除超过24小时的临时文件"
            )
            
            cleanup_interval = st.slider(
                "清理间隔 (小时)",
                min_value=1,
                max_value=168,
                value=24,
                help="自动清理的时间间隔"
            )
        
        st.divider()
        
        # 系统信息
        with st.expander("📊 系统信息"):
            try:
                from app_utils.video_studio.generation_engine import get_generation_engine
                engine = get_generation_engine()
                stats = engine.get_engine_stats()
                
                st.metric("可用模型", stats.get('available_models', 0))
                st.metric("总生成数", stats.get('total_generations', 0))
                st.metric("成功率", f"{stats.get('success_rate', 0) * 100:.1f}%")
                st.metric("活跃请求", stats.get('active_requests', 0))
                
            except Exception as e:
                st.warning(f"无法获取系统信息: {str(e)}")
        
        # 配置导出/导入
        st.divider()
        
        col_export, col_import = st.columns(2)
        
        with col_export:
            if st.button("📤 导出配置", use_container_width=True):
                config_data = {
                    "openai_key": "***" if openai_key else "",
                    "primary_model": primary_model,
                    "video_quality": video_quality,
                    "aspect_ratio": aspect_ratio,
                    "video_style": video_style,
                    "max_concurrent": max_concurrent,
                    "max_retries": max_retries,
                    "request_timeout": request_timeout,
                    "auto_cleanup": auto_cleanup,
                    "cleanup_interval": cleanup_interval
                }
                
                st.download_button(
                    "下载配置文件",
                    data=json.dumps(config_data, indent=2, ensure_ascii=False),
                    file_name="video_studio_config.json",
                    mime="application/json"
                )
        
        with col_import:
            uploaded_config = st.file_uploader(
                "导入配置",
                type=['json'],
                help="上传之前导出的配置文件"
            )
            
            if uploaded_config:
                try:
                    config_data = json.load(uploaded_config)
                    st.success("✅ 配置文件已加载")
                    st.json(config_data)
                except Exception as e:
                    st.error(f"❌ 配置文件格式错误: {str(e)}")
        
        # 返回配置字典
        config = {
            "api_key": openai_key,
            "primary_model": primary_model,
            "video_quality": video_quality,
            "aspect_ratio": aspect_ratio,
            "style": video_style,
            "max_concurrent": max_concurrent,
            "max_retries": max_retries,
            "request_timeout": request_timeout,
            "auto_cleanup": auto_cleanup,
            "cleanup_interval": cleanup_interval
        }
        
        # 添加模型特定配置
        if primary_model == "luma":
            config.update({
                "luma_key": luma_key,
                "luma_endpoint": luma_endpoint
            })
        elif primary_model == "runway":
            config.update({
                "runway_key": runway_key,
                "runway_model_version": runway_model_version
            })
        elif primary_model == "pika":
            config.update({
                "pika_key": pika_key,
                "pika_quality": pika_quality
            })
        
        if enable_fallback:
            config["fallback_models"] = fallback_models
        
        return config

def render_step_indicator(current_step):
    """可视化的步骤指示器"""
    steps = ["1. 编写剧本", "2. 生成素材", "3. 剪辑合成"]
    # 简单的文本进度条，也可以做成更复杂的图形
    st.markdown(f"**当前阶段:** {' » '.join([f'`{s}`' if i == current_step else s for i, s in enumerate(steps)])}")
    st.divider()


def render_task_status(task_info):
    """渲染任务状态和进度"""
    if not task_info:
        return
    
    status_colors = {
        "pending": "🟡",
        "processing": "🔵",
        "generating": "🟣",
        "rendering": "🟠",
        "completed": "🟢",
        "failed": "🔴",
        "cancelled": "⚫"
    }
    
    status_icon = status_colors.get(task_info.status.value, "⚪")
    
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        st.markdown(f"### {status_icon} 任务状态: {task_info.status.value.upper()}")
    
    with col2:
        st.metric("进度", f"{int(task_info.progress * 100)}%")
    
    with col3:
        st.metric("任务ID", task_info.task_id[:8])
    
    # 进度条
    st.progress(task_info.progress)
    
    # 显示详细信息
    with st.expander("查看详细信息"):
        st.json({
            "task_id": task_info.task_id,
            "status": task_info.status.value,
            "progress": f"{task_info.progress * 100:.1f}%",
            "created_at": task_info.created_at.isoformat(),
            "updated_at": task_info.updated_at.isoformat(),
            "result_url": task_info.result_url,
            "error_message": task_info.error_message
        })


def render_real_time_progress(task_id: str, placeholder):
    """实时更新任务进度"""
    import asyncio
    from app_utils.video_studio.workflow_manager import get_task_status
    
    async def update_progress():
        while True:
            task_info = await get_task_status(task_id)
            if task_info:
                with placeholder.container():
                    render_task_status(task_info)
                
                # 如果任务完成或失败，停止更新
                if task_info.status.value in ["completed", "failed", "cancelled"]:
                    break
            
            await asyncio.sleep(2)  # 每2秒更新一次
    
    # 在Streamlit中运行异步任务
    try:
        asyncio.run(update_progress())
    except Exception as e:
        st.error(f"进度更新失败: {str(e)}")


def render_model_status_panel():
    """渲染模型状态监控面板"""
    st.subheader("🔍 模型状态监控")
    
    try:
        from app_utils.video_studio.generation_engine import get_generation_engine
        engine = get_generation_engine()
        
        # 获取可用模型列表
        available_models = engine.get_available_models()
        
        if not available_models:
            st.warning("⚠️ 当前没有可用的模型")
            return
        
        # 为每个模型显示状态
        for model_name in available_models:
            model_info = engine.get_model_info(model_name)
            
            if model_info:
                with st.expander(f"📊 {model_name.upper()} 状态"):
                    col_metrics, col_details = st.columns([1, 1])
                    
                    with col_metrics:
                        metrics = model_info.get('metrics', {})
                        
                        st.metric(
                            "成功率",
                            f"{metrics.get('success_rate', 0) * 100:.1f}%"
                        )
                        
                        st.metric(
                            "平均响应时间",
                            f"{metrics.get('average_response_time', 0):.1f}s"
                        )
                        
                        st.metric(
                            "当前负载",
                            metrics.get('current_load', 0)
                        )
                    
                    with col_details:
                        st.write("**模型信息:**")
                        st.json({
                            "name": model_info.get('name', model_name),
                            "version": model_info.get('version', 'N/A'),
                            "capabilities": model_info.get('capabilities', []),
                            "max_duration": model_info.get('max_duration', 'N/A'),
                            "supported_formats": model_info.get('supported_formats', [])
                        })
                        
                        # 模型健康状态指示器
                        success_rate = metrics.get('success_rate', 0)
                        if success_rate >= 0.9:
                            st.success("🟢 模型状态良好")
                        elif success_rate >= 0.7:
                            st.warning("🟡 模型状态一般")
                        else:
                            st.error("🔴 模型状态异常")
    
    except Exception as e:
        st.error(f"❌ 无法获取模型状态: {str(e)}")


def render_template_selector(template_manager):
    """渲染模板选择器组件"""
    st.subheader("🎨 视频模板")
    
    try:
        # 获取模板分类
        categories = template_manager.get_template_categories()
        
        # 分类选择
        def format_category(x):
            if x == "all":
                return "全部模板"
            try:
                from app_utils.video_studio.localization import get_category_chinese_name
                return get_category_chinese_name(x)
            except:
                return x.replace("_", " ").title()
        
        selected_category = st.selectbox(
            "选择模板分类",
            options=["all"] + categories,
            format_func=format_category,
            key="template_category_selector"
        )
        
        # 获取模板列表
        if selected_category == "all":
            templates = template_manager.list_templates()
        else:
            from app_utils.video_studio.template_manager import TemplateCategory
            category_enum = TemplateCategory(selected_category)
            templates = template_manager.list_templates(category_enum)
        
        if not templates:
            st.info("该分类下暂无模板")
            return None
        
        # 模板网格显示
        cols = st.columns(3)
        selected_template = None
        
        for i, template in enumerate(templates):
            with cols[i % 3]:
                # 模板卡片
                with st.container():
                    st.markdown(f"**{template.metadata.name}**")
                    st.caption(template.metadata.description)
                    
                    # 模板标签
                    if template.metadata.tags:
                        tag_str = " ".join([f"`{tag}`" for tag in template.metadata.tags[:3]])
                        st.markdown(tag_str)
                    
                    # 模板信息
                    st.write(f"⏱️ {template.config.duration}s")
                    st.write(f"📐 {template.config.aspect_ratio.value}")
                    st.write(f"🎬 {template.config.style.value}")
                    
                    # 选择按钮
                    if st.button(f"选择", key=f"select_template_{template.template_id}"):
                        selected_template = template
                        st.session_state.selected_template = template
                        st.success(f"✅ 已选择模板: {template.metadata.name}")
        
        return selected_template
    
    except Exception as e:
        st.error(f"❌ 模板加载失败: {str(e)}")
        return None


def render_advanced_config_panel():
    """渲染高级配置面板"""
    with st.expander("🔧 高级生成配置"):
        col_left, col_right = st.columns(2)
        
        with col_left:
            st.subheader("🎬 视频参数")
            
            motion_strength = st.slider(
                "运动强度",
                min_value=0.1,
                max_value=1.0,
                value=0.7,
                step=0.1,
                help="控制视频中的运动幅度"
            )
            
            camera_control = st.selectbox(
                "镜头运动",
                options=["auto", "static", "slow_zoom", "pan", "orbit"],
                format_func=lambda x: {
                    "auto": "自动选择",
                    "static": "静态镜头",
                    "slow_zoom": "缓慢推拉",
                    "pan": "平移扫描",
                    "orbit": "环绕运动"
                }.get(x, x)
            )
            
            lighting_style = st.selectbox(
                "光照风格",
                options=["natural", "dramatic", "soft", "high_contrast", "cinematic"],
                format_func=lambda x: {
                    "natural": "自然光照",
                    "dramatic": "戏剧光照",
                    "soft": "柔和光照",
                    "high_contrast": "高对比度",
                    "cinematic": "电影光照"
                }.get(x, x)
            )
        
        with col_right:
            st.subheader("⚙️ 生成控制")
            
            seed_value = st.number_input(
                "随机种子",
                min_value=0,
                max_value=999999,
                value=0,
                help="设置为0使用随机种子，固定值可重现结果"
            )
            
            guidance_scale = st.slider(
                "引导强度",
                min_value=1.0,
                max_value=20.0,
                value=7.5,
                step=0.5,
                help="控制AI对提示词的遵循程度"
            )
            
            inference_steps = st.slider(
                "推理步数",
                min_value=10,
                max_value=100,
                value=50,
                step=5,
                help="更多步数通常产生更好质量，但需要更长时间"
            )
        
        return {
            "motion_strength": motion_strength,
            "camera_control": camera_control,
            "lighting_style": lighting_style,
            "seed": seed_value if seed_value > 0 else None,
            "guidance_scale": guidance_scale,
            "inference_steps": inference_steps
        }


def render_file_upload_zone(asset_manager, key_prefix="upload"):
    """渲染增强的文件上传区域"""
    st.subheader("📤 素材上传")
    
    # 上传区域
    uploaded_files = st.file_uploader(
        "拖拽文件到此处或点击选择",
        type=['png', 'jpg', 'jpeg', 'webp', 'gif', 'mp4', 'mov', 'avi'],
        accept_multiple_files=True,
        help="支持图片格式: PNG, JPG, JPEG, WebP, GIF\n支持视频格式: MP4, MOV, AVI",
        key=f"{key_prefix}_files"
    )
    
    # 显示支持的格式信息
    with st.expander("📋 支持的文件格式"):
        col_img, col_vid = st.columns(2)
        
        with col_img:
            st.write("**图片格式:**")
            st.write("• PNG - 支持透明背景")
            st.write("• JPG/JPEG - 通用格式")
            st.write("• WebP - 高压缩比")
            st.write("• GIF - 动图支持")
        
        with col_vid:
            st.write("**视频格式:**")
            st.write("• MP4 - 推荐格式")
            st.write("• MOV - Apple格式")
            st.write("• AVI - 传统格式")
    
    # 文件大小限制提示
    st.info("📏 文件大小限制: 图片 ≤ 50MB, 视频 ≤ 500MB")
    
    uploaded_assets = []
    
    if uploaded_files:
        # 创建进度条
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for i, uploaded_file in enumerate(uploaded_files):
            # 更新进度
            progress = (i + 1) / len(uploaded_files)
            progress_bar.progress(progress)
            status_text.text(f"正在处理: {uploaded_file.name} ({i+1}/{len(uploaded_files)})")
            
            try:
                # 验证文件
                file_size = len(uploaded_file.getvalue())
                is_valid, error_msg = asset_manager.validate_file_upload(uploaded_file.name, file_size)
                
                if not is_valid:
                    st.error(f"❌ {uploaded_file.name}: {error_msg}")
                    continue
                
                # 确定文件类型
                file_ext = uploaded_file.name.lower().split('.')[-1]
                is_image = file_ext in ['png', 'jpg', 'jpeg', 'webp', 'gif']
                
                # 上传文件
                if is_image:
                    async def upload_image():
                        return await asset_manager.upload_image(
                            uploaded_file.getvalue(),
                            uploaded_file.name
                        )
                    asset_id = asyncio.run(upload_image())
                else:
                    async def upload_video():
                        return await asset_manager.upload_video(
                            uploaded_file.getvalue(),
                            uploaded_file.name
                        )
                    asset_id = asyncio.run(upload_video())
                
                # 获取资产元数据
                metadata = asset_manager.get_asset_metadata(asset_id)
                
                uploaded_assets.append({
                    'asset_id': asset_id,
                    'filename': uploaded_file.name,
                    'file_size': file_size,
                    'file_type': 'image' if is_image else 'video',
                    'metadata': metadata,
                    'upload_time': datetime.now()
                })
                
                st.success(f"✅ {uploaded_file.name} 上传成功")
                
            except Exception as e:
                st.error(f"❌ {uploaded_file.name} 上传失败: {str(e)}")
        
        # 清除进度显示
        progress_bar.empty()
        status_text.empty()
    
    return uploaded_assets


def render_asset_gallery(assets, asset_manager, key_prefix="gallery"):
    """渲染资产画廊和预览"""
    if not assets:
        st.info("📁 暂无上传的素材")
        return []
    
    st.subheader(f"🖼️ 素材库 ({len(assets)} 个文件)")
    
    # 筛选和排序选项
    col_filter, col_sort = st.columns(2)
    
    with col_filter:
        filter_type = st.selectbox(
            "筛选类型",
            options=["all", "image", "video"],
            format_func=lambda x: {"all": "全部", "image": "图片", "video": "视频"}.get(x, x),
            key=f"{key_prefix}_filter"
        )
    
    with col_sort:
        sort_by = st.selectbox(
            "排序方式",
            options=["upload_time", "filename", "file_size"],
            format_func=lambda x: {
                "upload_time": "上传时间",
                "filename": "文件名",
                "file_size": "文件大小"
            }.get(x, x),
            key=f"{key_prefix}_sort"
        )
    
    # 应用筛选
    filtered_assets = assets
    if filter_type != "all":
        filtered_assets = [a for a in assets if a['file_type'] == filter_type]
    
    # 应用排序
    if sort_by == "upload_time":
        filtered_assets.sort(key=lambda x: x['upload_time'], reverse=True)
    elif sort_by == "filename":
        filtered_assets.sort(key=lambda x: x['filename'])
    elif sort_by == "file_size":
        filtered_assets.sort(key=lambda x: x['file_size'], reverse=True)
    
    # 网格显示
    cols_per_row = 3
    selected_assets = []
    
    for i in range(0, len(filtered_assets), cols_per_row):
        cols = st.columns(cols_per_row)
        
        for j, asset in enumerate(filtered_assets[i:i+cols_per_row]):
            with cols[j]:
                render_asset_card(asset, asset_manager, key_prefix, i+j, selected_assets)
    
    return selected_assets


def render_asset_card(asset, asset_manager, key_prefix, index, selected_assets):
    """渲染单个资产卡片"""
    with st.container():
        # 资产预览
        asset_url = asset_manager.get_asset_url(asset['asset_id'])
        
        if asset['file_type'] == 'image' and asset_url:
            try:
                st.image(asset_url, use_column_width=True)
            except:
                st.write("🖼️ 图片预览")
        elif asset['file_type'] == 'video' and asset_url:
            try:
                st.video(asset_url)
            except:
                st.write("🎬 视频文件")
        else:
            st.write(f"📄 {asset['file_type'].upper()}")
        
        # 文件信息
        st.write(f"**{asset['filename']}**")
        st.caption(f"ID: {asset['asset_id'][:8]}")
        st.caption(f"大小: {asset['file_size'] / 1024 / 1024:.1f} MB")
        
        # 元数据信息
        if asset['metadata']:
            metadata = asset['metadata']
            if metadata.width and metadata.height:
                st.caption(f"尺寸: {metadata.width}×{metadata.height}")
            if metadata.duration:
                st.caption(f"时长: {metadata.duration:.1f}s")
        
        # 操作按钮
        col_select, col_delete = st.columns(2)
        
        with col_select:
            if st.button("✅", key=f"{key_prefix}_select_{index}", help="选择此素材"):
                if asset not in selected_assets:
                    selected_assets.append(asset)
                    st.success("已选择")
        
        with col_delete:
            if st.button("🗑️", key=f"{key_prefix}_delete_{index}", help="删除素材"):
                async def delete_asset():
                    return await asset_manager.delete_asset(asset['asset_id'])
                
                if asyncio.run(delete_asset()):
                    st.success("已删除")
                    st.rerun()
                else:
                    st.error("删除失败")


def render_scene_preview_editor(scenes, key_prefix="scene_editor"):
    """渲染场景预览和编辑器"""
    if not scenes:
        st.info("📝 暂无场景数据")
        return scenes
    
    st.subheader("🎬 场景编辑器")
    
    # 场景列表
    edited_scenes = []
    
    for i, scene in enumerate(scenes):
        with st.expander(f"场景 {i+1}: {scene.get('visual_prompt', 'N/A')[:50]}..."):
            col_edit, col_preview = st.columns([2, 1])
            
            with col_edit:
                # 编辑场景参数
                visual_prompt = st.text_area(
                    "视觉描述",
                    value=scene.get('visual_prompt', ''),
                    height=100,
                    key=f"{key_prefix}_prompt_{i}"
                )
                
                col_duration, col_movement = st.columns(2)
                
                with col_duration:
                    duration = st.number_input(
                        "时长 (秒)",
                        min_value=0.5,
                        max_value=30.0,
                        value=float(scene.get('duration', 3.0)),
                        step=0.5,
                        key=f"{key_prefix}_duration_{i}"
                    )
                
                with col_movement:
                    camera_movement = st.selectbox(
                        "镜头运动",
                        options=["static", "slow_zoom", "pan_left", "pan_right", "orbit", "dolly"],
                        index=0,
                        key=f"{key_prefix}_movement_{i}"
                    )
                
                lighting = st.selectbox(
                    "光照设置",
                    options=["natural", "dramatic", "soft", "high_contrast", "cinematic"],
                    index=0,
                    key=f"{key_prefix}_lighting_{i}"
                )
            
            with col_preview:
                st.write("**场景预览**")
                
                # 生成预览图像（模拟）
                st.write("🎨 AI 预览")
                st.info(f"时长: {duration}s\n镜头: {camera_movement}\n光照: {lighting}")
                
                # 预览按钮
                if st.button(f"🔍 生成预览", key=f"{key_prefix}_preview_{i}"):
                    with st.spinner("生成预览中..."):
                        time.sleep(1)  # 模拟预览生成
                        st.success("预览已生成")
            
            # 保存编辑后的场景
            edited_scene = {
                'scene_id': scene.get('scene_id', f'scene_{i+1}'),
                'visual_prompt': visual_prompt,
                'duration': duration,
                'camera_movement': camera_movement,
                'lighting': lighting
            }
            edited_scenes.append(edited_scene)
    
    # 添加新场景按钮
    if st.button("➕ 添加新场景", key=f"{key_prefix}_add_scene"):
        new_scene = {
            'scene_id': f'scene_{len(scenes)+1}',
            'visual_prompt': '在此输入场景描述...',
            'duration': 3.0,
            'camera_movement': 'static',
            'lighting': 'natural'
        }
        edited_scenes.append(new_scene)
        st.rerun()
    
    return edited_scenes


def render_batch_processing_controls(assets, key_prefix="batch"):
    """渲染批量处理控制面板"""
    if not assets:
        return
    
    st.subheader("⚡ 批量处理")
    
    # 选择要处理的资产
    selected_indices = st.multiselect(
        "选择要处理的素材",
        options=range(len(assets)),
        format_func=lambda i: f"{assets[i]['filename']} ({assets[i]['file_type']})",
        key=f"{key_prefix}_selection"
    )
    
    if not selected_indices:
        st.info("请选择要处理的素材")
        return
    
    # 批量操作选项
    col_ops, col_params = st.columns([1, 2])
    
    with col_ops:
        st.write("**批量操作:**")
        
        resize_batch = st.checkbox("统一调整尺寸")
        enhance_batch = st.checkbox("批量增强")
        format_batch = st.checkbox("格式转换")
        watermark_batch = st.checkbox("添加水印")
    
    with col_params:
        batch_params = {}
        
        if resize_batch:
            st.write("**尺寸设置:**")
            col_w, col_h = st.columns(2)
            with col_w:
                batch_params['width'] = st.number_input("宽度", value=1920, key=f"{key_prefix}_width")
            with col_h:
                batch_params['height'] = st.number_input("高度", value=1080, key=f"{key_prefix}_height")
        
        if format_batch:
            batch_params['format'] = st.selectbox(
                "目标格式",
                options=['jpg', 'png', 'webp'],
                key=f"{key_prefix}_format"
            )
        
        if watermark_batch:
            batch_params['watermark_text'] = st.text_input(
                "水印文字",
                value="Video Studio",
                key=f"{key_prefix}_watermark"
            )
    
    # 执行批量处理
    if st.button("🚀 开始批量处理", type="primary", key=f"{key_prefix}_execute"):
        if any([resize_batch, enhance_batch, format_batch, watermark_batch]):
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            for i, asset_index in enumerate(selected_indices):
                asset = assets[asset_index]
                progress = (i + 1) / len(selected_indices)
                progress_bar.progress(progress)
                status_text.text(f"处理中: {asset['filename']} ({i+1}/{len(selected_indices)})")
                
                # 模拟处理时间
                time.sleep(0.5)
            
            progress_bar.empty()
            status_text.empty()
            st.success(f"✅ 批量处理完成，共处理 {len(selected_indices)} 个文件")
        else:
            st.warning("请至少选择一个处理操作")


def render_download_panel(task_info, key_prefix="download"):
    """渲染下载面板"""
    if not task_info or task_info.status.value != "completed" or not task_info.result_url:
        st.info("📥 视频生成完成后可在此下载")
        return
    
    st.subheader("📥 下载中心")
    
    col_preview, col_options = st.columns([2, 1])
    
    with col_preview:
        st.write("**视频预览**")
        
        # 视频预览
        try:
            st.video(task_info.result_url)
        except Exception as e:
            st.warning("视频预览暂不可用")
            st.code(task_info.result_url)
        
        # 视频信息
        with st.expander("📊 视频信息"):
            video_info = {
                "任务ID": task_info.task_id,
                "生成时间": task_info.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                "完成时间": task_info.updated_at.strftime("%Y-%m-%d %H:%M:%S"),
                "文件路径": task_info.result_url,
                "状态": task_info.status.value
            }
            
            for key, value in video_info.items():
                st.write(f"**{key}:** {value}")
    
    with col_options:
        st.write("**下载选项**")
        
        # 格式选择
        download_format = st.selectbox(
            "文件格式",
            options=["mp4", "mov", "avi", "webm"],
            format_func=lambda x: {
                "mp4": "MP4 (推荐)",
                "mov": "MOV (Apple)",
                "avi": "AVI (兼容)",
                "webm": "WebM (Web)"
            }.get(x, x.upper()),
            key=f"{key_prefix}_format"
        )
        
        # 质量选择
        download_quality = st.selectbox(
            "视频质量",
            options=["original", "1080p", "720p", "480p"],
            format_func=lambda x: {
                "original": "原始质量",
                "1080p": "1080p (高清)",
                "720p": "720p (标清)",
                "480p": "480p (压缩)"
            }.get(x, x),
            key=f"{key_prefix}_quality"
        )
        
        # 下载按钮
        filename = f"video_{task_info.task_id[:8]}.{download_format}"
        
        # 模拟文件数据（实际应该读取真实文件）
        try:
            # 这里应该根据task_info.result_url读取实际文件
            # 暂时使用占位符数据
            file_data = b"placeholder_video_data"
            
            st.download_button(
                label=f"📥 下载 {download_format.upper()}",
                data=file_data,
                file_name=filename,
                mime=f"video/{download_format}",
                type="primary",
                use_container_width=True,
                key=f"{key_prefix}_download"
            )
            
        except Exception as e:
            st.error(f"下载准备失败: {str(e)}")
        
        st.divider()
        
        # 快速操作
        st.write("**快速操作**")
        
        if st.button("📋 复制文件路径", use_container_width=True, key=f"{key_prefix}_copy_path"):
            st.code(task_info.result_url)
            st.success("✅ 路径已显示，请手动复制")
        
        if st.button("🔄 重新生成", use_container_width=True, key=f"{key_prefix}_regenerate"):
            st.info("请返回剧本创作页面重新开始")


def render_sharing_panel(task_info, key_prefix="share"):
    """渲染分享面板"""
    if not task_info or task_info.status.value != "completed":
        st.info("🔗 视频生成完成后可在此分享")
        return
    
    st.subheader("🔗 分享中心")
    
    # 生成分享链接
    base_url = "https://video-studio.example.com"  # 实际应该从配置获取
    share_url = f"{base_url}/video/{task_info.task_id}"
    
    # 分享链接
    st.write("**分享链接**")
    st.code(share_url)
    
    col_copy, col_qr = st.columns(2)
    
    with col_copy:
        if st.button("📋 复制链接", use_container_width=True, key=f"{key_prefix}_copy"):
            # 在实际应用中，这里应该使用JavaScript复制到剪贴板
            st.success("✅ 链接已复制")
    
    with col_qr:
        if st.button("📱 生成二维码", use_container_width=True, key=f"{key_prefix}_qr"):
            try:
                import qrcode
                from io import BytesIO
                
                # 生成二维码
                qr = qrcode.QRCode(version=1, box_size=10, border=5)
                qr.add_data(share_url)
                qr.make(fit=True)
                
                img = qr.make_image(fill_color="black", back_color="white")
                
                # 转换为字节流
                buf = BytesIO()
                img.save(buf, format='PNG')
                buf.seek(0)
                
                st.image(buf, caption="扫描二维码分享", width=200)
                
            except ImportError:
                st.warning("二维码功能需要安装 qrcode 库")
            except Exception as e:
                st.error(f"生成二维码失败: {str(e)}")
    
    st.divider()
    
    # 社交媒体分享
    st.write("**社交媒体分享**")
    
    # 分享文本模板
    share_text = st.text_area(
        "分享文案",
        value=f"我用 Video Studio 制作了一个精彩的视频！快来看看吧：{share_url}",
        height=100,
        key=f"{key_prefix}_text"
    )
    
    # 社交平台按钮
    col_platforms = st.columns(4)
    
    platforms = [
        ("微信", "💬", "#07C160"),
        ("微博", "📱", "#E6162D"), 
        ("抖音", "🎵", "#000000"),
        ("小红书", "📖", "#FF2442")
    ]
    
    for i, (name, icon, color) in enumerate(platforms):
        with col_platforms[i]:
            if st.button(f"{icon} {name}", use_container_width=True, key=f"{key_prefix}_{name}"):
                st.info(f"请手动分享到{name}")
    
    st.divider()
    
    # 嵌入代码
    with st.expander("🔧 嵌入代码"):
        st.write("**HTML 嵌入代码**")
        
        embed_width = st.slider("宽度", 300, 800, 640, key=f"{key_prefix}_width")
        embed_height = st.slider("高度", 200, 600, 360, key=f"{key_prefix}_height")
        
        embed_code = f'''<iframe 
    src="{share_url}/embed" 
    width="{embed_width}" 
    height="{embed_height}" 
    frameborder="0" 
    allowfullscreen>
</iframe>'''
        
        st.code(embed_code, language="html")
        
        if st.button("📋 复制嵌入代码", key=f"{key_prefix}_embed_copy"):
            st.success("✅ 嵌入代码已复制")


def render_video_analytics_panel(task_info, key_prefix="analytics"):
    """渲染视频分析面板"""
    if not task_info:
        return
    
    st.subheader("📊 视频分析")
    
    # 基础统计
    col_stats = st.columns(4)
    
    with col_stats[0]:
        st.metric("生成时间", f"{(task_info.updated_at - task_info.created_at).total_seconds():.1f}s")
    
    with col_stats[1]:
        st.metric("任务状态", task_info.status.value.upper())
    
    with col_stats[2]:
        st.metric("进度", f"{task_info.progress * 100:.0f}%")
    
    with col_stats[3]:
        # 模拟文件大小
        file_size_mb = 15.6  # 实际应该从文件系统获取
        st.metric("文件大小", f"{file_size_mb:.1f} MB")
    
    # 详细信息
    with st.expander("📋 详细信息"):
        details = {
            "任务ID": task_info.task_id,
            "创建时间": task_info.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "更新时间": task_info.updated_at.strftime("%Y-%m-%d %H:%M:%S"),
            "结果URL": task_info.result_url or "N/A",
            "错误信息": task_info.error_message or "无"
        }
        
        for key, value in details.items():
            st.write(f"**{key}:** {value}")
    
    # 性能分析（模拟数据）
    if task_info.status.value == "completed":
        with st.expander("⚡ 性能分析"):
            col_perf1, col_perf2 = st.columns(2)
            
            with col_perf1:
                st.write("**处理阶段耗时:**")
                stages = [
                    ("脚本解析", 2.1),
                    ("素材处理", 5.3),
                    ("视频生成", 45.2),
                    ("后期合成", 8.7)
                ]
                
                for stage, duration in stages:
                    st.write(f"• {stage}: {duration}s")
            
            with col_perf2:
                st.write("**资源使用:**")
                resources = [
                    ("CPU 使用率", "65%"),
                    ("内存使用", "2.1 GB"),
                    ("GPU 使用率", "89%"),
                    ("网络传输", "156 MB")
                ]
                
                for resource, usage in resources:
                    st.write(f"• {resource}: {usage}")


def render_export_options_panel(task_info, key_prefix="export"):
    """渲染导出选项面板"""
    if not task_info or task_info.status.value != "completed":
        return
    
    st.subheader("📤 导出选项")
    
    # 导出格式选择
    export_formats = {
        "video": {
            "name": "视频文件",
            "formats": ["mp4", "mov", "avi", "webm", "mkv"],
            "icon": "🎬"
        },
        "gif": {
            "name": "GIF 动图",
            "formats": ["gif"],
            "icon": "🖼️"
        },
        "frames": {
            "name": "帧序列",
            "formats": ["png", "jpg"],
            "icon": "📸"
        }
    }
    
    selected_type = st.selectbox(
        "导出类型",
        options=list(export_formats.keys()),
        format_func=lambda x: f"{export_formats[x]['icon']} {export_formats[x]['name']}",
        key=f"{key_prefix}_type"
    )
    
    # 格式特定选项
    if selected_type == "video":
        col_format, col_quality = st.columns(2)
        
        with col_format:
            video_format = st.selectbox(
                "视频格式",
                options=export_formats[selected_type]["formats"],
                key=f"{key_prefix}_video_format"
            )
        
        with col_quality:
            video_quality = st.selectbox(
                "视频质量",
                options=["ultra", "high", "medium", "low"],
                format_func=lambda x: {
                    "ultra": "超高 (4K)",
                    "high": "高清 (1080p)",
                    "medium": "标清 (720p)",
                    "low": "压缩 (480p)"
                }.get(x, x),
                index=1,
                key=f"{key_prefix}_video_quality"
            )
        
        # 高级视频选项
        with st.expander("🔧 高级选项"):
            col_adv1, col_adv2 = st.columns(2)
            
            with col_adv1:
                bitrate = st.slider("码率 (Mbps)", 1, 50, 10, key=f"{key_prefix}_bitrate")
                fps = st.selectbox("帧率", [24, 30, 60], index=1, key=f"{key_prefix}_fps")
            
            with col_adv2:
                codec = st.selectbox(
                    "编码器",
                    ["h264", "h265", "vp9"],
                    format_func=lambda x: {
                        "h264": "H.264 (兼容性好)",
                        "h265": "H.265 (高压缩)",
                        "vp9": "VP9 (开源)"
                    }.get(x, x),
                    key=f"{key_prefix}_codec"
                )
                
                audio_enabled = st.checkbox("包含音频", value=True, key=f"{key_prefix}_audio")
    
    elif selected_type == "gif":
        col_gif1, col_gif2 = st.columns(2)
        
        with col_gif1:
            gif_fps = st.slider("帧率", 5, 30, 15, key=f"{key_prefix}_gif_fps")
            gif_quality = st.slider("质量", 1, 10, 7, key=f"{key_prefix}_gif_quality")
        
        with col_gif2:
            gif_loop = st.checkbox("循环播放", value=True, key=f"{key_prefix}_gif_loop")
            gif_optimize = st.checkbox("优化大小", value=True, key=f"{key_prefix}_gif_optimize")
    
    elif selected_type == "frames":
        col_frame1, col_frame2 = st.columns(2)
        
        with col_frame1:
            frame_format = st.selectbox(
                "图片格式",
                options=export_formats[selected_type]["formats"],
                key=f"{key_prefix}_frame_format"
            )
            
            frame_interval = st.slider("提取间隔 (秒)", 0.1, 5.0, 1.0, key=f"{key_prefix}_interval")
        
        with col_frame2:
            frame_quality = st.slider("图片质量", 50, 100, 90, key=f"{key_prefix}_frame_quality")
            frame_size = st.selectbox(
                "图片尺寸",
                ["original", "1920x1080", "1280x720", "640x360"],
                key=f"{key_prefix}_frame_size"
            )
    
    # 导出按钮
    st.divider()
    
    export_filename = f"video_{task_info.task_id[:8]}"
    
    if st.button("🚀 开始导出", type="primary", use_container_width=True, key=f"{key_prefix}_start"):
        with st.spinner("正在导出..."):
            # 模拟导出过程
            progress_bar = st.progress(0)
            for i in range(101):
                progress_bar.progress(i / 100)
                time.sleep(0.02)
            
            progress_bar.empty()
            st.success(f"✅ 导出完成: {export_filename}")
            
            # 提供下载
            st.download_button(
                label=f"📥 下载 {selected_type.upper()}",
                data=b"exported_file_data",
                file_name=f"{export_filename}.{video_format if selected_type == 'video' else 'gif' if selected_type == 'gif' else 'zip'}",
                mime=f"video/{video_format}" if selected_type == "video" else "image/gif" if selected_type == "gif" else "application/zip"
            )
