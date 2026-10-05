"""Seed a local moto_server with the bucket/object `make sam-invoke` expects.

Run against a moto_server instance (not real AWS) started by the
`sam-invoke` Makefile target. See tests/sam/env.mock.json for the matching
bucket/prefix values passed to the Lambda container.
"""

import os

import boto3

ENDPOINT_URL = os.environ.get("AWS_ENDPOINT_URL", "http://127.0.0.1:5099")
SOURCE_BUCKET = "test-alma-bucket"
SOURCE_PREFIX = "test/source-prefix/bursar_export_to_test"
TARGET_BUCKET = "test-pickup-bucket"
JOB_ID = "12345678"


def main() -> None:
    client = boto3.client(
        "s3",
        endpoint_url=ENDPOINT_URL,
        region_name="us-east-1",
        aws_access_key_id="testing",
        aws_secret_access_key="testing",  # noqa: S106 -- mock creds, not a real secret
    )
    for bucket in (SOURCE_BUCKET, TARGET_BUCKET):
        client.create_bucket(Bucket=bucket)

    key = f"{SOURCE_PREFIX}-{JOB_ID}-5678.xml"
    with open("tests/fixtures/test.xml", "rb") as file:
        client.put_object(Bucket=SOURCE_BUCKET, Key=key, Body=file)

    print(f"Seeded mock S3 at {ENDPOINT_URL}: {SOURCE_BUCKET}/{key}")  # noqa: T201 -- CLI script output


if __name__ == "__main__":
    main()
