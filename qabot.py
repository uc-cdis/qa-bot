import logging
import os
import traceback

from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_bolt.app import App

from qabot.greeter import Greeter
from qabot.jenkins_job_invoker import JenkinsJobInvoker
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
    "compare-manifests": {
        "args": "pr number and signed-off manifest",
        "example": "@qa-bot compare-manifests 928 internalstaging.datastage.io",
        "call": ManifestsChecker().compare_manifests,
    },
    "whereis": {
        "args": "release version",
        "example": "@qa-bot whereis release 2020.02 \n or \n @qa-bot whereis tube 2020.08",
        "call": ManifestsChecker().whereis_version,
    },
    "run-test": {
        "args": "jenkins instance, target environment and test suite to be executed",
        "example": "@qa-bot run-test jenkins2 ci-env-1 test-portal-homepageTest",
        "call": JenkinsJobInvoker().run_test_on_environment,
    },
    "create-ticket": {
        "args": 'ticket_type {"title":"any title","description":"any description","assignee":"Name [Middle Name] LastName"}',
        "example": '@qa-bot create-ticket bug {"title":"PR-1234 failed. help!","description":"This test test-portal-discoveryPageTest is failing","assignee":"Hara Prasad Juvala"}',
        "call": PipelineMaintenance().create_ticket,
    },
    "check-result": {
        "args": "job name, id id and jenkins instance",
        "example": "@qa-bot check-result run-tests-on-environment 21 jenkins2",
        "call": JenkinsJobInvoker().get_status_of_job,
    },
    "run-jenkins-job": {
        "args": "job name, jenkins instance and parameters (json without spaces)",
        "example": '@qa-bot run-jenkins-job self-service-qa-gen3-roll jenkins2 {"SERVICE_NAME":"all","TARGET_ENVIRONMENT":"ci-env-1"}',
        "call": JenkinsJobInvoker().invoke_jenkins_job,
    },
    "list-environments": {
        "args": "selected K8s cluster (e.g., qaplanetv1, qaplanetv2)",
        "example": "@qa-bot list-environments qaplanetv1",
        "call": JenkinsJobInvoker().fetch_list_of_environments,
    },
    "selenium-check-status": {
        "args": "selected K8s cluster (e.g., qaplanetv1, qaplanetv2)",
        "example": "@qa-bot selenium-check-status qaplanetv1",
        "call": JenkinsJobInvoker().fetch_selenium_status,
    },
    "roll-service": {
        "args": "service to roll, ci_environment_name",
        "example": "@qa-bot roll-service guppy jenkins-brain",
        "call": JenkinsJobInvoker().roll_service,
    },
    "replay-nightly-run": {
        "args": "repo name, comma-separated list of labels",
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
    "state-of-the-nation": {
        "args": "name_of_the_project state_of_the_prs(all, open or closed) [number_of_prs_to_scan]",
        "example": "bdcat all 50",
        "call": StateOfTheNation().run_state_of_the_nation_report,
    },
    "get-failure-rate": {
        "args": "test_suite_name",
        "example": "test-portal-homepageTest",
        "call": PipelineMaintenance().failure_rate_for_test_suite,
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
    "check-pool-of-ci-environments": {
        "args": "",
        "example": "@qa-bot check-pool-of-ci-environments",
        "call": PipelineMaintenance().check_pool_of_ci_envs,
    },
    "ci-benchmarking": {
        "args": "repo_name pr_number stage_name",
        "example": " cdis-manifest 3265 K8sReset\n gitops-qa 1523 RunTests",
        "call": PipelineMaintenance().ci_benchmarking,
    },
    "fetch-test-results": {
        "args": "repo_name pr_number",
        "example": " cdis-manifest 1234 \n fence 5678",
        "call": PipelineMaintenance().fetch_ci_failures,
    },
    "who-do-I-ask-about": {
        "args": "repo_name",
        "example": "@qa-bot who-do-I-ask-about arborist",
        "call": PipelineMaintenance().get_repo_sme,
    },
    "get-ci-summary": {
        "args": "",
        "example": "@qa-bot get-ci-summary",
        "call": PipelineMaintenance().get_ci_summary,
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


# @app.event("message")
# def capture_messages(**payload):
#     data = payload["data"]
#     # this will log every single msg, it should be disabled by default
#     # log.debug("### DATA: {}".format(data))

#     channel_id = data["channel"]

#     # determine user for logging purposes
#     # ignore username when receiving msgs from other bots or other events
#     if "user" in data.keys():
#         user = data["user"]
#     else:
#         user = ""
#     # determines if the bot is being called
#     the_msg = ""
#     if "text" in data.keys():
#         the_msg = data["text"]
#     elif data["subtype"] == "message_changed":
#         the_msg = data["message"]["text"]

#     if "bot_profile" in data.keys() and data["bot_profile"]["id"] == "B80E3HU5P":
#         log.info("Jenkins just posted a Slack msg")
#         bot_reply = PipelineMaintenance().react_to_jenkins_updates(data)
#         if bot_reply is not None:
#             post_message(payload, bot_reply, "C01TS6PDMRT")


if __name__ == "__main__":
    SocketModeHandler(app, SLACK_APP_TOKEN).start()
