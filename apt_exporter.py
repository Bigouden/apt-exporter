#!/usr/bin/env python3
# coding: utf-8
# pyright: reportMissingImports=false

"""APT-Exporter"""

import logging
import os
import sys
import threading
import time
from datetime import datetime
from typing import Callable
from wsgiref.simple_server import make_server

import pytz
from prometheus_client import PLATFORM_COLLECTOR, PROCESS_COLLECTOR
from prometheus_client.core import REGISTRY, CollectorRegistry, Metric
from prometheus_client.exposition import _bake_output, _SilentHandler, parse_qs

APT_EXPORTER_NAME = os.environ.get("APT_EXPORTER_NAME", "apt-exporter")
APT_EXPORTER_LOGLEVEL = os.environ.get("APT_EXPORTER_LOGLEVEL", "INFO").upper()
APT_EXPORTER_TZ = os.environ.get("TZ", "Europe/Paris")


def make_wsgi_app(
    registry: CollectorRegistry = REGISTRY, disable_compression: bool = False
) -> Callable:
    """Create a WSGI app which serves the metrics from a registry."""

    def prometheus_app(environ, start_response):
        # Prepare parameters
        accept_header = environ.get("HTTP_ACCEPT")
        accept_encoding_header = environ.get("HTTP_ACCEPT_ENCODING")
        params = parse_qs(environ.get("QUERY_STRING", ""))
        headers = [
            ("Server", ""),
            ("Cache-Control", "no-cache, no-store, must-revalidate, max-age=0"),
            ("Pragma", "no-cache"),
            ("Expires", "0"),
            ("X-Content-Type-Options", "nosniff"),
        ]
        if environ["PATH_INFO"] == "/":
            status = "301 Moved Permanently"
            headers.append(("Location", "/metrics"))
            output = b""
        elif environ["PATH_INFO"] == "/favicon.ico":
            status = "200 OK"
            output = b""
        elif environ["PATH_INFO"] == "/metrics":
            status, tmp_headers, output = _bake_output(
                registry,
                accept_header,
                accept_encoding_header,
                params,
                disable_compression,
            )
            headers += tmp_headers
        else:
            status = "404 Not Found"
            output = b""
        start_response(status, headers)
        return [output]

    return prometheus_app


def start_wsgi_server(
    port: int,
    addr: str = "0.0.0.0",  # nosec B104
    registry: CollectorRegistry = REGISTRY,
) -> None:
    """Starts a WSGI server for prometheus metrics as a daemon thread."""
    app = make_wsgi_app(registry)
    httpd = make_server(addr, port, app, handler_class=_SilentHandler)
    thread = threading.Thread(target=httpd.serve_forever)
    thread.daemon = True
    thread.start()


start_http_server = start_wsgi_server

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
