import json
import logging
import os
import time

import requests
from github import Github
from github.GithubException import GithubException

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


class GithubLib:
    def __init__(
        self,
        org="uc-cdis",
        repo="cdis-manifest",
        token=os.environ["GITHUB_TOKEN"].strip(),
    ):
        """
        Creates a Github utils object to perform various operations against the uc-cdis repos and its branches, pull requests, etc.
        """
        self.org = org
        self.repo = repo
        self.token = token

    def get_github_client(self):
        """
        return a github client object that can instrument a given repo
        """
        g = Github(self.token)
        org = g.get_organization(self.org)
        repo = org.get_repo(self.repo)
        return repo

    def get_file_raw_url(self, pr_number, filename):
        pr = self.get_github_client().get_pull(pr_number)
        for file in pr.get_files():
            if filename in file.filename:
                return file.raw_url
        raise Exception(
            "Could not find {} among the files of PR #{}".format(filename, pr_number)
        )

    def list_files_in_dir(self, dir):
        ghc = self.get_github_client()
        content_files = ghc.get_dir_contents(dir)
        # This content_files list contains something like:
        # [ContentFile(path="releases/2020"), ContentFile(path="releases/2021")]
        # hence, obtain the path and keep only the name of the last folder
        files = [f.path.split("/")[-1] for f in content_files]
        return files

    def set_label_to_pr(self, pr_number, label, override_all=False):
        pr = self.get_github_client().get_pull(pr_number)
        if override_all:
            pr.set_labels(label)
        else:
            pr.add_to_labels(label)

    def replay_pr(self, pr_number):
        gh_client = self.get_github_client()
        pr = gh_client.get_pull(int(pr_number))
        head_sha = pr.head.sha
        workflow_runs = gh_client.get_workflow_runs()
        target_run = None
        for run in workflow_runs:
            if run.name == "Integration Tests" and run.head_sha == head_sha:
                target_run = run
                break
        if target_run:
            log.info(f"Latest 'Tests' workflow run ID: {target_run.id}")
            try:
                target_run.rerun()
                rerun_url = f"https://github.com/{self.org}/{self.repo}/actions/runs/{target_run.id}"
                return f"Your PR has been labeled and replayed successfully :tada: \n Czech it out :muscle: {rerun_url}"
            except GithubException as e:
                log.error(e.data)
                return "Failed to replay the PR :sadcat:, please try from Github directly :pray:"
        else:
            return "No `Integration Tests` workflow run found for this PR :thinking:"

    def trigger_gh_action_workflow(self, workflow_repo, workflow_filename, ref, inputs):
        url = f"https://api.github.com/repos/{self.org}/{workflow_repo}/actions/workflows/{workflow_filename}/dispatches"
        headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github+json",
        }
        payload = {"ref": ref}
        if inputs:
            payload["inputs"] = inputs
        response = requests.post(url, headers=headers, json=payload)
        return response

    def get_external_pr_number(self, repo_name, search_title):
        for i in range(6):
            time.sleep(10)
            url = "https://api.github.com/search/issues"
            query = f"repo:{self.org}/{repo_name}+type:pr+in:title+{search_title}"
            headers = {
                "Authorization": f"token {self.token}",
                "Accept": "application/vnd.github+json",
            }
            response = requests.get(url, headers=headers, params={"q": query})
            response.raise_for_status()
            items = response.json().get("items", [])
            if not items:
                continue
            pr = items[0]
            return pr["html_url"]
        return False
