from datetime import date
from importlib import reload

import pytest

from lambdas import bursar_transfer


def test_bursar_transfer_configures_sentry_if_dsn_present(caplog, monkeypatch) -> None:
    monkeypatch.setenv("SENTRY_DSN", "https://1234567890@00000.ingest.sentry.io/123456")
    reload(bursar_transfer)
    assert (
        "Sentry DSN found, exceptions will be sent to Sentry with env=test"
        in caplog.text
    )


def test_bursar_transfer_doesnt_configure_sentry_if_dsn_not_present(
    caplog, monkeypatch
) -> None:
    monkeypatch.delenv("SENTRY_DSN", raising=False)
    reload(bursar_transfer)
    assert "No Sentry DSN found, exceptions will not be sent to Sentry" in caplog.text


def test_get_bursar_export_xml_from_s3(mocked_s3) -> None:
    with open("tests/fixtures/test.xml", encoding="utf-8") as file:
        xml_file = file.read()
    assert (
        bursar_transfer.get_bursar_export_xml_from_s3(
            mocked_s3, bucket="test-alma-bucket", key="exlibris/bursar/test.xml"
        )
        == xml_file
    )


@pytest.mark.parametrize(
    "test_date,expected",
    [
        (date(2023, 1, 1), "2023FA"),
        (date(2023, 2, 1), "2023FA"),
        (date(2023, 3, 1), "2023SP"),
        (date(2023, 4, 1), "2023SP"),
        (date(2023, 5, 1), "2023SP"),
        (date(2023, 6, 1), "2023SP"),
        (date(2023, 7, 1), "2023SU"),
        (date(2023, 8, 1), "2023SU"),
        (date(2023, 9, 1), "2024FA"),
        (date(2023, 10, 1), "2024FA"),
        (date(2023, 11, 1), "2024FA"),
        (date(2023, 12, 1), "2024FA"),
    ],
)
def test_billing_term(test_date, expected) -> None:
    assert bursar_transfer.billing_term(test_date) == expected


def test_xml_to_csv_error_if_missing_field(test_xml: str) -> None:
    xml_missing_amount = test_xml.replace("123.45", "")
    today = date(2023, 3, 1)
    with pytest.raises(ValueError):
        bursar_transfer.xml_to_csv(xml_missing_amount, today)


def test_xml_to_csv(test_xml: str) -> None:
    with open("tests/fixtures/test.csv", encoding="utf-8") as file:
        expected_file = file.read()
        today = date(2023, 3, 1)
        assert bursar_transfer.xml_to_csv(test_xml, today) == expected_file


def test_put_csv(mocked_s3) -> None:
    with open("tests/fixtures/test.csv", encoding="utf-8") as file:
        csv_file = file.read()
    bursar_transfer.put_csv(
        mocked_s3,
        bucket="test-pickup-bucket",
        key="exlibris/bursar/foo.csv",
        csv_file=csv_file,
    )

    retrieved_file = mocked_s3.get_object(
        Bucket="test-pickup-bucket", Key="exlibris/bursar/foo.csv"
    )
    assert (
        retrieved_file["ResponseMetadata"]["HTTPHeaders"]["content-type"] == "text/csv"
    )
    assert retrieved_file["Body"].read().decode("utf-8") == csv_file


def test_lambda_handler_missing_workspace_env_raises_error(monkeypatch) -> None:
    monkeypatch.delenv("WORKSPACE", raising=False)
    with pytest.raises(RuntimeError) as error:
        bursar_transfer.lambda_handler({}, {})
    assert "Required env variable WORKSPACE is not set" in str(error)


def test_lambda_handler_success(event_data, caplog) -> None:
    csv_location = "test-pickup-bucket/exlibris/bursar/test.csv"
    response = bursar_transfer.lambda_handler(event_data, {})
    assert f"bursar csv available for download at {csv_location}" in caplog.text
    assert response == {"target_file": csv_location}
