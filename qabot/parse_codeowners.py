from qabot.lib.httplib import HttpLib
import logging
import os
from pprint import pprint

logging.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"))
log = logging.getLogger(__name__)

CDIS_MANIFEST_LINK = (
    "https://raw.githubusercontent.com/uc-cdis/cdis-manifest/master/CODEOWNERS"
)
GITOPS_QA_LINK = "https://raw.githubusercontent.com/uc-cdis/gitops-qa/master/CODEOWNERS"


class EnvironmentsManager:
    def __init__(self):
        """
        Provides utilitary functions to manage environments and their respective config (e.g., owners, etc.)
        """
        self.httplib = self.get_httplib()

    def get_httplib(self):
        return HttpLib()

    def get_envs_owned(self, user, repo):
        url = f"https://raw.githubusercontent.com/uc-cdis/{repo}/master/CODEOWNERS"
        codeowners = self.httplib.fetch_raw_data(url)
        envs = []
        for line in codeowners.splitlines():
            if user in line:
                envs.append(line.split()[0])
        return envs

    def create_dict(self, repo, dict):
        url = f"https://raw.githubusercontent.com/uc-cdis/{repo}/master/CODEOWNERS"
        CODEOWNERS = self.httplib.fetch_raw_data(url)
        lines = CODEOWNERS.splitlines()

        for line in lines:
            if line != "":
                githubIDs = line.split()
                env = githubIDs.pop(0)
                # pop planxqa at the end
                githubIDs.pop(-1)

                dict[env] = githubIDs

    def map_environments_and_owners(self):
        envdict = {}

        self.create_dict(CDIS_MANIFEST_LINK, envdict)
        self.create_dict(GITOPS_QA_LINK, envdict)

        log.info(
            "Returning a map of environments and owners with {} keys".format(
                len(envdict)
            )
        )
        return envdict


if __name__ == "__main__":
    em = EnvironmentsManager()
    print(em.map_environments_and_owners())
