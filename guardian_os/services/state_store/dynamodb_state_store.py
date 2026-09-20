"""
AEGIS — DynamoDB State Store

Persistent state store for the deployed AEGIS control plane.
"""

from __future__ import annotations

import pickle
from typing import Any

import boto3
from boto3.dynamodb.types import Binary


class DynamoDBStateStore:
    """DynamoDB-backed state store for deployed AEGIS."""

    def __init__(
        self,
        table_name: str,
        region_name: str | None = None,
    ) -> None:
        if not table_name:
            raise ValueError("table_name is required.")

        if region_name:
            dynamodb = boto3.resource(
                "dynamodb",
                region_name=region_name,
            )
        else:
            dynamodb = boto3.resource("dynamodb")

        self.table = dynamodb.Table(table_name)

    @staticmethod
    def _serialize(value: Any) -> bytes:
        return pickle.dumps(
            value,
            protocol=pickle.HIGHEST_PROTOCOL,
        )

    @staticmethod
    def _deserialize(value: bytes | Binary) -> Any:
        if isinstance(value, Binary):
            value = bytes(value)

        return pickle.loads(value)

    def put(self, key: str, value: Any) -> None:
        if not key:
            raise ValueError("key is required.")

        self.table.put_item(
            Item={
                "assessment_id": key,
                "state_blob": self._serialize(value),
            }
        )

    def get(self, key: str) -> Any | None:
        if not key:
            return None

        response = self.table.get_item(
            Key={"assessment_id": key}
        )

        item = response.get("Item")

        if item is None:
            return None

        return self._deserialize(item["state_blob"])

    def delete(self, key: str) -> None:
        if not key:
            return

        self.table.delete_item(
            Key={"assessment_id": key}
        )

    def exists(self, key: str) -> bool:
        return self.get(key) is not None

    def all(self) -> dict[str, Any]:
        response = self.table.scan()

        records: dict[str, Any] = {}

        for item in response.get("Items", []):
            records[item["assessment_id"]] = self._deserialize(
                item["state_blob"]
            )

        return records