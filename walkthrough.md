# Professional Mutual Fund Analysis Tool - Walkthrough

This tool provides institutional-grade analytics for Indian Mutual Funds, inspired by platforms like AdvisorKhoj.

## 🚀 Key Features

### 1. Advanced Performance Analytics
- **CAGR**: Cumulative Annualized Growth Rate over the entire fund history.
- **Rolling Returns**: Evaluate consistency by looking at returns across different windows (1Y, 3Y, 5Y).
- **Growth Multiplier**: Instantly see how many times your initial investment would have grown.

### 2. 💰 SIP Analysis
- **Monthly Simulator**: Input any SIP amount and see the total invested value vs. current market value.
- **Absolute Gains**: Calculated based on the first business day of every month.

### 3. ⚖️ Risk & Benchmarking
- **Alpha**: The fund's ability to beat the benchmark (e.g., Nifty 50).
- **Beta**: Measures the fund's volatility relative to the market.
- **Sharpe & Sortino Ratios**: Risk-adjusted returns focusing on total volatility and downside risk respectively.
- **R-Squared**: Understanding how closely the fund follows its benchmark.

### 4. 🎯 Market Capture Ratios
- **Upside Capture**: How much of the market's gains the fund captures during positive months.
- **Downside Capture**: How much of the market's losses the fund participates in. (Pro tip: Lower is better!)
- **Benchmark Comparison**: Visual overlay of fund NAV vs. rebased benchmark (Nifty 50, Sensex, etc.).

## 🛠️ Tech Stack
- **Frontend**: Streamlit
- **Data Source**: `mftool` (AMFI Data), `yfinance` (NSE/BSE Benchmarks)
- **Visuals**: Plotly Interactive Charts
- **Math**: Pandas, NumPy, SciPy

## 🏃 How to Run
```bash
streamlit run mf_analysis/mf_dashboard.py
```

## 📂 Project Structure
- `mf_dashboard.py`: Main UI and layout logic.
- `src/analytics.py`: Mathematical core for risk and return calculations.
- `src/data_fetcher.py`: Data retrieval and cleaning from multiple sources.
- `src/components/charts.py`: Reusable Plotly visualization components.
