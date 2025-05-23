import dash_bootstrap_components as dbc
from dash import dcc, html, Input, Output, State, Dash, dash_table
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import sqlalchemy
import urllib

# SQL setup
server = 'valentasql.database.windows.net'
database = 'Xero_CRM'
username = 'valdb'
password = 'Valenta@1234'
table_name = 'dbo.INVOICES'

params = urllib.parse.quote_plus(
    f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server};DATABASE={database};UID={username};PWD={password};"
)
engine = sqlalchemy.create_engine(f"mssql+pyodbc:///?odbc_connect={params}")
df = pd.read_sql(f"SELECT * FROM {table_name}", engine)

# Preprocessing
df['Invoice_Date'] = pd.to_datetime(df['Invoice_Date'], errors='coerce')
df['Year'] = df['Invoice_Date'].dt.year
df['Year'] = df['Year'].fillna(0).astype(int).astype(str)
df = df[df['Year'] != '0']
df['Month'] = df['Invoice_Date'].dt.month_name()
df['AccountCode'] = df['AccountCode'].fillna("Unknown")
df['Location'] = df['Location'].fillna("Unknown")


def kpi_card(title, value, color="green"):
    color_code = {
        "green": "#00FF00",
        "red": "#FF0000",
        "orange": "#FFA500"
    }
    return dbc.Card(
        dbc.CardBody([
            html.H4(value, className="mb-0", style={"color": color_code[color], "fontWeight": "bold"}),
            html.P(title, className="mb-0", style={"color": "white", "fontSize": "14px"})
        ]),
        className="text-left shadow-sm",
        style={
            "backgroundColor": "#2b2b2b", "borderRadius": "10px", "padding": "10px",
            "minWidth": "200px", "boxShadow": "2px 2px 8px #000"
        }
    )


layout = dbc.Container([
    dbc.Row([
        dbc.Col(html.H4("All Region Invoice and Commissions Report", className="text-white mt-3"), width=10)
    ], className="mb-4"),

    dbc.Row([
        dbc.Col(dcc.Dropdown(options=[{"label": y, "value": y} for y in sorted(df["Year"].dropna().unique())],
                             placeholder="Year", id="year-filter", className="text-dark", multi=True), width=3),
        dbc.Col(dcc.Dropdown(options=[{"label": m, "value": m} for m in sorted(df["Month"].dropna().unique())],
                             placeholder="Month", id="month-filter", className="text-dark", multi=True), width=3),
        dbc.Col(dcc.Dropdown(options=[{"label": e, "value": e} for e in sorted(df["Invoice_Entity"].dropna().unique())],
                             placeholder="Invoice Entity", id="entity-filter", className="text-dark", multi=True), width=3),
        dbc.Col(dcc.Dropdown(id="mpcode-filter", placeholder="MP Code", className="text-dark", multi=True), width=3),
    ], className="mb-3"),

    dbc.Row(id="kpis", className="mb-4 d-flex flex-row flex-wrap", style={"gap": "10px"}),

    dbc.Row([
        dbc.Col(html.Div(id="data-table", style={
            "backgroundColor": "#2d2d2d", "padding": "10px", "borderRadius": "10px", "color": "white",
            "overflowX": "auto", "maxHeight": "500px", "overflowY": "auto"
        }), width=8),

        dbc.Col([
            dcc.Graph(id="line-chart", style={"height": "350px"}),
            dcc.Graph(id="donut-chart", style={"height": "350px"})
        ], width=4)
    ]),

    dbc.Row([
        dbc.Col(html.Button("Export Table", id="export-button", n_clicks=0, className="btn btn-warning")),
        dcc.Download(id="download-table-csv")
    ], className="mt-3")
], fluid=True, style={"backgroundColor": "#121212", "padding": "20px"})


def update_dashboard(year, month, entity, mpcode, user_data):
    username = user_data.get("username") if user_data else "admin"
    dff = df.copy()

    if username != 'admin':
        dff = dff[dff["Location"] == username]

    if year:
        dff = dff[dff["Year"].isin(year)]
    if month:
        dff = dff[dff["Month"].isin(month)]
    if entity:
        dff = dff[dff["Invoice_Entity"].isin(entity)]
    if mpcode:
        dff = dff[dff["Location"].isin(mpcode)]

    summary = dff.copy()
    summary["Paid_Amount"] = summary["Invoice_Amount_USD"] - summary["Quantity"]
    summary["Receivables"] = summary["Invoice_Amount_USD"] - summary["Paid_Amount"]

    by_mp = summary.groupby("Location").agg({
        "Invoice_Amount_USD": "sum",
        "Paid_Amount": "sum",
        "Receivables": "sum"
    }).reset_index()
    by_mp["Paid %"] = round((by_mp["Paid_Amount"] / by_mp["Invoice_Amount_USD"]) * 100, 0)
    by_mp["Receivables %"] = (by_mp["Receivables"] / by_mp["Invoice_Amount_USD"]) * 100

    total_row = by_mp[["Invoice_Amount_USD", "Paid_Amount", "Receivables"]].sum()
    total_paid_pct = (total_row["Paid_Amount"] / total_row["Invoice_Amount_USD"]) * 100 if total_row["Invoice_Amount_USD"] else 0
    total_recv_pct = (total_row["Receivables"] / total_row["Invoice_Amount_USD"]) * 100 if total_row["Invoice_Amount_USD"] else 0

    kpi_cards = [
        kpi_card("Invoice Amount", f"${total_row['Invoice_Amount_USD']:,.0f}", "green"),
        kpi_card("Paid Amount", f"${total_row['Paid_Amount']:,.0f}", "green"),
        kpi_card("Paid %", f"{total_paid_pct:.0f}%", "green"),
        kpi_card("Receivables", f"${total_row['Receivables']:,.0f}", "red"),
        kpi_card("Receivables %", f"{total_recv_pct:.2f}%", "red")
    ]

    table_cell_style = {"border": "1px solid white", "padding": "6px", "textAlign": "center"}

    table_header = html.Thead(html.Tr([
        html.Th("MP Code", style=table_cell_style),
        html.Th("Invoice Amount", style=table_cell_style),
        html.Th("Paid Amount", style=table_cell_style),
        html.Th("Paid %", style=table_cell_style),
        html.Th("Receivables", style=table_cell_style),
        html.Th("Receivables %", style=table_cell_style)
    ]))

    table_rows = [html.Tr([
        html.Td(row["Location"], style=table_cell_style),
        html.Td(f"${row['Invoice_Amount_USD']:,.0f}", style=table_cell_style),
        html.Td(f"${row['Paid_Amount']:,.0f}", style=table_cell_style),
        html.Td(f"{row['Paid %']:.0f}%", style=table_cell_style),
        html.Td(f"${row['Receivables']:,.0f}", style=table_cell_style),
        html.Td(f"{row['Receivables %']:.2f}%", style=table_cell_style)
    ]) for _, row in by_mp.iterrows()]

    table_rows.append(html.Tr([
        html.Td(html.B("Total"), style=table_cell_style),
        html.Td(html.B(f"${total_row['Invoice_Amount_USD']:,.0f}"), style=table_cell_style),
        html.Td(html.B(f"${total_row['Paid_Amount']:,.0f}"), style=table_cell_style),
        html.Td(html.B(f"{total_paid_pct:.0f}%"), style=table_cell_style),
        html.Td(html.B(f"${total_row['Receivables']:,.0f}"), style=table_cell_style),
        html.Td(html.B(f"{total_recv_pct:.2f}%"), style=table_cell_style)
    ]))

    table = html.Table(
        children=[table_header, html.Tbody(table_rows)],
        style={
            "width": "100%", "borderCollapse": "collapse", "backgroundColor": "#2d2d2d",
            "color": "white", "fontSize": "14px", "border": "1px solid white"
        }
    )

    line_df = dff.groupby("Year")["Invoice_Amount_USD"].sum().reset_index()
    line_fig = px.line(line_df, x="Year", y="Invoice_Amount_USD", markers=True)
    line_fig.update_layout(
        paper_bgcolor="#1e1e1e", plot_bgcolor="#1e1e1e", font_color="white",
        title="Invoice Amount by Year", showlegend=False,
        xaxis=dict(showgrid=False), yaxis=dict(showgrid=False)
    )

    donut_fig = go.Figure(data=[go.Pie(
        labels=["Paid Amount", "Receivables"],
        values=[total_row["Paid_Amount"], total_row["Receivables"]],
        hole=0.5,
        marker=dict(colors=["#60a5fa", "#ff6b6b"])
    )])
    donut_fig.update_layout(paper_bgcolor="#1e1e1e", font_color="white", title="Invoice Breakdown", showlegend=True)

    mp_options = [{"label": mp, "value": mp} for mp in sorted(dff["Location"].dropna().unique())]
    if username != 'admin':
        mp_options = [{"label": username, "value": username}]

    return [dbc.Col(card, width="auto") for card in kpi_cards], table, line_fig, donut_fig, mp_options


def register_callbacks(app):
    app.callback(
        [Output("kpis", "children"),
         Output("data-table", "children"),
         Output("line-chart", "figure"),
         Output("donut-chart", "figure"),
         Output("mpcode-filter", "options")],
        [Input("year-filter", "value"),
         Input("month-filter", "value"),
         Input("entity-filter", "value"),
         Input("mpcode-filter", "value"),
         Input("user-store", "data")]
    )(update_dashboard)

    @app.callback(
        Output("download-table-csv", "data"),
        Input("export-button", "n_clicks"),
        State("year-filter", "value"),
        State("month-filter", "value"),
        State("entity-filter", "value"),
        State("mpcode-filter", "value"),
        State("user-store", "data"),
        prevent_initial_call=True
    )
    def export_table(n_clicks, year, month, entity, mpcode, user_data):
        dff = df.copy()
        username = user_data.get("username") if user_data else "admin"

        if username != "admin":
            dff = dff[dff["Location"] == username]
        if year:
            dff = dff[dff["Year"].isin(year)]
        if month:
            dff = dff[dff["Month"].isin(month)]
        if entity:
            dff = dff[dff["Invoice_Entity"].isin(entity)]
        if mpcode:
            dff = dff[dff["Location"].isin(mpcode)]

        summary = dff.copy()
        summary["Paid_Amount"] = summary["Invoice_Amount_USD"] - summary["Quantity"]
        summary["Receivables"] = summary["Invoice_Amount_USD"] - summary["Paid_Amount"]

        by_mp = summary.groupby("Location").agg({
            "Invoice_Amount_USD": "sum",
            "Paid_Amount": "sum",
            "Receivables": "sum"
        }).reset_index()
        by_mp["Paid %"] = round((by_mp["Paid_Amount"] / by_mp["Invoice_Amount_USD"]) * 100, 0)
        by_mp["Receivables %"] = (by_mp["Receivables"] / by_mp["Invoice_Amount_USD"]) * 100

        return dcc.send_data_frame(by_mp.to_csv, filename="overview_report.csv")
