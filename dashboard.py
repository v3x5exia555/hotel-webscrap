import dash
from dash import dcc, html, dash_table
from dash.dependencies import Input, Output, State
import dash_bootstrap_components as dbc
import pandas as pd
import sqlite3
import plotly.express as px
import plotly.graph_objects as go
from utils.database import get_supabase_client, get_supabase_table, fetch_data_from_db
from datetime import datetime
import os
import yaml
from flask_caching import Cache
import logging
import gc  # Garbage collection for memory optimization

# Optimize pandas
pd.options.mode.copy_on_write = True
pd.set_option('display.max_rows', 500)  # Limit display rows

# Configure logging to console as well
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Database Path
DB_PATH = "data/hotel_data.db"
REG_PATH = "data/property_registration.csv"

SUBMITTED_PATH = "data/submitted_records.csv"

# Configure Caching
cache = Cache()

# Get min/max dates from database (BOOKING/STAY DATES, not scrape dates)
def get_data_date_range():
    """Fetch the actual STAY DATE range (booking check-in dates) from the database"""
    # Try Supabase first
    table = get_supabase_table("snapshots")
    if table:
        try:
            res = table.select("stay_date").order("stay_date", desc=False).limit(1).execute()
            min_date_str = res.data[0]['stay_date'] if res.data else None
            
            res = table.select("stay_date").order("stay_date", desc=True).limit(1).execute()
            max_date_str = res.data[0]['stay_date'] if res.data else None
            
            if min_date_str and max_date_str:
                min_date = datetime.strptime(min_date_str, '%Y-%m-%d').date()
                max_date = datetime.strptime(max_date_str, '%Y-%m-%d').date()
                return min_date, max_date
        except Exception as e:
            logging.warning(f"Could not fetch date range from Supabase: {e}")

    # Fallback to SQLite
    if os.path.exists(DB_PATH):
        try:
            conn = sqlite3.connect(DB_PATH, timeout=10)
            cursor = conn.cursor()
            cursor.execute("SELECT MIN(stay_date) as min_date, MAX(stay_date) as max_date FROM snapshots;")
            result = cursor.fetchone()
            conn.close()
            
            if result[0] and result[1]:
                min_date = datetime.strptime(result[0], '%Y-%m-%d').date()
                max_date = datetime.strptime(result[1], '%Y-%m-%d').date()
                return min_date, max_date
        except Exception as e:
            logging.warning(f"Could not fetch booking date range from SQLite: {e}")
    
    return datetime(2025, 1, 1).date(), datetime.now().date()

# Cache the date range (updated once per app start)
MIN_DATE, MAX_DATE = get_data_date_range()
logging.info(f"Data date range: {MIN_DATE} to {MAX_DATE}")

def init_cache(flask_app):
    cache.init_app(flask_app, config={
        'CACHE_TYPE': 'filesystem',
        'CACHE_DIR': 'cache-directory',
        'CACHE_DEFAULT_TIMEOUT': 600
    })

@cache.memoize(timeout=600)
def fetch_pickup_trends():
    df = fetch_data_from_db("pickup_trends", days=7, limit=5000)
    if not df.empty:
        df['detected_at'] = pd.to_datetime(df['detected_at'])
    return df

@cache.memoize(timeout=300)
def fetch_data():
    logging.info("Dashboard: Fetching data using centralized utility...")
    
    # Fetch snapshots (remove days limit to support historical analysis)
    df = fetch_data_from_db("snapshots", limit=250000)
    
    # Fetch trends (allow full history for revenue tracking)
    trends_df = fetch_data_from_db("pickup_trends", limit=50000)
    
    if trends_df.empty:
        trends_df = pd.DataFrame(columns=['hotel_name', 'stay_date', 'nights', 'platform', 'pickup_count', 'estimated_revenue', 'calculation_date', 'detected_at'])
    
    # Calculate pickup_df
    pickup_df = pd.DataFrame(columns=['hotel_name', 'platform', 'total_pickup', 'total_nights'])
    if not trends_df.empty:
        pickup_df = trends_df.groupby(['hotel_name', 'platform']).agg(
            total_pickup=('pickup_count', 'sum'),
            total_nights=('pickup_count', 'sum')
        ).reset_index()
                
    return finalize_fetching(df, trends_df, pickup_df)

def finalize_fetching(df, trends_df, pickup_df):
    # OPTIMIZATION: Convert string columns to categorical (saves 80% memory)
    if not df.empty:
        for col in ['platform', 'location', 'district', 'hotel_type']:
            if col in df.columns:
                df[col] = df[col].astype('category')
    
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
        
    # Standardize names and locations
    for d in [df, trends_df, pickup_df, reg_df, sub_df]:
        if not d.empty:
            for col in ['hotel_name', 'location', 'district', 'Hotel Name']:
                if col in d.columns:
                    d[col] = d[col].astype(str).str.strip().str.title()

    return df, reg_df, pickup_df, trends_df, sub_df

# Initialize the Dash app
app = dash.Dash(__name__, 
                external_stylesheets=[dbc.themes.FLATLY, dbc.icons.BOOTSTRAP],
                suppress_callback_exceptions=True)
init_cache(app.server)
app.title = "Pahang Hotel Intelligence Dashboard"

# Layout
app.layout = dbc.Container([
    # Header
    dbc.Row([
        dbc.Col([
            html.Div([
                html.H1([html.I(className="bi bi-shield-check me-3"), "Pahang Revenue Intelligence & Compliance"], 
                        className="text-center mt-4 text-primary fw-bold"),
                html.P("Automated Revenue Audit & Tax Compliance System", className="text-center text-muted mb-4"),
                dbc.Row([
                    dbc.Col([
                        dbc.Button([html.I(className="bi bi-arrow-clockwise me-2"), "Full Refresh Dashboard"], 
                                   id="refresh-button", color="primary", className="shadow-sm fw-bold px-4")
                    ], width="auto")
                ], justify="center")
            ], className="py-3 shadow-sm rounded bg-white border mb-4")
        ], width=12)
    ]),

    # Filters Section
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    dbc.Row([
                        dbc.Col([
                            html.Label("Search Property", className="text-secondary small fw-bold"),
                            html.Div([
                                dcc.Input(id="search-filter", placeholder="Search name...", type="text", 
                                          className="form-control border-primary shadow-none",
                                          debounce=True,
                                          style={'fontWeight': '500', 'borderRadius': '4px 0 0 4px'}),
                                dbc.Button([html.I(className="bi bi-search")], id="search-btn", color="primary", 
                                            style={'borderRadius': '0 4px 4px 0'})
                            ], className="d-flex")
                        ], width=2),
                        dbc.Col([
                            html.Label("District", className="text-secondary small fw-bold"),
                            dcc.Dropdown(id="district-filter", multi=True, placeholder="All Districts")
                        ], width=2),
                        dbc.Col([
                            html.Label("Area", className="text-secondary small fw-bold"),
                            dcc.Dropdown(id="area-filter", multi=True, placeholder="All Areas")
                        ], width=2),
                        dbc.Col([
                            html.Label("Platform", className="text-muted small"),
                            dcc.Dropdown(id="platform-filter", multi=True, placeholder="All Platforms")
                        ], width=2),
                        dbc.Col([
                            html.Label("Status", className="text-muted small"),
                            dcc.Dropdown(id="status-filter", multi=True, placeholder="All Status", options=[
                                {'label': 'OK', 'value': 'OK'},
                                {'label': 'HIGH', 'value': 'HIGH'},
                                {'label': 'CRITICAL', 'value': 'CRITICAL'}
                            ])
                        ], width=2),
                        dbc.Col([
                            html.Label("Booking Date Range 📅", className="text-muted small fw-bold"),
                            dcc.DatePickerRange(
                                id="date-filter",
                                min_date_allowed=MIN_DATE,
                                max_date_allowed=MAX_DATE,
                                start_date=MIN_DATE,
                                end_date=MAX_DATE,
                                minimum_nights=0,
                                className="border-secondary",
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
                            ])
                        ], width=2),
                        dbc.Col([
                            html.Label("\u00a0", className="d-block small"),
                            dbc.Button([html.I(className="bi bi-x-circle me-2"), "Reset Filters"], 
                                       id="reset-button", color="secondary", outline=True, size="sm", className="w-100")
                        ], width=2, className="d-flex align-items-end"),
                    ], className="mt-2")
                ])
            ], className="mb-4 shadow-sm border-0 bg-white")
        ], width=12)
    ]),
    
    # Summary Metrics Row
    dbc.Row(id="summary-metrics-container", className="mb-4"),

    # Tabs
    dbc.Tabs(id='tabs', active_tab='audit', children=[
        dbc.Tab(label="Audit Analysis", children=[
            dbc.Row([
                dbc.Col([
                    html.H4("Revenue Audit Matrix", className="mt-4 mb-3 text-primary"),
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
        dbc.Tab(label="Property Explorer", children=[
            dbc.Row([
                dbc.Col([
                    html.H4("Individual Property Intelligence Deep-Dive", className="mt-4 mb-3 text-info"),
                    
                    # Control Bar for Filtering
                    dbc.Card([
                        dbc.CardBody([
                            dbc.Row([
                                dbc.Col([
                                    html.Label("Search Property Intelligence 🔍", className="small fw-bold mb-1"),
                                    dcc.Dropdown(id='explorer-hotel-search', placeholder="Search name...", search_value="")
                                ], width=3),
                                dbc.Col([
                                    html.Label("Filter by Targeted Stay Date 📅", className="small fw-bold mb-1"),
                                    dcc.Dropdown(id='explorer-date-filter', placeholder="Showing All Dates")
                                ], width=3),
                                dbc.Col([
                                    dbc.Button("📋 Back to Directory", id="clear-hotel-btn", color="secondary", size="sm", className="me-3")
                                ], width=2, className="d-flex align-items-center justify-content-end"),
                                dbc.Col([
                                    html.H5(id="explorer-hotel-name", className="text-info text-end fw-bold mb-0")
                                ], width=4, className="d-flex align-items-center justify-content-end")
                            ])
                        ])
                    ], className="mb-3 border-info shadow-sm"),

                    html.Div(id="explorer-main-content", className="mt-3")
                ], width=12)
            ])
        ], tab_id="explorer"),
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
                    html.H5("Platform Distribution Detail", className="text-primary mb-3 fw-bold"),
                    html.Div(id="platform-dist-container")
                ], width=6),
                dbc.Col([
                    html.H5("Area-Based Audit Overview", className="text-primary mb-3 fw-bold"),
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
    ], className="mt-2"),

    dcc.Store(id='selected-hotel-store'),
    dcc.Interval(id='interval-component', interval=300*1000, n_intervals=0)
], fluid=True, className="p-4 bg-light")

@app.callback(
    [Output("district-filter", "options"),
     Output("area-filter", "options"),
     Output("platform-filter", "options"),
     Output("explorer-hotel-search", "options")],
    [Input("interval-component", "n_intervals"),
     Input("district-filter", "value")]
)
def update_filter_options(n, district_val):
    df, _, _, _, _ = fetch_data()
    if df.empty:
        return [], [], []
    
    # Infer district mapping
    try:
        with open('configs/locations.yaml', 'r') as f:
            loc_cfg = yaml.safe_load(f)
        dist_map = {}
        for d in loc_cfg.get('districts', []):
            d_name = str(d.get('name', 'Unknown')).strip().title()
            for a in d.get('areas', []):
                a_name = str(a.get('name', 'Unknown')).strip().title()
                dist_map[a_name] = d_name
    except:
        dist_map = {}

    if 'district' not in df.columns or df['district'].isnull().any():
        df['district'] = df.get('district', pd.Series([None]*len(df)))
        df.loc[df['district'].isnull(), 'district'] = df['location'].map(dist_map).fillna('Other')

    districts = [{'label': i, 'value': i} for i in sorted(df['district'].unique())]
    
    # Dependent Area list based on selected District
    if district_val:
        areas_df = df[df['district'].isin(district_val)]
    else:
        areas_df = df
        
    areas = [{'label': i, 'value': i} for i in sorted(areas_df['location'].unique() if 'location' in areas_df.columns else [])]
    platforms = [{'label': i, 'value': i} for i in sorted(df['platform'].unique() if 'platform' in df.columns else [])]
    
    # All hotels for explorer search
    hotels = [{'label': i, 'value': i} for i in sorted(df['hotel_name'].unique() if 'hotel_name' in df.columns else [])]
    
    return districts, areas, platforms, hotels

@app.callback(
    [Output("search-filter", "value"),
     Output("district-filter", "value"),
     Output("area-filter", "value"),
     Output("platform-filter", "value"),
     Output("status-filter", "value"),
     Output("gap-filter", "value"),
     Output("date-filter", "start_date"),
     Output("date-filter", "end_date")],
    [Input("reset-button", "n_clicks")]
)
def reset_all_filters(n):
    if n is None: return dash.no_update
    return "", None, None, None, None, None, MIN_DATE, MAX_DATE

def get_status(row):
    reg_status = str(row.get('Registration Status', 'UNREGISTERED')).upper()
    total_nights = row.get('total_nights', 0)
    missing_nights = row.get('Missing Nights', 0)
    if reg_status in ['ACTIVE', 'REGISTERED', 'PENDING']:
        if missing_nights > 100: return 'HIGH'
        if missing_nights > 0: return 'WARN'
        return 'OK'
    else:
        return 'CRITICAL' if total_nights > 0 else 'UNREGISTERED'

@cache.memoize(timeout=600)
def get_master_df(start_date=None, end_date=None):
    df, reg_df, pickup_df, trends_df, sub_df = fetch_data()
    if df.empty:
        return pd.DataFrame(), pd.DataFrame(), 7

    # Ensure dates are in datetime format for robust filtering
    df['stay_date'] = pd.to_datetime(df['stay_date'])
    logging.info(f"get_master_df: Initial snapshots: {len(df)}")
    if not trends_df.empty:
        trends_df['stay_date'] = pd.to_datetime(trends_df['stay_date'])

    # Apply Date Filters
    if start_date:
        start_dt = pd.to_datetime(start_date)
        df = df[df['stay_date'] >= start_dt]
        if not trends_df.empty:
            trends_df = trends_df[trends_df['stay_date'] >= start_dt]
    if end_date:
        end_dt = pd.to_datetime(end_date)
        df = df[df['stay_date'] <= end_dt]
        if not trends_df.empty:
            trends_df = trends_df[trends_df['stay_date'] <= end_dt]
    
    logging.info(f"get_master_df: After date filtering: {len(df)}")
    
    # Deduplicate: For each hotel/platform/stay_date, keep only the latest scan
    # This ensures that if we scanned the same date multiple times, we only count it once for the audit
    df = df.sort_values('scraped_at').drop_duplicates(['hotel_name', 'platform', 'stay_date'], keep='last')
    
    logging.info(f"get_master_df: After deduplication: {len(df)}")
    
    days_count = 7 # Default
    try:
        d1_str = str(start_date)[:10] if start_date else None
        d2_str = str(end_date)[:10] if end_date else None
        if d1_str and d2_str:
            d1 = datetime.strptime(d1_str, '%Y-%m-%d')
            d2 = datetime.strptime(d2_str, '%Y-%m-%d')
            days_count = (d2 - d1).days + 1
    except: pass

    # Infer district if missing
    try:
        with open('configs/locations.yaml', 'r') as f:
            loc_cfg = yaml.safe_load(f)
        dist_map = {}
        for d in loc_cfg.get('districts', []):
            d_name = str(d.get('name', 'Unknown')).strip().title()
            for a in d.get('areas', []):
                a_name = str(a.get('name', 'Unknown')).strip().title()
                dist_map[a_name] = d_name
    except:
        dist_map = {}

    if 'district' not in df.columns or df['district'].isnull().any():
        df['district'] = df.get('district', pd.Series([None]*len(df)))
        df.loc[df['district'].isnull(), 'district'] = df['location'].map(dist_map).fillna('Other')

    # Aggregation
    hotel_stats = df.groupby(['hotel_name', 'location', 'district']).agg({
        'platform': lambda x: ", ".join(sorted(set(x.unique()))),
        'hotel_type': 'last',
        'rooms_left': 'mean', # Average occupancy found (for reference)
        'scraped_at': 'max'
    }).reset_index()
    
    # 0. Integrate Pickups (Sold Nights) as the new audit basis
    if not trends_df.empty:
        # Group trends by hotel to get total detected pickups, revenue, and separate out cancellations
        # Pickup count in trends_df can be negative for cancellations
        hotel_pickups = trends_df.groupby('hotel_name').agg(
            total_pickup_count=('pickup_count', lambda x: x[x > 0].sum()),
            total_estimated_revenue=('estimated_revenue', lambda x: x[x > 0].sum()),
            total_cancellation_count=('pickup_count', lambda x: abs(x[x < 0].sum()))
        ).reset_index()
        
        hotel_stats = pd.merge(hotel_stats, hotel_pickups, on='hotel_name', how='left')
        hotel_stats['total_nights'] = hotel_stats['total_pickup_count'].fillna(0)
        hotel_stats['total_rev'] = hotel_stats['total_estimated_revenue'].fillna(0)
        hotel_stats['total_cancels'] = hotel_stats['total_cancellation_count'].fillna(0)
    else:
        hotel_stats['total_nights'] = 0
        hotel_stats['total_rev'] = 0
        hotel_stats['total_cancels'] = 0
        
    hotel_stats['scan_date_disp'] = pd.to_datetime(hotel_stats['scraped_at']).dt.strftime('%Y-%m-%d')
    hotel_stats['hotel_name_clean'] = hotel_stats['hotel_name'].str.strip().str.lower()
    
    # 1. Registration Mapping (Improved fuzzy matching with cache)
    if not reg_df.empty:
        reg_df['Hotel Name Clean'] = reg_df['Hotel Name'].str.strip().str.lower()
        reg_map = reg_df.set_index('Hotel Name Clean')['Hotel Name'].to_dict()
        reg_clean_list = list(reg_map.keys())
        
        def find_reg_match(ota_name):
            if ota_name in reg_map: return reg_map[ota_name]
            for reg_clean in reg_clean_list:
                if reg_clean in ota_name or ota_name in reg_clean: return reg_map[reg_clean]
            return None
        
        hotel_stats['Matched Reg Name'] = hotel_stats['hotel_name_clean'].apply(find_reg_match)
        master_df = pd.merge(hotel_stats, reg_df, left_on='Matched Reg Name', right_on='Hotel Name', how='left')
    else:
        master_df = hotel_stats.copy()
        master_df['Registration Status'] = 'Unregistered'

    # 2. Submitted Mapping
    if not sub_df.empty:
        sub_df['Hotel Name Clean'] = sub_df['Hotel Name'].str.strip().str.lower()
        sub_map = sub_df.set_index('Hotel Name Clean')['Hotel Name'].to_dict()
        sub_clean_list = list(sub_map.keys())
        
        def find_sub_match(ota_name):
            if ota_name in sub_map: return sub_map[ota_name]
            for sub_clean in sub_clean_list:
                if sub_clean in ota_name or ota_name in sub_clean: return sub_map[sub_clean]
            return None
            
        master_df['Matched Sub Name'] = master_df['hotel_name_clean'].apply(find_sub_match)
        cols_to_drop = [c for c in ['Submitted Nights', 'Tax Submitted'] if c in master_df.columns]
        master_df = pd.merge(master_df.drop(columns=cols_to_drop or []), 
                             sub_df.drop(columns=['Hotel Name']), 
                             left_on='Matched Sub Name', right_on='Hotel Name Clean', how='left')
    
    # Pro-rate and calculations
    period_ratio = min(1.0, days_count / 30.0)
    master_df['Submitted_Nights_Adj'] = master_df['Submitted Nights'].fillna(0) * period_ratio
    master_df['Tax_Submitted_Adj'] = master_df['Tax Submitted'].fillna(0) * period_ratio
    master_df['Missing Nights'] = master_df['total_nights'] - master_df['Submitted_Nights_Adj']
    master_df['Tax Expected (RM)'] = master_df['total_nights'] * 3.0
    master_df['Tax Loss (RM)'] = master_df['Tax Expected (RM)'] - master_df['Tax_Submitted_Adj']
    
    master_df['Status'] = master_df.apply(get_status, axis=1)
    
    master_df['Rooms'] = pd.to_numeric(master_df['Rooms'], errors='coerce').fillna(1)
    master_df['Max Possible Nights'] = master_df['Rooms'] * days_count
    master_df['Possible?'] = master_df.apply(lambda row: 'Yes' if row['total_nights'] <= row['Max Possible Nights'] else 'Suspicious', axis=1)
    
    logging.info(f"get_master_df: Final master_df size: {len(master_df)}")
    
    # OPTIMIZATION: Clean up intermediate dataframes to free memory
    del df, reg_df, pickup_df, sub_df
    gc.collect()
    
    return master_df, trends_df, days_count

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
     Input("search-btn", "n_clicks"),
     Input("search-filter", "n_submit"),
     Input("district-filter", "value"),
     Input("area-filter", "value"),
     Input("platform-filter", "value"),
     Input("status-filter", "value"),
     Input("gap-filter", "value"),
     Input("date-filter", "start_date"),
     Input("date-filter", "end_date")],
    [State("search-filter", "value")]
)
def update_dashboard(n, n_clicks, s_clicks, s_submit, district_val, area_val, platform_val, status_val, gap_val, start_date, end_date, search_val):
    ctx = dash.callback_context
    if ctx.triggered and any('refresh-button' in t['prop_id'] for t in ctx.triggered):
        logging.info("Dashboard: Manual cache clear triggered by refresh button")
        cache.clear()
        
    master_df, trends_df, days_count = get_master_df(start_date, end_date)
    if master_df.empty:
        empty_fig = go.Figure().update_layout(template="plotly_white")
        return html.Div("No data available"), "No Data", "No Data", "No Data", "No Data", "No Data", empty_fig, "No Data", empty_fig, empty_fig, empty_fig, empty_fig

    # Filtering
    filtered_df = master_df.copy()
    if search_val and str(search_val).strip():
        s = str(search_val).strip().lower()
        # Broad search across name, location, district and operator
        name_mask = filtered_df['hotel_name'].str.lower().str.contains(s, na=False, regex=False)
        loc_mask = filtered_df['location'].str.lower().str.contains(s, na=False, regex=False)
        dist_mask = filtered_df['district'].str.lower().str.contains(s, na=False, regex=False)
        
        final_mask = name_mask | loc_mask | dist_mask
        if 'Operator' in filtered_df.columns:
            op_mask = filtered_df['Operator'].str.lower().str.contains(s, na=False, regex=False)
            final_mask = final_mask | op_mask
            
        filtered_df = filtered_df[final_mask]
        
        if not trends_df.empty:
            t_mask = trends_df['hotel_name'].str.lower().str.contains(s, na=False, regex=False)
            if 'location' in trends_df.columns:
                t_mask = t_mask | trends_df['location'].str.lower().str.contains(s, na=False, regex=False)
            trends_df = trends_df[t_mask]
            
    if district_val: 
        filtered_df = filtered_df[filtered_df['district'].isin(district_val)]
        if not trends_df.empty:
            trends_df = trends_df[trends_df['district'].isin(district_val)] if 'district' in trends_df.columns else trends_df
            
    if area_val: 
        filtered_df = filtered_df[filtered_df['location'].isin(area_val)]
        if not trends_df.empty:
            trends_df = trends_df[trends_df['location'].isin(area_val)] if 'location' in trends_df.columns else trends_df

    if platform_val and len(platform_val) > 0: 
        # 1. Filter filtered_df based on hotel presence on the selected platforms
        filtered_df = filtered_df[filtered_df['platform'].apply(lambda x: any(p in str(x) for p in platform_val))]
        
        # 2. Update displayed platform to only show the selected ones
        def filter_plat_str(s):
            parts = [p.strip() for p in str(s).split(',')]
            matched = [p for p in parts if p in platform_val]
            return ", ".join(matched)
        filtered_df['platform'] = filtered_df['platform'].apply(filter_plat_str)

        # 3. Recalculate metrics based on platform-specific performance
        # Filter trends_df to only the selected platforms
        if not trends_df.empty:
            trends_df = trends_df[trends_df['platform'].isin(platform_val)]
        
        # Group to get new totals (even if trends_df is now empty, this will result in 0s correctly)
        new_stats_df = pd.DataFrame(columns=['hotel_name', 'total_pickup_count', 'total_estimated_revenue', 'total_cancellation_count'])
        if not trends_df.empty:
            new_stats_df = trends_df.groupby('hotel_name').agg(
                total_pickup_count=('pickup_count', lambda x: x[x > 0].sum()),
                total_estimated_revenue=('estimated_revenue', lambda x: x[x > 0].sum()),
                total_cancellation_count=('pickup_count', lambda x: abs(x[x < 0].sum()))
            ).reset_index()
            
        totals_map = new_stats_df.set_index('hotel_name').to_dict('index')
        
        def update_metrics(row):
            stats = totals_map.get(row['hotel_name'], {'total_pickup_count': 0, 'total_estimated_revenue': 0, 'total_cancellation_count': 0})
            row['total_nights'] = stats['total_pickup_count']
            row['total_rev'] = stats['total_estimated_revenue']
            row['total_cancels'] = stats['total_cancellation_count']
                
            row['Tax Expected (RM)'] = row['total_nights'] * 3.0
            row['Tax Loss (RM)'] = row['Tax Expected (RM)'] - row['Tax_Submitted_Adj']
            row['Missing Nights'] = row['total_nights'] - row['Submitted_Nights_Adj']
            row['Status'] = get_status(row)
            return row
            
        # Only apply if we have rows to avoid errors
        if not filtered_df.empty:
            filtered_df = filtered_df.apply(update_metrics, axis=1)

    if status_val: filtered_df = filtered_df[filtered_df['Status'].isin(status_val)]
    if gap_val:
        if gap_val == 'missing': filtered_df = filtered_df[filtered_df['Missing Nights'] > 0]
        else: filtered_df = filtered_df[filtered_df['Missing Nights'] <= 0]

    # Metrics
    total_props = len(filtered_df)
    if total_props > 0:
        reg_status_clean = filtered_df['Registration Status'].fillna('UNREGISTERED').astype(str).str.upper()
        reg_props = len(filtered_df[reg_status_clean.isin(['ACTIVE', 'REGISTERED', 'PENDING'])])
    else:
        reg_props = 0
    unreg_props = total_props - reg_props
    total_scraped = int(filtered_df['total_nights'].sum())
    
    # Use Adjusted values for Summary Metrics
    total_submitted_adj = filtered_df['Submitted_Nights_Adj'].sum()
    missing_nights = total_scraped - total_submitted_adj
    tax_actual_adj = filtered_df['Tax_Submitted_Adj'].sum()
    tax_expect = filtered_df['Tax Expected (RM)'].sum()
    tax_leakage = filtered_df['Tax Loss (RM)'].sum()
    total_cancels = filtered_df['total_cancels'].sum()
    potential_leak_rm = total_cancels * 3.0
    
    comp_rate = (tax_actual_adj / tax_expect * 100) if tax_expect > 0 else 100
    
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
        ], className="p-3"), className="h-100 border-0 shadow-sm bg-white"), width=None, className="flex-grow-1")

    summary_cards = [
        # Row 1: Property Basics
        dbc.Row([
            make_metric_card("Total Properties", f"{total_props}", "primary"),
            make_metric_card("Registered", f"{reg_props}", "success"),
            make_metric_card("Unregistered", f"{unreg_props}", "warning"),
            make_metric_card("Compliance Rate", f"{comp_rate:.1f}%", "success" if comp_rate > 80 else "warning")
        ], className="g-3 mb-3 w-100"),
        
        # Row 2: Room-Nights Analysis
        dbc.Row([
            make_metric_card("Detected Sold Nights (OTAs)", f"{total_scraped:,}", "primary", subtitle="Actual Bookings Found"),
            make_metric_card("Confirmed Nights (Tax Office)", f"{total_submitted_adj:,.0f}", "info", subtitle="Official Portal Data"),
            make_metric_card("Unreported Activity", f"{missing_nights:,.0f}", "danger", subtitle="Potential Tax Leakage")
        ], className="g-3 mb-3 w-100"),
 
        # Row 3: Tax Intelligence
        dbc.Row([
            make_metric_card("Estimated Tax (From OTAs)", f"RM{tax_expect:,.0f}", "primary"),
            make_metric_card("Actual Tax Collected", f"RM{tax_actual_adj:,.0f}", "success"),
            make_metric_card("Estimated Tax Loss", f"RM{tax_leakage:,.0f}", "danger"),
            make_metric_card("Suspicious Cancellations", f"{total_cancels:,.0f}", "warning", subtitle=f"Potential Leak: RM{potential_leak_rm:,.0f}")
        ], className="g-3 w-100")
    ]

    # Tables
    audit_disp = filtered_df[['hotel_name', 'location', 'district', 'platform', 'total_nights', 'total_rev', 'Tax_Submitted_Adj', 'Tax Expected (RM)', 'Submitted Nights', 'Status', 'Tax Loss (RM)', 'scan_date_disp']].copy()
    audit_disp.insert(0, '#', range(1, len(audit_disp) + 1))
    audit_disp.columns = ['#', 'Property', 'Area', 'District', 'Platform', 'Sold (OTA)', 'Est. Revenue', 'Tax Collected', 'Est. Tax', 'Gov Declared', 'Status', 'Tax Loss (RM)', 'Scan Date 📅']
    audit_table = dash_table.DataTable(
        id='audit-table',
        data=audit_disp.to_dict('records'), columns=[{"name": i, "id": i} for i in audit_disp.columns],
        style_header={'backgroundColor': '#f8f9fa', 'color': '#007bff', 'fontWeight': 'bold'},
        style_cell={'backgroundColor': 'white', 'color': '#333', 'fontSize': '12px'},
        filter_action="native", sort_action="native", page_size=10,
        filter_options={'case': 'insensitive'},
        row_selectable='single',
        selected_rows=[],
        cell_selectable=True
    )
 
    priority_df = filtered_df[filtered_df['Status'].isin(['CRITICAL', 'HIGH'])].sort_values(by='Tax Loss (RM)', ascending=False)
    priority_disp = priority_df[['hotel_name', 'Operator', 'location', 'district', 'platform', 'Registration Status', 'total_nights', 'total_rev', 'Tax Expected (RM)', 'Tax_Submitted_Adj', 'Submitted Nights', 'scan_date_disp']].copy()
    priority_disp.insert(0, '#', range(1, len(priority_disp) + 1))
    priority_table = dash_table.DataTable(
        id='priority-table',
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
            {"name": "Detected Sold", "id": "total_nights"},
            {"name": "Est. Revenue (RM)", "id": "total_rev"},
            {"name": "Tax Collected (RM)", "id": "Tax_Submitted_Adj"},
            {"name": "Est. Tax (RM)", "id": "Tax Expected (RM)"},
            {"name": "Gov Declared (Nights)", "id": "Submitted Nights"}
        ],
        style_header={'backgroundColor': '#fff3cd', 'color': '#856404', 'fontWeight': 'bold'},
        style_cell={'backgroundColor': 'white', 'color': '#333'},
        filter_action="native", sort_action="native", page_size=10,
        filter_options={'case': 'insensitive'},
        row_selectable='single',
        selected_rows=[],
        cell_selectable=True
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
        style_header={'backgroundColor': '#f8d7da', 'color': '#721c24', 'fontWeight': 'bold'},
        style_cell={'backgroundColor': 'white', 'color': '#333'},
        style_data_conditional=[{
            'if': {'filter_query': '{Possible?} eq "Suspicious"'},
            'backgroundColor': '#fff1f1', 'color': '#721c24', 'fontWeight': 'bold'
        }],
        filter_action="native", sort_action="native", page_size=10,
        filter_options={'case': 'insensitive'}
    )

    # Platform Table
    plat_stats = filtered_df.copy()
    # Since filtered_df is aggregated by hotel, we need to handle the comma-separated platform list
    # Let's count occurrences of each platform in the strings
    all_plats = []
    for p_str in filtered_df['platform'].unique():
        all_plats.extend([p.strip() for p in p_str.split(',')])
    unique_plats = sorted(list(set(all_plats)))
    
    plat_rows = []
    for p in unique_plats:
        p_props = filtered_df[filtered_df['platform'].str.contains(p)].hotel_name.nunique()
        # For room-nights, we approximate if data is multi-platform
        # This is a bit complex since rooms are aggregated. 
        # For simplicity, we'll use the filtered_df stats
        plat_rows.append({'Platform': p, 'Properties': p_props})
    
    platform_table = dash_table.DataTable(
        data=plat_rows, 
        columns=[{"name": i, "id": i} for i in ['Platform', 'Properties']], 
        style_header={'backgroundColor': '#e9ecef', 'fontWeight': 'bold'},
        style_cell={'backgroundColor': 'white', 'color': '#333'}
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
        style_header={'backgroundColor': '#e9ecef', 'fontWeight': 'bold'},
        style_cell={'backgroundColor': 'white', 'color': '#333'}
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
        }).reset_index()
        property_velocity['tax_expected'] = property_velocity['pickup_count'] * 3.0
        property_velocity = property_velocity.sort_values(by='pickup_count', ascending=False).head(15)
        
        # Merge carefully to avoid Cartesian product if property name exists in multiple areas
        # We'll take the first mapping available in master_df for that name
        hotel_meta = master_df.drop_duplicates('hotel_name')[['hotel_name', 'location', 'district', 'Tax_Submitted_Adj']]
        property_velocity = pd.merge(property_velocity, hotel_meta, on='hotel_name', how='left')
        property_velocity.insert(0, '#', range(1, len(property_velocity) + 1))
        
        pickup_table = dash_table.DataTable(
            id='pickup-table',
            data=property_velocity.to_dict('records'),
            columns=[
                {"name": "#", "id": "#"},
                {"name": "Property", "id": "hotel_name"},
                {"name": "Area", "id": "location"},
                {"name": "District", "id": "district"},
                {"name": "Platform", "id": "platform"},
                {"name": "Rooms Reserved", "id": "pickup_count"},
                {"name": "Est. Revenue (RM)", "id": "estimated_revenue"},
                {"name": "Tax Collected (RM)", "id": "Tax_Submitted_Adj"},
                {"name": "Est. Tax (RM)", "id": "tax_expected"}
            ],
            style_header={'backgroundColor': '#d4edda', 'color': '#155724', 'fontWeight': 'bold'},
            style_cell={'backgroundColor': 'white', 'color': '#333'},
            filter_action="native", sort_action="native", page_size=10,
            filter_options={'case': 'insensitive'},
            row_selectable='single',
            selected_rows=[],
            cell_selectable=True
        )
    else:
        fig_pickup_trend = go.Figure().update_layout(title="No Reservation Data Yet", template="plotly_white")
        pickup_table = html.Div("Waiting for second scan to detect changes...")

    for fig in [fig_daerah, fig_bentong, fig_type, fig_comp, fig_pickup_trend]:
        fig.update_layout(template="plotly_white", plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', margin=dict(l=20, r=40, t=50, b=20))

    return summary_cards, audit_table, priority_table, capacity_table, platform_table, area_overview, fig_pickup_trend, pickup_table, fig_daerah, fig_bentong, fig_type, fig_comp

# Callback to handle property selection and tab switching
@app.callback(
    [Output('selected-hotel-store', 'data'),
     Output('tabs', 'active_tab'),
     Output('explorer-hotel-search', 'value')],
    [Input('audit-table', 'active_cell'),
     Input('priority-table', 'active_cell'),
     Input('pickup-table', 'active_cell'),
     Input('explorer-hotel-search', 'value'),
     Input('explorer-directory-table', 'active_cell'),
     Input('clear-hotel-btn', 'n_clicks')],
    [State('audit-table', 'derived_virtual_data'),
     State('priority-table', 'derived_virtual_data'),
     State('pickup-table', 'derived_virtual_data'),
     State('explorer-directory-table', 'derived_virtual_data')]
)
def update_selected_hotel(audit_cell, priority_cell, pickup_cell, search_val, directory_cell, clear_clicks, audit_data, priority_data, pickup_data, directory_data):
    ctx = dash.callback_context
    if not ctx.triggered:
        return dash.no_update, dash.no_update, dash.no_update
    
    triggered_id = ctx.triggered[0]['prop_id'].split('.')[0]
    logging.info(f"Dashboard: selection trigger from {triggered_id}")
    
    if triggered_id == 'clear-hotel-btn':
        return "", dash.no_update, ""

    selected_name = None
    try:
        if triggered_id == 'explorer-hotel-search':
            selected_name = search_val
        elif triggered_id == 'explorer-directory-table' and directory_cell and directory_data:
            selected_name = directory_data[directory_cell['row']]['Property']
        elif triggered_id == 'audit-table' and audit_cell and audit_data:
            selected_name = audit_data[audit_cell['row']]['Property']
        elif triggered_id == 'priority-table' and priority_cell and priority_data:
            selected_name = priority_data[priority_cell['row']]['hotel_name']
        elif triggered_id == 'pickup-table' and pickup_cell and pickup_data:
            selected_name = pickup_data[pickup_cell['row']]['hotel_name']
    except Exception as e:
        logging.error(f"Error selecting hotel: {e}")
        return dash.no_update, dash.no_update, dash.no_update
        
    if selected_name:
        logging.info(f"Dashboard: Selected hotel '{selected_name}'")
        # ALWAYS switch to 'explorer' tab for the "One Click" experience
        tab_output = 'explorer' 
        search_output = dash.no_update if triggered_id == 'explorer-hotel-search' else selected_name
        return selected_name, tab_output, search_output
    
    return dash.no_update, dash.no_update, dash.no_update

# Callback to populate the Explorer tab
@app.callback(
    [Output('explorer-hotel-name', 'children'),
     Output('explorer-main-content', 'children'),
     Output('explorer-date-filter', 'options')],
    [Input('selected-hotel-store', 'data'),
     Input('explorer-date-filter', 'value')]
)
def populate_explorer(hotel_name, stay_date_filter):
    # --- ALWAYS SHOW DIRECTORY ---
    master_df, _, _ = get_master_df()
    if master_df.empty:
        return "Master Directory", html.Div("No data available to list properties."), []
    
    dir_df = master_df[['hotel_name', 'location', 'district', 'platform']].copy()
    dir_df.insert(0, '#', range(1, len(dir_df) + 1))
    dir_df.columns = ['#', 'Property', 'Area', 'District', 'Platforms']
    
    directory_section = dbc.Card([
        dbc.CardHeader(html.H5("Master Property Directory (Click a Property to Deep-Dive)", className="mb-0 text-secondary")),
        dbc.CardBody([
            dash_table.DataTable(
                id='explorer-directory-table',
                data=dir_df.to_dict('records'),
                columns=[{"name": i, "id": i} for i in dir_df.columns],
                style_header={'backgroundColor': '#f8f9fa', 'color': '#6c757d', 'fontWeight': 'bold'},
                style_cell={'fontSize': '12px', 'textAlign': 'left'},
                sort_action="native",
                filter_action="native",
                page_size=10,
                row_selectable='single',
            )
        ])
    ], className="mb-4 shadow-sm border-0")

    # If no hotel selected yet, just return the directory
    if not hotel_name:
        return "Master Property Directory", directory_section, []

    # --- IF HOTEL SELECTED, SHOW ONLY INTELLIGENCE ---
    logging.info(f"Dashboard: Populating explorer for '{hotel_name}' (Filter: {stay_date_filter})")
    
    # Fetch raw snapshots
    conn = sqlite3.connect(DB_PATH)
    query = "SELECT * FROM snapshots WHERE TRIM(hotel_name) = ? COLLATE NOCASE"
    raw_df = pd.read_sql_query(query, conn, params=(hotel_name.strip(),))
    conn.close()

    if raw_df.empty:
        conn = sqlite3.connect(DB_PATH)
        query = "SELECT * FROM snapshots WHERE hotel_name LIKE ? LIMIT 500"
        raw_df = pd.read_sql_query(query, conn, params=(f"%{hotel_name.strip()}%",))
        conn.close()
        
    if raw_df.empty:
        return f"Property: {hotel_name}", html.Div([
            dbc.Alert(f"No specific records found for '{hotel_name}'. Please try another search.", color="warning"),
            directory_section
        ]), []

    raw_df = raw_df.sort_values('scraped_at', ascending=False)
    raw_df = raw_df.rename(columns={'price': 'price_value'})
    
    if 'availability' not in raw_df.columns:
        raw_df['availability'] = raw_df['rooms_left'].apply(
            lambda x: f"Only {int(x)} left" if pd.notnull(x) and x != "" else "Available"
        )

    raw_df['scraped_dt'] = pd.to_datetime(raw_df['scraped_at'])
    all_dates = sorted(raw_df['stay_date'].unique(), reverse=True)
    date_options = [{'label': d, 'value': d} for d in all_dates]
    date_options.insert(0, {'label': 'Show All Dates', 'value': None})

    display_df = raw_df.copy()
    if stay_date_filter:
        display_df = display_df[display_df['stay_date'] == stay_date_filter]

    # Meta
    latest = raw_df.iloc[0]
    meta = html.Div([
        html.H6("Property Context", className="text-secondary small fw-bold mb-3"),
        html.P([html.Strong("Area: "), latest.get('location', 'N/A')], className="mb-1"),
        html.P([html.Strong("Platforms: "), ", ".join(raw_df['platform'].unique())], className="mb-3"),
        html.Div([
            html.H6("Timeline Intelligence", className="text-secondary small fw-bold mb-1"),
            html.P([f"Scans: {len(raw_df):,}"], className="small mb-1"),
            html.P([f"Last: {latest['scraped_at']}"], className="small mb-0 text-primary"),
        ], className="p-2 bg-light rounded shadow-sm mb-3")
    ], className="p-3 bg-white rounded border h-100")

    # Transactions
    transactions = []
    for (sdate, plat), group in raw_df.sort_values('scraped_at').groupby(['stay_date', 'platform']):
        group = group.dropna(subset=['rooms_left'])
        if len(group) < 2: continue
        group['prev_rooms'] = group['rooms_left'].shift(1)
        group['pickup'] = group['prev_rooms'] - group['rooms_left']
        changes = group[group['pickup'] != 0].dropna(subset=['pickup'])
        for _, row in changes.iterrows():
            transactions.append({
                'Time': row['scraped_at'],
                'Stay Date': row['stay_date'],
                'Plat': row['platform'],
                'Type': 'Booking' if row['pickup'] > 0 else 'Release',
                'Change': f"{int(row['prev_rooms'])} → {int(row['rooms_left'])} (Net: {int(row['pickup'])})"
            })
    
    trans_df = pd.DataFrame(transactions)
    if not trans_df.empty:
        trans_table = dash_table.DataTable(
            data=trans_df.sort_values('Time', ascending=False).to_dict('records'),
            columns=[{"name": i, "id": i} for i in trans_df.columns],
            style_header={'backgroundColor': '#d4edda', 'fontWeight': 'bold'},
            style_cell={'fontSize': '10px'},
            page_size=5
        )
    else:
        trans_table = html.Div("No inventory changes detected.", className="text-muted small")

    # Facts
    col_map = {'scraped_at': 'Time', 'platform': 'Plat', 'stay_date': 'Date', 'price_value': 'Price', 'rooms_left': 'Inv'}
    table_cols = [c for c in col_map.keys() if c in display_df.columns]
    explorer_table = dash_table.DataTable(
        data=display_df[table_cols].to_dict('records'),
        columns=[{"name": col_map[i], "id": i} for i in table_cols],
        style_header={'backgroundColor': '#e3f2fd', 'fontWeight': 'bold'},
        style_cell={'fontSize': '10px'},
        page_size=10,
        sort_action="native"
    )

    # Graphs
    fig_price = px.line(display_df.sort_values('scraped_dt'), x='scraped_dt', y='price_value', color='platform', markers=True)
    fig_price.update_layout(height=300, margin=dict(l=20, r=20, t=30, b=20), template="plotly_white", title="Price Evolution")
    
    fig_inventory = px.line(display_df.dropna(subset=['rooms_left']).sort_values('scraped_dt'), 
                            x='scraped_dt', y='rooms_left', color='platform', markers=True)
    fig_inventory.update_layout(height=300, margin=dict(l=20, r=20, t=30, b=20), template="plotly_white", title="Inventory Levels")

    # Combined content for the main explorer view
    intelligence_view = html.Div([
        dbc.Row([
            dbc.Col(meta, width=3),
            dbc.Col([
                html.H5(f"Intelligence: {hotel_name}", className="text-info fw-bold mb-2"),
                dbc.Row([
                    dbc.Col([html.Strong("Transactional History (Pickup/Release)"), trans_table], width=6),
                    dbc.Col([html.Strong("Full Scrape Audit Trail"), explorer_table], width=6)
                ]),
                dbc.Row([
                    dbc.Col(dcc.Graph(figure=fig_price), width=6),
                    dbc.Col(dcc.Graph(figure=fig_inventory), width=6)
                ], className="mt-3")
            ], width=9)
        ])
    ])

    return f"Deep-Dive: {hotel_name}", intelligence_view, date_options

if __name__ == '__main__':
    from utils.database import init_db
    init_db()
    app.run(debug=False, port=8050, host='0.0.0.0')
