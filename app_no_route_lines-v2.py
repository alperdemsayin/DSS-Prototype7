"""User-friendly Streamlit dashboard for maritime routing optimization."""

import json
import math
from typing import Dict, List, Tuple

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from structures import Plant, Ship
from solver import quick_diagnostics, run_solver

st.set_page_config(
    page_title="Maritime Optimizer",
    page_icon="⚓",
    layout="wide",
    initial_sidebar_state="expanded",
)

APP_TITLE = "Maritime Inventory Routing"
APP_SUBTITLE = "Decision support dashboard for route planning, plant monitoring, and cost analysis."

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

MENU_ITEMS = ["Dashboard Home", "Scenario Optimizer", "Network Map"]
IGNORED_ROUTE_LABELS = {"Depot", "End of service", "Depot (return)"}


# -----------------------------------------------------------------------------
# Styling (Boxes & Menus Modern Theme)
# -----------------------------------------------------------------------------
def inject_custom_css() -> None:
    st.markdown(
        """
        <style>
        /* Base Backgrounds */
        .stApp { background-color: #f8fafc; }
        [data-testid="stAppViewContainer"] { background: #f8fafc; }
        
        /* Sidebar Styling */
        [data-testid="stSidebar"] {
            background-color: #ffffff;
            border-right: 1px solid #e2e8f0;
        }
        
        /* Box/Container Styling */
        div[data-testid="stVerticalBlockBorderWrapper"] > div {
            background: #ffffff;
            border-radius: 12px;
            border: 1px solid #e2e8f0;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
            padding: 1rem;
        }

        /* Hero Banner */
        .hero-box {
            background: #0f172a;
            border-radius: 16px;
            padding: 2rem;
            color: white;
            margin-bottom: 1.5rem;
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
        }
        .hero-box h1 { color: #f8fafc !important; font-size: 2.2rem; margin-bottom: 0.5rem; font-weight: 700; }
        .hero-box p { color: #cbd5e1 !important; font-size: 1.1rem; margin: 0; }

        /* Metric Cards */
        [data-testid="stMetric"] {
            background: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 12px;
            padding: 1rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }
        [data-testid="stMetricValue"] { color: #0f172a !important; font-weight: 700; }
        [data-testid="stMetricLabel"] { color: #64748b !important; font-weight: 600; text-transform: uppercase; font-size: 0.8rem; }

        /* Buttons */
        .stButton > button {
            border-radius: 8px;
            font-weight: 600;
            transition: all 0.2s;
        }
        .stButton > button[kind="primary"] {
            background-color: #2563eb;
            color: white;
            border: none;
        }
        .stButton > button[kind="primary"]:hover {
            background-color: #1d4ed8;
            box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3);
        }

        /* Route Chips */
        .route-chip {
            display: inline-flex;
            align-items: center;
            background: #f1f5f9;
            border: 1px solid #cbd5e1;
            padding: 0.4rem 0.75rem;
            border-radius: 8px;
            font-weight: 600;
            color: #334155;
            margin: 0.25rem;
        }
        .route-chip.start { background: #dcfce7; border-color: #86efac; color: #166534; }
        .route-chip.end { background: #fee2e2; border-color: #fca5a5; color: #991b1b; }
        .route-arrow { color: #94a3b8; font-weight: bold; margin: 0 0.25rem; }

        /* DataFrames */
        .stDataFrame { border-radius: 8px; overflow: hidden; border: 1px solid #e2e8f0; }
        </style>
        """,
        unsafe_allow_html=True,
    )

inject_custom_css()

# -----------------------------------------------------------------------------
# Utility functions
# -----------------------------------------------------------------------------
def haversine_nm(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 3440.065
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return r * 2 * math.asin(math.sqrt(a))

@st.cache_data(show_spinner=False)
def compute_distance_matrix(depot_lat: float, depot_lon: float, plant_rows: List[Dict]):
    n = len(plant_rows)
    dist = [[0.0] * (n + 2) for _ in range(n + 2)]
    points = [(depot_lat, depot_lon)] + [(p["lat"], p["lon"]) for p in plant_rows]
    for i in range(n + 1):
        for j in range(n + 1):
            if i != j:
                dist[i][j] = round(haversine_nm(points[i][0], points[i][1], points[j][0], points[j][1]), 1)
    return dist

def make_active_plant_rows() -> List[Dict]:
    return [
        {
            "id": i + 1, "name": item["name"], "lat": float(item["lat"]), "lon": float(item["lon"]),
            "cap": float(item["cap"]), "init_stock": float(item["init_stock"]),
            "cons_rate": float(item["cons_rate"]), "deadline": float(item["deadline"]),
        }
        for i, item in enumerate(st.session_state.fixed_plants) if item["enabled"]
    ]

def make_plants(rows: List[Dict]) -> List[Plant]:
    return [Plant(name=r["name"], cap=r["cap"], init_stock=r["init_stock"], cons_rate=r["cons_rate"], deadline=r["deadline"]) for r in rows]

def navigate(page_name: str) -> None:
    st.session_state.nav_page = page_name
    st.rerun()

def build_map_view(active_rows: List[Dict], depot: Dict) -> Tuple[Dict, float]:
    points = [(depot["lat"], depot["lon"])] + [(row["lat"], row["lon"]) for row in active_rows]
    latitudes = [lat for lat, _ in points]
    longitudes = [lon for _, lon in points]
    center = {"lat": sum(latitudes) / len(latitudes), "lon": sum(longitudes) / len(longitudes)}
    span = max(max(latitudes) - min(latitudes), max(longitudes) - min(longitudes)) if len(latitudes) > 1 else 0.0
    
    if span <= 1: zoom = 7.2
    elif span <= 3: zoom = 6.0
    elif span <= 6: zoom = 5.2
    elif span <= 12: zoom = 4.6
    else: zoom = 3.8
    return center, zoom

def render_route_highlight(result: Dict) -> None:
    route_steps = [label for label in result["route_labels"] if label not in IGNORED_ROUTE_LABELS]
    chips = ['<span class="route-chip start">Depot</span>']
    for idx, name in enumerate(route_steps, start=1):
        chips.append('<span class="route-arrow">→</span>')
        chips.append(f'<span class="route-chip"><b>{idx}.</b> &nbsp; {name}</span>')

    end_label = "Return to Depot" if result["route_labels"] and result["route_labels"][-1] == "Depot (return)" else "End of Service"
    chips.append('<span class="route-arrow">→</span>')
    chips.append(f'<span class="route-chip end">{end_label}</span>')

    st.markdown(f'<div style="margin: 1rem 0;">{"".join(chips)}</div>', unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# Maps & Charts
# -----------------------------------------------------------------------------
def render_plant_map(active_rows: List[Dict], depot: Dict, plot_key: str) -> None:
    fig = go.Figure()
    center, zoom = build_map_view(active_rows, depot)

    fig.add_trace(go.Scattermapbox(
        lat=[depot["lat"]], lon=[depot["lon"]], mode="markers+text",
        marker=dict(size=24, color="#1e293b"), text=["D"],
        textfont=dict(size=14, color="white", family="Arial Black"),
        name="Depot", hoverinfo="text", hovertext=f"<b>{depot['name']}</b><br>Depot"
    ))

    if active_rows:
        fig.add_trace(go.Scattermapbox(
            lat=[row["lat"] for row in active_rows], lon=[row["lon"] for row in active_rows],
            mode="markers+text", marker=dict(size=28, color="#3b82f6"),
            text=[str(row["id"]) for row in active_rows],
            textfont=dict(size=14, color="white", family="Arial Black"),
            name="Plants", hoverinfo="text",
            hovertext=[f"<b>{r['name']}</b><br>ID: {r['id']}<br>Cap: {r['cap']}T" for r in active_rows]
        ))

    fig.update_layout(
        mapbox=dict(style="carto-positron", center=center, zoom=zoom),
        margin=dict(l=0, r=0, t=0, b=0), height=400, showlegend=False
    )
    st.plotly_chart(fig, use_container_width=True, key=plot_key)

def colorize_figure(fig: go.Figure) -> None:
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#334155"), margin=dict(l=10, r=10, t=40, b=10)
    )

# -----------------------------------------------------------------------------
# Views
# -----------------------------------------------------------------------------
def render_sidebar() -> None:
    st.sidebar.markdown("## ⚓ Route Optimizer")
    current_index = MENU_ITEMS.index(st.session_state.nav_page)
    selected = st.sidebar.radio("Navigation Menu", MENU_ITEMS, index=current_index, label_visibility="collapsed")
    if selected != st.session_state.nav_page:
        st.session_state.nav_page = selected
        st.rerun()
    
    st.sidebar.divider()
    active_rows = make_active_plant_rows()
    st.sidebar.metric("Active Destinations", f"{len(active_rows)} / {len(FIXED_SCENARIO['plants'])}")
    st.sidebar.metric("Vessel Speed", f"{DEFAULT_SHIP['speed']} NM/hr")

def render_header() -> None:
    st.markdown(
        f"""
        <div class="hero-box">
            <h1>{APP_TITLE}</h1>
            <p>{APP_SUBTITLE}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

def render_home() -> None:
    render_header()
    active_rows = make_active_plant_rows()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Plants", len(FIXED_SCENARIO["plants"]))
    col2.metric("Active for Routing", len(active_rows))
    col3.metric("System Mode", "Open / Closed")
    col4.metric("Status", "Ready" if active_rows else "Setup Required")

    left, right = st.columns([1, 1])
    with left:
        with st.container(border=True):
            st.markdown("### 📋 Quick Actions")
            st.write("Configure your fleet and select active nodes to run the optimization model.")
            if st.button("Configure & Run Optimizer", type="primary", use_container_width=True):
                navigate("Scenario Optimizer")
            if st.button("View Full Network Map", use_container_width=True):
                navigate("Network Map")

    with right:
        with st.container(border=True):
            st.markdown("### 🗺️ Network Overview")
            render_plant_map(active_rows, FIXED_SCENARIO["depot"], plot_key="home_map")

def render_optimizer() -> None:
    st.markdown("## Scenario Optimizer")
    
    tab_setup, tab_results = st.tabs(["⚙️ Configuration Setup", "📊 Optimization Results"])

    with tab_setup:
        col_plants, col_settings = st.columns([1.2, 0.8])

        with col_plants:
            with st.container(border=True):
                st.markdown("### 📍 Destination Nodes")
                st.caption("Toggle plants and set demands. Adjust deadlines and capacities as needed.")
                
                for idx, plant in enumerate(st.session_state.fixed_plants):
                    with st.expander(f"{'✅' if plant['enabled'] else '❌'} {plant['name']}", expanded=plant['enabled']):
                        plant["enabled"] = st.toggle("Include in route", value=plant["enabled"], key=f"tgl_{idx}")
                        c1, c2, c3, c4 = st.columns(4)
                        plant["cap"] = c1.number_input("Capacity (T)", value=float(plant["cap"]), key=f"c_{idx}")
                        plant["init_stock"] = c2.number_input("Stock (T)", value=float(plant["init_stock"]), key=f"i_{idx}")
                        plant["cons_rate"] = c3.number_input("Burn (T/hr)", value=float(plant["cons_rate"]), key=f"r_{idx}")
                        plant["deadline"] = c4.number_input("Deadline", value=float(plant["deadline"]), key=f"d_{idx}")

        with col_settings:
            with st.container(border=True):
                st.markdown("### 🚢 Fleet Parameters")
                c1, c2 = st.columns(2)
                empty_weight = c1.number_input("Empty Wgt (T)", value=DEFAULT_SHIP["empty_weight"], step=100.0)
                pump_rate = c2.number_input("Pump Rate (T/hr)", value=DEFAULT_SHIP["pump_rate"], step=5.0)
                prep_time = c1.number_input("Prep Time (hr)", value=DEFAULT_SHIP["prep_time"], step=0.1)
                speed = c2.number_input("Speed (NM/hr)", value=DEFAULT_SHIP["speed"], step=1.0)
                
            with st.container(border=True):
                st.markdown("### ⚙️ Solver Settings")
                return_to_depot = st.toggle("Return to Depot (Closed Route)", value=False)
                penalty = st.number_input("Lateness Penalty Weight", value=1000000.0, step=100000.0, format="%.0f")
                
                active_rows = make_active_plant_rows()
                if st.button("🚀 Run Solver", type="primary", use_container_width=True):
                    if not active_rows:
                        st.error("Select at least one destination.")
                    else:
                        ship = Ship(empty_weight, pump_rate, prep_time, DEFAULT_SHIP["charter_rate"], DEFAULT_SHIP["fuel_cost"], speed)
                        plants = make_plants(active_rows)
                        dist = compute_distance_matrix(FIXED_SCENARIO["depot"]["lat"], FIXED_SCENARIO["depot"]["lon"], active_rows)
                        
                        with st.spinner("Optimizing route sequence..."):
                            res = run_solver(plants, ship, dist, penalty=penalty, return_to_depot=return_to_depot)
                        
                        st.session_state.last_result = res
                        st.session_state.last_inputs = {"active_rows": active_rows, "depot": FIXED_SCENARIO["depot"]}
                        st.success("Routing calculated! Check the Results tab.")

    with tab_results:
        if st.session_state.last_result is None:
            st.info("Configure your scenario and click 'Run Solver' to view results.")
        else:
            res = st.session_state.last_result
            if res.get("kind") in ["validation_error", "infeasible"]:
                st.error(res.get("message", "Validation failed."))
            else:
                sol = res["solutions"][0]
                st.markdown("### Recommended Route Sequence")
                render_route_highlight(sol)
                
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Total Voyage Cost", f"${sol['total_cost']:,.0f}")
                c2.metric("Total Voyage Time", f"{sol['voyage_time']:.1f} hr")
                c3.metric("Fuel Cost", f"${sol['cargo_fuel'] + sol['empty_fuel']:,.0f}")
                
                late_count = sum(1 for d in sol["deliveries"] if not d["On Time"])
                c4.metric("Late Deliveries", late_count, delta=f"-${sol['lateness_penalty']:,.0f}" if late_count else "All on time", delta_color="inverse")

                with st.container(border=True):
                    st.markdown("#### Delivery Manifest")
                    st.dataframe(pd.DataFrame(sol["deliveries"]), use_container_width=True)

def render_plant_map_page() -> None:
    st.markdown("## Network Map")
    active_rows = make_active_plant_rows()
    
    with st.container(border=True):
        render_plant_map(active_rows, FIXED_SCENARIO["depot"], plot_key="full_map")

# -----------------------------------------------------------------------------
# Session State Initialization
# -----------------------------------------------------------------------------
if "fixed_plants" not in st.session_state:
    st.session_state.fixed_plants = [dict(item, enabled=True) for item in FIXED_SCENARIO["plants"]]
if "last_result" not in st.session_state:
    st.session_state.last_result = None
if "nav_page" not in st.session_state:
    st.session_state.nav_page = "Dashboard Home"

# -----------------------------------------------------------------------------
# App Shell
# -----------------------------------------------------------------------------
render_sidebar()

if st.session_state.nav_page == "Dashboard Home":
    render_home()
elif st.session_state.nav_page == "Scenario Optimizer":
    render_optimizer()
else:
    render_plant_map_page()
