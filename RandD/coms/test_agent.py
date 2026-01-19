#!/usr/bin/env python3
"""
Test script for Market Sentiment Analysis Agent
"""

import sys
import traceback
from datetime import datetime

def test_basic_imports():
    """Test basic package imports"""
    print("🧪 Testing basic imports...")
    
    try:
        import pandas as pd
        import numpy as np
        import yfinance as yf
        print("✅ Core packages imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False

def test_optional_imports():
    """Test optional package imports"""
    print("🧪 Testing optional imports...")
    
    results = {}
    
    try:
        import tradingview_ta
        results['tradingview'] = True
        print("✅ TradingView TA available")
    except ImportError:
        results['tradingview'] = False
        print("⚠️  TradingView TA not available (will use fallback)")
    
    try:
        import matplotlib.pyplot as plt
        results['matplotlib'] = True
        print("✅ Matplotlib available")
    except ImportError:
        results['matplotlib'] = False
        print("⚠️  Matplotlib not available")
    
    try:
        import streamlit as st
        results['streamlit'] = True
        print("✅ Streamlit available")
    except ImportError:
        results['streamlit'] = False
        print("⚠️  Streamlit not available")
    
    return results

def test_yahoo_finance_connection():
    """Test Yahoo Finance data connection"""
    print("🧪 Testing Yahoo Finance connection...")
    
    try:
        import yfinance as yf
        
        # Test with a simple ticker
        ticker = yf.Ticker("GC=F")  # Gold futures
        data = ticker.history(period="5d")
        
        if not data.empty:
            print(f"✅ Yahoo Finance connection successful")
            print(f"   Retrieved {len(data)} days of data")
            print(f"   Latest price: ${data['Close'].iloc[-1]:.2f}")
            return True
        else:
            print("❌ No data retrieved from Yahoo Finance")
            return False
            
    except Exception as e:
        print(f"❌ Yahoo Finance connection failed: {e}")
        return False

def test_agent_basic_functionality():
    """Test basic agent functionality"""
    print("🧪 Testing agent basic functionality...")
    
    try:
        from market_sentiment_agent import MarketSentimentAgent
        
        agent = MarketSentimentAgent()
        print("✅ Agent initialized successfully")
        
        # Test data fetching
        data = agent.get_yahoo_data('XAUUSD', period='5d')
        if not data.empty:
            print(f"✅ Data fetching works ({len(data)} records)")
        else:
            print("⚠️  No data retrieved (might be market hours)")
        
        # Test indicator calculations
        if not data.empty:
            close_prices = data['Close']
            rsi = agent.calculate_rsi(close_prices)
            macd_data = agent.calculate_macd(close_prices)
            
            if not rsi.empty and not macd_data['macd'].empty:
                print("✅ Technical indicators calculation works")
                print(f"   Latest RSI: {rsi.iloc[-1]:.2f}")
                print(f"   Latest MACD: {macd_data['macd'].iloc[-1]:.4f}")
            else:
                print("⚠️  Insufficient data for indicators")
        
        return True
        
    except Exception as e:
        print(f"❌ Agent functionality test failed: {e}")
        traceback.print_exc()
        return False

def test_sentiment_analysis():
    """Test full sentiment analysis"""
    print("🧪 Testing sentiment analysis...")
    
    try:
        from market_sentiment_agent import MarketSentimentAgent
        
        agent = MarketSentimentAgent()
        sentiment_data = agent.get_comprehensive_sentiment('XAUUSD')
        
        if 'error' not in sentiment_data:
            print("✅ Sentiment analysis successful")
            print(f"   Symbol: {sentiment_data['symbol']}")
            print(f"   Sentiment: {sentiment_data['sentiment_label']}")
            print(f"   Score: {sentiment_data['overall_sentiment']:.1f}/100")
            return True
        else:
            print(f"❌ Sentiment analysis failed: {sentiment_data['error']}")
            return False
            
    except Exception as e:
        print(f"❌ Sentiment analysis test failed: {e}")
        return False

def main():
    """Main test function"""
    print("🚀 Market Sentiment Agent - Test Suite")
    print("=" * 60)
    print(f"Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    tests = [
        ("Basic Imports", test_basic_imports),
        ("Optional Imports", test_optional_imports),
        ("Yahoo Finance Connection", test_yahoo_finance_connection),
        ("Agent Basic Functionality", test_agent_basic_functionality),
        ("Sentiment Analysis", test_sentiment_analysis)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"❌ Test '{test_name}' crashed: {e}")
            results[test_name] = False
        print()
    
    # Summary
    print("📋 TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for result in results.values() if result is True)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result is True else "❌ FAIL" if result is False else "⚠️  PARTIAL"
        print(f"{status} {test_name}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The agent is ready to use.")
        print("\n📋 Next steps:")
        print("1. Run: python market_sentiment_agent.py")
        print("2. Try: python sentiment_visualizer.py")
        print("3. Launch: streamlit run streamlit_dashboard.py")
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
        print("   The agent may still work with limited functionality.")
    
    print(f"\nTest completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()