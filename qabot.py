import logging
import os
import traceback

from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_bolt.app import App

from qabot.env_maintenance import EnvMaintenance
from qabot.greeter import Greeter
from qabot.manifests_checker import ManifestsChecker
from qabot.pipeline_maintenance import PipelineMaintenance
from qabot.release import ReleaseManager
from qabot.state_of_the_nation import StateOfTheNation

logging.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"))
log = logging.getLogger(__name__)

SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN").strip("\n")
SLACK_APP_TOKEN = os.environ.get("SLACK_APP_TOKEN").strip("\n")

app = App(token=SLACK_BOT_TOKEN)


def list_all_commands():
    all_commands = commands_map.keys()
    return "here are all the commands available in qa-bot:\n {}".format(
        ",".join(all_commands)
    )


commands_map = {
    "help": {
        "args": "",
        "example": "@qa-bot help",
        "call": list_all_commands,
        "pass_thread_ts": False,
    },
    "roll": {
        "args": "service to roll, ci_environment_name",
        "example": "@qa-bot roll guppy jenkins-brain",
        "call": EnvMaintenance().roll_service,
        "pass_thread_ts": False,
    },
    "replay-nightly-run": {
        "args": "comma-separated list of labels",
        "example": "@qa-bot replay-nightly-run test-portal-homepageTest,test-apis-dataUploadTest",
        "call": PipelineMaintenance().replay_nightly_run,
        "pass_thread_ts": False,
    },
    "replay-nightly-run-gen3ff": {
        "args": "comma-separated list of labels",
        "example": "@qa-bot replay-nightly-run-gen3ff test-portal-homepageTest,test-apis-dataUploadTest",
        "call": PipelineMaintenance().replay_nightly_run_gen3ff,
        "pass_thread_ts": False,
    },
    "replay-pr": {
        "args": "repo name, pr number, comma-separated list of labels",
        "example": "@qa-bot replay-pr gen3-qa 549 test-portal-homepageTest,test-apis-dataUploadTest",
        "call": PipelineMaintenance().replay_pr,
        "pass_thread_ts": False,
    },
    "self-service-release": {
        "args": "github username of environment's owner",
        "example": "@qa-bot self-service-release ac3eb",
        "call": ReleaseManager().roll_out_latest_gen3_release_to_environments,
        "pass_thread_ts": True,
    },
    "quarantine-ci-environment": {
        "args": "ci_environment_name",
        "example": "jenkins-brain",
        "call": PipelineMaintenance().quarantine_ci_env,
        "pass_thread_ts": False,
    },
    "unquarantine-ci-environment": {
        "args": "ci_environment_name",
        "example": "jenkins-brain",
        "call": PipelineMaintenance().unquarantine_ci_env,
        "pass_thread_ts": False,
    },
    "scaleup-namespace": {
        "args": "ci_environment_name",
        "example": "jenkins-brain",
        "call": EnvMaintenance().scaleup_namespace,
        "pass_thread_ts": False,
    },
    "run-gen3-job": {
        "args": "gen3_job_name, env_name",
        "example": "@qa-bot run-gen3-job usersync jenkins-brain",
        "call": EnvMaintenance().run_gen3_job,
        "pass_thread_ts": False,
    },
    "test-external-pr": {
        "args": "repo_name, pr_num",
        "example": "@qa-bot test-external-pr fence 123",
        "call": PipelineMaintenance().test_external_pr,
        "pass_thread_ts": False,
    },
    "hello": {
        "args": "",
        "example": "@qa-bot hello",
        "call": Greeter().say_hello,
        "pass_thread_ts": False,
    },
}


def process_command(command, args, thread_ts=None):
    log.info(f"command = {command}, args = {args}")
    # process args to handle whitespaces inside json blocks
    entered_json_block_at_index = None
    for i, a in enumerate(args):
        if "{" in a and "}" not in a:
            # print('Entered an incomplete JSON block. We have whitespaces in one of the json values')
            entered_json_block_at_index = i
            continue
        if entered_json_block_at_index:
            args[entered_json_block_at_index] += " " + args[i]

    if entered_json_block_at_index:
        args = args[: entered_json_block_at_index + 1]
        log.debug("args: {}".format(args))

    # execute command
    if command in commands_map.keys():
        log.info("args: " + str(args))
        if len(args) >= 1 and args[0] == "help":
            return f"""instructions for {command}: \n
args:  {commands_map[command]['args']}
example:  {commands_map[command]['example']}
      """
        else:
            try:
                if commands_map[command]["pass_thread_ts"]:
                    return commands_map[command]["call"](*args, thread_ts)
                else:
                    return commands_map[command]["call"](*args)
            except TypeError as te:
                return str(te)
            except Exception as e:
                log.error(e)
                traceback.print_exc()
                return "Something went wrong. Contact the QA team"
    else:
        return "command not recognized. :thisisfine:"


@app.event("app_mention")
def handle_app_mention(payload, say, logger):
    logger.info(payload)
    user = payload.get("user", "")
    if not user:
        logger.info("There is no user associated with the last message")
    text = (
        payload.get("text", "").replace("\xa0", " ").replace("“", '"').replace("”", '"')
    )
    if text:
        msg_parts = list(filter(None, text.split(" ")))
        # identify command
        if len(msg_parts) > 1:
            command = msg_parts[1]
            args = msg_parts[2:]
            thread_ts = (payload.get("thread_ts") or payload.get("ts"),)
            say(
                text=f"<@{payload['user']}> {process_command(command, args, thread_ts)}",
                thread_ts=thread_ts,
            )
    else:
        usage_msg = """
# Usage instructions: *@qa-bot <command>* \n
# e.g., @qa-bot command
#           _visit https://github.com/uc-cdis/qa-bot to learn more_
#           """
        say(
            text=f"<@{payload['user']}> {usage_msg}",
            thread_ts=payload.get("thread_ts") or payload.get("ts"),
        )


@app.event("message")
def handle_message_events(body, say, logger):
    logger.info(body)


if __name__ == "__main__":
    SocketModeHandler(app, SLACK_APP_TOKEN).start()
