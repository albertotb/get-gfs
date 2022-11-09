import cartopy.crs as ccrs
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import xarray as xr
from cartopy.mpl.gridliner import LATITUDE_FORMATTER, LONGITUDE_FORMATTER
import logging

def set_logging(loglevel: str):
    numeric_level = getattr(logging, loglevel.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError("Invalid log level: %s" % loglevel)
    logging.basicConfig(level=numeric_level)


def degree2radians(degree):
    # convert degrees to radians
    return degree * np.pi / 180


def plot_wind_speed_dir(wind: xr.Dataset, fout: str):
    """Plot wind speed and direction

    From: https://disc.gsfc.nasa.gov/information/howto?title=How%20to%20calculate%20and%20plot%20wind%20speed%20using%20MERRA-2%20wind%20component%20data%20using%20Python
    Another example: https://scitools.org.uk/iris/docs/v2.2/examples/Meteorology/wind_speed.html
    """
    lon, lat = np.meshgrid(wind["lon"], wind["lat"])
    u, v = wind["ugrd10m"].data, wind["vgrd10m"].data
    wspeed = np.sqrt(u ** 2 + v ** 2) * 1.94384

    # wdir = np.arctan2(v, u)

    # Set the figure size, projection, and extent
    fig = plt.figure(figsize=(9, 5))
    ax = plt.axes(projection=ccrs.PlateCarree())
    ax.set_extent([-45, -35, 45, 35])
    ax.coastlines(resolution="50m", linewidth=1)
    # Add gridlines
    gl = ax.gridlines(
        crs=ccrs.PlateCarree(),
        draw_labels=True,
        linewidth=1,
        color="black",
        linestyle="--",
    )
    gl.top_labels = False
    gl.right_labels = False
    gl.xlines = True
    # gl.xlocator = mticker.FixedLocator([-65, -60, -50, -40, -30])
    # gl.ylocator = mticker.FixedLocator([30, 40, 50, 60])
    gl.xformatter = LONGITUDE_FORMATTER
    gl.yformatter = LATITUDE_FORMATTER
    gl.xlabel_style = {"size": 10, "color": "black"}
    gl.ylabel_style = {"size": 10, "color": "black"}

    # Plot windspeed
    clevs = np.arange(0, 14.5, 1)
    plt.contourf(lon, lat, wspeed, clevs, transform=ccrs.PlateCarree())
    plt.title("GFS 10m Wind Speed and Direction", size=16)
    cb = plt.colorbar(ax=ax, orientation="vertical", pad=0.02, aspect=16, shrink=0.8)
    cb.set_label("m/s", size=14, rotation=0, labelpad=15)
    cb.ax.tick_params(labelsize=10)
    # Overlay wind vectors
    # qv = plt.quiver(lon, lat, u, v, scale=420, color="k")
    fig.savefig(fout, format="png", dpi=120)
