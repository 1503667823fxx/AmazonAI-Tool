import streamlit as st
import google.generativeai as genai
from PIL import Image
import json
import sys      # (这两行是为了让子页面能找到根目录的 auth.py，必须要加)
import os
sys.path.append(os.path.abspath('.'))
import auth     # <--- 引入

# --- 1. 页面基础配置 ---
st.set_page_config(
    page_title="亚马逊全能智造台 V2.1",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded"
)
if not auth.check_password():
    st.stop()
    
# 自定义 CSS：优化间距，让界面更紧凑，代码块字体更清晰
st.markdown("""
<style>
    .stTextArea textarea {font-size: 14px; font-family: 'Microsoft YaHei', sans-serif;}
    .reportview-container .main .block-container {padding-top: 2rem;}
    /* 优化侧边栏字体 */
    section[data-testid="stSidebar"] {
        width: 400px !important; # 尝试加宽侧边栏
    }
</style>
""", unsafe_allow_html=True)

# --- 2. 验证 API Key ---
try:
    if "GOOGLE_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    else:
        st.error("❌ 未找到 Google API Key。请检查 .streamlit/secrets.toml")
        st.stop()
except Exception as e:
    st.error(f"API配置出错: {e}")

# --- 3. 侧边栏：规则与红线 (Rule Engine) ---
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/a/a9/Amazon_logo.svg", width=120)
    st.title("⚙️ 全局规则配置")
    
    # Layer 2: 品类与风格
    col_s1, col_s2 = st.columns(2)
    with col_s1:
        category = st.selectbox("品类", ["3C电子", "家居生活", "时尚服饰", "户外运动", "母婴用品", "美妆个护", "宠物用品", "汽配"])
    with col_s2:
        language = st.selectbox("语言", ["English (US)", "English (UK)", "Deutsch (DE)", "Français (FR)", "日本語 (JP)", "Español (ES)"])

    tone = st.selectbox("文案风格", ["专业权威 (Professional)", "极具感染力 (Persuasive)", "简洁清晰 (Concise)", "生活化 (Lifestyle)"])
    
    st.divider()
    
    # Layer 3: 亚马逊撰写规则 (已放大)
    default_amazon_rules = """1. 标题：品牌名开头，核心词前置，首字母大写(介词除外)，无特殊符号。
2. 五点：采用 [大写卖点] + [具体描述] 结构。每点不超过200字符。
3. 严禁：夸大宣传(Best/No.1)，保修承诺(Warranty)，引导好评。
4. 格式：数字请用阿拉伯数字(1, 2)而非单词(one, two)。"""
    
    with st.expander("📜 Listing 通用撰写规则 (点击展开)", expanded=True):
        amazon_rules = st.text_area(
            "在此输入平台规范，框体已加大：",
            value=default_amazon_rules,
            height=300, # 大幅增加高度
            help="在这里编辑所有通用的撰写逻辑，AI会严格遵守。"
        )

    # Search Terms 规则 (单独新增)
    default_st_rules = """1. 仅包含关键词，用空格分隔。
2. 不要重复标题和五点中已出现的词。
3. 不要使用品牌名或竞品名。
4. 总字节数控制在 249 bytes 以内。"""

    with st.expander("🔍 Search Terms (ST) 规则", expanded=False):
        st_rules = st.text_area(
            "后台关键词规则：",
            value=default_st_rules,
            height=150
        )

    # 违禁词库
    with st.expander("🛑 违禁词库 (Blacklist)", expanded=False):
        forbidden_words = st.text_area(
            "严禁使用的词 (逗号分隔)",
            value="Best Seller, No.1, Top rated, Free shipping, Guarantee, 100%, Satisfaction, FDA approved",
            height=100
        )

# --- 4. 辅助函数 ---
def parse_gemini_response(text):
    """尝试从 Gemini 的回复中提取 JSON"""
    try:
        start = text.find('{')
        end = text.rfind('}') + 1
        if start != -1 and end != -1:
            return json.loads(text[start:end])
    except:
        pass
    return None

# --- 5. 主界面布局 ---
st.title("🛒 亚马逊 Listing 生成器 V2.1")
st.caption(f"当前引擎：Gemini 3.0 Pro | 模式：{category} + {language} | 优化的宽屏编辑模式")

# 调整列比例，给右侧输出区更多空间 [4, 6]
col1, col2 = st.columns([4, 6])

# === 左侧：深度信息输入 ===
with col1:
    st.subheader("1. 产品档案 (Product DNA)")
    
    # 基础信息
    uploaded_file = st.file_uploader("上传产品主图", type=["jpg", "png", "jpeg", "webp"])
    if uploaded_file:
        st.image(uploaded_file, width=150)
        
    product_name = st.text_input("产品名称 (Core Name) *", placeholder="例如：Active Noise Cancelling Headphones")
    
    # 核心SEO
    top_keywords = st.text_area("🔍 核心关键词 Top 10 (SEO Keywords) *", 
                                placeholder="流量词，AI会强制埋入标题和五点中。\n例如：wireless earbuds, bluetooth headphones...",
                                height=100)
    
    # 深度细节 (已删除 What's in the box)
    with st.expander("📝 详细卖点与参数", expanded=True):
        core_selling_point = st.text_area("💎 核心卖点描述", placeholder="例如：行业领先的42dB降噪深度，瞬间静音。", height=100)
        usage_scope = st.text_area("🎯 适用范围/人群", placeholder="例如：通勤、健身房、飞机出行。兼容iPhone和Android。", height=100)
        bullet_supplements = st.text_area("➕ 五点描述补充内容", placeholder="还有什么必须写进五点的？例如：IPX7防水等级。", height=100)

# === 右侧：生成结果 ===
with col2:
    st.subheader("2. 智能生成结果 (Review & Edit)")
    
    generate_btn = st.button("✨ 立即生成 Listing", type="primary", use_container_width=True)

    if generate_btn:
        if not uploaded_file or not product_name:
            st.warning("⚠️ 请至少上传图片并填写产品名称！")
        else:
            with st.spinner("🧠 深度分析中... \n(AI正在阅读您的规则库...)"):
                try:
                    # 使用 3.0 Pro Preview
                    model = genai.GenerativeModel('gemini-3-pro-preview')
                    
                    # 构建 Prompt (移除装箱清单，加入ST规则)
                    prompt = f"""
                    你是一个亚马逊Listing顶级撰写专家。请严格基于以下信息生成Listing。

                    【产品档案】
                    - 产品名称: {product_name}
                    - 核心关键词(必须埋入): {top_keywords}
                    - 核心卖点: {core_selling_point}
                    - 适用范围: {usage_scope}
                    - 补充要求: {bullet_supplements}
                    
                    【目标受众与风格】
                    - 语言: {language}
                    - 风格: {tone}
                    - 品类: {category}

                    【全局撰写规则 (Compliance)】
                    {amazon_rules}
                    
                    【后台关键词规则 (Search Terms)】
                    {st_rules}

                    - 严禁词汇: {forbidden_words}

                    【输出格式 - JSON】
                    请仅输出标准 JSON，包含以下字段：
                    {{
                        "title": "符合SEO规则的标题",
                        "bullet_point_1": "大写卖点: 描述",
                        "bullet_point_2": "大写卖点: 描述",
                        "bullet_point_3": "大写卖点: 描述",
                        "bullet_point_4": "大写卖点: 描述",
                        "bullet_point_5": "大写卖点: 描述",
                        "description": "HTML格式的产品描述(A+文本)",
                        "search_terms": "后台ST词"
                    }}
                    """
                    
                    # 传入图片和Prompt
                    image_obj = Image.open(uploaded_file)
                    response = model.generate_content([prompt, image_obj])
                    
                    # 解析
                    result = parse_gemini_response(response.text)
                    
                    if result:
                        st.success("✅ 生成成功！所有文本框均可直接编辑修改。")
                        
                        st.markdown("#### 📝 Title (标题)")
                        st.text_area("Title", value=result.get("title", ""), height=100, label_visibility="collapsed")
                        
                        st.markdown("#### 📌 Bullet Points (五点描述)")
                        # 使用 text_area 替代 code，实现自动换行和编辑功能
                        st.text_area("Bullet 1", value=result.get("bullet_point_1", ""), height=100)
                        st.text_area("Bullet 2", value=result.get("bullet_point_2", ""), height=100)
                        st.text_area("Bullet 3", value=result.get("bullet_point_3", ""), height=100)
                        st.text_area("Bullet 4", value=result.get("bullet_point_4", ""), height=100)
                        st.text_area("Bullet 5", value=result.get("bullet_point_5", ""), height=100)
                        
                        st.markdown("#### 🔍 Search Terms (后台ST - 独立规则控制)")
                        st.text_area("Search Terms", value=result.get("search_terms", ""), height=100)
                        
                        st.markdown("#### 📖 Description (文案)")
                        st.text_area("Description (HTML)", value=result.get("description", ""), height=300)
                        
                    else:
                        st.error("⚠️ 格式解析失败，请重试。以下是原始内容：")
                        st.text(response.text)
                        
                except Exception as e:
                    st.error(f"发生错误: {e}")

st.markdown("---")
st.caption("Amazon AI Studio V2.1 | Powered by Gemini 3.0 Pro")
