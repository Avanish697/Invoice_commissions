import pandas as pd
from dash import dcc, html, Input, Output, State, callback_context
import dash_table
import plotly.graph_objects as go
import urllib
import sqlalchemy
import dash
from dash.exceptions import PreventUpdate

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

# Preprocessing
df['Created Time'] = pd.to_datetime(df['Created Time'], errors='coerce')
df['Closing Date'] = pd.to_datetime(df['Closing Date'], errors='coerce')
df['Stage'] = df['Stage'].fillna('')
df['Deal Owner Name'] = df['Deal Owner Name'].fillna('Unknown')
df['# Deals Entered'] = 1
closed_stages = ['Closed-Won', 'Closed (Lost)', 'Closed (Future prospect)']
df['Is Closed'] = df['Stage'].isin(closed_stages)

deal_owners = sorted(df['Deal Owner Name'].unique())
service_lines = sorted(df['Service Line'].dropna().unique())

# Dropdown style as requested
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

# ===================== Layout =====================
deals_closing_layout = html.Div(style={'backgroundColor': '#111', 'padding': '15px'}, children=[
    html.Div([
        html.Div([
            dcc.Dropdown(
                id='service-filter-deals-closing',
                options=[{'label': i, 'value': i} for i in service_lines],
                placeholder="Select Service Line",
                clearable=True,
                multi=True,
                style=dropdown_style
            ),
        ], style={'marginRight': '20px'}),

        html.Div([
            dcc.Dropdown(
                id='owner-filter-deals-closing',
                options=[{'label': i, 'value': i} for i in deal_owners],
                placeholder="Select Deal Owner",
                clearable=True,
                multi=True,
                style=dropdown_style
            ),
        ]),
    ], style={'display': 'flex', 'marginBottom': '20px'}),

    html.Div(id='kpi-cards-deals-closing', style={'display': 'flex', 'marginBottom': '20px', 'gap': '15px'}),

    html.Div(style={'display': 'flex'}, children=[
        html.Div([
            html.Div(id='data-table-deals-closing'),
            html.Button("Export to CSV", id="export-btn-deals-closing", n_clicks=0,
                        style={'marginTop': '10px', 'backgroundColor': '#FFD700', 'color': 'black',
                               'fontWeight': 'bold', 'border': 'none', 'borderRadius': '5px', 'padding': '8px'}),
            dcc.Download(id="download-deals-closing")
        ], style={'width': '50%', 'paddingRight': '10px'}),
        html.Div(id='bar-chart-deals-closing', style={'width': '50%', 'paddingLeft': '10px'}),
    ])
])

# ===================== Callbacks =====================
def register_deals_closing_callbacks(app):
    @app.callback(
        [Output('kpi-cards-deals-closing', 'children'),
         Output('data-table-deals-closing', 'children'),
         Output('bar-chart-deals-closing', 'children')],
        [Input('owner-filter-deals-closing', 'value'),
         Input('service-filter-deals-closing', 'value')],
    )
    def update_dashboard(selected_owner, selected_service):
        filtered_df = df.copy()
        if selected_owner:
            filtered_df = filtered_df[filtered_df['Deal Owner Name'].isin(selected_owner)]
        if selected_service:
            filtered_df = filtered_df[filtered_df['Service Line'].isin(selected_service)]

        entered_group = filtered_df.groupby('Deal Owner Name').agg({
            'Deal Name': pd.Series.nunique
        }).reset_index().rename(columns={'Deal Name': '# Deals Entered'})

        closed_df = filtered_df[filtered_df['Is Closed']]
        closed_group = closed_df.groupby('Deal Owner Name').agg({
            'Deal Name': pd.Series.nunique
        }).reset_index().rename(columns={'Deal Name': '# Deals Closed'})

        grouped = pd.merge(entered_group, closed_group, on='Deal Owner Name', how='left')
        grouped['# Deals Closed'] = grouped['# Deals Closed'].fillna(0).astype(int)
        grouped['% Deals Closed'] = ((grouped['# Deals Closed'] / grouped['# Deals Entered']) * 100).round(2)

        total_row = {
            'Deal Owner Name': 'Total',
            '# Deals Entered': grouped['# Deals Entered'].sum(),
            '# Deals Closed': grouped['# Deals Closed'].sum(),
            '% Deals Closed': round(
                grouped['# Deals Closed'].sum() / grouped['# Deals Entered'].sum() * 100, 2
            ) if grouped['# Deals Entered'].sum() != 0 else 0
        }

        grouped = pd.concat([grouped, pd.DataFrame([total_row])], ignore_index=True)
        grouped['% Deals Closed'] = grouped['% Deals Closed'].astype(str) + '%'

        grouped_no_total = grouped[grouped['Deal Owner Name'] != 'Total']

        # KPI Cards
        kpi_cards = []
        for kpi, value in zip(
            ['# Deals Entered', '# Deals Closed', '% Deals Closed'],
            [total_row['# Deals Entered'], total_row['# Deals Closed'], str(total_row['% Deals Closed']) + '%']
        ):
            kpi_cards.append(
                html.Div([
                    html.H3(value, style={'margin': 0}),
                    html.P(kpi, style={'margin': 0})
                ], style={
                    'backgroundColor': '#FFD700',
                    'padding': '10px 15px',
                    'borderRadius': '8px',
                    'fontWeight': 'bold',
                    'color': 'black',
                    'width': '180px',
                    'textAlign': 'center'
                })
            )

        # Data Table
        table = dash_table.DataTable(
            columns=[{'name': i, 'id': i} for i in grouped.columns],
            data=grouped.to_dict('records'),
            style_table={'overflowX': 'auto'},
            style_cell={
                'backgroundColor': '#1e1e1e', 'color': 'white', 'textAlign': 'left', 'padding': '8px'
            },
            style_header={
                'backgroundColor': '#444', 'color': 'white', 'fontWeight': 'bold'
            },
            style_data_conditional=[{
                'if': {'filter_query': '{Deal Owner Name} = "Total"'},
                'backgroundColor': '#333', 'fontWeight': 'bold'
            }],
        )

        # Bar Chart
        grouped_no_total['Entered %'] = grouped_no_total['# Deals Entered'] / grouped_no_total['# Deals Entered'].max()
        grouped_no_total['Closed %'] = grouped_no_total['# Deals Closed'] / grouped_no_total['# Deals Entered']

        bar_fig = go.Figure()

        bar_fig.add_trace(go.Bar(
            x=grouped_no_total['Deal Owner Name'],
            y=grouped_no_total['Entered %'],
            name='# Deals Entered',
            marker_color='skyblue',
            offsetgroup=0,
            width=1.6,
            hovertemplate='%{x}<br># Deals Entered: %{customdata}<extra></extra>',
            customdata=grouped_no_total['# Deals Entered'],
        ))

        bar_fig.add_trace(go.Bar(
            x=grouped_no_total['Deal Owner Name'],
            y=grouped_no_total['Closed %'],
            name='# Deals Closed',
            marker_color='orange',
            offsetgroup=0,
            width=1.6,
            base=grouped_no_total['Entered %'],
            hovertemplate='%{x}<br># Deals Closed: %{customdata}<extra></extra>',
            customdata=grouped_no_total['# Deals Closed'],
        ))

        bar_fig.update_layout(
            barmode='stack',
            plot_bgcolor='#111',
            paper_bgcolor='#111',
            font=dict(color='white'),
            title=dict(
                text='# Deals Entered and # Deals Closed by Deal Owner Name',
                x=0.5,
                xanchor='center',
                y=0.95
            ),
            xaxis=dict(title='Deal Owner Name'),
            yaxis=dict(title='# Deals Entered and # Deals Closed', tickformat='.0%', range=[0, 1.2]),
            legend=dict(orientation='h', x=0, y=1.05),
            margin=dict(t=80, l=40, r=10, b=80)
        )

        return kpi_cards, table, dcc.Graph(figure=bar_fig)

    @app.callback(
        Output("download-deals-closing", "data"),
        Input("export-btn-deals-closing", "n_clicks"),
        State('owner-filter-deals-closing', 'value'),
        State('service-filter-deals-closing', 'value'),
        prevent_initial_call=True
    )
    def export_csv(n_clicks, selected_owner, selected_service):
        if n_clicks is None or n_clicks == 0:
            raise PreventUpdate
        filtered_df = df.copy()
        if selected_owner:
            filtered_df = filtered_df[filtered_df['Deal Owner Name'].isin(selected_owner)]
        if selected_service:
            filtered_df = filtered_df[filtered_df['Service Line'].isin(selected_service)]

        entered_group = filtered_df.groupby('Deal Owner Name').agg({
            'Deal Name': pd.Series.nunique
        }).reset_index().rename(columns={'Deal Name': '# Deals Entered'})

        closed_df = filtered_df[filtered_df['Is Closed']]
        closed_group = closed_df.groupby('Deal Owner Name').agg({
            'Deal Name': pd.Series.nunique
        }).reset_index().rename(columns={'Deal Name': '# Deals Closed'})

        grouped = pd.merge(entered_group, closed_group, on='Deal Owner Name', how='left')
        grouped['# Deals Closed'] = grouped['# Deals Closed'].fillna(0).astype(int)
        grouped['% Deals Closed'] = ((grouped['# Deals Closed'] / grouped['# Deals Entered']) * 100).round(2)

        total_row = {
            'Deal Owner Name': 'Total',
            '# Deals Entered': grouped['# Deals Entered'].sum(),
            '# Deals Closed': grouped['# Deals Closed'].sum(),
            '% Deals Closed': round(
                grouped['# Deals Closed'].sum() / grouped['# Deals Entered'].sum() * 100, 2
            ) if grouped['# Deals Entered'].sum() != 0 else 0
        }

        grouped = pd.concat([grouped, pd.DataFrame([total_row])], ignore_index=True)
        grouped['% Deals Closed'] = grouped['% Deals Closed'].astype(str) + '%'

        return dcc.send_data_frame(grouped.to_csv, "Deals_Closing_Export.csv", index=False)


# ===================== Dash App Setup =====================
app = dash.Dash(__name__)
app.layout = deals_closing_layout
register_deals_closing_callbacks(app)

