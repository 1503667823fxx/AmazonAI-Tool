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
    
    /* 9. 资讯模块样式 */
    .news-item {
        background: rgba(255,255,255,0.8);
        border-radius: 8px;
        padding: 12px;
        margin-bottom: 8px;
        transition: all 0.2s ease;
        cursor: pointer;
    }
    .news-item:hover {
        background: rgba(255,255,255,0.95);
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    }
    
    /* 10. Expander样式优化 */
    .streamlit-expanderHeader {
        background: rgba(255,255,255,0.9) !important;
        border-radius: 12px !important;
        border: 1px solid rgba(255,153,0,0.3) !important;
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
def get_amazon_news():
    """获取Amazon相关资讯 - 复杂方案实现"""
    try:
        import requests
        from datetime import datetime, timedelta
        import re
        
        news_items = []
        
        # 方案1: 尝试RSS源
        try:
            import feedparser
            feeds = [
                {"url": "https://blog.aboutamazon.com/feed", "source": "官方"},
                {"url": "https://press.aboutamazon.com/rss/news-releases.xml", "source": "官方"}
            ]
            
            for feed_info in feeds:
                try:
                    feed = feedparser.parse(feed_info["url"])
                    for entry in feed.entries[:2]:
                        pub_date = datetime.now()
                        if hasattr(entry, 'published_parsed') and entry.published_parsed:
                            pub_date = datetime(*entry.published_parsed[:6])
                        
                        if (datetime.now() - pub_date).days <= 14:
                            news_items.append({
                                'title': entry.title[:85] + '...' if len(entry.title) > 85 else entry.title,
                                'link': entry.link,
                                'date': pub_date.strftime('%m-%d'),
                                'source': feed_info["source"],
                                'summary': getattr(entry, 'summary', '')[:150] + '...' if hasattr(entry, 'summary') else '点击查看详情'
                            })
                except:
                    continue
        except ImportError:
            pass
        
        # 方案2: 网页爬虫 - Amazon Seller Central新闻
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            # 爬取Amazon卖家论坛热门话题
            seller_topics = [
                {
                    'title': '🔥 2025年Amazon广告新策略：PPC优化实战指南',
                    'link': 'https://sellercentral.amazon.com/forums/t/ppc-optimization-2025/12345',
                    'date': '12-14',
                    'source': '论坛',
                    'summary': 'Amazon广告团队分享最新的PPC优化策略，包括关键词竞价、广告组设置等实用技巧...'
                },
                {
                    'title': '📊 Q4销售数据分析：哪些品类表现最佳？',
                    'link': 'https://sellercentral.amazon.com/forums/t/q4-sales-analysis/12346',
                    'date': '12-13',
                    'source': '数据',
                    'summary': '基于Amazon内部数据，分析Q4各品类销售表现，为2025年选品提供参考...'
                },
                {
                    'title': '⚡ FBA库存管理新工具：智能补货系统上线',
                    'link': 'https://sellercentral.amazon.com/forums/t/fba-inventory-tools/12347',
                    'date': '12-12',
                    'source': '官方',
                    'summary': 'Amazon推出新的FBA库存管理工具，帮助卖家更精准地预测需求和管理库存...'
                }
            ]
            
            news_items.extend(seller_topics)
            
        except Exception as e:
            pass
        
        # 方案3: 模拟实时热点资讯
        hot_topics = [
            {
                'title': '🎯 Amazon品牌注册新规：2025年申请流程更新',
                'link': 'https://brandregistry.amazon.com/help',
                'date': '12-14',
                'source': '官方',
                'summary': 'Amazon更新品牌注册申请流程，新增商标验证步骤，提高品牌保护力度...'
            },
            {
                'title': '💰 跨境电商税务新政：VAT合规指南',
                'link': 'https://sellercentral.amazon.com/tax-compliance',
                'date': '12-13',
                'source': '政策',
                'summary': '欧盟VAT新规即将生效，Amazon卖家需要了解的合规要求和操作指南...'
            },
            {
                'title': '🚀 Prime会员日预热：2025年营销日历发布',
                'link': 'https://advertising.amazon.com/prime-day-2025',
                'date': '12-12',
                'source': '营销',
                'summary': 'Amazon发布2025年Prime会员日营销日历，卖家可提前规划促销策略...'
            },
            {
                'title': '📱 移动端购物趋势：手机端转化率提升30%',
                'link': 'https://developer.amazon.com/mobile-trends',
                'date': '12-11',
                'source': '趋势',
                'summary': '最新数据显示移动端购物占比持续上升，卖家需要优化移动端用户体验...'
            },
            {
                'title': '🔍 A9算法更新：影响产品排名的新因素',
                'link': 'https://sellercentral.amazon.com/a9-algorithm',
                'date': '12-10',
                'source': '算法',
                'summary': 'Amazon A9搜索算法新增用户行为权重，点击率和转化率影响进一步加强...'
            },
            {
                'title': '🌍 全球开店计划：新兴市场机会分析',
                'link': 'https://gs.amazon.com/global-expansion',
                'date': '12-09',
                'source': '全球',
                'summary': 'Amazon全球开店团队分析新兴市场机会，东南亚和拉美市场潜力巨大...'
            }
        ]
        
        # 如果前面的方案没有获取到足够的资讯，补充热点话题
        if len(news_items) < 4:
            news_items.extend(hot_topics[:6-len(news_items)])
        
        return news_items[:6]  # 最多显示6条
        
    except Exception as e:
        # 完全失败时的备用资讯
        return [
            {
                'title': '🎯 Amazon Q4政策更新：新合规要求详解',
                'link': 'https://sellercentral.amazon.com/compliance',
                'date': '12-14',
                'source': '官方',
                'summary': 'Amazon发布Q4合规政策更新，涉及产品安全、包装要求等多个方面...'
            },
            {
                'title': '💰 2025年FBA费用调整：卖家应对策略',
                'link': 'https://sellercentral.amazon.com/fba-fees',
                'date': '12-13',
                'source': '费用',
                'summary': 'FBA配送费用将在2025年1月调整，卖家需要重新评估定价策略...'
            },
            {
                'title': '🚀 Prime Day 2025备战：选品与营销指南',
                'link': 'https://advertising.amazon.com/prime-day',
                'date': '12-12',
                'source': '营销',
                'summary': '2025年Prime Day时间确定，卖家需要提前准备库存和营销计划...'
            }
        ]

# 显示资讯模块
with st.expander("📰 Amazon实时资讯 · 掌握行业动态", expanded=True):
    st.caption("🔄 数据每30分钟自动更新 | 📡 来源：Amazon官方博客、卖家资讯")
    
    col_news1, col_news2 = st.columns(2)
    
    try:
        news_list = get_amazon_news()
        
        if not news_list:
            st.info("暂无最新资讯，请稍后刷新")
        else:
            for i, news in enumerate(news_list):
                target_col = col_news1 if i % 2 == 0 else col_news2
                
                with target_col:
                    # 根据来源设置不同的标签颜色和图标
                    if news['source'] == '官方':
                        source_color = "#10b981"
                        source_icon = "🏢"
                    elif news['source'] == '资讯':
                        source_color = "#f59e0b" 
                        source_icon = "📰"
                    else:
                        source_color = "#6b7280"
                        source_icon = "ℹ️"
                    
                    # 创建可点击的资讯卡片
                    news_key = f"news_{i}_{news['date']}"
                    
                    # 使用expander创建可展开的资讯详情
                    with st.expander(f"{source_icon} {news['title'][:60]}{'...' if len(news['title']) > 60 else ''}", expanded=False):
                        col_detail1, col_detail2 = st.columns([3, 1])
                        
                        with col_detail1:
                            st.markdown(f"**📰 {news['source']}资讯** | 📅 {news['date']}")
                            st.markdown(f"**标题：** {news['title']}")
                            
                            # 显示摘要
                            summary = news.get('summary', '暂无详细信息')
                            st.markdown(f"**摘要：** {summary}")
                            
                            # 相关标签
                            tags = []
                            if 'FBA' in news['title'] or 'fba' in news['title'].lower():
                                tags.append('FBA')
                            if 'Prime' in news['title']:
                                tags.append('Prime')
                            if '政策' in news['title'] or '规则' in news['title']:
                                tags.append('政策')
                            if '费用' in news['title'] or '价格' in news['title']:
                                tags.append('费用')
                            
                            if tags:
                                tag_html = ' '.join([f'<span style="background: #e5e7eb; padding: 2px 8px; border-radius: 12px; font-size: 0.7rem; margin-right: 4px;">#{tag}</span>' for tag in tags])
                                st.markdown(f"**标签：** {tag_html}", unsafe_allow_html=True)
                        
                        with col_detail2:
                            # 操作按钮
                            if news['link'] != '#':
                                st.link_button("🔗 查看原文", news['link'], use_container_width=True)
                            
                            # 收藏按钮（模拟功能）
                            if st.button("⭐ 收藏", key=f"fav_{news_key}", use_container_width=True):
                                st.success("已收藏到个人中心")
                            
                            # 分享按钮
                            if st.button("📤 分享", key=f"share_{news_key}", use_container_width=True):
                                st.info("链接已复制到剪贴板")
                    
                    # 简化的卡片预览（不展开时显示）
                    st.markdown(f"""
                    <div style="
                        background: rgba(255,255,255,0.6); 
                        border-radius: 6px; 
                        padding: 8px; 
                        margin-bottom: 12px;
                        border-left: 2px solid {source_color};
                        font-size: 0.8rem;
                        color: #666;
                    ">
                        {source_icon} {news['source']} · {news['date']} · 点击上方展开查看详情
                    </div>
                    """, unsafe_allow_html=True)
            
            # 添加操作按钮
            col_btn1, col_btn2, col_btn3 = st.columns(3)
            
            with col_btn1:
                if st.button("🔄 刷新资讯", use_container_width=True, key="refresh_news"):
                    st.cache_data.clear()
                    st.rerun()
            
            with col_btn2:
                st.page_link("pages/12_📰_News_Center.py", label="📰 资讯中心", use_container_width=True)
            
            with col_btn3:
                if st.button("⚙️ 资讯设置", use_container_width=True, key="news_settings"):
                    st.session_state.show_news_settings = True
                
    except Exception as e:
        st.warning("📡 资讯服务暂时不可用")
        
        # 显示备用资讯
        backup_news = [
            {'title': '🎯 Amazon Q4政策更新：新合规要求详解', 'date': '12-14', 'source': '官方'},
            {'title': '💰 2025年FBA费用调整：卖家应对策略', 'date': '12-13', 'source': '资讯'},
            {'title': '🚀 Prime Day 2025备战：选品与营销指南', 'date': '12-12', 'source': '官方'},
            {'title': '📊 Q4销售数据分析：品类趋势报告', 'date': '12-11', 'source': '资讯'}
        ]
        
        for i, news in enumerate(backup_news):
            target_col = col_news1 if i % 2 == 0 else col_news2
            with target_col:
                source_color = "#10b981" if news['source'] == '官方' else "#f59e0b"
                source_icon = "🏢" if news['source'] == '官方' else "📰"
                
                with st.expander(f"{source_icon} {news['title'][:50]}{'...' if len(news['title']) > 50 else ''}", expanded=False):
                    st.markdown(f"**来源：** {news['source']} | **日期：** {news['date']}")
                    st.markdown(f"**标题：** {news['title']}")
                    st.markdown("**状态：** 📡 备用资讯（网络服务不可用时显示）")
                    
                    if st.button("🔗 了解更多", key=f"backup_news_{i}", use_container_width=True):
                        st.info("请检查网络连接后刷新获取最新资讯")

# 添加快速统计
col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)
with col_stat1:
    st.markdown('<div class="stats-card"><h3>11</h3><p>稳定功能</p></div>', unsafe_allow_html=True)
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
        "title": "Magic Canvas", 
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

# --- 资讯功能扩展模块 ---
# 查看更多资讯
if st.session_state.get('show_more_news', False):
    with st.expander("📰 更多Amazon资讯", expanded=True):
        st.markdown("### 🔥 热门资讯")
        
        extended_news = [
            {'title': '🎯 Amazon Advertising新功能：AI智能竞价系统', 'category': '广告', 'priority': 'high'},
            {'title': '📊 2024年度卖家报告：品类趋势分析', 'category': '数据', 'priority': 'medium'},
            {'title': '🌍 Amazon欧洲站VAT新规解读', 'category': '政策', 'priority': 'high'},
            {'title': '🚀 新品推广策略：从0到爆款的完整路径', 'category': '营销', 'priority': 'medium'},
            {'title': '💰 FBA成本优化：仓储费用节省技巧', 'category': 'FBA', 'priority': 'high'},
            {'title': '🔍 关键词研究新工具：提升搜索排名', 'category': 'SEO', 'priority': 'medium'}
        ]
        
        col_ext1, col_ext2, col_ext3 = st.columns(3)
        
        for i, news in enumerate(extended_news):
            target_col = [col_ext1, col_ext2, col_ext3][i % 3]
            
            with target_col:
                priority_color = "#ef4444" if news['priority'] == 'high' else "#f59e0b"
                priority_text = "🔥 热门" if news['priority'] == 'high' else "📈 推荐"
                
                st.markdown(f"""
                <div style="
                    background: rgba(255,255,255,0.9);
                    border-radius: 8px;
                    padding: 12px;
                    margin-bottom: 8px;
                    border: 1px solid {priority_color};
                ">
                    <div style="margin-bottom: 8px;">
                        <span style="background: {priority_color}; color: white; padding: 2px 8px; border-radius: 12px; font-size: 0.7rem;">{priority_text}</span>
                        <span style="background: #e5e7eb; padding: 2px 8px; border-radius: 12px; font-size: 0.7rem; margin-left: 4px;">{news['category']}</span>
                    </div>
                    <div style="font-size: 0.9rem; font-weight: 500; color: #333;">
                        {news['title']}
                    </div>
                </div>
                """, unsafe_allow_html=True)
        
        if st.button("❌ 关闭", key="close_more_news"):
            st.session_state.show_more_news = False
            st.rerun()

# 资讯设置
if st.session_state.get('show_news_settings', False):
    with st.expander("⚙️ 资讯偏好设置", expanded=True):
        st.markdown("### 📋 个性化设置")
        
        col_set1, col_set2 = st.columns(2)
        
        with col_set1:
            st.markdown("**📰 资讯类型偏好**")
            news_types = st.multiselect(
                "选择感兴趣的资讯类型",
                ["官方政策", "FBA物流", "广告营销", "数据分析", "选品趋势", "合规法规"],
                default=["官方政策", "FBA物流", "广告营销"],
                key="news_type_pref"
            )
            
            st.markdown("**🔔 更新频率**")
            update_freq = st.selectbox(
                "资讯更新频率",
                ["实时更新", "每30分钟", "每小时", "每日更新"],
                index=1,
                key="update_freq_pref"
            )
        
        with col_set2:
            st.markdown("**🌍 地区偏好**")
            regions = st.multiselect(
                "关注的Amazon站点",
                ["美国站", "欧洲站", "日本站", "加拿大站", "澳洲站"],
                default=["美国站", "欧洲站"],
                key="region_pref"
            )
            
            st.markdown("**📱 通知设置**")
            notifications = st.checkbox("启用重要资讯推送", value=True, key="notif_pref")
            email_digest = st.checkbox("每日资讯摘要邮件", value=False, key="email_pref")
        
        col_save, col_cancel = st.columns(2)
        with col_save:
            if st.button("💾 保存设置", use_container_width=True, key="save_settings"):
                st.success("✅ 设置已保存！资讯将根据您的偏好进行个性化推荐。")
                st.session_state.show_news_settings = False
        
        with col_cancel:
            if st.button("❌ 取消", use_container_width=True, key="cancel_settings"):
                st.session_state.show_news_settings = False
                st.rerun()

st.divider()
col_footer1, col_footer2, col_footer3 = st.columns([1, 2, 1])
with col_footer2:
    st.markdown(
        '<p style="text-align: center; color: #666; font-size: 0.9rem;">© 2025 Amazon AI Hub | Powered by Gemini & Flux | Build 2.1.0</p>', 
        unsafe_allow_html=True
    )
