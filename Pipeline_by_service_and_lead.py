import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import dcc, html, Input, Output
from sqlalchemy import create_engine
import urllib

# Fetch data from SSMS
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

df["Closing Date"] = pd.to_datetime(df["Closing Date"], errors="coerce")
df["Closing Month"] = df["Closing Date"].dt.strftime("%Y-%m")

current_month = pd.Timestamp.today().strftime("%Y-%m")
next_month = (pd.Timestamp.today() + pd.DateOffset(months=1)).strftime("%Y-%m")

closing_month_options = {
    "This Month": current_month,
    "Next Month": next_month
}

service_lines = ["Digital Transformation", "Staff Augmentation", "Consulting Milestone", "Consulting"]
color_map = {
    "Consulting": "#1f77b4",
    "Consulting Milestone": "#aec7e8",
    "Digital Transformation": "#ff7f0e",
    "Staff Augmentation": "#2ca02c"
}

stage_order = ["Agreement Signed", "Issue Agreement", "1st Meeting Complete", "Contact Made", "Proposal Sent"]

# Layout
graphs_layout = html.Div(
    style={"backgroundColor": "#222222", "color": "white", "padding": "20px"},
    children=[
        html.Div(
            style={"display": "flex", "justifyContent": "center", "gap": "20px", "marginBottom": "20px"},
            children=[
                dcc.Dropdown(
                    id="deal-owner-dropdown",
                    options=[{"label": owner, "value": owner} for owner in df["Deal Owner Name"].dropna().unique()],
                    placeholder="Select Deal Owner",
                    style={"width": "300px", "color": "green", "fontSize": "14px","background": "white"},
                    multi=True
                ),
                dcc.Dropdown(
                    id="closing-month-dropdown",
                    options=[{"label": "This Month", "value": "This Month"},
                             {"label": "Next Month", "value": "Next Month"}],
                    placeholder="Select Closing Month",
                    style={"width": "300px", "color": "green", "fontSize": "14px","background": "white"},
                    multi=True
                ),
            ]
        ),

        html.Div(
            style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "20px"},
            children=[
                dcc.Graph(id="lead-source-graph", style={"height": "500px", "width": "100%"}),
                dcc.Graph(id="billing-company-graph", style={"height": "500px", "width": "100%"}),
                dcc.Graph(id="service-line-graph", style={"height": "400px", "width": "100%"}),
                dcc.Graph(id="stage-graph", style={"height": "400px", "width": "100%"}),
            ]
        ),
    ]
)

# Callback
def register_graphs_callbacks(app):
    @app.callback(
        [Output("lead-source-graph", "figure"),
         Output("billing-company-graph", "figure"),
         Output("service-line-graph", "figure"),
         Output("stage-graph", "figure")],
        [Input("deal-owner-dropdown", "value"),
         Input("closing-month-dropdown", "value")]
    )
    def update_graphs(selected_deal_owners, selected_closing_months):
        df_filtered = df.copy()

        # Handle multi-selection for Deal Owner
        if selected_deal_owners:
            df_filtered = df_filtered[df_filtered["Deal Owner Name"].isin(selected_deal_owners)]

        # Handle multi-selection for Closing Month
        if selected_closing_months:
            selected_month_values = [closing_month_options[month] for month in selected_closing_months if month in closing_month_options]
            df_filtered = df_filtered[df_filtered["Closing Month"].isin(selected_month_values)]

        # Lead Source
        lead_sources = [
            "Existing Client", "Personal Network", "Conference or Event", "Email Campaign",
            "Client Referral", "Conference", "LinkedIn", "Advertisement", "Chat", "Social Media"
        ]
        df_lead = df_filtered[df_filtered["Lead Source"].isin(lead_sources)]
        df_lead_summary = df_lead["Lead Source"].value_counts().reset_index()
        df_lead_summary.columns = ["Lead Source", "Deals_In_Pipeline1"]
        df_lead_summary = df_lead_summary.sort_values(by="Deals_In_Pipeline1", ascending=True)

        fig_lead = px.bar(
            df_lead_summary, x="Deals_In_Pipeline1", y="Lead Source", orientation="h",
            text="Deals_In_Pipeline1", title="Deals in Pipeline by Lead Source",
            color_discrete_sequence=["#4682B4"]
        )
        fig_lead.update_traces(
            textposition="outside",
            textfont=dict(size=13, color="white"),
            cliponaxis=False
        )
        fig_lead.update_layout(
            plot_bgcolor="#222222", paper_bgcolor="#222222", font=dict(color="white", size=14),
            xaxis=dict(title="Deals", showgrid=False),
            yaxis=dict(title="Lead Source", categoryorder="total ascending"),
            margin=dict(l=160, r=80, t=60, b=40),
            height=500,
            showlegend=False
        )

        # Billing Company
        billing_companies = [
            "Valenta AU", "Valenta UK", "Valenta NZ", "Valenta DE", "Valenta US",
            "Valenta EU", "Valenta India", "Valenta LATAM", "Valenta TT"
        ]
        df_bill = df_filtered[df_filtered["Billing Company"].isin(billing_companies)]
        df_bill_summary = df_bill["Billing Company"].value_counts().reset_index()
        df_bill_summary.columns = ["Billing Company", "Deals_In_Pipeline1"]
        df_bill_summary = df_bill_summary.sort_values(by="Deals_In_Pipeline1", ascending=False)

        fig_bill = px.bar(
            df_bill_summary, x="Billing Company", y="Deals_In_Pipeline1", text="Deals_In_Pipeline1",
            title="Deals in Pipeline by Billing Company", color_discrete_sequence=["#4682B4"]
        )
        fig_bill.update_traces(
            textposition="outside",
            textfont=dict(size=14, color="white"),
            cliponaxis=False
        )
        fig_bill.update_layout(
            plot_bgcolor="#222222", paper_bgcolor="#222222", font=dict(color="white", size=14),
            xaxis=dict(title="Billing Company", showgrid=False, tickangle=45),
            yaxis=dict(title="Deals", showgrid=False),
            margin=dict(l=40, r=20, t=60, b=100),
            height=500,
            showlegend=False
        )

        # Donut - Service Line
        df_service_filtered = df_filtered[df_filtered["Service Line"].isin(service_lines)]
        df_service_summary = df_service_filtered.groupby("Service Line").size().reset_index(name="Deals")

        fig_service = px.pie(
            df_service_summary, names="Service Line", values="Deals", hole=0.6,
            color="Service Line", color_discrete_map=color_map,
            title="Deals in Pipeline by Service Line"
        )
        fig_service.update_layout(template="plotly_dark", font=dict(size=12), showlegend=True)

        # Stacked Bar - Stage and Service Line
        df_stage_filtered = df_filtered[df_filtered["Stage"].isin(stage_order)]
        df_stage_grouped = df_stage_filtered.groupby(["Stage", "Service Line"]).size().reset_index(name="Deals")

        if not df_stage_grouped.empty:
            df_stage_grouped["Percentage"] = df_stage_grouped.groupby("Stage")["Deals"].transform(
                lambda x: x / x.sum()
            )

            fig_stage = px.bar(
                df_stage_grouped, x="Stage", y="Percentage", color="Service Line",
                color_discrete_map=color_map, category_orders={"Stage": stage_order},
                title="Deals in Pipeline by Stage and Service Line",
                hover_data={"Percentage": ':.0%'}
            )
            fig_stage.update_layout(
                template="plotly_dark",
                yaxis=dict(tickformat=".0%", tickvals=[i / 10 for i in range(0, 11)], title="Percentage"),
                showlegend=True
            )
        else:
            fig_stage = go.Figure()
            fig_stage.add_annotation(
                text="No Data Available for Selected Filters",
                x=0.5, y=0.5, showarrow=False, font=dict(size=20, color="white"),
                xref="paper", yref="paper"
            )
            fig_stage.update_layout(
                plot_bgcolor="#222222", paper_bgcolor="#222222",
                xaxis=dict(visible=False), yaxis=dict(visible=False),
                title="Deals in Pipeline by Stage and Service Line",
                font=dict(color="white")
            )

        return fig_lead, fig_bill, fig_service, fig_stage
