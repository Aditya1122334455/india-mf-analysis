# Development Log: India Mutual Fund Analytics Dashboard

This document serves as a summary of the development journey, key technical decisions, and features implemented for the dashboard.

## 🚀 Project Overview
A professional-grade Mutual Fund Analytics dashboard for the Indian market, focusing on risk-adjusted returns, rolling performance, and market capture sensitivity.

---

## 🛠️ Technical Stack
- **Framework**: Streamlit (Web UI)
- **Data Sourcing**: `mftool` (AMFI Data), `yfinance` (Indices)
- **Visualization**: Plotly (Interactive Charts)
- **Analytics**: Pandas, NumPy, SciPy (Quantitative Math)

---

## ✨ Key Features Implemented

### 1. Performance & Risk Metrics
- **Dynamic CAGR & Growth**: Calculates annualized returns based on selected time horizons (1Y, 3Y, 5Y, 10Y, All Time).
- **Risk-Adjusted Ratios**: Real-time calculation of **Sharpe Ratio**, **Sortino Ratio**, and **Volatility**.
- **Max Drawdown**: Visual history of the deepest "peaks-to-troughs" to understand downside risk.

### 2. Rolling Returns Consistency
- **Visual Confidence**: 1Y, 3Y, and 5Y rolling return charts to see how a fund performs across different market cycles.
- **Consistency Table**: A mathematical breakdown showing the % of time a fund delivered returns in specific brackets (e.g., % times returns > 15%).

### 3. Advanced Benchmarking (Peer Comparison)
- **Dual Mode**: Choice between tracking against **Market Indices** (Nifty 50, Nifty 500) or **other Mutual Funds**.
- **Rebased Comparison**: Normalizes both the fund and benchmark to 100 to visualize the absolute "wealth gap" created over time.

### 4. Market Participation Analysis (Upside/Downside)
- **Capture Ratios**: Insight into how much of a market rally a fund "captures" vs. how much it protects during a crash.
- **Sensitivity Scatter Plot**: A monthly outperformance visual showing fund returns vs. benchmark returns with a trendline.

---

## 🔧 Major Technical Fixes & Revisions

### 🛡️ Robust Architecture
- **Short History Handling**: Implemented logic to detect funds with < 3 or 5 years of data, automatically labeling them as "Short Hist." or "S.I. (Since Inception)" to prevent misleading CAGR figures.
- **Empty Data Safety**: Fixed critical `IndexError` crashes that occurred when switching between benchmark types or when data failed to fetch.
- **Lean Metadata Model**: Initially attempted to scrape AUM/Expense Ratios from external sites; decided to remove this in favor of a **performance-first analytics model** to ensure data accuracy and speed.

### 📦 Deployment Readiness
- **Git Backups**: Version control established with specific snapshots for stability.
- **Streamlit Cloud**: Configured `requirements.txt` with specific dependencies (like `deprecated`) to ensure seamless hosting.

---

## 📝 Roadmap & Future Ideas
- [ ] Portfolio Overlap tool.
- [ ] SIP vs Lumpsum comparison calculator.
- [ ] Category-average benchmarking (Peer group comparison).

---
*Created on 2026-02-12*
