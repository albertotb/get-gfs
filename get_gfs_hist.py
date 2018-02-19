#!/bin/env python
# -*- coding: UTF-8 -*-
""" Descarga ficheros de meteorología del servidor histórico del GFS """

import sys
import os
import argparse
import numpy as np
from Queue import Queue
from threading import Thread
from time import time
from datetime import timedelta, datetime
from itertools import product
from pydap.client import open_dods
from pydap.exceptions import ServerError
from traceback import format_exc

DIR = "{0}/{1}/gfs_4_{1}_{2:02d}00"
URL = "https://nomads.ncdc.noaa.gov/thredds/dodsC/gfs-004/{0}_{1:03d}.grb2.dods?"


FORMAT_STR    = "{0}.{0}[0][{lat[0]}:{lat[1]}][{lon[0]}:{lon[1]}]"
FORMAT_STR_HAG = "{0}.{0}[0][0:2][{lat[0]}:{lat[1]}][{lon[0]}:{lon[1]}]"
VAR_DIC = {"U-component_of_wind_height_above_ground": FORMAT_STR_HAG,
           "Pressure_surface":                        FORMAT_STR,
           "Temperature_height_above_ground":         FORMAT_STR_HAG,
           "V-component_of_wind_height_above_ground": FORMAT_STR_HAG}

FORMAT_STR_PL = "{0}.{0}[0][{lev[0]}:{lev[1]}][{lat[0]}:{lat[1]}][{lon[0]}:{lon[1]}]"
VAR_DIC_PL = {"U-component_of_wind": FORMAT_STR_PL,
              "V-component_of_wind": FORMAT_STR_PL,
              "Temperature":         FORMAT_STR_PL,
              "Geopotential_height": FORMAT_STR_PL}

DATE_FORMAT = '%Y%m%d'

range1 = lambda start, end, step=1: range(start, end+1, step)

def main(args):

    # leer parametros de entrada
    parser = argparse.ArgumentParser(description=__doc__, epilog='Reportar bugs o sugerencias a <alberto.torres@uam.es>')
    parser.add_argument('-x', '--lon', help='longitude range [Default: %(default)s]', default=(-9.5, 4.5), nargs=2, type=lon_type, metavar=('FIRST', 'LAST'))
    parser.add_argument('-y', '--lat', help='latitude range [Default: %(default)s]', default=(35.5, 44.0), nargs=2, type=lat_type, metavar=('FIRST', 'LAST'))
    parser.add_argument('-t', '--time', help='time steps [Default: %(default)s]', type=int, nargs=2, default=(0, 180), metavar=('FIRST', 'LAST'))
    parser.add_argument('-l', '--lev', help='pressure levels [Default: %(default)s]', type=int, nargs=2, default=None, metavar=('FIRST', 'LAST'))
    parser.add_argument('-e', '--end-date', help='end date [Default: same as start date]', dest='end_date', metavar='END_DATE')
    parser.add_argument('-o', '--output', help='output path [Default: "%(default)s"]', default='.')
    parser.add_argument('-f', '--force', help='overwrite existing files', action='store_true')
    parser.add_argument('-v', '--verbose', help='print download progress', action='store_true')
    parser.add_argument('date', metavar='DATE', help='date')
    parser.add_argument('hour', metavar='HOUR', help='hour [Default: %(default)s]', type=int, choices=range1(0,18,6), nargs='?', default=(0,6,12,18))
    args = parser.parse_args()

    if args.lat[0] > args.lat[1] or args.lon[0] > args.lon[1]:
        sys.exit("First lat/lon has to be greater than the last")

    end_date = args.end_date if args.end_date else args.date
    hour_range = args.hour if type(args.hour) is tuple else (args.hour, )

    #q = Queue(4)

    # catch daterange exception
    for date in daterange(args.date, end_date):
        for hour in hour_range:

            date_str = date.strftime(DATE_FORMAT)
            fname = "{0}/{1}_{2:02d}".format(args.output, date_str, hour)

            #q.put(hour)
            if not os.path.isfile(fname) or args.force:
                try:
                    if args.verbose:
                        print "Downloading {0} {1:02d}...".format(date_str, hour),
                #    sys.stdout.flush()
                    save_dataset(hour, date, args.lev, args.time, args.lat, args.lon, fname)
                #except ValueError as err:
                #    print err
                except ServerError as err:
                    if not args.verbose:
                        print "[{0} {1:02d}]".format(date_str, hour),
                    print eval(str(err))
                except UnboundLocalError:
                    if not args.verbose:
                        print "[{0} {1:02d}]".format(date_str, hour),
                    print "dataset not available"
                except:
                    if not args.verbose:
                        print "[{0} {1:02d}]".format(date_str, hour),
                    print format_exc().splitlines()[-1]
                    #print "Unexpected error:", sys.exc_info()[0]
                    #print sys.exc_info()[1]
                else:
                    if args.verbose:
                        print "done!"
            else:
                if args.verbose:
                    print "File {0} already exists (re-run with -f to overwrite)".format(fname)
            #t = Thread(target=save_dataset, args=(q, date, (0, 2), args.lat, args.lon, args.output))
            #t.start()

    #q.join()


def daterange(start, end):
    def convert(date):
        try:
            date = datetime.strptime(date, DATE_FORMAT)
            return date.date()
        except TypeError:
            return date
        # catch and raise:
        #ValueError: day is out of range for month

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


def get_sequential(file, time, lev_idx, lat_idx, lon_idx):

    request = URL.format(file, time)
    params = {'lev': lev_idx, 'lat': lat_idx, 'lon': lon_idx}

    if lev_idx is None:
        vars = [ format_str.format(var, **params) for (var, format_str) in VAR_DIC.items() ]
        nlev = -1
    else:
        vars = [ format_str.format(var, **params) for (var, format_str) in VAR_DIC_PL.items() ]
        nlev = lev_idx[1]-lev_idx[0]+1

    ncoord = (lat_idx[1]-lat_idx[0]+1)*(lon_idx[1]-lon_idx[0]+1)

    try:
        dataset = open_dods(request + ','.join(vars))
    except:
        # crear un np.array de error
        raise

    # the [...,::-1,:] reverses the latitudes axis
    var_data = tuple([var[...,::-1,:].reshape(nlev, ncoord).T for var in dataset.data])
    return np.concatenate(var_data, axis=1)


def get_general(file, time, lev_idx, lat_idx, lon_idx_w, lon_idx_e):

    request = URL.format(file, time)
    params_w = {'lev': lev_idx, 'lat': lat_idx, 'lon': lon_idx_w}
    params_e = {'lev': lev_idx, 'lat': lat_idx, 'lon': lon_idx_e}

    if lev_idx is None:
        vars_w = [ format_str.format(var, **params_w) for (var, format_str) in VAR_DIC.items() ]
        vars_e = [ format_str.format(var, **params_e) for (var, format_str) in VAR_DIC.items() ]
        nlev = -1
    else:
        vars_w = [ format_str.format(var, **params_w) for (var, format_str) in VAR_DIC_PL.items() ]
        vars_e = [ format_str.format(var, **params_e) for (var, format_str) in VAR_DIC_PL.items() ]
        nlev = lev_idx[1]-lev_idx[0]+1

    ncoord = (lat_idx[1]-lat_idx[0]+1)*((lon_idx_w[1]-lon_idx_w[0]+1) + (lon_idx_e[1]-lon_idx_e[0]+1))

    try:
        dataset_w = open_dods(request + ','.join(vars_w))
        dataset_e = open_dods(request + ','.join(vars_e))
    except:
        # crear un np.array de error
        raise

    # the [...,::-1,:] reverses the latitudes axis
    var_data = tuple([ np.concatenate(var, axis=var[0].ndim-1)[...,::-1,:].reshape(nlev, ncoord).T for var in
                       zip(dataset_w.data, dataset_e.data) ])

    return np.concatenate(var_data, axis=1)


def save_dataset(hour, date, lev_idx, time_tuple, lat_tuple, lon_tuple, fname):
    """ Download the 4 datasets (00, 06, 12, 18) for a specific date """

    #hour = q.get()
    date_str = date.strftime("%Y%m%d")
    month_str = date.strftime("%Y%m")

    file = DIR.format(month_str, date_str, hour)

    # get the lat and lon grids from the first dataset present in the server
    for time in range1(time_tuple[0], time_tuple[1], 3):

        request = URL.format(file, time)
        try:
            coord = open_dods(request + "lat,lon")
        except:
            continue
        else:
            break

    try:
        lat, lon = coord['lat'][:], coord['lon'][:]
    except:
        # UnboundLocalError: local variable 'coord' referenced before assignment
        # none of the 180/3 + 1 datasets where present in the server
        raise

    # transform longitudes from range 0..360 to -180..180
    lon = np.where(lon > 180, lon-360, lon)

    # transform into python lists to use the index() method
    lat_list, lon_list = lat.tolist(), lon.tolist()

    try:
        lat_idx = (lat_list.index(lat_tuple[1]), lat_list.index(lat_tuple[0]))
    except:
        raise ValueError('Latitude not in the grid', lat_tuple)

    lat = lat[range1(*lat_idx)][::-1]

    if lon_tuple[0] < 0 and lon_tuple[1] > 0:
        try:
            lon_idx_w = (lon_list.index(lon_tuple[0]), len(lon_list)-1)
            lon_idx_e = (0, lon_list.index(lon_tuple[1]))
        except:
            raise ValueError('Longitude not in the grid', lon_tuple)
        lon = np.concatenate((lon[range1(*lon_idx_w)], lon[range1(*lon_idx_e)]))
        try:
            data = np.array([ get_general(file, time, lev_idx, lat_idx, lon_idx_w, lon_idx_e) for time in range1(time_tuple[0], time_tuple[1], 3) ])
        except:
            raise

    else:
        try:
            lon_idx = (lon_list.index(lon_tuple[0]), lon_list.index(lon_tuple[1]))
        except:
            raise ValueError('Longitude not in the grid', lon_tuple)
        lon = lon[range1(*lon_idx)]
        try:
            data = np.array([ get_sequential(file, time, lev_idx, lat_idx, lon_idx) for time in range1(time_tuple[0], time_tuple[1], 3) ])
        except:
            raise

    coord = np.array(list(product(lat, lon)))
    data = data.transpose(1,0,2).reshape(len(lat)*len(lon), -1)
    dataset = np.hstack((coord[:,1][:, np.newaxis], coord[:,0][:, np.newaxis], data))

    np.savetxt(fname, dataset, fmt='%.2f')

    #q.task_done()


if __name__ == '__main__':
    main(sys.argv)
