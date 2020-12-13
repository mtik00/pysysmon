#!/usr/bin/env python3

import argparse
import os
import socket
import sys
import time

import psutil
from influxdb import InfluxDBClient

APP_HOSTNAME = os.getenv("APP_HOSTNAME", os.getenv("HOST", os.getenv("HOSTNAME")))
INFLUXDB_HOST = os.environ.get("INFLUXDB_HOST")
INFLUXDB_PORT = os.environ.get("INFLUXDB_PORT")
INFLUXDB_USERNAME = os.environ.get("INFLUXDB_USERNAME")
INFLUXDB_PASSWORD = os.environ.get("INFLUXDB_PASSWORD")
INFLUXDB_DBNAME = os.environ.get("INFLUXDB_DBNAME")


def parse_arguments(argv=sys.argv):
    parser = argparse.ArgumentParser("Export system hardware info to influx")
    parser.add_argument(
        "-d",
        "--debug",
        help="Only print measurements",
        action="store_true",
        default=False,
    )
    parser.add_argument(
        "-v",
        "--verbose",
        help="More verbose output",
        action="store_true",
        default=False,
    )

    return parser.parse_args(sys.argv[1:])


def get_memory():
    result = psutil.virtual_memory()
    return {
        "total": result.total,
        "used": result.used,
    }


def get_cpu():
    load_1, load_5, load_15 = psutil.getloadavg()

    return {
        "count": psutil.cpu_count(),
        "frequency": psutil.cpu_freq().current,
        "percent": psutil.cpu_percent(),
        "load_1": load_1,
        "load_5": load_5,
        "load_15": load_15,
    }


def get_temperature():
    """
    Returns the sensors temperature data.

    This function flattens the measurements for ingestion by InfluxDB.

    See here for an example:
        https://psutil.readthedocs.io/en/latest/#psutil.sensors_temperatures
    """
    result = psutil.sensors_temperatures()
    json_body = {}

    for sensor_name, measurements in result.items():
        for index, measurement in enumerate(measurements):
            measurement_label = (
                f"_{measurement.label.replace(' ', '_')}" if measurement.label else ""
            )
            measure_name = f"{sensor_name}{measurement_label}_{index}_current"
            json_body[measure_name] = measurement.current

    return json_body


def get_metics():
    return {
        "memory": get_memory(),
        "cpu": get_cpu(),
        "temperature": get_temperature(),
    }


def post_metrics(client: InfluxDBClient, metrics: dict, hostname: str):
    json_body = [
        {
            "measurement": "sysmon",
            "tags": {
                "hostname": hostname,
            },
            "fields": {
                "memory_total": metrics["memory"]["total"] or None,
                "memory_used": metrics["memory"]["used"] or None,
                "cpu_count": metrics["cpu"]["count"] or None,
                "cpu_frequency": metrics["cpu"]["frequency"] or None,
                "cpu_percent": metrics["cpu"]["percent"] or None,
                "cpu_load_1": metrics["cpu"]["load_1"] or None,
                "cpu_load_5": metrics["cpu"]["load_5"] or None,
                "cpu_load_15": metrics["cpu"]["load_15"] or None,
            },
        },
    ]

    # Temperatures are stored as nested structures, so we need to add them separate.
    for name, measurement in metrics["temperature"].items():
        json_body[0]["fields"][name] = measurement

    client.write_points(json_body)


class InfluxDBVars:
    def __init__(self):
        self.hostname = os.environ.get("INFLUXDB_HOST") or None
        self.port = os.environ.get("INFLUXDB_PORT") or None
        self.username = os.environ.get("INFLUXDB_USERNAME") or None
        self.password = os.environ.get("INFLUXDB_PASSWORD") or None
        self.dbname = os.environ.get("INFLUXDB_DBNAME") or None

    def __str__(self):
        return f"<InfluxDBVars hostname={self.hostname} port={self.port} username={self.username} password={'***' if self.password else self.password} dbname={self.dbname}>"

    def valid(self):
        """Returns whether or not we have enough variables defined to attempt to make a connection."""
        return self.hostname and self.port and self.dbname


class DBClient:
    def __init__(
        self,
        db_vars: InfluxDBVars,
        debug: bool = False,
    ):
        self.debug = debug

        if (not self.debug) and (not db_vars.valid()):
            print(str(db_vars))
            print(
                "WARNING: InfluxDB connection vars are not valid; enabling debug mode"
            )
            self.debug = True

        if not self.debug:
            self.client = InfluxDBClient(
                host=INFLUXDB_HOST,
                port=INFLUXDB_PORT,
                username=INFLUXDB_USERNAME,
                password=INFLUXDB_PASSWORD,
                ssl=False,
            )
            self.client.switch_database(INFLUXDB_DBNAME)

    def write_points(self, json_body):
        if self.debug:
            print(json_body)
        else:
            self.client.write_points(json_body)


def main():
    args = parse_arguments(sys.argv[1:])

    db_vars = InfluxDBVars()
    client = DBClient(db_vars, args.debug)

    hostname = APP_HOSTNAME or socket.gethostname()

    while True:
        metrics = get_metics()
        post_metrics(client, metrics, hostname)

        if args.verbose and (not args.debug):
            print(".", end="", flush=True)

        time.sleep(10)


if __name__ == "__main__":
    main()
