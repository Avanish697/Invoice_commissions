import pandas as pd
import plotly.express as px
from dash import dcc, html, dash_table, Input, Output
from sqlalchemy import create_engine
import urllib
import datetime

# ✅ Fetch data from SQL Server
server = 'valentasql.database.windows.net'
database = 'Xero_CRM'
username = 'valdb'
password = 'Valenta@1234'
table_name = 'dbo.DEALS'

params = urllib.parse.quote_plus(
    f"DRIVER={{ODBC Driver 17 for SQL Server}};"
    f"SERVER={server};DATABASE={database};UID={username};PWD={password};"
)

engine = create_engine(f"mssql+pyodbc:///?odbc_connect={params}")
df = pd.read_sql(f"SELECT * FROM {table_name}", engine)

# ✅ Clean and preprocess data
df["Amount"] = df["Amount"].replace({r'\$': '', ',': ''}, regex=True).astype(float)
df["Closing Date"] = pd.to_datetime(df["Closing Date"], errors='coerce')
df["Closing Month"] = df["Closing Date"].dt.strftime("%b-%Y")

# ✅ Time References
current_month = pd.Timestamp.now().strftime("%b-%Y")
next_month = (pd.Timestamp.now() + pd.DateOffset(months=1)).strftime("%b-%Y")

# ✅ Franchise Valid Stages
valid_stages = [
    "New Lead", "Introduction Meeting", "FDD Review",
    "Application Form & Background Verification"
]

# ✅ Layout
franchise_layout = html.Div(style={"backgroundColor": "black", "color": "white", "padding": "10px"}, children=[

    html.Div([
        dcc.Dropdown(id="franchise_deal_owner",
                     multi=True,  # ✅ Enable multiple selection
                     options=[{"label": i, "value": i} for i in sorted(df["Deal Owner Name"].dropna().unique())],
                     placeholder="Deal Owner Name",
                     style={"flex": 1, "backgroundColor": "white", "color": "green", "border": "2px solid white"}),

        dcc.Dropdown(id="franchise_closing_month",
                     multi=True,  # ✅ Enable multiple selection
                     options=[
                         {"label": "This Month", "value": "this_month"},
                         {"label": "Next Month", "value": "next_month"},
                         {"label": "Other", "value": "other"}
                     ],
                     placeholder="Closing Month",
                     style={"flex": 1, "backgroundColor": "white", "color": "green", "border": "2px solid white"}),

        dcc.Dropdown(id="franchise_region",
                     multi=True,  # ✅ Enable multiple selection
                     options=[{"label": "All", "value": "All"}] + (
                         [{"label": i, "value": i} for i in sorted(df["Region"].dropna().unique())]
                         if "Region" in df.columns else []
                     ),
                     placeholder="Region",
                     style={"flex": 1, "backgroundColor": "white", "color": "green", "border": "2px solid white"})
    ], style={"display": "flex", "gap": "10px", "padding": "10px"}),

    html.Div(id="franchise_kpi_cards", style={"display": "flex", "justifyContent": "space-around", "padding": "20px"}),

    html.Div([
        dash_table.DataTable(id="franchise_stage_table",
                             style_table={"width": "100%", "backgroundColor": "black"},
                             style_header={"backgroundColor": "black", "color": "white", "fontWeight": "bold"},
                             style_cell={"backgroundColor": "black", "color": "white", "textAlign": "center"})
    ], style={"padding": "10px"}),

    dcc.Graph(id="franchise_bar_chart")
])

# ✅ Callbacks
def register_franchise_callbacks(app):
    @app.callback(
        [Output("franchise_kpi_cards", "children"),
         Output("franchise_stage_table", "columns"),
         Output("franchise_stage_table", "data"),
         Output("franchise_bar_chart", "figure")],
        [Input("franchise_deal_owner", "value"),
         Input("franchise_closing_month", "value"),
         Input("franchise_region", "value")]
    )
    def update_franchise(deal_owner, closing_month, region):
        filtered_df = df[df["Stage"].isin(valid_stages)]

        if deal_owner:
            filtered_df = filtered_df[filtered_df["Deal Owner Name"].isin(deal_owner)]

        if closing_month:
            month_filters = []
            if "this_month" in closing_month:
                month_filters.append(filtered_df["Closing Month"] == current_month)
            if "next_month" in closing_month:
                month_filters.append(filtered_df["Closing Month"] == next_month)
            if "other" in closing_month:
                month_filters.append(~filtered_df["Closing Month"].isin([current_month, next_month]))
            if month_filters:
                filtered_df = filtered_df[pd.concat(month_filters, axis=1).any(axis=1)]

        if region:
            if "All" not in region and "Region" in df.columns:
                filtered_df = filtered_df[filtered_df["Region"].isin(region)]

        # ✅ KPI Cards
        ongoing_revenue = filtered_df["Amount"].sum() if not filtered_df.empty else 0
        deals_closing = filtered_df.shape[0]

        kpi_card_style = {
            "border": "1px solid #555",
            "padding": "10px",
            "borderRadius": "8px",
            "width": "260px",
            "textAlign": "center",
            "backgroundColor": "#FFD700",  
            "color": "black",
            "boxShadow": "2px 2px 6px rgba(0,0,0,0.4)",
            "display": "flex",
            "flexDirection": "column",
            "justifyContent": "center",
            "alignItems": "center",
            "gap": "5px"
        }

        kpi_cards = [
            html.Div([
                html.H4("Ongoing Revenue", style={"color": "black"}),
                html.H2(f"${ongoing_revenue:,.2f}", style={"color": "black"})
            ], style=kpi_card_style),

            html.Div([
                html.H4("Deals Closing", style={"color": "black"}),
                html.H2(f"{deals_closing}", style={"color": "black"})
            ], style=kpi_card_style)
        ]

        # ✅ Table
        if not filtered_df.empty:
            stage_summary = filtered_df.groupby("Stage").size().reset_index(name="Deals_In_Pipeline")
            stage_summary["%GT Deals_In_Pipeline"] = (
                (stage_summary["Deals_In_Pipeline"] / stage_summary["Deals_In_Pipeline"].sum()) * 100
            ).map("{:.2f}%".format)
            stage_summary.loc[len(stage_summary)] = [
                "Total", stage_summary["Deals_In_Pipeline"].sum(), "100.00%"
            ]
        else:
            stage_summary = pd.DataFrame(columns=["Stage", "Deals_In_Pipeline", "%GT Deals_In_Pipeline"])

        table_columns = [{"name": col, "id": col} for col in stage_summary.columns]
        table_data = stage_summary.to_dict("records")

        # ✅ Bar Chart
        if not filtered_df.empty:
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
                title="Deals in Franchise Pipeline by Deal Owner Name and Stage",
                xaxis_title="Deals in Pipeline",
                yaxis_title="Deal Owner Name",
                plot_bgcolor="black",
                paper_bgcolor="black",
                font=dict(color="white", size=14),
                barmode="stack",
                height=140 + len(sorted_owners) * 70,
                margin=dict(l=180, r=30, t=80, b=40)
            )
        else:
            bar_chart = px.bar(title="No data available for the selected filters")
            bar_chart.update_layout(
                plot_bgcolor="black",
                paper_bgcolor="black",
                font=dict(color="white", size=14)
            )

        return kpi_cards, table_columns, table_data, bar_chart
