#!/usr/bin/env python3
"""
Streamlit Web Dashboard for Market Sentiment Analysis
Run with: streamlit run streamlit_dashboard.py
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import json
from market_sentiment_agent import MarketSentimentAgent

# Page configuration
st.set_page_config(
    page_title="Market Sentiment Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

@st.cache_data(ttl=300)  # Cache for 5 minutes
def get_sentiment_data(symbol):
    """Cached function to get sentiment data"""
    agent = MarketSentimentAgent()
    return agent.get_comprehensive_sentiment(symbol)

@st.cache_data(ttl=300)
def get_market_data(symbol, period):
    """Cached function to get market data"""
    agent = MarketSentimentAgent()
    return agent.get_yahoo_data(symbol, period)

def create_price_chart(data, symbol):
    """Create interactive price chart with technical indicators"""
    if data.empty:
        return None
        
    fig = make_subplots(
        rows=3, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        subplot_titles=('Price & Moving Averages', 'RSI', 'MACD'),
        row_heights=[0.5, 0.25, 0.25]
    )
    
    # Price and moving averages
    close_prices = data['Close']
    sma_20 = close_prices.rolling(window=20).mean()
    sma_50 = close_prices.rolling(window=50).mean()
    
    fig.add_trace(go.Scatter(x=data.index, y=close_prices, name='Price', 
                            line=dict(color='black', width=2)), row=1, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=sma_20, name='SMA 20', 
                            line=dict(color='blue', width=1)), row=1, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=sma_50, name='SMA 50', 
                            line=dict(color='red', width=1)), row=1, col=1)
    
    # RSI
    agent = MarketSentimentAgent()
    rsi = agent.calculate_rsi(close_prices)
    fig.add_trace(go.Scatter(x=data.index, y=rsi, name='RSI', 
                            line=dict(color='purple', width=2)), row=2, col=1)
    fig.add_hline(y=70, line_dash="dash", line_color="red", opacity=0.7, row=2, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="green", opacity=0.7, row=2, col=1)
    
    # MACD
    macd_data = agent.calculate_macd(close_prices)
    fig.add_trace(go.Scatter(x=data.index, y=macd_data['macd'], name='MACD', 
                            line=dict(color='blue', width=2)), row=3, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=macd_data['signal'], name='Signal', 
                            line=dict(color='red', width=2)), row=3, col=1)
    fig.add_trace(go.Bar(x=data.index, y=macd_data['histogram'], name='Histogram', 
                        opacity=0.3, marker_color='gray'), row=3, col=1)
    
    fig.update_layout(height=800, showlegend=True, title_text=f"{symbol} Technical Analysis")
    fig.update_yaxes(title_text="Price ($)", row=1, col=1)
    fig.update_yaxes(title_text="RSI", row=2, col=1, range=[0, 100])
    fig.update_yaxes(title_text="MACD", row=3, col=1)
    
    return fig

def create_sentiment_gauge(sentiment_score, sentiment_label):
    """Create a sentiment gauge chart"""
    fig = go.Figure(go.Indicator(
        mode = "gauge+number+delta",
        value = sentiment_score,
        domain = {'x': [0, 1], 'y': [0, 1]},
        title = {'text': "Overall Sentiment"},
        delta = {'reference': 50},
        gauge = {
            'axis': {'range': [None, 100]},
            'bar': {'color': "darkblue"},
            'steps': [
                {'range': [0, 30], 'color': "red"},
                {'range': [30, 45], 'color': "orange"},
                {'range': [45, 55], 'color': "yellow"},
                {'range': [55, 70], 'color': "lightgreen"},
                {'range': [70, 100], 'color': "green"}
            ],
            'threshold': {
                'line': {'color': "black", 'width': 4},
                'thickness': 0.75,
                'value': sentiment_score
            }
        }
    ))
    
    fig.update_layout(height=300, font={'size': 16})
    return fig

def create_sentiment_breakdown(sentiment_scores, weights):
    """Create sentiment breakdown chart"""
    indicators = list(sentiment_scores.keys())
    scores = list(sentiment_scores.values())
    
    # Calculate weighted contributions
    contributions = [scores[i] * weights.get(indicators[i], 0) for i in range(len(scores))]
    
    fig = go.Figure()
    
    # Add bars for scores
    fig.add_trace(go.Bar(
        y=indicators,
        x=scores,
        orientation='h',
        name='Sentiment Score',
        marker_color=['green' if score >= 50 else 'red' for score in scores],
        opacity=0.7
    ))
    
    fig.update_layout(
        title="Sentiment Indicators Breakdown",
        xaxis_title="Sentiment Score (0-100)",
        height=400,
        showlegend=False
    )
    
    fig.add_vline(x=50, line_dash="dash", line_color="gray", opacity=0.7)
    
    return fig

def main():
    """Main Streamlit application"""
    
    # Header
    st.title("📈 Market Sentiment Dashboard")
    st.markdown("**Real-time sentiment analysis for XAUUSD (Gold) and XAGUSD (Silver)**")
    
    # Sidebar
    st.sidebar.header("Settings")
    
    # Symbol selection
    symbol = st.sidebar.selectbox(
        "Select Symbol",
        ["XAUUSD", "XAGUSD"],
        help="Choose the precious metal to analyze"
    )
    
    # Time period selection
    period = st.sidebar.selectbox(
        "Time Period",
        ["1d", "5d", "1mo", "3mo", "6mo", "1y"],
        index=2,
        help="Select the time period for analysis"
    )
    
    # Auto-refresh option
    auto_refresh = st.sidebar.checkbox("Auto-refresh (5 min)", value=False)
    
    if auto_refresh:
        st.sidebar.info("Dashboard will refresh every 5 minutes")
    
    # Manual refresh button
    if st.sidebar.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()
    
    # Main content
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.header(f"📊 {symbol} Analysis")
        
        # Get sentiment data
        with st.spinner("Loading sentiment analysis..."):
            sentiment_data = get_sentiment_data(symbol)
        
        if 'error' in sentiment_data:
            st.error(f"Error loading data: {sentiment_data['error']}")
            return
        
        # Display current sentiment
        sentiment_score = sentiment_data['overall_sentiment']
        sentiment_label = sentiment_data['sentiment_label']
        sentiment_emoji = sentiment_data['sentiment_emoji']
        
        st.metric(
            label="Current Sentiment",
            value=f"{sentiment_emoji} {sentiment_label}",
            delta=f"{sentiment_score:.1f}/100"
        )
        
        # Get market data and create charts
        with st.spinner("Loading market data..."):
            market_data = get_market_data(symbol, period)
        
        if not market_data.empty:
            # Price chart
            price_fig = create_price_chart(market_data, symbol)
            if price_fig:
                st.plotly_chart(price_fig, use_container_width=True)
        else:
            st.warning("No market data available for the selected period")
    
    with col2:
        st.header("🎯 Sentiment Metrics")
        
        # Sentiment gauge
        gauge_fig = create_sentiment_gauge(sentiment_score, sentiment_label)
        st.plotly_chart(gauge_fig, use_container_width=True)
        
        # Key indicators
        indicators = sentiment_data['analysis']['indicators']
        
        st.subheader("📈 Key Indicators")
        
        col_a, col_b = st.columns(2)
        with col_a:
            st.metric("RSI", f"{indicators['rsi']:.1f}")
            st.metric("MACD", f"{indicators['macd']:.4f}")
        
        with col_b:
            st.metric("Price", f"${indicators['price']:.2f}")
            if indicators['sma_20']:
                st.metric("SMA 20", f"${indicators['sma_20']:.2f}")
        
        # TradingView data if available
        if 'tradingview_raw' in sentiment_data['analysis']:
            st.subheader("📺 TradingView Signals")
            tv_data = sentiment_data['analysis']['tradingview_raw']
            
            col_c, col_d, col_e = st.columns(3)
            with col_c:
                st.metric("Buy", tv_data.get('BUY', 0), delta_color="normal")
            with col_d:
                st.metric("Neutral", tv_data.get('NEUTRAL', 0), delta_color="off")
            with col_e:
                st.metric("Sell", tv_data.get('SELL', 0), delta_color="inverse")
            
            st.info(f"**Recommendation:** {tv_data.get('RECOMMENDATION', 'N/A')}")
    
    # Sentiment breakdown chart
    st.header("🔍 Detailed Sentiment Analysis")
    
    sentiment_scores = sentiment_data['analysis']['sentiment_scores']
    weights = MarketSentimentAgent().weights
    
    breakdown_fig = create_sentiment_breakdown(sentiment_scores, weights)
    st.plotly_chart(breakdown_fig, use_container_width=True)
    
    # Comparison section
    st.header("⚖️ Gold vs Silver Comparison")
    
    col_gold, col_silver = st.columns(2)
    
    with col_gold:
        gold_data = get_sentiment_data('XAUUSD')
        if 'error' not in gold_data:
            st.metric(
                "Gold (XAUUSD)",
                f"{gold_data['sentiment_emoji']} {gold_data['sentiment_label']}",
                f"{gold_data['overall_sentiment']:.1f}/100"
            )
    
    with col_silver:
        silver_data = get_sentiment_data('XAGUSD')
        if 'error' not in silver_data:
            st.metric(
                "Silver (XAGUSD)",
                f"{silver_data['sentiment_emoji']} {silver_data['sentiment_label']}",
                f"{silver_data['overall_sentiment']:.1f}/100"
            )
    
    # Footer
    st.markdown("---")
    st.markdown(
        f"**Last Updated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
        "**Disclaimer:** This analysis is for educational purposes only. "
        "Always conduct your own research before making trading decisions."
    )
    
    # Auto-refresh logic
    if auto_refresh:
        import time
        time.sleep(300)  # 5 minutes
        st.rerun()

if __name__ == "__main__":
    main()