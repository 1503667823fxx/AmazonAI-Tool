import streamlit as st
from PIL import Image, ImageSequence
import io
import sys
import os
import zipfile
import json

# 导入模板管理服务
sys.path.append(os.path.abspath('.'))
try:
    from services.aplus_template.template_manager import TemplateManager, AITemplateProcessor, create_aplus_sections
except ImportError:
    st.error("模板服务未正确安装，请检查 services/aplus_template/ 目录")

# --- 基础设置 ---
sys.path.append(os.path.abspath('.'))
try:
    import auth
except ImportError:
    pass 

st.set_page_config(page_title="A+ Studio", page_icon="🧩", layout="wide")

if 'auth' in sys.modules:
    if not auth.check_password():
        st.stop()

st.title("🧩 A+ 创意工场 (APlus Studio)")
st.caption("亚马逊高级内容页面 (EBC) 专属设计工具流")

tab_template, tab_slice, tab_preview, tab_gif = st.tabs(["🎨 智能模板工作流", "📏 智能切图 (Slicer)", "📱 无缝拼接预览", "🎬 动态 GIF 制作"])

# ==========================================
# Tab 1: 智能模板工作流 (新功能)
# ==========================================
with tab_template:
    st.subheader("🎨 AI 驱动的模板定制工作流")
    st.info("💡 选择专业模板，AI 智能替换产品内容，自动适配美化")
    
    col_template, col_product, col_result = st.columns([1, 1, 1.2], gap="medium")
    
    with col_template:
        st.markdown("### 1️⃣ 选择模板")
        
        # 加载真实模板库
        try:
            template_manager = TemplateManager()
            available_templates = template_manager.get_available_templates()
            
            if not available_templates:
                st.warning("暂无可用模板，请联系管理员添加模板")
                template_options = {"示例模板": "demo"}
            else:
                template_options = {t["name"]: t["id"] for t in available_templates}
            
            selected_template_name = st.selectbox("选择适合的模板风格", list(template_options.keys()))
            selected_template_id = template_options[selected_template_name]
            
            # 显示模板详情
            if available_templates:
                template_info = next((t for t in available_templates if t["id"] == selected_template_id), None)
                if template_info:
                    st.caption(f"📂 {template_info['category']} | {template_info['description']}")
        
        except Exception as e:
            st.error(f"加载模板失败: {e}")
            template_options = {"示例模板": "demo"}
            selected_template_name = st.selectbox("选择适合的模板风格", list(template_options.keys()))
            selected_template_id = template_options[selected_template_name]
        
        # 模板预览 (这里用占位图，实际项目中显示真实模板)
        st.image("https://via.placeholder.com/300x400/4CAF50/white?text=Template+Preview", 
                caption=f"模板预览: {selected_template}", use_container_width=True)
        
        # 模板自定义选项
        st.markdown("**模板定制选项:**")
        color_scheme = st.selectbox("配色方案", ["原始配色", "品牌色调", "暖色调", "冷色调", "黑白简约"])
        layout_style = st.selectbox("布局风格", ["标准布局", "紧凑型", "宽松型", "创意型"])
    
    with col_product:
        st.markdown("### 2️⃣ 产品信息")
        
        # 产品信息收集
        product_name = st.text_input("产品名称", placeholder="例: 无线蓝牙耳机 Pro Max")
        product_category = st.selectbox("产品类别", ["电子产品", "美妆护肤", "家居用品", "运动户外", "服装配饰", "母婴用品"])
        
        # 产品图片上传
        product_images = st.file_uploader("上传产品图片 (1-5张)", type=["jpg", "png"], accept_multiple_files=True, key="product_imgs")
        
        # 产品特点
        st.markdown("**产品卖点 (最多5个):**")
        features = []
        for i in range(5):
            feature = st.text_input(f"卖点 {i+1}", key=f"feature_{i}", placeholder="例: 降噪技术 / 超长续航")
            if feature.strip():
                features.append(feature)
        
        # 品牌信息
        brand_name = st.text_input("品牌名称", placeholder="例: TechPro")
        brand_color = st.color_picker("品牌主色调", "#FF6B6B")
        
        # AI 生成选项
        st.markdown("**AI 增强选项:**")
        ai_enhance_text = st.checkbox("AI 优化文案", value=True)
        ai_enhance_layout = st.checkbox("AI 智能排版", value=True)
        ai_background_gen = st.checkbox("AI 生成背景元素", value=False)
    
    with col_result:
        st.markdown("### 3️⃣ 生成结果")
        
        if st.button("🚀 生成 A+ 页面", type="primary", use_container_width=True):
            if not product_name or not features:
                st.error("请至少填写产品名称和一个卖点")
            else:
                with st.spinner("AI 正在生成定制化 A+ 页面..."):
                    try:
                        # 准备产品数据
                        product_data = {
                            "product_name": product_name,
                            "product_category": product_category,
                            "features": features,
                            "brand_name": brand_name,
                            "brand_color": brand_color,
                            "product_images": product_images
                        }
                        
                        # 准备定制选项
                        customization_options = {
                            "color_scheme": color_scheme,
                            "layout_style": layout_style,
                            "ai_enhance_text": ai_enhance_text,
                            "ai_enhance_layout": ai_enhance_layout,
                            "ai_background_gen": ai_background_gen
                        }
                        
                        # 模拟处理时间
                        import time
                        time.sleep(2)
                        
                        st.success("✅ A+ 页面生成完成！")
                        
                        # 显示生成的产品信息摘要
                        with st.expander("📋 生成摘要", expanded=True):
                            col_summary1, col_summary2 = st.columns(2)
                            with col_summary1:
                                st.write(f"**产品名称:** {product_name}")
                                st.write(f"**品牌:** {brand_name}")
                                st.write(f"**类别:** {product_category}")
                            with col_summary2:
                                st.write(f"**模板:** {selected_template_name}")
                                st.write(f"**配色:** {color_scheme}")
                                st.write(f"**布局:** {layout_style}")
                        
                        # 显示生成结果 (目前使用占位图，实际项目中会调用真实的AI服务)
                        st.markdown("### 🎨 生成的 A+ 模块")
                        
                        # 根据模板类型生成不同的模块
                        if "tech" in selected_template_id.lower():
                            result_sections = [
                                ("产品展示模块", "https://via.placeholder.com/970x400/2196F3/white?text=Tech+Product+Header"),
                                ("功能特性模块", "https://via.placeholder.com/970x300/4CAF50/white?text=Key+Features"), 
                                ("产品图库模块", "https://via.placeholder.com/970x350/FF9800/white?text=Product+Gallery"),
                                ("技术规格模块", "https://via.placeholder.com/970x250/9C27B0/white?text=Specifications")
                            ]
                        elif "beauty" in selected_template_id.lower():
                            result_sections = [
                                ("品牌故事模块", "https://via.placeholder.com/970x400/E91E63/white?text=Beauty+Brand+Story"),
                                ("成分介绍模块", "https://via.placeholder.com/970x300/4CAF50/white?text=Natural+Ingredients"), 
                                ("使用效果模块", "https://via.placeholder.com/970x350/FF5722/white?text=Amazing+Results"),
                                ("使用方法模块", "https://via.placeholder.com/970x250/795548/white?text=How+to+Use")
                            ]
                        else:
                            result_sections = [
                                ("主要展示模块", "https://via.placeholder.com/970x400/FF6B6B/white?text=Main+Header"),
                                ("产品特色模块", "https://via.placeholder.com/970x300/4CAF50/white?text=Product+Features"), 
                                ("使用场景模块", "https://via.placeholder.com/970x350/2196F3/white?text=Usage+Scenarios"),
                                ("品牌保证模块", "https://via.placeholder.com/970x250/FF9800/white?text=Brand+Promise")
                            ]
                        
                        for i, (section_name, section_url) in enumerate(result_sections):
                            st.image(section_url, caption=f"{section_name} (模块 {i+1})", use_container_width=True)
                        
                        # 下载选项
                        col_download1, col_download2, col_download3 = st.columns(3)
                        with col_download1:
                            # 创建模拟的ZIP文件
                            zip_buffer = io.BytesIO()
                            with zipfile.ZipFile(zip_buffer, "w") as zf:
                                for i, (section_name, _) in enumerate(result_sections):
                                    zf.writestr(f"section_{i+1}_{section_name}.jpg", b"mock_image_data")
                            
                            st.download_button("📥 下载所有模块", 
                                             data=zip_buffer.getvalue(), 
                                             file_name=f"aplus_{product_name.replace(' ', '_')}.zip", 
                                             mime="application/zip")
                        
                        with col_download2:
                            # 生成HTML代码
                            html_code = f"""
                            <!-- A+ 页面代码 - {product_name} -->
                            <div class="aplus-content">
                                <h1>{product_name}</h1>
                                <div class="brand">{brand_name}</div>
                                <div class="features">
                                    {''.join([f'<p>✓ {feature}</p>' for feature in features])}
                                </div>
                            </div>
                            """
                            st.download_button("📄 下载 HTML 代码", 
                                             data=html_code, 
                                             file_name=f"aplus_{product_name.replace(' ', '_')}.html", 
                                             mime="text/html")
                        
                        with col_download3:
                            # 生成配置文件
                            config_data = {
                                "product_info": product_data,
                                "template_config": {
                                    "template_id": selected_template_id,
                                    "template_name": selected_template_name,
                                    "customization": customization_options
                                },
                                "generated_at": str(time.time())
                            }
                            st.download_button("⚙️ 下载配置文件", 
                                             data=json.dumps(config_data, indent=2, ensure_ascii=False), 
                                             file_name=f"aplus_config_{product_name.replace(' ', '_')}.json", 
                                             mime="application/json")
                    
                    except Exception as e:
                        st.error(f"生成失败: {e}")
                        st.info("💡 这是演示版本，完整功能需要配置AI服务和模板文件")
        
        # 实时预览选项
        if st.checkbox("实时预览模式"):
            st.info("💡 修改左侧参数时会实时更新预览")
            # 这里可以添加实时预览逻辑

# ==========================================
# Tab 2: 智能切图 (把长图切成标准模块)
# ==========================================
with tab_slice:
    col1, col2 = st.columns([1, 1.5], gap="large")
    
    with col1:
        st.subheader("1. 上传长图")
        st.info("💡 用于将设计师制作的整张长海报，自动切割为亚马逊 A+ 标准模块图 (通常宽度 970px)。")
        
        uploaded_long_img = st.file_uploader("上传长图 (JPG/PNG)", type=["jpg", "png", "jpeg"])
        
        slice_height = st.number_input("单张切片高度 (px)", min_value=100, value=600, step=100, help="亚马逊标准模块通常为 600px 或 300px")
        output_format = st.radio("输出格式", ["JPEG", "PNG"], horizontal=True)
        
        btn_slice = st.button("🔪 开始切图", type="primary")

    with col2:
        st.subheader("2. 切片结果")
        if uploaded_long_img and btn_slice:
            image = Image.open(uploaded_long_img)
            img_w, img_h = image.size
            
            st.caption(f"原始尺寸: {img_w}x{img_h} px")
            
            # 切图逻辑
            slices = []
            num_slices = (img_h + slice_height - 1) // slice_height # 向上取整
            
            # 准备压缩包
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w") as zf:
                
                for i in range(num_slices):
                    top = i * slice_height
                    bottom = min((i + 1) * slice_height, img_h)
                    
                    # 裁剪
                    crop_img = image.crop((0, top, img_w, bottom))
                    
                    # 转字节
                    img_byte_arr = io.BytesIO()
                    ext = output_format.lower()
                    if ext == "jpeg":
                        crop_img = crop_img.convert("RGB")
                    crop_img.save(img_byte_arr, format=output_format, quality=95)
                    img_bytes = img_byte_arr.getvalue()
                    
                    # 存入列表用于显示
                    slices.append(crop_img)
                    
                    # 写入压缩包
                    zf.writestr(f"slice_{i+1:02d}.{ext}", img_bytes)
            
            # 显示切片
            st.success(f"成功切为 {len(slices)} 张图片！")
            
            # 下载全部
            st.download_button(
                "📦 打包下载所有切片 (ZIP)", 
                data=zip_buffer.getvalue(), 
                file_name="aplus_slices.zip", 
                mime="application/zip"
            )
            
            # 预览
            with st.expander("查看切片详情", expanded=True):
                grid = st.columns(2)
                for idx, s_img in enumerate(slices):
                    with grid[idx % 2]:
                        st.image(s_img, caption=f"Slice {idx+1} ({s_img.width}x{s_img.height})", use_container_width=True)

# ==========================================
# Tab 2: 无缝拼接预览 (模拟前台效果)
# ==========================================
with tab_preview:
    st.subheader("📱 移动端/PC端 滚动预览")
    st.caption("上传多张切片，检查拼接处是否自然无缝。")
    
    preview_files = st.file_uploader("按顺序上传所有切片 (支持多选)", type=["jpg", "png"], accept_multiple_files=True)
    
    if preview_files:
        # 排序逻辑：尝试按文件名排序，否则按上传顺序
        try:
            preview_files.sort(key=lambda x: x.name)
        except:
            pass
            
        st.divider()
        
        # 模拟无缝拼接：使用 st.image 的特性，将 margin 设为 0 (CSS hack)
        st.markdown("""
        <style>
            .seamless-container img {
                display: block;
                margin-bottom: -5px; /* 消除图片间隙 */
                width: 100%;
            }
            .preview-frame {
                border: 10px solid #333;
                border-radius: 20px;
                padding: 10px;
                background: #fff;
                max-width: 500px; /* 模拟手机宽度 */
                margin: 0 auto;
                overflow-y: auto;
                max-height: 800px;
                box-shadow: 0 10px 25px rgba(0,0,0,0.2);
            }
        </style>
        """, unsafe_allow_html=True)
        
        st.markdown('<div class="preview-frame">', unsafe_allow_html=True)
        for p_file in preview_files:
            # 直接读取并显示，不加 caption 以免破坏无缝感
            img = Image.open(p_file)
            st.image(img, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

# ==========================================
# Tab 3: 动态 GIF 制作 (简单动效)
# ==========================================
with tab_gif:
    c_g1, c_g2 = st.columns([1, 1.5], gap="large")
    
    with c_g1:
        st.subheader("1. 制作设置")
        gif_files = st.file_uploader("上传关键帧 (2-10张)", type=["jpg", "png"], accept_multiple_files=True, key="gif_upload")
        
        duration = st.slider("每帧停留时间 (毫秒)", 100, 2000, 500, step=100)
        loop_count = st.number_input("循环次数 (0=无限循环)", value=0)
        resize_width = st.number_input("统一宽度缩放 (px, 0=不缩放)", value=970)
        
        btn_gif = st.button("🎬 生成 GIF", type="primary")
        
    with c_g2:
        st.subheader("2. 效果预览")
        if btn_gif and gif_files:
            if len(gif_files) < 2:
                st.error("至少需要上传 2 张图片才能制作 GIF")
            else:
                try:
                    frames = []
                    for f in gif_files:
                        im = Image.open(f)
                        # 统一尺寸逻辑
                        if resize_width > 0:
                            ratio = resize_width / im.width
                            new_h = int(im.height * ratio)
                            im = im.resize((resize_width, new_h), Image.Resampling.LANCZOS)
                        frames.append(im)
                    
                    # 保存 GIF
                    gif_buffer = io.BytesIO()
                    # duration 是每帧的时间(ms)
                    frames[0].save(
                        gif_buffer, 
                        format='GIF', 
                        save_all=True, 
                        append_images=frames[1:], 
                        optimize=True, 
                        duration=duration, 
                        loop=loop_count
                    )
                    
                    st.success("GIF 生成成功！")
                    st.image(gif_buffer.getvalue(), caption="生成的动态 A+ 模块")
                    
                    st.download_button(
                        "📥 下载 GIF", 
                        data=gif_buffer.getvalue(), 
                        file_name="aplus_motion.gif", 
                        mime="image/gif"
                    )
                    
                except Exception as e:
                    st.error(f"生成失败: {e}")
