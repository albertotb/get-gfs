#!/usr/bin/env python
import datetime as dt
import logging
import warnings

# import cartopy.crs as ccrs
# import matplotlib.pyplot as plt
# import matplotlib.ticker as mticker
# from cartopy.mpl.gridliner import LATITUDE_FORMATTER, LONGITUDE_FORMATTER
import numpy as np
import typer
import xarray as xr
import plotly.graph_objects as go
from plotly.offline import iplot
from mpl_toolkits.basemap import Basemap

GFS_BASE = "https://nomads.ncep.noaa.gov/dods"


def set_logging(loglevel: str):
    numeric_level = getattr(logging, loglevel.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError("Invalid log level: %s" % loglevel)
    logging.basicConfig(level=numeric_level)


def degree2radians(degree):
    # convert degrees to radians
    return degree * np.pi / 180


def mapping_map_to_sphere(lon, lat, radius=1):
    # this function maps the points of coords (lon, lat) to points onto the  sphere of radius radius

    lon = np.array(lon, dtype=np.float64)
    lat = np.array(lat, dtype=np.float64)
    lon = degree2radians(lon)
    lat = degree2radians(lat)
    xs = radius * np.cos(lon) * np.cos(lat)
    ys = radius * np.sin(lon) * np.cos(lat)
    zs = radius * np.sin(lat)
    return xs, ys, zs


m = Basemap()


# Functions converting coastline/country polygons to lon/lat traces
def polygons_to_traces(poly_paths, N_poly):
    """
    pos arg 1. (poly_paths): paths to polygons
    pos arg 2. (N_poly): number of polygon to convert
    """
    # init. plotting list
    lons = []
    lats = []

    for i_poly in range(N_poly):
        poly_path = poly_paths[i_poly]

        # get the Basemap coordinates of each segment
        coords_cc = np.array(
            [
                (vertex[0], vertex[1])
                for (vertex, code) in poly_path.iter_segments(simplify=False)
            ]
        )

        # convert coordinates to lon/lat by 'inverting' the Basemap projection
        lon_cc, lat_cc = m(coords_cc[:, 0], coords_cc[:, 1], inverse=True)

        lats.extend(lat_cc.tolist() + [None])
        lons.extend(lon_cc.tolist() + [None])

    return lons, lats


# Function generating coastline lon/lat
def get_coastline_traces():
    poly_paths = m.drawcoastlines().get_paths()  # coastline polygon paths
    N_poly = 91  # use only the 91st biggest coastlines (i.e. no rivers)
    cc_lons, cc_lats = polygons_to_traces(poly_paths, N_poly)
    return cc_lons, cc_lats


# Function generating country lon/lat
def get_country_traces():
    poly_paths = m.drawcountries().get_paths()  # country polygon paths
    N_poly = len(poly_paths)  # use all countries
    country_lons, country_lats = polygons_to_traces(poly_paths, N_poly)
    return country_lons, country_lats


def plot_sphere(wind: xr.Dataset, fout: str):

    lon, lat = wind["lon"].data, wind["lat"].data
    u, v = wind["ugrd10m"].data, wind["vgrd10m"].data
    wspeed = np.sqrt(u ** 2 + v ** 2) * 1.94384

    # Shift 'lon' from [0,360] to [-180,180]
    tmp_lon = np.array(
        [lon[n] - 360 if l >= 180 else lon[n] for n, l in enumerate(lon)]
    )  # => [0,180]U[-180,2.5]

    (i_east,) = np.where(tmp_lon >= 0)  # indices of east lon
    (i_west,) = np.where(tmp_lon < 0)  # indices of west lon
    lon = np.hstack((tmp_lon[i_west], tmp_lon[i_east]))  # stack the 2 halves

    # Correspondingly, shift the olr array
    wspeed_tmp = np.hstack((wspeed[:, i_west], wspeed[:, i_east]))

    # Get list of of coastline, country, and state lon/lat

    cc_lons, cc_lats = get_coastline_traces()
    country_lons, country_lats = get_country_traces()

    # concatenate the lon/lat for coastlines and country boundaries:
    lons = cc_lons + [None] + country_lons
    lats = cc_lats + [None] + country_lats

    xs, ys, zs = mapping_map_to_sphere(lons, lats, radius=1.01)
    boundaries = dict(
        type="scatter3d",
        x=xs,
        y=ys,
        z=zs,
        mode="lines",
        line=dict(color="black", width=1),
    )

    colorscale = [
        [0.0, "#313695"],
        [0.07692307692307693, "#3a67af"],
        [0.15384615384615385, "#5994c5"],
        [0.23076923076923078, "#84bbd8"],
        [0.3076923076923077, "#afdbea"],
        [0.38461538461538464, "#d8eff5"],
        [0.46153846153846156, "#d6ffe1"],
        [0.5384615384615384, "#fef4ac"],
        [0.6153846153846154, "#fed987"],
        [0.6923076923076923, "#fdb264"],
        [0.7692307692307693, "#f78249"],
        [0.8461538461538461, "#e75435"],
        [0.9230769230769231, "#cc2727"],
        [1.0, "#a50026"],
    ]

    clons = np.array(lon.tolist() + [180], dtype=np.float64)

    clats = np.array(lat, dtype=np.float64)
    clons, clats = np.meshgrid(clons, clats)

    XS, YS, ZS = mapping_map_to_sphere(clons, clats)

    nrows, ncolumns = clons.shape

    OLR = np.zeros(clons.shape, dtype=np.float64)
    OLR[:, : ncolumns - 1] = np.copy(np.array(wspeed_tmp, dtype=np.float64))
    OLR[:, ncolumns - 1] = np.copy(wspeed_tmp[:, 0])

    text = [
        [
            "lon: "
            + "{:.2f}".format(clons[i, j])
            + "<br>lat: "
            + "{:.2f}".format(clats[i, j])
            + "<br>W: "
            + "{:.2f}".format(OLR[i][j])
            for j in range(ncolumns)
        ]
        for i in range(nrows)
    ]

    sphere = dict(
        type="surface",
        x=XS,
        y=YS,
        z=ZS,
        colorscale=colorscale,
        surfacecolor=OLR,
        cmin=-20,
        cmax=20,
        colorbar=dict(thickness=20, len=0.75, ticklen=4, title="W/m²"),
        text=text,
        hoverinfo="text",
    )

    noaxis = dict(
        showbackground=False,
        showgrid=False,
        showline=False,
        showticklabels=False,
        ticks="",
        title="",
        zeroline=False,
    )

    layout3d = dict(
        title="Outgoing Longwave Radiation Anomalies<br>Dec 2017-Jan 2018",
        font=dict(family="Balto", size=14),
        width=800,
        height=800,
        scene=dict(
            xaxis=noaxis,
            yaxis=noaxis,
            zaxis=noaxis,
            aspectratio=dict(x=1, y=1, z=1),
            camera=dict(eye=dict(x=1.15, y=1.15, z=1.15)),
        ),
        paper_bgcolor="rgba(235,235,235, 0.9)",
    )

    # fig = dict(data=[sphere, boundaries], layout=layout3d)
    fig = go.Figure(data=[sphere, boundaries], layout=layout3d)
    fig.write_html(fout)


# def plot_wind_speed_dir(wind: xr.Dataset, fout: str):
#     """Plot wind speed and direction

#     From: https://disc.gsfc.nasa.gov/information/howto?title=How%20to%20calculate%20and%20plot%20wind%20speed%20using%20MERRA-2%20wind%20component%20data%20using%20Python
#     Another example: https://scitools.org.uk/iris/docs/v2.2/examples/Meteorology/wind_speed.html
#     """
#     lon, lat = np.meshgrid(wind["lon"], wind["lat"])
#     u, v = wind["ugrd10m"].data, wind["vgrd10m"].data
#     wspeed = np.sqrt(u ** 2 + v ** 2) * 1.94384

#     # wdir = np.arctan2(v, u)

#     # Set the figure size, projection, and extent
#     fig = plt.figure(figsize=(9, 5))
#     ax = plt.axes(projection=ccrs.PlateCarree())
#     ax.set_extent([-45, -35, 45, 35])
#     ax.coastlines(resolution="50m", linewidth=1)
#     # Add gridlines
#     gl = ax.gridlines(
#         crs=ccrs.PlateCarree(),
#         draw_labels=True,
#         linewidth=1,
#         color="black",
#         linestyle="--",
#     )
#     gl.top_labels = False
#     gl.right_labels = False
#     gl.xlines = True
#     # gl.xlocator = mticker.FixedLocator([-65, -60, -50, -40, -30])
#     # gl.ylocator = mticker.FixedLocator([30, 40, 50, 60])
#     gl.xformatter = LONGITUDE_FORMATTER
#     gl.yformatter = LATITUDE_FORMATTER
#     gl.xlabel_style = {"size": 10, "color": "black"}
#     gl.ylabel_style = {"size": 10, "color": "black"}

#     # Plot windspeed
#     clevs = np.arange(0, 14.5, 1)
#     plt.contourf(lon, lat, wspeed, clevs, transform=ccrs.PlateCarree())
#     plt.title("GFS 10m Wind Speed and Direction", size=16)
#     cb = plt.colorbar(ax=ax, orientation="vertical", pad=0.02, aspect=16, shrink=0.8)
#     cb.set_label("m/s", size=14, rotation=0, labelpad=15)
#     cb.ax.tick_params(labelsize=10)
#     # Overlay wind vectors
#     # qv = plt.quiver(lon, lat, u, v, scale=420, color="k")
#     fig.savefig(fout, format="png", dpi=120)


def get_gfs(
    date: dt.date,
    varlist: list,
    run: int = 0,
    hour: int = None,
    res: str = "0p25",
    step: str = "1hr",
):

    date_str = date.strftime("%Y%m%d")
    url = f"{GFS_BASE}/gfs_{res}_{step}/gfs{date_str}/gfs_{res}_{step}_{run:02d}z"

    logging.info(url)

    with warnings.catch_warnings():
        # xarray/coding/times.py:119: SerializationWarning: Ambiguous reference date string
        warnings.filterwarnings(
            "ignore",
            category=xr.SerializationWarning,
            module=r"xarray",
        )
        with xr.open_dataset(url) as ds:
            # We use "nearest" in case of small precision problems
            if hour is None:
                dataset = ds[varlist]
            else:
                time = dt.time(hour=hour)
                dataset = ds[varlist].sel(
                    time=dt.datetime.combine(date, time), method="nearest"
                )
            dataset.to_netcdf(f"{date_str}_{run:02}_{hour:02}.nc")
            return dataset.load()


def main(date: dt.datetime = None, hour: int = None, run: int = 0, log: str = "info"):

    set_logging(log)

    date = date.date() if date is not None else dt.date.today()

    variables = ["ugrd10m", "vgrd10m"]
    try:
        wind = get_gfs(date, variables, hour=hour, run=run)
    except Exception as err:
        logging.exception(err)
    else:
        # plot_wind_speed_dir(wind, f"{date}_{run:02}_{hour:02}.png")
        # plot_sphere(wind, f"{date}_{run:02}_{hour:02}.html")
        pass


if __name__ == "__main__":
    typer.run(main)
