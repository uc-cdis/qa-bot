import json
import logging
import os
import random
import re
import string
import subprocess
import time
from datetime import datetime, timedelta, timezone

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
                scale_up_command = [
                    "kubectl",
                    "scale",
                    "deployment",
                    "--all",
                    "--replicas=1",
                    "-n",
                    env_name,
                ]
                scale_up_result = subprocess.run(
                    scale_up_command, capture_output=True, text=True, check=True
                )
                log.info(
                    f"Output from command when scaling up deployment: {scale_up_result.stdout}"
                )
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
                if service_name not in [
                    "sower",
                    "ssjdispatcher",
                    "jupyter-enterprise-gateway",
                ]:
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

    def argocd_sync_status(
        self, app_name, env_name, since, start_wait=30, finish_wait=300
    ):
        """
        Read the last operation state of an ArgoCD application and wait for the
        sync triggered at `since` to reach a final phase. Only the phase and
        start/finish times are read; the operation message is never fetched since
        it can contain sensitive details. Polls for up to start_wait seconds for
        the operation to start (the controller picks up the patched operation
        asynchronously), then up to finish_wait seconds for it to finish.
        Returns (started, phase, details).
        """
        jsonpath = (
            'phase: {.status.operationState.phase}{"\\n"}'
            'started: {.status.operationState.startedAt}{"\\n"}'
            'finished: {.status.operationState.finishedAt}{"\\n"}'
        )
        command = [
            "kubectl",
            "get",
            "application",
            app_name,
            "-n",
            env_name,
            "-o",
            f"jsonpath={jsonpath}",
        ]
        start_deadline = time.monotonic() + start_wait
        finish_deadline = time.monotonic() + finish_wait
        details = ""
        while True:
            result = subprocess.run(command, capture_output=True, text=True, check=True)
            details = result.stdout.strip()
            log.info(f"Operation state of {app_name}: {details}")
            fields = dict(
                line.split(": ", 1) for line in details.splitlines() if ": " in line
            )
            phase = fields.get("phase", "").strip()
            started = fields.get("started", "").strip()
            recent = False
            if started:
                # an operation older than our patch is a previous sync, not ours
                started_at = datetime.fromisoformat(started.replace("Z", "+00:00"))
                recent = started_at >= since - timedelta(seconds=10)
            if recent and phase in ("Succeeded", "Failed", "Error"):
                return True, phase, details
            deadline = finish_deadline if recent else start_deadline
            if time.monotonic() >= deadline:
                return recent, phase, details
            time.sleep(5)

    def argocd_sync(self, env_name, slack_user):
        """
        Trigger an ArgoCD sync (with prune) for the application of the given env,
        recording the slack user who requested it as the initiator.
        The application is named either gen3-dev-{env_name} or {env_name}, so try both.
        """
        if not slack_user:
            return "Could not identify the Slack user who triggered argocd-sync, so it was not run."
        # env_name comes from a slack message and ends up as a kubectl argument
        if not re.fullmatch(r"[a-z0-9][a-z0-9.-]*", env_name):
            return f"`{env_name}` is not a valid environment name."
        log.info(f"Running argocd-sync on {env_name} for {slack_user}")
        patch = json.dumps(
            {
                "operation": {
                    "initiatedBy": {"username": slack_user},
                    "sync": {"prune": True},
                }
            }
        )
        results = []  # (app_name, icon, summary, details)
        patched = []
        since = datetime.now(timezone.utc)
        # patch every application first so the syncs run in parallel, then wait on each
        for app_name in (f"gen3-dev-{env_name}", env_name):
            command = [
                "kubectl",
                "patch",
                "application",
                app_name,
                "-n",
                env_name,
                "--type",
                "merge",
                "-p",
                patch,
            ]
            try:
                result = subprocess.run(
                    command, capture_output=True, text=True, check=True
                )
                log.info(f"Output from argocd sync of {app_name}: {result.stdout}")
                patched.append(app_name)
            except subprocess.CalledProcessError as e:
                log.info(e.stderr)
                # an application that doesn't exist under this name is expected
                if "NotFound" not in e.stderr and "not found" not in e.stderr:
                    results.append((app_name, ":x:", "failed to trigger sync", ""))
        for app_name in patched:
            try:
                recent, phase, details = self.argocd_sync_status(
                    app_name, env_name, since
                )
            except (subprocess.CalledProcessError, ValueError) as se:
                log.info(f"Could not read sync status of {app_name}: {se}")
                results.append(
                    (
                        app_name,
                        ":x:",
                        "sync triggered but its status could not be read",
                        "",
                    )
                )
                continue
            if not recent:
                results.append(
                    (app_name, ":x:", "sync did not start after the patch", details)
                )
            elif phase == "Succeeded":
                results.append(
                    (app_name, ":white_check_mark:", "sync succeeded", details)
                )
            elif phase == "Running":
                results.append(
                    (app_name, ":hourglass_flowing_sand:", "sync in progress", details)
                )
            else:
                results.append(
                    (app_name, ":x:", f"sync {phase or 'status unknown'}", details)
                )

        if not results:
            return f":x: No ArgoCD application found for {env_name}, please try again or contact QA team"
        icons = {r[1] for r in results}
        if icons == {":white_check_mark:"}:
            header = f":white_check_mark: ArgoCD sync succeeded for {env_name}."
        elif icons <= {":white_check_mark:", ":hourglass_flowing_sand:"}:
            header = f":hourglass_flowing_sand: ArgoCD sync still in progress for {env_name}."
        else:
            header = f":x: ArgoCD sync needs attention for {env_name}, please retry or contact QA team."
        blocks = [
            f"{icon} {app_name}: {summary}" + (f"\n{details}" if details else "")
            for app_name, icon, summary, details in results
        ]
        return header + "\n" + "\n".join(blocks)


if __name__ == "__main__":
    em = EnvMaintenance()
