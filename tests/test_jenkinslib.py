import unittest

from lib.jenkinslib import JenkinsLib


class JenkinsLibTestCase(unittest.TestCase):
    """Tests for lib/jenkinsLib.py'."""

    def setUp(self):
        # initialize the JenkinsLib instance
        self.jenkins_lib = JenkinsLib("jenkins2")

    def test_invoke_jenkins_job(self):
        result = self.jenkins_lib.prepare_remote_build_request(
            "run-tests-on-environment",
            {
                "TARGET_ENVIRONMENT": "ci-env-1",
                "TEST_SUITE": "test-portal-homepageTest",
            },
        )

        # The result must create a prepared request similar to:
        # curl -u <user>:<jenkins_api_token> "https://jenkins2.planx-pla.net/job/run-tests-on-environment/buildWithParameters?token=<job_remote_build_token>&TARGET_ENVIRONMENT=ci-env-1&TEST_SUITE=test-portal-homepageTest"
        self.assertEqual(
            "https://jenkins2.planx-pla.net/job/run-tests-on-environment/buildWithParameters?token=abc123XYZ&TARGET_ENVIRONMENT=ci-env-1&TEST_SUITE=test-portal-homepageTest",
            result.url,
            "The URL of the prepared request does not match the expected url.",
        )


if __name__ == "__main__":
    unittest.main()
