from lib.githublib import GithubLib
from lib.httplib import HttpLib
from functools import lru_cache
import time
import logging
import re
from pprint import pprint

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

class ManifestsChecker():
  def __init__(self, manifests_base_url='https://raw.githubusercontent.com/uc-cdis/cdis-manifest/master'):
    """
     Checks manifest.json files to assist with sign-off procedures
    """
    # example of raw url:
    # https://raw.githubusercontent.com/uc-cdis/cdis-manifest/master/internalstaging.datastage.io/manifest.json
    self.manifests_base_url = manifests_base_url
    self.githublib = self.get_githublib()
    self.httplib = self.get_httplib()

  def get_githublib(self):
    return GithubLib()

  def get_httplib(self):
    return HttpLib()

  def _get_ttl_hash(self, seconds=300):
    """To facilitate caching: Return the same value withing `seconds` time period"""
    return round(time.time() / seconds)

  @lru_cache()
  def _get_directories_from_repo(self, repo, ttl_hash=None):
    del ttl_hash
    github_client = GithubLib(repo=repo).get_github_client()
    contents_from_repo = github_client.get_contents('/')
    directories = []
    for file in contents_from_repo:
      if file.type == 'dir':
        log.debug('file: {}'.format(file.name))
        directories.append(file.name)
    return directories


  def whereis_version(self, looking_for, version):
    """
    Crawl through all the manifests in cdis-manifest & gitops-qa to check which environments are running a given Gen3 Core Release version or find environments running a specific version of a given service
    """
    # repos_with_manifests = ['cdis-manifest', 'gitops-qa']
    repos_with_manifests = ['cdis-manifest']
    to_be_ignored = ['releases', 'login.bionimbus.org']
    list_of_environments = "```\n"
    environments_count = 0

    for repo in repos_with_manifests:
      directories = self._get_directories_from_repo(repo, self._get_ttl_hash())
      for env in directories:
        if env not in to_be_ignored:
          environments_count += 1
          manifest_url = 'https://raw.githubusercontent.com/uc-cdis/{}/master/{}/manifest.json'.format(repo, env)
          versions_block = self.httplib.fetch_json(manifest_url)['versions']
          if looking_for == 'release':
            the_version = versions_block['fence'] if 'fence' in versions_block.keys() else versions_block['indexd']
          elif looking_for in versions_block.keys():
            the_version = versions_block[looking_for]
          else:
            continue
          log.debug('repo: {} - env: {} - version: {}'.format(repo, env, the_version))
          match = re.search('.*\:(.*)$', the_version)
          if match.group(1) == version:
            log.debug('found it!: {}'.format(env))
            list_of_environments += env + "\n"
    num_of_envs_with_version = len(list_of_environments.split('\n'))-2
    version_adoption = round((num_of_envs_with_version / environments_count) * 100, 2)
    log.debug('percentage of envs with [{}:{}]'.format(looking_for, version_adoption))
    bot_response =  "\nThe following environments are running [{}:{}]:\n".format(looking_for, version)
    bot_response += list_of_environments
    bot_response += "```\n This represents a *{}%* adoption across *{}* environments.".format(version_adoption, environments_count)
    return bot_response


  def compare_manifests(self, pr_to_be_verified, signed_off_env):
    """
     Compare the manifest.json from a PR that is about to be rolled out with the one from an environment where all tests have been performed (i.e., signed off by the QA team)    
    """
    pr_manifest_url = self.githublib.get_file_raw_url(int(pr_to_be_verified), 'manifest.json')
    log.info('manifest from PR: ' + pr_manifest_url)
    pr_manifest_versions = self.httplib.fetch_json(pr_manifest_url)['versions']

    # the "signed_off_env" input needs to be adjusted as Slack converts hostnames to a special format
    # e.g., "<http://internalstaging.datastage.io|internalstaging.datastage.io>"
    signed_off_env_host = re.search(r".*\|(.*)>", signed_off_env).group(1)
    log.info('signed_off_env_host: ' + signed_off_env_host)
    singed_off_manifest_url = '{}/{}/manifest.json'.format(self.manifests_base_url, signed_off_env_host)
    log.info('manifest with versions that have been tested: ' + singed_off_manifest_url)
    signed_off_versions = self.httplib.fetch_json(singed_off_manifest_url)['versions']

    diff = set(sorted(signed_off_versions.items())) - set(sorted(pr_manifest_versions.items()))
    diff_dict = dict(diff)
    if len(diff_dict.keys()) == 0:
      return ':white_check_mark: The `manifest.json` from <https://github.com/uc-cdis/cdis-manifest/pull/{0}/files|PR #{0}> and the one from <https://github.com/uc-cdis/cdis-manifest/blob/master/{1}/manifest.json|{1}> contain the same versions.'.format(pr_to_be_verified, signed_off_env_host)
    else:
      return f"""
The following discrepancies have been identified:
```
{dict(sorted(diff_dict.items()))}
```
"""

if __name__ == '__main__':
  mc = ManifestsChecker()
#  #diff = mc.compare_manifests(928, 'internalstaging.datastage.io')
#  diff = mc.compare_manifests(928, 'data.kidsfirstdrc.org')
#  print('diff: ')
#  pprint(diff)
  print(mc.whereis_version('release', '2020.02'))
  print(mc.whereis_version('revproxy', '1.17.6-ctds-1.0.1'))
