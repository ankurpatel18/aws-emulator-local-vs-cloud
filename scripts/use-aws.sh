#!/usr/bin/env bash
set -euo pipefail

unset AWS_ENDPOINT_URL || true
unset AWS_SHARED_CREDENTIALS_FILE || true
unset AWS_CONFIG_FILE || true
unset AWS_CA_BUNDLE || true
unset AWS_DISABLE_HOST_PREFIX_INJECTION || true
unset AWS_EC2_METADATA_DISABLED || true

export AWS_REGION="${AWS_REGION:-us-west-2}"
export AWS_DEFAULT_REGION="$AWS_REGION"

printf '%s\n' "Real AWS target selected in region ${AWS_REGION}."
printf '%s\n' "Use only an isolated test account or tightly scoped test role."
printf '%s\n' "Verify identity: aws sts get-caller-identity"
printf '%s\n' "Then: pytest -q"
