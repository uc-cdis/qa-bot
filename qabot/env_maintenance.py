import logging
import os
import random
import string
import subprocess

logging.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"))
log = logging.getLogger(__name__)


class EnvMaintenance:
    def roll_service(self, service_name: str, env_name: str):
        """
        Roll a service in one of our gen3 environments
        """
        log.info(f"Running roll-service on {env_name}")
        try:
            # Sets commands and messages when all services need to be restarted
            if service_name.upper() == "ALL":
                restart_command = [
                    "kubectl",
                    "rollout",
                    "restart",
                    "deployment",
                    "-n",
                    env_name,
                ]
                status_command = [
                    "kubectl",
                    "rollout",
                    "status",
                    "deployment",
                    "-n",
                    env_name,
                ]
                msg = f"All services have been rolled on {env_name}. :awesome-face:"
            # Sets commands and messages when one service needs to be restarted
            else:
                if service_name not in ["sower", "ssjdispatcher"]:
                    deployment_name = f"{service_name}-deployment"
                else:
                    deployment_name = service_name
                restart_command = [
                    "kubectl",
                    "rollout",
                    "restart",
                    f"deployment/{deployment_name}",
                    "-n",
                    env_name,
                ]
                status_command = [
                    "kubectl",
                    "rollout",
                    "status",
                    f"deployment/{deployment_name}",
                    "-n",
                    env_name,
                ]
                msg = f"The service {service_name} has been rolled on {env_name}. :awesome-face:"
            # Run the commands
            result = subprocess.run(
                restart_command, capture_output=True, text=True, check=True
            )
            log.info(f"Output from command when rolling deployment: {result.stdout}")
            result = subprocess.run(
                status_command, capture_output=True, text=True, check=True
            )
            log.info(
                f"Output from command when checking deployment status: {result.stdout}"
            )
            return msg
        except subprocess.CalledProcessError as e:
            log.info(e.stderr)
            return f"Failed to roll service(s) on {env_name}, please try again or contact QA team"

    def scaleup_namespace(self, env_name):
        """
        Scaleup the given namespace in gen3 environments
        """
        log.info(f"Running scaleup-namespace on {env_name}")
        script_path = "/src/qabot/scripts/scaleup-namespace.sh"
        try:
            os.chmod(script_path, 0o755)
            # Run command to scaleup the namespace
            command = [
                script_path,
                env_name,
            ]
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=True,
                input="yes\n",
            )
            log.info(f"Output from command when scaling up namespace: {result.stdout}")
            command = [
                "kubectl",
                "rollout",
                "status",
                "deployment",
                "-n",
                env_name,
            ]
            result = subprocess.run(command, capture_output=True, text=True, check=True)
            log.info(
                f"Output from command when checking scaleup-namespace status: {result.stdout}"
            )
            return f"Namespace {env_name} has been scaled up. :rocket:"
        except subprocess.CalledProcessError as e:
            log.info(e.stderr)
            return f"Failed to scaleup namespace {env_name}, please try again or contact QA team"

    def run_gen3_job(self, job_name, env_name):
        """
        Run gen3 job in the given namespace in gen3 environments
        """
        log.info(f"Running run-gen3-job on {env_name}")
        try:
            cronjob_name = job_name
            if job_name == "etl":
                cronjob_name = "etl-cronjob"
            job_name += "-" + "".join(
                random.choices(string.ascii_lowercase + string.digits, k=4)
            )
            command = [
                "kubectl",
                "create",
                "job",
                f"--from=cronjob/{cronjob_name}",
                job_name,
                "-n",
                env_name,
            ]
            result = subprocess.run(command, capture_output=True, text=True, check=True)
            log.info(
                f"Output from command when running gen3 job {job_name}: {result.stdout}"
            )
            command = [
                "kubectl",
                "wait",
                "--for=condition=complete",
                "--timeout=600s",
                f"job/{job_name}",
                "-n",
                env_name,
            ]
            result = subprocess.run(command, capture_output=True, text=True, check=True)
            assert (
                "condition met" in result.stdout
            ), f"Condition didn't meet for job completion: {result.stdout}"
            return (
                f"Job {job_name} executed and completed on {env_name}. :checkered_flag:"
            )
        except subprocess.CalledProcessError as e:
            log.info(e.stderr)
            return f"Failed to execute {job_name} in namespace {env_name}, please try again or contact QA team"


if __name__ == "__main__":
    em = EnvMaintenance()
