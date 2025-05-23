import pandas as pd
from dash import html, dcc, dash_table, Input, Output, callback, ctx
from datetime import datetime
import sqlalchemy
import urllib
from dash.dcc import send_data_frame, Download
import dash

# SQL Connection
server = 'valentasql.database.windows.net'
database = 'Xero_CRM'
username = 'valdb'
password = 'Valenta@1234'
table_name = 'dbo.INVOICES'

params = urllib.parse.quote_plus(
    f"DRIVER={{ODBC Driver 17 for SQL Server}};"
    f"SERVER={server};DATABASE={database};UID={username};PWD={password};"
)

engine = sqlalchemy.create_engine(f"mssql+pyodbc:///?odbc_connect={params}")
df = pd.read_sql(f"SELECT * FROM {table_name}", engine)

# Prepare data
df['Name'] = df['Client_Name']
df['Due Date'] = pd.to_datetime(df['Invoice_DueDate']).dt.strftime('%Y-%m-%d')
df['Invoice_Date'] = pd.to_datetime(df['Invoice_Date'], errors='coerce')

df['Year'] = df['Invoice_Date'].dt.year
df['Year'] = df['Year'].fillna(0).astype(int).astype(str)
df = df[df['Year'] != '0']

df['Month'] = df['Invoice_Date'].dt.strftime('%B')
today = pd.to_datetime(datetime.now().date())
df['Days Overdue'] = (today - pd.to_datetime(df['Due Date'])).dt.days.clip(lower=0)

df['Receivables'] = df.apply(
    lambda row: float(row['Invoice_Amount_USD']) if row['Status'] == 'AUTHORISED' and pd.isna(row['FullyPaidOnDate']) else 0,
    axis=1
)

df_display = df[['Location', 'Name', 'Description', 'Due Date', 'Days Overdue', 'Receivables', 'Year', 'Month', 'Invoice_Entity']].copy()
df_display['MP'] = df_display['Location']
df_display = df_display[['MP', 'Name', 'Description', 'Due Date', 'Days Overdue', 'Receivables', 'Year', 'Month', 'Invoice_Entity']]

layout = html.Div(style={"backgroundColor": "black", "color": "white"}, children=[
    html.H2("Receivables Dashboard", style={"textAlign": "center"}),

    html.Div(style={"display": "flex", "gap": "10px", "marginBottom": "20px", "flexWrap": "wrap"}, children=[
        dcc.Dropdown(
            id='year-filter',
            options=[{'label': y, 'value': y} for y in sorted(df_display['Year'].dropna().unique())],
            placeholder="Filter by Year",
            style={'width': '250px', 'color': 'green'},
            multi=True
        ),
        dcc.Dropdown(
            id='month-filter',
            options=[{'label': m, 'value': m} for m in sorted(df_display['Month'].dropna().unique())],
            placeholder="Filter by Month",
            style={'width': '250px', 'color': 'green'},
            multi=True
        ),
        dcc.Dropdown(
            id='entity-filter',
            options=[{'label': e, 'value': e} for e in sorted(df_display['Invoice_Entity'].dropna().unique())],
            placeholder="Filter by Entity",
            style={'width': '250px', 'color': 'green'},
            multi=True
        ),
        dcc.Dropdown(
            id='mp-filter',
            options=[],
            placeholder="Filter by MP",
            style={'width': '250px', 'color': 'green'},
            multi=True
        )
    ]),

    dash_table.DataTable(
        id='receivable-table',
        columns=[
            {"name": "MP", "id": "MP"},
            {"name": "Name", "id": "Name"},
            {"name": "Description", "id": "Description"},
            {"name": "Due Date", "id": "Due Date"},
            {"name": "Days Overdue", "id": "Days Overdue", "type": "numeric"},
            {"name": "Receivables", "id": "Receivables", "type": "numeric",
             "format": {"locale": {"symbol": ["$", ""]}, "specifier": "$,d"}}
        ],
        page_size=20,
        style_table={"overflowX": "auto"},
        style_header={
            "backgroundColor": "#222",
            "color": "white",
            "fontWeight": "bold"
        },
        style_cell={
            "backgroundColor": "#111",
            "color": "white",
            "padding": "10px",
            "textAlign": "left"
        },
        style_data_conditional=[
            {'if': {'row_index': 'odd'}, 'backgroundColor': '#1a1a1a'},
            {'if': {'column_id': 'Receivables'}, 'textAlign': 'center'},
            {'if': {'column_id': 'Days Overdue'}, 'textAlign': 'center'},
        ]
    ),

    html.Div(id="total_receivable_amount", style={
        "marginTop": "20px", "fontSize": "18px", "fontWeight": "bold", "textAlign": "right"
    }),

    html.Div(style={"display": "flex", "justifyContent": "flex-end", "marginTop": "20px"}, children=[
        html.Button("Export to CSV", id="export-button", n_clicks=0, style={
            "backgroundColor": "#28a745", "color": "white", "padding": "10px 20px",
            "border": "none", "borderRadius": "5px", "cursor": "pointer"
        })
    ]),

    Download(id="download-receivables")
])


@callback(
    Output('mp-filter', 'options'),
    Input('user-store', 'data')
)
def update_mp_filter(user_data):
    username = user_data.get("username")
    if username != 'admin':
        mp_options = [{'label': username, 'value': username}]
    else:
        mp_options = [{'label': mp, 'value': mp} for mp in sorted(df_display['MP'].dropna().unique())]
    return mp_options


@callback(
    Output('receivable-table', 'data'),
    Output('total_receivable_amount', 'children'),
    Input('year-filter', 'value'),
    Input('month-filter', 'value'),
    Input('entity-filter', 'value'),
    Input('mp-filter', 'value'),
    Input('user-store', 'data')
)
def update_receivables(year, month, entity, mp, user_data):
    username = user_data.get("username")
    dff = df_display.copy()

    if username != 'admin':
        dff = dff[dff["MP"] == username]

    if year:
        dff = dff[dff['Year'].isin(year)]
    if month:
        dff = dff[dff['Month'].isin(month)]
    if entity:
        dff = dff[dff['Invoice_Entity'].isin(entity)]
    if mp:
        dff = dff[dff['MP'].isin(mp)]

    display_data = dff[['MP', 'Name', 'Description', 'Due Date', 'Days Overdue', 'Receivables']]
    total_value = display_data['Receivables'].sum()
    return display_data.to_dict('records'), f"Total Receivables: ${total_value:,.0f}"


@callback(
    Output("download-receivables", "data"),
    Input("export-button", "n_clicks"),
    Input('year-filter', 'value'),
    Input('month-filter', 'value'),
    Input('entity-filter', 'value'),
    Input('mp-filter', 'value'),
    Input('user-store', 'data'),
    prevent_initial_call=True
)
def export_to_csv(n_clicks, year, month, entity, mp, user_data):
    if not ctx.triggered_id == "export-button":
        return dash.no_update

    username = user_data.get("username")
    dff = df_display.copy()

    if username != 'admin':
        dff = dff[dff["MP"] == username]

    if year:
        dff = dff[dff['Year'].isin(year)]
    if month:
        dff = dff[dff['Month'].isin(month)]
    if entity:
        dff = dff[dff['Invoice_Entity'].isin(entity)]
    if mp:
        dff = dff[dff['MP'].isin(mp)]

    return send_data_frame(dff.to_csv, "receivables_export.csv", index=False)
