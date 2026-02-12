import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
from src.data_fetcher import MFDataFetcher
from src.analytics import MFAnalytics
from src.components.charts import (
    plot_nav_history, plot_rolling_returns, plot_drawdown, 
    plot_returns_distribution, plot_benchmark_comparison, plot_capture_ratios
)

# Page Configuration
st.set_page_config(page_title="India Mutual Fund Analytics", page_icon="📈", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stMetric {
        background-color: #ffffff;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        border: 1px solid #eef2f6;
    }
    .metric-card {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        border: 1px solid #eef2f6;
        margin-bottom: 20px;
    }
    div[data-testid="stSidebar"] {
        background-color: #f0f2f6;
    }
    </style>
    """, unsafe_allow_html=True)

def get_tools():
    return MFDataFetcher(), MFAnalytics()

fetcher, analytics = get_tools()

# Sidebar - Search and Selection
with st.sidebar:
    st.title("📈 MF Analytics")
    st.caption("India Mutual Fund Analytics")
    st.markdown("---")
    st.header("🔍 Fund Discovery")
    search_query = st.text_input("Mutual Fund Name", placeholder="e.g. HDFC Flexi Cap")
    
    selected_code = None
    if search_query:
        search_results = fetcher.search_funds(search_query)
        if search_results:
            selected_name = st.selectbox("Matching Schemes", options=list(search_results.values()))
            selected_code = [k for k, v in search_results.items() if v == selected_name][0]
        else:
            st.error("No funds found.")

    st.markdown("---")
    st.header("⚙️ Analysis Settings")
    risk_free_rate = st.slider("Risk Free Rate (%)", 0.0, 10.0, 6.5, 0.1) / 100
    analytics.rf = risk_free_rate
    
    bench_type = st.radio("Benchmark Type", ["Index", "Mutual Fund"], horizontal=True)
    
    benchmark_code = None
    benchmark_name = "Benchmark"
    benchmark_ticker = None

    if bench_type == "Index":
        bench_option = st.selectbox("Select Index", ["^NSEI (Nifty 50)", "^CRSLDX (Nifty 500)"], index=0)
        benchmark_ticker = bench_option.split(" ")[0]
        benchmark_name = bench_option.split("(")[1].replace(")", "")
    else:
        bench_search = st.text_input("Search Benchmark Fund", placeholder="e.g. Parag Parikh")
        if bench_search:
            bench_results = fetcher.search_funds(bench_search)
            if bench_results:
                benchmark_name = st.selectbox("Select Benchmark Fund", options=list(bench_results.values()))
                benchmark_code = [k for k, v in bench_results.items() if v == benchmark_name][0]
            else:
                st.error("No benchmark funds found.")
    
    st.markdown("---")
    st.header("⏳ Time Horizon")
    analysis_period = st.radio(
        "Select Analysis Period",
        ["All Time", "1 Year", "3 Years", "5 Years", "10 Years"],
        index=0
    )

# Main Content
if selected_code:
    with st.spinner(f"Analyzing {selected_name}..."):
        raw_nav_data = fetcher.get_nav_history(selected_code)
        fund_info = fetcher.get_fund_info(selected_code)
        
        if not raw_nav_data.empty:
            # Determine start date for benchmark based on available fund history
            raw_start_date = raw_nav_data.index[0]
            
            if bench_type == "Index":
                raw_bench_data = fetcher.get_benchmark_history(benchmark_ticker, start_date=raw_start_date)
            else:
                if benchmark_code:
                    if benchmark_code == selected_code:
                        st.warning("Comparing a fund against itself. Benchmark data will be identical.")
                    raw_bench_data_df = fetcher.get_nav_history(benchmark_code)
                    raw_bench_data = raw_bench_data_df['nav'] if not raw_bench_data_df.empty else pd.Series()
                else:
                    raw_bench_data = pd.Series()
            
            # Apply Time Period Filtering
            nav_data = raw_nav_data.copy()
            bench_data = raw_bench_data.copy() if not raw_bench_data.empty else pd.Series()
            
            if analysis_period != "All Time":
                years = int(analysis_period.split(" ")[0])
                cutoff_date = nav_data.index[-1] - pd.DateOffset(years=years)
                nav_data = nav_data[nav_data.index >= cutoff_date]
                if not bench_data.empty:
                    bench_data = bench_data[bench_data.index >= cutoff_date]

    if not raw_nav_data.empty:
        # Fund Title & Stats Summary
        st.markdown(f"### {selected_name}")
        st.caption(f"**{fund_info.get('scheme_type', 'N/A')}** | {fund_info.get('scheme_category', 'N/A')} | {fund_info.get('fund_house', 'N/A')}")
        st.markdown("---")

        # Top Level Metrics - Single Row
        metrics = analytics.calculate_risk_metrics(nav_data['nav'])
        _, max_dd = analytics.calculate_drawdowns(nav_data['nav'])
        multiplier = analytics.calculate_fund_multiplier(nav_data['nav'])
        
        # Clarify Period Label if actual history is shorter than selection
        actual_days = (nav_data.index[-1] - nav_data.index[0]).days
        actual_yrs = actual_days / 365.25
        
        # Determine if we should show 'Since Inception' or the selected period
        is_si = False
        if analysis_period != "All Time":
            req_yrs = int(analysis_period.split(" ")[0])
            if actual_yrs < (req_yrs - 0.1): # If significantly shorter than requested
                is_si = True
        
        display_label = f"S.I. (~{actual_yrs:.1f}Y)" if (is_si or analysis_period == "All Time") else analysis_period

        m_col0, m_col1, m_col2, m_col3, m_col4 = st.columns(5)
        m_col0.metric(f"Growth ({display_label})", f"{multiplier:.2f}x")
        m_col1.metric(f"CAGR ({display_label})", f"{metrics.get('cagr', 0):.1%}")
        m_col2.metric("Volatility", f"{metrics.get('volatility', 0):.1%}")
        m_col3.metric("Sharpe Ratio", f"{metrics.get('sharpe_ratio', 0):.2f}")
        m_col4.metric("Max Drawdown", f"{max_dd:.1%}")

        # 1. Performance History (Rebased to 100)
        st.markdown("### 📈 Performance & Drawdown")
        if not bench_data.empty:
            st.plotly_chart(plot_benchmark_comparison(nav_data['nav'], bench_data, selected_name, benchmark_name), width='stretch', key="main_perf_comparison")
        else:
            st.plotly_chart(plot_nav_history(nav_data, selected_name), width='stretch', key="main_nav_history")

        # 2. Drawdown History
        drawdown_series, _ = analytics.calculate_drawdowns(nav_data['nav'])
        st.plotly_chart(plot_drawdown(drawdown_series), width='stretch', key="main_drawdown_history")
        
        # Performance Analysis Data Prep
        def get_stats_for_period(series, years, bench_series=None):
            if series.empty: return None, None, None
            
            # Check if fund has enough history for the requested 'years'
            total_days = (series.index[-1] - series.index[0]).days
            if total_days < (years * 365 - 30): # 30 day grace period for holidays/launch gaps
                return None, None, None

            target_date = series.index[-1] - pd.DateOffset(years=years)
            try:
                subset = series.loc[series.index >= target_date]
                if len(subset) < 20: return None, None, None
                
                # Annualized Return
                start_val = subset.iloc[0]
                end_val = series.iloc[-1]
                ann_ret = (end_val / start_val) ** (1/years) - 1
                
                # Annualized Volatility
                daily_rets = subset.pct_change().dropna()
                ann_vol = daily_rets.std() * np.sqrt(252)

                # Ratios & Capture if bench provided
                ratios = {}
                if bench_series is not None and not bench_series.empty:
                    b_subset = bench_series.loc[bench_series.index >= target_date]
                    if len(b_subset) >= 20:
                        ab = analytics.calculate_alpha_beta(subset, b_subset)
                        rm = analytics.calculate_risk_metrics(subset)
                        cap = analytics.calculate_capture_ratios(subset, b_subset)
                        ratios = {
                            'Alpha': ab['alpha'],
                            'Beta': ab['beta'],
                            'R-Squared': ab['r_squared'],
                            'Sortino': rm.get('sortino_ratio', 0),
                            'Upside': cap['upside'],
                            'Downside': cap['downside']
                        }
                
                return ann_ret, ann_vol, ratios
            except:
                return None, None, None

        periods = {"1 Year": 1, "3 Years": 3, "5 Years": 5, "10 Years": 10}
        ret_data, vol_data, ratio_data, deep_metrics = [], [], [], []
        
        for label, yrs in periods.items():
            f_ret, f_vol, f_stats = get_stats_for_period(raw_nav_data['nav'], yrs, raw_bench_data)
            
            b_ret, b_vol = None, None
            if not raw_bench_data.empty and len(raw_bench_data) > 0:
                try:
                    b_target_date = raw_bench_data.index[-1] - pd.DateOffset(years=yrs)
                    b_subset = raw_bench_data.loc[raw_bench_data.index >= b_target_date]
                    if len(b_subset) > 20:
                        b_ret = (b_subset.iloc[-1] / b_subset.iloc[0]) ** (1/yrs) - 1
                        b_vol = b_subset.pct_change().std() * np.sqrt(252)
                except:
                    pass
            
            # Data for compact sections
            ret_data.append({"Period": label, "Fund": f_ret, f"{benchmark_name}": b_ret})
            vol_data.append({"Period": label, "Fund": f_vol, f"{benchmark_name}": b_vol})
            
            f_rat = (f_ret / f_vol) if f_ret and f_vol else None
            b_rat = (b_ret / b_vol) if b_ret and b_vol else None
            ratio_data.append({"Period": label, "Fund": f_rat, f"{benchmark_name}": b_rat})

            if f_stats:
                deep_metrics.append({
                    "Period": label,
                    "Alpha": f"{f_stats['Alpha']:.1%}",
                    "Beta": f"{f_stats['Beta']:.2f}",
                    "R2": f"{f_stats['R-Squared']:.1%}",
                    "Sortino": f"{f_stats['Sortino']:.2f}",
                    "Upside Cap": f"{f_stats['Upside']:.1f}%",
                    "Downside Cap": f"{f_stats['Downside']:.1f}%"
                })

        def display_metric_section(title, data_list, is_pct=True):
            st.markdown(f"#### {title}")
            df = pd.DataFrame(data_list)
            col_tbl, col_cht = st.columns([1, 1.5])
            with col_tbl:
                display_df = df.copy()
                for col in ["Fund", benchmark_name]:
                    display_df[col] = display_df[col].apply(lambda x: f"{x:.1%}" if is_pct and pd.notnull(x) else (f"{x:.2f}" if pd.notnull(x) else "-"))
                st.dataframe(display_df, hide_index=True, width='stretch', column_config={"Period": st.column_config.TextColumn(width="small")})
            with col_cht:
                plot_df = df.melt(id_vars="Period", var_name="Type", value_name="Value")
                fig = px.bar(plot_df, x="Period", y="Value", color="Type", barmode="group", color_discrete_sequence=['#1f77b4', '#ff7f0e'], height=180)
                fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), showlegend=True, xaxis_title=None, yaxis_title=None)
                if is_pct: fig.update_yaxes(tickformat=".0%")
                st.plotly_chart(fig, width='stretch', key=f"bar_{title.lower().replace(' ', '_')}")

        display_metric_section("Periodic Returns", ret_data)
        display_metric_section("Periodic Volatility", vol_data)
        display_metric_section("Return / Risk Ratio", ratio_data, is_pct=False)

        # 3. Market Participation Insight
        st.markdown("### 🎯 Market Participation & Efficiency")
        if not bench_data.empty and len(bench_data) > 20:
            c1, c2 = st.columns([1.2, 1])
            with c1:
                # Scatter Plot for Insight: Fund Monthly vs Benchmark Monthly
                df_monthly = pd.DataFrame({'Fund': nav_data['nav'], 'Bench': bench_data}).resample('ME').last().pct_change().dropna()
                fig_scatter = px.scatter(df_monthly, x='Bench', y='Fund', trendline="ols",
                                         title="Monthly Performance Sensitivity",
                                         labels={'Bench': f'{benchmark_name} Return', 'Fund': 'Fund Return'})
                # Add diagonal y=x line
                lims = [min(df_monthly.min()), max(df_monthly.max())]
                fig_scatter.add_shape(type="line", x0=lims[0], y0=lims[0], x1=lims[1], y1=lims[1], line=dict(color="gray", dash="dash"))
                fig_scatter.update_layout(height=400, template="plotly_white")
                fig_scatter.update_xaxes(tickformat=".0%")
                fig_scatter.update_yaxes(tickformat=".0%")
                st.plotly_chart(fig_scatter, width='stretch', key="market_sensitivity_scatter")
                st.info(f"**Interpretation:** Points above the dashed line indicate months where the fund outperformed {benchmark_name}. A steeper trendline than the dashed line suggests a high-beta fund.")
            
            with c2:
                cap_metrics = analytics.calculate_capture_ratios(nav_data['nav'], bench_data)
                st.plotly_chart(plot_capture_ratios(cap_metrics), width='stretch', key="capture_ratios_summary")
        
        if deep_metrics:
            st.markdown("#### Historical Performance Metrics")
            st.dataframe(pd.DataFrame(deep_metrics), hide_index=True, width='stretch')
        
        # 4. Rolling Returns Profile
        st.markdown("---")
        st.markdown("### 📊 Rolling Returns Performance")
        rolling_profile = analytics.calculate_rolling_return_profile(raw_nav_data['nav'])
        
        if rolling_profile:
            profile_df = pd.DataFrame(rolling_profile)
            row_order = [
                "Minimum", "Median", "Maximum", 
                "% times -ve returns", 
                "% times returns 0 - 5%", 
                "% times returns 5 - 10%", 
                "% times returns 10 - 15%", 
                "% times returns 15 - 20%", 
                "% times returns > 20%"
            ]
            profile_df = profile_df.reindex(row_order)
            
            # Professionally highlight insufficient history
            def format_rolling(val):
                if pd.isna(val) or val is None:
                    return "Short Hist."
                return f"{val:.1%}"

            st.dataframe(
                profile_df.map(format_rolling),
                width='stretch',
                column_config={
                    "index": st.column_config.TextColumn("Returns Statistic", width="medium"),
                    "1 Year": st.column_config.TextColumn(width="small"),
                    "3 Years": st.column_config.TextColumn(width="small"),
                    "5 Years": st.column_config.TextColumn(width="small"),
                }
            )
        else:
            st.info("Insufficient history for rolling return profile (requires at least 1 year of data).")
        
        if not deep_metrics and not bench_data.empty:
            st.warning("Insufficient history for detailed periodic metrics.")

    else:
        st.error("Historical NAV data unavailable.")

else:
    st.info("👈 Enter a fund name (e.g., 'HDFC Flexi' or 'SBI Bluechip') to begin deep analysis.")
