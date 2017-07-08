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


def map_neighborhood(df, city, output_file, output_title):
    """
    Creates a heat map using neighborhood from shape file
    """
    print("Creating heat map ({})".format(output_file))
    # Select city
    if city == "seattle":
        shapepath = "map/seattle/Neighborhoods"
    elif city == "sanfrancisco":
        shapepath = "map/sanfrancisco/Neighborhoods"
    else:
        raise ValueError("unsupported city '{}'".format(city))
    # Read shape files
    with fiona.open(shapepath+".shp") as shapefile:
        x_min, y_min, x_max, y_max = shapefile.bounds
    x_center = 0.5 * (x_min + x_max)
    y_center = 0.5 * (y_min + y_max)
    margin_factor = 0.01
    x_margin = (x_max - x_min) * margin_factor
    y_margin = (y_max - y_min) * margin_factor
    yx_ratio = (y_max - y_min) / (x_max - x_min)
    city_map = Basemap(
        projection='tmerc', ellps='WGS84',
        lon_0 = x_center,
        lat_0 = y_center,
        llcrnrlon = x_min - x_margin,
        llcrnrlat = y_min - y_margin,
        urcrnrlon = x_max + x_margin,
        urcrnrlat = y_max + y_margin,
        resolution='i',
        suppress_ticks=True)
    city_map.readshapefile(shapepath, name="city", drawbounds=False, color='none', zorder=2)
    # Get polygons corresponding to neighborhoods
    df_map = pd.DataFrame({
        'Polygon': [Polygon(hood_points) for hood_points in city_map.city],
    })
    # Global to local coordinates
    mapped_points = [Point(city_map(x, y)) for x, y in zip(df["X"], df["Y"])]
    all_points = MultiPoint(mapped_points)
    hood_polygons = prep(MultiPolygon(list(df_map["Polygon"].values))) # faster computation
    # Put point in their corresponding neighborhood
    city_points = filter(hood_polygons.contains, all_points)
    df_map["Count"] = df_map["Polygon"].apply(count_points_in_polygon, args=(city_points,))
    max_count = max(df_map["Count"].values)
    num_breaks = 8
    breaks = [0.] + [i * max_count / float(num_breaks) for i in range(num_breaks)] + [1e20]
    df_map["Bins"] = df_map["Count"].apply(self_categorize, args=(breaks,))
    # create figure
    figwidth = 14
    fig = plt.figure(figsize=(figwidth, figwidth*yx_ratio))
    ax = fig.add_subplot(111, facecolor='w', frame_on=False)
    cmap = plt.get_cmap('YlOrRd')
    # draw neighborhoods with grey outlines
    df_map['Patches'] = df_map['Polygon'].map(lambda x: PolygonPatch(x, ec='#111111', lw=.8, alpha=1., zorder=4))
    pc = PatchCollection(df_map['Patches'], match_original=True)
    # apply colors
    cmap_list = [cmap(val) for val in (df_map["Bins"].values - df_map["Bins"].values.min())/(
                      df_map["Bins"].values.max()-float(df_map["Bins"].values.min()))]
    pc.set_facecolor(cmap_list)
    ax.add_collection(pc)
    city_map.drawmapboundary(fill_color="#eaf2f8")
    # colored scale
    jenks_labels = [int_with_commas(10*int(int(i * max_count / float(num_breaks))/10)) for i in range(num_breaks)]
    cbar = scale_on_map(cmap, ncolors=len(jenks_labels)+1, labels=jenks_labels, shrink=0.5)
    cbar.ax.tick_params(labelsize=16)
    # title and output
    fig.suptitle(output_title, fontdict={'size':24, 'fontweight':'bold'}, y=0.92)
    plt.savefig(output_file, dpi=100, frameon=False, bbox_inches='tight', pad_inches=0.5, facecolor='#F2F2F2')


_astral = Astral() # outside of function to speed up computation
_astral.solar_depression = 'civil'
def is_at_night(ts, city):
    """ determine if time is 30 min after sunset or 30 before sunset.
    The term 'night time' is defined like this in Common Law.
    """
    if city == "seattle":
        city = "Seattle"
    elif city == "sanfrancisco":
        city = "San Francisco"
    else:
        raise ValueError("unsupported city '{}'".format(city))
    cityinfo = _astral[city]
    dt = ts.to_pydatetime()
    sun = cityinfo.sun(date=dt, local=True)
    sunrise = sun['sunrise']
    sunset = sun['sunset']
    sunrise = sunrise.replace(tzinfo=None)
    sunset = sunset.replace(tzinfo=None)
    return ((sunrise - dt).total_seconds() >= 1800 or (dt - sunset).total_seconds() >= 1800)

