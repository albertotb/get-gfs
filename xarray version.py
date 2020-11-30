import numpy as np
import xarray as xr
import pandas as pd

# File Details
dt = '20201129'
res = 25
step = '1hr'
run = '{:02}'.format(0)
lat_toplot = np.arange(-43, -17.25, 0.25) # last number is exclusive
lon_toplot = np.arange(135, 152.25, 0.25) # last number is exclusive

# ******************************
# SELECT GFS FILE
# ******************************
# URL
URL = f'http://nomads.ncep.noaa.gov:80/dods/gfs_0p{res}_{step}/gfs{dt}/gfs_0p{res}_{step}_{run}z'

variables = ['ugrd100m', 'vgrd100m', 'dswrfsfc', 'tcdcclm', 'tcdcblcll',
             'tcdclcll', 'tcdcmcll', 'tcdchcll', 'tmp2m', 'gustsfc']

dataset = xr.open_dataset(URL)[variables]
time = dataset.variables['time']
lat = dataset.variables['lat'][:]
lon = dataset.variables['lon'][:]
# lev = dataset.variables['lev'][:]

# Narrow Down Selection
time_toplot = time
# lev_toplot = np.array([1000])

# Select required data via xarray
dataset = dataset.sel(time=time_toplot, lon=lon_toplot, lat=lat_toplot)
print(dataset)

df = dataset.to_dataframe()
# df = df.unstack(level=-1).fillna(0)
print(df)
