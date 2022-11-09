#!/usr/bin/env python
import datetime as dt
import warnings
import logging

import typer
import xarray as xr

from utils import set_logging

GFS_BASE = "https://nomads.ncep.noaa.gov/dods"


def get_gfs(
    date: dt.date,
    varlist: list,
    run: int = 0,
    hour: int = None,
    res: str = "0p25",
    step: str = "1hr",
):

    date_str = date.strftime("%Y%m%d")
    url = f"{GFS_BASE}/gfs_{res}_{step}/gfs{date_str}/gfs_{res}_{step}_{run:02d}z"

    logging.info(url)

    with warnings.catch_warnings():
        # xarray/coding/times.py:119: SerializationWarning: Ambiguous reference date string
        warnings.filterwarnings(
            "ignore",
            category=xr.SerializationWarning,
            module=r"xarray",
        )
        with xr.open_dataset(url) as ds:
            # We use "nearest" in case of small precision problems
            if hour is None:
                dataset = ds[varlist]
                fout = f"{date_str}_{run:02}.nc"
            else:
                time = dt.time(hour=hour)
                dataset = ds[varlist].sel(
                    time=dt.datetime.combine(date, time), method="nearest"
                )
                fout = f"{date_str}_{run:02}_{hour:02}.nc"
            dataset.to_netcdf(fout)


def main(date: dt.datetime = None, hour: int = 0, run: int = 0, log: str = "info"):

    set_logging(log)

    date = date.date() if date is not None else dt.date.today()

    variables = ["ugrd10m", "vgrd10m"]
    try:
        get_gfs(date, variables, hour=hour, run=run)
    except Exception as err:
        logging.exception(err)


if __name__ == "__main__":
    typer.run(main)
