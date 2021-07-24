#!/usr/bin/env python
import datetime as dt
import logging

import typer
import xarray as xr

from utils import set_logging

GFS_HIST_BASE = "https://www.ncei.noaa.gov/thredds/dodsC/model-gfs-004-files-old"


def get_gfs_hist(
    date: dt.date,
    varlist: list,
    run: int = 0,
    time: int = 0,
):

    date_str = date.strftime("%Y%m%d")
    month_str = date.strftime("%Y%m")
    url = f"{GFS_HIST_BASE}/{month_str}/{date_str}/gfs_4_{date_str}_{run:02d}00_{time:03d}.grb2"

    logging.info(url)

    with xr.open_dataset(url) as ds:
        ds[varlist].to_netcdf(f"{date_str}_{run:02d}_{time:03d}.nc")


def main(date: dt.datetime = None, time: int = 0, run: int = 0, log: str = "info"):

    set_logging(log)

    date = date.date() if date is not None else dt.date.today()

    variables = [
        "u-component_of_wind_height_above_ground",
        "v-component_of_wind_height_above_ground",
    ]
    try:
        get_gfs_hist(date, variables, time=time, run=run)
    except Exception as err:
        logging.exception(err)


if __name__ == "__main__":
    typer.run(main)
