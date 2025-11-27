import streamlit as st
import sys
import os

# ==========================================
# 🛠️ 关键修复：路径补丁
# ==========================================
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# ==========================================
# 📦 模块导入
# ==========================================
try:
    # 导入核心工具和子模块
    from core_utils import AITranslator, HistoryManager
    from tab1_workflow import render_tab1
    from tab2_restyling import render_tab2
    from tab3_background import render_tab3
    
    try:
        import auth
    except ImportError: pass
    
    HAS_IMPORTS = True

except ImportError as e:
    st.error(f"❌ 模块导入失败: {e}")
    st.warning("请确保所有 .py 文件都在同一目录下")
    HAS_IMPORTS = False
except SyntaxError as e:
    st.error(f"❌ 语法错误: {e}")
    st.warning("请检查复制的代码是否完整，不要包含
    st.info("⚠️ 等待模块加载... 如果持续报错，请检查文件名是否正确。")
else:
    st.warning("系统模块加载不完整，请检查文件结构。")
