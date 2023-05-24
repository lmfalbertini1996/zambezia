# -*- coding: utf-8 -*-
"""
Created on Fri Sep 17
"""

import os
import streamlit as st
import pandas as pd
import plotly.express as px
import matplotlib.pyplot as plt
from streamlit_folium import folium_static
import folium
import geopandas as gpd
from shapely import wkt
import xarray as xr
import rioxarray as rxr
#from osgeo import gdal
from Code.directories_creation import create_directories_only_if_not_exist
import pydeck as pdk
import ast
import numpy as np 
from matplotlib import cm
import random
import time
from folium import Circle
from geopandas.tools import sjoin
import plotly.graph_objects as go
import s3fs
fs = s3fs.S3FileSystem(anon=False)

st.set_page_config(layout="wide")
numerics = ['int16', 'int32', 'int64', 'float16', 'float32', 'float64']



def replace_name(stringa):
    stringa = ''.join( c for c in stringa if c not in '[]""' )
    return stringa

def two_d_mapping(grid,country_level_db_path,country):
    key = 6
    if st.checkbox("Existing National Grid", False, key=key):
        grid = True

    # center on Liberty Bell
    long = file_gdf.geometry.x.mean()
    lat = file_gdf.geometry.y.mean()

    if grid:
        grid_gdf = gpd.read_file(os.path.join(country_level_db_path, country, 'Networks', 'grid.shp'))
        grid_gdf = grid_gdf[grid_gdf.geometry != None]
        grid_gdf = grid_gdf.reset_index()
        if grid_gdf.crs != 'epsg:4326':
            grid_gdf = grid_gdf.to_crs(4326)

    m = folium.Map(location=[lat, long], zoom_start=7, show=True)
    tile = folium.TileLayer(
        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        attr='Esri',
        name='Esri Satellite',
        overlay=False,
        control=True
    ).add_to(m)

    tile = folium.TileLayer(
        tiles='http://mt0.google.com/vt/lyrs=y&hl=en&x={x}&y={y}&z={z}',
        attr='Google',
        name='Google Hybrid',
        overlay=False,
        control=True
    ).add_to(m)

    tile = folium.TileLayer(
        tiles='http://mt0.google.com/vt/lyrs=m&hl=en&x={x}&y={y}&z={z}',
        attr='Google',
        name='Google Maps',
        overlay=False,
        control=True
    ).add_to(m)

    # folium.TileLayer('stamentoner').add_to(m)

    style1 = {'fillColor': '#228B22', 'lineColor': '#228B22'}
    style2 = {'fillColor': '#00FFFFFF', 'lineColor': '#00FFFFFF'}
    style3 = {'fillColor': 'green', 'color': 'green'}
    style4 = {'fillColor': 'red', 'color': 'red'}

    feature_group_1 = folium.FeatureGroup(name='Electrified Clusters', show=True)
    feature_group_2 = folium.FeatureGroup(name='Non Electrified Clusters', show=True)
    # folium_static(m)

    polygons_df = pd.read_csv(os.path.join(run_directory, 'Output', 'Analysis', 'Demographics', 'polygons.csv'))

    polygons_gdf = gpd.GeoDataFrame(polygons_df)
    polygons_gdf['geometry'] = polygons_gdf.polygons.apply(wkt.loads)
    polygons_gdf = polygons_gdf.set_crs(4326)

    a = pd.merge(file_gdf.drop(columns=['polygons']), polygons_gdf, left_index=True, right_index=True)

    if not polygons_gdf[polygons_gdf.night_lights == 0].empty:
        folium.GeoJson(polygons_gdf[polygons_gdf.night_lights == 0].to_json(), name='non-electrified clusters',
                       style_function=lambda x: style4).add_to(feature_group_2)
    if not polygons_gdf[polygons_gdf.night_lights > 0].empty:
        folium.GeoJson(polygons_gdf[polygons_gdf.night_lights > 0].to_json(), name='electrified clusters',
                       style_function=lambda x: style3).add_to(feature_group_1)

    feature_group = folium.FeatureGroup(name='Clusters Info', show=False)

    for index, row in file_gdf.set_index('ID').iterrows():
        # df_ = pd.DataFrame(file_gdf.drop(columns=['geometry','polygons','centroid']).set_index('ID')).iloc(index)

        text = pd.DataFrame(row).drop(['geometry', 'polygons', 'centroid']).to_html()

        iframe = folium.IFrame(text, width=500, height=350)

        popup = folium.Popup(iframe, max_width=500)

        x = row.geometry.x
        y = row.geometry.y

        marker = folium.Marker([y, x], popup=popup,
                               icon=folium.Icon(color='blue', icon='hospital-o', prefix='fa')).add_to(feature_group)

    if 'grid_gdf' in locals():
        feature_group_a = folium.FeatureGroup(name='Grid Path')
        feature_group_b = folium.FeatureGroup(name='Grid Info')

        status_col_name = [x for x in grid_gdf.columns if
                           any(ext in x for ext in ['status', 'Status', 'STATUS'])]

        if len(status_col_name) > 0:
            status_col_name = status_col_name[0]
        else:
            status_col_name = 'no_status_column'

        voltage_col_name = [x for x in grid_gdf.columns if any(ext in x for ext in ['volt', 'Volt', 'VOLT'])]

        if len(voltage_col_name) > 0:
            voltage_col_name = voltage_col_name[0]

        main_attribute = status_col_name
        if main_attribute not in grid_gdf.columns:
            main_attribute = voltage_col_name

        attribute_list = grid_gdf[main_attribute].unique()
        # color_list = [style1, style2,style3, style4]
        color_list = ['green', 'red', 'yellow', 'blue', 'black', 'orange', 'white'][:len(attribute_list)]

        for index, row in grid_gdf.iterrows():
            properties = color_list[attribute_list.tolist().index(row[main_attribute])]
            # print(index, row[main_attribute], properties, '\n_______')
            file = grid_gdf.iloc[[index]].to_json()
            folium.features.Choropleth(geo_data=file, name=index, line_color=properties, line_weight=3).add_to(
                feature_group_a)

        style = {'fillColor': '#00000000', 'color': '#00000000'}
        folium.GeoJson(grid_gdf.to_json(), name='_info', style_function=lambda x: style,
                       tooltip=folium.features.GeoJsonTooltip(fields=list(grid_gdf.columns[:-1]))).add_to(
            feature_group_b)

        feature_group_a.add_to(m)
        feature_group_b.add_to(m)

    feature_group.add_to(m)
    feature_group_1.add_to(m)
    feature_group_2.add_to(m)
    #
    #
    # key = 7
    # if st.checkbox("Zoom On Specific Community", True, key=key):
    #
    #
    #     key = 8
    #     comm = st.selectbox('Select the Community',file_gdf.index)
    #
    #     comm_gdf = file_gdf[file_gdf.Community == comm]
    #
    #     feature_group_3 = folium.FeatureGroup(name=comm, show=True)
    #
    #     new_lat = float(comm_gdf.geometry.y)
    #     new_long = float(comm_gdf.geometry.x)
    #
    #     # add marker
    #     tooltip = comm
    #     folium.Marker(
    #         [new_lat, new_long], popup=comm, tooltip=tooltip
    #     ).add_to(feature_group_3)
    #
    #     m.location = [new_lat, new_long]
    #     m.zoom_start = 15
    #
    #     feature_group_3.add_to(m)

    #
    folium.plugins.Draw(export=True, filename='data.geojson', position='topleft', draw_options=None,
                        edit_options=None).add_to(m)
    folium.plugins.Fullscreen(position='topleft', title='Full Screen', title_cancel='Exit Full Screen',
                              force_separate_button=False).add_to(m)
    folium.plugins.MeasureControl(position='bottomleft', primary_length_unit='meters',
                                  secondary_length_unit='miles',
                                  primary_area_unit='sqmeters', secondary_area_unit='acres').add_to(m)
    folium.LayerControl().add_to(m)

    # Displaying a map

    folium_static(m)


##############################################################################
key = 0
# Block for selecting the run directory based on the case study
working_directory = os.getcwd()
#working_directory = "s3://vania"
database_folder_path = 'Data'  # UI
country_level_db_path = os.path.join(database_folder_path, 'Case_Study', 'Country Level')
        
# old_runs_complete = list(os.listdir(os.path.join(working_directory, 'Runs')))
# #old_runs_complete = [old_runs_complete[5]]
# old_runs = [''.join([i for i in x if not i.isdigit()]) for x in list(os.listdir(os.path.join(working_directory, 'Runs')))]
# #old_runs = [old_runs[5]]
# old_runs_total = list(os.listdir(os.path.join(working_directory, 'Runs')))
#
# run_directory_ID = st.sidebar.selectbox('Select the Case Study', old_runs)
# country = run_directory_ID.split('_')[0]
# run_directory = os.path.join(working_directory, 'Runs', old_runs_complete[old_runs.index(run_directory_ID)])
country = 'Mozambique'
run_directory = os.path.join(working_directory,'Runs','Mozambique_2022_04_27_21_42_15_teresa_first')
is_case_with_names = True

crs_dict = {'Uganda': 21095,
            'Mozambique': 32737,
            'Nigeria': 26392,  # COMMENT (DARLAIN): need to manage how to work on 3 crs in nigeria
            'Sudan': 29636,
            'Rwanda': 32736,
            'Lesotho': 22287,
            'Burkina_Faso': 32630,
            'RDC': 4061,
            'Malawi': 20936,
            'Niger': 26392,
            'Tanzania': 32737,
            'Chad': 32634,
            'Liberia': 32629,
            'South_Sudan': 20136}  # 4251
crs = crs_dict.get(country)

    
# Importing all results to be put in the dashboard
demographic_data = pd.read_csv(os.path.join(run_directory, 'Output', 'Analysis', 'Demographics', 'first_analysis_results_df.csv'), index_col=0)

population_data = pd.read_csv(os.path.join(run_directory, 'Output', 'Analysis', 'Demographics', 'overall_pop_analysis_results_df.csv'), index_col=0)

night_lights_data = pd.read_csv(os.path.join(run_directory, 'Output', 'Analysis', 'Demographics', 'overall_nights_analysis_results_df.csv'), index_col=0)

specific_night_lights_data = pd.read_csv(os.path.join(run_directory, 'Output', 'Analysis', 'Demographics', 'overall_spec_nights_analysis_results_df.csv'), index_col=0)

crops_data = pd.read_csv(os.path.join(run_directory, 'Output', 'Analysis', 'Overall', 'crop_analysis.csv'), index_col=0)

second_level_analysis_data = pd.read_csv(os.path.join(run_directory, 'Output', 'Analysis', 'Overall', 'second_analysis_results_df.csv'), index_col=0)

polygons = pd.read_csv(os.path.join(run_directory, 'Output', 'Analysis', 'Demographics', 'polygons.csv'), index_col=0)

all_clusters = pd.merge(demographic_data, second_level_analysis_data, left_index=True, right_index=True)
all_clusters['geometry'] = all_clusters.centroid.apply(wkt.loads)
all_clusters_gdf = gpd.GeoDataFrame(all_clusters, geometry='geometry')
all_clusters_gdf = all_clusters_gdf.set_crs(crs)
all_clusters_gdf['ID'] = all_clusters_gdf.index
all_clusters_gdf['Community']=all_clusters_gdf['cluster_ID']
if all_clusters_gdf.crs != 'epsg:4326':
    all_clusters_gdf = all_clusters_gdf.to_crs(4326)




# THIS IS DATA FROM VANIA


#THIS IS DATA FROM THE SURVEYS
file_gdf = gpd.read_file(os.path.join(run_directory,'Output','Surveys','Final_surveyed.geojson'))
file_gdf['Name'] = file_gdf['index']
file_gdf = file_gdf.reset_index()
file_gdf = file_gdf.set_crs(crs)

if file_gdf.crs != 'epsg:4326':
    file_gdf = file_gdf.to_crs(4326)

file_gdf['Community'] = file_gdf['cluster_ID']
file_gdf['index'] = file_gdf['cluster_ID']
file_gdf = file_gdf.set_index('index')
file_gdf = file_gdf.sort_values('Community')



##############################################################################

which_modes = ['Entire Area', 'Single Cluster', 'Compare Clusters']
which_mode = st.sidebar.selectbox('Select the Mode', which_modes, index=0)


if which_mode == 'Entire Area':
    "# Project description"
    'The purpose of this tool is to allow for an interactive visualization of the data processed during the surveys, within ' \
    'the project TERESA.'
    # Comparison with all the other communities based on input from user in dropdown menu

    row1_1, row1_2 = st.columns((3,3))


    # 2D MAPPING
    key = 5
    mapping_2d = st.sidebar.selectbox('------ 2D MAPPING ------',[ 'ON','OFF'],key=key, index=0)

    if mapping_2d == 'ON':
        key=1000
        with row1_1:
            color_communities = st.selectbox('------ Coloring of communities ------',
                                             ['Energy requirement per capita', 'Type', 'Uniform'], key=key, index=2)
            long = file_gdf.geometry.centroid.x.mean()
            lat = file_gdf.geometry.centroid.y.mean()
            m = folium.Map(location=[lat, long], zoom_start=10, show=True)
            tile = folium.TileLayer(
                tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
                attr='Esri',
                name='Esri Satellite',
                overlay=False,
                control=True
            ).add_to(m)

            tile = folium.TileLayer(
                tiles='http://mt0.google.com/vt/lyrs=y&hl=en&x={x}&y={y}&z={z}',
                attr='Google',
                name='Google Hybrid',
                overlay=False,
                control=True
            ).add_to(m)

            tile = folium.TileLayer(
                tiles='http://mt0.google.com/vt/lyrs=m&hl=en&x={x}&y={y}&z={z}',
                attr='Google',
                name='Google Maps',
                overlay=False,
                control=True
            ).add_to(m)

            # folium.TileLayer('stamentoner').add_to(m)

            style1 = {'fillColor': '#228B22', 'lineColor': '#228B22'}
            style2 = {'fillColor': '#00FFFFFF', 'lineColor': '#00FFFFFF'}
            style3 = {'fillColor': 'green', 'color': 'green'}
            style4 = {'fillColor': 'red', 'color': 'red'}


            style_low = {'fillColor': 'orange', 'color': 'black'}
            style_med = {'fillColor': 'red', 'color': 'black'}
            style_high = {'fillColor': 'black', 'color': 'black'}

            feature_group_1 = folium.FeatureGroup(name='All surveyed communities', show=True)
            folium.GeoJson(file_gdf.to_json(), name='All surveyed communities',
                           style_function=lambda x: style3).add_to(feature_group_1)
            if color_communities=='Type':
                legend = pd.DataFrame({'Color': ['orange', 'red', 'black'],
                                       'Significance': ['Rural', 'Semi-urban',
                                                        'Urban']})
                st.dataframe(legend)
                feature_group_2 = folium.FeatureGroup(name='Rural', show=True)
                feature_group_3 = folium.FeatureGroup(name='Semi-urban', show=True)
                feature_group_4 = folium.FeatureGroup(name='Urban', show=True)

                folium.GeoJson(file_gdf[file_gdf['type']=='Rural'].to_json(), name='Rural',
                               style_function=lambda x: style_low).add_to(feature_group_2)
                folium.GeoJson(file_gdf[file_gdf['type']=='Suburban'].to_json(), name='Semi-urban',
                               style_function=lambda x: style_med).add_to(feature_group_3)
                folium.GeoJson(file_gdf[file_gdf['type']== 'City'].to_json(),
                               name='Urban',
                               style_function=lambda x: style_high).add_to(feature_group_4)
                feature_group_2.add_to(m)
                feature_group_3.add_to(m)
                feature_group_4.add_to(m)
            elif color_communities=='Energy requirement per capita':
                legend=pd.DataFrame({'Color':['orange','red','black'],'Significance':['Low energy requirement','Medium energy requirement','High energy requirement']})
                st.dataframe(legend)
                feature_group_2 = folium.FeatureGroup(name='Low needs (<600Wh/pp)', show=True)
                feature_group_3 = folium.FeatureGroup(name='Medium needs (600-1500Wh/pp)', show=True)
                feature_group_4 = folium.FeatureGroup(name='Large needs (>1500Wh/pp)', show=True)

                folium.GeoJson(file_gdf[file_gdf['energy_daily_pp Wh']<600].to_json(), name='Low needs (<600Wh/pp)',
                               style_function=lambda x: style_low).add_to(feature_group_2)
                folium.GeoJson(file_gdf[(file_gdf['energy_daily_pp Wh']>600) & (file_gdf['energy_daily_pp Wh']<1500)].to_json(), name='Medium needs (600-1500Wh/pp)',
                               style_function=lambda x: style_med).add_to(feature_group_3)
                folium.GeoJson(file_gdf[file_gdf['energy_daily_pp Wh']>1500].to_json(), name='Large needs (>1500Wh/pp)',
                               style_function=lambda x: style_high).add_to(feature_group_4)
                feature_group_2.add_to(m)
                feature_group_3.add_to(m)
                feature_group_4.add_to(m)

            feature_group = folium.FeatureGroup(name='Surveys Info', show=False)

            for index, row in file_gdf.set_index('Comunidade').iterrows():
                # df_ = pd.DataFrame(file_gdf.drop(columns=['geometry','polygons','centroid']).set_index('ID')).iloc(index)

                text = pd.DataFrame(row).drop(['geometry']).to_html()

                iframe = folium.IFrame(text, width=500, height=350)

                popup = folium.Popup(iframe, max_width=500)

                x = row.geometry.centroid.x
                y = row.geometry.centroid.y

                marker = folium.Marker([y, x], popup=popup,
                                       icon=folium.Icon(color='blue', icon='hospital-o', prefix='fa')).add_to(feature_group)

            feature_group.add_to(m)
            feature_group_1.add_to(m)


            #
            #
            key = 7
            if st.checkbox("Zoom On Specific Community", False, key=key):


                key = 8
                comm = st.selectbox('Select the Community',file_gdf.index,index=0)

                comm_gdf = file_gdf[file_gdf.Community == comm]

                feature_group_3 = folium.FeatureGroup(name=comm, show=True)

                new_lat = float(comm_gdf.geometry.centroid.y)
                new_long = float(comm_gdf.geometry.centroid.x)

                # add marker
                tooltip = comm
                folium.Marker(
                    [new_lat, new_long], popup=comm, tooltip=tooltip
                ).add_to(feature_group_3)

                m.location = [new_lat, new_long]
                m.zoom_start = 30

                feature_group_3.add_to(m)

            #
            folium.plugins.Draw(export=True, filename='data.geojson', position='topleft', draw_options=None,
                                edit_options=None).add_to(m)
            folium.plugins.Fullscreen(position='topleft', title='Full Screen', title_cancel='Exit Full Screen',
                                      force_separate_button=False).add_to(m)
            folium.plugins.MeasureControl(position='bottomleft', primary_length_unit='meters',
                                          secondary_length_unit='miles',
                                          primary_area_unit='sqmeters', secondary_area_unit='acres').add_to(m)
            folium.LayerControl().add_to(m)

            # Displaying a map

            folium_static(m)

    further_plots = st.sidebar.selectbox('------ Plot ------',['OFF','Scatter', 'Histogram','Pie chart'], index=0)

    if further_plots == 'Histogram':
        def plot_hist():
            #key_slider = random.random()
            bin_size = st.slider("Number of Bins", min_value=3,
                                         max_value=15, value=5, key=100)
            if coloring_type == 'Unique':
                plot = px.histogram(x=choose_param_histogram, data_frame=file_gdf, nbins=bin_size,color="Community")
            else:
                plot = px.histogram(x=choose_param_histogram, data_frame=file_gdf, nbins=bin_size)
            st.plotly_chart(plot)
        # choose_param_histogram = st.sidebar.selectbox('Select the parameter to analyze:',
        #                                                        file_gdf.select_dtypes(include=numerics).columns,
        #                                                        key=key,
        #                                                        index=35)

        with row1_2:
            key = 9
            choose_param_histogram = st.selectbox('Select the parameter to analyze:',
                                                  file_gdf.select_dtypes(include=numerics).columns,
                                                  key=key,
                                                  index=35)
            key = 10
            coloring_type = st.selectbox('Select the coloring of the histogram:',
                                                  ['Unique', 'Uniform'],
                                                  key=key,
                                                  index=0)
            plot_hist()
    elif further_plots == 'Scatter':
        with row1_2:
            key=11
            initial_index_x = ['population'==i for i in file_gdf.columns].index(True)
            x_axis = st.selectbox('Select the parameter on the x-axis:',
                                         file_gdf.columns,
                                         key=key,
                                         index=initial_index_x)

            key = 12
            initial_index_y = ['Average_Income' == i for i in file_gdf.columns].index(True)
            y_axis = st.selectbox('Select the parameter on the y-axis:',
                                         file_gdf.columns,
                                         key=key,
                                         index=initial_index_y)
            key = 13
            initial_index_color = ['Ele_access' == i for i in file_gdf.columns].index(True)
            z_axis = st.selectbox('Select the parameter on on which to color:',
                                         file_gdf.columns,
                                         key=key,
                                         index=initial_index_color)

            plot = px.scatter(data_frame=file_gdf, x=x_axis, y=y_axis,
                              color=z_axis,color_continuous_scale='reds', hover_name='Community')
            plot.update_layout({'plot_bgcolor': 'rgba(0, 0, 0, 0)',
            'paper_bgcolor': 'rgba(0, 0, 0, 0)',
            })
            # display the chart
            st.plotly_chart(plot)
    elif further_plots == 'Pie chart':
        with row1_2:
            key = 14
            select_parameter = st.selectbox('Select the type of analysis:',
                                  ['Reasons for lack of electrification','Source of income','Type of connection','Multi-tier framework assessment'
                                   ,'Number of surveys performed in each community'],
                                  key=key,
                                  index=0)
            if select_parameter == 'Reasons for lack of electrification':
                reasons = ['Territorial_lim', 'Political_issues', 'Money','Desinterest', 'Other']
                values = [int(file_gdf[reason].sum()) for reason in reasons]
                plot=go.Figure(data=[go.Pie(labels=reasons,values=values)])
                st.plotly_chart(plot)
            elif select_parameter == 'Source of income':
                sources = ['Agriculture', 'Fishing', 'Teaching', 'Carpentery', 'Other_activities', 'Market']
                values = [int(file_gdf[source].sum()) for source in sources]
                plot = go.Figure(data=[go.Pie(labels=sources, values=values)])
                st.plotly_chart(plot)
            elif select_parameter == 'Type of connection':
                options = ['National Grid','Solar Home Sytem']
                values = [int(file_gdf[option].sum()) for option in options]
                unelectrified_people = int(file_gdf['Total_survey'].sum()) - sum(values)
                options.append('Unelectrified')
                values.append(unelectrified_people)
                plot = go.Figure(data=[go.Pie(labels=options, values=values)])
                st.plotly_chart(plot)
            elif select_parameter == 'Multi-tier framework assessment':
                options = ['Tier 0_Inc', 'Tier 1_Inc', 'Tier 2_Inc', 'Tier 3_Inc','Tier 4_Inc', 'Tier 5_Inc']
                values = [file_gdf[option].sum() for option in options]
                options = [option.split('_')[0] for option in options]
                plot = go.Figure(data=[go.Pie(labels=options, values=values)])
                st.plotly_chart(plot)
            elif select_parameter == 'Number of surveys performed in each community':
                clusters = file_gdf.cluster_ID.to_list()
                values = file_gdf['Total_survey'].to_list()
                clusters = ['ID:'+str(i) for i in clusters]
                plot = go.Figure(data=[go.Pie(labels=clusters, values=values)])
                st.plotly_chart(plot)
    key=15
    detailed_table_survey = st.sidebar.selectbox('------ Detailed Table Surveys------', ['ON', 'OFF'], key=key, index=1)
    if detailed_table_survey == "ON":
        "# Survey outcome"

        survey_outcomes = ['Name','Total_survey',
       'Average_Income', 'Average_Expenditure','Max_Income', 'Min_Income','Average Willingness to pay' ,
       'Ele_access', 'Territorial_lim', 'Political_issues', 'Money',
       'Desinterest', 'Other', 'Agriculture', 'Fishing', 'Teaching',
       'Carpentery', 'Other_activities', 'Market', 'el_work_yes',
       'National Grid', 'Solar Home Sytem', 'Exp ele']
        file_gdf_for_table = file_gdf[survey_outcomes]
        st.dataframe(file_gdf_for_table.set_index('Name'))

    key = 16
    detailed_table_vania = st.sidebar.selectbox('------ Detailed Table Vania------', ['ON', 'OFF'], key=key, index=1)
    #key = 15
    if detailed_table_vania == "ON":
        "# VANIA outcome"

        vania_outcomes = ['Name','type','area','population','Population_2','building_d','Distance from road','road_densi',
       'Distance from grid', 'Distance from city', 'HDI','Average Wealth Index'
       ]
        file_gdf_for_table = file_gdf[vania_outcomes]
        st.dataframe(file_gdf_for_table.set_index('Name'))


# #################################################################################################
elif which_mode == 'Single Cluster':
    # Side bar for selecting the community to be investigated
    select_name = st.sidebar.selectbox('Select the Community',file_gdf.Comunidade, index=0)
    select = int(file_gdf.index[file_gdf['Comunidade']==select_name].values[0])
    #gisele = st.sidebar.selectbox('GISEle',['Yes','No'], index=1)



    old_ID = all_clusters_gdf.loc[all_clusters_gdf['cluster_ID']==select,'ID'].values[0]

    community_path = os.path.join(run_directory, 'Output', 'Clusters','Communities', str(old_ID))
    dashboarding_path = os.path.join(community_path, 'Dashboarding')
    #
    info_gdf = all_clusters_gdf[all_clusters_gdf.cluster_ID == select] # qui
    survey_gdf = file_gdf[file_gdf.cluster_ID==select]
    #
    # crops_files_list = [x for x in os.listdir(community_path) if '.tif' in x and 'spam' in x]
    # pop_list = [x for x in os.listdir(community_path) if '.tif' in x and 'ppp' in x]
    # lights_list = [x for x in os.listdir(community_path) if '.tif' in x and 'Harmonized' in x]
    #
    # raster_list_2d = [x for x in os.listdir(community_path) if '.tif' in x]
    # raster_list_2d = [x for x in raster_list_2d if x not in crops_files_list]
    # raster_list_2d = [x for x in raster_list_2d if x not in pop_list]
    # raster_list_2d = [x for x in raster_list_2d if x not in lights_list]
    #
    # raster_list_3d = raster_list_2d.copy()
    #
    row1_1, row1_2 = st.columns((2,2))

    with row1_1:

        "# Community Description"

        # Block of information about the community - name etc. -
        country = replace_name(str(list(info_gdf.admin_0)))
        energy_trend = night_lights_data[night_lights_data.index == old_ID]
        b = pd.DataFrame(data = energy_trend.transpose().values, index=energy_trend.columns, columns=[old_ID])


        population_trend = population_data[population_data.index == old_ID].transpose().dropna()

        max_pop_worldpop = int(info_gdf.population_worldpop / population_trend[old_ID][-1]) # qui
        max_pop_facebook = int(info_gdf.population_facebook / population_trend[old_ID][-1]) # qui
        a = pd.DataFrame(data = population_trend.values, index=population_trend.index, columns=['WorldPop Estimation'])
        a['Facebook Estimation'] = [int(i) for i in a['WorldPop Estimation']*max_pop_facebook]
        a['WorldPop Estimation'] = [int(i) for i in a['WorldPop Estimation']*max_pop_worldpop]


        'The community under analysis is called %s and is located in %s. More precisely, with respect to \
        the first level administrative division it is in %s, while in %s when \
        considering the second level.'\
            % (survey_gdf.field_1.values[0],
               country[1:-1],
               str(info_gdf.admin_1.values)[2:-2],
               str(info_gdf.admin_2.values)[2:-2])

        if 'No OSM location found' not in str(list(info_gdf.OSM)):
            #info_osm = ast.literal_eval(replace_name(str(info_gdf.OSM.values)))
            info_osm = replace_name(str(info_gdf.OSM.values))
            types = info_osm[0::2]
            names = info_osm[1::2]
            settlements_df = pd.DataFrame({'types': types,
                                            'names': names
                                            })
            towns = settlements_df[settlements_df.types == 'town']
            villages = settlements_df[settlements_df.types == 'village']
            residentials = settlements_df[settlements_df.types == 'residential']

            'In it, there are %i towns (%s), %i villages (%s),\
            and %i residential areas (%s). Moreover, the community is located %s km \
            from the closest important road.'\
                %(len(towns),
                   replace_name(str(list(towns.names))),
                   len(villages),
                   replace_name(str(list(villages.names))),
                   len(residentials),
                   replace_name(str(list(residentials.names))),
                   round(float(info_gdf.distance_road),2)
                   )

        'Based on our open-source databases, we estimated a total of %s buildings, home to between %s and %s people.\
        The community develops itself over approximately %s km2, resulting in a\
        population density of %s people per km2 and a building density of \
        %s buildings per km2. Furthermore, it reached its maximum population in %s, with\
        a growth of %s percent from 2000 to 2020.'\
            % (int(info_gdf.n_buildings),
               min(int(info_gdf.population_worldpop), int(info_gdf.population_facebook)),
               max(int(info_gdf.population_worldpop), int(info_gdf.population_facebook)),
               round(float(info_gdf['area']), 2),
               round(float(info_gdf['population_density']), 2),
               round(float(info_gdf['building_density']), 2)     ,
               int(a.sort_values("WorldPop Estimation").index[-1]),
               round(abs(a["WorldPop Estimation"][-1] - a["WorldPop Estimation"][0]) / a["WorldPop Estimation"][0] * 100.0,2)
               )



        if int(info_gdf.night_lights) == 0:
            if int(b.dropna().sum()) == 0:
                'Moreover, looking at nightlight data, it seems that in 2018 (our most recent data) the village lacked \
                access to electricity as when looking at it from the sky during \
                the night we were not able to see any light. Looking at the progression of satelite immages, it seems that \
                this community never experienced any form of electrification.'

            elif int(b.sum()) > 0:
                'It seems that in 2018 (our most recent data) the village lacked \
                access to electricity as when looking at it from the sky during \
                the night we were not able to see any light. Nonetheless, it seems\
                this community experienced some form of electrification in the years: %s.'\
                    % (b[b[old_ID] > 0].index,
                       )


        elif int(info_gdf.night_lights) > 0:
            'It seems that the village has access to electricity since %s, and \
            still has it today. In particular, the %s percent of the area seems to\
            have lights during nights, ammounting to %s percent of buildings being in \
            potentially electrified zone.'\
                % (b[b[old_ID] > 0].index[0],
                   round(int(info_gdf.night_lights.values), 2),
                   round(int(info_gdf.lights_build.values), 2))
        load_profiles = pd.read_csv(os.path.join(run_directory, 'Output', 'Surveys','energy_households.csv'), index_col=0)
        power = pd.read_csv(os.path.join(run_directory, 'Output', 'Surveys','power_households.csv'), index_col=0)
        "# Survey outcome"

        'Moving on to the survey performed, we surveyed a total of %s people. In terms of income, we found an average of \
         %s mt, with a maximum of %s mt and minimum of %s mt. The village has an electrification rate of %s, with %s \
        being electrified through the national grid and %s with solar home systems. When asking the surveyed people about the reasons \
        for lack of electrification, we found that %s identificated territorial limitations, %s think that political issues are hindering \
        the development of infrastructure, %s blame their economic situation and only %s think that the reason is lack of interest from public bodies. \
        In terms of main source of income we have: %s Agriculture, %s Fishing, %s Teaching, %s Carpenetery, %s Market and %s are other activities.\
        Finally, based on the analysis performed for the village, we estimated %s kWh of electric needs and a peak load of %s kW. For more information,\
        check the load profiles.' \
            % (survey_gdf['Total_survey'].values[0], survey_gdf['Average_Income'].values[0],survey_gdf['Max_Income'].values[0],survey_gdf['Min_Income'].values[0],
               round(survey_gdf['Ele_access'].values[0],4)*100, round(survey_gdf['National Grid'].values[0]/survey_gdf['Total_survey'].values[0],2),
               round(survey_gdf['Solar Home Sytem'].values[0]/survey_gdf['Total_survey'].values[0],2),int(survey_gdf['Territorial_lim'].values[0]),
               int(survey_gdf['Political_issues'].values[0]),int(survey_gdf['Money'].values[0]),int(survey_gdf['Desinterest'].values[0]),
               int(survey_gdf['Agriculture'].values[0]),int(survey_gdf['Fishing'].values[0]),int(survey_gdf['Teaching'].values[0]),int(survey_gdf['Carpentery'].values[0]),
               int(survey_gdf['Market'].values[0]), int(survey_gdf['Other_activities'].values[0]),
               round(load_profiles.loc[select_name,:].sum()/1000,2),
               round(power.loc[select_name].values[0]/1000,2))
    create_directories_only_if_not_exist(dashboarding_path, False)


    # 2D MAPPING
    with row1_2:
        key = 10
        grid = False
        rasters_on = False
        if st.sidebar.checkbox("------ 2D MAPPING ------", True, key=key):
            # Displaying a map
            key = 11

            grid = False
            "# 2D MAP (%s)" % (survey_gdf.Comunidade.values[0])
            #shapefile = st.file_uploader("Upload Shapefile", type="shp")

            m = folium.Map(location=[float(info_gdf.geometry.y), float(info_gdf.geometry.x)], zoom_start=14)
            tile = folium.TileLayer(
                tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
                attr='Esri',
                name='Esri Satellite',
                overlay=False,
                control=True
            ).add_to(m)

            tile = folium.TileLayer(
                tiles='http://mt0.google.com/vt/lyrs=y&hl=en&x={x}&y={y}&z={z}',
                attr='Google',
                name='Google Hybrid',
                overlay=False,
                control=True
            ).add_to(m)

            tile = folium.TileLayer(
                tiles='http://mt0.google.com/vt/lyrs=m&hl=en&x={x}&y={y}&z={z}',
                attr='Google',
                name='Google Maps',
                overlay=False,
                control=True
            ).add_to(m)

            #folium.TileLayer('stamentoner').add_to(m)

            style1 = {'fillColor': '#228B22', 'lineColor': '#228B22'}
            style2 = {'fillColor': '#00FFFFFF', 'lineColor': '#00FFFFFF'}
            style3 = {'fillColor': 'green', 'color': 'green'}
            style4 = {'fillColor': 'red', 'color': 'red'}






            feature_group_1 = folium.FeatureGroup(name=select, show=True)
            feature_group_2 = folium.FeatureGroup(name='Community Boundaries', show=True)



            #polygon_gdf = gpd.read_file(os.path.join(run_directory, 'Output', 'Clusters',
            #                             'Communities', str(renewvia_rev_dict.get(select)), '4326.shp'))

            polygon_gdf = gpd.read_file(os.path.join(community_path, '4326.shp'))
            folium.GeoJson(polygon_gdf.geometry.to_json(), name='community boundaries').add_to(feature_group_2)

            feature_group = folium.FeatureGroup(name='Clusters Info', show=False)

            feature_group_2.add_to(m)
            feature_group_1.add_to(m)

            feature_group.add_to(m)

            for index, row in all_clusters_gdf[all_clusters_gdf.ID == old_ID].iterrows(): # qui
                df_ = pd.DataFrame(file_gdf.drop(columns=['geometry']))
                df_ = df_[df_.index == select]

                text = df_.to_html()

                iframe = folium.IFrame(text, width=500, height=350)

                popup = folium.Popup(iframe, max_width=500)

                x = row.geometry.x
                y = row.geometry.y

                marker = folium.Marker([y, x], popup=popup, icon=folium.Icon(color='blue', icon='hospital-o', prefix='fa')).add_to(feature_group)


                # add marker for Liberty Bell
                tooltip = select
                folium.Marker(
                    [y, x], popup=select, tooltip=tooltip
                ).add_to(feature_group_1)
            folium.plugins.Draw(export=True, filename='data.geojson', position='topleft', draw_options=None,
                                edit_options=None).add_to(m)
            folium.plugins.Fullscreen(position='topleft', title='Full Screen', title_cancel='Exit Full Screen',
                                      force_separate_button=False).add_to(m)
            folium.plugins.MeasureControl(position='bottomleft', primary_length_unit='meters',
                                          secondary_length_unit='miles',
                                          primary_area_unit='sqmeters', secondary_area_unit='acres').add_to(m)
            folium.LayerControl().add_to(m)
            folium_static(m)

    further_analysis = st.sidebar.selectbox('------ Survey Outcomes ------', ['Yes', 'No'], index=1)
    if further_analysis == 'Yes':
        row2_1, row2_2 = st.columns((2,2))
        with row2_1:
            select_parameter_hist = st.selectbox('Select the parameter to visualize:',
                                            ['Reasons for lack of electrification', 'Source of income',
                                             'Type of connection', 'Multi-tier framework assessment'
                                                , 'Number of surveys performed in each community'],
                                            key=key,
                                            index=0)
            if select_parameter_hist == 'Reasons for lack of electrification':
                reasons = ['Territorial_lim', 'Political_issues', 'Money', 'Desinterest', 'Other']
                values = [int(survey_gdf[reason].sum()) for reason in reasons]
                plot = go.Figure(data=[go.Pie(labels=reasons, values=values)])
                st.plotly_chart(plot)
            elif select_parameter_hist == 'Source of income':
                sources = ['Agriculture', 'Fishing', 'Teaching', 'Carpentery', 'Other_activities', 'Market']
                values = [int(survey_gdf[source].sum()) for source in sources]
                plot = go.Figure(data=[go.Pie(labels=sources, values=values)])
                st.plotly_chart(plot)
            elif select_parameter_hist == 'Type of connection':
                options = ['National Grid', 'Solar Home Sytem']
                values = [int(survey_gdf[option].sum()) for option in options]
                unelectrified_people = int(file_gdf['Total_survey'].sum()) - sum(values)
                options.append('Unelectrified')
                values.append(unelectrified_people)
                plot = go.Figure(data=[go.Pie(labels=options, values=values)])
                st.plotly_chart(plot)
            elif select_parameter_hist == 'Multi-tier framework assessment':
                options = ['Tier 0_Inc', 'Tier 1_Inc', 'Tier 2_Inc', 'Tier 3_Inc', 'Tier 4_Inc', 'Tier 5_Inc']
                values = [survey_gdf[option].sum() for option in options]
                options = [option.split('_')[0] for option in options]
                plot = go.Figure(data=[go.Pie(labels=options, values=values)])
                st.plotly_chart(plot)
        with row2_2:
            options = ['Average_Expenditure','Average_Income', 'Average Willingness to pay','Total_survey',
                       'Max_Income', 'Min_Income','Ele_access','Territorial_lim', 'Political_issues', 'Money', 'Desinterest', 'Other']
            key=200
            select_parameter = st.selectbox('Select the survey parameter to compare with other communities:',
                                            options,
                                            key=key,
                                            index=0)

            file_gdf_copy = file_gdf.copy()
            file_gdf_copy['Selected_community'] = '0'
            file_gdf_copy.loc[file_gdf_copy['cluster_ID']==select,'Selected_community'] = '1'

            reasons = ['Territorial_lim', 'Political_issues', 'Money', 'Desinterest', 'Other']
            economic = ['Average_Expenditure','Average_Income', 'Average Willingness to pay','Max_Income', 'Min_Income']
            for i in reasons:
                file_gdf_copy[i] = file_gdf_copy[i]/file_gdf_copy['Total_survey']*100
            file_gdf_copy = file_gdf_copy.sort_values(by=[select_parameter])
            plot = px.bar(file_gdf_copy, x='field_1', y=select_parameter)

            plot.update_traces(marker_color = ['red' if i=='1' else 'blue' for i in file_gdf_copy["Selected_community"]])
            st.plotly_chart(plot)

    load_profiles = st.sidebar.selectbox('------ Daily load profiles ------', ['Yes', 'No'], index=1)
    key = 200
    if load_profiles == 'Yes':
        row3_1, row3_2 = st.columns((1, 1))
        with row3_1:
            files = ['energy_total','energy_shops','energy_schools','energy_households','energy_hospitals']
            colors = ['green','blue','yellow','orange','red']
            plot = go.Figure()
            for i in range(len(files)):
                load_profiles = pd.read_csv(os.path.join(run_directory, 'Output', 'Surveys', files[i]+'.csv'),index_col=0)

                if 'geometry' in load_profiles.columns:
                    load_profiles.drop(columns=['geometry'],inplace=True)

                load_profile = load_profiles.loc[survey_gdf.field_1.values[0],:] #find the correct one

                plot.add_trace(go.Scatter(x=list(load_profile.index),y=list(load_profile.values),mode = 'lines+markers',name=files[i]))
                plot.update_layout(title = "Load profiles",title_x=0.5,
                    title_font_family="Times New Roman",legend_title_font_color="green",
                                   yaxis_title = " Power [Wh/h]",xaxis_title = "hour [h]")
            st.plotly_chart(plot)

            'This load profiles also includes estimates on business and utility such as shops,' \
            'hospitals and schools'


        with row3_2:
            load_profiles = pd.read_csv(os.path.join(run_directory, 'Output', 'Surveys',  'energy_households.csv'),
                                        index_col=0)
            if 'geometry' in load_profiles.columns:
                load_profiles.drop(columns=['geometry'], inplace=True)
            load_profile = load_profiles.loc[survey_gdf.field_1.values[0], :]  # find the correct one
            plot = go.Figure()
            plot.add_trace(go.Scatter(x=list(load_profile.index), y=list(load_profile.values), mode='lines+markers',
                                      name=files[i]))
            plot.update_layout(title="Load profile", title_x=0.5,
                               title_font_family="Times New Roman", legend_title_font_color="green",
                               yaxis_title=" Power [Wh/h]", xaxis_title="hour [h]")
            st.plotly_chart(plot)
            'This is a load profile solely based on the surveys regarding residential energy requirements.'

    off_grid = st.sidebar.selectbox('------ Off-grid solution ------', ['Yes', 'No'], index=1)

    if off_grid=='Yes':
        row3_1, row3_2 = st.columns((1, 1))
        energy_profile = st.sidebar.selectbox('------ Which energy profile? ------', ['Household (surveys)', 'Overall (estimate)'], index=0)
        if energy_profile == 'Household (surveys)':
            microgrid_solutions = pd.read_csv(os.path.join(run_directory, 'Output', 'Surveys', 'microgrid_survey_energy.csv'))
        else:
            microgrid_solutions = pd.read_csv(os.path.join(run_directory, 'Output', 'Surveys', 'microgrid_overall_energy.csv'))

        microgrid_solutions['Load unsupplied [%]'] = 100 - microgrid_solutions['Energy Produced [MWh]']/microgrid_solutions['Energy Demand [MWh]']*100

        microgrid_solutions=microgrid_solutions[['cluster_ID','PV [kW]','Wind [kW]','Diesel [kW]','BESS [kWh]','Inverter [kW]','Investment Cost [kEUR]','Replace Cost [kEUR]','Energy Produced [MWh]','Load unsupplied [%]','CO2 [kg]']]
        microgrid_solution = pd.DataFrame(microgrid_solutions.loc[microgrid_solutions['cluster_ID']==select, :])
        microgrid_solution['cluster_ID'] = survey_gdf.field_1.values[0]
        microgrid_solution.set_index('cluster_ID', inplace=True)

        with row3_1:
            "#     Outcome of the microgrid optimisation"
            st.dataframe(microgrid_solution.transpose())
        with row3_2:
            "#     Generation portfolio"
            reasons = ['PV [kW]', 'Wind [kW]', 'Diesel [kW]']
            values = [int(microgrid_solution[reason].sum()) for reason in reasons]
            plot = go.Figure(data=[go.Pie(labels=reasons, values=values)])
            plot.update_traces(hoverinfo='percent',textinfo='label+value')
            st.plotly_chart(plot)
elif which_mode == 'Compare Clusters':
    row1_1, row1_2 = st.columns((1, 1))
    with row1_1:
        cluster1 = st.selectbox('------ Select cluster? ------',
                                          file_gdf.Comunidade, index=0)
    with row1_2:
        cluster2 = st.selectbox('------ Select cluster? ------',
                                          file_gdf.Comunidade, index=1)


    cluster1_data= file_gdf[file_gdf.Comunidade == cluster1]
    cluster2_data = file_gdf[file_gdf.Comunidade == cluster2]
    select_parameter_hist = st.sidebar.selectbox('Select the parameter to visualize:',
                                         ['Reasons for lack of electrification', 'Source of income',
                                          'Type of connection', 'Multi-tier framework assessment'
                                             , 'Number of surveys performed in each community'],
                                         key=key,
                                         index=0)
    with row1_1:
        '#### In the community %s, a total of %s surveys were performed. Here are the results for %s:'\
            % (cluster1,cluster1_data['Total_survey'].values[0],select_parameter_hist)
        if select_parameter_hist == 'Reasons for lack of electrification':
            reasons = ['Territorial_lim', 'Political_issues', 'Money', 'Desinterest', 'Other']
            values = [int(cluster1_data[reason].sum()) for reason in reasons]
            plot = go.Figure(data=[go.Pie(labels=reasons, values=values)])
            st.plotly_chart(plot)
        elif select_parameter_hist == 'Source of income':
            sources = ['Agriculture', 'Fishing', 'Teaching', 'Carpentery', 'Other_activities', 'Market']
            values = [int(cluster1_data[source].sum()) for source in sources]
            plot = go.Figure(data=[go.Pie(labels=sources, values=values)])
            st.plotly_chart(plot)
        elif select_parameter_hist == 'Type of connection':
            options = ['National Grid', 'Solar Home Sytem']
            values = [int(cluster1_data[option].sum()) for option in options]
            unelectrified_people = int(file_gdf['Total_survey'].sum()) - sum(values)
            options.append('Unelectrified')
            values.append(unelectrified_people)
            plot = go.Figure(data=[go.Pie(labels=options, values=values)])
            st.plotly_chart(plot)
        elif select_parameter_hist == 'Multi-tier framework assessment':
            options = ['Tier 0_Inc', 'Tier 1_Inc', 'Tier 2_Inc', 'Tier 3_Inc', 'Tier 4_Inc', 'Tier 5_Inc']
            values = [cluster1_data[option].sum() for option in options]
            options = [option.split('_')[0] for option in options]
            plot = go.Figure(data=[go.Pie(labels=options, values=values)])
            st.plotly_chart(plot)
    with row1_2:
        '#### In the community %s, a total of %s surveys were performed. Here are the results for %s:' \
            % (cluster2, cluster2_data['Total_survey'].values[0], select_parameter_hist)
        if select_parameter_hist == 'Reasons for lack of electrification':
            reasons = ['Territorial_lim', 'Political_issues', 'Money', 'Desinterest', 'Other']
            values = [int(cluster2_data[reason].sum()) for reason in reasons]
            plot = go.Figure(data=[go.Pie(labels=reasons, values=values)])
            st.plotly_chart(plot)
        elif select_parameter_hist == 'Source of income':
            sources = ['Agriculture', 'Fishing', 'Teaching', 'Carpentery', 'Other_activities', 'Market']
            values = [int(cluster2_data[source].sum()) for source in sources]
            plot = go.Figure(data=[go.Pie(labels=sources, values=values)])
            st.plotly_chart(plot)
        elif select_parameter_hist == 'Type of connection':
            options = ['National Grid', 'Solar Home Sytem']
            values = [int(cluster2_data[option].sum()) for option in options]
            unelectrified_people = int(file_gdf['Total_survey'].sum()) - sum(values)
            options.append('Unelectrified')
            values.append(unelectrified_people)
            plot = go.Figure(data=[go.Pie(labels=options, values=values)])
            st.plotly_chart(plot)
        elif select_parameter_hist == 'Multi-tier framework assessment':
            options = ['Tier 0_Inc', 'Tier 1_Inc', 'Tier 2_Inc', 'Tier 3_Inc', 'Tier 4_Inc', 'Tier 5_Inc']
            values = [cluster2_data[option].sum() for option in options]
            options = [option.split('_')[0] for option in options]
            plot = go.Figure(data=[go.Pie(labels=options, values=values)])
            st.plotly_chart(plot)

    options = ['Average_Expenditure', 'Average_Income', 'Average Willingness to pay', 'Total_survey',
               'Max_Income', 'Min_Income', 'Ele_access', 'Territorial_lim', 'Political_issues', 'Money', 'Desinterest',
               'Other']
    key=201
    compare_bar = st.sidebar.selectbox('Would you like to use a bar plot to see the 2 communities among all others?',
                                    ['No','Yes'],
                                    key=key,
                                    index=0)
    if compare_bar == 'Yes':
        key=202
        select_parameter = st.selectbox('Select the survey parameter to compare with other communities:',
                                        options,
                                        key=key,
                                        index=0)

        file_gdf_copy = file_gdf.copy()
        file_gdf_copy['Selected_community'] = '0'
        file_gdf_copy.loc[file_gdf_copy['Comunidade'] == cluster1, 'Selected_community'] = '1'
        file_gdf_copy.loc[file_gdf_copy['Comunidade'] == cluster2, 'Selected_community'] = '2'
        reasons = ['Territorial_lim', 'Political_issues', 'Money', 'Desinterest', 'Other']
        economic = ['Average_Expenditure', 'Average_Income', 'Average Willingness to pay', 'Max_Income', 'Min_Income']
        for i in reasons:
            file_gdf_copy[i] = file_gdf_copy[i] / file_gdf_copy['Total_survey'] * 100
        file_gdf_copy = file_gdf_copy.sort_values(by=[select_parameter])
        plot = px.bar(file_gdf_copy, x='field_1', y=select_parameter)

        colors=[]
        for i in file_gdf_copy["Selected_community"]:
            if i=='1':
                colors.append('red')
            elif i=='2':
                colors.append('green')
            else:
                colors.append('blue')

        plot.update_traces(marker_color=colors)
        st.plotly_chart(plot)
