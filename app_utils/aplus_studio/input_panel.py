"""
A+ Studio Product Input Panel Component
Provides specialized input interface for product listing and image upload
"""

import streamlit as st
from typing import List, Optional, Dict, Any, Tuple
from PIL import Image
import io
from dataclasses import dataclass
from services.aplus_studio.models import ProductInfo


@dataclass
class ValidationResult:
    """Input validation result"""
    is_valid: bool
    errors: List[str]
    warnings: List[str]


class ProductInputPanel:
    """Product input panel for A+ Studio workflow"""
    
    def __init__(self):
        self.max_images = 10
        self.supported_formats = ["jpg", "jpeg", "png", "webp"]
        self.max_file_size = 10 * 1024 * 1024  # 10MB
        self.min_listing_length = 50
        self.max_listing_length = 5000
    
    def render_input_panel(self) -> Tuple[Optional[ProductInfo], ValidationResult]:
        """
        Render the complete product input interface
        
        Returns:
            Tuple of (ProductInfo, ValidationResult)
        """
        st.subheader("📝 产品信息输入")
        
        # Create form for better UX
        with st.form("product_input_form", clear_on_submit=False):
            # Product listing text input
            listing_text = self._render_listing_input()
            
            # Product images upload
            product_images = self._render_image_upload()
            
            # Additional product metadata
            product_metadata = self._render_metadata_input()
            
            # Submit button
            submitted = st.form_submit_button(
                "🔍 开始产品分析", 
                type="primary",
                use_container_width=True
            )
            
            if submitted:
                # Validate inputs
                validation = self._validate_inputs(listing_text, product_images, product_metadata)
                
                if validation.is_valid:
                    # Create ProductInfo object
                    product_info = ProductInfo(
                        name=product_metadata.get("name", ""),
                        category=product_metadata.get("category", ""),
                        description=listing_text,
                        key_features=self._extract_key_features(listing_text),
                        target_audience=product_metadata.get("target_audience", ""),
                        price_range=product_metadata.get("price_range", ""),
                        uploaded_images=product_images
                    )
                    
                    return product_info, validation
                else:
                    # Show validation errors
                    self._display_validation_errors(validation)
                    return None, validation
        
        return None, ValidationResult(True, [], [])
    
    def _render_listing_input(self) -> str:
        """Render product listing text input with validation"""
        
        st.write("**产品Listing文本**")
        
        # Help text
        with st.expander("📋 Listing输入指南", expanded=False):
            st.markdown("""
            **请包含以下信息以获得最佳分析效果：**
            
            - 🏷️ **产品名称和品牌**
            - 📝 **详细产品描述**
            - ⭐ **核心特点和卖点**
            - 🔧 **技术规格参数**
            - 👥 **目标用户群体**
            - 💰 **价格区间信息**
            - 🏆 **竞争优势说明**
            
            **示例格式：**
            ```
            产品名称：[品牌] [产品名]
            产品类别：[类别]
            核心特点：
            - 特点1
            - 特点2
            技术规格：...
            ```
            """)
        
        listing_text = st.text_area(
            "输入产品Listing内容",
            placeholder="请输入完整的产品描述，包括产品名称、特点、规格、卖点等信息...",
            height=200,
            help=f"建议长度：{self.min_listing_length}-{self.max_listing_length}字符",
            label_visibility="collapsed"
        )
        
        # Real-time character count and validation
        if listing_text:
            char_count = len(listing_text)
            
            col1, col2, col3 = st.columns([2, 1, 1])
            
            with col1:
                if char_count < self.min_listing_length:
                    st.warning(f"⚠️ 内容较短 ({char_count}/{self.min_listing_length}字符)")
                elif char_count > self.max_listing_length:
                    st.error(f"❌ 内容过长 ({char_count}/{self.max_listing_length}字符)")
                else:
                    st.success(f"✅ 长度合适 ({char_count}字符)")
            
            with col2:
                # Word count
                word_count = len(listing_text.split())
                st.metric("词数", word_count)
            
            with col3:
                # Completeness score
                completeness = self._calculate_completeness_score(listing_text)
                st.metric("完整度", f"{completeness}%")
        
        return listing_text
    
    def _render_image_upload(self) -> List[Image.Image]:
        """Render product image upload interface"""
        
        st.write("**产品图片**")
        
        # Help text
        with st.expander("🖼️ 图片上传指南", expanded=False):
            st.markdown(f"""
            **图片要求：**
            
            - 📏 **格式**：{', '.join(self.supported_formats).upper()}
            - 📐 **尺寸**：建议最小 600x600 像素
            - 💾 **大小**：单张最大 {self.max_file_size // (1024*1024)}MB
            - 🔢 **数量**：最多 {self.max_images} 张
            
            **建议包含：**
            - 🎯 主产品图（白底或透明背景）
            - 📐 多角度展示图
            - 🔍 细节特写图
            - 📦 包装或配件图
            - 🏠 使用场景图
            """)
        
        uploaded_files = st.file_uploader(
            "上传产品图片",
            type=self.supported_formats,
            accept_multiple_files=True,
            help=f"支持 {', '.join(self.supported_formats).upper()} 格式，最多 {self.max_images} 张",
            label_visibility="collapsed"
        )
        
        images = []
        
        if uploaded_files:
            # Validate file count
            if len(uploaded_files) > self.max_images:
                st.error(f"❌ 图片数量超限：{len(uploaded_files)}/{self.max_images}")
                uploaded_files = uploaded_files[:self.max_images]
            
            # Process and display images
            st.write(f"已上传 {len(uploaded_files)} 张图片：")
            
            # Display images in grid
            cols_per_row = 4
            rows = (len(uploaded_files) + cols_per_row - 1) // cols_per_row
            
            for row in range(rows):
                cols = st.columns(cols_per_row)
                for col_idx in range(cols_per_row):
                    file_idx = row * cols_per_row + col_idx
                    if file_idx < len(uploaded_files):
                        file = uploaded_files[file_idx]
                        
                        with cols[col_idx]:
                            try:
                                # Validate file
                                validation = self._validate_image_file(file)
                                
                                if validation.is_valid:
                                    # Load and display image
                                    img = Image.open(file)
                                    images.append(img)
                                    
                                    st.image(img, use_container_width=True, caption=file.name)
                                    
                                    # Show image info
                                    st.caption(f"{img.size[0]}×{img.size[1]} • {file.size // 1024}KB")
                                    
                                else:
                                    # Show validation errors
                                    st.error(f"❌ {file.name}")
                                    for error in validation.errors:
                                        st.caption(f"• {error}")
                                        
                            except Exception as e:
                                st.error(f"❌ 无法加载 {file.name}: {str(e)}")
            
            # Image analysis preview
            if images:
                with st.expander("🔍 图片分析预览", expanded=False):
                    self._render_image_analysis_preview(images)
        
        return images
    
    def _render_metadata_input(self) -> Dict[str, Any]:
        """Render additional product metadata input"""
        
        st.write("**产品信息补充**")
        
        col1, col2 = st.columns(2)
        
        with col1:
            product_name = st.text_input(
                "产品名称",
                placeholder="例：Apple iPhone 15 Pro",
                help="产品的完整名称"
            )
            
            category = st.selectbox(
                "产品类别",
                [
                    "请选择...",
                    "电子产品",
                    "家居用品", 
                    "服装配饰",
                    "美容护理",
                    "运动户外",
                    "汽车用品",
                    "母婴用品",
                    "食品饮料",
                    "图书文具",
                    "其他"
                ]
            )
        
        with col2:
            target_audience = st.selectbox(
                "目标用户",
                [
                    "请选择...",
                    "年轻专业人士 (25-35岁)",
                    "中产家庭 (30-45岁)",
                    "高端消费者 (35-55岁)",
                    "学生群体 (18-25岁)",
                    "老年用户 (55+岁)",
                    "企业用户",
                    "通用人群"
                ]
            )
            
            price_range = st.selectbox(
                "价格区间",
                [
                    "请选择...",
                    "$0-25 (经济型)",
                    "$25-50 (中低端)",
                    "$50-100 (中端)",
                    "$100-200 (中高端)",
                    "$200-500 (高端)",
                    "$500+ (奢侈品)"
                ]
            )
        
        return {
            "name": product_name,
            "category": category if category != "请选择..." else "",
            "target_audience": target_audience if target_audience != "请选择..." else "",
            "price_range": price_range if price_range != "请选择..." else ""
        }
    
    def _validate_inputs(self, listing_text: str, images: List[Image.Image], 
                        metadata: Dict[str, Any]) -> ValidationResult:
        """Validate all inputs"""
        
        errors = []
        warnings = []
        
        # Validate listing text
        if not listing_text or not listing_text.strip():
            errors.append("产品Listing文本不能为空")
        elif len(listing_text) < self.min_listing_length:
            errors.append(f"Listing文本过短，至少需要 {self.min_listing_length} 字符")
        elif len(listing_text) > self.max_listing_length:
            errors.append(f"Listing文本过长，最多 {self.max_listing_length} 字符")
        
        # Validate images
        if not images:
            warnings.append("建议上传至少1张产品图片以获得更好的分析效果")
        elif len(images) > self.max_images:
            errors.append(f"图片数量超限，最多 {self.max_images} 张")
        
        # Validate metadata
        if not metadata.get("name"):
            warnings.append("建议填写产品名称")
        
        if not metadata.get("category"):
            warnings.append("建议选择产品类别")
        
        # Check completeness
        completeness = self._calculate_completeness_score(listing_text)
        if completeness < 60:
            warnings.append("产品信息完整度较低，建议补充更多详细信息")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    def _validate_image_file(self, file) -> ValidationResult:
        """Validate individual image file"""
        
        errors = []
        warnings = []
        
        try:
            # Check file size
            if hasattr(file, 'size') and file.size > self.max_file_size:
                errors.append(f"文件过大 ({file.size // (1024*1024)}MB > {self.max_file_size // (1024*1024)}MB)")
            
            # Check file format
            file_extension = file.name.split('.')[-1].lower()
            if file_extension not in self.supported_formats:
                errors.append(f"不支持的格式 ({file_extension})")
            
            # Check image properties
            try:
                img = Image.open(file)
                width, height = img.size
                
                # Check minimum dimensions
                if width < 300 or height < 300:
                    warnings.append(f"分辨率较低 ({width}×{height})")
                
                # Check aspect ratio
                aspect_ratio = width / height
                if aspect_ratio < 0.5 or aspect_ratio > 2.0:
                    warnings.append("图片比例可能不适合A+展示")
                
                file.seek(0)  # Reset file pointer
                
            except Exception as e:
                errors.append(f"无法读取图片: {str(e)}")
        
        except Exception as e:
            errors.append(f"文件验证失败: {str(e)}")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    def _calculate_completeness_score(self, text: str) -> int:
        """Calculate completeness score for listing text"""
        
        if not text:
            return 0
        
        score = 0
        text_lower = text.lower()
        
        # Check for key elements
        key_elements = [
            ("产品名称", ["产品", "名称", "品牌"]),
            ("特点描述", ["特点", "优势", "功能", "特色"]),
            ("技术规格", ["规格", "参数", "尺寸", "重量", "材质"]),
            ("使用场景", ["适用", "场景", "用途", "使用"]),
            ("目标用户", ["适合", "用户", "人群", "客户"]),
            ("价格信息", ["价格", "价值", "性价比", "优惠"])
        ]
        
        for element_name, keywords in key_elements:
            if any(keyword in text_lower for keyword in keywords):
                score += 15
        
        # Length bonus
        if len(text) >= self.min_listing_length:
            score += 10
        
        return min(score, 100)
    
    def _extract_key_features(self, text: str) -> List[str]:
        """Extract key features from listing text"""
        
        features = []
        
        # Simple feature extraction based on common patterns
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            
            # Look for bullet points or numbered lists
            if line.startswith(('•', '-', '*', '·')) or \
               (len(line) > 0 and line[0].isdigit() and '.' in line[:3]):
                feature = line.lstrip('•-*·0123456789. ').strip()
                if len(feature) > 5 and len(feature) < 100:
                    features.append(feature)
        
        # If no bullet points found, extract sentences with key words
        if not features:
            sentences = text.replace('\n', ' ').split('。')
            
            key_words = ['特点', '优势', '功能', '特色', '亮点', '卖点']
            
            for sentence in sentences:
                sentence = sentence.strip()
                if any(word in sentence for word in key_words) and len(sentence) > 10:
                    features.append(sentence[:80] + ('...' if len(sentence) > 80 else ''))
        
        return features[:5]  # Return top 5 features
    
    def _render_image_analysis_preview(self, images: List[Image.Image]) -> None:
        """Render image analysis preview"""
        
        if not images:
            return
        
        st.write("**图片分析预览：**")
        
        # Basic image statistics
        total_pixels = sum(img.size[0] * img.size[1] for img in images)
        avg_width = sum(img.size[0] for img in images) // len(images)
        avg_height = sum(img.size[1] for img in images) // len(images)
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("图片数量", len(images))
        
        with col2:
            st.metric("平均尺寸", f"{avg_width}×{avg_height}")
        
        with col3:
            # Estimate dominant colors (simplified)
            st.metric("色彩丰富度", "分析中...")
        
        with col4:
            # Image quality assessment (simplified)
            quality_score = min(100, (avg_width * avg_height) // 10000)
            st.metric("质量评分", f"{quality_score}%")
        
        # Color analysis preview
        st.write("**色彩分析：**")
        st.info("🎨 将在产品分析阶段进行详细的色彩和材质分析")
    
    def _display_validation_errors(self, validation: ValidationResult) -> None:
        """Display validation errors and warnings"""
        
        if validation.errors:
            st.error("❌ **输入验证失败：**")
            for error in validation.errors:
                st.write(f"• {error}")
        
        if validation.warnings:
            st.warning("⚠️ **建议改进：**")
            for warning in validation.warnings:
                st.write(f"• {warning}")
    
    def render_input_preview(self, product_info: ProductInfo) -> None:
        """Render preview of input data"""
        
        st.subheader("📋 输入数据预览")
        
        with st.expander("查看输入摘要", expanded=False):
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**产品信息：**")
                st.write(f"• 名称: {product_info.name or '未填写'}")
                st.write(f"• 类别: {product_info.category or '未选择'}")
                st.write(f"• 目标用户: {product_info.target_audience or '未选择'}")
                st.write(f"• 价格区间: {product_info.price_range or '未选择'}")
                st.write(f"• 描述长度: {len(product_info.description)} 字符")
                st.write(f"• 关键特点: {len(product_info.key_features)} 个")
            
            with col2:
                st.write("**图片信息：**")
                st.write(f"• 图片数量: {len(product_info.uploaded_images)}")
                
                if product_info.uploaded_images:
                    for i, img in enumerate(product_info.uploaded_images[:3]):
                        st.write(f"• 图片{i+1}: {img.size[0]}×{img.size[1]}")
                    
                    if len(product_info.uploaded_images) > 3:
                        st.write(f"• ... 还有 {len(product_info.uploaded_images) - 3} 张")
    
    def get_input_guidelines(self) -> Dict[str, str]:
        """Get input guidelines for help display"""
        
        return {
            "listing_text": f"产品描述应包含完整信息，长度 {self.min_listing_length}-{self.max_listing_length} 字符",
            "images": f"上传 1-{self.max_images} 张产品图片，支持 {', '.join(self.supported_formats).upper()} 格式",
            "metadata": "填写产品基本信息有助于提高分析准确性",
            "completeness": "完整的产品信息能够生成更精准的A+图片"
        }
    
    def validate_before_analysis(self, product_info: ProductInfo) -> ValidationResult:
        """Final validation before starting analysis"""
        
        errors = []
        warnings = []
        
        # Check essential fields
        if not product_info.description or len(product_info.description.strip()) < self.min_listing_length:
            errors.append("产品描述信息不足")
        
        if not product_info.uploaded_images:
            warnings.append("没有上传产品图片，可能影响视觉分析效果")
        
        # Check data quality
        completeness = self._calculate_completeness_score(product_info.description)
        if completeness < 50:
            warnings.append("产品信息完整度较低，建议补充更多详细信息")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )


# Global instance for easy access
product_input_panel = ProductInputPanel()