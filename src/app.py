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

    return parser.parse_args(sys.argv[1:])


def get_memory():
    result = psutil.virtual_memory()
    return {
        "total": result.total,
        "used": result.used,
    }


def get_cpu():
    return {
        "count": psutil.cpu_count(),
        "frequency": psutil.cpu_freq().current,
        "percent": psutil.cpu_percent(),
    }

def get_temperature():
    result = psutil.sensors_temperatures()
    json_body = {}

    for temp_description, items in result.items():
        values = [{"label": value.label, "current": value.current, "high": value.high, "critical": value.critical} for value in items]
        json_body[temp_description] = values
    
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
                "memory_total": metrics["memory"]["total"],
                "memory_used": metrics["memory"]["used"],
                "cpu_count": metrics["cpu"]["count"],
                "cpu_frequency": metrics["cpu"]["frequency"],
                "cpu_percent": metrics["cpu"]["percent"],
                "temperatures": metrics["temperature"],
            },
        },
    ]
    client.write_points(json_body)


class DBClient:
    def __init__(self, debug=False):
        self.debug = debug

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
    client = DBClient(args.debug)

    hostname = APP_HOSTNAME or socket.gethostname()

    while True:
        metrics = get_metics()
        post_metrics(client, metrics, hostname)

        if not args.debug:
            print(".", end="", flush=True)

        time.sleep(10)


if __name__ == "__main__":
    main()
