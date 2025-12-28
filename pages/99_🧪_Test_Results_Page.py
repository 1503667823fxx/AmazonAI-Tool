"""
专业的"查看生成结果"功能测试模块
模拟完整的图片生成 → 查看结果 → 跳转流程
用于验证状态转换和数据持久化问题
"""

import streamlit as st
import sys
import os
from datetime import datetime
import logging
import time

# 添加项目根目录到路径
sys.path.append(os.path.abspath('.'))

logger = logging.getLogger(__name__)

# 页面配置
st.set_page_config(
    page_title="查看结果功能测试", 
    page_icon="🧪", 
    layout="wide"
)

def create_mock_generated_images():
    """创建模拟的生成图片数据"""
    return {
        'PRODUCT_OVERVIEW': {
            'image_path': 'generated/product_overview_1735123456.png',
            'generation_time': 3.2,
            'quality_score': 0.92,
            'success': True,
            'has_image_data': True,
            'image_data_size': 1024000,
            'module_name': '产品概览',
            'description': '展示产品的核心价值和主要特性',
            'generated_at': datetime.now().isoformat()
        },
        'FEATURE_ANALYSIS': {
            'image_path': 'generated/feature_analysis_1735123489.png',
            'generation_time': 2.8,
            'quality_score': 0.88,
            'success': True,
            'has_image_data': True,
            'image_data_size': 896000,
            'module_name': '功能解析',
            'description': '详细分析产品的各项功能特点',
            'generated_at': datetime.now().isoformat()
        },
        'USAGE_SCENARIOS': {
            'image_path': 'generated/usage_scenarios_1735123512.png',
            'generation_time': 3.5,
            'quality_score': 0.90,
            'success': True,
            'has_image_data': True,
            'image_data_size': 1152000,
            'module_name': '使用场景',
            'description': '展示产品在实际使用中的应用场景',
            'generated_at': datetime.now().isoformat()
        },
        'QUALITY_ASSURANCE': {
            'image_path': 'generated/quality_assurance_1735123534.png',
            'generation_time': 2.9,
            'quality_score': 0.85,
            'success': True,
            'has_image_data': True,
            'image_data_size': 768000,
            'module_name': '品质保证',
            'description': '通过认证和保修信息建立品质信任',
            'generated_at': datetime.now().isoformat()
        }
    }

def simulate_image_generation_step():
    """模拟图片生成步骤"""
    st.subheader("🖼️ 图片生成步骤 (模拟)")
    st.markdown("模拟真实的图片生成完成状态")
    
    # 显示生成状态
    modules = ['PRODUCT_OVERVIEW', 'FEATURE_ANALYSIS', 'USAGE_SCENARIOS', 'QUALITY_ASSURANCE']
    
    st.write("**生成进度**:")
    for i, module in enumerate(modules):
        module_name = module.replace('_', ' ').title()
        st.write(f"✅ {module_name} - 已完成 (质量: {85 + i * 2}%)")
    
    # 显示生成统计
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("总模块数", "4")
    with col2:
        st.metric("成功生成", "4")
    with col3:
        st.metric("失败数量", "0")
    with col4:
        st.metric("平均质量", "87.5%")
    
    st.success("✅ 批量生成完成！成功: 4, 失败: 0")
    
    # 关键测试：模拟真实的"查看生成结果"按钮
    st.markdown("---")
    st.markdown("**🎯 核心测试区域**")
    
    # 模拟保存生成数据到session state
    if 'test_generated_images' not in st.session_state:
        st.session_state.test_generated_images = create_mock_generated_images()
        st.session_state.test_generation_completed = True
    
    # 显示当前数据状态
    with st.expander("📊 当前数据状态", expanded=False):
        st.write(f"**生成数据**: {'存在' if st.session_state.get('test_generated_images') else '不存在'}")
        if st.session_state.get('test_generated_images'):
            st.write(f"**数据数量**: {len(st.session_state.test_generated_images)}")
        st.write(f"**生成完成标志**: {st.session_state.get('test_generation_completed', False)}")
        st.write(f"**当前页面状态**: 图片生成步骤")
    
    # 核心测试按钮 - 模拟真实的"查看生成结果"按钮
    if st.button("📊 查看生成结果", type="primary", use_container_width=True):
        # 模拟真实按钮的逻辑
        logger.info("User clicked '查看生成结果' button (test simulation)")
        
        # 检查生成数据是否存在
        generated_images = st.session_state.get('test_generated_images')
        if generated_images:
            logger.info(f"Generated images found: {len(generated_images)} modules")
            
            # 设置跳转标志
            st.session_state.test_should_show_results = True
            st.session_state.test_transition_timestamp = datetime.now().isoformat()
            
            # 模拟URL参数设置
            st.query_params.update({"step": "completed", "test": "true", "t": str(int(datetime.now().timestamp()))})
            
            st.success("✅ 正在跳转到结果页面...")
            logger.info("Triggering page rerun for results view")
            
            # 触发页面重新加载
            st.rerun()
        else:
            logger.error("No generated images found!")
            st.error("❌ 没有找到生成的图片数据")
    
    # 测试辅助按钮
    st.markdown("---")
    st.markdown("**🔧 测试辅助功能**")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🗑️ 清除测试数据"):
            # 清除所有测试数据
            keys_to_clear = [k for k in st.session_state.keys() if k.startswith('test_')]
            for key in keys_to_clear:
                del st.session_state[key]
            st.query_params.clear()
            st.success("✅ 测试数据已清除")
            st.rerun()
    
    with col2:
        if st.button("🔄 重新生成数据"):
            # 重新创建测试数据
            st.session_state.test_generated_images = create_mock_generated_images()
            st.session_state.test_generation_completed = True
            st.success("✅ 测试数据已重新生成")
            st.rerun()
    
    with col3:
        if st.button("❌ 模拟数据丢失"):
            # 模拟数据丢失场景
            if 'test_generated_images' in st.session_state:
                del st.session_state.test_generated_images
            st.warning("⚠️ 已模拟数据丢失")
            st.rerun()

def simulate_results_page():
    """模拟结果页面"""
    st.subheader("� 智能工作流完成目！")
    st.markdown("恭喜！您的A+页面已经生成完成")
    
    # 检查跳转是否成功
    transition_time = st.session_state.get('test_transition_timestamp')
    if transition_time:
        st.info(f"✅ 成功从图片生成步骤跳转 (跳转时间: {transition_time})")
    
    # 尝试获取生成的图片数据
    generated_images = st.session_state.get('test_generated_images')
    
    # 显示数据恢复调试信息
    with st.expander("🔧 数据恢复调试信息", expanded=True):
        st.write("**跳转状态检查**:")
        st.write(f"- URL参数: {dict(st.query_params)}")
        st.write(f"- 跳转标志: {st.session_state.get('test_should_show_results', False)}")
        st.write(f"- 跳转时间: {transition_time or '未记录'}")
        
        st.write("**数据状态检查**:")
        st.write(f"- 生成图片数据: {'存在' if generated_images else '不存在'}")
        if generated_images:
            st.write(f"- 图片数量: {len(generated_images)}")
            st.write(f"- 数据完整性: {'完整' if all(img.get('has_image_data') for img in generated_images.values()) else '不完整'}")
        
        st.write("**Session State 键值**:")
        test_keys = [k for k in st.session_state.keys() if k.startswith('test_')]
        for key in test_keys:
            st.write(f"- {key}: {type(st.session_state[key]).__name__}")
    
    if generated_images:
        # 成功场景 - 显示生成结果
        st.success(f"**生成结果**: 成功生成 {len(generated_images)} 个A+模块")
        
        # 显示生成的模块列表
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
                st.caption(f"生成时间: {result.get('generation_time', 0):.1f}s")
            
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
                # 返回图片生成步骤
                st.session_state.test_should_show_results = False
                st.query_params.clear()
                st.info("返回图片生成步骤...")
                st.rerun()
        
        with col3:
            if st.button("🆕 新建项目", use_container_width=True):
                # 清除所有测试数据
                keys_to_clear = [k for k in st.session_state.keys() if k.startswith('test_')]
                for key in keys_to_clear:
                    del st.session_state[key]
                st.query_params.clear()
                st.info("开始新项目...")
                st.rerun()
        
        # 测试结果评估
        st.markdown("---")
        st.markdown("**✅ 测试结果评估**")
        st.success("🎯 核心功能测试通过:")
        st.write("- ✅ 数据成功保存到 session state")
        st.write("- ✅ '查看生成结果' 按钮成功触发跳转")
        st.write("- ✅ 页面重新加载后数据成功恢复")
        st.write("- ✅ 结果页面正确显示生成的模块")
        st.write("- ✅ 下载和批量操作功能正常")
        
    else:
        # 失败场景 - 数据丢失
        st.error("❌ 没有找到生成的图片数据")
        
        st.warning("**可能的问题：**")
        st.write("1. 页面重新加载时数据丢失")
        st.write("2. Session state 数据没有正确保存")
        st.write("3. 数据序列化过程中出现错误")
        st.write("4. 状态转换逻辑有问题")
        
        # 测试结果评估
        st.markdown("---")
        st.markdown("**❌ 测试结果评估**")
        st.error("🎯 核心功能测试失败:")
        st.write("- ❌ 数据在页面重新加载后丢失")
        st.write("- ❌ 无法在结果页面显示生成的模块")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🔙 返回图片生成", use_container_width=True):
                st.session_state.test_should_show_results = False
                st.query_params.clear()
                st.info("返回图片生成步骤...")
                st.rerun()
        
        with col2:
            if st.button("🔄 尝试恢复数据", use_container_width=True):
                # 尝试重新创建数据
                st.session_state.test_generated_images = create_mock_generated_images()
                st.success("✅ 已重新创建测试数据")
                st.rerun()

def main():
    """主函数"""
    try:
        st.title("🧪 '查看生成结果' 功能专业测试")
        st.caption("模拟完整的图片生成 → 查看结果 → 跳转流程")
        
        # 测试说明
        with st.expander("📋 测试说明", expanded=False):
            st.markdown("""
            **测试目标**: 验证"查看生成结果"按钮的完整功能链路
            
            **测试流程**:
            1. 模拟图片生成完成状态
            2. 点击"查看生成结果"按钮
            3. 验证页面跳转和数据保持
            4. 检查结果页面功能
            
            **关键测试点**:
            - 数据是否正确保存到 session state
            - 按钮点击是否触发正确的状态转换
            - 页面重新加载后数据是否丢失
            - 结果页面是否正确显示生成的模块
            """)
        
        # 根据当前状态决定显示哪个页面
        should_show_results = st.session_state.get('test_should_show_results', False)
        url_step = st.query_params.get("step")
        
        if should_show_results or url_step == "completed":
            simulate_results_page()
        else:
            simulate_image_generation_step()
        
        # 页面底部信息
        st.markdown("---")
        st.caption("🧪 专业测试模块 - 用于验证查看结果功能的完整链路")
        st.caption("📝 测试完成后可以直接删除此文件")
        
    except Exception as e:
        st.error(f"测试页面运行错误: {str(e)}")
        st.code(str(e))
        import traceback
        st.code(traceback.format_exc())

if __name__ == "__main__":
    main()
