from dataclasses import dataclass
from typing import List

from services.event_ingestion.event_models import (
    EventSeverity,
    OperationalEvent,
)
from services.risk_engine.station_models import (
    StationState,
    calculate_capacity_overload,
    calculate_utilization,
)


# =========================================================
# GUARDIAN OS — DETERMINISTIC RISK ENGINE
# =========================================================
#
# Purpose:
#
#     Operational Event + Station State
#                  ↓
#             Risk Factors
#                  ↓
#          Composite Risk Score
#                  ↓
#          Risk Level + Drivers
#
# Design principles:
#
#   1. Deterministic
#   2. Explainable
#   3. Bounded to 0–100
#   4. No LLM dependency
#   5. Explicit factor contributions
#
# Bedrock/agentic intelligence will NOT calculate this
# numeric score. It may later explain the result and reason
# about response strategies.
#
# All thresholds and weights below are prototype policy
# parameters for synthetic simulation, not validated
# operational thresholds.
# =========================================================


# =========================================================
# PROTOTYPE POLICY PARAMETERS
# =========================================================

# Maximum contribution from each risk dimension.

UTILIZATION_WEIGHT = 40.0
OVERLOAD_WEIGHT = 25.0
EVENT_SEVERITY_WEIGHT = 20.0
ROUTE_PRESSURE_WEIGHT = 15.0


# Route pressure is normalized against this reference point.
# It is a prototype normalization constant for simulation.

ROUTE_REFERENCE = 500


# =========================================================
# RISK LEVELS
# =========================================================


RISK_LEVEL_CRITICAL = "CRITICAL"
RISK_LEVEL_HIGH = "HIGH"
RISK_LEVEL_MEDIUM = "MEDIUM"
RISK_LEVEL_LOW = "LOW"


def classify_risk(
    risk_score: float,
) -> str:
    """
    Convert a bounded numerical risk score into a
    categorical level.

    Prototype thresholds:
        75–100  → CRITICAL
        50–74.99 → HIGH
        25–49.99 → MEDIUM
        0–24.99 → LOW
    """

    if risk_score >= 75:
        return RISK_LEVEL_CRITICAL

    if risk_score >= 50:
        return RISK_LEVEL_HIGH

    if risk_score >= 25:
        return RISK_LEVEL_MEDIUM

    return RISK_LEVEL_LOW


# =========================================================
# RISK ASSESSMENT
# =========================================================


@dataclass(frozen=True)
class RiskAssessment:
    """
    Complete deterministic risk assessment.
    """

    station_id: str

    risk_score: float
    risk_level: str

    utilization: float
    capacity_overload: float

    utilization_contribution: float
    overload_contribution: float
    severity_contribution: float
    route_pressure_contribution: float

    drivers: List[str]


# =========================================================
# UTILIZATION RISK
# =========================================================


def calculate_utilization_risk(
    utilization: float,
) -> float:
    """
    Convert station utilization into a normalized risk
    contribution.

    Prototype behavior:

        <= 70%       → 0
        70–100%      → progressive risk
        >= 100%      → maximum contribution

    Maximum contribution = UTILIZATION_WEIGHT.
    """

    if utilization <= 70:
        return 0.0

    normalized = (
        (utilization - 70)
        / 30
    )

    normalized = min(
        max(normalized, 0.0),
        1.0,
    )

    return round(
        normalized * UTILIZATION_WEIGHT,
        2,
    )


# =========================================================
# CAPACITY OVERLOAD RISK
# =========================================================


def calculate_overload_risk(
    overload: float,
) -> float:
    """
    Convert capacity overload into a risk contribution.

    0% overload → 0 contribution.

    A 10% or greater overload reaches the maximum
    contribution for this factor.
    """

    if overload <= 0:
        return 0.0

    normalized = min(
        overload / 10,
        1.0,
    )

    return round(
        normalized * OVERLOAD_WEIGHT,
        2,
    )


# =========================================================
# EVENT SEVERITY RISK
# =========================================================


def calculate_severity_risk(
    severity: EventSeverity,
) -> float:
    """
    Convert event severity into a bounded risk contribution.
    """

    severity_scores = {
        EventSeverity.LOW: 0.25,
        EventSeverity.MEDIUM: 0.50,
        EventSeverity.HIGH: 0.75,
        EventSeverity.CRITICAL: 1.00,
    }

    normalized = severity_scores[
        severity
    ]

    return round(
        normalized
        * EVENT_SEVERITY_WEIGHT,
        2,
    )


# =========================================================
# ROUTE PRESSURE RISK
# =========================================================


def calculate_route_pressure(
    active_routes: int,
) -> float:
    """
    Estimate route-pressure contribution using a normalized
    reference point.

    This does not claim that 500 routes is a real-world
    operational threshold. It is a prototype simulation
    reference.
    """

    if active_routes <= 0:
        return 0.0

    normalized = min(
        active_routes / ROUTE_REFERENCE,
        1.0,
    )

    return round(
        normalized * ROUTE_PRESSURE_WEIGHT,
        2,
    )


# =========================================================
# DRIVER GENERATION
# =========================================================


def build_risk_drivers(
    state: StationState,
    event: OperationalEvent,
    utilization: float,
    overload: float,
) -> List[str]:

    drivers = []

    if utilization > 100:
        drivers.append(
            "Station operating above effective capacity"
        )

    elif utilization > 90:
        drivers.append(
            "Station utilization is approaching effective capacity"
        )

    if overload > 0:
        drivers.append(
            f"Capacity overload detected at "
            f"{overload:.2f}%"
        )

    if event.impact.severity in {
        EventSeverity.HIGH,
        EventSeverity.CRITICAL,
    }:
        drivers.append(
            f"Event classified as "
            f"{event.impact.severity.value.lower()} severity"
        )

    if state.active_routes >= ROUTE_REFERENCE:
        drivers.append(
            "Active route volume is at the "
            "prototype pressure reference"
        )

    if not drivers:
        drivers.append(
            "No major operational risk driver detected"
        )

    return drivers


# =========================================================
# COMPOSITE RISK
# =========================================================


def calculate_risk(
    state: StationState,
    event: OperationalEvent,
) -> RiskAssessment:
    """
    Calculate the complete deterministic risk assessment.
    """

    utilization = calculate_utilization(
        state
    )

    overload = calculate_capacity_overload(
        state
    )

    utilization_contribution = (
        calculate_utilization_risk(
            utilization
        )
    )

    overload_contribution = (
        calculate_overload_risk(
            overload
        )
    )

    severity_contribution = (
        calculate_severity_risk(
            event.impact.severity
        )
    )

    route_pressure_contribution = (
        calculate_route_pressure(
            state.active_routes
        )
    )

    raw_score = (
        utilization_contribution
        + overload_contribution
        + severity_contribution
        + route_pressure_contribution
    )

    risk_score = round(
        min(
            max(raw_score, 0.0),
            100.0,
        ),
        2,
    )

    risk_level = classify_risk(
        risk_score
    )

    drivers = build_risk_drivers(
        state,
        event,
        utilization,
        overload,
    )

    return RiskAssessment(
        station_id=state.station_id,

        risk_score=risk_score,
        risk_level=risk_level,

        utilization=utilization,
        capacity_overload=overload,

        utilization_contribution=(
            utilization_contribution
        ),

        overload_contribution=(
            overload_contribution
        ),

        severity_contribution=(
            severity_contribution
        ),

        route_pressure_contribution=(
            route_pressure_contribution
        ),

        drivers=drivers,
    )


# =========================================================
# RISK REPORT
# =========================================================


def print_risk_assessment(
    assessment: RiskAssessment,
) -> None:

    print()
    print("=" * 75)
    print("                         GUARDIAN OS")
    print("                      RISK ENGINE")
    print("=" * 75)

    print()
    print("RISK ASSESSMENT")
    print("-" * 75)

    print(
        f"Station            : "
        f"{assessment.station_id}"
    )

    print(
        f"Risk Score         : "
        f"{assessment.risk_score}/100"
    )

    print(
        f"Risk Level         : "
        f"{assessment.risk_level}"
    )

    print(
        f"Utilization        : "
        f"{assessment.utilization}%"
    )

    print(
        f"Capacity Overload  : "
        f"{assessment.capacity_overload}%"
    )

    print()
    print("RISK CONTRIBUTIONS")
    print("-" * 75)

    print(
        f"Utilization Risk   : "
        f"{assessment.utilization_contribution}"
    )

    print(
        f"Overload Risk      : "
        f"{assessment.overload_contribution}"
    )

    print(
        f"Event Severity     : "
        f"{assessment.severity_contribution}"
    )

    print(
        f"Route Pressure     : "
        f"{assessment.route_pressure_contribution}"
    )

    print()
    print("RISK DRIVERS")
    print("-" * 75)

    for index, driver in enumerate(
        assessment.drivers,
        start=1,
    ):
        print(
            f"{index}. {driver}"
        )


# =========================================================
# LOCAL TEST
# =========================================================


if __name__ == "__main__":

    # Import the canonical models.

    from services.event_ingestion.event_models import (
        event_from_dict,
    )

    sample_event_payload = {
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
        },
    }

    event = event_from_dict(
        sample_event_payload
    )

    state = StationState(
        station_id="CHN-017",
        city="Chennai",
        region="Tamil Nadu",
        capacity=8000,
        current_load=8200,
        active_routes=384,
    )

    assessment = calculate_risk(
        state,
        event,
    )

    print_risk_assessment(
        assessment
    )

    print()
    print("=" * 75)
    print("                    RISK ENGINE TEST PASSED")
    print("=" * 75)