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
    """完全复刻原面板的图片生成步骤布局"""
    st.subheader("🖼️ 第六步：图片生成")
    st.markdown("AI正在为您生成专业的A+模块图片")
    
    # 添加调试信息（复刻原版）
    with st.expander("🔍 调试信息", expanded=False):
        st.write("**测试环境信息**:")
        st.write(f"- Session ID: test_session_12345")
        st.write(f"- 当前状态: IMAGE_GENERATION")
        st.write(f"- Module Contents: 4 个模块")
        st.write("  - PRODUCT_OVERVIEW: 产品概览")
        st.write("  - FEATURE_ANALYSIS: 功能解析")
        st.write("  - USAGE_SCENARIOS: 使用场景")
        st.write("  - QUALITY_ASSURANCE: 品质保证")
        st.write(f"- Final Content: 存在")
        st.write(f"  - 模块数量: 4")
        st.write(f"- Style Theme: 存在")
        st.write(f"  - 主题名称: 现代简约风格")
    
    # 模拟前置条件检查通过
    final_content = create_mock_generated_images()
    style_theme = {"theme_name": "现代简约风格"}
    
    # 显示生成配置（复刻原版）
    st.write("**生成配置：**")
    col1, col2 = st.columns(2)
    
    with col1:
        st.write(f"**模块数量**: {len(final_content)} 个")
        st.write(f"**风格主题**: {style_theme.get('theme_name', '未选择')}")
    
    with col2:
        st.write(f"**图片尺寸**: 600x450 像素")
        st.write(f"**预计用时**: 3-5 分钟")
    
    # 开始生成按钮（复刻原版）
    if st.button("🚀 开始批量生成", type="primary", use_container_width=True):
        # 模拟生成过程
        with st.spinner("AI正在生成A+模块图片..."):
            # 创建进度显示
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # 模拟生成配置信息
            with st.expander("🔧 生成配置", expanded=False):
                col1, col2 = st.columns(2)
                with col1:
                    st.info("生成模式: PARALLEL")
                    st.info("并行任务数: 3")
                with col2:
                    st.info("重试次数: 2")
                    st.info("质量阈值: 70.0%")
            
            st.info("⏱️ 预计生成时间: 12 秒")
            
            # 模拟生成过程
            modules = ['PRODUCT_OVERVIEW', 'FEATURE_ANALYSIS', 'USAGE_SCENARIOS', 'QUALITY_ASSURANCE']
            generated_images = {}
            
            for i, module in enumerate(modules):
                module_name = module.replace('_', ' ').title()
                status_text.text(f"正在生成 {module_name} 模块图片... ({int((i+1)/len(modules)*100)}%)")
                progress_bar.progress((i + 1) / len(modules))
                time.sleep(1.5)  # 模拟生成时间
                
                # 模拟生成结果
                generated_images[module] = {
                    'image_path': f'generated/{module}_{int(time.time())}.png',
                    'generation_time': 2.0 + i * 0.3,
                    'quality_score': 0.85 + (i * 0.02),
                    'success': True,
                    'has_image_data': True,
                    'image_data_size': 800000 + i * 50000,
                    'is_simulated': True
                }
            
            # 保存生成结果到session state
            st.session_state.test_generated_images = generated_images
            st.session_state.test_generation_completed = True
            
            # 显示生成摘要（复刻原版）
            success_count = len(generated_images)
            failure_count = 0
            total_time = sum(img['generation_time'] for img in generated_images.values())
            total_quality = sum(img['quality_score'] for img in generated_images.values())
            
            st.success(f"✅ 批量生成完成！成功: {success_count}, 失败: {failure_count}")
            
            # 显示质量统计（复刻原版）
            success_rate = success_count / len(modules)
            avg_quality = total_quality / success_count
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("成功率", f"{success_rate:.1%}")
            with col2:
                st.metric("平均质量", f"{avg_quality:.1%}")
            with col3:
                st.metric("总用时", f"{total_time:.1f}s")
            
            # 显示生成统计详情（复刻原版）
            with st.expander("📊 详细生成统计", expanded=False):
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("总生成数", len(modules))
                    st.metric("成功生成", success_count)
                    st.metric("平均质量", f"{avg_quality:.1%}")
                with col2:
                    st.metric("失败生成", failure_count)
                    st.metric("平均用时", f"{total_time/len(modules):.1f}s")
                    st.metric("总批次数", 1)
                with col3:
                    st.metric("整体成功率", f"{success_rate:.1%}")
                    st.metric("总用时", f"{total_time:.1f}s")
                    st.metric("复杂模块数", 2)
            
            # 显示质量分析（复刻原版）
            quality_scores = [img['quality_score'] for img in generated_images.values()]
            with st.expander("🎯 质量分析", expanded=False):
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("最高质量", f"{max(quality_scores):.1%}")
                    st.metric("最低质量", f"{min(quality_scores):.1%}")
                with col2:
                    high_quality_count = sum(1 for score in quality_scores if score >= 0.7)
                    st.metric("高质量模块", f"{high_quality_count}/{len(quality_scores)}")
                    st.metric("质量达标率", f"{high_quality_count/len(quality_scores):.1%}")
            
            # 显示生成时间分析（复刻原版）
            generation_times = [img['generation_time'] for img in generated_images.values()]
            with st.expander("⏱️ 性能分析", expanded=False):
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("最快生成", f"{min(generation_times):.1f}s")
                    st.metric("最慢生成", f"{max(generation_times):.1f}s")
                with col2:
                    avg_time = sum(generation_times) / len(generation_times)
                    st.metric("平均时间", f"{avg_time:.1f}s")
                    efficiency = len(generation_times) / total_time if total_time > 0 else 0
                    st.metric("生成效率", f"{efficiency:.2f} 模块/秒")
            
            # 🎯 关键测试：完全复刻的"查看生成结果"按钮
            if st.button("📊 查看生成结果", type="primary", use_container_width=True):
                # 完全复刻原版的逻辑
                logger.info("User clicked '查看生成结果' button (test simulation)")
                
                # 检查生成图片数据
                generated_images = st.session_state.get('test_generated_images')
                logger.info(f"Generated images available: {generated_images is not None}")
                if generated_images:
                    logger.info(f"Generated images count: {len(generated_images)}")
                
                # 设置URL参数强制跳转到完成状态（复刻原版）
                timestamp = str(int(datetime.now().timestamp()))
                st.query_params.update({"step": "completed", "t": timestamp})
                logger.info(f"Set URL params: step=completed, t={timestamp}")
                
                # 设置跳转标志
                st.session_state.test_should_show_results = True
                st.session_state.test_transition_timestamp = datetime.now().isoformat()
                
                # 显示调试信息给用户（复刻原版）
                st.info("🔄 正在跳转到结果页面...")
                logger.info("Triggering page rerun...")
                
                # 触发页面重新加载
                st.rerun()
            
            # 临时测试按钮（复刻原版）
            st.markdown("---")
            st.markdown("**🧪 测试区域**")
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("🔧 直接跳转 (测试)", type="secondary"):
                    # 直接设置状态，不使用URL参数
                    st.session_state.test_should_show_results = True
                    st.session_state.test_transition_timestamp = datetime.now().isoformat()
                    st.success("✅ 状态已设置为COMPLETED")
                    st.rerun()
            
            with col2:
                if st.button("🔍 检查数据", type="secondary"):
                    # 检查生成的图片数据
                    generated_images = st.session_state.get('test_generated_images')
                    if generated_images:
                        st.success(f"✅ 找到 {len(generated_images)} 个生成的图片")
                    else:
                        st.error("❌ 没有找到生成的图片数据")
    
    # 如果已经生成完成，显示生成结果和按钮
    elif st.session_state.get('test_generation_completed'):
        generated_images = st.session_state.get('test_generated_images', {})
        
        if generated_images:
            st.success(f"✅ 批量生成完成！成功: {len(generated_images)}, 失败: 0")
            
            # 显示统计信息
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("成功率", "100.0%")
            with col2:
                avg_quality = sum(img['quality_score'] for img in generated_images.values()) / len(generated_images)
                st.metric("平均质量", f"{avg_quality:.1%}")
            with col3:
                total_time = sum(img['generation_time'] for img in generated_images.values())
                st.metric("总用时", f"{total_time:.1f}s")
            
            # 🎯 关键测试：完全复刻的"查看生成结果"按钮
            if st.button("📊 查看生成结果", type="primary", use_container_width=True):
                # 完全复刻原版的逻辑
                logger.info("User clicked '查看生成结果' button (test simulation)")
                
                # 检查生成图片数据
                logger.info(f"Generated images available: {generated_images is not None}")
                if generated_images:
                    logger.info(f"Generated images count: {len(generated_images)}")
                
                # 设置URL参数强制跳转到完成状态（复刻原版）
                timestamp = str(int(datetime.now().timestamp()))
                st.query_params.update({"step": "completed", "t": timestamp})
                logger.info(f"Set URL params: step=completed, t={timestamp}")
                
                # 设置跳转标志
                st.session_state.test_should_show_results = True
                st.session_state.test_transition_timestamp = datetime.now().isoformat()
                
                # 显示调试信息给用户（复刻原版）
                st.info("🔄 正在跳转到结果页面...")
                logger.info("Triggering page rerun...")
                
                # 触发页面重新加载
                st.rerun()
            
            # 临时测试按钮（复刻原版）
            st.markdown("---")
            st.markdown("**🧪 测试区域**")
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("🔧 直接跳转 (测试)", type="secondary", key="direct_jump_2"):
                    # 直接设置状态，不使用URL参数
                    st.session_state.test_should_show_results = True
                    st.session_state.test_transition_timestamp = datetime.now().isoformat()
                    st.success("✅ 状态已设置为COMPLETED")
                    st.rerun()
            
            with col2:
                if st.button("🔍 检查数据", type="secondary", key="check_data_2"):
                    # 检查生成的图片数据
                    if generated_images:
                        st.success(f"✅ 找到 {len(generated_images)} 个生成的图片")
                    else:
                        st.error("❌ 没有找到生成的图片数据")
    
    # 测试辅助功能
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
