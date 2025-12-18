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
    from app_utils.aplus_studio.template_manager import TemplateManager, AITemplateProcessor, create_aplus_sections
    from app_utils.aplus_studio.search_engine import TemplateSearchEngine, SmartTemplateRecommender
except ImportError:
    st.error("模板服务未正确安装，请检查 app_utils/aplus_studio/ 目录")

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
st.caption("AI 驱动的亚马逊 A+ 页面智能生成工具")

# ==========================================
# 智能模板工作流
# ==========================================
    st.subheader("🎨 AI 驱动的模板定制工作流")
    st.info("💡 选择专业模板，AI 智能替换产品内容，自动适配美化")
    
    col_template, col_product, col_result = st.columns([1, 1, 1.2], gap="medium")
    
    with col_template:
        st.markdown("### 1️⃣ 智能模板选择")
        
        # 初始化搜索引擎
        try:
            search_engine = TemplateSearchEngine()
            recommender = SmartTemplateRecommender(search_engine)
            
            # 搜索功能
            st.markdown("**🔍 搜索模板**")
            search_query = st.text_input("输入关键词搜索", placeholder="例: 南瓜服、万圣节、科技产品、美妆...")
            
            # 搜索建议
            if search_query and len(search_query) >= 2:
                suggestions = search_engine.get_search_suggestions(search_query)
                if suggestions:
                    st.caption(f"💡 搜索建议: {' | '.join(suggestions[:4])}")
            
            # 快速筛选
            col_filter1, col_filter2 = st.columns(2)
            with col_filter1:
                category_filter = st.selectbox("按类别筛选", 
                    ["全部", "电子产品", "美妆护肤", "家居用品", "运动户外", "母婴用品", "节日主题", "风格主题"])
            with col_filter2:
                holiday_filter = st.selectbox("按节日筛选", 
                    ["全部", "万圣节", "圣诞节", "春节", "情人节", "母亲节"])
            
            # 执行搜索
            if search_query:
                search_results = search_engine.search_templates(search_query, limit=8)
            else:
                search_results = search_engine._get_all_templates()
            
            # 应用筛选
            if category_filter != "全部":
                search_results = [r for r in search_results if r["config"].get("category") == category_filter]
            if holiday_filter != "全部":
                search_results = [r for r in search_results if r["config"].get("holiday") == holiday_filter]
            
            # 显示搜索结果
            if search_results:
                st.markdown("**📋 搜索结果**")
                
                # 创建模板选择器
                template_options = {}
                for result in search_results[:6]:  # 最多显示6个结果
                    template_id = result["template_id"]
                    template_config = result["config"]
                    score = result.get("score", 0)
                    match_reasons = result.get("match_reasons", [])
                    
                    # 构建显示名称
                    display_name = template_config["name"]
                    if score > 5:  # 高相关性
                        display_name = f"⭐ {display_name}"
                    if match_reasons:
                        display_name += f" ({match_reasons[0]})"
                    
                    template_options[display_name] = template_id
                
                selected_template_name = st.selectbox("选择模板", list(template_options.keys()))
                selected_template_id = template_options[selected_template_name]
                
                # 显示选中模板的详细信息
                selected_result = next((r for r in search_results if r["template_id"] == selected_template_id), None)
                if selected_result:
                    template_config = selected_result["config"]
                    
                    # 模板信息
                    st.caption(f"📂 {template_config.get('category', '')} | {template_config.get('description', '')}")
                    
                    # 匹配原因
                    if "match_reasons" in selected_result and selected_result["match_reasons"]:
                        st.success(f"✨ 匹配原因: {' | '.join(selected_result['match_reasons'])}")
                    
                    # 标签展示
                    if template_config.get("tags"):
                        tags_text = " ".join([f"#{tag}" for tag in template_config["tags"][:4]])
                        st.caption(f"🏷️ {tags_text}")
            
            else:
                st.warning("未找到匹配的模板，请尝试其他关键词")
                # 提供默认选项
                template_options = {"示例模板": "demo"}
                selected_template_name = st.selectbox("选择模板", list(template_options.keys()))
                selected_template_id = template_options[selected_template_name]
        
        except Exception as e:
            st.error(f"搜索功能加载失败: {e}")
            # 降级到基础模板选择
            template_options = {"示例模板": "demo"}
            selected_template_name = st.selectbox("选择模板", list(template_options.keys()))
            selected_template_id = template_options[selected_template_name]
        
        # 模板预览
        st.markdown("**🖼️ 模板预览**")
        
        # 根据模板ID显示不同的预览图
        preview_colors = {
            "tech_modern": "2196F3",
            "beauty_elegant": "E91E63", 
            "home_cozy": "FF9800",
            "sports_dynamic": "4CAF50",
            "baby_cute": "FF69B4",
            "halloween_spooky": "FF4500",
            "christmas_festive": "DC143C",
            "vintage_retro": "8B4513"
        }
        
        color = preview_colors.get(selected_template_id, "4CAF50")
        preview_url = f"https://via.placeholder.com/300x400/{color}/white?text={selected_template_name.replace(' ', '+')}"
        
        st.image(preview_url, caption=f"模板预览: {selected_template_name}", use_container_width=True)
        
        # 显示相似模板
        if search_results and len(search_results) > 1:
            try:
                similar_templates = search_engine.get_similar_templates(selected_template_id, limit=3)
                if similar_templates:
                    with st.expander("🔗 相似模板推荐"):
                        for sim in similar_templates:
                            sim_name = sim["config"]["name"]
                            sim_category = sim["config"].get("category", "")
                            similarity = sim.get("similarity_score", 0)
                            st.caption(f"• {sim_name} ({sim_category}) - 相似度: {similarity:.1f}")
            except:
                pass
        
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
        
        # 智能推荐
        if product_name and product_category and features:
            if st.button("🤖 获取AI推荐模板", help="根据产品信息智能推荐最适合的模板"):
                try:
                    recommendations = recommender.recommend_by_product_info(
                        product_name, product_category, features
                    )
                    if recommendations:
                        st.markdown("**🎯 AI推荐模板:**")
                        for i, rec in enumerate(recommendations[:3]):
                            template_name = rec["config"]["name"]
                            reason = rec.get("recommendation_reason", "风格匹配")
                            score = rec.get("score", 0)
                            
                            if st.button(f"📌 {template_name}", key=f"rec_{i}", 
                                       help=f"推荐原因: {reason} (匹配度: {score:.1f})"):
                                # 更新选中的模板
                                st.session_state.recommended_template = rec["template_id"]
                                st.rerun()
                except Exception as e:
                    st.error(f"推荐功能暂时不可用: {e}")
        
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
