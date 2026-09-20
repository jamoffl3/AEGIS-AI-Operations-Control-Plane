from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional


# =========================================================
# GUARDIAN OS — OPERATIONAL EVENT DOMAIN MODEL
# =========================================================
#
# This module defines the canonical event contract used by
# Guardian OS.
#
# Design goals:
#   1. Strongly typed event representation
#   2. Explicit event taxonomy
#   3. Validation at the system boundary
#   4. Easy serialization for APIs / EventBridge
#   5. No business intelligence or risk calculation here
#
# The event model is deliberately independent of AWS so that
# the same contract works in BUILD IT and SHIP IT modes.
# =========================================================


class EventType(str, Enum):
    """
    Canonical operational disruption types supported by
    Guardian OS.
    """

    STATION_CAPACITY_SHOCK = "STATION_CAPACITY_SHOCK"
    TRAFFIC_DISRUPTION = "TRAFFIC_DISRUPTION"
    WEATHER_DISRUPTION = "WEATHER_DISRUPTION"
    DEMAND_SPIKE = "DEMAND_SPIKE"
    ASSOCIATE_SHORTAGE = "ASSOCIATE_SHORTAGE"
    ROUTE_OVERLOAD = "ROUTE_OVERLOAD"
    DELIVERY_EXCEPTION = "DELIVERY_EXCEPTION"


class EventSeverity(str, Enum):
    """
    Severity classification attached to an operational event.
    """

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass(frozen=True)
class StationReference:
    """
    Identifies the operational station affected by an event.
    """

    station_id: str
    city: str
    region: str

    def __post_init__(self) -> None:

        if not self.station_id.strip():
            raise ValueError(
                "station_id cannot be empty."
            )

        if not self.city.strip():
            raise ValueError(
                "city cannot be empty."
            )

        if not self.region.strip():
            raise ValueError(
                "region cannot be empty."
            )


@dataclass(frozen=True)
class EventImpact:
    """
    Structured impact information associated with an event.

    Different event types may use different fields. Optional
    fields allow the canonical contract to represent multiple
    disruption classes without creating unrelated event models.
    """

    severity: EventSeverity

    capacity_change_percent: Optional[float] = None
    demand_change_percent: Optional[float] = None
    workforce_change_percent: Optional[float] = None
    route_change_percent: Optional[float] = None

    description: Optional[str] = None

    def __post_init__(self) -> None:

        percentages = {
            "capacity_change_percent": (
                self.capacity_change_percent
            ),
            "demand_change_percent": (
                self.demand_change_percent
            ),
            "workforce_change_percent": (
                self.workforce_change_percent
            ),
            "route_change_percent": (
                self.route_change_percent
            ),
        }

        for name, value in percentages.items():

            if value is None:
                continue

            if value < -100:
                raise ValueError(
                    f"{name} cannot be less than -100."
                )


@dataclass(frozen=True)
class OperationalEvent:
    """
    Canonical Guardian OS operational event.

    This is the boundary object entering the control plane.
    """

    event_id: str
    event_type: EventType
    timestamp: datetime
    source: str
    station: StationReference
    impact: EventImpact
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self) -> None:

        if not self.event_id.strip():
            raise ValueError(
                "event_id cannot be empty."
            )

        if not self.source.strip():
            raise ValueError(
                "source cannot be empty."
            )


# =========================================================
# SERIALIZATION
# =========================================================


def event_to_dict(
    event: OperationalEvent,
) -> Dict[str, Any]:
    """
    Convert an OperationalEvent into a JSON-compatible
    dictionary.

    This representation is suitable for APIs, event buses,
    logs, and persistence layers.
    """

    return {
        "event_id": event.event_id,

        "event_type": (
            event.event_type.value
        ),

        "timestamp": (
            event.timestamp.isoformat()
        ),

        "source": event.source,

        "station": {
            "station_id": (
                event.station.station_id
            ),
            "city": event.station.city,
            "region": event.station.region,
        },

        "impact": {
            "severity": (
                event.impact.severity.value
            ),
            "capacity_change_percent": (
                event.impact.capacity_change_percent
            ),
            "demand_change_percent": (
                event.impact.demand_change_percent
            ),
            "workforce_change_percent": (
                event.impact.workforce_change_percent
            ),
            "route_change_percent": (
                event.impact.route_change_percent
            ),
            "description": (
                event.impact.description
            ),
        },

        "metadata": event.metadata or {},
    }


# =========================================================
# DESERIALIZATION
# =========================================================


def event_from_dict(
    payload: Dict[str, Any],
) -> OperationalEvent:
    """
    Validate and construct an OperationalEvent from a raw
    dictionary.

    This function represents the boundary between untrusted/
    external event payloads and Guardian's typed domain model.
    """

    if not isinstance(payload, dict):
        raise TypeError(
            "Event payload must be a dictionary."
        )

    required_fields = [
        "event_id",
        "event_type",
        "timestamp",
        "source",
        "station",
        "impact",
    ]

    missing = [
        field
        for field in required_fields
        if field not in payload
    ]

    if missing:
        raise ValueError(
            "Missing required event fields: "
            + ", ".join(missing)
        )

    station_payload = payload["station"]

    if not isinstance(station_payload, dict):
        raise TypeError(
            "station must be a dictionary."
        )

    impact_payload = payload["impact"]

    if not isinstance(impact_payload, dict):
        raise TypeError(
            "impact must be a dictionary."
        )

    station = StationReference(
        station_id=station_payload[
            "station_id"
        ],
        city=station_payload[
            "city"
        ],
        region=station_payload[
            "region"
        ],
    )

    impact = EventImpact(
        severity=EventSeverity(
            impact_payload[
                "severity"
            ]
        ),
        capacity_change_percent=(
            impact_payload.get(
                "capacity_change_percent"
            )
        ),
        demand_change_percent=(
            impact_payload.get(
                "demand_change_percent"
            )
        ),
        workforce_change_percent=(
            impact_payload.get(
                "workforce_change_percent"
            )
        ),
        route_change_percent=(
            impact_payload.get(
                "route_change_percent"
            )
        ),
        description=(
            impact_payload.get(
                "description"
            )
        ),
    )

    timestamp = datetime.fromisoformat(
        payload["timestamp"].replace(
            "Z",
            "+00:00",
        )
    )

    return OperationalEvent(
        event_id=payload["event_id"],
        event_type=EventType(
            payload["event_type"]
        ),
        timestamp=timestamp,
        source=payload["source"],
        station=station,
        impact=impact,
        metadata=payload.get(
            "metadata"
        ),
    )


# =========================================================
# LOCAL CONTRACT TEST
# =========================================================


if __name__ == "__main__":

    sample_payload = {
        "event_id": "EVT-0001",

        "event_type": (
            "STATION_CAPACITY_SHOCK"
        ),

        "timestamp": (
            "2026-09-18T10:30:00Z"
        ),

        "source": (
            "GUARDIAN_SIMULATOR"
        ),

        "station": {
            "station_id": "CHN-017",
            "city": "Chennai",
            "region": "Tamil Nadu",
        },

        "impact": {
            "severity": "HIGH",
            "capacity_change_percent": -20,
            "description": (
                "Synthetic station capacity disruption"
            ),
        },
    }

    event = event_from_dict(
        sample_payload
    )

    serialized = event_to_dict(
        event
    )

    print()
    print("=" * 70)
    print("              GUARDIAN OS")
    print("          EVENT MODEL CONTRACT")
    print("=" * 70)

    print()
    print("VALIDATION: PASSED")

    print(
        f"Event ID       : "
        f"{event.event_id}"
    )

    print(
        f"Event Type     : "
        f"{event.event_type.value}"
    )

    print(
        f"Station        : "
        f"{event.station.station_id}"
    )

    print(
        f"Severity       : "
        f"{event.impact.severity.value}"
    )

    print(
        f"Capacity Delta : "
        f"{event.impact.capacity_change_percent}%"
    )

    print()
    print("SERIALIZATION: PASSED")

    print(
        f"Serialized Type: "
        f"{type(serialized).__name__}"
    )

    print("=" * 70)