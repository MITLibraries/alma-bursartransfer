# Alma Bursar Transfer

Transforms fine and fee data exported from Alma to the correct format to be
uploaded to the bursar's system.

## Development

- To install with dev dependencies: `make install`
- To update dependencies: `make update`
- To run unit tests: `make test`
- To lint the repo: `make lint`

## Required ENV

```text
WORKSPACE=# Set to `dev` for local development, this will be set to `stage` and `prod` in those environments by Terraform.
SOURCE_BUCKET=# The bucket containing the fine and fee data exported from Alma.
SOURCE_PREFIX=# The prefix of the source object key within the source bucket, up to, but not including the hyphen before the job id. This will look something like `[s3 source folder]/[s3 source subfolder]/[bursar integration profile code from alma]`. The bursar integration's _profile code_ in Alma is used as the start of the filename that Alma exports.
TARGET_BUCKET=# The bucket where the transformed object will be deposited.
TARGET_PREFIX=# Prefix of the target object key within target bucket. This will look something like `[s3 target folder]/[s3 target subfolder]/[beginning of target filename]`
```

## Optional ENV

```text
SENTRY_DSN=# If set to a valid Sentry DSN, enables Sentry exception monitoring. This is not needed for local development.
LOG_LEVEL=# Set to a valid Python logging level (e.g. DEBUG, case-insensitive) if desired. Can also be passed as an option directly to the ccslips command. Defaults to INFO if not set or passed to the command.
```


## Mapping from Alma to SFS

| Alma                                | SFS csv Field              | example                     |
| ----------------------------------- | -------------------------- | --------------------------- |
| user ID type 02                     | MITID                      | 12345678                    |
| Last name, First Name               | STUDENTNAME                | Doe, Jane                   |
| (use CHASS detail code ROLH)        | DETAILCODE                 | ROLH                        |
| (see calculating DESCRIPTION below) | DESCRIPTION                | Library lost 99999999999999 |
| Amount owed for the fine or fee     | AMOUNT                     | 123.45                      |
| Date the export is run (i.e. today) | EFFECTIVEDATE <mm/dd/yyyy> | 12/31/2023                  |
| (see calculating BILLINGTERM below) | BILLINGTERM \<YYYYXX\>     | 2023FA                      |

### Calculating DESCRIPTION values

| fine fee type          | DESCRIPTION (right truncated to 30 char.) |
| ---------------------- | ----------------------------------------- |
| DAMAGEDITEMFINE        | Library damaged [barcode]                 |
| LOSTITEMPROCESSFEE     | Library lost [barcode]                    |
| LOSTITEMREPLACEMENTFEE | Library repl [barcode]                    |
| OTHER                  | Library other [barcode]                   |
| OVERDUEFINE            | Library overdue [barcode]                 |
| RECALLEDOVERDUEFINE    | Library recalled [barcode]                |

### Calculating BILLINGTERM values

`BILLINGTERM` values have two parts, a 4 digit year \<YYYY> followed by a 2 digit
term code. One of:

- `SP` = Spring
- `SU` = Summer
- `FA` = Fall

`BILLINGTERM` is calculated based on the current month and year when the Alma
bursar export is run. At MIT, the year used in the Fall `BILLINGTERM` should be the upcoming year, not the current year. For example, for exports run in calendar year `2023`:

| current month (number) is | year    | term code | BILLINGTERM |
| ------------------------- | ------- | --------- | ----------- |
| 1, 2, 3, 4                | 2023    | SP        | 2023SP      |
| 5, 6, 7                    | 2023    | SU        | 2023SU      |
| 8, 9, 10, 11 or 12     | 2023 +1 | FA        | 2024FA      |

## Local Testing

Local testing runs the Lambda via [SAM](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli.html)
using the real Dockerfile, without touching real AWS resources.

- Build the SAM image:

  ```bash
  make sam-build
  ```

- Invoke the lambda:

  ```bash
  make sam-invoke
  ```

  This starts a local [moto](https://github.com/getmoto/moto) mock S3 server,
  seeds it with `tests/fixtures/test.xml` (see `tests/sam/seed_mock_s3.py`),
  invokes the function against that mock via `tests/sam/env.mock.json`, and
  tears the mock server down afterward. No AWS credentials are required and
  no real bucket is touched.

- Observe output:

  ```
  {"target_file": "test-pickup-bucket/test/target-prefix/bursar_file_ready_to_pickup-12345678-5678.csv",
  "record_count": 10,
  "total_charges": 579.72
  }
  ```

### Testing against a real dev environment

Occasionally (e.g. to verify the deployed dev Lambda's actual IAM/bucket
permissions) you may want to invoke against real AWS resources instead of the
mock. This requires active AWS CLI credentials (e.g. via SSO login) for the
account/role that has access to the buckets you're testing against.

- Populate `tests/sam/env.json` (gitignored, safe to edit locally) with real
  values from the deployed dev Lambda's configuration:

  ```bash
  make sam-env
  ```

- Upload a sample bursar export .xml file to the real `SOURCE_BUCKET` set in
  `tests/sam/env.json`. Rename the file and move to a different subfolder if
  necessary so that the object key looks like `[SOURCE_PREFIX]-[job_id]-[timestamp].xml`
  - For example the object key could be `test/bursar/export-1234-5678.xml`
  - Note that the timestamp can be any string, it doesn't have to be a 'real'
    timestamp
  - You can use the fixture file in this repo `tests/fixtures/test.xml` as your
    sample file.

- Invoke the lambda, passing in the `job_id` from the object key you created
  (update the `job_id` in the `Makefile`'s `sam-invoke-live` target if it
  differs from `12345678`):

  ```bash
  make sam-invoke-live
  ```

- Observe output:

  ```
  {"target_file": "[TARGET_BUCKET]/[TARGET_PREFIX]-1234-5678.csv",
  "records": [count of records in the file],
  "total_charges: [sum of charges in the file]
  }
  ```
