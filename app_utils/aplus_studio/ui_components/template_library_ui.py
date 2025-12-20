"""
模板库界面组件
实现模板浏览、搜索和预览功能
"""

import streamlit as st
from typing import Dict, List, Optional, Any, Tuple
from PIL import Image
import io
import base64

from ..interfaces import ITemplateManager, ISearchEngine, ICategoryManager
from ..models.core_models import Template, Category


class TemplateLibraryUI:
    """模板库界面组件"""
    
    def __init__(self, 
                 template_manager: ITemplateManager,
                 search_engine: ISearchEngine,
                 category_manager: ICategoryManager):
        """
        初始化模板库界面
        
        Args:
            template_manager: 模板管理器
            search_engine: 搜索引擎
            category_manager: 分类管理器
        """
        self.template_manager = template_manager
        self.search_engine = search_engine
        self.category_manager = category_manager
        
    def render(self) -> Optional[str]:
        """
        渲染模板库界面
        
        Returns:
            选中的模板ID，如果没有选择则返回None
        """
        st.markdown("### 🎨 模板库")
        
        # 搜索和筛选区域
        selected_template_id = self._render_search_section()
        
        # 如果有选中的模板，显示详细信息
        if selected_template_id:
            self._render_template_details(selected_template_id)
            
        return selected_template_id
    
    def _render_search_section(self) -> Optional[str]:
        """渲染搜索和筛选区域"""
        col_search, col_filter = st.columns([2, 1])
        
        with col_search:
            # 搜索框
            search_query = st.text_input(
                "🔍 搜索模板",
                placeholder="输入关键词搜索模板...",
                help="支持按名称、标签、节日等搜索"
            )
            
            # 搜索建议
            if search_query and len(search_query) >= 2:
                suggestions = self.search_engine.get_search_suggestions(search_query)
                if suggestions:
                    st.caption(f"💡 搜索建议: {' | '.join(suggestions[:4])}")
        
        with col_filter:
            # 分类筛选
            categories = self._get_category_options()
            selected_category = st.selectbox(
                "📂 分类筛选",
                options=list(categories.keys()),
                index=0
            )
            
            # 节日筛选
            holiday_options = self._get_holiday_options()
            selected_holiday = st.selectbox(
                "🎉 节日筛选", 
                options=holiday_options,
                index=0
            )
        
        # 执行搜索
        templates = self._search_templates(search_query, selected_category, selected_holiday)
        
        # 显示搜索结果
        return self._render_template_grid(templates, search_query)
    
    def _get_category_options(self) -> Dict[str, Optional[str]]:
        """获取分类选项"""
        options = {"全部分类": None}
        
        try:
            categories = self.category_manager.get_all_categories()
            for category in categories:
                if category.level == 0:  # 只显示顶级分类
                    options[category.name] = category.id
        except Exception as e:
            st.error(f"加载分类失败: {e}")
            
        return options
    
    def _get_holiday_options(self) -> List[str]:
        """获取节日选项"""
        return [
            "全部节日",
            "万圣节", 
            "圣诞节",
            "春节",
            "情人节", 
            "母亲节",
            "父亲节",
            "感恩节"
        ]
    
    def _search_templates(self, query: str, category: str, holiday: str) -> List[Dict[str, Any]]:
        """搜索模板"""
        try:
            # 执行搜索
            if query:
                results = self.search_engine.search_templates(query, limit=20)
            else:
                # 获取所有模板
                all_templates = self.template_manager.get_available_templates()
                results = [
                    {
                        "template_id": t.id,
                        "config": t.to_dict(),
                        "score": 1.0,
                        "match_reasons": []
                    }
                    for t in all_templates
                ]
            
            # 应用分类筛选
            if category != "全部分类":
                results = [r for r in results if r["config"].get("category") == category]
            
            # 应用节日筛选
            if holiday != "全部节日":
                results = [r for r in results if r["config"].get("holiday") == holiday]
            
            return results
            
        except Exception as e:
            st.error(f"搜索失败: {e}")
            return []
    
    def _render_template_grid(self, templates: List[Dict[str, Any]], search_query: str) -> Optional[str]:
        """渲染模板网格"""
        if not templates:
            self._render_empty_state(search_query)
            return None
        
        st.markdown(f"**📋 找到 {len(templates)} 个模板**")
        
        # 分页显示
        templates_per_page = 6
        total_pages = (len(templates) + templates_per_page - 1) // templates_per_page
        
        if total_pages > 1:
            page = st.selectbox("页码", range(1, total_pages + 1)) - 1
        else:
            page = 0
        
        start_idx = page * templates_per_page
        end_idx = min(start_idx + templates_per_page, len(templates))
        page_templates = templates[start_idx:end_idx]
        
        # 网格布局显示模板
        cols = st.columns(3)
        selected_template_id = None
        
        for i, template_data in enumerate(page_templates):
            col_idx = i % 3
            template_config = template_data["config"]
            template_id = template_data["template_id"]
            
            with cols[col_idx]:
                # 模板卡片
                with st.container():
                    # 预览图
                    preview_image = self._get_template_preview(template_id, template_config)
                    st.image(preview_image, use_container_width=True)
                    
                    # 模板信息
                    st.markdown(f"**{template_config['name']}**")
                    st.caption(f"📂 {template_config.get('category', '未分类')}")
                    
                    # 标签
                    if template_config.get('tags'):
                        tags_text = " ".join([f"#{tag}" for tag in template_config['tags'][:3]])
                        st.caption(f"🏷️ {tags_text}")
                    
                    # 匹配信息
                    if template_data.get('match_reasons'):
                        st.success(f"✨ {template_data['match_reasons'][0]}")
                    
                    # 选择按钮
                    if st.button(f"选择此模板", key=f"select_{template_id}_{i}"):
                        selected_template_id = template_id
                        st.session_state.selected_template_id = template_id
        
        return selected_template_id or st.session_state.get('selected_template_id')
    
    def _render_empty_state(self, search_query: str):
        """渲染空状态"""
        if search_query:
            st.warning("🔍 未找到匹配的模板")
            st.info("💡 尝试使用其他关键词或调整筛选条件")
        else:
            st.info("📁 模板库为空")
            
            # 提供上传功能的提示
            with st.expander("📤 上传新模板"):
                st.markdown("""
                **管理员功能：**
                - 上传模板文件
                - 设置模板分类和标签
                - 配置可替换区域
                
                请联系管理员添加模板到库中。
                """)
    
    def _get_template_preview(self, template_id: str, template_config: Dict[str, Any]) -> str:
        """获取模板预览图"""
        # 根据模板类型生成不同颜色的预览图
        color_map = {
            "电子产品": "2196F3",
            "美妆护肤": "E91E63",
            "家居用品": "FF9800", 
            "运动户外": "4CAF50",
            "母婴用品": "FF69B4",
            "服装配饰": "9C27B0"
        }
        
        category = template_config.get('category', '其他')
        color = color_map.get(category, "607D8B")
        
        # 生成预览图URL
        template_name = template_config['name'].replace(' ', '+')
        return f"https://via.placeholder.com/300x200/{color}/white?text={template_name}"
    
    def _render_template_details(self, template_id: str):
        """渲染模板详细信息"""
        try:
            template = self.template_manager.load_template(template_id)
            if not template:
                st.error("模板加载失败")
                return
            
            with st.expander("📋 模板详细信息", expanded=True):
                col_info, col_preview = st.columns([1, 1])
                
                with col_info:
                    st.markdown(f"**名称:** {template.name}")
                    st.markdown(f"**分类:** {template.category}")
                    st.markdown(f"**描述:** {template.description}")
                    
                    if template.holiday:
                        st.markdown(f"**节日:** {template.holiday}")
                    
                    if template.tags:
                        tags_text = ", ".join(template.tags)
                        st.markdown(f"**标签:** {tags_text}")
                    
                    if template.color_schemes:
                        st.markdown(f"**配色方案:** {', '.join(template.color_schemes)}")
                    
                    if template.sections:
                        st.markdown(f"**包含模块:** {', '.join(template.sections)}")
                
                with col_preview:
                    # 显示更大的预览图
                    preview_image = self._get_template_preview(template_id, template.to_dict())
                    st.image(preview_image, caption="模板预览", use_container_width=True)
                    
                    # 可替换区域信息
                    if template.replaceable_areas:
                        st.markdown("**可替换区域:**")
                        for area_name, area in template.replaceable_areas.items():
                            st.caption(f"• {area_name} ({area.type})")
            
            # 相似模板推荐
            self._render_similar_templates(template_id)
            
        except Exception as e:
            st.error(f"加载模板详情失败: {e}")
    
    def _render_similar_templates(self, template_id: str):
        """渲染相似模板推荐"""
        try:
            similar_templates = self.search_engine.get_similar_templates(template_id, limit=3)
            
            if similar_templates:
                with st.expander("🔗 相似模板推荐"):
                    for sim_template in similar_templates:
                        config = sim_template["config"]
                        similarity = sim_template.get("similarity_score", 0)
                        
                        col_sim_info, col_sim_btn = st.columns([3, 1])
                        
                        with col_sim_info:
                            st.markdown(f"**{config['name']}**")
                            st.caption(f"📂 {config.get('category', '')} | 相似度: {similarity:.1f}")
                        
                        with col_sim_btn:
                            if st.button("选择", key=f"sim_{sim_template['template_id']}"):
                                st.session_state.selected_template_id = sim_template['template_id']
                                st.rerun()
                                
        except Exception as e:
            st.warning(f"加载相似模板失败: {e}")
    
    def render_compact(self) -> Optional[str]:
        """
        渲染紧凑版模板选择器
        
        Returns:
            选中的模板ID
        """
        st.markdown("**🎨 选择模板**")
        
        # 简化的搜索
        search_query = st.text_input("搜索模板", placeholder="输入关键词...")
        
        # 获取模板列表
        if search_query:
            templates = self.search_engine.search_templates(search_query, limit=10)
        else:
            all_templates = self.template_manager.get_available_templates()
            templates = [
                {
                    "template_id": t.id,
                    "config": t.to_dict()
                }
                for t in all_templates[:10]
            ]
        
        if not templates:
            st.warning("未找到模板")
            return None
        
        # 下拉选择
        template_options = {}
        for template_data in templates:
            config = template_data["config"]
            display_name = f"{config['name']} ({config.get('category', '未分类')})"
            template_options[display_name] = template_data["template_id"]
        
        selected_name = st.selectbox("选择模板", list(template_options.keys()))
        return template_options[selected_name]