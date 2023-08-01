# Alma Bursar Transfer

Transforms fine and fee data exported from Alma to the correct format to be uploaded to the
bursar's system.

## Development

- To install with dev dependencies: `make install`
- To update dependencies: `make update`
- To run unit tests: `make test`
- To lint the repo: `make lint`

## Required ENV

- `ALMA_BURSAR_SOURCE_BUCKET` = The bucket containing the fine and fee data exported from Alma.
- `ALMA_BURSAR_SOURCE_PREFIX` = prefix of the source object key within the source bucket.
- `ALMA_BURSAR_TARGET_BUCKET` = The bucket where the transformed object will be deposited. 
- `ALMA_BURSAR_TARGET_PREFIX` = prefix of the target object key within target bucket.
- `WORKSPACE` = Set to `dev` for local development, this will be set to `stage` and `prod` in those environments by Terraform.

## Optional ENV

- `SENTRY_DSN` = If set to a valid Sentry DSN, enables Sentry exception monitoring. This is not needed for local development.
- `LOG_LEVEL` = Set to a valid Python logging level (e.g. DEBUG, case-insensitive) if desired. Can also be passed as an option directly to the ccslips command. Defaults to INFO if not set or passed to the command.

## Mapping from Alma to SFS

| Alma                             | SFS csv Field | example                            |
|----------------------------------|---------------|------------------------------------|
| user ID type 02                  | MITID         | 12345678                           |
| Last name, First Name            | STUDENTNAME   | Doe, Jane                          |
|                                  | DETAILCODE    |                                    |
| Fine Fee Type                    | DESCRIPTION   | LOSTITEMREPLACEMENTFEE             |
| Amount owed for the fine or fee  | AMOUNT        | 123.45                             |
|                                  | EFFECTIVEDATE |                                    |
| see calculating BILLINGTERM below| BILLINGTERM   |2023FA                              |

### calculating BILLINGTERM values

|current month (number) is  |BILLINGTERM  |
|-------------              |-------------|
|1 or 2                     | \<yyyy>FA   |
|3, 4, 5 or 6               | \<yyyy>SP   |
|7 or 8                     | \<yyyy>SU   |
|9, 10, 11 or 12            | \<yyyy+1>FA

## Running locally

<https://docs.aws.amazon.com/lambda/latest/dg/images-test.html>

- Build the container:

  ```bash
  docker build -t bursar_transfer:latest .
  ```

- Run the default handler for the container:

  ```bash
  docker run -e WORKSPACE=dev -p 9000:8080 bursar_transfer:latest
  ```

- Post to the container:

  ```bash
  curl -XPOST "http://localhost:9000/2015-03-31/functions/function/invocations" -d '{}'
  ```

- Observe output:

  ```
  "You have successfully called this lambda!"
  ```
