
from dash import html, dcc
import dash_bootstrap_components as dbc
import dash_ag_grid as dag
import dash
import pandas as pd
from pathlib import Path
import os
import io
import sys

import boto3

APP_ENV = os.environ['ENV']
QH_APPDATA_ACCESS_KEY = os.environ['QH_APPDATA_ACCESS_KEY']
QH_APPDATA_SECRET_KEY = os.environ['QH_APPDATA_SECRET_KEY']
QH_APPDATA_BUCKET_NAME = os.environ['QH_APPDATA_BUCKET_NAME']


qh_appdata_session = boto3.Session(aws_access_key_id=QH_APPDATA_ACCESS_KEY,
                                   aws_secret_access_key=QH_APPDATA_SECRET_KEY,
                                   region_name='us-east-1')

qh_appdata_client = qh_appdata_session.client('s3')


def get_s3_df(filepath):
    obj = qh_appdata_client.get_object(Bucket=QH_APPDATA_BUCKET_NAME, Key=filepath)
    df = pd.read_csv(io.BytesIO(obj['Body'].read()))
    return df

def load_table_data_s3():
    path = 'appdata/CSR_Exposure_Tool/market_cap_data_2025_19_03.csv'
    return get_s3_df(path)

selected_columns = [
    'companyname', 'sedol', 'sector', 'marketcapusd', 'country_exposure_name',
    'country_exposure(pct)', 'country_exposure_revenue', 'industry'
]

# df = pd.read_csv(Path(__file__).parent.parent / 'data' / 'newer_data_table.csv')[selected_columns]

# TODO this is for s3
df = load_table_data_s3()
df = df[selected_columns]


#df['market_type'] = df['market_type'].str.title()
# print(df.columns)
# print(df['country_exp_revenue'].dtype)

numeric_columns = ['country_exposure(pct)', 'country_exposure_revenue', 'marketcapusd'] # marketcapusd, .. marketcapusd_new
for col in numeric_columns:
    df[col] = pd.to_numeric(df[col], errors='coerce')

string_columns = ['companyname', 'sedol', 'sector', 'country_exposure_name', 'industry']
for col in string_columns:
    df[col] = df[col].astype(str).replace('nan', '')

sectors = df['sector'].unique()
# Note: The original code had a potential mistake: sorting by 'country_exp_revenue' for countries, but keeping as is
countries = sorted(df['country_exposure_name'].unique())

def get_color(value):
    if value <= 50:
        return f"rgba(255, 255, {int(255 * (1 - value/50))}, 0.8)"
    else:
        return f"rgba(255, {int(255 * (1 - (value-50)/50))}, 0, 0.8)"

percentage_cell_style = {
    "styleConditions": [
        {
            "condition": f"params.value == {value}",
            "style": {
                "backgroundColor": get_color(value),
                "color": "white"
            }
        } for value in range(0, 101, 5)
    ]
}

columnDefs = [
    {"field": "companyname", 'headerName': 'Company', 'sortable': False},
    {"field": "sedol", "maxWidth": 100, 'headerName': 'SEDOL', 'sortable': False},
    {"field": "sector", 'headerName': 'Sector', 'sortable': False},
    {
        "field": "marketcapusd",
        "headerName": "Market Cap",
        "sortable": True,
        "valueFormatter": {"function": "d3.format('.3s')(params.value).replace('G', 'B')"}
    },
    {"field": "country_exposure_name", "maxWidth": 300, 'headerName': 'Exposure Country', 'sortable': False},
    {
        "field": "country_exposure_revenue",
        'headerName': 'Exposure Revenue', 
        'sortable': False,
        'valueFormatter': {"function": "d3.format('.3s')(params.value).replace('G', 'B')"}
    },
    {
        "field": "country_exposure(pct)",
        'headerName': 'Exposure Percentage',
        'sortable': True,
        'cellStyle': percentage_cell_style,
        'valueFormatter': {'function': 'd3.format(".1f")(params.value) + "%"'}
    },
    {"field": "industry", 'headerName': 'Market Type', 'sortable': False, "valueFormatter": {"function": "params.value ? params.value.title() : '' "}},
]

dropdown_style = {
    'width': '200px',
    'font-family': '"DM Sans", sans-serif',
    'font-size': '15px'
}

label_style = {
    'font-family': '"DM Sans", sans-serif',
    'font-size': '15px',
    'font-weight': '400',
    'color': '#2C3E50',
    'marginBottom': '2px'
}

def create_tab_layout():
    filter_row = dbc.Row([
        dbc.Col([
            dcc.Dropdown(
                id='country-filter',
                options=[{'label': c, 'value': c} for c in countries],
                value=countries[0],
                clearable=False,
                style=dropdown_style
            )
        ], width="auto", className="me-3"),
        dbc.Col([
            dcc.Dropdown(
                id='sector-filter',
                options=[{'label': 'All Sectors', 'value': 'all'}] + [{'label': c, 'value': c} for c in sectors],
                value='all',
                clearable=False,
                style=dropdown_style
            )
        ], width="auto", className="me-3"),
        dbc.Col([
            html.Div(style={'height': '24px'}),
            dbc.Button(
                [html.I(className="fas fa-download me-2"), "Download CSV"],
                id="btn-download-csv",
                color="primary",
                size="sm",
                style={'fontSize': '15px', 'fontFamily': '"DM Sans", sans-serif'}
            ),
            dcc.Download(id="download-dataframe-csv")
        ], width="auto"),
        dbc.Col([
            html.Div(style={'height': '24px'}),
            html.Span(
                "Market Cap Data: (2025-01-01) | Exposure Data: (2024-12-31)",
                style={
                    'fontWeight': 'bold',
                    'fontSize': '16px',
                    'fontFamily': '"DM Sans", sans-serif',
                    'color': '#2C3E50',
                    'marginRight': '20px',
                    'lineHeight': '38px'
                }
            ),
        ], width="auto", className="ms-auto"),
    ], className="mb-3 g-2 align-items-end")

    grid = dag.AgGrid(
        id="selection-checkbox-grid",
        columnDefs=columnDefs,
        rowData=df.to_dict("records"),
        defaultColDef={"flex": 1, "minWidth": 150, "sortable": True, "resizable": True, "filter": True},
        dashGridOptions={
            'headerHeight':50,
            "animateRows": False,
            'pagination':True,
            "paginationPageSize": 20,
            "suppressRowClickSelection": True,
        },
        className="ag-theme-alpine dbc-ag-grid",
        columnSize="sizeToFit",
        style={"height": "800px", "width": "100%", "--ag-header-background-color": '#F0F0F0'},
        dangerously_allow_code=True
    )

    return dbc.Container(
        [
            filter_row,
            grid,
        ],
        className="dbc dbc-ag-grid",
        style={"marginTop": "20px"},
    )

tab_layout = create_tab_layout()
