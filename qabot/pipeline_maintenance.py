import json
import os
import re
import logging
import datetime

import requests
from requests.exceptions import RequestException

from lib.slacklib import SlackLib
from lib.githublib import GithubLib
from lib.influxlib import InfluxLib
from lib.jenkinslib import JenkinsLib

from jenkins_job_invoker import JenkinsJobInvoker

logging.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"))
log = logging.getLogger(__name__)


class PipelineMaintenance:
    def __init__(self):
        """
        Aggregating various utility functions to increase productivity by automating CI pipeline maintenance tasks
        e.g., find out test suite failure trends (to support auto-replay), purge jenkins queue, facilitate debugging, etc.
        """
        self.ci_swimming_lanes = ["services", "releases"]
        self.cdis_public_bucket_base_url = (
            "https://cdistest-public-test-bucket.s3.amazonaws.com/"
        )

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
            # whitespaces need to be converted to underscore characters
            feature_name = feature_name.replace(" ", "_")
        else:
            raise Exception(
                f":facepalm: Could not find the CodeceptJs feature name in script `{test_script}`"
            )
        return feature_name

    def unquarantine_ci_env(self, ci_env_name):
        """
        Add ci-environment back to the source-of-truth pool of CI environments files:
         - services pool: https://cdistest-public-test-bucket.s3.amazonaws.com/jenkins-envs-services.txt
         - releases pool: https://cdistest-public-test-bucket.s3.amazonaws.com/jenkins-envs-releases.txt
        """
        bot_response = ""

        jji = JenkinsJobInvoker()
        log.info(f"Putting environment {ci_env_name} back into CI-envs pool...")
        json_params = {
            "ENVIRONMENT_NAME": ci_env_name,
        }
        str_params = json.dumps(json_params, separators=(",", ":"))
        bot_response = jji.invoke_jenkins_job(
            "unquarantine-ci-environment", "jenkins", str_params
        )
        if "something went wrong" in bot_response:
            return bot_response

        bot_response = f"The environment {ci_env_name} has been placed back into the CI-envs pool. :awesome-face:"
        return bot_response

    def quarantine_ci_env(self, ci_env_name):
        """
        Remove ci-environment from the source-of-truth pool of CI environments files:
         - services pool: https://cdistest-public-test-bucket.s3.amazonaws.com/jenkins-envs-services.txt
         - releases pool: https://cdistest-public-test-bucket.s3.amazonaws.com/jenkins-envs-releases.txt
        both files are restored every night by a cronjob.
        """
        bot_response = ""

        jji = JenkinsJobInvoker()
        log.info(f"Putting environment {ci_env_name} in quarantine...")
        json_params = {
            "ENVIRONMENT_NAME": ci_env_name,
        }
        str_params = json.dumps(json_params, separators=(",", ":"))
        bot_response = jji.invoke_jenkins_job(
            "quarantine-ci-environment", "jenkins", str_params
        )
        if "something went wrong" in bot_response:
            return bot_response

        bot_response = f"The environment {ci_env_name} has been placed under quarantine. :face_with_thermometer:"
        return bot_response

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

    def check_pool_of_ci_envs(self):
        bot_response = "Pool of CI environments :jenkins-fire: \n"

        for ci_pool in self.ci_swimming_lanes:
            bot_response += f"{ci_pool} pool :point_down:\n"
            bot_response += "```"
            try:
                response = requests.get(
                    f"{self.cdis_public_bucket_base_url}jenkins-envs-{ci_pool}.txt"
                )
                response.raise_for_status()
            except requests.exceptions.HTTPError as httperr:
                log.error(
                    "request to {0} failed due to the following error: {1}".format(
                        url, str(httperr)
                    )
                )
                return httperr
            bot_response += response.text
            bot_response += "```\n"
        return bot_response

    # TODO: This should empower auto-replay features
    # based on test suite's failure rate
    def react_to_jenkins_updates(self, jenkins_slack_msg_raw):
        log.debug(f"###  ## Slack msg from Jenkins: {jenkins_slack_msg_raw}")

    def ci_benchmarking(self, repo_name, pr_num, stage_name):
        bot_response = ""
        jl = JenkinsLib("jenkins")
        try:
            stage_duration = jl.get_duration_of_ci_pipeline_stage(
                repo_name, pr_num, stage_name
            )
            duration_raw = datetime.datetime.fromtimestamp(stage_duration / 1000.0)
            friendly_duration_format = duration_raw.strftime("%Mm and %Ss")
            bot_response += f"the {stage_name} stage from repo `{repo_name}` PR `#{pr_num}` took `{friendly_duration_format}` to run... :clock1:\n"
        except RequestException as err:
            err_msg = f"Could not fetch jenkins job metadata. Details: {err}"
            log.error(err_msg)
            bot_response += err_msg

        return bot_response

    def fetch_ci_failures(self, repo_name, pr_num, create_bug_tickets=False):
        bot_response = ""
        jl = JenkinsLib("jenkins")
        try:
            log.info("find the number of the last build...")
            job_num = jl.get_number_of_last_build(repo_name, pr_num)

            successful_tests, failed_tests = jl.fetch_tests_summary_from_pr_check(
                repo_name, pr_num, job_num
            )
            bot_response += f"The last build from this PR check contains \n"

            # let us just track the number of successfully executed tests
            successful_tests_count = len(successful_tests)
            bot_response += f" `{successful_tests_count} successful tests` \n"

            if len(failed_tests) > 0:
                bot_response += (
                    f"and the following {len(failed_tests)} tests failed: \n ```"
                )

                # let us explicitly return a list of the failing tests' names/description
                for failed_test in failed_tests:
                    bot_response += f"- {failed_test} \n"

                bot_response += f"```"

                bot_response += f"If you wish to consult a Subject Matter Expert (SME) to triage this CI failure, just run: \n"
                bot_response += (
                    f"``` @qa-bot who-do-I-ask-about <name-of-the-service> ``` \n"
                )

        except RequestException as err:
            err_msg = f"Could not fetch jenkins job metadata. Details: {err}"
            log.error(err_msg)
            bot_response += err_msg
        return bot_response


if __name__ == "__main__":
    pipem = PipelineMaintenance()
    # result = pipem.failure_rate_for_test_suite("test-portal-homepageTest")
    # result = pipem.quarantine_ci_env("jenkins-new")
    # result = pipem.check_pool_of_ci_envs()
    # result = pipem.ci_benchmarking("cdis-manifest", "3265", "K8sReset")
    # result = pipem.ci_benchmarking("gitops-qa", "1523", "RunTests")
    # negative test
    # result = pipem.ci_benchmarking("gen3-qa", "666", "Typo")
    result = pipem.fetch_ci_failures("gitops-qa", 1649)
    print(result)
