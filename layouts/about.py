
import dash_bootstrap_components as dbc
# import dash_html_components as html
from dash import html
from pathlib import Path
import pandas as pd
import os


# DATA_DIR = Path(__file__).parent.parent / 'data'
# file_path = os.path.join(DATA_DIR, "newer_data_table.csv")
# df = pd.read_csv(file_path)

styles = {
    'container': {
        'padding': '40px',
        'max-width': '1400px',
        'margin': '0 auto',
        'font-family': "'DM Sans', sans-serif",
        'display': 'flex',
        'gap': '40px'
    },
    'main_content': {
        'flex': '1',
        'max-width': '900px'
    },
    'team_sidebar': {
        'width': '300px',
        'padding': '20px',
        'background': 'white',
        'border-radius': '8px',
        'box-shadow': '0 2px 4px rgba(0, 0, 0, 0.05)',
    },
    'team_member': {
        'display': 'flex',
        'align-items': 'center',
        'margin-bottom': '15px',
        'padding': '10px',
        'border-radius': '8px',
        'transition': 'background-color 0.3s'
    },
    'team_member_img': {
        'width': '40px',
        'height': '40px',
        'border-radius': '50%',
        'margin-right': '15px'
    },
    'team_member_info': {
        'flex': '1'
    },
    'section': {
        'margin-bottom': '30px'
    },
    'subsection': {
        'margin-left': '20px',
        'margin-bottom': '15px'
    }
}

# Team members data
team_members = [
    {"name": "Stephen Green", "role": "STG"},
    {"name": "Chuming Wang", "role": "CMGW"},
    {"name": "Veronica Chu", "role": "VRNC"},
]

about_layout = html.Div(style=styles['container'], children=[
    # Main Content
    html.Div(style=styles['main_content'], children=[
        html.H1("About The Tool", style={'margin-bottom': '1px', 'color': 'black', 'font-size': '2.1rem'}),

        html.P(),
        
        html.P([
            "The Exposure Tool provides a comprehensive view of the revenue that worldwide public companies derive from China,"
            "covering data from 2014 to the most recent reporting period. By tracking revenue exposure trends over time, it highlights the"
            "heightened geopolitical and regulatory risks these firms face amid shifting U.S.-China relations. Investors can use these insights"
            "to better evaluate potential impacts on their portfolios, anticipate volatility, and make more informed decisions in an increasingly uncertain"
            "global market."
        ], style={'margin-top': '30px', 'margin-bottom': '30px', 'line-height': '1.6', 'color': '#5a6c7d'}),

        html.Div(style=styles['section'], children=[
            # Additional content or sections can be added here
        ])
    ]),

    # Team Sidebar
    html.Div(style=styles['team_sidebar'], children=[
        html.H2("CSR Team", style={'margin-bottom': '20px', 'color': '#2c3e50'}),
        html.Div([
            html.Div(style=styles['team_member'], children=[
                # Uncomment and update image source if required
                # html.Img(src="assets/stephen.jpg", style=styles['team_member_img']),
                html.Div(style=styles['team_member_info'], children=[
                    html.Div(member["name"], style={'font-weight': '500'}),
                    html.Div(member["role"], style={'color': '#6c757d', 'font-size': '0.9rem'})
                ])
            ]) for member in team_members
        ])
    ])
]) 
