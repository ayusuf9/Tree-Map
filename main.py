import dash
import dash_bootstrap_components as dbc
#from dash import dcc, html
from dash import html
import os
from pathlib import Path
import pandas as pd
import uvicorn
from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop
from tornado.wsgi import WSGIContainer
from flask import Flask
from components.data_loader import load_exposure_data_s3  #TODO for S3 --> #load_exposure_data_s3 #TODO for local testing --> load_exposure_data
from Callbacks.callbacks import register_callbacks

from layouts import main_layout

app = Flask(__name__) # initiating flask client

DEBUG = True

dashapp = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.FLATLY],
    server=app,
    assets_folder="assets",
    external_scripts=["https://d3js.org/d3.v7.min.js"]  # Include d3 for custom formatting functions in AgGrid
)


# file_path = "data/processed_exposure_data.parquet"
# data = pd.read_parquet(file_path)

#TODO for S3
data = load_exposure_data_s3()

data['Date'] = pd.to_datetime(data['calculation_date'])
data['security_name'] = data['security_name'].astype('category')
data['iso_country_symbol'] = data['iso_country_symbol'].astype('category')
data['market_type'] = data['market_type'].astype('category')
data['sedol'] = data['sedol'].astype('category')
data['security_name'] = data['security_name'].astype(str) + ' (' + data['sedol'].astype(str) + ')'

data['Year'] = data['Date'].dt.year

securities_with_data = data.groupby('security_name')['Year'].nunique().reset_index()
#securities_with_data = securities_with_data[securities_with_data['Year'] >= 7]
securities_with_data = securities_with_data['security_name'].tolist()

data = data[data['security_name'].isin(securities_with_data)]
data['country_exposure_pct'] = data['country_exposure(pct)']
market_types = data['market_type'].unique()
security_types = data['security_name'].unique()
sectors = sorted(data['sector'].unique())
default_sector = sectors[0]
default_market_type = market_types[0]
exposure_types = data['country_exposure_name'].unique()
# print(exposure_types)
default_exposure_to = ['China', 'Hong Kong']
exposure_table = main_layout.prepare_exposure_table(data)  # Keep this call

def get_default_securities(market_type):
    market_defaults = {
        #'Frontier': ['Adams Ltd (fdpCtSc)'],
        'emerging market': ['Lenovo Group (6218089)', 'Infosys (6205122)'],
        'developed market': ['Nvidia (2379504)', 'Qualcomm (2714923)']
    }
    return market_defaults.get(market_type, [])

#'Nvidia (2379504)', 'Qualcomm (2714923)'

default_securities = []
for mt in market_types:
    default_securities.extend(get_default_securities(mt))

# --- End of Data Loading and Preparation ---

dashapp.layout = main_layout.get_page3(
    dashapp,
    data,
    market_types,
    default_market_type,
    sectors,
    default_sector,
    exposure_types,
    default_exposure_to,
    exposure_table,
    default_securities
)

register_callbacks(dashapp)

if __name__ == '__main__':
    settings = dict(
        xheaders={
            "Content-Security-Policy": "frame-ancestors *.capgroup.com/",
            "X-Frame-Options": "ALLOW-FROM *.capgroup.com/"
        }
    )
    http_server = HTTPServer(WSGIContainer(app), **settings)
    http_server.listen(8010)
    print("Tornado server starting on port 8082...")
    IOLoop.instance().start()
