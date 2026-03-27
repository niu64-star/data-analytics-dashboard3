import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import datetime

# --- 页面配置 ---
st.set_page_config(
    page_title="SalesMind Executive Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 辅助函数：加载数据 (使用缓存以提高性能) ---
@st.cache_data
def load_data():
    """加载所有CSV文件并执行初步的数据清洗和合并"""
    # 加载主要数据表
    sales = pd.read_csv('SalesMind_Sales_Transactions_2026.csv')
    stores = pd.read_csv('SalesMind_Stores_Master_2026.csv')
    products = pd.read_csv('SalesMind_Products_Master_2026.csv')
    calendar = pd.read_csv('SalesMind_Calendar_Dimension_2026.csv')
    customers = pd.read_csv('SalesMind_Customer_Segments_2026.csv')
    external = pd.read_csv('SalesMind_External_Factors_2026.csv')
    inventory = pd.read_csv('SalesMind_Inventory_Supply_2026.csv')
    campaigns = pd.read_csv('SalesMind_Marketing_Campaigns_2026.csv')
    suspicious = pd.read_csv('suspicious_transactions.csv')

    # 转换日期列
    sales['date'] = pd.to_datetime(sales['date'])
    calendar['date'] = pd.to_datetime(calendar['date'])
    external['date'] = pd.to_datetime(external['date'])
    suspicious['InvoiceDate'] = pd.to_datetime(suspicious['InvoiceDate'])
    suspicious['DueDate'] = pd.to_datetime(suspicious['DueDate'])
    if 'PaidDate' in suspicious.columns:
        suspicious['PaidDate'] = pd.to_datetime(suspicious['PaidDate'], errors='coerce')

    # --- 数据合并 ---
    # 1. 将销售数据与门店、产品、日历维度连接
    df = sales.merge(stores, on='store_id', how='left')
    df = df.merge(products, on='product_id', how='left')
    df = df.merge(calendar, on='date', how='left')
    df = df.merge(customers, on='customer_segment', how='left')
    
    # 2. 合并外部因素 (按日期)
    df = df.merge(external, on='date', how='left')
    
    # 3. 合并库存数据 (按门店和产品)
    df = df.merge(inventory, on=['store_id', 'product_id'], how='left')
    
    # 4. 为每个交易分配一个营销活动？这里我们简单地按日期和广告渠道聚合营销数据。
    # 注意：营销数据中没有直接关联到交易的字段，所以我们按日期和渠道聚合，然后合并到df。
    campaigns_by_date = campaigns.groupby('date')['marketing_spend'].sum().reset_index()
    campaigns_by_date['date'] = pd.to_datetime(campaigns_by_date['date'])
    df = df.merge(campaigns_by_date, on='date', how='left')
    df['marketing_spend'].fillna(0, inplace=True) # 没有营销活动的日期设为0

    return df, stores, products, calendar, customers, external, inventory, campaigns, suspicious

# --- 加载数据 ---
with st.spinner('Loading data...'):
    df, stores, products, calendar, customers, external, inventory, campaigns, suspicious = load_data()

# --- 侧边栏: 全局筛选器 ---
st.sidebar.image("https://via.placeholder.com/150x50?text=SalesMind", use_column_width=True) # Placeholder for a logo
st.sidebar.title("📊 Dashboard Filters")

# 日期范围选择器
min_date = df['date'].min().date()
max_date = df['date'].max().date()
start_date, end_date = st.sidebar.date_input(
    "Select Date Range",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date
)
# 将date列转换为date对象以便比较
df['date_only'] = df['date'].dt.date
mask = (df['date_only'] >= start_date) & (df['date_only'] <= end_date)
filtered_df = df.loc[mask].copy()

# 其他筛选器
st.sidebar.markdown("---")
stores_list = ['All'] + sorted(filtered_df['store_type'].unique().tolist())
selected_store_type = st.sidebar.selectbox("Select Store Type", stores_list)

customer_list = ['All'] + sorted(filtered_df['customer_segment'].unique().tolist())
selected_customer = st.sidebar.selectbox("Select Customer Segment", customer_list)

product_cat_list = ['All'] + sorted(filtered_df['product_category'].unique().tolist())
selected_product_cat = st.sidebar.selectbox("Select Product Category", product_cat_list)

# 应用筛选器
if selected_store_type != 'All':
    filtered_df = filtered_df[filtered_df['store_type'] == selected_store_type]
if selected_customer != 'All':
    filtered_df = filtered_df[filtered_df['customer_segment'] == selected_customer]
if selected_product_cat != 'All':
    filtered_df = filtered_df[filtered_df['product_category'] == selected_product_cat]


# --- 主面板: KPI 卡片 ---
st.title("📈 SalesMind Executive Dashboard")
st.markdown(f"**Period:** {start_date} to {end_date} | **Store Type:** {selected_store_type} | **Customer:** {selected_customer} | **Product Category:** {selected_product_cat}")
st.markdown("---")

# 计算关键指标
total_net_sales = filtered_df['net_sales'].sum()
total_units_sold = filtered_df['units_sold'].sum()
avg_discount_rate = (filtered_df['total_discount_given'].sum() / filtered_df['total_sales_revenue'].sum()) * 100
avg_return_rate = filtered_df['return_rate'].mean() * 100
gross_profit_margin = (filtered_df['gross_profit'].sum() / filtered_df['net_sales'].sum()) * 100
total_inventory = inventory[inventory['store_id'].isin(filtered_df['store_id'].unique())]['inventory_level'].sum()
stockout_count = inventory[(inventory['stockout_flag'] == 1) & (inventory['store_id'].isin(filtered_df['store_id'].unique()))]['inventory_id'].count()

# 展示KPI
col1, col2, col3, col4, col5, col6 = st.columns(6)
with col1:
    st.metric(label="💰 Net Sales", value=f"${total_net_sales:,.0f}")
with col2:
    st.metric(label="📦 Units Sold", value=f"{total_units_sold:,.0f}")
with col3:
    st.metric(label="💸 Avg. Discount", value=f"{avg_discount_rate:.1f}%")
with col4:
    st.metric(label="🔄 Return Rate", value=f"{avg_return_rate:.1f}%")
with col5:
    st.metric(label="📈 Gross Profit Margin", value=f"{gross_profit_margin:.1f}%")
with col6:
    st.metric(label="⚠️ Stockout Events", value=f"{stockout_count:,}")

st.markdown("---")

# --- 可视化部分 ---
# 创建选项卡，让用户在不同分析之间切换
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Sales Performance", "🏪 Store & Inventory", "🎯 Marketing & Customers", "🌍 External Factors", "🚨 Suspicious Transactions"])

with tab1:
    st.subheader("Sales Performance Analysis")
    col1, col2 = st.columns(2)
    
    with col1:
        # 1. 销售额随时间变化 (按星期几聚合，消除年份和季节影响)
        sales_over_time = filtered_df.groupby('date_only')['net_sales'].sum().reset_index()
        fig_sales = px.line(sales_over_time, x='date_only', y='net_sales', title='Daily Net Sales', labels={'date_only': 'Date', 'net_sales': 'Net Sales ($)'})
        st.plotly_chart(fig_sales, use_container_width=True)
        
    with col2:
        # 2. 按产品类别的销售额饼图
        sales_by_category = filtered_df.groupby('product_category')['net_sales'].sum().reset_index()
        fig_category = px.pie(sales_by_category, values='net_sales', names='product_category', title='Net Sales by Product Category', hole=0.3)
        st.plotly_chart(fig_category, use_container_width=True)
        
    col3, col4 = st.columns(2)
    with col3:
        # 3. 不同客户细分市场的销售额
        sales_by_segment = filtered_df.groupby('customer_segment')['net_sales'].sum().reset_index()
        fig_segment = px.bar(sales_by_segment, x='customer_segment', y='net_sales', title='Net Sales by Customer Segment', color='customer_segment', text_auto='.2s')
        st.plotly_chart(fig_segment, use_container_width=True)
        
    with col4:
        # 4. 退货率 vs 满意度 (散点图)
        segment_metrics = filtered_df.groupby('customer_segment')[['return_rate', 'customer_satisfaction_score']].mean().reset_index()
        fig_satisfaction = px.scatter(segment_metrics, x='return_rate', y='customer_satisfaction_score', size='return_rate', color='customer_segment',
                                     title='Return Rate vs. Customer Satisfaction', labels={'return_rate': 'Avg. Return Rate', 'customer_satisfaction_score': 'Avg. Satisfaction Score'})
        st.plotly_chart(fig_satisfaction, use_container_width=True)

with tab2:
    st.subheader("Store & Inventory Analysis")
    col1, col2 = st.columns(2)
    with col1:
        # 5. 门店类型销售额对比
        sales_by_store_type = filtered_df.groupby('store_type')['net_sales'].sum().reset_index()
        fig_store = px.bar(sales_by_store_type, x='store_type', y='net_sales', title='Net Sales by Store Type', color='store_type')
        st.plotly_chart(fig_store, use_container_width=True)
        
        # 6. 库存水平 vs 缺货事件 (Top 10 缺货产品)
        # 计算库存平均值和缺货总数
        stockout_by_product = inventory[inventory['stockout_flag'] == 1].groupby('product_id').size().reset_index(name='stockout_count')
        stockout_by_product = stockout_by_product.merge(products[['product_id', 'product_category']], on='product_id', how='left')
        top_stockout = stockout_by_product.nlargest(10, 'stockout_count')
        fig_stockout = px.bar(top_stockout, x='product_id', y='stockout_count', title='Top 10 Products by Stockout Events', color='product_category')
        st.plotly_chart(fig_stockout, use_container_width=True)
        
    with col2:
        # 7. 库存周转率 (简单模拟: 总销售额 / 平均库存水平)
        # 计算平均库存水平 (假设期末库存)
        avg_inventory = inventory.groupby('store_id')['inventory_level'].mean().reset_index()
        store_sales = filtered_df.groupby('store_id')['net_sales'].sum().reset_index()
        store_turnover = store_sales.merge(avg_inventory, on='store_id')
        store_turnover['turnover_rate'] = store_turnover['net_sales'] / store_turnover['inventory_level']
        fig_turnover = px.bar(store_turnover, x='store_id', y='turnover_rate', title='Store Turnover Rate (Net Sales / Avg Inventory)', color='turnover_rate')
        st.plotly_chart(fig_turnover, use_container_width=True)

with tab3:
    st.subheader("Marketing & Customer Insights")
    col1, col2 = st.columns(2)
    with col1:
        # 8. 营销活动ROI (按渠道)
        campaign_roi = campaigns.groupby('ad_channel')[['marketing_spend', 'conversion_rate', 'impressions']].mean().reset_index()
        # 假设 ROI = conversion_rate / (marketing_spend/impressions) 的简化计算
        campaign_roi['roi'] = campaign_roi['conversion_rate'] / (campaign_roi['marketing_spend'] / campaign_roi['impressions']) * 1000
        fig_roi = px.bar(campaign_roi, x='ad_channel', y='roi', title='Average ROI by Ad Channel', color='ad_channel')
        st.plotly_chart(fig_roi, use_container_width=True)
        
        # 9. 客户流失率 vs 忠诚度会员比例
        segment_data = customers[['customer_segment', 'churn_rate', 'loyalty_member_ratio']]
        fig_loyalty = px.scatter(segment_data, x='loyalty_member_ratio', y='churn_rate', size='churn_rate', color='customer_segment',
                                 title='Loyalty Members vs. Churn Rate', labels={'loyalty_member_ratio': 'Loyalty Member Ratio', 'churn_rate': 'Churn Rate'})
        st.plotly_chart(fig_loyalty, use_container_width=True)
        
    with col2:
        # 10. 营销活动转化率 vs 花费
        fig_conversion = px.scatter(campaigns, x='marketing_spend', y='conversion_rate', size='impressions', color='ad_channel',
                                   title='Marketing Spend vs. Conversion Rate', labels={'marketing_spend': 'Marketing Spend ($)', 'conversion_rate': 'Conversion Rate'})
        st.plotly_chart(fig_conversion, use_container_width=True)

with tab4:
    st.subheader("External Factors Impact")
    # 11. 销售额 vs 通胀率/竞争对手价格
    external_merged = filtered_df.groupby('date_only')[['net_sales', 'inflation_rate', 'competitor_price']].mean().reset_index()
    external_merged = external_merged.melt(id_vars='date_only', value_vars=['net_sales', 'inflation_rate', 'competitor_price'], var_name='Metric', value_name='Value')
    
    # 多折线图
    fig_ext = px.line(external_merged, x='date_only', y='Value', color='Metric', title='Net Sales vs. Inflation Rate vs. Competitor Price Over Time')
    st.plotly_chart(fig_ext, use_container_width=True)
    
    # 12. 天气状况对销售额的影响
    sales_by_weather = filtered_df.groupby('weather_condition')['net_sales'].sum().reset_index()
    fig_weather = px.bar(sales_by_weather, x='weather_condition', y='net_sales', title='Net Sales by Weather Condition', color='weather_condition')
    st.plotly_chart(fig_weather, use_container_width=True)

with tab5:
    st.subheader("🚨 Anomaly Detection in Accounts Payable")
    st.markdown("This table highlights suspicious transactions detected in the AP system based on size, payment delay, or other rules.")
    
    # 显示可疑交易表
    if not suspicious.empty:
        st.dataframe(suspicious[['APID', 'Vendor', 'InvoiceDate', 'DueDate', 'Amount', 'Currency', 'Status', 'amount_usd']], use_container_width=True)
        
        # 按供应商统计异常金额
        anomaly_by_vendor = suspicious.groupby('Vendor')['amount_usd'].sum().reset_index().nlargest(10, 'amount_usd')
        fig_anomaly = px.bar(anomaly_by_vendor, x='Vendor', y='amount_usd', title='Top 10 Vendors with Highest Suspicious Amounts (USD)', color='amount_usd')
        st.plotly_chart(fig_anomaly, use_container_width=True)
    else:
        st.info("No suspicious transactions found in the selected period.")

# --- 在侧边栏底部展示数据字典概要 ---
st.sidebar.markdown("---")
with st.sidebar.expander("📘 Quick Data Dictionary"):
    st.markdown("""
    - **Net Sales**: Revenue after discounts
    - **Return Rate**: Percentage of returned units
    - **Gross Profit Margin**: (Gross Profit / Net Sales) * 100
    - **Stockout Events**: Number of products out of stock
    - **Stockout Rate**: Total stockout events / total inventory count
    - **Customer Segments**: Budget, Enterprise, Premium
    - **Store Types**: Online, Offline, Hybrid
    - **External Factors**: Inflation rate, competitor price, weather
    - **Suspicious AP**: Transactions flagged by the system as anomalies
    """)
    
st.sidebar.markdown("---")
st.sidebar.caption("© SalesMind Analytics Dashboard | Powered by Streamlit")
