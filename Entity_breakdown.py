import pandas as pd
import urllib
import sqlalchemy
from dash import html, dcc, Input, Output
import dash_bootstrap_components as dbc
import plotly.graph_objs as go

# Database config
server = 'valentasql.database.windows.net'
database = 'Xero_CRM'
username = 'valdb'
password = 'Valenta@1234'
table_name = 'dbo.INVOICES'

# SQLAlchemy connection
params = urllib.parse.quote_plus(
    f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server};DATABASE={database};UID={username};PWD={password};"
)
engine = sqlalchemy.create_engine(f"mssql+pyodbc:///?odbc_connect={params}")
df = pd.read_sql(f"SELECT * FROM {table_name}", engine)

# Preprocess
df['Invoice_Date'] = pd.to_datetime(df['Invoice_Date'])
df['Year'] = df['Invoice_Date'].dt.year
df['Quarter'] = df['Invoice_Date'].dt.to_period("Q").astype(str)
df['Month'] = df['Invoice_Date'].dt.month_name()

years = sorted(df['Year'].dropna().unique())
years = [str(int(year)) for year in years]

quarters = sorted(df['Quarter'].dropna().unique())
months = df['Month'].dropna().unique()

# Layout
layout = dbc.Container([
    html.Div([], className="mb-3 text-center"),

    dbc.Row([
        dbc.Col(dcc.Dropdown(
            options=[{"label": str(y), "value": str(y)} for y in years],
            value=None,
            id="year-dropdown",
            placeholder="Select Year",
            style={"backgroundColor": "white", "color": "green"},
            multi=True
        ), width=3),
        dbc.Col(dcc.Dropdown(
            options=[{"label": q, "value": q} for q in quarters],
            value=None,
            id="quarter-dropdown",
            placeholder="Select Quarter",
            style={"backgroundColor": "white", "color": "green"},
            multi=True
        ), width=3),
        dbc.Col(dcc.Dropdown(
            options=[{"label": m, "value": m} for m in months],
            value=None,
            id="month-dropdown",
            placeholder="Select Month",
            style={"backgroundColor": "white", "color": "green"},
            multi=True
        ), width=3),
    ], className="mb-4 justify-content-center"),

    html.Div(style={"marginTop": "80px"}),

    dbc.Row([
        dbc.Col(html.Div(id="invoice-amount-card"), width=2),
        dbc.Col(html.Div(id="paid-amount-card"), width=2),
        dbc.Col(html.Div(id="paid-percent-card"), width=2),
        dbc.Col(html.Div(id="receivables-card"), width=2),
        dbc.Col(html.Div(id="receivables-percent-card"), width=2),
    ], className="mb-4 gx-4 justify-content-center"),

    dbc.Row([
        dbc.Col(dcc.Graph(
            id="entity-table",
            style={"height": "600px", "marginTop": "60px"},
            config={"modeBarButtonsToRemove": ["toImage"]}
        ), width=6),
        dbc.Col(dcc.Graph(id="invoice-receivable-chart"), width=6)
    ])
], fluid=True, style={"backgroundColor": "#000000", "color": "white", "padding": "20px"})


# ✅ Updated dashboard logic with user filtering
def update_dashboard(year, quarter, month, user_data):
    username = user_data.get("username")
    dff = df.copy()

    if username != 'admin':
        dff = dff[dff["Location"] == username]

    if year:
        dff = dff[dff['Year'].isin([int(y) for y in year])]
    if quarter:
        dff = dff[dff['Quarter'].isin(quarter)]
    if month:
        dff = dff[dff['Month'].isin(month)]

    total_invoice = dff['Invoice_Amount'].sum()
    paid_amount = dff['Invoice_Amount'] - dff['Quantity']
    total_paid = paid_amount.sum()
    receivables = total_invoice - total_paid

    paid_pct = round((total_paid / total_invoice) * 100, 2) if total_invoice else 0
    recv_pct = round((receivables / total_invoice) * 100, 2) if total_invoice else 0

    def styled_card(value, label):
        return dbc.Card(
            dbc.CardBody([
                html.H4(value, className="card-title", style={"color": "black", "fontWeight": "bold", "fontSize": "24px"}),
                html.P(label, className="card-text", style={"color": "black", "fontSize": "14px"})
            ]),
            style={"backgroundColor": "#FFA500", "borderRadius": "16px", "boxShadow": "0px 4px 12px rgba(0,0,0,0.6)", "textAlign": "center"}
        )

    by_entity = dff.groupby('Entity').agg({
        'Invoice_Amount': 'sum',
        'Quantity': 'sum'
    }).reset_index()

    by_entity['Paid_Amount'] = by_entity['Invoice_Amount'] - by_entity['Quantity']
    by_entity['Paid %'] = (by_entity['Paid_Amount'] / by_entity['Invoice_Amount']) * 100
    by_entity['Receivables'] = by_entity['Quantity']
    by_entity['Receivables %'] = (by_entity['Receivables'] / by_entity['Invoice_Amount']) * 100
    by_entity = by_entity.drop(columns=['Quantity'])

    total_row = pd.DataFrame({
        'Entity': ['Total'],
        'Invoice_Amount': [round(by_entity['Invoice_Amount'].sum(), 2)],
        'Paid_Amount': [round(by_entity['Paid_Amount'].sum(), 2)],
        'Paid %': [round((by_entity['Paid_Amount'].sum() / by_entity['Invoice_Amount'].sum()) * 100, 2)],
        'Receivables': [round(by_entity['Receivables'].sum(), 2)],
        'Receivables %': [round((by_entity['Receivables'].sum() / by_entity['Invoice_Amount'].sum()) * 100, 2)]
    })
    by_entity = pd.concat([by_entity, total_row], ignore_index=True)

    by_entity_fig = go.Figure(data=[
        go.Table(
            header=dict(values=list(by_entity.columns),
                        fill_color="#2a2a2a",
                        font=dict(color="white", size=14),
                        align="left",
                        height=30),
            cells=dict(values=[by_entity[col].round(2) if by_entity[col].dtype != 'O' else by_entity[col] for col in by_entity.columns],
                       fill_color=[
                           ['#1f1f1f'] * (len(by_entity) - 1) + ['#333333']
                           for _ in range(len(by_entity.columns))
                       ],
                       font=dict(color="white", size=13),
                       align="left",
                       height=28)
        )
    ])
    by_entity_fig.update_layout(
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="#000000",
        plot_bgcolor="#000000",
    )

    by_year = dff.groupby('Year').agg({
        'Invoice_Amount': 'sum',
        'Quantity': 'sum'
    }).reset_index()
    by_year['Receivables'] = by_year['Quantity']

    chart = go.Figure()
    chart.add_trace(go.Bar(x=by_year['Year'], y=by_year['Invoice_Amount'],
                           name='Invoice Amount', marker_color='#00BFFF'))
    chart.add_trace(go.Scatter(x=by_year['Year'], y=by_year['Receivables'],
                               name='Receivables', yaxis='y2', line=dict(color='orange', width=3)))

    chart.update_layout(
        paper_bgcolor="#000000",
        plot_bgcolor="#000000",
        font_color="white",
        yaxis=dict(title='Invoice Amount', showgrid=False, zeroline=False),
        yaxis2=dict(title='Receivables', overlaying='y', side='right', showgrid=False, zeroline=False),
        legend=dict(x=0, y=1.2, orientation='h'),
        bargap=0.3,
        margin=dict(t=20, b=20, l=0, r=0),
        height=400
    )

    return (
        styled_card(f"${total_invoice:,.0f}", "Invoice Amount"),
        styled_card(f"${total_paid:,.0f}", "Paid Amount"),
        styled_card(f"{paid_pct}%", "Paid %"),
        styled_card(f"${receivables:,.0f}", "Receivables"),
        styled_card(f"{recv_pct}%", "Receivables %"),
        by_entity_fig,
        chart
    )


# ✅ Updated callback registration with user-store input
def register_callbacks(app):
    app.callback(
        [Output("invoice-amount-card", "children"),
         Output("paid-amount-card", "children"),
         Output("paid-percent-card", "children"),
         Output("receivables-card", "children"),
         Output("receivables-percent-card", "children"),
         Output("entity-table", "figure"),
         Output("invoice-receivable-chart", "figure")],
        [Input("year-dropdown", "value"),
         Input("quarter-dropdown", "value"),
         Input("month-dropdown", "value"),
         Input("user-store", "data")]  # 👈 New input added
    )(update_dashboard)
