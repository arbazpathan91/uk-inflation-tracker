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
st.caption("Live data from the Office for National Statistics (ONS)")

@st.cache_data(ttl=3600)
def fetch_timeseries(series_id):
    """Fetch from ONS stable timeseries API"""
    url = f"https://api.ons.gov.uk/v1/timeseries/{series_id}/dataset/mm23/data"
    try:
        r = requests.get(url, timeout=20)
        r.raise_for_status()
        data = r.json()
        months = data.get("months", [])
        rows = []
        for m in months:
            try:
                rows.append({
                    "date": m["date"],
                    "value": float(m["value"])
                })
            except (ValueError, KeyError):
                continue
        df = pd.DataFrame(rows)
        if df.empty:
            return None
        df["date"] = pd.to_datetime(df["date"], format="%Y %b", errors="coerce")
        df = df.dropna().sort_values("date").reset_index(drop=True)
        return df
    except Exception as e:
        return None

# Series codes from ONS MM23 dataset
SERIES = {
    "CPIH Overall":       "l55o",
    "Food & Drink":       "l55r",
    "Housing & Utilities":"l55s",
    "Energy & Fuel":      "l55t",
    "Transport":          "l55u",
    "Recreation":         "l55v",
    "Restaurants & Hotels":"l55w",
}

with st.spinner("Fetching latest ONS data..."):
    all_data = {}
    for label, code in SERIES.items():
        df = fetch_timeseries(code)
        if df is not None and not df.empty:
            df["category"] = label
            all_data[label] = df

if not all_data:
    st.error("Could not reach ONS API. Try again in a moment.")
    st.info("ONS API status: https://api.ons.gov.uk")
    st.stop()

cpih = all_data.get("CPIH Overall")

if cpih is None:
    st.error("CPIH data unavailable.")
    st.stop()

cpih_recent = cpih.tail(60)

# --- KPIs ---
latest_val = cpih_recent.iloc[-1]["value"]
prev_val   = cpih_recent.iloc[-2]["value"]
yr_ago_val = cpih_recent.iloc[-13]["value"] if len(cpih_recent) >= 13 else cpih_recent.iloc[0]["value"]
latest_date = cpih_recent.iloc[-1]["date"].strftime("%B %Y")

st.markdown(f"### 📅 Data as of {latest_date}")

k1, k2, k3, k4 = st.columns(4)
with k1:
    st.metric("CPIH Rate", f"{latest_val:.1f}%", f"{latest_val - prev_val:+.2f}% vs last month")
with k2:
    st.metric("Annual Change", f"{latest_val - yr_ago_val:+.2f}%", "vs same month last year")
with k3:
    st.metric("5yr Peak", f"{cpih_recent['value'].max():.1f}%")
with k4:
    st.metric("5yr Low", f"{cpih_recent['value'].min():.1f}%")

st.markdown("---")

# --- Main chart ---
st.subheader("📈 CPIH Rate — Last 5 Years")
fig = go.Figure()
fig.add_trace(go.Scatter(
    x=cpih_recent["date"],
    y=cpih_recent["value"],
    mode="lines",
    line=dict(color="#58a6ff", width=2.5),
    fill="tozeroy",
    fillcolor="rgba(88,166,255,0.08)",
    name="CPIH"
))
fig.add_hline(y=2.0, line_dash="dash", line_color="#f78166",
              annotation_text="BoE 2% target", annotation_position="top left")
fig.update_layout(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    height=360,
    margin=dict(l=0, r=0, t=10, b=0),
    yaxis_title="Rate (%)",
    hovermode="x unified"
)
st.plotly_chart(fig, use_container_width=True)

# --- Category comparison ---
st.subheader("🛒 Inflation by Category")

with st.sidebar:
    st.header("⚙️ Filters")
    selected = st.multiselect(
        "Categories",
        options=list(all_data.keys()),
        default=list(all_data.keys())
    )
    window = st.selectbox("Time window", ["12 months", "24 months", "36 months", "5 years"], index=1)

months_map = {"12 months": 12, "24 months": 24, "36 months": 36, "5 years": 60}
cutoff = pd.Timestamp.now() - pd.DateOffset(months=months_map[window])

if selected:
    combined = pd.concat([all_data[s] for s in selected if s in all_data])
    combined = combined[combined["date"] >= cutoff]

    fig2 = px.line(
        combined, x="date", y="value", color="category",
        template="plotly_dark",
        color_discrete_sequence=px.colors.qualitative.Pastel,
        labels={"value": "Rate (%)", "date": "", "category": ""}
    )
    fig2.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=380,
        margin=dict(l=0, r=0, t=10, b=0),
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02)
    )
    st.plotly_chart(fig2, use_container_width=True)

# --- Snapshot table ---
st.subheader("📋 Category Snapshot")
rows = []
for label, df in all_data.items():
    if len(df) >= 13:
        rows.append({
            "Category": label,
            "Latest (%)": round(df.iloc[-1]["value"], 2),
            "Monthly Δ": round(df.iloc[-1]["value"] - df.iloc[-2]["value"], 2),
            "Annual Δ":  round(df.iloc[-1]["value"] - df.iloc[-13]["value"], 2),
        })

snap = pd.DataFrame(rows)

def colour(val):
    return "color: #f78166" if val > 0 else "color: #56d364"

st.dataframe(
    snap.style.applymap(colour, subset=["Monthly Δ", "Annual Δ"]),
    use_container_width=True,
    hide_index=True
)

# --- Purchasing power ---
st.markdown("---")
st.subheader("🧮 Purchasing Power Calculator")

c1, c2 = st.columns(2)
with c1:
    amount = st.number_input("Amount (£)", min_value=1.0, value=1000.0, step=50.0)
with c2:
    years_back = st.slider("Years ago", 1, 5, 2)

if len(cpih) >= years_back * 12:
    past  = cpih.iloc[-(years_back * 12)]["value"]
    now   = cpih.iloc[-1]["value"]
    real  = amount * (past / now)
    lost  = amount - real
    r1, r2, r3 = st.columns(3)
    with r1:
        st.metric("Today's equivalent", f"£{real:,.2f}")
    with r2:
        st.metric("Purchasing power lost", f"£{lost:,.2f}")
    with r3:
        st.metric("Real terms loss", f"{(lost/amount)*100:.1f}%")

st.markdown("---")
st.caption("Source: ONS MM23 dataset | Open Government Licence v3.0")