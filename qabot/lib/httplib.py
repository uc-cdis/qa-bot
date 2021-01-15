import requests
import json
import logging
import os

logging.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"))
log = logging.getLogger(__name__)


class HttpLib:
    def fetch_json(self, url):
        try:
            response = requests.get(url)
            response.raise_for_status()
            json_data = response.json()
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
        return json_data
