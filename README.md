## Note

There is now a probably easier way to download this kind of data using `xarray`. There are examples downloading and ploting variables in the folder `notebook`. It wouldn't be hard to create an script similar to `get_gfs.py` with this code instead, or to adapt the existing one. There is now an example, `xarray_example.py`, thanks to @heyerbobby). The old scripts using `pydap` SHOULD still work.


## Installation

These scripts were tested with Python 3.7+, but they should work with any Python 3 version. First install [Anaconda](https://www.anaconda.com/distribution/#download-section) and then
create an enviroment with 

    conda env create -f environment.yml

Then activate the environment

    conda activate get-gfs


## Downloading meteorological information from GFS

Scripts to fetch meteorological data from the GFS model:
 * `get_gfs.py` gets data from the real-time server, which is located at
   <https://nomads.ncep.noaa.gov/dods/> and holds the last 15 days of data.
 * `get_gfs_hist.py` gets data from the historical server, which is located
   at <https://www.ncei.noaa.gov/thredds/catalog/model-gfs-004-files-old/catalog.html> and
   holds the last 2 years of data (more information: <https://www.ncdc.noaa.gov/data-access/model-data/model-datasets/global-forcast-system-gfs>)

Example for the real time server:

    ./get_gfs.py -s 1 -r 0.25 -t 0 48 -x -10 10 -y -15 15 -p 0 2 -c example_conf.json 20210217 00

The previous line will download meteorology from the GFS run on 2021-02-17 at 00z:

   * Temporal resolution of 1 hour
   * Spatial resolution of 0.25º
   * Time steps from 0 to 48 (since temporal resolution is 1h, 48 hours from 20210217 at 00)
   * Longitudes from -10 to 10
   * Latitudes from -15 to 15
   * Pressure levels from 0 to 2 (only for variables that have pressure level data)
   * Variables in `example_conf.json`

Example for the historical server:

    ./get_gfs_hist.py -t 0 10 -x -10 10 -y -10 10 -c example_conf_hist.json 20191005 00

Note that the historical server:

   * Only has 0.5º spatial resolution (the default)
   * Only has 3h temporal resolution (the default)
   * It downloads the first 10 time steps, which in turn it translates to hours 00-30 (due to temporal resolution of 3 hours)
   * Pressure levels and heights are specified for each variable in the configuration file

To build the JSON configuration files for the historical server you can go 
directly to the server and check the following URL for any day:

<https://www.ncei.noaa.gov/thredds/dodsC/model-gfs-004-files-old/202005/20200515/gfs_4_20200515_0600_000.grb2.html>

The possible values for the `height_above_ground` and `isobaric` levels can be
obtained running a query directly in the browser, for instance:

<https://www.ncei.noaa.gov/thredds/dodsC/model-gfs-004-files-old/202005/20200515/gfs_4_20200515_0600_000.grb2.ascii?isobaric,height_above_ground>

Similarly, for the real time server you can get this information by adding the suffix `.dds`, `.info` and `.das`

In the URLs you can also see some information about the meteorological variables
such us units, minimum, maximum, representation of missing values and so on.

The output of the script is an Pandas dataframe written to an ASCII file, with a
multi-index in the rows (lat, lon) and a multi-index in the columns
(variables-time). It can be read back into Python using `pd.read_csv()`.

## Differences between the real time server and the historical server

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
