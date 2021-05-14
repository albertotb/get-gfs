#!/bin/env python
# -*- coding: UTF-8 -*-
import sys
import numpy as np
import pandas as pd

#      Historical variable                Real time variables
MAP = {"Pressure_surface0":                        "pressfc0",
       "Temperature_height_above_ground0":         "tmp2m0",
       "Temperature_height_above_ground1":         "tmp80m0",
       "Temperature_height_above_ground2":         "tmp100m0",
       "U-component_of_wind_height_above_ground0": "ugrd10m0",
       "U-component_of_wind_height_above_ground1": "ugrd80m0",
       "U-component_of_wind_height_above_ground2": "ugrd100m0",
       "Temperature0":                             "tmpprs0",
       "V-component_of_wind_height_above_ground0": "vgrd10m0",
       "V-component_of_wind_height_above_ground1": "vgrd80m0",
       "V-component_of_wind_height_above_ground2": "vgrd100m0",
       "U-component_of_wind0":                     "ugrdprs0",
       "V-component_of_wind0":                     "vgrdprs0",
       "Geopotential_height0":                     "hgtprs0",
       "Geopotential_height1":                     "hgtprs1"}


if __name__ == '__main__':

    if len(sys.argv) != 3:
        print "usage: {} GFS GFS_HIST".format(sys.argv[0])
        sys.exit(1)

    df1 = pd.read_csv(sys.argv[1], sep=" ", header=[0, 1], index_col=[0, 1])
    df2 = pd.read_csv(sys.argv[2], sep=" ", header=[0, 1], index_col=[0, 1])
    df2.rename(columns=MAP, level='var', inplace=True)

    print df1.sub(df2).abs().sum(axis=1)
