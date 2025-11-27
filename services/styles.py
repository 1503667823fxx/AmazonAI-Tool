# services/styles.py

"""
亚马逊电商风格预设库 (Amazon Fashion Style Library)
可以在这里随时添加新的风格，无需修改核心代码。
格式：
"显示名称": {
    "desc": "核心风格描述词",
    "lighting": "光影建议",
    "negative": "默认自带的负向词(可选)"
}
"""

PRESETS = {
    "💡 默认 (None)": {
        "desc": "",
        "lighting": "natural commercial lighting",
        "negative": ""
    },
    "⚪ 亚马逊纯白 (Studio White)": {
        "desc": "professional Amazon e-commerce photography, clean pure white background, high end fashion",
        "lighting": "soft studio lighting, uniform illumination, no harsh shadows",
        "negative": "dark background, messy background, low light, shadows"
    },
    "🏙️ 街头潮流 (Urban Street)": {
        "desc": "trendy streetwear fashion photography, blurred city street background, bokeh",
        "lighting": "natural sunlight, golden hour, dynamic shadows",
        "negative": "studio lighting, indoor, plain background"
    },
    "🏠 居家休闲 (Cozy Home)": {
        "desc": "lifestyle photography, cozy modern living room background, comfortable atmosphere",
        "lighting": "warm interior lighting, soft window light",
        "negative": "cold colors, industrial, outdoor"
    },
    "✨ 极简高级 (Luxury Minimalist)": {
        "desc": "luxury fashion editorial, minimalist architectural background, concrete or marble texture",
        "lighting": "dramatic high-contrast lighting, artistic shadows",
        "negative": "cluttered, messy, colorful background"
    },
    "🌲 户外自然 (Nature/Outdoor)": {
        "desc": "outdoor lifestyle photography, nature park or forest background, fresh vibe",
        "lighting": "bright daylight, sun flare",
        "negative": "urban, building, indoor"
    }
}
