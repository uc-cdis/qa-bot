import json
import os
import logging

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


class StateOfTheNation:
    def __init__(self, project_name):
        """
        Initializes an object to map all the environments and their correspondent 
        code promotion sequence according to a given project.
        It also includes functions to sweep Github repos and determine the state of
        echo environment next steps to move forward with the project's release cycle.
        """
        self.prj_envs_map = {
            "TheAnvil": {
                "environments": [
                    {
                        "qa": {
                            "name": "qa-anvil.planx-pla.net",
                            "repo": "gitops-qa",
                            "purpose": "Used for disruptive experiments (e.g., new DD versions/features) and reproduce PROD bugs",
                            "promote_to": ["internalstaging"],
                            "health_check": ["presigned_url"],
                            "currently_running": "",
                            "pending_prs": [],
                            "owners": [],
                        }
                    },
                    {
                        "internalstaging": {
                            "name": "internalstaging.theanvil.io",
                            "repo": "cdis-manifest",
                            "purpose": "Used for pre-release testing. This is the preprod / non-customer facing tier that resembles prod and it is used for Data Release through DB flips.",
                            "promote_to": ["prod"],
                            "health_check": ["presigned_url"],
                            "currently_running": "",
                            "pending_prs": [],
                            "owners": [],
                        }
                    },
                    {
                        "prod": {
                            "name": "gen3.theanvil.io",
                            "repo": "cdis-manifest",
                            "purpose": "This is the PRODUCTION / customer-facing environment.",
                            "promote_to": ["staging"],
                            "health_check": ["presigned_url"],
                            "currently_running": "",
                            "pending_prs": [],
                            "owners": [],
                        }
                    },
                    {
                        "staging": {
                            "name": "staging.theanvil.io",
                            "repo": "cdis-manifest",
                            "purpose": "This is the non-prod / customer-facing environment to be used for cross-org testing and sneak peek into new features.",
                            "promote_to": [],
                            "health_check": ["presigned_url"],
                            "currently_running": "",
                            "pending_prs": [],
                            "owners": [],
                        }
                    },
                ]
            }
        }
        self.slacklib = self.get_slacklib()
        self.githublib = self.get_githublib()

    def get_slacklib(self):
        return SlackLib()

    def get_githublib(self):
        return GithubLib()

    def get_slack_user_id(self, real_name):
        return self.get_slacklib(real_name)["id"]

    def run_state_of_the_nation_report(self):
        """
        Prepare full report around the state of the release for a given project
        by executing the following operations:
        1. Fetch Slack user IDs of the project owners (if it is not already in memory)
        2. 
        """
        bot_response = ""
        return bot_response


if __name__ == "__main__":
    sotn = StateOfTheNation("TheAnvil")
    result = sotn.run_state_of_the_nation_report()
    print(result)
