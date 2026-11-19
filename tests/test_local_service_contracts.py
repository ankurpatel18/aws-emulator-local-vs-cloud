from contextlib import closing
from uuid import uuid4


def test_s3_object_round_trip(emulator_client):
    s3 = emulator_client("s3")
    bucket = f"emulator-lab-{uuid4().hex}"
    region = s3.meta.region_name
    bucket_options = {}
    if region != "us-east-1":
        bucket_options["CreateBucketConfiguration"] = {"LocationConstraint": region}
    s3.create_bucket(Bucket=bucket, **bucket_options)

    key = "sample-order.txt"
    payload = b"order-123: RECEIVED"
    try:
        s3.put_object(Bucket=bucket, Key=key, Body=payload)
        response = s3.get_object(Bucket=bucket, Key=key)
        with closing(response["Body"]) as body:
            assert body.read() == payload
    finally:
        try:
            s3.delete_object(Bucket=bucket, Key=key)
        finally:
            s3.delete_bucket(Bucket=bucket)


def test_sqs_message_round_trip(emulator_client):
    sqs = emulator_client("sqs")
    queue = sqs.create_queue(QueueName=f"emulator-lab-{uuid4().hex}")["QueueUrl"]
    payload = "order-123: RECEIVED"
    try:
        sent = sqs.send_message(QueueUrl=queue, MessageBody=payload)
        for _ in range(3):
            received = sqs.receive_message(
                QueueUrl=queue, MaxNumberOfMessages=1, WaitTimeSeconds=3
            )
            messages = received.get("Messages", [])
            if messages:
                break
        else:
            raise AssertionError("SQS returned no message after three receive calls.")

        message = messages[0]
        assert message["MessageId"] == sent["MessageId"]
        assert message["Body"] == payload
        sqs.delete_message(QueueUrl=queue, ReceiptHandle=message["ReceiptHandle"])
    finally:
        sqs.delete_queue(QueueUrl=queue)


def test_sns_publish_returns_message_id(emulator_client):
    sns = emulator_client("sns")
    topic = sns.create_topic(Name=f"emulator-lab-{uuid4().hex}")["TopicArn"]
    try:
        published = sns.publish(TopicArn=topic, Message="order-123: RECEIVED")
        assert published.get("MessageId"), "SNS returned no publish message ID."
    finally:
        sns.delete_topic(TopicArn=topic)
