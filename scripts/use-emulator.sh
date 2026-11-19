#!/usr/bin/env bash

# This file is sourced. Preserve the calling shell's error-handling options.

PORT="${1:-9297}"
ROOT="${HOME}/.aws/emulator/${PORT}"

export AWS_ENDPOINT_URL="https://127.0.0.1:${PORT}"
export AWS_SHARED_CREDENTIALS_FILE="${ROOT}/emulator_credentials"
export AWS_CONFIG_FILE="${ROOT}/config"
export AWS_CA_BUNDLE="${ROOT}/ca.pem"
export AWS_EC2_METADATA_DISABLED=true
export AWS_DISABLE_HOST_PREFIX_INJECTION=true
export AWS_REGION=us-west-2
export AWS_DEFAULT_REGION=us-west-2

unset AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_SESSION_TOKEN AWS_SECURITY_TOKEN
unset AWS_PROFILE AWS_DEFAULT_PROFILE AWS_ROLE_ARN AWS_WEB_IDENTITY_TOKEN_FILE
unset AWS_CONTAINER_CREDENTIALS_RELATIVE_URI AWS_CONTAINER_CREDENTIALS_FULL_URI
unset AWS_IGNORE_CONFIGURED_ENDPOINT_URLS AWS_ENDPOINT_URL_STS
unset AWS_ENDPOINT_URL_DYNAMODB AWS_ENDPOINT_URL_S3 AWS_ENDPOINT_URL_SQS AWS_ENDPOINT_URL_SNS

printf '%s\n' "AWS Emulator environment configured for port ${PORT}."
printf '%s\n' "Run: aws sts get-caller-identity"
printf '%s\n' "Then: python -m pytest -q"
