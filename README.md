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

Project Managers can start the release process with a simple Slack message. The Bot will invoke the required Jenkins job to automatically tailor a Pull Request in `cdis-manifest` targeting all the environments associated with that PM / Project.

Example: `@qa-bot self-service-release`

*whereis*

Sweeps all manifests in cdis-manifest to find a specific “<service_name> <version>” or “release <version>“. Very useful to track the adoption rate of monthly releases and also quickly find whether or not a given service hot patch / security patch has been deployed to all environments.

Here are a couple of examples:

```
@qa-bot whereis revproxy 1.17.6-ctds-1.0.1
@qa-bot whereis release 2020.11
```

*run-test*

Invokes a Jenkins job that exists both in Jenkins1 and Jenkins2 called run-tests-on-environment: 
```
https://jenkins.planx-pla.net/job/run-tests-on-environment/
https://jenkins2.planx-pla.net/job/run-tests-on-environment/
```

It requires the following parameters: TARGET_ENVIRONMENT (e.g., qa-dcp) & TEST_SUITE (e.g., test-portal-homepageTest). Here’s an example:

`@qa-bot run-test jenkins2 ci-env-1 test-portal-homepageTest`

*run-jenkins-job*

This command is used quite frequently by Developers and Bios across PlanX. It basically invokes any Jenkins job to interact with Gen3 environments in either `qaplanetv1` or `qaplanetv2`, which requires either a `jenkins` or `jenkins2` argument (respectively) to indicate where the environment can be found. e.g., `qa-dcp` is hosted on `qaplanetv1`, therefore, to roll all services against this environment one needs to run:

`@qa-bot run-jenkins-job self-service-gen3-roll jenkins {"SERVICE_NAME":"fence","TARGET_ENVIRONMENT":"qa-dcp"}`

But, for `qa-dcf`, that lives in `qaplanetv2`, the _jenkins2_ argument is required:

`@qa-bot  run-jenkins-job self-service-gen3-roll jenkins2 {"SERVICE_NAME":"all","TARGET_ENVIRONMENT":"qa-dcf"}`

There are many Jenkins jobs, the examples above illustrate the usage of self-service-gen3-roll , which has the ability to run a gen3 roll command for a given service (like fence, guppy, etc.) or all services (to wake up an environment whose pods have been disabled as part of our cost-saving nightly job).

This is widely adopted as it gives our PlanX team members the ability to perform operations without the need to SSH to a given user namespace in our Admin VM (through the DEV VPN), which is particularly useful for whoever doesn’t have access to the environments or just wants to perform operations against the environment quickly through Slack without wasting time.

Other Jenkins jobs that are often used are:

*self-service-run-usersync*
`@qa-bot run-jenkins-job self-service-run-usersync jenkins {“TARGET_ENVIRONMENT”:“qa-dcp”}`

*gen3-self-service-push-quay-img-to-ecr*

`@qa-bot  run-jenkins-job gen3-self-service-push-quay-img-to-ecr jenkins {"SERVICE_NAME":"fence","QUAY_VERSION":"4.24.0"}`

*self-service-generate-test-data*

`@qa-bot run-jenkins-job self-service-generate-test-data jenkins {"TARGET_ENVIRONMENT":"qa-dcp"}`

*self-service-run-etl*

`@qa-bot run-jenkins-job self-service-run-etl jenkins {“TARGET_ENVIRONMENT”:“qa-dcp”}`

*gen3-self-service-push-dockerhub-img-to-quay*

`@qa-bot run-jenkins-job gen3-self-service-push-dockerhub-img-to-quay jenkins {“SOURCE”:“python:3.7-slim-buster”,“TARGET”:“quay.io/cdis/python:3.7-slim-buster”}`

*create-release-pr*

`@qa-bot run-jenkins-job create-release-pr jenkins {“PR_TITLE”:“BDCat prod release”,“SOURCE_ENVIRONMENT”:“preprod.gen3.biodatacatalyst.nhlbi.nih.gov”,“TARGET_ENVIRONMENT”:“gen3.biodatacatalyst.nhlbi.nih.gov”,“REPO_NAME”:“cdis-manifest”}`

*deploy-gen3-release-to-environment*

`@qa-bot run-jenkins-job deploy-gen3-release-to-environment jenkins {"GEN3_RELEASE":"2020.12","PR_TITLE":"BDCat PRE-Prod release","TARGET_ENVIRONMENT":"preprod.gen3.biodatacatalyst.nhlbi.nih.gov","REPO_NAME":"cdis-manifest"}`

TODO: The QA team needs to, eventually, make these commands friendlier by wrapping up the JSON formatted list of Jenkins job arguments as proper Slack bot command arguments.

*list-environments*

Lists all the environments (k8s namespaces) from a given EKS cluster.

Exameple: `@qa-bot list-environments qaplanetv1`

*hello*

Just replies back with a ”hello” msg (for testing purposes)

*compare-manifests*

Compares the manifest from a PR that is meant to deploy changes to a PROD environment against a PREPROD environment to make sure there are no discrepancies between the versions declared on them (This was implemented before the gen3-release-utils was developed, back when there was no automated code promotion between preprod and prod). Hence, it is deprecated (To be removed later).

Example: `@qa-bot compare-manifests 1487 preprod.gen3.biodatacatalyst.nhlbi.nih.gov`
