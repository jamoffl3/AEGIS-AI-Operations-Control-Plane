from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict


# =========================================================
# GUARDIAN OS — NETWORK STATE DOMAIN MODEL
# =========================================================
#
# This module represents the operational state of a station
# at a specific point in time.
#
# Event ingestion tells us:
#
#     "Something happened."
#
# StationState tells Guardian:
#
#     "What does the network look like because of it?"
#
# The Risk Engine will consume this model.
#
# IMPORTANT:
# This model contains operational state only.
# It does NOT calculate risk.
# =========================================================


class StationStatus(str, Enum):
    """
    Operational state of a station.
    """

    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    OVER_CAPACITY = "OVER_CAPACITY"
    CRITICAL = "CRITICAL"


@dataclass(frozen=True)
class StationState:
    """
    Canonical operational state for a single station.
    """

    station_id: str
    city: str
    region: str

    capacity: int
    current_load: int
    active_routes: int

    status: StationStatus = StationStatus.HEALTHY

    def __post_init__(self) -> None:

        # ---------------------------------------------
        # Identity validation
        # ---------------------------------------------

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

        # ---------------------------------------------
        # Operational validation
        # ---------------------------------------------

        if self.capacity <= 0:
            raise ValueError(
                "capacity must be greater than zero."
            )

        if self.current_load < 0:
            raise ValueError(
                "current_load cannot be negative."
            )

        if self.active_routes < 0:
            raise ValueError(
                "active_routes cannot be negative."
            )


# =========================================================
# DERIVED OPERATIONAL METRICS
# =========================================================


def calculate_utilization(
    state: StationState,
) -> float:
    """
    Calculate station utilization as a percentage.

    Example:

        load = 8,200
        capacity = 8,000

        utilization = 102.5%
    """

    utilization = (
        state.current_load
        / state.capacity
    ) * 100

    return round(
        utilization,
        2,
    )


def calculate_capacity_overload(
    state: StationState,
) -> float:
    """
    Calculate the percentage by which station load exceeds
    capacity.

    Returns zero when the station is operating within
    capacity.
    """

    if state.current_load <= state.capacity:
        return 0.0

    overload = (
        (
            state.current_load
            - state.capacity
        )
        / state.capacity
    ) * 100

    return round(
        overload,
        2,
    )


def determine_station_status(
    state: StationState,
) -> StationStatus:
    """
    Determine operational status from utilization.

    This is a state classification, not a risk score.
    """

    utilization = calculate_utilization(
        state
    )

    if utilization > 110:
        return StationStatus.CRITICAL

    if utilization > 100:
        return StationStatus.OVER_CAPACITY

    if utilization > 90:
        return StationStatus.DEGRADED

    return StationStatus.HEALTHY


# =========================================================
# SERIALIZATION
# =========================================================


def station_state_to_dict(
    state: StationState,
) -> Dict[str, Any]:
    """
    Convert StationState into a JSON-compatible structure.
    """

    return {
        "station_id": state.station_id,
        "city": state.city,
        "region": state.region,
        "capacity": state.capacity,
        "current_load": state.current_load,
        "active_routes": state.active_routes,
        "status": state.status.value,

        "derived_metrics": {
            "utilization_percent": (
                calculate_utilization(state)
            ),
            "capacity_overload_percent": (
                calculate_capacity_overload(state)
            ),
        },
    }


# =========================================================
# DESERIALIZATION
# =========================================================


def station_state_from_dict(
    payload: Dict[str, Any],
) -> StationState:
    """
    Construct a validated StationState from a raw
    dictionary.
    """

    if not isinstance(
        payload,
        dict,
    ):
        raise TypeError(
            "Station state must be a dictionary."
        )

    required_fields = [
        "station_id",
        "city",
        "region",
        "capacity",
        "current_load",
        "active_routes",
    ]

    missing = [
        field
        for field in required_fields
        if field not in payload
    ]

    if missing:
        raise ValueError(
            "Missing required station fields: "
            + ", ".join(missing)
        )

    return StationState(
        station_id=str(
            payload["station_id"]
        ),
        city=str(
            payload["city"]
        ),
        region=str(
            payload["region"]
        ),
        capacity=int(
            payload["capacity"]
        ),
        current_load=int(
            payload["current_load"]
        ),
        active_routes=int(
            payload["active_routes"]
        ),
        status=StationStatus(
            payload.get(
                "status",
                StationStatus.HEALTHY.value,
            )
        ),
    )


# =========================================================
# LOCAL CONTRACT TEST
# =========================================================


if __name__ == "__main__":

    sample_station = {
        "station_id": "CHN-017",
        "city": "Chennai",
        "region": "Tamil Nadu",
        "capacity": 8000,
        "current_load": 8200,
        "active_routes": 384,
    }

    state = station_state_from_dict(
        sample_station
    )

    utilization = calculate_utilization(
        state
    )

    overload = calculate_capacity_overload(
        state
    )

    status = determine_station_status(
        state
    )

    serialized = station_state_to_dict(
        state
    )

    print()
    print("=" * 75)
    print("                         GUARDIAN OS")
    print("                  STATION STATE MODEL")
    print("=" * 75)

    print()
    print("VALIDATION: PASSED")

    print(
        f"Station            : "
        f"{state.station_id}"
    )

    print(
        f"Location           : "
        f"{state.city}, {state.region}"
    )

    print(
        f"Capacity           : "
        f"{state.capacity:,}"
    )

    print(
        f"Current Load       : "
        f"{state.current_load:,}"
    )

    print(
        f"Active Routes      : "
        f"{state.active_routes:,}"
    )

    print()
    print("DERIVED STATE")
    print("-" * 75)

    print(
        f"Utilization        : "
        f"{utilization}%"
    )

    print(
        f"Capacity Overload  : "
        f"{overload}%"
    )

    print(
        f"Station Status     : "
        f"{status.value}"
    )

    print()
    print("SERIALIZATION: PASSED")

    print(
        f"Serialized Type    : "
        f"{type(serialized).__name__}"
    )

    print("=" * 75)