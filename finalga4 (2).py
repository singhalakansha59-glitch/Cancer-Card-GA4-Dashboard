
import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px

st.set_page_config(
    page_title="Cancer Card GA4 Dashboard",
    page_icon="",
    layout="wide"
)

@st.cache_data
def load_data(file=None, fallback_path="Cancer Card GA4 Data (_).csv"):
    if file is not None:
        df = pd.read_csv(file)
    else:
        df = pd.read_csv(fallback_path)

    df.columns = [c.strip() for c in df.columns]
    num_cols = [
        "Active users","New users","Sessions per user","Views per session",
        "One-day active users","Seven-day active users","28-day active users",
        "30-day active users","Engaged sessions","Engagement rate","Events per session"
    ]
    for c in num_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    if {"Active users","New users"}.issubset(df.columns):
        df["Returning users"] = df["Active users"] - df["New users"]

    if {"Engaged sessions","Active users"}.issubset(df.columns):
        df["Engaged sessions rate"] = (df["Engaged sessions"] / df["Active users"]).replace([np.inf,-np.inf], np.nan)

    if {"30-day active users","One-day active users","Seven-day active users","28-day active users"}.issubset(df.columns):
        denom = df["30-day active users"].replace(0, np.nan)
        df["d1_retention"]  = df["One-day active users"]/denom
        df["d7_retention"]  = df["Seven-day active users"]/denom
        df["d28_retention"] = df["28-day active users"]/denom

    return df

# Sidebar filters
st.sidebar.header("Filters")
uploaded = st.sidebar.file_uploader("Upload GA4 CSV (optional)", type=["csv"])
df = load_data(uploaded)

# Remove "(not set)"
for col in df.select_dtypes(include="object").columns:
    df[col] = df[col].replace("(not set)", np.nan)

continents = ["All"] + sorted(df.get("Continent", pd.Series(dtype=str)).dropna().unique().tolist())
countries  = ["All"] + sorted(df.get("Country", pd.Series(dtype=str)).dropna().unique().tolist())
devices    = ["All"] + sorted(df.get("Device category", pd.Series(dtype=str)).dropna().unique().tolist())

sel_cont    = st.sidebar.selectbox("Continent", continents, 0)
sel_country = st.sidebar.selectbox("Country", countries, 0)
sel_device  = st.sidebar.selectbox("Device category", devices, 0)

fdf = df.copy()
if sel_cont    != "All": fdf = fdf[fdf["Continent"] == sel_cont]
if sel_country != "All": fdf = fdf[fdf["Country"] == sel_country]
if sel_device  != "All": fdf = fdf[fdf["Device category"] == sel_device]

fdf = fdf.dropna(subset=["Country", "Continent", "Device category"], how="any")

if fdf.empty:
    st.warning("No data for the current filters.")
    st.stop()

# KPI Cards
st.markdown("## Key Metrics Overview")
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Active Users", f"{fdf['Active users'].sum():,}")
col2.metric("New Users", f"{fdf['New users'].sum():,}")
col3.metric("Returning Users", f"{(fdf['Active users']-fdf['New users']).sum():,}")
col4.metric("Engagement Rate", f"{fdf['Engagement rate'].mean():.1%}")
col5.metric("Events per Session", f"{fdf['Events per session'].mean():.2f}")

# -------- NEW GEO BUBBLE MAP --------
if {"Country","Active users"}.issubset(fdf.columns):
    geo = fdf.groupby("Country", as_index=False)["Active users"].sum()
    total_users = geo["Active users"].sum()
    geo["% of Total"] = (geo["Active users"] / total_users) * 100

    fig_map = px.scatter_geo(
        geo,
        locations="Country",
        locationmode="country names",
        size="Active users",
        color="Active users",
        hover_name="Country",
        hover_data={"Active users": ":,", "% of Total": ":.2f"},
        color_continuous_scale=px.colors.sequential.Plasma,
        projection="natural earth",
        title="<b>Active Users by Country</b>"
    )
    fig_map.update_traces(marker=dict(line=dict(width=0.5, color="white")))
    fig_map.update_layout(
        margin=dict(l=10, r=10, t=50, b=10),
        title_font=dict(size=22, color="#333"),
        geo=dict(
            showland=True,
            landcolor="white",
            showcountries=True,
            countrycolor="lightgray"
        )
    )
    st.plotly_chart(fig_map, use_container_width=True)

# Top Countries Bar Chart
if not geo.empty:
    top_c = geo.sort_values("Active users", ascending=False).head(15)
    fig_bar = px.bar(
        top_c, x="Country", y="Active users",
        text="Active users", color="Active users",
        color_continuous_scale=px.colors.sequential.Viridis,
        title="<b>Top 15 Countries</b>"
    )
    fig_bar.update_traces(texttemplate="%{text:,}", textposition="outside", marker_line_color="white", marker_line_width=0.5)
    fig_bar.update_layout(
        margin=dict(l=10,r=10,t=50,b=10),
        title_font=dict(size=22, color="#333"),
        xaxis_tickangle=-30, showlegend=False
    )
    st.plotly_chart(fig_bar, use_container_width=True)

# Device Share Pie Chart
if {"Device category","Active users"}.issubset(fdf.columns):
    dev = fdf.groupby("Device category", as_index=False)["Active users"].sum()
    fig_donut = px.pie(
        dev, names="Device category", values="Active users", hole=0.45,
        color_discrete_sequence=px.colors.sequential.RdPu,
        title="<b>Device Share</b>"
    )
    fig_donut.update_traces(textposition="inside", textinfo="percent+label", pull=[0.05]*len(dev))
    fig_donut.update_layout(margin=dict(l=10,r=10,t=50,b=10))
    st.plotly_chart(fig_donut, use_container_width=True)

# -------- NEW EVENTS PER SESSION PLOT --------
if "Events per session" in fdf:
    fig_violin = px.violin(
        fdf, y="Events per session", box=True, points="all",
        color_discrete_sequence=["#E76F51"],
        title="<b>Events per Session Distribution</b>"
    )
    fig_violin.update_traces(meanline_visible=True)
    fig_violin.update_layout(
        margin=dict(l=10,r=10,t=50,b=10),
        title_font=dict(size=22),
        yaxis_title="Events per Session"
    )
    st.plotly_chart(fig_violin, use_container_width=True)

# Engagement Rate vs Events per Session Scatter
if {"Engagement rate","Events per session"}.issubset(fdf.columns):
    fig_scatter = px.scatter(
        fdf, x="Engagement rate", y="Events per session",
        size="Active users", color="Device category",
        hover_data=["Country","Continent"],
        trendline="ols", trendline_color_override="gray",
        color_discrete_sequence=px.colors.qualitative.Bold,
        title="<b>Engagement vs Events per Session</b>"
    )
    fig_scatter.update_traces(marker=dict(opacity=0.8, line=dict(width=1, color='white')))
    fig_scatter.update_layout(
        margin=dict(l=10,r=10,t=50,b=10),
        title_font=dict(size=22),
        xaxis_title="Engagement Rate (%)",
        yaxis_title="Events per Session"
    )
    st.plotly_chart(fig_scatter, use_container_width=True)

# for col in ["d1_retention", "d7_retention", "d28_retention", "Engaged sessions rate"]:
    if col not in fdf.columns:
        fdf[col] = np.nan

ret_vals = {
    "Day 1 Retention": np.nanmean(fdf["d1_retention"]),
    "Day 7 Retention": np.nanmean(fdf["d7_retention"]),
    "Day 28 Retention": np.nanmean(fdf["d28_retention"]),
    "Engaged Sessions Rate": np.nanmean(fdf["Engaged sessions rate"]),
}

ret_df = pd.DataFrame({"Metric": list(ret_vals.keys()), "Value": list(ret_vals.values())})
ret_df["Value"] = np.where(ret_df["Value"] <= 1, ret_df["Value"], ret_df["Value"] / 100.0)
ret_df = ret_df.sort_values("Value", ascending=True)

fig_ret = px.bar(
    ret_df,
    x="Value",
    y="Metric",
    orientation="h",
    text=ret_df["Value"].apply(lambda v: f"{v:.1%}"),
    color="Value",
    color_continuous_scale=px.colors.sequential.Tealgrn,
    title="<b>Retention & Engagement Metrics</b>"
)
fig_ret.update_traces(textposition="inside", insidetextanchor="middle")
fig_ret.update_xaxes(tickformat=".0%", range=[0, 1])
fig_ret.update_layout(
    margin=dict(l=10, r=10, t=50, b=10),
    title_font=dict(size=22),
    showlegend=False,
    yaxis_title="",
    xaxis_title="Rate"
)
st.plotly_chart(fig_ret, use_container_width=True)

