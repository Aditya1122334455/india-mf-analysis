import dash
from dash import dcc, html, Input, Output, State, dash_table
import dash_bootstrap_components as dbc
import plotly.express as px
import pandas as pd
import numpy as np
from src.data_fetcher import MFDataFetcher
from src.analytics import MFAnalytics

# Initialize App with a Modern Theme (Slate/Cerulean)
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.CERULEAN])
app.title = "Dash MF Analytics"

fetcher = MFDataFetcher()
analytics = MFAnalytics()

# 🎨 Layout: Defining the Structure
app.layout = dbc.Container([
    dbc.Row([
        dbc.Col(html.H1("📈 India Mutual Fund Analytics", className="text-center my-4"), width=12)
    ]),
    
    dbc.Row([
        dbc.Col([
            dbc.InputGroup([
                dbc.Input(id='fund-query', placeholder='Search Fund (e.g. HDFC Flexi Cap)', type='text'),
                dbc.Button('Analyze', id='search-btn', color='primary', n_clicks=0)
            ])
        ], width={"size": 6, "offset": 3}, className="mb-4")
    ]),

    dbc.Row([
        dbc.Col(id='fund-title', width=12, className="text-center mb-2")
    ]),

    dcc.Loading(
        id="loading-main",
        type="circle",
        children=[
            dbc.Row([
                dbc.Col(dcc.Graph(id='growth-chart'), width=12, className="mb-4")
            ]),
            dbc.Row([
                dbc.Col(id='metrics-output', width={"size": 8, "offset": 2})
            ])
        ]
    )
], fluid=True)

# 🧠 Callbacks: Interactive Logic
@app.callback(
    [Output('growth-chart', 'figure'),
     Output('metrics-output', 'children'),
     Output('fund-title', 'children')],
    [Input('search-btn', 'n_clicks')],
    [State('fund-query', 'value')]
)
def run_analysis(n_clicks, query):
    if n_clicks == 0 or not query:
        return px.line(title="Search for a fund to see history"), "", ""

    # 1. Search Logic
    results = fetcher.search_funds(query)
    if not results:
        return px.line(title="No results found."), html.P("No matching funds found. Try a broader search.", className="text-danger"), ""
    
    code = list(results.keys())[0]
    full_name = results[code]
    
    # 2. Fetch Data
    df = fetcher.get_nav_history(code)
    if df.empty:
        return px.line(title="Data unavailable."), html.P("Historical data not available for this AMFI code.", className="text-warning"), ""
    
    # 3. Process Analytics (Basic Portfolio Stats)
    cagr = analytics.calculate_cagr(df['nav'])
    risk = analytics.calculate_risk_metrics(df['nav'])
    _, max_dd = analytics.calculate_drawdowns(df['nav'])

    # 4. Generate Chart (Rebased to 100)
    rebased = (df['nav'] / df['nav'].iloc[0]) * 100
    fig = px.line(rebased, title="Growth of ₹100", template="plotly_white")
    fig.update_layout(height=450, margin=dict(l=20, r=20, t=50, b=20))
    fig.update_yaxes(title="Value")

    # 5. Build Metrics Table
    raw_metrics = [
        {"Metric": "CAGR (Total)", "Value": f"{cagr:.1%}"},
        {"Metric": "Volatility (Annual)", "Value": f"{risk.get('volatility', 0):.1%}"},
        {"Metric": "Sharpe Ratio", "Value": f"{risk.get('sharpe_ratio', 0):.2f}"},
        {"Metric": "Max Drawdown", "Value": f"{max_dd:.1%}"},
        {"Metric": "Latest NAV", "Value": f"₹{df['nav'].iloc[-1]:.2f}"}
    ]
    
    table = dash_table.DataTable(
        data=raw_metrics,
        columns=[{"name": i, "id": i} for i in ["Metric", "Value"]],
        style_header={'backgroundColor': 'rgb(210, 210, 210)', 'fontWeight': 'bold'},
        style_cell={'textAlign': 'left', 'padding': '10px'},
        style_as_list_view=True,
    )

    return fig, table, html.H3(full_name, className="text-primary")

if __name__ == '__main__':
    app.run(debug=True, port=8050)
