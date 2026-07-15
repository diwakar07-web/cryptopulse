import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
import plotly.express as px

# --- PAGE CONFIG ---
st.set_page_config(page_title="CryptoPulse Analytics", page_icon="⚡", layout="wide", initial_sidebar_state="collapsed")

# --- PREMIUM CSS INJECTION ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&display=swap');
    
    /* Global Font & Background */
    html, body, [class*="css"] {
        font-family: 'Outfit', sans-serif !important;
    }
    
    .stApp {
        background: radial-gradient(circle at 15% 50%, #0d1117, #000000);
        color: #e6edf3;
    }

    /* Glassmorphism Cards for Metrics */
    [data-testid="metric-container"] {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        border-radius: 16px;
        padding: 20px;
        transition: transform 0.3s ease, box-shadow 0.3s ease, border-color 0.3s ease;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    
    [data-testid="metric-container"]:hover {
        transform: translateY(-5px);
        box-shadow: 0 10px 20px rgba(0, 198, 255, 0.15);
        border-color: rgba(0, 198, 255, 0.3);
    }

    /* Fix Metric Text Truncation & Styling */
    [data-testid="stMetricValue"] {
        font-size: 1.8rem !important;
        font-weight: 800 !important;
        background: -webkit-linear-gradient(45deg, #00c6ff, #0072ff);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        white-space: normal !important; 
        word-wrap: break-word !important;
        line-height: 1.2 !important;
    }
    
    [data-testid="stMetricLabel"] {
        font-size: 1rem !important;
        color: #8b949e !important;
        font-weight: 600 !important;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 8px;
    }

    /* Headers */
    h1, h2, h3 {
        font-weight: 800 !important;
        background: -webkit-linear-gradient(45deg, #ffffff, #a5b4fc);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    
    .header-subtitle {
        color: #8b949e;
        font-size: 1.1rem;
        font-weight: 300;
        margin-top: -15px;
        margin-bottom: 30px;
        letter-spacing: 0.5px;
    }

    /* Table Styling */
    .stDataFrame {
        border-radius: 12px;
        overflow: hidden;
        border: 1px solid rgba(255,255,255,0.05);
    }
    
    /* Adjust spacing */
    .block-container {
        padding-top: 2rem !important;
        max-width: 95% !important;
    }
</style>
""", unsafe_allow_html=True)

st.markdown("<h1>⚡ CryptoPulse Analytics Engine</h1>", unsafe_allow_html=True)
st.markdown("<p class='header-subtitle'>Live Data Engineering Pipeline • Powered by Apache Airflow & PostgreSQL</p>", unsafe_allow_html=True)

# --- DATABASE CONNECTION ---
@st.cache_resource
def get_connection():
    return create_engine("postgresql://cryptopulse:cryptopulse_secret@localhost:5433/cryptopulse")

engine = get_connection()

# --- LOAD DATA ---
@st.cache_data(ttl=60)
def load_data(query):
    with engine.connect() as conn:
        return pd.read_sql(text(query), conn)

try:
    # --- TOP LEVEL METRICS ---
    market_overview = load_data("SELECT * FROM analytics_market_overview ORDER BY snapshot_date DESC LIMIT 1")
    sentiment = load_data("SELECT * FROM analytics_sentiment ORDER BY snapshot_date DESC LIMIT 1")

    if not market_overview.empty:
        col1, col2, col3, col4, col5 = st.columns(5)
        m = market_overview.iloc[0]
        
        # Format large numbers neatly
        def format_billions(val):
            return f"${val / 1e9:.2f}B" if val >= 1e9 else f"${val / 1e6:.2f}M"

        col1.metric("Total Market Cap", format_billions(m['total_market_cap']))
        col2.metric("24h Volume", format_billions(m['total_volume']))
        col3.metric("BTC Price", f"${m['btc_price']:,.0f}")
        col4.metric("BTC Dominance", f"{m['btc_dominance']}%")
        
        if not sentiment.empty:
            s = sentiment.iloc[0]
            # Emoji based on sentiment
            emoji = "😨" if s['avg_index'] < 40 else "🚀" if s['avg_index'] > 60 else "😐"
            col5.metric("Fear & Greed", f"{s['avg_index']}/100 {emoji}")
    
    st.markdown("<br><br>", unsafe_allow_html=True)

    # --- MAIN CONTENT GRID ---
    colA, colB = st.columns([1.8, 1.2], gap="large")

    with colA:
        st.markdown("### 🏆 Top Assets by Market Cap")
        coin_summary = load_data("""
            SELECT coin_name, symbol, latest_price as "Price", price_change_24h as "24h %", 
                   market_cap as "Market Cap", rolling_avg_7d as "7D Avg"
            FROM analytics_coin_summary 
            WHERE snapshot_date = CURRENT_DATE
            ORDER BY market_cap DESC LIMIT 12
        """)
        
        if not coin_summary.empty:
            st.dataframe(
                coin_summary.style.format({
                    "Price": "${:,.2f}", 
                    "Market Cap": "${:,.0f}", 
                    "7D Avg": "${:,.2f}",
                    "24h %": "{:+.2f}%"
                }).map(lambda x: 'color: #00ff88; font-weight: bold;' if x > 0 else 'color: #ff3366; font-weight: bold;', subset=['24h %']),
                use_container_width=True,
                hide_index=True,
                height=450
            )

    with colB:
        st.markdown("### 🚀 Top Movers (24h)")
        gainers = load_data("SELECT symbol, price_change_24h FROM analytics_top_gainers WHERE snapshot_date = CURRENT_DATE LIMIT 5")
        losers = load_data("SELECT symbol, price_change_24h FROM analytics_top_losers WHERE snapshot_date = CURRENT_DATE LIMIT 5")
        
        # Custom Plotly Theme
        layout_updates = dict(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(family="Outfit", color="#8b949e"),
            margin=dict(l=0, r=0, t=0, b=20),
            height=200,
            xaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)', title=""),
            yaxis=dict(title="")
        )

        if not gainers.empty:
            st.markdown("<p style='color:#00ff88; font-weight:600; margin-bottom:0;'>Top Gainers</p>", unsafe_allow_html=True)
            fig_gainers = px.bar(gainers, x="price_change_24h", y="symbol", orientation='h')
            fig_gainers.update_traces(marker_color='rgba(0, 255, 136, 0.7)', marker_line_color='#00ff88', marker_line_width=1.5)
            fig_gainers.update_layout(**layout_updates)
            st.plotly_chart(fig_gainers, use_container_width=True, config={'displayModeBar': False})
            
        st.markdown("<br>", unsafe_allow_html=True)

        if not losers.empty:
            st.markdown("<p style='color:#ff3366; font-weight:600; margin-bottom:0;'>Top Losers</p>", unsafe_allow_html=True)
            fig_losers = px.bar(losers, x="price_change_24h", y="symbol", orientation='h')
            fig_losers.update_traces(marker_color='rgba(255, 51, 102, 0.7)', marker_line_color='#ff3366', marker_line_width=1.5)
            fig_losers.update_layout(**layout_updates)
            st.plotly_chart(fig_losers, use_container_width=True, config={'displayModeBar': False})
        else:
            st.info("🟢 No top losers today! The entire tracked market is in the green.")

except Exception as e:
    st.error(f"Waiting for pipeline to finish initial load... \n\nError details: {e}")

st.markdown("""
    <div style='text-align: center; margin-top: 50px; color: #8b949e; font-size: 0.9rem;'>
        Auto-refreshes every 60 seconds • Data processed by Airflow
    </div>
""", unsafe_allow_html=True)
