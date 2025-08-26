import logging
import os

from qabot.lib.githublib import GithubLib
from qabot.parse_codeowners import EnvironmentsManager

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

        prs_count = 0
        ghl = self.githublib
        url_list = []

        for repo_name in ["gen3-gitops-dev", "gen3-gitops"]:
            env_list = em.get_envs_owned(user, repo_name)
            prs_count += len(env_list)

            # Continue to the next env_list if no entries in current env list
            if len(env_list) == 0:
                continue

            # Print out the envs release PR creation message
            [log.info("creating release PR for {}".format(e)) for e in env_list]

            json_params = {
                "RELEASE_VERSION": latest_release,
                "LIST_OF_ENVIRONMENTS": ",".join(env_list),
                "REPO_NAME": repo_name,
            }
            bot_response = ghl.trigger_gh_action_workflow(
                workflow_repo="thor",
                workflow_filename="deploy_monthly_release.yaml",
                ref="master",
                inputs=json_params,
            )
            if bot_response.status_code == 204:
                log.info("Workflow triggered successfully.")
            else:
                log.error(bot_response.text)
                raise Exception(
                    f"Failed to trigger workflow: {bot_response.status_code}"
                )
            url_list.append(f"https://github.com/uc-cdis/{repo_name}/pulls")

        log.info(
            f"Creating release PRs for {prs_count} environments owned by user {user}"
        )

        bot_response = f"The release is being rolled out... :clock1: Check {', '.join(url_list)} to see the PRs"
        return bot_response


if __name__ == "__main__":
    rm = ReleaseManager()
    print(rm.roll_out_latest_gen3_release_to_environments("gkuffel"))
