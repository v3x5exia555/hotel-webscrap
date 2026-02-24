import dash
from dash import dcc, html, dash_table
from dash.dependencies import Input, Output
import dash_bootstrap_components as dbc
import pandas as pd
import sqlite3
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import os
import yaml

# Database Path
DB_PATH = "data/hotel_data.db"
REG_PATH = "data/property_registration.csv"

SUBMITTED_PATH = "data/submitted_records.csv"

def fetch_pickup_trends():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM pickup_trends", conn)
    conn.close()
    if not df.empty:
        df['detected_at'] = pd.to_datetime(df['detected_at'])
    return df

def fetch_data():
    if not os.path.exists(DB_PATH):
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    
    conn = sqlite3.connect(DB_PATH, timeout=60)
    try:
        df = pd.read_sql_query("SELECT * FROM snapshots", conn)
        
        # Pickup Trends Data
        try:
            trends_df = pd.read_sql_query("SELECT * FROM pickup_trends", conn)
        except:
            trends_df = pd.DataFrame(columns=['hotel_name', 'stay_date', 'nights', 'platform', 'pickup_count', 'estimated_revenue', 'calculation_date'])
            
        # Aggregated Pickup for metrics
        pickup_query = """
        SELECT hotel_name, platform, SUM(pickup_count) as total_pickup, SUM(nights * pickup_count) as total_nights
        FROM pickup_trends
        GROUP BY hotel_name, platform
        """
        try:
            pickup_df = pd.read_sql_query(pickup_query, conn)
        except:
            pickup_df = pd.DataFrame(columns=['hotel_name', 'platform', 'total_pickup', 'total_nights'])
    finally:
        conn.close()
    
    # Load Registration Data
    if os.path.exists(REG_PATH):
        reg_df = pd.read_csv(REG_PATH)
    else:
        reg_df = pd.DataFrame(columns=['Hotel Name', 'Operator', 'Registration No', 'Registration Status'])
        
    # Load Submitted Data
    if os.path.exists(SUBMITTED_PATH):
        sub_df = pd.read_csv(SUBMITTED_PATH)
    else:
        sub_df = pd.DataFrame(columns=['Hotel Name', 'Submitted Nights', 'Tax Submitted'])
        
    return df, reg_df, pickup_df, trends_df, sub_df

# Initialize the Dash app
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.CYBORG, dbc.icons.BOOTSTRAP])
app.title = "Pahang Hotel Intelligence Dashboard"

# Layout
app.layout = dbc.Container([
    # Header
    dbc.Row([
        dbc.Col([
            html.Div([
                html.H1([html.I(className="bi bi-shield-check me-3"), "Pahang Revenue Intelligence & Compliance"], 
                        className="text-center mt-4 text-info fw-bold"),
                html.P("Automated Revenue Audit & Tax Compliance System", className="text-center text-muted mb-4"),
                dbc.Row([
                    dbc.Col([
                        dbc.Button([html.I(className="bi bi-arrow-clockwise me-2"), "Full Refresh Dashboard"], 
                                   id="refresh-button", color="info", className="shadow-sm fw-bold px-4")
                    ], width="auto")
                ], justify="center")
            ], className="py-3 shadow-sm rounded bg-dark mb-4")
        ], width=12)
    ]),

    # Filters Section
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    dbc.Row([
                        dbc.Col([
                            html.Label("Search Property", className="text-light small fw-bold"),
                            dcc.Input(id="search-filter", placeholder="Search by name...", type="text", 
                                      className="form-control bg-dark border-info text-white shadow-none",
                                      style={'color': 'white', 'fontWeight': '500'})
                        ], width=2),
                        dbc.Col([
                            html.Label("District", className="text-light small fw-bold"),
                            dcc.Dropdown(id="district-filter", multi=True, placeholder="All Districts", className="text-dark")
                        ], width=2),
                        dbc.Col([
                            html.Label("Area", className="text-light small fw-bold"),
                            dcc.Dropdown(id="area-filter", multi=True, placeholder="All Areas", className="text-dark")
                        ], width=2),
                        dbc.Col([
                            html.Label("Platform", className="text-muted small"),
                            dcc.Dropdown(id="platform-filter", multi=True, placeholder="All Platforms", className="bg-dark text-white")
                        ], width=2),
                        dbc.Col([
                            html.Label("Status", className="text-muted small"),
                            dcc.Dropdown(id="status-filter", multi=True, placeholder="All Status", options=[
                                {'label': 'OK', 'value': 'OK'},
                                {'label': 'HIGH', 'value': 'HIGH'},
                                {'label': 'CRITICAL', 'value': 'CRITICAL'}
                            ], className="bg-dark text-white")
                        ], width=2),
                        dbc.Col([
                            html.Label("Analysis Period", className="text-muted small"),
                            dcc.DatePickerRange(
                                id="date-filter",
                                min_date_allowed=datetime(2025, 1, 1),
                                max_date_allowed=datetime(2027, 12, 31),
                                start_date=datetime.now().date(),
                                end_date=datetime(datetime.now().year, 12, 31),
                                className="bg-dark text-white border-secondary",
                                style={'fontSize': '11px'}
                            )
                        ], width=2),
                    ]),
                    dbc.Row([
                        dbc.Col([
                            html.Label("Booking Gap", className="text-muted small"),
                            dcc.Dropdown(id="gap-filter", placeholder="Any Gap", options=[
                                {'label': 'Has Missing Nights', 'value': 'missing'},
                                {'label': 'Full Compliance', 'value': 'exact'}
                            ], className="bg-dark text-white")
                        ], width=2),
                    ], className="mt-2")
                ])
            ], className="mb-4 shadow-sm border-0 bg-dark")
        ], width=12)
    ]),
    
    # Summary Metrics Row
    dbc.Row(id="summary-metrics-container", className="mb-4"),

    # Tabs
    dbc.Tabs([
        dbc.Tab(label="Audit Analysis", children=[
            dbc.Row([
                dbc.Col([
                    html.H4("Revenue Audit Matrix", className="mt-4 mb-3 text-info"),
                    html.Div(id="audit-table-container")
                ], width=12)
            ])
        ], tab_id="audit"),
        dbc.Tab(label="Enforcement Priority", children=[
            dbc.Row([
                dbc.Col([
                    html.H4("Priority Enforcement List", className="mt-4 mb-3 text-warning"),
                    html.Div(id="priority-table-container")
                ], width=12)
            ]),
            dbc.Row([
                dbc.Col([
                    html.H4("Property Capacity Validation (Suspicious Activity)", className="mt-4 mb-3 text-danger"),
                    html.Div(id="capacity-table-container")
                ], width=12)
            ])
        ], tab_id="enforcement"),
        dbc.Tab(label="Market Demand", children=[
            dbc.Row([
                dbc.Col([
                    html.H4("Real-Time Reservation Behavior (Pickups)", className="mt-4 mb-3 text-success"),
                    dcc.Graph(id="pickup-trend-graph")
                ], width=12)
            ]),
            dbc.Row([
                dbc.Col([
                    html.H4("Top Performing Properties (High Booking Velocity)", className="mt-4 mb-3 text-success"),
                    html.Div(id="pickup-table-container")
                ], width=12)
            ])
        ], tab_id="behavior"),
        dbc.Tab(label="Analytics & Trends", children=[
            dbc.Row([
                dbc.Col([
                    html.H5("Platform Distribution Detail", className="text-info mb-3 fw-bold"),
                    html.Div(id="platform-dist-container")
                ], width=6),
                dbc.Col([
                    html.H5("Area-Based Audit Overview", className="text-info mb-3 fw-bold"),
                    html.Div(id="area-overview-container")
                ], width=6)
            ], className="mt-3 mb-3"),
            dbc.Row([
                dbc.Col(dcc.Graph(id="daerah-distribution"), width=6),
                dbc.Col(dcc.Graph(id="bentong-detail-distribution"), width=6),
            ], className="mt-2 text-center"),
            dbc.Row([
                dbc.Col(dcc.Graph(id="property-type-distribution"), width=6),
                dbc.Col(dcc.Graph(id="compliance-summary"), width=6),
            ], className="mt-2"),
        ], tab_id="trends"),
    ], className="mt-2", id="tabs", active_tab="audit"),

    dcc.Interval(id='interval-component', interval=300*1000, n_intervals=0)
], fluid=True, className="p-4")

@app.callback(
    [Output("district-filter", "options"),
     Output("area-filter", "options"),
     Output("platform-filter", "options")],
    [Input("interval-component", "n_intervals")]
)
def update_filter_options(n):
    df, _, _, _, _ = fetch_data()
    if df.empty:
        return [], [], []
    
    # Infer district for filter options if data hasn't been re-scraped yet
    try:
        with open('configs/locations.yaml', 'r') as f:
            loc_cfg = yaml.safe_load(f)
        dist_map = {}
        for d in loc_cfg.get('districts', []):
            for a in d.get('areas', []):
                dist_map[a['name']] = d['name']
    except:
        dist_map = {}

    if 'district' not in df.columns or df['district'].isnull().any():
        df['district'] = df.get('district', pd.Series([None]*len(df)))
        df.loc[df['district'].isnull(), 'district'] = df['location'].map(dist_map).fillna('Other')

    districts = [{'label': i, 'value': i} for i in sorted(df['district'].unique())]
    areas = [{'label': i, 'value': i} for i in sorted(df['location'].unique() if 'location' in df.columns else [])]
    platforms = [{'label': i, 'value': i} for i in sorted(df['platform'].unique() if 'platform' in df.columns else [])]
    return districts, areas, platforms

@app.callback(
    [Output("summary-metrics-container", "children"),
     Output("audit-table-container", "children"),
     Output("priority-table-container", "children"),
     Output("capacity-table-container", "children"),
     Output("platform-dist-container", "children"),
     Output("area-overview-container", "children"),
     Output("pickup-trend-graph", "figure"),
     Output("pickup-table-container", "children"),
     Output("daerah-distribution", "figure"),
     Output("bentong-detail-distribution", "figure"),
     Output("property-type-distribution", "figure"),
     Output("compliance-summary", "figure")],
    [Input("interval-component", "n_intervals"),
     Input("refresh-button", "n_clicks"),
     Input("search-filter", "value"),
     Input("district-filter", "value"),
     Input("area-filter", "value"),
     Input("platform-filter", "value"),
     Input("status-filter", "value"),
     Input("gap-filter", "value"),
     Input("date-filter", "start_date"),
     Input("date-filter", "end_date")]
)
def update_dashboard(n, n_clicks, search_val, district_val, area_val, platform_val, status_val, gap_val, start_date, end_date):
    df, reg_df, pickup_df, trends_df, sub_df = fetch_data()
    if df.empty:
        # Assuming empty_fig is defined elsewhere or needs to be imported
        import plotly.graph_objects as go
        empty_fig = go.Figure().update_layout(template="plotly_dark")
        return html.Div("No data available"), "No Data", "No Data", "No Data", "No Data", "No Data", empty_fig, "No Data", empty_fig, empty_fig, empty_fig, empty_fig

    # Load District Mapping from config safely
    try:
        with open('configs/locations.yaml', 'r') as f:
            loc_cfg = yaml.safe_load(f)
        dist_map = {}
        for d in loc_cfg.get('districts', []):
            for a in d.get('areas', []):
                dist_map[a['name']] = d['name']
    except:
        dist_map = {}

    # Infer district if missing
    if 'district' not in df.columns or df['district'].isnull().any():
        df['district'] = df.get('district', pd.Series([None]*len(df)))
        df.loc[df['district'].isnull(), 'district'] = df['location'].map(dist_map).fillna('Other')

    # Apply Date Filters first to the raw snapshots
    if start_date:
        df = df[df['stay_date'] >= start_date]
    if end_date:
        df = df[df['stay_date'] <= end_date]
    
    # Calculate days in period for capacity validation
    days_count = 7 # Default to 7 if no filter
    if start_date and end_date:
        try:
            d1 = datetime.strptime(start_date, '%Y-%m-%d')
            d2 = datetime.strptime(end_date, '%Y-%m-%d')
            days_count = (d2 - d1).days + 1
        except: pass

    # Data Processing: Merge everything into a master audit dataframe
    df['rooms_left_calc'] = df['rooms_left'].fillna(1)
    
    hotel_stats = df.groupby('hotel_name').agg({
        'location': 'last',
        'district': 'last',
        'platform': lambda x: ", ".join(sorted(x.unique())),
        'hotel_type': 'last',
        'rooms_left_calc': 'sum',
        'scraped_at': 'max'
    }).reset_index()
    hotel_stats['scan_date_disp'] = pd.to_datetime(hotel_stats['scraped_at']).dt.strftime('%Y-%m-%d')
    hotel_stats.rename(columns={'rooms_left_calc': 'total_nights'}, inplace=True)
    
    # Normalize names for merging
    hotel_stats['hotel_name_clean'] = hotel_stats['hotel_name'].str.strip().str.lower()
    
    # 1. Registration Mapping (Fuzzy)
    if not reg_df.empty:
        reg_df['Hotel Name Clean'] = reg_df['Hotel Name'].str.strip().str.lower()
        reg_names = reg_df.set_index('Hotel Name Clean')['Hotel Name'].to_dict()
        def find_reg_match(ota_name):
            for reg_clean, reg_orig in reg_names.items():
                if reg_clean in ota_name or ota_name in reg_clean: return reg_orig
            return None
        hotel_stats['Matched Reg Name'] = hotel_stats['hotel_name_clean'].apply(find_reg_match)
        master_df = pd.merge(hotel_stats, reg_df, left_on='Matched Reg Name', right_on='Hotel Name', how='left')
    else:
        master_df = hotel_stats.copy()
        master_df['Registration Status'] = 'Unregistered'

    # 2. Submitted Mapping
    if not sub_df.empty:
        sub_df['Hotel Name Clean'] = sub_df['Hotel Name'].str.strip().str.lower()
        sub_names = sub_df.set_index('Hotel Name Clean')['Hotel Name'].to_dict()
        def find_sub_match(ota_name):
            for sub_clean, sub_orig in sub_names.items():
                if sub_clean in ota_name or ota_name in sub_clean: return sub_orig
            return None
        master_df['Matched Sub Name'] = master_df['hotel_name_clean'].apply(find_sub_match)
        cols_to_drop = [c for c in ['Submitted Nights', 'Tax Submitted'] if c in master_df.columns]
        master_df = pd.merge(master_df.drop(columns=cols_to_drop), 
                             sub_df.drop(columns=['Hotel Name']), 
                             left_on='Matched Sub Name', right_on='Hotel Name Clean', how='left')
    
    master_df['Submitted Nights'] = master_df['Submitted Nights'].fillna(0)
    master_df['Tax Submitted'] = master_df['Tax Submitted'].fillna(0)
    master_df['total_nights'] = master_df['total_nights'].fillna(0)
    
    # Calculations
    master_df['Missing Nights'] = master_df['total_nights'] - master_df['Submitted Nights']
    master_df['Tax Expected (RM)'] = master_df['total_nights'] * 3.0
    master_df['Tax Loss (RM)'] = master_df['Tax Expected (RM)'] - master_df['Tax Submitted']
    
    # Status Logic
    def get_status(row):
        reg_status = str(row.get('Registration Status', 'UNREGISTERED')).upper()
        if reg_status in ['ACTIVE', 'REGISTERED', 'PENDING']:
            if row['Missing Nights'] > 100: return 'HIGH'
            if row['Missing Nights'] > 0: return 'WARN'
            return 'OK'
        else:
            return 'CRITICAL' if row['total_nights'] > 0 else 'UNREGISTERED'
    master_df['Status'] = master_df.apply(get_status, axis=1)

    # 3. Capacity Checks
    master_df['Rooms'] = pd.to_numeric(master_df['Rooms'], errors='coerce').fillna(1)
    master_df['Max Possible Nights'] = master_df['Rooms'] * days_count
    master_df['Possible?'] = master_df.apply(lambda row: 'Yes' if row['total_nights'] <= row['Max Possible Nights'] else 'Suspicious', axis=1)

    # Filtering
    filtered_df = master_df.copy()
    if search_val: filtered_df = filtered_df[filtered_df['hotel_name'].str.contains(search_val, case=False)]
    if district_val: filtered_df = filtered_df[filtered_df['district'].isin(district_val)]
    if area_val: filtered_df = filtered_df[filtered_df['location'].isin(area_val)]
    if platform_val: filtered_df = filtered_df[filtered_df['platform'].apply(lambda x: any(p in x for p in platform_val))]
    if status_val: filtered_df = filtered_df[filtered_df['Status'].isin(status_val)]
    if gap_val:
        if gap_val == 'missing': filtered_df = filtered_df[filtered_df['Missing Nights'] > 0]
        else: filtered_df = filtered_df[filtered_df['Missing Nights'] <= 0]

    # Metrics
    total_props = len(filtered_df)
    reg_props = len(filtered_df[filtered_df['Registration Status'].str.upper().isin(['ACTIVE', 'REGISTERED', 'PENDING'])])
    unreg_props = total_props - reg_props
    total_scraped = int(filtered_df['total_nights'].sum())
    total_submitted = int(filtered_df['Submitted Nights'].sum())
    missing_nights = total_scraped - total_submitted
    tax_actual = filtered_df['Tax Submitted'].sum()
    tax_expect = filtered_df['Tax Expected (RM)'].sum()
    tax_leakage = filtered_df['Tax Loss (RM)'].sum()
    comp_rate = (tax_actual / tax_expect * 100) if tax_expect > 0 else 100
    
    def make_metric_card(title, value, color, subtitle=None, delta=None, delta_higher_is_better=True):
        badge = None
        if delta is not None and delta != 0:
            is_good = (delta > 0) == delta_higher_is_better
            prefix = "+" if delta > 0 else ""
            icon = "bi-arrow-up-right" if delta > 0 else "bi-arrow-down-right"
            badge_color = "success" if is_good else "danger"
            # Format delta
            if isinstance(delta, float): d_str = f"{prefix}{delta:,.1f}%" if abs(delta) < 1000 else f"{prefix}{delta:,.0f}"
            else: d_str = f"{prefix}{delta:,}"
            badge = html.Span([html.I(className=f"bi {icon} me-1"), d_str], 
                             className=f"badge rounded-pill bg-{badge_color} ms-2 small")

        return dbc.Col(dbc.Card(dbc.CardBody([
            html.Div([
                html.H6(title, className="text-secondary mb-0 small fw-bold text-uppercase"),
                badge
            ], className="d-flex align-items-center justify-content-between mb-2"),
            html.H3(value, className=f"text-{color} mb-1 fw-bold"),
            html.Div(subtitle, className="text-muted x-small") if subtitle else None
        ], className="p-3"), className="h-100 border-0 shadow-sm bg-dark"), width=None, className="flex-grow-1")

    # --- Benchmarking Logic (Today vs Yesterday) ---
    df['scan_date'] = pd.to_datetime(df['scraped_at']).dt.date
    available_dates = sorted(df['scan_date'].unique())
    
    latest_metrics = {}
    prev_metrics = {}

    def get_period_metrics(p_df):
        if p_df.empty: return None
        # Simplified metrics for comparison
        m_nights = p_df['rooms_left_calc'].sum()
        m_props = p_df['hotel_name'].nunique()
        # Mocking tax for speed in this closure
        m_tax = m_nights * 3.0
        return {'nights': m_nights, 'props': m_props, 'tax': m_tax}

    if len(available_dates) >= 2:
        latest_date = available_dates[-1]
        prev_date = available_dates[-2]
        latest_metrics = get_period_metrics(df[df['scan_date'] == latest_date])
        prev_metrics = get_period_metrics(df[df['scan_date'] == prev_date])

    def calc_delta(key, higher_is_better=True):
        if not latest_metrics or not prev_metrics: return None
        v1 = prev_metrics.get(key, 0)
        v2 = latest_metrics.get(key, 0)
        if v1 == 0: return None
        return ((v2 - v1) / v1) * 100

    summary_cards = [
        # Row 1: Property Basics
        dbc.Row([
            make_metric_card("Total Properties", f"{total_props}", "info", delta=calc_delta('props')),
            make_metric_card("Registered", f"{reg_props}", "success"),
            make_metric_card("Unregistered", f"{unreg_props}", "warning", delta_higher_is_better=False),
            make_metric_card("Compliance Rate", f"{comp_rate:.1f}%", "success" if comp_rate > 80 else "warning")
        ], className="g-3 mb-3 w-100"),
        
        # Row 2: Room-Nights Analysis
        dbc.Row([
            make_metric_card("Estimated Room-Nights (Scraped)", f"{total_scraped:,}", "primary", delta=calc_delta('nights')),
            make_metric_card("Confirmed Room-Nights (Submitted)", f"{total_submitted:,}", "info"),
            make_metric_card("Missing Room-Nights", f"{missing_nights:,}", "danger", delta_higher_is_better=False)
        ], className="g-3 mb-3 w-100"),

        # Row 3: Tax Intelligence
        dbc.Row([
            make_metric_card("Estimated Tax from Scraped", f"RM{tax_expect:,.0f}", "primary", delta=calc_delta('tax')),
            make_metric_card("Actual Tax Collected", f"RM{tax_actual:,.0f}", "success"),
            make_metric_card("Estimated Tax Leakage", f"RM{tax_leakage:,.0f}", "danger", delta_higher_is_better=False)
        ], className="g-3 w-100")
    ]

    # Tables
    audit_disp = filtered_df[['hotel_name', 'location', 'district', 'total_nights', 'Submitted Nights', 'Status', 'Tax Loss (RM)', 'scan_date_disp']].copy()
    audit_disp.insert(0, '#', range(1, len(audit_disp) + 1))
    audit_disp.columns = ['#', 'Property', 'Area', 'District', 'Scraped', 'Gov Confirmed', 'Status', 'Tax Loss (RM)', 'Scan Date 📅']
    audit_table = dash_table.DataTable(
        data=audit_disp.to_dict('records'), columns=[{"name": i, "id": i} for i in audit_disp.columns],
        style_header={'backgroundColor': '#1a1a1a', 'color': '#0dcaf0'},
        style_cell={'backgroundColor': '#212529', 'color': 'white', 'fontSize': '12px'},
        filter_action="native", sort_action="native", page_size=10
    )

    priority_df = filtered_df[filtered_df['Status'].isin(['CRITICAL', 'HIGH'])].sort_values(by='Tax Loss (RM)', ascending=False)
    priority_disp = priority_df[['hotel_name', 'Operator', 'location', 'district', 'platform', 'Registration Status', 'total_nights', 'Submitted Nights', 'scan_date_disp']].copy()
    priority_disp.insert(0, '#', range(1, len(priority_disp) + 1))
    priority_table = dash_table.DataTable(
        data=priority_disp.to_dict('records'),
        columns=[
            {"name": "#", "id": "#"},
            {"name": "Property", "id": "hotel_name"},
            {"name": "Operator", "id": "Operator"},
            {"name": "Area", "id": "location"},
            {"name": "District", "id": "district"},
            {"name": "Scan Date 📅", "id": "scan_date_disp"},
            {"name": "Platform", "id": "platform"},
            {"name": "Registration", "id": "Registration Status"},
            {"name": "Est Nights", "id": "total_nights"},
            {"name": "Confirmed Nights", "id": "Submitted Nights"}
        ],
        style_header={'backgroundColor': '#2c2c2c', 'color': '#ffc107'},
        style_cell={'backgroundColor': '#212529', 'color': 'white'},
        page_size=10
    )

    # Capacity Table
    cap_df = filtered_df.sort_values(by=['Possible?', 'total_nights'], ascending=[True, False])
    cap_disp = cap_df[['hotel_name', 'location', 'district', 'Rooms', 'Max Possible Nights', 'total_nights', 'Possible?', 'scan_date_disp']].copy()
    cap_disp.insert(0, '#', range(1, len(cap_disp) + 1))
    capacity_table = dash_table.DataTable(
        data=cap_disp.to_dict('records'),
        columns=[
            {"name": "#", "id": "#"},
            {"name": "Property", "id": "hotel_name"},
            {"name": "Area", "id": "location"},
            {"name": "District", "id": "district"},
            {"name": "Scan Date 📅", "id": "scan_date_disp"},
            {"name": "Rooms", "id": "Rooms"},
            {"name": "Max Supportable", "id": "Max Possible Nights"},
            {"name": "Est Nights", "id": "total_nights"},
            {"name": "Possible?", "id": "Possible?"}
        ],
        style_header={'backgroundColor': '#331111', 'color': '#ff4444'},
        style_cell={'backgroundColor': '#212529', 'color': 'white'},
        style_data_conditional=[{
            'if': {'filter_query': '{Possible?} eq "Suspicious"'},
            'backgroundColor': '#441111', 'color': 'white', 'fontWeight': 'bold'
        }],
        page_size=10
    )

    # Platform Table
    plat_stats = df.groupby('platform').agg({
        'hotel_name': 'nunique',
        'rooms_left_calc': 'sum'
    }).reset_index()
    plat_stats.columns = ['Platform', 'Properties', 'Estimated Room-Nights']
    platform_table = dash_table.DataTable(
        data=plat_stats.to_dict('records'), 
        columns=[{"name": i, "id": i} for i in plat_stats.columns], 
        style_cell={'backgroundColor': '#212529', 'color': 'white'}
    )

    # Area-Based Overview
    area_stats = filtered_df.groupby('location').agg({
        'hotel_name': 'count',
        'Registration Status': lambda x: (x.str.upper().isin(['ACTIVE', 'REGISTERED', 'PENDING'])).sum(),
        'Tax Loss (RM)': 'sum'
    }).reset_index()
    area_stats['Unregistered'] = area_stats['hotel_name'] - area_stats['Registration Status']
    area_stats.columns = ['Area', 'Properties', 'Registered', 'Tax Loss (RM)', 'Unregistered']
    area_overview = dash_table.DataTable(
        data=area_stats[['Area', 'Properties', 'Registered', 'Unregistered', 'Tax Loss (RM)']].to_dict('records'),
        columns=[{"name": i, "id": i} for i in ['Area', 'Properties', 'Registered', 'Unregistered', 'Tax Loss (RM)']],
        style_cell={'backgroundColor': '#212529', 'color': 'white'}
    )

    daerah_counts = filtered_df.groupby('district')['hotel_name'].count().reset_index().sort_values(by='hotel_name', ascending=True)
    fig_daerah = px.bar(daerah_counts, y='district', x='hotel_name', orientation='h', title="<b>Property Distribution by Daerah</b>", text='hotel_name')
    fig_daerah.update_traces(marker_color='#0dcaf0', texttemplate='%{text}', textposition='outside')
    fig_daerah.update_layout(xaxis=dict(showgrid=False, zeroline=False), yaxis=dict(categoryorder='total ascending'))

    bentong_df = filtered_df[filtered_df['district'] == 'Bentong']
    if not bentong_df.empty:
        bentong_counts = bentong_df.groupby('location')['hotel_name'].count().reset_index().sort_values(by='hotel_name', ascending=True)
        fig_bentong = px.bar(bentong_counts, y='location', x='hotel_name', orientation='h', title="<b>Property Distribution within Bentong</b>", text='hotel_name')
        fig_bentong.update_traces(marker_color='#0dcaf0', texttemplate='%{text}', textposition='outside')
        fig_bentong.update_layout(xaxis=dict(showgrid=False, zeroline=False), yaxis=dict(categoryorder='total ascending'))
    else: 
        fig_bentong = go.Figure().update_layout(title="Bentong Distribution (Searching...)")

    fig_comp = px.pie(filtered_df['Registration Status'].value_counts().reset_index(), values='count', names='Registration Status', title="Registration Summary", hole=0.5)

    type_counts = filtered_df['hotel_type'].value_counts().reset_index().sort_values(by='count', ascending=True)
    fig_type = px.bar(type_counts, y='hotel_type', x='count', orientation='h', title="<b>Property Distribution by Type</b>", text='count')
    fig_type.update_traces(marker_color='#0dcaf0', texttemplate='%{text}', textposition='outside')
    fig_type.update_layout(xaxis=dict(showgrid=False, zeroline=False), yaxis=dict(categoryorder='total ascending'))
    # Demand Behavior Visualization
    if not trends_df.empty:
        # 1. Pickup Trend over time
        # Ensure detected_at is datetime if it's there
        if 'detected_at' in trends_df.columns:
            trends_df['detected_at'] = pd.to_datetime(trends_df['detected_at'])
            pickup_over_time = trends_df.groupby(trends_df['detected_at'].dt.floor('h')).agg({'pickup_count': 'sum'}).reset_index()
            fig_pickup_trend = px.line(pickup_over_time, x='detected_at', y='pickup_count', 
                                       title="<b>Total Rooms Reserved (Hourly Velocity)</b>",
                                       labels={'detected_at': 'Time', 'pickup_count': 'Rooms Reserved'})
        else:
            # Fallback to calculation_date
            pickup_over_time = trends_df.groupby('calculation_date').agg({'pickup_count': 'sum'}).reset_index()
            fig_pickup_trend = px.bar(pickup_over_time, x='calculation_date', y='pickup_count', 
                                      title="<b>Daily Rooms Reserved</b>")

        # 2. Top Performing Properties Table
        # Merge with hotel_stats to get district/location for trends
        property_velocity = trends_df.groupby(['hotel_name', 'platform']).agg({
            'pickup_count': 'sum',
            'estimated_revenue': 'sum'
        }).reset_index().sort_values(by='pickup_count', ascending=False).head(15)
        
        property_velocity = pd.merge(property_velocity, hotel_stats[['hotel_name', 'location', 'district']], on='hotel_name', how='left')
        property_velocity.insert(0, '#', range(1, len(property_velocity) + 1))
        
        pickup_table = dash_table.DataTable(
            data=property_velocity.to_dict('records'),
            columns=[
                {"name": "#", "id": "#"},
                {"name": "Property", "id": "hotel_name"},
                {"name": "Area", "id": "location"},
                {"name": "District", "id": "district"},
                {"name": "Platform", "id": "platform"},
                {"name": "Rooms Reserved", "id": "pickup_count"},
                {"name": "Est. Revenue (RM)", "id": "estimated_revenue"}
            ],
            style_header={'backgroundColor': '#153315', 'color': '#00ff00'},
            style_cell={'backgroundColor': '#212529', 'color': 'white'},
            page_size=10
        )
    else:
        fig_pickup_trend = go.Figure().update_layout(title="No Reservation Data Yet", template="plotly_dark")
        pickup_table = html.Div("Waiting for second scan to detect changes...")

    for fig in [fig_daerah, fig_bentong, fig_type, fig_comp, fig_pickup_trend]:
        fig.update_layout(template="plotly_dark", plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', margin=dict(l=20, r=40, t=50, b=20))

    return summary_cards, audit_table, priority_table, capacity_table, platform_table, area_overview, fig_pickup_trend, pickup_table, fig_daerah, fig_bentong, fig_type, fig_comp

if __name__ == '__main__':
    from utils.database import init_db
    init_db()
    app.run(debug=False, port=8050, host='0.0.0.0')
