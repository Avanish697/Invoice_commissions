import pandas as pd
import dash
from dash import dcc, html, dash_table
from dash.dependencies import Input, Output, State
from sqlalchemy import create_engine
import urllib
import numpy as np
import io
import base64

# Layout for Account Score Page
accounts_layout = html.Div([
    # Filters
    html.Div([
        html.Div([
            html.Label("Account Owner Name", style={"color": "black"}),
            dcc.Dropdown(
                id='account-score-owner-filter',
                placeholder='Select Account Owner Name',
                multi=True,
                style={
                    "width": "220px",
                    "color": "green",
                    "backgroundColor": "white",
                    "borderRadius": "5px",
                    "padding": "4px",
                    "fontSize": "14px",
                }
            )
        ], style={'marginRight': '30px'}),

        html.Div([
            html.Label("Score Bucket", style={"color": "black"}),
            dcc.Dropdown(
                id='account-score-score-filter',
                placeholder='Select Score Bucket',
                multi=True,
                style={
                    "width": "220px",
                    "color": "green",
                    "backgroundColor": "white",
                    "borderRadius": "5px",
                    "padding": "4px",
                    "fontSize": "14px"
                }
            )
        ])
    ], style={'display': 'flex', 'marginBottom': '30px'}),

    # Score Summary Boxes
    html.Div(id='account-score-summary', style={'display': 'flex', 'gap': '20px', 'marginBottom': '30px'}),

    # Table + Export button in one row
    html.Div([
        html.Div(id='account-score-data-table', style={'width': '90%'}),
        html.Div([
            html.Button("Export to CSV", id="export-csv-button", n_clicks=0,
                        style={"marginTop": "10px", "padding": "10px 20px", "backgroundColor": "#4CAF50",
                               "color": "white", "border": "none", "borderRadius": "5px", "cursor": "pointer"})
        ], style={'display': 'flex', 'justifyContent': 'flex-end', 'alignItems': 'flex-start', 'width': '10%'})
    ], style={'display': 'flex', 'justifyContent': 'space-between'}),

    dcc.Download(id="download-account-score-csv")
], style={"backgroundColor": "black", "padding": "30px", "minHeight": "100vh"})


# Callback Registration Function
def register_accounts_callbacks(app):
    @app.callback(
        [
            Output('account-score-data-table', 'children'),
            Output('account-score-owner-filter', 'options'),
            Output('account-score-score-filter', 'options'),
            Output('account-score-summary', 'children')
        ],
        [
            Input('account-score-owner-filter', 'value'),
            Input('account-score-score-filter', 'value')
        ],
        prevent_initial_call=False
    )
    def update_table(selected_owner, selected_score):
        # Connect to SQL Server
        try:
            server = 'valentasql.database.windows.net'
            database = 'Xero_CRM'
            username = 'valdb'
            password = 'Valenta@1234'
            table_name = 'dbo.ACCOUNTS'

            params = urllib.parse.quote_plus(
                f"DRIVER={{ODBC Driver 17 for SQL Server}};"
                f"SERVER={server};DATABASE={database};UID={username};PWD={password};"
            )

            engine = create_engine(f"mssql+pyodbc:///?odbc_connect={params}")
            df = pd.read_sql(f"SELECT * FROM {table_name}", engine)

            # Clean and select required columns
            df = df.rename(columns=lambda x: x.strip())
            df = df[['Account Name', 'Account Owner Name', 'Existing Account']]

            # Simulated Score Bucket (Replace with real logic if needed)
            np.random.seed(42)
            df['Score Bucket'] = np.random.choice(
                ['Under 50', '50-100', '100-150', 'Over 150'],
                size=len(df),
                p=[0.7, 0.2, 0.05, 0.05]
            )

        except Exception as e:
            print(f"Error fetching Accounts data: {e}")
            df = pd.DataFrame(columns=['Account Name', 'Account Owner Name', 'Existing Account', 'Score Bucket'])

        # Filter based on selections
        if selected_owner and 'All' not in selected_owner:
            df = df[df['Account Owner Name'].isin(selected_owner)]

        if selected_score and 'All' not in selected_score:
            df = df[df['Score Bucket'].isin(selected_score)]

        # Store filtered data to memory for export
        app.server.df_account_score = df.copy()

        # Dropdown options
        owner_options = [{'label': owner, 'value': owner}
                         for owner in sorted(df['Account Owner Name'].dropna().unique())]

        score_options = [{'label': bucket, 'value': bucket}
                         for bucket in sorted(df['Score Bucket'].dropna().unique())]

        # Score Summary
        under_50_count = len(df[df['Score Bucket'] == 'Under 50'])
        bucket_50_100_count = len(df[df['Score Bucket'] == '50-100'])
        bucket_100_150_count = len(df[df['Score Bucket'] == '100-150'])
        over_150_count = len(df[df['Score Bucket'] == 'Over 150'])

        score_summary = [
            html.Div([
                html.H4(str(under_50_count), style={'margin': 0}),
                html.P('Under 50', style={'margin': 0})
            ], style={
                'backgroundColor': '#FFD700',
                'padding': '15px',
                'borderRadius': '10px',
                'color': 'black',
                'textAlign': 'center',
                'minWidth': '100px'
            }),
            html.Div([
                html.H4(str(bucket_50_100_count), style={'margin': 0}),
                html.P('50-100', style={'margin': 0})
            ], style={
                'backgroundColor': '#FFD700',
                'padding': '15px',
                'borderRadius': '10px',
                'color': 'black',
                'textAlign': 'center',
                'minWidth': '100px'
            }),
            html.Div([
                html.H4(str(bucket_100_150_count), style={'margin': 0}),
                html.P('100-150', style={'margin': 0})
            ], style={
                'backgroundColor': '#FFD700',
                'padding': '15px',
                'borderRadius': '10px',
                'color': 'black',
                'textAlign': 'center',
                'minWidth': '100px'
            }),
            html.Div([
                html.H4(str(over_150_count), style={'margin': 0}),
                html.P('Over 150', style={'margin': 0})
            ], style={
                'backgroundColor': '#FFD700',
                'padding': '15px',
                'borderRadius': '10px',
                'color': 'black',
                'textAlign': 'center',
                'minWidth': '100px'
            }),
        ]

        # DataTable
        table = dash_table.DataTable(
            columns=[
                {'name': 'Account Name', 'id': 'Account Name'},
                {'name': 'Account Owner Name', 'id': 'Account Owner Name'},
                {'name': 'Existing Account', 'id': 'Existing Account'},
                {'name': 'Score Bucket', 'id': 'Score Bucket'},
            ],
            data=df.to_dict('records'),
            style_table={'overflowY': 'auto', 'maxHeight': '500px'},
            style_cell={
                'textAlign': 'left',
                'backgroundColor': '#1e1e1e',
                'color': 'white',
                'padding': '8px'
            },
            style_header={
                'backgroundColor': '#444',
                'color': 'white',
                'fontWeight': 'bold'
            },
            page_size=25
        )

        return table, owner_options, score_options, score_summary

    # Export to CSV Callback
    @app.callback(
        Output("download-account-score-csv", "data"),
        Input("export-csv-button", "n_clicks"),
        prevent_initial_call=True
    )
    def export_csv(n_clicks):
        df = getattr(app.server, 'df_account_score', pd.DataFrame())
        if not df.empty:
            return dcc.send_data_frame(df.to_csv, "Account_Score_Data.csv", index=False)
        return dash.no_update
