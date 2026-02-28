import reflex as rx
from src.data_fetcher import MFDataFetcher
from src.analytics import MFAnalytics

class State(rx.State):
    """The App State with Reactive logic."""
    search_query: str = ""
    is_loading: bool = False
    fund_name: str = "Search a fund to begin analysis"
    latest_nav: str = "₹0.00"
    cagr: str = "0.0%"
    volatility: str = "0.0%"
    results_found: bool = False
    plot_data: list[dict[str, any]] = []

    def set_search_query(self, query: str):
        self.search_query = query

    def handle_search(self):
        """Perform the search."""
        if not self.search_query:
            return
            
        self.is_loading = True
        yield  # Show loading spinner in UI
        
        fetcher = MFDataFetcher()
        analytics = MFAnalytics()
        
        search_results = fetcher.search_funds(self.search_query)
        if search_results:
            self.results_found = True
            code = list(search_results.keys())[0]
            self.fund_name = search_results[code]
            
            # Fetch data & metrics
            nav_data = fetcher.get_nav_history(code)
            if not nav_data.empty:
                self.latest_nav = f"₹{nav_data['nav'].iloc[-1]:.2f}"
                cagr_val = analytics.calculate_cagr(nav_data['nav'])
                self.cagr = f"{cagr_val:.1%}"
                risk = analytics.calculate_risk_metrics(nav_data['nav'])
                self.volatility = f"{risk.get('volatility', 0):.1%}"
                
                # Populate plot_data for the chart (Rebased to 100)
                rebased = (nav_data['nav'] / nav_data['nav'].iloc[0]) * 100
                # Sample the data to ~200 points to keep it light
                if len(rebased) > 200:
                    step = len(rebased) // 200
                    rebased = rebased.iloc[::step]
                
                self.plot_data = [
                    {"date": str(index.date()), "value": round(float(val), 2)}
                    for index, val in rebased.items()
                ]
            else:
                self.fund_name = "Data unavailable for this fund."
                self.plot_data = []
        else:
            self.results_found = False
            self.fund_name = "No funds found matching your search."
            
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
        # 🏙️ Background/Hero
        rx.center(
            rx.vstack(
                rx.heading(
                    "Intuitive Mutual Funds Analytics (v2.1)", 
                    size="8", 
                    font_weight="900",
                    background_clip="text",
                    background_image="linear-gradient(to right, #2563eb, #3b82f6, #60a5fa)",
                    text_align="center"
                ),
                rx.text("Institutional grade insights with a modern touch", color="gray.500"),
                
                # 🔍 Search Bar - HIGH CONTRAST VERSION
                rx.hstack(
                    rx.input(
                        placeholder="Type fund name here...",
                        on_change=State.set_search_query,
                        width="500px",
                        height="60px",
                        style={
                            "fontSize": "26px",
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
                
                # 📊 Results Section
                rx.cond(
                    State.results_found,
                    rx.vstack(
                        rx.divider(margin_top="3em", margin_bottom="3em"),
                        rx.heading(State.fund_name, size="6", color="gray.800"),
                        rx.grid(
                            metric_card("LATEST NAV", State.latest_nav, "circle-dollar-sign", "blue"),
                            metric_card("ANN. RETURNS", State.cagr, "trending-up", "green"),
                            metric_card("ANN. VOLATILITY", State.volatility, "activity", "red"),
                            columns="3",
                            spacing="4",
                            width="100%",
                            margin_top="1.5em"
                        ),
                        
                        # 📈 Growth Chart
                        rx.box(
                            rx.recharts.line_chart(
                                rx.recharts.line(
                                    data_key="value",
                                    type_="monotone",
                                    dot=False,
                                    stroke="#3b82f6",
                                    stroke_width=3,
                                ),
                                rx.recharts.x_axis(data_key="date", hide=True),
                                rx.recharts.y_axis(domain=["auto", "auto"]),
                                rx.recharts.graphing_tooltip(),
                                rx.recharts.reference_line(y=100, stroke="#e2e8f0", stroke_dasharray="3 3"),
                                data=State.plot_data,
                                width="100%",
                                height=350,
                            ),
                            width="100%",
                            padding="1.5em",
                            bg="white",
                            border_radius="15px",
                            box_shadow="0 10px 30px rgba(0,0,0,0.05)",
                            margin_top="2em",
                            border="1px solid #f1f5f9"
                        ),
                        rx.text("Historical Growth of ₹100", font_size="0.8em", color="gray.400", margin_top="1em"),
                        
                        width="100%",
                        align="center"
                    )
                ),
                
                # 🚫 Not Found Message
                rx.cond(
                    ~State.results_found & (State.fund_name != "Search a fund to begin analysis"),
                    rx.text(State.fund_name, color="red.500", margin_top="2em")
                ),
                
                spacing="4",
                width="100%",
                max_width="1000px",
                padding="2em"
            ),
            width="100%",
            padding_top="5em"
        ),
        bg="gray.25",
        min_height="100vh"
    )

app = rx.App(
    theme=rx.theme(
        appearance="light", 
        has_background=True, 
        radius="large",
        accent_color="blue"
    )
)
app.add_page(index)
