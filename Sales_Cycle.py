import pandas as pd
from dash import html, dcc, dash_table, Input, Output
import dash_bootstrap_components as dbc
import urllib
from sqlalchemy import create_engine
from dash import ctx
from dash.dependencies import State
from dash import Dash
from dash.dcc import send_data_frame

# ✅ Fetch data from SSMS
server = 'valentasql.database.windows.net'   
database = 'Xero_CRM'                         
username = 'valdb'                            
password = 'Valenta@1234'                     
table_name = 'dbo.DEALS'                      

params = urllib.parse.quote_plus(
    f"DRIVER={{ODBC Driver 17 for SQL Server}};"
    f"SERVER={server};"
    f"DATABASE={database};"
    f"UID={username};"
    f"PWD={password};"
)

engine = create_engine(f"mssql+pyodbc:///?odbc_connect={params}")
df = pd.read_sql(f"SELECT * FROM {table_name}", engine)

# Clean and prepare the data
df = df[["Deal Owner Name", "Deal Name", "Stage", "Closing Date", "Sales Cycle Duration", "Billing Company"]].dropna()
df["Closing Date"] = pd.to_datetime(df["Closing Date"], errors='coerce')
sales_cycle = round(df["Sales Cycle Duration"].mean(), 2)

# Dropdown options
years = sorted(df["Closing Date"].dt.year.dropna().unique())
months = [ 
    {'label': 'January', 'value': 1}, 
    {'label': 'February', 'value': 2}, 
    {'label': 'March', 'value': 3}, 
    {'label': 'April', 'value': 4}, 
    {'label': 'May', 'value': 5}, 
    {'label': 'June', 'value': 6}, 
    {'label': 'July', 'value': 7}, 
    {'label': 'August', 'value': 8}, 
    {'label': 'September', 'value': 9}, 
    {'label': 'October', 'value': 10}, 
    {'label': 'November', 'value': 11}, 
    {'label': 'December', 'value': 12}
]
deal_owners = sorted(df["Deal Owner Name"].unique())
billing_companies = sorted(df["Billing Company"].dropna().unique())

# Layout
sales_cycle_layout = dbc.Container([
    dbc.Row([
        dbc.Col([
            dcc.Dropdown(
                id='year_filter_sales_cycle',
                options=[{'label': y, 'value': y} for y in years],
                placeholder='Year',
                clearable=True,
                multi=True,
                style={'color': 'green', 'backgroundColor': 'white'}
            ),
        ], width=2),

        dbc.Col([
            dcc.Dropdown(
                id='month_filter_sales_cycle',
                options=months,
                placeholder='Month',
                clearable=True,
                multi=True,
                style={'color': 'green', 'backgroundColor': 'white'}
            ),
        ], width=2),

        dbc.Col([
            dcc.Dropdown(
                id='deal_owner_filter_sales_cycle',
                options=[{'label': d, 'value': d} for d in deal_owners],
                placeholder='Deal Owner Name',
                clearable=True,
                multi=True,
                style={'color': 'green', 'backgroundColor': 'white'}
            ),
        ], width=3),

        dbc.Col([
            dcc.Dropdown(
                id='billing_company_filter_sales_cycle',
                options=[{'label': b, 'value': b} for b in billing_companies],
                placeholder='Billing Company',
                clearable=True,
                multi=True,
                style={'color': 'green', 'backgroundColor': 'white'}
            ),
        ], width=3),
    ], className="mb-4"),

    dbc.Row([
        dbc.Col(
            dbc.Card(
                dbc.CardBody([
                    html.H2(f"{sales_cycle}", className="text-center", style={'color': 'black'}),
                    html.H5("Sales Cycle", className="text-center", style={'color': 'black'})
                ]),
                style={
                    'backgroundColor': '#FFD700',
                    'borderRadius': '10px',
                    'padding': '10px',
                    'boxShadow': '0 4px 8px rgba(0, 0, 0, 0.3)'
                }
            ),
            width=2
        )
    ], className="mb-4"),

    dbc.Row([
        dbc.Col(
            dash_table.DataTable(
                id='deal_table_sales_cycle',
                columns=[
                    {'name': 'Deal Owner Name', 'id': 'Deal Owner Name'},
                    {'name': 'Deal Name', 'id': 'Deal Name'},
                    {'name': 'Sales Cycle Duration', 'id': 'Sales Cycle Duration'},
                    {'name': 'Stage', 'id': 'Stage'},
                    {'name': 'Billing Company', 'id': 'Billing Company'},
                ],
                data=df.to_dict("records"),
                page_size=15,  # Increased page size for bigger table
                style_table={'overflowX': 'auto', 'minHeight': '500px'},  # Bigger height
                style_cell={
                    'textAlign': 'left',
                    'padding': '10px',
                    'color': 'white',
                    'backgroundColor': 'black'
                },
                style_header={
                    'backgroundColor': 'darkgray',
                    'fontWeight': 'bold'
                }
            ),
            width=12
        )
    ]),

    dbc.Row([
        dbc.Col([], width=9),  # Empty column to push button to right
        dbc.Col([
            dbc.Button("Export CSV", id="export_sales_cycle_btn", color="success", className="mt-3"),
            dcc.Download(id="download_sales_cycle_csv")
        ], width=3, style={'textAlign': 'right'})
    ])
], fluid=True)


# Callback to filter data
def register_sales_cycle_callbacks(app):
    @app.callback(
        Output('deal_table_sales_cycle', 'data'),
        [
            Input('year_filter_sales_cycle', 'value'),
            Input('month_filter_sales_cycle', 'value'),
            Input('deal_owner_filter_sales_cycle', 'value'),
            Input('billing_company_filter_sales_cycle', 'value'),
        ]
    )
    def update_table(year, month, deal_owner, billing_company):
        filtered_df = df.copy()
        if year:
            filtered_df = filtered_df[filtered_df["Closing Date"].dt.year.isin(year)]
        if month:
            filtered_df = filtered_df[filtered_df["Closing Date"].dt.month.isin(month)]
        if deal_owner:
            filtered_df = filtered_df[filtered_df["Deal Owner Name"].isin(deal_owner)]
        if billing_company:
            filtered_df = filtered_df[filtered_df["Billing Company"].isin(billing_company)]
        return filtered_df.to_dict("records")

    # ✅ Export CSV Callback
    @app.callback(
        Output("download_sales_cycle_csv", "data"),
        Input("export_sales_cycle_btn", "n_clicks"),
        State('deal_table_sales_cycle', 'data'),
        prevent_initial_call=True,
    )
    def export_csv(n_clicks, table_data):
        export_df = pd.DataFrame(table_data)
        return send_data_frame(export_df.to_csv, filename="Sales_Cycle_Deals.csv", index=False)
