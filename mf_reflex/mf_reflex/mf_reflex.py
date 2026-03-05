import reflex as rx
from src.data_fetcher import MFDataFetcher
from src.analytics import MFAnalytics
import pandas as pd
import numpy as np

class State(rx.State):
    """The App State with Reactive logic."""
    search_query: str = ""
    is_loading: bool = False
    fund_name: str = "Search a fund to begin analysis"
    latest_nav: str = "₹0.00"
    cagr: str = "0.0%"
    volatility: str = "0.0%"
    max_drawdown: str = "0.0%"
    multiplier: str = "1.00x"
    results_found: bool = False
    
    # Advanced Config
    analysis_period: str = "3Y"
    custom_start_date: str = "2020-01-01"
    custom_end_date: str = ""
    risk_free_rate: float = 5.3

    # Benchmark Config
    selected_benchmark: str = "^NSEI"
    benchmark_display_name: str = "Nifty 50"
    bench_type: str = "Index"
    bench_search_query: str = ""
    selected_bench_fund_code: str = ""
    available_bench_funds: list[str] = []
    bench_fund_map: dict[str, str] = {}
    benchmark_map: dict[str, str] = {
        "^NSEI": "NIFTY 50",
        "^CRSLDX": "NIFTY 500",
        "^NSEMDCP100": "MIDCAP 100",
        "^NSESCP100": "SMALLCAP 100",
    }
    
    # Chart Data
    compare_plot_data: list[dict[str, any]] = []    # Rebased Growth (Fund vs Benchmark)
    drawdown_plot_data: list[dict[str, any]] = []   # Drawdown series
    calendar_plot_data: list[dict[str, any]] = []   # Annual returns
    rolling_plot_data: list[dict[str, any]] = []    # Rolling returns series
    
    # Advanced Metrics
    sharpe_ratio: str = "0.00"
    sortino_ratio: str = "0.00"
    beta: str = "0.00"
    jensen_alpha: str = "0.0%"
    hurst_exp: str = "0.00"
    batting_avg: str = "0.0%"
    upside_capture: str = "0.0%"
    downside_capture: str = "0.0%"
    
    # Detailed Tabular Data
    periodic_returns: list[list[str]] = []
    periodic_volatility: list[list[str]] = []
    periodic_ratios: list[list[str]] = []
    deep_metrics_table: list[list[str]] = []
    rolling_profile_table: list[list[str]] = []
    
    # Scatter Chart Data
    scatter_plot_data: list[dict[str, any]] = []

    def set_search_query(self, query: str):

        self.search_query = query
        
    def set_bench_type(self, value: str):
        self.bench_type = value
        
    def set_bench_search(self, query: str):
        self.bench_search_query = query
        if len(query) > 2:
            fetcher = MFDataFetcher()
            results = fetcher.search_funds(query)
            self.available_bench_funds = [v for k, v in results.items()][:20] if results else []
            self.bench_fund_map = {v: k for k, v in results.items()} if results else {}

    def set_bench_fund(self, name: str):
        if name in self.bench_fund_map:
            self.selected_bench_fund_code = self.bench_fund_map[name]
        if self.results_found:
            return self.handle_search()

    def set_benchmark(self, value: str):
        self.selected_benchmark = value
        self.benchmark_display_name = self.benchmark_map.get(value, "Nifty 50")
        if self.results_found:
            return self.handle_search()

    def set_analysis_period(self, value: str | list[str]):
        self.analysis_period = str(value)
        if self.results_found:
            return self.handle_search()
            
    def set_risk_free_rate(self, value: list[float]):
        self.risk_free_rate = float(value[0])
        if self.results_found:
            return self.handle_search()
            
    def set_custom_start(self, date: str):
        self.custom_start_date = date
        if self.analysis_period == "Custom Range" and self.results_found:
            return self.handle_search()
            
    def set_custom_end(self, date: str):
        self.custom_end_date = date
        if self.analysis_period == "Custom Range" and self.results_found:
            return self.handle_search()

    def handle_search(self):
        """Perform full analysis and update all datasets."""
        if not self.search_query:
            return
            
        self.is_loading = True
        yield
        
        fetcher = MFDataFetcher()
        analytics = MFAnalytics(risk_free_rate=self.risk_free_rate / 100.0)
        
        search_results = fetcher.search_funds(self.search_query)
        if search_results:
            self.results_found = True
            code = list(search_results.keys())[0]
            self.fund_name = search_results[code]
            
            # 1. Fetch Master Data
            raw_nav_data = fetcher.get_nav_history(code)
            
            if self.bench_type == "Index":
                raw_bench_data = fetcher.get_benchmark_history(self.selected_benchmark)
            else:
                if self.selected_bench_fund_code:
                    raw_bench_data_df = fetcher.get_nav_history(self.selected_bench_fund_code)
                    raw_bench_data = raw_bench_data_df['nav'] if not raw_bench_data_df.empty else pd.Series()
                    self.benchmark_display_name = "Benchmark Fund"
                else:
                    raw_bench_data = pd.Series()

            
            if raw_nav_data.empty:
                self.fund_name = "Data unavailable."
                self.results_found = False
                self.is_loading = False
                return

            # 2. Date Filtering & Standardizing (Ensure naive for joining)
            nav_data = raw_nav_data.copy()
            if nav_data.index.tz is not None:
                nav_data.index = nav_data.index.tz_localize(None)
                
            bench_data = raw_bench_data.copy()
            if not bench_data.empty and bench_data.index.tz is not None:
                bench_data.index = bench_data.index.tz_localize(None)
            
            if self.analysis_period == "Custom Range":
                if self.custom_start_date:
                    try:
                        start_ts = pd.Timestamp(self.custom_start_date)
                        nav_data = nav_data[nav_data.index >= start_ts]
                        if not bench_data.empty: bench_data = bench_data[bench_data.index >= start_ts]
                    except: pass
                if self.custom_end_date:
                    try:
                        end_ts = pd.Timestamp(self.custom_end_date)
                        nav_data = nav_data[nav_data.index <= end_ts]
                        if not bench_data.empty: bench_data = bench_data[bench_data.index <= end_ts]
                    except: pass
            elif self.analysis_period != "All Time":
                years = int(self.analysis_period.replace("Y", ""))
                cutoff = nav_data.index[-1] - pd.DateOffset(years=years)
                nav_data = nav_data[nav_data.index >= cutoff]
                if not bench_data.empty:
                    bench_data = bench_data[bench_data.index >= cutoff]

            print(f"DEBUG: Nav data points: {len(nav_data)}")
            print(f"DEBUG: Bench data points: {len(bench_data)}")

            # 3. Core Metrics
            self.latest_nav = f"₹{nav_data['nav'].iloc[-1]:.2f}"
            cagr_val = analytics.calculate_cagr(nav_data['nav'])
            self.cagr = f"{cagr_val:.1%}"
            risk = analytics.calculate_risk_metrics(nav_data['nav'])
            self.volatility = f"{risk.get('volatility', 0):.1%}"
            self.sharpe_ratio = f"{risk.get('sharpe_ratio', 0):.2f}"
            self.sortino_ratio = f"{risk.get('sortino_ratio', 0):.2f}"
            
            dd_series, m_dd = analytics.calculate_drawdowns(nav_data['nav'])
            self.max_drawdown = f"{m_dd:.1%}"
            self.multiplier = f"{analytics.calculate_fund_multiplier(nav_data['nav']):.2f}x"
            
            # 4. Deep Metrics & Scatter Plot
            if not bench_data.empty:
                deep = analytics.calculate_deep_metrics(nav_data['nav'], bench_data)
                self.beta = f"{deep.get('Beta', 0):.2f}"
                self.jensen_alpha = f"{deep.get('Jensen Alpha', 0):.1%}"
                self.hurst_exp = f"{deep.get('Hurst (H)', 0):.2f}"
                self.upside_capture = f"{deep.get('Upside Capture', 0):.1%}"
                self.downside_capture = f"{deep.get('Downside Capture', 0):.1%}"
                
                # Market Participation Scatter (Monthly Returns)
                df_monthly = pd.DataFrame({'fund': nav_data['nav'], 'bench': bench_data}).resample('ME').last().pct_change().dropna()
                if len(df_monthly) > 200:
                    step = max(1, len(df_monthly)//200)
                    df_monthly = df_monthly.iloc[::step]
                self.scatter_plot_data = [
                    {"bench": round(float(row["bench"])*100, 2), "fund": round(float(row["fund"])*100, 2)}
                    for _, row in df_monthly.iterrows()
                ]
            
            # 5. Chart Data: Rebased Performance
            f_rebased = (nav_data['nav'] / nav_data['nav'].iloc[0]) * 100
            if not bench_data.empty:
                b_rebased = (bench_data / bench_data.iloc[0]) * 100
                combined = pd.DataFrame({"fund": f_rebased, "bench": b_rebased}).fillna(method='ffill')
            else:
                combined = pd.DataFrame({"fund": f_rebased})

            if len(combined) > 200:
                step = max(1, len(combined)//200)
                combined = combined.iloc[::step]

            self.compare_plot_data = [
                {"date": str(idx.date()), "fund": round(float(row["fund"]), 2), "bench": round(float(row["bench"]), 2) if "bench" in row and not pd.isna(row["bench"]) else None}
                for idx, row in combined.iterrows()
            ]

            # 6. Chart Data: Drawdowns
            if len(dd_series) > 200:
                step = max(1, len(dd_series)//200)
                dd_series = dd_series.iloc[::step]
            self.drawdown_plot_data = [
                {"date": str(idx.date()), "drawdown": round(float(val)*100, 2)}
                for idx, val in dd_series.items()
            ]

            # 7. Chart Data: Calendar Performance
            f_cal = analytics.calculate_calendar_returns(raw_nav_data['nav'])
            if not raw_bench_data.empty:
                b_cal = analytics.calculate_calendar_returns(raw_bench_data)
                years = sorted(list(set(f_cal.index) | set(b_cal.index)), reverse=True)[:10]
                self.calendar_plot_data = [
                    {
                        "year": str(y), 
                        "fund": round(float(f_cal.get(y, 0))*100, 1), 
                        "bench": round(float(b_cal.get(y, 0))*100, 1)
                    }
                    for y in years
                ][::-1] 

            # 8. Rolling Returns (1Y Rolling) Chart
            rolling = analytics.calculate_rolling_returns(nav_data['nav'], window_years=1)
            if not rolling.empty:
                if len(rolling) > 200:
                    step = max(1, len(rolling)//200)
                    rolling = rolling.iloc[::step]
                self.rolling_plot_data = [
                    {"date": str(idx.date()), "rolling": round(float(val)*100, 2)}
                    for idx, val in rolling.items()
                ]

            # 9. Complex Tabular Data Generation (Periodic)
            periods = {"1 Year": 1, "3 Years": 3, "5 Years": 5, "10 Years": 10}
            ret_data, vol_data, rat_data, deep_data = [], [], [], []
            
            for label, yrs in periods.items():
                target_date = raw_nav_data.index[-1] - pd.DateOffset(years=yrs)
                f_subset = raw_nav_data[raw_nav_data.index >= target_date]
                
                f_ret, f_vol, f_rat = "-", "-", "-"
                if len(f_subset) > 20:
                    ret_val = (f_subset.iloc[-1] / f_subset.iloc[0]) ** (1/yrs) - 1
                    f_ret = f"{ret_val:.1%}"
                    vol_val = f_subset.pct_change().std() * np.sqrt(252)
                    f_vol = f"{vol_val:.1%}"
                    if vol_val != 0: f_rat = f"{ret_val / vol_val:.2f}"
                    
                b_ret, b_vol, b_rat = "-", "-", "-"
                if not raw_bench_data.empty:
                    b_subset = raw_bench_data[raw_bench_data.index >= target_date]
                    if len(b_subset) > 20:
                        b_ret_val = (b_subset.iloc[-1] / b_subset.iloc[0]) ** (1/yrs) - 1
                        b_ret = f"{b_ret_val:.1%}"
                        b_vol_val = b_subset.pct_change().std() * np.sqrt(252)
                        b_vol = f"{b_vol_val:.1%}"
                        if b_vol_val != 0: b_rat = f"{b_ret_val / b_vol_val:.2f}"
                        
                ret_data.append([label, f_ret, b_ret])
                vol_data.append([label, f_vol, b_vol])
                rat_data.append([label, f_rat, b_rat])
                
                if len(f_subset) > 20 and not raw_bench_data.empty and len(b_subset) > 20:
                    ab = analytics.calculate_alpha_beta(f_subset, b_subset)
                    rm = analytics.calculate_risk_metrics(f_subset)
                    cap = analytics.calculate_capture_ratios(f_subset, b_subset)
                    deep_data.append([
                        label,
                        f"{ab['alpha']:.1%}",
                        f"{ab['beta']:.2f}",
                        f"{rm.get('sharpe_ratio', 0):.2f}",
                        f"{rm.get('sortino_ratio', 0):.2f}",
                        f"{ab.get('info_ratio', 0):.2f}",
                        f"{ab.get('batting_average', 0):.1f}%",
                        f"{cap['upside']:.1f}%",
                        f"{cap['downside']:.1f}%"
                    ])

            self.periodic_returns = ret_data
            self.periodic_volatility = vol_data
            self.periodic_ratios = rat_data
            self.deep_metrics_table = deep_data
            
            # 10. Rolling Profile Table
            profile = analytics.calculate_rolling_return_profile(raw_nav_data['nav'])
            if profile:
                keys = ["Minimum", "Median", "Maximum", "% times -ve returns", "% times returns 0 - 5%", "% times returns 5 - 10%", 
                        "% times returns 10 - 15%", "% times returns 15 - 20%", "% times returns > 20%"]
                prof_data = []
                for k in keys:
                    row = [k]
                    for p_label in ["1 Year", "3 Years", "5 Years"]:
                        val = profile.get(p_label, {}).get(k, None) if profile.get(p_label) else None
                        row.append(f"{val:.1%}" if val is not None else "Short Hist.")
                    prof_data.append(row)
                self.rolling_profile_table = prof_data

        else:
            self.results_found = False
            self.fund_name = "Not found."
            
        self.is_loading = False

def metric_card(label: str, value: str, icon: str, color: str):
    """A reusable mini-component for a metric."""
    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.icon(tag=icon, size=20, color=color),
                rx.text(label, font_size="0.8em", color="gray.500", font_weight="bold"),
                spacing="2"
            ),
            rx.text(value, font_size="1.8em", font_weight="extra-bold", color="black"),
            align="start",
            spacing="1"
        ),
        padding="1.5em",
        border_radius="15px",
        bg="white",
        box_shadow="0 10px 30px rgba(0,0,0,0.05)",
        width="100%",
        border=f"1px solid {rx.color(color, 2)}",
        _hover={"transform": "translateY(-5px)", "transition": "0.3s ease"}
    )

def index() -> rx.Component:
    """The Main UI Layout."""
    return rx.box(
        rx.center(
            rx.vstack(
                rx.heading(
                    "Intuitive Mutual Funds Analytics (v3.0)", 
                    size="8", 
                    font_weight="900",
                    background_clip="text",
                    background_image="linear-gradient(to right, #2563eb, #3b82f6, #60a5fa)",
                    text_align="center"
                ),
                rx.text("Complete feature parity with Streamlit - High Fidelity Version", color="gray.500"),
                
                # 🔍 Search Bar
                rx.hstack(
                    rx.input(
                        placeholder="Search fund (e.g. HDFC Flexi Cap)",
                        on_change=State.set_search_query,
                        width="500px",
                        height="60px",
                        style={
                            "fontSize": "22px",
                            "fontWeight": "bold",
                            "color": "black",
                            "backgroundColor": "white",
                            "border": "3px solid #2563eb",
                            "borderRadius": "10px",
                            "paddingLeft": "15px",
                        },
                    ),
                    rx.button(
                        rx.cond(State.is_loading, rx.spinner(size="3"), "Analyze Now"),
                        on_click=State.handle_search,
                        size="4",
                        color_scheme="blue",
                        height="60px",
                        padding="0 2em",
                        font_weight="bold",
                    ),
                    spacing="3",
                    margin_top="2.5em",
                ),
                
                # ⚙️ Analysis Settings
                rx.box(
                    rx.vstack(
                        rx.hstack(
                            rx.icon(tag="settings-2", color="gray.500"),
                            rx.text("Analysis Configuration", font_weight="bold", color="gray.700"),
                            spacing="2"
                        ),
                        rx.divider(margin_y="1em"),
                        rx.hstack(
                            # Column 1: Benchmark Strategy
                            rx.vstack(
                                rx.text("Benchmark Strategy", font_size="0.8em", color="gray.500", font_weight="bold"),
                                rx.radio.root(
                                    rx.radio.item("Market Index", value="Index"),
                                    rx.radio.item("Compare Fund", value="Fund"),
                                    value=State.bench_type,
                                    on_change=State.set_bench_type,
                                    direction="row",
                                    spacing="4"
                                ),
                                rx.cond(
                                    State.bench_type == "Index",
                                    rx.select.root(
                                        rx.select.trigger(width="100%"),
                                        rx.select.content(
                                            rx.select.group(
                                                rx.select.item("Nifty 50", value="^NSEI"),
                                                rx.select.item("Nifty 500", value="^CRSLDX"),
                                                rx.select.item("Midcap 100", value="^NSEMDCP100"),
                                                rx.select.item("Smallcap 100", value="^NSESCP100"),
                                            ),
                                        ),
                                        value=State.selected_benchmark,
                                        on_change=State.set_benchmark,
                                    ),
                                    rx.vstack(
                                        rx.input(placeholder="Search benchmark fund...", on_change=State.set_bench_search, width="100%"),
                                        rx.cond(
                                            State.available_bench_funds.length() > 0,
                                            rx.select.root(
                                                rx.select.trigger(width="100%"),
                                                rx.select.content(
                                                    rx.foreach(State.available_bench_funds, lambda f: rx.select.item(f, value=f))
                                                ),
                                                on_change=State.set_bench_fund,
                                                placeholder="Select a fund"
                                            ),
                                        ),
                                        width="100%"
                                    )
                                ),
                                width="30%", align="start", spacing="2"
                            ),
                            
                            # Column 2: Time Horizon
                            rx.vstack(
                                rx.text("Time Horizon", font_size="0.8em", color="gray.500", font_weight="bold"),
                                rx.segmented_control.root(
                                    rx.segmented_control.item("1Y", value="1Y"),
                                    rx.segmented_control.item("3Y", value="3Y"),
                                    rx.segmented_control.item("5Y", value="5Y"),
                                    rx.segmented_control.item("All Time", value="All Time"),
                                    rx.segmented_control.item("Custom Range", value="Custom Range"),
                                    value=State.analysis_period,
                                    on_change=State.set_analysis_period,
                                    width="100%"
                                ),
                                rx.cond(
                                    State.analysis_period == "Custom Range",
                                    rx.hstack(
                                        rx.input(type_="date", value=State.custom_start_date, on_change=State.set_custom_start),
                                        rx.text("to"),
                                        rx.input(type_="date", value=State.custom_end_date, on_change=State.set_custom_end),
                                        width="100%", align="center", justify="between"
                                    )
                                ),
                                width="40%", align="start", spacing="2"
                            ),
                            
                            # Column 3: Risk Free Rate
                            rx.vstack(
                                rx.text(f"Risk Free Rate ({State.risk_free_rate}%)", font_size="0.8em", color="gray.500", font_weight="bold"),
                                rx.slider(
                                    default_value=[5.3],
                                    min=0.0,
                                    max=10.0,
                                    step=0.1,
                                    on_value_commit=State.set_risk_free_rate,
                                    width="100%"
                                ),
                                rx.text("Used for Sharpe, Sortino ratios & Alpha calculations", font_size="0.7em", color="gray.400"),
                                width="25%", align="start", spacing="2"
                            ),
                            
                            width="100%",
                            justify="between",
                            align="start",
                            spacing="6"
                        )
                    ),
                    bg="white",
                    padding="2em",
                    border_radius="15px",
                    box_shadow="0 4px 6px rgba(0,0,0,0.02)",
                    border="1px solid #e2e8f0",
                    width="100%",
                    margin_top="2em"
                ),
                
                # 📊 Results Section
                rx.cond(
                    State.results_found,
                    rx.vstack(
                        rx.divider(margin_top="3em", margin_bottom="3em"),
                        rx.heading(State.fund_name, size="6", color="gray.800"),
                        
                        # Top Metrics (5 columns)
                        rx.grid(
                            metric_card("GROWTH", State.multiplier, "trending-up", "blue"),
                            metric_card("CAGR", State.cagr, "percent", "green"),
                            metric_card("VOLATILITY", State.volatility, "activity", "red"),
                            metric_card("SHARPE", State.sharpe_ratio, "shield-check", "purple"),
                            metric_card("MAX DRAWDOWN", State.max_drawdown, "arrow-down-to-line", "orange"),
                            columns="5",
                            spacing="4",
                            width="100%",
                            margin_top="1.5em"
                        ),
                        
                        # 📑 Detailed Navigation
                        rx.tabs.root(
                            rx.tabs.list(
                                rx.tabs.trigger("Performance Analysis", value="perf"),
                                rx.tabs.trigger("Risk Efficiency", value="risk"),
                                rx.tabs.trigger("Style & Capture", value="style"),
                                rx.tabs.trigger("Calendar returns", value="calendar"),
                            ),
                            rx.tabs.content(
                                rx.vstack(
                                    # Comparison Chart
                                    rx.box(
                                        rx.heading("Growth: Fund vs Benchmark", size="4", margin_bottom="1em"),
                                        rx.recharts.line_chart(
                                            rx.recharts.line(data_key="fund", name="Fund", stroke="#2563eb", stroke_width=3, dot=False),
                                            rx.recharts.line(data_key="bench", name="Benchmark", stroke="#94a3b8", stroke_width=2, stroke_dasharray="5 5", dot=False),
                                            rx.recharts.x_axis(data_key="date", hide=True),
                                            rx.recharts.y_axis(domain=["auto", "auto"]),
                                            rx.recharts.graphing_tooltip(),
                                            rx.recharts.legend(),
                                            data=State.compare_plot_data,
                                            width="100%",
                                            height=350,
                                        ),
                                        padding="2em", bg="white", border_radius="15px", box_shadow="0 10px 30px rgba(0,0,0,0.05)", width="100%", margin_top="2em"
                                    ),
                                    # Drawdown Chart
                                    rx.box(
                                        rx.heading("Drawdown Analysis (%)", size="4", margin_bottom="1em"),
                                        rx.recharts.area_chart(
                                            rx.recharts.area(data_key="drawdown", stroke="#dc2626", fill="#fee2e2", name="Drawdown"),
                                            rx.recharts.x_axis(data_key="date", hide=True),
                                            rx.recharts.y_axis(),
                                            rx.recharts.graphing_tooltip(),
                                            data=State.drawdown_plot_data,
                                            width="100%",
                                            height=250,
                                        ),
                                        padding="2em", bg="white", border_radius="15px", box_shadow="0 10px 30px rgba(0,0,0,0.05)", width="100%", margin_top="2em"
                                    ),
                                    # Rolling Returns
                                    rx.box(
                                        rx.heading("1Y Rolling Returns (%)", size="4", margin_bottom="1em"),
                                        rx.recharts.line_chart(
                                            rx.recharts.line(data_key="rolling", stroke="#059669", stroke_width=2, dot=False),
                                            rx.recharts.x_axis(data_key="date", hide=True),
                                            rx.recharts.y_axis(),
                                            rx.recharts.graphing_tooltip(),
                                            data=State.rolling_plot_data,
                                            width="100%",
                                            height=250,
                                        ),
                                        padding="2em", bg="white", border_radius="15px", box_shadow="0 10px 30px rgba(0,0,0,0.05)", width="100%", margin_top="2em"
                                    ),
                                    rx.divider(margin_y="2em"),
                                    rx.heading("Periodic Performance Summary", size="5", margin_bottom="1.5em", color="gray.800"),
                                    rx.grid(
                                        rx.box(
                                            rx.heading("Returns (CAGR)", size="4", margin_bottom="1em", color="blue.600"),
                                            rx.data_table(data=State.periodic_returns, columns=["Period", "Fund", "Benchmark"], pagination=False, width="100%"),
                                            padding="1.5em", bg="white", border_radius="10px", width="100%", border="1px solid #eef2f6"
                                        ),
                                        rx.box(
                                            rx.heading("Volatility (Risk)", size="4", margin_bottom="1em", color="red.600"),
                                            rx.data_table(data=State.periodic_volatility, columns=["Period", "Fund", "Benchmark"], pagination=False, width="100%"),
                                            padding="1.5em", bg="white", border_radius="10px", width="100%", border="1px solid #eef2f6"
                                        ),
                                        rx.box(
                                            rx.heading("Return/Risk Ratio", size="4", margin_bottom="1em", color="purple.600"),
                                            rx.data_table(data=State.periodic_ratios, columns=["Period", "Fund", "Benchmark"], pagination=False, width="100%"),
                                            padding="1.5em", bg="white", border_radius="10px", width="100%", border="1px solid #eef2f6"
                                        ),
                                        columns="3", spacing="4", width="100%"
                                    ),
                                    spacing="4", width="100%"
                                ),
                                value="perf",
                            ),
                            rx.tabs.content(
                                rx.vstack(
                                    rx.grid(
                                        metric_card("SHARPE RATIO", State.sharpe_ratio, "shield-check", "purple"),
                                        metric_card("SORTINO RATIO", State.sortino_ratio, "shield", "indigo"),
                                        metric_card("HURST (H)", State.hurst_exp, "dna", "orange"),
                                        columns="3", spacing="4", width="100%", padding_top="1em"
                                    ),
                                    rx.divider(margin_y="2em"),
                                    rx.heading("Risk & Return Efficiency (Multi-Period)", size="4", margin_bottom="1em"),
                                    rx.data_table(
                                        data=State.deep_metrics_table,
                                        columns=["Period", "Alpha", "Beta", "Sharpe", "Sortino", "Information Ratio", "Batting Avg", "Upside Capture", "Downside Capture"],
                                        width="100%",
                                        pagination=False,
                                    ),
                                    rx.text("Includes Alpha, Beta, Sharpe, Sortino, Information Ratio, and Batting Average across different historical horizons.", font_size="0.8em", color="gray.500", margin_top="1em"),
                                    width="100%"
                                ),
                                value="risk",
                            ),
                            rx.tabs.content(
                                rx.vstack(
                                    rx.grid(
                                        metric_card("BETA", State.beta, "git-branch", "cyan"),
                                        metric_card("JENSEN ALPHA", State.jensen_alpha, "zap", "amber"),
                                        metric_card("UPSIDE CAPTURE", State.upside_capture, "arrow-up-right", "teal"),
                                        metric_card("DOWNSIDE CAPTURE", State.downside_capture, "arrow-down-right", "pink"),
                                        columns="4", spacing="4", width="100%", padding_top="1em"
                                    ),
                                    rx.divider(margin_y="2em"),
                                    rx.hstack(
                                        rx.box(
                                            rx.heading("Market Participation (Monthly)", size="4", margin_bottom="1em"),
                                            rx.recharts.scatter_chart(
                                                rx.recharts.scatter(data_key="bench", name="Benchmark", fill="#8884d8", data=State.scatter_plot_data),
                                                rx.recharts.x_axis(data_key="bench", type_="number", name="Benchmark Return", unit="%"),
                                                rx.recharts.y_axis(data_key="fund", type_="number", name="Fund Return", unit="%"),
                                                rx.recharts.graphing_tooltip(cursor={"strokeDasharray": "3 3"}),
                                                rx.recharts.legend(),
                                                width="100%",
                                                height=350,
                                            ),
                                            padding="2em", bg="white", border_radius="15px", box_shadow="0 10px 30px rgba(0,0,0,0.05)", width="50%"
                                        ),
                                        rx.box(
                                            rx.heading("Rolling Returns Profile", size="4", margin_bottom="1em"),
                                            rx.data_table(
                                                data=State.rolling_profile_table,
                                                columns=["Metric", "1 Year", "3 Years", "5 Years"],
                                                width="100%",
                                                pagination=False,
                                            ),
                                            padding="2em", bg="white", border_radius="15px", box_shadow="0 10px 30px rgba(0,0,0,0.05)", width="50%"
                                        ),
                                        width="100%", spacing="6", align="start"
                                    ),
                                    width="100%"
                                ),
                                value="style",
                            ),
                            rx.tabs.content(
                                rx.vstack(
                                    rx.box(
                                        rx.recharts.bar_chart(
                                            rx.recharts.bar(data_key="fund", fill="#2563eb", name="Fund"),
                                            rx.recharts.bar(data_key="bench", fill="#94a3b8", name="Benchmark"),
                                            rx.recharts.x_axis(data_key="year"),
                                            rx.recharts.y_axis(),
                                            rx.recharts.graphing_tooltip(),
                                            rx.recharts.legend(),
                                            data=State.calendar_plot_data,
                                            width="100%",
                                            height=400,
                                        ),
                                        padding="2em", bg="white", border_radius="15px", box_shadow="0 10px 30px rgba(0,0,0,0.05)", width="100%", margin_top="2em"
                                    ),
                                    width="100%"
                                ),
                                value="calendar",
                            ),
                            width="100%", margin_top="2em", default_value="perf",
                        ),
                        width="100%", align="center"
                    )
                ),
                
                # 🚫 Not Found Message
                rx.cond(
                    ~State.results_found & (State.fund_name != "Search a fund to begin analysis"),
                    rx.text(State.fund_name, color="red.500", margin_top="2em")
                ),
                
                spacing="4", width="100%", max_width="1100px", padding="2em"
            ),
            width="100%", padding_top="5em"
        ),
        bg="gray.25", min_height="100vh"
    )

app = rx.App(
    theme=rx.theme(
        appearance="light", has_background=True, radius="large", accent_color="blue"
    )
)
app.add_page(index)
