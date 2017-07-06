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

def parse_csv_sanfrancisco(normalize=True, remove_non_criminal=False):
    print("Reading San Franciso CSV")
    df = pd.read_csv("sanfrancisco_incidents_summer_2014.csv",
        header = 0,
        usecols = [1,2,3,4,5,6,7,9,10],
        parse_dates = [3,4],
        infer_datetime_format = True,
        dtype={ "Category":str,
                "Offense Code":str,
                "Descript":str,
                "DayofWeek":str,
                "Date":str,
                "Time":str,
                "PdDistrit":str,
                "Resolution":str,
                "X": np.float32,
                "Y": np.float32})
    if normalize:
        def merge_timedate(r):
            d = r["Date"]
            return r["Time"].replace(year=d.year, month=d.month, day=d.day)
        df["Time"] = df.apply(merge_timedate, axis=1)
        df = df[["Category", "Time", "X", "Y", "Resolution"]]
        df.columns = ["Cat", "Time", "X", "Y", "Res"]
    if remove_non_criminal:
        df = df.loc[df["Cat"] != "NON-CRIMINAL"]
    return df


"""
Map utils
"""
def count_points_in_polygon(polygon, points):
    return len(filter(prep(polygon).contains, points))

def self_categorize(entry, breaks):
    for i in range(len(breaks)-1):
        if entry > breaks[i] and entry <= breaks[i+1]:
            return i
    return -1

def scale_on_map(cmap, ncolors, labels, **kwargs):
    norm = BoundaryNorm(range(0, ncolors), cmap.N)
    mappable = ScalarMappable(cmap=cmap, norm=norm)
    mappable.set_array([])
    mappable.set_clim(-0.5, ncolors+0.5)
    colorbar = plt.colorbar(mappable, **kwargs)
    colorbar.set_ticks(np.linspace(0, ncolors, ncolors+1)+0.5)
    colorbar.set_ticklabels(range(0, ncolors))
    colorbar.set_ticklabels(labels)
    return colorbar

def int_with_commas(x):
    if x < 0:
        return '-' + intWithCommas(-x)
    result = ''
    while x >= 1000:
        x, r = divmod(x, 1000)
        result = ",%03d%s" % (r, result)
    return "%d%s" % (x, result)

