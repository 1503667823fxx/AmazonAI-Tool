import streamlit as st
import sys
import os
import datetime

# --- 0. 基础设置与路径 ---
sys.path.append(os.path.abspath('.'))
try:
    import auth
except ImportError:
    pass

# --- 1. 页面配置 (默认收起侧边栏) ---
st.set_page_config(
    page_title="Amazon AI Hub",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="collapsed" # 默认收起
)

# --- 2. 深度样式定制 (CSS) ---
st.markdown("""
<style>
    /* 1. 隐藏 Home 页面的侧边栏导航，防止冲突 */
    [data-testid="stSidebarNav"] {
        display: none !important;
    }
    [data-testid="stSidebar"] {
        display: none !important;
    }
    
    /* 隐藏Streamlit原生弹窗和工具栏 */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stDeployButton {display: none;}
    .stDecoration {display: none;}
    
    /* 隐藏右上角的Share按钮和菜单 */
    [data-testid="stToolbar"] {
        display: none !important;
    }
    
    /* 隐藏右上角的设置按钮 */
    button[title="View fullscreen"] {
        display: none !important;
    }
    
    /* 隐藏GitHub图标等 */
    .css-1jc7ptx, .e1ewe7hr3, .viewerBadge_container__1QSob, .styles_viewerBadge__1yB5_, .viewerBadge_link__1S137, .viewerBadge_text__1JaDK {
        display: none !important;
    }
    
    /* 2. 全局字体与背景优化 */
    .main {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        min-height: 100vh;
    }
    
    /* 3. 标题样式 */
    .hero-title {
        font-size: 3rem;
        font-weight: 900;
        background: linear-gradient(135deg, #232F3E, #FF9900, #146EB4);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 0.5rem;
        text-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .hero-subtitle {
        font-size: 1.2rem;
        color: #666;
        text-align: center;
        margin-bottom: 3rem;
        font-weight: 300;
    }

    /* 4. 卡片容器样式 */
    .feature-card {
        background: rgba(255, 255, 255, 0.95);
        border: none;
        border-radius: 16px;
        padding: 24px;
        box-shadow: 0 8px 32px rgba(0,0,0,0.1);
        backdrop-filter: blur(10px);
        transition: all 0.3s ease;
        height: 100%;
        border: 1px solid rgba(255, 255, 255, 0.2);
    }
    .feature-card:hover {
        transform: translateY(-8px);
        box-shadow: 0 16px 48px rgba(0,0,0,0.15);
        border-color: #FF9900;
    }

    /* 5. 状态徽章样式 */
    .status-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.7rem;
        font-weight: 600;
        margin-left: 8px;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .badge-stable { 
        background: linear-gradient(135deg, #10b981, #059669);
        color: white;
        box-shadow: 0 2px 8px rgba(16, 185, 129, 0.3);
    }
    .badge-beta { 
        background: linear-gradient(135deg, #f59e0b, #d97706);
        color: white;
        box-shadow: 0 2px 8px rgba(245, 158, 11, 0.3);
    }
    .badge-dev { 
        background: linear-gradient(135deg, #6b7280, #4b5563);
        color: white;
        box-shadow: 0 2px 8px rgba(107, 114, 128, 0.3);
    }
    
    /* 6. 分类标题 */
    .category-title {
        font-size: 1.8rem;
        font-weight: 700;
        color: #1f2937;
        margin: 40px 0 20px 0;
        text-align: center;
        position: relative;
    }
    .category-title::after {
        content: '';
        position: absolute;
        bottom: -8px;
        left: 50%;
        transform: translateX(-50%);
        width: 60px;
        height: 3px;
        background: linear-gradient(135deg, #FF9900, #232F3E);
        border-radius: 2px;
    }

    /* 7. 按钮样式优化 */
    .stButton > button {
        background: linear-gradient(135deg, #FF9900, #e68900);
        color: white;
        border: none;
        border-radius: 12px;
        padding: 12px 24px;
        font-weight: 600;
        transition: all 0.3s ease;
        box-shadow: 0 4px 16px rgba(255, 153, 0, 0.3);
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 24px rgba(255, 153, 0, 0.4);
    }

    /* 8. 统计卡片 */
    .stats-card {
        background: rgba(255, 255, 255, 0.9);
        border-radius: 12px;
        padding: 20px;
        text-align: center;
        box-shadow: 0 4px 16px rgba(0,0,0,0.1);
        border: 1px solid rgba(255, 255, 255, 0.3);
    }
</style>
""", unsafe_allow_html=True)

# --- 3. 安全门禁 ---
if 'auth' in sys.modules:
    if not auth.check_password():
        st.stop()

# --- 4. 欢迎头部 ---
st.markdown('<div class="hero-title">🚀 Amazon AI Hub</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-subtitle">智能运营工作台 · 让AI为你的电商业务赋能</div>', unsafe_allow_html=True)

# --- 实时资讯模块 ---
@st.cache_data(ttl=1800)  # 缓存30分钟
def get_real_amazon_news():
    """获取真实的Amazon相关资讯"""
    import requests
    from datetime import datetime, timedelta
    
    news_items = []
    rss_success = False
    
    try:
        # 方案1: 尝试多个RSS源
        try:
            import feedparser
            
            # 扩展RSS源列表，增加成功率
            rss_feeds = [
                {
                    'url': 'https://press.aboutamazon.com/rss/news-releases.xml',
                    'source': '官方新闻',
                    'timeout': 10
                },
                {
                    'url': 'https://blog.aboutamazon.com/feed',
                    'source': '官方博客',
                    'timeout': 10
                },
                {
                    'url': 'https://advertising.amazon.com/blog/feed',
                    'source': '广告博客',
                    'timeout': 10
                },
                # 添加更多可能有内容的RSS源
                {
                    'url': 'https://aws.amazon.com/blogs/aws/feed/',
                    'source': 'AWS博客',
                    'timeout': 10
                },
                {
                    'url': 'https://developer.amazon.com/blogs/alexa/feed.xml',
                    'source': 'Alexa开发',
                    'timeout': 10
                }
            ]
            
            for feed_info in rss_feeds:
                try:
                    # 设置用户代理，避免被拒绝
                    feed = feedparser.parse(feed_info['url'])
                    
                    if feed.entries and len(feed.entries) > 0:
                        # 找到有内容的源就标记成功
                        rss_success = True
                        
                        # 处理每个条目，降低过滤条件
                        for entry in feed.entries[:3]:  # 每个源取3条，增加机会
                            pub_date = datetime.now()
                            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                                try:
                                    pub_date = datetime(*entry.published_parsed[:6])
                                except:
                                    pub_date = datetime.now()
                            
                            # 几乎不过滤时间，只要有内容就要
                            days_old = (datetime.now() - pub_date).days
                            if days_old <= 730:  # 2年内的内容都要
                                # 清理HTML标签和描述
                                desc = getattr(entry, 'summary', getattr(entry, 'description', ''))
                                if desc:
                                    import re
                                    desc = re.sub('<[^<]+?>', '', desc)
                                    desc = re.sub(r'\s+', ' ', desc).strip()
                                    desc = desc[:150] + '...' if len(desc) > 150 else desc
                                else:
                                    desc = f'来自{feed_info["source"]}的最新资讯，点击查看详情'
                                
                                news_items.append({
                                    'title': entry.title[:80] + '...' if len(entry.title) > 80 else entry.title,
                                    'desc': desc,
                                    'link': entry.link,
                                    'source': feed_info['source'],
                                    'date': pub_date.strftime('%Y-%m-%d'),
                                    'is_rss': True
                                })
                                
                                # 限制总数，避免过多
                                if len(news_items) >= 8:
                                    break
                    
                    # 如果已经获取到足够内容，跳出循环
                    if len(news_items) >= 6:
                        break
                        
                except Exception as e:
                    # 记录但不显示错误，继续尝试下一个源
                    continue
                    
        except ImportError:
            # feedparser未安装，跳过RSS
            pass
        
        # 方案2: 补充官方资源链接（始终显示，确保有内容）
        official_links = [
            {
                'title': 'Amazon Seller Central - 卖家资讯中心',
                'desc': '获取最新的政策更新、费用调整、新功能发布等官方资讯',
                'link': 'https://sellercentral.amazon.com/news',
                'source': '卖家中心',
                'date': datetime.now().strftime('%Y-%m-%d'),
                'is_rss': False
            },
            {
                'title': 'Amazon Advertising Blog - 广告策略',
                'desc': '了解最新广告功能、优化技巧和行业趋势分析',
                'link': 'https://advertising.amazon.com/blog',
                'source': '广告中心',
                'date': datetime.now().strftime('%Y-%m-%d'),
                'is_rss': False
            },
            {
                'title': 'Amazon Brand Registry - 品牌保护',
                'desc': '品牌注册指南、知识产权保护和反假冒政策更新',
                'link': 'https://brandregistry.amazon.com/help',
                'source': '品牌注册',
                'date': datetime.now().strftime('%Y-%m-%d'),
                'is_rss': False
            },
            {
                'title': 'FBA Resource Center - 物流资源',
                'desc': 'FBA费用计算、库存管理、配送政策的详细说明',
                'link': 'https://sellercentral.amazon.com/fba',
                'source': 'FBA中心',
                'date': datetime.now().strftime('%Y-%m-%d'),
                'is_rss': False
            }
        ]
        
        # 如果RSS成功，添加2个官方链接；如果失败，添加所有官方链接
        if rss_success and len(news_items) >= 2:
            news_items.extend(official_links[:2])
        else:
            news_items.extend(official_links)
        
        # 返回前4条，确保数量一致
        return news_items[:4], rss_success
        
    except Exception as e:
        # 完全失败时的最小备用方案
        return [
            {
                'title': 'Amazon Seller Central',
                'desc': '访问官方卖家中心获取最新资讯',
                'link': 'https://sellercentral.amazon.com',
                'source': '官方',
                'date': datetime.now().strftime('%Y-%m-%d'),
                'is_rss': False
            },
            {
                'title': 'Amazon Press Room',
                'desc': '查看Amazon官方新闻和公告',
                'link': 'https://press.aboutamazon.com',
                'source': '新闻',
                'date': datetime.now().strftime('%Y-%m-%d'),
                'is_rss': False
            }
        ], False

# 显示实时资讯模块
with st.expander("📰 Amazon实时资讯", expanded=True):
    # 获取资讯数据
    with st.spinner("📡 正在获取Amazon资讯..."):
        news_list, rss_success = get_real_amazon_news()
    
    # 显示状态信息
    if rss_success:
        rss_count = sum(1 for news in news_list if news.get('is_rss', False))
        official_count = len(news_list) - rss_count
        st.success(f"✅ 获取成功：{rss_count} 条RSS实时资讯 + {official_count} 条官方资源")
        st.caption("🔄 每30分钟自动更新 | 📡 RSS功能正常 | 🔗 点击查看详情")
    else:
        st.info("📡 RSS源暂时无法访问，显示Amazon官方资源链接")
        st.caption("🔗 官方资源始终可用 | 💡 这些链接包含最新的政策和功能更新")
    
    if not news_list:
        st.warning("⚠️ 暂时无法获取资讯，请稍后刷新页面")
    else:
        # 使用2列布局显示资讯
        col1, col2 = st.columns(2)
        
        for i, news in enumerate(news_list):
            target_col = col1 if i % 2 == 0 else col2
            
            with target_col:
                with st.container(border=True):
                    # 来源标签和类型指示
                    source_colors = {
                        '官方新闻': '🟢',
                        '官方博客': '🟢', 
                        '广告博客': '🟣',
                        '卖家中心': '🔵',
                        '广告中心': '🟣',
                        '品牌注册': '🔴',
                        'FBA中心': '🟠',
                        '官方': '🟢',
                        '新闻': '⚪'
                    }
                    source_icon = source_colors.get(news['source'], '⚪')
                    
                    # 显示类型标识
                    if news.get('is_rss', False):
                        type_badge = "📡 实时"
                    else:
                        type_badge = "🔗 官方"
                    
                    # 标题行
                    st.markdown(f"**{source_icon} {news['source']}** · {type_badge} · {news['date']}")
                    
                    # 资讯标题
                    st.markdown(f"### {news['title']}")
                    
                    # 描述内容
                    st.markdown(news['desc'])
                    
                    # 跳转按钮
                    if news.get('link'):
                        st.link_button(
                            "🔗 查看详情", 
                            news['link'], 
                            use_container_width=True,
                            help=f"跳转到 {news['source']} 查看完整内容"
                        )
                    else:
                        st.button("暂无链接", disabled=True, use_container_width=True)
    
    # 操作按钮
    col_btn1, col_btn2 = st.columns(2)
    
    with col_btn1:
        if st.button("🔄 刷新资讯", use_container_width=True, key="refresh_real_news"):
            st.cache_data.clear()
            st.rerun()
    

    with col_btn2:
        st.link_button(
            "🌐 更多资讯", 
            "https://sellercentral.amazon.com/news",
            use_container_width=True,
            help="访问Amazon Seller Central获取更多官方资讯"
        )

# 添加快速统计
col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)
with col_stat1:
    st.markdown('<div class="stats-card"><h3>10</h3><p>稳定功能</p></div>', unsafe_allow_html=True)
with col_stat2:
    st.markdown('<div class="stats-card"><h3>0</h3><p>测试功能</p></div>', unsafe_allow_html=True)
with col_stat3:
    st.markdown('<div class="stats-card"><h3>2</h3><p>开发中</p></div>', unsafe_allow_html=True)
with col_stat4:
    st.markdown('<div class="stats-card"><h3>🟢</h3><p>系统状态</p></div>', unsafe_allow_html=True)

# --- 5. 功能模块配置 ---
# 重新整理功能模块，突出核心功能
core_tools = {
    "copywriter": {
        "path": "pages/1_✍️_Listing_Copywriter.py", 
        "icon": "✍️", 
        "title": "智能文案", 
        "desc": "SEO文案生成、五点描述优化",
        "status": "stable"
    },
    "visual": {
        "path": "pages/6_🎨_Visual_Studio.py", 
        "icon": "🎨", 
        "title": "AI绘图", 
        "desc": "产品海报、场景图生成",
        "status": "stable"
    },
    "smart_edit": {
        "path": "pages/2_🖼️_Smart_Edit.py", 
        "icon": "🖼️", 
        "title": "图片编辑", 
        "desc": "智能修图、场景替换",
        "status": "stable"
    },
    "batch": {
        "path": "pages/7_🔄_Batch_Variant.py", 
        "icon": "🔄", 
        "title": "批量变体", 
        "desc": "快速生成产品变体图",
        "status": "stable"
    }
}

utility_tools = {
    "upscale": {
        "path": "pages/9_🔍_HD_Upscale.py", 
        "icon": "🔍", 
        "title": "高清放大", 
        "desc": "图片无损放大增强",
        "status": "stable"
    },
    "resizer": {
        "path": "pages/10_📐_Smart_Resizer.py", 
        "icon": "📐", 
        "title": "尺寸调整", 
        "desc": "智能画幅适配",
        "status": "stable"
    },
    "fba": {
        "path": "pages/11_🎰_fba_app.py", 
        "icon": "📦", 
        "title": "FBA计算器", 
        "desc": "费用计算与优化建议",
        "status": "stable"
    },
    "canvas": {
        "path": "pages/3_🖌️_Magic_Canvas.py", 
        "icon": "🖌️", 
        "title": "局部重绘", 
        "desc": "局部重绘与智能扩展",
        "status": "stable"
    },
    "chat": {
        "path": "pages/8_💬_AI_Studio.py", 
        "icon": "💬", 
        "title": "AI助手", 
        "desc": "智能问答对话",
        "status": "stable"
    }
}

# 辅助函数：渲染状态徽章
def get_status_badge(status):
    if status == "stable":
        return '<span class="status-badge badge-stable">稳定</span>'
    elif status == "beta":
        return '<span class="status-badge badge-beta">测试</span>'
    else:
        return '<span class="status-badge badge-dev">开发中</span>'

# --- 6. 核心功能区 ---
st.markdown('<div class="category-title">🎯 核心功能</div>', unsafe_allow_html=True)

# 使用2x2网格布局展示核心功能
col1, col2 = st.columns(2, gap="large")

with col1:
    # 智能文案
    t = core_tools["copywriter"]
    st.markdown(f'''
    <div class="feature-card">
        <h3>{t['icon']} {t['title']} {get_status_badge(t['status'])}</h3>
        <p style="color: #666; margin: 12px 0;">{t['desc']}</p>
    </div>
    ''', unsafe_allow_html=True)
    st.page_link(t['path'], label="开始创作文案", icon="✍️", use_container_width=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # 图片编辑
    t = core_tools["smart_edit"]
    st.markdown(f'''
    <div class="feature-card">
        <h3>{t['icon']} {t['title']} {get_status_badge(t['status'])}</h3>
        <p style="color: #666; margin: 12px 0;">{t['desc']}</p>
    </div>
    ''', unsafe_allow_html=True)
    st.page_link(t['path'], label="开始编辑图片", icon="🖼️", use_container_width=True)

with col2:
    # AI绘图
    t = core_tools["visual"]
    st.markdown(f'''
    <div class="feature-card">
        <h3>{t['icon']} {t['title']} {get_status_badge(t['status'])}</h3>
        <p style="color: #666; margin: 12px 0;">{t['desc']}</p>
    </div>
    ''', unsafe_allow_html=True)
    st.page_link(t['path'], label="开始AI绘图", icon="🎨", use_container_width=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # 批量变体
    t = core_tools["batch"]
    st.markdown(f'''
    <div class="feature-card">
        <h3>{t['icon']} {t['title']} {get_status_badge(t['status'])}</h3>
        <p style="color: #666; margin: 12px 0;">{t['desc']}</p>
    </div>
    ''', unsafe_allow_html=True)
    st.page_link(t['path'], label="批量生成变体", icon="🔄", use_container_width=True)

# --- 7. 实用工具区 ---
st.markdown('<div class="category-title">🛠️ 实用工具</div>', unsafe_allow_html=True)

# 使用5列网格展示工具
col1, col2, col3, col4, col5 = st.columns(5, gap="medium")

with col1:
    t = utility_tools["upscale"]
    st.markdown(f'''
    <div class="feature-card">
        <h4>{t['icon']} {t['title']}</h4>
        <p style="color: #666; font-size: 0.9rem; margin: 8px 0;">{t['desc']}</p>
        {get_status_badge(t['status'])}
    </div>
    ''', unsafe_allow_html=True)
    st.page_link(t['path'], label="开始使用", use_container_width=True)

with col2:
    t = utility_tools["resizer"]
    st.markdown(f'''
    <div class="feature-card">
        <h4>{t['icon']} {t['title']}</h4>
        <p style="color: #666; font-size: 0.9rem; margin: 8px 0;">{t['desc']}</p>
        {get_status_badge(t['status'])}
    </div>
    ''', unsafe_allow_html=True)
    st.page_link(t['path'], label="开始使用", use_container_width=True)

with col3:
    t = utility_tools["fba"]
    st.markdown(f'''
    <div class="feature-card">
        <h4>{t['icon']} {t['title']}</h4>
        <p style="color: #666; font-size: 0.9rem; margin: 8px 0;">{t['desc']}</p>
        {get_status_badge(t['status'])}
    </div>
    ''', unsafe_allow_html=True)
    st.page_link(t['path'], label="开始使用", use_container_width=True)

with col4:
    t = utility_tools["canvas"]
    st.markdown(f'''
    <div class="feature-card">
        <h4>{t['icon']} {t['title']}</h4>
        <p style="color: #666; font-size: 0.9rem; margin: 8px 0;">{t['desc']}</p>
        {get_status_badge(t['status'])}
    </div>
    ''', unsafe_allow_html=True)
    st.page_link(t['path'], label="开始使用", use_container_width=True)

with col5:
    t = utility_tools["chat"]
    st.markdown(f'''
    <div class="feature-card">
        <h4>{t['icon']} {t['title']}</h4>
        <p style="color: #666; font-size: 0.9rem; margin: 8px 0;">{t['desc']}</p>
        {get_status_badge(t['status'])}
    </div>
    ''', unsafe_allow_html=True)
    st.page_link(t['path'], label="开始使用", use_container_width=True)

# --- 8. 开发中功能 ---
st.markdown('<div class="category-title">🚧 开发中功能</div>', unsafe_allow_html=True)

col1, col2 = st.columns(2, gap="large")

with col1:
    st.markdown(f'''
    <div class="feature-card" style="opacity: 0.6;">
        <h4>🎬 Video Studio</h4>
        <p style="color: #666; font-size: 0.9rem; margin: 8px 0;">电商短视频生成 (开发中)</p>
        <span class="status-badge badge-dev">开发中</span>
    </div>
    ''', unsafe_allow_html=True)
    st.button("敬请期待", disabled=True, use_container_width=True, key="video_btn")

with col2:
    st.markdown(f'''
    <div class="feature-card" style="opacity: 0.5;">
        <h4>🧩 A+ Studio</h4>
        <p style="color: #666; font-size: 0.9rem; margin: 8px 0;">A+ 页面创意工场 (规划中)</p>
        <span class="status-badge badge-dev">规划中</span>
    </div>
    ''', unsafe_allow_html=True)
    st.button("待开发", disabled=True, use_container_width=True, key="aplus_btn")

# --- 9. 底部信息 ---
st.markdown("<br><br>", unsafe_allow_html=True)

# 添加使用提示
with st.expander("💡 使用提示", expanded=False):
    col_tip1, col_tip2 = st.columns(2)
    with col_tip1:
        st.markdown("""
        **🚀 快速上手：**
        1. 从智能文案开始，生成产品描述
        2. 使用AI绘图创建产品海报
        3. 通过图片编辑优化视觉效果
        4. 利用批量变体快速扩展SKU
        """)
    with col_tip2:
        st.markdown("""
        **🛠️ 实用工具：**
        - 高清放大：提升图片质量
        - 尺寸调整：适配不同平台
        - FBA计算器：优化成本结构
        - AI助手：获取运营建议
        """)

st.divider()
col_footer1, col_footer2, col_footer3 = st.columns([1, 2, 1])
with col_footer2:
    st.markdown(
        '<p style="text-align: center; color: #666; font-size: 0.9rem;">© 2025 Amazon AI Hub | Powered by Gemini & Flux | Build 2.1.0</p>', 
        unsafe_allow_html=True
    )
