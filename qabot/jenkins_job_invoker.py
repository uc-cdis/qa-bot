import json
import logging
import os
import subprocess

from qabot.lib.githublib import GithubLib
from qabot.lib.jenkinslib import JenkinsLib

logging.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"))
log = logging.getLogger(__name__)


class JenkinsJobInvoker:
    def run_test_on_environment(self, jenkins_instance, target_environment, test_suite):
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
        jl = JenkinsLib(jenkins_instance)
        err, id_of_triggered_job = jl.prepare_request_and_invoke(job_name, params)
        if err == None:
            bot_response = "The job has been triggered, here's its URL: \n  {}".format(
                "https://{}.planx-pla.net/job/{}/{}/console".format(
                    jenkins_instance,
                    job_name,
                    id_of_triggered_job,
                )
            )
        else:
            bot_response = "Something wrong happened :facepalm:. Deets: {}".format(err)
        return bot_response

    def replay_pr(self, repo_name, pr_number):
        """
        Replay a Pull Request like a boss
        """
        jl = JenkinsLib("jenkins")
        log.info("find the number of the last build...")
        job_num = jl.get_number_of_last_build(repo_name, pr_number)

        err, url_from_replayed_pr = jl.send_blueocean_request(
            repo_name, pr_number, job_num
        )
        if err is None:
            bot_response = "Your PR has been labeled and replayed successfully :tada: \n Czech it out :muscle: {}".format(
                url_from_replayed_pr
            )
        else:
            bot_response = "Something wrong happened :facepalm:. Deets: {}".format(err)
        return bot_response

    def get_status_of_job(self, job_name, job_id, jenkins_instance):
        """
        Return status of a given job based on its id
        """
        return "not implemented yet"

    def roll_service(self, service_name, ci_env_name):
        """
        Roll a service in one of our gen3 environments
        """
        if service_name not in ["sower", "ssjdispatcher"]:
            deployment_name = f"{service_name}-deployment"
        else:
            deployment_name = service_name
        try:
            command = [
                "kubectl",
                "rollout",
                "restart",
                f"deployment/{deployment_name}",
                "-n",
                ci_env_name,
            ]
            result = subprocess.run(command, capture_output=True, text=True, check=True)
            log.info(f"Output from command when rolling deployment: {result.stdout}")
            command = [
                "kubectl",
                "rollout",
                "status",
                f"deployment/{deployment_name}",
                "-n",
                ci_env_name,
            ]
            result = subprocess.run(command, capture_output=True, text=True, check=True)
            log.info(
                f"Output from command when checking deployment status: {result.stdout}"
            )
            return f"The service {service_name} has been rolled on {ci_env_name}. :awesome-face:"
        except subprocess.CalledProcessError as e:
            log.info(e.stderr)
            return f"Failed to roll service {service_name} on {ci_env_name}, please try again or contact QA team"

    def fetch_list_of_environments(self, cluster_name):
        # TODO: Refactor and move this to a dictionary lookup in Jenkinslib
        jenkins_instance = None
        if cluster_name == "qaplanetv1":
            jenkins_instance = "jenkins"
        elif cluster_name == "qaplanetv2":
            jenkins_instance = "jenkins2"
        else:
            return "This cluster does not exist :wat:"
        jl = JenkinsLib(jenkins_instance)
        # Just fetch the latest archived artifact (the job runs on a schedule)
        err, list_of_environments = jl.fetch_archived_artifact(
            "list-namespaces-in-this-cluster", "ls_environments.txt"
        )
        if err == None:
            bot_response = "Here is the list of environments in this cluster: \n"
            bot_response += "```{}```".format(list_of_environments)
        else:
            bot_response = "Something wrong happened :facepalm:. Deets: {}".format(err)
        return bot_response

    def fetch_selenium_status(self, cluster_name):
        # TODO: Refactor and move this to a dictionary lookup in Jenkinslib
        jenkins_instance = None
        if cluster_name == "qaplanetv1":
            jenkins_instance = "jenkins"
        elif cluster_name == "qaplanetv2":
            jenkins_instance = "jenkins2"
        else:
            return "This cluster does not exist :wat:"

        jl = JenkinsLib(jenkins_instance)
        err, id_of_triggered_job = jl.prepare_request_and_invoke(
            "selenium-check-status", None
        )

        if err == None:
            selenium_status_check_result = jl.get_status_of_job(
                "selenium-check-status", id_of_triggered_job
            )
            log.info("checking the result of the selenium-status-check job...")
            log.info(f"result: {selenium_status_check_result}")

            err, selenium_status = jl.fetch_archived_artifact(
                "selenium-check-status", "selenium-status.txt"
            )
            if err == None:
                bot_response = "Here is the status of the Selenium hub :selenium: \n"
                bot_response += "```{}```".format(selenium_status)
            else:
                bot_response = "Could not fetch archived artifacts from the Jenkins job :facepalm:. Deets: {}".format(
                    err
                )
        else:
            bot_response = "Could not run the Jenkins job :facepalm:. Deets: {}".format(
                err
            )

        return bot_response


if __name__ == "__main__":
    # jji = JenkinsJobInvoker()
    # result = jji.run_test_on_environment(
    #    "run-tests-on-environment", "jenkins2", "ci-env-1", "test-portal-homepageTest"
    # )
    # print(result)
    # result2 = jji.invoke_jenkins_job(
    #    "self-service-qa-gen3-roll",
    #    "jenkins2",
    #    '{ "SERVICE_NAME": "all", "TARGET_ENVIRONMENT": "ci-env-1" }',
    # )
    jji = JenkinsJobInvoker()
    # jji.replay_pr('gen3-qa', '549', 'test-portal-homepageTest,test-portal-dataUploadTest')
    jji.replay_pr(
        "gen3-qa", "549", "test-portal-homepageTest, test-portal-dataUploadTest"
    )
