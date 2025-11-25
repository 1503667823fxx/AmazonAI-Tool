import streamlit as st
import google.generativeai as genai
from PIL import Image
import json
import sys
import os
import re

# 为了引入根目录的 auth.py
sys.path.append(os.path.abspath('.'))
try:
    import auth
except ImportError:
    pass 

# --- 1. 页面配置 ---
st.set_page_config(page_title="文案工作室", page_icon="✍️", layout="wide")

# 自定义 CSS
st.markdown("""
<style>
    .stTextArea textarea {font-size: 14px; font-family: 'Microsoft YaHei', sans-serif;}
    section[data-testid="stSidebar"] {width: 400px !important;}
    
    /* 关键词高亮样式 */
    .kw-highlight {
        background-color: #fff3cd;
        color: #856404;
        font-weight: bold;
        padding: 2px 4px;
        border-radius: 4px;
        border: 1px solid #ffeeba;
    }
</style>
""", unsafe_allow_html=True)

# 安全检查
if 'auth' in sys.modules:
    if not auth.check_password():
        st.stop()

# --- 2. 验证 API Key ---
try:
    if "GOOGLE_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    else:
        st.error("❌ 未找到 Google API Key")
        st.stop()
except Exception as e:
    st.error(f"API配置出错: {e}")

# --- 3. 侧边栏 ---
with st.sidebar:
    st.title("⚙️ 文案规则配置")
    
    col_s1, col_s2 = st.columns(2)
    with col_s1:
        category = st.selectbox("品类", ["3C电子", "家居生活", "时尚服饰", "户外运动", "母婴用品", "美妆个护", "宠物用品", "汽配"])
    with col_s2:
        language = st.selectbox("语言", ["English (US)", "English (UK)", "Deutsch (DE)", "Français (FR)", "日本語 (JP)", "Español (ES)"])

    st.info("💡 当前已启用：亚马逊通用高转化风格 (专业、地道、SEO优化)")
    
    st.divider()
    
    # =========================================================
    # 🔴 【亚马逊 2025 新规库】 🔴
    # =========================================================
    default_amazon_rules = """【标题规则 (Title)】
1. 可读性优先：标题必须通顺、有逻辑，严禁单纯堆砌关键词。必须结合产品参数和卖点。
2. 长度：大部分分类不得超过 200 字符。建议控制在 80-150 字符。
3. 格式：
   - 结构：品牌 + 核心大词 + 核心卖点/属性 + 适用场景/型号 + 颜色/尺寸。
   - 单词首字母大写 (Title Case)，介词/连词小写。
   - 使用阿拉伯数字 (2) 而非单词 (Two)。
4. 禁止：
   - 特殊符号 (! $ ? _ {} ^ ~ # < > *)。
   - 促销语 (Free shipping, Sale) 和主观评价 (Best Seller)。

【五点描述规则 (Bullet Points)】
1. 格式：
   - 采用 [Title Case Feature]: [Description] 结构。
   - **卖点短语 (冒号前)**：单词首字母大写，介词/连词小写 (例如: Long Battery Life for Travel)。不要全大写。
   - **具体描述 (冒号后)**：自然段落句式。
   - 结尾不加标点。
2. 内容：真实、准确、可量化。

【产品描述规则 (Description)】
1. 格式：HTML 代码 (<b>, <br>, <p>)。
2. 内容：完整句子，包含详细参数。"""
    # =========================================================

    with st.expander("📜 Listing 核心撰写规范", expanded=True):
        amazon_rules = st.text_area("在此输入平台规范：", value=default_amazon_rules, height=400)

    # Search Terms 规则 - 已更新为更务实的逻辑
    default_st_rules = """1. 核心策略：
   - 优先包含高流量的核心词（即使标题里有，如果非常重要也可以重复，确保收录）。
   - 重点补充同义词、近义词、西班牙语/法语变体、特定场景词。
2. 格式：
   - 总字节数 < 250 bytes。
   - 词与词之间用半角空格隔开。
   - 严禁标点符号。
   - 严禁品牌名。"""

    with st.expander("🔍 Search Terms (ST) 规则", expanded=False):
        st_rules = st.text_area("后台关键词规则：", value=default_st_rules, height=250)

    with st.expander("🛑 违禁词库", expanded=False):
        forbidden_words = st.text_area("严禁使用的词", value="Best Seller, No.1, Top rated, Free shipping, Guarantee, Hot item, Amazing, 100% Quality", height=100)

# --- 4. 辅助函数 ---
def parse_gemini_response(text):
    try:
        start = text.find('{')
        end = text.rfind('}') + 1
        if start != -1 and end != -1:
            return json.loads(text[start:end])
    except:
        pass
    return None

def render_highlighted_text(text):
    """
    将 <<keyword>> 转换为 HTML 高亮显示
    """
    if not text: return ""
    # 将 <<内容>> 替换为 <span class='kw-highlight'>内容</span>
    highlighted = re.sub(r"<<(.*?)>>", r"<span class='kw-highlight'>\1</span>", text)
    return highlighted

def clean_text_for_copy(text):
    """
    移除 << >> 符号，返回纯净文本供复制
    """
    if not text: return ""
    return text.replace("<<", "").replace(">>", "")

# --- 5. 主界面 ---
st.title("✍️ Listing 文案工作室")
st.caption(f"Engine: Gemini 3.0 Pro | {category} | {language} | 通用高转化风格")

col1, col2 = st.columns([4, 6])

with col1:
    st.subheader("1. 产品档案")
    uploaded_file = st.file_uploader("上传产品主图", type=["jpg", "png", "jpeg", "webp"])
    if uploaded_file:
        st.image(uploaded_file, width=150)
        
    product_name = st.text_input("产品名称 *", placeholder="例如：Active Noise Cancelling Headphones")
    
    top_keywords = st.text_area(
        "🔍 核心关键词 Top 10 *", 
        placeholder="⚠️ 注意顺序：请按重要性从高到低输入！\n越靠前的词，AI会优先埋入标题和五点前部。\n例如：wireless earbuds, bluetooth headphones", 
        height=100,
        help="底层规则：AI会严格遵循“顺序即权重”原则。输入框中最靠前的词权重最高。"
    )
    
    with st.expander("📝 详细卖点与参数", expanded=True):
        core_selling_point = st.text_area("💎 核心卖点描述", height=100)
        usage_scope = st.text_area("🎯 适用范围", height=100)
        bullet_supplements = st.text_area("➕ 补充内容", height=100)

with col2:
    st.subheader("2. 生成结果")
    if st.button("✨ 立即生成 Listing", type="primary", use_container_width=True):
        if not uploaded_file or not product_name:
            st.warning("请上传图片并填写名称")
        else:
            with st.spinner("🧠 Gemini 正在撰写 (已优化标题可读性 & 五点格式)..."):
                try:
                    model = genai.GenerativeModel('gemini-3-pro-preview')
                    
                    # === Prompt 升级 ===
                    prompt = f"""
                    你是一个亚马逊Listing顶级专家。请严格基于以下信息和规则生成JSON格式Listing。
                    
                    【输入信息】
                    产品:{product_name}
                    核心关键词(SEO Keywords):{top_keywords}
                    卖点:{core_selling_point}
                    适用:{usage_scope}
                    补充:{bullet_supplements}
                    语言:{language} 
                    风格: 亚马逊通用高转化风格 (专业、地道、SEO友好、简洁有力)
                    品类:{category}
                    
                    【🔴 必须严格遵守的规则库 (Based on 2025 Rules)】
                    通用规则:{amazon_rules}
                    ST规则:{st_rules}
                    违禁词:{forbidden_words}
                    
                    【重要指令：标题生成逻辑 (Readability)】
                    1. **拒绝堆砌**：严禁把关键词简单罗列！标题必须是一个通顺、有逻辑的句子。
                    2. **内容融合**：必须将【核心关键词】与用户的【核心卖点/参数】有机结合。
                    3. **结构**：Brand + Core Keywords + Key Features (e.g. 40H Playtime, IPX7) + Model/Size.
                    
                    【重要指令：五点描述格式 (Bullet Points)】
                    1. **格式**：`[Title Case Feature]: [Description]`
                    2. **首字母规则**：冒号前的“卖点短语”，单词首字母大写 (Title Case)，但介词 (in, on, with, for) 和连词 (and, or) 必须小写。例如：`High Quality Material for Sleep:`
                    3. **禁止**：不要全大写 (DO NOT USE ALL CAPS)。
                    
                    【重要指令：Search Terms (ST)】
                    1. **策略**：优先覆盖高流量词。如果核心词（如产品原本名称）非常重要，**允许**在 ST 中再次包含，以确保索引安全。
                    2. **补充**：挖掘同义词、场景词。
                    
                    【重要指令：关键词标记】
                    请将所有埋入的【核心关键词】用双尖括号 << >> 包裹起来。
                    例如：This <<Wireless Earbuds>> features...
                    
                    【输出格式】
                    仅输出 JSON：
                    {{ 
                        "title": "...", 
                        "bullet_point_1": "Feature Name: Description...", 
                        "bullet_point_2": "Feature Name: Description...", 
                        "bullet_point_3": "Feature Name: Description...", 
                        "bullet_point_4": "Feature Name: Description...", 
                        "bullet_point_5": "Feature Name: Description...", 
                        "description": "HTML Code...", 
                        "search_terms": "..." 
                    }}
                    """
                    
                    image_obj = Image.open(uploaded_file)
                    response = model.generate_content([prompt, image_obj])
                    
                    clean_text_resp = response.text.replace("```json", "").replace("```", "")
                    result = parse_gemini_response(clean_text_resp)
                    
                    if result:
                        st.success("✅ 生成成功！标题已优化可读性，五点格式已修正。")
                        
                        # --- 标题区域 ---
                        st.markdown("#### 📝 Title (标题)")
                        raw_title = result.get("title", "")
                        st.markdown(render_highlighted_text(raw_title), unsafe_allow_html=True)
                        st.text_area("Title (Copy here)", value=clean_text_for_copy(raw_title), height=80, label_visibility="collapsed")
                        
                        # --- 五点区域 ---
                        st.markdown("#### 📌 Bullet Points (五点描述)")
                        for i in range(1, 6):
                            raw_bullet = result.get(f"bullet_point_{i}", "")
                            col_b1, col_b2 = st.columns([0.1, 0.9])
                            with col_b1:
                                st.markdown(f"**BP{i}**")
                            with col_b2:
                                st.markdown(render_highlighted_text(raw_bullet), unsafe_allow_html=True)
                                st.text_area(f"Bullet {i}", value=clean_text_for_copy(raw_bullet), height=100, label_visibility="collapsed")
                        
                        # --- ST 区域 ---
                        st.markdown("#### 🔍 Search Terms")
                        st.text_area("Search Terms", value=clean_text_for_copy(result.get("search_terms", "")), height=100)
                        
                        # --- 描述区域 (HTML) ---
                        st.markdown("#### 📖 Description (HTML Source)")
                        st.text_area("Description Code", value=clean_text_for_copy(result.get("description", "")), height=200)
                        
                        # --- 总预览页面 ---
                        st.markdown("---")
                        with st.expander("📋 全局文案总览 (All-in-One Preview)", expanded=True):
                            st.info("💡 提示：这里汇总了所有生成内容（纯净版），方便一次性查看或复制。")
                            
                            all_content = f"""【Title】
{clean_text_for_copy(raw_title)}

【Bullet Points】
1. {clean_text_for_copy(result.get('bullet_point_1', ''))}
2. {clean_text_for_copy(result.get('bullet_point_2', ''))}
3. {clean_text_for_copy(result.get('bullet_point_3', ''))}
4. {clean_text_for_copy(result.get('bullet_point_4', ''))}
5. {clean_text_for_copy(result.get('bullet_point_5', ''))}

【Search Terms】
{clean_text_for_copy(result.get('search_terms', ''))}

【Description (HTML)】
{clean_text_for_copy(result.get('description', ''))}
"""
                            st.text_area("Full Listing Content", value=all_content, height=600)
                            
                    else:
                        st.error("解析失败")
                        st.text(response.text)
                except Exception as e:
                    st.error(f"错误: {e}")
