#!/usr/bin/env python
import datetime as dt
import logging

import typer
import xarray as xr

GFS_BASE = "https://nomads.ncep.noaa.gov/dods"


def set_logging(loglevel: str):
    numeric_level = getattr(logging, loglevel.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError("Invalid log level: %s" % loglevel)
    logging.basicConfig(level=numeric_level)


def get_gfs(
    date: dt.date,
    hour: int,
    varlist: list,
    run: int = 0,
    res: str = "0p25",
    step: str = "1hr",
):

    date_str = date.strftime("%Y%m%d")
    url = f"{GFS_BASE}/gfs_{res}_{step}/gfs{date_str}/gfs_{res}_{step}_{run:02d}z"

    time = dt.time(hour=hour)

    logging.info(url)

    with xr.open_dataset(url) as ds:
        # We use "nearest" in case of small precision problems
        dataset = ds[varlist].sel(
            time=dt.datetime.combine(date, time), method="nearest"
        )
        dataset.to_netcdf(f"{date_str}_{run:02}_{hour:02}.nc")


def main(date: dt.datetime = None, hour: int = 0, run: int = 0, log: str = "info"):

    set_logging(log)

    date = date.date() if date is not None else dt.date.today()

    variables = ["ugrd10m", "vgrd10m"]
    try:
        get_gfs(date, hour, variables, run=run)
    except Exception as err:
        logging.exception(err)


if __name__ == "__main__":
    typer.run(main)
