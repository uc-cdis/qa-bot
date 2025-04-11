import json
import logging
import os

import requests

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


class SlackLib:
    def __init__(
        self,
        base_url="https://slack.com/api",
        token=os.environ["SLACK_BOT_TOKEN"].strip(),
    ):
        """
        Creates a Github utils object to perform various operations against the uc-cdis repos and its branches, pull requests, etc.
        """
        self.base_url = base_url
        self.token = token

    def get_user_info(self, real_name):
        try:
            response = requests.get(
                "{}/users.list?token={}".format(self.base_url, self.token)
            )
            response.raise_for_status()
            json_data = response.json()
            for member in json_data["members"]:
                if member["profile"]["real_name"] == real_name:
                    return member
            return None
        except requests.exceptions.HTTPError as httperr:
            log.error(f"request failed due to the following error: {str(httperr)}")
            return None
        except json.JSONDecodeError as jsonerr:
            log.error(f"error while trying to fetch json data - error: {str(jsonerr)}")
            return None


if __name__ == "__main__":
    sl = SlackLib()
    print(sl.get_user_info("Andrew Prokhorenkov")["id"])
