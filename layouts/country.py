import dash
import dash_bootstrap_components as dbc
from dash import html, dcc
import dash_mantine_components as dmc
import dash_ag_grid as dag

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
        
        # Main content container - now with two columns
        html.Div(
            style={
                'display': 'flex',
                'flexDirection': 'row',
                'flexWrap': 'wrap',
                'gap': '30px',
            },
            children=[
                # Treemap container (left column)
                html.Div(
                    style={
                        'flex': '2',
                        'minWidth': '500px',
                        'backgroundColor': 'white',
                        'padding': '20px',
                        'borderRadius': '10px',
                        'boxShadow': '0 4px 8px rgba(0, 0, 0, 0.1)',
                    },
                    children=[
                        dcc.Graph(
                            id='country-treemap',
                            figure={},
                            style={'height': '550px'},
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
                
                # Exposure table container (right column)
                html.Div(
                    style={
                        'flex': '1',
                        'minWidth': '350px',
                        'backgroundColor': 'white',
                        'padding': '20px',
                        'borderRadius': '10px',
                        'boxShadow': '0 4px 8px rgba(0, 0, 0, 0.1)',
                    },
                    children=[
                        html.H3(
                            "Country Exposure Data",
                            style={
                                'fontSize': '22px',
                                'fontWeight': 'bold',
                                'marginBottom': '15px',
                                'color': '#00294b',
                                'borderBottom': '1px solid #e0e0e0',
                                'paddingBottom': '10px',
                            }
                        ),
                        
                        # AG Grid component for exposure data
                        dag.AgGrid(
                            id='country-exposure-table',
                            rowData=[],
                            columnDefs=[
                                {"field": "Country", "headerName": "Country", "sortable": True, "filter": True, "resizable": True},
                                {"field": "Exposure (%)", "headerName": "Exposure (%)", "sortable": True, "filter": True, "resizable": True},
                                {"field": "Revenue", "headerName": "Revenue", "sortable": True, "filter": True, "resizable": True},
                            ],
                            dashGridOptions={
                                "domLayout": "autoHeight",
                                "rowSelection": "single",
                                "pagination": True,
                                "paginationPageSize": 10,
                                "paginationAutoPageSize": False,
                                "defaultColDef": {
                                    "resizable": True,
                                    "sortable": True,
                                    "filter": True,
                                    "floatingFilter": True
                                },
                                "animateRows": False,
                                "suppressCellSelection": True
                            },
                            className="ag-theme-alpine",
                            style={"height": "auto", "width": "100%", "minHeight": "400px"},
                        ),
                        
                        # Small footnote
                        html.Div(
                            "Sorted by exposure percentage (descending)",
                            style={
                                'marginTop': '15px',
                                'fontSize': '12px',
                                'fontStyle': 'italic',
                                'color': '#666'
                            }
                        )
                    ]
                )
            ]
        ),
        
        # Footer with source info
        html.Div(
            style={
                'display': 'flex',
                'justifyContent': 'space-between',
                'padding': '15px',
                'marginTop': '20px',
                'backgroundColor': '#f8f9fa',
                'borderRadius': '5px',
                'color': '#5a5a5a',
                'fontSize': '14px'
            },
            children=[
                html.Div("Source: MSCI Economic Exposure Data"),
                html.Div("SPG CSR | CMGW FRG | VRNC Quanthub")
            ]
        )
    ]
) 