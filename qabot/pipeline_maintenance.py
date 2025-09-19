import datetime
import json
import logging
import os
import re
import subprocess
import time

import requests
from ascii_graph import Pyasciigraph
from requests.exceptions import RequestException

from qabot.lib.githublib import GithubLib
from qabot.lib.influxlib import InfluxLib
from qabot.lib.jenkinslib import JenkinsLib
from qabot.lib.jiralib import JiraLib
from qabot.lib.slacklib import SlackLib

logging.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"))
log = logging.getLogger(__name__)


def singleton(cls):
    instances = {}

    def getinstance():
        if cls not in instances:
            instances[cls] = cls()
        return instances[cls]

    return getinstance


@singleton
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
        self.in_memory_ci_stats = {}
        self.in_memory_ci_stats["repos"] = {}
        self.ci_env_pools = {
            "services": [
                "jenkins-brain",
                "jenkins-blood",
                "jenkins-dcp",
                "jenkins-genomel",
                "jenkins-niaid",
            ],
            "releases": [
                "jenkins-new",
                "jenkins-new-1",
                "jenkins-new-2",
                "jenkins-new-3",
                "jenkins-new-4",
            ],
        }

    def get_slacklib(self):
        return SlackLib()

    def get_githublib(self):
        return GithubLib()

    def _get_ci_env_pool(self, ci_env):
        if ci_env in self.ci_env_pools["services"]:
            return "services"
        elif ci_env in self.ci_env_pools["releases"]:
            return "releases"
        else:
            raise Exception(f"Invalid CI Environment value - {ci_env}")

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
                f":facepalm: Could not find the CodeceptJs feature name in script `{test_script_source}`"
            )
        return feature_name

    def unquarantine_ci_env(self, ci_env_name):
        try:
            command = ["kubectl", "label", "namespace", ci_env_name, "quarantine-"]
            result = subprocess.run(command, capture_output=True, text=True, check=True)
            log.info(f"Output from command: {result.stdout}")
            command = [
                "kubectl",
                "label",
                "namespace",
                ci_env_name,
                "teardown=true",
                "--overwrite",
            ]
            result = subprocess.run(command, capture_output=True, text=True, check=True)
            log.info(f"Output from command: {result.stdout}")
            return f"The environment {ci_env_name} has been removed from quarantine. :awesome-face:"
        except subprocess.CalledProcessError as e:
            log.info(e.stderr)
            return f"Failed to unquarantine environment {ci_env_name}, please try again or contact QA team"

    def quarantine_ci_env(self, ci_env_name):
        command = [
            "kubectl",
            "label",
            "namespace",
            ci_env_name,
            "quarantine=true",
            "--overwrite",
        ]
        try:
            result = subprocess.run(command, capture_output=True, text=True, check=True)
            log.info(f"Output from command: {result.stdout}")
            return f"The environment {ci_env_name} has been placed under quarantine. :face_with_thermometer:"
        except subprocess.CalledProcessError as e:
            log.info(e.stderr)
            return f"Failed to quarantine environment {ci_env_name}, please try again or contact QA team"

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

        influxlib = InfluxLib()
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
                (
                    repo_key.__setitem__(
                        point["pr_num"], int(repo_key[point["pr_num"]]) + 1
                    )
                    if point["pr_num"] in repo_key
                    else repo_key.__setitem__(point["pr_num"], 1)
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
                        self.cdis_public_bucket_base_url, str(httperr)
                    )
                )
                return httperr
            bot_response += response.text
            bot_response += "```\n"
        return bot_response

    def _populate_ci_stats(self, msg_event_ts, repo_name, pr_number, ci_results):
        msg_timestamp = datetime.datetime.fromtimestamp(msg_event_ts)
        print(f"### ## msg_timestamp: {msg_timestamp}")

        # purge ci stats from the past whenever a new jenkins msg is sent on the next day
        # if we don't do this, the in-memory dict will keep growing indefinitely
        if "latest_entry_ts" in self.in_memory_ci_stats:
            date1 = self.in_memory_ci_stats["latest_entry_ts"]
            date2 = msg_timestamp
            # diff between timestamps
            diff_between_timestamps = abs(date2 - date1).days
            log.debug(f"### ## diff between timestamps: {diff_between_timestamps}")

            if diff_between_timestamps > 0:
                # reset everything so we don't store more than a day's worth of CI stats
                log.warn("Resetting CI stats...")
                self.in_memory_ci_stats["repos"] = {}
        else:
            self.in_memory_ci_stats["latest_entry_ts"] = msg_timestamp

        if repo_name not in self.in_memory_ci_stats:
            self.in_memory_ci_stats["repos"][repo_name] = {}

        stats_key = "failed" if "failed" in ci_results else "successful"
        if stats_key not in self.in_memory_ci_stats["repos"][repo_name]:
            self.in_memory_ci_stats["repos"][repo_name][stats_key] = {}

        pr = f"PR-{pr_number}"
        repo_stats_mapping = self.in_memory_ci_stats["repos"][repo_name][stats_key]
        (
            repo_stats_mapping.__setitem__(pr, repo_stats_mapping[pr] + 1)
            if pr in repo_stats_mapping
            else repo_stats_mapping.__setitem__(pr, 1)
        )

    def _identify_pr_details_from_jenkins_notification(self, jenkins_msg):
        # identify repo_name and pr_number in the msg
        log.debug(f"### ## jenkins_msg: {jenkins_msg}")
        matchstring = ".*https:\/\/github.com\/uc-cdis\/(.*)\/pull\/(.*)>.*"
        regex_result = re.match(matchstring, jenkins_msg)

        if regex_result:
            log.info(f"repo_name from CI notification: {regex_result.group(1)}")
            log.info(f"pr_number from CI notification: {regex_result.group(2)}")
            repo_name = regex_result.group(1)
            pr_number = regex_result.group(2)

            return repo_name, pr_number
        else:
            log.warn(
                "invalid CI notification, can't identify repo_name and pr_number. Just ignore... meh."
            )
            return None, None

    # TODO: This should empower auto-replay features
    # based on test suite's failure rate
    def react_to_jenkins_updates(self, jenkins_slack_msg_raw):
        log.debug(f"###  ## Slack msg from Jenkins: {jenkins_slack_msg_raw}")
        msg_event_ts = int(jenkins_slack_msg_raw["event_ts"].split(".")[0])

        bot_response = ""
        actual_msg = jenkins_slack_msg_raw["attachments"][0]["fields"][0]["value"]

        # if a CI notification is sent to the #nightly-builds channel
        if jenkins_slack_msg_raw["channel"] == "C01TS6PDMRT":
            log.info("new Jenkins msg on the #nightly-builds channel...")
            bot_response += "Additional nightly-build stats :moon: \n"
            repo_name, pr_number = self._identify_pr_details_from_jenkins_notification(
                actual_msg
            )

            if repo_name and pr_number:
                bot_response += self.ci_benchmarking(repo_name, pr_number, "K8sReset")
                bot_response += self.ci_benchmarking(repo_name, pr_number, "RunTests")
                # wait for the remaining pipeline stages (post-RunTests)
                time.sleep(60)
                ci_results = self.fetch_ci_failures(repo_name, pr_number)
                bot_response += ci_results
                log.info("populating ci stats....")
                self._populate_ci_stats(msg_event_ts, repo_name, pr_number, ci_results)

                return bot_response
        # if a CI notification is sent to the #gen3-qa-notifications channel
        elif jenkins_slack_msg_raw["channel"] == "C0183EFTPLG":
            log.info("new Jenkins msg on the #gen3-qa-notifications channel...")
            repo_name, pr_number = self._identify_pr_details_from_jenkins_notification(
                actual_msg
            )

            if repo_name and pr_number:
                ci_results = self.fetch_ci_failures(repo_name, pr_number)
                log.info("populating ci stats....")
                self._populate_ci_stats(msg_event_ts, repo_name, pr_number, ci_results)

    def ci_benchmarking(self, repo_name, pr_num, stage_name):
        bot_response = ""
        jl = JenkinsLib("jenkins")
        try:
            stage_duration = jl.get_duration_of_ci_pipeline_stage(
                repo_name, pr_num, stage_name
            )
            duration = (
                str(datetime.timedelta(milliseconds=stage_duration))
                .split(".")[0]
                .split(":")
            )
            friendly_duration_format = " ".join(
                [i + j for i, j in zip(duration, ["h", "m", "s"])]
            )
            bot_response += f"the {stage_name} stage from repo `{repo_name}` PR `#{pr_num}` took `{friendly_duration_format}` to run... :clock1:\n"
        except RequestException as err:
            err_msg = f"Could not fetch jenkins job metadata. Details: {err}"
            log.error(err_msg)
            bot_response += err_msg

        return bot_response

    def fetch_ci_failures(self, repo_name, pr_num):
        bot_response = ""
        jl = JenkinsLib("jenkins")
        try:
            log.info("find the number of the last build...")
            job_num = jl.get_number_of_last_build(repo_name, pr_num)

            if job_num == None:
                bot_response += "Could not fetch test results form this PR check. The Blueocean workspace is no longer available."
                return bot_response

            successful_tests, failed_tests = jl.fetch_tests_summary_from_pr_check(
                repo_name, pr_num, job_num
            )
            # the latest PR build is still in flight
            if successful_tests == None and failed_tests == None:
                bot_response += "The latest PR build is still in flight... keep an eye on #gen3-qa-notifications :eye: "
                return bot_response

            bot_response += f"The last build from this PR check contains \n"

            # let us just track the number of successfully executed tests
            successful_tests_count = len(successful_tests)
            # singular/plural logic due to OCD
            test_tests = "test" if successful_tests_count == 1 else "tests"
            bot_response += f" `{successful_tests_count} successful {test_tests}` \n"

            if len(failed_tests) > 0:
                bot_response += (
                    f"and the following {len(failed_tests)} tests failed: \n"
                )
                # start formatted text here
                bot_response += "```"

                # let us explicitly return a list of the failing tests' names/description
                for failed_test in failed_tests:
                    bot_response += f"- {failed_test} \n"
                # end of formatted text
                bot_response += "```\n"

                bot_response += f"If you wish to consult a Subject Matter Expert (SME) to triage this CI failure, just run: \n"
                bot_response += (
                    f"``` @qa-bot who-do-I-ask-about <name-of-the-service> ``` \n"
                )

        except RequestException as err:
            err_msg = f"Could not fetch jenkins job metadata. Details: {err}"
            log.error(err_msg)
            bot_response += err_msg
        return bot_response

    def create_ticket(self, type, args=""):
        # handle arguments
        jira_ticket_params = json.loads(args)

        type = type.capitalize()

        bot_response = ""
        jil = JiraLib()
        try:
            jira_id = jil.create_ticket(
                jira_ticket_params["title"],
                jira_ticket_params["description"],
                type,
                jira_ticket_params["assignee"],
            )
        except Exception as err:
            log.error(str(err))
            return f"Could not create the bug ticket :sad-super-sad: {str(err)}"

        bot_response = (
            f"JIRA bug ticket {jira_id} has been created successfully. :tada: \n"
        )
        bot_response += (
            f"click here to see the ticket: {jil.jira_server}/browse/{jira_id} \n"
        )
        return bot_response

    def get_repo_sme(self, repo_name):
        contents_url = (
            "https://api.github.com/repos/uc-cdis/qa-bot/contents/qabot/repo_owner.json"
        )
        contents_url_info = requests.get(
            contents_url,
            headers={
                "Authorization": "token {}".format(os.environ["GITHUB_TOKEN"].strip()),
                "Accept": "application/vnd.github.v3+json",
            },
        ).json()
        download_url = contents_url_info["download_url"]
        r = requests.get(
            download_url,
            headers={
                "Authorization": "token {}".format(os.environ["GITHUB_TOKEN"].strip())
            },
        )
        if r.status_code != 200:
            raise Exception(
                "Unable to get file repo_owner.json at `{}`: got code {}.".format(
                    download_url[: download_url.index("token")],
                    r.status_code,
                )
            )
        repos_and_owners = r.json()
        try:
            bot_response = f"primary: {repos_and_owners[repo_name]['primary']} & secondary: {repos_and_owners[repo_name]['secondary']}"
        except KeyError:
            bot_response = f"hey :sweat_smile:, there's no point of contact defined for `{repo_name}`, please update the repo_owner.json file or just go to #gen3-dev-oncall ."
        return bot_response

    def get_ci_summary(self):
        print(f"### ## self.in_memory_ci_stats: {self.in_memory_ci_stats}")

        prs_tuples = {"failed": [], "successful": []}
        repos_list = self.in_memory_ci_stats["repos"].keys()

        for result in ["failed", "successful"]:
            for repo in repos_list:
                per_repo_counter = 0
                if result in self.in_memory_ci_stats["repos"][repo]:
                    for pr in self.in_memory_ci_stats["repos"][repo][result].keys():
                        per_repo_counter += self.in_memory_ci_stats["repos"][repo][
                            result
                        ][pr]
                prs_tuples[result].append((repo, per_repo_counter))

        failed_prs = prs_tuples["failed"]

        bot_response = "CI Summary:"
        output = "```"
        graph = Pyasciigraph()
        for line in graph.graph("Failed PR checks:", failed_prs):
            output += line + "\n"

        successful_prs = prs_tuples["successful"]

        output += "\n"
        for line in graph.graph("Successful PR checks:", successful_prs):
            output += line + "\n"

        output += "```"
        bot_response += output
        return bot_response

    def replay_pr(self, repo_name, pr_number, labels=[]):
        """
        Replay a Pull Request like a boss
        """
        githublib = GithubLib(repo=repo_name)
        try:
            if " " in labels:
                raise Exception("Whitespace found in comma-separated list of labels")
            if len(labels) > 0:
                labels = labels.split(",")
                log.info("applying labels...")
                for i, label in enumerate(labels):
                    # only override all labels on the first iteration
                    override_all = i == 0
                    githublib.set_label_to_pr(
                        int(pr_number), label.replace("*", ""), override_all
                    )
                    log.debug("applied label: {}".format(label))
            else:
                log.info("Replaying PR without labels...")
        except Exception as err:
            return "Something wrong happened :facepalm:. Deets: {}".format(err)

        bot_response = githublib.replay_pr(pr_number)
        return bot_response


if __name__ == "__main__":
    # pipem = PipelineMaintenance()
    # result = pipem.failure_rate_for_test_suite("test-portal-homepageTest")
    # result = pipem.quarantine_ci_env("jenkins-new")
    # result = pipem.check_pool_of_ci_envs()
    # result = pipem.ci_benchmarking("cdis-manifest", "3265", "K8sReset")
    # result = pipem.ci_benchmarking("gitops-qa", "1523", "RunTests")
    # negative test
    # result = pipem.ci_benchmarking("gen3-qa", "666", "Typo")
    # result = pipem.fetch_ci_failures("gitops-qa", 1649)
    # result = pipem.fetch_ci_failures("gen3-qa", 700)
    # result = pipem.create_bug_ticket(
    #    title="this PR-123 is failing",
    #    description="help, this is failing",
    #    assignee="Atharva Rane",
    # )
    # result = pipem.get_repo_sme("arborist")
    pipem1 = PipelineMaintenance()
    pipem1.react_to_jenkins_updates(
        {
            "subtype": "bot_message",
            "text": "",
            "suppress_notification": False,
            "attachments": [
                {
                    "fallback": "Successful CI run for <https://github.com/uc-cdis/cdis-manifest/pull/3593> :tada:",
                    "id": 1,
                    "color": "439FE0",
                    "fields": [
                        {
                            "title": "",
                            "value": "Successful CI run for <https://github.com/uc-cdis/cdis-manifest/pull/3593> :tada:",
                            "short": False,
                        }
                    ],
                    "mrkdwn_in": ["pretext", "text", "fields"],
                }
            ],
            "channel": "C01TS6PDMRT",
            "event_ts": "1633005588.151600",
            "ts": "1633106721.151600",
        }
    )
    pipem2 = PipelineMaintenance()
    pipem2.react_to_jenkins_updates(
        {
            "subtype": "bot_message",
            "text": "",
            "suppress_notification": False,
            "attachments": [
                {
                    "fallback": "CI Failure on <https://github.com/uc-cdis/gitops-qa/pull/1668> :facepalm: running on jenkins-dcp :jenkins:.",
                    "id": 1,
                    "color": "439FE0",
                    "fields": [
                        {
                            "title": "",
                            "value": "CI Failure on <https://github.com/uc-cdis/gitops-qa/pull/1668> :facepalm: running on jenkins-dcp :jenkins:.",
                            "short": False,
                        }
                    ],
                    "mrkdwn_in": ["pretext", "text", "fields"],
                }
            ],
            "channel": "C01TS6PDMRT",
            "event_ts": "1633178730.151600",
            "ts": "1633106721.151600",
        }
    )
    # pipem.in_memory_ci_stats = {}
    # trying with different instances to test singleton
    pipem3 = PipelineMaintenance()
    result = pipem3.get_ci_summary()
    print(result)
