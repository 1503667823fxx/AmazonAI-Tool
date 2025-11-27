import streamlit as st
import google.generativeai as genai
from PIL import Image
import io
import time
import json
import re
from collections import deque

# ==========================================
# 🧠 双语智能分析 (Bilingual Analysis) [NEW]
# ==========================================
def analyze_image_bilingual(model_name, image_file, prompt_type="fashion"):
    """
    专门用于 Tab 2 和 Tab 3 的双语读图函数。
    强制 AI 输出 JSON 格式，同时包含英文和中文描述。
    """
    try:
        image_file.seek(0)
        img_obj = Image.open(image_file)
        model = genai.GenerativeModel(model_name)

        if prompt_type == "fashion":
            # Tab 2: 改款分析 Prompt
            sys_prompt = """
            Analyze the fashion image. Describe the Silhouette, Fabric, Color, and Pattern in detail.
            Output a JSON object with two keys:
            1. "en": The description in English.
            2. "zh": The description in Simplified Chinese (简体中文).
            ENSURE the Chinese translation is accurate and natural fashion terminology.
            Output JSON ONLY. No markdown blocks.
            """
        else:
            # Tab 3: 背景置换分析 Prompt
            sys_prompt = """
            Describe the FOREGROUND PRODUCT ONLY in detail. Ignore the background.
            Output a JSON object with two keys:
            1. "en": The description in English.
            2. "zh": The description in Simplified Chinese (简体中文).
            ENSURE the Chinese translation is accurate.
            Output JSON ONLY. No markdown blocks.
            """

        # 生成内容
        response = model.generate_content([sys_prompt, img_obj])
        txt = response.text.strip()
        
        # 清洗 Markdown 标记 (如果 AI 加了 ```json ... ```)
        if txt.startswith("```"):
            txt = re.sub(r"^```json\s*", "", txt)
            txt = re.sub(r"^```\s*", "", txt)
            txt = re.sub(r"\s*```$", "", txt)
        
        # 解析 JSON
        try:
            data = json.loads(txt)
            return data.get("en", ""), data.get("zh", "")
        except json.JSONDecodeError:
            # 兜底：如果 JSON 解析失败，尝试用简单的规则分割或直接返回原文本
            st.warning("AI 输出格式轻微异常，正在尝试修复...")
            return txt, "自动翻译失败，请参考英文版"

    except Exception as e:
        st.error(f"双语分析失败: {str(e)}")
        return "", ""

# ==========================================
# 🧠 智能分析核心 (Smart Analysis Engine - Tab 1)
# ==========================================
def smart_analyze_image(model_name, image_file, task_type, user_idea, user_weight, enable_split, translator):
    """
    Tab 1 的复杂分析逻辑 (保持原样，微调稳定性)
    """
    try:
        image_file.seek(0)
        img_obj = Image.open(image_file)
        model = genai.GenerativeModel(model_name)
        
        special_instruction = ""
        if "Product Only" in task_type:
            special_instruction = "Focus on product details, lighting, and texture."
        
        weight_instruction = f"User Weight: {user_weight}. (1.0 = Follow User Idea strictly, 0.0 = Follow Image strictly)."
        lang_instruction = "Output strictly in English. Use '|||' to separate multiple prompts if needed."

        prompt_req = f"""
        Role: Art Director. Task: Create prompt(s) for {task_type}.
        User Idea: {user_idea}
        {weight_instruction}
        {special_instruction}
        {lang_instruction}
        Output pure text, no markdown.
        """

        response = model.generate_content([prompt_req, img_obj])
        raw_text = response.text.strip()
        
        prompt_list = raw_text.split("|||")
        result_data = []
        
        for p in prompt_list:
            p_en = p.strip().lstrip("=- ").strip()
            if p_en:
                p_zh = translator.to_chinese(p_en)
                if not p_zh: p_zh = p_en
                result_data.append({"en": p_en, "zh": p_zh})
        
        return result_data

    except Exception as e:
        st.error(f"Tab 1 分析模块出错: {str(e)}")
        return []

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
# 🛠️ 图片/工具核心
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
    def to_chinese(self, t): return self._run(t, "Simplified Chinese") if self.valid and t else t
    def to_english(self, t): return self._run(t, "English") if self.valid and t else t
    def _run(self, text, lang):
        try: return self.model.generate_content(f"Translate to {lang}. Output ONLY text: {text}").text.strip()
        except: return text
