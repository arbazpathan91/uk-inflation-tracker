import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests

st.set_page_config(
    page_title="Global Inflation Tracker",
    page_icon="🌍",
    layout="wide"
)

st.markdown("""
<style>
[data-testid="stAppViewContainer"] { background-color: #0a0e1a; }
[data-testid="stSidebar"] { background-color: #111827; }
div[data-testid="stMetric"] {
    background: #111827;
    border: 1px solid #1f2937;
    border-radius: 12px;
    padding: 16px;
}
h1 { background: linear-gradient(90deg, #60a5fa, #a78bfa, #f472b6); 
     -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
</style>
""", unsafe_allow_html=True)

st.title("🌍 Global Inflation Tracker")
st.caption("UK · USA · Eurozone · India · China · Brazil — World Bank open data")

COUNTRIES = {
    "🇬🇧 United Kingdom": "GB",
    "🇺🇸 United States":  "US",
    "🇪🇺 Eurozone":       "XC",
    "🇮🇳 India":          "IN",
    "🇨🇳 China":          "CN",
    "🇧🇷 Brazil":         "BR",
}

COLORS = {
    "🇬🇧 United Kingdom": "#3b82f6",
    "🇺🇸 United States":  "#f43f5e",
    "🇪🇺 Eurozone":       "#f59e0b",
    "🇮🇳 India":          "#10b981",
    "🇨🇳 China":          "#a78bfa",
    "🇧🇷 Brazil":         "#fb923c",
}

@st.cache_data(ttl=86400, show_spinner=False)
def fetch_inflation(country_code):
    """World Bank API — CPI inflation annual %"""
    url = (
        f"https://api.worldbank.org/v2/country/{country_code}"
        f"/indicator/FP.CPI.TOTL.ZG?format=json&per_page=30&mrv=30"
    )
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        raw = r.json()
        if len(raw) < 2 or not raw[1]:
            return None
        rows = [
            {"year": int(d["date"]), "value": d["value"]}
            for d in raw[1] if d["value"] is not None
        ]
        df = pd.DataFrame(rows).sort_values("year").reset_index(drop=True)
        return df
    except:
        return None

# --- Sidebar ---
with st.sidebar:
    st.header("⚙️ Settings")
    selected = st.multiselect(
        "Countries",
        options=list(COUNTRIES.keys()),
        default=list(COUNTRIES.keys())
    )
    year_min, year_max = st.slider(
        "Year range", 1995, 2024, (2005, 2024)
    )
    st.markdown("---")
    st.caption("Data: World Bank Open Data")
    st.caption("Indicator: FP.CPI.TOTL.ZG")
    st.caption("License: CC BY 4.0")

# --- Fetch ---
with st.spinner("Loading World Bank data..."):
    all_data = {}
    for label in selected:
        code = COUNTRIES[label]
        df = fetch_inflation(code)
        if df is not None:
            df["country"] = label
            all_data[label] = df

if not all_data:
    st.error("Could not load data. Check your connection.")
    st.stop()

# --- KPI Row ---
st.markdown("### 📊 Latest Annual Inflation Rate")
cols = st.columns(len(all_data))
for i, (label, df) in enumerate(all_data.items()):
    latest = df[df["year"] <= year_max].iloc[-1]
    prev   = df[df["year"] <= year_max].iloc[-2]
    delta  = latest["value"] - prev["value"]
    with cols[i]:
        st.metric(
            label,
            f"{latest['value']:.1f}%",
            f"{delta:+.1f}pp vs prior year"
        )

st.markdown("---")

# --- Line chart ---
st.subheader("📈 Inflation Over Time")

combined = pd.concat(all_data.values())
combined = combined[combined["year"].between(year_min, year_max)]

fig = go.Figure()
for label, df in all_data.items():
    df_f = df[df["year"].between(year_min, year_max)]
    fig.add_trace(go.Scatter(
        x=df_f["year"],
        y=df_f["value"],
        name=label,
        mode="lines+markers",
        line=dict(color=COLORS.get(label, "#ffffff"), width=2.5),
        marker=dict(size=5),
        hovertemplate=f"{label}<br>%{{x}}: %{{y:.1f}}%<extra></extra>"
    ))

fig.add_hline(y=2.0, line_dash="dot", line_color="rgba(255,255,255,0.2)",
              annotation_text="2% target", annotation_position="top left",
              annotation_font_color="rgba(255,255,255,0.4)")

fig.update_layout(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    height=420,
    margin=dict(l=0, r=0, t=10, b=0),
    yaxis_title="Inflation Rate (%)",
    xaxis_title="",
    hovermode="x unified",
    legend=dict(orientation="h", yanchor="bottom", y=1.02,
                bgcolor="rgba(0,0,0,0)")
)
st.plotly_chart(fig, use_container_width=True)

# --- Bar chart: latest snapshot ---
c1, c2 = st.columns(2)

with c1:
    st.subheader("🏆 Latest Ranking")
    snapshot = []
    for label, df in all_data.items():
        latest = df[df["year"] <= year_max].iloc[-1]
        snapshot.append({"Country": label, "Rate (%)": round(latest["value"], 2),
                         "Year": int(latest["year"])})
    snap_df = pd.DataFrame(snapshot).sort_values("Rate (%)", ascending=True)

    fig3 = px.bar(
        snap_df, x="Rate (%)", y="Country",
        orientation="h",
        color="Rate (%)",
        color_continuous_scale=["#10b981", "#f59e0b", "#f43f5e"],
        text="Rate (%)",
        template="plotly_dark"
    )
    fig3.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
    fig3.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        coloraxis_showscale=False,
        height=320,
        margin=dict(l=0, r=60, t=10, b=0)
    )
    st.plotly_chart(fig3, use_container_width=True)

with c2:
    st.subheader("📉 Peak Inflation (selected period)")
    peaks = []
    for label, df in all_data.items():
        df_f = df[df["year"].between(year_min, year_max)]
        peak_row = df_f.loc[df_f["value"].idxmax()]
        peaks.append({
            "Country": label,
            "Peak (%)": round(peak_row["value"], 1),
            "Year": int(peak_row["year"])
        })
    peak_df = pd.DataFrame(peaks).sort_values("Peak (%)", ascending=False)

    fig4 = px.bar(
        peak_df, x="Country", y="Peak (%)",
        color="Peak (%)",
        color_continuous_scale=["#f59e0b", "#f43f5e"],
        text="Peak (%)",
        template="plotly_dark"
    )
    fig4.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
    fig4.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        coloraxis_showscale=False,
        height=320,
        margin=dict(l=0, r=0, t=10, b=0),
        xaxis_tickangle=-20
    )
    st.plotly_chart(fig4, use_container_width=True)

# --- Purchasing power ---
st.markdown("---")
st.subheader("🧮 Purchasing Power Erosion")

pc1, pc2, pc3 = st.columns(3)
with pc1:
    pp_amount = st.number_input("Amount", min_value=100.0, value=10000.0, step=500.0)
with pc2:
    pp_country = st.selectbox("Country", options=list(all_data.keys()))
with pc3:
    pp_since = st.number_input("Since year", min_value=year_min, max_value=year_max-1, value=2019)

df_pp = all_data[pp_country]
df_pp_range = df_pp[df_pp["year"].between(pp_since, year_max)]

if len(df_pp_range) >= 2:
    cumulative = 1.0
    for _, row in df_pp_range.iterrows():
        cumulative *= (1 + row["value"] / 100)
    real_value = pp_amount / cumulative
    lost = pp_amount - real_value

    m1, m2, m3 = st.columns(3)
    with m1:
        st.metric("Original value", f"{pp_amount:,.0f}")
    with m2:
        st.metric("Real value today", f"{real_value:,.0f}", f"-{lost:,.0f}")
    with m3:
        st.metric("Purchasing power lost", f"{(lost/pp_amount)*100:.1f}%")

st.markdown("---")
st.caption("World Bank Open Data · CC BY 4.0 · Built with Streamlit & Plotly")