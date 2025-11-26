import streamlit as st
import replicate
from PIL import Image
import io
import sys
import os
import base64
import uuid

# --- 0. 基础设置 ---
sys.path.append(os.path.abspath('.'))
try:
    import auth
    from core_utils import process_image_for_download 
except ImportError:
    pass 

# --- 安全导入画布 ---
try:
    from streamlit_drawable_canvas import st_canvas
except ImportError:
    st_canvas = None

st.set_page_config(page_title="Magic Canvas", page_icon="🖌️", layout="wide")

if 'auth' in sys.modules:
    if not auth.check_password():
        st.stop()

if "REPLICATE_API_TOKEN" in st.secrets:
    os.environ["REPLICATE_API_TOKEN"] = st.secrets["REPLICATE_API_TOKEN"]
else:
    st.error("❌ 缺少 REPLICATE_API_TOKEN")
    st.stop()

st.title("🖌️ 魔术画布 (Magic Canvas)")
st.caption("交互式局部重绘 & 智能扩图工作台")

if st_canvas is None:
    st.error("❌ 缺少组件，请检查 requirements.txt")
    st.stop()

# ==========================================
# 🛠️ 核心函数：手动转 Base64
# ==========================================
def pil_to_base64(image):
    """
    将 PIL 图片转为前端能直接显示的 Data URL 字符串。
    这能绕过 streamlit-drawable-canvas 内部破损的图片处理逻辑。
    """
    try:
        # 统一转 RGB (JPEG 兼容性最好)
        if image.mode != "RGB":
            image = image.convert("RGB")
        
        buff = io.BytesIO()
        image.save(buff, format="JPEG", quality=85)
        img_str = base64.b64encode(buff.getvalue()).decode()
        return f"data:image/jpeg;base64,{img_str}"
    except Exception as e:
        st.error(f"图片转换失败: {e}")
        return ""

# --- 状态管理 ---
if "canvas_key" not in st.session_state: st.session_state["canvas_key"] = str(uuid.uuid4())
if "last_upload" not in st.session_state: st.session_state["last_upload"] = None
if "magic_result" not in st.session_state: st.session_state["magic_result"] = None
if "out_result" not in st.session_state: st.session_state["out_result"] = None

tab_inp, tab_out = st.tabs(["🖌️ 交互式局部重绘", "↔️ 智能画幅扩展"])

# ==========================================
# Tab 1: 交互式重绘 (直通模式)
# ==========================================
with tab_inp:
    col_draw, col_result = st.columns([1.5, 1], gap="large")
    
    with col_draw:
        st.subheader("1. 涂抹修改区域")
        
        uploaded_file = st.file_uploader("上传原图", type=["png", "jpg", "jpeg"], key="inp_upload")
        
        bg_base64 = None # 准备发给画布的字符串
        original_pil = None # 保留 PIL 对象用于后续发送给 API
        
        if uploaded_file:
            try:
                raw_img = Image.open(uploaded_file).convert("RGB")
                
                # 1. 限制尺寸 (防止前端卡顿)
                max_w = 700
                if raw_img.width > max_w:
                    ratio = max_w / raw_img.width
                    new_h = int(raw_img.height * ratio)
                    original_pil = raw_img.resize((max_w, new_h), Image.Resampling.LANCZOS)
                else:
                    original_pil = raw_img
                
                # 2. 转换为 Base64 字符串 (绕过库的 Bug)
                bg_base64 = pil_to_base64(original_pil)
                
                # 3. 如果换图了，更新 Key 强制重绘组件
                if st.session_state["last_upload"] != uploaded_file.name:
                    st.session_state["canvas_key"] = str(uuid.uuid4())
                    st.session_state["last_upload"] = uploaded_file.name
                    st.rerun()
                    
            except Exception as e:
                st.error(f"读取图片出错: {e}")

        # --- 画布组件 ---
        if bg_base64:
            stroke_width = st.slider("画笔大小", 5, 50, 20)
            
            try:
                canvas_result = st_canvas(
                    fill_color="rgba(255, 255, 255, 0)",  
                    stroke_width=stroke_width,
                    stroke_color="#FFFFFF",
                    # 🚀 关键修改：这里传字符串，而不是 Image 对象
                    # 这样库就会跳过它内部那段报错的代码，直接把字符串发给前端
                    background_image=bg_image if False else None, # 故意置空
                    background_color="#eee", # 设个底色防止完全看不见
                    update_streamlit=True,   # 稍微开启实时以获得反馈，若卡顿可改为 False
                    height=original_pil.height,
                    width=original_pil.width,
                    drawing_mode="freedraw",
                    key=st.session_state["canvas_key"],
                    display_toolbar=True,
                )
                
                # 🛠️ 补丁方案：利用 markdown 强制把背景图塞到底层
                # 因为旧版组件可能不接受 base64 string 作为 background_image 参数
                # 我们用 CSS 手动把图片垫在画布下面
                st.markdown(
                    f"""
                    <style>
                    [data-testid="stImage"] {{
                        position: absolute;
                        top: 0;
                        left: 0;
                        z-index: 0;
                    }}
                    iframe {{
                        background-image: url("{bg_base64}");
                        background-size: contain;
                        background-repeat: no-repeat;
                        background-position: center;
                    }}
                    </style>
                    """,
                    unsafe_allow_html=True,
                )
                st.caption("💡 提示：如果看不到图片，请尝试缩放浏览器窗口。")

            except Exception as e:
                st.error(f"组件加载失败: {e}")

            prompt = st.text_area("2. 修改指令", placeholder="例如：Change to red silk dress...", height=80)
            
            if st.button("🚀 开始重绘", type="primary"):
                # 检查蒙版
                has_mask = False
                if canvas_result.image_data is not None:
                    if np.sum(canvas_result.image_data) > 0:
                        has_mask = True
                
                if not has_mask:
                    st.warning("请先涂抹区域！")
                else:
                    with st.spinner("AI 正在重绘..."):
                        try:
                            # 准备原图
                            src_buf = io.BytesIO()
                            original_pil.save(src_buf, format='JPEG', quality=95)
                            
                            # 准备蒙版
                            mask_data = canvas_result.image_data.astype('uint8')
                            mask_img = Image.fromarray(mask_data, mode="RGBA")
                            mask_img = mask_img.split()[3] # Alpha
                            
                            mask_buf = io.BytesIO()
                            mask_img.save(mask_buf, format='PNG')
                            
                            output = replicate.run(
                                "black-forest-labs/flux-fill-pro",
                                input={
                                    "image": src_buf,
                                    "mask": mask_buf,
                                    "prompt": prompt,
                                    "output_format": "jpg",
                                    "output_quality": 95
                                }
                            )
                            st.session_state["magic_result"] = str(output)
                            st.success("完成！")
                        except Exception as e:
                            st.error(f"API 错误: {e}")

    with col_result:
        st.subheader("🖼️ 结果展示")
        if st.session_state["magic_result"]:
            st.image(st.session_state["magic_result"], caption="重绘结果", use_container_width=True)
        else:
            st.info("等待操作...")

# ==========================================
# Tab 2: 画幅扩展 (Flux Fill)
# ==========================================
with tab_out:
    st.markdown("### ↔️ 智能扩图")
    c1, c2 = st.columns([1, 1])
    with c1:
        out_img = st.file_uploader("上传原图", key="out_img_up")
        target_ar = st.selectbox("扩展比例", ["16:9", "9:16", "4:3", "1:1"], index=0)
        out_prompt = st.text_input("环境描述", placeholder="Modern background...")
        
        if st.button("🚀 开始扩展"):
            if out_img:
                with st.spinner("扩展中..."):
                    try:
                        out_res = replicate.run(
                            "black-forest-labs/flux-fill-pro",
                            input={
                                "image": out_img,
                                "prompt": out_prompt if out_prompt else "background texture",
                                "aspect_ratio": target_ar,
                                "output_format": "jpg"
                            }
                        )
                        st.session_state["out_result"] = str(out_res)
                    except Exception as e:
                        st.error(f"失败: {e}")
    
    with c2:
        if st.session_state["out_result"]:
            st.image(st.session_state["out_result"], caption="扩图结果", use_container_width=True)
