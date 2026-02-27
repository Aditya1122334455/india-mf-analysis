import pandas as pd
from mftool import Mftool
import datetime

class MFDataFetcher:
    def __init__(self):
        self.mf = Mftool()
        self._all_schemes = None

    def get_all_schemes(self):
        """Fetch all available schemes and cache them."""
        try:
            if self._all_schemes is None or len(self._all_schemes) < 100:
                self._all_schemes = self.mf.get_scheme_codes()
            return self._all_schemes
        except Exception as e:
            print(f"Error fetching scheme list: {e}")
            return {}

    def search_funds(self, query):
        """Search for funds matching the query string."""
        if not query: return {}
        
        schemes = self.get_all_schemes()
        if not schemes: return {}
        
        results = {}
        # Clean query: lowercase and remove special chars that might hinder matching
        clean_query = query.lower().replace("-", " ").replace(",", " ")
        query_parts = clean_query.split()
        
        for code, name in schemes.items():
            # Skip header or empty
            if not code or not name or str(code).strip().lower() == 'scheme code':
                continue
                
            name_str = str(name).lower().replace("-", " ").replace(",", " ")
            # Try to match: either all parts are present, or the full query is partially present
            if all(part in name_str for part in query_parts):
                results[code] = name
        
        # If no results and it's a single word, try partial matching
        if not results and len(query_parts) == 1:
            part = query_parts[0]
            for code, name in schemes.items():
                if part in str(name).lower():
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
        """Get detailed info about a fund."""
        try:
            info = self.mf.get_scheme_details(amfi_code)
            return info if info else {}
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
