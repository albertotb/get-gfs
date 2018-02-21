#!/bin/env python
# -*- coding: UTF-8 -*-
""" Download meteorological files from GFS """

import sys
import os
import argparse
import numpy as np
import pandas as pd
from itertools import product
from datetime import timedelta, datetime
from pydap.client import open_dods
from pydap.exceptions import ServerError, OpenFileError
from inspect import getmembers
from traceback import print_exc

URL = "http://nomads.ncep.noaa.gov:9090/dods/gfs_{res}{step}/gfs{date}/gfs_{res}{step}_{hour:02d}z.dods?"

FORMAT_STR    = "{var}.{var}[{time[0]}:{time[1]}][{lat[0]}:{lat[1]}][{lon[0]}:{lon[1]}]"
FORMAT_STR_PL = "{var}.{var}[{time[0]}:{time[1]}][{lev[0]}:{lev[1]}][{lat[0]}:{lat[1]}][{lon[0]}:{lon[1]}]"

VAR_CONF = {"pressfc":  "surface",
            "tmp2m":    "surface",
            "tmp80m":   "surface",
            "tmp100m":  "surface",
            "ugrd10m":  "surface",
            "ugrd80m":  "surface",
            "ugrd100m": "surface",
            "vgrd10m":  "surface",
            "vgrd80m":  "surface",
            "vgrd100m": "surface",
            "tmpprs":   "pressure",
            "ugrdprs":  "pressure",
            "vgrdprs":  "pressure",
            "hgtprs":   "pressure"}

DATE_FORMAT = '%Y%m%d'

range1 = lambda start, end, step=1: range(start, end+1, step)


def daterange(start, end):
    def convert(date):
        try:
            date = datetime.strptime(date, DATE_FORMAT)
            return date.date()
        except TypeError:
            return date
        # Catch and raise:
        # ValueError: day is out of range for month

    def get_date(n):
        return convert(start) + timedelta(days=n)

    days = (convert(end) - convert(start)).days
    if days < 0:
        raise ValueError('The start date must be before the end date.')
    for n in range1(0, days):
        yield get_date(n)


def lat_type(str):
    try:
        lat = float(str)
    except:
        raise argparse.ArgumentTypeError("invalid float value: '{0}'".format(str))

    if lat < -90 or lat > 90:
        raise argparse.ArgumentTypeError('latitude not in range -90..90')
    else:
        return lat


def lon_type(str):
    try:
        lon = float(str)
    except:
        raise argparse.ArgumentTypeError("invalid float value: '{0}'".format(str))

    if lon < -180 or lon > 180:
        raise argparse.ArgumentTypeError('longitude not in range -180..180')
    else:
        return lon


def get_file(request, param, var_conf, time, lat, lon):

    ntime  = len(time)
    ncoord = len(lat) * len(lon)

    var_list = [ ((FORMAT_STR if vartype == 'surface' else FORMAT_STR_PL)
                  .format(var, **param)) for var, vartype in var_conf.items() ]

    try:
        dataset = open_dods(request + ','.join(var_list))
    except:
        raise OpenFileError("file '{}' not available".format(request[:-1]))

    var_data  = [ var.data.reshape((ntime, -1, ncoord)) for var in dataset ]
    var_names = ['{}{}'.format(var.id, n) for idx, var in enumerate(dataset)
                                          for n in range(var_data[idx].shape[1])]

    index   = pd.MultiIndex.from_product((lat, lon),        names=[ 'lat', 'lon'])
    columns = pd.MultiIndex.from_product((time, var_names), names=['time', 'var'])

    return pd.DataFrame((np.concatenate(var_data, axis=1)
                           .transpose(2,0,1)
                           .reshape(ncoord, -1)), index=index, columns=columns)


def save_dataset(fname, date, hour, var_conf, res, step, time_tuple, lev_idx,
                 lat_tuple, lon_tuple):

    request = URL.format(date = date, hour = hour,
                         res  = "{0:.2f}".format(res).replace(".","p"),
                         step = "" if step == 3 else "_{:1d}hr".format(step))

    try:
        coord = open_dods(request + "lat,lon")
    except:
        raise OpenFileError("file '{}' not available".format(request[:-1]))

    # We don't get the time array from the server since it is in seconds from a
    # date. Instead we compute the times in hours manually.
    time = range1(*time_tuple, step=step)
    time_idx = (time_tuple[0]/step, time_tuple[1]/step)

    # Slicing [:] downloads the data from the server
    lat, lon = coord['lat'][:], coord['lon'][:]

    # Transform longitudes from range 0..360 to -180..180
    lon = np.where(lon > 180, lon-360, lon)

    # Transform into python lists to use the index() method
    # TODO: change to find the closest lat/lon with argmin and not an exact match
    lat_list, lon_list = lat.tolist(), lon.tolist()

    try:
        lat_idx = (lat_list.index(lat_tuple[0]), lat_list.index(lat_tuple[1]))
    except:
        raise ValueError('Latitude not in the grid', lat_tuple)

    lat = lat[range1(*lat_idx)].tolist()


    if lon_tuple[0] < 0 and lon_tuple[1] > 0:
        try:
            lon_idx_w = (lon_list.index(lon_tuple[0]), len(lon_list)-1)
            lon_idx_e = (0, lon_list.index(lon_tuple[1]))
        except:
            raise ValueError('Longitude not in the grid', lon_tuple)

        lon_w = lon[range1(*lon_idx_w)].tolist()
        lon_e = lon[range1(*lon_idx_e)].tolist()

        param_w  = {'lat': lat_idx, 'lon': lon_idx_w, 'time': time_idx, 'lev': lev_idx}
        param_e  = {'lat': lat_idx, 'lon': lon_idx_e, 'time': time_idx, 'lev': lev_idx}
        try:
            data_w = get_file(request, param_w, var_conf, time, lat, lon_w)
            data_e = get_file(request, param_e, var_conf, time, lat, lon_e)
        except:
            raise
        data = pd.concat((data_w, data_e), axis=0)

    else:
        try:
            lon_idx = (lon_list.index(lon_tuple[0]), lon_list.index(lon_tuple[1]))
        except:
            raise ValueError('Longitude not in the grid', lon_tuple)

        lon = lon[range1(*lon_idx)].tolist()

        param  = {'lat': lat_idx, 'lon': lon_idx, 'time': time_idx, 'lev': lev_idx}
        try:
            data = get_file(request, param, var_conf, time, lat, lon)
        except:
            raise

    data.to_csv(fname, sep=" ", float_format='%.3f')


def main(args):

    # Input parameters and options
    parser = argparse.ArgumentParser(description=__doc__, epilog='Report bugs or suggestions to <alberto.torres@icmat.es>')
    parser.add_argument('-x', '--lon',      help='longitude range [Default: %(default)s]',default=(-9.5,  4.5), nargs=2, type=lon_type, metavar=('FIRST', 'LAST'))
    parser.add_argument('-y', '--lat',      help='latitude range [Default: %(default)s]', default=(35.5, 44.0), nargs=2, type=lat_type, metavar=('FIRST', 'LAST'))
    parser.add_argument('-t', '--time',     help='time steps [Default: %(default)s]',      type=int, nargs=2, default=(0, 180), metavar=('FIRST', 'LAST'))
    parser.add_argument('-p', '--pl',       help='pressure levels [Default: %(default)s]', type=int, nargs=2, default=(0,   1), metavar=('FIRST', 'LAST'))
    parser.add_argument('-c', '--conf',     help='JSON file with meteo vars configuration [Default: %(default)s]', type=str, default=None, metavar=('VAR_CONF'))
    parser.add_argument('-r', '--res',      help='spatial resolution in degrees [Default: %(default)s]', type=float, choices=(0.25, 0.5), default=0.5)
    parser.add_argument('-s', '--step',     help='temporal resolution in hours [Default: %(default)s]',  type=int,   choices=(1, 3),      default=3)
    parser.add_argument('-e', '--end-date', help='end date [Default: DATE]', dest='end_date')
    parser.add_argument('-o', '--output',   help='output path [Default: %(default)s]', default='.')
    parser.add_argument('-f', '--force',    help='overwrite existing files', action='store_true')
    parser.add_argument('-v', '--version', action='version', version='%(prog)s 1.0')
    parser.add_argument('date', metavar='DATE', help='date')
    parser.add_argument('hour', metavar='HOUR', help='hour [Default: %(default)s]', type=int, choices=range1(0,18,6), nargs='?', default=(0,6,12,18))
    args = parser.parse_args()

    if args.lat[0] > args.lat[1] or args.lon[0] > args.lon[1]:
        sys.exit("First lat/lon has to be lower than the last")

    if args.time[0] > args.time[1]:
        sys.exit("First time step has to be lower than the last")

    if not args.conf:
        var_conf = VAR_CONF
    else:
        with open(args.conf, 'r') as f:
            var_conf = json.load(f)

    end_date = args.end_date if args.end_date else args.date
    hour_range = args.hour if type(args.hour) is tuple else (args.hour, )

    # Catch daterange exception
    for date in daterange(args.date, end_date):
        for hour in hour_range:
            date_str = date.strftime(DATE_FORMAT)
            fname = "{0}/{1}_{2:02d}".format(args.output, date_str, hour)

            if not args.force and os.path.isfile(fname):
                print "File {0} already exists".format(fname)
            else:
                try:
                    print "Downloading {0} {1:02d}...".format(date_str, hour),
                    sys.stdout.flush()
                    save_dataset(fname, date_str, hour, var_conf, args.res,
                                 args.step, args.time, args.pl, args.lat, args.lon)
                except (ValueError, TypeError) as err:
                    print
                    print_exc()
                except (ServerError, OpenFileError) as err:
                    print
                    print eval(str(err))
                except:
                    print
                    print "Unexpected error:", sys.exc_info()[0]
                    print sys.exc_info()[1]
                    print_exc()
                else:
                    print "done!"
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
