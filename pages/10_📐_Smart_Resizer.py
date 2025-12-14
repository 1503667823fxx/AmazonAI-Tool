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

    # 3. 简单设置
    st.info("🎨 使用 Gemini 进行画幅重构")
    
    # 4. 触发按钮
    generate_btn = st.button("🚀 开始重构画幅", type="primary", use_container_width=True)

    # 4. 状态显示和使用说明
    if "api_cost" not in st.session_state:
        st.info("💡 本功能使用 Google Gemini (视觉分析)")
    
    with st.expander("📖 使用说明"):
        st.markdown("""
        **功能特点:**
        - 🧠 Gemini智能分析背景特征
        - 🎨 保持原图完整，只扩展背景
        - 🔄 自动适配目标画幅比例
        - ✨ 无缝融合，自然过渡
        
        **最佳实践:**
        1. 上传清晰的产品图片
        2. 选择合适的目标比例
        3. 检查预览效果
        4. 点击"开始重构"按钮
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
        
        # 显示处理参数
        with st.expander("🔧 查看处理参数"):
            st.write(f"- 原图比例: {orig_ratio:.3f}")
            st.write(f"- 目标比例: {target_ratio_val:.3f}")
            st.write(f"- 需要扩展: {'是' if abs(orig_ratio - target_ratio_val) > 0.01 else '否'}")
            st.write(f"- 扩展方向: {'宽度' if target_ratio_val > orig_ratio else '高度' if target_ratio_val < orig_ratio else '无需扩展'}")

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
                    
                    # 调用Gemini进行画幅重构
                    final_image = generation_service.fill_image(
                        image=original_image,
                        mask=None,
                        prompt="",
                        use_gemini=True,
                        target_ratio=target_ratio,
                        test_mode=False
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
                
                # 显示处理信息
                with st.expander("📊 处理详情"):
                    col_info1, col_info2, col_info3 = st.columns(3)
                    with col_info1:
                        st.metric("原始尺寸", f"{orig_w}×{orig_h}")
                        st.metric("原始比例", f"{orig_ratio:.2f}")
                    with col_info2:
                        final_w, final_h = final_image.size
                        st.metric("扩展尺寸", f"{final_w}×{final_h}")
                        st.metric("目标比例", f"{target_ratio_val:.2f}")
                    with col_info3:
                        st.write("**使用的模型:**")
                        st.success("🤖 Gemini 画幅重构")
                        st.code("models/gemini-3-pro-image-preview")

            except Exception as e:
                st.error(f"处理过程中发生错误: {str(e)}")
                st.info("💡 提示：请确保上传的是有效的图片文件，并检查网络连接。")
else:
    # 空状态提示
    st.info("👈 请在左侧侧边栏上传图片并选择目标比例。")
    st.markdown("""
    **功能说明：**
    * **1:1** - 适合亚马逊主图
    * **4:3** - 适合A+页面标准插图
    * **21:9** - 适合品牌故事模块或Banner
    """)
