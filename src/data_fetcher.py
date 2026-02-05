import pandas as pd
from mftool import Mftool
import datetime

class MFDataFetcher:
    def __init__(self):
        self.mf = Mftool()
        self._all_schemes = None

    def get_all_schemes(self):
        """Fetch all available schemes and cache them."""
        if self._all_schemes is None:
            self._all_schemes = self.mf.get_scheme_codes()
        return self._all_schemes

    def search_funds(self, query):
        """Search for funds matching the query string."""
        schemes = self.get_all_schemes()
        results = {}
        query_parts = query.lower().split()
        
        for code, name in schemes.items():
            # Skip header or empty
            if not code or not name or code == 'Scheme Code':
                continue
                
            name_str = str(name).lower()
            if all(part in name_str for part in query_parts):
                results[code] = name
        return results

    def get_nav_history(self, amfi_code):
        """Fetch historical NAV for a given AMFI code and return a DataFrame."""
        try:
            data = self.mf.get_scheme_historical_nav(amfi_code, as_Dataframe=True)
            if data is None or data.empty:
                return pd.DataFrame()
            
            # Convert to standard format
            df = data.copy()
            
            # If date is the index, reset it to process as column or handle directly
            if 'nav' in df.columns:
                df['nav'] = pd.to_numeric(df['nav'], errors='coerce')
            
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'], dayfirst=True)
            elif df.index.name == 'date' or not df.index.is_numeric():
                # Date is likely the index
                df.index = pd.to_datetime(df.index, dayfirst=True)
                df = df.sort_index()
                return df
                
            df = df.sort_values('date')
            df = df.set_index('date')
            return df
        except Exception as e:
            print(f"Error fetching NAV for {amfi_code}: {e}")
            return pd.DataFrame()

    def get_fund_info(self, amfi_code):
        """Get detailed info about a fund, merging with local metadata if available."""
        try:
            import json
            import os
            
            info = self.mf.get_scheme_details(amfi_code)
            
            # Load local metadata for extra details (AUM, Expense Ratio, Managers)
            meta_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'fund_metadata.json')
            if os.path.exists(meta_path):
                with open(meta_path, 'r') as f:
                    metadata = json.load(f)
                    if str(amfi_code) in metadata:
                        info.update(metadata[str(amfi_code)])
            
            return info
        except Exception as e:
            print(f"Error fetching details for {amfi_code}: {e}")
            return {}

    def get_benchmark_history(self, ticker='^NSEI', start_date=None):
        """Fetch benchmark history using yfinance."""
        import yfinance as yf
        try:
            # Added auto_adjust=True to fix FutureWarning
            bench = yf.download(ticker, start=start_date, progress=False, auto_adjust=True)
            if bench.empty: return pd.Series()
            
            # Ensure we return a 1D Series even if yfinance returns a DataFrame
            # (which can happen with MultiIndex results)
            close_data = bench['Close']
            if isinstance(close_data, pd.DataFrame):
                close_data = close_data.iloc[:, 0]
            
            return close_data.squeeze()
        except Exception as e:
            print(f"Error fetching benchmark {ticker}: {e}")
            return pd.Series()

    def get_peers(self, category, current_amfi_code):
        """Find other funds in the same category."""
        schemes = self.get_all_schemes()
        peers = {}
        # This is a bit slow as we need to check details for many funds
        # In a real app, we'd have a database of categories.
        # For this tool, we'll limit the search or use a heuristic.
        # For now, let's just return a few hardcoded peers or similar named ones
        # to demonstrate the UI.
        return peers

if __name__ == "__main__":
    # Test
    fetcher = MFDataFetcher()
    results = fetcher.search_funds("HDFC Top 100")
    print(f"Search results: {results}")
    if results:
        code = list(results.keys())[0]
        nav = fetcher.get_nav_history(code)
        print(f"NAV History for {code}:\n{nav.tail()}")
        info = fetcher.get_fund_info(code)
        print(f"Fund Info: {info.get('scheme_name')}")
