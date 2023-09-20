import os

import boto3
import pytest
from moto import mock_s3


@pytest.fixture(autouse=True)
def aws_credentials():
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"


@pytest.fixture(autouse=True)
def test_env():
    os.environ = {
        "SOURCE_BUCKET": "test-alma-bucket",
        "TARGET_BUCKET": "test-pickup-bucket",
        "WORKSPACE": "test",
        "SOURCE_PREFIX": "test/source-prefix/bursar_export_to_test",
        "TARGET_PREFIX": "test/target-prefix/bursar_file_ready_to_pickup",
    }


@pytest.fixture(autouse=True)
def mocked_s3():
    with mock_s3():
        client = boto3.client("s3", region_name="us-east-1")
        client.create_bucket(Bucket="test-pickup-bucket")
        client.create_bucket(Bucket="test-alma-bucket")
        with open(
            "tests/fixtures/test.xml",
            "rb",
        ) as file:
            client.put_object(
                Bucket="test-alma-bucket",
                Key="test/source-prefix/bursar_export_to_test-1234-5678.xml",
                Body=file,
            )
        client.create_bucket(Bucket="no-files")  # a bucket with no files
        client.create_bucket(Bucket="no-match")
        client.put_object(
            Bucket="no-match",
            Key="test/source-prefix/bursar_export_to_test-abcd-5678.xml",
            Body="no match",
        )
        client.create_bucket(Bucket="multiple-matches")
        client.put_object(
            Bucket="multiple-matches",
            Key="test/source-prefix/bursar_export_to_test-1234-5678.xml",
            Body="multiple file 1",
        )
        client.put_object(
            Bucket="multiple-matches",
            Key="test/source-prefix/bursar_export_to_test-1234-abcd.xml",
            Body="multiple file 2",
        )

        yield client


@pytest.fixture()
def s3_client():
    yield boto3.client("s3")


@pytest.fixture()
def test_xml() -> str:
    with open("tests/fixtures/test.xml", encoding="utf-8") as file:
        xml_string = file.read()
    return xml_string


@pytest.fixture()
def event_data():
    event = {"job_id": "1234"}
    return event
