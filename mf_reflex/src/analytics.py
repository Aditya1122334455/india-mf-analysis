import pandas as pd
import numpy as np
from scipy.stats import norm

class MFAnalytics:
    def __init__(self, risk_free_rate=0.06):
        self.rf = risk_free_rate

    def calculate_cagr(self, nav_series):
        """Calculate Cumulative Annual Growth Rate."""
        if nav_series.empty or len(nav_series) < 2:
            return 0.0
        
        start_val = nav_series.iloc[0]
        end_val = nav_series.iloc[-1]
        
        years = (nav_series.index[-1] - nav_series.index[0]).days / 365.25
        if years <= 0:
            return 0.0
            
        cagr = (end_val / start_val) ** (1 / years) - 1
        return cagr

    def calculate_rolling_returns(self, nav_series, window_years=1):
        """Calculate rolling returns for a given window in years."""
        if nav_series.empty:
            return pd.Series()
            
        # Assuming ~252 trading days in a year
        window = int(window_years * 252)
        if len(nav_series) < window:
            return pd.Series()
            
        rolling_returns = (nav_series / nav_series.shift(window)) ** (1 / window_years) - 1
        return rolling_returns.dropna()

    def calculate_downside_deviation(self, nav_series):
        """
        Calculate Downside Risk as requested:
        X = Returns below zero
        Y = Sum of all squares of X
        Z = Y / number of days taken for computing the ratio
        Downside risk = Square root of Z
        Annualized = Downside risk * sqrt(252)
        """
        if nav_series.empty or len(nav_series) < 2:
            return 0.0
            
        returns = nav_series.pct_change().dropna()
        if returns.empty:
            return 0.0
            
        x = returns[returns < 0]
        y = (x**2).sum()
        z = y / len(returns)
        
        downside_risk_daily = np.sqrt(z)
        return downside_risk_daily * np.sqrt(252) # Annualized

    def calculate_risk_metrics(self, nav_series):
        """Calculate Sharpe, Sortino, Volatility, Downside Deviation, Calmar, and Omega."""
        if nav_series.empty or len(nav_series) < 2:
            return {}
            
        returns = nav_series.pct_change().dropna()
        if returns.empty:
            return {}
            
        volatility = returns.std() * np.sqrt(252)
        mean_return = returns.mean() * 252
        cagr = self.calculate_cagr(nav_series)
        
        excess_return = mean_return - self.rf
        sharpe = excess_return / volatility if volatility != 0 else 0
        
        downside_dev = self.calculate_downside_deviation(nav_series)
        sortino = excess_return / downside_dev if downside_dev != 0 else 0
        
        # Calmar Ratio
        _, max_dd = self.calculate_drawdowns(nav_series)
        calmar = (cagr / abs(max_dd)) if max_dd != 0 else 0
        
        # Omega Ratio (simplified for threshold self.rf/252)
        # Ratio of probability-weighted gains vs losses
        threshold = self.rf / 252
        gains = returns[returns > threshold].sum()
        losses = abs(returns[returns <= threshold].sum())
        omega = gains / losses if losses != 0 else 0

        hurst = self.calculate_hurst(nav_series)
        
        return {
            "volatility": volatility,
            "sharpe_ratio": sharpe,
            "sortino_ratio": sortino,
            "downside_deviation": downside_dev,
            "calmar_ratio": calmar,
            "omega_ratio": omega,
            "hurst_exponent": hurst,
            "cagr": cagr
        }

    def calculate_hurst(self, nav_series):
        """
        Calculate Hurst Exponent (H) to measure consistency/randomness.
        H = 0.5: Random Walk
        H < 0.5: Mean Reverting
        H > 0.5: Persistent (Trending)
        """
        if nav_series.empty or len(nav_series) < 100:
            return 0.5
            
        lags = range(2, 20)
        # Convert to values to ignore index alignment
        vals = nav_series.values
        # Calculate the variance of the differences with different lags
        tau = [np.sqrt(np.std(vals[lag:] - vals[:-lag])) for lag in lags]
        # Calculate the slope of the log plot -> Hurst Exponent
        poly = np.polyfit(np.log(lags), np.log(tau), 1)
        return poly[0] * 2.0  # Corrections for log-volatility scaling

    def calculate_drawdowns(self, nav_series):
        """Calculate drawdown series and max drawdown."""
        if nav_series.empty:
            return pd.Series(), 0.0
            
        rolling_max = nav_series.cummax()
        drawdown = (nav_series - rolling_max) / rolling_max
        max_drawdown = drawdown.min()
        
        return drawdown, max_drawdown

    def calculate_sip_returns(self, nav_series, monthly_sip=10000):
        """Simulate monthly SIP and return final value, total invested, and XIRR estimate."""
        if nav_series.empty:
            return {}
            
        # Get first business day of each month
        monthly_nav = nav_series.resample('BMS').first()
        
        total_units = 0
        total_invested = 0
        investment_dates = []
        
        for date, nav in monthly_nav.items():
            units = monthly_sip / nav
            total_units += units
            total_invested += monthly_sip
            investment_dates.append(date)
            
        current_value = total_units * nav_series.iloc[-1]
        
        # Simple XIRR approximation (CAGR of the SIP)
        # Note: True XIRR requires solving for r in sum(P_i / (1+r)^t_i) = V
        # We'll provide the absolute gain and CAGR for now
        total_gain = current_value - total_invested
        absolute_return = (total_gain / total_invested) if total_invested > 0 else 0
        
        return {
            "current_value": current_value,
            "total_invested": total_invested,
            "absolute_return": absolute_return,
            "total_units": total_units
        }

    def calculate_capture_ratios(self, fund_nav, benchmark_nav):
        """Calculate Upside and Downside Capture Ratios."""
        # Align series - ensure benchmark_nav is a 1D Series
        if hasattr(benchmark_nav, 'squeeze'):
            benchmark_nav = benchmark_nav.squeeze()
            
        df = pd.DataFrame({'fund': fund_nav, 'bench': benchmark_nav}).dropna()
        if df.empty: return {"upside": 0, "downside": 0}
        
        # Monthly returns - using 'ME' (Month End) to avoid deprecation warning
        monthly_df = df.resample('ME').last().pct_change().dropna()
        
        upside_bench = monthly_df[monthly_df['bench'] > 0]
        downside_bench = monthly_df[monthly_df['bench'] <= 0]
        
        # Upside Capture = (Avg Fund Return in Up Months / Avg Bench Return in Up Months)
        upside_ratio = (upside_bench['fund'].mean() / upside_bench['bench'].mean()) if not upside_bench.empty else 0
        downside_ratio = (downside_bench['fund'].mean() / downside_bench['bench'].mean()) if not downside_bench.empty else 0
        
        return {
            "upside": upside_ratio * 100, # In percentage
            "downside": downside_ratio * 100
        }

    def calculate_alpha_beta(self, fund_nav, benchmark_nav):
        """Calculate Alpha and Beta using linear regression on excess returns."""
        # Ensure benchmark_nav is a 1D Series
        if hasattr(benchmark_nav, 'squeeze'):
            benchmark_nav = benchmark_nav.squeeze()
            
        df = pd.DataFrame({'fund': fund_nav, 'bench': benchmark_nav}).dropna()
        if len(df) < 20: return {"alpha": 0, "beta": 0, "r_squared": 0}
        
        f_ret = df['fund'].pct_change().dropna()
        b_ret = df['bench'].pct_change().dropna()
        
        # Convert annual risk-free rate to daily (simple annualization for daily returns)
        daily_rf = self.rf / 252
        
        # Calculate daily excess returns
        f_excess = f_ret - daily_rf
        b_excess = b_ret - daily_rf
        
        # Linear regression: Fund_Excess = Alpha + Beta * Bench_Excess
        beta, alpha_daily = np.polyfit(b_excess, f_excess, 1)
        
        # Annualize Alpha (Daily Alpha * 252)
        # This gives the annualized risk-adjusted excess return
        alpha_annual = alpha_daily * 252
        
        # R-Squared
        correlation_matrix = np.corrcoef(b_excess, f_excess)
        correlation_xy = correlation_matrix[0,1]
        r_squared = correlation_xy**2

        # Information Ratio
        # (Fund Return - Bench Return) / Tracking Error
        active_returns = f_ret - b_ret
        tracking_error = active_returns.std() * np.sqrt(252)
        info_ratio = (active_returns.mean() * 252) / tracking_error if tracking_error != 0 else 0

        # Batting Average (Daily beating bench)
        batting_avg = (f_ret > b_ret).mean() * 100
        
        return {
            "alpha": alpha_annual,
            "beta": beta,
            "r_squared": r_squared,
            "info_ratio": info_ratio,
            "batting_average": batting_avg
        }

    def calculate_fund_multiplier(self, nav_series):
        """Calculate how many times the investment has grown."""
        if nav_series.empty: return 1.0
        return nav_series.iloc[-1] / nav_series.iloc[0]

    def calculate_calendar_returns(self, nav_series):
        """Calculate calendar year returns including YTD."""
        if nav_series.empty:
            return pd.Series()
        
        # Get year-end values
        yearly_nav = nav_series.resample('YE').last()
        
        # If the last date in nav_series is not the same as the last date in yearly_nav,
        # it means the current year is still in progress (YTD).
        # But resample('YE').last() already includes the last available point for the current year.
        
        returns = yearly_nav.pct_change()
        
        # Calculate the first year's return separately since pct_change puts NaN there
        # but the first year might be a partial year.
        if not yearly_nav.empty:
            first_actual_nav = nav_series.iloc[0]
            returns.iloc[0] = (yearly_nav.iloc[0] / first_actual_nav) - 1
            
        returns.index = returns.index.year
        return returns

    def calculate_rolling_return_profile(self, nav_series):
        """Calculate profile-like stats for standard time horizons."""
        profile = {}
        horizons = {1: "1 Year", 3: "3 Years", 5: "5 Years"}
        
        for yrs, label in horizons.items():
            rolling = self.calculate_rolling_returns(nav_series, window_years=yrs)
            if rolling.empty:
                profile[label] = None
                continue
                
            profile[label] = {
                "Minimum": rolling.min(),
                "Median": rolling.median(),
                "Maximum": rolling.max(),
                "% times -ve returns": (rolling < 0).mean(),
                "% times returns 0 - 5%": ((rolling >= 0.00) & (rolling < 0.05)).mean(),
                "% times returns 5 - 10%": ((rolling >= 0.05) & (rolling < 0.10)).mean(),
                "% times returns 10 - 15%": ((rolling >= 0.10) & (rolling < 0.15)).mean(),
                "% times returns 15 - 20%": ((rolling >= 0.15) & (rolling < 0.20)).mean(),
                "% times returns > 20%": (rolling >= 0.20).mean()
            }
        return profile

if __name__ == "__main__":
    # Mock data for testing
    dates = pd.date_range(start="2020-01-01", periods=1000, freq='B')
    nav = pd.Series(100 * (1 + 0.0005 + np.random.normal(0, 0.01, 1000)).cumprod(), index=dates)
    
    analytics = MFAnalytics()
    print(f"CAGR: {analytics.calculate_cagr(nav):.2%}")
    metrics = analytics.calculate_risk_metrics(nav)
    print(f"Metrics: {metrics}")
    _, max_dd = analytics.calculate_drawdowns(nav)
    print(f"Max Drawdown: {max_dd:.2%}")
    rolling = analytics.calculate_rolling_returns(nav, window_years=1)
    print(f"Rolling Return (latest): {rolling.iloc[-1]:.2%}")
