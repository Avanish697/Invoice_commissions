import pandas as pd
import dash
from dash import dcc, html, dash_table
from dash.dependencies import Input, Output, State
from sqlalchemy import create_engine
import urllib
import numpy as np

# Define dropdown style with increased font size
dropdown_style = {
    "width": "220px",
    "backgroundColor": "white",
    "color": "green",
    "border": "1px",
    "borderRadius": "4px",
    "fontSize": "18px",  # Increased font size from 15px to 18px
    "boxShadow": "none",
    "outline": "none",
    "height": "45px"     # Increased height slightly to match font
}

# Layout for Account Score Page
accounts_layout = html.Div([
    # Filters
    html.Div([
        html.Div([
            html.Label("Account Owner Name", style={"color": "black", "fontSize": "20px", "fontWeight": "bold"}),
            dcc.Dropdown(
                id='account-score-owner-filter',
                placeholder='Select Account Owner Name',
                multi=True,
                style=dropdown_style
            )
        ], style={'marginRight': '30px'}),

        html.Div([
            html.Label("Score Bucket", style={"color": "black", "fontSize": "20px", "fontWeight": "bold"}),
            dcc.Dropdown(
                id='account-score-score-filter',
                placeholder='Select Score Bucket',
                multi=True,
                style=dropdown_style
            )
        ])
    ], style={'display': 'flex', 'marginBottom': '30px'}),

    # Score Summary Boxes
    html.Div(id='account-score-summary', style={'display': 'flex', 'gap': '20px', 'marginBottom': '30px'}),

    # Table
    html.Div(id='account-score-data-table', style={'width': '100%', 'marginBottom': '20px'}),

    # Export button below table
    html.Div([
        html.Button("Export to CSV", id="export-csv-button", n_clicks=0,
                    style={
                        "padding": "12px 24px",
                        "backgroundColor": "#4CAF50",
                        "color": "white",
                        "border": "none",
                        "borderRadius": "5px",
                        "cursor": "pointer",
                        "fontSize": "18px",  # Increased font size
                        "fontWeight": "bold"
                    })
    ], style={'display': 'flex', 'justifyContent': 'flex-end'}),

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

            df = df.rename(columns=lambda x: x.strip())
            df = df[['Account Name', 'Account Owner Name', 'Existing Account']]

            # Simulate Score Bucket
            np.random.seed(42)
            df['Score Bucket'] = np.random.choice(
                ['Under 50', '50-100', '100-150', 'Over 150'],
                size=len(df),
                p=[0.7, 0.2, 0.05, 0.05]
            )

        except Exception as e:
            print(f"Error fetching Accounts data: {e}")
            df = pd.DataFrame(columns=['Account Name', 'Account Owner Name', 'Existing Account', 'Score Bucket'])

        # Filters
        if selected_owner and 'All' not in selected_owner:
            df = df[df['Account Owner Name'].isin(selected_owner)]
        if selected_score and 'All' not in selected_score:
            df = df[df['Score Bucket'].isin(selected_score)]

        app.server.df_account_score = df.copy()

        owner_options = [{'label': owner, 'value': owner}
                         for owner in sorted(df['Account Owner Name'].dropna().unique())]
        score_options = [{'label': bucket, 'value': bucket}
                         for bucket in sorted(df['Score Bucket'].dropna().unique())]

        # Score Summary
        score_summary = []
        for label in ['Under 50', '50-100', '100-150', 'Over 150']:
            count = len(df[df['Score Bucket'] == label])
            score_summary.append(
                html.Div([
                    html.H4(str(count), style={'margin': 0, 'fontSize': '24px', 'fontWeight': 'bold'}),
                    html.P(label, style={'margin': 0, 'fontSize': '18px'})
                ], style={
                    'backgroundColor': '#FFD700',
                    'padding': '20px',
                    'borderRadius': '10px',
                    'color': 'black',
                    'textAlign': 'center',
                    'minWidth': '120px'
                })
            )

        # Table
        table = dash_table.DataTable(
            columns=[
                {'name': 'Account Name', 'id': 'Account Name'},
                {'name': 'Account Owner Name', 'id': 'Account Owner Name'},
                {'name': 'Existing Account', 'id': 'Existing Account'},
                {'name': 'Score Bucket', 'id': 'Score Bucket'},
            ],
            data=df.to_dict('records'),
            style_table={
                'overflowY': 'auto',
                'maxHeight': '650px',
                'minHeight': '400px'
            },
            style_cell={
                'textAlign': 'left',
                'backgroundColor': '#1e1e1e',
                'color': 'white',
                'padding': '14px',
                'fontSize': '18px'   # Increased from 15px
            },
            style_header={
                'backgroundColor': '#444',
                'color': 'white',
                'fontWeight': 'bold',
                'fontSize': '20px'   # Increased from 16px
            },
            page_size=25
        )

        return table, owner_options, score_options, score_summary

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
