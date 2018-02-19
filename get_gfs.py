#!/bin/env python
# -*- coding: UTF-8 -*-
""" Download meteorological files from GFS """

import sys
import os
import argparse
import numpy as np
from itertools import product
from datetime import timedelta, datetime
from pydap.client import open_dods
from pydap.exceptions import ServerError

URL = "http://nomads.ncep.noaa.gov:9090/dods/gfs_{0}/gfs{1}/gfs_{0}_{2:02d}z.dods?"

FORMAT_STR = "{0}.{0}[{time[0]}:{time[1]}][{lat[0]}:{lat[1]}][{lon[0]}:{lon[1]}]"
VAR_STR = ( "pressfc", "tmp2m", "tmp80m", "tmp100m", "ugrd10m", "ugrd80m", "ugrd100m", "vgrd10m", "vgrd80m", "vgrd100m")
#VAR_STR = ( "pressfc", "tmp2m", "ugrd10m", "vgrd10m")

FORMAT_STR_PL = "{0}.{0}[{time[0]}:{time[1]}][{lev[0]}:{lev[1]}][{lat[0]}:{lat[1]}][{lon[0]}:{lon[1]}]"
VAR_STR_PL = ("hgtprs", "tmpprs", "ugrdprs", "vgrdprs")

DATE_FORMAT = '%Y%m%d'

range1 = lambda start, end, step=1: range(start, end+1, step)

def main(args):

    # input parameters and options
    parser = argparse.ArgumentParser(description=__doc__, epilog='Report bugs or suggestions to <alberto.torres@uam.es>')
    parser.add_argument('-x', '--lon', help='longitude range [Default: %(default)s]', default=(-9.5, 4.5), nargs=2, type=lon_type, metavar=('FIRST', 'LAST'))
    parser.add_argument('-y', '--lat', help='latitude range [Default: %(default)s]', default=(35.5, 44.0), nargs=2, type=lat_type, metavar=('FIRST', 'LAST'))
    parser.add_argument('-t', '--time', help='time steps [Default: %(default)s]', type=int, nargs=2, default=(0, 60), metavar=('FIRST', 'LAST'))
    parser.add_argument('-l', '--lev', help='pressure levels [Default: %(default)s]', type=int, nargs=2, default=None, metavar=('FIRST', 'LAST'))
    parser.add_argument('-r', '--res', help='resolution [Default: %(default)s]', type=float, default=0.5)
    parser.add_argument('-e', '--end-date', help='end date [Default: DATE]', dest='end_date')
    parser.add_argument('-o', '--output', help='output path [Default: %(default)s]', default='.')
    parser.add_argument('-f', '--force', help='overwrite existing files', action='store_true')
    parser.add_argument('-v', '--version', action='version', version='%(prog)s 1.0')
    parser.add_argument('date', metavar='DATE', help='date')
    parser.add_argument('hour', metavar='HOUR', help='hour [Default: %(default)s]', type=int, choices=range1(0,18,6), nargs='?', default=(0,6,12,18))
    args = parser.parse_args()

    if args.lat[0] > args.lat[1] or args.lon[0] > args.lon[1]:
        sys.exit("First lat/lon has to be greater than the last")

    end_date = args.end_date if args.end_date else args.date
    hour_range = args.hour if type(args.hour) is tuple else (args.hour, )

    # catch daterange exception
    for date in daterange(args.date, end_date):
        for hour in hour_range:
            fname = "{0}/{1}_{2:02d}".format(args.output, date, hour)

            if not args.force and os.path.isfile(fname):
                print "File {0} already exists".format(fname)
            else:
                try:
                    print "Downloading {0} {1:02d}...".format(date, hour),
                    sys.stdout.flush()
                    save_dataset(fname, date, hour, args.res, args.time, args.lev, args.lat, args.lon)
                except (ValueError, TypeError) as err:
                    print err
                    return 1
                except ServerError as err:
                    print eval(str(err))
                    return 2
                except:
                    print "Unexpected error:", sys.exc_info()[0]
                    print sys.exc_info()[1]
                    return 3
                else:
                    print "done!"
    return 0


def daterange(start, end):
    def convert(date):
        try:
            date = datetime.strptime(date, DATE_FORMAT)
            return date.date()
        except TypeError:
            return date

    def get_date(n):
        return datetime.strftime(convert(start) + timedelta(days=n), DATE_FORMAT)

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


# catch exception if time_idx or lev_idx out of range
def get_sequential(request, time_idx, lev_idx, lat_idx, lon_idx):

    param = {'lat': lat_idx, 'lon': lon_idx, 'time': time_idx, 'lev': lev_idx}

    ntime = (time_idx[1]-time_idx[0]+1)

    if lev_idx is None:
        vars = [ FORMAT_STR.format(var, **param) for var in VAR_STR ]
        nlev = 1
    else:
        vars = [ FORMAT_STR_PL.format(var, **param) for var in VAR_STR_PL ]
        nlev = lev_idx[1]-lev_idx[0]+1

    dataset = open_dods(request + ','.join(vars))

    var_data = np.array([ var.data.reshape(ntime, nlev, -1) for var in dataset ])
    return var_data.transpose(3,1,0,2).reshape(-1, ntime*nlev*len(var_data))


# catch exception if time_idx or lev_idx out of range
def get_general(request, time_idx, lev_idx, lat_idx, lon_idx_w, lon_idx_e):

    param_w = {'lat': lat_idx, 'lon': lon_idx_w, 'time': time_idx, 'lev': lev_idx}
    param_e = {'lat': lat_idx, 'lon': lon_idx_e, 'time': time_idx, 'lev': lev_idx}

    ntime = (time_idx[1]-time_idx[0]+1)

    if lev_idx is None:
        vars_w = [ FORMAT_STR.format(var, **param_w) for var in VAR_STR ]
        vars_e = [ FORMAT_STR.format(var, **param_e) for var in VAR_STR ]
        nlev = 1
    else:
        vars_w = [ FORMAT_STR_PL.format(var, **param_w) for var in VAR_STR_PL ]
        vars_e = [ FORMAT_STR_PL.format(var, **param_e) for var in VAR_STR_PL ]
        nlev = (lev_idx[1]-lev_idx[0]+1)

    dataset_w = open_dods(request + ','.join(vars_w))
    dataset_e = open_dods(request + ','.join(vars_e))

    var_data = np.array([ np.concatenate(var, axis=var[0].ndim-1).reshape(ntime, nlev, -1)
                          for var in zip(dataset_w.data, dataset_e.data) ])

    return var_data.transpose(3,1,0,2).reshape(-1, ntime*nlev*len(var_data))


def save_dataset(fname, date, hour, res, time_idx, lev_idx, lat_tuple, lon_tuple):

    request = URL.format("{0:.2f}".format(res).replace(".","p"), date, hour)

    try:
        coord = open_dods(request + "lat,lon")
    except:
        raise

    # slicing [:] downloads the data from the server
    lat, lon = coord['lat'][:], coord['lon'][:]

    # transform longitudes from range 0..360 to -180..180
    lon = np.where(lon > 180, lon-360, lon)

    # transform into python lists to use the index() method
    lat_list, lon_list = lat.tolist(), lon.tolist()

    try:
        lat_idx = (lat_list.index(lat_tuple[0]), lat_list.index(lat_tuple[1]))
    except:
        raise ValueError('Latitude not in the grid', lat_tuple)

    lat = lat[range1(*lat_idx)]

    if lon_tuple[0] < 0 and lon_tuple[1] > 0:
        try:
            lon_idx_w = (lon_list.index(lon_tuple[0]), len(lon_list)-1)
            lon_idx_e = (0, lon_list.index(lon_tuple[1]))
        except:
            raise ValueError('Longitude not in the grid', lon_tuple)
        lon = np.concatenate((lon[range1(*lon_idx_w)], lon[range1(*lon_idx_e)]))

        data = get_general(request, time_idx, lev_idx, lat_idx, lon_idx_w, lon_idx_e)

    else:
        try:
            lon_idx = (lon_list.index(lon_tuple[0]), lon_list.index(lon_tuple[1]))
        except:
            raise ValueError('Longitude not in the grid', lon_tuple)
        lon = lon[range1(*lon_idx)]

        data = get_sequential(request, time_idx, lev_idx, lat_idx, lon_idx)

    coord = np.array(list(product(lat, lon)))
    dataset = np.hstack((coord[:,1][:, np.newaxis], coord[:,0][:, np.newaxis], data))

    np.savetxt(fname, dataset, fmt='%.2f')


if __name__ == '__main__':
    sys.exit(main(sys.argv))
