import logging
import os
import json
from pprint import pprint

from qabot.parse_codeowners import EnvironmentsManager
from qabot.jenkins_job_invoker import JenkinsJobInvoker
from qabot.lib.githublib import GithubLib

logging.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"))
log = logging.getLogger(__name__)


class ReleaseManager:
    def __init__(self):
        """
        Manage releases to automate the QA engineers out of this job (so they can work on innovation and other tech debt items)
        """
        self.githublib = self.get_githublib()

    def get_githublib(self):
        return GithubLib()

    def find_latest_release(self):
        # find latest published gen3 release
        github_client = self.get_githublib()

        # TODO: Make sure only PMs are allowed to invoke this command
        # Correlate Slack user ID and Slack Full Name with the github user id in CODEOWNERS

        # TODO: Figure out a better way to identify the latest release
        # Identify most recent year folder among published releases
        year_folders = github_client.list_files_in_dir("releases")
        latest_year = sorted(year_folders)[-1]
        log.info("latest_year: {}".format(latest_year))
        # Identify most recent month folder among published releases
        month_folders = github_client.list_files_in_dir(
            "releases/{}".format(latest_year)
        )
        latest_month = sorted(month_folders)[-1]

        latest_release = "{}.{}".format(latest_year, latest_month)

        log.info("The latest published Gen3 Release is {}".format(latest_release))

        return latest_release

    def roll_out_latest_gen3_release_to_environments(self, user):
        latest_release = self.find_latest_release()

        # find all environments owned by the user
        em = EnvironmentsManager()

        qa_envs = em.get_envs_owned(user, "gitops-qa")
        prod_envs = em.get_envs_owned(user, "cdis-manifest")

        log.info(
            "Creating release PRs for {} environments owned by user {}".format(
                len(qa_envs) + len(prod_envs), user
            )
        )

        jji = JenkinsJobInvoker()

        # Invoke Jenkins job for QA environments owned by this user
        for e in qa_envs:
            log.info("creating release PR for {}".format(e))

        json_params = {
            "RELEASE_VERSION": latest_release,
            "LIST_OF_ENVIRONMENTS": ",".join(qa_envs),
            "REPO_NAME": "gitops-qa",
        }
        str_params = json.dumps(json_params, separators=(",", ":"))
        bot_response = jji.invoke_jenkins_job(
            "create-prs-for-all-monthly-release-envs", "jenkins", str_params
        )
        if "something went wrong" in bot_response:
            return bot_response

        # Invoke Jenkins job for Prod environments owned by this user
        for e in prod_envs:
            log.info("creating release PR for {}".format(e))

        json_params = {
            "RELEASE_VERSION": latest_release,
            "LIST_OF_ENVIRONMENTS": ",".join(qa_envs),
            "REPO_NAME": "cdis-manifest",
        }
        str_params = json.dumps(json_params, separators=(",", ":"))
        bot_response = jji.invoke_jenkins_job(
            "create-prs-for-all-monthly-release-envs", "jenkins", str_params
        )
        if "something went wrong" in bot_response:
            return bot_response

        bot_response = "The release is being rolled out... :clock1: Check https://github.com/uc-cdis/cdis-manifest/pulls to see the PRs"
        return bot_response


if __name__ == "__main__":
    rm = ReleaseManager()
    print(rm.roll_out_latest_gen3_release_to_environments("gkuffel"))
