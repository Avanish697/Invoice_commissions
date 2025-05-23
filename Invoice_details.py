import pandas as pd
import calendar
from dash import html, dcc, dash_table, Input, Output, callback, State
import sqlalchemy
import urllib
import dash
import io

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

# Clean & transform data
df["Invoice Date"] = pd.to_datetime(df["Invoice_Date"], errors="coerce")
df = df[df["Invoice Date"].notna()]
df["Year"] = df["Invoice Date"].dt.year
df["Month"] = df["Invoice Date"].dt.strftime("%B")
df["MP"] = df["Location"]
df["Name"] = df["Client_Name"].fillna("")
df["Description"] = df["Description"]
df["Invoice_Amount_USD"] = pd.to_numeric(df["Invoice_Amount_USD"], errors="coerce").abs().fillna(0)

month_order = list(calendar.month_name)[1:]

layout = html.Div(style={"backgroundColor": "black", "color": "white"}, children=[
    html.H2("Invoice Details", style={"textAlign": "center"}),

    html.Div(style={"display": "flex", "gap": "10px", "marginBottom": "20px"}, children=[
        dcc.Dropdown(
            id="year_filter",
            options=[{"label": str(y), "value": y} for y in sorted(df["Year"].dropna().unique())],
            placeholder="Select Year",
            style={"width": "250px", "backgroundColor": "white", 'color': 'green'},
            className="dropdown-custom",
            multi=True
        ),
        dcc.Dropdown(
            id="month_filter",
            options=[{"label": m, "value": m} for m in month_order if m in df["Month"].unique()],
            placeholder="Select Month",
            style={"width": "250px", "backgroundColor": "white", 'color': 'green'},
            className="dropdown-custom",
            multi=True
        ),
        dcc.Dropdown(
            id="entity_filter",
            options=[{"label": e, "value": e} for e in sorted(df["Invoice_Entity"].dropna().unique())],
            placeholder="Select Entity",
            style={"width": "250px", "backgroundColor": "white", 'color': 'green'},
            className="dropdown-custom",
            multi=True
        ),
        dcc.Dropdown(
            id="mp_filter",
            options=[],  # Will be updated dynamically
            placeholder="Select MP Code",
            style={"width": "250px", "backgroundColor": "white", 'color': 'green'},
            className="dropdown-custom",
            multi=True
        )
    ]),

    dash_table.DataTable(
        id='invoice_table',
        columns=[
            {"name": "MP", "id": "MP"},
            {"name": "Name", "id": "Name"},
            {"name": "Description", "id": "Description"},
            {"name": "Invoice Date", "id": "Invoice Date"},
            {"name": "Invoice Amount", "id": "Invoice_Amount_USD", "type": "numeric",
             "format": {"locale": {"symbol": ["$", ""]}, "specifier": "$,.0f"}}
        ],
        page_size=20,
        style_table={"overflowX": "auto"},
        style_header={"backgroundColor": "#222", "color": "white", "fontWeight": "bold"},
        style_cell={
            "backgroundColor": "#111",
            "color": "white",
            "padding": "10px",
            "textAlign": "left"
        },
        style_data_conditional=[
            {'if': {'row_index': 'odd'}, 'backgroundColor': '#1a1a1a'},
            {'if': {'column_id': 'Invoice_Amount_USD'}, 'textAlign': 'center'}
        ]
    ),

    html.Div(
        style={"display": "flex", "justifyContent": "flex-end", "marginTop": "20px"},
        children=[
            html.Button("Export to CSV", id="export_button", style={
                "color": "white",
                "backgroundColor": "green",
                "padding": "10px 20px",
                "borderRadius": "5px"
            })
        ]
    ),

    dcc.Download(id="download-dataframe-csv"),

    html.Div(id="total_invoice_amount", style={
        "marginTop": "20px", "fontSize": "18px", "fontWeight": "bold", "textAlign": "right"
    })
])


@dash.callback(
    Output("mp_filter", "options"),
    Input("user-store", "data")
)
def update_mp_filter(user_data):
    username = user_data.get("username")

    if username == "admin":
        mp_options = [{"label": mp, "value": mp} for mp in sorted(df["MP"].dropna().unique())]
    else:
        mp_options = [{"label": username, "value": username}]
    
    return mp_options


@dash.callback(
    Output("invoice_table", "data"),
    Output("total_invoice_amount", "children"),
    Input("year_filter", "value"),
    Input("month_filter", "value"),
    Input("entity_filter", "value"),
    Input("mp_filter", "value"),
    Input("user-store", "data")
)
def update_table(year, month, entity, mp_code, user_data):
    username = user_data.get("username")
    dff = df.copy()

    if username != "admin":
        dff = dff[dff["MP"] == username]

    if year:
        dff = dff[dff["Year"].isin(year)]
    if month:
        dff = dff[dff["Month"].isin(month)]
    if entity:
        dff = dff[dff["Invoice_Entity"].isin(entity)]
    if mp_code:
        dff = dff[dff["MP"].isin(mp_code)]

    dff = dff[["MP", "Name", "Description", "Invoice Date", "Invoice_Amount_USD"]].copy()
    dff["Invoice Date"] = dff["Invoice Date"].dt.strftime("%Y-%m-%d")

    total_amount = dff["Invoice_Amount_USD"].sum()
    return dff.to_dict("records"), f"Total Invoice Amount: ${total_amount:,.0f}"


@dash.callback(
    Output("download-dataframe-csv", "data"),
    Input("export_button", "n_clicks"),
    State("invoice_table", "data"),
    prevent_initial_call=True
)
def export_table(n_clicks, table_data):
    if n_clicks is None or not table_data:
        return dash.no_update
    
    df_export = pd.DataFrame(table_data)
    return dcc.send_data_frame(df_export.to_csv, "invoice_data.csv", index=False)
