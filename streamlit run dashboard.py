import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import matplotlib.pyplot as plt
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Page configuration
st.set_page_config(
    page_title="SalesMind Analytics Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1E3A8A;
        margin-bottom: 1rem;
    }
    .metric-card {
        background-color: #F3F4F6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem;
    }
    .sub-header {
        font-size: 1.5rem;
        font-weight: 600;
        color: #2563EB;
        margin-top: 1rem;
        margin-bottom: 1rem;
    }
    </style>
""", unsafe_allow_html=True)

# Load all data files
@st.cache_data
def load_data():
    # Load main datasets
    sales = pd.read_csv('SalesMind_Sales_Transactions_2026.csv')
    stores = pd.read_csv('SalesMind_Stores_Master_2026.csv')
    products = pd.read_csv('SalesMind_Products_Master_2026.csv')
    campaigns = pd.read_csv('SalesMind_Marketing_Campaigns_2026.csv')
    inventory = pd.read_csv('SalesMind_Inventory_Supply_2026.csv')
    calendar = pd.read_csv('SalesMind_Calendar_Dimension_2026.csv')
    customer_segments = pd.read_csv('SalesMind_Customer_Segments_2026.csv')
    external_factors = pd.read_csv('SalesMind_External_Factors_2026.csv')
    suspicious = pd.read_csv('suspicious_transactions.csv')
    
    # Convert date columns
    sales['date'] = pd.to_datetime(sales['date'])
    external_factors['date'] = pd.to_datetime(external_factors['date'])
    if 'date' in calendar.columns:
        calendar['date'] = pd.to_datetime(calendar['date'])
    
    # Add year and month columns
    sales['year'] = sales['date'].dt.year
    sales['month'] = sales['date'].dt.month
    sales['quarter'] = sales['date'].dt.quarter
    
    return sales, stores, products, campaigns, inventory, calendar, customer_segments, external_factors, suspicious

# Load data
sales, stores, products, campaigns, inventory, calendar, customer_segments, external_factors, suspicious = load_data()

# Merge sales with store and product data for analysis
sales_with_details = sales.merge(stores, left_on='store_id', right_on='store_id', how='left')
sales_with_details = sales_with_details.merge(products, left_on='product_id', right_on='product_id', how='left')
sales_with_details = sales_with_details.merge(customer_segments, left_on='customer_segment', right_on='customer_segment', how='left')

# Sidebar filters
st.sidebar.title("🔍 Filters")

# Date range filter
min_date = sales['date'].min().date()
max_date = sales['date'].max().date()
date_range = st.sidebar.date_input(
    "Date Range",
    [min_date, max_date],
    min_value=min_date,
    max_value=max_date
)

# Segment filter
segments = ['All'] + list(sales['customer_segment'].unique())
selected_segment = st.sidebar.selectbox("Customer Segment", segments)

# Product category filter
categories = ['All'] + list(products['product_category'].unique())
selected_category = st.sidebar.selectbox("Product Category", categories)

# Region filter
regions = ['All'] + list(stores['region'].unique())
selected_region = st.sidebar.selectbox("Region", regions)

# Apply filters
filtered_sales = sales_with_details.copy()
if len(date_range) == 2:
    filtered_sales = filtered_sales[
        (filtered_sales['date'] >= pd.to_datetime(date_range[0])) &
        (filtered_sales['date'] <= pd.to_datetime(date_range[1]))
    ]
if selected_segment != 'All':
    filtered_sales = filtered_sales[filtered_sales['customer_segment'] == selected_segment]
if selected_category != 'All':
    filtered_sales = filtered_sales[filtered_sales['product_category'] == selected_category]
if selected_region != 'All':
    filtered_sales = filtered_sales[filtered_sales['region'] == selected_region]

# Main Dashboard Title
st.markdown('<div class="main-header">📊 SalesMind Analytics Dashboard</div>', unsafe_allow_html=True)
st.markdown("### Real-time Business Intelligence & Sales Performance Insights")
st.markdown("---")

# Key Metrics Row
st.markdown('<div class="sub-header">🎯 Key Performance Indicators</div>', unsafe_allow_html=True)

col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    total_revenue = filtered_sales['total_sales_revenue'].sum()
    st.metric("💰 Total Revenue", f"${total_revenue:,.0f}")

with col2:
    total_units = filtered_sales['units_sold'].sum()
    st.metric("📦 Units Sold", f"{total_units:,}")

with col3:
    avg_margin = filtered_sales['profit_margin'].mean()
    st.metric("📈 Avg Profit Margin", f"${avg_margin:.2f}")

with col4:
    avg_discount = filtered_sales['total_discount_given'].sum() / len(filtered_sales) if len(filtered_sales) > 0 else 0
    st.metric("🏷️ Avg Discount", f"${avg_discount:.2f}")

with col5:
    avg_return_rate = filtered_sales['return_rate'].mean() * 100
    st.metric("↩️ Return Rate", f"{avg_return_rate:.1f}%")

st.markdown("---")

# Row 1: Revenue Trends and Customer Segment Analysis
col1, col2 = st.columns(2)

with col1:
    st.markdown('<div class="sub-header">📈 Sales Revenue Trend</div>', unsafe_allow_html=True)
    
    # Aggregate daily revenue
    daily_revenue = filtered_sales.groupby('date')['total_sales_revenue'].sum().reset_index()
    
    fig_revenue = px.line(daily_revenue, x='date', y='total_sales_revenue',
                          title='Daily Sales Revenue',
                          labels={'total_sales_revenue': 'Revenue ($)', 'date': 'Date'},
                          template='plotly_white')
    fig_revenue.update_layout(showlegend=False, height=400)
    st.plotly_chart(fig_revenue, use_container_width=True)

with col2:
    st.markdown('<div class="sub-header">👥 Customer Segment Performance</div>', unsafe_allow_html=True)
    
    segment_revenue = filtered_sales.groupby('customer_segment')['total_sales_revenue'].sum().reset_index()
    segment_units = filtered_sales.groupby('customer_segment')['units_sold'].sum().reset_index()
    
    fig_segment = make_subplots(specs=[[{"secondary_y": True}]])
    fig_segment.add_trace(go.Bar(name='Revenue ($)', x=segment_revenue['customer_segment'], 
                                 y=segment_revenue['total_sales_revenue'], marker_color='#3B82F6'),
                         secondary_y=False)
    fig_segment.add_trace(go.Scatter(name='Units Sold', x=segment_units['customer_segment'], 
                                     y=segment_units['units_sold'], mode='lines+markers', 
                                     line=dict(color='#EF4444', width=2)),
                         secondary_y=True)
    fig_segment.update_layout(title='Revenue vs Units by Segment', height=400, template='plotly_white')
    fig_segment.update_xaxes(title_text="Customer Segment")
    fig_segment.update_yaxes(title_text="Revenue ($)", secondary_y=False)
    fig_segment.update_yaxes(title_text="Units Sold", secondary_y=True)
    st.plotly_chart(fig_segment, use_container_width=True)

# Row 2: Product Analysis and Store Performance
col1, col2 = st.columns(2)

with col1:
    st.markdown('<div class="sub-header">🏆 Top 10 Products by Revenue</div>', unsafe_allow_html=True)
    
    top_products = filtered_sales.groupby(['product_id', 'product_category', 'brand'])['total_sales_revenue'].sum().reset_index()
    top_products = top_products.nlargest(10, 'total_sales_revenue')
    
    fig_products = px.bar(top_products, x='total_sales_revenue', y='product_id', 
                          orientation='h', color='product_category',
                          title='Top Products by Revenue',
                          labels={'total_sales_revenue': 'Revenue ($)', 'product_id': 'Product ID'},
                          template='plotly_white')
    fig_products.update_layout(height=400)
    st.plotly_chart(fig_products, use_container_width=True)

with col2:
    st.markdown('<div class="sub-header">🏪 Store Performance by Region</div>', unsafe_allow_html=True)
    
    store_revenue = filtered_sales.groupby(['store_id', 'region'])['total_sales_revenue'].sum().reset_index()
    store_revenue = store_revenue.nlargest(15, 'total_sales_revenue')
    
    fig_stores = px.bar(store_revenue, x='total_sales_revenue', y='store_id', 
                        color='region', orientation='h',
                        title='Top 15 Stores by Revenue',
                        labels={'total_sales_revenue': 'Revenue ($)', 'store_id': 'Store ID'},
                        template='plotly_white')
    fig_stores.update_layout(height=400)
    st.plotly_chart(fig_stores, use_container_width=True)

# Row 3: Marketing Campaign Analysis
st.markdown('<div class="sub-header">📢 Marketing Campaign Performance</div>', unsafe_allow_html=True)

col1, col2, col3 = st.columns(3)

with col1:
    total_marketing_spend = campaigns['marketing_spend'].sum()
    st.metric("Total Marketing Spend", f"${total_marketing_spend:,.0f}")

with col2:
    avg_conversion = campaigns['conversion_rate'].mean() * 100
    st.metric("Avg Conversion Rate", f"{avg_conversion:.1f}%")

with col3:
    total_impressions = campaigns['impressions'].sum()
    st.metric("Total Impressions", f"{total_impressions:,.0f}")

# Marketing ROI Analysis
campaign_performance = campaigns.groupby('ad_channel').agg({
    'marketing_spend': 'sum',
    'conversion_rate': 'mean',
    'impressions': 'sum'
}).reset_index()

fig_channels = px.bar(campaign_performance, x='ad_channel', y='marketing_spend',
                      color='conversion_rate', title='Marketing Spend by Channel',
                      labels={'marketing_spend': 'Spend ($)', 'ad_channel': 'Channel'},
                      template='plotly_white')
st.plotly_chart(fig_channels, use_container_width=True)

# Row 4: Inventory and Supply Chain
st.markdown('<div class="sub-header">📦 Inventory & Supply Chain Metrics</div>', unsafe_allow_html=True)

col1, col2 = st.columns(2)

with col1:
    # Inventory levels by store type
    inventory_with_stores = inventory.merge(stores, left_on='store_id', right_on='store_id', how='left')
    inv_by_type = inventory_with_stores.groupby('store_type')['inventory_level'].mean().reset_index()
    
    fig_inventory = px.bar(inv_by_type, x='store_type', y='inventory_level',
                           title='Average Inventory Level by Store Type',
                           labels={'inventory_level': 'Avg Inventory', 'store_type': 'Store Type'},
                           color='store_type', template='plotly_white')
    st.plotly_chart(fig_inventory, use_container_width=True)

with col2:
    # Stockout risk analysis
    stockout_count = inventory['stockout_flag'].sum()
    stockout_pct = (stockout_count / len(inventory)) * 100
    
    fig_stockout = go.Figure(data=[go.Pie(labels=['In Stock', 'Stockout'], 
                                         values=[len(inventory) - stockout_count, stockout_count],
                                         marker_colors=['#10B981', '#EF4444'])])
    fig_stockout.update_layout(title='Stockout Risk Analysis', height=400)
    st.plotly_chart(fig_stockout, use_container_width=True)

# Row 5: External Factors Impact
st.markdown('<div class="sub-header">🌍 External Factors Impact on Sales</div>', unsafe_allow_html=True)

# Merge sales with external factors
sales_with_external = sales.merge(external_factors, left_on='date', right_on='date', how='left')
external_aggregated = sales_with_external.groupby('weather_condition').agg({
    'total_sales_revenue': 'mean',
    'units_sold': 'mean'
}).reset_index()

fig_weather = px.bar(external_aggregated, x='weather_condition', y='total_sales_revenue',
                     title='Average Sales Revenue by Weather Condition',
                     labels={'total_sales_revenue': 'Avg Revenue ($)', 'weather_condition': 'Weather'},
                     color='weather_condition', template='plotly_white')
st.plotly_chart(fig_weather, use_container_width=True)

# Row 6: Suspicious Transactions Alert
st.markdown('<div class="sub-header">⚠️ Suspicious Transactions Alert</div>', unsafe_allow_html=True)

if len(suspicious) > 0:
    col1, col2, col3 = st.columns(3)
    with col1:
        st.warning(f"🚨 {len(suspicious)} Suspicious Transactions Detected")
    with col2:
        total_suspicious = suspicious['amount_usd'].sum()
        st.metric("Total Suspicious Amount", f"${total_suspicious:,.0f}")
    with col3:
        open_status = suspicious[suspicious['Status'] == 'Open'].shape[0]
        st.metric("Open Investigations", open_status)
    
    # Show suspicious transactions table
    st.dataframe(suspicious[['APID', 'Vendor', 'InvoiceDate', 'Amount', 'Currency', 'Status', 'amount_usd']].head(10),
                 use_container_width=True)
else:
    st.success("✅ No suspicious transactions detected in the current period")

# Row 7: Customer Insights
st.markdown('<div class="sub-header">👥 Customer Insights</div>', unsafe_allow_html=True)

col1, col2 = st.columns(2)

with col1:
    # Customer segment metrics
    segment_metrics = filtered_sales.groupby('customer_segment').agg({
        'repeat_customer_rate': 'mean',
        'customer_satisfaction_score': 'mean'
    }).reset_index()
    
    fig_customer = px.scatter(segment_metrics, x='repeat_customer_rate', y='customer_satisfaction_score',
                              text='customer_segment', size=[50]*len(segment_metrics),
                              title='Customer Segment: Repeat Rate vs Satisfaction',
                              labels={'repeat_customer_rate': 'Repeat Customer Rate', 
                                     'customer_satisfaction_score': 'Satisfaction Score'},
                              template='plotly_white')
    fig_customer.update_traces(textposition='top center')
    st.plotly_chart(fig_customer, use_container_width=True)

with col2:
    # Churn rate by segment
    churn_data = filtered_sales.groupby('customer_segment')['churn_rate'].mean().reset_index()
    
    fig_churn = px.bar(churn_data, x='customer_segment', y='churn_rate',
                       title='Churn Rate by Customer Segment',
                       labels={'churn_rate': 'Churn Rate', 'customer_segment': 'Segment'},
                       color='churn_rate', template='plotly_white')
    st.plotly_chart(fig_churn, use_container_width=True)

# Row 8: Time Series Analysis
st.markdown('<div class="sub-header">📅 Time Series Analysis</div>', unsafe_allow_html=True)

col1, col2 = st.columns(2)

with col1:
    # Monthly trend by segment
    monthly_trend = filtered_sales.groupby(['month', 'customer_segment'])['total_sales_revenue'].sum().reset_index()
    
    fig_monthly = px.line(monthly_trend, x='month', y='total_sales_revenue', 
                          color='customer_segment', title='Monthly Revenue Trend by Segment',
                          labels={'total_sales_revenue': 'Revenue ($)', 'month': 'Month'},
                          template='plotly_white')
    st.plotly_chart(fig_monthly, use_container_width=True)

with col2:
    # Quarterly performance
    quarterly_perf = filtered_sales.groupby(['quarter', 'year'])['total_sales_revenue'].sum().reset_index()
    quarterly_perf['Quarter_Label'] = quarterly_perf['year'].astype(str) + '-Q' + quarterly_perf['quarter'].astype(str)
    
    fig_quarterly = px.bar(quarterly_perf, x='Quarter_Label', y='total_sales_revenue',
                           title='Quarterly Revenue Performance',
                           labels={'total_sales_revenue': 'Revenue ($)', 'Quarter_Label': 'Quarter'},
                           color='total_sales_revenue', template='plotly_white')
    st.plotly_chart(fig_quarterly, use_container_width=True)

# Row 9: Profitability Analysis
st.markdown('<div class="sub-header">💰 Profitability Analysis</div>', unsafe_allow_html=True)

col1, col2 = st.columns(2)

with col1:
    # Profit by category
    profit_by_category = filtered_sales.groupby('product_category')['gross_profit'].sum().reset_index()
    
    fig_profit = px.pie(profit_by_category, values='gross_profit', names='product_category',
                        title='Gross Profit Distribution by Product Category',
                        template='plotly_white')
    st.plotly_chart(fig_profit, use_container_width=True)

with col2:
    # Discount vs Profit correlation
    discount_profit = filtered_sales.groupby('product_category').agg({
        'total_discount_given': 'mean',
        'gross_profit': 'mean'
    }).reset_index()
    
    fig_discount = px.scatter(discount_profit, x='total_discount_given', y='gross_profit',
                              text='product_category', size=[50]*len(discount_profit),
                              title='Discount vs Profit Correlation',
                              labels={'total_discount_given': 'Avg Discount ($)', 
                                     'gross_profit': 'Avg Gross Profit ($)'},
                              template='plotly_white')
    st.plotly_chart(fig_discount, use_container_width=True)

# Footer
st.markdown("---")
st.markdown("### 📊 Dashboard Summary")
st.markdown(f"""
- **Data Period**: {date_range[0]} to {date_range[1]} (if applicable)
- **Total Transactions Analyzed**: {len(filtered_sales):,}
- **Unique Stores**: {filtered_sales['store_id'].nunique()}
- **Unique Products**: {filtered_sales['product_id'].nunique()}
- **Customer Segments**: {', '.join(filtered_sales['customer_segment'].unique())}
""")

st.markdown("---")
st.markdown("### 🔄 Data Refresh Information")
st.markdown("Last updated: March 2026")
st.markdown("Dashboard built with Streamlit | Data Source: SalesMind Enterprise Data Warehouse")

# Download button for filtered data
if st.sidebar.button("📥 Download Filtered Data"):
    csv = filtered_sales.to_csv(index=False)
    st.sidebar.download_button(
        label="Download as CSV",
        data=csv,
        file_name="filtered_sales_data.csv",
        mime="text/csv"
    )
