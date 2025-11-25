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
    
    /* 重写按钮样式微调 */
    div[data-testid="stButton"] button {
        border-radius: 20px;
        font-size: 12px;
        height: 2em;
        padding-top: 0;
        padding-bottom: 0;
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

# --- 初始化 Session State ---
if "listing_data" not in st.session_state:
    st.session_state["listing_data"] = {
        "title": "",
        "bullet_point_1": "",
        "bullet_point_2": "",
        "bullet_point_3": "",
        "bullet_point_4": "",
        "bullet_point_5": "",
        "search_terms": "",
        "description": ""
    }

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
1. 移动端优先 (Mobile First)：前 60 个字符非常关键！必须包含最核心的卖点，确保用户在手机端第一眼能看到价值。
2. 长度：建议控制在 80-150 字符。
3. 格式：
   - 结构：品牌 + [数量/包装] + 核心材质/工艺 + 核心大词 + 适用场景/节日/对象。
   - **关键词限制**：【严禁堆砌】最多只允许使用 2-3 个核心关键词。多余的流量词请安排在 Search Terms 中。
   - 单词首字母大写 (Title Case)，介词/连词小写。
   - 使用阿拉伯数字 (2) 而非单词 (Two)。
4. 禁止：
   - 特殊符号 (! $ ? _ {} ^ ~ # < > *)。
   - 促销语 (Free shipping, Sale) 和主观评价 (Best Seller)。

【五点描述规则 (Bullet Points)】
1. 核心原则：简洁清晰 (Concise & Clear)。不要说废话，直接切入痛点和解决方案。
2. **去重策略 (No Repetition)**：五点内容必须相互独立（MECE原则）。例如：第1点讲材质，第2点讲功能，第3点讲场景。**严禁**在不同的点中重复描述同一个意思。
3. 格式：
   - 采用 [Title Case Feature]: [Description] 结构。
   - **卖点短语 (冒号前)**：单词首字母大写，介词/连词小写 (例如: Long Battery Life for Travel)。不要全大写。
   - **具体描述 (冒号后)**：自然段落句式。
   - **标点禁令**：结尾【绝对不要】加句号、叹号等任何标点符号。
4. 内容：
   - **严禁主观词**：禁止使用 Premium, Best, Amazing, Top-quality 等自嗨词。必须用数据和事实说话。
   - 真实、准确、可量化。

【产品描述规则 (Description)】
1. 格式：HTML 代码 (<b>, <br>, <p>)。
2. 内容：完整句子，包含详细参数。"""
    # =========================================================

    with st.expander("📜 Listing 核心撰写规范", expanded=True):
        amazon_rules = st.text_area("在此输入平台规范：", value=default_amazon_rules, height=400)

    # Search Terms 规则
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
        forbidden_words = st.text_area(
            "严禁使用的词 (逗号分隔)", 
            value="Best Seller, No.1, Top rated, Free shipping, Guarantee, Warranty, Satisfaction, FDA approved, Anti-bacterial, Eco-friendly, Lowest Price, Discount, Sale, Cheap, Bonus, Gift, Prime, 100% Quality, High quality, Premium, Ultra, Super, Amazing, Unique, Perfect, durable, safe",
            height=150,
            help="包含主观形容词、促销词、医疗宣称、价格诱导词等，确保账户安全。"
        )

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
    if not text: return ""
    highlighted = re.sub(r"<<(.*?)>>", r"<span class='kw-highlight'>\1</span>", text)
    return highlighted

def clean_text_for_copy(text):
    if not text: return ""
    # 移除高亮符号
    text = text.replace("<<", "").replace(">>", "")
    # 【新增】强制移除末尾标点（针对五点描述的最后清洗）
    # 如果文本看起来像是一句话，且以句号结尾，去掉它。
    # 但为了防止误伤（比如 Description 是需要句号的），这个函数通常用于显示。
    # 我们只在 Bullet Point 的逻辑里做特殊处理。
    return text

def rewrite_section(section_key, prompt_instruction, context_data, rules_context):
    """
    AI 重写函数 - 升级版：注入规则库
    """
    try:
        model = genai.GenerativeModel('gemini-3-pro-preview')
        prompt = f"""
        你是一个亚马逊Listing优化专家。请仅重写 Listing 中的以下部分：【{section_key}】。
        
        【必须严格遵守的底层规则】
        {rules_context['amazon_rules']}
        
        【严禁使用的违禁词】
        {rules_context['forbidden_words']}
        
        【本次重写的具体要求】
        {prompt_instruction}
        
        【产品背景信息】
        产品:{context_data['product_name']}
        关键词:{context_data['top_keywords']}
        卖点:{context_data['core_selling_point']}
        
        【重要输出规则】
        1. 直接输出重写后的内容，不要加任何解释，不要 Markdown 代码块。
        2. 保持关键词高亮标记：使用 <<keyword>> 包裹核心词。
        3. 遵守所有格式规则（如 Title Case, 冒号格式）。
        4. **标点注意**：如果是 Bullet Point，结尾绝对不要加标点。
        """
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        st.error(f"重写失败: {e}")
        return None

# --- 5. 主界面 ---
st.title("✍️ Listing 文案工作室")
st.caption(f"Engine: Gemini 3.0 Pro | {category} | {language} | 通用高转化风格")

col1, col2 = st.columns([4, 6])

with col1:
    st.subheader("1. 产品档案")
    uploaded_file = st.file_uploader("上传产品主图 (仅供预览，不参与生成)", type=["jpg", "png", "jpeg", "webp"])
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
    
    generate_btn = st.button("✨ 立即生成 Listing (全部)", type="primary", use_container_width=True)
    st.caption("💡 提示：生成后，点击每项下方的 **🔄 AI 重写** 按钮可单独修改该部分。")

    # --- 上下文数据包 ---
    context_data = {
        "product_name": product_name,
        "top_keywords": top_keywords,
        "core_selling_point": core_selling_point,
        "usage_scope": usage_scope,
        "bullet_supplements": bullet_supplements,
        "category": category,
        "language": language,
        "tone": "亚马逊通用高转化风格"
    }
    
    # --- 规则数据包 (传递给重写函数) ---
    rules_context = {
        "amazon_rules": amazon_rules,
        "st_rules": st_rules,
        "forbidden_words": forbidden_words
    }

    # === 生成逻辑 ===
    if generate_btn:
        if not product_name:
            st.warning("请填写产品名称！")
        else:
            with st.spinner("🧠 Gemini 正在撰写 (如果想停止输出请点击界面右上角stop)..."):
                try:
                    model = genai.GenerativeModel('gemini-3-pro-preview')
                    
                    # === Prompt 升级 ===
                    # 【修改点1】不再传入 image_obj，只基于文本生成，避免视觉幻觉
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
                    
                    【重要指令：标题生成逻辑】
                    1. **参考风格**：模仿高信息密度风格："2 Pack 3D Embroidered Heart Throw Pillow Covers..."
                    2. **结构**：Brand + [Quantity/Pack Count] + Material/Technique/Feature + Core Keywords + Usage/Occasion.
                    3. **前60字符**：必须展示最核心的卖点。
                    4. **关键词数量限制**：【严禁堆砌】标题中最多包含 2-3 个最核心的大词。
                    
                    【重要指令：五点描述 (No Fluff & MECE)】
                    1. **去重原则 (MECE)**：确保这5点分别侧重于产品的不同维度（例如：尺寸、材质、功能、场景、售后）。严禁两点说同一件事。
                    2. **拒绝废话**：直接切入痛点。
                    3. **尺寸全覆盖**：如果用户输入了多个尺寸/变体，必须在关于尺寸的那一点中全部列出。
                    4. **标点禁令**：内容结尾【绝对不要】加句号。
                    5. **格式**：`[Title Case Feature]: [Description]`
                    
                    【重要指令：Search Terms (ST)】
                    1. **策略**：优先覆盖高流量词。
                    
                    【重要指令：关键词标记】
                    请将所有埋入的【核心关键词】用双尖括号 << >> 包裹起来。
                    例如：This <<Wireless Earbuds>> features...
                    
                    【输出格式】
                    仅输出 JSON：
                    {{ 
                        "title": "...", 
                        "bullet_point_1": "Feature: Description", 
                        "bullet_point_2": "Feature: Description", 
                        "bullet_point_3": "Feature: Description", 
                        "bullet_point_4": "Feature: Description", 
                        "bullet_point_5": "Feature: Description", 
                        "description": "HTML Code...", 
                        "search_terms": "..." 
                    }}
                    """
                    
                    # 纯文本生成
                    response = model.generate_content(prompt)
                    
                    clean_text_resp = response.text.replace("```json", "").replace("```", "")
                    result = parse_gemini_response(clean_text_resp)
                    
                    if result:
                        st.session_state["listing_data"] = result
                        st.success("✅ 生成成功！")
                    else:
                        st.error("解析失败")
                        st.text(response.text)
                except Exception as e:
                    st.error(f"错误: {e}")

    # === 展示与重写逻辑 ===
    data = st.session_state["listing_data"]
    
    if data["title"]:
        # --- 标题 ---
        st.markdown("#### 📝 Title (标题)")
        st.markdown(render_highlighted_text(data["title"]), unsafe_allow_html=True)
        new_title = st.text_area("Title", value=clean_text_for_copy(data["title"]), height=80, label_visibility="collapsed", key="txt_title")
        if st.button("🔄 重写标题 (不合适？)", key="btn_rewrite_title"):
            with st.spinner("正在重写标题..."):
                # 【修改点2】重写时传入具体限制
                instruction = "参考风格：2 Pack 3D Embroidered... 结构：Brand+Qty+Material+Keyword+Occasion。**注意：仅限2-3个核心关键词，不要堆砌。**"
                rewritten = rewrite_section("Title", instruction, context_data, rules_context)
                if rewritten:
                    st.session_state["listing_data"]["title"] = rewritten
                    st.rerun()

        # --- 五点 ---
        st.markdown("#### 📌 Bullet Points (五点描述)")
        for i in range(1, 6):
            key = f"bullet_point_{i}"
            val = data.get(key, "")
            
            # 【修改点3】代码层面的强制清洗：如果结尾有句号，去掉
            if val and val.strip().endswith("."):
                val = val.strip()[:-1]
            
            col_b1, col_b2 = st.columns([0.1, 0.9])
            with col_b1:
                st.markdown(f"**BP{i}**")
            with col_b2:
                st.markdown(render_highlighted_text(val), unsafe_allow_html=True)
                new_bp = st.text_area(f"BP{i}", value=clean_text_for_copy(val), height=100, label_visibility="collapsed", key=f"txt_{key}")
                
                if st.button(f"🔄 重写 BP{i}", key=f"btn_rewrite_{key}"):
                    with st.spinner(f"正在重写 BP{i}..."):
                        # 【修改点4】重写指令强调去重和标点
                        instruction = "更加简洁，去除废话。与其他五点保持内容独立，不要重复其他点的意思。**结尾不要加句号**。"
                        rewritten = rewrite_section(f"Bullet Point {i}", instruction, context_data, rules_context)
                        if rewritten:
                            st.session_state["listing_data"][key] = rewritten
                            st.rerun()

        # --- ST ---
        st.markdown("#### 🔍 Search Terms")
        st.text_area("Search Terms", value=clean_text_for_copy(data.get("search_terms", "")), height=100, key="txt_st")
        if st.button("🔄 重写 ST", key="btn_rewrite_st"):
            with st.spinner("正在挖掘更多长尾词..."):
                instruction = "挖掘更多同义词、场景词，不要标点符号，不要包含品牌名。"
                rewritten = rewrite_section("Search Terms", instruction, context_data, rules_context)
                if rewritten:
                    st.session_state["listing_data"]["search_terms"] = rewritten
                    st.rerun()

        # --- 描述 ---
        st.markdown("#### 📖 Description (HTML Source)")
        st.text_area("Description Code", value=clean_text_for_copy(data.get("description", "")), height=200, key="txt_desc")
        if st.button("🔄 重写描述", key="btn_rewrite_desc"):
            with st.spinner("正在重写描述..."):
                rewritten = rewrite_section("Product Description", "保持 HTML 格式，增加参数细节，语言更地道", context_data, rules_context)
                if rewritten:
                    st.session_state["listing_data"]["description"] = rewritten
                    st.rerun()

        # --- 总预览 ---
        st.markdown("---")
        with st.expander("📋 全局文案总览 (All-in-One Preview)", expanded=True):
            # 再次清洗一下总览里的标点
            bp1 = clean_text_for_copy(data.get('bullet_point_1', '')).rstrip('.')
            bp2 = clean_text_for_copy(data.get('bullet_point_2', '')).rstrip('.')
            bp3 = clean_text_for_copy(data.get('bullet_point_3', '')).rstrip('.')
            bp4 = clean_text_for_copy(data.get('bullet_point_4', '')).rstrip('.')
            bp5 = clean_text_for_copy(data.get('bullet_point_5', '')).rstrip('.')

            all_content = f"""【Title】
{clean_text_for_copy(data['title'])}

【Bullet Points】
1. {bp1}
2. {bp2}
3. {bp3}
4. {bp4}
5. {bp5}

【Search Terms】
{clean_text_for_copy(data.get('search_terms', ''))}

【Description (HTML)】
{clean_text_for_copy(data.get('description', ''))}
"""
            st.text_area("Full Listing Content", value=all_content, height=600)
