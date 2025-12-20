"""
Streamlit工具模块
提供Streamlit环境下的工具函数和组件
"""

import streamlit as st
from pathlib import Path
from typing import Optional, Dict, Any, List
import json
import yaml
from tools.config import get_config


def setup_page_config(
    page_title: str = "模板库管理",
    page_icon: str = "🎨",
    layout: str = "wide"
):
    """设置Streamlit页面配置"""
    st.set_page_config(
        page_title=page_title,
        page_icon=page_icon,
        layout=layout,
        initial_sidebar_state="expanded"
    )


def show_config_info():
    """显示配置信息"""
    config = get_config()
    
    with st.expander("🔧 系统配置信息"):
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("基础配置")
            st.write(f"调试模式: {config.is_debug_mode()}")
            st.write(f"日志级别: {config.get('template_system', 'log_level')}")
            st.write(f"最大文件大小: {config.get('template_system', 'max_file_size_mb')}MB")
            
        with col2:
            st.subheader("图片配置")
            desktop_size = config.get_image_size('desktop')
            mobile_size = config.get_image_size('mobile')
            preview_size = config.get_image_size('preview')
            
            st.write(f"桌面版尺寸: {desktop_size[0]}x{desktop_size[1]}")
            st.write(f"移动版尺寸: {mobile_size[0]}x{mobile_size[1]}")
            st.write(f"预览图尺寸: {preview_size[0]}x{preview_size[1]}")


def display_file_tree(root_path: Path, max_depth: int = 3):
    """显示文件树结构"""
    def _build_tree(path: Path, depth: int = 0, prefix: str = "") -> List[str]:
        if depth > max_depth:
            return []
        
        items = []
        if path.is_dir():
            items.append(f"{prefix}📁 {path.name}/")
            
            try:
                children = sorted(path.iterdir(), key=lambda x: (x.is_file(), x.name))
                for i, child in enumerate(children):
                    is_last = i == len(children) - 1
                    child_prefix = prefix + ("    " if is_last else "│   ")
                    connector = "└── " if is_last else "├── "
                    
                    if child.is_dir():
                        items.append(f"{prefix}{connector}📁 {child.name}/")
                        items.extend(_build_tree(child, depth + 1, child_prefix))
                    else:
                        icon = "📄" if child.suffix in ['.json', '.md', '.yaml', '.yml'] else "🖼️"
                        items.append(f"{prefix}{connector}{icon} {child.name}")
            except PermissionError:
                items.append(f"{prefix}    ❌ 权限不足")
        
        return items
    
    if root_path.exists():
        tree_items = _build_tree(root_path)
        st.code("\n".join(tree_items), language="text")
    else:
        st.error(f"路径不存在: {root_path}")


def validate_environment() -> Dict[str, bool]:
    """验证Streamlit环境"""
    results = {}
    config = get_config()
    
    # 检查必要目录
    required_dirs = [
        config.get_path('templates_root'),
        config.get_path('templates_root') / 'config',
        config.get_path('templates_root') / 'by_category',
        Path('tools'),
        Path('tools/models'),
        Path('tools/validators')
    ]
    
    for dir_path in required_dirs:
        results[f"目录: {dir_path}"] = dir_path.exists() and dir_path.is_dir()
    
    # 检查配置文件
    config_files = [
        config.get_path('templates_root') / 'config' / 'categories.yaml',
        config.get_path('templates_root') / 'config' / 'template_types.yaml',
        Path('tools/schemas/template_config_schema.json')
    ]
    
    for file_path in config_files:
        results[f"配置: {file_path.name}"] = file_path.exists() and file_path.is_file()
    
    # 检查Python模块
    try:
        from tools.models import Template, TemplateConfig
        results["模型模块"] = True
    except ImportError:
        results["模型模块"] = False
    
    try:
        from tools.validators import ConfigValidator
        results["验证器模块"] = True
    except ImportError:
        results["验证器模块"] = False
    
    return results


def show_validation_results():
    """显示环境验证结果"""
    st.subheader("🔍 环境验证")
    
    results = validate_environment()
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        for item, status in results.items():
            if status:
                st.success(f"✅ {item}")
            else:
                st.error(f"❌ {item}")
    
    with col2:
        passed = sum(results.values())
        total = len(results)
        
        st.metric(
            label="验证通过率",
            value=f"{passed}/{total}",
            delta=f"{passed/total*100:.1f}%"
        )
        
        if passed == total:
            st.balloons()


def create_sidebar_navigation():
    """创建侧边栏导航"""
    st.sidebar.title("🎨 模板库管理")
    
    pages = {
        "🏠 首页": "home",
        "📁 模板管理": "templates",
        "🔧 配置管理": "config",
        "✅ 验证工具": "validation",
        "📊 统计信息": "stats"
    }
    
    selected = st.sidebar.selectbox(
        "选择功能",
        options=list(pages.keys()),
        format_func=lambda x: x
    )
    
    return pages[selected]


def load_yaml_file(file_path: Path) -> Optional[Dict[str, Any]]:
    """加载YAML文件"""
    try:
        if file_path.exists():
            with open(file_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
    except Exception as e:
        st.error(f"加载YAML文件失败: {e}")
    return None


def load_json_file(file_path: Path) -> Optional[Dict[str, Any]]:
    """加载JSON文件"""
    try:
        if file_path.exists():
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        st.error(f"加载JSON文件失败: {e}")
    return None


def save_yaml_file(file_path: Path, data: Dict[str, Any]) -> bool:
    """保存YAML文件"""
    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True)
        return True
    except Exception as e:
        st.error(f"保存YAML文件失败: {e}")
        return False


def save_json_file(file_path: Path, data: Dict[str, Any]) -> bool:
    """保存JSON文件"""
    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        st.error(f"保存JSON文件失败: {e}")
        return False