import requests
import time
from datetime import datetime
import json

class StockFetcher:
    """Fetch real-time stock data"""
    
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://www.alphavantage.co/query"
    
    def get_realtime_quote(self, symbol):
        """Get current stock price"""
        params = {
            'function': 'GLOBAL_QUOTE',
            'symbol': symbol,
            'apikey': self.api_key
        }
        
        try:
            response = requests.get(self.base_url, params=params)
            data = response.json()
            
            if 'Global Quote' in data:
                quote = data['Global Quote']
                return {
                    'symbol': symbol,
                    'price': float(quote.get('05. price', 0)),
                    'volume': int(quote.get('06. volume', 0)),
                    'timestamp': datetime.now(),
                    'change_percent': float(quote.get('10. change percent', '0').rstrip('%'))
                }
        except Exception as e:
            print(f"Error fetching {symbol}: {e}")
            return None
    
    def stream_quotes(self, symbols, interval_seconds=5):
        """Stream quotes continuously"""
        while True:
            for symbol in symbols:
                quote = self.get_realtime_quote(symbol)
                if quote:
                    yield quote
                time.sleep(interval_seconds)

# Test code - only runs when executing this file directly
if __name__ == "__main__":
    try:
        from config import API_KEY
    except ImportError:
        API_KEY = "YOUR_API_KEY_HERE"
    
    fetcher = StockFetcher(API_KEY)
    
    # Test symbols
    symbols = ['AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA']
    
    print("Testing single fetch (not streaming)...")
    for symbol in symbols:
        quote = fetcher.get_realtime_quote(symbol)
        if quote:
            print(f"{quote['symbol']}: ${quote['price']:.2f} ({quote['change_percent']:.2f}%)")
    
    print("Test complete!")