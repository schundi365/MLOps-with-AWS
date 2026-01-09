# Market Sentiment Agent - Usage Guide 🚀

## Quick Start Commands

### 1. Basic Sentiment Analysis
```bash
python market_sentiment_agent.py
```
This runs a complete sentiment analysis for both XAUUSD (Gold) and XAGUSD (Silver) and displays:
- Overall sentiment scores (0-100)
- Technical indicators (RSI, MACD, Moving Averages)
- Weighted sentiment breakdown
- Comparison between Gold and Silver

### 2. Interactive Visualizations
```bash
python sentiment_visualizer.py
```
Creates interactive charts including:
- Price charts with technical indicators
- Sentiment breakdown charts
- Comparison visualizations
- Historical trend analysis

### 3. Web Dashboard
```bash
streamlit run streamlit_dashboard.py
```
Launches a web-based dashboard at `http://localhost:8501` with:
- Real-time sentiment analysis
- Interactive Plotly charts
- Auto-refresh capabilities
- Mobile-responsive interface

## Understanding the Output

### Sentiment Scores
- **🟢 BULLISH (70-100)**: Strong positive sentiment
- **🟡 SLIGHTLY BULLISH (55-69)**: Mild positive sentiment  
- **⚪ NEUTRAL (45-54)**: Balanced sentiment
- **🟠 SLIGHTLY BEARISH (31-44)**: Mild negative sentiment
- **🔴 BEARISH (0-30)**: Strong negative sentiment

### Technical Indicators

#### RSI (Relative Strength Index)
- **Above 70**: Potentially overbought
- **Below 30**: Potentially oversold
- **Around 50**: Neutral momentum

#### MACD (Moving Average Convergence Divergence)
- **Positive MACD above Signal**: Bullish momentum
- **Negative MACD below Signal**: Bearish momentum
- **Crossovers**: Potential trend changes

#### Moving Averages
- **Price above MA**: Bullish trend
- **Price below MA**: Bearish trend
- **MA crossovers**: Trend confirmations

### Sentiment Weights
The agent uses weighted scoring:
- **RSI**: 25% - Momentum analysis
- **MACD**: 20% - Trend direction
- **Moving Averages**: 20% - Price position
- **Volume**: 15% - Market participation
- **Volatility**: 10% - Risk assessment
- **TradingView**: 10% - Professional signals

## Customization

### Modify Sentiment Weights
Edit `config.json`:
```json
{
  "sentiment_weights": {
    "rsi": 0.30,
    "macd": 0.25,
    "moving_averages": 0.20,
    "volume": 0.15,
    "volatility": 0.05,
    "tradingview": 0.05
  }
}
```

### Change Technical Parameters
```json
{
  "technical_parameters": {
    "rsi_period": 14,
    "macd_fast": 12,
    "macd_slow": 26,
    "sma_short": 20,
    "sma_long": 50
  }
}
```

## Programmatic Usage

### Basic Analysis
```python
from market_sentiment_agent import MarketSentimentAgent

agent = MarketSentimentAgent()

# Analyze specific symbol
gold_sentiment = agent.get_comprehensive_sentiment('XAUUSD')
print(f"Gold sentiment: {gold_sentiment['sentiment_label']}")
print(f"Score: {gold_sentiment['overall_sentiment']:.1f}/100")

# Get raw market data
data = agent.get_yahoo_data('XAUUSD', period='1mo')
print(f"Latest price: ${data['Close'].iloc[-1]:.2f}")
```

### Custom Analysis
```python
# Calculate specific indicators
close_prices = data['Close']
rsi = agent.calculate_rsi(close_prices)
macd_data = agent.calculate_macd(close_prices)

print(f"Current RSI: {rsi.iloc[-1]:.2f}")
print(f"Current MACD: {macd_data['macd'].iloc[-1]:.4f}")
```

### Visualization
```python
from sentiment_visualizer import SentimentVisualizer

visualizer = SentimentVisualizer()

# Create dashboard for specific symbol
visualizer.create_sentiment_dashboard('XAUUSD')

# Create comparison chart
visualizer.create_comparison_chart()

# Historical trend analysis
visualizer.create_historical_sentiment_trend('XAUUSD', days=30)
```

## Data Sources & Symbols

### Yahoo Finance Symbols
- **Gold**: `GC=F` (Gold Futures)
- **Silver**: `SI=F` (Silver Futures)

### Available Time Periods
- `1d`, `5d`, `1mo`, `3mo`, `6mo`, `1y`, `2y`, `5y`, `10y`, `ytd`, `max`

### TradingView Integration
- Provides professional technical analysis
- Real-time sentiment signals
- May have occasional connectivity issues

## Troubleshooting

### Common Issues

1. **No Data Available**
   - Check internet connection
   - Verify market is open
   - Try different time periods

2. **TradingView Errors**
   - Normal behavior, agent continues without TradingView data
   - Uses fallback neutral sentiment (50)

3. **Import Errors**
   ```bash
   pip install -r requirements.txt
   ```

4. **Streamlit Issues**
   ```bash
   streamlit run streamlit_dashboard.py --server.port 8502
   ```

### Performance Tips
- Use shorter time periods for faster analysis
- Cache results for repeated queries
- Close matplotlib figures to save memory

## Scheduling Automated Analysis

### Windows Task Scheduler
Create a batch file `run_analysis.bat`:
```batch
@echo off
cd /d "C:\path\to\your\agent"
python market_sentiment_agent.py >> analysis_log.txt 2>&1
```

### Linux/Mac Cron Job
```bash
# Run every hour during market hours
0 9-16 * * 1-5 cd /path/to/agent && python market_sentiment_agent.py >> analysis_log.txt 2>&1
```

### Python Scheduler
```python
import schedule
import time
from market_sentiment_agent import MarketSentimentAgent

def run_analysis():
    agent = MarketSentimentAgent()
    results = agent.run_analysis()
    # Save results or send notifications

schedule.every().hour.do(run_analysis)

while True:
    schedule.run_pending()
    time.sleep(60)
```

## Integration Examples

### Discord Bot Integration
```python
import discord
from market_sentiment_agent import MarketSentimentAgent

class SentimentBot(discord.Client):
    async def on_message(self, message):
        if message.content.startswith('!sentiment'):
            agent = MarketSentimentAgent()
            results = agent.run_analysis()
            
            embed = discord.Embed(title="Market Sentiment")
            for symbol, data in results.items():
                if 'error' not in data:
                    embed.add_field(
                        name=f"{data['name']} ({symbol})",
                        value=f"{data['sentiment_emoji']} {data['sentiment_label']} ({data['overall_sentiment']:.1f})",
                        inline=False
                    )
            
            await message.channel.send(embed=embed)
```

### Telegram Bot Integration
```python
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from market_sentiment_agent import MarketSentimentAgent

async def sentiment_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    agent = MarketSentimentAgent()
    results = agent.run_analysis()
    
    message = "📈 Market Sentiment Update\n\n"
    for symbol, data in results.items():
        if 'error' not in data:
            message += f"{data['sentiment_emoji']} {data['name']}: {data['sentiment_label']} ({data['overall_sentiment']:.1f})\n"
    
    await update.message.reply_text(message)

# Setup bot
app = Application.builder().token("YOUR_BOT_TOKEN").build()
app.add_handler(CommandHandler("sentiment", sentiment_command))
app.run_polling()
```

## Best Practices

1. **Regular Updates**: Run analysis multiple times per day during market hours
2. **Combine Sources**: Use multiple indicators and timeframes
3. **Risk Management**: Never rely solely on automated analysis
4. **Backtesting**: Test strategies with historical data
5. **Documentation**: Keep logs of analysis results and decisions

## Disclaimer ⚠️

This tool is for educational and research purposes only. Market sentiment analysis should be used as part of a comprehensive trading strategy, not as the sole basis for trading decisions. Always:

- Conduct your own research
- Consider multiple sources of information
- Understand the risks involved in trading
- Consult with financial professionals
- Never invest more than you can afford to lose

---

**Happy Trading! 📈💰**