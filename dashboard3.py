import streamlit as st
import pandas as pd
import plotly.express as px
import os

st.set_page_config(page_title="SalesMind Executive Dashboard", layout="wide")

# ---------- 1. 检查核心文件 ----------
required_files = [
    'SalesMind_Sales_Transactions_2026.csv',
    'SalesMind_Products_Master_2026.csv',
    'SalesMind_Calendar_Dimension_2026.csv',
    'SalesMind_Customer_Segments_2026.csv',
    'SalesMind_Marketing_Campaigns_2026.csv'
]
missing = [f for f in required_files if not os.path.exists(f)]
if missing:
    st.error(f"❌ Missing files: {', '.join(missing)}")
    st.stop()

# ---------- 2. 加载核心数据 ----------
@st.cache_data
def load_core_data():
    sales = pd.read_csv('SalesMind_Sales_Transactions_2026.csv')
    products = pd.read_csv('SalesMind_Products_Master_2026.csv')
    calendar = pd.read_csv('SalesMind_Calendar_Dimension_2026.csv')
    customers = pd.read_csv('SalesMind_Customer_Segments_2026.csv')
    campaigns = pd.read_csv('SalesMind_Marketing_Campaigns_2026.csv')
    
    # 转换日期
    sales['date'] = pd.to_datetime(sales['date'])
    calendar['date'] = pd.to_datetime(calendar['date'])
    
    # 合并
    df = sales.merge(products, on='product_id', how='left')
    df = df.merge(calendar, on='date', how='left')
    df = df.merge(customers, on='customer_segment', how='left')
    
    df['date_only'] = df['date'].dt.date
    return df, campaigns

with st.spinner("Loading data..."):
    df, campaigns = load_core_data()

st.success("✅ Core data loaded successfully!")

# ---------- 3. 侧边栏筛选 ----------
st.sidebar.title("📊 Dashboard Filters")
min_date = df['date'].min().date()
max_date = df['date'].max().date()
start_date, end_date = st.sidebar.date_input(
    "Select Date Range",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date
)
mask = (df['date_only'] >= start_date) & (df['date_only'] <= end_date)
filtered = df.loc[mask].copy()

# 动态筛选选项
cust_segs = ['All'] + sorted(filtered['customer_segment'].dropna().unique().tolist())
cat_types = ['All'] + sorted(filtered['product_category'].dropna().unique().tolist())

cust_seg = st.sidebar.selectbox("Customer Segment", cust_segs)
cat_type = st.sidebar.selectbox("Product Category", cat_types)

if cust_seg != 'All':
    filtered = filtered[filtered['customer_segment'] == cust_seg]
if cat_type != 'All':
    filtered = filtered[filtered['product_category'] == cat_type]

# ---------- 4. KPI ----------
st.title("📈 SalesMind Executive Dashboard")
st.markdown(f"**Period:** {start_date} to {end_date} | **Customer:** {cust_seg} | **Category:** {cat_type}")
st.markdown("---")

if filtered.empty:
    st.warning("No data matches the selected filters.")
    st.stop()

total_net = filtered['net_sales'].sum()
total_units = filtered['units_sold'].sum()
total_discount = filtered['total_discount_given'].sum()
total_rev = filtered['total_sales_revenue'].sum()
discount_rate = (total_discount / total_rev * 100) if total_rev > 0 else 0
return_rate = filtered['return_rate'].mean() * 100
gross_margin = (filtered['gross_profit'].sum() / total_net * 100) if total_net > 0 else 0

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("💰 Net Sales", f"${total_net:,.0f}")
col2.metric("📦 Units Sold", f"{total_units:,.0f}")
col3.metric("💸 Avg. Discount", f"{discount_rate:.1f}%")
col4.metric("🔄 Return Rate", f"{return_rate:.1f}%")
col5.metric("📈 Gross Margin", f"{gross_margin:.1f}%")
st.markdown("---")

# ---------- 5. 选项卡 ----------
tab1, tab2 = st.tabs(["📊 Sales Performance", "🎯 Marketing Insights"])

with tab1:
    st.subheader("Sales Performance")
    c1, c2 = st.columns(2)
    with c1:
        daily = filtered.groupby('date_only')['net_sales'].sum().reset_index()
        fig = px.line(daily, x='date_only', y='net_sales', title='Daily Net Sales')
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        cat_sales = filtered.groupby('product_category')['net_sales'].sum().reset_index()
        fig = px.pie(cat_sales, values='net_sales', names='product_category', title='Sales by Category', hole=0.3)
        st.plotly_chart(fig, use_container_width=True)
    
    c3, c4 = st.columns(2)
    with c3:
        seg_sales = filtered.groupby('customer_segment')['net_sales'].sum().reset_index()
        fig = px.bar(seg_sales, x='customer_segment', y='net_sales', title='Sales by Customer Segment', color='customer_segment')
        st.plotly_chart(fig, use_container_width=True)
    with c4:
        seg_metrics = filtered.groupby('customer_segment')[['return_rate', 'customer_satisfaction_score']].mean().reset_index()
        fig = px.scatter(seg_metrics, x='return_rate', y='customer_satisfaction_score', size='return_rate',
                         color='customer_segment', title='Return Rate vs. Satisfaction')
        st.plotly_chart(fig, use_container_width=True)

with tab2:
    st.subheader("Marketing Channel ROI")
    try:
        channel_agg = campaigns.groupby('ad_channel').agg(
            total_spend=('marketing_spend', 'sum'),
            avg_conv=('conversion_rate', 'mean'),
            total_imp=('impressions', 'sum')
        ).reset_index()
        channel_agg['roi'] = channel_agg.apply(
            lambda x: x['avg_conv'] / (x['total_spend'] / x['total_imp']) * 1000 if x['total_spend'] > 0 else 0, axis=1
        )
        fig = px.bar(channel_agg, x='ad_channel', y='roi', title='Estimated ROI by Ad Channel', color='ad_channel')
        st.plotly_chart(fig, use_container_width=True)

        fig2 = px.scatter(campaigns, x='marketing_spend', y='conversion_rate', size='impressions',
                          color='ad_channel', hover_data=['campaign_type'], title='Spend vs. Conversion Rate')
        st.plotly_chart(fig2, use_container_width=True)
    except Exception as e:
        st.error(f"Error in marketing tab: {e}")