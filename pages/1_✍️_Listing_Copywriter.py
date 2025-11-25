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

    tone = st.selectbox("文案风格", ["专业权威 (Professional)", "极具感染力 (Persuasive)", "简洁清晰 (Concise)", "生活化 (Lifestyle)"])
    
    st.divider()
    
    # =========================================================
    # 🔴 【亚马逊 2025 新规库】 🔴
    # 基于你上传的《规则.docx》整理，涵盖标题、五点、描述的核心要求
    # =========================================================
    default_amazon_rules = """【标题规则 (Title)】
1. 长度：大部分分类不得超过 200 字符。**强烈建议控制在 80 字符以内**以优化移动端显示。
2. 格式：
   - 推荐结构：品牌 + 核心关键词 + 关键属性 + 颜色 + 尺寸 + 型号。
   - 每个单词首字母大写（介词/连词/冠词 <5 字母除外）。
   - 使用阿拉伯数字 (2) 而非单词 (Two)。
   - 禁止全大写。
3. 禁止：
   - 特殊符号 (! $ ? _ {} ^ ~ # < > *) 及作为装饰的符号。
   - 单词重复超过 2 次（单复数算重复）。
   - 促销语 (Free shipping, 100% Quality, Sale)。
   - 主观评价 (Best Seller, Hot Item, Amazing)。
   - 卖家名称。

【五点描述规则 (Bullet Points)】
1. 长度：单条建议控制在 200 字符以内（上限 500）。
2. 格式：
   - 采用 [大写卖点] + [具体描述] 结构。
   - 开头首字母大写。
   - **结尾不要加标点符号**。
3. 内容：真实、准确、可量化（尺寸/材质/原产地）。保持顺序一致。
4. 禁止：含糊其辞、促销信息、运送信息、主观评论。

【产品描述规则 (Description)】
1. 长度：不超过 2000 字符。
2. 内容：语法正确，完整句子。包含尺寸、保养、保修。
3. 禁止：卖家联系方式、外链、促销信息。"""
    # =========================================================

    with st.expander("📜 Listing 核心撰写规范", expanded=True):
        amazon_rules = st.text_area("在此输入平台规范：", value=default_amazon_rules, height=400)

    # Search Terms 规则 (基于文档更新)
    default_st_rules = """1. 长度：总字节数控制在 250 bytes 以内。
2. 内容策略：
   - 仅输入同义词、近义词、缩写、场景词。
   - **禁止重复**标题、五点、品牌中已有的词（不增加权重）。
   - 禁止品牌名、ASIN、UPC。
   - 禁止主观词 (Amazing, Best) 和临时词 (New, Sale)。
   - 禁止错别字变体（亚马逊会自动修正）。
3. 格式：
   - 词与词之间用**半角空格**隔开。
   - **严禁使用标点符号**（逗号、冒号、分号等）。
4. 逻辑：按逻辑顺序排列。"""

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
st.caption(f"Engine: Gemini 3.0 Pro | {category} | {language}")

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
            with st.spinner("🧠 Gemini 正在根据《2025新规》撰写 (已启用权重排序)..."):
                try:
                    model = genai.GenerativeModel('gemini-3-pro-preview')
                    
                    # === Prompt 升级：加入权重排序指令 ===
                    prompt = f"""
                    你是一个亚马逊Listing顶级专家。请严格基于以下信息和规则生成JSON格式Listing。
                    
                    【输入信息】
                    产品:{product_name}
                    核心关键词(SEO Keywords):{top_keywords}
                    卖点:{core_selling_point}
                    适用:{usage_scope}
                    补充:{bullet_supplements}
                    语言:{language} 风格:{tone} 品类:{category}
                    
                    【🔴 必须严格遵守的规则库 (Based on 2025 Rules)】
                    通用规则(标题/五点/描述):{amazon_rules}
                    ST规则(Search Terms):{st_rules}
                    违禁词:{forbidden_words}
                    
                    【重要指令：关键词权重排序】
                    用户输入的【核心关键词】严格遵循“顺序即权重”的原则：
                    1. 输入越靠前的关键词权重最高（High Weight），必须优先安排在 Listing 的高权重位置（如标题前部、五点描述的第一、二条）。
                    2. 输入越靠后的关键词权重越低（Low Weight），可以安排在五点描述的后部或产品描述中。
                    3. 请勿打乱这一权重逻辑。
                    
                    【重要指令：关键词标记】
                    请将所有埋入的【核心关键词】用双尖括号 << >> 包裹起来。
                    例如：This <<wireless earbuds>> features...
                    不要使用 markdown 的 **，只用 << >>。
                    
                    【输出格式】
                    仅输出 JSON：
                    {{ "title": "...", "bullet_point_1": "...", "bullet_point_2": "...", "bullet_point_3": "...", "bullet_point_4": "...", "bullet_point_5": "...", "description": "...", "search_terms": "..." }}
                    """
                    
                    image_obj = Image.open(uploaded_file)
                    response = model.generate_content([prompt, image_obj])
                    
                    clean_text_resp = response.text.replace("```json", "").replace("```", "")
                    result = parse_gemini_response(clean_text_resp)
                    
                    if result:
                        st.success("✅ 生成成功！已根据新规和权重优化。")
                        
                        # --- 标题区域 ---
                        st.markdown("#### 📝 Title (标题)")
                        raw_title = result.get("title", "")
                        # 1. 显示高亮预览 (HTML)
                        st.markdown(render_highlighted_text(raw_title), unsafe_allow_html=True)
                        # 2. 显示纯净编辑框
                        st.text_area("Title (Copy here)", value=clean_text_for_copy(raw_title), height=80, label_visibility="collapsed")
                        
                        st.markdown("#### 📌 Bullet Points (五点描述)")
                        for i in range(1, 6):
                            raw_bullet = result.get(f"bullet_point_{i}", "")
                            col_b1, col_b2 = st.columns([0.1, 0.9])
                            with col_b1:
                                st.markdown(f"**BP{i}**")
                            with col_b2:
                                # 预览
                                st.markdown(render_highlighted_text(raw_bullet), unsafe_allow_html=True)
                                # 复制框
                                st.text_area(f"Bullet {i}", value=clean_text_for_copy(raw_bullet), height=100, label_visibility="collapsed")
                        
                        st.markdown("#### 🔍 Search Terms")
                        st.text_area("Search Terms", value=clean_text_for_copy(result.get("search_terms", "")), height=100)
                        
                        st.markdown("#### 📖 Description")
                        st.text_area("Description", value=clean_text_for_copy(result.get("description", "")), height=200)
                    else:
                        st.error("解析失败")
                        st.text(response.text)
                except Exception as e:
                    st.error(f"错误: {e}")
