import dash
import dash_bootstrap_components as dbc
from dash import html, dcc
import dash_mantine_components as dmc

country_layout = html.Div(
    style={
        'margin': '0 auto',
        'width': '100%',
        'maxWidth': '1650px',
        'padding': '20px 40px',
        'fontFamily': "'DM Sans', sans-serif",
    },
    children=[
        html.H1(
            "Country Exposure Treemap",
            style={
                'fontSize': '36px',
                'fontWeight': 'bold',
                'marginBottom': '30px',
                'color': '#00294b'
            }
        ),
        
        # Filter container for dropdowns
        html.Div(
            style={
                'display': 'flex',
                'flexWrap': 'wrap',
                'gap': '20px',
                'marginBottom': '30px',
                'alignItems': 'flex-end'
            },
            children=[
                # Sector dropdown
                html.Div(
                    style={
                        'flex': '1',
                        'minWidth': '200px'
                    },
                    children=[
                        html.Label(
                            "Select Sector",
                            style={
                                'fontWeight': 'bold',
                                'fontSize': '16px',
                                'marginBottom': '8px',
                                'display': 'block'
                            }
                        ),
                        dcc.Dropdown(
                            id='country-sector-dropdown',
                            placeholder="Select a sector",
                            style={'width': '100%'},
                            clearable=False
                        )
                    ]
                ),
                
                # Security dropdown
                html.Div(
                    style={
                        'flex': '1',
                        'minWidth': '300px'
                    },
                    children=[
                        html.Label(
                            "Select Security",
                            style={
                                'fontWeight': 'bold',
                                'fontSize': '16px',
                                'marginBottom': '8px',
                                'display': 'block'
                            }
                        ),
                        dcc.Dropdown(
                            id='country-security-dropdown',
                            placeholder="Select a security",
                            style={'width': '100%'},
                            clearable=False
                        )
                    ]
                )
            ]
        ),
        
        # Treemap container
        html.Div(
            style={
                'backgroundColor': 'white',
                'padding': '20px',
                'borderRadius': '10px',
                'boxShadow': '0 4px 8px rgba(0, 0, 0, 0.1)',
                'marginBottom': '30px'
            },
            children=[
                dcc.Graph(
                    id='country-treemap',
                    figure={},
                    style={'height': '600px'},
                    config={
                        'displayModeBar': True,
                        'displaylogo': False,
                        'modeBarButtonsToRemove': [
                            'select2d', 'lasso2d', 'resetScale2d',
                            'hoverClosestCartesian', 'hoverCompareCartesian'
                        ]
                    }
                )
            ]
        ),
        
        # Information text
        html.Div(
            style={
                'marginTop': '20px',
                'padding': '15px',
                'backgroundColor': '#f8f9fa',
                'borderRadius': '5px',
                'fontSize': '14px',
                'color': '#555'
            },
            children=[
                html.P(
                    [
                        html.Strong("How to use: "),
                        "Select a sector from the first dropdown, then choose a specific security from the second dropdown to view its country exposure as a treemap visualization. The size of each block represents the percentage of exposure to that country."
                    ]
                ),
                html.P(
                    [
                        html.Strong("Hover info: "),
                        "Hover over each country block to see detailed information about the exposure percentage."
                    ]
                )
            ]
        )
    ]
) 