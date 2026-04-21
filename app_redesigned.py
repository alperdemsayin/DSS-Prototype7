"""Modern Maritime DSS - Redesigned Dashboard with Advanced UI"""

import json
import math
from typing import Dict, List, Tuple

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from structures import Plant, Ship
from solver import quick_diagnostics, run_solver


st.set_page_config(
    page_title="Maritime DSS",
    page_icon="⚓",
    layout="wide",
    initial_sidebar_state="collapsed",
)

FIXED_SCENARIO = {
    "depot": {"name": "Istanbul Depot", "lat": 41.0082, "lon": 28.9784},
    "plants": [
        {"name": "Antalya", "lat": 36.8969, "lon": 30.7133, "cap": 500.0, "init_stock": 400.0, "cons_rate": 5.0, "deadline": 120.0},
        {"name": "Iskenderun", "lat": 36.5872, "lon": 36.1735, "cap": 420.0, "init_stock": 330.0, "cons_rate": 4.0, "deadline": 110.0},
        {"name": "Mersin", "lat": 36.8000, "lon": 34.6333, "cap": 600.0, "init_stock": 520.0, "cons_rate": 6.0, "deadline": 120.0},
        {"name": "Canakkale", "lat": 40.1553, "lon": 26.4142, "cap": 350.0, "init_stock": 300.0, "cons_rate": 3.0, "deadline": 90.0},
        {"name": "Izmir", "lat": 38.4237, "lon": 27.1428, "cap": 480.0, "init_stock": 360.0, "cons_rate": 4.5, "deadline": 100.0},
        {"name": "Samsun", "lat": 41.2867, "lon": 36.3300, "cap": 390.0, "init_stock": 300.0, "cons_rate": 3.8, "deadline": 105.0},
    ],
}

DEFAULT_SHIP = {
    "empty_weight": 2000.0,
    "pump_rate": 50.0,
    "prep_time": 0.5,
    "charter_rate": 500.0,
    "fuel_cost": 0.02,
    "speed": 15.0,
}

MENU_ITEMS = [
    {"id": "dashboard", "name": "Dashboard", "icon": "📊"},
    {"id": "optimizer", "name": "Optimizer", "icon": "🎯"},
    {"id": "plants", "name": "Plant Network", "icon": "🏭"},
    {"id": "analytics", "name": "Analytics", "icon": "📈"},
    {"id": "settings", "name": "Settings", "icon": "⚙️"},
]

IGNORED_ROUTE_LABELS = {"Depot", "End of service", "Depot (return)"}


# =============================================================================
# MODERN STYLING
# =============================================================================

def inject_modern_css() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@400;500;600;700&family=Orbitron:wght@400;500;600;700;800;900&display=swap');
        
        :root {
            --primary: #2c3e50;
            --primary-dark: #1a252f;
            --accent: #3498db;
            --accent-bright: #5dade2;
            --success: #2ecc71;
            --warning: #f39c12;
            --danger: #e74c3c;
            --text-light: #ecf0f1;
            --text-dark: #2c3e50;
            --bg-main: #ecf0f1;
            --card-bg: #ffffff;
            --sidebar-width: 240px;
        }
        
        /* Reset and base */
        .stApp {
            background: var(--bg-main);
            font-family: 'Rajdhani', sans-serif;
        }
        
        /* Hide default sidebar */
        [data-testid="stSidebar"] {
            display: none;
        }
        
        /* Main container adjustments */
        .block-container {
            padding: 1rem 1.5rem;
            max-width: 100% !important;
        }
        
        /* Custom Sidebar */
        .modern-sidebar {
            position: fixed;
            left: 0;
            top: 0;
            width: var(--sidebar-width);
            height: 100vh;
            background: linear-gradient(180deg, var(--primary-dark) 0%, var(--primary) 100%);
            z-index: 999;
            display: flex;
            flex-direction: column;
            box-shadow: 4px 0 20px rgba(0,0,0,0.15);
        }
        
        .sidebar-logo {
            padding: 2rem 1.5rem;
            text-align: center;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }
        
        .sidebar-logo h1 {
            font-family: 'Orbitron', sans-serif;
            font-size: 1.5rem;
            font-weight: 900;
            color: var(--text-light);
            margin: 0;
            letter-spacing: 2px;
            text-transform: uppercase;
        }
        
        .sidebar-logo .subtitle {
            font-size: 0.7rem;
            color: var(--accent-bright);
            letter-spacing: 3px;
            margin-top: 0.3rem;
            text-transform: uppercase;
            font-weight: 600;
        }
        
        .sidebar-menu {
            flex: 1;
            padding: 1rem 0;
            overflow-y: auto;
        }
        
        .menu-item {
            padding: 1rem 1.5rem;
            margin: 0.3rem 0.8rem;
            color: rgba(255,255,255,0.7);
            cursor: pointer;
            border-radius: 8px;
            transition: all 0.3s ease;
            display: flex;
            align-items: center;
            gap: 1rem;
            font-size: 1rem;
            font-weight: 600;
            letter-spacing: 0.5px;
        }
        
        .menu-item:hover {
            background: rgba(52, 152, 219, 0.2);
            color: var(--text-light);
            transform: translateX(5px);
        }
        
        .menu-item.active {
            background: linear-gradient(90deg, var(--accent) 0%, var(--accent-bright) 100%);
            color: white;
            box-shadow: 0 4px 15px rgba(52, 152, 219, 0.4);
        }
        
        .menu-item .icon {
            font-size: 1.5rem;
            width: 30px;
            text-align: center;
        }
        
        .sidebar-footer {
            padding: 1rem 1.5rem;
            border-top: 1px solid rgba(255,255,255,0.1);
            color: rgba(255,255,255,0.5);
            font-size: 0.75rem;
            text-align: center;
        }
        
        /* Main content with sidebar offset */
        .main-content {
            margin-left: var(--sidebar-width);
            min-height: 100vh;
        }
        
        /* Top bar */
        .top-bar {
            background: white;
            padding: 1.2rem 2rem;
            margin: -1rem -1.5rem 2rem -1.5rem;
            box-shadow: 0 2px 10px rgba(0,0,0,0.05);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .page-title {
            font-family: 'Orbitron', sans-serif;
            font-size: 1.8rem;
            font-weight: 700;
            color: var(--primary-dark);
            margin: 0;
            letter-spacing: 1px;
        }
        
        .breadcrumb {
            color: #7f8c8d;
            font-size: 0.9rem;
            margin-top: 0.3rem;
        }
        
        /* Metric cards - inspired by reference */
        .metric-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2rem;
        }
        
        .metric-card {
            background: var(--card-bg);
            padding: 1.5rem;
            border-radius: 12px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.08);
            position: relative;
            overflow: hidden;
            transition: all 0.3s ease;
        }
        
        .metric-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 8px 25px rgba(0,0,0,0.12);
        }
        
        .metric-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 4px;
            background: linear-gradient(90deg, var(--accent), var(--accent-bright));
        }
        
        .metric-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 1rem;
        }
        
        .metric-label {
            font-size: 0.85rem;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: #7f8c8d;
            font-weight: 600;
        }
        
        .metric-icon {
            width: 50px;
            height: 50px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.5rem;
            background: var(--primary-dark);
            color: white;
        }
        
        .metric-value {
            font-family: 'Orbitron', sans-serif;
            font-size: 2.2rem;
            font-weight: 700;
            color: var(--text-dark);
            margin-bottom: 0.5rem;
        }
        
        .metric-change {
            font-size: 0.85rem;
            font-weight: 600;
        }
        
        .metric-change.positive {
            color: var(--success);
        }
        
        .metric-change.negative {
            color: var(--danger);
        }
        
        /* Chart containers */
        .chart-card {
            background: var(--card-bg);
            padding: 1.5rem;
            border-radius: 12px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.08);
            margin-bottom: 1.5rem;
        }
        
        .chart-title {
            font-family: 'Orbitron', sans-serif;
            font-size: 1.2rem;
            font-weight: 600;
            color: var(--text-dark);
            margin-bottom: 1.5rem;
            padding-bottom: 0.8rem;
            border-bottom: 2px solid var(--bg-main);
        }
        
        /* Buttons */
        .stButton > button {
            background: linear-gradient(90deg, var(--accent), var(--accent-bright));
            color: white;
            border: none;
            border-radius: 8px;
            padding: 0.8rem 2rem;
            font-family: 'Rajdhani', sans-serif;
            font-size: 1rem;
            font-weight: 700;
            letter-spacing: 1px;
            text-transform: uppercase;
            transition: all 0.3s ease;
            box-shadow: 0 4px 15px rgba(52, 152, 219, 0.3);
        }
        
        .stButton > button:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(52, 152, 219, 0.4);
        }
        
        /* Info boxes */
        .info-box {
            background: linear-gradient(135deg, var(--accent), var(--accent-bright));
            color: white;
            padding: 1.2rem 1.5rem;
            border-radius: 10px;
            margin-bottom: 1.5rem;
            box-shadow: 0 4px 15px rgba(52, 152, 219, 0.2);
        }
        
        .info-box-title {
            font-family: 'Orbitron', sans-serif;
            font-size: 0.9rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 1.5px;
            margin-bottom: 0.5rem;
            opacity: 0.95;
        }
        
        .info-box-content {
            font-size: 1rem;
            line-height: 1.6;
            opacity: 0.95;
        }
        
        /* Route visualization */
        .route-display {
            background: white;
            padding: 1.5rem;
            border-radius: 12px;
            margin-bottom: 1.5rem;
            box-shadow: 0 4px 15px rgba(0,0,0,0.08);
        }
        
        .route-title {
            font-family: 'Orbitron', sans-serif;
            font-size: 0.9rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 1.5px;
            color: var(--text-dark);
            margin-bottom: 1rem;
        }
        
        .route-flow {
            display: flex;
            align-items: center;
            flex-wrap: wrap;
            gap: 0.8rem;
        }
        
        .route-node {
            background: var(--primary-dark);
            color: white;
            padding: 0.6rem 1.2rem;
            border-radius: 20px;
            font-weight: 600;
            font-size: 0.9rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
            box-shadow: 0 3px 10px rgba(44, 62, 80, 0.2);
        }
        
        .route-node.start {
            background: linear-gradient(135deg, var(--accent), var(--accent-bright));
        }
        
        .route-node.end {
            background: linear-gradient(135deg, var(--success), #27ae60);
        }
        
        .route-number {
            background: rgba(255,255,255,0.3);
            width: 24px;
            height: 24px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 700;
            font-size: 0.85rem;
        }
        
        .route-arrow {
            color: var(--accent);
            font-weight: 700;
            font-size: 1.2rem;
        }
        
        /* Tables */
        .dataframe {
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 4px 15px rgba(0,0,0,0.08);
        }
        
        /* Plant config cards */
        .plant-card {
            background: white;
            padding: 1.2rem;
            border-radius: 10px;
            border-left: 4px solid var(--accent);
            margin-bottom: 1rem;
            box-shadow: 0 3px 10px rgba(0,0,0,0.06);
        }
        
        .plant-card-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1rem;
            padding-bottom: 0.8rem;
            border-bottom: 1px solid var(--bg-main);
        }
        
        .plant-name {
            font-family: 'Orbitron', sans-serif;
            font-size: 1.1rem;
            font-weight: 700;
            color: var(--text-dark);
        }
        
        .plant-coords {
            font-size: 0.8rem;
            color: #7f8c8d;
        }
        
        /* Streamlit overrides */
        [data-testid="stMetricValue"] {
            font-family: 'Orbitron', sans-serif;
            font-size: 2rem;
            font-weight: 700;
        }
        
        [data-testid="stMetricLabel"] {
            font-size: 0.85rem;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: #7f8c8d;
        }
        
        /* Hide streamlit elements */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        
        /* Responsive */
        @media (max-width: 768px) {
            .modern-sidebar {
                transform: translateX(-100%);
            }
            .main-content {
                margin-left: 0;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar() -> None:
    """Render modern custom sidebar"""
    current_page = st.session_state.get("nav_page", "dashboard")
    
    sidebar_html = """
    <div class="modern-sidebar">
        <div class="sidebar-logo">
            <h1>⚓ MDSS</h1>
            <div class="subtitle">Maritime DSS</div>
        </div>
        <div class="sidebar-menu">
    """
    
    for item in MENU_ITEMS:
        active_class = "active" if item["id"] == current_page else ""
        sidebar_html += f"""
            <div class="menu-item {active_class}" onclick="window.parent.postMessage({{type: 'streamlit:setComponentValue', value: '{item["id"]}'}}, '*')">
                <span class="icon">{item["icon"]}</span>
                <span>{item["name"]}</span>
            </div>
        """
    
    sidebar_html += """
        </div>
        <div class="sidebar-footer">
            © 2024 Maritime DSS<br>v2.0.0
        </div>
    </div>
    <div class="main-content">
    """
    
    st.markdown(sidebar_html, unsafe_allow_html=True)


def render_top_bar(title: str, breadcrumb: str = "") -> None:
    """Render top navigation bar"""
    st.markdown(
        f"""
        <div class="top-bar">
            <div>
                <h1 class="page-title">{title}</h1>
                {f'<div class="breadcrumb">{breadcrumb}</div>' if breadcrumb else ''}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def metric_card(label: str, value: str, change: str = "", icon: str = "📊", change_type: str = "positive") -> str:
    """Generate HTML for metric card"""
    change_html = ""
    if change:
        change_class = "positive" if change_type == "positive" else "negative"
        change_html = f'<div class="metric-change {change_class}">{change}</div>'
    
    return f"""
    <div class="metric-card">
        <div class="metric-header">
            <div class="metric-label">{label}</div>
            <div class="metric-icon">{icon}</div>
        </div>
        <div class="metric-value">{value}</div>
        {change_html}
    </div>
    """


def info_box(title: str, content: str) -> None:
    """Render info box"""
    st.markdown(
        f"""
        <div class="info-box">
            <div class="info-box-title">{title}</div>
            <div class="info-box-content">{content}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate great circle distance in nautical miles"""
    R = 3440.065
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))
    return R * c


def compute_distance_matrix(depot_lat: float, depot_lon: float, active_rows: List[Dict]) -> List[List[float]]:
    """Build distance matrix"""
    n = len(active_rows)
    dist = [[0.0] * (n + 2) for _ in range(n + 2)]
    
    for i in range(1, n + 1):
        dist[0][i] = haversine(depot_lat, depot_lon, active_rows[i - 1]["lat"], active_rows[i - 1]["lon"])
        dist[i][0] = dist[0][i]
    
    for i in range(1, n + 1):
        for j in range(i + 1, n + 1):
            dist[i][j] = haversine(
                active_rows[i - 1]["lat"],
                active_rows[i - 1]["lon"],
                active_rows[j - 1]["lat"],
                active_rows[j - 1]["lon"],
            )
            dist[j][i] = dist[i][j]
    
    for i in range(n + 1):
        dist[i][n + 1] = dist[i][0]
        dist[n + 1][i] = dist[0][i]
    
    return dist


def make_active_plant_rows() -> List[Dict]:
    """Get active plants with IDs"""
    rows = []
    for idx, plant in enumerate(st.session_state.fixed_plants, start=1):
        if plant.get("enabled", True):
            rows.append(
                {
                    "id": idx,
                    "name": plant["name"],
                    "lat": plant["lat"],
                    "lon": plant["lon"],
                    "cap": plant["cap"],
                    "init_stock": plant["init_stock"],
                    "cons_rate": plant["cons_rate"],
                    "deadline": plant.get("deadline", plant["init_stock"] / plant["cons_rate"]),
                }
            )
    return rows


def make_plants(active_rows: List[Dict]) -> List[Plant]:
    """Convert to Plant objects"""
    return [
        Plant(
            name=row["name"],
            cap=row["cap"],
            init_stock=row["init_stock"],
            cons_rate=row["cons_rate"],
            deadline=row.get("deadline"),
        )
        for row in active_rows
    ]


def build_map_view(active_rows: List[Dict], depot: Dict) -> Tuple[Dict, float]:
    """Calculate map center and zoom"""
    all_lats = [depot["lat"]] + [row["lat"] for row in active_rows]
    all_lons = [depot["lon"]] + [row["lon"] for row in active_rows]
    
    center = {"lat": sum(all_lats) / len(all_lats), "lon": sum(all_lons) / len(all_lons)}
    
    lat_span = max(all_lats) - min(all_lats)
    lon_span = max(all_lons) - min(all_lons)
    span = max(lat_span, lon_span)
    
    if span <= 1:
        zoom = 7.2
    elif span <= 3:
        zoom = 6.0
    elif span <= 6:
        zoom = 5.2
    elif span <= 12:
        zoom = 4.6
    elif span <= 20:
        zoom = 3.8
    else:
        zoom = 2.6
    
    return center, zoom


def colorize_figure(fig: go.Figure) -> None:
    """Apply modern chart styling"""
    fig.update_layout(
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
        font=dict(color="#2c3e50", size=13, family="Rajdhani"),
        title_font=dict(size=18, color="#2c3e50", family="Orbitron"),
        legend=dict(bgcolor="rgba(255,255,255,0.95)", bordercolor="#ecf0f1", borderwidth=1),
        margin=dict(l=20, r=20, t=60, b=20),
    )
    fig.update_xaxes(showgrid=True, gridcolor="#ecf0f1", zeroline=False)
    fig.update_yaxes(showgrid=True, gridcolor="#ecf0f1", zeroline=False)


# =============================================================================
# VISUALIZATION FUNCTIONS
# =============================================================================

def render_route_highlight(result: Dict) -> None:
    """Display route order with modern styling"""
    route_steps = [label for label in result["route_labels"] if label not in IGNORED_ROUTE_LABELS]
    
    nodes_html = '<div class="route-node start">🏁 Depot</div>'
    
    for idx, name in enumerate(route_steps, start=1):
        nodes_html += '<span class="route-arrow">→</span>'
        nodes_html += f'<div class="route-node"><span class="route-number">{idx}</span>{name}</div>'
    
    end_label = "Return to Depot" if result["route_labels"] and result["route_labels"][-1] == "Depot (return)" else "End of Service"
    nodes_html += '<span class="route-arrow">→</span>'
    nodes_html += f'<div class="route-node end">🏁 {end_label}</div>'
    
    st.markdown(
        f"""
        <div class="route-display">
            <div class="route-title">Route Sequence</div>
            <div class="route-flow">{nodes_html}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_plant_map(active_rows: List[Dict], depot: Dict, plot_key: str) -> None:
    """Render interactive plant map"""
    fig = go.Figure()
    center, zoom = build_map_view(active_rows, depot)
    
    # Depot
    fig.add_trace(
        go.Scattermapbox(
            lat=[depot["lat"]],
            lon=[depot["lon"]],
            mode="markers+text",
            marker=dict(size=32, color="#3498db", opacity=0.95),
            text=["D"],
            textfont=dict(size=18, color="#ffffff", family="Orbitron"),
            textposition="middle center",
            name="Depot",
            customdata=[f"<b>{depot['name']}</b><br>Main Depot"],
            hovertemplate="%{customdata}<extra></extra>",
        )
    )
    
    # Plants
    if active_rows:
        hover_rows = []
        for row in active_rows:
            hover_rows.append(
                f"<b>{row['name']}</b><br>"
                f"Plant #{row['id']}<br>"
                f"Capacity: {row['cap']:.0f} T<br>"
                f"Stock: {row['init_stock']:.0f} T<br>"
                f"Consumption: {row['cons_rate']:.1f} T/hr<br>"
                f"Deadline: {row['deadline']:.1f} hr"
            )
        
        fig.add_trace(
            go.Scattermapbox(
                lat=[row["lat"] for row in active_rows],
                lon=[row["lon"] for row in active_rows],
                mode="markers+text",
                marker=dict(size=40, color="#2ecc71", opacity=0.95),
                text=[str(row["id"]) for row in active_rows],
                textfont=dict(size=20, color="#ffffff", family="Orbitron"),
                textposition="middle center",
                name="Plants",
                customdata=hover_rows,
                hovertemplate="%{customdata}<extra></extra>",
            )
        )
    
    fig.update_layout(
        mapbox=dict(style="carto-positron", center=center, zoom=zoom),
        margin=dict(l=0, r=0, t=0, b=0),
        height=600,
        legend=dict(orientation="h", yanchor="bottom", y=0.01, xanchor="left", x=0.01),
    )
    
    st.plotly_chart(fig, use_container_width=True, key=plot_key)


def render_solution_map(result: Dict, active_rows: List[Dict], depot: Dict, rank: int) -> None:
    """Render solution route map"""
    coord_map = {"Depot": (depot["lat"], depot["lon"]), depot["name"]: (depot["lat"], depot["lon"])}
    for row in active_rows:
        coord_map[row["name"]] = (row["lat"], row["lon"])
    
    visit_order: Dict[str, int] = {}
    order = 1
    for label in result["route_labels"]:
        if label in IGNORED_ROUTE_LABELS:
            continue
        if label in coord_map and label not in visit_order:
            visit_order[label] = order
            order += 1
    
    center, zoom = build_map_view(active_rows, depot)
    fig = go.Figure()
    
    # Depot
    fig.add_trace(
        go.Scattermapbox(
            lat=[depot["lat"]],
            lon=[depot["lon"]],
            mode="markers+text",
            marker=dict(size=32, color="#3498db", opacity=0.95),
            text=["D"],
            textfont=dict(size=18, color="#ffffff", family="Orbitron"),
            textposition="middle center",
            name="Depot",
            hovertemplate="<b>Depot</b><extra></extra>",
        )
    )
    
    # Plants
    visited_lat, visited_lon, visited_text, visited_hover = [], [], [], []
    idle_lat, idle_lon, idle_text, idle_hover = [], [], [], []
    
    for row in active_rows:
        delivery = next((d for d in result["deliveries"] if d["Plant"] == row["name"]), None)
        hover_lines = [f"<b>{row['name']}</b>"]
        
        if row["name"] in visit_order:
            hover_lines.append(f"Visit order: {visit_order[row['name']]}")
        else:
            hover_lines.append("Not visited in this solution")
        
        if delivery:
            late = delivery.get("Lateness (hr)", 0)
            hover_lines.extend([
                f"Arrival: {delivery['Arrival (hr)']} hr",
                f"Deadline: {delivery['Eff. Deadline (hr)']} hr",
                f"Delivered: {delivery['Delivered (T)']} T",
                f"Lateness: {late:.3f} hr",
            ])
        
        hover_text = "<br>".join(hover_lines)
        
        if row["name"] in visit_order:
            visited_lat.append(row["lat"])
            visited_lon.append(row["lon"])
            visited_text.append(str(visit_order[row["name"]]))
            visited_hover.append(hover_text)
        else:
            idle_lat.append(row["lat"])
            idle_lon.append(row["lon"])
            idle_text.append(str(row["id"]))
            idle_hover.append(hover_text)
    
    # Unvisited
    if idle_lat:
        fig.add_trace(
            go.Scattermapbox(
                lat=idle_lat,
                lon=idle_lon,
                mode="markers+text",
                marker=dict(size=30, color="#95a5a6", opacity=0.9),
                text=idle_text,
                textfont=dict(size=16, color="#ffffff", family="Orbitron"),
                textposition="middle center",
                name="Unvisited",
                customdata=idle_hover,
                hovertemplate="%{customdata}<extra></extra>",
            )
        )
    
    # Visited
    if visited_lat:
        fig.add_trace(
            go.Scattermapbox(
                lat=visited_lat,
                lon=visited_lon,
                mode="markers+text",
                marker=dict(size=42, color="#2ecc71", opacity=0.95),
                text=visited_text,
                textfont=dict(size=22, color="#ffffff", family="Orbitron"),
                textposition="middle center",
                name="Visit order",
                customdata=visited_hover,
                hovertemplate="%{customdata}<extra></extra>",
            )
        )
    
    fig.update_layout(
        mapbox=dict(style="carto-positron", center=center, zoom=zoom),
        margin=dict(l=0, r=0, t=0, b=0),
        height=600,
        legend=dict(orientation="h", yanchor="bottom", y=0.01, xanchor="left", x=0.01),
    )
    
    st.plotly_chart(fig, use_container_width=True, key=f"solution_map_{rank}")


# =============================================================================
# PAGE RENDERERS
# =============================================================================

def render_dashboard() -> None:
    """Main dashboard page"""
    render_top_bar("Dashboard", "Home > Dashboard")
    
    active_rows = make_active_plant_rows()
    depot = FIXED_SCENARIO["depot"]
    
    # Metrics
    total_capacity = sum(row["cap"] for row in active_rows)
    total_stock = sum(row["init_stock"] for row in active_rows)
    avg_consumption = sum(row["cons_rate"] for row in active_rows) / len(active_rows) if active_rows else 0
    avg_deadline = sum(row["deadline"] for row in active_rows) / len(active_rows) if active_rows else 0
    
    st.markdown(
        f"""
        <div class="metric-grid">
            {metric_card("Active Plants", str(len(active_rows)), "6 plants in network", "🏭", "positive")}
            {metric_card("Total Capacity", f"{total_capacity:,.0f} T", f"{(total_stock/total_capacity*100):.1f}% utilized", "📦", "positive")}
            {metric_card("Avg Consumption", f"{avg_consumption:.2f} T/hr", "Fleet average", "⚡", "positive")}
            {metric_card("Avg Deadline", f"{avg_deadline:.1f} hr", "Time window", "⏱️", "positive")}
        </div>
        """,
        unsafe_allow_html=True,
    )
    
    # Quick info
    info_box(
        "System Status",
        f"Monitoring {len(active_rows)} active plants across the maritime network. "
        f"Total inventory capacity: {total_capacity:,.0f} tons. "
        f"Default vessel speed: {DEFAULT_SHIP['speed']} NM/hr."
    )
    
    # Network map
    st.markdown('<div class="chart-card"><div class="chart-title">🗺️ Network Overview</div>', unsafe_allow_html=True)
    render_plant_map(active_rows, depot, "dashboard_map")
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Plant summary table
    if active_rows:
        st.markdown('<div class="chart-card"><div class="chart-title">📋 Plant Summary</div>', unsafe_allow_html=True)
        df = pd.DataFrame(active_rows)
        df = df[["id", "name", "cap", "init_stock", "cons_rate", "deadline"]]
        df.columns = ["ID", "Plant", "Capacity (T)", "Current Stock (T)", "Consumption (T/hr)", "Deadline (hr)"]
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.markdown('</div>', unsafe_allow_html=True)


def render_optimizer() -> None:
    """Optimizer configuration and results page"""
    render_top_bar("Optimizer", "Home > Optimizer")
    
    depot = FIXED_SCENARIO["depot"]
    
    tab1, tab2 = st.tabs(["⚙️ Configuration", "📊 Results"])
    
    with tab1:
        col1, col2 = st.columns([1.2, 1])
        
        with col1:
            st.markdown('<div class="chart-card"><div class="chart-title">Plant Configuration</div>', unsafe_allow_html=True)
            
            for idx, plant in enumerate(st.session_state.fixed_plants):
                with st.expander(f"🏭 {plant['name']}", expanded=False):
                    enabled = st.toggle(
                        f"Active",
                        value=plant["enabled"],
                        key=f"enabled_{idx}",
                    )
                    plant["enabled"] = enabled
                    
                    c1, c2 = st.columns(2)
                    plant["cap"] = c1.number_input(
                        "Capacity (T)",
                        min_value=0.0,
                        value=float(plant["cap"]),
                        step=10.0,
                        key=f"cap_{idx}",
                    )
                    plant["init_stock"] = c2.number_input(
                        "Initial Stock (T)",
                        min_value=0.0,
                        value=float(plant["init_stock"]),
                        step=10.0,
                        key=f"init_{idx}",
                    )
                    
                    c3, c4 = st.columns(2)
                    plant["cons_rate"] = c3.number_input(
                        "Consumption (T/hr)",
                        min_value=0.01,
                        value=float(plant["cons_rate"]),
                        step=0.1,
                        key=f"cons_{idx}",
                    )
                    plant["deadline"] = c4.number_input(
                        "Deadline (hr)",
                        min_value=0.1,
                        value=float(plant.get("deadline") or plant["init_stock"] / plant["cons_rate"]),
                        step=1.0,
                        key=f"ddl_{idx}",
                    )
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col2:
            st.markdown('<div class="chart-card"><div class="chart-title">Vessel Settings</div>', unsafe_allow_html=True)
            
            c1, c2 = st.columns(2)
            empty_weight = c1.number_input("Empty Weight (T)", min_value=0.0, value=DEFAULT_SHIP["empty_weight"], step=100.0)
            pump_rate = c2.number_input("Pump Rate (T/hr)", min_value=0.1, value=DEFAULT_SHIP["pump_rate"], step=5.0)
            prep_time = c1.number_input("Prep Time (hr)", min_value=0.0, value=DEFAULT_SHIP["prep_time"], step=0.1)
            charter_rate = c2.number_input("Charter Rate ($/hr)", min_value=0.0, value=DEFAULT_SHIP["charter_rate"], step=50.0)
            fuel_cost = c1.number_input("Fuel Cost ($/T-NM)", min_value=0.0, value=DEFAULT_SHIP["fuel_cost"], step=0.01, format="%.4f")
            speed = c2.number_input("Speed (NM/hr)", min_value=0.1, value=DEFAULT_SHIP["speed"], step=1.0)
            
            st.markdown('</div>', unsafe_allow_html=True)
            
            st.markdown('<div class="chart-card"><div class="chart-title">Solver Options</div>', unsafe_allow_html=True)
            
            o1, o2 = st.columns(2)
            return_to_depot = o1.toggle("Closed Route", value=False)
            top_n = o2.number_input("Solutions", min_value=1, max_value=10, value=1)
            
            penalty = st.number_input(
                "Penalty Coefficient",
                min_value=0.0,
                value=1_000_000.0,
                step=100_000.0,
                format="%.0f",
            )
            
            st.markdown('</div>', unsafe_allow_html=True)
            
            active_rows = make_active_plant_rows()
            
            if active_rows:
                ship = Ship(
                    empty_weight=empty_weight,
                    pump_rate=pump_rate,
                    prep_time=prep_time,
                    charter_rate=charter_rate,
                    fuel_cost=fuel_cost,
                    speed=speed,
                )
                
                plants = make_plants(active_rows)
                dist = compute_distance_matrix(depot["lat"], depot["lon"], active_rows)
                diagnostics = quick_diagnostics(plants, ship, dist, return_to_depot=return_to_depot)
                
                for warning in diagnostics.get("warnings", []):
                    st.warning(warning)
                for issue in diagnostics.get("issues", []):
                    st.error(issue)
                
                if st.button("🚀 Run Optimization", type="primary", use_container_width=True):
                    with st.spinner("Solving optimization problem..."):
                        result = run_solver(
                            plants,
                            ship,
                            dist,
                            penalty=penalty,
                            return_to_depot=return_to_depot,
                            top_n=int(top_n),
                        )
                    st.session_state.last_result = result
                    st.session_state.last_inputs = {"active_rows": active_rows, "depot": depot}
                    st.success("✅ Optimization complete! View results in the Results tab.")
            else:
                st.error("⚠️ Select at least one active plant to run optimization.")
    
    with tab2:
        if st.session_state.last_result is None:
            info_box(
                "No Results Yet",
                "Run the optimization from the Configuration tab to view results here."
            )
        else:
            render_results(
                st.session_state.last_result,
                st.session_state.last_inputs["active_rows"],
                st.session_state.last_inputs["depot"],
            )


def render_plants() -> None:
    """Plant network page"""
    render_top_bar("Plant Network", "Home > Plant Network")
    
    depot = FIXED_SCENARIO["depot"]
    active_rows = make_active_plant_rows()
    
    col1, col2 = st.columns([1, 1.2])
    
    with col1:
        info_box(
            "Network Overview",
            f"Depot location: {depot['name']}. "
            f"Blue marker (D) = depot. Green numbered markers (1-6) = active plants. "
            f"Each plant displays its ID number for easy identification."
        )
        
        st.markdown('<div class="chart-card"><div class="chart-title">📋 Plant Details</div>', unsafe_allow_html=True)
        
        if active_rows:
            df = pd.DataFrame(active_rows)
            df = df[["id", "name", "cap", "init_stock", "cons_rate", "deadline"]]
            df.columns = ["ID", "Plant", "Capacity (T)", "Stock (T)", "Consumption (T/hr)", "Deadline (hr)"]
            st.dataframe(df, use_container_width=True, hide_index=True)
            
            st.markdown("**Key Metrics:**")
            avg_cap = df["Capacity (T)"].mean()
            avg_cons = df["Consumption (T/hr)"].mean()
            avg_deadline = df["Deadline (hr)"].mean()
            
            m1, m2, m3 = st.columns(3)
            m1.metric("Avg Capacity", f"{avg_cap:.0f} T")
            m2.metric("Avg Consumption", f"{avg_cons:.2f} T/hr")
            m3.metric("Avg Deadline", f"{avg_deadline:.1f} hr")
        else:
            st.warning("No active plants. Enable plants in the Optimizer page.")
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="chart-card"><div class="chart-title">🗺️ Network Map</div>', unsafe_allow_html=True)
        render_plant_map(active_rows, depot, "network_map")
        st.markdown('</div>', unsafe_allow_html=True)


def render_analytics() -> None:
    """Analytics page (placeholder)"""
    render_top_bar("Analytics", "Home > Analytics")
    
    info_box(
        "Analytics Module",
        "Advanced analytics and historical performance tracking coming soon. "
        "This module will include route efficiency analysis, cost trends, and predictive insights."
    )
    
    # Placeholder metrics
    st.markdown(
        f"""
        <div class="metric-grid">
            {metric_card("Avg Route Efficiency", "92.3%", "+3.2% vs last month", "📈", "positive")}
            {metric_card("Total Distance", "8,450 NM", "Last 30 days", "🌊", "positive")}
            {metric_card("Cost Savings", "$124,500", "+$15K vs target", "💰", "positive")}
            {metric_card("On-Time Rate", "96.8%", "+1.5% improvement", "✅", "positive")}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_settings() -> None:
    """Settings page (placeholder)"""
    render_top_bar("Settings", "Home > Settings")
    
    info_box(
        "System Settings",
        "Configure system preferences, user access, and optimization parameters."
    )
    
    st.markdown('<div class="chart-card"><div class="chart-title">⚙️ General Settings</div>', unsafe_allow_html=True)
    
    st.selectbox("Default Distance Unit", ["Nautical Miles", "Kilometers", "Miles"])
    st.selectbox("Default Weight Unit", ["Metric Tons", "Short Tons", "Long Tons"])
    st.selectbox("Currency", ["USD", "EUR", "GBP", "TRY"])
    
    st.markdown('</div>', unsafe_allow_html=True)


def render_results(multi: Dict, active_rows: List[Dict], depot: Dict) -> None:
    """Render optimization results"""
    if isinstance(multi, str):
        st.error(multi)
        return
    
    if multi.get("kind") == "validation_error":
        st.error("❌ Input validation failed.")
        for issue in multi["diagnostics"]["issues"]:
            st.write(f"• {issue}")
        return
    
    if multi.get("kind") == "infeasible":
        st.error(f"❌ {multi['message']}")
        checks = pd.DataFrame(multi["diagnostics"].get("plant_checks", []))
        if not checks.empty:
            st.dataframe(checks, use_container_width=True, hide_index=True)
        return
    
    solutions = multi.get("solutions", [])
    st.caption(f"✅ Found {multi.get('n_found', len(solutions))} solution(s) | Solve time: {multi['elapsed']} s")
    
    for warning in multi.get("diagnostics", {}).get("warnings", []):
        st.warning(warning)
    
    if len(solutions) == 1:
        render_one_solution(solutions[0], active_rows, depot, rank=1)
    else:
        tabs = st.tabs([f"Solution #{sol['solution_rank']} — {sol['status']}" for sol in solutions])
        for tab, solution in zip(tabs, solutions):
            with tab:
                render_one_solution(solution, active_rows, depot, rank=solution["solution_rank"])


def render_one_solution(result: Dict, active_rows: List[Dict], depot: Dict, rank: int = 1) -> None:
    """Render single solution details"""
    on_time = sum(1 for delivery in result["deliveries"] if delivery["On Time"])
    total_plants = len(result["deliveries"])
    late_count = total_plants - on_time
    
    # Key metrics
    st.markdown(
        f"""
        <div class="metric-grid">
            {metric_card("Total Cost", f"${result['total_cost']:,.0f}", "", "💰")}
            {metric_card("Voyage Time", f"{result['voyage_time']:.2f} hr", "", "⏱️")}
            {metric_card("On-Time Deliveries", f"{on_time}/{total_plants}", f"{(on_time/total_plants*100):.1f}%", "✅")}
            {metric_card("Lateness Penalty", f"${result['lateness_penalty']:,.0f}", f"{late_count} plant(s) late" if late_count > 0 else "All on time", "⚠️", "negative" if late_count > 0 else "positive")}
        </div>
        """,
        unsafe_allow_html=True,
    )
    
    # Route visualization
    render_route_highlight(result)
    
    # Tabs for detailed views
    t1, t2, t3, t4 = st.tabs(["🗺️ Map", "📦 Deliveries", "💰 Costs", "🔧 Technical"])
    
    with t1:
        info_box(
            "Route Map Guide",
            "Blue D = depot. Green numbered circles = visited plants showing route order (1, 2, 3...). "
            "Gray markers = unvisited plants."
        )
        render_solution_map(result, active_rows, depot, rank=rank)
    
    with t2:
        df = pd.DataFrame(result["deliveries"])
        if not df.empty:
            # Charts
            col1, col2 = st.columns(2)
            
            with col1:
                delivery_bar = go.Figure(
                    data=[
                        go.Bar(
                            x=df["Plant"],
                            y=df["Delivered (T)"],
                            text=df["Delivered (T)"].round(1),
                            textposition="outside",
                            marker_color="#3498db",
                        )
                    ]
                )
                delivery_bar.update_layout(title="Delivered Quantities", xaxis_title="Plant", yaxis_title="Tons")
                colorize_figure(delivery_bar)
                st.plotly_chart(delivery_bar, use_container_width=True)
            
            with col2:
                timing_fig = go.Figure()
                timing_fig.add_trace(
                    go.Bar(
                        x=df["Plant"],
                        y=df["Arrival (hr)"],
                        name="Arrival",
                        marker_color="#3498db",
                    )
                )
                timing_fig.add_trace(
                    go.Bar(
                        x=df["Plant"],
                        y=df["Eff. Deadline (hr)"],
                        name="Deadline",
                        marker_color="#e74c3c",
                    )
                )
                timing_fig.update_layout(title="Arrival vs Deadline", xaxis_title="Plant", yaxis_title="Hours", barmode="group")
                colorize_figure(timing_fig)
                st.plotly_chart(timing_fig, use_container_width=True)
        
        # Table
        st.markdown('<div class="chart-card"><div class="chart-title">Delivery Details</div>', unsafe_allow_html=True)
        
        def highlight_late(row: pd.Series):
            if not row.get("On Time", True):
                return ["background-color: #ffe5e5"] * len(row)
            return [""] * len(row)
        
        st.dataframe(df.style.apply(highlight_late, axis=1), use_container_width=True, hide_index=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with t3:
        cost_df = pd.DataFrame([
            {"Component": "Charter Cost", "Value ($)": round(result["charter"], 2)},
            {"Component": "Empty Fuel", "Value ($)": round(result["empty_fuel"], 2)},
            {"Component": "Cargo Fuel", "Value ($)": round(result["cargo_fuel"], 2)},
            {"Component": "Lateness Penalty", "Value ($)": round(result["lateness_penalty"], 2)},
        ])
        
        col1, col2 = st.columns(2)
        
        with col1:
            cost_bar = go.Figure(
                data=[
                    go.Bar(
                        x=cost_df["Component"],
                        y=cost_df["Value ($)"],
                        text=cost_df["Value ($)"].round(2),
                        textposition="outside",
                        marker_color="#3498db",
                    )
                ]
            )
            cost_bar.update_layout(title="Cost Breakdown", xaxis_title="Component", yaxis_title="Cost ($)")
            colorize_figure(cost_bar)
            st.plotly_chart(cost_bar, use_container_width=True)
        
        with col2:
            positive_costs = cost_df[cost_df["Value ($)"] > 0]
            if not positive_costs.empty:
                cost_pie = go.Figure(
                    data=[
                        go.Pie(
                            labels=positive_costs["Component"],
                            values=positive_costs["Value ($)"],
                            hole=0.45,
                            textinfo="label+percent",
                        )
                    ]
                )
                cost_pie.update_layout(title="Cost Distribution")
                colorize_figure(cost_pie)
                st.plotly_chart(cost_pie, use_container_width=True)
        
        total_row = pd.DataFrame([{"Component": "TOTAL", "Value ($)": round(result["total_cost"], 2)}])
        st.dataframe(pd.concat([cost_df, total_row], ignore_index=True), use_container_width=True, hide_index=True)
    
    with t4:
        st.markdown("**Active Arcs:**")
        st.dataframe(pd.DataFrame(result["arcs"]), use_container_width=True, hide_index=True)
        
        pre = result.get("pre", {})
        if pre:
            st.markdown("**Model Parameters:**")
            st.json({
                "worst_case_cargo_Q": round(pre.get("Q", 0.0), 3),
                "penalty_coefficient": pre.get("penalty"),
                "terminal_label": pre.get("terminal_label"),
            })


# =============================================================================
# SESSION STATE & MAIN
# =============================================================================

if "fixed_plants" not in st.session_state:
    st.session_state.fixed_plants = [dict(item, enabled=True) for item in FIXED_SCENARIO["plants"]]
if "last_result" not in st.session_state:
    st.session_state.last_result = None
if "last_inputs" not in st.session_state:
    st.session_state.last_inputs = None
if "nav_page" not in st.session_state:
    st.session_state.nav_page = "dashboard"


# Inject CSS
inject_modern_css()

# Render sidebar
render_sidebar()

# Route to page
current_page = st.session_state.nav_page

if current_page == "dashboard":
    render_dashboard()
elif current_page == "optimizer":
    render_optimizer()
elif current_page == "plants":
    render_plants()
elif current_page == "analytics":
    render_analytics()
elif current_page == "settings":
    render_settings()
else:
    render_dashboard()

# Close main content div
st.markdown('</div>', unsafe_allow_html=True)
