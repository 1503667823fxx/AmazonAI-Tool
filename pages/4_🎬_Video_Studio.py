import streamlit as st
import asyncio
import time
import json
from typing import Optional, Dict, Any, List
from datetime import datetime

from auth import check_password  # 引入门禁系统
from app_utils.video_studio import ui_components
from app_utils.video_studio.workflow_manager import get_workflow_manager, create_video_task, get_task_status
from app_utils.video_studio.generation_engine import get_generation_engine
from app_utils.video_studio.asset_manager import AssetManager
from app_utils.video_studio.template_manager import TemplateManager
from app_utils.video_studio.models import VideoConfig, TaskStatus, Scene, AspectRatio, VideoQuality
from services.video_studio.script_engine import generate_video_script 
from services.video_studio.visual_engine import batch_generate_videos

# --- 1. 门禁检查 ---
if not check_password():
    st.stop()

# --- 2. 页面初始化 ---
ui_components.setup_page_config()
st.title("🎬 Amazon AI Video Studio")
st.caption("从商品链接到高转化短视频，全流程 AI 驱动工作台")

# 初始化后端系统
@st.cache_resource
def initialize_backend_systems():
    """Initialize backend systems with caching"""
    asset_manager = AssetManager()
    template_manager = TemplateManager()
    return asset_manager, template_manager

# 初始化 Session State (状态管理)
if 'video_script' not in st.session_state:
    st.session_state.video_script = ""
if 'generated_scenes' not in st.session_state:
    st.session_state.generated_scenes = [] # 存储生成的视频片段路径
if 'current_task_id' not in st.session_state:
    st.session_state.current_task_id = None
if 'task_status' not in st.session_state:
    st.session_state.task_status = None
if 'uploaded_assets' not in st.session_state:
    st.session_state.uploaded_assets = []
if 'selected_template' not in st.session_state:
    st.session_state.selected_template = None

# 获取后端系统实例
asset_manager, template_manager = initialize_backend_systems()

# --- 3. 侧边栏配置 ---
config = ui_components.render_sidebar()

# --- 4. 主工作区 (Tabs 流) ---
tab_script, tab_assets, tab_render = st.tabs([
    "📝 第一幕：剧本创作", 
    "🎨 第二幕：素材生成", 
    "🎞️ 第三幕：剪辑合成"
])
# ... (之前的 import)
# 引入新写好的服务


# ... (UI 代码)

# ==========================================
# TAB 1: 剧本创作和模板选择 - 重构版
# ==========================================
with tab_script:
    ui_components.render_step_indicator(0)
    
    # 显示当前任务状态（如果有）
    if st.session_state.current_task_id:
        st.info(f"当前任务: {st.session_state.current_task_id}")
        
        # 实时状态更新
        async def get_current_task_status():
            return await get_task_status(st.session_state.current_task_id)
        
        try:
            task_info = asyncio.run(get_current_task_status())
            if task_info:
                ui_components.render_task_status(task_info)
                st.session_state.task_status = task_info
        except Exception as e:
            st.warning(f"无法获取任务状态: {str(e)}")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("🎨 模板选择")
        
        # 获取可用模板
        available_templates = template_manager.list_templates()
        template_options = {f"{t.metadata.name} ({t.metadata.category.value})": t.template_id 
                          for t in available_templates}
        
        selected_template_name = st.selectbox(
            "选择视频模板",
            options=list(template_options.keys()),
            help="选择预设模板或使用自定义配置"
        )
        
        if selected_template_name:
            selected_template_id = template_options[selected_template_name]
            st.session_state.selected_template = template_manager.get_template(selected_template_id)
            
            # 显示模板信息
            if st.session_state.selected_template:
                template = st.session_state.selected_template
                st.info(f"**{template.metadata.name}**\n\n{template.metadata.description}")
                
                with st.expander("模板详情"):
                    st.write(f"**时长:** {template.config.duration}秒")
                    st.write(f"**画幅:** {template.config.aspect_ratio.value}")
                    st.write(f"**质量:** {template.config.quality.value}")
                    st.write(f"**风格:** {template.config.style.value}")
                    st.write(f"**场景数:** {template.config.scene_count}")
        
        st.divider()
        
        st.subheader("📦 商品输入")
        
        system_api_key = st.secrets.get("OPENAI_API_KEY", None)
        user_api_key = config.get("api_key") 
        final_api_key = system_api_key if system_api_key else user_api_key
        
        product_url = st.text_input("亚马逊商品链接 (ASIN)")
        product_features = st.text_area("或直接输入核心卖点", height=150, 
                                      placeholder="例如：这款蓝牙耳机拥有30小时续航...")
        
        # 自定义参数（如果选择了模板）
        if st.session_state.selected_template:
            st.subheader("⚙️ 自定义参数")
            custom_duration = st.slider("视频时长 (秒)", 5, 60, 
                                      st.session_state.selected_template.config.duration)
            custom_quality = st.selectbox("视频质量", 
                                        ["720p", "1080p", "4k"],
                                        index=1)
        else:
            target_duration = st.slider("目标视频时长 (秒)", 10, 60, 15)
        
        generate_btn = st.button("✨ AI 生成分镜脚本", type="primary", use_container_width=True)

    with col2:
        st.subheader("📜 分镜脚本编辑器")
        
        if generate_btn:
            if not final_api_key:
                st.error("🚫 未检测到 API Key。请在侧边栏输入或在 Secrets 中配置。")
            elif not product_features:
                 st.warning("⚠️ 请输入商品卖点信息。")
            else:
                with st.spinner("🧠 AI 导演正在拆解卖点、规划分镜..."):
                    # 使用模板或默认配置
                    if st.session_state.selected_template:
                        duration = custom_duration
                        style = st.session_state.selected_template.config.style.value
                    else:
                        duration = target_duration
                        style = config['style']
                    
                    # === 调用核心服务 ===
                    script_result = generate_video_script(
                        api_key=final_api_key,
                        product_info=product_features,
                        video_duration=duration,
                        style=style
                    )
                    
                    if "error" in script_result:
                        st.error(f"生成失败: {script_result['error']}")
                    else:
                        st.session_state.video_script = json.dumps(script_result, indent=4, ensure_ascii=False)
                        st.toast("脚本生成成功！", icon="✅")
                        st.rerun()

        # 显示和编辑脚本
        if st.session_state.video_script:
            # 允许用户编辑 JSON，这对后续步骤至关重要
            new_script = st.text_area(
                "请确认或微调生成的 JSON 脚本 (JSON 格式决定了后续画面的生成)",
                value=st.session_state.video_script,
                height=400,
                help="请勿破坏 JSON 的大括号 {} 结构"
            )
            st.session_state.video_script = new_script
            
            # 简单的 JSON 校验可视化
            try:
                parsed = json.loads(st.session_state.video_script)
                st.success(f"✅ 脚本有效：共包含 {len(parsed.get('scenes', []))} 个场景")
                
                # 显示场景预览
                with st.expander("场景预览"):
                    for i, scene in enumerate(parsed.get('scenes', [])):
                        st.write(f"**场景 {i+1}:** {scene.get('visual_prompt', 'N/A')}")
                        
            except Exception as e:
                st.error(f"⚠️ JSON 格式错误: {str(e)}")
        
        # 快速开始按钮
        if st.session_state.video_script and st.session_state.selected_template:
            if st.button("🚀 使用模板快速生成视频", type="primary", use_container_width=True):
                try:
                    # 解析脚本
                    script_data = json.loads(st.session_state.video_script)
                    
                    # 创建场景对象
                    scenes = []
                    for i, scene_data in enumerate(script_data.get('scenes', [])):
                        scene = Scene(
                            scene_id=f"scene_{i+1}",
                            visual_prompt=scene_data.get('visual_prompt', ''),
                            duration=scene_data.get('duration', 3.0),
                            camera_movement=scene_data.get('camera_movement'),
                            lighting=scene_data.get('lighting')
                        )
                        scenes.append(scene)
                    
                    # 创建视频配置
                    video_config = VideoConfig(
                        template_id=st.session_state.selected_template.template_id,
                        input_images=st.session_state.uploaded_assets,
                        duration=custom_duration if st.session_state.selected_template else target_duration,
                        aspect_ratio=AspectRatio.LANDSCAPE,  # 默认横屏
                        style=st.session_state.selected_template.config.style.value,
                        quality=VideoQuality.FULL_HD_1080P,
                        scenes=scenes
                    )
                    
                    # 创建任务
                    async def create_task():
                        return await create_video_task(video_config)
                    
                    task_id = asyncio.run(create_task())
                    st.session_state.current_task_id = task_id
                    st.success(f"✅ 视频生成任务已创建: {task_id}")
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"创建任务失败: {str(e)}")
# ==========================================
# TAB 2: 素材管理和生成 - 重构版
# ==========================================
with tab_assets:
    ui_components.render_step_indicator(1)
    
    # 使用新的文件上传组件
    new_uploads = ui_components.render_file_upload_zone(asset_manager, "main_upload")
    
    # 将新上传的文件添加到session state
    if new_uploads:
        for upload in new_uploads:
            # 检查是否已存在
            existing_ids = [asset.get('asset_id') for asset in st.session_state.uploaded_assets]
            if upload['asset_id'] not in existing_ids:
                st.session_state.uploaded_assets.append(upload)
        st.rerun()
    
    st.divider()
    
    # 使用新的资产画廊组件
    if st.session_state.uploaded_assets:
        selected_assets = ui_components.render_asset_gallery(
            st.session_state.uploaded_assets, 
            asset_manager, 
            "main_gallery"
        )
        
        # 批量处理控制
        ui_components.render_batch_processing_controls(
            st.session_state.uploaded_assets,
            "main_batch"
        )
    
    else:
        st.info("📁 请上传素材开始创作")
    
    st.divider()
    
    # 视频生成部分
    if st.session_state.video_script and st.session_state.uploaded_assets:
        st.subheader("🎬 视频生成")
        
        col_gen_config, col_gen_action = st.columns([2, 1])
        
        with col_gen_config:
            # 获取脚本对象
            try:
                script_obj = json.loads(st.session_state.video_script)
                scenes = script_obj.get('scenes', [])
                st.info(f"检测到 {len(scenes)} 个分镜场景，{len(st.session_state.uploaded_assets)} 个素材")
            except:
                st.error("脚本格式错误，无法解析")
                st.stop()
            
            # 生成配置
            generation_model = st.selectbox(
                "选择生成模型",
                options=["luma", "runway", "pika"],
                format_func=lambda x: {
                    "luma": "Luma Dream Machine",
                    "runway": "Runway ML",
                    "pika": "Pika Labs"
                }.get(x, x)
            )
            
            video_quality = st.selectbox("视频质量", ["720p", "1080p", "4k"], index=1)
            
        with col_gen_action:
            st.write("**生成控制**")
            
            if st.button("🎥 开始生成视频", type="primary", use_container_width=True):
                try:
                    # 创建场景对象
                    scenes_list = []
                    for i, scene_data in enumerate(scenes):
                        scene = Scene(
                            scene_id=f"scene_{i+1}",
                            visual_prompt=scene_data.get('visual_prompt', ''),
                            duration=scene_data.get('duration', 3.0),
                            camera_movement=scene_data.get('camera_movement'),
                            lighting=scene_data.get('lighting'),
                            reference_image=st.session_state.uploaded_assets[i % len(st.session_state.uploaded_assets)]['asset_id'] if st.session_state.uploaded_assets else None
                        )
                        scenes_list.append(scene)
                    
                    # 创建视频配置
                    video_config = VideoConfig(
                        template_id=st.session_state.selected_template.template_id if st.session_state.selected_template else "custom",
                        input_images=[asset['asset_id'] for asset in st.session_state.uploaded_assets],
                        duration=sum(scene.duration for scene in scenes_list),
                        aspect_ratio=AspectRatio.LANDSCAPE,
                        style="cinematic",
                        quality=VideoQuality.FULL_HD_1080P if video_quality == "1080p" else VideoQuality.HD_720P,
                        scenes=scenes_list
                    )
                    
                    # 创建生成任务
                    async def create_generation_task():
                        return await create_video_task(video_config)
                    
                    task_id = asyncio.run(create_generation_task())
                    st.session_state.current_task_id = task_id
                    
                    st.success(f"✅ 视频生成任务已创建: {task_id}")
                    st.info("请切换到 '剪辑合成' 标签页查看进度")
                    
                except Exception as e:
                    st.error(f"❌ 创建生成任务失败: {str(e)}")
    
    elif not st.session_state.video_script:
        st.warning("⚠️ 请先在 '剧本创作' 页面生成脚本")
    elif not st.session_state.uploaded_assets:
        st.warning("⚠️ 请先上传参考素材")
# ==========================================
# TAB 3: 渲染和下载 - 重构版
# ==========================================
with tab_render:
    ui_components.render_step_indicator(2)
    
    st.subheader("🎞️ 视频渲染和下载")
    
    # 显示当前任务状态
    if st.session_state.current_task_id:
        st.markdown("### 📊 任务进度监控")
        
        # 创建实时更新的占位符
        status_placeholder = st.empty()
        
        # 获取任务状态
        async def get_current_status():
            return await get_task_status(st.session_state.current_task_id)
        
        try:
            current_task = asyncio.run(get_current_status())
            if current_task:
                with status_placeholder.container():
                    ui_components.render_task_status(current_task)
                
                # 如果任务完成，显示下载和分享选项
                if current_task.status == TaskStatus.COMPLETED and current_task.result_url:
                    st.success("🎉 视频生成完成！")
                    
                    # 创建标签页用于不同功能
                    tab_download, tab_share, tab_export, tab_analytics = st.tabs([
                        "📥 下载", "🔗 分享", "📤 导出", "📊 分析"
                    ])
                    
                    with tab_download:
                        ui_components.render_download_panel(current_task, "main_download")
                    
                    with tab_share:
                        ui_components.render_sharing_panel(current_task, "main_share")
                    
                    with tab_export:
                        ui_components.render_export_options_panel(current_task, "main_export")
                    
                    with tab_analytics:
                        ui_components.render_video_analytics_panel(current_task, "main_analytics")
                
                elif current_task.status == TaskStatus.FAILED:
                    st.error("❌ 视频生成失败")
                    if current_task.error_message:
                        st.error(f"错误信息: {current_task.error_message}")
                    
                    # 重试选项
                    if st.button("🔄 重试生成", type="secondary"):
                        async def retry_task():
                            from app_utils.video_studio.workflow_manager import get_workflow_manager
                            manager = await get_workflow_manager()
                            return await manager.retry_failed_task(st.session_state.current_task_id)
                        
                        if asyncio.run(retry_task()):
                            st.success("✅ 任务已重新提交")
                            st.rerun()
                        else:
                            st.error("❌ 重试失败")
                
                # 任务控制按钮
                st.divider()
                col_control1, col_control2, col_control3 = st.columns(3)
                
                with col_control1:
                    if st.button("🔄 刷新状态", use_container_width=True):
                        st.rerun()
                
                with col_control2:
                    if current_task.status in [TaskStatus.PENDING, TaskStatus.PROCESSING, TaskStatus.GENERATING]:
                        if st.button("⏹️ 取消任务", use_container_width=True):
                            async def cancel_current_task():
                                from app_utils.video_studio.workflow_manager import cancel_task
                                return await cancel_task(st.session_state.current_task_id)
                            
                            if asyncio.run(cancel_current_task()):
                                st.success("✅ 任务已取消")
                                st.session_state.current_task_id = None
                                st.rerun()
                            else:
                                st.error("❌ 取消失败")
                
                with col_control3:
                    if st.button("🆕 新建任务", use_container_width=True):
                        st.session_state.current_task_id = None
                        st.session_state.video_script = ""
                        st.session_state.uploaded_assets = []
                        st.success("✅ 已清空当前任务，可以开始新的创作")
                        st.rerun()
            
            else:
                st.warning("⚠️ 无法获取任务信息")
        
        except Exception as e:
            st.error(f"❌ 获取任务状态失败: {str(e)}")
    
    else:
        # 没有当前任务时的界面
        st.info("📝 当前没有进行中的任务")
        
        col_info, col_action = st.columns([2, 1])
        
        with col_info:
            st.markdown("""
            ### 🎬 视频生成工作流
            
            1. **剧本创作**: 选择模板并生成分镜脚本
            2. **素材管理**: 上传和处理参考图片
            3. **视频生成**: 启动AI视频生成任务
            4. **渲染下载**: 监控进度并下载成品
            
            请按照上述步骤完成视频创作。
            """)
        
        with col_action:
            st.markdown("### 🚀 快速开始")
            
            if st.button("📝 开始创作", type="primary", use_container_width=True):
                st.info("请切换到 '剧本创作' 标签页开始")
            
            if st.button("📊 查看历史任务", use_container_width=True):
                # 显示历史任务（这里可以扩展）
                st.info("历史任务功能将在后续版本中提供")
    
    # 系统状态信息
    with st.expander("🔧 系统状态"):
        try:
            # 获取存储统计
            storage_stats = asset_manager.get_storage_stats()
            
            col_stat1, col_stat2, col_stat3 = st.columns(3)
            
            with col_stat1:
                st.metric("总素材数", storage_stats['total_assets'])
            
            with col_stat2:
                st.metric("存储使用", f"{storage_stats['total_size_mb']:.1f} MB")
            
            with col_stat3:
                if 'disk_usage_percent' in storage_stats:
                    st.metric("磁盘使用率", f"{storage_stats['disk_usage_percent']:.1f}%")
            
            # 显示详细统计
            st.json(storage_stats)
            
        except Exception as e:
            st.error(f"无法获取系统状态: {str(e)}")
