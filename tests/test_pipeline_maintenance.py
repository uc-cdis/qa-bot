from httmock import urlmatch, HTTMock
import unittest
import os
from unittest.mock import Mock, patch
from pprint import pprint

from qabot.pipeline_maintenance import PipelineMaintenance
from lib.influxlib import InfluxLib


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

    def test_failure_rate_for_test_suite(self):
        with HTTMock(self.get_test_script_source_mock):
            result = self.pipeline_maintenance.failure_rate_for_test_suite(
                "test-portal-mockHomepageTest"
            )

            self.assertEqual(
                ":information_source: The test suite test-portal-mockHomepageTest failed:\n```- 1 time(s) on PR-123 from repo myRepo\n- 2 time(s) on PR-456 from repo myOtherRepo\n```",
                result,
                "Must show statistics on how often the test suite failed across diff repos/PRs",
            )


if __name__ == "__main__":
    unittest.main()
