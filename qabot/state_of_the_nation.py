import requests
from lib.slacklib import SlackLib
from lib.githublib import GithubLib
from lib.httplib import HttpLib
import json
import os
import re
import logging

logging.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"))
log = logging.getLogger(__name__)


class StateOfTheNation:
    def __init__(self):
        """
        Initializes an object to map all the environments and their correspondent
        code promotion sequence according to a given project.
        It also includes functions to sweep Github repos and determine the state of
        echo environment next steps to move forward with the project's release cycle.
        """
        # TODO: Find the owners / reviewers of pending PRs and utilize Slack lib to ping them on Slack
        self.prj_envs_map = {
            "anvil": {
                "environments": {
                    "qa-anvil.planx-pla.net": {
                        "tier": "qa",
                        "repo": "gitops-qa",
                        "purpose": "Used for disruptive experiments (e.g., new DD versions/features) and reproduce PROD bugs",
                        "promote_to": ["internalstaging"],
                        "health_check": ["presigned_url"],
                        "currently_running": "",
                        "pending_prs": [],
                        "owners": [],
                    },
                    "internalstaging.theanvil.io": {
                        "tier": "preprod",
                        "repo": "cdis-manifest",
                        "purpose": "Used for pre-release testing. This is the preprod / non-customer facing tier that resembles prod and it is used for Data Release through DB flips.",
                        "promote_to": ["prod"],
                        "health_check": ["presigned_url"],
                        "currently_running": "",
                        "pending_prs": [],
                        "owners": [],
                    },
                    "gen3.theanvil.io": {
                        "tier": "prod",
                        "repo": "cdis-manifest",
                        "purpose": "This is the PRODUCTION / customer-facing environment.",
                        "promote_to": ["staging"],
                        "health_check": ["presigned_url"],
                        "currently_running": "",
                        "pending_prs": [],
                        "owners": [],
                    },
                    "staging.theanvil.io": {
                        "tier": "staging",
                        "repo": "cdis-manifest",
                        "purpose": "This is the non-prod / customer-facing environment to be used for cross-org testing and sneak peek into new features.",
                        "promote_to": [],
                        "health_check": ["presigned_url"],
                        "currently_running": "",
                        "pending_prs": [],
                        "owners": [],
                    },
                },
            },
            "bdcat": {
                "environments": {
                    "qa-dcp.planx-pla.net": {
                        "tier": "qa",
                        "repo": "gitops-qa",
                        "purpose": "Used for disruptive experiments (e.g., new DD versions/features) and reproduce PROD bugs",
                        "promote_to": ["preprod"],
                        "health_check": ["presigned_url"],
                        "currently_running": "",
                        "pending_prs": [],
                        "owners": [],
                    },
                    "preprod.gen3.biodatacatalyst.nhlbi.nih.gov": {
                        "tier": "preprod",
                        "repo": "cdis-manifest",
                        "purpose": "Used for pre-release testing. This is the preprod / non-customer facing tier that resembles prod and it is used for Data Release through DB flips.",
                        "promote_to": ["prod"],
                        "health_check": ["presigned_url"],
                        "currently_running": "",
                        "pending_prs": [],
                        "owners": [],
                    },
                    "gen3.biodatacatalyst.nhlbi.nih.gov": {
                        "tier": "prod",
                        "repo": "cdis-manifest",
                        "purpose": "This is the PRODUCTION / customer-facing environment.",
                        "promote_to": ["staging"],
                        "health_check": ["presigned_url"],
                        "currently_running": "",
                        "pending_prs": [],
                        "owners": [],
                    },
                    "staging.gen3.biodatacatalyst.nhlbi.nih.gov": {
                        "tier": "staging",
                        "repo": "cdis-manifest",
                        "purpose": "This is the non-prod / customer-facing environment to be used for cross-org testing and sneak peek into new features.",
                        "promote_to": [],
                        "health_check": ["presigned_url"],
                        "currently_running": "",
                        "pending_prs": [],
                        "owners": [],
                    },
                },
            },
            "dcf": {
                "environments": {
                    "qa-dcf.planx-pla.net": {
                        "tier": "qa",
                        "repo": "gitops-qa",
                        "purpose": "Used for disruptive experiments (e.g., new DD versions/features) and reproduce PROD bugs",
                        "promote_to": ["staging"],
                        "health_check": ["presigned_url"],
                        "currently_running": "",
                        "pending_prs": [],
                        "owners": [],
                    },
                    "nci-crdc-staging.datacommons.io": {
                        "tier": "preprod",
                        "repo": "cdis-manifest",
                        "purpose": "Non-prod customer-facing environment that is also used for pre-release testing.",
                        "promote_to": ["prod"],
                        "health_check": ["presigned_url"],
                        "currently_running": "",
                        "pending_prs": [],
                        "owners": [],
                    },
                    "nci-crdc.datacommons.io": {
                        "tier": "prod",
                        "repo": "cdis-manifest",
                        "purpose": "This is the PRODUCTION / customer-facing environment.",
                        "promote_to": [],
                        "health_check": ["presigned_url"],
                        "currently_running": "",
                        "pending_prs": [],
                        "owners": [],
                    },
                },
            },
        }

        self.slacklib = self.get_slacklib()
        self.githublib = self.get_githublib()
        self.httplib = self.get_httplib()

    def get_slacklib(self):
        return SlackLib()

    def get_githublib(self):
        return GithubLib()

    def get_httplib(self):
        return HttpLib()

    def get_slack_user_id(self, real_name):
        return self.get_slacklib(real_name)["id"]

    def run_state_of_the_nation_report(
        self, project_name, state_of_the_prs, num_of_prs_to_scan=50
    ):
        """
        Prepare full report around the state of the release for a given project
        """
        bot_response = ""

        project_name = project_name.lower()

        # correlate project's environments with the open/closed PRs
        if project_name not in self.prj_envs_map:
            bot_response = "invalid project name :facepalm:"
            return bot_response

        envs = self.prj_envs_map[project_name]["environments"].keys()

        # Fetch all the PRs opened for the environments correspondent to the project
        ghlib = self.get_githublib()
        github_client = ghlib.get_github_client()

        # TODO: Also track PRs in gitops-qa
        # fetch the most recent PRs (arbitrarily 200 of them... that should be enough)
        log.info(
            f"Shooting a GET request to https://api.github.com/repos/uc-cdis/cdis-manifest/pulls?per_page={num_of_prs_to_scan}&state={state_of_the_prs}..."
        )
        get_pull_requests = requests.get(
            f"https://api.github.com/repos/uc-cdis/cdis-manifest/pulls?per_page={num_of_prs_to_scan}&state={state_of_the_prs}",
            auth=("themarcelor", ghlib.token),
        )
        # print(pull_requests_resp.json())

        for pr in get_pull_requests.json():
            log.info(f"pr #: {pr['number']}")
            # fetch the first file referenced on the PR
            get_pr_files = requests.get(
                f"https://api.github.com/repos/uc-cdis/cdis-manifest/pulls/{pr['number']}/files",
                auth=("themarcelor", ghlib.token),
            )
            pr_files = get_pr_files.json()
            env_folder_name = pr_files[0]["filename"].split("/")[0]
            log.debug(f"1st file from this pr: {env_folder_name}")

            # ignore dotted files
            if env_folder_name[0] == ".":
                continue

            # ignore PRs that are closed without merging (abandoned)
            if pr["state"] == "closed" and not pr["merged_at"]:
                continue

            # check if the folder associated with the PR matches any of the project's environments
            if env_folder_name in envs:
                pr_deets = {
                    "html_url": pr["html_url"],
                    "title": pr["title"],
                    "tier": self.prj_envs_map[project_name]["environments"][
                        env_folder_name
                    ]["tier"],
                    "state": pr["state"],
                    "merged_at": pr["merged_at"],
                }
                self.prj_envs_map[project_name]["environments"][env_folder_name][
                    "pending_prs"
                ].append(pr_deets)

        bot_response += f":book: State of the nation report for {project_name}: \n"
        bot_response += f"~ \n"

        # TODO: There are too many http requests here.
        # We need to move them to diff functions and utilize some cache
        # Similar to: https://github.com/uc-cdis/qa-bot/blob/master/qabot/manifests_checker.py#L38

        # Determine versions that are currently_running on each environment associated to the project
        # populate bot response with the PRs correspondent to the project_name
        for e in envs:
            # scan the versions block of each manifest
            # TODO: Also track QA envs -> self.prj_envs_map[project_name]['environments'][e]['repo']
            # Skip QA environments for now
            if (
                self.prj_envs_map[project_name]["environments"][e]["repo"]
                == "gitops-qa"
            ):
                continue
            the_repo = "cdis-manifest"
            manifest_url = "https://raw.githubusercontent.com/uc-cdis/{}/master/{}/manifest.json".format(
                the_repo, e
            )
            versions_block = self.httplib.fetch_json(manifest_url)["versions"]

            # TODO: Move this logic to manifests_checker.py later
            third_party_svcs_to_ignore = [
                "arranger",
                "arranger-dashboard",
                "arranger-adminapi",
                "aws-es-proxy",
                "fluentd",
                "ambassador",
                "nb2",
                "jupyterhub",
                "google-sa-validation",
            ]

            # sweep versions and find common monthly version
            # (and alert a couple of semantic versions, if any)
            versions = set()
            for svc in versions_block.keys():
                # skip 3rd party svcs
                if svc in third_party_svcs_to_ignore:
                    continue

                print(f"checking svc: {versions_block[svc]}")
                match = re.search(".*/(.*)\:(.*)$", versions_block[svc])
                img_name = match.group(1)
                version = match.group(2)
                # print(f"img_name: {img_name}")

                if version:
                    # check if the version follows the monthly release format
                    # if it doesn't, report the name of the service and the semantic version
                    version_match = re.search("[0-9]{4}.[0-9]{2}", version)
                    if bool(version_match):
                        versions.add(version)
                    else:
                        versions.add(img_name + ":" + version)

            log.debug(f"versions: {versions}")

            bot_response += f"*{self.prj_envs_map[project_name]['environments'][e]['tier']}* environment: \n"
            bot_response += f":point_right: {e}: \n"
            bot_response += f"Currently running: {versions}: \n"

            # PRs for a given environment
            pending_prs = self.prj_envs_map[project_name]["environments"][e][
                "pending_prs"
            ]

            if len(pending_prs) > 0:
                bot_response += f"*PRs:* \n"
                bot_response += f"```"
                for pr_deets in pending_prs:
                    bot_response += f"### {pr_deets['title']} \n"
                    bot_response += (
                        f"Click here to visit the PR: -> {pr_deets['html_url']} \n"
                    )
                    if pr_deets["state"] == "closed":
                        bot_response += f"Merged at {pr_deets['merged_at']} \n"
                    else:
                        # TODO: tag reviewers (requested_reviewers: [])
                        bot_response += f"This PR has not been merged yet. \n"
                    bot_response += "--- \n"
                bot_response += f"``` \n"

        return bot_response


if __name__ == "__main__":
    sotn = StateOfTheNation()
    result = sotn.run_state_of_the_nation_report("anvil")
    print(result)
