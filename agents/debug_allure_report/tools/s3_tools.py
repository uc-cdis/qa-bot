import json
import os
from pathlib import Path

import boto3
from langchain.tools import tool
from langchain_ollama import ChatOllama

LOCALSTACK_ENDPOINT = "http://localhost:4566"
REGION = "us-east-1"
ROLE_ARN = "arn:aws:iam::000000000000:role/MyS3AccessRole"
llm = ChatOllama(model="qwen3:4b", temperature=0)


def get_se_client_using_role():
    sts = boto3.client(
        "sts",
        endpoint_url=LOCALSTACK_ENDPOINT,
        region_name=REGION,
    )

    assumed = sts.assume_role(
        RoleArn=ROLE_ARN,
        RoleSessionName="localstack-session",
    )

    creds = assumed["Credentials"]

    return boto3.client(
        "s3",
        endpoint_url=LOCALSTACK_ENDPOINT,
        aws_access_key_id=creds["AccessKeyId"],
        aws_secret_access_key=creds["SecretAccessKey"],
        aws_session_token=creds["SessionToken"],
        region_name=REGION,
    )


@tool
def download_allure_files(bucket_name: str, prefix: str) -> None:
    """download the test cases files from S3 bucket and its prefix"""
    client = get_se_client_using_role()
    local_dir = "allure-report/data/test-cases"
    source_dir = f"{prefix}/data/test-cases"  # Folder in S3
    local_dir = "allure-report/data/test-cases"
    os.makedirs(local_dir, exist_ok=True)

    # ---- List objects with the given source_dir ----
    response = client.list_objects_v2(Bucket=bucket_name, Prefix=source_dir)

    for obj in response.get("Contents", []):
        key = obj["Key"]
        file_name = os.path.basename(key)
        local_path = os.path.join(local_dir, file_name)

        # Download each file
        client.download_file(bucket_name, key, local_path)


@tool
def find_failed_tests() -> str:
    """go throught the downloaded allure files and find the failed tests"""
    report_dir = Path("allure-report/data/test-cases")

    for case_file in report_dir.glob("*.json"):
        case = json.load(case_file.open())
        if case.get("status") == "failed" or case.get("status") == "broken":
            if case.get("name") == "test_home_page_navigation[chromium]":
                return case.get("statusTrace")


@tool
def analyze_failed_tests(failed_test_status_trace: str) -> str:
    """Analyze the failed tests and provide fixes"""
    debug_prompt = f"""
    You are a senior DevOps engineer.

    Analyze the status trace below.

    1. Identify the most likely root cause.
    2. Explain why it failed.
    3. Provide specific remediation steps.

    Status Trace:
    {failed_test_status_trace}
    """
    response = llm.invoke(debug_prompt)
    return response.content
