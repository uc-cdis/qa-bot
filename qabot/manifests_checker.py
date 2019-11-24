from lib.githublib import GithubLib
from lib.httplib import HttpLib
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

#if __name__ == '__main__':
#  mc = ManifestsChecker()
#  #diff = mc.compare_manifests(928, 'internalstaging.datastage.io')
#  diff = mc.compare_manifests(928, 'data.kidsfirstdrc.org')
#  print('diff: ')
#  pprint(diff)
