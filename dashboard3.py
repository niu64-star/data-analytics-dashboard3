import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

# Page configuration
st.set_page_config(page_title="Marketing ROI Dashboard", layout="wide")

st.title("📊 Marketing Effectiveness Dashboard")
st.markdown("### Question: Which channel (Social Media, Email, Paid Search) generates the highest ROI?")
st.markdown("**Hypothesis:** Email yields the highest ROI; social media drives engagement.")

# ------------------------------------------------------------------------------
# Sidebar: User-adjustable CTR (Click-Through Rate) assumption
# ------------------------------------------------------------------------------
st.sidebar.markdown("## ⚙️ Estimation Assumptions")
st.sidebar.markdown("""
The dashboard estimates revenue using:
A lower CTR yields more conservative revenue and ROI estimates.
""")
ctr = st.sidebar.slider(
    "Click-Through Rate (CTR) Assumption",
    min_value=0.005, max_value=0.10, value=0.02, step=0.005,
    format="%.3f",
    help="CTR represents the percentage of impressions that result in a click. "
         "A typical range is 1%–5%. Lower values give more conservative estimates."
)
st.sidebar.markdown(f"Current CTR: **{ctr:.1%}**")

# ------------------------------------------------------------------------------
# 1. Load data
# ------------------------------------------------------------------------------
@st.cache_data
def load_data():
    df_marketing = pd.read_csv("SalesMind_Marketing_Campaigns_2026.csv")
    df_transactions = pd.read_csv("SalesMind_Sales_Transactions_2026.csv")
    return df_marketing, df_transactions

try:
    df_marketing, df_transactions = load_data()
except FileNotFoundError as e:
    st.error(f"File not found: {e}\nPlease ensure the CSV files are in the current directory.")
    st.stop()

# ------------------------------------------------------------------------------
# 2. Data preprocessing
# ------------------------------------------------------------------------------
df_marketing = df_marketing.rename(columns={
    'ad_channel': 'channel',
    'marketing_spend': 'spend',
    'conversion_rate': 'conv_rate',
    'impressions': 'impressions'
})
df_marketing['spend'] = pd.to_numeric(df_marketing['spend'], errors='coerce')
df_marketing['conv_rate'] = pd.to_numeric(df_marketing['conv_rate'], errors='coerce')
df_marketing['impressions'] = pd.to_numeric(df_marketing['impressions'], errors='coerce')
df_marketing.dropna(subset=['spend', 'conv_rate', 'impressions'], inplace=True)

# Calculate Average Order Value (AOV) from transaction data
aov = df_transactions['net_sales'].mean()
st.sidebar.metric("📦 Average Order Value (AOV)", f"${aov:,.2f}")

# -------- CONSERVATIVE ESTIMATION ----------
# Estimated conversions = impressions * CTR * conversion_rate
df_marketing['estimated_conversions'] = df_marketing['impressions'] * ctr * df_marketing['conv_rate']

# Estimated revenue = estimated_conversions * AOV
df_marketing['estimated_revenue'] = df_marketing['estimated_conversions'] * aov

# Calculate ROI
df_marketing['roi'] = (df_marketing['estimated_revenue'] - df_marketing['spend']) / df_marketing['spend']
df_marketing['roi_pct'] = df_marketing['roi'] * 100

# Map to channel categories
channel_mapping = {
    'Google': 'Paid Search',
    'Email': 'Email',
    'Meta': 'Social Media',
    'TikTok': 'Social Media'
}
df_marketing['channel_group'] = df_marketing['channel'].map(channel_mapping)
df_marketing = df_marketing[df_marketing['channel_group'].notna()]

# ------------------------------------------------------------------------------
# 3. Aggregate by channel category
# ------------------------------------------------------------------------------
agg_dict = {
    'spend': 'sum',
    'estimated_revenue': 'sum',
    'impressions': 'sum',
    'estimated_conversions': 'sum'
}
df_grouped = df_marketing.groupby('channel_group').agg(agg_dict).reset_index()
df_grouped['roi'] = (df_grouped['estimated_revenue'] - df_grouped['spend']) / df_grouped['spend']
df_grouped['roi_pct'] = df_grouped['roi'] * 100
df_grouped['avg_conv_rate'] = df_grouped['estimated_conversions'] / df_grouped['impressions']  # weighted avg conversion rate (post-click)
df_grouped = df_grouped.sort_values('roi', ascending=False)

# ------------------------------------------------------------------------------
# 4. Overall KPIs
# ------------------------------------------------------------------------------
total_spend = df_grouped['spend'].sum()
total_revenue = df_grouped['estimated_revenue'].sum()
overall_roi = (total_revenue - total_spend) / total_spend
overall_roi_pct = overall_roi * 100

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("💰 Total Marketing Spend", f"${total_spend:,.0f}")
with col2:
    st.metric("📈 Estimated Total Revenue", f"${total_revenue:,.0f}")
with col3:
    st.metric("🎯 Overall ROI", f"{overall_roi_pct:.1f}%", delta=f"{overall_roi_pct:.1f}%")

st.markdown("---")

# ------------------------------------------------------------------------------
# 5. Visualizations
# ------------------------------------------------------------------------------
st.subheader("Channel Performance Comparison")

# 5.1 ROI bar chart
fig_roi = px.bar(
    df_grouped, x='channel_group', y='roi_pct',
    title='ROI by Channel (%)',
    labels={'roi_pct': 'ROI (%)', 'channel_group': 'Channel'},
    text='roi_pct',
    color='channel_group',
    color_discrete_sequence=px.colors.qualitative.Set2
)
fig_roi.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
st.plotly_chart(fig_roi, use_container_width=True)

# 5.2 Spend vs Revenue
fig_spend_rev = go.Figure()
fig_spend_rev.add_trace(go.Bar(
    x=df_grouped['channel_group'], y=df_grouped['spend'],
    name='Marketing Spend', marker_color='lightcoral'
))
fig_spend_rev.add_trace(go.Bar(
    x=df_grouped['channel_group'], y=df_grouped['estimated_revenue'],
    name='Estimated Revenue', marker_color='mediumseagreen'
))
fig_spend_rev.update_layout(
    title='Marketing Spend vs. Estimated Revenue',
    xaxis_title='Channel',
    yaxis_title='Amount ($)',
    barmode='group'
)
st.plotly_chart(fig_spend_rev, use_container_width=True)

# 5.3 Post-click conversion rate (estimated)
fig_cr = px.bar(
    df_grouped, x='channel_group', y='avg_conv_rate',
    title='Average Post-Click Conversion Rate (Estimated)',
    labels={'avg_conv_rate': 'Conversion Rate', 'channel_group': 'Channel'},
    text=df_grouped['avg_conv_rate'].apply(lambda x: f"{x:.2%}"),
    color='channel_group'
)
fig_cr.update_traces(textposition='outside')
st.plotly_chart(fig_cr, use_container_width=True)

# 5.4 Impressions
fig_imp = px.bar(
    df_grouped, x='channel_group', y='impressions',
    title='Total Impressions',
    labels={'impressions': 'Impressions', 'channel_group': 'Channel'},
    color='channel_group'
)
st.plotly_chart(fig_imp, use_container_width=True)

st.markdown("---")

# ------------------------------------------------------------------------------
# 6. Data tables
# ------------------------------------------------------------------------------
st.subheader("Channel Summary")
display_cols = ['channel_group', 'spend', 'estimated_revenue', 'roi_pct', 'impressions', 'avg_conv_rate']
df_display = df_grouped[display_cols].copy()
df_display.columns = ['Channel', 'Total Spend ($)', 'Estimated Revenue ($)', 'ROI (%)', 'Total Impressions', 'Avg. Post-Click Conv. Rate']
df_display['ROI (%)'] = df_display['ROI (%)'].round(1)
df_display['Avg. Post-Click Conv. Rate'] = df_display['Avg. Post-Click Conv. Rate'].apply(lambda x: f"{x:.2%}")
st.dataframe(df_display, use_container_width=True)

st.subheader("Breakdown by Original Ad Channel")
df_raw = df_marketing.groupby('channel').agg({
    'spend': 'sum',
    'estimated_revenue': 'sum',
    'impressions': 'sum',
    'estimated_conversions': 'sum'
}).reset_index()
df_raw['roi'] = (df_raw['estimated_revenue'] - df_raw['spend']) / df_raw['spend']
df_raw['roi_pct'] = df_raw['roi'] * 100
df_raw['avg_conv_rate'] = df_raw['estimated_conversions'] / df_raw['impressions']
df_raw = df_raw.sort_values('roi', ascending=False)
df_raw_display = df_raw[['channel', 'spend', 'estimated_revenue', 'roi_pct', 'impressions', 'avg_conv_rate']].copy()
df_raw_display.columns = ['Ad Channel', 'Total Spend ($)', 'Estimated Revenue ($)', 'ROI (%)', 'Total Impressions', 'Avg. Post-Click Conv. Rate']
df_raw_display['ROI (%)'] = df_raw_display['ROI (%)'].round(1)
df_raw_display['Avg. Post-Click Conv. Rate'] = df_raw_display['Avg. Post-Click Conv. Rate'].apply(lambda x: f"{x:.2%}")
st.dataframe(df_raw_display, use_container_width=True)

# ------------------------------------------------------------------------------
# 7. Conclusion
# ------------------------------------------------------------------------------
st.markdown("---")
st.subheader("📌 Conclusion")
best_channel = df_grouped.iloc[0]['channel_group']
best_roi = df_grouped.iloc[0]['roi_pct']
st.success(f"✅ Among the channels analyzed, **{best_channel}** delivers the highest ROI at **{best_roi:.1f}%**.")

# Hypothesis testing
email_roi = df_grouped[df_grouped['channel_group'] == 'Email']['roi_pct'].values[0] if 'Email' in df_grouped['channel_group'].values else None
social_roi = df_grouped[df_grouped['channel_group'] == 'Social Media']['roi_pct'].values[0] if 'Social Media' in df_grouped['channel_group'].values else None
paid_roi = df_grouped[df_grouped['channel_group'] == 'Paid Search']['roi_pct'].values[0] if 'Paid Search' in df_grouped['channel_group'].values else None

if email_roi and (email_roi >= (social_roi or 0)) and (email_roi >= (paid_roi or 0)):
    st.info("📧 Hypothesis confirmed: **Email** shows the highest ROI, aligning with the expectation.")
else:
    st.info("📊 Observation: While email performs well, the highest ROI channel may vary. Continuous optimization is recommended.")

st.caption("""
**Note on revenue estimation:**  
Revenue is estimated using a conservative model:  
`Estimated Conversions = Impressions × CTR × Conversion Rate`  
where CTR (Click-Through Rate) is adjustable in the sidebar (default 2%).  
This approach avoids the unrealistic assumption that every impression leads directly to a conversion.  
Actual ROI in practice depends on many factors; use this dashboard to compare relative channel efficiency.
""")
