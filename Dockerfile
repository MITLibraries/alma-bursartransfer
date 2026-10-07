FROM public.ecr.aws/lambda/python:3.13

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

COPY pyproject.toml uv.lock* ./

RUN cd ${LAMBDA_TASK_ROOT} && \
    uv export --format requirements-txt --no-hashes --no-dev > requirements.txt && \
    uv pip install -r requirements.txt --target "${LAMBDA_TASK_ROOT}" --system

COPY . ${LAMBDA_TASK_ROOT}/

# Default handler. See README for how to override to a different handler.
CMD [ "lambdas.bursar_transfer.lambda_handler" ]