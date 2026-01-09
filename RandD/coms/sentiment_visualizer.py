#!/usr/bin/env python3
"""
Market Sentiment Visualizer for XAUUSD and XAGUSD
Creates charts and visual reports for sentiment analysis
"""

import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np
from datetime import datetime
import json
from market_sentiment_agent import MarketSentimentAgent

class SentimentVisualizer:
    """
    Creates visualizations for market sentiment analysis
    """
    
    def __init__(self):
        self.agent = MarketSentimentAgent()
        plt.style.use('seaborn-v0_8')
        
    def create_sentiment_dashboard(self, symbol: str, save_path: str = None):
        """Create a comprehensive sentiment dashboard"""
        # Get data and analysis
        data = self.agent.get_yahoo_data(symbol, period="3mo")
        sentiment_data = self.agent.get_comprehensive_sentiment(symbol)
        
        if data.empty or 'error' in sentiment_data:
            print(f"Cannot create dashboard for {symbol}: insufficient data")
            return
            
        # Create subplots
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        fig.suptitle(f'{sentiment_data["name"]} ({symbol}) - Market Sentiment Dashboard', 
                     fontsize=16, fontweight='bold')
        
        # 1. Price chart with moving averages
        ax1 = axes[0, 0]
        close_prices = data['Close']
        sma_20 = close_prices.rolling(window=20).mean()
        sma_50 = close_prices.rolling(window=50).mean()
        
        ax1.plot(data.index, close_prices, label='Price', linewidth=2, color='black')
        ax1.plot(data.index, sma_20, label='SMA 20', alpha=0.7, color='blue')
        ax1.plot(data.index, sma_50, label='SMA 50', alpha=0.7, color='red')
        ax1.set_title('Price & Moving Averages')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # 2. RSI
        ax2 = axes[0, 1]
        rsi = self.agent.calculate_rsi(close_prices)
        ax2.plot(data.index, rsi, label='RSI', color='purple', linewidth=2)
        ax2.axhline(y=70, color='r', linestyle='--', alpha=0.7, label='Overbought')
        ax2.axhline(y=30, color='g', linestyle='--', alpha=0.7, label='Oversold')
        ax2.axhline(y=50, color='gray', linestyle='-', alpha=0.5)
        ax2.set_title('Relative Strength Index (RSI)')
        ax2.set_ylim(0, 100)
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        # 3. MACD
        ax3 = axes[1, 0]
        macd_data = self.agent.calculate_macd(close_prices)
        ax3.plot(data.index, macd_data['macd'], label='MACD', color='blue')
        ax3.plot(data.index, macd_data['signal'], label='Signal', color='red')
        ax3.bar(data.index, macd_data['histogram'], label='Histogram', alpha=0.3, color='gray')
        ax3.set_title('MACD Indicator')
        ax3.legend()
        ax3.grid(True, alpha=0.3)
        
        # 4. Sentiment breakdown
        ax4 = axes[1, 1]
        sentiment_scores = sentiment_data['analysis']['sentiment_scores']
        indicators = list(sentiment_scores.keys())
        scores = list(sentiment_scores.values())
        
        colors = ['green' if score >= 50 else 'red' for score in scores]
        bars = ax4.barh(indicators, scores, color=colors, alpha=0.7)
        ax4.axvline(x=50, color='gray', linestyle='--', alpha=0.7)
        ax4.set_xlim(0, 100)
        ax4.set_title('Sentiment Indicators Breakdown')
        ax4.set_xlabel('Sentiment Score (0-100)')
        
        # Add score labels on bars
        for bar, score in zip(bars, scores):
            ax4.text(score + 1, bar.get_y() + bar.get_height()/2, 
                    f'{score:.1f}', va='center', fontweight='bold')
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"Dashboard saved to {save_path}")
        
        plt.show()
        
    def create_comparison_chart(self, save_path: str = None):
        """Create a comparison chart for both symbols"""
        results = {}
        for symbol in ['XAUUSD', 'XAGUSD']:
            sentiment_data = self.agent.get_comprehensive_sentiment(symbol)
            if 'error' not in sentiment_data:
                results[symbol] = sentiment_data
        
        if len(results) < 2:
            print("Insufficient data for comparison chart")
            return
            
        # Create comparison visualization
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
        
        # Overall sentiment comparison
        symbols = list(results.keys())
        names = [results[sym]['name'] for sym in symbols]
        sentiments = [results[sym]['overall_sentiment'] for sym in symbols]
        colors = ['green' if s >= 50 else 'red' for s in sentiments]
        
        bars1 = ax1.bar(names, sentiments, color=colors, alpha=0.7)
        ax1.axhline(y=50, color='gray', linestyle='--', alpha=0.7)
        ax1.set_ylim(0, 100)
        ax1.set_title('Overall Sentiment Comparison')
        ax1.set_ylabel('Sentiment Score (0-100)')
        
        # Add score labels
        for bar, score in zip(bars1, sentiments):
            ax1.text(bar.get_x() + bar.get_width()/2, score + 2, 
                    f'{score:.1f}', ha='center', fontweight='bold')
        
        # Detailed breakdown comparison
        indicators = list(results[symbols[0]]['analysis']['sentiment_scores'].keys())
        x = np.arange(len(indicators))
        width = 0.35
        
        gold_scores = [results['XAUUSD']['analysis']['sentiment_scores'][ind] for ind in indicators]
        silver_scores = [results['XAGUSD']['analysis']['sentiment_scores'][ind] for ind in indicators]
        
        ax2.bar(x - width/2, gold_scores, width, label='Gold (XAUUSD)', alpha=0.7, color='gold')
        ax2.bar(x + width/2, silver_scores, width, label='Silver (XAGUSD)', alpha=0.7, color='silver')
        
        ax2.set_xlabel('Indicators')
        ax2.set_ylabel('Sentiment Score')
        ax2.set_title('Detailed Sentiment Breakdown')
        ax2.set_xticks(x)
        ax2.set_xticklabels([ind.replace('_', ' ').title() for ind in indicators], rotation=45)
        ax2.legend()
        ax2.axhline(y=50, color='gray', linestyle='--', alpha=0.7)
        ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"Comparison chart saved to {save_path}")
            
        plt.show()
        
    def create_historical_sentiment_trend(self, symbol: str, days: int = 30, save_path: str = None):
        """Create historical sentiment trend analysis"""
        print(f"Analyzing {days}-day sentiment trend for {symbol}...")
        
        # This is a simplified version - in practice, you'd store historical sentiment data
        data = self.agent.get_yahoo_data(symbol, period=f"{days}d")
        if data.empty:
            print(f"No data available for {symbol}")
            return
            
        # Calculate rolling sentiment indicators
        close_prices = data['Close']
        rsi = self.agent.calculate_rsi(close_prices)
        macd_data = self.agent.calculate_macd(close_prices)
        
        # Create trend visualization
        fig, axes = plt.subplots(3, 1, figsize=(12, 10))
        fig.suptitle(f'{self.agent.symbols[symbol]["name"]} - {days} Day Trend Analysis', 
                     fontsize=14, fontweight='bold')
        
        # Price trend
        axes[0].plot(data.index, close_prices, linewidth=2, color='black')
        axes[0].set_title('Price Trend')
        axes[0].grid(True, alpha=0.3)
        
        # RSI trend
        axes[1].plot(data.index, rsi, color='purple', linewidth=2)
        axes[1].axhline(y=70, color='r', linestyle='--', alpha=0.7)
        axes[1].axhline(y=30, color='g', linestyle='--', alpha=0.7)
        axes[1].set_title('RSI Trend')
        axes[1].set_ylim(0, 100)
        axes[1].grid(True, alpha=0.3)
        
        # MACD trend
        axes[2].plot(data.index, macd_data['macd'], label='MACD', color='blue')
        axes[2].plot(data.index, macd_data['signal'], label='Signal', color='red')
        axes[2].bar(data.index, macd_data['histogram'], alpha=0.3, color='gray')
        axes[2].set_title('MACD Trend')
        axes[2].legend()
        axes[2].grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"Trend analysis saved to {save_path}")
            
        plt.show()

def main():
    """Main function for visualization demo"""
    visualizer = SentimentVisualizer()
    
    print("🎨 Market Sentiment Visualizer")
    print("=" * 50)
    
    # Create individual dashboards
    for symbol in ['XAUUSD', 'XAGUSD']:
        print(f"\nCreating dashboard for {symbol}...")
        visualizer.create_sentiment_dashboard(symbol)
    
    # Create comparison chart
    print("\nCreating comparison chart...")
    visualizer.create_comparison_chart()
    
    # Create trend analysis
    print("\nCreating trend analysis...")
    visualizer.create_historical_sentiment_trend('XAUUSD', days=60)

if __name__ == "__main__":
    main()