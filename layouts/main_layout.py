import os
import dash
import pandas as pd
from dash import html
# import dash_html_components as html
import dash_bootstrap_components as dbc
import dash_mantine_components as dmc

from  dash import dcc#
from dash import Dash, html, dcc, dash_table
from dash.dependencies import Input, Output, State
from layouts.about import about_layout
from layouts.table import tab_layout, create_tab_layout
from layouts.country import country_layout
from dash._dash_renderer import _set_react_version
from components.data_loader import load_exposure_data, load_latest_data #load_exposure_data_s3, load_table_data_s3

# Set React version for dash-mantine-components
_set_react_version("18.2.0")


nav_items = [
    dbc.NavItem(
        dbc.NavLink(
            "HOME",
            href="/",
            className="nav-link-yusuf",
            active="exact"
        )
    ),
    dbc.NavItem(
        dbc.NavLink(
            "TABLE",
            href="/table",
            className="nav-link-yusuf",
            active="exact"
        )
    ),
    dbc.NavItem(
        dbc.NavLink(
            "COUNTRY",
            href="/country",
            className="nav-link-yusuf",
            active="exact"
        )
    ),
    dbc.NavItem(
        dbc.NavLink(
            "ABOUT",
            href="/about",
            className="nav-link-yusuf",
            active="exact"
        )
    ),
]

def get_data():
    """Example data loading function."""
    return load_exposure_data_s3() #load_exposure_data()

def get_defaults():
    data = get_data()
    market_types = data['market_type'].unique()
    default_market_type = market_types[1]
    default_securities = data[data['market_type'] == default_market_type]['security_name'].unique()[-2:]
    return default_market_type, default_securities

def prepare_exposure_table(data):
    """
    Keep this helper function if you need it in app.py or elsewhere.
    """
    data['Date'] = pd.to_datetime(data['calculation_date'])
    latest_date = data.groupby('security_name')['Date'].max().reset_index()
    latest_data = data.merge(latest_date, on=['security_name', 'Date'])
    ch_hk_data = latest_data[latest_data['country_exposure_name'].isin(['China', 'Hong Kong'])]

    exposure_table = ch_hk_data.groupby(['security_name', 'sector']).agg({
        'consolidated_revenue': 'sum',
        'country_exposure(pct)': 'sum'
    }).reset_index()
    exposure_table.columns = [
        'Company Name',
        'Sector',
        'Exposure Revenue (China + HK)',
        'Exposure Percentage (China + HK)'
    ]

    def format_revenue(value):
        if abs(value) >= 1e9:
            return f"{value/1e9:.1f}B"
        elif abs(value) >= 1e6:
            return f"{value/1e6:.1f}M"
        else:
            return f"{value/1e3:.1f}K"

    exposure_table['Exposure Revenue (China + HK)'] = (
        exposure_table['Exposure Revenue (China + HK)'].apply(format_revenue)
    )
    exposure_table['Exposure Percentage (China + HK)'] = (
        exposure_table['Exposure Percentage (China + HK)']
        .round(2)
        .apply(lambda x: f"{x}%")
    )

    exposure_table = exposure_table.sort_values(
        'Exposure Percentage (China + HK)',
        ascending=False,
        key=lambda x: x.str.rstrip('%').astype(float)
    ).head(50)

    return exposure_table

def get_page3(
    app,
    data,
    market_types,
    default_market_type,
    sectors,
    default_sector,
    exposure_types,
    default_exposure_to,
    exposure_table,
    default_securities
):
    styles = {
        'container': {
            'margin': '0 auto',
            'width': '100%',
            'maxWidth': '1650px',
            'padding': '20px 40px',
            'fontFamily': "'DM Sans', sans-serif",
        },
        'filter_container': {
            'backgroundColor': 'rgba(0, 0, 0, 0)', #'rgba(245, 245, 245, 0.7)'
            'padding': '15px 15px 13px 15px',
            'marginTop': '-11px',
            'marginLeft': '-50px',
            'borderRadius': '8px',
        },
        'filters_row': {
            'display': 'flex',
            'flexWrap': 'wrap',
            'gap': '15px',
            'alignItems': 'flex-end',
            'justifyContent': 'flex-start',
            'margin': '0 auto',
            'width': '100%',
        },
        'filter_item': {
            'flex': '0 0 auto',
            'minWidth': 'auto',
            'padding': '0 5px',
            'marginBottom': '0px',
            'display': 'flex',
            'flexDirection': 'column',
            'justifyContent': 'flex-end',
            'overflow': 'hidden',
            'maxWidth': '100%',
        },
        'button_container': {
            'display': 'flex',
            'alignItems': 'flex-end',
            'padding': '0 5px',
            'marginBottom': '1px',
            'height': '100%',
        },
        'label': {
            'display': 'block',
            'marginBottom': '8px',
            'fontWeight': 'bold',
            'fontFamily': "'DM Sans', sans-serif",
            'fontSize': '14px'
        },
        'dropdown_sector': {
            'width': '240px',
            'fontFamily': "'DM Sans', sans-serif",
            'fontSize': '14px',
            'overflow': 'hidden',
            'textOverflow': 'ellipsis',
            'whiteSpace': 'nowrap',
        },
        'chart_container': {
            'display': 'flex',
            'flexDirection': 'column',
            'gap': '30px',
            'marginTop': '10px'
        },
        'tabs_section': {
            'display': 'flex',
            'flexDirection': 'column',
            'marginTop': '20px'
        },
        'chart': {
            'className': 'chart-item',
            'backgroundColor': '#f9f9f9',
            'borderRadius': '8px',
            'padding': '15px',
            'boxShadow': '0 2px 4px rgba(0,0,0,0.05)'
        },
        'chart_two': {
            'className': 'chart-item',
            'backgroundColor': '#f9f9f9',
            'borderRadius': '8px',
            'padding': '15px',
            'boxShadow': '0 2px 4px rgba(0,0,0,0.05)'
        },
        'chart_header': {
            'fontFamily': "'DM Sans', sans-serif",
            'fontSize': '18px',
            'fontWeight': 'bold',
            'color': '#00294b',
            'marginBottom': '10px',
            'paddingBottom': '8px',
            'borderBottom': '1px solid #e0e0e0'
        },
        'source_footer': {
            'display': 'flex',
            'justifyContent': 'space-between',
            'padding': '10px',
            'marginTop': '5px',
            'borderTop': '1px solid #f0f0f0',
            'backgroundColor': '#fcfcfc',
            'borderRadius': '0 0 8px 8px'
        },
        'graph': {
            'height': '550px',
            'max-width': '100%',
            'width': '100%',
            'margin-left': 'auto',
            'margin-right': 'auto',
            'display': 'block'
        },
        'graph_two': {
            'height': '600px',
            'max-width': '100%',
            'width': '100%',
            'margin-left': 'auto',
            'margin-right': 'auto',
            'margin-top': '20px',
            'display': 'block'
        }
    }

    navbar = dbc.Navbar(
        dbc.Container(
            [
                dbc.Row(
                    [
                        dbc.Col(
                            html.A(
                                dbc.Row(
                                    [
                                        dbc.Col(html.Img(src="/assets/logo.svg", height="50px")),
                                        dbc.Col(dbc.NavbarBrand(html.Strong("Exposure Tool"), className="ms-2")),
                                    ],
                                    align="center",
                                    className="g-0",
                                ),
                                href="/",
                                style={"textDecoration": "none"},
                            ),
                            className="ps-5 ms-5 large-shift"
                        ),
                    ],
                    className="me-auto",
                ),
                dbc.Row(
                    [
                        dbc.Col(
                            dbc.Nav(
                                nav_items,
                                navbar=True,
                                className="justify-content-center gap-4",
                            ),
                            className="flex-grow-1 text-center",
                        ),
                    ],
                    className="flex-grow-1 justify-content-center",
                ),
                dbc.Row(
                    [
                        dbc.Col(
                            #flags,
                            className="pe-5 me-5 large-shift",
                        ),
                    ],
                ),
            ],
            fluid=True,
        ),
        color="#ffffff",
        dark=False,
        style={
            "fontFamily": "'DM Sans', sans-serif",
            "borderBottom": "0.5px solid #949494",
            "backgroundColor": "white"
        },
    )

    admin_periods = [
        {
            "name": "Obama (2014-2016)",
            "subtitle": "Engagement & Competition",
            "policy": "Trade growth, selective tech restrictions, TPP negotiations, rising geopolitical tensions.",
            "from": 2014,
            "to": 2016,
            "color": "rgba(0, 112, 192, 0.15)"  # Blue for Democratic
        },
        {
            "name": "Trump (2017-2020)",
            "subtitle": "Trade War & Tech Decoupling",
            "policy": "Tariffs, supply chain disruptions, Huawei ban, financial scrutiny, escalating tensions.",
            "from": 2017,
            "to": 2020,
            "color": "rgba(165, 42, 42, 0.15)"  # Brown for Republican
        },
        {
            "name": "Biden (2021-2023)",
            "subtitle": "Strategic Competition & De-risking",
            "policy": "Chip export controls, supply chain shifts, IRA subsidies, selective engagement, capital market stabilization.",
            "from": 2021,
            "to": 2023,
            "color": "rgba(144, 238, 144, 0.15)"  # Light green for Democratic
        },
        {
            "name": "Biden (2024-Present)",
            "subtitle": "Managed Competition & Protectionism",
            "policy": "Continued strategic competition with targeted protectionist measures.",
            "from": 2024,
            "to": 2025,  # Assuming current year is 2025 as per your date
            "color": "rgba(147, 112, 219, 0.15)"  # Purple for Democratic
        }
    ]

    content = html.Div(
        style=styles['container'],
        children=[
            html.Div(
                style=styles['filter_container'],
                children=[
                    html.Div(
                        style=styles['filters_row'],
                         children=[
                            # Add back the hidden input for market type
                            html.Div(
                                style=styles['filter_item'],
                                children=[
                                    dcc.Input(
                                        id='market-type-hidden-input',
                                        type='hidden',
                                        value=default_market_type
                                    )
                                ]
                            ),
                            html.Div(
                                style=styles['filter_item'],
                                children=[
                                    dmc.MultiSelect(
                                        id='exposure-type-dropdown',
                                        data=[
                                            {'value': et, 'label': et.title()}
                                            for et in exposure_types
                                        ],
                                        value=default_exposure_to,
                                        style={
                                            'fontFamily': "'DM Sans', sans-serif",
                                            'fontSize': '14px',
                                            'width': '400px'
                                        },
                                        searchable=True,
                                        w=450,
                                        description="Country Exposure",
                                        clearable=False,
                                        maxValues=3,
                                        maxDropdownHeight=300,
                                        #nothingFound="No options found",
                                        styles={
                                            "value": {"maxWidth": "100%", "textOverflow": "ellipsis", "whiteSpace": "nowrap"},
                                            "item": {"maxWidth": "100%", "textOverflow": "ellipsis", "whiteSpace": "nowrap"},
                                            "values": {"maxWidth": "100%", "display": "flex", "flexWrap": "nowrap", "overflow": "hidden"}
                                        }
                                    ),
                                ]
                            ),
                            html.Div(
                                style=styles['filter_item'],
                                children=[
                                    dmc.Select(
                                        id='sector-dropdown',
                                        data=[{'value': sector, 'label': sector} for sector in sectors],
                                        value=default_sector,
                                        style=styles['dropdown_sector'],
                                        description="Sector Type",
                                        searchable=True,
                                        clearable=True,
                                        maxDropdownHeight=300,
                                        #nothingFound="No options found",
                                        styles={
                                            "item": {"maxWidth": "100%", "textOverflow": "ellipsis", "whiteSpace": "nowrap"},
                                            "input": {"textOverflow": "ellipsis", "whiteSpace": "nowrap"}
                                        }
                                    )
                                ]
                            ),
                            html.Div(
                                style={**styles['filter_item'], 'flex': '2'},
                                children=[
                                    dmc.MultiSelect(
                                        id='securities-dropdown',
                                        value=default_securities,
                                        style={'width': '480px'},
                                        description="Companies/Securities",
                                        placeholder="",
                                        searchable=True,
                                        clearable=False,
                                        maxValues=2,
                                        w=600,
                                        #maxDropdownHeight=300,
                                        #nothingFound="No options found",
                                        styles={
                                            "value": {"maxWidth": "100%", "textOverflow": "ellipsis", "whiteSpace": "nowrap"},
                                            "item": {"maxWidth": "100%", "textOverflow": "ellipsis", "whiteSpace": "nowrap"},
                                            "values": {"maxWidth": "100%", "display": "flex", "flexWrap": "nowrap", "overflow": "hidden"}
                                        }
                                    ),
                                ]
                            ),
                            html.Div(
                                style=styles['button_container'],
                                children=[
                                    dbc.Button(
                                        'Download Data',
                                        id='download-csv-button',
                                        color='primary',
                                        className='me-2',
                                        style={'height': '36px'}
                                    ),
                                    dcc.Download(id='download-csv'),
                                ]
                            ),
                        ]
                    ),
                ]
            ),

            html.Div(
                style=styles['tabs_section'],
                children=[
                    dbc.Tabs(
                        id="tabs",
                        active_tab='tab-2',
                        children=[
                            dbc.Tab(
                                label='Exposure',
                                tab_id='tab-1',
                                label_style={"color": "#00294b"},
                                # active_tab_style={'color': '#00294b'},
                                children=[
                                    html.Div(
                                        style={'marginTop': '20px'},
                                        children=[
                                            html.Div(
                                                style=styles['chart_container'],
                                                children=[
                                                    html.Div(
                                                        style=styles['chart'],
                                                        children=[
                                                            html.Div(
                                                                "Country Revenue Exposure Over Time",
                                                                style=styles['chart_header']
                                                            ),
                                                            dcc.Graph(
                                                                id='country-exposure-revenue-graph',
                                                                config={
                                                                    'responsive': True,
                                                                    'autosizable': True,
                                                                    'displayModeBar': True,
                                                                    'displaylogo': False,
                                                                },
                                                                style=styles['graph']
                                                            ),
                                                            html.Div(
                                                                style=styles['source_footer'],
                                                                children=[
                                                                    html.Div(
                                                                        "Source: MSCI Economic Exposure Data",
                                                                        style={
                                                                            'fontFamily': "'DM Sans', sans-serif",
                                                                            'fontSize': '14px',
                                                                            'color': '#5a5a5a'
                                                                        }
                                                                    ),
                                                                    html.Div(
                                                                        "SPG CSR | CMGW FRG | VRNC Quanthub",
                                                                        style={
                                                                            'fontFamily': "'DM Sans', sans-serif",
                                                                            'fontSize': '14px',
                                                                            'color': '#5a5a5a'
                                                                        }
                                                                    ),
                                                                ]
                                                            ),
                                                        ]
                                                    ),
                                                    
                                                    html.Div(
                                                        style=styles['chart'],
                                                        children=[
                                                            html.Div(
                                                                "Country Percentage Exposure Trends",
                                                                style=styles['chart_header']
                                                            ),
                                                            dcc.Graph(
                                                                id='country-exposure-pct-graph',
                                                                config={
                                                                    'responsive': True,
                                                                    'autosizable': True,
                                                                    'displayModeBar': True,
                                                                    'displaylogo': False,
                                                                },
                                                                style=styles['graph']
                                                            ),
                                                            html.Div(
                                                                style=styles['source_footer'],
                                                                children=[
                                                                    html.Div(
                                                                        "Source: MSCI Economic Exposure Data",
                                                                        style={
                                                                            'fontFamily': "'DM Sans', sans-serif",
                                                                            'fontSize': '14px',
                                                                            'color': '#5a5a5a'
                                                                        }
                                                                    ),
                                                                    html.Div(
                                                                        "SPG CSR | CMGW FRG | VRNC Quanthub",
                                                                        style={
                                                                            'fontFamily': "'DM Sans', sans-serif",
                                                                            'fontSize': '14px',
                                                                            'color': '#5a5a5a'
                                                                        }
                                                                    ),
                                                                ]
                                                            ),
                                                        ]
                                                    ),

                                                    html.Div(
                                                        style=styles['chart'],
                                                        children=[
                                                            html.Div(
                                                                "Purchasing Power Parity Analysis",
                                                                style=styles['chart_header']
                                                            ),
                                                            dcc.Graph(
                                                                id='parity-graph',
                                                                config={
                                                                    'displayModeBar': True,
                                                                },
                                                                style=styles['graph']
                                                            ),
                                                            html.Div(
                                                                style=styles['source_footer'],
                                                                children=[
                                                                    html.Div(
                                                                        "Source: Haver Analytics",
                                                                        style={
                                                                            'fontFamily': "'DM Sans', sans-serif",
                                                                            'fontSize': '14px',
                                                                            'color': '#5a5a5a'
                                                                        }
                                                                    ),
                                                                    html.Div(
                                                                        "SPG CSR | CMGW FRG | VRNC Quanthub",
                                                                        style={
                                                                            'fontFamily': "'DM Sans', sans-serif",
                                                                            'fontSize': '14px',
                                                                            'color': '#5a5a5a'
                                                                        }
                                                                    ),
                                                                ]
                                                            ),
                                                        ]
                                                    ),
                                                ]
                                            )
                                        ],
                                    ),
                                ]
                            ),
                            dbc.Tab(
                                label='Exposure (%) Bubble',
                                tab_id='tab-2',
                                label_style={"color": "#00294b"},
                                children=[
                                    html.Div(
                                        style=styles['chart_two'],
                                        children=[
                                            html.Div(
                                                "Corporate Exposure Percentage Bubble Chart",
                                                style=styles['chart_header']
                                            ),
                                            dcc.Graph(
                                                id='percentage-bubble-graph',
                                                config={
                                                    'responsive': True,
                                                    'autosizable': True,
                                                    'displayModeBar': True,
                                                    'displaylogo': False,
                                                },
                                                style=styles['graph_two']
                                            ),
                                            html.Div(
                                                style=styles['source_footer'],
                                                children=[
                                                    html.Div(
                                                        "Source: MSCI Economic Exposure Data",
                                                        style={
                                                            'fontFamily': "'DM Sans', sans-serif",
                                                            'fontSize': '14px',
                                                            'color': '#5a5a5a'
                                                        }
                                                    ),
                                                    html.Div(
                                                        "SPG CSR, CMGW FRG, VRNC Quanthub",
                                                        style={
                                                            'fontFamily': "'DM Sans', sans-serif",
                                                            'fontSize': '14px',
                                                            'color': '#5a5a5a'
                                                        }
                                                    ),
                                                ]
                                            ),
                                        ]
                                    ),
                                    html.Div(
                                        style={
                                            'display': 'flex',
                                            'justifyContent': 'space-between',
                                            'padding': '10px',
                                        },
                                        children=[
                                            html.Div(
                                                "Source: MSCI Economic Exposure Data",
                                                style={
                                                    'fontFamily': "'DM Sans', sans-serif",
                                                    'fontSize': '18px',
                                                    'color': '#5a5a5a'
                                                }
                                            ),
                                            html.Div(
                                                "SPG CSR | CMGW FRG | VRNC Quanthub",
                                                style={
                                                    'fontFamily': "'DM Sans', sans-serif",
                                                    'fontSize': '18px',
                                                    'color': '#5a5a5a'
                                                }
                                            ),
                                        ]
                                    ),


                                    # Add the admin_periods_legend component here
                                    html.Div(
                                        style={
                                            'border': '1px solid #ddd',
                                            'borderRadius': '5px',
                                            'padding': '15px',
                                            'marginTop': '20px',
                                            'backgroundColor': 'white',
                                        },
                                        children=[
                                            # html.H4(
                                            #     "US Administration Periods and China Policy",
                                            #     style={
                                            #         'textAlign': 'center',
                                            #         'marginBottom': '15px',
                                            #         'fontFamily': "'DM Sans', sans-serif",
                                            #         'fontWeight': 'bold',
                                            #         'color': '#00294b'
                                            #     }
                                            # ),
                                            html.Div(
                                                style={
                                                    'display': 'flex',
                                                    'flexWrap': 'wrap',
                                                    'justifyContent': 'space-around',
                                                    'gap': '10px'
                                                },
                                                children=[
                                                    html.Div(
                                                        style={
                                                            'flex': '1 1 300px',
                                                            'display': 'flex',
                                                            'alignItems': 'center',
                                                            'padding': '10px',
                                                            'border': '1px solid #eee',
                                                            'borderRadius': '5px',
                                                            'backgroundColor': period["color"].replace("0.15", "0.1"),
                                                            'marginBottom': '5px'
                                                        },
                                                        children=[
                                                            html.Div(
                                                                style={
                                                                    'width': '20px',
                                                                    'height': '20px',
                                                                    'backgroundColor': period["color"].replace("0.15", "0.8"),
                                                                    'marginRight': '10px',
                                                                    'border': '1px solid #000'
                                                                }
                                                            ),
                                                            html.Div(
                                                                style={'flex': '1'},
                                                                children=[
                                                                    html.Strong(
                                                                        f"{period['name']}: {period['subtitle']}",
                                                                        style={'display': 'block', 'marginBottom': '5px'}
                                                                    ),
                                                                    html.Span(
                                                                        period['policy'],
                                                                        style={'fontSize': '0.9em'}
                                                                    )
                                                                ]
                                                            )
                                                        ]
                                                    )
                                                    for period in admin_periods
                                                ]
                                            )
                                        ]
                                    ),
                                                            ]
                            ),
                        ],
                    ),
                ]
            ),

            dbc.Alert(
                id='security-alert',
                is_open=False,
                duration=4000,
                color='warning',
                dismissable=True,
                style={'margin-top': '10px'}
            ),
        ]
    )

    layout = dmc.MantineProvider(
        theme={
            "colorScheme": "light",
            "fontFamily": "'DM Sans', sans-serif",
        },
        children=[
            # html.Link(
            #     href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700&display=swap",
            #     rel="stylesheet"
            # ),
            dcc.Location(id="url", refresh=False),
            navbar,
            html.Div(id="page-content")
        ]
    )

    @app.callback(
        Output("page-content", "children"),
        [Input("url", "pathname")],
        prevent_initial_call=False
    )
    def display_page(pathname):
        """
        This callback decides which "page" to display based on the URL.
        """
        if pathname == "/table":
            return create_tab_layout() #tab_layout
        elif pathname == "/about":
            return about_layout
        elif pathname == "/country":
            return country_layout
        else:
            return content

    return layout