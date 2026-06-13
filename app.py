import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests

st.set_page_config(
    page_title="UK Cost of Living Tracker",
    page_icon="💷",
    layout="wide"
)

st.markdown("""
<style>
    [data-testid="stAppViewContainer"] { background-color: #0d1117; }
    [data-testid="stSidebar"] { background-color: #161b22; }
    h1, h2, h3 { color: #e6edf3; }
    .stMetric { background: #161b22; border-radius: 10px; padding: 10px; border: 1px solid #30363d; }
    .stMetric label { color: #8b949e !important; }
</style>
""", unsafe_allow_html=True)

st.title("💷 UK Inflation & Cost of Living Tracker")
st.caption("Live data from the Office for National Statistics (ONS) — updated monthly")

# ----------------------------
# ONS API — no key needed
# ----------------------------
@st.cache_data(ttl=3600)
def fetch_ons_series(series_id):
    url = f"https://api.beta.ons.gov.uk/v1/datasets/{series_id}/editions/time-series/versions/2/observations?time=*&geography=K02000001"
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        data = r.json()
        rows = []
        for obs in data.get("observations", []):
            rows.append({
                "date": obs["dimensions"]["time"]["label"],
                "value": float(obs["observation"])
            })
        df = pd.DataFrame(rows)
        df["date"] = pd.to_datetime(df["date"], format="%b-%y", errors="coerce")
        df = df.dropna().sort_values("date").reset_index(drop=True)
        return df
    except Exception as e:
        return None

@st.cache_data(ttl=3600)
def fetch_cpih():
    """CPIH - Consumer Prices Index including Housing"""
    url = "https://api.beta.ons.gov.uk/v1/timeseries/l55o/dataset/mm23/data"
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        data = r.json()
        months = data.get("months", [])
        rows = [{"date": m["date"], "value": float(m["value"])} for m in months if m.get("value")]
        df = pd.DataFrame(rows)
        df["date"] = pd.to_datetime(df["date"], format="%Y %b", errors="coerce")
        df = df.dropna().sort_values("date").tail(60).reset_index(drop=True)
        return df
    except Exception as e:
        return None

@st.cache_data(ttl=3600)
def fetch_multiple_series():
    """Fetch multiple ONS timeseries for key categories"""
    series = {
        "CPIH (Overall)": "l55o",
        "Food & Drink": "l55r",
        "Energy & Fuel": "l55t",
        "Housing & Utilities": "l55s",
        "Transport": "l55u",
        "Restaurants & Hotels": "l55w",
    }
    results = {}
    for label, code in series.items():
        url = f"https://api.beta.ons.gov.uk/v1/timeseries/{code}/dataset/mm23/data"
        try:
            r = requests.get(url, timeout=15)
            data = r.json()
            months = data.get("months", [])
            rows = [{"date": m["date"], "value": float(m["value"])} for m in months if m.get("value")]
            df = pd.DataFrame(rows)
            df["date"] = pd.to_datetime(df["date"], format="%Y %b", errors="coerce")
            df = df.dropna().sort_values("date").tail(60).reset_index(drop=True)
            df["category"] = label
            results[label] = df
        except:
            continue
    return results

# ----------------------------
# Load data
# ----------------------------
with st.spinner("Fetching latest ONS data..."):
    cpih_df = fetch_cpih()
    all_series = fetch_multiple_series()

if cpih_df is None or cpih_df.empty:
    st.error("Could not load ONS data. The API may be temporarily unavailable — try refreshing.")
    st.stop()

# ----------------------------
# KPI Row
# ----------------------------
latest = cpih_df.iloc[-1]
prev = cpih_df.iloc[-2]
year_ago = cpih_df.iloc[-13] if len(cpih_df) >= 13 else cpih_df.iloc[0]

current_rate = latest["value"]
monthly_change = latest["value"] - prev["value"]
annual_change = latest["value"] - year_ago["value"]

k1, k2, k3, k4 = st.columns(4)
with k1:
    st.metric(
        "CPIH Rate (Latest)",
        f"{current_rate:.1f}%",
        delta=f"{monthly_change:+.2f}% vs last month"
    )
with k2:
    st.metric(
        "Annual Change",
        f"{annual_change:+.2f}%",
        delta="vs same month last year"
    )
with k3:
    peak = cpih_df["value"].max()
    st.metric("Peak (5yr)", f"{peak:.1f}%")
with k4:
    low = cpih_df["value"].min()
    st.metric("Low (5yr)", f"{low:.1f}%")

st.markdown("---")

# ----------------------------
# Main CPIH chart
# ----------------------------
st.subheader("📈 CPIH Inflation Rate — Last 5 Years")

fig = go.Figure()
fig.add_trace(go.Scatter(
    x=cpih_df["date"],
    y=cpih_df["value"],
    mode="lines",
    name="CPIH",
    line=dict(color="#58a6ff", width=2.5),
    fill="tozeroy",
    fillcolor="rgba(88, 166, 255, 0.08)"
))
fig.add_hline(
    y=2.0, line_dash="dash",
    line_color="#f78166",
    annotation_text="BoE Target 2%",
    annotation_position="top left"
)
fig.update_layout(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    height=380,
    margin=dict(l=0, r=0, t=10, b=0),
    yaxis_title="Inflation Rate (%)",
    hovermode="x unified"
)
st.plotly_chart(fig, use_container_width=True)

# ----------------------------
# Category breakdown
# ----------------------------
st.subheader("🛒 Inflation by Category")

if all_series:
    combined = pd.concat(all_series.values(), ignore_index=True)
    
    # Sidebar filter
    with st.sidebar:
        st.header("⚙️ Filters")
        selected = st.multiselect(
            "Categories",
            options=list(all_series.keys()),
            default=list(all_series.keys())
        )
        show_from = st.selectbox(
            "Show last",
            ["12 months", "24 months", "36 months", "All (5yr)"],
            index=1
        )
    
    months_map = {"12 months": 12, "24 months": 24, "36 months": 36, "All (5yr)": 60}
    n_months = months_map[show_from]
    
    filtered = combined[combined["category"].isin(selected)]
    cutoff = pd.Timestamp.now() - pd.DateOffset(months=n_months)
    filtered = filtered[filtered["date"] >= cutoff]
    
    fig2 = px.line(
        filtered,
        x="date", y="value",
        color="category",
        template="plotly_dark",
        color_discrete_sequence=px.colors.qualitative.Pastel,
        labels={"value": "Rate (%)", "date": "", "category": ""}
    )
    fig2.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=400,
        margin=dict(l=0, r=0, t=10, b=0),
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02)
    )
    st.plotly_chart(fig2, use_container_width=True)

# ----------------------------
# Latest snapshot table
# ----------------------------
st.subheader("📋 Latest Snapshot by Category")

if all_series:
    snapshot_rows = []
    for label, df in all_series.items():
        if len(df) >= 13:
            latest_val = df.iloc[-1]["value"]
            prev_val = df.iloc[-2]["value"]
            yr_ago_val = df.iloc[-13]["value"]
            snapshot_rows.append({
                "Category": label,
                "Latest Rate (%)": round(latest_val, 2),
                "Monthly Δ": round(latest_val - prev_val, 2),
                "Annual Δ": round(latest_val - yr_ago_val, 2),
            })
    
    snap_df = pd.DataFrame(snapshot_rows)
    
    def color_delta(val):
        color = "#f78166" if val > 0 else "#56d364"
        return f"color: {color}"
    
    styled = snap_df.style.applymap(color_delta, subset=["Monthly Δ", "Annual Δ"])
    st.dataframe(styled, use_container_width=True, hide_index=True)

# ----------------------------
# Purchasing power calculator
# ----------------------------
st.markdown("---")
st.subheader("🧮 Purchasing Power Calculator")
st.caption("How much has £X from a past month lost in real value?")

col1, col2 = st.columns(2)
with col1:
    amount = st.number_input("Amount (£)", min_value=1.0, value=1000.0, step=50.0)
with col2:
    years_back = st.slider("Years ago", 1, 5, 2)

if len(cpih_df) >= years_back * 12:
    past_rate = cpih_df.iloc[-(years_back * 12)]["value"]
    current = cpih_df.iloc[-1]["value"]
    real_value = amount * (past_rate / current) * 100 / 100
    lost = amount - real_value
    
    r1, r2, r3 = st.columns(3)
    with r1:
        st.metric(f"£{amount:,.0f} in today's money", f"£{real_value:,.2f}")
    with r2:
        st.metric("Purchasing power lost", f"£{lost:,.2f}")
    with r3:
        pct = (lost / amount) * 100
        st.metric("Real terms loss", f"{pct:.1f}%")

# ----------------------------
# Footer
# ----------------------------
st.markdown("---")
st.caption("Source: Office for National Statistics (ONS) | Open Government Licence v3.0 | Data updates monthly")
st.caption("Series: MM23 dataset — CPIH and category sub-indices")