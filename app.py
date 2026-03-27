import streamlit as st
import pandas as pd
import plotly.express as px
import os

st.set_page_config(page_title="SalesMind Executive Dashboard", layout="wide")

# ---------- 1. 检查文件是否存在 ----------
required_files = [
    'SalesMind_Sales_Transactions_2026.csv',
    'SalesMind_Stores_Master_2026.csv',
    'SalesMind_Products_Master_2026.csv',
    'SalesMind_Calendar_Dimension_2026.csv',
    'SalesMind_Customer_Segments_2026.csv',
    'SalesMind_External_Factors_2026.csv',
    'SalesMind_Inventory_Supply_2026.csv',
    'SalesMind_Marketing_Campaigns_2026.csv',
    'suspicious_transactions.csv'
]
missing = [f for f in required_files if not os.path.exists(f)]
if missing:
    st.error(f"Missing files: {', '.join(missing)}")
    st.stop()

# ---------- 2. 加载数据 ----------
@st.cache_data
def load_data():
    sales = pd.read_csv('SalesMind_Sales_Transactions_2026.csv')
    stores = pd.read_csv('SalesMind_Stores_Master_2026.csv')
    products = pd.read_csv('SalesMind_Products_Master_2026.csv')
    calendar = pd.read_csv('SalesMind_Calendar_Dimension_2026.csv')
    customers = pd.read_csv('SalesMind_Customer_Segments_2026.csv')
    external = pd.read_csv('SalesMind_External_Factors_2026.csv')
    inventory = pd.read_csv('SalesMind_Inventory_Supply_2026.csv')
    campaigns = pd.read_csv('SalesMind_Marketing_Campaigns_2026.csv')
    suspicious = pd.read_csv('suspicious_transactions.csv')

    # 日期转换
    sales['date'] = pd.to_datetime(sales['date'])
    calendar['date'] = pd.to_datetime(calendar['date'])
    external['date'] = pd.to_datetime(external['date'])
    if 'InvoiceDate' in suspicious.columns:
        suspicious['InvoiceDate'] = pd.to_datetime(suspicious['InvoiceDate'])
        suspicious['DueDate'] = pd.to_datetime(suspicious['DueDate'])

    # 主表合并
    df = sales.merge(stores, on='store_id', how='left')
    df = df.merge(products, on='product_id', how='left')
    df = df.merge(calendar, on='date', how='left')
    df = df.merge(customers, on='customer_segment', how='left')
    df = df.merge(external, on='date', how='left')
    df = df.merge(inventory, on=['store_id', 'product_id'], how='left')

    # 营销数据按日聚合
    daily_mkt = campaigns.groupby('date')['marketing_spend'].sum().reset_index()
    daily_mkt['date'] = pd.to_datetime(daily_mkt['date'])
    df = df.merge(daily_mkt, on='date', how='left')
    df['marketing_spend'] = df['marketing_spend'].fillna(0)

    df['date_only'] = df['date'].dt.date
    return df, stores, products, calendar, customers, external, inventory, campaigns, suspicious

df, stores, products, calendar, customers, external, inventory, campaigns, suspicious = load_data()

# ---------- 3. 侧边栏筛选器 ----------
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
store_types = ['All'] + sorted(filtered['store_type'].dropna().unique())
store_type = st.sidebar.selectbox("Store Type", store_types)
cust_segs = ['All'] + sorted(filtered['customer_segment'].dropna().unique())
cust_seg = st.sidebar.selectbox("Customer Segment", cust_segs)
cat_types = ['All'] + sorted(filtered['product_category'].dropna().unique())
cat_type = st.sidebar.selectbox("Product Category", cat_types)

if store_type != 'All':
    filtered = filtered[filtered['store_type'] == store_type]
if cust_seg != 'All':
    filtered = filtered[filtered['customer_segment'] == cust_seg]
if cat_type != 'All':
    filtered = filtered[filtered['product_category'] == cat_type]

# ---------- 4. 标题与KPI ----------
st.title("📈 SalesMind Executive Dashboard")
st.markdown(f"**Period:** {start_date} to {end_date} | **Store:** {store_type} | **Customer:** {cust_seg} | **Category:** {cat_type}")
st.markdown("---")

total_net = filtered['net_sales'].sum()
total_units = filtered['units_sold'].sum()
total_discount = filtered['total_discount_given'].sum()
total_rev = filtered['total_sales_revenue'].sum()
discount_rate = (total_discount / total_rev * 100) if total_rev > 0 else 0
return_rate = filtered['return_rate'].mean() * 100
gross_margin = (filtered['gross_profit'].sum() / total_net * 100) if total_net > 0 else 0

# 库存指标（基于筛选后的门店）
store_ids = filtered['store_id'].unique()
inv_filtered = inventory[inventory['store_id'].isin(store_ids)]
stockout_count = inv_filtered[inv_filtered['stockout_flag'] == 1].shape[0]

col1, col2, col3, col4, col5, col6 = st.columns(6)
col1.metric("💰 Net Sales", f"${total_net:,.0f}")
col2.metric("📦 Units Sold", f"{total_units:,.0f}")
col3.metric("💸 Avg. Discount", f"{discount_rate:.1f}%")
col4.metric("🔄 Return Rate", f"{return_rate:.1f}%")
col5.metric("📈 Gross Margin", f"{gross_margin:.1f}%")
col6.metric("⚠️ Stockout Events", f"{stockout_count:,}")

st.markdown("---")

# ---------- 5. 选项卡 ----------
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Sales Performance",
    "🏪 Store & Inventory",
    "🎯 Marketing & Customers",
    "🌍 External Factors",
    "🚨 Suspicious AP"
])

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
    st.subheader("Store & Inventory Analysis")
    c1, c2 = st.columns(2)
    with c1:
        store_sales = filtered.groupby('store_type')['net_sales'].sum().reset_index()
        fig = px.bar(store_sales, x='store_type', y='net_sales', title='Sales by Store Type', color='store_type')
        st.plotly_chart(fig, use_container_width=True)

        # Top 10 stockout products
        if not inv_filtered.empty:
            stockout_prods = inv_filtered[inv_filtered['stockout_flag'] == 1].groupby('product_id').size().reset_index(name='count')
            if not stockout_prods.empty:
                stockout_prods = stockout_prods.merge(products[['product_id', 'product_category']], on='product_id', how='left')
                top10 = stockout_prods.nlargest(10, 'count')
                fig = px.bar(top10, x='product_id', y='count', title='Top 10 Stockout Products', color='product_category')
                st.plotly_chart(fig, use_container_width=True)
    with c2:
        # Inventory turnover (sales / avg inventory)
        avg_inv = inv_filtered.groupby('store_id')['inventory_level'].mean().reset_index()
        store_sales_sum = filtered.groupby('store_id')['net_sales'].sum().reset_index()
        turnover = store_sales_sum.merge(avg_inv, on='store_id')
        turnover['turnover'] = turnover.apply(lambda row: row['net_sales'] / row['inventory_level'] if row['inventory_level'] > 0 else 0, axis=1)
        fig = px.bar(turnover, x='store_id', y='turnover', title='Store Turnover (Sales / Avg Inventory)', color='turnover')
        st.plotly_chart(fig, use_container_width=True)

with tab3:
    st.subheader("Marketing & Customer Insights")
    c1, c2 = st.columns(2)
    with c1:
        # Channel ROI (simplified)
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

        # Loyalty vs Churn
        seg_data = customers[['customer_segment', 'churn_rate', 'loyalty_member_ratio']].dropna()
        fig = px.scatter(seg_data, x='loyalty_member_ratio', y='churn_rate', size='churn_rate',
                         color='customer_segment', title='Loyalty Members vs. Churn Rate')
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        fig = px.scatter(campaigns, x='marketing_spend', y='conversion_rate', size='impressions',
                         color='ad_channel', hover_data=['campaign_type'], title='Spend vs. Conversion Rate')
        st.plotly_chart(fig, use_container_width=True)

with tab4:
    st.subheader("External Factors Impact")
    ext_data = filtered.groupby('date_only')[['net_sales', 'inflation_rate', 'competitor_price']].mean().reset_index()
    ext_melt = ext_data.melt(id_vars='date_only', value_vars=['net_sales', 'inflation_rate', 'competitor_price'],
                             var_name='Metric', value_name='Value')
    fig = px.line(ext_melt, x='date_only', y='Value', color='Metric', title='Net Sales vs. Inflation vs. Competitor Price')
    st.plotly_chart(fig, use_container_width=True)

    weather_sales = filtered.groupby('weather_condition')['net_sales'].sum().reset_index()
    fig = px.bar(weather_sales, x='weather_condition', y='net_sales', title='Sales by Weather', color='weather_condition')
    st.plotly_chart(fig, use_container_width=True)

with tab5:
    st.subheader("Suspicious Accounts Payable")
    if not suspicious.empty:
        st.dataframe(suspicious[['APID', 'Vendor', 'InvoiceDate', 'DueDate', 'Amount', 'Currency', 'Status', 'amount_usd']])
        vendor_sum = suspicious.groupby('Vendor')['amount_usd'].sum().reset_index().nlargest(10, 'amount_usd')
        fig = px.bar(vendor_sum, x='Vendor', y='amount_usd', title='Top 10 Vendors by Suspicious Amount')
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No suspicious transactions found in the data.")