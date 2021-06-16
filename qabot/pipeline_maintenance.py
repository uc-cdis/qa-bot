import json
import os
import re
import logging
from lib.slacklib import SlackLib
from lib.githublib import GithubLib
from lib.influxlib import InfluxLib

logging.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"))
log = logging.getLogger(__name__)


class PipelineMaintenance:
    def __init__(self):
        """
        Aggregating various utility functions to increase productivity by automating CI pipeline maintenance tasks
        e.g., find out test suite failure trends (to support auto-replay), purge jenkins queue, facilitate debugging, etc.
        """
        ci_swimming_lanes = ["services", "environments", "nightly_build"]

    def get_slacklib(self):
        return SlackLib()

    def get_githublib(self):
        return GithubLib()

    def get_influxlib(self, host):
        return InfluxLib(host=host)

    def failure_rate_for_test_suite(self, test_suite_name):
        """
        Fetch metrics from time-series db and determine how often a given test suite failed
        across different PRs and repositories
        """
        bot_response = ""

        influxlib = self.get_influxlib(host="localhost")
        print(influxlib.query_ci_metrics("fail_count", {"suite_name": test_suite_name}))

        return bot_response


if __name__ == "__main__":
    pipem = PipelineMaintenance()
    result = pipem.failure_rate_for_test_suite("Homepage")
    print(result)
