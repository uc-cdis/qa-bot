from lib.httplib import HttpLib
import logging
import os
from pprint import pprint

logging.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"))
log = logging.getLogger(__name__)

GITHUBLINK = "https://raw.githubusercontent.com/uc-cdis/cdis-manifest/master/CODEOWNERS"


class EnvironmentsManager:
    def __init__(self):
        """
    Provides utilitary functions to manage environments and their respective config (e.g., owners, etc.)
    """
        self.httplib = self.get_httplib()

    def get_httplib(self):
        return HttpLib()

    def map_environments_and_owners(self):
        envdict = {}

        CODEOWNERS = self.httplib.fetch_raw_data(GITHUBLINK)
        lines = CODEOWNERS.splitlines()

        for line in lines:
            if line != "":
                githubIDs = line.split()
                env = githubIDs.pop(0)
                # pop planxqa at the end
                githubIDs.pop(-1)

                envdict[env] = githubIDs

        log.info(
            "Returning a map of environments and owners with {} keys".format(
                len(envdict)
            )
        )
        return envdict


if __name__ == "__main__":
    em = EnvironmentsManager()
    print(em.map_environments_and_owners())
