from jira import JIRA
from jira.exceptions import JIRAError
from functools import lru_cache
import time
import requests
import logging
import os

logging.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"))
log = logging.getLogger(__name__)


class JiraLib:
    def __init__(
        self,
        jira_server="https://ctds-planx.atlassian.net",
        service_account="ctds.qa.automation@gmail.com",
        token=os.environ["JIRA_API_TOKEN"].strip(),
    ):
        """
        Creates a JiraLib utils object to perform various operations against JIRA
        """
        self.jira_server = jira_server
        self.service_account = service_account
        self.token = token

    def get_jira_client(self):
        """
        return a jira client object
        """
        options = {"server": self.jira_server}
        j = JIRA(options, basic_auth=(self.service_account, self.token))
        return j

    def _get_ttl_hash(self, seconds=300):
        """To facilitate caching: Return the same value withing `seconds` time period"""
        return round(time.time() / seconds)

    @lru_cache()
    def _get_all_jira_users(self, ttl_hash=None):
        del ttl_hash
        url = f"{self.jira_server}/rest/api/3/user/search?query=_&maxResults=1000"
        try:
            response = requests.get(
                url,
                headers={"Content-type": "application/json"},
                auth=(self.service_account, self.token),
            )
            response.raise_for_status()
            all_users_json = response.json()
        except requests.exceptions.HTTPError as httperr:
            log.error(
                "request to {0} failed due to the following error: {1}".format(
                    url, str(httperr)
                )
            )
            return None
        return all_users_json

    # TODO: It would be great to use the email instead but the JIRA Cloud API hides it
    def get_jira_user_id(self, display_name):
        all_users = self._get_all_jira_users(self._get_ttl_hash())
        user_found = None
        for user in all_users:
            if user["displayName"] == display_name:
                user_found = user["accountId"]

        if user_found:
            log.info(f"Found user id: {user_found}")
            return user_found
        else:
            log.warn(f"could not find user id based on display name: {display_name}")
            return "-1"

    def create_ticket(
        self, title, description, type, assignee="-1", project_name="PXP"
    ):
        # fetch user id IF the assignee argument is provided, -1 = unassigned by default
        if assignee != -1:
            assignee = self.get_jira_user_id(assignee)

        issue_dict = {
            "project": project_name,
            "summary": title,
            "description": description,
            "customfield_10067": {"id": "10055", "value": "Project Team"},
            "issuetype": {"name": type},
            "components": [{"name": "N/A"}],  # teams should be defined here
            "assignee": {"accountId": assignee},
        }
        try:
            jira = self.get_jira_client()
            created_jira = jira.create_issue(fields=issue_dict)
            jira_id = created_jira.key
        except JIRAError as je:
            log.error(f"Failed to create a JIRA bug ticket. Details: {je}")
            raise je
        log.info(f"successfully created bug ticket: {jira_id}")
        return jira_id


if __name__ == "__main__":
    jl = JiraLib()
    # print(jl.create_bug_ticket("just a test", "test description"))
    print(jl.get_jira_user_id("Atharva_Rane"))
    print(jl.get_jira_user_id("Marcelo Costa"))
    print(jl.get_jira_user_id("Marcelo_Rodrigues_Costa"))
    print(jl.create_bug_ticket("just a test2", "test description", "Atharva_Rane"))
