"""
GUARDIAN OS
Execution Engine

Purpose:
    Safely execute an approved intervention decision.

Architecture:

    Intervention Engine
            |
            v
    Execution Request
            |
            v
    Pre-execution Validation
            |
            v
    Idempotency Check
            |
            v
    State Transition
            |
            v
    Execution Result
            |
            v
    Audit Record

Important:
    - Intervention Engine decides WHAT should happen.
    - Execution Engine applies the approved transition.
    - Numeric execution logic is deterministic.
    - The original StationState is never mutated.
    - Execution is currently in-memory.
    - AWS persistence will be added later.
"""


from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional


# ============================================================
# GUARDIAN OS IMPORTS
# ============================================================

from services.risk_engine.station_models import (
    StationState,
    calculate_utilization,
    determine_station_status,
)

from services.intervention_engine.intervention_engine import (
    InterventionDecision,
    evaluate_interventions,
)


# ============================================================
# EXECUTION STATUS
# ============================================================

class ExecutionStatus:
    """
    Lifecycle states for intervention execution.
    """

    VALIDATED = "VALIDATED"
    EXECUTED = "EXECUTED"
    REJECTED = "REJECTED"
    ALREADY_EXECUTED = "ALREADY_EXECUTED"


# ============================================================
# EXECUTION REQUEST
# ============================================================

@dataclass
class ExecutionRequest:
    """
    Represents a request to execute an approved intervention.
    """

    execution_id: str
    station_id: str
    strategy: str
    decision_score: float
    requested_by: str = "GUARDIAN_CONTROL_PLANE"


# ============================================================
# STATE TRANSITION
# ============================================================

@dataclass
class StateTransition:
    """
    Auditable before-and-after representation of a
    station state.
    """

    station_id: str

    previous_capacity: float
    new_capacity: float

    previous_load: float
    new_load: float

    previous_routes: int
    new_routes: int

    previous_utilization: float
    new_utilization: float

    previous_status: str
    new_status: str


# ============================================================
# EXECUTION RESULT
# ============================================================

@dataclass
class ExecutionResult:
    """
    Complete result of an execution attempt.
    """

    execution_id: str
    station_id: str
    strategy: str

    status: str

    executed_at: str

    state_transition: Optional[StateTransition]

    validation_errors: List[str]

    audit_record: Dict


# ============================================================
# LOCAL IDEMPOTENCY STORE
# ============================================================

"""
Local prototype implementation.

Later this boundary will be replaced with a durable
DynamoDB-backed idempotency record.
"""

_EXECUTED_INTERVENTIONS: Dict[str, ExecutionResult] = {}


# ============================================================
# SUPPORTED STRATEGIES
# ============================================================

SUPPORTED_STRATEGIES = {
    "HYBRID_RESPONSE",
    "ROUTE_REBALANCE",
    "CAPACITY_SHIFT",
}


# ============================================================
# STRATEGY VALIDATION
# ============================================================

def validate_strategy(
    strategy: str,
) -> List[str]:
    """
    Validate whether the requested strategy is supported.
    """

    errors: List[str] = []

    if strategy not in SUPPORTED_STRATEGIES:

        errors.append(
            f"Unsupported intervention strategy: {strategy}"
        )

    return errors


# ============================================================
# DECISION VALIDATION
# ============================================================

def validate_decision(
    decision: InterventionDecision,
) -> List[str]:
    """
    Validate that the Intervention Engine produced an
    executable recommendation.
    """

    errors: List[str] = []

    if decision.decision_status != "RECOMMEND":

        errors.append(
            "Intervention decision is not executable."
        )

    if not decision.safety_checks_passed:

        errors.append(
            "Intervention did not pass safety validation."
        )

    errors.extend(
        validate_strategy(
            decision.selected_strategy
        )
    )

    if not decision.station_id:

        errors.append(
            "Station ID is required."
        )

    if decision.decision_score < 0:

        errors.append(
            "Decision score cannot be negative."
        )

    return errors


# ============================================================
# EXECUTION REQUEST CREATION
# ============================================================

def create_execution_request(
    decision: InterventionDecision,
    execution_id: str,
) -> ExecutionRequest:
    """
    Convert an approved intervention decision into an
    execution request.
    """

    errors = validate_decision(
        decision
    )

    if errors:

        raise ValueError(
            "Cannot create execution request: "
            + " | ".join(errors)
        )

    return ExecutionRequest(
        execution_id=execution_id,
        station_id=decision.station_id,
        strategy=decision.selected_strategy,
        decision_score=decision.decision_score,
    )


# ============================================================
# IDEMPOTENCY CHECK
# ============================================================

def check_idempotency(
    execution_id: str,
) -> Optional[ExecutionResult]:
    """
    Check whether an execution with the same ID has already
    been processed.
    """

    return _EXECUTED_INTERVENTIONS.get(
        execution_id
    )


# ============================================================
# BUILD UPDATED STATION
# ============================================================

def build_updated_station(
    state: StationState,
    capacity: float,
    load: float,
    routes: int,
) -> StationState:
    """
    Construct a new StationState with the correct status.

    IMPORTANT:
        StationState is frozen, so status must be supplied
        during construction rather than assigned afterwards.
    """

    updated_state = StationState(
        station_id=state.station_id,
        city=state.city,
        region=state.region,
        capacity=capacity,
        current_load=load,
        active_routes=routes,
    )

    calculated_status = determine_station_status(
        updated_state
    )

    return StationState(
        station_id=updated_state.station_id,
        city=updated_state.city,
        region=updated_state.region,
        capacity=updated_state.capacity,
        current_load=updated_state.current_load,
        active_routes=updated_state.active_routes,
        status=calculated_status,
    )


# ============================================================
# APPLY HYBRID RESPONSE
# ============================================================

def apply_hybrid_response(
    state: StationState,
) -> StationState:
    """
    Apply the HYBRID_RESPONSE transition.

    Prototype policy:

        +10% capacity
        -10% load
        -10% active routes
    """

    new_capacity = (
        state.capacity * 1.10
    )

    new_load = (
        state.current_load * 0.90
    )

    new_routes = int(
        round(
            state.active_routes * 0.90
        )
    )

    return build_updated_station(
        state,
        new_capacity,
        new_load,
        new_routes,
    )


# ============================================================
# APPLY ROUTE REBALANCE
# ============================================================

def apply_route_rebalance(
    state: StationState,
) -> StationState:
    """
    Apply the ROUTE_REBALANCE transition.

    Prototype policy:

        capacity unchanged
        -15% load
        -15% active routes
    """

    new_capacity = state.capacity

    new_load = (
        state.current_load * 0.85
    )

    new_routes = int(
        round(
            state.active_routes * 0.85
        )
    )

    return build_updated_station(
        state,
        new_capacity,
        new_load,
        new_routes,
    )


# ============================================================
# APPLY CAPACITY SHIFT
# ============================================================

def apply_capacity_shift(
    state: StationState,
) -> StationState:
    """
    Apply the CAPACITY_SHIFT transition.

    Prototype policy:

        +15% capacity
        load unchanged
        routes unchanged
    """

    new_capacity = (
        state.capacity * 1.15
    )

    new_load = state.current_load

    new_routes = state.active_routes

    return build_updated_station(
        state,
        new_capacity,
        new_load,
        new_routes,
    )


# ============================================================
# APPLY INTERVENTION
# ============================================================

def apply_intervention(
    state: StationState,
    strategy: str,
) -> StationState:
    """
    Apply a supported intervention strategy.

    Returns a NEW StationState.
    """

    if strategy == "HYBRID_RESPONSE":

        return apply_hybrid_response(
            state
        )

    if strategy == "ROUTE_REBALANCE":

        return apply_route_rebalance(
            state
        )

    if strategy == "CAPACITY_SHIFT":

        return apply_capacity_shift(
            state
        )

    raise ValueError(
        f"Unsupported intervention strategy: {strategy}"
    )


# ============================================================
# BUILD STATE TRANSITION
# ============================================================

def build_state_transition(
    previous: StationState,
    updated: StationState,
) -> StateTransition:
    """
    Create an auditable before-and-after state transition.
    """

    return StateTransition(
        station_id=previous.station_id,

        previous_capacity=round(
            previous.capacity,
            2,
        ),

        new_capacity=round(
            updated.capacity,
            2,
        ),

        previous_load=round(
            previous.current_load,
            2,
        ),

        new_load=round(
            updated.current_load,
            2,
        ),

        previous_routes=previous.active_routes,

        new_routes=updated.active_routes,

        previous_utilization=round(
            calculate_utilization(
                previous
            ),
            2,
        ),

        new_utilization=round(
            calculate_utilization(
                updated
            ),
            2,
        ),

        previous_status=(
            previous.status.value
        ),

        new_status=(
            updated.status.value
        ),
    )


# ============================================================
# BUILD AUDIT RECORD
# ============================================================

def build_audit_record(
    request: ExecutionRequest,
    result: ExecutionResult,
) -> Dict:
    """
    Build a structured audit record.
    """

    transition = result.state_transition

    return {
        "execution_id": request.execution_id,

        "station_id": request.station_id,

        "strategy": request.strategy,

        "decision_score": request.decision_score,

        "status": result.status,

        "executed_at": result.executed_at,

        "requested_by": request.requested_by,

        "state_transition": {
            "previous_capacity": (
                transition.previous_capacity
                if transition
                else None
            ),

            "new_capacity": (
                transition.new_capacity
                if transition
                else None
            ),

            "previous_load": (
                transition.previous_load
                if transition
                else None
            ),

            "new_load": (
                transition.new_load
                if transition
                else None
            ),

            "previous_routes": (
                transition.previous_routes
                if transition
                else None
            ),

            "new_routes": (
                transition.new_routes
                if transition
                else None
            ),

            "previous_utilization": (
                transition.previous_utilization
                if transition
                else None
            ),

            "new_utilization": (
                transition.new_utilization
                if transition
                else None
            ),

            "previous_status": (
                transition.previous_status
                if transition
                else None
            ),

            "new_status": (
                transition.new_status
                if transition
                else None
            ),
        },

        "validation_errors": (
            result.validation_errors
        ),
    }


# ============================================================
# EXECUTE INTERVENTION
# ============================================================

def execute_intervention(
    state: StationState,
    decision: InterventionDecision,
    execution_id: str,
) -> ExecutionResult:
    """
    Execute an approved intervention.

    Execution sequence:

        1. Validate decision
        2. Check idempotency
        3. Create execution request
        4. Apply state transition
        5. Build audit record
        6. Store result
        7. Return result
    """

    # --------------------------------------------------------
    # STEP 1 — VALIDATION
    # --------------------------------------------------------

    validation_errors = validate_decision(
        decision
    )

    if validation_errors:

        timestamp = datetime.now(
            timezone.utc
        ).isoformat()

        return ExecutionResult(
            execution_id=execution_id,

            station_id=decision.station_id,

            strategy=decision.selected_strategy,

            status=ExecutionStatus.REJECTED,

            executed_at=timestamp,

            state_transition=None,

            validation_errors=validation_errors,

            audit_record={},
        )

    # --------------------------------------------------------
    # STEP 2 — IDEMPOTENCY
    # --------------------------------------------------------

    existing_result = check_idempotency(
        execution_id
    )

    if existing_result is not None:

        return ExecutionResult(
            execution_id=existing_result.execution_id,

            station_id=existing_result.station_id,

            strategy=existing_result.strategy,

            status=ExecutionStatus.ALREADY_EXECUTED,

            executed_at=existing_result.executed_at,

            state_transition=(
                existing_result.state_transition
            ),

            validation_errors=[],

            audit_record=(
                existing_result.audit_record
            ),
        )

    # --------------------------------------------------------
    # STEP 3 — CREATE REQUEST
    # --------------------------------------------------------

    request = create_execution_request(
        decision,
        execution_id,
    )

    timestamp = datetime.now(
        timezone.utc
    ).isoformat()

    # --------------------------------------------------------
    # STEP 4 — APPLY STATE TRANSITION
    # --------------------------------------------------------

    updated_state = apply_intervention(
        state,
        request.strategy,
    )

    # --------------------------------------------------------
    # STEP 5 — BUILD TRANSITION
    # --------------------------------------------------------

    transition = build_state_transition(
        state,
        updated_state,
    )

    # --------------------------------------------------------
    # STEP 6 — BUILD RESULT
    # --------------------------------------------------------

    result = ExecutionResult(
        execution_id=request.execution_id,

        station_id=request.station_id,

        strategy=request.strategy,

        status=ExecutionStatus.EXECUTED,

        executed_at=timestamp,

        state_transition=transition,

        validation_errors=[],

        audit_record={},
    )

    # --------------------------------------------------------
    # STEP 7 — BUILD AUDIT RECORD
    # --------------------------------------------------------

    result.audit_record = (
        build_audit_record(
            request,
            result,
        )
    )

    # --------------------------------------------------------
    # STEP 8 — STORE EXECUTION
    # --------------------------------------------------------

    _EXECUTED_INTERVENTIONS[
        execution_id
    ] = result

    return result


# ============================================================
# SERIALIZATION
# ============================================================

def execution_result_to_dict(
    result: ExecutionResult,
) -> Dict:
    """
    Convert an ExecutionResult into a JSON-compatible
    dictionary.
    """

    transition = result.state_transition

    return {
        "execution_id": result.execution_id,

        "station_id": result.station_id,

        "strategy": result.strategy,

        "status": result.status,

        "executed_at": result.executed_at,

        "state_transition": {
            "previous_capacity": (
                transition.previous_capacity
                if transition
                else None
            ),

            "new_capacity": (
                transition.new_capacity
                if transition
                else None
            ),

            "previous_load": (
                transition.previous_load
                if transition
                else None
            ),

            "new_load": (
                transition.new_load
                if transition
                else None
            ),

            "previous_routes": (
                transition.previous_routes
                if transition
                else None
            ),

            "new_routes": (
                transition.new_routes
                if transition
                else None
            ),

            "previous_utilization": (
                transition.previous_utilization
                if transition
                else None
            ),

            "new_utilization": (
                transition.new_utilization
                if transition
                else None
            ),

            "previous_status": (
                transition.previous_status
                if transition
                else None
            ),

            "new_status": (
                transition.new_status
                if transition
                else None
            ),
        },

        "validation_errors": (
            result.validation_errors
        ),

        "audit_record": (
            result.audit_record
        ),
    }


# ============================================================
# LOCAL TEST
# ============================================================

if __name__ == "__main__":

    print("=" * 70)
    print("GUARDIAN OS — EXECUTION ENGINE TEST")
    print("=" * 70)

    # --------------------------------------------------------
    # SYNTHETIC STATION
    # --------------------------------------------------------

    station = StationState(
        station_id="CHN-017",
        city="Chennai",
        region="Tamil Nadu",
        capacity=8000,
        current_load=8200,
        active_routes=384,
    )

    # --------------------------------------------------------
    # GENERATE INTERVENTION DECISION
    # --------------------------------------------------------

    decision = evaluate_interventions(
        station
    )

    print("\nINTERVENTION DECISION")
    print("-" * 70)

    print(
        f"Strategy: "
        f"{decision.selected_strategy}"
    )

    print(
        f"Decision Score: "
        f"{decision.decision_score:.2f}"
    )

    print(
        f"Status: "
        f"{decision.decision_status}"
    )

    print(
        f"Safety Checks: "
        f"{'PASSED' if decision.safety_checks_passed else 'FAILED'}"
    )

    # --------------------------------------------------------
    # EXECUTE INTERVENTION
    # --------------------------------------------------------

    result = execute_intervention(
        state=station,
        decision=decision,
        execution_id="EXEC-0001",
    )

    print("\nEXECUTION RESULT")
    print("-" * 70)

    print(
        f"Execution ID: "
        f"{result.execution_id}"
    )

    print(
        f"Station: "
        f"{result.station_id}"
    )

    print(
        f"Strategy: "
        f"{result.strategy}"
    )

    print(
        f"Status: "
        f"{result.status}"
    )

    # --------------------------------------------------------
    # STATE TRANSITION
    # --------------------------------------------------------

    transition = result.state_transition

    if transition:

        print("\nSTATE TRANSITION")
        print("-" * 70)

        print(
            f"Capacity: "
            f"{transition.previous_capacity:.2f}"
            f" → "
            f"{transition.new_capacity:.2f}"
        )

        print(
            f"Load: "
            f"{transition.previous_load:.2f}"
            f" → "
            f"{transition.new_load:.2f}"
        )

        print(
            f"Routes: "
            f"{transition.previous_routes}"
            f" → "
            f"{transition.new_routes}"
        )

        print(
            f"Utilization: "
            f"{transition.previous_utilization:.2f}%"
            f" → "
            f"{transition.new_utilization:.2f}%"
        )

        print(
            f"Status: "
            f"{transition.previous_status}"
            f" → "
            f"{transition.new_status}"
        )

    # --------------------------------------------------------
    # IDEMPOTENCY TEST
    # --------------------------------------------------------

    duplicate = execute_intervention(
        state=station,
        decision=decision,
        execution_id="EXEC-0001",
    )

    print("\nIDEMPOTENCY TEST")
    print("-" * 70)

    print(
        f"Second execution status: "
        f"{duplicate.status}"
    )

    # --------------------------------------------------------
    # AUDIT RECORD
    # --------------------------------------------------------

    print("\nAUDIT RECORD")
    print("-" * 70)

    for key, value in result.audit_record.items():

        print(
            f"{key}: {value}"
        )

    print("\n" + "=" * 70)
    print("EXECUTION ENGINE TEST COMPLETE")
    print("=" * 70)