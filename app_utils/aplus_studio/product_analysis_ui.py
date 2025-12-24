"""
A+ 智能工作流产品分析界面组件

该模块提供产品分析阶段的用户界面，包括图片上传、分析进度显示、结果展示和错误处理。
支持多图片上传、实时验证、分析进度跟踪和结果预览功能。
"""

import streamlit as st
from typing import List, Optional, Dict, Any, Tuple
from PIL import Image
import io
import time
from datetime import datetime
from dataclasses import dataclass
import logging

from services.aplus_studio.models import ProductInfo, WorkflowState
from services.aplus_studio.product_analysis_service import ProductAnalysisService
from services.aplus_studio.intelligent_workflow import IntelligentWorkflowController

logger = logging.getLogger(__name__)


@dataclass
class AnalysisProgress:
    """分析进度跟踪"""
    stage: str
    progress: float  # 0.0 to 1.0
    message: str
    start_time: Optional[float] = None
    estimated_remaining: Optional[float] = None


class ProductAnalysisUI:
    """产品分析界面组件"""
    
    def __init__(self, workflow_controller: IntelligentWorkflowController):
        self.workflow_controller = workflow_controller
        self.analysis_service = ProductAnalysisService()
        
        # 配置参数
        self.max_images = 5
        self.supported_formats = ["jpg", "jpeg", "png", "webp"]
        self.max_file_size = 10 * 1024 * 1024  # 10MB
        self.min_description_length = 50
        
        # 分析阶段配置
        self.analysis_stages = {
            "image_processing": {"name": "图片处理", "weight": 0.2},
            "feature_extraction": {"name": "特征提取", "weight": 0.3},
            "category_analysis": {"name": "类别分析", "weight": 0.2},
            "insight_generation": {"name": "洞察生成", "weight": 0.3}
        }
    
    def render_analysis_interface(self) -> Dict[str, Any]:
        """
        渲染完整的产品分析界面
        
        Returns:
            Dict: 包含用户操作和分析结果的字典
        """
        st.subheader("🔍 产品分析")
        
        # 检查当前会话状态
        session = self.workflow_controller.state_manager.get_current_session()
        
        # 如果已有分析结果，显示结果界面
        if session and session.product_analysis:
            return self._render_analysis_results(session.product_analysis)
        
        # 检查是否正在进行分析（通过session_state标记）
        if st.session_state.get('analysis_in_progress', False):
            return self._render_analysis_progress()
        
        # 否则显示输入界面
        return self._render_input_interface()
    
    def _render_input_interface(self) -> Dict[str, Any]:
        """渲染产品信息输入界面"""
        
        st.write("**上传产品图片和信息，开始AI智能分析**")
        
        with st.form("product_analysis_form", clear_on_submit=False):
            # 图片上传区域
            uploaded_images = self._render_image_upload_section()
            
            # 产品描述输入
            product_description = self._render_description_input()
            
            # 可选的产品元数据
            product_metadata = self._render_metadata_input()
            
            # 分析选项
            analysis_options = self._render_analysis_options()
            
            # 提交按钮
            col1, col2 = st.columns([3, 1])
            
            with col1:
                submitted = st.form_submit_button(
                    "🚀 开始AI产品分析",
                    type="primary",
                    use_container_width=True
                )
            
            with col2:
                if st.form_submit_button("💾 保存草稿", use_container_width=True):
                    self._save_draft(uploaded_images, product_description, product_metadata)
                    st.success("草稿已保存")
            
            if submitted:
                # 验证输入
                validation_result = self._validate_inputs(
                    uploaded_images, product_description, product_metadata
                )
                
                if validation_result["is_valid"]:
                    # 创建产品信息对象
                    product_info = ProductInfo(
                        name=product_metadata.get("name", ""),
                        category=product_metadata.get("category", ""),
                        description=product_description,
                        key_features=self._extract_key_features(product_description),
                        target_audience=product_metadata.get("target_audience", ""),
                        price_range=product_metadata.get("price_range", ""),
                        uploaded_images=uploaded_images
                    )
                    
                    return {
                        "action": "start_analysis",
                        "product_info": product_info,
                        "analysis_options": analysis_options
                    }
                else:
                    # 显示验证错误
                    self._display_validation_errors(validation_result)
        
        # 显示使用指南
        self._render_usage_guide()
        
        return {"action": None}
    
    def _render_image_upload_section(self) -> List[Image.Image]:
        """渲染图片上传区域"""
        
        st.write("**📸 产品图片上传**")
        
        # 帮助信息
        with st.expander("📋 图片上传指南", expanded=False):
            st.markdown(f"""
            **图片要求：**
            - 📏 **格式**：{', '.join(self.supported_formats).upper()}
            - 📐 **尺寸**：建议最小 600x600 像素
            - 💾 **大小**：单张最大 {self.max_file_size // (1024*1024)}MB
            - 🔢 **数量**：1-{self.max_images} 张
            
            **建议包含：**
            - 🎯 主产品图（白底或透明背景）
            - 📐 多角度展示图
            - 🔍 细节特写图
            - 📦 包装或配件图
            - 🏠 使用场景图（可选）
            
            **AI分析效果：**
            - 更多角度的图片 → 更准确的产品识别
            - 高质量图片 → 更精确的材质和工艺分析
            - 使用场景图 → 更好的目标用户分析
            """)
        
        # 文件上传组件
        uploaded_files = st.file_uploader(
            "选择产品图片",
            type=self.supported_formats,
            accept_multiple_files=True,
            help=f"支持 {', '.join(self.supported_formats).upper()} 格式，最多 {self.max_images} 张",
            label_visibility="collapsed"
        )
        
        images = []
        
        if uploaded_files:
            # 验证文件数量
            if len(uploaded_files) > self.max_images:
                st.error(f"❌ 图片数量超限：{len(uploaded_files)}/{self.max_images}")
                uploaded_files = uploaded_files[:self.max_images]
            
            # 处理和显示图片
            st.write(f"已上传 {len(uploaded_files)} 张图片：")
            
            # 网格显示图片
            cols_per_row = 3
            rows = (len(uploaded_files) + cols_per_row - 1) // cols_per_row
            
            for row in range(rows):
                cols = st.columns(cols_per_row)
                for col_idx in range(cols_per_row):
                    file_idx = row * cols_per_row + col_idx
                    if file_idx < len(uploaded_files):
                        file = uploaded_files[file_idx]
                        
                        with cols[col_idx]:
                            try:
                                # 验证和加载图片
                                validation = self._validate_image_file(file)
                                
                                if validation["is_valid"]:
                                    img = Image.open(file)
                                    images.append(img)
                                    
                                    # 显示图片
                                    st.image(img, use_container_width=True, caption=file.name)
                                    
                                    # 显示图片信息
                                    file_size_kb = file.size // 1024
                                    st.caption(f"{img.size[0]}×{img.size[1]} • {file_size_kb}KB")
                                    
                                    # 质量评估
                                    quality_score = self._assess_image_quality(img)
                                    quality_color = "green" if quality_score > 0.7 else "orange" if quality_score > 0.4 else "red"
                                    st.markdown(f"<span style='color: {quality_color}'>质量: {quality_score:.1f}/1.0</span>", 
                                              unsafe_allow_html=True)
                                else:
                                    # 显示验证错误
                                    st.error(f"❌ {file.name}")
                                    for error in validation["errors"]:
                                        st.caption(f"• {error}")
                                        
                            except Exception as e:
                                st.error(f"❌ 无法加载 {file.name}: {str(e)}")
            
            # 图片分析预览
            if images:
                self._render_image_analysis_preview(images)
        
        return images
    
    def _render_description_input(self) -> str:
        """渲染产品描述输入区域"""
        
        st.write("**📝 产品描述**")
        
        # 帮助信息
        with st.expander("✍️ 描述输入指南", expanded=False):
            st.markdown("""
            **请包含以下信息以获得最佳分析效果：**
            
            - 🏷️ **产品名称和品牌**
            - 📝 **详细产品描述**
            - ⭐ **核心特点和卖点**
            - 🔧 **技术规格参数**
            - 👥 **目标用户群体**
            - 💰 **价格区间信息**
            - 🏆 **竞争优势说明**
            
            **AI分析优势：**
            - 详细描述 → 更准确的产品分类
            - 技术规格 → 更精确的模块推荐
            - 用户群体 → 更合适的营销角度
            """)
        
        # 文本输入区域
        description = st.text_area(
            "输入产品详细描述",
            placeholder="请输入完整的产品描述，包括产品名称、特点、规格、卖点等信息...\n\n示例：\n产品名称：Apple iPhone 15 Pro\n产品类别：智能手机\n核心特点：\n- A17 Pro芯片，性能强劲\n- 钛金属机身，轻盈耐用\n- 48MP主摄像头，专业摄影\n技术规格：6.1英寸屏幕，128GB存储...",
            height=200,
            help=f"建议长度：{self.min_description_length}+ 字符，详细描述有助于AI更准确分析",
            label_visibility="collapsed"
        )
        
        # 实时字符统计和质量评估
        if description:
            char_count = len(description)
            word_count = len(description.split())
            completeness_score = self._calculate_description_completeness(description)
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if char_count < self.min_description_length:
                    st.warning(f"⚠️ 内容较短 ({char_count}/{self.min_description_length}+)")
                else:
                    st.success(f"✅ 长度合适 ({char_count} 字符)")
            
            with col2:
                st.metric("词数", word_count)
            
            with col3:
                color = "green" if completeness_score > 70 else "orange" if completeness_score > 40 else "red"
                st.markdown(f"<span style='color: {color}'>完整度: {completeness_score}%</span>", 
                          unsafe_allow_html=True)
        
        return description
    
    def _render_metadata_input(self) -> Dict[str, Any]:
        """渲染产品元数据输入区域"""
        
        st.write("**📊 产品信息补充**")
        
        col1, col2 = st.columns(2)
        
        with col1:
            product_name = st.text_input(
                "产品名称",
                placeholder="例：Apple iPhone 15 Pro",
                help="产品的完整名称，有助于AI理解产品定位"
            )
            
            category = st.selectbox(
                "产品类别",
                [
                    "请选择...",
                    "电子产品", "家居用品", "服装配饰", "美容护理",
                    "运动户外", "汽车用品", "母婴用品", "食品饮料",
                    "图书文具", "工具设备", "其他"
                ],
                help="选择最符合的产品类别"
            )
        
        with col2:
            target_audience = st.selectbox(
                "目标用户",
                [
                    "请选择...",
                    "年轻专业人士 (25-35岁)", "中产家庭 (30-45岁)",
                    "高端消费者 (35-55岁)", "学生群体 (18-25岁)",
                    "老年用户 (55+岁)", "企业用户", "通用人群"
                ],
                help="主要目标用户群体"
            )
            
            price_range = st.selectbox(
                "价格区间",
                [
                    "请选择...",
                    "$0-25 (经济型)", "$25-50 (中低端)", "$50-100 (中端)",
                    "$100-200 (中高端)", "$200-500 (高端)", "$500+ (奢侈品)"
                ],
                help="产品的大致价格区间"
            )
        
        return {
            "name": product_name,
            "category": category if category != "请选择..." else "",
            "target_audience": target_audience if target_audience != "请选择..." else "",
            "price_range": price_range if price_range != "请选择..." else ""
        }
    
    def _render_analysis_options(self) -> Dict[str, Any]:
        """渲染分析选项配置"""
        
        with st.expander("🔧 分析选项", expanded=False):
            col1, col2 = st.columns(2)
            
            with col1:
                analysis_depth = st.selectbox(
                    "分析深度",
                    ["标准分析", "深度分析", "专业分析"],
                    index=1,
                    help="更深度的分析需要更长时间但结果更准确"
                )
                
                include_competitor_analysis = st.checkbox(
                    "包含竞品分析",
                    value=False,
                    help="分析同类产品的特点和差异化优势"
                )
            
            with col2:
                language_preference = st.selectbox(
                    "分析语言",
                    ["中文", "English", "自动检测"],
                    index=0,
                    help="AI分析和结果展示的语言"
                )
                
                save_analysis_data = st.checkbox(
                    "保存分析数据",
                    value=True,
                    help="保存详细的分析数据用于后续优化"
                )
        
        return {
            "analysis_depth": analysis_depth,
            "include_competitor_analysis": include_competitor_analysis,
            "language_preference": language_preference,
            "save_analysis_data": save_analysis_data
        }
    
    def _render_analysis_progress(self) -> Dict[str, Any]:
        """渲染分析进度界面"""
        
        st.write("**🔄 AI正在分析您的产品...**")
        
        # 获取当前分析进度
        progress_data = st.session_state.get("analysis_progress", {})
        
        if not progress_data:
            # 初始化进度数据
            progress_data = {
                "current_stage": "image_processing",
                "overall_progress": 0.0,
                "stage_progress": 0.0,
                "start_time": time.time(),
                "estimated_total_time": 60,  # 60秒预估
                "messages": []
            }
            st.session_state.analysis_progress = progress_data
        
        # 计算总体进度
        current_stage = progress_data["current_stage"]
        stage_weights = [self.analysis_stages[stage]["weight"] for stage in self.analysis_stages.keys()]
        completed_weight = sum(stage_weights[:list(self.analysis_stages.keys()).index(current_stage)])
        current_stage_weight = self.analysis_stages[current_stage]["weight"]
        stage_progress = progress_data["stage_progress"]
        
        overall_progress = completed_weight + (current_stage_weight * stage_progress)
        
        # 显示总体进度
        st.progress(overall_progress, text=f"总体进度: {overall_progress*100:.0f}%")
        
        # 显示当前阶段
        stage_name = self.analysis_stages[current_stage]["name"]
        st.write(f"**当前阶段：{stage_name}**")
        st.progress(stage_progress, text=f"阶段进度: {stage_progress*100:.0f}%")
        
        # 显示预估剩余时间
        elapsed_time = time.time() - progress_data["start_time"]
        if overall_progress > 0:
            estimated_total = elapsed_time / overall_progress
            estimated_remaining = max(0, estimated_total - elapsed_time)
            st.info(f"⏱️ 预计剩余时间: {estimated_remaining:.0f} 秒")
        
        # 显示分析阶段详情
        with st.expander("📋 分析阶段详情", expanded=True):
            for i, (stage_key, stage_info) in enumerate(self.analysis_stages.items()):
                stage_status = "✅" if i < list(self.analysis_stages.keys()).index(current_stage) else \
                              "🔄" if stage_key == current_stage else "⏳"
                
                st.write(f"{stage_status} **{stage_info['name']}** ({stage_info['weight']*100:.0f}%)")
        
        # 显示实时消息
        if progress_data["messages"]:
            with st.expander("📝 分析日志", expanded=False):
                for message in progress_data["messages"][-10:]:  # 显示最近10条消息
                    st.text(f"[{message['time']}] {message['text']}")
        
        # 取消按钮
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col2:
            if st.button("⏹️ 取消分析", type="secondary"):
                return {"action": "cancel_analysis"}
        
        with col3:
            if st.button("🔄 刷新状态"):
                return {"action": "refresh_progress"}
        
        # 模拟进度更新（在实际实现中，这应该由后台任务更新）
        if st.button("🔄 更新进度", key="update_progress_hidden", type="primary", 
                    help="点击更新分析进度", disabled=False):
            return {"action": "update_progress"}
        
        return {"action": "check_progress"}
    
    def _render_analysis_results(self, analysis_result) -> Dict[str, Any]:
        """渲染分析结果界面"""
        
        st.write("**✅ 产品分析完成**")
        
        # 分析摘要
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("产品类别", analysis_result.product_category)
        
        with col2:
            st.metric("置信度", f"{analysis_result.confidence_score:.1%}")
        
        with col3:
            st.metric("特征数量", len(analysis_result.key_features))
        
        with col4:
            analysis_time = getattr(analysis_result, 'analysis_time', 0)
            st.metric("分析时间", f"{analysis_time:.1f}s")
        
        # 详细分析结果
        tab1, tab2, tab3, tab4 = st.tabs(["🎯 核心洞察", "🏷️ 产品特征", "👥 用户画像", "📊 详细数据"])
        
        with tab1:
            self._render_core_insights(analysis_result)
        
        with tab2:
            self._render_product_features(analysis_result)
        
        with tab3:
            self._render_user_profile(analysis_result)
        
        with tab4:
            self._render_detailed_data(analysis_result)
        
        # 操作按钮
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            if st.button("➡️ 继续到模块推荐", type="primary", use_container_width=True):
                return {"action": "proceed_to_recommendation"}
        
        with col2:
            if st.button("🔄 重新分析", use_container_width=True):
                return {"action": "restart_analysis"}
        
        with col3:
            if st.button("📥 导出结果", use_container_width=True):
                return {"action": "export_results"}
        
        return {"action": None}
    
    def _render_core_insights(self, analysis_result) -> None:
        """渲染核心洞察"""
        
        st.write("**🎯 AI核心洞察**")
        
        # 产品定位
        if hasattr(analysis_result, 'product_positioning'):
            st.write("**产品定位：**")
            st.info(analysis_result.product_positioning)
        
        # 营销角度建议
        if hasattr(analysis_result, 'marketing_angles'):
            st.write("**推荐营销角度：**")
            for i, angle in enumerate(analysis_result.marketing_angles[:3], 1):
                st.write(f"{i}. {angle}")
        
        # 竞争优势
        if hasattr(analysis_result, 'competitive_advantages'):
            st.write("**竞争优势：**")
            for advantage in analysis_result.competitive_advantages:
                st.write(f"• {advantage}")
    
    def _render_product_features(self, analysis_result) -> None:
        """渲染产品特征"""
        
        st.write("**🏷️ 识别的产品特征**")
        
        # 主要特征
        if analysis_result.key_features:
            st.write("**核心特征：**")
            for feature in analysis_result.key_features:
                st.write(f"• {feature}")
        
        # 材质信息
        if hasattr(analysis_result, 'materials') and analysis_result.materials:
            st.write("**材质分析：**")
            for material in analysis_result.materials:
                st.write(f"• {material}")
        
        # 使用场景
        if hasattr(analysis_result, 'use_cases') and analysis_result.use_cases:
            st.write("**使用场景：**")
            for use_case in analysis_result.use_cases:
                st.write(f"• {use_case}")
    
    def _render_user_profile(self, analysis_result) -> None:
        """渲染用户画像"""
        
        st.write("**👥 目标用户画像**")
        
        if hasattr(analysis_result, 'target_audience'):
            st.write(f"**主要用户群体：** {analysis_result.target_audience}")
        
        # 用户需求分析
        if hasattr(analysis_result, 'user_needs'):
            st.write("**用户需求：**")
            for need in analysis_result.user_needs:
                st.write(f"• {need}")
        
        # 购买动机
        if hasattr(analysis_result, 'purchase_motivations'):
            st.write("**购买动机：**")
            for motivation in analysis_result.purchase_motivations:
                st.write(f"• {motivation}")
    
    def _render_detailed_data(self, analysis_result) -> None:
        """渲染详细数据"""
        
        st.write("**📊 详细分析数据**")
        
        # 置信度分布
        if hasattr(analysis_result, 'confidence_breakdown'):
            st.write("**置信度分布：**")
            for category, confidence in analysis_result.confidence_breakdown.items():
                st.write(f"• {category}: {confidence:.1%}")
        
        # 分析元数据
        st.write("**分析元数据：**")
        st.write(f"• 分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        st.write(f"• 产品ID: {getattr(analysis_result, 'product_id', 'N/A')}")
        st.write(f"• 分析版本: {getattr(analysis_result, 'analysis_version', '1.0')}")
        
        # 原始数据（可选）
        with st.expander("🔍 原始分析数据", expanded=False):
            st.json(analysis_result.__dict__ if hasattr(analysis_result, '__dict__') else {})
    
    def _validate_inputs(self, images: List[Image.Image], description: str, 
                        metadata: Dict[str, Any]) -> Dict[str, Any]:
        """验证输入数据"""
        
        errors = []
        warnings = []
        
        # 验证图片
        if not images:
            warnings.append("建议上传至少1张产品图片以获得更好的分析效果")
        elif len(images) > self.max_images:
            errors.append(f"图片数量超限，最多 {self.max_images} 张")
        
        # 验证描述
        if not description or not description.strip():
            errors.append("产品描述不能为空")
        elif len(description) < self.min_description_length:
            errors.append(f"产品描述过短，至少需要 {self.min_description_length} 字符")
        
        # 验证元数据
        if not metadata.get("name"):
            warnings.append("建议填写产品名称")
        
        if not metadata.get("category"):
            warnings.append("建议选择产品类别")
        
        # 检查描述完整度
        completeness = self._calculate_description_completeness(description)
        if completeness < 50:
            warnings.append("产品信息完整度较低，建议补充更多详细信息")
        
        return {
            "is_valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }
    
    def _validate_image_file(self, file) -> Dict[str, Any]:
        """验证单个图片文件"""
        
        errors = []
        warnings = []
        
        try:
            # 检查文件大小
            if hasattr(file, 'size') and file.size > self.max_file_size:
                errors.append(f"文件过大 ({file.size // (1024*1024)}MB > {self.max_file_size // (1024*1024)}MB)")
            
            # 检查文件格式
            file_extension = file.name.split('.')[-1].lower()
            if file_extension not in self.supported_formats:
                errors.append(f"不支持的格式 ({file_extension})")
            
            # 检查图片属性
            try:
                img = Image.open(file)
                width, height = img.size
                
                # 检查最小尺寸
                if width < 300 or height < 300:
                    warnings.append(f"分辨率较低 ({width}×{height})")
                
                # 检查宽高比
                aspect_ratio = width / height
                if aspect_ratio < 0.3 or aspect_ratio > 3.0:
                    warnings.append("图片比例可能不适合分析")
                
                file.seek(0)  # 重置文件指针
                
            except Exception as e:
                errors.append(f"无法读取图片: {str(e)}")
        
        except Exception as e:
            errors.append(f"文件验证失败: {str(e)}")
        
        return {
            "is_valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }
    
    def _assess_image_quality(self, image: Image.Image) -> float:
        """评估图片质量"""
        
        try:
            width, height = image.size
            
            # 基于分辨率的质量评分
            resolution_score = min(1.0, (width * height) / (600 * 600))
            
            # 基于宽高比的评分
            aspect_ratio = width / height
            aspect_score = 1.0 if 0.5 <= aspect_ratio <= 2.0 else 0.7
            
            # 基于文件格式的评分
            format_score = 1.0 if image.format in ['PNG', 'JPEG'] else 0.8
            
            # 综合评分
            quality_score = (resolution_score * 0.5 + aspect_score * 0.3 + format_score * 0.2)
            
            return quality_score
            
        except Exception as e:
            logger.warning(f"Image quality assessment failed: {str(e)}")
            return 0.5
    
    def _calculate_description_completeness(self, description: str) -> int:
        """计算描述完整度评分"""
        
        if not description:
            return 0
        
        score = 0
        text_lower = description.lower()
        
        # 检查关键要素
        key_elements = [
            ("产品名称", ["产品", "名称", "品牌", "型号"]),
            ("特点描述", ["特点", "优势", "功能", "特色", "亮点"]),
            ("技术规格", ["规格", "参数", "尺寸", "重量", "材质", "配置"]),
            ("使用场景", ["适用", "场景", "用途", "使用", "应用"]),
            ("目标用户", ["适合", "用户", "人群", "客户", "消费者"]),
            ("价格价值", ["价格", "价值", "性价比", "优惠", "经济"])
        ]
        
        for element_name, keywords in key_elements:
            if any(keyword in text_lower for keyword in keywords):
                score += 15
        
        # 长度奖励
        if len(description) >= self.min_description_length:
            score += 10
        
        return min(score, 100)
    
    def _extract_key_features(self, description: str) -> List[str]:
        """从描述中提取关键特征"""
        
        features = []
        
        # 简单的特征提取基于常见模式
        lines = description.split('\n')
        
        for line in lines:
            line = line.strip()
            
            # 查找项目符号或编号列表
            if line.startswith(('•', '-', '*', '·')) or \
               (len(line) > 0 and line[0].isdigit() and '.' in line[:3]):
                feature = line.lstrip('•-*·0123456789. ').strip()
                if len(feature) > 5 and len(feature) < 100:
                    features.append(feature)
        
        # 如果没有找到项目符号，提取包含关键词的句子
        if not features:
            sentences = description.replace('\n', ' ').split('。')
            
            key_words = ['特点', '优势', '功能', '特色', '亮点', '卖点', '优点']
            
            for sentence in sentences:
                sentence = sentence.strip()
                if any(word in sentence for word in key_words) and len(sentence) > 10:
                    features.append(sentence[:80] + ('...' if len(sentence) > 80 else ''))
        
        return features[:5]  # 返回前5个特征
    
    def _render_image_analysis_preview(self, images: List[Image.Image]) -> None:
        """渲染图片分析预览"""
        
        if not images:
            return
        
        with st.expander("🔍 图片分析预览", expanded=False):
            st.write("**图片统计：**")
            
            # 基本统计
            total_pixels = sum(img.size[0] * img.size[1] for img in images)
            avg_width = sum(img.size[0] for img in images) // len(images)
            avg_height = sum(img.size[1] for img in images) // len(images)
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("图片数量", len(images))
            
            with col2:
                st.metric("平均尺寸", f"{avg_width}×{avg_height}")
            
            with col3:
                avg_quality = sum(self._assess_image_quality(img) for img in images) / len(images)
                st.metric("平均质量", f"{avg_quality:.1f}")
            
            with col4:
                # 估算分析时间
                estimated_time = len(images) * 10 + 20  # 每张图片10秒 + 基础20秒
                st.metric("预计分析时间", f"{estimated_time}s")
            
            st.info("🎨 将在产品分析阶段进行详细的图片内容、色彩和材质分析")
    
    def _render_usage_guide(self) -> None:
        """渲染使用指南"""
        
        with st.expander("📖 使用指南", expanded=False):
            st.markdown("""
            ### 🚀 如何获得最佳分析效果
            
            **1. 图片准备**
            - 📸 上传清晰的产品图片，多角度展示
            - 🎯 包含主产品图和细节图
            - 💡 确保良好的光线和背景
            
            **2. 描述撰写**
            - ✍️ 详细描述产品特点和规格
            - 🏷️ 包含品牌、型号、材质等信息
            - 👥 说明目标用户和使用场景
            
            **3. 信息补充**
            - 📊 选择正确的产品类别
            - 💰 提供价格区间信息
            - 🎯 明确目标用户群体
            
            **4. 分析结果**
            - 🔍 AI将分析产品特征和定位
            - 💡 提供营销角度和用户洞察
            - 📈 为后续模块推荐提供依据
            """)
    
    def _save_draft(self, images: List[Image.Image], description: str, 
                   metadata: Dict[str, Any]) -> None:
        """保存草稿"""
        
        try:
            draft_data = {
                "description": description,
                "metadata": metadata,
                "image_count": len(images),
                "saved_at": datetime.now().isoformat()
            }
            
            st.session_state["analysis_draft"] = draft_data
            logger.info("Analysis draft saved")
            
        except Exception as e:
            logger.error(f"Failed to save draft: {str(e)}")
            st.error("草稿保存失败")
    
    def _display_validation_errors(self, validation_result: Dict[str, Any]) -> None:
        """显示验证错误和警告"""
        
        if validation_result["errors"]:
            st.error("❌ **输入验证失败：**")
            for error in validation_result["errors"]:
                st.write(f"• {error}")
        
        if validation_result["warnings"]:
            st.warning("⚠️ **建议改进：**")
            for warning in validation_result["warnings"]:
                st.write(f"• {warning}")
    
    def update_analysis_progress(self, stage: str, progress: float, message: str) -> None:
        """更新分析进度"""
        
        if "analysis_progress" not in st.session_state:
            st.session_state.analysis_progress = {}
        
        progress_data = st.session_state.analysis_progress
        progress_data["current_stage"] = stage
        progress_data["stage_progress"] = progress
        progress_data["messages"].append({
            "time": datetime.now().strftime("%H:%M:%S"),
            "text": message
        })
        
        # 限制消息数量
        if len(progress_data["messages"]) > 50:
            progress_data["messages"] = progress_data["messages"][-30:]
    
    def clear_analysis_progress(self) -> None:
        """清除分析进度"""
        
        if "analysis_progress" in st.session_state:
            del st.session_state.analysis_progress
    
    def get_analysis_summary(self) -> Dict[str, Any]:
        """获取分析摘要"""
        
        session = self.workflow_controller.state_manager.get_current_session()
        
        if not session or not session.product_analysis:
            return {"has_analysis": False}
        
        analysis = session.product_analysis
        
        return {
            "has_analysis": True,
            "product_category": analysis.product_category,
            "confidence_score": analysis.confidence_score,
            "key_features_count": len(analysis.key_features),
            "analysis_time": getattr(analysis, 'analysis_time', 0),
            "created_at": analysis.analysis_timestamp.isoformat() if hasattr(analysis, 'analysis_timestamp') else None
        }


# 全局实例，便于访问
def create_product_analysis_ui(workflow_controller: IntelligentWorkflowController) -> ProductAnalysisUI:
    """创建产品分析UI实例"""
    return ProductAnalysisUI(workflow_controller)
