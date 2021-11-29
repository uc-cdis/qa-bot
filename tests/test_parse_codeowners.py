from httmock import urlmatch, HTTMock
import unittest
import os
from pprint import pprint

from qabot.parse_codeowners import EnvironmentsManager


class EnvironmentsManagerTestCase(unittest.TestCase):
    """Tests for parse_codeowners.py"""

    # Utilizing httpmock to obtain a fake dictionary that maps caninedc against a fake owner (@theowner)
    @urlmatch(netloc=r"(.*\.)?raw\.githubusercontent\.com$", path=r".*CODEOWNERS$")
    def codeowners_mock(self, url, request):
        return {
            "status_code": 200,
            "content": "caninedc.org @theowner @uc-cdis/planx-qa",
        }

    # TODO: Negative test
    # What if the CODEOWNERS file contains just one owner?
    # You can't unpack that line into 3-tuple variables

    def test_map_environments_and_owners(self):
        # initialize the EnvironmentsManager instance
        em = EnvironmentsManager()
        with HTTMock(self.codeowners_mock):
            result = em.map_environments_and_owners()

            self.assertEqual(
                ["@theowner"],
                result["caninedc.org"],
                'Must return a dictionary containing the expected owner list ["@theowner"] for the environment "caninedc.org"',
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
