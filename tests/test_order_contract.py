from __future__ import annotations

import pytest
from botocore.exceptions import ClientError

from src.order_repository import DuplicateOrderError, Order, OrderRepository


def test_create_then_read_order(ddb, orders_table):
    repo = OrderRepository(ddb, orders_table)
    expected = Order(order_id="ord-1001", customer_id="cust-42")

    repo.create(expected)

    assert repo.get(expected.order_id) == expected


def test_duplicate_order_is_rejected(ddb, orders_table):
    repo = OrderRepository(ddb, orders_table)
    order = Order(order_id="ord-1002", customer_id="cust-42")

    repo.create(order)

    with pytest.raises(DuplicateOrderError):
        repo.create(order)


def test_invalid_table_name_returns_validation_exception(ddb):
    with pytest.raises(ClientError) as captured:
        ddb.create_table(
            TableName="ab",
            AttributeDefinitions=[
                {"AttributeName": "id", "AttributeType": "S"},
            ],
            KeySchema=[
                {"AttributeName": "id", "KeyType": "HASH"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )

    assert captured.value.response["Error"]["Code"] == "ValidationException"
