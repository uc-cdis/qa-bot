import requests
from requests import Session, Request
import os
import re
import logging

logging.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"))
log = logging.getLogger(__name__)


class JenkinsLib:
    def __init__(self, jenkins_instance):
        """
        Invokes a Jenkins job
        """
        self.jenkins_instance = jenkins_instance
        self.base_url = "https://{}.planx-pla.net/job".format(jenkins_instance)
        self.base_blueocean_url = "https://jenkins.planx-pla.net/blue/rest/organizations/jenkins/pipelines/CDIS_GitHub_Org"
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
            if "http" in pv:
                log.warn("url found, stripping off characters added by slack...")
                pv = re.search("http[s]?:\/\/(.*)\|.*", pv)[1]
            the_url += "&{}={}".format(pk, pv)
        req = requests.Request(
            "GET", the_url, auth=("themarcelor", self.jenkins_user_api_token),
        )
        prepared_request = req.prepare()
        return prepared_request

    def send_blueocean_request(self, repo_name, pr_number, job_number):
        """
        Prepares a py request against the Jenkins Blueocean REST API
        with url and basic auth based on details provided by the user

        sample curl to trigger a Jenkins Blueocean REST API Replay operation
        curl -X POST -u themarcelor:$JENKINS_USER_API_TOKEN \
         -H "Content-Type: application/json" \
         "https://jenkins.planx-pla.net/blue/rest/organizations/jenkins/pipelines/CDIS_GitHub_Org/gen3-qa/PR-549/runs/1/replay"
        """
        log.info(
            "Sending a request to Jenkins Blueocean REST API to PR {} from Repo {}".format(
                pr_number, repo_name
            )
        )
        the_url = "{}/{}/PR-{}/runs/{}/replay".format(
            self.base_blueocean_url, repo_name, pr_number, job_number
        )
        # https://jenkins.planx-pla.net/blue/organizations/jenkins/CDIS_GitHub_Org%2Fcdis-manifest/detail/PR-2503/7/pipeline
        url_to_return = "{}/{}/detail/PR-{}/{}/pipeline".format(
            self.base_blueocean_url, repo_name, pr_number, job_number
        )
        log.debug("sending POST reques to the following url: {}".format(the_url))
        resp = requests.post(
            the_url,
            headers={"Content-type": "application/json"},
            auth=("themarcelor", self.jenkins_user_api_token),
        )
        if resp.status_code != 200:
            err_msg = "The replay operation failed. Details: {}".format(resp.reason)
            log.error(err_msg)
            err = Exception(err_msg)
            return err, None
        return None, url_to_return

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
        if resp != None and resp.status_code == 201:
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

        print("Job could not be invoked.")
        return err, None

    def get_number_of_last_build(self, repo_name, job_number):
        job_metadata = requests.get(
            "{}/CDIS_GitHub_Org/job/{}/job/PR-{}/lastBuild/api/json".format(
                self.base_url, repo_name, job_number
            ),
            auth=("themarcelor", self.jenkins_user_api_token),
        )
        return job_metadata.json()["number"]

    def get_status_of_job(self, job_name, job_id):
        job_metadata = requests.get(
            "{}/{}/{}/api/json".format(self.base_url, job_name, job_id,),
            auth=("themarcelor", self.jenkins_user_api_token),
        )
        bot_response = "The result of {} job # {} is: {}".format(
            job_name, job_id, job_metadata.json().result
        )
        return bot_response

    def fetch_archived_artifact(self, job_name, file_name):
        artifact_url = "{}/{}/lastSuccessfulBuild/artifact/{}?token=$JENKINS_JOB_TOKEN".format(
            self.base_url, job_name, file_name
        )
        resp = requests.get(
            artifact_url, auth=("themarcelor", self.jenkins_user_api_token),
        )
        if resp.status_code != 200:
            err_msg = "The request failed. Details: {}".format(resp.reason)
            log.error(err_msg)
            err = Exception(err_msg)
            return err, None
        return None, resp.text


if __name__ == "__main__":
    jl = JenkinsLib("jenkins2")
    req = jl.prepare_remote_build_request(
        "run-tests-on-environment",
        {"TARGET_ENVIRONMENT": "ci-env-1", "TEST_SUITE": "test-portal-homepageTest"},
    )
    print(req.url)
    print(jl.invoke_job(req))
