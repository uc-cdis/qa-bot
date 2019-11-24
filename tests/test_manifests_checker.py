from httmock import urlmatch, HTTMock
import unittest
from unittest.mock import Mock, patch
from pprint import pprint

from manifests_checker import ManifestsChecker

class ManifestsCheckerTestCase(unittest.TestCase):
  """Tests for manifests_checker.py'."""

  @urlmatch(netloc=r'(.*\.)?raw\.githubusercontent\.com$', path=r'.*this_is_from_a_pr.*$')
  def pr_manifest_mock(self, url, request):
    return { 'status_code': 200,
	     'content': {
               'versions': {
                 'arborist': 'quay.io/cdis/arborist:2.3.2',
                 'fence': 'quay.io/cdis/fence:4.11.0',
                 'indexd': 'quay.io/cdis/indexd:2.1.0',
                 'sheepdog': 'quay.io/cdis/sheepdog:1.1.11'
               }
             }
           }

  @urlmatch(netloc=r'(.*\.)?raw\.githubusercontent\.com$', path=r'.*internalstaging.datastage.io.*$')
  def signed_off_manifest_mock(self, url, request):
    return { 'status_code': 200,
             'content': {
               'versions': {
                 'arborist': 'quay.io/cdis/arborist:2.3.2',
                 'fence': 'quay.io/cdis/fence:2.8.2',
                 'indexd': 'quay.io/cdis/indexd:2.1.0',
                 'sheepdog': 'quay.io/cdis/sheepdog:1.1.10'
               }
             }
           }

  def setUp(self):
    # create a mock GithubLib object
    githublibMock = Mock(name='GithubLibMock', return_value=(Mock()))
    # create a mock HttpLib object
    httplibMock = Mock(name='HttpLibMock', return_value=(Mock()))

    # mock GithubLib "get_file_raw_url" function
    def get_file_raw_url(pr_number, filename):
      return 'https://raw.githubusercontent.com/uc-cdis/cdis-manifest/this_is_from_a_pr/manifest.json'

    githublibMock.get_file_raw_url = get_file_raw_url

    # mock get_githublib function to return the githublibMock mock obj
    def get_githublib(self):
      return githublibMock

    self.patch1 = patch.object(ManifestsChecker, 'get_githublib', get_githublib)
    self.patch1.start()

    # initialize the ManifestsChecker instance
    self.manifests_checker = ManifestsChecker()

  def tearDown(self):
    self.patch1.stop()

  def test_compare_manifests(self):
    with HTTMock(self.pr_manifest_mock, self.signed_off_manifest_mock):
      result = self.manifests_checker.compare_manifests(928, '<http://internalstaging.datastage.io|internalstaging.datastage.io>')
      # Must show discrepancies between versions found on the PR\'s manifest and the versions deployed against the environment that has been signed off by the QA team
      self.assertEqual(
        "\nThe following discrepancies have been identified:\n```\n{'fence': 'quay.io/cdis/fence:2.8.2', 'sheepdog': 'quay.io/cdis/sheepdog:1.1.10'}\n```\n", 
        result,
        'Must show discrepancies between versions from both manifests')

if __name__ == '__main__':
  unittest.main() 
