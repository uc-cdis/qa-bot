from github import Github
import logging
import os

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
