import boto3
import pytest
from moto import mock_aws


@pytest.fixture(autouse=True)
def aws_credentials(monkeypatch):
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_SECURITY_TOKEN", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")


@pytest.fixture(autouse=True)
def test_env(monkeypatch):
    monkeypatch.setenv("SOURCE_BUCKET", "test-alma-bucket")
    monkeypatch.setenv("TARGET_BUCKET", "test-pickup-bucket")
    monkeypatch.setenv("WORKSPACE", "test")
    monkeypatch.setenv("SOURCE_PREFIX", "test/source-prefix/bursar_export_to_test")
    monkeypatch.setenv("TARGET_PREFIX", "test/target-prefix/bursar_file_ready_to_pickup")


@pytest.fixture(autouse=True)
def mocked_s3():
    with mock_aws():
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


@pytest.fixture
def s3_client():
    return boto3.client("s3")


@pytest.fixture
def test_xml() -> str:
    with open("tests/fixtures/test.xml", encoding="utf-8") as file:
        return file.read()


@pytest.fixture
def event_data():
    return {"job_id": "1234"}
