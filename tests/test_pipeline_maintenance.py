import os
import unittest
from pprint import pprint
from unittest.mock import Mock, patch

from httmock import HTTMock, urlmatch

from qabot.lib.influxlib import InfluxLib
from qabot.pipeline_maintenance import PipelineMaintenance


class PipelineMaintenanceTestCase(unittest.TestCase):
    """Tests for test_pipeline_maintenance.py"""

    @urlmatch(
        netloc=r"(.*\.)?raw\.githubusercontent\.com$", path=r".*mockHomepageTest.*$"
    )
    def get_test_script_source_mock(self, url, request):
        # mock JS source code containing a Feature() line
        return """
            const fetch = require('node-fetch');

            Feature('MockHomepage').retry(2);

            Scenario('mock login @portal', async ({ home }) => {
                console.log('INFO: Test');
            });
        """

    mock_influx_query_results = [
        {
            "time": "2021-01-27T19:20:20Z",
            "ci_environment": "jenkins-dcp",
            "fail_count": 1.0,
            "pr_num": "123",
            "repo_name": "myRepo",
            "run_time": "0.492",
            "selenium_grid_sessions": "1",
            "suite_name": "MockHomepage",
            "test_name": "login_@portal",
        },
        {
            "time": "2021-01-27T19:20:21Z",
            "ci_environment": "jenkins-genomel",
            "fail_count": 1.0,
            "pr_num": "456",
            "repo_name": "myOtherRepo",
            "run_time": "0.326",
            "selenium_grid_sessions": "1",
            "suite_name": "MockHomepage",
            "test_name": "login_@portal_@topBarLogin",
        },
        {
            "time": "2021-01-26T12:00:00Z",
            "ci_environment": "jenkins-brain",
            "fail_count": 1.0,
            "pr_num": "456",
            "repo_name": "myOtherRepo",
            "run_time": "0.326",
            "selenium_grid_sessions": "1",
            "suite_name": "MockHomepage",
            "test_name": "login_@portal_@topBarLogin",
        },
    ]

    def setUp(self):
        # mock InfluxLib "query_ci_metrics" function
        influxdb = InfluxLib()

        def query_ci_metrics(influxdb, measurement, tags):
            # expect {"suite_name": "MockHomepage"}
            if tags["suite_name"] == "MockHomepage":
                return self.mock_influx_query_results
            else:
                return "could not identify the name of the feature"

        self.patch1 = patch.object(InfluxLib, "query_ci_metrics", query_ci_metrics)
        self.patch1.start()

        # initialize the ManifestsChecker instance
        self.pipeline_maintenance = PipelineMaintenance()

    def tearDown(self):
        self.patch1.stop()


if __name__ == "__main__":
    unittest.main()
