#!/usr/bin/env python3
"""
Market Sentiment Analysis Agent for XAUUSD (Gold) and XAGUSD (Silver)

This agent analyzes market sentiment using multiple data sources:
- Yahoo Finance for historical data
- TradingView for technical analysis
- Multiple technical indicators for sentiment scoring
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import requests
import json
from typing import Dict, List, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')

try:
    from tradingview_ta import TA_Handler, Interval, Exchange
    TRADINGVIEW_AVAILABLE = True
except ImportError:
    TRADINGVIEW_AVAILABLE = False
    print("TradingView TA not available. Install with: pip install tradingview_ta")

class MarketSentimentAgent:
    """
    Advanced market sentiment analysis agent for precious metals trading
    """
    
    def __init__(self):
        self.symbols = {
            'XAUUSD': {'yahoo': 'GC=F', 'name': 'Gold'},  # Gold futures
            'XAGUSD': {'yahoo': 'SI=F', 'name': 'Silver'}  # Silver futures
        }
        
        # Sentiment scoring weights
        self.weights = {
            'rsi': 0.25,
            'macd': 0.20,
            'moving_averages': 0.20,
            'volume': 0.15,
            'volatility': 0.10,
            'tradingview': 0.10
        }
    
    def get_yahoo_data(self, symbol: str, period: str = "1mo") -> pd.DataFrame:
        """Fetch data from Yahoo Finance"""
        try:
            yahoo_symbol = self.symbols[symbol]['yahoo']
            ticker = yf.Ticker(yahoo_symbol)
            data = ticker.history(period=period)
            return data
        except Exception as e:
            print(f"Error fetching Yahoo data for {symbol}: {e}")
            return pd.DataFrame()
    
    def calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Calculate Relative Strength Index"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def calculate_macd(self, prices: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Dict:
        """Calculate MACD indicator"""
        exp1 = prices.ewm(span=fast).mean()
        exp2 = prices.ewm(span=slow).mean()
        macd_line = exp1 - exp2
        signal_line = macd_line.ewm(span=signal).mean()
        histogram = macd_line - signal_line
        
        return {
            'macd': macd_line,
            'signal': signal_line,
            'histogram': histogram
        }
    
    def calculate_moving_averages(self, prices: pd.Series) -> Dict:
        """Calculate various moving averages"""
        return {
            'sma_20': prices.rolling(window=20).mean(),
            'sma_50': prices.rolling(window=50).mean(),
            'ema_20': prices.ewm(span=20).mean(),
            'ema_50': prices.ewm(span=50).mean()
        }
    
    def get_tradingview_analysis(self, symbol: str) -> Optional[Dict]:
        """Get TradingView technical analysis"""
        if not TRADINGVIEW_AVAILABLE:
            return None
            
        try:
            # Map symbols to TradingView format
            tv_symbols = {
                'XAUUSD': {'symbol': 'XAUUSD', 'screener': 'forex', 'exchange': 'FX_IDC'},
                'XAGUSD': {'symbol': 'XAGUSD', 'screener': 'forex', 'exchange': 'FX_IDC'}
            }
            
            if symbol not in tv_symbols:
                return None
                
            handler = TA_Handler(
                symbol=tv_symbols[symbol]['symbol'],
                screener=tv_symbols[symbol]['screener'],
                exchange=tv_symbols[symbol]['exchange'],
                interval=Interval.INTERVAL_1_DAY
            )
            
            analysis = handler.get_analysis()
            return analysis.summary
            
        except Exception as e:
            print(f"Error getting TradingView analysis for {symbol}: {e}")
            return None
    
    def analyze_sentiment_indicators(self, data: pd.DataFrame) -> Dict:
        """Analyze various sentiment indicators"""
        if data.empty:
            return {}
            
        close_prices = data['Close']
        volume = data['Volume'] if 'Volume' in data.columns else pd.Series()
        
        # Calculate technical indicators
        rsi = self.calculate_rsi(close_prices)
        macd_data = self.calculate_macd(close_prices)
        ma_data = self.calculate_moving_averages(close_prices)
        
        # Get latest values
        latest_rsi = rsi.iloc[-1] if not rsi.empty else 50
        latest_macd = macd_data['macd'].iloc[-1] if not macd_data['macd'].empty else 0
        latest_signal = macd_data['signal'].iloc[-1] if not macd_data['signal'].empty else 0
        latest_price = close_prices.iloc[-1]
        
        # Calculate sentiment scores (0-100, where 50 is neutral)
        sentiment_scores = {}
        
        # RSI Sentiment (inverted: low RSI = oversold = bullish potential)
        if latest_rsi < 30:
            sentiment_scores['rsi'] = 70 + (30 - latest_rsi)  # Bullish
        elif latest_rsi > 70:
            sentiment_scores['rsi'] = 30 - (latest_rsi - 70)  # Bearish
        else:
            sentiment_scores['rsi'] = 50  # Neutral
            
        # MACD Sentiment
        macd_sentiment = 50
        if latest_macd > latest_signal:
            macd_sentiment += min(25, abs(latest_macd - latest_signal) * 100)
        else:
            macd_sentiment -= min(25, abs(latest_macd - latest_signal) * 100)
        sentiment_scores['macd'] = max(0, min(100, macd_sentiment))
        
        # Moving Average Sentiment
        ma_sentiment = 50
        if latest_price > ma_data['sma_20'].iloc[-1]:
            ma_sentiment += 15
        if latest_price > ma_data['sma_50'].iloc[-1]:
            ma_sentiment += 15
        if ma_data['sma_20'].iloc[-1] > ma_data['sma_50'].iloc[-1]:
            ma_sentiment += 20
        sentiment_scores['moving_averages'] = max(0, min(100, ma_sentiment))
        
        # Volume sentiment (if available)
        if not volume.empty and len(volume) > 20:
            avg_volume = volume.rolling(window=20).mean().iloc[-1]
            current_volume = volume.iloc[-1]
            volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1
            sentiment_scores['volume'] = min(100, 50 + (volume_ratio - 1) * 25)
        else:
            sentiment_scores['volume'] = 50
            
        # Volatility sentiment
        returns = close_prices.pct_change().dropna()
        if len(returns) > 1:
            volatility = returns.std() * np.sqrt(252)  # Annualized volatility
            # Higher volatility can indicate uncertainty (slightly bearish)
            sentiment_scores['volatility'] = max(0, 60 - volatility * 100)
        else:
            sentiment_scores['volatility'] = 50
            
        return {
            'indicators': {
                'rsi': latest_rsi,
                'macd': latest_macd,
                'macd_signal': latest_signal,
                'price': latest_price,
                'sma_20': ma_data['sma_20'].iloc[-1] if not ma_data['sma_20'].empty else None,
                'sma_50': ma_data['sma_50'].iloc[-1] if not ma_data['sma_50'].empty else None,
            },
            'sentiment_scores': sentiment_scores
        }
    
    def get_comprehensive_sentiment(self, symbol: str) -> Dict:
        """Get comprehensive sentiment analysis for a symbol"""
        print(f"\n🔍 Analyzing {self.symbols[symbol]['name']} ({symbol})...")
        
        # Get Yahoo Finance data
        data = self.get_yahoo_data(symbol)
        if data.empty:
            return {'error': f'No data available for {symbol}'}
        
        # Analyze sentiment indicators
        analysis = self.analyze_sentiment_indicators(data)
        
        # Get TradingView analysis
        tv_analysis = self.get_tradingview_analysis(symbol)
        if tv_analysis:
            # Convert TradingView recommendation to sentiment score
            tv_sentiment = 50  # Default neutral
            if tv_analysis.get('RECOMMENDATION') == 'STRONG_BUY':
                tv_sentiment = 90
            elif tv_analysis.get('RECOMMENDATION') == 'BUY':
                tv_sentiment = 70
            elif tv_analysis.get('RECOMMENDATION') == 'SELL':
                tv_sentiment = 30
            elif tv_analysis.get('RECOMMENDATION') == 'STRONG_SELL':
                tv_sentiment = 10
            
            analysis['sentiment_scores']['tradingview'] = tv_sentiment
            analysis['tradingview_raw'] = tv_analysis
        else:
            analysis['sentiment_scores']['tradingview'] = 50
        
        # Calculate weighted overall sentiment
        sentiment_scores = analysis['sentiment_scores']
        overall_sentiment = sum(
            sentiment_scores.get(indicator, 50) * weight 
            for indicator, weight in self.weights.items()
        )
        
        # Determine sentiment label
        if overall_sentiment >= 70:
            sentiment_label = "BULLISH"
            sentiment_emoji = "🟢"
        elif overall_sentiment >= 55:
            sentiment_label = "SLIGHTLY BULLISH"
            sentiment_emoji = "🟡"
        elif overall_sentiment >= 45:
            sentiment_label = "NEUTRAL"
            sentiment_emoji = "⚪"
        elif overall_sentiment >= 30:
            sentiment_label = "SLIGHTLY BEARISH"
            sentiment_emoji = "🟠"
        else:
            sentiment_label = "BEARISH"
            sentiment_emoji = "🔴"
        
        return {
            'symbol': symbol,
            'name': self.symbols[symbol]['name'],
            'overall_sentiment': overall_sentiment,
            'sentiment_label': sentiment_label,
            'sentiment_emoji': sentiment_emoji,
            'analysis': analysis,
            'timestamp': datetime.now().isoformat()
        }
    
    def print_sentiment_report(self, sentiment_data: Dict):
        """Print a formatted sentiment report"""
        if 'error' in sentiment_data:
            print(f"❌ {sentiment_data['error']}")
            return
            
        print(f"\n{sentiment_data['sentiment_emoji']} {sentiment_data['name']} ({sentiment_data['symbol']}) - {sentiment_data['sentiment_label']}")
        print(f"Overall Sentiment Score: {sentiment_data['overall_sentiment']:.1f}/100")
        print("-" * 50)
        
        indicators = sentiment_data['analysis']['indicators']
        sentiment_scores = sentiment_data['analysis']['sentiment_scores']
        
        print("📊 Technical Indicators:")
        print(f"  RSI: {indicators['rsi']:.2f} (Sentiment: {sentiment_scores['rsi']:.1f})")
        print(f"  MACD: {indicators['macd']:.4f} (Sentiment: {sentiment_scores['macd']:.1f})")
        print(f"  Price: ${indicators['price']:.2f}")
        if indicators['sma_20']:
            print(f"  SMA 20: ${indicators['sma_20']:.2f}")
        if indicators['sma_50']:
            print(f"  SMA 50: ${indicators['sma_50']:.2f}")
        
        print(f"\n📈 Sentiment Breakdown:")
        for indicator, score in sentiment_scores.items():
            weight = self.weights.get(indicator, 0) * 100
            print(f"  {indicator.replace('_', ' ').title()}: {score:.1f} (Weight: {weight:.0f}%)")
        
        if 'tradingview_raw' in sentiment_data['analysis']:
            tv_data = sentiment_data['analysis']['tradingview_raw']
            print(f"\n📺 TradingView Analysis:")
            print(f"  Recommendation: {tv_data.get('RECOMMENDATION', 'N/A')}")
            print(f"  Buy Signals: {tv_data.get('BUY', 0)}")
            print(f"  Neutral Signals: {tv_data.get('NEUTRAL', 0)}")
            print(f"  Sell Signals: {tv_data.get('SELL', 0)}")
    
    def run_analysis(self):
        """Run complete sentiment analysis for both symbols"""
        print("🚀 Market Sentiment Analysis Agent")
        print("=" * 60)
        
        results = {}
        for symbol in self.symbols.keys():
            sentiment_data = self.get_comprehensive_sentiment(symbol)
            results[symbol] = sentiment_data
            self.print_sentiment_report(sentiment_data)
        
        # Summary comparison
        print("\n📋 SUMMARY COMPARISON")
        print("=" * 60)
        for symbol, data in results.items():
            if 'error' not in data:
                print(f"{data['sentiment_emoji']} {data['name']}: {data['sentiment_label']} ({data['overall_sentiment']:.1f})")
        
        return results

def main():
    """Main function to run the sentiment analysis"""
    agent = MarketSentimentAgent()
    results = agent.run_analysis()
    
    print(f"\n⏰ Analysis completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\n💡 Disclaimer: This analysis is for educational purposes only.")
    print("   Always conduct your own research before making trading decisions.")

if __name__ == "__main__":
    main()