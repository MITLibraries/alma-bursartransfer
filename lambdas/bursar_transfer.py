import csv
import logging
import os
from datetime import date
from io import StringIO
from xml.etree import ElementTree  # nosec

import boto3
import sentry_sdk
from mypy_boto3_s3 import S3Client
from sentry_sdk.integrations.aws_lambda import AwsLambdaIntegration

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

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


def get_bursar_export_xml_from_s3(s3_client: S3Client, bucket: str, key: str) -> str:
    """Get an object bytes data from s3 and return as a utf-8 encoded string."""
    response = s3_client.get_object(Bucket=bucket, Key=key)
    return response["Body"].read().decode("utf-8")


def billing_term(today: date) -> str:
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


def xml_to_csv(alma_xml: str, today: date) -> str:
    """Convert xml from the alma bursar export to a csv.

    see jira XXXXX for details on bursar's specifications and library business rules.
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
            csv_line["DETAILCODE"] = "ROLH"  # Not sure how to calculate
            csv_line["DESCRIPTION"] = fine_fee.findtext(
                "xb:fineFeeType", default=None, namespaces=name_space
            )
            csv_line["AMOUNT"] = fine_fee.findtext(
                "xb:compositeSum/xb:sum", default=None, namespaces=name_space
            )
            csv_line["EFFECTIVEDATE"] = "effective_date"  # Not sure how to calculate
            csv_line["BILLINGTERM"] = billing_term(today)
            if all(csv_line.values()):
                print(csv_line)
                writer.writerow(csv_line)
            else:
                raise ValueError

    return csv_file.getvalue()


def put_csv(s3_client: S3Client, bucket: str, key: str, csv_file: str) -> None:
    s3_client.put_object(
        Bucket=bucket, Key=key, Body=csv_file.encode("utf-8"), ContentType="text/csv"
    )


def lambda_handler(event: dict, context: object) -> None:  # noqa
    if not os.getenv("WORKSPACE"):
        raise RuntimeError("Required env variable WORKSPACE is not set")

    # Create boto3 client
    s3_client = boto3.client("s3")

    # Get the object from the event and show its content type
    bucket = event["Records"][0]["s3"]["bucket"]["name"]
    key = event["Records"][0]["s3"]["object"]["key"]

    # Get the XML from s3
    alma_xml = get_bursar_export_xml_from_s3(s3_client, bucket, key)

    # Convert the xml to csv
    bursar_csv = xml_to_csv(alma_xml, TODAY)

    # upload csv
    put_csv(
        s3_client,
        os.environ["ALMA_BURSAR_PICKUP_BUCKET_ID"],
        key.replace(".xml", ".csv"),
        bursar_csv,
    )
    csv_location = (
        f"{os.environ['ALMA_BURSAR_PICKUP_BUCKET_ID']}/{key.replace('.xml', '.csv')}"
    )
    logger.info("bursar csv available for download at %s", csv_location)
