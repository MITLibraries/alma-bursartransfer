# bursar_transfer

Transforms fine and fee data exported from Alma to the correct format to be uploaded to the
bursar's system.

## Development

- To install with dev dependencies: `make install`
- To update dependencies: `make update`
- To run unit tests: `make test`
- To lint the repo: `make lint`

## Required ENV

- `SENTRY_DSN` = If set to a valid Sentry DSN, enables Sentry exception monitoring. This is not needed for local development.
- `WORKSPACE` = Set to `dev` for local development, this will be set to `stage` and `prod` in those environments by Terraform.
- `ALMA_BUCKET` = The bucket containing the fine and fee data exported from Alma.
- `TARGET_BUCKET` = The bucket where the transformed file will be deposited. 

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
