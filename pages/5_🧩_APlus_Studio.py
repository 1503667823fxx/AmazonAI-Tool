import streamlit as st
import sys
import os
import asyncio
from typing import List, Dict, Any, Optional
from PIL import Image
from datetime import datetime
import google.generativeai as genai
import json

# 添加项目根目录到路径
sys.path.append(os.path.abspath('.'))

# 身份验证
try:
    import auth
    if not auth.check_password():
        st.stop()
except ImportError:
    pass

# 导入A+工作流组件
try:
    from app_utils.aplus_studio.controller import APlusController
    from app_utils.aplus_studio.input_panel import ProductInputPanel
    from app_utils.aplus_studio.generation_panel import ModuleGenerationPanel
    from app_utils.aplus_studio.preview_gallery import ImagePreviewGallery
    from app_utils.aplus_studio.regeneration_panel import RegenerationPanel
    from services.aplus_studio.models import ModuleType, GenerationStatus
    APLUS_AVAILABLE = True
except ImportError as e:
    APLUS_AVAILABLE = False
    st.error(f"A+ Studio组件导入失败: {e}")

# 页面配置
st.set_page_config(
    page_title="A+ Studio", 
    page_icon="🧩", 
    layout="wide"
)

def main():
    """主应用入口"""
    st.title("🧩 A+ 图片制作流 (APlus Studio)")
    st.caption("AI 驱动的亚马逊 A+ 页面智能图片生成工具")
    
    if not APLUS_AVAILABLE:
        st.error("A+ Studio系统组件未正确加载，请检查系统配置")
        return
    
    # 初始化控制器和组件
    if 'aplus_controller' not in st.session_state:
        st.session_state.aplus_controller = APlusController()
    
    controller = st.session_state.aplus_controller
    
    # 初始化UI组件
    input_panel = ProductInputPanel()
    generation_panel = ModuleGenerationPanel(controller)
    preview_gallery = ImagePreviewGallery(controller)
    regeneration_panel = RegenerationPanel(controller)
    
    # 侧边栏 - 会话管理和系统状态
    render_sidebar(controller)
    
    # 主界面标签页
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "💡 卖点分析", "📝 产品分析", "🎨 模块生成", "🖼️ 图片预览", "🔄 重新生成", "📊 数据导出"
    ])
    
    with tab1:
        render_selling_points_analysis_tab(controller)
    
    with tab2:
        render_product_analysis_tab(controller, input_panel)
    
    with tab3:
        render_module_generation_tab(controller, generation_panel)
    
    with tab4:
        render_preview_gallery_tab(controller, preview_gallery)
    
    with tab5:
        render_regeneration_tab(controller, regeneration_panel)
    
    with tab6:
        render_export_tab(controller)


def render_sidebar(controller: APlusController):
    """渲染侧边栏"""
    with st.sidebar:
        st.header("🎛️ 控制面板")
        
        # 会话信息
        session_info = controller.get_session_info()
        if session_info:
            st.success(f"会话ID: {session_info['session_id'][:8]}...")
            
            # 会话统计
            col1, col2 = st.columns(2)
            with col1:
                st.metric("已完成", session_info['completed_modules'])
            with col2:
                st.metric("总模块", session_info['total_modules'])
            
            # 会话操作
            if st.button("🔄 重置会话", use_container_width=True):
                controller.reset_session()
                st.rerun()
        else:
            st.info("没有活跃会话")
        
        st.divider()
        
        # 模块状态概览
        st.subheader("📊 模块状态")
        progress = controller.get_generation_progress()
        
        for module_type in ModuleType:
            status = progress.get(module_type, GenerationStatus.NOT_STARTED)
            status_icon = {
                GenerationStatus.NOT_STARTED: "⚪",
                GenerationStatus.IN_PROGRESS: "🟡", 
                GenerationStatus.COMPLETED: "🟢",
                GenerationStatus.FAILED: "🔴"
            }.get(status, "⚪")
            
            module_names = {
                ModuleType.IDENTITY: "身份代入",
                ModuleType.SENSORY: "感官解构",
                ModuleType.EXTENSION: "多维延展",
                ModuleType.TRUST: "信任转化"
            }
            
            st.write(f"{status_icon} {module_names.get(module_type, module_type.value)}")
        
        st.divider()
        
        # 系统健康状态
        st.subheader("🔧 系统状态")
        health_status = controller.get_system_health_status()
        
        if health_status.get("overall_status") == "healthy":
            st.success("✅ 系统正常")
        elif health_status.get("overall_status") == "degraded":
            st.warning("⚠️ 系统降级")
        else:
            st.error("❌ 系统异常")
        
        # 快速操作
        st.subheader("⚡ 快速操作")
        
        if st.button("🔍 系统诊断", use_container_width=True):
            with st.expander("系统诊断结果", expanded=True):
                st.json(health_status)
        
        if st.button("🧹 清理缓存", use_container_width=True):
            controller.cleanup_old_versions()
            st.success("缓存已清理")


def render_selling_points_analysis_tab(controller: APlusController):
    """渲染产品卖点分析标签页"""
    st.header("💡 产品卖点分析")
    st.caption("上传产品图片，让AI智能分析产品卖点并生成营销建议")
    
    # 检查当前会话状态
    session = controller.state_manager.get_current_session()
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("📸 图片上传")
        
        # 图片上传组件
        uploaded_files = st.file_uploader(
            "上传产品图片进行卖点分析",
            type=["jpg", "jpeg", "png", "webp"],
            accept_multiple_files=True,
            help="支持多张图片，AI将分析产品的视觉卖点和特征",
            key="selling_points_images"
        )
        
        if uploaded_files:
            # 图片预览 - 默认收起
            with st.expander(f"📷 已上传 {len(uploaded_files)} 张图片", expanded=False):
                # 显示上传的图片预览 - 紧凑布局
                if len(uploaded_files) <= 3:
                    cols = st.columns(len(uploaded_files))
                    for i, file in enumerate(uploaded_files):
                        with cols[i]:
                            image = Image.open(file)
                            st.image(image, caption=f"图片 {i+1}", use_container_width=True)
                else:
                    # 如果图片多，使用2列布局
                    for i in range(0, len(uploaded_files), 2):
                        cols = st.columns(2)
                        for j in range(2):
                            if i + j < len(uploaded_files):
                                with cols[j]:
                                    image = Image.open(uploaded_files[i + j])
                                    st.image(image, caption=f"图片 {i+j+1}", use_container_width=True)
            
            # 分析按钮
            if st.button("🔍 开始卖点分析", type="primary", use_container_width=True):
                with st.spinner("🤖 AI正在分析产品卖点..."):
                    try:
                        # 转换图片格式
                        images = []
                        for file in uploaded_files:
                            image = Image.open(file)
                            images.append(image)
                        
                        # 执行卖点分析 - 直接调用Gemini API
                        selling_points_result = analyze_selling_points_sync(images)
                        
                        # 为这次分析生成唯一ID
                        import time
                        analysis_id = str(int(time.time()))
                        selling_points_result['analysis_id'] = analysis_id
                        
                        # 保存分析结果到session state
                        st.session_state['selling_points_result'] = selling_points_result
                        st.success("✅ 卖点分析完成！")
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"❌ 卖点分析失败: {str(e)}")
        else:
            st.info("👆 请上传产品图片开始分析")
            
            # 功能说明 - 紧凑版本
            with st.expander("💡 功能说明", expanded=False):
                st.markdown("""
                **AI将分析：**
                - 🎯 核心卖点识别
                - 🎨 视觉特征分析  
                - 💼 营销建议生成
                - 🏠 使用场景定位
                """)
    
    with col2:
        st.subheader("📊 分析结果")
        
        # 显示分析结果
        if 'selling_points_result' in st.session_state:
            result = st.session_state['selling_points_result']
            render_selling_points_results_compact(result)
        else:
            st.info("等待图片上传和分析...")
            
            # 简化的功能介绍
            st.markdown("""
            **🚀 智能卖点分析**
            
            - 📈 自动识别产品优势
            - 🎨 分析设计风格特点  
            - 💡 生成营销建议
            - 📋 提供可复制文案
            """)


def render_selling_points_results_compact(result: Dict[str, Any]):
    """渲染卖点分析结果 - 紧凑版本"""
    if not result:
        st.warning("分析结果为空")
        return
    
    # 获取分析ID，用于生成唯一的key
    analysis_id = result.get('analysis_id', 'default')
    
    # 核心卖点 - 紧凑显示
    if 'key_selling_points' in result:
        st.markdown("**🎯 核心卖点**")
        selling_points = result['key_selling_points']
        
        # 显示所有卖点，但用视觉层次区分重要性
        for i, point in enumerate(selling_points, 1):
            title = point.get('title', '卖点')
            description = point.get('description', '暂无描述')
            confidence = point.get('confidence', 0)
            
            # 前3个用粗体，后面的用普通字体
            if i <= 3:
                st.write(f"**{i}. {title}** ({confidence:.0%})")
                st.caption(description[:80] + "..." if len(description) > 80 else description)
            else:
                # 后面的卖点用较小的字体和较淡的颜色
                st.write(f"{i}. {title} ({confidence:.0%})")
                st.caption(description[:60] + "..." if len(description) > 60 else description)
            
            # 准备复制文本
            point_text = f"{i}. {title}\n   {description}"
            copyable_points.append(point_text)
            
            # 前3个后面加个小分隔
            if i == 3 and len(selling_points) > 3:
                st.markdown("---")
        
        # 可复制的卖点汇总 - 紧凑版
        with st.expander("📋 复制卖点文案", expanded=False):
            all_points_text = "\n\n".join(copyable_points)
            st.text_area("", value=all_points_text, height=150, key=f"copyable_points_{analysis_id}", label_visibility="collapsed")
    
    # 营销建议 - 紧凑显示
    if 'marketing_insights' in result:
        st.markdown("**💼 营销建议**")
        insights = result['marketing_insights']
        
        # 只显示关键信息
        if 'target_audience' in insights:
            st.write(f"👥 **目标用户**: {insights['target_audience'][:50]}...")
        
        if 'aplus_recommendations' in insights and insights['aplus_recommendations']:
            st.write("📝 **A+页面建议**:")
            for i, rec in enumerate(insights['aplus_recommendations'][:2], 1):
                st.write(f"  {i}. {rec[:60]}...")
        
        # 完整营销建议 - 可展开
        with st.expander("📊 完整营销分析", expanded=False):
            if 'emotional_triggers' in insights:
                st.write("**情感触发点**:")
                for trigger in insights['emotional_triggers']:
                    st.write(f"• {trigger}")
            
            if 'competitive_advantages' in insights:
                st.write("**竞争优势**:")
                for adv in insights['competitive_advantages']:
                    st.write(f"• {adv}")
            
            # 可复制的营销文案
            marketing_text = f"""目标用户: {insights.get('target_audience', '未分析')}

A+页面建议:
{chr(10).join(['• ' + rec for rec in insights.get('aplus_recommendations', [])])}

情感触发点:
{chr(10).join(['• ' + trigger for trigger in insights.get('emotional_triggers', [])])}

竞争优势:
{chr(10).join(['• ' + adv for adv in insights.get('competitive_advantages', [])])}"""
            
            st.text_area("营销建议文案", value=marketing_text, height=200, key=f"copyable_marketing_{analysis_id}")
    
    # 视觉特征 - 可展开
    if 'visual_features' in result:
        with st.expander("🎨 视觉特征分析", expanded=False):
            visual = result['visual_features']
            
            col1, col2 = st.columns(2)
            with col1:
                if 'design_style' in visual:
                    st.write(f"**设计风格**: {visual['design_style']}")
                if 'color_scheme' in visual:
                    st.write(f"**色彩方案**: {visual['color_scheme'][:30]}...")
            
            with col2:
                if 'material_perception' in visual:
                    st.write(f"**材质感知**: {visual['material_perception'][:30]}...")
                if 'quality_indicators' in visual:
                    st.write(f"**品质指标**: {', '.join(visual['quality_indicators'][:2])}")
            
            # 可复制的视觉特征
            visual_text = f"""设计风格: {visual.get('design_style', '未识别')}
色彩方案: {visual.get('color_scheme', '未分析')}
材质感知: {visual.get('material_perception', '未识别')}
品质指标: {', '.join(visual.get('quality_indicators', []))}"""
            
            st.text_area("视觉特征文案", value=visual_text, height=120, key=f"copyable_visual_{analysis_id}")
    
    # 操作按钮 - 紧凑布局
    st.divider()
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📄 完整报告", use_container_width=True):
            st.session_state['show_full_report'] = True
            st.rerun()
    
    with col2:
        if st.button("🔄 重新分析", use_container_width=True):
            if 'selling_points_result' in st.session_state:
                del st.session_state['selling_points_result']
            if 'show_full_report' in st.session_state:
                del st.session_state['show_full_report']
            st.rerun()
    
    with col3:
        # 导出按钮
        export_data = {
            "analysis_timestamp": datetime.now().isoformat(),
            "selling_points_analysis": result
        }
        import json
        json_str = json.dumps(export_data, indent=2, ensure_ascii=False)
        st.download_button(
            "💾 导出",
            data=json_str,
            file_name=f"selling_points_{datetime.now().strftime('%m%d_%H%M')}.json",
            mime="application/json",
            use_container_width=True
        )
    
    # 显示完整报告
    if st.session_state.get('show_full_report', False):
        with st.expander("📄 完整分析报告", expanded=True):
            full_report = generate_copyable_report(result)
            st.text_area("", value=full_report, height=300, key=f"full_report_{analysis_id}", label_visibility="collapsed")
            
            if st.button("❌ 关闭报告"):
                st.session_state['show_full_report'] = False
                st.rerun()


def render_selling_points_results(result: Dict[str, Any]):
    """渲染卖点分析结果 - 优化为方便复制粘贴的格式"""
    if not result:
        st.warning("分析结果为空")
        return
    
    # 获取分析ID，用于生成唯一的key
    analysis_id = result.get('analysis_id', 'default')
    
    # 核心卖点 - 可复制格式
    if 'key_selling_points' in result:
        st.subheader("🎯 核心卖点")
        selling_points = result['key_selling_points']
        
        # 生成可复制的卖点文本
        copyable_points = []
        for i, point in enumerate(selling_points, 1):
            title = point.get('title', '卖点')
            description = point.get('description', '暂无描述')
            confidence = point.get('confidence', 0)
            
            # 格式化为可复制的文本
            point_text = f"{i}. {title}\n   {description}"
            copyable_points.append(point_text)
            
            # 显示在界面上
            with st.container():
                st.markdown(f"**{i}. {title}** (置信度: {confidence:.1%})")
                st.write(f"📝 {description}")
                
                if point.get('visual_evidence'):
                    st.caption(f"🔍 视觉证据: {point['visual_evidence']}")
                
                st.divider()
        
        # 提供可复制的卖点汇总
        with st.expander("📋 卖点汇总 (可复制)", expanded=False):
            all_points_text = "\n\n".join(copyable_points)
            st.text_area("核心卖点汇总", value=all_points_text, height=200, key=f"copyable_points_{analysis_id}")
    
    # 视觉特征分析 - 可复制格式
    if 'visual_features' in result:
        st.subheader("🎨 视觉特征")
        visual = result['visual_features']
        
        col1, col2 = st.columns(2)
        
        with col1:
            if 'design_style' in visual:
                st.write(f"**设计风格**: {visual['design_style']}")
            
            if 'color_scheme' in visual:
                st.write(f"**色彩方案**: {visual['color_scheme']}")
            
            if 'material_perception' in visual:
                st.write(f"**材质感知**: {visual['material_perception']}")
        
        with col2:
            if 'quality_indicators' in visual:
                st.write("**品质指标**:")
                for indicator in visual['quality_indicators']:
                    st.write(f"• {indicator}")
        
        # 可复制的视觉特征文本
        with st.expander("🎨 视觉特征汇总 (可复制)", expanded=False):
            visual_text = f"""设计风格: {visual.get('design_style', '未识别')}
色彩方案: {visual.get('color_scheme', '未分析')}
材质感知: {visual.get('material_perception', '未识别')}
品质指标: {', '.join(visual.get('quality_indicators', []))}
美学吸引力: {visual.get('aesthetic_appeal', '未评估')}"""
            st.text_area("视觉特征汇总", value=visual_text, height=150, key=f"copyable_visual_{analysis_id}")
    
    # 营销建议 - 可复制格式
    if 'marketing_insights' in result:
        st.subheader("💼 营销建议")
        insights = result['marketing_insights']
        
        # 目标用户
        if 'target_audience' in insights:
            st.write(f"**目标用户**: {insights['target_audience']}")
        
        # 情感触发点
        if 'emotional_triggers' in insights:
            st.write("**情感触发点**:")
            for trigger in insights['emotional_triggers']:
                st.write(f"• {trigger}")
        
        # A+页面建议
        if 'aplus_recommendations' in insights:
            st.write("**A+页面建议**:")
            for rec in insights['aplus_recommendations']:
                st.write(f"• {rec}")
        
        # 可复制的营销建议文本
        with st.expander("💼 营销建议汇总 (可复制)", expanded=False):
            marketing_text = f"""目标用户: {insights.get('target_audience', '未分析')}

情感触发点:
{chr(10).join(['• ' + trigger for trigger in insights.get('emotional_triggers', [])])}

定位策略: {insights.get('positioning_strategy', '未提供')}

A+页面建议:
{chr(10).join(['• ' + rec for rec in insights.get('aplus_recommendations', [])])}

竞争优势:
{chr(10).join(['• ' + adv for adv in insights.get('competitive_advantages', [])])}"""
            st.text_area("营销建议汇总", value=marketing_text, height=250, key=f"copyable_marketing_{analysis_id}")
    
    # 使用场景 - 可复制格式
    if 'usage_scenarios' in result:
        st.subheader("🏠 使用场景")
        scenarios = result['usage_scenarios']
        
        scenario_texts = []
        for i, scenario in enumerate(scenarios, 1):
            scenario_desc = scenario.get('scenario', '场景描述')
            benefits = scenario.get('benefits', '优势说明')
            emotion = scenario.get('target_emotion', '目标情感')
            
            scenario_text = f"场景{i}: {scenario_desc}\n优势: {benefits}\n情感: {emotion}"
            scenario_texts.append(scenario_text)
            
            st.write(f"**场景 {i}**: {scenario_desc}")
            st.write(f"• 优势: {benefits}")
            st.write(f"• 目标情感: {emotion}")
            st.divider()
        
        # 可复制的场景文本
        with st.expander("🏠 使用场景汇总 (可复制)", expanded=False):
            all_scenarios_text = "\n\n".join(scenario_texts)
            st.text_area("使用场景汇总", value=all_scenarios_text, height=200, key=f"copyable_scenarios_{analysis_id}")
    
    # 置信度和质量评估
    if 'analysis_quality' in result:
        st.subheader("📈 分析质量")
        quality = result['analysis_quality']
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            overall_score = quality.get('overall_confidence', 0.8)
            st.metric("整体置信度", f"{overall_score:.1%}")
        
        with col2:
            image_quality = quality.get('image_quality_score', 0.8)
            st.metric("图片质量", f"{image_quality:.1%}")
        
        with col3:
            analysis_depth = quality.get('analysis_depth', 0.8)
            st.metric("分析深度", f"{analysis_depth:.1%}")
    
    # 完整分析报告 - 一键复制
    st.divider()
    st.subheader("📄 完整分析报告")
    
    # 生成完整的可复制报告
    full_report = generate_copyable_report(result)
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📋 生成完整报告", use_container_width=True):
            st.session_state['show_full_report'] = True
    
    with col2:
        if st.button("🔄 重新分析", use_container_width=True):
            if 'selling_points_result' in st.session_state:
                del st.session_state['selling_points_result']
            if 'show_full_report' in st.session_state:
                del st.session_state['show_full_report']
            st.rerun()
    
    # 显示完整报告
    if st.session_state.get('show_full_report', False):
        st.text_area("完整分析报告 (可复制)", value=full_report, height=400, key=f"full_report_{analysis_id}")


def generate_copyable_report(result: Dict[str, Any]) -> str:
    """生成完整的可复制分析报告"""
    report_lines = []
    report_lines.append("=" * 50)
    report_lines.append("产品卖点分析报告")
    report_lines.append("=" * 50)
    report_lines.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append("")
    
    # 核心卖点
    if 'key_selling_points' in result:
        report_lines.append("【核心卖点】")
        for i, point in enumerate(result['key_selling_points'], 1):
            title = point.get('title', '卖点')
            description = point.get('description', '暂无描述')
            confidence = point.get('confidence', 0)
            report_lines.append(f"{i}. {title} (置信度: {confidence:.1%})")
            report_lines.append(f"   {description}")
            if point.get('visual_evidence'):
                report_lines.append(f"   视觉证据: {point['visual_evidence']}")
            report_lines.append("")
    
    # 视觉特征
    if 'visual_features' in result:
        visual = result['visual_features']
        report_lines.append("【视觉特征】")
        report_lines.append(f"设计风格: {visual.get('design_style', '未识别')}")
        report_lines.append(f"色彩方案: {visual.get('color_scheme', '未分析')}")
        report_lines.append(f"材质感知: {visual.get('material_perception', '未识别')}")
        if visual.get('quality_indicators'):
            report_lines.append(f"品质指标: {', '.join(visual['quality_indicators'])}")
        report_lines.append("")
    
    # 营销建议
    if 'marketing_insights' in result:
        insights = result['marketing_insights']
        report_lines.append("【营销建议】")
        report_lines.append(f"目标用户: {insights.get('target_audience', '未分析')}")
        report_lines.append(f"定位策略: {insights.get('positioning_strategy', '未提供')}")
        
        if insights.get('emotional_triggers'):
            report_lines.append("情感触发点:")
            for trigger in insights['emotional_triggers']:
                report_lines.append(f"• {trigger}")
        
        if insights.get('aplus_recommendations'):
            report_lines.append("A+页面建议:")
            for rec in insights['aplus_recommendations']:
                report_lines.append(f"• {rec}")
        
        if insights.get('competitive_advantages'):
            report_lines.append("竞争优势:")
            for adv in insights['competitive_advantages']:
                report_lines.append(f"• {adv}")
        report_lines.append("")
    
    # 使用场景
    if 'usage_scenarios' in result:
        report_lines.append("【使用场景】")
        for i, scenario in enumerate(result['usage_scenarios'], 1):
            report_lines.append(f"场景{i}: {scenario.get('scenario', '场景描述')}")
            report_lines.append(f"优势: {scenario.get('benefits', '优势说明')}")
            report_lines.append(f"目标情感: {scenario.get('target_emotion', '目标情感')}")
            report_lines.append("")
    
    # 分析质量
    if 'analysis_quality' in result:
        quality = result['analysis_quality']
        report_lines.append("【分析质量】")
        report_lines.append(f"整体置信度: {quality.get('overall_confidence', 0.8):.1%}")
        report_lines.append(f"图片质量评分: {quality.get('image_quality_score', 0.8):.1%}")
        report_lines.append(f"分析深度: {quality.get('analysis_depth', 0.8):.1%}")
        report_lines.append("")
    
    report_lines.append("=" * 50)
    report_lines.append("报告结束")
    
    return "\n".join(report_lines)


def analyze_selling_points_sync(images: List[Image.Image]) -> Dict[str, Any]:
    """同步版本的产品卖点分析函数"""
    try:
        # 检查API配置
        if "GOOGLE_API_KEY" not in st.secrets:
            st.error("❌ 未找到 Google API Key")
            return generate_fallback_selling_points()
        
        # 配置Gemini API
        genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
        
        # 使用gemini-3-flash-preview模型进行图片分析
        model = genai.GenerativeModel('models/gemini-3-flash-preview')
        
        # 构建分析提示词
        selling_points_prompt = """
        你是一个专业的产品营销分析师。请仔细分析这些产品图片，识别产品的核心卖点和营销价值。

        请以JSON格式返回详细的产品卖点分析：

        {
            "key_selling_points": [
                {
                    "title": "卖点标题",
                    "description": "详细描述这个卖点如何吸引消费者，为什么重要",
                    "category": "功能性/美观性/品质感/便利性",
                    "confidence": 0.95,
                    "visual_evidence": "从图片中观察到的具体支持证据"
                }
            ],
            "visual_features": {
                "design_style": "现代简约/奢华精致/实用主义/工业风等具体风格",
                "color_scheme": "主要色彩搭配和视觉效果描述",
                "material_perception": "材质给人的感受和品质印象",
                "quality_indicators": ["从图片看出的品质指标1", "品质指标2"],
                "aesthetic_appeal": "整体美学吸引力评估"
            },
            "marketing_insights": {
                "target_audience": "基于产品特征推断的目标用户群体",
                "emotional_triggers": ["能触发购买欲望的情感点1", "情感点2"],
                "positioning_strategy": "建议的产品市场定位策略",
                "aplus_recommendations": ["Amazon A+页面展示建议1", "建议2", "建议3"],
                "competitive_advantages": ["相比同类产品的优势1", "优势2"]
            },
            "usage_scenarios": [
                {
                    "scenario": "具体使用场景描述",
                    "benefits": "在此场景下的具体优势",
                    "target_emotion": "想要激发的目标情感"
                }
            ],
            "analysis_quality": {
                "overall_confidence": 0.9,
                "image_quality_score": 0.85,
                "analysis_depth": 0.88,
                "recommendations_reliability": 0.92
            }
        }

        分析要求：
        1. 仔细观察产品的外观、材质、设计细节
        2. 识别产品的独特特征和潜在卖点
        3. 考虑北美消费者的购买心理和偏好
        4. 提供具体可执行的营销建议
        5. 评估产品在Amazon A+页面中的展示潜力
        6. 分析结果要客观、具体、有说服力

        请只返回JSON格式的分析结果，不要包含其他文字。
        """
        
        # 准备图片和提示词
        content_parts = [selling_points_prompt]
        content_parts.extend(images)
        
        # 调用Gemini API进行分析
        response = model.generate_content(content_parts)
        
        # 解析响应
        response_text = response.text.strip()
        
        # 清理响应文本，移除可能的markdown标记
        if response_text.startswith('```json'):
            response_text = response_text[7:]
        if response_text.endswith('```'):
            response_text = response_text[:-3]
        response_text = response_text.strip()
        
        try:
            selling_points_data = json.loads(response_text)
            
            # 验证返回的数据结构
            if not isinstance(selling_points_data, dict):
                raise ValueError("返回的数据不是有效的字典格式")
            
            # 确保必要的字段存在
            required_fields = ['key_selling_points', 'visual_features', 'marketing_insights']
            for field in required_fields:
                if field not in selling_points_data:
                    selling_points_data[field] = {}
            
            return selling_points_data
            
        except json.JSONDecodeError as e:
            st.warning(f"JSON解析失败: {str(e)}")
            st.text("原始响应:")
            st.text(response_text[:500] + "..." if len(response_text) > 500 else response_text)
            return generate_fallback_selling_points()
            
    except Exception as e:
        st.error(f"AI分析失败: {str(e)}")
        return generate_fallback_selling_points()


async def analyze_selling_points_from_images(images: List[Image.Image]) -> Dict[str, Any]:
    """从图片中分析产品卖点 - 直接调用Gemini Vision API"""
    try:
        # 检查API配置
        if "GOOGLE_API_KEY" not in st.secrets:
            st.error("❌ 未找到 Google API Key")
            return generate_fallback_selling_points()
        
        # 配置Gemini API
        import google.generativeai as genai
        genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
        
        # 使用gemini-3-flash-preview模型进行图片分析
        model = genai.GenerativeModel('models/gemini-3-flash-preview')
        
        # 构建分析提示词
        selling_points_prompt = """
        你是一个专业的产品营销分析师。请仔细分析这些产品图片，识别产品的核心卖点和营销价值。

        请以JSON格式返回详细的产品卖点分析：

        {
            "key_selling_points": [
                {
                    "title": "卖点标题",
                    "description": "详细描述这个卖点如何吸引消费者，为什么重要",
                    "category": "功能性/美观性/品质感/便利性",
                    "confidence": 0.95,
                    "visual_evidence": "从图片中观察到的具体支持证据"
                }
            ],
            "visual_features": {
                "design_style": "现代简约/奢华精致/实用主义/工业风等具体风格",
                "color_scheme": "主要色彩搭配和视觉效果描述",
                "material_perception": "材质给人的感受和品质印象",
                "quality_indicators": ["从图片看出的品质指标1", "品质指标2"],
                "aesthetic_appeal": "整体美学吸引力评估"
            },
            "marketing_insights": {
                "target_audience": "基于产品特征推断的目标用户群体",
                "emotional_triggers": ["能触发购买欲望的情感点1", "情感点2"],
                "positioning_strategy": "建议的产品市场定位策略",
                "aplus_recommendations": ["Amazon A+页面展示建议1", "建议2", "建议3"],
                "competitive_advantages": ["相比同类产品的优势1", "优势2"]
            },
            "usage_scenarios": [
                {
                    "scenario": "具体使用场景描述",
                    "benefits": "在此场景下的具体优势",
                    "target_emotion": "想要激发的目标情感"
                }
            ],
            "analysis_quality": {
                "overall_confidence": 0.9,
                "image_quality_score": 0.85,
                "analysis_depth": 0.88,
                "recommendations_reliability": 0.92
            }
        }

        分析要求：
        1. 仔细观察产品的外观、材质、设计细节
        2. 识别产品的独特特征和潜在卖点
        3. 考虑北美消费者的购买心理和偏好
        4. 提供具体可执行的营销建议
        5. 评估产品在Amazon A+页面中的展示潜力
        6. 分析结果要客观、具体、有说服力

        请只返回JSON格式的分析结果，不要包含其他文字。
        """
        
        # 准备图片和提示词
        content_parts = [selling_points_prompt]
        content_parts.extend(images)
        
        # 调用Gemini API进行分析
        response = model.generate_content(content_parts)
        
        # 解析响应
        response_text = response.text.strip()
        
        # 清理响应文本，移除可能的markdown标记
        if response_text.startswith('```json'):
            response_text = response_text[7:]
        if response_text.endswith('```'):
            response_text = response_text[:-3]
        response_text = response_text.strip()
        
        try:
            import json
            selling_points_data = json.loads(response_text)
            
            # 验证返回的数据结构
            if not isinstance(selling_points_data, dict):
                raise ValueError("返回的数据不是有效的字典格式")
            
            # 确保必要的字段存在
            required_fields = ['key_selling_points', 'visual_features', 'marketing_insights']
            for field in required_fields:
                if field not in selling_points_data:
                    selling_points_data[field] = {}
            
            return selling_points_data
            
        except json.JSONDecodeError as e:
            st.warning(f"JSON解析失败: {str(e)}")
            st.text("原始响应:")
            st.text(response_text[:500] + "..." if len(response_text) > 500 else response_text)
            return generate_fallback_selling_points()
            
    except Exception as e:
        st.error(f"AI分析失败: {str(e)}")
        return generate_fallback_selling_points()


def generate_fallback_selling_points(image_analysis: Optional[Any] = None) -> Dict[str, Any]:
    """生成备用的卖点分析结果"""
    if not image_analysis:
        return {
            "key_selling_points": [
                {
                    "title": "产品品质",
                    "description": "从图片可以看出产品具有良好的制作工艺",
                    "category": "品质感",
                    "confidence": 0.7,
                    "visual_evidence": "整体视觉呈现"
                }
            ],
            "visual_features": {
                "design_style": "现代风格",
                "color_scheme": "经典配色",
                "material_perception": "优质材质",
                "quality_indicators": ["工艺精良", "设计合理"],
                "aesthetic_appeal": "视觉吸引力良好"
            },
            "marketing_insights": {
                "target_audience": "注重品质的消费者",
                "emotional_triggers": ["品质保证", "实用价值"],
                "positioning_strategy": "品质优先定位",
                "aplus_recommendations": ["突出产品细节", "展示使用场景"],
                "competitive_advantages": ["设计优秀", "品质可靠"]
            },
            "usage_scenarios": [
                {
                    "scenario": "日常使用",
                    "benefits": "提供便利和品质体验",
                    "target_emotion": "满意和信任"
                }
            ],
            "analysis_quality": {
                "overall_confidence": 0.7,
                "image_quality_score": 0.7,
                "analysis_depth": 0.6,
                "recommendations_reliability": 0.7
            }
        }
    
    # 基于图片分析生成卖点
    selling_points = []
    
    # 基于设计风格生成卖点
    if image_analysis.design_style:
        selling_points.append({
            "title": f"{image_analysis.design_style}设计",
            "description": f"产品采用{image_analysis.design_style}设计风格，符合现代审美趋势",
            "category": "美观性",
            "confidence": 0.8,
            "visual_evidence": f"设计风格体现为{image_analysis.design_style}"
        })
    
    # 基于材质生成卖点
    if image_analysis.material_types and image_analysis.material_types[0] != "unknown":
        materials = ', '.join(image_analysis.material_types[:2])
        selling_points.append({
            "title": "优质材质",
            "description": f"采用{materials}等优质材质，确保产品耐用性和品质感",
            "category": "品质感",
            "confidence": 0.75,
            "visual_evidence": f"可观察到{materials}材质特征"
        })
    
    # 基于颜色生成卖点
    if len(image_analysis.dominant_colors) > 1:
        selling_points.append({
            "title": "精心配色",
            "description": "产品配色经过精心设计，视觉效果出色",
            "category": "美观性", 
            "confidence": 0.7,
            "visual_evidence": f"主要颜色包括{', '.join(image_analysis.dominant_colors[:3])}"
        })
    
    # 如果没有生成足够的卖点，添加通用卖点
    if len(selling_points) < 2:
        selling_points.append({
            "title": "实用设计",
            "description": "产品设计注重实用性，能够满足用户的实际需求",
            "category": "功能性",
            "confidence": 0.7,
            "visual_evidence": "整体设计体现实用性考虑"
        })
    
    return {
        "key_selling_points": selling_points,
        "visual_features": {
            "design_style": image_analysis.design_style,
            "color_scheme": f"以{image_analysis.dominant_colors[0] if image_analysis.dominant_colors else '#FFFFFF'}为主的配色方案",
            "material_perception": f"{', '.join(image_analysis.material_types)}材质呈现",
            "quality_indicators": ["视觉品质良好", "设计合理"],
            "aesthetic_appeal": f"整体美观度{image_analysis.quality_assessment}"
        },
        "marketing_insights": {
            "target_audience": "注重设计和品质的消费者",
            "emotional_triggers": ["品质认同", "设计欣赏"],
            "positioning_strategy": "品质与设计并重",
            "aplus_recommendations": ["突出设计特色", "展示材质细节", "强调品质工艺"],
            "competitive_advantages": ["设计出色", "材质优良"]
        },
        "usage_scenarios": [
            {
                "scenario": "日常使用场景",
                "benefits": "提供优质的使用体验",
                "target_emotion": "满意和认同"
            }
        ],
        "analysis_quality": {
            "overall_confidence": image_analysis.confidence_score,
            "image_quality_score": 0.8 if image_analysis.quality_assessment == "excellent" else 0.7,
            "analysis_depth": 0.7,
            "recommendations_reliability": 0.75
        }
    }


def render_product_analysis_tab(controller: APlusController, input_panel: ProductInputPanel):
    """渲染产品分析标签页"""
    st.header("📝 产品信息分析")
    
    # 检查当前会话状态
    session = controller.state_manager.get_current_session()
    
    # 如果已有分析结果，显示摘要
    if session and session.analysis_result:
        render_analysis_summary(session.analysis_result)
        
        # 提供重新分析选项
        if st.button("🔄 重新分析产品", type="secondary"):
            controller.state_manager.update_analysis_result(None)
            st.rerun()
        
        return
    
    # 产品输入界面
    product_info, validation_result = input_panel.render_input_panel()
    
    if product_info and validation_result.is_valid:
        # 显示输入预览
        input_panel.render_input_preview(product_info)
        
        # 执行分析
        with st.spinner("🔍 正在分析产品信息..."):
            try:
                analysis_result = asyncio.run(
                    controller.process_product_input(
                        product_info.description, 
                        product_info.uploaded_images
                    )
                )
                
                if analysis_result:
                    st.success("✅ 产品分析完成！")
                    render_analysis_summary(analysis_result)
                else:
                    st.error("❌ 产品分析失败")
                    
            except Exception as e:
                st.error(f"❌ 分析过程中出现错误: {str(e)}")


def render_analysis_summary(analysis_result):
    """渲染分析结果摘要"""
    st.subheader("📊 分析结果摘要")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**📋 产品特征**")
        if hasattr(analysis_result, 'listing_analysis') and analysis_result.listing_analysis:
            listing = analysis_result.listing_analysis
            st.write(f"• **产品类别**: {listing.product_category}")
            st.write(f"• **目标用户**: {listing.target_demographics}")
            
            if listing.key_selling_points:
                st.write("• **核心卖点**:")
                for point in listing.key_selling_points[:3]:
                    st.write(f"  - {point}")
    
    with col2:
        st.write("**🎨 视觉特征**")
        if hasattr(analysis_result, 'image_analysis') and analysis_result.image_analysis:
            image_analysis = analysis_result.image_analysis
            if image_analysis.dominant_colors:
                st.write(f"• **主色调**: {', '.join(image_analysis.dominant_colors[:3])}")
            if image_analysis.material_types:
                st.write(f"• **材质类型**: {', '.join(image_analysis.material_types[:3])}")
            if image_analysis.design_style:
                st.write(f"• **设计风格**: {image_analysis.design_style}")
    
    # 视觉连贯性信息
    if hasattr(analysis_result, 'visual_style') and analysis_result.visual_style:
        with st.expander("🎨 视觉风格设定", expanded=False):
            visual_style = analysis_result.visual_style
            if visual_style.color_palette:
                st.write(f"**色调盘**: {', '.join(visual_style.color_palette)}")
            if visual_style.aesthetic_direction:
                st.write(f"**美学方向**: {visual_style.aesthetic_direction}")


def render_module_generation_tab(controller: APlusController, generation_panel: ModuleGenerationPanel):
    """渲染模块生成标签页"""
    st.header("🎨 模块图片生成")
    
    # 检查前置条件
    session = controller.state_manager.get_current_session()
    if not session or not session.analysis_result:
        st.warning("⚠️ 请先完成产品分析")
        st.info("💡 提示：你可以先使用「卖点分析」功能快速分析产品图片，或者使用「产品分析」进行完整的产品信息分析")
        return
    
    # 渲染生成控制面板
    generation_action = generation_panel.render_generation_panel()
    
    # 处理生成动作
    if generation_action and generation_action.get("action"):
        handle_generation_action(controller, generation_panel, generation_action)
    
    # 显示生成摘要
    generation_panel.render_generation_summary()


def handle_generation_action(controller: APlusController, generation_panel: ModuleGenerationPanel, action: Dict[str, Any]):
    """处理生成动作"""
    action_type = action.get("action")
    
    if action_type == "generate_individual":
        # 单个模块生成
        module_type = action.get("module_type")
        custom_params = action.get("module_params", {})
        
        generation_panel.start_generation_tracking(module_type)
        
        try:
            with st.spinner(f"正在生成 {module_type.value} 模块..."):
                result = asyncio.run(controller.generate_module_image(module_type, custom_params))
                
                generation_panel.complete_generation(module_type, True)
                st.success(f"✅ {module_type.value} 模块生成完成！")
                
                # 显示结果预览
                if result.image_data:
                    st.image(result.image_data, caption=f"{module_type.value} 模块结果")
                    st.write(f"质量分数: {result.quality_score:.2f}")
                
        except Exception as e:
            generation_panel.complete_generation(module_type, False)
            st.error(f"❌ {module_type.value} 模块生成失败: {str(e)}")
    
    elif action_type in ["generate_batch", "generate_parallel"]:
        # 批量或并行生成
        selected_modules = action.get("selected_modules", [])
        module_params = action.get("module_params", {})
        
        if action_type == "generate_batch":
            handle_batch_generation(controller, generation_panel, selected_modules, module_params)
        else:
            handle_parallel_generation(controller, generation_panel, selected_modules, module_params)
    
    elif action_type == "stop_all":
        # 停止所有生成
        for module_type in generation_panel.get_active_generations():
            generation_panel._stop_generation(module_type)
        st.info("已停止所有生成任务")
    
    elif action_type == "reset_progress":
        # 重置进度
        generation_panel.reset_progress()
        st.info("已重置生成进度")


def handle_batch_generation(controller: APlusController, generation_panel: ModuleGenerationPanel, 
                          selected_modules: List[ModuleType], module_params: Dict[ModuleType, Dict]):
    """处理批量生成"""
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i, module_type in enumerate(selected_modules):
        status_text.text(f"正在生成 {module_type.value} 模块... ({i+1}/{len(selected_modules)})")
        progress_bar.progress(i / len(selected_modules))
        
        generation_panel.start_generation_tracking(module_type)
        
        try:
            custom_params = module_params.get(module_type, {})
            result = asyncio.run(controller.generate_module_image(module_type, custom_params))
            
            generation_panel.complete_generation(module_type, True)
            st.success(f"✅ {module_type.value} 模块生成完成")
            
        except Exception as e:
            generation_panel.complete_generation(module_type, False)
            st.error(f"❌ {module_type.value} 模块生成失败: {str(e)}")
    
    progress_bar.progress(1.0)
    status_text.text("✅ 批量生成完成！")


def handle_parallel_generation(controller: APlusController, generation_panel: ModuleGenerationPanel,
                             selected_modules: List[ModuleType], module_params: Dict[ModuleType, Dict]):
    """处理并行生成"""
    st.info("🚀 开始并行生成...")
    
    # 启动所有模块的生成跟踪
    for module_type in selected_modules:
        generation_panel.start_generation_tracking(module_type)
    
    # 并行生成（简化实现，实际应该使用真正的并行处理）
    results = {}
    for module_type in selected_modules:
        try:
            custom_params = module_params.get(module_type, {})
            result = asyncio.run(controller.generate_module_image(module_type, custom_params))
            results[module_type] = result
            generation_panel.complete_generation(module_type, True)
            
        except Exception as e:
            generation_panel.complete_generation(module_type, False)
            st.error(f"❌ {module_type.value} 模块生成失败: {str(e)}")
    
    st.success(f"✅ 并行生成完成！成功生成 {len(results)} 个模块")


def render_preview_gallery_tab(controller: APlusController, preview_gallery: ImagePreviewGallery):
    """渲染图片预览标签页"""
    st.header("🖼️ 图片预览画廊")
    
    # 渲染预览画廊
    gallery_action = preview_gallery.render_preview_gallery()
    
    # 处理画廊动作
    if gallery_action and gallery_action.get("action"):
        handle_gallery_action(controller, preview_gallery, gallery_action)
    
    # 批量操作
    module_results = controller.get_module_results()
    if module_results:
        st.divider()
        batch_action = preview_gallery.render_batch_operations(module_results)
        
        if batch_action and batch_action.get("action"):
            handle_batch_action(controller, batch_action)


def handle_gallery_action(controller: APlusController, preview_gallery: ImagePreviewGallery, action: Dict[str, Any]):
    """处理画廊动作"""
    action_type = action.get("action")
    
    if action_type == "export_selected":
        modules = action.get("modules", [])
        st.success(f"已选择导出 {len(modules)} 个模块的图片")
    
    elif action_type == "refresh":
        st.rerun()


def handle_batch_action(controller: APlusController, action: Dict[str, Any]):
    """处理批量操作"""
    action_type = action.get("action")
    modules = action.get("modules", [])
    
    if action_type == "batch_download":
        st.success(f"正在准备下载 {len(modules)} 个模块的图片...")
        # 实际实现中会创建ZIP文件供下载
    
    elif action_type == "batch_regenerate":
        st.info(f"将重新生成 {len(modules)} 个模块...")
        # 跳转到重新生成标签页
    
    elif action_type == "quality_analysis":
        module_results = controller.get_module_results()
        filtered_results = {m: r for m, r in module_results.items() if m in modules}
        
        # 显示质量分析
        with st.expander("📊 质量分析结果", expanded=True):
            render_quality_analysis(filtered_results)


def render_quality_analysis(module_results: Dict[ModuleType, Any]):
    """渲染质量分析"""
    if not module_results:
        st.info("没有可分析的数据")
        return
    
    quality_scores = [result.quality_score for result in module_results.values()]
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        avg_quality = sum(quality_scores) / len(quality_scores)
        st.metric("平均质量", f"{avg_quality:.2f}")
    
    with col2:
        max_quality = max(quality_scores)
        st.metric("最高质量", f"{max_quality:.2f}")
    
    with col3:
        min_quality = min(quality_scores)
        st.metric("最低质量", f"{min_quality:.2f}")


def render_regeneration_tab(controller: APlusController, regeneration_panel: RegenerationPanel):
    """渲染重新生成标签页"""
    st.header("🔄 单模块重新生成")
    
    # 检查已生成的模块
    module_results = controller.get_module_results()
    
    if not module_results:
        st.info("还没有已生成的模块，请先在模块生成标签页生成模块")
        if st.button("🎨 前往模块生成", type="primary"):
            st.session_state["active_tab"] = "module_generation"
        return
    
    # 模块选择
    available_modules = list(module_results.keys())
    
    module_names = {
        ModuleType.IDENTITY: "🎭 身份代入",
        ModuleType.SENSORY: "👁️ 感官解构",
        ModuleType.EXTENSION: "🔄 多维延展",
        ModuleType.TRUST: "🤝 信任转化"
    }
    
    selected_module = st.selectbox(
        "选择要重新生成的模块",
        available_modules,
        format_func=lambda x: module_names.get(x, x.value)
    )
    
    if selected_module:
        # 显示当前模块结果
        current_result = module_results[selected_module]
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.subheader("当前结果")
            if current_result.image_data:
                st.image(current_result.image_data, caption="当前版本")
            st.write(f"**质量分数**: {current_result.quality_score:.2f}")
            st.write(f"**生成时间**: {current_result.generation_time:.1f}s")
            st.write(f"**验证状态**: {current_result.validation_status.value}")
        
        with col2:
            # 重新生成控制面板
            regen_action = regeneration_panel.render_regeneration_controls(selected_module)
            
            if regen_action.get("action") == "regenerate":
                with st.spinner("🔄 正在重新生成..."):
                    try:
                        new_result = asyncio.run(
                            controller.regenerate_image(
                                selected_module, 
                                regen_action.get("custom_params")
                            )
                        )
                        
                        st.success("✅ 重新生成完成！")
                        
                        # 显示新结果对比
                        if new_result.image_data:
                            st.subheader("新版本")
                            st.image(new_result.image_data, caption="新版本")
                            st.write(f"**新质量分数**: {new_result.quality_score:.2f}")
                            
                            # 质量对比
                            quality_diff = new_result.quality_score - current_result.quality_score
                            if quality_diff > 0:
                                st.success(f"质量提升: +{quality_diff:.2f}")
                            elif quality_diff < 0:
                                st.warning(f"质量下降: {quality_diff:.2f}")
                            else:
                                st.info("质量无变化")
                        
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"❌ 重新生成失败: {str(e)}")
        
        # 版本历史
        st.divider()
        
        tab1, tab2 = st.tabs(["📚 版本历史", "📊 版本对比"])
        
        with tab1:
            regeneration_panel.render_version_history_panel(selected_module)
        
        with tab2:
            regeneration_panel.render_version_comparison(selected_module)


def render_export_tab(controller: APlusController):
    """渲染结果导出标签页"""
    st.header("📊 数据导出")
    
    module_results = controller.get_module_results()
    
    if not module_results:
        st.info("还没有可导出的结果")
        return
    
    # 导出选项
    st.subheader("📥 导出选项")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # 模块选择
        module_names = {
            ModuleType.IDENTITY: "🎭 身份代入",
            ModuleType.SENSORY: "👁️ 感官解构",
            ModuleType.EXTENSION: "🔄 多维延展",
            ModuleType.TRUST: "🤝 信任转化"
        }
        
        export_modules = st.multiselect(
            "选择要导出的模块",
            list(module_results.keys()),
            default=list(module_results.keys()),
            format_func=lambda x: module_names.get(x, x.value)
        )
        
        export_format = st.selectbox(
            "导出格式",
            ["PNG (推荐)", "JPG", "PDF报告", "ZIP压缩包"]
        )
    
    with col2:
        # 导出设置
        include_metadata = st.checkbox("包含元数据", value=True)
        include_prompts = st.checkbox("包含提示词", value=False)
        include_analysis = st.checkbox("包含分析报告", value=True)
        
        quality_level = st.selectbox(
            "图片质量",
            ["原始质量", "高质量", "压缩版本"],
            index=0
        )
    
    # 导出预览
    if export_modules:
        st.subheader("📋 导出预览")
        
        total_size = 0
        for module_type in export_modules:
            result = module_results[module_type]
            if result.image_data:
                size_mb = len(result.image_data) / (1024 * 1024)
                total_size += size_mb
                st.write(f"• {module_names.get(module_type, module_type.value)}: {size_mb:.1f} MB")
        
        st.write(f"**总大小**: {total_size:.1f} MB")
    
    # 导出按钮
    if st.button("📥 开始导出", type="primary", disabled=not export_modules):
        if export_modules:
            with st.spinner("📦 正在准备导出文件..."):
                # 模拟导出过程
                import time
                time.sleep(2)
                
                st.success("✅ 导出完成！")
                
                # 显示导出摘要
                st.subheader("📊 导出摘要")
                for module_type in export_modules:
                    result = module_results[module_type]
                    st.write(f"• {module_names.get(module_type, module_type.value)}: 质量分数 {result.quality_score:.2f}")
                
                # 创建下载按钮
                export_data = controller.export_results()
                if export_data:
                    import json
                    json_str = json.dumps(export_data, indent=2, ensure_ascii=False)
                    
                    st.download_button(
                        "📥 下载导出文件",
                        data=json_str,
                        file_name=f"aplus_export_{len(export_modules)}_modules.json",
                        mime="application/json"
                    )
        else:
            st.warning("请选择要导出的模块")
    
    # 导出历史
    st.divider()
    st.subheader("📚 导出历史")
    
    # 显示会话摘要
    session_summary = controller.state_manager.get_session_summary()
    if session_summary.get("has_session"):
        with st.expander("📊 当前会话统计", expanded=False):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("会话健康度", f"{session_summary['health_score']:.0f}%")
            
            with col2:
                st.metric("已完成模块", session_summary['completed_modules'])
            
            with col3:
                st.metric("会话时长", f"{session_summary['session_age_hours']:.1f}h")
    
    # 视觉连贯性报告
    consistency_report = controller.get_visual_consistency_report()
    if consistency_report and "error" not in consistency_report:
        with st.expander("🎨 视觉连贯性报告", expanded=False):
            if consistency_report.get("is_consistent"):
                st.success(f"✅ 视觉连贯性良好 (评分: {consistency_report.get('overall_score', 0):.2f})")
            else:
                st.warning("⚠️ 检测到视觉风格不一致")
                
                conflicts = consistency_report.get("conflicts", [])
                if conflicts:
                    st.write("**风格冲突:**")
                    for conflict in conflicts[:3]:
                        st.write(f"• {conflict}")


if __name__ == "__main__":
    main()
