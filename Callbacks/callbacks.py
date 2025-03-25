from dash.dependencies import Input, Output, State
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import os
from dash import no_update
from datetime import datetime
# import dash_core_components as dcc
from dash import dcc
import plotly.express as px
import datetime
import dash
# from components.data_loader import load_exposure_data, load_latest_data
from components.data_loader import load_exposure_data_s3, load_table_data_s3, load_parity_data_s3
from pathlib import Path
from flask_caching import Cache
import time

# Initialize global variables to store data
# This prevents reloading data on every callback
dfb = None
data = None 
parity_data = None
sector_mapping_one = None

def initialize_data():
    """Load data once at application startup"""
    global dfb, data, parity_data, sector_mapping_one
    
    # Only load if not already loaded
    if dfb is None:
        print("Loading table data...")
        start_time = time.time()
        dfb = load_table_data_s3()
        print(f"Table data loaded in {time.time() - start_time:.2f} seconds")
    
    if data is None:
        print("Loading exposure data...")
        start_time = time.time()
        data = load_exposure_data_s3()
        
        # Process data once to avoid processing in every callback
        data['Date'] = pd.to_datetime(data['calculation_date'])
        data['security_name'] = data['security_name'].astype('category')
        data['iso_country_symbol'] = data['iso_country_symbol'].astype('category')
        data['market_type'] = data['market_type'].astype('category')
        data['sedol'] = data['sedol'].astype('category')
        data['security_name'] = data['security_name'].astype(str) + ' (' + data['sedol'].astype(str) + ')'
        data['Year'] = data['Date'].dt.year
        # Get the list of securities that have data
        securities_with_data = data['security_name'].unique()
        data = data[data['security_name'].isin(securities_with_data)]
        data['country_exposure_pct'] = data['country_exposure(pct)']
        print(f"Exposure data loaded and processed in {time.time() - start_time:.2f} seconds")
        
        # Create sector mapping only once
        sector_mapping_one = dict(
            zip(
                data['security_name'].apply(lambda x: x.split(' (')[0]),
                data['sector']
            )
        )
    
    if parity_data is None:
        print("Loading parity data...")
        start_time = time.time()
        parity_data = load_parity_data_s3()
        parity_data['dates'] = pd.to_datetime(parity_data['dates'])
        print(f"Parity data loaded in {time.time() - start_time:.2f} seconds")
        
    return dfb, data, parity_data, sector_mapping_one

# Cache for storing processed data results
table_sectors_cache = {}
table_securities_cache = {}
treemap_data_cache = {}

def get_max_date(fig):
    if not fig.data or len(fig.data) == 0:
        return None
    all_dates = []
    for trace in fig.data:
        if hasattr(trace, 'x') and len(trace.x) > 0:
            for date in trace.x:
                try:
                    if isinstance(date, str):
                        all_dates.append(pd.to_datetime(date))
                    else:
                        all_dates.append(date)
                except:
                    continue
    if all_dates:
        return max(all_dates)
    return None


def get_date_range(fig, days):
    end_date = get_max_date(fig)
    if end_date is None:
        return [None, None]

    min_date = None
    for trace in fig.data:
        if hasattr(trace, 'x') and len(trace.x) > 0:
            try:
                trace_dates = [pd.to_datetime(date) if isinstance(date, str) else date for date in trace.x]
                trace_min = min(trace_dates)
                if min_date is None or trace_min < min_date:
                    min_date = trace_min
            except:
                continue

    if min_date is None:
        start_date = end_date - pd.Timedelta(days=days)
        return [start_date, end_date]

    # Ensure consistent date handling
    if isinstance(end_date, (int, float)):
        end_date = pd.to_datetime(end_date, unit='ms')
    if isinstance(min_date, (int, float)):
        min_date = pd.to_datetime(min_date, unit='ms')

    # Calculate start date based on days parameter
    start_date = max(min_date, end_date - pd.Timedelta(days=days))

    return [start_date, end_date]

# def get_date_range(fig, days):
#     end_date = get_max_date(fig)
#     if end_date is None:
#         return [None, None]
#     min_date = None
#     for trace in fig.data:
#         if hasattr(trace, 'x') and len(trace.x) > 0:
#             try:
#                 trace_min = min(pd.to_datetime(date) if isinstance(date, str) else date for date in trace.x)
#                 if min_date is None or trace_min < min_date:
#                     min_date = trace_min
#             except:
#                 continue
#
#     if min_date is None:
#         return [end_date - pd.Timedelta(days=days), end_date]
#
#     if isinstance(end_date, (int, float)) and isinstance(min_date, (int, float)):
#         start_date = max(min_date, end_date - (days * 24 * 60 * 60 * 1000))
#     else:
#         if isinstance(end_date, (int, float)):
#             end_date = pd.to_datetime(end_date, unit='ms')
#         if isinstance(min_date, (int, float)):
#             min_date = pd.to_datetime(min_date, unit='ms')
#
#         start_date = max(min_date, end_date - pd.Timedelta(days=days))
#
#     return [start_date, end_date]


end_date = datetime.datetime.now()
start_date = end_date - datetime.timedelta(days=3 * 365)

cgs_color_pallet = {
    'sapphire': '#011a2e',
    'ocean': '#008E77',
    'turquoise': '#00AEA9',
}
colors_to_use = [cgs_color_pallet['sapphire'], cgs_color_pallet['ocean']]


def register_callbacks(app):
    # Initialize data when app starts
    global dfb, data, parity_data, sector_mapping_one
    dfb, data, parity_data, sector_mapping_one = initialize_data()
    
    # Set up a Flask-Cache instance for the app if it doesn't have one
    if not hasattr(app, 'cache'):
        cache = Cache(app.server, config={
            'CACHE_TYPE': 'simple',
            'CACHE_DEFAULT_TIMEOUT': 300  # 5 minutes cache
        })
        app.cache = cache
    else:
        cache = app.cache
        
    @app.callback(
        Output("selection-checkbox-grid", "rowData"),
        [
            Input('country-filter', 'value'),
            Input('sector-filter', 'value'),
        ],
        prevent_initial_call=False
    )
    def update_grid(selected_country, selected_sector):
        try:
            # Create a cache key based on filter values
            cache_key = f"grid_{selected_country}_{selected_sector}"
            
            # Check if result is in cache
            if cache_key in app.cache.cache:
                return app.cache.cache[cache_key]
            
            # If not in cache, compute and store
            filtered_df = dfb.copy()
            if selected_country:
                filtered_df = filtered_df[filtered_df['country_exposure_name'] == selected_country]
            if selected_sector and selected_sector != 'all':
                filtered_df = filtered_df[filtered_df['sector'] == selected_sector]
                
            result = filtered_df.to_dict('records')
            app.cache.set(cache_key, result)
            return result
        except Exception as e:
            print(f"Error in update_grid: {str(e)}")
            return dfb.to_dict('records')

    @app.callback(
        Output('exposure-type-dropdown', 'options'),
        Output('exposure-type-dropdown', 'value'),
        [Input('market-type-hidden-input', 'value')],
    )
    def update_country_dropdown(market_type):
        # Now we're only using the hidden input value
        if market_type is None:
            market_type = "Developed Market"

        # countries = data[data['market_type'] == market_type]['country_exposure_name'].unique()
        countries = data['country_exposure_name'].unique()
        options = [{'label': country.title(), 'value': country} for country in countries]
        default_countries = ['Canada', 'Mexico']  # ['China', 'Hong Kong']
        default_value = [c for c in default_countries if c in countries]
        if not default_value:
            default_value = countries[:2].tolist() if len(countries) >= 2 else countries.tolist()
        return options, default_value

    @app.callback(
        Output('sector-dropdown', 'options'),
        Output('sector-dropdown', 'value'),
        [Input('market-type-hidden-input', 'value'),
         Input('exposure-type-dropdown', 'value')]
    )
    def update_sector_dropdown(market_type, countries):
        # Now we're only using the hidden input value
        if market_type is None:
            market_type = "Developed Market"

        if not isinstance(countries, list):
            countries = [countries]

        filtered_securities = data[
            # (data['market_type'] == market_type) &
            data['country_exposure_name'].isin(countries)
        ]['security_name'].unique()

        available_sectors = set()
        for security in filtered_securities:
            company_name = security.split(' (')[0]
            if company_name in sector_mapping_one:
                available_sectors.add(sector_mapping_one[company_name])

        options = [{'label': sector, 'value': sector} for sector in sorted(available_sectors)]
        default_value = list(sorted(available_sectors))[7] if len(available_sectors) > 7 else None
        return options, default_value

    @app.callback(
        [
            Output('securities-dropdown', 'data'),
            Output('securities-dropdown', 'value'),
        ],
        [
            Input('market-type-hidden-input', 'value'),
            Input('exposure-type-dropdown', 'value'),
            Input('sector-dropdown', 'value')
        ],
        [State('securities-dropdown', 'value')]
    )
    def update_securities_dropdown(market_type, countries, sector, current_securities):
        # Use the market-type value directly from the hidden input
        if market_type is None:
            market_type = "Developed Market"
        if countries is None:
            countries = ['China', 'Hong Kong']

        if not isinstance(countries, list):
            countries = [countries]

        filtered_data = data[
            # (data['market_type'] == market_type) &
            data['country_exposure_name'].isin(countries)
        ]

        if sector:
            filtered_data = filtered_data[filtered_data['sector'] == sector]

        securities = filtered_data['security_name'].unique()
        options = [{'value': security, 'label': security} for security in securities]

        if current_securities:
            if isinstance(current_securities, list):
                current_securities = current_securities[:2]
                valid_securities = [s for s in current_securities if s in securities]
                if valid_securities:
                    return options, valid_securities

        if market_type.lower() == "developed market":
            default_value = [s for s in ['Nvidia (2379504)', 'Qualcomm (2714923)'] if s in securities][:2]
        elif market_type.lower() == "emerging market":
            default_value = [s for s in ['Lenovo Group (6218089)', 'Infosys (6205122)'] if s in securities][:2]
        else:
            default_value = securities[:2].tolist() if len(securities) >= 2 else securities.tolist()

        return options, default_value

    @app.callback(
        [
            Output('country-exposure-pct-graph', 'figure'),
            Output('country-exposure-revenue-graph', 'figure'),
            Output('percentage-bubble-graph', 'figure'),
            Output('parity-graph', 'figure'),
            Output('security-alert', 'is_open'),
            Output('security-alert', 'children')
        ],
        [
            Input('market-type-hidden-input', 'value'),
            Input('exposure-type-dropdown', 'value'),
            Input('sector-dropdown', 'value'),
            Input('securities-dropdown', 'value')
        ]
    )
    def update_graphs(market_type, countries, sector, securities):
        # Use the market-type value directly from the hidden input
        if market_type is None:
            market_type = "Developed Market"

        if not securities:
            return no_update, no_update, no_update, no_update, True, "Please select at least one security"
        elif isinstance(securities, list) and len(securities) > 2:
            return no_update, no_update, no_update, no_update, True, "Maximum 2 securities allowed"

        if countries is None:
            countries = ['China', 'Hong Kong']
        elif not isinstance(countries, list):
            countries = [countries]

        filtered_data = data[
            # (data['market_type'] == market_type) &
            (data['country_exposure_name'].isin(countries)) &
            (data['security_name'].isin(securities))
            ]

        if sector:
            filtered_securities = []
            for sec in securities:
                comp_name = sec.split(' (')[0]
                if comp_name in sector_mapping_one and sector_mapping_one[comp_name] == sector:
                    filtered_securities.append(sec)
            filtered_data = filtered_data[filtered_data['security_name'].isin(filtered_securities)]

        filtered_data = (
            filtered_data
            .groupby(['security_name', 'Date'])
            .agg({
                'country_exposure_pct': 'sum',
                # 'consolidated_revenue': 'sum',
                'country_exposure_revenue': 'sum',
                'isd_currency_symbol': 'first'
            })
            .reset_index()
        )

        cg_color_pallet = {
            'dark_sapphire': '#00294B',
            'sapphire': '#005F9E',
            'ocean': '#009CDC',
            'light_ocean': '#7BD0E2',
            'turquoise': '#00AEA9',
            'dark_turquoise_1': '#008E77',
            'dark_turquoise_2': '#004C46',
            'raspberry': '#B42573',
            'dark_raspberry_1': '#762157',
            'dark_raspberry_2': '#532a45',
            'neutral_7': '#554742',
            'neutral_4': '#A39E99',
            'neutral_2': '#D5D0CA',
            'cg_recession': '#f3f3f3'
        }

        color_list = [
            cg_color_pallet['dark_sapphire'],
            cg_color_pallet['raspberry'],
            cg_color_pallet['turquoise'],
            cg_color_pallet['neutral_4'],
            cg_color_pallet['sapphire'],
            cg_color_pallet['light_ocean']
        ]

        ## fixing bubble inconsistency

        all_pcts = []
        for security in securities:
            sec_data = filtered_data[filtered_data['security_name'] == security]
            latest_obs = (sec_data
                          .assign(Year=sec_data['Date'].dt.year)
                          .groupby('Year')
                          .agg({
                'country_exposure_pct': 'last',
                'security_name': 'first'
            })
                          .reset_index())
            all_pcts.extend(latest_obs['country_exposure_pct'].tolist())

        max_pct = max(all_pcts) if all_pcts else 100
        size_max = 90
        global_sizeref = 1.5 * max_pct / (size_max ** 2)

        ## fixing bubble inconsistency

        fig_pct = go.Figure()
        fig_revenue = go.Figure()
        fig_bubble = go.Figure()
        fig_parity = go.Figure()

        if filtered_data.empty:
            return fig_pct, fig_revenue, fig_bubble, True, "No data available for the selected filters."

        if filtered_data.empty or not securities:
            return fig_pct, fig_revenue, True, "No data available for the selected filters."

        overall_pct_min = filtered_data['country_exposure_pct'].min()
        overall_pct_max = filtered_data['country_exposure_pct'].max()
        # overall_revenue_min = filtered_data['consolidated_revenue'].min()
        # overall_revenue_max = filtered_data['consolidated_revenue'].max()

        overall_parity_min = parity_data['x924usc'].min()
        overall_parity_max = parity_data['x924usc'].max()
        overall_revenue_min = filtered_data['country_exposure_revenue'].min()
        overall_revenue_max = filtered_data['country_exposure_revenue'].max()

        pct_padding = (overall_pct_max - overall_pct_min) * 0.40
        parity_padding = (overall_parity_max - overall_parity_min) * 0.40
        revenue_padding = (overall_revenue_max - overall_revenue_min) * 0.40

        pct_range = {
            'min': overall_pct_min - pct_padding,
            'max': overall_pct_max + pct_padding
        }
        revenue_range = {
            'min': max(0, overall_revenue_min - revenue_padding),
            'max': overall_revenue_max + revenue_padding
        }

        parity_range = {
            'min': overall_parity_min - parity_padding,
            'max': overall_parity_max + parity_padding
        }

        date_min = filtered_data['Date'].min()
        date_max = filtered_data['Date'].max()
        default_end = filtered_data['Date'].max()
        default_start = default_end - pd.DateOffset(years=4)

        ## Parity ***

        date_min_parity = parity_data['dates'].min()
        date_max_parity = parity_data['dates'].max()
        default_end_parity = parity_data['dates'].max()
        default_start_parity = default_end_parity - pd.DateOffset(years=4)

        ## Parity ***

        small_offset = 0.13 * (overall_revenue_max - overall_revenue_min)

        fig_pct.add_shape(
            type="line",
            x0=date_min,
            x1=date_max,
            y0=pct_range['max'],
            y1=pct_range['max'],
            yref="y",
            line=dict(color="#7a7c7d", width=5.5),
            layer="below"
        )

        fig_pct.add_shape(
            type="line",
            x0=date_min,
            x1=date_max,
            y0=pct_range['min'],
            y1=pct_range['min'],
            yref="y",
            line=dict(color="#7a7c7d", width=5.5),
            layer="below"
        )

        fig_revenue.add_shape(
            type="line",
            x0=date_min,
            x1=date_max,
            y0=revenue_range['max'] + small_offset,
            y1=revenue_range['max'] + small_offset,
            yref="y2",
            line=dict(color="#7a7c7d", width=4.5),
            layer="below"
        )

        fig_revenue.add_shape(
            type="line",
            x0=date_min,
            x1=date_max,
            y0=revenue_range['min'] - small_offset,
            y1=revenue_range['min'] - small_offset,
            yref="y2",
            line=dict(color="#7a7c7d", width=4.5),
            layer="below"
        )

        fig_parity.add_shape(
            type="line",
            x0=date_min_parity,
            x1=date_max_parity,
            y0=parity_range['max'],
            y1=parity_range['max'],
            yref="y",
            line=dict(color="#7a7c7d", width=5.5),
            layer="below"
        )

        fig_parity.add_shape(
            type="line",
            x0=date_min_parity,
            x1=date_max_parity,
            y0=parity_range['min'],
            y1=parity_range['min'],
            yref="y",
            line=dict(color="#7a7c7d", width=5.5),
            layer="below"
        )

        for i, security in enumerate(securities):
            security_data = filtered_data[filtered_data['security_name'] == security]

            if len(security_data) == 0:
                continue

            def format_revenue_str(value):
                if abs(value) >= 1e9:
                    return f"{value / 1e9:.1f}B"
                elif abs(value) >= 1e6:
                    return f"{value / 1e6:.1f}M"
                else:
                    return f"{value:.0f}"

            security_data['formatted_revenue'] = security_data['country_exposure_revenue'].apply(format_revenue_str)
            # security_data['formatted_consolidated_revenue'] = security_data['consolidated_revenue'].apply(
            #     format_revenue_str)

            line_style_pct = dict(
                width=5,
                color=color_list[i % len(color_list)],
                dash=None
            )
            line_style_revenue = dict(
                width=5,
                color=color_list[i % len(color_list)],
                dash=None
            )

            fig_pct.add_trace(go.Scatter(
                x=security_data['Date'],
                y=security_data['country_exposure_pct'],
                name=f"<b>{security}</b>",
                line=line_style_pct,
                mode='lines',
                yaxis='y2',
                hovertemplate=(
                    "<b>%{fullData.name}</b><br>"
                    "Date: %{x|%Y-%m-%d}<br>"
                    "Exposure: <b>%{y:.1f}%</b><br>"
                    "<extra></extra>"
                )
            ))

            fig_revenue.add_trace(go.Scatter(
                x=security_data['Date'],
                y=security_data['country_exposure_revenue'],  # ['country_exposure_revenue'],
                name=f"<b>{security}</b>",
                line=line_style_revenue,
                mode='lines',
                yaxis='y',
                customdata=np.stack((
                    security_data['formatted_revenue'],
                    security_data['isd_currency_symbol']
                ), axis=-1),
                hovertemplate=(
                    "<b>%{fullData.name}</b><br>"
                    "Date: %{x|%Y-%m-%d}<br>"
                    "Revenue: <b>%{customdata[0]} %{customdata[1]}</b><br>"
                    "<extra></extra>"
                )
            )
            )

            # Inside the for loop where securities are processed
            fig_parity.add_trace(go.Scatter(
                x=parity_data['dates'],
                y=parity_data['x924usc'],
                name="Parity Index",
                line=dict(
                    width=5,
                    color=color_list[i % len(color_list)],
                    dash=None
                ),
                mode='lines',
                yaxis='y',
                hovertemplate=(
                    "<b>Parity Index</b><br>"
                    "Date: %{x|%Y-%m-%d}<br>"
                    # "Value: <b>%{y:.2f}</b><br>"
                    "<extra></extra>"
                )
            ))

            base_layout = dict(
                paper_bgcolor='white',
                plot_bgcolor='white',
                font=dict(family="'DM Sans', sans-serif", size=14),
                hoverlabel=dict(
                    bgcolor="white",
                    font_size=12,
                    font_family="'DM Sans', sans-serif",
                ),
                hovermode="x unified",
                showlegend=True,
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1,
                    font=dict(size=11),
                    itemsizing='constant'
                ),
                margin=dict(t=120, r=70, l=70, b=50, pad=0),
                xaxis=dict(
                    type="date",
                    tickfont=dict(weight='bold'),
                    title_font=dict(weight='bold'),
                    autorange=True,
                    mirror='ticks',
                    showline=False,
                    linewidth=2,
                    linecolor='black',
                    showgrid=False,
                    gridcolor='lightgray',
                    gridwidth=0.5,
                    fixedrange=True,
                    constrain='domain',
                    layer='above traces',

                    #just added to control layout..
                    nticks=6,
                    rangemode='normal',
                    automargin=True,
                    tickmode='auto',
                )
            )

        fig_pct.update_layout(
            base_layout,
            title=dict(
                text="Exposure (Percentage)",
                font=dict(size=21, color="#00294b", weight='bold'),
                x=0.04
            ),
            annotations=[
                dict(
                    text="Data as of: 2024-12-31",
                    font=dict(
                        size=16,
                        color="#5a5a5a",
                        weight='bold'
                    ),
                    x=1,
                    y=1.12,
                    xref="paper",
                    yref="paper",
                    showarrow=False,
                    xanchor="right",
                    yanchor="bottom"
                )],
            yaxis=dict(
                title="Exposure (%)",
                showline=False,
                tickformat=".1f",
                ticksuffix="%",
                anchor='x',
                autorange=True,
                showgrid=False,
                tickfont=dict(weight='bold'),
                title_font=dict(weight='bold'),
                mirror='ticks',
                linewidth=2,
                linecolor='black',
                fixedrange=False
            ),
            yaxis2=dict(
                title="Exposure (%)",
                tickformat=".1f",
                ticksuffix="%",
                gridcolor='lightgray',
                gridwidth=0.5,
                autorange=True,
                zeroline=False,
                tickfont=dict(weight='bold'),
                title_font=dict(weight='bold'),
                mirror='ticks',
                showline=False,
                linewidth=2,
                linecolor='black',
                anchor='x',
                overlaying='y',
                side='right',
                position=0,
                fixedrange=False,
                layer='above traces',
                matches='y'
            )
        )

        fig_revenue.update_layout(
            base_layout,
            title=dict(
                text="Country Exposure Revenue",
                font=dict(size=24, color="#00294b", weight='bold'),
                x=0.04
            ),
            annotations=[
                dict(
                    text="Data as of: 2024-12-31",
                    font=dict(
                        size=16,
                        color="#5a5a5a",
                        weight='bold'
                    ),
                    x=1,
                    y=1.12,
                    xref="paper",
                    yref="paper",
                    showarrow=False,
                    xanchor="right",
                    yanchor="bottom"
                )],
            yaxis=dict(
                title="Revenue",
                mirror='ticks',
                showgrid=False,
                tickfont=dict(weight='bold'),
                title_font=dict(weight='bold'),
                anchor='x',
                showline=False,
                linewidth=2,
                linecolor='black',
                autorange=True,
                fixedrange=False
            ),
            yaxis2=dict(
                title="Revenue",
                gridcolor='lightgray',
                gridwidth=0.5,
                autorange=True,
                zeroline=False,
                tickfont=dict(weight='bold'),
                title_font=dict(weight='bold'),
                mirror='ticks',
                showline=False,
                linewidth=2,
                linecolor='black',
                anchor='x',
                overlaying='y',
                side='right',
                position=0,
                fixedrange=False,
                layer='above traces',
                matches='y'
            )
        )

        fig_parity.update_layout(
            base_layout,
            title=dict(
                text="China: Central Parity Rate: United States (Yuan/US$)",
                font=dict(size=24, color="#00294b", weight='bold'),
                x=0.04
            ),
            showlegend=False,
            annotations=[
                dict(
                    text="Data as of: 2025-02-26",
                    font=dict(
                        size=16,
                        color="#5a5a5a",
                        weight='bold'
                    ),
                    x=1,
                    y=1.12,
                    xref="paper",
                    yref="paper",
                    showarrow=False,
                    xanchor="right",
                    yanchor="bottom"
                )
            ],
            yaxis=dict(
                title="Index Value",
                mirror='ticks',
                showgrid=True,
                tickfont=dict(weight='bold'),
                title_font=dict(weight='bold'),
                anchor='x',
                showline=False,
                linewidth=2,
                linecolor='black',
                autorange=True,
                fixedrange=False
            ),
            yaxis2=dict(
                title="Index Value",
                gridcolor='lightgray',
                gridwidth=0.5,
                autorange=True,
                zeroline=False,
                tickfont=dict(weight='bold'),
                title_font=dict(weight='bold'),
                mirror='ticks',
                showline=False,
                linewidth=2,
                linecolor='black',
                anchor='x',
                overlaying='y',
                side='right',
                position=0,
                fixedrange=False,
                layer='above traces',
                matches='y'
            )
        )

        fig_bubble.data = []

        for i, security in enumerate(securities):
            sec_data = filtered_data[filtered_data['security_name'] == security]
            latest_obs = (sec_data
                          .assign(Year=sec_data['Date'].dt.year)
                          .groupby('Year')
                          .agg({
                'country_exposure_pct': 'last',
                'security_name': 'first'
            })
                          .reset_index())

            fig_bubble.add_trace(
                go.Scatter(
                    x=latest_obs['Year'],
                    y=latest_obs['country_exposure_pct'],
                    name=security.split(' (')[0],
                    mode='markers+text',
                    marker=dict(
                        size=latest_obs['country_exposure_pct'],
                        color=color_list[i % len(color_list)],
                        sizemode='area',
                        sizeref=global_sizeref,  # Use the global sizeref here
                        sizemin=4
                    ),
                    text=latest_obs['country_exposure_pct'].round(2).astype(str) + "%",  # round(0).
                    textposition='middle center',
                    textfont=dict(
                        size=11,
                        color='white',
                        family="'DM Sans', sans-serif",
                        weight='bold'
                    ),
                    hovertemplate=(
                            "<b>%{fullData.name}</b><br>" +
                            "Year: %{x}<br>" +
                            "Exposure: %{y:.2f}%<br>" +
                            "<extra></extra>"
                    )
                )
            )

        admin_periods = [
            {
                "name": "Obama (2014-2016)",
                "subtitle": "Engagement & Competition",
                "policy": "Trade growth, selective tech restrictions, TPP negotiations, rising geopolitical tensions.",
                "from": 2014,
                "to": 2016,
                "color": "rgba(0, 112, 192, 0.15)"
            },
            {
                "name": "Trump (2017-2020)",
                "subtitle": "Trade War & Tech Decoupling",
                "policy": "Tariffs, supply chain disruptions, Huawei ban, financial scrutiny, escalating tensions.",
                "from": 2017,
                "to": 2020,
                "color": "rgba(192, 0, 0, 0.15)"
            },
            {
                "name": "Biden (2021-2023)",
                "subtitle": "Strategic Competition & De-risking",
                "policy": "Chip export controls, supply chain shifts, IRA subsidies, selective engagement, capital market stabilization.",
                "from": 2021,
                "to": 2023,
                "color": "rgba(50, 205, 50, 0.15)"  # greenish
            },
            {
                "name": "Biden (2024-Present)",
                "subtitle": "Managed Competition & Protectionism",
                "policy": "Continued strategic competition with targeted protectionist measures.",
                "from": 2024,
                "to": 2025,  # Assuming current year is 2025 as per your date
                "color": "rgba(128, 0, 128, 0.15)"
            }
        ]
        # Add shaded regions to the bubble chart
        for period in admin_periods:
            # Add shaded background
            fig_bubble.add_shape(
                type="rect",
                x0=period["from"] - 0.5,  # Adjust to cover the full year
                x1=period["to"] + 0.5,
                y0=0,  # Start from bottom of chart
                y1=1,  # Go to top of chart
                yref="paper",  # Use paper coordinates for y
                fillcolor=period["color"],
                opacity=0.8,
                layer="below",
                line_width=0,
            )

        # Add administration name at the top
        fig_bubble.add_annotation(
            x=(period["from"] + period["to"]) / 2,
            y=0.95,  # Position near top
            yref="paper",
            text=f"<b>{period['name']}</b>",
            showarrow=False,
            font=dict(size=12, color="black"),
            bgcolor="rgba(255, 255, 255, 0.7)",
            bordercolor="black",
            borderwidth=1,
            borderpad=4,
            opacity=0.9
        )

        fig_bubble.add_trace(
            go.Scatter(
                x=[(period["from"] + period["to"]) / 2],
                y=[0],
                mode="markers",
                marker=dict(size=0, opacity=0),  # Invisible marker
                name=period["name"],
                hoverinfo="text",
                hovertext=f"<b>{period['name']}</b><br>{period['subtitle']}<br><br>{period['policy']}",
                showlegend=False
            )
        )

        # Add administration name
        fig_bubble.add_annotation(
            x=(period["from"] + period["to"]) / 2,
            y=0.95,  # Position near top
            yref="paper",
            text=f"<b>{period['name']}</b>",
            showarrow=False,
            font=dict(size=12, color="black"),
            bgcolor="rgba(255, 255, 255, 0.7)",
            bordercolor="black",
            borderwidth=1,
            borderpad=4,
            opacity=0.9
        )

        # Add policy description
        fig_bubble.add_annotation(
            x=(period["from"] + period["to"]) / 2,
            y=0.05,  # Position near bottom
            yref="paper",
            text=f"<i>{period['subtitle']}</i>",
            showarrow=False,
            font=dict(size=10, color="black"),
            bgcolor="rgba(255, 255, 255, 0.7)",
            bordercolor="black",
            borderwidth=1,
            borderpad=4,
            opacity=0.9
        )

        fig_bubble.update_layout(
            title=dict(
                text="Country Exposure (%)",
                font=dict(size=23, color="#00294b", family="'DM Sans', sans-serif", weight='bold'),
                x=0.04,
                y=0.91
            ),
            paper_bgcolor='white',
            plot_bgcolor='white',
            font=dict(family="'DM Sans', sans-serif", size=14),
            hoverlabel=dict(
                bgcolor="white",
                font_size=12,
                font_family="'DM Sans', sans-serif"
            ),
            annotations=[
                dict(
                    text="Data as of: 2024-12-31",
                    font=dict(
                        size=16,
                        color="#5a5a5a",
                        weight='bold'
                    ),
                    x=1,
                    y=1.09,
                    xref="paper",
                    yref="paper",
                    showarrow=False,
                    xanchor="right",
                    yanchor="bottom"
                ),
            ],
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1,
                font=dict(size=14, weight='bold'),
                itemsizing='constant',
                title=None,
                bgcolor='rgba(255, 255, 255, 0.8)'
            ),
            height=600,
            margin=dict(l=80, r=80, t=100, b=40),
            autosize=True,
            uniformtext=dict(
                mode='hide',
                minsize=4
            ),
            hovermode="closest"
        )
        fig_bubble.update_xaxes(
            ticks='outside',
            tickwidth=2,
            linecolor='grey',
            linewidth=4.5,
            mirror=True,
            title="Year",
            showgrid=False,
            tickfont=dict(weight='bold', size=15),
            title_font=dict(weight='bold', size=15),
            # Set fixed range to ensure all periods are visible
            range=[2013.5, 2025.5]
        )

        fig_bubble.update_layout(
            yaxis2=dict(
                title="Exposure (%)",
                tickformat=".1f",
                ticksuffix="%",
                gridcolor='rgba(128, 128, 128, 0.2)',
                zeroline=False,
                tickfont=dict(weight='bold', size=15),
                title_font=dict(weight='bold', size=15),
                mirror=False,
                showline=True,
                linewidth=3,
                linecolor='grey',
                anchor='x',
                overlaying='y',
                side='right',
                position=1,
                fixedrange=False,
                layer='above traces',
                matches='y',
                showticklabels=True,  # Force tick labels to show
                ticklabelposition='outside'  # Place tick labels outside the plot area
            )
        )

        fig_bubble.update_xaxes(
            ticks='outside',
            tickwidth=2,
            linecolor='grey',
            linewidth=4.5,
            mirror=True,
            title="",
            showgrid=False,
            tickfont=dict(weight='bold', size=15),
            title_font=dict(weight='bold', size=15),
        )

        fig_bubble.update_yaxes(
            title="Exposure (%)",
            ticks='outside',
            tickwidth=2,
            tickformat=".1f",
            ticksuffix="%",
            linecolor='grey',
            linewidth=3,
            showline=False,
            tickfont=dict(weight='bold', size=15),
            title_font=dict(weight='bold', size=15),
            mirror=True,
            showgrid=True,
            gridcolor='rgba(128, 128, 128, 0.2)',
            zeroline=False,
            title_standoff=20,
            rangemode='nonnegative',
            automargin=True
        )

        fig_parity.update_yaxes(
            title="Index Value",
            ticks='outside',
            tickwidth=2,
            linecolor='grey',
            linewidth=3,
            showline=False,
            tickfont=dict(weight='bold', size=15),
            title_font=dict(weight='bold', size=15),
            mirror=True,
            showgrid=True,  # Explicitly set to True
            gridcolor='rgba(128, 128, 128, 0.2)',
            zeroline=False,
            title_standoff=20,
            automargin=True
        )

        for fig in [fig_pct, fig_revenue]:
            max_fig_date = get_max_date(fig)
            if max_fig_date is None:
                continue
            fig.update_layout(
                updatemenus=[
                    go.layout.Updatemenu(
                        type="buttons",
                        showactive=True,
                        active=2,
                        direction='right',
                        x=0,
                        xanchor='left',
                        y=1.10,
                        yanchor='top',
                        buttons=[
                            # dict(
                            #     label="2YR",
                            #     method="relayout",
                            #     args=[{"xaxis.range": get_date_range(fig, 365 * 2)}],
                            # ),
                            # dict(
                            #     label="4YR",
                            #     method="relayout",
                            #     args=[{"xaxis.range": get_date_range(fig, 365 * 4)}],
                            # ),
                            dict(
                                label="Max",
                                method="relayout",
                                args=[{"xaxis.autorange": True}],
                            ),
                        ],
                        font=dict(
                            family="'DM Sans', sans-serif",
                            size=9
                        ),
                    )
                ]
            )

            date_range = get_date_range(fig, 365 * 2)
            if date_range[0] is not None and date_range[1] is not None:
                fig.update_xaxes(range=date_range)

            fig.update_xaxes(range=date_range)

        return fig_pct, fig_revenue, fig_bubble, fig_parity, False, ""

    @app.callback(
        Output('download-csv', 'data'),
        Input('download-csv-button', 'n_clicks'),
        [State('market-type-hidden-input', 'value'),
         State('securities-dropdown', 'value')],
        prevent_initial_call=True
    )
    def download_csv(n_clicks, market_type, securities):
        if n_clicks is None or not securities:
            return no_update

        # Use the market-type value directly from the hidden input
        if market_type is None:
            market_type = "Developed Market"

        # Handle single security selection
        if not isinstance(securities, list):
            securities = [securities]

        filtered_data = data[
            (data['market_type'] == market_type) &
            (data['security_name'].isin(securities))
            ]

        if filtered_data.empty:
            return no_update

        return dict(
            content=filtered_data.to_csv(index=False),
            filename=f"exposure_data_{datetime.datetime.now().strftime('%Y%m%d')}.csv",
            type='text/csv'
        )

    @app.callback(
        Output("download-dataframe-csv", "data"),
        Input("btn-download-csv", "n_clicks"),
        [
            State("country-filter", "value"),
            State("sector-filter", "value"),
            State("selection-checkbox-grid", "rowData")
        ],
        prevent_initial_call=True
    )
    def download_csv(n_clicks, selected_country, selected_sector, grid_data):
        # Convert grid data back to DataFrame
        filtered_df = pd.DataFrame(grid_data)

        # Apply additional filters from dropdowns
        if selected_country:
            filtered_df = filtered_df[filtered_df['country_exposure_name'] == selected_country]
        if selected_sector and selected_sector != 'all':
            filtered_df = filtered_df[filtered_df['sector'] == selected_sector]

        # Convert SEDOL to string to preserve leading zeros
        filtered_df['sedol'] = filtered_df['sedol'].astype(str).str.zfill(7)

        # Format market cap and revenue columns
        numeric_cols = ['marketcapusd', 'country_exposure_revenue']
        filtered_df[numeric_cols] = filtered_df[numeric_cols].apply(pd.to_numeric, errors='coerce')

        return dcc.send_data_frame(
            filtered_df.to_csv,
            filename=f"exposure_data_{pd.Timestamp.now().strftime('%Y%m%d')}.csv",
            type="text/csv", index=False
        )

    # Callback to populate the sector dropdown on Country page
    @app.callback(
        Output('country-sector-dropdown', 'options'),
        Output('country-sector-dropdown', 'value'),
        Input('url', 'pathname')
    )
    def update_country_sectors(pathname):
        if pathname != '/country':
            return no_update, no_update
        
        # Use cached data if available
        if 'sectors' in table_sectors_cache:
            sectors = table_sectors_cache['sectors']
            options = table_sectors_cache['options']
        else:
            # Get unique sectors from the data
            start_time = time.time()
            sectors = sorted(data['sector'].unique())
            options = [{'label': sector, 'value': sector} for sector in sectors]
            
            # Cache the result
            table_sectors_cache['sectors'] = sectors
            table_sectors_cache['options'] = options
            print(f"Sectors computed in {time.time() - start_time:.2f} seconds")
        
        # Set the default value to the first sector
        default_value = sectors[0] if sectors else None
        
        return options, default_value
    
    # Callback to populate the security dropdown based on selected sector
    @app.callback(
        Output('country-security-dropdown', 'options'),
        Output('country-security-dropdown', 'value'),
        Input('country-sector-dropdown', 'value'),
        State('url', 'pathname')
    )
    def update_country_securities(selected_sector, pathname):
        if pathname != '/country' or not selected_sector:
            return no_update, no_update
        
        # Use cached data if available
        cache_key = f"securities_{selected_sector}"
        if cache_key in table_securities_cache:
            options = table_securities_cache[cache_key]['options']
            filtered_securities = table_securities_cache[cache_key]['securities']
        else:
            # Filter securities by selected sector
            start_time = time.time()
            filtered_securities = data[data['sector'] == selected_sector]['security_name'].unique()
            options = [{'label': security, 'value': security} for security in filtered_securities]
            
            # Cache the result
            table_securities_cache[cache_key] = {
                'options': options,
                'securities': filtered_securities
            }
            print(f"Securities for {selected_sector} computed in {time.time() - start_time:.2f} seconds")
        
        # Set the default value to the first security
        default_value = filtered_securities[0] if len(filtered_securities) > 0 else None
        
        return options, default_value
    
    # Callback to generate the treemap visualization based on selected security
    @app.callback(
        Output('country-treemap', 'figure'),
        Output('country-exposure-table', 'rowData'),
        Input('country-security-dropdown', 'value'),
        State('url', 'pathname')
    )
    def update_treemap(selected_security, pathname):
        if pathname != '/country' or not selected_security:
            # Return empty figure if no security is selected
            return {}, []
        
        # Use cached data if available
        cache_key = f"treemap_{selected_security}"
        if cache_key in treemap_data_cache:
            return treemap_data_cache[cache_key]['figure'], treemap_data_cache[cache_key]['table_rows']
        
        start_time = time.time()
        
        # Filter data for the selected security
        security_data = data[data['security_name'] == selected_security]
        
        if security_data.empty:
            # Return an informative figure if no data is found
            fig = go.Figure()
            fig.add_annotation(
                text="No data available for this security",
                font=dict(size=20, color="#00294b"),
                showarrow=False,
                xref="paper", yref="paper",
                x=0.5, y=0.5
            )
            fig.update_layout(
                paper_bgcolor='white',
                plot_bgcolor='white',
                height=600
            )
            return fig, []
        
        # Get the latest date for the selected security
        latest_date = security_data['Date'].max()
        latest_data = security_data[security_data['Date'] == latest_date]
        
        # Filter out "Domestic Exposure" and "International Exposure"
        filtered_data = latest_data[~latest_data['country_exposure_name'].isin(['Domestic Exposure', 'International Exposure'])]
        
        # Prepare table data (for all countries including domestic/international)
        table_data = latest_data[['country_exposure_name', 'country_exposure_pct', 'country_exposure_revenue']].copy()
        
        # Format the revenue values
        def format_revenue(value):
            if abs(value) >= 1e9:
                return f"${value/1e9:.2f}B"
            elif abs(value) >= 1e6:
                return f"${value/1e6:.2f}M"
            else:
                return f"${value/1e3:.2f}K"
        
        table_data['revenue'] = table_data['country_exposure_revenue'].apply(format_revenue)
        table_data['exposure'] = table_data['country_exposure_pct'].round(2).astype(str) + "%"
        
        # Prepare table rows for AG Grid
        table_rows = table_data.sort_values('country_exposure_pct', ascending=False).rename(
            columns={
                'country_exposure_name': 'Country',
                'exposure': 'Exposure (%)',
                'revenue': 'Revenue'
            }
        )[['Country', 'Exposure (%)', 'Revenue']].to_dict('records')
        
        # Using the filtered data (without domestic/international) for the treemap
        country_exposure = filtered_data[['country_exposure_name', 'country_exposure_pct']].copy()
        
        # Check if all exposure values are zero
        if country_exposure.empty or country_exposure['country_exposure_pct'].sum() == 0:
            fig = go.Figure()
            fig.add_annotation(
                text=f"No country exposure data for {selected_security.split(' (')[0]}",
                font=dict(size=20, color="#00294b"),
                showarrow=False,
                xref="paper", yref="paper",
                x=0.5, y=0.5
            )
            fig.update_layout(
                paper_bgcolor='white',
                plot_bgcolor='white',
                height=600
            )
            result = {'figure': fig, 'table_rows': table_rows}
            treemap_data_cache[cache_key] = result
            print(f"Treemap for {selected_security} computed in {time.time() - start_time:.2f} seconds")
            return fig, table_rows
        
        country_exposure = country_exposure.sort_values('country_exposure_pct', ascending=False)
        
        # Create the treemap figure
        try:
            fig = px.treemap(
                country_exposure,
                path=[px.Constant("All Countries"), 'country_exposure_name'],
                values='country_exposure_pct',
                color='country_exposure_pct',
                color_continuous_scale='RdBu',
                color_continuous_midpoint=np.median(country_exposure['country_exposure_pct']),
                hover_data={'country_exposure_pct': ':.2f%'},
            )
            
            # Security name without SEDOL for title
            security_name = selected_security.split(' (')[0] if ' (' in selected_security else selected_security
            
            # Get the formatted date for display
            date_str = latest_date.strftime('%Y-%m-%d')
            
            # Update layout
            fig.update_layout(
                title=dict(
                    text=f"Country Exposure for {security_name} (as of {date_str})",
                    font=dict(size=24, color="#00294b", weight='bold'),
                    x=0.5,
                    xanchor='center'
                ),
                margin=dict(t=50, l=25, r=25, b=25),
                paper_bgcolor='white',
                plot_bgcolor='white',
                font=dict(family="'DM Sans', sans-serif", size=14),
                coloraxis_colorbar=dict(
                    title="Exposure %",
                    tickformat='.2f%',
                    len=0.6,
                    thickness=20,
                    xanchor='left',
                    x=1.05
                )
            )
            
            # Update hover template to show percentage
            fig.update_traces(
                hovertemplate='<b>%{label}</b><br>Exposure: %{value:.2f}%<extra></extra>',
                texttemplate='%{label}<br>%{value:.2f}%'
            )
            
            # Cache the result
            result = {'figure': fig, 'table_rows': table_rows}
            treemap_data_cache[cache_key] = result
            print(f"Treemap for {selected_security} computed in {time.time() - start_time:.2f} seconds")
            
            return fig, table_rows
            
        except Exception as e:
            # Handle any errors during treemap creation
            print(f"Error creating treemap: {str(e)}")
            fig = go.Figure()
            fig.add_annotation(
                text=f"Error creating visualization: {str(e)}",
                font=dict(size=16, color="#00294b"),
                showarrow=False,
                xref="paper", yref="paper",
                x=0.5, y=0.5
            )
            fig.update_layout(
                paper_bgcolor='white',
                plot_bgcolor='white',
                height=600
            )
            return fig, table_rows
