import logging
import os
import subprocess

from qabot.lib.githublib import GithubLib

logging.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"))
log = logging.getLogger(__name__)


class PipelineMaintenance:
    def unquarantine_ci_env(self, ci_env_name):
        try:
            command = ["kubectl", "label", "namespace", ci_env_name, "quarantine-"]
            result = subprocess.run(command, capture_output=True, text=True, check=True)
            log.info(f"Output from command: {result.stdout}")
            command = [
                "kubectl",
                "label",
                "namespace",
                ci_env_name,
                "teardown=true",
                "--overwrite",
            ]
            result = subprocess.run(command, capture_output=True, text=True, check=True)
            log.info(f"Output from command: {result.stdout}")
            return f"The environment {ci_env_name} has been removed from quarantine. :awesome-face:"
        except subprocess.CalledProcessError as e:
            log.info(e.stderr)
            return f"Failed to unquarantine environment {ci_env_name}, please try again or contact QA team"

    def quarantine_ci_env(self, ci_env_name):
        command = [
            "kubectl",
            "label",
            "namespace",
            ci_env_name,
            "quarantine=true",
            "--overwrite",
        ]
        try:
            result = subprocess.run(command, capture_output=True, text=True, check=True)
            log.info(f"Output from command: {result.stdout}")
            return f"The environment {ci_env_name} has been placed under quarantine. :face_with_thermometer:"
        except subprocess.CalledProcessError as e:
            log.info(e.stderr)
            return f"Failed to quarantine environment {ci_env_name}, please try again or contact QA team"

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
                log.info("Replaying PR without labels...")
        except Exception as err:
            return "Something wrong happened :facepalm:. Deets: {}".format(err)

        bot_response = githublib.replay_pr(pr_number)
        return bot_response

    def replay_nightly_run(self, labels=""):
        """
        Replay nightly-build like a boss
        """
        repo_name = "gen3-code-vigil"
        githublib = GithubLib(repo=repo_name)

        json_params = {
            "TEST_LABELS": labels,
        }
        bot_response = githublib.trigger_gh_action_workflow(
            workflow_repo=repo_name,
            workflow_filename="nightly_run.yaml",
            ref="master",
            inputs=json_params,
        )
        if bot_response.status_code == 204:
            log.info("Workflow triggered successfully.")
            bot_response = "Replayed nightly-build run successfully. :awesome-face:"
        else:
            log.error(bot_response.text)
            raise Exception(f"Failed to trigger workflow: {bot_response.status_code}")
        return bot_response


if __name__ == "__main__":
    pipem1 = PipelineMaintenance()
