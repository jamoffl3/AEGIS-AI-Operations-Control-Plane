"""
GUARDIAN OS
Outcome Engine

Purpose:
    Measure the operational effect of an executed intervention.

Architecture:

    Baseline State
          |
          v
    Intervention Execution
          |
          v
    Updated State
          |
          v
    Outcome Measurement
          |
          v
    Effectiveness Assessment
          |
          v
    Audit / Analytics Record

Important:
    - This engine measures outcomes.
    - It does not decide interventions.
    - It does not execute interventions.
    - Calculations are deterministic.
    - Current measurements use synthetic simulation data.
"""


from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict


# ============================================================
# GUARDIAN OS IMPORTS
# ============================================================

from services.risk_engine.station_models import (
    StationState,
    calculate_utilization,
)

from services.risk_engine.risk_engine import (
    calculate_risk,
)

from services.event_ingestion.event_models import (
    EventSeverity,
    EventType,
    EventImpact,
    OperationalEvent,
    StationReference,
)

from services.intervention_engine.intervention_engine import (
    InterventionDecision,
    evaluate_interventions,
)

from services.execution_engine.execution_engine import (
    ExecutionResult,
    ExecutionStatus,
    execute_intervention,
)


# ============================================================
# OUTCOME STATUS
# ============================================================

class OutcomeStatus:
    """
    High-level classification of intervention outcome.
    """

    IMPROVED = "IMPROVED"
    STABLE = "STABLE"
    DEGRADED = "DEGRADED"
    FAILED = "FAILED"


# ============================================================
# OUTCOME MEASUREMENT
# ============================================================

@dataclass
class OutcomeMeasurement:
    """
    Structured measurement of an intervention outcome.
    """

    execution_id: str

    station_id: str

    strategy: str

    baseline_risk: float
    post_intervention_risk: float

    risk_reduction: float

    baseline_utilization: float
    post_intervention_utilization: float

    utilization_improvement: float

    baseline_capacity: float
    post_intervention_capacity: float

    capacity_change: float

    baseline_load: float
    post_intervention_load: float

    load_change: float

    baseline_routes: int
    post_intervention_routes: int

    routes_moved: int

    effectiveness_score: float

    outcome_status: str

    measured_at: str

    measurement_notes: str


# ============================================================
# SYNTHETIC EVENT
# ============================================================

def build_capacity_shock_event(
    state: StationState,
) -> OperationalEvent:
    """
    Build the synthetic capacity-shock event used by the
    current Guardian prototype.
    """

    return OperationalEvent(
        event_id="EVT-0001",

        event_type=EventType.STATION_CAPACITY_SHOCK,

        timestamp="2026-09-18T10:30:00Z",

        source="GUARDIAN_SIMULATOR",

        station=StationReference(
            station_id=state.station_id,
            city=state.city,
            region=state.region,
        ),

        impact=EventImpact(
            severity=EventSeverity.HIGH,

            capacity_change_percent=-20.0,

            description=(
                "Synthetic station capacity disruption"
            ),
        ),

        metadata={
            "simulation": True,
        },
    )


# ============================================================
# RISK CALCULATION
# ============================================================

def calculate_state_risk(
    state: StationState,
) -> float:
    """
    Calculate risk for a station state using the canonical
    Guardian Risk Engine.
    """

    event = build_capacity_shock_event(
        state
    )

    assessment = calculate_risk(
        state,
        event,
    )

    return round(
        assessment.risk_score,
        2,
    )


# ============================================================
# RISK CHANGE
# ============================================================

def calculate_risk_reduction(
    baseline_risk: float,
    post_intervention_risk: float,
) -> float:
    """
    Calculate percentage reduction in risk.
    """

    if baseline_risk <= 0:
        return 0.0

    reduction = (
        (
            baseline_risk
            - post_intervention_risk
        )
        / baseline_risk
    ) * 100.0

    return round(
        max(
            0.0,
            reduction,
        ),
        2,
    )


# ============================================================
# UTILIZATION CHANGE
# ============================================================

def calculate_utilization_improvement(
    baseline_utilization: float,
    post_intervention_utilization: float,
) -> float:
    """
    Calculate improvement in utilization in percentage
    points.

    Lower utilization represents more available operational
    headroom in this prototype.
    """

    improvement = (
        baseline_utilization
        - post_intervention_utilization
    )

    return round(
        improvement,
        2,
    )


# ============================================================
# CAPACITY CHANGE
# ============================================================

def calculate_capacity_change(
    baseline_capacity: float,
    post_intervention_capacity: float,
) -> float:
    """
    Calculate absolute capacity change.
    """

    return round(
        post_intervention_capacity
        - baseline_capacity,
        2,
    )


# ============================================================
# LOAD CHANGE
# ============================================================

def calculate_load_change(
    baseline_load: float,
    post_intervention_load: float,
) -> float:
    """
    Calculate absolute load change.
    """

    return round(
        post_intervention_load
        - baseline_load,
        2,
    )


# ============================================================
# ROUTE MOVEMENT
# ============================================================

def calculate_routes_moved(
    baseline_routes: int,
    post_intervention_routes: int,
) -> int:
    """
    Calculate how many routes changed.
    """

    return abs(
        post_intervention_routes
        - baseline_routes
    )


# ============================================================
# EFFECTIVENESS SCORE
# ============================================================

def calculate_effectiveness_score(
    risk_reduction: float,
    utilization_improvement: float,
    capacity_change: float,
    load_change: float,
) -> float:
    """
    Calculate a normalized intervention effectiveness score.

    Prototype measurement policy:

        60% risk improvement
        25% utilization improvement
        15% operational recovery

    This is a prototype analytical metric, not a validated
    real-world business KPI.
    """

    # --------------------------------------------------------
    # Risk component
    # --------------------------------------------------------

    risk_component = min(
        100.0,
        max(
            0.0,
            risk_reduction,
        ),
    )

    # --------------------------------------------------------
    # Utilization component
    # --------------------------------------------------------

    utilization_component = min(
        100.0,
        max(
            0.0,
            (utilization_improvement / 30.0)
            * 100.0,
        ),
    )

    # --------------------------------------------------------
    # Operational recovery component
    # --------------------------------------------------------

    capacity_recovery = max(
        0.0,
        capacity_change,
    )

    load_reduction = max(
        0.0,
        -load_change,
    )

    operational_recovery = min(
        100.0,
        (
            (
                capacity_recovery
                / 1000.0
            )
            * 50.0
        )
        + (
            (
                load_reduction
                / 1000.0
            )
            * 50.0
        ),
    )

    # --------------------------------------------------------
    # Final score
    # --------------------------------------------------------

    score = (
        risk_component * 0.60
        + utilization_component * 0.25
        + operational_recovery * 0.15
    )

    return round(
        min(
            100.0,
            max(
                0.0,
                score,
            ),
        ),
        2,
    )


# ============================================================
# OUTCOME CLASSIFICATION
# ============================================================

def classify_outcome(
    baseline_risk: float,
    post_intervention_risk: float,
    effectiveness_score: float,
) -> str:
    """
    Classify the measured intervention outcome.
    """

    # --------------------------------------------------------
    # Strong improvement
    # --------------------------------------------------------

    if (
        post_intervention_risk
        < baseline_risk
        and effectiveness_score >= 50.0
    ):

        return OutcomeStatus.IMPROVED

    # --------------------------------------------------------
    # Moderate improvement
    # --------------------------------------------------------

    if (
        post_intervention_risk
        < baseline_risk
    ):

        return OutcomeStatus.IMPROVED

    # --------------------------------------------------------
    # No meaningful change
    # --------------------------------------------------------

    if abs(
        post_intervention_risk
        - baseline_risk
    ) < 0.01:

        return OutcomeStatus.STABLE

    # --------------------------------------------------------
    # Degradation
    # --------------------------------------------------------

    if (
        post_intervention_risk
        > baseline_risk
    ):

        return OutcomeStatus.DEGRADED

    return OutcomeStatus.FAILED


# ============================================================
# MEASURE OUTCOME
# ============================================================

def measure_outcome(
    baseline_state: StationState,
    post_intervention_state: StationState,
    execution_result: ExecutionResult,
) -> OutcomeMeasurement:
    """
    Measure the effect of an executed intervention.
    """

    # --------------------------------------------------------
    # Validate execution
    # --------------------------------------------------------

    if execution_result.status != ExecutionStatus.EXECUTED:

        raise ValueError(
            "Outcome measurement requires a successfully "
            "executed intervention."
        )

    # --------------------------------------------------------
    # Risk
    # --------------------------------------------------------

    baseline_risk = calculate_state_risk(
        baseline_state
    )

    post_intervention_risk = calculate_state_risk(
        post_intervention_state
    )

    risk_reduction = calculate_risk_reduction(
        baseline_risk,
        post_intervention_risk,
    )

    # --------------------------------------------------------
    # Utilization
    # --------------------------------------------------------

    baseline_utilization = (
        calculate_utilization(
            baseline_state
        )
    )

    post_intervention_utilization = (
        calculate_utilization(
            post_intervention_state
        )
    )

    utilization_improvement = (
        calculate_utilization_improvement(
            baseline_utilization,
            post_intervention_utilization,
        )
    )

    # --------------------------------------------------------
    # Capacity
    # --------------------------------------------------------

    capacity_change = calculate_capacity_change(
        baseline_state.capacity,
        post_intervention_state.capacity,
    )

    # --------------------------------------------------------
    # Load
    # --------------------------------------------------------

    load_change = calculate_load_change(
        baseline_state.current_load,
        post_intervention_state.current_load,
    )

    # --------------------------------------------------------
    # Routes
    # --------------------------------------------------------

    routes_moved = calculate_routes_moved(
        baseline_state.active_routes,
        post_intervention_state.active_routes,
    )

    # --------------------------------------------------------
    # Effectiveness
    # --------------------------------------------------------

    effectiveness_score = (
        calculate_effectiveness_score(
            risk_reduction,
            utilization_improvement,
            capacity_change,
            load_change,
        )
    )

    # --------------------------------------------------------
    # Outcome status
    # --------------------------------------------------------

    outcome_status = classify_outcome(
        baseline_risk,
        post_intervention_risk,
        effectiveness_score,
    )

    # --------------------------------------------------------
    # Timestamp
    # --------------------------------------------------------

    measured_at = datetime.now(
        timezone.utc
    ).isoformat()

    # --------------------------------------------------------
    # Notes
    # --------------------------------------------------------

    notes = (
        f"Intervention {execution_result.strategy} "
        f"changed measured station risk from "
        f"{baseline_risk:.2f} to "
        f"{post_intervention_risk:.2f}. "
        f"Utilization changed from "
        f"{baseline_utilization:.2f}% to "
        f"{post_intervention_utilization:.2f}%. "
        f"Effectiveness score: "
        f"{effectiveness_score:.2f}/100. "
        f"Measurement is based on synthetic prototype "
        f"simulation data."
    )

    return OutcomeMeasurement(

        execution_id=execution_result.execution_id,

        station_id=execution_result.station_id,

        strategy=execution_result.strategy,

        baseline_risk=baseline_risk,

        post_intervention_risk=post_intervention_risk,

        risk_reduction=risk_reduction,

        baseline_utilization=round(
            baseline_utilization,
            2,
        ),

        post_intervention_utilization=round(
            post_intervention_utilization,
            2,
        ),

        utilization_improvement=utilization_improvement,

        baseline_capacity=round(
            baseline_state.capacity,
            2,
        ),

        post_intervention_capacity=round(
            post_intervention_state.capacity,
            2,
        ),

        capacity_change=capacity_change,

        baseline_load=round(
            baseline_state.current_load,
            2,
        ),

        post_intervention_load=round(
            post_intervention_state.current_load,
            2,
        ),

        load_change=load_change,

        baseline_routes=baseline_state.active_routes,

        post_intervention_routes=(
            post_intervention_state.active_routes
        ),

        routes_moved=routes_moved,

        effectiveness_score=effectiveness_score,

        outcome_status=outcome_status,

        measured_at=measured_at,

        measurement_notes=notes,
    )


# ============================================================
# SERIALIZATION
# ============================================================

def outcome_to_dict(
    outcome: OutcomeMeasurement,
) -> Dict:
    """
    Convert an outcome measurement into a JSON-compatible
    dictionary.
    """

    return {
        "execution_id": outcome.execution_id,

        "station_id": outcome.station_id,

        "strategy": outcome.strategy,

        "baseline_risk": outcome.baseline_risk,

        "post_intervention_risk": (
            outcome.post_intervention_risk
        ),

        "risk_reduction": (
            outcome.risk_reduction
        ),

        "baseline_utilization": (
            outcome.baseline_utilization
        ),

        "post_intervention_utilization": (
            outcome.post_intervention_utilization
        ),

        "utilization_improvement": (
            outcome.utilization_improvement
        ),

        "baseline_capacity": (
            outcome.baseline_capacity
        ),

        "post_intervention_capacity": (
            outcome.post_intervention_capacity
        ),

        "capacity_change": (
            outcome.capacity_change
        ),

        "baseline_load": (
            outcome.baseline_load
        ),

        "post_intervention_load": (
            outcome.post_intervention_load
        ),

        "load_change": (
            outcome.load_change
        ),

        "baseline_routes": (
            outcome.baseline_routes
        ),

        "post_intervention_routes": (
            outcome.post_intervention_routes
        ),

        "routes_moved": (
            outcome.routes_moved
        ),

        "effectiveness_score": (
            outcome.effectiveness_score
        ),

        "outcome_status": (
            outcome.outcome_status
        ),

        "measured_at": (
            outcome.measured_at
        ),

        "measurement_notes": (
            outcome.measurement_notes
        ),
    }


# ============================================================
# LOCAL TEST
# ============================================================

if __name__ == "__main__":

    print("=" * 70)
    print("GUARDIAN OS — OUTCOME ENGINE TEST")
    print("=" * 70)

    # --------------------------------------------------------
    # BASELINE STATION
    # --------------------------------------------------------

    baseline_station = StationState(
        station_id="CHN-017",
        city="Chennai",
        region="Tamil Nadu",
        capacity=8000,
        current_load=8200,
        active_routes=384,
    )

    # --------------------------------------------------------
    # INTERVENTION DECISION
    # --------------------------------------------------------

    decision = evaluate_interventions(
        baseline_station
    )

    print("\nINTERVENTION")
    print("-" * 70)

    print(
        f"Strategy: "
        f"{decision.selected_strategy}"
    )

    print(
        f"Decision Score: "
        f"{decision.decision_score:.2f}"
    )

    # --------------------------------------------------------
    # EXECUTION
    # --------------------------------------------------------

    execution_result = execute_intervention(
        state=baseline_station,
        decision=decision,
        execution_id="EXEC-OUTCOME-0001",
    )

    print("\nEXECUTION")
    print("-" * 70)

    print(
        f"Execution ID: "
        f"{execution_result.execution_id}"
    )

    print(
        f"Status: "
        f"{execution_result.status}"
    )

    # --------------------------------------------------------
    # RECONSTRUCT POST-INTERVENTION STATE
    # --------------------------------------------------------

    transition = (
        execution_result.state_transition
    )

    if transition is None:

        raise RuntimeError(
            "Execution did not produce a state transition."
        )

    post_intervention_state = StationState(
        station_id=baseline_station.station_id,

        city=baseline_station.city,

        region=baseline_station.region,

        capacity=transition.new_capacity,

        current_load=transition.new_load,

        active_routes=transition.new_routes,
    )

    # --------------------------------------------------------
    # MEASURE
    # --------------------------------------------------------

    outcome = measure_outcome(
        baseline_state=baseline_station,

        post_intervention_state=(
            post_intervention_state
        ),

        execution_result=execution_result,
    )

    # --------------------------------------------------------
    # OUTCOME
    # --------------------------------------------------------

    print("\nOUTCOME MEASUREMENT")
    print("-" * 70)

    print(
        f"Station: "
        f"{outcome.station_id}"
    )

    print(
        f"Strategy: "
        f"{outcome.strategy}"
    )

    print(
        f"Risk: "
        f"{outcome.baseline_risk:.2f}"
        f" → "
        f"{outcome.post_intervention_risk:.2f}"
    )

    print(
        f"Risk Reduction: "
        f"{outcome.risk_reduction:.2f}%"
    )

    print(
        f"Utilization: "
        f"{outcome.baseline_utilization:.2f}%"
        f" → "
        f"{outcome.post_intervention_utilization:.2f}%"
    )

    print(
        f"Utilization Improvement: "
        f"{outcome.utilization_improvement:.2f} "
        f"percentage points"
    )

    print(
        f"Capacity: "
        f"{outcome.baseline_capacity:.2f}"
        f" → "
        f"{outcome.post_intervention_capacity:.2f}"
    )

    print(
        f"Load: "
        f"{outcome.baseline_load:.2f}"
        f" → "
        f"{outcome.post_intervention_load:.2f}"
    )

    print(
        f"Routes: "
        f"{outcome.baseline_routes}"
        f" → "
        f"{outcome.post_intervention_routes}"
    )

    print(
        f"Routes Moved: "
        f"{outcome.routes_moved}"
    )

    print(
        f"Effectiveness Score: "
        f"{outcome.effectiveness_score:.2f}/100"
    )

    print(
        f"Outcome Status: "
        f"{outcome.outcome_status}"
    )

    print(
        f"\nMeasurement Notes:\n"
        f"{outcome.measurement_notes}"
    )

    # --------------------------------------------------------
    # SERIALIZATION TEST
    # --------------------------------------------------------

    serialized = outcome_to_dict(
        outcome
    )

    print("\nSERIALIZATION TEST")
    print("-" * 70)

    print(
        f"Fields generated: "
        f"{len(serialized)}"
    )

    print(
        f"Execution ID: "
        f"{serialized['execution_id']}"
    )

    print(
        f"Outcome Status: "
        f"{serialized['outcome_status']}"
    )

    print("\n" + "=" * 70)
    print("OUTCOME ENGINE TEST COMPLETE")
    print("=" * 70)