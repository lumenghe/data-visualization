"""
This script creates a number of figures for crime analytics.

Seatle shape file: https://data.seattle.gov/dataset/Neighborhoods/2mbt-aqqx
San Francisco shape file: https://www.arcgis.com/home/item.html?id=3b2a461c2c7848899b7b4cbfa9ebdb67

A good tutorial for displaying maps: http://beneathdata.com/how-to/visualizing-my-location-history/

In case the shape file is not in the right format, converting
to XSG format can be done with the following code snippet:

import geopandas as gdp
gdf = gpd.GeoDataFrame.from_file("Neighborhoods.shp")
gdf = gdf.to_crs(epsg=4326)
gdf.to_file("Neighborhoods.shp", driver="ESRI Shapefile")
"""
