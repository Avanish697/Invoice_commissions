import dash
from dash import dcc, html
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output
import flask
import dash_auth
from flask import request
import os

# Import layouts and callbacks
from Invoice_details import layout as invoice_layout
from Receivables_details import layout as receivables_layout
from Overview import layout as overview_layout, register_callbacks as register_overview_callbacks
from Entity_breakdown import layout as entity_layout, register_callbacks as register_entity_callbacks
from Accounts_Score import accounts_layout, register_accounts_callbacks
from Deals_in_client_pipeline import client_layout, register_client_callbacks
from Deals_Closing import deals_closing_layout, register_deals_closing_callbacks
from Deals_in_Franchise_pipeline import franchise_layout, register_franchise_callbacks
from Pipeline_by_service_and_lead import graphs_layout, register_graphs_callbacks
from Sales_Cycle import sales_cycle_layout, register_sales_cycle_callbacks

# 1. Define username-password pairs
VALID_USERNAME_PASSWORD_PAIRS = {
    'Alpesh Patel': 'alpesh123',
    'Danyaal Shah': 'danyaal123',
    'admin': 'admin123'
}

# 2. Create server and app
server = flask.Flask(__name__)
app = dash.Dash(
    __name__,
    server=server,
    suppress_callback_exceptions=True,
    external_stylesheets=[dbc.themes.BOOTSTRAP]
)
app.title = "Valenta Invoice & Sales Dashboard"
app.server.secret_key = '12345678'

# 3. Auth setup
auth = dash_auth.BasicAuth(app, VALID_USERNAME_PASSWORD_PAIRS)

# 4. Sidebar
sidebar = html.Div(
    dbc.Nav(
        [
            dbc.NavLink("Overview", href="/overview", id="overview-link", active="exact"),
            dbc.NavLink("Entity Breakdown", href="/entity", id="entity-link", active="exact"),
            dbc.NavLink("Invoice Details", href="/invoice", id="invoice-link", active="exact"),
            dbc.NavLink("Receivables Details", href="/receivables", id="receivables-link", active="exact"),
            dbc.NavLink("Deals in Client Pipeline", href="/client", id="client-link", active="exact"),
            dbc.NavLink("Deals in Franchise Pipeline", href="/franchise", id="franchise-link", active="exact"),
            dbc.NavLink("Pipeline by Service and Lead", href="/graphs", id="graphs-link", active="exact"),
            dbc.NavLink("Accounts Score", href="/accounts_score", id="accounts-link", active="exact"),
            dbc.NavLink("Deals Closing Rate", href="/deals_closing", id="deals-closing-link", active="exact"),
            dbc.NavLink("Sales Cycle", href="/sales_cycle", id="sales-cycle-link", active="exact"),
            dbc.NavLink("Logout", href="/logout", id="logout-link", active="exact", style={"color": "red"}),
        ],
        vertical=True,
        pills=True,
        className="text-white",
    ),
    style={
        'backgroundColor': 'black',
        'height': '100vh',
        'overflowY': 'auto',
        'padding': '20px',
        'position': 'fixed',
        'top': 0,
        'left': 0,
        'width': '16.666667%'
    }
)

# 5. Main content
content = html.Div(
    id="page-content",
    className="p-4",
    style={
        "marginLeft": "16.666667%",
        "backgroundColor": "#121212",
        "width": "83.333333%",
        "minHeight": "100vh",
        "color": "white"
    }
)

# 6. Layout
app.layout = html.Div([
    dcc.Location(id="url"),
    dcc.Store(id="user-store", storage_type="session"),  # Stores logged-in user
    sidebar,
    content
])

# 7. Register callbacks
register_overview_callbacks(app)
register_entity_callbacks(app)
register_client_callbacks(app)
register_franchise_callbacks(app)
register_graphs_callbacks(app)
register_deals_closing_callbacks(app)
register_sales_cycle_callbacks(app)
register_accounts_callbacks(app)

# 8. Store username in dcc.Store
@app.callback(
    Output("user-store", "data"),
    Input("url", "pathname")
)
def store_user(pathname):
    username = request.authorization.username
    return {"username": username}

# 9. Page routing
@app.callback(
    Output("page-content", "children"),
    Input("url", "pathname")
)
def display_page(pathname):
    if pathname == "/logout":
        return html.Div([
            html.H2("Logged Out", style={"color": "red"}),
            html.P("To fully log out, please close this browser tab or clear your browser cache."),
            html.P("Due to HTTP Basic Auth limitations, full logout is handled by the browser.")
        ])
    if pathname in ["/", "/overview"]:
        return overview_layout
    elif pathname == "/entity":
        return entity_layout
    elif pathname == "/invoice":
        return invoice_layout
    elif pathname == "/receivables":
        return receivables_layout
    elif pathname == "/client":
        return client_layout
    elif pathname == "/franchise":
        return franchise_layout
    elif pathname == "/graphs":
        return graphs_layout
    elif pathname == "/accounts_score":
        return accounts_layout
    elif pathname == "/deals_closing":
        return deals_closing_layout
    elif pathname == "/sales_cycle":
        return sales_cycle_layout
    else:
        return overview_layout

# 10. Sidebar active link highlight
@app.callback(
    [Output("overview-link", "active"),
     Output("entity-link", "active"),
     Output("invoice-link", "active"),
     Output("receivables-link", "active"),
     Output("client-link", "active"),
     Output("franchise-link", "active"),
     Output("graphs-link", "active"),
     Output("accounts-link", "active"),
     Output("deals-closing-link", "active"),
     Output("sales-cycle-link", "active")],
    Input("url", "pathname")
)
def set_active_link(pathname):
    return [
        pathname in ["/", "/overview"],
        pathname == "/entity",
        pathname == "/invoice",
        pathname == "/receivables",
        pathname == "/client",
        pathname == "/franchise",
        pathname == "/graphs",
        pathname == "/accounts_score",
        pathname == "/deals_closing",
        pathname == "/sales_cycle"
    ]

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=False)