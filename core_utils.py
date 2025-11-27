import streamlit as st
import google.generativeai as genai
from PIL import Image
import io
import time
import json
import re
from collections import deque

# ==========================================
# 🧠 Tab 2 & 3: 双语基底分析 (强制 JSON)
# ==========================================
def analyze_image_bilingual(model_name, image_file, prompt_type="fashion"):
    """
    一次性让 AI 输出中文和英文描述，解决“中文框显示英文”的问题。
    """
    try:
        image_file.seek(0)
        img_obj = Image.open(image_file)
        model = genai.GenerativeModel(model_name)

        if prompt_type == "fashion":
            # Tab 2: 改款分析
            sys_prompt = """
            Analyze the fashion image details (Silhouette, Fabric, Color, Pattern).
            Output a JSON object with exactly two keys:
            {
                "zh": "此处填写详细的中文描述(Simplified Chinese)",
                "en": "Detailed description in English"
            }
            Output JSON ONLY. No markdown blocks.
            """
        else:
            # Tab 3: 背景锁定分析
            sys_prompt = """
            Describe the FOREGROUND PRODUCT ONLY. Ignore background.
            Output a JSON object with exactly two keys:
            {
                "zh": "此处填写产品的详细中文描述(Simplified Chinese)",
                "en": "Detailed description in English"
            }
            Output JSON ONLY. No markdown blocks.
            """

        # 生成并解析
        response = model.generate_content([sys_prompt, img_obj])
        txt = response.text.strip()
        
        # 清洗 JSON 格式 (去除 ```json 等包裹)
        txt = clean_json_string(txt)
        
        data = json.loads(txt)
        return data.get("en", ""), data.get("zh", "")

    except Exception as e:
        # 如果 JSON 解析失败，尝试用正则提取或者降级处理
        st.error(f"AI 分析格式异常，正在重试... ({str(e)})")
        return "", "分析失败，请重试"

# ==========================================
# 🧠 Tab 1: 智能创意分析 (强制 JSON 列表)
# ==========================================
def smart_analyze_image(model_name, image_file, task_type, user_idea, user_weight, enable_split):
    """
    Tab 1 的复杂创意生成，同样强制双语 JSON 输出。
    """
    try:
        image_file.seek(0)
        img_obj = Image.open(image_file)
        model = genai.GenerativeModel(model_name)
        
        weight_desc = f"User Weight: {user_weight} (1.0=User Idea dominant, 0.0=Image dominant)."
        
        # 构造强制 JSON 的 Prompt
        prompt_req = f"""
        Role: Art Director. Task: Create prompt(s) for {task_type}.
        User Idea: {user_idea}
        {weight_desc}
        
        Output a JSON LIST of objects. Each object must have "zh" and "en" keys.
        Example:
        [
            {{ "zh": "中文提示词1...", "en": "English prompt 1..." }},
            {{ "zh": "中文提示词2...", "en": "English prompt 2..." }}
        ]
        
        IMPORTANT: 
        1. If 'enable_split' is true, allow multiple objects. If false, return list with 1 object.
        2. Ensure "zh" is Simplified Chinese and "en" is English.
        3. Output JSON ONLY.
        """

        response = model.generate_content([prompt_req, img_obj])
        txt = response.text.strip()
        
        txt = clean_json_string(txt)
        result_list = json.loads(txt)
        
        # 格式化为标准格式
        final_data = []
        if isinstance(result_list, list):
            for item in result_list:
                final_data.append({
                    "en": item.get("en", ""),
                    "zh": item.get("zh", "")
                })
        elif isinstance(result_list, dict):
            final_data.append({
                "en": result_list.get("en", ""),
                "zh": result_list.get("zh", "")
            })
            
        return final_data

    except Exception as e:
        st.error(f"创意分析失败: {str(e)}")
        return []

# --- 辅助工具 ---
def clean_json_string(txt):
    """清洗 AI 输出的 JSON 字符串"""
    if txt.startswith("```"):
        txt = re.sub(r"^```json\s*", "", txt)
        txt = re.sub(r"^```\s*", "", txt)
        txt = re.sub(r"\s*```$", "", txt)
    return txt

# ==========================================
# 🗂️ 历史记录核心
# ==========================================
class HistoryManager:
    def __init__(self):
        if "history_queue" not in st.session_state:
            st.session_state["history_queue"] = deque(maxlen=20)

    def add(self, image_bytes, source, prompt_summary):
        timestamp = time.strftime("%H:%M")
        unique_id = f"{int(time.time()*1000)}"
        st.session_state["history_queue"].appendleft({
            "id": unique_id, "image": image_bytes, "source": source, "time": timestamp, "desc": prompt_summary
        })

    def render_sidebar(self):
        with st.expander("🕒 历史记录 (History)", expanded=False):
            if not st.session_state["history_queue"]:
                st.caption("暂无生成记录"); return
            for item in st.session_state["history_queue"]:
                c1, c2 = st.columns([1, 2])
                with c1: st.image(create_preview_thumbnail(item['image'], 150), use_container_width=True)
                with c2:
                    st.caption(f"**{item['source']}**")
                    st.caption(f"_{item['desc'][:15]}..._")
                    b1, b2 = st.columns(2)
                    if b1.button("🔍", key=f"h_z_{item['id']}"): show_preview_modal(item['image'], item['source'])
                    fb, m = process_image_for_download(item['image'], "JPEG")
                    b2.download_button("📥", fb, f"h_{item['id']}.jpg", m, key=f"h_d_{item['id']}")
                st.divider()

# ==========================================
# 🛠️ 图片/翻译工具
# ==========================================
@st.cache_data(show_spinner=False)
def process_image_for_download(image_bytes, format="PNG", quality=95):
    try:
        if not image_bytes: return None, None
        img = Image.open(io.BytesIO(image_bytes))
        buf = io.BytesIO()
        fmt = format.upper()
        if fmt == "JPEG":
            if img.mode in ("RGBA", "P"): img = img.convert("RGB")
            img.save(buf, "JPEG", quality=quality)
            return buf.getvalue(), "image/jpeg"
        img.save(buf, "PNG")
        return buf.getvalue(), "image/png"
    except: return image_bytes, "image/png"

@st.cache_data(show_spinner=False)
def create_preview_thumbnail(image_bytes, max_width=800):
    try:
        img = Image.open(io.BytesIO(image_bytes))
        if img.width > max_width:
            ratio = max_width / img.width
            img = img.resize((max_width, int(img.height * ratio)), Image.Resampling.LANCZOS)
        buf = io.BytesIO()
        if img.mode in ("RGBA", "P"): img = img.convert("RGB")
        img.save(buf, "JPEG", quality=70)
        return buf.getvalue()
    except: return image_bytes

def show_preview_modal(image_bytes, caption):
    st.toast(f"全屏预览: {caption}")
    st.image(image_bytes, caption=caption, use_container_width=True)

class AITranslator:
    def __init__(self):
        if "GOOGLE_API_KEY" in st.secrets:
            genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
            self.model = genai.GenerativeModel("models/gemini-flash-latest")
            self.valid = True
        else: self.valid = False
    
    def to_english(self, text):
        """将中文翻译成英文，用于同步逻辑"""
        if not text or not self.valid: return text
        try:
            prompt = f"Translate the following Chinese text to English for an AI image generator prompt. Output ONLY the English text.\nText: {text}"
            return self.model.generate_content(prompt).text.strip()
        except: return text

    def to_chinese(self, text): return text # 占位，新逻辑主要依赖 to_english
