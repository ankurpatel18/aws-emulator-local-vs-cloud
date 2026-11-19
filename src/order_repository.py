from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any

from botocore.exceptions import ClientError


class DuplicateOrderError(RuntimeError):
    pass


@dataclass(frozen=True)
class Order:
    order_id: str
    customer_id: str
    status: str = "RECEIVED"


class OrderRepository:
    def __init__(self, dynamodb_client: Any, table_name: str) -> None:
        self._ddb = dynamodb_client
        self._table_name = table_name

    def create(self, order: Order) -> None:
        try:
            self._ddb.put_item(
                TableName=self._table_name,
                Item={
                    "order_id": {"S": order.order_id},
                    "customer_id": {"S": order.customer_id},
                    "status": {"S": order.status},
                },
                ConditionExpression="attribute_not_exists(order_id)",
            )
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code")
            if code == "ConditionalCheckFailedException":
                raise DuplicateOrderError(order.order_id) from exc
            raise

    def get(self, order_id: str) -> Order | None:
        response = self._ddb.get_item(
            TableName=self._table_name,
            Key={"order_id": {"S": order_id}},
            ConsistentRead=True,
        )
        item = response.get("Item")
        if not item:
            return None
        return Order(
            order_id=item["order_id"]["S"],
            customer_id=item["customer_id"]["S"],
            status=item["status"]["S"],
        )
