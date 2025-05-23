import dash
from dash import dcc, html, Input, Output, dash_table
import pandas as pd
import plotly.express as px
import urllib
import sqlalchemy
import warnings

warnings.simplefilter("ignore")

# SQL Server Connection
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

engine = sqlalchemy.create_engine(f"mssql+pyodbc:///?odbc_connect={params}")
df = pd.read_sql(f"SELECT * FROM {table_name}", engine)

# Clean numeric columns
for col in ["Amount", "Consulting Fee"]:
    if col in df.columns and not df[col].isnull().all():
        df[col] = df[col].astype(str).replace({r'[$,]': ''}, regex=True)
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

df["Closing Date"] = pd.to_datetime(df["Closing Date"], errors='coerce')
df["Closing Month"] = df["Closing Date"].dt.strftime("%b-%Y")

current_month = pd.Timestamp.now().strftime("%b-%Y")
next_month = (pd.Timestamp.now() + pd.DateOffset(months=1)).strftime("%b-%Y")

# Dropdown Style
dropdown_style = {
    "width": "220px",
    "backgroundColor": "white",
    "color": "green",
    "border": "1px",
    "borderRadius": "4px",
    "fontSize": "13px",
    "boxShadow": "none",
    "outline": "none",
    "height": "38px"
}

# KPI Card Style
kpi_card_style = {
    "border": "1px solid #555",
    "padding": "10px",
    "borderRadius": "8px",
    "width": "260px",
    "textAlign": "center",
    "backgroundColor": "#FFD700",
    "color": "black",
    "display": "flex",
    "flexDirection": "column",
    "justifyContent": "center",
    "alignItems": "center",
    "gap": "5px"
}

# Layout
client_layout = html.Div(style={"backgroundColor": "black", "color": "white", "padding": "20px"}, children=[
    html.Div([
        dcc.Dropdown(
            id="deal_owner",
            multi=True,
            placeholder="Select Deal Owner",
            style=dropdown_style
        ),
        dcc.Dropdown(
            id="closing_month",
            multi=True,
            options=[
                {"label": "This Month", "value": "this_month"},
                {"label": "Next Month", "value": "next_month"},
                {"label": "Other", "value": "other"}
            ],
            placeholder="Select Closing Month",
            style=dropdown_style
        )
    ], style={
        "display": "flex",
        "gap": "15px",
        "padding": "10px",
        "borderRadius": "8px",
        "justifyContent": "center",
        "marginBottom": "25px"
    }),

    html.Div(id="kpi_cards", style={"display": "flex", "justifyContent": "center", "gap": "20px", "marginBottom": "30px"}),

    html.Div([
        dash_table.DataTable(
            id="stage_table",
            style_table={"width": "100%", "overflowX": "auto"},
            style_header={
                "backgroundColor": "#222",
                "color": "white",
                "fontWeight": "bold",
                "border": "1px solid #444"
            },
            style_cell={
                "backgroundColor": "#111",
                "color": "white",
                "textAlign": "center",
                "padding": "10px",
                "border": "1px solid #333",
                "fontFamily": "Arial"
            },
            style_data_conditional=[
                {"if": {"row_index": "odd"}, "backgroundColor": "#1a1a1a"},
                {"if": {"filter_query": '{Stage} = "Total"'}, "fontWeight": "bold", "backgroundColor": "#333"}
            ]
        )
    ], style={"padding": "10px"}),

    dcc.Graph(id="bar_chart", config={"displayModeBar": False})
])


# Callback
def register_client_callbacks(app):
    @app.callback(
        [Output("deal_owner", "options"),
         Output("kpi_cards", "children"),
         Output("stage_table", "columns"),
         Output("stage_table", "data"),
         Output("bar_chart", "figure")],
        [Input("deal_owner", "value"),
         Input("closing_month", "value")]
    )
    def update_dashboard(deal_owner, closing_month):
        filtered_df = df[df["Stage"].isin([
            "Agreement Signed", "Awareness", "Closed (Future prospect)", "Closed (Lost)", "Did Not Proceed",
            "Discovery", "Engagement Completed", "Implementation", "Issue Agreement", "Needs Identified",
            "Ongoing Services", "Prospect"
        ])]

        if deal_owner:
            filtered_df = filtered_df[filtered_df["Deal Owner Name"].isin(deal_owner)]

        if closing_month:
            filters = []
            if "this_month" in closing_month:
                filters.append(df["Closing Month"] == current_month)
            if "next_month" in closing_month:
                filters.append(df["Closing Month"] == next_month)
            if "other" in closing_month:
                filters.append(~df["Closing Month"].isin([current_month, next_month]))
            if filters:
                filtered_df = filtered_df[pd.concat(filters, axis=1).any(axis=1)]

        deal_owner_options = [{"label": owner, "value": owner} for owner in sorted(df["Deal Owner Name"].dropna().unique())]

        ongoing_revenue = filtered_df["Amount"].sum()
        onetime_revenue = filtered_df["Consulting Fee"].sum()
        deals_closing = filtered_df.shape[0]

        kpi_cards = [
            html.Div([html.H2(f"${ongoing_revenue:,.2f}"), html.H4("Ongoing Revenue")], style=kpi_card_style),
            html.Div([html.H2(f"${onetime_revenue:,.2f}"), html.H4("One-Time Revenue")], style=kpi_card_style),
            html.Div([html.H2(f"{deals_closing}"), html.H4("Deals Closing")], style=kpi_card_style)
        ]

        stage_summary = filtered_df.groupby("Stage").size().reset_index(name="Deals_In_Pipeline")
        stage_summary["%GT Deals_In_Pipeline"] = (
            (stage_summary["Deals_In_Pipeline"] / stage_summary["Deals_In_Pipeline"].sum()) * 100
        ).round(2).astype(str) + "%"

        stage_summary.loc[len(stage_summary)] = [
            "Total",
            stage_summary["Deals_In_Pipeline"].sum(),
            "100.00%"
        ]

        table_columns = [{"name": col, "id": col} for col in stage_summary.columns]
        table_data = stage_summary.to_dict("records")

        df_grouped = filtered_df.groupby(["Deal Owner Name", "Stage"]).size().reset_index(name="Deals_In_Pipeline")
        df_grouped["Label"] = df_grouped["Deals_In_Pipeline"].astype(str)

        total_deals_per_owner = df_grouped.groupby("Deal Owner Name")["Deals_In_Pipeline"].sum().reset_index()
        sorted_owners = total_deals_per_owner.sort_values(by="Deals_In_Pipeline", ascending=False)["Deal Owner Name"]

        bar_chart = px.bar(
            df_grouped,
            x="Deals_In_Pipeline",
            y="Deal Owner Name",
            color="Stage",
            text="Label",
            category_orders={"Deal Owner Name": sorted_owners.tolist()},
            orientation="h"
        )

        bar_chart.update_layout(
            title="Deals in Pipeline by Deal Owner Name and Stage",
            xaxis_title="Deals in Pipeline",
            yaxis_title="",
            plot_bgcolor="black",
            paper_bgcolor="black",
            font=dict(color="white", size=14),
            barmode="stack",
            height=100 + len(sorted_owners) * 70,
            margin=dict(l=220, r=40, t=60, b=60),
            legend_title_text="Stage",
            bargap=0.1,
            bargroupgap=0.05
        )

        bar_chart.update_traces(
            textposition="inside",
            textfont=dict(size=12, color="white"),
            marker_line=dict(width=1, color="black")
        )

        return deal_owner_options, kpi_cards, table_columns, table_data, bar_chart
