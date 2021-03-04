import os
import slack
import logging

from jenkins_job_invoker import JenkinsJobInvoker
from manifests_checker import ManifestsChecker
from state_of_the_nation import StateOfTheNation
from greeter import Greeter
from release import ReleaseManager

logging.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"))
log = logging.getLogger(__name__)

slack_token = os.environ["SLACK_API_TOKEN"]
# override base_url to use whitelisted domain
rtmclient = slack.RTMClient(
    token=slack_token.strip(), base_url="https://cdis.slack.com/api/"
)


def list_all_commands():
    all_commands = commands_map.keys()
    return "here are all the commands available in qa-bot:\n {}".format(
        ",".join(all_commands)
    )


commands_map = {
    "help": {
        "args": "list all commands",
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
    "roll": {
        "args": "service to roll, jenkins instance and parameters (json without spaces)",
        "example": "@qa-bot roll guppy in qaplanetv1 qa-dcp",
        "call": JenkinsJobInvoker().roll_service,
    },
    "replay-pr": {
        "args": "repo name, pr number, comma-separated list of labels",
        "example": "@qa-bot replay-pr gen3-qa 549 test-portal-homepageTest,test-apis-dataUploadTest",
        "call": JenkinsJobInvoker().replay_pr,
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
    "hello": {"args": "", "example": "@qa-bot hello", "call": Greeter().say_hello},
}


def process_command(command, args):
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
            return help_txt
        else:
            try:
                return commands_map[command]["call"](*args)
            except TypeError as te:
                return str(te)
            except Exception as e:
                log.error(e)
                return "something went wrong. Contact the QA team"
    else:
        return "command not recognized. :thisisfine:"


def post_message(payload, bot_reply, channel_id):
    webclient = payload["web_client"]
    webclient.chat_postMessage(
        channel=channel_id,
        text=bot_reply,
        username="qa-bot",
        icon_url="https://avatars.slack-edge.com/2019-11-23/846894374304_3adeb13422453e142051_192.png",
    )


@slack.RTMClient.run_on(event="message")
def capture_messages(**payload):
    data = payload["data"]
    log.debug("### DATA: {}".format(data))
    if "subtype" not in data.keys():
        channel_id = data["channel"]
        user = data["user"]

        # determines if the bot is being called
        if "<@UQKCGCU1H>" in data["text"]:
            log.info("user {} just sent a msg: {}".format(user, data["text"]))

            raw_command = data["text"].replace("\xa0", " ")
            raw_command = raw_command.replace("“", '"').replace("”", '"')
            msg_parts_split = raw_command.split(" ")
            msg_parts = list(filter(None, msg_parts_split))
            # identify command
            if len(msg_parts) > 1:
                command = msg_parts[1]
                args = msg_parts[2:]
                bot_reply = process_command(command, args)
            else:
                bot_reply = """
Usage instructions: *@qa-bot <command>* \n
e.g., @qa-bot command
          _visit https://github.com/uc-cdis/qa-bot to learn more_
          """

            post_message(payload, bot_reply, channel_id)


def main():
    rtmclient.start()


if __name__ == "__main__":
    main()
