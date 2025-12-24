"""
A+ Studio 通用素材上传界面

为所有模块提供标准化的素材上传界面，支持图片、文档、文本和自定义提示词。
"""

import streamlit as st
from typing import List, Dict, Any, Optional, Tuple
from PIL import Image
import io
from services.aplus_studio.models import (
    ModuleType, MaterialType, MaterialPriority, MaterialRequirement,
    MaterialSet, UploadedFile, ValidationStatus
)
from services.aplus_studio.material_processor import MaterialProcessor


def render_material_upload_interface(selected_modules: List[ModuleType]) -> Dict[ModuleType, MaterialSet]:
    """
    渲染通用素材上传界面
    
    Args:
        selected_modules: 已选择的模块列表
        
    Returns:
        每个模块的素材集合
    """
    st.header("📁 素材上传")
    st.markdown("为选中的模块上传所需素材，AI将根据素材生成专业的A+内容")
    
    # 初始化素材处理器
    processor = MaterialProcessor()
    
    # 初始化会话状态
    if 'module_materials' not in st.session_state:
        st.session_state.module_materials = {}
    
    # 为每个选中的模块创建素材上传区域
    material_sets = {}
    
    for module_type in selected_modules:
        st.markdown("---")
        material_set = _render_module_material_section(module_type, processor)
        material_sets[module_type] = material_set
        
        # 保存到会话状态
        st.session_state.module_materials[module_type.value] = material_set
    
    # 全局素材上传区域
    st.markdown("---")
    st.subheader("🌐 通用素材")
    st.caption("这些素材将应用于所有选中的模块")
    
    global_materials = _render_global_materials_section(processor)
    
    # 将全局素材应用到所有模块
    for module_type in selected_modules:
        if module_type in material_sets:
            _merge_global_materials(material_sets[module_type], global_materials)
    
    # 素材验证和摘要
    st.markdown("---")
    _render_material_summary(material_sets, selected_modules)
    
    return material_sets


def _render_module_material_section(module_type: ModuleType, processor: MaterialProcessor) -> MaterialSet:
    """渲染单个模块的素材上传区域"""
    display_name = _get_module_display_name(module_type)
    
    with st.expander(f"📋 {display_name} - 素材需求", expanded=True):
        # 获取模块的素材需求
        requirements = _get_module_requirements(module_type)
        
        # 显示素材需求指导
        _render_material_requirements_guide(requirements)
        
        # 创建素材上传标签页
        tab1, tab2, tab3, tab4 = st.tabs(["📸 图片", "📄 文档", "✏️ 文本", "🎯 自定义"])
        
        material_set = MaterialSet()
        
        with tab1:
            material_set.images = _render_image_upload_section(module_type, processor)
        
        with tab2:
            material_set.documents = _render_document_upload_section(module_type, processor)
        
        with tab3:
            material_set.text_inputs = _render_text_input_section(module_type)
        
        with tab4:
            material_set.custom_prompts = _render_custom_prompt_section(module_type)
        
        return material_set


def _render_material_requirements_guide(requirements: List[MaterialRequirement]) -> None:
    """渲染素材需求指导"""
    if not requirements:
        st.info("此模块无特殊素材需求")
        return
    
    st.markdown("**📋 素材需求指导:**")
    
    # 按优先级分组显示
    required_items = [req for req in requirements if req.priority == MaterialPriority.REQUIRED]
    recommended_items = [req for req in requirements if req.priority == MaterialPriority.RECOMMENDED]
    ai_generated_items = [req for req in requirements if req.priority == MaterialPriority.AI_GENERATED]
    
    if required_items:
        st.markdown("🔴 **必需素材** (必须提供):")
        for req in required_items:
            st.markdown(f"• **{req.description}**")
            if req.examples:
                st.caption(f"   示例: {', '.join(req.examples[:2])}")
    
    if recommended_items:
        st.markdown("🟡 **推荐素材** (建议提供):")
        for req in recommended_items:
            st.markdown(f"• {req.description}")
    
    if ai_generated_items:
        st.markdown("🟢 **AI生成** (可自动生成):")
        for req in ai_generated_items:
            st.markdown(f"• {req.description}")


def _render_image_upload_section(module_type: ModuleType, processor: MaterialProcessor) -> List[UploadedFile]:
    """渲染图片上传区域"""
    uploaded_images = []
    
    # 图片上传组件
    image_files = st.file_uploader(
        "上传产品图片",
        type=["jpg", "jpeg", "png", "webp"],
        accept_multiple_files=True,
        help="支持JPG、PNG、WebP格式，建议分辨率不低于600x450px",
        key=f"images_{module_type.value}"
    )
    
    if image_files:
        # 处理上传的图片
        for i, file in enumerate(image_files):
            try:
                # 读取图片
                image = Image.open(file)
                
                # 验证图片
                validation_result = processor.validate_image(image, file.name)
                
                # 创建上传文件对象
                uploaded_file = UploadedFile(
                    filename=file.name,
                    file_type=MaterialType.IMAGE,
                    file_size=file.size,
                    content=image,
                    validation_status=validation_result.validation_status
                )
                
                uploaded_images.append(uploaded_file)
                
                # 显示图片预览和状态
                col1, col2 = st.columns([1, 2])
                
                with col1:
                    st.image(image, caption=f"图片 {i+1}", width=150)
                
                with col2:
                    st.write(f"**文件名**: {file.name}")
                    st.write(f"**尺寸**: {image.size[0]}x{image.size[1]}px")
                    st.write(f"**大小**: {file.size/1024:.1f} KB")
                    
                    # 验证状态
                    if validation_result.is_valid:
                        st.success("✅ 图片符合A+规范")
                    else:
                        st.warning("⚠️ 图片需要优化")
                        for issue in validation_result.issues:
                            st.caption(f"• {issue}")
                
                st.divider()
                
            except Exception as e:
                st.error(f"处理图片 {file.name} 时出错: {str(e)}")
    
    return uploaded_images


def _render_document_upload_section(module_type: ModuleType, processor: MaterialProcessor) -> List[UploadedFile]:
    """渲染文档上传区域"""
    uploaded_documents = []
    
    # 文档上传组件
    doc_files = st.file_uploader(
        "上传产品文档",
        type=["pdf", "doc", "docx", "txt"],
        accept_multiple_files=True,
        help="支持PDF、Word、文本文件，AI将提取其中的产品信息",
        key=f"documents_{module_type.value}"
    )
    
    if doc_files:
        for file in doc_files:
            try:
                # 读取文档内容
                content = processor.extract_document_text(file)
                
                # 创建上传文件对象
                uploaded_file = UploadedFile(
                    filename=file.name,
                    file_type=MaterialType.DOCUMENT,
                    file_size=file.size,
                    content=content,
                    validation_status=ValidationStatus.PASSED
                )
                
                uploaded_documents.append(uploaded_file)
                
                # 显示文档信息
                with st.expander(f"📄 {file.name}", expanded=False):
                    st.write(f"**文件大小**: {file.size/1024:.1f} KB")
                    st.write(f"**提取文本长度**: {len(content)} 字符")
                    
                    # 显示文本预览
                    if len(content) > 200:
                        st.text_area("文本预览", value=content[:200] + "...", height=100, disabled=True)
                    else:
                        st.text_area("文本内容", value=content, height=100, disabled=True)
                
            except Exception as e:
                st.error(f"处理文档 {file.name} 时出错: {str(e)}")
    
    return uploaded_documents


def _render_text_input_section(module_type: ModuleType) -> Dict[str, str]:
    """渲染文本输入区域"""
    text_inputs = {}
    
    # 根据模块类型提供不同的文本输入字段
    text_fields = _get_module_text_fields(module_type)
    
    for field_key, field_info in text_fields.items():
        label = field_info['label']
        placeholder = field_info.get('placeholder', '')
        help_text = field_info.get('help', '')
        max_chars = field_info.get('max_chars', 500)
        
        text_value = st.text_area(
            label,
            placeholder=placeholder,
            help=help_text,
            max_chars=max_chars,
            key=f"text_{module_type.value}_{field_key}"
        )
        
        if text_value.strip():
            text_inputs[field_key] = text_value.strip()
    
    return text_inputs


def _render_custom_prompt_section(module_type: ModuleType) -> Dict[str, str]:
    """渲染自定义提示词区域"""
    custom_prompts = {}
    
    st.markdown("**🎯 自定义生成指令**")
    st.caption("提供具体的生成要求，AI将根据您的指令调整生成效果")
    
    # 风格指令
    style_prompt = st.text_area(
        "视觉风格要求",
        placeholder="例如：现代简约风格，使用蓝白配色，突出科技感...",
        help="描述您希望的视觉风格和色彩搭配",
        key=f"style_prompt_{module_type.value}"
    )
    
    if style_prompt.strip():
        custom_prompts['style'] = style_prompt.strip()
    
    # 内容重点
    content_prompt = st.text_area(
        "内容重点",
        placeholder="例如：重点突出产品的耐用性和防水功能...",
        help="描述您希望重点展示的产品特性",
        key=f"content_prompt_{module_type.value}"
    )
    
    if content_prompt.strip():
        custom_prompts['content_focus'] = content_prompt.strip()
    
    # 目标受众
    audience_prompt = st.text_input(
        "目标受众",
        placeholder="例如：年轻专业人士，注重品质的家庭用户...",
        help="描述产品的目标用户群体",
        key=f"audience_prompt_{module_type.value}"
    )
    
    if audience_prompt.strip():
        custom_prompts['target_audience'] = audience_prompt.strip()
    
    return custom_prompts


def _render_global_materials_section(processor: MaterialProcessor) -> MaterialSet:
    """渲染全局素材上传区域"""
    st.caption("这些素材将用于所有模块的生成")
    
    global_materials = MaterialSet()
    
    col1, col2 = st.columns(2)
    
    with col1:
        # 全局产品图片
        global_images = st.file_uploader(
            "通用产品图片",
            type=["jpg", "jpeg", "png", "webp"],
            accept_multiple_files=True,
            help="这些图片将用于所有模块",
            key="global_images"
        )
        
        if global_images:
            for file in global_images:
                try:
                    image = Image.open(file)
                    uploaded_file = UploadedFile(
                        filename=file.name,
                        file_type=MaterialType.IMAGE,
                        file_size=file.size,
                        content=image,
                        validation_status=ValidationStatus.PASSED
                    )
                    global_materials.images.append(uploaded_file)
                except Exception as e:
                    st.error(f"处理全局图片失败: {str(e)}")
    
    with col2:
        # 全局产品描述
        global_description = st.text_area(
            "产品总体描述",
            placeholder="请描述产品的基本信息、主要功能和特点...",
            help="这个描述将用于所有模块的生成",
            key="global_description"
        )
        
        if global_description.strip():
            global_materials.text_inputs['product_description'] = global_description.strip()
    
    return global_materials


def _render_material_summary(material_sets: Dict[ModuleType, MaterialSet], selected_modules: List[ModuleType]) -> None:
    """渲染素材摘要"""
    st.subheader("📊 素材摘要")
    
    # 统计信息
    total_images = sum(len(ms.images) for ms in material_sets.values())
    total_documents = sum(len(ms.documents) for ms in material_sets.values())
    total_text_fields = sum(len(ms.text_inputs) for ms in material_sets.values())
    total_prompts = sum(len(ms.custom_prompts) for ms in material_sets.values())
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("图片", total_images)
    
    with col2:
        st.metric("文档", total_documents)
    
    with col3:
        st.metric("文本字段", total_text_fields)
    
    with col4:
        st.metric("自定义提示", total_prompts)
    
    # 素材完整性检查
    st.markdown("**📋 素材完整性检查:**")
    
    for module_type in selected_modules:
        display_name = _get_module_display_name(module_type)
        material_set = material_sets.get(module_type, MaterialSet())
        
        # 检查必需素材
        requirements = _get_module_requirements(module_type)
        required_items = [req for req in requirements if req.priority == MaterialPriority.REQUIRED]
        
        if not required_items:
            st.success(f"✅ {display_name}: 无必需素材要求")
        else:
            missing_required = []
            for req in required_items:
                if not _check_material_provided(material_set, req):
                    missing_required.append(req.description)
            
            if missing_required:
                st.warning(f"⚠️ {display_name}: 缺少必需素材")
                for item in missing_required:
                    st.caption(f"   • {item}")
            else:
                st.success(f"✅ {display_name}: 必需素材已提供")
    
    # 继续按钮
    if total_images > 0 or total_text_fields > 0:
        st.markdown("---")
        if st.button("🚀 开始生成", type="primary", use_container_width=True):
            st.session_state.current_step = "generation"
            st.success("素材准备完成，开始生成A+内容！")
            st.rerun()
    else:
        st.info("💡 请至少上传一些图片或填写文本信息")


def _merge_global_materials(module_materials: MaterialSet, global_materials: MaterialSet) -> None:
    """将全局素材合并到模块素材中"""
    # 合并图片
    module_materials.images.extend(global_materials.images)
    
    # 合并文档
    module_materials.documents.extend(global_materials.documents)
    
    # 合并文本输入
    for key, value in global_materials.text_inputs.items():
        if key not in module_materials.text_inputs:
            module_materials.text_inputs[key] = value
    
    # 合并自定义提示
    for key, value in global_materials.custom_prompts.items():
        if key not in module_materials.custom_prompts:
            module_materials.custom_prompts[key] = value


def _get_module_display_name(module_type: ModuleType) -> str:
    """获取模块显示名称"""
    display_names = {
        ModuleType.PRODUCT_OVERVIEW: "产品概览",
        ModuleType.PROBLEM_SOLUTION: "问题解决",
        ModuleType.FEATURE_ANALYSIS: "功能解析",
        ModuleType.SPECIFICATION_COMPARISON: "规格对比",
        ModuleType.USAGE_SCENARIOS: "使用场景",
        ModuleType.INSTALLATION_GUIDE: "安装指南",
        ModuleType.SIZE_COMPATIBILITY: "尺寸兼容",
        ModuleType.MAINTENANCE_CARE: "维护保养",
        ModuleType.MATERIAL_CRAFTSMANSHIP: "材质工艺",
        ModuleType.QUALITY_ASSURANCE: "品质保证",
        ModuleType.CUSTOMER_REVIEWS: "用户评价",
        ModuleType.PACKAGE_CONTENTS: "包装内容"
    }
    return display_names.get(module_type, module_type.value)


def _get_module_requirements(module_type: ModuleType) -> List[MaterialRequirement]:
    """获取模块的素材需求"""
    # 这里应该从模块生成器获取实际需求，暂时返回示例需求
    common_requirements = [
        MaterialRequirement(
            material_type=MaterialType.IMAGE,
            priority=MaterialPriority.REQUIRED,
            description="产品主图",
            examples=["产品正面图", "产品使用图"],
            file_formats=["JPG", "PNG"],
            max_file_size=5*1024*1024  # 5MB
        )
    ]
    
    # 根据模块类型添加特定需求
    specific_requirements = {
        ModuleType.PRODUCT_OVERVIEW: [
            MaterialRequirement(
                material_type=MaterialType.TEXT,
                priority=MaterialPriority.RECOMMENDED,
                description="产品核心功能描述",
                examples=["主要功能列表", "产品规格参数"]
            )
        ],
        ModuleType.PROBLEM_SOLUTION: [
            MaterialRequirement(
                material_type=MaterialType.IMAGE,
                priority=MaterialPriority.RECOMMENDED,
                description="问题场景图片",
                examples=["使用前场景", "问题展示图"]
            )
        ],
        ModuleType.INSTALLATION_GUIDE: [
            MaterialRequirement(
                material_type=MaterialType.IMAGE,
                priority=MaterialPriority.REQUIRED,
                description="安装步骤图片",
                examples=["安装过程图", "工具展示图"]
            ),
            MaterialRequirement(
                material_type=MaterialType.TEXT,
                priority=MaterialPriority.REQUIRED,
                description="安装步骤说明",
                examples=["详细安装步骤", "注意事项"]
            )
        ]
    }
    
    return common_requirements + specific_requirements.get(module_type, [])


def _get_module_text_fields(module_type: ModuleType) -> Dict[str, Dict[str, Any]]:
    """获取模块的文本输入字段"""
    common_fields = {
        'product_name': {
            'label': '产品名称',
            'placeholder': '请输入产品名称',
            'help': '产品的完整名称',
            'max_chars': 100
        },
        'key_features': {
            'label': '核心功能',
            'placeholder': '请列出产品的主要功能和特点...',
            'help': '产品的主要功能和卖点',
            'max_chars': 300
        }
    }
    
    # 根据模块类型添加特定字段
    specific_fields = {
        ModuleType.PROBLEM_SOLUTION: {
            'problem_description': {
                'label': '解决的问题',
                'placeholder': '描述产品解决的具体问题...',
                'help': '产品解决的用户痛点',
                'max_chars': 200
            }
        },
        ModuleType.INSTALLATION_GUIDE: {
            'installation_steps': {
                'label': '安装步骤',
                'placeholder': '1. 第一步...\n2. 第二步...',
                'help': '详细的安装步骤说明',
                'max_chars': 500
            },
            'tools_needed': {
                'label': '所需工具',
                'placeholder': '螺丝刀、扳手、测量尺...',
                'help': '安装过程中需要的工具',
                'max_chars': 100
            }
        },
        ModuleType.SPECIFICATION_COMPARISON: {
            'specifications': {
                'label': '产品规格',
                'placeholder': '尺寸: 30x20x10cm\n重量: 2kg\n材质: 不锈钢...',
                'help': '详细的产品规格参数',
                'max_chars': 400
            }
        }
    }
    
    result = common_fields.copy()
    result.update(specific_fields.get(module_type, {}))
    return result


def _check_material_provided(material_set: MaterialSet, requirement: MaterialRequirement) -> bool:
    """检查是否提供了必需的素材"""
    if requirement.material_type == MaterialType.IMAGE:
        return len(material_set.images) > 0
    elif requirement.material_type == MaterialType.DOCUMENT:
        return len(material_set.documents) > 0
    elif requirement.material_type == MaterialType.TEXT:
        return len(material_set.text_inputs) > 0
    elif requirement.material_type == MaterialType.CUSTOM_PROMPT:
        return len(material_set.custom_prompts) > 0
    
    return False