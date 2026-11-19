from __future__ import annotations

import os
import uuid
from contextlib import ExitStack
from pathlib import Path
from urllib.parse import urlsplit

import boto3
import pytest
from botocore.config import Config


@pytest.fixture(scope="session")
def emulator_client():
    endpoint = os.getenv("AWS_ENDPOINT_URL")
    if not endpoint:
        pytest.skip("These checks require the local emulator. Use bash scripts/test-emulator.sh.")

    target = urlsplit(endpoint)
    if (
        target.hostname != "127.0.0.1"
        or not target.port
        or endpoint != f"https://127.0.0.1:{target.port}"
    ):
        pytest.fail("Set AWS_ENDPOINT_URL to the emulator's HTTPS loopback endpoint.", pytrace=False)

    for variable in ("AWS_SHARED_CREDENTIALS_FILE", "AWS_CONFIG_FILE", "AWS_CA_BUNDLE"):
        if not Path(os.environ.get(variable, "")).is_file():
            pytest.fail(f"{variable} is missing. Start AWS Emulator first.", pytrace=False)

    def require_local_request(request, **kwargs):
        if not request.url.startswith(f"{endpoint}/"):
            raise RuntimeError(f"Blocked request outside the emulator endpoint at {endpoint}.")

    with ExitStack() as clients:
        def create_client(service):
            service_config = {"s3": {"addressing_style": "path"}} if service == "s3" else {}
            client = boto3.client(
                service,
                endpoint_url=endpoint,
                region_name=os.getenv("AWS_REGION", "us-west-2"),
                verify=os.environ["AWS_CA_BUNDLE"],
                config=Config(
                    inject_host_prefix=False,
                    connect_timeout=5,
                    read_timeout=15,
                    retries={"total_max_attempts": 1},
                    proxies={},
                    **service_config,
                ),
            )
            clients.callback(client.close)
            client.meta.events.register("before-send.*.*", require_local_request)
            return client

        if create_client("sts").get_caller_identity()["Account"] != "000000000000":
            pytest.fail("STS returned an unexpected account for the local emulator.", pytrace=False)
        yield create_client


@pytest.fixture(scope="session")
def ddb(request):
    if os.getenv("AWS_ENDPOINT_URL"):
        return request.getfixturevalue("emulator_client")("dynamodb")
    return boto3.client("dynamodb", region_name=os.getenv("AWS_REGION", "us-west-2"))


@pytest.fixture()
def orders_table(ddb):
    table_name = f"orders-contract-{uuid.uuid4().hex[:10]}"
    ddb.create_table(
        TableName=table_name,
        AttributeDefinitions=[
            {"AttributeName": "order_id", "AttributeType": "S"},
        ],
        KeySchema=[
            {"AttributeName": "order_id", "KeyType": "HASH"},
        ],
        BillingMode="PAY_PER_REQUEST",
    )
    try:
        ddb.get_waiter("table_exists").wait(
            TableName=table_name,
            WaiterConfig={"Delay": 1, "MaxAttempts": 60},
        )
        yield table_name
    finally:
        ddb.delete_table(TableName=table_name)
