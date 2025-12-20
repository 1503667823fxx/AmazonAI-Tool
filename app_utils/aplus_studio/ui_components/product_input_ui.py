"""
产品信息输入界面组件
实现产品信息收集和文件上传功能
"""

import streamlit as st
from typing import Dict, List, Optional, Any, Tuple
from PIL import Image
import io
import base64

from ..interfaces import IFileUploadHandler
from ..models.core_models import ProductData, UploadedFile


class ProductInputUI:
    """产品信息输入界面组件"""
    
    def __init__(self, file_upload_handler: IFileUploadHandler):
        """
        初始化产品信息输入界面
        
        Args:
            file_upload_handler: 文件上传处理器
        """
        self.file_upload_handler = file_upload_handler
        
    def render(self) -> Optional[ProductData]:
        """
        渲染产品信息输入界面
        
        Returns:
            收集到的产品数据，如果未完成则返回None
        """
        st.markdown("### 📦 产品信息")
        
        # 基本产品信息
        product_info = self._render_basic_info()
        
        # 产品图片上传
        uploaded_images = self._render_image_upload()
        
        # 产品特性
        features = self._render_features_input()
        
        # 品牌信息
        brand_info = self._render_brand_info()
        
        # 实时验证
        validation_result = self._validate_input(product_info, features, brand_info, uploaded_images)
        
        # 显示验证结果
        self._render_validation_feedback(validation_result)
        
        # 如果验证通过，返回产品数据
        if validation_result["is_valid"]:
            return self._create_product_data(product_info, features, brand_info, uploaded_images)
        
        return None
    
    def _render_basic_info(self) -> Dict[str, str]:
        """渲染基本产品信息输入"""
        st.markdown("**基本信息**")
        
        col_name, col_category = st.columns([2, 1])
        
        with col_name:
            product_name = st.text_input(
                "产品名称 *",
                placeholder="例: 无线蓝牙耳机 Pro Max",
                help="请输入完整的产品名称"
            )
        
        with col_category:
            product_category = st.selectbox(
                "产品类别 *",
                options=[
                    "请选择类别",
                    "电子产品",
                    "美妆护肤", 
                    "家居用品",
                    "运动户外",
                    "服装配饰",
                    "母婴用品",
                    "食品饮料",
                    "图书文具",
                    "其他"
                ]
            )
        
        # 产品描述
        product_description = st.text_area(
            "产品描述",
            placeholder="简要描述产品的主要功能和特点...",
            height=100,
            help="可选，但建议填写以获得更好的AI处理效果"
        )
        
        return {
            "name": product_name,
            "category": product_category if product_category != "请选择类别" else "",
            "description": product_description
        }
    
    def _render_image_upload(self) -> List[UploadedFile]:
        """渲染图片上传区域"""
        st.markdown("**产品图片 ***")
        
        # 上传区域
        uploaded_files = st.file_uploader(
            "上传产品图片 (1-5张)",
            type=["jpg", "jpeg", "png", "webp"],
            accept_multiple_files=True,
            help="支持 JPG、PNG、WebP 格式，单个文件不超过 10MB"
        )
        
        uploaded_images = []
        
        if uploaded_files:
            # 验证和处理上传的文件
            for i, uploaded_file in enumerate(uploaded_files[:5]):  # 最多5张
                try:
                    # 创建UploadedFile对象
                    file_data = UploadedFile(
                        filename=uploaded_file.name,
                        content_type=uploaded_file.type,
                        size=uploaded_file.size,
                        data=uploaded_file.read()
                    )
                    
                    # 验证文件
                    validation_errors = self.file_upload_handler.validate_file(file_data)
                    
                    if validation_errors:
                        st.error(f"文件 {uploaded_file.name} 验证失败: {'; '.join(validation_errors)}")
                        continue
                    
                    uploaded_images.append(file_data)
                    
                    # 显示预览
                    col_preview, col_info = st.columns([1, 2])
                    
                    with col_preview:
                        try:
                            image = Image.open(io.BytesIO(file_data.data))
                            st.image(image, caption=f"图片 {i+1}", use_container_width=True)
                        except Exception as e:
                            st.error(f"图片预览失败: {e}")
                    
                    with col_info:
                        st.markdown(f"**文件名:** {file_data.filename}")
                        st.markdown(f"**大小:** {self._format_file_size(file_data.size)}")
                        st.markdown(f"**类型:** {file_data.content_type}")
                        
                        # 图片信息
                        try:
                            image = Image.open(io.BytesIO(file_data.data))
                            st.markdown(f"**尺寸:** {image.width} × {image.height}")
                        except:
                            pass
                
                except Exception as e:
                    st.error(f"处理文件 {uploaded_file.name} 时出错: {e}")
        
        # 上传提示
        if not uploaded_images:
            st.info("📸 请上传至少一张产品图片")
        elif len(uploaded_images) < len(uploaded_files):
            st.warning("⚠️ 部分文件上传失败，请检查文件格式和大小")
        
        return uploaded_images
    
    def _render_features_input(self) -> List[str]:
        """渲染产品特性输入"""
        st.markdown("**产品卖点 ***")
        st.caption("请输入产品的主要卖点和特色功能（至少1个，最多5个）")
        
        features = []
        
        # 动态特性输入
        if 'feature_count' not in st.session_state:
            st.session_state.feature_count = 1
        
        for i in range(st.session_state.feature_count):
            col_input, col_btn = st.columns([4, 1])
            
            with col_input:
                feature = st.text_input(
                    f"卖点 {i+1}",
                    key=f"feature_{i}",
                    placeholder="例: 主动降噪技术 / 30小时续航 / 快速充电",
                    help="简洁明了地描述产品优势"
                )
                
                if feature.strip():
                    features.append(feature.strip())
            
            with col_btn:
                if i == st.session_state.feature_count - 1 and i < 4:  # 最后一个且未达到上限
                    if st.button("➕", key=f"add_feature_{i}", help="添加更多卖点"):
                        st.session_state.feature_count += 1
                        st.rerun()
                elif i > 0:  # 不是第一个
                    if st.button("➖", key=f"remove_feature_{i}", help="删除此卖点"):
                        st.session_state.feature_count -= 1
                        st.rerun()
        
        return features
    
    def _render_brand_info(self) -> Dict[str, str]:
        """渲染品牌信息输入"""
        st.markdown("**品牌信息**")
        
        col_brand, col_color = st.columns([2, 1])
        
        with col_brand:
            brand_name = st.text_input(
                "品牌名称 *",
                placeholder="例: TechPro",
                help="请输入品牌的正式名称"
            )
        
        with col_color:
            brand_color = st.color_picker(
                "品牌主色调 *",
                value="#FF6B6B",
                help="选择品牌的主要颜色，用于AI生成时的色彩搭配"
            )
        
        # 品牌描述
        brand_description = st.text_area(
            "品牌理念",
            placeholder="简要描述品牌的理念、定位或特色...",
            height=80,
            help="可选，有助于AI更好地理解品牌风格"
        )
        
        return {
            "name": brand_name,
            "color": brand_color,
            "description": brand_description
        }
    
    def _validate_input(self, product_info: Dict[str, str], features: List[str], 
                       brand_info: Dict[str, str], images: List[UploadedFile]) -> Dict[str, Any]:
        """验证输入数据"""
        errors = []
        warnings = []
        
        # 验证必填字段
        if not product_info["name"]:
            errors.append("产品名称不能为空")
        
        if not product_info["category"]:
            errors.append("请选择产品类别")
        
        if not features:
            errors.append("请至少输入一个产品卖点")
        
        if not brand_info["name"]:
            errors.append("品牌名称不能为空")
        
        if not images:
            errors.append("请至少上传一张产品图片")
        
        # 验证数据质量
        if product_info["name"] and len(product_info["name"]) < 3:
            warnings.append("产品名称建议至少3个字符")
        
        if len(features) < 2:
            warnings.append("建议添加更多产品卖点以获得更好效果")
        
        if not product_info["description"]:
            warnings.append("建议添加产品描述以获得更好的AI处理效果")
        
        if len(images) < 2:
            warnings.append("建议上传多张图片以获得更好的合成效果")
        
        return {
            "is_valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }
    
    def _render_validation_feedback(self, validation_result: Dict[str, Any]):
        """渲染验证反馈"""
        if validation_result["errors"]:
            st.error("❌ 请完善以下必填信息:")
            for error in validation_result["errors"]:
                st.error(f"• {error}")
        
        if validation_result["warnings"]:
            with st.expander("💡 优化建议", expanded=False):
                for warning in validation_result["warnings"]:
                    st.warning(f"• {warning}")
        
        if validation_result["is_valid"]:
            st.success("✅ 产品信息已完善，可以进行下一步")
    
    def _create_product_data(self, product_info: Dict[str, str], features: List[str],
                           brand_info: Dict[str, str], images: List[UploadedFile]) -> ProductData:
        """创建产品数据对象"""
        additional_info = {}
        
        if product_info["description"]:
            additional_info["description"] = product_info["description"]
        
        if brand_info["description"]:
            additional_info["brand_description"] = brand_info["description"]
        
        return ProductData(
            name=product_info["name"],
            category=product_info["category"],
            features=features,
            brand_name=brand_info["name"],
            brand_color=brand_info["color"],
            images=images,
            additional_info=additional_info
        )
    
    def _format_file_size(self, size_bytes: int) -> str:
        """格式化文件大小"""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        else:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
    
    def render_compact(self) -> Optional[ProductData]:
        """
        渲染紧凑版产品信息输入
        
        Returns:
            产品数据对象
        """
        st.markdown("**📦 产品信息**")
        
        # 基本信息
        product_name = st.text_input("产品名称", placeholder="输入产品名称...")
        product_category = st.selectbox("类别", ["电子产品", "美妆护肤", "家居用品", "其他"])
        
        # 简化的特性输入
        features_text = st.text_area(
            "产品卖点",
            placeholder="每行一个卖点...",
            height=100
        )
        features = [f.strip() for f in features_text.split('\n') if f.strip()]
        
        # 品牌信息
        col_brand, col_color = st.columns(2)
        with col_brand:
            brand_name = st.text_input("品牌名称", placeholder="品牌名称...")
        with col_color:
            brand_color = st.color_picker("品牌色", "#FF6B6B")
        
        # 图片上传
        uploaded_files = st.file_uploader(
            "产品图片",
            type=["jpg", "png"],
            accept_multiple_files=True
        )
        
        # 处理上传的文件
        images = []
        if uploaded_files:
            for uploaded_file in uploaded_files:
                file_data = UploadedFile(
                    filename=uploaded_file.name,
                    content_type=uploaded_file.type,
                    size=uploaded_file.size,
                    data=uploaded_file.read()
                )
                images.append(file_data)
        
        # 验证并返回数据
        if product_name and product_category and features and brand_name and images:
            return ProductData(
                name=product_name,
                category=product_category,
                features=features,
                brand_name=brand_name,
                brand_color=brand_color,
                images=images
            )
        
        return None