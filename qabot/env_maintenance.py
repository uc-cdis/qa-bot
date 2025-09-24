import logging
import os
import subprocess

logging.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"))
log = logging.getLogger(__name__)


class EnvMaintenance:
    def roll_service(self, service_name: str, env_name: str):
        """
        Roll a service in one of our gen3 environments
        """
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
            return f"Namespace {env_name} is being scaled up. :rocket:"
        except subprocess.CalledProcessError as e:
            log.info(e.stderr)
            return f"Failed to scaleup namespace {env_name}, please try again or contact QA team"


if __name__ == "__main__":
    em = EnvMaintenance()
