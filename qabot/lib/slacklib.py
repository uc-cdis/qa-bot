import requests
import json
import os
import logging

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


class SlackLib:
    def __init__(
        self,
        base_url="https://slack.com/api",
        token=os.environ["SLACK_API_TOKEN"].strip(),
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
            log.error(
                "request to {0} failed due to the following error: {1}".format(
                    url, str(httperr)
                )
            )
            return None
        except json.JSONDecodeError as jsonerr:
            log.error(
                "error while trying to fetch json data."
                + "url: {0}. error: {0}".format(url, str(jsonerr))
            )
            return None


if __name__ == "__main__":
    sl = SlackLib()
    print(sl.get_user_info("Andrew Prokhorenkov")["id"])
