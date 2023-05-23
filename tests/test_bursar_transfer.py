from importlib import reload

import pytest

from lambdas import bursar_transfer


def test_bursar_transfer_configures_sentry_if_dsn_present(caplog, monkeypatch):
    monkeypatch.setenv("SENTRY_DSN", "https://1234567890@00000.ingest.sentry.io/123456")
    reload(bursar_transfer)
    assert (
        "Sentry DSN found, exceptions will be sent to Sentry with env=test"
        in caplog.text
    )


def test_bursar_transfer_doesnt_configure_sentry_if_dsn_not_present(
    caplog, monkeypatch
):
    monkeypatch.delenv("SENTRY_DSN", raising=False)
    reload(bursar_transfer)
    assert "No Sentry DSN found, exceptions will not be sent to Sentry" in caplog.text


def test_lambda_handler_missing_workspace_env_raises_error(monkeypatch):
    monkeypatch.delenv("WORKSPACE", raising=False)
    with pytest.raises(RuntimeError) as error:
        bursar_transfer.lambda_handler({}, {})
    assert "Required env variable WORKSPACE is not set" in str(error)


def test_get_xml(mocked_s3):
    with open("tests/fixtures/test.xml", encoding="utf-8") as file:
        xml_file = file.read()
    assert (
        bursar_transfer.get_xml(
            mocked_s3, bucket="test-alma-bucket", key="exlibris/bursar/test.xml"
        )
        == xml_file
    )


def test_put_csv(mocked_s3):
    with open("tests/fixtures/test.csv", encoding="utf-8") as file:
        csv_file = file.read()
    bursar_transfer.put_csv(
        mocked_s3,
        bucket="test-bursar-bucket",
        key="exlibris/bursar/test.csv",
        csv_file=csv_file,
    )

    retrieved_file = mocked_s3.get_object(
        Bucket="test-bursar-bucket", Key="exlibris/bursar/test.csv"
    )
    assert (
        retrieved_file["ResponseMetadata"]["HTTPHeaders"]["content-type"] == "text/csv"
    )
    assert retrieved_file["Body"].read().decode("utf-8") == csv_file


def test_xml_to_csv_error_if_missing_field(test_xml: str) -> None:
    xml_missing_amount = test_xml.replace("123.45", "")
    print(xml_missing_amount)
    with pytest.raises(ValueError):
        bursar_transfer.xml_to_csv(xml_missing_amount)


def test_xml_to_csv(test_xml: str) -> None:
    with open("tests/fixtures/test.csv", encoding=("utf-8")) as file:
        expected_file = file.read()
        assert bursar_transfer.xml_to_csv(test_xml) == expected_file
