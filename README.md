# AWS Emulator contract lab

Run contract tests for DynamoDB, S3, SQS, and SNS against AWS Emulator on your Mac. The lab uses temporary resources and synthetic order data.

Open [the local HTML companion](aws-emulator-local-only.html) in your browser for copyable commands and evidence recording. 

The steps below follow the HTML lab. Emulator endpoint: `https://127.0.0.1:9297`.

## 1. Prepare the lab

Start Docker Desktop. Install Python 3 and the AWS CLI if they are missing. Open two Terminal windows in the repository root, the folder that contains `Dockerfile.aws-emulator` and `scripts/test-emulator.sh`.

```bash
docker version
python3 --version
aws --version
```

## 2. Build and start the emulator

Terminal 1. Run from the repository root and leave this window running during the tests. The build selects the emulator package for Apple silicon or Intel. If the emulator is already running on port 9297, continue to step 3.

```bash
(
  set -eu
  case "$(uname -m)" in
    arm64|aarch64)
      docker build --platform linux/arm64 --build-arg EMULATOR_RPM_ARCH=aarch64 \
        -f Dockerfile.aws-emulator -t aws-emulator .
      ;;
    x86_64)
      docker build --platform linux/amd64 -f Dockerfile.aws-emulator -t aws-emulator .
      ;;
    *)
      printf '%s\n' 'Unsupported CPU architecture.' >&2
      exit 1
      ;;
  esac
  mkdir -p "$HOME/.aws/emulator"
  docker run --rm -p 127.0.0.1:9297:9297 \
    -e HOME="$HOME" \
    -v "$HOME/.aws/emulator:$HOME/.aws/emulator" \
    aws-emulator -p 9297
)
```

The port mapping binds to loopback on your Mac. The bind mount lets boto3 read the generated credentials and certificate.

[AWS Emulator Docker setup](https://docs.aws.amazon.com/emulator/latest/userguide/getting-started-docker.html)

## 3. Prepare Python and verify the connection

Terminal 2. Run from the repository root. Set up the virtual environment once. If `.venv` already exists with the dependencies installed, run only `source .venv/bin/activate`.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Verify the emulator identity before testing:

```bash
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
)
```

Expected output is `Emulator account: 000000000000`.

## 4. Run the tests

Terminal 2, with the virtual environment active. Run the four-service pytest suite:

```bash
bash scripts/test-emulator.sh -v
```

The runner loads the emulator configuration in its own Bash process and repeats the preflight checks: HTTPS loopback endpoint, generated credentials and CA files, and STS account `000000000000`. It uses the emulator CA for TLS.

| Service | Assertions |
| --- | --- |
| DynamoDB | An order round-trips, a duplicate order raises the expected error, and an invalid table name returns `ValidationException`. An optional missing-order test checks that the repository returns `None`. |
| S3 | An uploaded object downloads with exactly the same bytes. |
| SQS | A received message matches the sent message ID and body. The test deletes it with its receipt handle. |
| SNS | Publishing to a topic returns a message ID. Subscriber delivery is outside this check. |

Run a single check with `-k`, for example `bash scripts/test-emulator.sh -v -k test_s3_object_round_trip`. The DynamoDB tests are in `tests/test_order_contract.py`, for example `test_create_then_read_order`, `test_duplicate_order_is_rejected`, and `test_invalid_table_name_returns_validation_exception`.

To save console output and the exit status for your lab notes:

```bash
if bash scripts/test-emulator.sh -vv > aws-emulator-pytest.log 2>&1; then
  echo "pytest exit status: 0"
else
  echo "pytest exit status: $?"
fi
tail -n 60 aws-emulator-pytest.log
```

### Troubleshooting

- **`NoCredentialsError`**: run the complete guarded block or `scripts/test-emulator.sh`. The endpoint and generated credentials loaded by `source` are scoped to that block, so a bare pytest command can lose both.
- **Connection refused or missing files**: check Terminal 1 for a startup error, and confirm the container and script both use port 9297.
- **Certificate error**: restart the emulator if needed and rerun step 3 so the command uses the generated CA for the current instance.
- **HTTP 501 / `NotImplemented`**: record the operation and output as blocked. Local coverage varies by feature and release. See the [AWS Emulator fidelity guide](https://docs.aws.amazon.com/emulator/latest/userguide/check-project.html).

[Configure boto3 for AWS Emulator](https://docs.aws.amazon.com/emulator/latest/userguide/point-sdk-to-emulator.html)

## 5. Record evidence

Save one entry per check in the HTML companion (results stay in your browser) and export the JSON when done. For each check, record the result (met, did not meet, or blocked), the run time, the run reference or emulator version, and the sanitized terminal output. Keep credentials and customer data out of the log.

## 6. Stop the emulator

Press **Ctrl+C** in Terminal 1 after saving your evidence. The tests attempt to delete their temporary tables, bucket and object, queue, and topic. Stopping the emulator clears its in-memory state, including resources left by an interrupted check.

Use these results for local API and application behavior. IAM authorization, service quotas, and production behavior need separate validation. See [AWS Emulator security considerations](https://docs.aws.amazon.com/emulator/latest/userguide/security.html).

## Optional isolated AWS validation

Run only the DynamoDB contract tests against a dedicated AWS test account or tightly scoped test role. In a fresh shell with its credentials configured, verify that the returned account is your intended test account before running pytest.

```bash
(
  set -e
  source scripts/use-aws.sh
  expected_account="123456789012" # Replace with your isolated test account ID.
  account="$(aws sts get-caller-identity --query Account --output text)"
  test "$account" = "$expected_account" || { echo "Unexpected AWS account"; exit 1; }
  .venv/bin/python -m pytest -v tests/test_order_contract.py
)
```

Managed AWS use may incur charges. Keep IAM authorization, resource policies, and managed-service behavior in your isolated AWS validation stage.
