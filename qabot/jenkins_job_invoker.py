from lib.jenkinslib import JenkinsLib
from lib.githublib import GithubLib
import json
import time
import os
import logging

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
                    jenkins_instance, job_name, id_of_triggered_job,
                )
            )
        else:
            bot_response = "Something wrong happened :facepalm:. Deets: {}".format(err)
        return bot_response

    def replay_pr(self, repo_name, pr_number, labels=[]):
        """
        Replay a Pull Request like a boss
        """
        githublib = GithubLib(repo=repo_name)
        try:
            if " " in labels:
                raise Exception("Whitespace found in comma-separated list of labels")
            if len(labels) > 0:
                labels = labels.split(",")
                log.info("applying labels...")
                for i, label in enumerate(labels):
                    # only override all labels on the first iteration
                    override_all = i == 0
                    githublib.set_label_to_pr(
                        int(pr_number), label.replace("*", ""), override_all
                    )
                    log.debug("applied label: {}".format(label))
            else:
                log.warn("Replaying PR without labels...")
        except Exception as err:
            return "Something wrong happened :facepalm:. Deets: {}".format(err)

        jl = JenkinsLib("jenkins")
        log.info("find the number of the last build...")
        job_num = jl.get_number_of_last_build(repo_name, pr_number)

        err, url_from_replayed_pr = jl.send_blueocean_request(
            repo_name, pr_number, job_num
        )
        if err == None:
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

    def roll_service(self, service_name, cluster_name, environment):
        """
        Roll a service in one of our gen3 environments
        """
        return "not implemented yet"

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
