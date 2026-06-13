import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import numpy as np

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
st.caption("UK · USA · Eurozone · India · China · Brazil — World Bank open data · Annual CPI, updated as published")

COUNTRIES = {
    "🇬🇧 United Kingdom": "GB",
    "🇺🇸 United States":  "US",
    "🇩🇪 Germany":        "DE",
    "🇮🇳 India":          "IN",
    "🇨🇳 China":          "CN",
    "🇧🇷 Brazil":         "BR",
}

COLORS = {
    "🇬🇧 United Kingdom": "#3b82f6",
    "🇺🇸 United States":  "#f43f5e",
    "🇩🇪 Germany":        "#f59e0b",
    "🇮🇳 India":          "#10b981",
    "🇨🇳 China":          "#a78bfa",
    "🇧🇷 Brazil":         "#fb923c",
}

POLICY_RATES_2024 = {
    "🇬🇧 United Kingdom": 5.25,
    "🇺🇸 United States":  5.50,
    "🇩🇪 Germany":        4.50,
    "🇮🇳 India":          6.50,
    "🇨🇳 China":          3.45,
    "🇧🇷 Brazil":         10.50,
}

@st.cache_data(ttl=86400, show_spinner=False)
def fetch_inflation(country_code):
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
    year_min, year_max = st.slider("Year range", 1995, 2024, (2005, 2024))
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

# =============================================
# ORIGINAL CHARTS
# =============================================

st.subheader("📈 Inflation Over Time")
combined = pd.concat(all_data.values())
combined = combined[combined["year"].between(year_min, year_max)]

fig = go.Figure()
for label, df in all_data.items():
    df_f = df[df["year"].between(year_min, year_max)]
    fig.add_trace(go.Scatter(
        x=df_f["year"], y=df_f["value"],
        name=label, mode="lines+markers",
        line=dict(color=COLORS.get(label, "#ffffff"), width=2.5),
        marker=dict(size=5),
        hovertemplate=f"{label}<br>%{{x}}: %{{y:.1f}}%<extra></extra>"
    ))
fig.add_hline(y=2.0, line_dash="dot", line_color="rgba(255,255,255,0.2)",
              annotation_text="2% target", annotation_position="top left",
              annotation_font_color="rgba(255,255,255,0.4)")
fig.update_layout(
    template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)", height=420,
    margin=dict(l=0, r=0, t=10, b=0),
    yaxis_title="Inflation Rate (%)",
    hovermode="x unified",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, bgcolor="rgba(0,0,0,0)")
)
st.plotly_chart(fig, use_container_width=True)

c1, c2 = st.columns(2)

with c1:
    st.subheader("🏆 Latest Ranking")
    snapshot = []
    for label, df in all_data.items():
        latest = df[df["year"] <= year_max].iloc[-1]
        snapshot.append({"Country": label, "Rate (%)": round(latest["value"], 2),
                         "Year": int(latest["year"])})
    snap_df = pd.DataFrame(snapshot).sort_values("Rate (%)", ascending=True)
    fig3 = px.bar(snap_df, x="Rate (%)", y="Country", orientation="h",
                  color="Rate (%)", color_continuous_scale=["#10b981", "#f59e0b", "#f43f5e"],
                  text="Rate (%)", template="plotly_dark")
    fig3.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
    fig3.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                       coloraxis_showscale=False, height=320,
                       margin=dict(l=0, r=60, t=10, b=0))
    st.plotly_chart(fig3, use_container_width=True)

with c2:
    st.subheader("📉 Peak Inflation (selected period)")
    peaks = []
    for label, df in all_data.items():
        df_f = df[df["year"].between(year_min, year_max)]
        peak_row = df_f.loc[df_f["value"].idxmax()]
        peaks.append({"Country": label, "Peak (%)": round(peak_row["value"], 1),
                      "Year": int(peak_row["year"])})
    peak_df = pd.DataFrame(peaks).sort_values("Peak (%)", ascending=False)
    fig4 = px.bar(peak_df, x="Country", y="Peak (%)",
                  color="Peak (%)", color_continuous_scale=["#f59e0b", "#f43f5e"],
                  text="Peak (%)", template="plotly_dark")
    fig4.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
    fig4.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                       coloraxis_showscale=False, height=320,
                       margin=dict(l=0, r=0, t=10, b=0), xaxis_tickangle=-20)
    st.plotly_chart(fig4, use_container_width=True)

st.markdown("---")

# =============================================
# INSIGHT 1 — Years to halve your money
# =============================================
st.subheader("⏳ Insight 1 — Years to Halve Your Savings")
st.caption("At each country's latest inflation rate, how long until purchasing power drops 50%? (Rule of 70)")

halve_rows = []
for label, df in all_data.items():
    latest_rate = df[df["year"] <= year_max].iloc[-1]["value"]
    if latest_rate > 0:
        years = round(70 / latest_rate, 1)
    else:
        years = None
    halve_rows.append({"Country": label, "Current Rate (%)": round(latest_rate, 1),
                       "Years to Halve": years})

halve_df = pd.DataFrame(halve_rows).sort_values("Years to Halve")

fig_h = px.bar(
    halve_df, x="Country", y="Years to Halve",
    color="Years to Halve",
    color_continuous_scale=["#f43f5e", "#f59e0b", "#10b981"],
    text="Years to Halve",
    template="plotly_dark",
    hover_data=["Current Rate (%)"]
)
fig_h.update_traces(texttemplate="%{text}yrs", textposition="outside")
fig_h.update_layout(
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    coloraxis_showscale=False, height=350,
    margin=dict(l=0, r=0, t=10, b=0)
)
st.plotly_chart(fig_h, use_container_width=True)

h1, h2 = st.columns(2)
with h1:
    fastest = halve_df.iloc[0]
    st.error(f"🚨 **{fastest['Country']}** halves savings fastest — in just **{fastest['Years to Halve']} years** at {fastest['Current Rate (%)']}% inflation")
with h2:
    slowest = halve_df.dropna().iloc[-1]
    st.success(f"✅ **{slowest['Country']}** is safest — takes **{slowest['Years to Halve']} years** to halve at {slowest['Current Rate (%)']}% inflation")

st.markdown("---")

# =============================================
# INSIGHT 2 — Who recovered fastest post-2022
# =============================================
st.subheader("🚀 Insight 2 — Who Recovered Fastest from the 2022 Spike?")
st.caption("Rate of disinflation: percentage points dropped per year from peak to latest")

recovery_rows = []
for label, df in all_data.items():
    df_post = df[df["year"] >= 2020]
    if len(df_post) < 2:
        continue
    peak_idx = df_post["value"].idxmax()
    peak_val = df_post.loc[peak_idx, "value"]
    peak_year = df_post.loc[peak_idx, "year"]
    latest_val = df_post.iloc[-1]["value"]
    latest_year = df_post.iloc[-1]["year"]
    years_elapsed = latest_year - peak_year
    if years_elapsed > 0:
        rate_of_drop = round((peak_val - latest_val) / years_elapsed, 2)
    else:
        rate_of_drop = 0
    recovery_rows.append({
        "Country": label,
        "Peak (%)": round(peak_val, 1),
        "Peak Year": int(peak_year),
        "Latest (%)": round(latest_val, 1),
        "Drop (pp/yr)": rate_of_drop
    })

rec_df = pd.DataFrame(recovery_rows).sort_values("Drop (pp/yr)", ascending=False)

fig_r = px.bar(
    rec_df, x="Country", y="Drop (pp/yr)",
    color="Drop (pp/yr)",
    color_continuous_scale=["#f43f5e", "#10b981"],
    text="Drop (pp/yr)",
    template="plotly_dark",
    hover_data=["Peak (%)", "Peak Year", "Latest (%)"]
)
fig_r.update_traces(texttemplate="%{text:.1f}pp/yr", textposition="outside")
fig_r.update_layout(
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    coloraxis_showscale=False, height=350,
    margin=dict(l=0, r=0, t=10, b=0)
)
st.plotly_chart(fig_r, use_container_width=True)

if not rec_df.empty:
    winner = rec_df.iloc[0]
    loser  = rec_df.iloc[-1]
    r1, r2 = st.columns(2)
    with r1:
        st.success(f"🏆 **{winner['Country']}** recovered fastest — dropped **{winner['Drop (pp/yr)']}pp per year** from its {winner['Peak Year']} peak of {winner['Peak (%)']}%")
    with r2:
        st.warning(f"🐢 **{loser['Country']}** slowest to recover — only **{loser['Drop (pp/yr)']}pp per year** from peak")

st.markdown("---")

# =============================================
# INSIGHT 3 — Winner/Loser vs G20 average
# =============================================
st.subheader("🎯 Insight 3 — Above or Below G20 Average?")
st.caption("Each country vs the G20 average inflation rate per year")

all_combined = pd.concat(all_data.values())
all_combined = all_combined[all_combined["year"].between(year_min, year_max)]
g20_avg = all_combined.groupby("year")["value"].mean().reset_index()
g20_avg.columns = ["year", "g20_avg"]

fig_g = go.Figure()
fig_g.add_trace(go.Scatter(
    x=g20_avg["year"], y=g20_avg["g20_avg"],
    name="Selected Average", mode="lines",
    line=dict(color="rgba(255,255,255,0.4)", width=2, dash="dash"),
))
for label, df in all_data.items():
    df_f = df[df["year"].between(year_min, year_max)].merge(g20_avg, on="year")
    df_f["vs_avg"] = df_f["value"] - df_f["g20_avg"]
    fig_g.add_trace(go.Scatter(
        x=df_f["year"], y=df_f["vs_avg"],
        name=label, mode="lines+markers",
        line=dict(color=COLORS.get(label, "#ffffff"), width=2),
        marker=dict(size=4),
        hovertemplate=f"{label}<br>%{{x}}: %{{y:+.1f}}pp vs avg<extra></extra>"
    ))
fig_g.add_hline(y=0, line_color="rgba(255,255,255,0.2)", line_dash="solid")
fig_g.update_layout(
    template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)", height=400,
    margin=dict(l=0, r=0, t=10, b=0),
    yaxis_title="pp above/below average",
    hovermode="x unified",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, bgcolor="rgba(0,0,0,0)")
)
st.plotly_chart(fig_g, use_container_width=True)

st.markdown("---")

# =============================================
# INSIGHT 4 — The Lost Decade
# =============================================
st.subheader("💸 Insight 4 — The Lost Decade")
st.caption("Cumulative purchasing power lost since 2010 — what is £/$/₹10,000 actually worth today?")

lost_col1, lost_col2 = st.columns([1, 2])

with lost_col1:
    start_amount = st.number_input("Starting amount", min_value=1000.0,
                                   value=10000.0, step=1000.0)
    since_year   = st.number_input("Since year", min_value=2000,
                                   max_value=2020, value=2010)

lost_rows = []
for label, df in all_data.items():
    df_range = df[df["year"].between(since_year, year_max)]
    cumulative = 1.0
    for _, row in df_range.iterrows():
        cumulative *= (1 + row["value"] / 100)
    real_value = start_amount / cumulative
    lost = start_amount - real_value
    lost_rows.append({
        "Country": label,
        "Real Value Today": round(real_value, 0),
        "Lost": round(lost, 0),
        "Lost (%)": round((lost / start_amount) * 100, 1)
    })

lost_df = pd.DataFrame(lost_rows).sort_values("Lost (%)", ascending=False)

with lost_col2:
    fig_l = go.Figure()
    fig_l.add_trace(go.Bar(
        x=lost_df["Country"],
        y=lost_df["Real Value Today"],
        name="Real Value",
        marker_color="#3b82f6",
        text=lost_df["Real Value Today"].apply(lambda x: f"{x:,.0f}"),
        textposition="inside"
    ))
    fig_l.add_trace(go.Bar(
        x=lost_df["Country"],
        y=lost_df["Lost"],
        name="Lost to Inflation",
        marker_color="#f43f5e",
        text=lost_df["Lost (%)"].apply(lambda x: f"-{x}%"),
        textposition="inside"
    ))
    fig_l.update_layout(
        barmode="stack",
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=360,
        margin=dict(l=0, r=0, t=10, b=0),
        yaxis_title=f"Value of {start_amount:,.0f}",
        legend=dict(orientation="h", yanchor="bottom", y=1.02,
                    bgcolor="rgba(0,0,0,0)")
    )
    st.plotly_chart(fig_l, use_container_width=True)

worst = lost_df.iloc[0]
best  = lost_df.iloc[-1]
d1, d2 = st.columns(2)
with d1:
    st.error(f"🔥 **{worst['Country']}** — {start_amount:,.0f} is now worth just **{worst['Real Value Today']:,.0f}** in real terms. Lost **{worst['Lost (%)']:.1f}%** since {since_year}")
with d2:
    st.success(f"✅ **{best['Country']}** — best preserver of value. {start_amount:,.0f} still worth **{best['Real Value Today']:,.0f}**. Only lost **{best['Lost (%)']:.1f}%**")

st.markdown("---")

# =============================================
# INSIGHT 5 — Interest rate vs inflation gap
# =============================================
st.subheader("🏦 Insight 5 — Are Central Banks Actually Winning?")
st.caption("Real interest rate = Policy rate minus inflation. Positive = central bank ahead. Negative = still losing.")

real_rate_rows = []
for label, df in all_data.items():
    latest_inflation = df[df["year"] <= year_max].iloc[-1]["value"]
    policy_rate      = POLICY_RATES_2024.get(label, None)
    if policy_rate is not None:
        real_rate = round(policy_rate - latest_inflation, 2)
        real_rate_rows.append({
            "Country": label,
            "Policy Rate (%)": policy_rate,
            "Inflation (%)": round(latest_inflation, 1),
            "Real Rate (%)": real_rate,
            "Status": "✅ Winning" if real_rate > 0 else "❌ Losing"
        })

rr_df = pd.DataFrame(real_rate_rows).sort_values("Real Rate (%)", ascending=True)

fig_rr = go.Figure()
fig_rr.add_trace(go.Bar(
    x=rr_df["Real Rate (%)"],
    y=rr_df["Country"],
    orientation="h",
    marker_color=["#f43f5e" if v < 0 else "#10b981" for v in rr_df["Real Rate (%)"]],
    text=rr_df["Real Rate (%)"].apply(lambda x: f"{x:+.2f}%"),
    textposition="outside"
))
fig_rr.add_vline(x=0, line_color="rgba(255,255,255,0.3)", line_dash="solid")
fig_rr.update_layout(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    height=350,
    margin=dict(l=0, r=80, t=10, b=0),
    xaxis_title="Real Interest Rate (%)"
)
st.plotly_chart(fig_rr, use_container_width=True)

st.dataframe(
    rr_df[["Country", "Policy Rate (%)", "Inflation (%)", "Real Rate (%)", "Status"]],
    use_container_width=True,
    hide_index=True
)

# --- Purchasing power calculator ---
st.markdown("---")
st.subheader("🧮 Purchasing Power Calculator")
pc1, pc2, pc3 = st.columns(3)
with pc1:
    pp_amount  = st.number_input("Amount", min_value=100.0, value=10000.0, step=500.0)
with pc2:
    pp_country = st.selectbox("Country", options=list(all_data.keys()))
with pc3:
    pp_since   = st.number_input("Since year", min_value=year_min,
                                  max_value=year_max - 1, value=2019)

df_pp       = all_data[pp_country]
df_pp_range = df_pp[df_pp["year"].between(pp_since, year_max)]
if len(df_pp_range) >= 2:
    cumulative = 1.0
    for _, row in df_pp_range.iterrows():
        cumulative *= (1 + row["value"] / 100)
    real_value = pp_amount / cumulative
    lost       = pp_amount - real_value
    m1, m2, m3 = st.columns(3)
    with m1:
        st.metric("Original value", f"{pp_amount:,.0f}")
    with m2:
        st.metric("Real value today", f"{real_value:,.0f}", f"-{lost:,.0f}")
    with m3:
        st.metric("Purchasing power lost", f"{(lost / pp_amount) * 100:.1f}%")

st.markdown("---")
st.caption("World Bank Open Data · CC BY 4.0 · Built with Streamlit & Plotly")