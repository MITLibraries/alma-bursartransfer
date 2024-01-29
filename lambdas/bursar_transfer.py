import csv
import json
import logging
import os
from datetime import date
from io import StringIO
from math import fsum
from xml.etree import ElementTree  # nosec

import boto3
import sentry_sdk
from mypy_boto3_s3 import S3Client
from sentry_sdk.integrations.aws_lambda import AwsLambdaIntegration

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(os.getenv("LOG_LEVEL", "INFO"))
TODAY = date.today()

env = os.getenv("WORKSPACE")
if sentry_dsn := os.getenv("SENTRY_DSN"):
    sentry = sentry_sdk.init(
        dsn=sentry_dsn,
        environment=env,
        integrations=[
            AwsLambdaIntegration(),
        ],
        traces_sample_rate=1.0,
    )
    logger.info("Sentry DSN found, exceptions will be sent to Sentry with env=%s", env)
else:
    logger.info("No Sentry DSN found, exceptions will not be sent to Sentry")


def get_key_from_job_id(
    s3_client: S3Client, bucket: str, prefix_with_job_id: str
) -> str:
    """Use the Alma bursar transfer job ID to return the corresponding filename in s3.

    :param s3_client - a boto S3Client instance
    :param bucket - the source bucket where the export file from Alma lands.
    :param prefix_with_job_id - the beginning / predictable part of the filename.

    When fines and fees are exported from Alma, the filename takes the form
    [bursar transfer integration profile name]-[alma job id]-[time stamp].xml

    We don't have a way to know the time stamp based on the data available to this app.

    Given a bucket and prefix, find all of the object keys beginning with that prefix.
    Because the job ID in the prefix is unique, there should only be one matching file.
    If not, raise a KeyError.
    """
    logger.debug(
        "Getting bursar file from bucket: %s, with prefix: %s",
        bucket,
        prefix_with_job_id,
    )
    keys = s3_client.list_objects_v2(Bucket=bucket, Prefix=prefix_with_job_id)
    try:
        source_key = keys["Contents"][0]["Key"]
    except KeyError as error:
        raise KeyError(
            f"No files retrieved from bucket '{bucket}'"
            f"with prefix '{prefix_with_job_id}'"
        ) from error

    if len(keys["Contents"]) > 1:
        raise KeyError(
            f"multiple files retrieved from bucket '{bucket}'"
            f"with prefix '{prefix_with_job_id}'"
        )

    return source_key


def get_bursar_export_xml_from_s3(s3_client: S3Client, bucket: str, key: str) -> str:
    """Get an object bytes data from s3 and return as a utf-8 encoded string."""
    response = s3_client.get_object(Bucket=bucket, Key=key)
    return response["Body"].read().decode("utf-8")


def billing_term(today: date) -> str:
    """Calculate the appropriate billing term code based on the current date.

    See https://mitlibraries.atlassian.net/browse/ENSY-182 for details on bursar's
    specifications and library business rules.
    """
    year = int(today.strftime("%Y"))
    month = today.month
    if month in [1, 2]:
        term_code = "FA"
        term_year = year
    elif month in [3, 4, 5, 6]:
        term_code = "SP"
        term_year = year
    elif month in [7, 8]:
        term_code = "SU"
        term_year = year
    else:
        term_code = "FA"
        term_year = year + 1
    return f"{term_year}{term_code}"


def generate_description(fine_fee_type: str, barcode: str) -> str:
    """Generate the value for the output .csv DESCRIPTION field.

    The DESCRIPTION field has a limit of 30 characters, so we truncate
    to that.

    Raises an error if the fine_fee_type does not have a mapping.

    Only the fine / fee types we specify in alma should appear
    in the export file, so if an error occurs here it may mean
    that an unexpected change has been made in the Alma bursar
    integration config.
    """
    if fine_fee_type == "DAMAGEDITEMFINE":
        mapped_type = "Library damaged"
    elif fine_fee_type == "LOSTITEMPROCESSFEE":
        mapped_type = "Library lost"
    elif fine_fee_type == "LOSTITEMREPLACEMENTFEE":
        mapped_type = "Library repl"
    elif fine_fee_type == "OVERDUEFINE":
        mapped_type = "Library overdue"
    elif fine_fee_type == "OTHER":
        mapped_type = "Library other"
    elif fine_fee_type == "RECALLEDOVERDUEFINE":
        mapped_type = "Library recalled"

    else:
        raise ValueError(f"Unrecoginzed fine fee type: {fine_fee_type}")

    return f"{mapped_type} {barcode}"[:30]


def xml_to_csv(alma_xml: str, today: date) -> StringIO:
    """Convert xml from the alma bursar export to a csv.

    See https://mitlibraries.atlassian.net/browse/ENSY-182 for details on bursar's
    specifications and library business rules.
    """
    csv_file = StringIO()
    csv_fieldnames = [
        "MITID",
        "STUDENTNAME",
        "DETAILCODE",
        "DESCRIPTION",
        "AMOUNT",
        "EFFECTIVEDATE",
        "BILLINGTERM",
    ]
    writer = csv.DictWriter(
        csv_file,
        csv_fieldnames,
        delimiter=",",
        lineterminator="\n",
        quoting=csv.QUOTE_ALL,
    )
    writer.writeheader()

    root = ElementTree.fromstring(alma_xml)  # nosec

    name_space = {"xb": "http://com/exlibris/urm/rep/externalsysfinesfees/xmlbeans"}
    for user in root.iterfind(".//xb:userExportedFineFeesList", name_space):
        csv_line = {}
        csv_line["MITID"] = user.findtext(
            "xb:user/xb:value", default=None, namespaces=name_space
        )
        csv_line["STUDENTNAME"] = user.findtext(
            "xb:patronName", default=None, namespaces=name_space
        )
        for fine_fee in user.iterfind("xb:finefeeList/xb:userFineFee", name_space):
            csv_line["DETAILCODE"] = "ROLH"
            barcode = fine_fee.findtext(
                "xb:itemBarcode", default="", namespaces=name_space
            )
            fine_fee_type = fine_fee.findtext(
                "xb:fineFeeType", default="", namespaces=name_space
            )
            try:
                csv_line["DESCRIPTION"] = generate_description(fine_fee_type, barcode)
            except ValueError as error:
                transaction_id = fine_fee.findtext(
                    "xb:bursarTransactionId", default="", namespaces=name_space
                )
                logger.error("Skipping transaction %s. %s", transaction_id, error)
                continue

            csv_line["AMOUNT"] = fine_fee.findtext(
                "xb:compositeSum/xb:sum", default=None, namespaces=name_space
            )
            csv_line["EFFECTIVEDATE"] = today.strftime("%m/%d/%Y")
            csv_line["BILLINGTERM"] = billing_term(today)
            if all(csv_line.values()):
                writer.writerow(csv_line)
            else:
                raise ValueError(
                    "One or more required values are missing from the export file"
                )

    return csv_file


def put_csv(s3_client: S3Client, bucket: str, key: str, csv_file: str) -> None:
    s3_client.put_object(
        Bucket=bucket, Key=key, Body=csv_file.encode("utf-8"), ContentType="text/csv"
    )


def get_records_and_total_charges(bursar_csv: StringIO) -> tuple[int, float]:
    """Return the number of records and sum of charges in the bursar export file.

    Takes a `StringIO` containing the transformed bursar csv and returns the sum of
    the charges from the Amount column and the number of records in the file excluding
    the header row.
    """
    bursar_csv.seek(0)
    record_count = 0
    total_charges = float()

    for row in csv.DictReader(bursar_csv):
        record_count += 1
        total_charges = round(fsum([total_charges, float(row["AMOUNT"])]), 2)
    return record_count, total_charges


def lambda_handler(event: dict, context: object) -> dict:  # noqa
    logger.debug("Lambda handler starting with event: %s", json.dumps(event))
    if not os.getenv("WORKSPACE"):
        raise RuntimeError("Required env variable WORKSPACE is not set")

    # Create boto3 client
    s3_client = boto3.client("s3")

    source_key = get_key_from_job_id(
        s3_client,
        bucket=os.environ["SOURCE_BUCKET"],
        prefix_with_job_id=(f"{os.environ['SOURCE_PREFIX']}-{event['job_id']}"),
    )

    target_key = source_key.replace(
        os.environ["SOURCE_PREFIX"], os.environ["TARGET_PREFIX"]
    ).replace(".xml", ".csv")

    # Get the XML from s3
    alma_xml = get_bursar_export_xml_from_s3(
        s3_client, os.environ["SOURCE_BUCKET"], source_key
    )

    # Convert the xml to csv
    bursar_csv = xml_to_csv(alma_xml, TODAY)

    # upload csv
    put_csv(
        s3_client,
        os.environ["TARGET_BUCKET"],
        target_key,
        bursar_csv.getvalue(),
    )
    csv_location = f"{os.environ['TARGET_BUCKET']}/{target_key}"
    record_count, total_charges = get_records_and_total_charges(bursar_csv)
    logger.info("Bursar csv available for download at %s", csv_location)
    return {
        "target_file": csv_location,
        "record_count": record_count,
        "total_charges": total_charges,
    }
