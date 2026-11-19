#!/usr/bin/env bash

(
  set -eu
  unset AWS_SESSION_TOKEN AWS_SECURITY_TOKEN AWS_DEFAULT_PROFILE \
    AWS_ENDPOINT_URL_STS AWS_ENDPOINT_URL_DYNAMODB AWS_IGNORE_CONFIGURED_ENDPOINT_URLS
  source scripts/use-emulator.sh 9297
  if [ "$AWS_ENDPOINT_URL" != "https://127.0.0.1:9297" ]; then
    printf '%s\n' 'Unexpected endpoint. Stopping.' >&2
    exit 1
  fi
  account="$(aws sts get-caller-identity --endpoint-url "$AWS_ENDPOINT_URL" --query Account --output text)"
  if [ "$account" != "000000000000" ]; then
    printf '%s\n' 'Unexpected STS account. Stopping.' >&2
    exit 1
  fi
  printf "Emulator account: %s\n" "$account"
  python - <<'PY'

from contextlib import closing
import os
from urllib.parse import urlsplit
from uuid import uuid4

import boto3
from botocore.config import Config

endpoint = os.environ["AWS_ENDPOINT_URL"]
if endpoint != "https://127.0.0.1:9297":
    raise SystemExit("Unexpected endpoint. Stopping.")
region = os.environ["AWS_REGION"]
name = "emulator-lab-" + uuid4().hex[:12]

def require_local_request(request, **kwargs):
    target = urlsplit(request.url)
    if (target.scheme, target.hostname, target.port) != ("https", "127.0.0.1", 9297):
        raise RuntimeError("SDK attempted to use an endpoint outside the emulator.")

def local_client(service):
    options = {"s3": {"addressing_style": "path"}} if service == "s3" else {}
    client = boto3.client(
        service,
        endpoint_url=endpoint,
        region_name=region,
        verify=os.environ["AWS_CA_BUNDLE"],
        config=Config(
            inject_host_prefix=False,
            connect_timeout=5,
            read_timeout=15,
            retries={"total_max_attempts": 1},
            proxies={},
            **options,
        ),
    )
    client.meta.events.register("before-send.*.*", require_local_request)
    return client

s3 = local_client("s3")
bucket_args = {"Bucket": name}
if region != "us-east-1":
    bucket_args["CreateBucketConfiguration"] = {"LocationConstraint": region}
s3.create_bucket(**bucket_args)
key = "sample-order.txt"
payload = b"order-123: RECEIVED"
try:
    s3.put_object(Bucket=name, Key=key, Body=payload)
    try:
        with closing(s3.get_object(Bucket=name, Key=key)["Body"]) as body:
            if body.read() != payload:
                raise RuntimeError("S3 returned different object bytes.")
    finally:
        s3.delete_object(Bucket=name, Key=key)
finally:
    s3.delete_bucket(Bucket=name)
print("PASS S3: object bytes match and the temporary bucket was deleted.")

PY
)
