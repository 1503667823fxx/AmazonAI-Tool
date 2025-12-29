import streamlit as st
import sys
import os
from datetime import datetime
import asyncio
import json

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

st.set_page_config(
    page_title="🧪 图片数据测试",
    page_icon="🧪",
    layout="wide"
)

def main():
    st.title("🧪 图片数据测试页面")
    st.markdown("专门测试真实图片生成和状态转换问题")
    
    # 检查URL参数
    url_step = st.query_params.get("step")
    
    # 显示当前状态
    with st.expander("🔍 当前状态信息", expanded=True):
        st.write(f"**URL参数**: {dict(st.query_params)}")
        st.write(f"**Session State Keys**: {list(st.session_state.keys())}")
        
        if 'test_generated_images' in st.session_state:
            images_data = st.session_state.test_generated_images
            st.write(f"**生成的图片数据**: {len(images_data)} 个模块")
            
            # 显示数据大小信息
            total_size = 0
            for module_key, data in images_data.items():
                if isinstance(data, dict):
                    # 估算数据大小
                    data_str = str(data)
                    size_kb = len(data_str.encode('utf-8')) / 1024
                    total_size += size_kb
                    st.write(f"  - {module_key}: ~{size_kb:.1f} KB")
            
            st.write(f"**总数据大小**: ~{total_size:.1f} KB")
        else:
            st.write("**生成的图片数据**: 无")
    
    # 根据URL参数决定显示内容
    if url_step == "completed":
        render_test_results()
    else:
        render_test_controls()

def render_test_controls():
    """渲染测试控制界面"""
    st.subheader("🎮 测试控制面板")
    
    # 测试模式选择
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📊 模拟数据测试")
        st.info("使用模拟数据测试状态转换（已知可以工作）")
        
        if st.button("🎯 生成模拟数据", type="secondary", use_container_width=True):
            # 创建模拟数据
            mock_data = {
                'PRODUCT_OVERVIEW': {
                    'image_path': 'mock/product_overview.png',
                    'generation_time': 2.3,
                    'quality_score': 0.92,
                    'success': True,
                    'has_image_data': True,
                    'module_name': 'Product Overview',
                    'generated_at': datetime.now().isoformat(),
                    'is_mock': True
                },
                'PROBLEM_SOLUTION': {
                    'image_path': 'mock/problem_solution.png',
                    'generation_time': 1.8,
                    'quality_score': 0.88,
                    'success': True,
                    'has_image_data': True,
                    'module_name': 'Problem Solution',
                    'generated_at': datetime.now().isoformat(),
                    'is_mock': True
                }
            }
            
            st.session_state.test_generated_images = mock_data
            st.session_state.test_data_type = "mock"
            st.success("✅ 模拟数据已生成")
            st.rerun()
    
    with col2:
        st.markdown("### 🖼️ 真实数据测试")
        st.warning("使用真实API生成图片数据（可能导致问题）")
        
        # 图片数量选择
        num_images = st.selectbox("选择生成图片数量", [1, 2, 4], index=0)
        
        if st.button("🚀 生成真实图片", type="primary", use_container_width=True):
            generate_real_images(num_images)
    
    # 状态转换测试区域
    if 'test_generated_images' in st.session_state:
        st.markdown("---")
        st.subheader("🔄 状态转换测试")
        
        data_type = st.session_state.get('test_data_type', 'unknown')
        st.info(f"当前数据类型: **{data_type}**")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("📊 查看结果（URL跳转）", type="primary", use_container_width=True):
                # 设置URL参数跳转
                timestamp = str(int(datetime.now().timestamp()))
                st.query_params.update({"step": "completed", "t": timestamp})
                st.info("🔄 正在跳转到结果页面...")
                st.rerun()
        
        with col2:
            if st.button("🔍 直接显示结果", type="secondary", use_container_width=True):
                # 直接显示结果，不跳转
                st.session_state.show_results_inline = True
                st.rerun()
        
        with col3:
            if st.button("🗑️ 清除数据", type="secondary", use_container_width=True):
                # 清除测试数据
                if 'test_generated_images' in st.session_state:
                    del st.session_state.test_generated_images
                if 'test_data_type' in st.session_state:
                    del st.session_state.test_data_type
                if 'show_results_inline' in st.session_state:
                    del st.session_state.show_results_inline
                st.query_params.clear()
                st.success("✅ 数据已清除")
                st.rerun()
    
    # 内联结果显示
    if st.session_state.get('show_results_inline', False):
        st.markdown("---")
        st.subheader("📋 内联结果显示")
        display_results_inline()

def generate_real_images(num_images):
    """生成真实图片数据"""
    try:
        st.info(f"🚀 开始生成 {num_images} 张真实图片...")
        
        # 导入必要的服务
        from services.aplus_studio.enhanced_batch_image_service import EnhancedAPlusBatchService
        from services.aplus_studio.models import ModuleType
        
        # 创建测试用的内容数据
        test_modules = list(ModuleType)[:num_images]  # 取前N个模块类型
        
        final_content = {}
        for i, module_type in enumerate(test_modules):
            final_content[module_type.value] = {
                'title': f'测试模块 {i+1}',
                'description': f'这是第 {i+1} 个测试模块的描述',
                'key_points': [f'特点 {i+1}.1', f'特点 {i+1}.2', f'特点 {i+1}.3'],
                'generated_text': {'main_content': f'测试内容 {i+1}'},
                'material_requests': []
            }
        
        # 创建风格主题
        style_theme = {
            'theme_name': '测试风格',
            'theme_config': {
                'colors': ['蓝色', '白色', '灰色'],
                'description': '简洁测试风格'
            }
        }
        
        # 使用进度条显示生成过程
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        def update_progress(current, total, message=""):
            progress = current / total
            progress_bar.progress(progress)
            status_text.text(f"进度: {current}/{total} - {message}")
        
        # 调用真实的图片生成服务
        batch_service = EnhancedAPlusBatchService()
        
        with st.spinner("正在生成真实图片..."):
            results = batch_service.generate_batch_sync(
                final_content=final_content,
                style_theme=style_theme,
                progress_callback=update_progress
            )
        
        # 清除进度显示
        progress_bar.empty()
        status_text.empty()
        
        if results:
            st.session_state.test_generated_images = results
            st.session_state.test_data_type = "real"
            st.success(f"✅ 成功生成 {len(results)} 张真实图片")
            
            # 显示生成结果摘要
            with st.expander("📊 生成结果摘要", expanded=True):
                for module_key, result in results.items():
                    if isinstance(result, dict):
                        success = result.get('success', False)
                        quality = result.get('quality_score', 0)
                        gen_time = result.get('generation_time', 0)
                        
                        status_icon = "✅" if success else "❌"
                        st.write(f"{status_icon} **{module_key}**: 质量 {quality:.1%}, 用时 {gen_time:.1f}s")
            
            st.rerun()
        else:
            st.error("❌ 图片生成失败")
            
    except Exception as e:
        st.error(f"❌ 生成过程中出错: {str(e)}")
        st.exception(e)

def render_test_results():
    """渲染测试结果页面"""
    st.subheader("🎉 测试结果页面")
    st.success("✅ 状态转换成功！你现在在结果页面")
    
    # 显示跳转成功信息
    st.info("🎯 **关键发现**: URL参数跳转成功，页面正确显示结果页面")
    
    # 检查数据是否还存在
    if 'test_generated_images' in st.session_state:
        images_data = st.session_state.test_generated_images
        data_type = st.session_state.get('test_data_type', 'unknown')
        
        st.success(f"✅ 数据完整性检查通过 - {len(images_data)} 个模块数据存在")
        st.info(f"📊 数据类型: **{data_type}**")
        
        # 显示详细结果
        display_results_inline()
        
    else:
        st.error("❌ 数据丢失！图片数据在页面跳转后消失了")
        st.warning("这可能是导致原始问题的根本原因")
    
    # 返回按钮
    st.markdown("---")
    if st.button("🔙 返回测试控制面板", type="secondary"):
        st.query_params.clear()
        st.rerun()

def display_results_inline():
    """内联显示结果"""
    if 'test_generated_images' not in st.session_state:
        st.warning("没有图片数据可显示")
        return
    
    images_data = st.session_state.test_generated_images
    data_type = st.session_state.get('test_data_type', 'unknown')
    
    st.markdown(f"### 📋 生成结果 ({data_type} 数据)")
    
    for module_key, result in images_data.items():
        with st.expander(f"📋 {module_key}", expanded=True):
            if isinstance(result, dict):
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    success = result.get('success', False)
                    st.metric("状态", "成功" if success else "失败")
                
                with col2:
                    quality = result.get('quality_score', 0)
                    st.metric("质量评分", f"{quality:.1%}")
                
                with col3:
                    gen_time = result.get('generation_time', 0)
                    st.metric("生成时间", f"{gen_time:.1f}s")
                
                # 显示详细信息
                st.json(result)
            else:
                st.write("数据格式异常:", type(result))

if __name__ == "__main__":
    main()