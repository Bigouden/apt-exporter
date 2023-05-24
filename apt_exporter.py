#!/usr/bin/env python3
# coding: utf-8
# pyright: reportMissingImports=false

"""APT-Exporter"""

import logging
import os
import sys
import time
from datetime import datetime

import pytz
from prometheus_client import PLATFORM_COLLECTOR, PROCESS_COLLECTOR, start_http_server
from prometheus_client.core import REGISTRY, Metric

APT_EXPORTER_NAME = os.environ.get("APT_EXPORTER_NAME", "apt-exporter")
APT_EXPORTER_LOGLEVEL = os.environ.get("APT_EXPORTER_LOGLEVEL", "INFO").upper()
APT_EXPORTER_TZ = os.environ.get("TZ", "Europe/Paris")

# Logging Configuration
try:
    pytz.timezone(APT_EXPORTER_TZ)
    logging.Formatter.converter = lambda *args: datetime.now(
        tz=pytz.timezone(APT_EXPORTER_TZ)
    ).timetuple()
    logging.basicConfig(
        stream=sys.stdout,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%d/%m/%Y %H:%M:%S",
        level=APT_EXPORTER_LOGLEVEL,
    )
except pytz.exceptions.UnknownTimeZoneError:
    logging.Formatter.converter = lambda *args: datetime.now(
        tz=pytz.timezone("Europe/Paris")
    ).timetuple()
    logging.basicConfig(
        stream=sys.stdout,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%d/%m/%Y %H:%M:%S",
        level="INFO",
    )
    logging.error("TZ invalid : %s !", APT_EXPORTER_TZ)
    os._exit(1)
except ValueError:
    logging.basicConfig(
        stream=sys.stdout,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%d/%m/%Y %H:%M:%S",
        level="INFO",
    )
    logging.error("APT_EXPORTER_LOGLEVEL invalid !")

# Check APT_EXPORTER_PORT
try:
    APT_EXPORTER_PORT = int(os.environ.get("APT_EXPORTER_PORT", "8123"))
except ValueError:
    logging.error("APT_EXPORTER_PORT must be int !")
    os._exit(1)

# Check DPKG_STATUS_FILE
DPKG_STATUS_FILE = os.environ.get("DPKG_STATUS_FILE", "/var/lib/dpkg/status")
if not os.path.isfile(DPKG_STATUS_FILE):
    logging.error("Invalid DPKG_STATUS_FILE : %s", DPKG_STATUS_FILE)
    os._exit(1)

# METRICS Configuration
METRICS = [
    {"name": "apt_package", "description": "APT Package Information", "type": "gauge"}
]

# REGISTRY Configuration
REGISTRY.unregister(PROCESS_COLLECTOR)
REGISTRY.unregister(PLATFORM_COLLECTOR)
REGISTRY.unregister(REGISTRY._names_to_collectors["python_gc_objects_collected_total"])


class AptCollector:
    """APT Collector Class"""

    def __init__(self):
        pass

    @staticmethod
    def _parse(expr, lines):
        """Parse Lines"""
        try:
            return [
                line.replace(expr, b"", 1) for line in lines if line.startswith(expr)
            ][0]
        except IndexError:
            logging.error("Invalid DPKG_STATUS_FILE Format !")
            os._exit(1)

    def get_metrics(self):
        """Retrieve Prometheus Metrics"""
        res = []
        metric_name = "apt_package"
        metric_description = [
            metric["description"] for metric in METRICS if metric_name == metric["name"]
        ][0]
        metric_type = [
            metric["type"] for metric in METRICS if metric_name == metric["name"]
        ][0]
        with open(DPKG_STATUS_FILE, "rb") as filename:
            file_content = filename.read().strip()
            packages = file_content.split(b"\n\n")
        for package in packages:
            metric_labels = {}
            lines = package.split(b"\n")
            metric_labels["package"] = self._parse(b"Package: ", lines).decode()
            metric_labels["version"] = self._parse(b"Version: ", lines).decode()
            metric_labels["description"] = self._parse(b"Description: ", lines).decode()
            metric_labels["status"] = self._parse(b"Status: ", lines).decode()
            metric_labels["section"] = self._parse(b"Section: ", lines).decode()
            metric_labels["priority"] = self._parse(b"Priority: ", lines).decode()
            res.append(
                {
                    "name": metric_name,
                    "description": metric_description,
                    "type": metric_type,
                    "labels": metric_labels,
                }
            )
        return res

    def collect(self):
        """Collect Prometheus Metrics"""
        metrics = self.get_metrics()
        for metric in metrics:
            labels = {"job": APT_EXPORTER_NAME}
            labels |= metric["labels"]
            prometheus_metric = Metric(
                metric["name"], metric["description"], metric["type"]
            )
            prometheus_metric.add_sample(metric["name"], value=1, labels=labels)
            yield prometheus_metric


def main():
    """Main Function"""
    logging.info("Starting APT Exporter on port %s.", APT_EXPORTER_PORT)
    logging.debug("APT_EXPORTER_PORT: %s.", APT_EXPORTER_PORT)
    logging.debug("APT_EXPORTER_NAME: %s.", APT_EXPORTER_NAME)
    # Start Prometheus HTTP Server
    start_http_server(APT_EXPORTER_PORT)
    # Init AptCollector
    REGISTRY.register(AptCollector())
    # Infinite Loop
    while True:
        time.sleep(1)


if __name__ == "__main__":
    main()
