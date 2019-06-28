## INSTALLATION
-----------------------------------------------

This scripts only work with Python 2.7+. First install [Anaconda](https://www.anaconda.com/distribution/#download-section) and then
create an enviroment with 

    conda env create -f environment.yml

Then activate the environment

    conda activate get-gfs


## DOWNLOADING METEOROLOGICAL INFORMATION FROM GFS
-----------------------------------------------

Scripts to fetch meteorological data from the GFS model:
 * `get_gfs.py` gets data from the real-time server, which is located at
   <http://nomads.ncep.noaa.gov:9090/dods> and holds the last 15 days of data.
 * `get_gfs_hist.py` gets data from the historical server, which is located
   at <https://nomads.ncdc.noaa.gov/thredds/dodsC/gfs-004/catalog.html> and
   holds the last 2 years of data.

To build the JSON configuration files for the historical server you can go 
directly to the server and check the following URL for any day:

<https://nomads.ncdc.noaa.gov/thredds/dodsC/gfs-004/201802/20180217/gfs_4_20180217_1800_111.grb2.html>

The possible values for the `height_above_ground` and `pressure` levels can be
obtained running a query directly in the browser, for instance:

<https://nomads.ncdc.noaa.gov/thredds/dodsC/gfs-004/201802/20180217/gfs_4_20180217_1800_111.grb2.ascii?pressure,height_above_ground>

Similarly, for the real time server you can get this information at

<http://nomads.ncep.noaa.gov:9090/dods/gfs_0p50/gfs20180212/gfs_0p50_00z.info>
<http://nomads.ncep.noaa.gov:9090/dods/gfs_0p50/gfs20180212/gfs_0p50_00z.dds>
<http://nomads.ncep.noaa.gov:9090/dods/gfs_0p50/gfs20180212/gfs_0p50_00z.das>

In the URLs you can also see some information about the meteorological variables
such us units, minimum, maximum, representation of missing values and so on.

Apart from the name of the variables, which is different in both servers (even
though they refer to the same meteorological variable), there are also other
differences between them:
  * The real time server stores all the time steps in one file, while in the
    historical server there is one file for each time step (0, 3, 6, 9, 12,...)
  * The real time server has also 0.25º spatial resolution, while the historical
    server only has 0.5º
  * The real time server has a temporal resolution of 1hr and 3hr for 0.25º,
    while for 0.5º and in the historical server only an step of 3hr is available
  * In the real time server the different heights of the variables are stored
    in different entries. For instance `tmp2m`, `tmp80m`, `tmp100m` refer to
    the temperature at 2, 80 and 100m above ground. In the historical server
    these variables are a stored in an new dimension of the variable, for
    example `Temperature_height_above_ground`. Thus, in the historical server
    the z-axis (either `height_above_ground` or `pressure`) has to be set for
    *each* variable in the configuration file. In the real time server the
    pressure levels are controlled using an optional parameter, but they have
    to be the same for every variable which has them. Variables at different
    heights are different entries, as mentioned above.
