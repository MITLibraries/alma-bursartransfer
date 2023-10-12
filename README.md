# Alma Bursar Transfer

Transforms fine and fee data exported from Alma to the correct format to be uploaded to the
bursar's system.

## Development

- To install with dev dependencies: `make install`
- To update dependencies: `make update`
- To run unit tests: `make test`
- To lint the repo: `make lint`

## Required ENV

- `SOURCE_BUCKET` = The bucket containing the fine and fee data exported from Alma.
- `SOURCE_PREFIX` = The prefix of the source object key within the source bucket, up to, but not including the hyphen before the job id. This will look something like `[s3 source folder]/[s3 source subfolder]/[bursar integration profile code from alma]`. The bursar integration's *profile code* in Alma is used as the start of the filename that Alma exports. 
- `TARGET_BUCKET` = The bucket where the transformed object will be deposited. 
- `TARGET_PREFIX` = Prefix of the target object key within target bucket. This will look something like `[s3 target folder]/[s3 target subfolder]/[beginning of target filename]`
- `WORKSPACE` = Set to `dev` for local development, this will be set to `stage` and `prod` in those environments by Terraform.

## Optional ENV

- `SENTRY_DSN` = If set to a valid Sentry DSN, enables Sentry exception monitoring. This is not needed for local development.
- `LOG_LEVEL` = Set to a valid Python logging level (e.g. DEBUG, case-insensitive) if desired. Can also be passed as an option directly to the ccslips command. Defaults to INFO if not set or passed to the command.

## Mapping from Alma to SFS

| Alma                             | SFS csv Field               | example                            |
|----------------------------------|-----------------------------|------------------------------------|
| user ID type 02                  | MITID                       | 12345678                           |
| Last name, First Name            | STUDENTNAME                 | Doe, Jane                          |
| (use CHASS detail code ROLH)     | DETAILCODE                  | ROLH                               |
| (see calculating DESCRIPTION below)| DESCRIPTION                 | Library lost 99999999999999        |
| Amount owed for the fine or fee  | AMOUNT                      | 123.45                             |
| Last Transaction Date            | EFFECTIVEDATE <mm/dd/yyyy>  | 12/31/2023                         |
| (see calculating BILLINGTERM below)| BILLINGTERM \<YYYYXX\>      | 2023FA                             |

### Calculating DESCRIPTION values
| fine fee type contains | DESCRIPTION |
|------------------------|-------------|
|lost | Library lost [barcode] |
|overdue | Library overdue [barcode] | 

### Calculating BILLINGTERM values

|current month (number) is  |BILLINGTERM  |
|-------------              |-------------|
|1 or 2                     | \<yyyy>FA   |
|3, 4, 5 or 6               | \<yyyy>SP   |
|7 or 8                     | \<yyyy>SU   |
|9, 10, 11 or 12            | \<yyyy+1>FA

## Local Testing

<https://docs.aws.amazon.com/lambda/latest/dg/images-test.html>

- Build the container:

  ```bash
  docker build -t bursar_transfer:latest .
  ```

- Run the default handler for the container
  - Required environment variables and AWS credentials must be in `.env`. 
  - Make sure the buckets in your `.env` actually exist


  ```bash
  docker run --env-file .env -p 9000:8080 bursar_transfer:latest
  ```

- Upload a sample bursar export .xml file to the `SOURCE_BUCKET` specified in your `.env`. Rename the file and move to a different subfolder if necessary so that the object key looks like `[SOURCE_PREFIX]-[job_id]-[timestamp].xml`
  - For example the object key could be `test/bursar/export-1234-5678.xml`
  - Note that the timestamp can be any string, it doesn't have to be a 'real' timestamp
  - You can use the fixture file in this repo `tests/fixtures/test.xml` as your sample file.


- Post to the container, passing in the `job_id` from the object key you created:

  ```bash
  curl -XPOST "http://localhost:9000/2015-03-31/functions/function/invocations" -d '{"job_id":"1234"}'
  ```

- Observe output:

  ```
  {"target_file": "[TARGET_BUCKET]/[TARGET_PREFIX]-1234-5678.csv",
  "records": [count of records in the file],
  "total_charges: [sum of charges in the file]
  }
  ```
