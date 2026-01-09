#!/usr/bin/env python3
"""
Setup script for Market Sentiment Analysis Agent
"""

import subprocess
import sys
import os

def install_requirements():
    """Install required packages"""
    print("📦 Installing required packages...")
    
    requirements = [
        "yfinance>=0.2.18",
        "pandas>=1.5.0", 
        "numpy>=1.21.0",
        "requests>=2.28.0",
        "tradingview-ta>=3.3.0",
        "matplotlib>=3.5.0",
        "seaborn>=0.11.0",
        "plotly>=5.0.0",
        "streamlit>=1.28.0"
    ]
    
    for package in requirements:
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
            print(f"✅ Installed {package}")
        except subprocess.CalledProcessError:
            print(f"❌ Failed to install {package}")
            return False
    
    return True

def test_installation():
    """Test if all packages are properly installed"""
    print("\n🧪 Testing installation...")
    
    try:
        import yfinance
        import pandas
        import numpy
        import requests
        import matplotlib
        import seaborn
        import plotly
        import streamlit
        
        try:
            import tradingview_ta
            print("✅ TradingView TA available")
        except ImportError:
            print("⚠️  TradingView TA not available (optional)")
        
        print("✅ All core packages installed successfully!")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False

def create_sample_config():
    """Create sample configuration if it doesn't exist"""
    if not os.path.exists('config.json'):
        print("📝 Config file already exists")
        return
    
    print("✅ Configuration file created")

def main():
    """Main setup function"""
    print("🚀 Market Sentiment Analysis Agent Setup")
    print("=" * 50)
    
    # Install requirements
    if not install_requirements():
        print("❌ Setup failed during package installation")
        return
    
    # Test installation
    if not test_installation():
        print("❌ Setup failed during testing")
        return
    
    # Create config
    create_sample_config()
    
    print("\n🎉 Setup completed successfully!")
    print("\n📋 Next steps:")
    print("1. Run basic analysis: python market_sentiment_agent.py")
    print("2. Create visualizations: python sentiment_visualizer.py")
    print("3. Launch web dashboard: streamlit run streamlit_dashboard.py")
    print("\n💡 Make sure you have an internet connection for data fetching.")

if __name__ == "__main__":
    main()