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

from __future__ import print_function
import sys
import numpy as np
import pandas as pd
import matplotlib as mpl
import matplotlib.pyplot as plt
import fiona
import datetime
import locale
from astral import Astral
from mpl_toolkits.basemap import Basemap
from shapely.geometry import Point, Polygon, MultiPoint, MultiPolygon
from shapely.prepared import prep
from matplotlib.collections import PatchCollection
from matplotlib.colors import BoundaryNorm
from matplotlib.cm import ScalarMappable
from descartes import PolygonPatch


"""
Data readers. Convert to a unified format to apply generic tools
created below for data analysis
"""
def parse_csv_seattle(normalize=True):
    print("Reading Seattle CSV...")
    df = pd.read_csv("seattle_incidents_summer_2014.csv",
        header = 0,
        usecols = [2,3,4,5,6,7,8,9,11,12,14,15],
        na_values = ["X"],
        parse_dates = [5,6,7],
        infer_datetime_format = True,
        dtype = { "Offense Code":str,
                  "Offense Code Extension":str,
                  "Offense Type":str,
                  "Summary Offense Code":str,
                  "Summarized Offense Description":str,
                  "Date Reported":str,
                  "Occurred Date or Date Range Start":str,
                  "Occurred Date Range End":str,
                  "District/Sector":str,
                  "Zone/Beat":str,
                  "Longitude":np.float32,
                  "Latitude":np.float32 })
    if normalize:
        df = df[["Summarized Offense Description", "Occurred Date or Date Range Start", "Longitude", "Latitude", "Date Reported", "Occurred Date Range End"]]
        df.columns = ["Cat", "Time", "X", "Y", "TimeRep", "TimeEnd"]
    return df
