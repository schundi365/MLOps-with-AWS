# Market Sentiment Analysis Agent 📈

A comprehensive Python-based agent for analyzing market sentiment on XAUUSD (Gold) and XAGUSD (Silver) using multiple data sources including Yahoo Finance, TradingView, and advanced technical indicators.

## Features 🚀

- **Multi-Source Data Integration**: Yahoo Finance, TradingView APIs
- **Advanced Technical Analysis**: RSI, MACD, Moving Averages, Volume Analysis
- **Sentiment Scoring**: Weighted sentiment calculation with customizable parameters
- **Interactive Visualizations**: Charts, dashboards, and trend analysis
- **Web Dashboard**: Real-time Streamlit-based interface
- **Automated Analysis**: Scheduled sentiment updates and alerts

## Quick Start 🏃‍♂️

### 1. Installation

```bash
# Clone or download the files
# Run the setup script
python setup.py
```

### 2. Basic Usage

```bash
# Run sentiment analysis
python market_sentiment_agent.py

# Create visualizations
python sentiment_visualizer.py

# Launch web dashboard
streamlit run streamlit_dashboard.py
```

## Components 📦

### Core Agent (`market_sentiment_agent.py`)
- Main sentiment analysis engine
- Technical indicator calculations
- Multi-source data integration
- Weighted sentiment scoring

### Visualizer (`sentiment_visualizer.py`)
- Interactive charts and graphs
- Comparison visualizations
- Historical trend analysis
- Export capabilities

### Web Dashboard (`streamlit_dashboard.py`)
- Real-time web interface
- Interactive charts with Plotly
- Auto-refresh capabilities
- Mobile-responsive design

## Data Sources 📊

### Yahoo Finance
- Historical price data
- Volume information
- Real-time quotes
- Symbol: `GC=F` (Gold), `SI=F` (Silver)

### TradingView
- Technical analysis signals
- Professional indicators
- Market recommendations
- Real-time sentiment data

## Technical Indicators 📈

### RSI (Relative Strength Index)
- Momentum oscillator (0-100)
- Overbought/Oversold signals
- 14-period default

### MACD (Moving Average Convergence Divergence)
- Trend-following momentum indicator
- Signal line crossovers
- Histogram analysis

### Moving Averages
- Simple Moving Average (SMA)
- Exponential Moving Average (EMA)
- 20 and 50-period defaults

### Volume Analysis
- Volume-weighted sentiment
- Above/below average volume
- Volume trend analysis

### Volatility Metrics
- Price volatility calculation
- Annualized volatility
- Risk assessment

## Sentiment Scoring 🎯

The agent uses a weighted scoring system (0-100 scale):

| Indicator | Weight | Description |
|-----------|--------|-------------|
| RSI | 25% | Momentum analysis |
| MACD | 20% | Trend direction |
| Moving Averages | 20% | Price position |
| Volume | 15% | Market participation |
| Volatility | 10% | Risk assessment |
| TradingView | 10% | Professional signals |

### Sentiment Levels
- **🟢 BULLISH** (70-100): Strong positive sentiment
- **🟡 SLIGHTLY BULLISH** (55-69): Mild positive sentiment
- **⚪ NEUTRAL** (45-54): Balanced sentiment
- **🟠 SLIGHTLY BEARISH** (31-44): Mild negative sentiment
- **🔴 BEARISH** (0-30): Strong negative sentiment

## Configuration ⚙️

Edit `config.json` to customize:

```json
{
  "sentiment_weights": {
    "rsi": 0.25,
    "macd": 0.20,
    "moving_averages": 0.20,
    "volume": 0.15,
    "volatility": 0.10,
    "tradingview": 0.10
  },
  "technical_parameters": {
    "rsi_period": 14,
    "macd_fast": 12,
    "macd_slow": 26,
    "sma_short": 20,
    "sma_long": 50
  }
}
```

## Usage Examples 💡

### Basic Analysis
```python
from market_sentiment_agent import MarketSentimentAgent

agent = MarketSentimentAgent()
results = agent.run_analysis()
```

### Custom Symbol Analysis
```python
sentiment_data = agent.get_comprehensive_sentiment('XAUUSD')
print(f"Gold Sentiment: {sentiment_data['sentiment_label']}")
```

### Visualization
```python
from sentiment_visualizer import SentimentVisualizer

visualizer = SentimentVisualizer()
visualizer.create_sentiment_dashboard('XAUUSD')
visualizer.create_comparison_chart()
```

## Web Dashboard Features 🌐

- **Real-time Updates**: Auto-refresh every 5 minutes
- **Interactive Charts**: Zoom, pan, hover details
- **Responsive Design**: Works on desktop and mobile
- **Export Options**: Save charts and data
- **Comparison Tools**: Side-by-side analysis

### Dashboard Sections
1. **Overview**: Current sentiment and key metrics
2. **Technical Charts**: Price, RSI, MACD analysis
3. **Sentiment Breakdown**: Detailed indicator scores
4. **Comparison**: Gold vs Silver analysis
5. **Historical Trends**: Time-series analysis

## API Integration 🔌

### Yahoo Finance Integration
```python
# Fetch historical data
data = agent.get_yahoo_data('XAUUSD', period='1mo')

# Available periods: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max
```

### TradingView Integration
```python
# Get technical analysis
tv_analysis = agent.get_tradingview_analysis('XAUUSD')
print(tv_analysis['RECOMMENDATION'])  # BUY, SELL, NEUTRAL, etc.
```

## Troubleshooting 🔧

### Common Issues

1. **Import Errors**
   ```bash
   pip install -r requirements.txt
   ```

2. **TradingView API Issues**
   - Check internet connection
   - Verify symbol format
   - Try alternative intervals

3. **Yahoo Finance Data Issues**
   - Symbol might be delisted
   - Try different time periods
   - Check for market holidays

4. **Streamlit Dashboard Issues**
   ```bash
   streamlit run streamlit_dashboard.py --server.port 8501
   ```

### Performance Tips
- Use caching for repeated analysis
- Limit historical data periods for faster processing
- Close unused matplotlib figures to save memory

## Dependencies 📋

```
yfinance>=0.2.18
pandas>=1.5.0
numpy>=1.21.0
requests>=2.28.0
tradingview-ta>=3.3.0
matplotlib>=3.5.0
seaborn>=0.11.0
plotly>=5.0.0
streamlit>=1.28.0
```

## Disclaimer ⚠️

This tool is for educational and research purposes only. It should not be used as the sole basis for trading decisions. Always:

- Conduct your own research
- Consider multiple sources of information
- Understand the risks involved in trading
- Consult with financial professionals
- Never invest more than you can afford to lose

## License 📄

This project is open source and available under the MIT License.

## Contributing 🤝

Contributions are welcome! Please feel free to submit pull requests or open issues for:

- Bug fixes
- Feature enhancements
- Documentation improvements
- Additional data sources
- New technical indicators

## Support 💬

For questions, issues, or suggestions:
1. Check the troubleshooting section
2. Review existing issues
3. Create a new issue with detailed information
4. Include error messages and system information

---

**Happy Trading! 📈💰**