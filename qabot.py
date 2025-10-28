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
    },
    "roll": {
        "args": "service to roll, ci_environment_name",
        "example": "@qa-bot roll guppy jenkins-brain",
        "call": EnvMaintenance().roll_service,
    },
    "replay-nightly-run": {
        "args": "comma-separated list of labels",
        "example": "@qa-bot replay-nightly-run test-portal-homepageTest,test-apis-dataUploadTest",
        "call": PipelineMaintenance().replay_nightly_run,
    },
    "replay-pr": {
        "args": "repo name, pr number, comma-separated list of labels",
        "example": "@qa-bot replay-pr gen3-qa 549 test-portal-homepageTest,test-apis-dataUploadTest",
        "call": PipelineMaintenance().replay_pr,
    },
    "self-service-release": {
        "args": "github username of environment's owner",
        "example": "@qa-bot self-service-release ac3eb",
        "call": ReleaseManager().roll_out_latest_gen3_release_to_environments,
    },
    "quarantine-ci-environment": {
        "args": "ci_environment_name",
        "example": "jenkins-brain",
        "call": PipelineMaintenance().quarantine_ci_env,
    },
    "unquarantine-ci-environment": {
        "args": "ci_environment_name",
        "example": "jenkins-brain",
        "call": PipelineMaintenance().unquarantine_ci_env,
    },
    "scaleup-namespace": {
        "args": "ci_environment_name",
        "example": "jenkins-brain",
        "call": EnvMaintenance().scaleup_namespace,
    },
    "run-gen3-job": {
        "args": "gen3_job_name, env_name",
        "example": "@qa-bot run-gen3-job usersync jenkins-brain",
        "call": EnvMaintenance().run_gen3_job,
    },
    "test-external-pr": {
        "args": "repo_name, pr_num",
        "example": "@qa-bot test-external-pr fence 123",
        "call": PipelineMaintenance().test_external_pr,
    },
    "hello": {"args": "", "example": "@qa-bot hello", "call": Greeter().say_hello},
}


def process_command(command, args):
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
            say(process_command(command, args))
    else:
        say(
            """
# Usage instructions: *@qa-bot <command>* \n
# e.g., @qa-bot command
#           _visit https://github.com/uc-cdis/qa-bot to learn more_
#           """
        )


@app.event("message")
def handle_message_events(body, say, logger):
    logger.info(body)


if __name__ == "__main__":
    SocketModeHandler(app, SLACK_APP_TOKEN).start()
