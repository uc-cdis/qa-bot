from lib.jenkinslib import JenkinsLib
import json
import os
import logging

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


class JenkinsJobInvoker:
    def run_test_on_environment(
        self, job_name, jenkins_instance, target_environment, test_suite
    ):
        """
     Prepares a py request with url and basic auth based on details provided by the user
    """
        params_str = '{{ "TARGET_ENVIRONMENT": "{}", "TEST_SUITE": "{}" }}'.format(
            target_environment, test_suite
        )
        bot_response = self.invoke_jenkins_job(
            "run-tests-on-environment", jenkins_instance, params_str
        )
        return bot_response

    def invoke_jenkins_job(self, job_name, jenkins_instance, params_str=""):
        """
     Invoke any job
    """
        params = json.loads(params_str)
        jl = JenkinsLib()
        err, id_of_triggered_job = jl.prepare_request_and_invoke(
            job_name, jenkins_instance, params
        )
        if err == None:
            bot_response = "The job has been triggered, here's its URL: \n  {}".format(
                "https://{}.planx-pla.net/job/{}/{}/console".format(
                    jenkins_instance, job_name, id_of_triggered_job,
                )
            )
        else:
            bot_response = "Something wrong happened :facepalm:. Deets: {}".format(err)
        return bot_response


if __name__ == "__main__":
    jji = JenkinsJobInvoker()
    result = jji.run_test_on_environment(
        "run-tests-on-environment", "jenkins2", "ci-env-1", "test-portal-homepageTest"
    )
    print(result)
    result2 = jji.invoke_jenkins_job(
        "self-service-qa-gen3-roll",
        "jenkins2",
        '{ "SERVICE_NAME": "all", "TARGET_ENVIRONMENT": "ci-env-1" }',
    )
