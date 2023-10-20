import json
import logging
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


def test_get_key_from_job_id_bucket_with_matching_file(mocked_s3, caplog):
    with caplog.at_level(logging.DEBUG, logger="lambdas.bursar_transfer"):
        key = bursar_transfer.get_key_from_job_id(
            mocked_s3,
            bucket="test-alma-bucket",
            prefix_with_job_id="test/source-prefix/bursar_export_to_test-1234",
        )
    assert (
        "Getting bursar file from bucket: test-alma-bucket, with prefix: test/"
        "source-prefix/bursar_export_to_test-1234" in caplog.text
    )
    assert key == "test/source-prefix/bursar_export_to_test-1234-5678.xml"


def test_get_key_from_job_id_bucket_with_no_file(mocked_s3):
    with pytest.raises(KeyError):
        bursar_transfer.get_key_from_job_id(
            mocked_s3, bucket="no-files", prefix_with_job_id="nope"
        )


def test_get_key_from_job_id_without_matching_file(mocked_s3):
    with pytest.raises(KeyError):
        bursar_transfer.get_key_from_job_id(
            mocked_s3, bucket="no-match", prefix_with_job_id="bad/prefix-1234"
        )


def test_get_key_from_job_id_with_multiple_matching_file(mocked_s3):
    with pytest.raises(KeyError):
        bursar_transfer.get_key_from_job_id(
            mocked_s3,
            bucket="multiple-matches",
            prefix_with_job_id="test/source-prefix/bursar_export_to_test-1234",
        )


def test_get_bursar_export_xml_from_s3(mocked_s3) -> None:
    with open("tests/fixtures/test.xml", encoding="utf-8") as file:
        xml_file = file.read()
    assert (
        bursar_transfer.get_bursar_export_xml_from_s3(
            mocked_s3,
            bucket="test-alma-bucket",
            key="test/source-prefix/bursar_export_to_test-1234-5678.xml",
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


@pytest.mark.parametrize(
    "test_type,expected",
    [("TEST Overdue", "Library overdue"), ("test lost", "Library lost")],
)
def test_translate_fine_fee_type_success(test_type, expected) -> None:
    assert bursar_transfer.translate_fine_fee_type(test_type) == expected


def test_translate_fine_fee_type_fail():
    with pytest.raises(ValueError) as error:
        bursar_transfer.translate_fine_fee_type("foo")
    assert "unrecoginzed fine fee type: foo" in str(error)


def test_xml_to_csv_error_if_missing_field(test_xml: str) -> None:
    xml_missing_amount = test_xml.replace("123.45", "")
    today = date(2023, 3, 1)
    with pytest.raises(ValueError) as error:
        bursar_transfer.xml_to_csv(xml_missing_amount, today)
    assert "One or more required values are missing from the export file" in str(error)


def test_xml_to_csv_skip_line_if_unknown_fine_fee_type(test_xml: str, caplog) -> None:
    with caplog.at_level(logging.DEBUG, logger="lambdas.bursar_transfer"):
        xml_missing_amount = test_xml.replace("OVERDUEFINE", "foo", 1)
        today = date(2023, 3, 1)
        my_skipped_csv = bursar_transfer.xml_to_csv(xml_missing_amount, today)
    assert (
        "Skipping transaction 15216075630006761, unrecoginzed fine fee type: foo"
        in caplog.text
    )
    # We should have skipped one line in the file and so there should be
    # one fewer lines in the output file
    my_csv = bursar_transfer.xml_to_csv(test_xml, today)
    my_csv.seek(0)
    my_skipped_csv.seek(0)
    assert len(my_skipped_csv.readlines()) == len(my_csv.readlines()) - 1


def test_xml_to_csv(test_xml: str) -> None:
    with open("tests/fixtures/test.csv", encoding="utf-8") as expected_file:
        today = date(2023, 3, 1)
        assert (
            bursar_transfer.xml_to_csv(test_xml, today).getvalue()
            == expected_file.read()
        )


def test_put_csv(mocked_s3) -> None:
    with open("tests/fixtures/test.csv", encoding="utf-8") as file:
        csv_file = file.read()
    bursar_transfer.put_csv(
        mocked_s3,
        bucket="test-pickup-bucket",
        key="test/target-prefix/foo.csv",
        csv_file=csv_file,
    )

    retrieved_file = mocked_s3.get_object(
        Bucket="test-pickup-bucket", Key="test/target-prefix/foo.csv"
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
    csv_location = (
        "test-pickup-bucket/test/target-prefix/"
        "bursar_file_ready_to_pickup-1234-5678.csv"
    )
    with caplog.at_level(logging.DEBUG, logger="lambdas.bursar_transfer"):
        response = bursar_transfer.lambda_handler(event_data, {})
    assert (
        f"Lambda handler starting with event: {json.dumps(event_data)}" in caplog.text
    )

    records = 6
    total_charges = 539.72
    response = bursar_transfer.lambda_handler(event_data, {})
    assert f"Bursar csv available for download at {csv_location}" in caplog.text
    assert response == {
        "target_file": csv_location,
        "record_count": records,
        "total_charges": total_charges,
    }
