# qa-bot

Slack bot to automate QA tasks

# Overview
The @qa-bot is a Slack bot that has been registered as a custom-integration of our cdis.slack.com Slack Community to automate various QA & Release Management tasks.

## Running tests

`poetry run python -u -m unittest discover tests`

## Features

Here is a list of the current commands supported by our qa-bot:

*help*

Prints instructions for each command with examples.

*self-service-release*

Project Managers can start the release process with a simple Slack message. The Bot will invoke the required github action workflow to automatically tailor a Pull Request in `gen3-gitops` targeting all the environments associated with that PM / Project.

Example: `@qa-bot self-service-release`

*roll*

Example: `@qa-bot roll [<service-name>|ALL] <env-name>`

*replay-nightly-run*

Example: `@qa-bot replay-nightly-run <test-labels-seperated-by-comma>`

*replay-pr*

Example: `@qa-bot replay-replay-pr <repo-name> <run-number> <test-labels-seperated-by-comma>`

*quarantine-ci-environment*

Example: `@qa-bot quarantine-ci-environment <env-name>`

*unquarantine-ci-environment*

Example: `@qa-bot unquarantine-ci-environment <env-name>`

*scaleup-namespace*

Example: `@qa-bot scaleup-namespace <env-name>`

*hello*

Just replies back with a ”hello” msg (for testing purposes)
