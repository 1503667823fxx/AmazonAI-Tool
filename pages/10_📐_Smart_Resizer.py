import streamlit as st
import io
from PIL import Image
import auth

if not auth.check_password():
    st.stop()

# 引入简化的模块
try:
    from services.smart_resizer import generation_service
except ImportError as e:
    st.error(f"模块加载失败，请检查文件结构是否完整: {e}")
    st.stop()

# --- 页面配置 ---
st.set_page_config(page_title="Smart Resizer", page_icon="📐", layout="wide")

st.title("📐 Smart Resizer - 智能画幅重构")
st.markdown("### 亚马逊电商图 · 智能扩充与尺寸调整")

# --- 侧边栏：控制区 ---
with st.sidebar:
    st.header("🛠️ 设置工作流")
    
    # 1. 图片上传
    uploaded_file = st.file_uploader("上传产品原图", type=["jpg", "jpeg", "png"])
    
    # 2. 比例选择 (严格限制为您要求的三个比例)
    target_ratio_name = st.radio(
        "选择目标画幅比例",
        options=["1:1 (正方形)", "4:3 (标准横幅)", "21:9 (超宽电影感)"],
        index=0
    )
    
    # 映射比例名称到数值
    ratio_map = {
        "1:1 (正方形)": (1, 1),
        "4:3 (标准横幅)": (4, 3),
        "21:9 (超宽电影感)": (21, 9)
    }
    target_ratio = ratio_map[target_ratio_name]

    # 3. 智能设置
    st.subheader("🧠 智能重构选项")
    
    # 构图优化选项
    composition_mode = st.selectbox(
        "构图优化模式",
        options=["智能分析", "保持居中", "自定义位置"],
        help="选择如何处理主体在新画幅中的位置"
    )
    
    # 扩展质量设置
    quality_level = st.select_slider(
        "扩展质量",
        options=["快速", "标准", "高质量"],
        value="标准",
        help="更高质量需要更长处理时间"
    )
    
    # 背景处理选项
    background_handling = st.radio(
        "背景扩展方式",
        options=["智能延续", "模糊延续", "纯色填充"],
        help="选择如何扩展背景区域"
    )
    
    st.info("🎨 使用 Gemini 1.5 Pro Vision 进行智能重构")
    
    # 4. 触发按钮
    generate_btn = st.button("🚀 开始智能重构", type="primary", use_container_width=True)

    # 4. 状态显示和使用说明
    if "api_cost" not in st.session_state:
        st.info("💡 本功能使用 Google Gemini (视觉分析)")
    
    with st.expander("📖 使用说明"):
        st.markdown("""
        **智能功能特点:**
        - 🧠 AI分析图片构图和主体位置
        - � 智能重图新定位主体物品
        - 🎨 根据新比例优化构图布局
        - 🔄 自然扩展背景，无缝融合
        - ✨ 保持主体比例和视觉重点
        
        **使用建议:**
        1. 上传清晰的产品图片 (建议1000px以上)
        2. 选择目标画幅比例
        3. 选择合适的构图模式
        4. 调整质量和背景处理方式
        5. 点击"开始智能重构"
        
        **比例用途:**
        - **1:1** - 亚马逊主图、社交媒体
        - **4:3** - A+页面、产品详情
        - **21:9** - 品牌横幅、故事模块
        """)

# --- 主区域：执行逻辑 ---
if uploaded_file:
    # 加载图片
    original_image = Image.open(uploaded_file).convert("RGB")
    
    # 创建两列布局：左侧预览，右侧结果
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("原始素材")
        
        # 显示原图信息
        orig_w, orig_h = original_image.size
        orig_ratio = orig_w / orig_h
        target_w_ratio, target_h_ratio = target_ratio
        target_ratio_val = target_w_ratio / target_h_ratio
        
        st.info(f"原图尺寸: {orig_w}×{orig_h} (比例: {orig_ratio:.2f})")
        st.info(f"目标比例: {target_w_ratio}:{target_h_ratio} ({target_ratio_val:.2f})")
        
        # 显示原图
        st.image(original_image, caption="原始图片", use_column_width=True)
        
        # 显示处理参数和预期效果
        with st.expander("🔧 处理参数 & 预期效果"):
            col_param1, col_param2 = st.columns(2)
            
            with col_param1:
                st.write("**当前参数:**")
                st.write(f"- 原图比例: {orig_ratio:.3f}")
                st.write(f"- 目标比例: {target_ratio_val:.3f}")
                st.write(f"- 构图模式: {composition_mode}")
                st.write(f"- 质量级别: {quality_level}")
                st.write(f"- 背景处理: {background_handling}")
            
            with col_param2:
                st.write("**预期效果:**")
                if abs(orig_ratio - target_ratio_val) > 0.01:
                    if target_ratio_val > orig_ratio:
                        st.write("🔄 横向扩展，主体可能重新定位")
                        st.write("📐 增加左右背景区域")
                    else:
                        st.write("🔄 纵向扩展，主体可能重新定位")  
                        st.write("📐 增加上下背景区域")
                    st.write("🎯 主体将根据新比例优化位置")
                else:
                    st.write("✨ 比例相近，微调构图")
                    st.write("🎨 优化整体视觉效果")

    if generate_btn:
        with col2:
            st.subheader("AI 重构结果")
            status_container = st.empty()
            
# ... (保留上面的代码)
            
            try:
                # --- Gemini画幅重构 ---
                with status_container.status("🎨 Gemini 正在重构画幅...", expanded=True) as status:
                    # 显示处理信息
                    status.write(f"🎯 目标画幅: {target_ratio[0]}:{target_ratio[1]} (比例值: {target_ratio[0]/target_ratio[1]:.2f})")
                    status.write(f"📏 原始画幅: {orig_w}×{orig_h} (比例值: {orig_ratio:.2f})")
                    status.write(f"🔤 提示词: 'Outpaint this image to {target_ratio[0]}:{target_ratio[1]} aspect ratio'")
                    
                    # 调用Gemini进行智能画幅重构
                    final_image = generation_service.fill_image(
                        image=original_image,
                        mask=None,
                        prompt="",
                        use_gemini=True,
                        target_ratio=target_ratio,
                        test_mode=False,
                        composition_mode=composition_mode,
                        quality_level=quality_level,
                        background_handling=background_handling
                    )
                    
                    status.update(label="✅ 画幅重构完成！", state="complete", expanded=False)

                # 展示结果
                st.image(final_image, caption="智能扩展结果", use_column_width=True)
                
                # 提供下载功能
                img_buffer = io.BytesIO()
                final_image.save(img_buffer, format='PNG', quality=95)
                img_buffer.seek(0)
                
                st.download_button(
                    label="📥 下载扩展后的图片",
                    data=img_buffer.getvalue(),
                    file_name=f"smart_resized_{target_ratio[0]}x{target_ratio[1]}.png",
                    mime="image/png",
                    use_container_width=True
                )
                
                # 显示详细处理信息
                with st.expander("📊 智能重构详情"):
                    col_info1, col_info2, col_info3 = st.columns(3)
                    
                    with col_info1:
                        st.write("**原始信息:**")
                        st.metric("原始尺寸", f"{orig_w}×{orig_h}")
                        st.metric("原始比例", f"{orig_ratio:.3f}")
                        
                    with col_info2:
                        final_w, final_h = final_image.size
                        final_ratio = final_w / final_h
                        st.write("**重构结果:**")
                        st.metric("新尺寸", f"{final_w}×{final_h}")
                        st.metric("实际比例", f"{final_ratio:.3f}")
                        
                        # 计算比例精度
                        ratio_accuracy = (1 - abs(final_ratio - target_ratio_val) / target_ratio_val) * 100
                        st.metric("比例精度", f"{ratio_accuracy:.1f}%")
                        
                    with col_info3:
                        st.write("**处理设置:**")
                        st.info(f"🎯 构图: {composition_mode}")
                        st.info(f"⚡ 质量: {quality_level}")
                        st.info(f"🎨 背景: {background_handling}")
                        st.success("🤖 Gemini 1.5 Pro Vision")
                        
                    # 显示尺寸变化分析
                    st.write("**尺寸变化分析:**")
                    width_change = ((final_w - orig_w) / orig_w) * 100 if orig_w > 0 else 0
                    height_change = ((final_h - orig_h) / orig_h) * 100 if orig_h > 0 else 0
                    
                    col_change1, col_change2 = st.columns(2)
                    with col_change1:
                        if width_change > 5:
                            st.success(f"宽度增加: +{width_change:.1f}%")
                        elif width_change < -5:
                            st.warning(f"宽度减少: {width_change:.1f}%")
                        else:
                            st.info(f"宽度变化: {width_change:.1f}%")
                            
                    with col_change2:
                        if height_change > 5:
                            st.success(f"高度增加: +{height_change:.1f}%")
                        elif height_change < -5:
                            st.warning(f"高度减少: {height_change:.1f}%")
                        else:
                            st.info(f"高度变化: {height_change:.1f}%")

            except Exception as e:
                st.error(f"处理过程中发生错误: {str(e)}")
                st.info("💡 提示：请确保上传的是有效的图片文件，并检查网络连接。")
else:
    # 空状态提示和功能介绍
    st.info("👈 请在左侧侧边栏上传图片开始智能重构")
    
    # 功能展示
    col_demo1, col_demo2, col_demo3 = st.columns(3)
    
    with col_demo1:
        st.markdown("### 🎯 1:1 正方形")
        st.markdown("""
        **适用场景:**
        - 亚马逊主图
        - Instagram帖子  
        - 社交媒体头像
        
        **智能优化:**
        - 主体居中定位
        - 背景均匀扩展
        - 保持视觉平衡
        """)
        
    with col_demo2:
        st.markdown("### 📱 4:3 标准横幅")
        st.markdown("""
        **适用场景:**
        - A+页面插图
        - 产品详情页
        - 演示文稿
        
        **智能优化:**
        - 主体左右定位
        - 增加展示空间
        - 突出产品特征
        """)
        
    with col_demo3:
        st.markdown("### 🎬 21:9 超宽电影")
        st.markdown("""
        **适用场景:**
        - 品牌故事横幅
        - 网站Banner
        - 营销素材
        
        **智能优化:**
        - 主体重新构图
        - 创造视觉冲击
        - 电影级视觉效果
        """)
    
    st.markdown("---")
    st.markdown("""
    ### 🧠 智能重构技术特点
    
    **与传统扩展的区别:**
    - ❌ **传统方式**: 简单拉伸或填充，主体位置固定
    - ✅ **智能重构**: AI分析构图，重新定位主体，优化视觉效果
    
    **核心优势:**
    1. **构图分析** - AI理解图片内容和主体位置
    2. **智能定位** - 根据新比例重新安排主体位置  
    3. **自然扩展** - 背景无缝延续，保持视觉连贯
    4. **质量保证** - 保持原图清晰度，提升整体效果
    """)
    
    st.success("💡 上传图片体验AI驱动的智能画幅重构技术！")
