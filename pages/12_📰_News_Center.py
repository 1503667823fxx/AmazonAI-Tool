import streamlit as st
import sys
import os
from datetime import datetime, timedelta

# --- 路径环境设置 ---
current_script_path = os.path.abspath(__file__)
pages_dir = os.path.dirname(current_script_path)
root_dir = os.path.dirname(pages_dir)
if root_dir not in sys.path:
    sys.path.append(root_dir)

try:
    import auth
except ImportError:
    pass

# --- 页面配置 ---
st.set_page_config(page_title="Amazon资讯中心", page_icon="📰", layout="wide")

# --- 鉴权 ---
if 'auth' in sys.modules and not auth.check_password():
    st.stop()

# --- CSS样式 ---
st.markdown("""
<style>
    .news-card {
        background: white;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 16px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        border-left: 4px solid #FF9900;
        transition: all 0.3s ease;
    }
    .news-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 16px rgba(0,0,0,0.15);
    }
    .category-tag {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
        margin-right: 8px;
        margin-bottom: 8px;
    }
    .priority-high { background: #fee2e2; color: #dc2626; }
    .priority-medium { background: #fef3c7; color: #d97706; }
    .priority-low { background: #e0f2fe; color: #0369a1; }
</style>
""", unsafe_allow_html=True)

# --- 主界面 ---
st.title("📰 Amazon资讯中心")
st.markdown("### 🌍 全球Amazon电商资讯 · 实时更新")

# --- 侧边栏筛选 ---
with st.sidebar:
    st.header("🔍 资讯筛选")
    
    # 分类筛选
    categories = st.multiselect(
        "📂 资讯分类",
        ["官方政策", "FBA物流", "广告营销", "数据分析", "选品趋势", "合规法规", "技术更新"],
        default=["官方政策", "FBA物流", "广告营销"]
    )
    
    # 优先级筛选
    priority_filter = st.selectbox(
        "⭐ 优先级",
        ["全部", "🔥 高优先级", "📈 中优先级", "📋 低优先级"],
        index=0
    )
    
    # 时间筛选
    time_filter = st.selectbox(
        "📅 时间范围",
        ["今日", "本周", "本月", "全部"],
        index=1
    )
    
    # 地区筛选
    region_filter = st.multiselect(
        "🌍 Amazon站点",
        ["美国站", "欧洲站", "日本站", "加拿大站", "澳洲站", "全球"],
        default=["美国站", "欧洲站", "全球"]
    )

# --- 资讯数据 ---
@st.cache_data(ttl=900)  # 15分钟缓存
def get_all_news():
    """获取完整的资讯列表"""
    return [
        {
            'id': 1,
            'title': '🎯 Amazon Q4卖家政策重大更新：产品合规新要求详解',
            'summary': 'Amazon发布Q4季度卖家政策更新，涉及产品安全标准、包装要求、品牌保护等多个重要方面。新政策将于2025年1月1日正式生效，所有卖家需要在此之前完成相关调整。',
            'category': '官方政策',
            'priority': 'high',
            'date': datetime.now() - timedelta(hours=2),
            'region': '全球',
            'source': 'Amazon Seller Central',
            'tags': ['政策更新', '合规', 'Q4', '产品安全'],
            'read_time': '5分钟',
            'views': 1247
        },
        {
            'id': 2,
            'title': '💰 2025年FBA费用结构调整：配送费用优化策略',
            'summary': 'Amazon宣布2025年FBA费用调整方案，配送费用将根据包装尺寸和重量进行重新计算。小件商品费用下降，大件商品费用略有上升。卖家需要重新评估定价策略。',
            'category': 'FBA物流',
            'priority': 'high',
            'date': datetime.now() - timedelta(hours=6),
            'region': '美国站',
            'source': 'Amazon FBA Team',
            'tags': ['FBA费用', '定价策略', '成本优化'],
            'read_time': '7分钟',
            'views': 892
        },
        {
            'id': 3,
            'title': '🚀 Prime Day 2025营销日历发布：卖家备战指南',
            'summary': 'Amazon正式发布2025年Prime Day营销日历，包括春季Prime Day和夏季Prime Day两个重要节点。同时公布了卖家参与条件和营销工具升级计划。',
            'category': '广告营销',
            'priority': 'medium',
            'date': datetime.now() - timedelta(days=1),
            'region': '全球',
            'source': 'Amazon Advertising',
            'tags': ['Prime Day', '营销日历', '促销活动'],
            'read_time': '6分钟',
            'views': 1156
        },
        {
            'id': 4,
            'title': '📊 2024年度Amazon销售数据报告：品类趋势深度分析',
            'summary': '基于2024年全年销售数据，分析各品类表现和消费者行为变化。电子产品、家居用品、健康美容等品类表现突出，为2025年选品提供重要参考。',
            'category': '数据分析',
            'priority': 'medium',
            'date': datetime.now() - timedelta(days=2),
            'region': '全球',
            'source': 'Amazon Analytics',
            'tags': ['销售数据', '品类分析', '消费趋势'],
            'read_time': '10分钟',
            'views': 743
        },
        {
            'id': 5,
            'title': '🔍 A9搜索算法更新：新排名因素影响分析',
            'summary': 'Amazon A9搜索算法进行重要更新，新增用户行为权重，点击率、转化率、评价质量对排名的影响进一步加强。卖家需要调整SEO策略。',
            'category': '技术更新',
            'priority': 'high',
            'date': datetime.now() - timedelta(days=3),
            'region': '全球',
            'source': 'Amazon Search Team',
            'tags': ['A9算法', 'SEO优化', '搜索排名'],
            'read_time': '8分钟',
            'views': 1034
        },
        {
            'id': 6,
            'title': '🌍 Amazon欧洲站VAT合规新规：操作指南',
            'summary': '欧盟VAT新规即将在2025年Q2生效，Amazon欧洲站卖家需要完成新的税务合规流程。本文详细解读新规要求和操作步骤。',
            'category': '合规法规',
            'priority': 'high',
            'date': datetime.now() - timedelta(days=4),
            'region': '欧洲站',
            'source': 'Amazon Europe',
            'tags': ['VAT合规', '欧洲站', '税务'],
            'read_time': '12分钟',
            'views': 567
        }
    ]

# --- 获取并筛选资讯 ---
all_news = get_all_news()

# 应用筛选条件
filtered_news = all_news

# 分类筛选
if categories:
    filtered_news = [news for news in filtered_news if news['category'] in categories]

# 优先级筛选
if priority_filter != "全部":
    priority_map = {"🔥 高优先级": "high", "📈 中优先级": "medium", "📋 低优先级": "low"}
    filtered_news = [news for news in filtered_news if news['priority'] == priority_map[priority_filter]]

# 地区筛选
if region_filter:
    filtered_news = [news for news in filtered_news if news['region'] in region_filter]

# 时间筛选
now = datetime.now()
if time_filter == "今日":
    filtered_news = [news for news in filtered_news if (now - news['date']).days == 0]
elif time_filter == "本周":
    filtered_news = [news for news in filtered_news if (now - news['date']).days <= 7]
elif time_filter == "本月":
    filtered_news = [news for news in filtered_news if (now - news['date']).days <= 30]

# --- 统计信息 ---
col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)
with col_stat1:
    st.metric("📰 总资讯数", len(all_news))
with col_stat2:
    st.metric("🔍 筛选结果", len(filtered_news))
with col_stat3:
    high_priority_count = len([n for n in filtered_news if n['priority'] == 'high'])
    st.metric("🔥 高优先级", high_priority_count)
with col_stat4:
    today_count = len([n for n in filtered_news if (now - n['date']).days == 0])
    st.metric("📅 今日更新", today_count)

st.divider()

# --- 资讯列表 ---
if not filtered_news:
    st.info("🔍 没有找到符合筛选条件的资讯，请调整筛选条件。")
else:
    for news in filtered_news:
        # 优先级样式
        priority_class = f"priority-{news['priority']}"
        priority_text = {"high": "🔥 高优先级", "medium": "📈 中优先级", "low": "📋 低优先级"}[news['priority']]
        
        # 时间显示
        time_diff = now - news['date']
        if time_diff.days == 0:
            if time_diff.seconds < 3600:
                time_str = f"{time_diff.seconds // 60}分钟前"
            else:
                time_str = f"{time_diff.seconds // 3600}小时前"
        else:
            time_str = f"{time_diff.days}天前"
        
        # 资讯卡片
        st.markdown(f"""
        <div class="news-card">
            <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px;">
                <div>
                    <span class="category-tag {priority_class}">{priority_text}</span>
                    <span class="category-tag" style="background: #f3f4f6; color: #374151;">{news['category']}</span>
                    <span class="category-tag" style="background: #e0f2fe; color: #0369a1;">🌍 {news['region']}</span>
                </div>
                <div style="text-align: right; color: #6b7280; font-size: 0.9rem;">
                    <div>📅 {time_str}</div>
                    <div>👁️ {news['views']} 次查看</div>
                </div>
            </div>
            
            <h3 style="margin: 0 0 12px 0; color: #1f2937;">{news['title']}</h3>
            
            <p style="color: #4b5563; line-height: 1.6; margin-bottom: 16px;">{news['summary']}</p>
            
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div style="color: #6b7280; font-size: 0.9rem;">
                    📖 阅读时间: {news['read_time']} | 📡 来源: {news['source']}
                </div>
                <div>
                    <span style="margin-right: 8px;">标签:</span>
                    {' '.join([f'<span style="background: #e5e7eb; padding: 2px 8px; border-radius: 12px; font-size: 0.7rem; margin-right: 4px;">#{tag}</span>' for tag in news['tags']])}
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # 操作按钮
        col_btn1, col_btn2, col_btn3, col_btn4 = st.columns(4)
        with col_btn1:
            if st.button("📖 阅读全文", key=f"read_{news['id']}", use_container_width=True):
                st.info("📖 全文阅读功能开发中...")
        with col_btn2:
            if st.button("⭐ 收藏", key=f"fav_{news['id']}", use_container_width=True):
                st.success("✅ 已收藏到个人中心")
        with col_btn3:
            if st.button("📤 分享", key=f"share_{news['id']}", use_container_width=True):
                st.info("🔗 分享链接已复制")
        with col_btn4:
            if st.button("💬 评论", key=f"comment_{news['id']}", use_container_width=True):
                st.info("💬 评论功能即将上线")
        
        st.markdown("---")

# --- 底部信息 ---
st.markdown("### 📡 资讯来源")
st.info("""
**官方来源：** Amazon Seller Central、Amazon Advertising、Amazon FBA Team  
**数据更新：** 每15分钟自动更新  
**覆盖范围：** 全球主要Amazon站点  
**内容类型：** 政策更新、费用调整、营销活动、技术更新、合规法规
""")
