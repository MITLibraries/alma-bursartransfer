import os

import boto3
import pytest
from moto import mock_s3


@pytest.fixture(autouse=True)
def test_env():
    os.environ = {
        "BURSAR_ALMA_EXPORT_BUCKET_ID": "test-alma-bucket",
        "BURSAR_S3_EXTRACT_BUCKET_ID": "test-bursar-bucket",
        "WORKSPACE": "test",
    }


@pytest.fixture(autouse=True)
def mocked_s3():
    with mock_s3():
        client = boto3.client("s3", region_name="us-east-1")
        client.create_bucket(Bucket="test-bursar-bucket")
        client.create_bucket(Bucket="test-alma-bucket")
        with open(
            "tests/fixtures/test.xml",
            "rb",
        ) as file:
            client.put_object(
                Bucket="test-alma-bucket",
                Key="exlibris/bursar/test.xml",
                Body=file,
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
def s3_event():
    event = {
        "Records": [
            {
                "eventVersion": "2.0",
                "eventSource": "aws:s3",
                "awsRegion": "us-east-1",
                "eventTime": "1970-01-01T00:00:00.000Z",
                "eventName": "ObjectCreated:Put",
                "userIdentity": {"principalId": "AIDAJDPLRKLG7UEXAMPLE"},
                "requestParameters": {"sourceIPAddress": "127.0.0.1"},
                "responseElements": {
                    "x-amz-request-id": "C3D13FE58DE4C810",
                    "x-amz-id-2": "FMyUVURIY8/IgAtTv8xRjskZQpcI"
                    "Z9KG4V5Wp6S7S/JRWeUWerMUE5JgHvANOjpD",
                },
                "s3": {
                    "s3SchemaVersion": "1.0",
                    "configurationId": "testConfigRule",
                    "bucket": {
                        "name": "test-alma-bucket",
                        "ownerIdentity": {"principalId": "A3NL1KOZZKExample"},
                        "arn": "arn:aws:s3:::sourcebucket",
                    },
                    "object": {
                        "key": "exlibris/bursar/test.xml",
                        "size": 1024,
                        "eTag": "d41d8cd98f00b204e9800998ecf8427e",
                        "versionId": "096fKKXTRTtl3on89fVO.nfljtsv6qko",
                    },
                },
            }
        ]
    }
    return event
