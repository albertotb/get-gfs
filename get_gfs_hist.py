#!/usr/bin/env python
# -*- coding: UTF-8 -*-
""" Descarga ficheros de meteorología del servidor histórico del GFS """

import sys
import os
import argparse
import numpy as np
import pandas as pd
import json
from time import time
from datetime import timedelta, datetime
from pydap.client import open_dods
from pydap.exceptions import ServerError
from traceback import format_exc, print_exc

sys.path.append('.')
from get_gfs import range1, lat_type, lon_type, daterange

URL           = "https://www.ncei.noaa.gov/thredds/dodsC/model-gfs-004-files-old/{0}_{1:03d}.grb2.dods?"
DIR           = "{0}/{1}/gfs_4_{1}_{2:02d}00"
FORMAT_STR    = "{var}.{var}[0][{lat[0]}:{lat[1]}][{lon[0]}:{lon[1]}]"
FORMAT_STR_PL = "{var}.{var}[0][{lev[0]}:{lev[1]}][{lat[0]}:{lat[1]}][{lon[0]}:{lon[1]}]"
DATE_FORMAT   = "%Y%m%d"

VARS = {"Pressure_surface":                        {"type": "surface"},
        "U-component_of_wind_height_above_ground": {"type": "height_above_ground", "levels": [0, 2]},
        "V-component_of_wind_height_above_ground": {"type": "height_above_ground", "levels": [0, 2]},
        "Temperature_height_above_ground":         {"type": "height_above_ground", "levels": [0, 0]},
        "U-component_of_wind":                     {"type": "isobaric",            "levels": [0, 5]},
        "V-component_of_wind":                     {"type": "isobaric",            "levels": [0, 5]},
        "Temperature":                             {"type": "isobaric",            "levels": [0, 5]},
        "Geopotential_height":                     {"type": "isobaric",            "levels": [0, 1]}}


def get_sequential(file, time, var_config, lat_idx, lon_idx, verbose=False):

    var_list = []
    nlev_dict = {}
    for var, config in var_config.items():
        if config['type'] == 'surface':
            var_list.append(FORMAT_STR.format(var=var, lat=lat_idx, lon=lon_idx))
            nlev_dict[var] = 1
        else:
            lev_idx = tuple(config['levels'])
            var_list.append(FORMAT_STR_PL.format(var=var, lev=lev_idx, lat=lat_idx, lon=lon_idx))
            nlev_dict[var] = lev_idx[1]-lev_idx[0]+1

    ncoord = (lat_idx[1]-lat_idx[0]+1)*(lon_idx[1]-lon_idx[0]+1)

    request = URL.format(file, time) + ','.join(var_list)

    if verbose:
        print(request)

    try:
        dataset = open_dods(request)
    except:
        raise

    var_data = [ pd.DataFrame(var.data.reshape(nlev_dict[var.name], ncoord).T,
                              columns = ['{}{}'.format(var.name, n)
                                         for n in range(nlev_dict[var.name])])
                 for var in dataset]

    return pd.concat(var_data, axis=1)


def get_general(file, time, var_config, lat_idx, lon_idx_w, lon_idx_e, verbose=False):

    request = URL.format(file, time)

    var_w_list , var_e_list = [], []
    nlev_dict = {}
    for var, config in var_config.items():
        if config['type'] == 'surface':
            var_w_list.append(FORMAT_STR.format(var=var, lat=lat_idx, lon=lon_idx_w))
            var_e_list.append(FORMAT_STR.format(var=var, lat=lat_idx, lon=lon_idx_e))
            nlev_dict[var] = 1
        else:
            lev_idx = tuple(config['levels'])
            var_w_list.append(FORMAT_STR_PL.format(var=var, lev=lev_idx, lat=lat_idx, lon=lon_idx_w))
            var_e_list.append(FORMAT_STR_PL.format(var=var, lev=lev_idx, lat=lat_idx, lon=lon_idx_e))
            nlev_dict[var] = lev_idx[1]-lev_idx[0]+1

    ncoord = (lat_idx[1]-lat_idx[0]+1)*((lon_idx_w[1]-lon_idx_w[0]+1) + (lon_idx_e[1]-lon_idx_e[0]+1))

    request_w = request + ','.join(var_w_list)
    request_e = request + ','.join(var_e_list)

    if verbose:
        print(request_w)
        print(request_e)

    try:
        dataset_w = open_dods(request_w)
        dataset_e = open_dods(request_e)
    except:
        raise

    # 1. Concatenate both 'west' and 'east' data along 'lon' axis (last axis)
    # 2. Reshape 4D-array (1, nlev, nlat, nlon) to 2D-array (nlev, nlat*nlon)
    # 3. Transpose and store in DataFrame
    # This is ugly :(, partly because the long function names
    var_data = [ pd.DataFrame((np.concatenate((var_w.data, var_e.data),
                                              axis=len(var_w.shape)-1)
                                 .reshape(nlev_dict[var_w.name], ncoord).T),
                              columns = ['{}{}'.format(var_w.name, n)
                                         for n in range(nlev_dict[var_w.name])])
                 for var_w, var_e in zip(dataset_w.values(), dataset_e.values()) ]

    # 4. Concatenate the DataFrames for each var to obtain a single DataFrame
    #    with (nlat*nlon, nlev*nvar) Note every var can have a different number
    #    of levels (either pressure levels or height above ground levels)
    return pd.concat(var_data, axis=1)


def save_dataset(hour, date, var_config, time_tuple, lat_tuple, lon_tuple, fname, verbose=False):
    """ Download the datasets for a specific date and hour """

    date_str = date.strftime("%Y%m%d")
    month_str = date.strftime("%Y%m")

    file = DIR.format(month_str, date_str, hour)

    time_list = list(range1(time_tuple[0], time_tuple[1], 3))

    # Get the lat and lon grids from the first dataset present in the server
    for time in time_list:

        request = URL.format(file, time)
        try:
            coord = open_dods(request + "lat,lon")
        except:
            continue
        else:
            break

    try:
        lat, lon = coord['lat'][:].data, coord['lon'][:].data
    except:
        # UnboundLocalError: local variable 'coord' referenced before assignment
        # none of the 180/3 + 1 datasets where present in the server
        raise

    # Transform longitudes from range 0..360 to -180..180
    lon = np.where(lon > 180, lon-360, lon)

    # Transform into python lists to use the index() method
    # Actually it would be better to use np.where()
    lat_list, lon_list = lat.tolist(), lon.tolist()

    try:
        lat_idx = (lat_list.index(lat_tuple[1]), lat_list.index(lat_tuple[0]))
    except:
        raise ValueError('Latitude not in the grid', lat_tuple)

    lat = lat[range1(*lat_idx)].tolist()

    if lon_tuple[0] < 0 and lon_tuple[1] > 0:
        try:
            lon_idx_w = (lon_list.index(lon_tuple[0]), len(lon_list)-1)
            lon_idx_e = (0, lon_list.index(lon_tuple[1]))
        except:
            raise ValueError('Longitude not in the grid', lon_tuple)
        lon = (np.concatenate((lon[range1(*lon_idx_w)], lon[range1(*lon_idx_e)]))
                 .tolist())

        try:
            data_list = [get_general(file, time, var_config, lat_idx,
                                     lon_idx_w, lon_idx_e, verbose=verbose) for time in time_list]
        except:
            raise

    else:
        try:
            lon_idx = (lon_list.index(lon_tuple[0]), lon_list.index(lon_tuple[1]))
        except:
            raise ValueError('Longitude not in the grid', lon_tuple)
        lon = lon[range1(*lon_idx)].tolist()
        try:
            data_list = [get_sequential(file, time, var_config, lat_idx, lon_idx, verbose=verbose)
                         for time in time_list]
        except:
            raise

    data = pd.concat(data_list, axis=1, keys=time_list, names=['time', 'var'])
    data.index = pd.MultiIndex.from_product((lat, lon), names=[ 'lat', 'lon'])
    data.sort_index(inplace=True)
    data.to_csv(fname, sep=" ", float_format='%.3f')


def main(args):

    # Read input arguments
    parser = argparse.ArgumentParser(description=__doc__, epilog='Report bugs or suggestions to <alberto.torres@icmat.es>')
    parser.add_argument('-x', '--lon', help='longitude range [Default: %(default)s]', default=(-9.5, 4.5), nargs=2, type=lon_type, metavar=('FIRST', 'LAST'))
    parser.add_argument('-y', '--lat', help='latitude range [Default: %(default)s]', default=(35.5, 44.0), nargs=2, type=lat_type, metavar=('FIRST', 'LAST'))
    parser.add_argument('-t', '--time', help='time steps [Default: %(default)s]', type=int, nargs=2, default=(0, 180), metavar=('FIRST', 'LAST'))
    parser.add_argument('-c', '--config', help='JSON file with meteo vars configuration [Default: %(default)s]', type=str, default=None, metavar=('VAR_CONF'))
    parser.add_argument('-e', '--end-date', help='end date [Default: same as start date]', dest='end_date', metavar='END_DATE')
    parser.add_argument('-o', '--output', help='output path [Default: "%(default)s"]', default='.')
    parser.add_argument('-f', '--force', help='overwrite existing files', action='store_true')
    parser.add_argument('-v', '--verbose', help='print download progress', action='store_true')
    parser.add_argument('date', metavar='DATE', help='date')
    parser.add_argument('hour', metavar='HOUR', help='hour [Default: %(default)s]', type=int, choices=range1(0,18,6), nargs='?', default=(0,6,12,18))
    args = parser.parse_args()

    if args.lat[0] > args.lat[1] or args.lon[0] > args.lon[1]:
        sys.exit("First lat/lon has to be lower than the last")

    if args.time[0] > args.time[1]:
        sys.exit("First time step has to be lower than the last")

    end_date = args.end_date if args.end_date else args.date
    hour_range = args.hour if type(args.hour) is tuple else (args.hour, )

    if not args.config:
        var_config = VARS
    else:
        with open(args.config, 'r') as f:
            var_config = json.load(f)

    for date in daterange(args.date, end_date):
        for hour in hour_range:

            date_str = date.strftime(DATE_FORMAT)
            fname = "{0}/{1}_{2:02d}".format(args.output, date_str, hour)

            if not os.path.isfile(fname) or args.force:
                try:
                    print("Downloading {0} {1:02d}...".format(date_str, hour), end=' ')
                    save_dataset(hour, date, var_config, args.time, args.lat, args.lon, fname, verbose=args.verbose)
                except ServerError as err:
                    print("[{0} {1:02d}]".format(date_str, hour), end=' ')
                    print(eval(str(err)))
                except UnboundLocalError:
                    print("[{0} {1:02d}]".format(date_str, hour), end=' ')
                    print("dataset not available")
                #except ValueError as err:
                #    print err
                except:
                    print("[{0} {1:02d}]".format(date_str, hour), end=' ')
                    print(format_exc().splitlines()[-1])
                    print_exc()
                else:
                    print("done!")
            else:
                print("File {0} already exists (re-run with -f to overwrite)".format(fname))


if __name__ == '__main__':
    main(sys.argv)
