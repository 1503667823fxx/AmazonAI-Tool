"""
独立的结果页面测试模块
用于测试"查看生成结果"功能，包含虚拟数据
可以独立运行，方便测试和删除
"""

import streamlit as st
import sys
import os
from datetime import datetime
import logging

# 添加项目根目录到路径
sys.path.append(os.path.abspath('.'))

logger = logging.getLogger(__name__)

# 页面配置
st.set_page_config(
    page_title="结果页面测试", 
    page_icon="🧪", 
    layout="wide"
)

def create_mock_data():
    """创建虚拟测试数据"""
    return {
        'PRODUCT_OVERVIEW': {
            'image_path': 'mock/product_overview.png',
            'generation_time': 3.2,
            'quality_score': 0.92,
            'is_mock': True,
            'has_image_data': True,
            'image_data_size': 1024000,
            'module_name': '产品概览',
            'description': '展示产品的核心价值和主要特性'
        },
        'FEATURE_ANALYSIS': {
            'image_path': 'mock/feature_analysis.png',
            'generation_time': 2.8,
            'quality_score': 0.88,
            'is_mock': True,
            'has_image_data': True,
            'image_data_size': 896000,
            'module_name': '功能解析',
            'description': '详细分析产品的各项功能特点'
        },
        'USAGE_SCENARIOS': {
            'image_path': 'mock/usage_scenarios.png',
            'generation_time': 3.5,
            'quality_score': 0.90,
            'is_mock': True,
            'has_image_data': True,
            'image_data_size': 1152000,
            'module_name': '使用场景',
            'description': '展示产品在实际使用中的应用场景'
        },
        'QUALITY_ASSURANCE': {
            'image_path': 'mock/quality_assurance.png',
            'generation_time': 2.9,
            'quality_score': 0.85,
            'is_mock': True,
            'has_image_data': True,
            'image_data_size': 768000,
            'module_name': '品质保证',
            'description': '通过认证和保修信息建立品质信任'
        }
    }

def render_test_results_page():
    """渲染测试结果页面"""
    st.title("🧪 结果页面功能测试")
    st.caption("独立测试模块 - 用于验证查看生成结果功能")
    
    # 控制面板
    with st.sidebar:
        st.header("🎛️ 测试控制")
        
        # 数据状态控制
        st.subheader("数据状态")
        has_data = st.checkbox("模拟有生成数据", value=True)
        
        if has_data:
            data_source = st.selectbox(
                "数据来源",
                ["主数据源", "元数据源", "临时数据源", "无数据源"]
            )
        else:
            data_source = "无数据源"
        
        # 错误模拟
        st.subheader("错误模拟")
        simulate_error = st.checkbox("模拟数据丢失错误")
        
        # 重置按钮
        if st.button("🔄 重置测试", type="secondary"):
            # 清除session state中的测试数据
            for key in list(st.session_state.keys()):
                if key.startswith('test_'):
                    del st.session_state[key]
            st.rerun()
    
    # 主要内容区域
    st.markdown("---")
    
    if simulate_error or not has_data:
        render_no_data_scenario(data_source)
    else:
        render_with_data_scenario(data_source)

def render_with_data_scenario(data_source):
    """渲染有数据的场景"""
    st.subheader("🎉 智能工作流完成！")
    st.markdown("恭喜！您的A+页面已经生成完成")
    
    # 获取虚拟数据
    generated_images = create_mock_data()
    
    # 显示数据来源信息
    st.info(f"📊 当前数据来源: {data_source} (共 {len(generated_images)} 个模块)")
    
    # 显示调试信息
    with st.expander("🔧 数据恢复调试信息", expanded=False):
        st.write("**测试环境信息**:")
        st.write(f"- 数据来源: {data_source}")
        st.write(f"- 生成图片数据: 存在")
        st.write(f"- 图片数量: {len(generated_images)}")
        st.write(f"- 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        st.write("**数据源检查**:")
        st.write(f"- state_manager.get_generated_images(): {'有数据' if data_source == '主数据源' else '无数据'}")
        st.write(f"- session.workflow_metadata.generated_images: {'有数据' if data_source == '元数据源' else '无数据'}")
        st.write(f"- session._temp_generated_images: {'有数据' if data_source == '临时数据源' else '无数据'}")
        st.write(f"- session.generation_results: 无数据")
    
    # 显示生成的模块列表
    st.success(f"**生成结果**: 成功生成 {len(generated_images)} 个A+模块")
    
    for module_key, result in generated_images.items():
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            module_name = result.get('module_name', module_key.replace('_', ' ').title())
            st.write(f"📋 {module_name}")
            if result.get('description'):
                st.caption(result['description'])
        
        with col2:
            quality_score = result.get('quality_score', 0.0)
            st.write(f"质量: {quality_score:.1%}")
            if result.get('is_mock'):
                st.caption("🧪 测试数据")
        
        with col3:
            if st.button(f"下载", key=f"download_{module_key}"):
                if result.get('has_image_data'):
                    st.success(f"开始下载 {module_name}")
                    st.balloons()
                else:
                    st.warning("图片数据不可用")
    
    # 批量操作
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📦 批量下载", use_container_width=True):
            st.success("开始批量下载...")
            st.balloons()
    
    with col2:
        if st.button("🔄 重新生成", use_container_width=True):
            st.info("跳转到图片生成步骤...")
            st.rerun()
    
    with col3:
        if st.button("🆕 新建项目", use_container_width=True):
            st.info("开始新项目...")
            st.rerun()
    
    # 测试和调试区域
    st.markdown("---")
    st.markdown("**🧪 测试和调试区域**")
    test_col1, test_col2 = st.columns(2)
    
    with test_col1:
        if st.button("🔍 检查所有数据源", use_container_width=True):
            st.write("**数据源检查结果：**")
            st.write(f"- 主数据源: {'✅ 有数据' if data_source == '主数据源' else '❌ 无数据'}")
            if data_source == '主数据源':
                st.write(f"  数量: {len(generated_images)}")
            
            st.write(f"- 元数据源: {'✅ 有数据' if data_source == '元数据源' else '❌ 无数据'}")
            if data_source == '元数据源':
                st.write(f"  数量: {len(generated_images)}")
            
            st.write(f"- 临时数据源: {'✅ 有数据' if data_source == '临时数据源' else '❌ 无数据'}")
            if data_source == '临时数据源':
                st.write(f"  数量: {len(generated_images)}")
    
    with test_col2:
        if st.button("🔄 强制恢复数据", use_container_width=True):
            if data_source != "无数据源":
                st.success(f"✅ 从{data_source}恢复了 {len(generated_images)} 个图片")
                st.rerun()
            else:
                st.warning("⚠️ 没有找到可恢复的数据")

def render_no_data_scenario(data_source):
    """渲染无数据的场景"""
    st.subheader("🎉 智能工作流完成！")
    st.markdown("恭喜！您的A+页面已经生成完成")
    
    # 显示调试信息
    with st.expander("🔧 数据恢复调试信息", expanded=True):
        st.write("**测试环境信息**:")
        st.write(f"- 数据来源: {data_source}")
        st.write(f"- 生成图片数据: 不存在")
        st.write(f"- 图片数量: 0")
        st.write(f"- 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        st.write("**数据源检查**:")
        st.write("- state_manager.get_generated_images(): 无数据")
        st.write("- session.workflow_metadata.generated_images: 无数据")
        st.write("- session._temp_generated_images: 无数据")
        st.write("- session.generation_results: 无数据")
    
    # 错误信息
    st.error("❌ 没有找到生成的图片数据")
    
    st.warning("**可能的原因：**")
    st.write("1. 图片生成过程中出现错误")
    st.write("2. 页面刷新导致数据丢失")
    st.write("3. Session状态管理问题")
    st.write("4. 序列化过程中数据丢失")
    
    st.info("请返回上一步重新生成图片")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🔙 返回图片生成", use_container_width=True):
            st.info("跳转到图片生成步骤...")
            st.rerun()
    
    with col2:
        if st.button("🔄 尝试恢复数据", use_container_width=True):
            # 模拟恢复尝试
            st.info("正在尝试恢复数据...")
            
            # 模拟恢复失败
            st.warning("⚠️ 没有找到可恢复的数据")
            
            # 提供手动恢复选项
            if st.button("🧪 加载测试数据", key="load_test_data"):
                st.session_state.test_force_data = True
                st.success("✅ 已加载测试数据")
                st.rerun()

def main():
    """主函数"""
    try:
        render_test_results_page()
        
        # 页面底部信息
        st.markdown("---")
        st.caption("🧪 这是一个独立的测试页面，用于验证结果页面功能")
        st.caption("📝 测试完成后可以直接删除此文件")
        
    except Exception as e:
        st.error(f"测试页面运行错误: {str(e)}")
        st.code(str(e))

if __name__ == "__main__":
    main()
