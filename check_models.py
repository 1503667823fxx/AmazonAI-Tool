import google.generativeai as genai

# ==========================================
# 🛑 请手动把你的 Key 粘贴在下面引号里！
# 就像这样： api_key = "AIzaSyDxxxx..."
# ==========================================
api_key = "AIzaSyAR5DZZisxftyk0MEyy1dmsQ1g5GU66QSg" 

if "在这里" in api_key:
    print("❌ 大哥/大姐，你忘了把 Key 填进代码里了！请修改 check_models.py 第 7 行。")
    exit()

print(f"🔑 正在尝试连接 Google 服务器...")

try:
    genai.configure(api_key=api_key)
    
    print("\n📋 你的账号能用的模型如下（复制 output 里的名字）：")
    print("=" * 40)
    
    found = False
    for m in genai.list_models():
        # 我们只关心能生成文本的模型
        if 'generateContent' in m.supported_generation_methods:
            print(f"🌟 {m.name}")
            found = True
            
    print("=" * 40)
    
    if not found:
        print("⚠️ 奇怪，连接成功了，但没有发现可用模型。")
        
except Exception as e:
    print(f"\n❌ 还是报错了！原因如下：\n{e}")