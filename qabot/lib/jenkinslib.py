import requests
from requests import Session, Request
from requests.exceptions import RequestException
import time
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

    def prepare_remote_build_request(self, job_name, params):
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
        if params:
            for pk, pv in params.items():
                if "http" in pv:
                    log.warn("url found, stripping off characters added by slack...")
                    pv = re.search("http[s]?:\/\/(.*)\|.*", pv)[1]
                the_url += "&{}={}".format(pk, pv)

        the_url_logging_safe = the_url[0 : the_url.index("token")]
        log.info("Here's the URL: {}".format(the_url_logging_safe))

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
        url_to_return = "{}{}/detail/PR-{}/{}/pipeline".format(
            "https://jenkins.planx-pla.net/blue/organizations/jenkins/CDIS_GitHub_Org%2F",
            repo_name,
            pr_number,
            int(job_number) + 1,
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
            # wait for Jenkins to process the build before fetching its metadata
            time.sleep(2)
            log.debug(job_metadata.json().keys())
            try:
                next_build_number = int(job_metadata.json()["id"]) + 1
            except JSONDecodeError as jde:
                return "err: Could not determine the next build number :(", None
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

    def get_duration_of_ci_pipeline_stage(self, repo_name, job_number, stage_name):
        log.debug(
            f"Sending request to URL: {self.base_url}/CDIS_GitHub_Org/job/{repo_name}/job/PR-{job_number}/wfapi/runs"
        )
        try:
            job_metadata = requests.get(
                f"{self.base_url}/CDIS_GitHub_Org/job/{repo_name}/job/PR-{job_number}/wfapi/runs",
                auth=("themarcelor", self.jenkins_user_api_token),
            )
            job_metadata.raise_for_status()
        except requests.exceptions.HTTPError as httperr:
            raise RequestException(
                f"error_code:{job_metadata.status_code}, error_msg:{job_metadata.reason}"
            )

        # the first item in the array always represents the latest run
        ci_build_stages = job_metadata.json()[0]["stages"]
        for stage_metadata in ci_build_stages:
            if stage_metadata["name"] == stage_name:
                return stage_metadata["durationMillis"]

        # if it can't find any stages with that name
        raise RequestException(
            f"Could not find the ci pipeline stage metadata associated with repo_name:{repo_name}, pr_num:{pr_num} and stage_name:{stage_name}"
        )

    def get_status_of_job(self, job_name, job_id):
        # If the job has not been triggered yet, wait a few seconds and try again
        max_attempts = 15
        attempts = 0
        while attempts <= max_attempts:
            job_metadata = requests.get(
                "{}/{}/{}/api/json".format(self.base_url, job_name, job_id,),
                auth=("themarcelor", self.jenkins_user_api_token),
            )
            if job_metadata.status_code == 404:
                log.debug(
                    f"Attempt #{attempts} - The job does not exist yet. Sleeping for 5 seconds"
                )
                time.sleep(5)
                attempts += 1
                continue

            job_result = job_metadata.json()["result"]
            if job_result == None:
                log.debug(
                    f"Attempt #{attempts} - The job is still running, there is no result yet (result: {job_result}). Sleeping for 5 seconds"
                )
                time.sleep(5)
                attempts += 1
            else:
                return job_result

        return "Could not obtain status"

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
