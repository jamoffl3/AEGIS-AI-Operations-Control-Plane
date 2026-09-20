"""
AEGIS — Local Persistent State Store

Local development implementation of the AEGIS state layer.

The local implementation uses a pickle-backed file so that complete
Python domain objects can be persisted during development.

Runtime behavior:

    Local development
          ↓
    data/aegis_state.pkl

    AWS Lambda
          ↓
    /tmp/aegis_state.pkl

IMPORTANT:
This store is suitable for local development and temporary Lambda
execution state only.

AWS Lambda /tmp storage is ephemeral and is NOT a durable replacement
for DynamoDB.

The final deployed architecture should migrate persistent control-plane
state to DynamoDB.
"""

from __future__ import annotations

import os
import pickle
from pathlib import Path
from threading import Lock
from typing import Any


class LocalStateStore:
    """File-backed state store for AEGIS development and prototype use."""

    def __init__(
        self,
        file_path: str | None = None,
    ) -> None:
        self.file_path = self._resolve_file_path(file_path)
        self._lock = Lock()

        self.file_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        if not self.file_path.exists():
            self._write_state({})

    @staticmethod
    def _resolve_file_path(
        file_path: str | None,
    ) -> Path:
        """
        Resolve the state-file location.

        Local development:
            data/aegis_state.pkl

        AWS Lambda:
            /tmp/aegis_state.pkl

        An explicit file_path always takes precedence.
        """

        if file_path:
            return Path(file_path)

        # AWS Lambda exposes AWS_LAMBDA_FUNCTION_NAME.
        # Lambda's deployed application directory is read-only,
        # while /tmp is writable.
        if os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
            return Path("/tmp/aegis_state.pkl")

        return Path("data/aegis_state.pkl")

    def _read_state(self) -> dict[str, Any]:
        """Read the complete state from disk."""

        if not self.file_path.exists():
            return {}

        try:
            with self.file_path.open("rb") as file:
                state = pickle.load(file)

            if isinstance(state, dict):
                return state

            return {}

        except (
            EOFError,
            pickle.PickleError,
            OSError,
        ):
            return {}

    def _write_state(
        self,
        state: dict[str, Any],
    ) -> None:
        """Atomically persist the complete state to disk."""

        temporary_path = self.file_path.with_suffix(".tmp")

        with temporary_path.open("wb") as file:
            pickle.dump(
                state,
                file,
                protocol=pickle.HIGHEST_PROTOCOL,
            )

        temporary_path.replace(self.file_path)

    def put(
        self,
        key: str,
        value: Any,
    ) -> None:
        """Create or replace a state record."""

        with self._lock:
            state = self._read_state()
            state[key] = value
            self._write_state(state)

    def get(
        self,
        key: str,
    ) -> Any | None:
        """Retrieve a state record."""

        with self._lock:
            state = self._read_state()
            return state.get(key)

    def delete(
        self,
        key: str,
    ) -> None:
        """Delete a state record."""

        with self._lock:
            state = self._read_state()

            if key in state:
                del state[key]
                self._write_state(state)

    def exists(
        self,
        key: str,
    ) -> bool:
        """Check whether a state record exists."""

        with self._lock:
            state = self._read_state()
            return key in state

    def all(self) -> dict[str, Any]:
        """Return all stored records."""

        with self._lock:
            return self._read_state()