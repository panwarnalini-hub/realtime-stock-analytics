import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import sys
import os
import time

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))
from stock_fetcher import StockFetcher

# Import config
try:
    # Try Streamlit secrets first (for cloud deployment)
    API_KEY = st.secrets["API_KEY"]
except (KeyError, FileNotFoundError):
    # Fall back to config.py for local development
    try:
        sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
        from config import API_KEY
    except ImportError:
        st.error("Please create config.py with your API_KEY or add API_KEY to Streamlit secrets")
        st.stop()

st.set_page_config(
    page_title="Stock Analytics Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Professional CSS
st.markdown("""
<style>
    /* Main container */
    .block-container {
        padding-top: 1rem;
        padding-bottom: 2rem;
        max-width: 100%;
    }
    
    /* Headers */
    h1 {
        font-weight: 600;
        letter-spacing: -0.02em;
        border-bottom: 3px solid #4A90E2;
        padding-bottom: 0.5rem;
        margin-bottom: 1.5rem;
    }
    
    h2 {
        font-weight: 500;
        letter-spacing: -0.01em;
        color: #E0E0E0;
        margin-top: 2.5rem;
        margin-bottom: 1rem;
        padding-bottom: 0.3rem;
        border-bottom: 1px solid #404040;
    }
    
    /* Metrics */
    [data-testid="stMetricValue"] {
        font-size: 1.8rem;
        font-weight: 600;
    }
    
    [data-testid="stMetricLabel"] {
        font-size: 0.9rem;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #A0A0A0;
    }
    
    /* Button */
    .stButton button {
        width: 100%;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        padding: 0.6rem 1.2rem;
        font-weight: 600;
        letter-spacing: 0.02em;
        transition: all 0.3s ease;
    }
    
    .stButton button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
    }
    
    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #1a1a1a;
    }
    
    /* Progress bar */
    .stProgress > div > div {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
    }
    
    /* Table */
    [data-testid="stDataFrame"] {
        font-size: 0.95rem;
    }
    
    /* Divider */
    .divider {
        border-top: 1px solid #333;
        margin: 2rem 0;
    }
    
    /* Caption */
    .caption {
        font-size: 0.85rem;
        color: #808080;
        font-style: italic;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.title("Stock Market Analytics Dashboard")
st.caption("Real-time market data powered by Alpha Vantage")

# Sidebar configuration
with st.sidebar:
    st.header("Configuration")
    
    symbols = st.multiselect(
        "Select Stocks",
        ['AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA', 'META', 'NVDA', 'AMD'],
        default=['AAPL', 'GOOGL', 'MSFT'],
        help="Choose up to 8 stocks to analyze"
    )
    
    st.markdown("---")
    
    refresh_interval = st.slider(
        "Refresh Interval",
        min_value=30,
        max_value=300,
        value=60,
        step=30,
        help="Time between data refreshes in seconds"
    )
    
    st.markdown("---")
    
    st.markdown("#### Quick Guide")
    st.markdown("""
    1. Select stocks from dropdown
    2. Click 'Fetch Latest Data'
    3. Wait for data to load
    4. Analyze charts and metrics
    """)
    
    st.markdown("---")
    
    st.info("**API Rate Limit**\n\n5 calls per minute on free tier")

    st.markdown("---")

# Initialize fetcher
fetcher = StockFetcher(API_KEY)

# Metrics row
col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Symbols Tracked", len(symbols))

with col2:
    st.metric("Refresh Interval", f"{refresh_interval}s")

with col3:
    st.metric("API Status", "Active")

st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

# Fetch button
if st.button("Fetch Latest Data", use_container_width=True):
    progress_bar = st.progress(0, text="Initializing...")
    
    quotes = []
    for idx, symbol in enumerate(symbols):
        progress_bar.progress(
            (idx) / len(symbols),
            text=f"Fetching {symbol}... ({idx+1}/{len(symbols)})"
        )
        
        quote = fetcher.get_realtime_quote(symbol)
        if quote:
            quotes.append(quote)
        
        # Rate limiting
        if idx < len(symbols) - 1:
            time.sleep(15)
    
    progress_bar.progress(1.0, text="Complete!")
    time.sleep(0.5)
    progress_bar.empty()
    
    if quotes:
        df = pd.DataFrame(quotes)
        
        # Current prices
        st.subheader("Current Prices")
        
        cols = st.columns(len(quotes))
        for i, quote in enumerate(quotes):
            with cols[i]:
                st.metric(
                    label=quote['symbol'],
                    value=f"${quote['price']:.2f}",
                    delta=f"{quote['change_percent']:.2f}%"
                )
        
        st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
        
        # Price comparison chart
        st.subheader("Price Comparison")
        
        colors = ['#667eea', '#f093fb', '#4facfe', '#43e97b', '#fa709a', '#fee140', '#30cfd0', '#a8edea']
        
        fig = go.Figure()
        for idx, quote in enumerate(quotes):
            fig.add_trace(go.Bar(
                name=quote['symbol'],
                x=[quote['symbol']],
                y=[quote['price']],
                text=f"${quote['price']:.2f}",
                textposition='outside',
                textfont=dict(size=13, weight='bold'),
                marker=dict(
                    color=colors[idx % len(colors)],
                    line=dict(width=0)
                ),
                width=0.5,
                hovertemplate='<b>%{x}</b><br>Price: $%{y:.2f}<extra></extra>'
            ))
        
        fig.update_layout(
            yaxis_title="Price (USD)",
            showlegend=False,
            height=450,
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(size=12, color='#E0E0E0'),
            margin=dict(l=60, r=60, t=30, b=60),
            xaxis=dict(
                showgrid=False,
                tickfont=dict(size=13, weight='bold')
            ),
            yaxis=dict(
                showgrid=True,
                gridcolor='rgba(128,128,128,0.15)',
                gridwidth=1
            )
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
        
        # Volume chart
        st.subheader("Trading Volume")
        
        fig2 = go.Figure()
        fig2.add_trace(go.Bar(
            x=[q['symbol'] for q in quotes],
            y=[q['volume'] for q in quotes],
            text=[f"{q['volume']:,.0f}" for q in quotes],
            textposition='outside',
            textfont=dict(size=12, weight='bold'),
            marker=dict(
                color='#4facfe',
                line=dict(width=0)
            ),
            width=0.5,
            hovertemplate='<b>%{x}</b><br>Volume: %{y:,.0f}<extra></extra>'
        ))
        
        fig2.update_layout(
            yaxis_title="Volume",
            height=450,
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(size=12, color='#E0E0E0'),
            margin=dict(l=60, r=60, t=30, b=60),
            xaxis=dict(
                showgrid=False,
                tickfont=dict(size=13, weight='bold')
            ),
            yaxis=dict(
                showgrid=True,
                gridcolor='rgba(128,128,128,0.15)',
                gridwidth=1
            )
        )
        
        st.plotly_chart(fig2, use_container_width=True)
        
        st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
        
        # Data table
        st.subheader("Detailed Data")
        
        df_display = df.copy()
        df_display = df_display[['symbol', 'price', 'change_percent', 'volume', 'timestamp']]
        df_display.columns = ['Symbol', 'Price', 'Change', 'Volume', 'Timestamp']
        df_display['Price'] = df_display['Price'].apply(lambda x: f"${x:.2f}")
        df_display['Change'] = df_display['Change'].apply(lambda x: f"{x:+.2f}%")
        df_display['Volume'] = df_display['Volume'].apply(lambda x: f"{x:,}")
        
        st.dataframe(
            df_display,
            use_container_width=True,
            hide_index=True
        )
        
        st.markdown(f'<p class="caption">Last updated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")} | Fetched {len(quotes)}/{len(symbols)} symbols successfully</p>', unsafe_allow_html=True)
        
    else:
        st.error("Failed to fetch data. Please verify your API key and network connection.")

# ---------- Footer ----------
st.markdown("---")

st.markdown(
"""
<div style="text-align:center; font-size:0.9rem; color:#999;">
    <b>Author</b><br>
    Nalini Panwar<br>
    <a href="https://github.com/panwarnalini-hub" target="_blank">GitHub</a> ·
    <a href="https://www.linkedin.com/in/nalinipanwar/" target="_blank">LinkedIn</a>
</div>
""",
unsafe_allow_html=True
)
