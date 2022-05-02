import os
import geopandas as gpd
import shutil


def create_directories_only_if_not_exist(directory_path, delete):
    if os.path.exists(directory_path):
        if delete:
            shutil.rmtree(directory_path)
            os.makedirs(directory_path)
    else:
        os.makedirs(directory_path)

def create_countries_directories(countries_gdf_path, database_path):
    countries_gdf = gpd.read_file(countries_gdf_path)
    for countries in countries_gdf.ADM0_NAME:
        country_gdf = countries_gdf[countries_gdf.ADM0_NAME == countries]
        country_path = os.path.join(database_path, countries)
        create_directories_only_if_not_exist(country_path, False)
        country_gdf.to_file(os.path.join(country_path, '{0}.shp'.format(countries)))


