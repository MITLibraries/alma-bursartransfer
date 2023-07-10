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
- `ALMA_BURSAR_PICKUP_BUCKET_ID` = An s3 bucket where the transformed file will be deposited. 

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

## Running a different handler in the container

If this repo contains multiple lambda functions, you can call any handler you copy into the container (see Dockerfile) by name as part of the `docker run` command:

```bash
docker run -p 9000:8080 bursar_transfer:latest lambdas.<a-different-module>.lambda_handler
```
