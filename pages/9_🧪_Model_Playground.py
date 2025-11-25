import streamlit as st
import requests
import json
import base64
from PIL import Image
import io
import sys
import os

# --- 0. 引入门禁 ---
sys.path.append(os.path.abspath('.'))
try:
    import auth
    if not auth.check_password(): st.stop()
except ImportError:
    pass 

st.set_page_config(page_title="API 终极实验室", page_icon="🧪", layout="wide")

st.title("🧪 Gemini API 终极实验室 (TS 复刻版)")
st.info("本页面 1:1 复刻了 geminiService.ts 中的 '纹理锚定' 和 '图像预处理' 逻辑。")

# --- 1. 配置 ---
if "GOOGLE_API_KEY" not in st.secrets:
    st.error("请配置 GOOGLE_API_KEY")
    st.stop()

API_KEY = st.secrets["GOOGLE_API_KEY"]

# --- 2. TS 逻辑复刻函数 (Python版) ---

def resize_for_context(pil_img, max_dim=1024):
    """
    复刻 TS: resizeForContext
    将图片限制在 max_dim 以内，保持比例，转为 PNG
    """
    w, h = pil_img.size
    if w > max_dim or h > max_dim:
        ratio = min(max_dim / w, max_dim / h)
        new_w = int(w * ratio)
        new_h = int(h * ratio)
        pil_img = pil_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
    
    # 转 Base64 PNG
    buff = io.BytesIO()
    pil_img.save(buff, format="PNG")
    return base64.b64encode(buff.getvalue()).decode('utf-8')

def extract_texture_patch(pil_img):
    """
    复刻 TS: extractTexturePatch
    提取图片中心 50% 的区域作为纹理参考 (Ground Truth)
    """
    w, h = pil_img.size
    crop_w = int(w * 0.5)
    crop_h = int(h * 0.5)
    
    left = (w - crop_w) // 2
    top = (h - crop_h) // 2
    right = left + crop_w
    bottom = top + crop_h
    
    crop_img = pil_img.crop((left, top, right, bottom))
    
    # 转 Base64 PNG
    buff = io.BytesIO()
    crop_img.save(buff, format="PNG")
    return base64.b64encode(buff.getvalue()).decode('utf-8')

# --- 3. 界面 ---

col1, col2 = st.columns([4, 6])

with col1:
    st.subheader("1. 参数配置")
    
    # TS 代码写死用的这个模型
    model_name = st.text_input("模型名称", value="gemini-2.5-flash-image")
    
    uploaded_file = st.file_uploader("上传图片", type=["jpg", "png", "webp"])
    
    prompt_input = st.text_area("修改指令", value="Change the background to a luxury office", height=100)
    
    # 模拟 TS 的模式选择
    mode = st.radio("模式 (Mode)", ["Simple Edit (简单编辑)", "Texture Anchor (纹理锚定 - 强力推荐)"])

with col2:
    st.subheader("2. 执行与诊断")
    
    if st.button("🚀 发送请求 (复刻 TS 逻辑)", type="primary"):
        if not uploaded_file:
            st.warning("请上传图片")
        else:
            status = st.empty()
            debug_area = st.expander("🔍 查看 Payload 和 响应", expanded=True)
            
            try:
                status.info("正在预处理图片 (Resize & Crop)...")
                
                # 加载图片并转 RGB
                original_pil = Image.open(uploaded_file).convert("RGB")
                
                # 1. 准备主图 (Clean Source) - 限制尺寸
                clean_source_b64 = resize_for_context(original_pil, max_dim=1024)
                
                parts = []
                
                if mode == "Simple Edit (简单编辑)":
                    # 对应 TS 代码 line 408 (Standard General Edit)
                    final_prompt = f"Edit instruction: {prompt_input}. Maintain photorealism."
                    parts.append({"text": final_prompt})
                    parts.append({"inline_data": {"mime_type": "image/png", "data": clean_source_b64}})
                    
                else:
                    # 对应 TS 代码 line 390 (general fusion mode with Texture Patch)
                    # 2. 准备纹理补丁 (Texture Patch)
                    texture_patch_b64 = extract_texture_patch(original_pil)
                    
                    # 构造超强 Prompt
                    final_prompt = f"""Task: High-Fidelity Image Editing with TEXTURE ANCHORING.
Input 1: Source Image.
Input 2: TEXTURE PATCH (Ground Truth).

Instructions:
1. Edit the image according to: "{prompt_input}".
2. TEXTURE CONSISTENCY: Use Input 2 to understand the material quality. The generated area MUST match this texture.
3. Maintain photorealism.
"""
                    parts.append({"text": final_prompt})
                    parts.append({"inline_data": {"mime_type": "image/png", "data": clean_source_b64}}) # Input 1
                    parts.append({"inline_data": {"mime_type": "image/png", "data": texture_patch_b64}}) # Input 2 (Texture Patch)

                # 构建请求体
                payload = {
                    "contents": [{"parts": parts}],
                    "generationConfig": {
                        "response_modalities": ["IMAGE"],
                        "temperature": 0.4
                    }
                }
                
                # 发起 HTTP 请求
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={API_KEY}"
                
                status.info(f"正在 POST 到 {model_name} ...")
                
                response = requests.post(
                    url,
                    headers={"Content-Type": "application/json"},
                    data=json.dumps(payload)
                )
                
                # 处理响应
                if response.status_code == 200:
                    res_json = response.json()
                    with debug_area:
                        st.caption("Payload Preview (已发送):")
                        st.json({k:v for k,v in payload.items() if k != "contents"}) # 不显示巨大的 content
                        st.caption("API Response:")
                        st.json(res_json)
                    
                    # 提取图片
                    try:
                        candidates = res_json.get("candidates", [])
                        if candidates and candidates[0].get("content", {}).get("parts"):
                            part = candidates[0]["content"]["parts"][0]
                            if "inline_data" in part:
                                b64_data = part["inline_data"]["data"]
                                img_data = base64.b64decode(b64_data)
                                st.image(img_data, caption="Gemini 生成结果 (复刻成功!)")
                                st.success("🎉 成功！TS 逻辑复刻生效！")
                            else:
                                st.error("⚠️ API 返回了 Success 但没有图片 (可能是被拦截)。请查看 JSON。")
                        else:
                            st.error("⚠️ 返回数据结构异常。")
                    except Exception as e:
                        st.error(f"解析失败: {e}")
                else:
                    status.error(f"HTTP {response.status_code}")
                    st.error(response.text)

            except Exception as e:
                st.error(f"系统错误: {e}")
                    st.error(response.text) # 打印报错详情
                    
            except Exception as e:
                st.error(f"系统错误: {e}")
