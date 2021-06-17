import requests
import json
import logging
import os

from influxdb import InfluxDBClient
from influxdb.exceptions import InfluxDBClientError, InfluxDBServerError
from requests.exceptions import RequestException

logging.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"))
log = logging.getLogger(__name__)


class InfluxLib:
    """
    Handle interactions with InfluxDB
    """

    _instance = None

    def __new__(cls, host="influxdb", port=8086):
        if cls._instance is None:
            log.info(f"Creating the InfluxDB client object targeting {host}:{port}...")
            cls._instance = super(InfluxLib, cls).__new__(cls)
            # initialize instance attributes
            cls._instance.client = InfluxDBClient(host, port)
            cls._instance.client.switch_database("ci_metrics")
        return cls._instance

    def _run_query(self, query, tags, days_ago):
        log.debug(f"running query: {query} WHERE time > now() - {days_ago}d")
        results = self.client.query(f"{query} WHERE time > now() - {days_ago}d")
        return list(results.get_points(tags=tags))

    def query_ci_metrics(self, measurement, tags):
        try:
            points = self._run_query(f'SELECT * FROM "{measurement}"', tags, 14)

            # If zero metrics are found for this query/tags in a 2-week time frame
            # go further back a few months
            if len(points) == 0:
                points = self._run_query(f'SELECT * FROM "{measurement}"', tags, 120)

            if len(points) > 0:
                if logging.getLogger().level == logging.DEBUG:
                    for point in points:
                        log.debug(f"point {point}")
                return points
            else:
                log.warn(
                    "could not find any metrics with this query + tags. Return empty response."
                )
                return None
        except (RequestException, InfluxDBClientError, InfluxDBServerError) as err:
            log.error(f"request with query {query} failed. Details: {err}")
            return None
        return results
