import requests
from requests import Session, Request
import os
import logging

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


class JenkinsLib:
    def __init__(self, jenkins_instance):
        """
        Invokes a Jenkins job
        """
        self.jenkins_instance = jenkins_instance
        self.base_url = "https://{}.planx-pla.net/job".format(jenkins_instance)
        self.jenkins_user_api_token = os.environ[
            "{}_USER_API_TOKEN".format(jenkins_instance.upper())
        ].strip()

    def prepare_remote_build_request(self, job_name, params={}):
        """
        Prepares a py request with url and basic auth based on details provided by the user
        """
        log.info(
            "Invoking job {} from {} with params {}".format(
                job_name, self.jenkins_instance, params
            )
        )
        build_url_path = "buildWithParameters" if bool(params) else "build"
        the_url = "{}/{}/{}?token={}".format(
            self.base_url,
            job_name,
            build_url_path,
            os.environ["JENKINS_JOB_TOKEN"].strip(),
        )
        for pk, pv in params.items():
            the_url += "&{}={}".format(pk, pv)
        req = requests.Request(
            "GET", the_url, auth=("themarcelor", self.jenkins_user_api_token),
        )
        prepared_request = req.prepare()
        return prepared_request

    def invoke_job(self, req):
        s = requests.Session()
        resp = s.send(req)
        if resp.status_code != 201:
            err_msg = "The job was not invoked successfully. Details: {}".format(
                resp.reason
            )
            log.error(err_msg)
            err = Exception(err_msg)
            return err, None
        return None, resp

    def prepare_request_and_invoke(self, job_name, params={}):
        # convert list of params into dictionary
        pr = self.prepare_remote_build_request(job_name, params)
        err, resp = self.invoke_job(pr)
        if resp.status_code == 201:
            metadata_url = "{}/{}/lastBuild/api/json".format(self.base_url, job_name,)
            log.debug(
                "Job triggered successfully. Checking the json metadata: {}".format(
                    metadata_url
                )
            )
            job_metadata = requests.get(
                metadata_url, auth=("themarcelor", self.jenkins_user_api_token),
            )
            log.debug(job_metadata.json().keys())
            next_build_number = int(job_metadata.json()["id"]) + 1
            return None, next_build_number
        else:
            print("Job could not be invoked.")
            return err, None

    def get_status_of_job(self, job_name, job_id):
        job_metadata = requests.get(
            "{}/{}/{}/api/json".format(self.base_url, job_name, job_id,),
            auth=("themarcelor", self.jenkins_user_api_token),
        )
        bot_response = "The result of {} job # {} is: {}".format(
            job_name, job_id, job_metadata.json().result
        )
        return bot_response


if __name__ == "__main__":
    jl = JenkinsLib("jenkins2")
    req = jl.prepare_remote_build_request(
        "run-tests-on-environment",
        {"TARGET_ENVIRONMENT": "ci-env-1", "TEST_SUITE": "test-portal-homepageTest"},
    )
    print(req.url)
    print(jl.invoke_job(req))
