import json
import os
import re
import logging

import requests

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
        ci_swimming_lanes = ["services", "releases"]

    def get_slacklib(self):
        return SlackLib()

    def get_githublib(self):
        return GithubLib()

    def get_influxlib(self):
        return InfluxLib()

    def _get_test_script_source(self, test_script):
        try:
            # try to find the test script that corresponds to the test suite name
            test_script_lookup = requests.get(
                f"https://raw.githubusercontent.com/uc-cdis/gen3-qa/master/{test_script}"
            )
            test_script_lookup.raise_for_status()
            test_script_source = test_script_lookup.text
        except requests.exceptions.HTTPError as httperr:
            raise Exception(
                f"Could not fetch the source code for the {test_script} script: {str(httperr)}"
            )
        return test_script_source

    def _get_feature_name_from_source(self, test_script_source):
        # lookup the Feature() line in the source code
        match = re.search("Feature\('(.*)'\).*", test_script_source)
        if match:
            feature_name = match.group(1)
            log.info(f"Found feature name: {feature_name}")
        else:
            raise Exception(
                f":facepalm: Could not find the CodeceptJs feature name in script `{test_script}`"
            )
        return feature_name

    def failure_rate_for_test_suite(self, test_suite_name):
        """
        Fetch metrics from time-series db and determine how often a given test suite failed
        across different PRs and repositories
        """
        bot_response = ""

        log.info(f"Fetching feature name from codeceptjs script: {test_suite_name}")
        # converting label to test script path + file name
        test_label = test_suite_name.split("-")
        test_script = "suites/" + test_label[1] + "/" + test_label[2] + ".js"

        try:
            # try to find the test script that corresponds to the test suite name
            test_script_source = self._get_test_script_source(test_script)
        except Exception as err:
            log.error(str(err))
            return str(err)

        log.debug(f"Looking for the name of the feature in: {test_script}")
        try:
            feature_name = self._get_feature_name_from_source(test_script_source)
        except Exception as err:
            log.error(str(err))
            return str(err)

        influxlib = self.get_influxlib()
        data_points = influxlib.query_ci_metrics(
            "fail_count", {"suite_name": feature_name}
        )
        if data_points:
            # crunch numbers here
            test_suite_failures = {}

            # iterate through influxdb's data points obtained from query response
            for point in data_points:
                # initialize nested-dictionary of PRs inside the repo_name key if it is not yet created
                if point["repo_name"] not in test_suite_failures:
                    test_suite_failures[point["repo_name"]] = {}

                # Count failed PRs per repo_name
                repo_key = test_suite_failures[point["repo_name"]]
                repo_key.__setitem__(
                    point["pr_num"], int(repo_key[point["pr_num"]]) + 1
                ) if point["pr_num"] in repo_key else repo_key.__setitem__(
                    point["pr_num"], 1
                )

            log.debug(f"###  ## FINAL test_suite_failures: {test_suite_failures}")

            # prepare bot response
            bot_response += (
                f":information_source: The test suite {test_suite_name} failed:\n"
            )
            bot_response += "```"
            # each row of the report should print a msg similar to:
            # - 1 time(s) on PR-123 from repo myRepo
            for repo_name, prs in test_suite_failures.items():
                for pr_num, failure_count in prs.items():
                    bot_response += f"- {failure_count} time(s) on PR-{pr_num} from repo {repo_name}\n"
            bot_response += "```"
        else:
            bot_response += (
                "could not find any `fail_count` metrics for this test suite :shrug:"
            )

        return bot_response


if __name__ == "__main__":
    pipem = PipelineMaintenance()
    result = pipem.failure_rate_for_test_suite("test-portal-homepageTest")
    print(result)
