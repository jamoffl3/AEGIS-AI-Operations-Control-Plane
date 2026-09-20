"""
GUARDIAN OS
Simulation Engine

Purpose:
    Simulate counterfactual operational interventions without
    mutating the real station state.

Core flow:

    Current State
         ↓
    Simulate Strategies
         ↓
    Project Capacity / Load / Routes
         ↓
    Calculate Projected Utilization
         ↓
    Calculate Projected Risk
         ↓
    Compare Scenarios

Important:
    - All calculations are deterministic.
    - Simulation does NOT mutate the original station state.
    - Results are synthetic prototype projections.
    - No LLM is used for numerical calculations.
"""

from dataclasses import dataclass
from typing import List

from services.risk_engine.station_models import (
    StationState,
    calculate_utilization,
)


# ============================================================
# PROTOTYPE SIMULATION POLICY
# ============================================================

# Route rebalance:
# Move 15% of active routes to other network capacity.
ROUTE_REBALANCE_PERCENT = 0.15

# Hybrid response:
# Move 10% of routes while also recovering some capacity.
HYBRID_ROUTE_REBALANCE_PERCENT = 0.10

# Capacity shift:
# Recover 15% of the lost/available capacity.
CAPACITY_SHIFT_PERCENT = 0.15

# Hybrid capacity recovery.
HYBRID_CAPACITY_RECOVERY_PERCENT = 0.10

# Assumed load reduction produced by route rebalancing.
ROUTE_REBALANCE_LOAD_REDUCTION = 0.15

# Assumed load reduction produced by hybrid intervention.
HYBRID_LOAD_REDUCTION = 0.10


# ============================================================
# PROJECTED RISK POLICY
# ============================================================

# These weights are prototype policy parameters.
# They are NOT validated Amazon operational economics.

UTILIZATION_RISK_WEIGHT = 0.55
OVERLOAD_RISK_WEIGHT = 0.25
ROUTE_PRESSURE_WEIGHT = 0.20

ROUTE_REFERENCE = 500


# ============================================================
# SCENARIO RESULT
# ============================================================

@dataclass
class ScenarioResult:
    """
    Represents the projected outcome of one intervention strategy.
    """

    strategy: str

    projected_capacity: float
    projected_load: float
    projected_routes: int

    projected_utilization: float
    projected_risk: float

    capacity_recovered: float
    routes_moved: int

    status: str


# ============================================================
# BASIC CALCULATIONS
# ============================================================

def calculate_utilization(
    capacity: float,
    current_load: float,
) -> float:
    """
    Calculate station utilization as a percentage.

    Example:
        capacity = 8000
        load = 8200

        utilization = 102.5%
    """

    if capacity <= 0:
        raise ValueError("Capacity must be greater than zero.")

    return (current_load / capacity) * 100


def calculate_overload_percentage(
    utilization: float,
) -> float:
    """
    Calculate how far utilization is above 100%.

    Example:
        102.5% utilization → 2.5% overload
    """

    return max(0.0, utilization - 100.0)


# ============================================================
# PROJECTED RISK
# ============================================================

def calculate_projected_risk(
    capacity: float,
    current_load: float,
    active_routes: int,
) -> float:
    """
    Calculate projected operational risk for a simulated scenario.

    This is intentionally deterministic so that scenario comparisons
    are reproducible and auditable.

    Risk components:

        1. Utilization pressure
        2. Capacity overload
        3. Route pressure

    The result is normalized to 0–100.
    """

    utilization = calculate_utilization(
        capacity,
        current_load,
    )

    # --------------------------------------------------------
    # Utilization component
    # --------------------------------------------------------

    if utilization <= 70:
        utilization_risk = 0.0

    elif utilization <= 100:
        utilization_risk = (
            (utilization - 70) / 30
        ) * 100

    else:
        # Once capacity is exceeded, utilization pressure
        # remains at maximum.
        utilization_risk = 100.0

    # --------------------------------------------------------
    # Overload component
    # --------------------------------------------------------

    overload = calculate_overload_percentage(utilization)

    if overload <= 0:
        overload_risk = 0.0

    elif overload >= 10:
        overload_risk = 100.0

    else:
        overload_risk = (overload / 10) * 100

    # --------------------------------------------------------
    # Route pressure component
    # --------------------------------------------------------

    route_pressure = min(
        active_routes / ROUTE_REFERENCE,
        1.0,
    ) * 100

    # --------------------------------------------------------
    # Weighted risk
    # --------------------------------------------------------

    projected_risk = (
        utilization_risk * UTILIZATION_RISK_WEIGHT
        + overload_risk * OVERLOAD_RISK_WEIGHT
        + route_pressure * ROUTE_PRESSURE_WEIGHT
    )

    return round(
        max(0.0, min(projected_risk, 100.0)),
        2,
    )


# ============================================================
# STATUS CLASSIFICATION
# ============================================================

def determine_status(
    utilization: float,
) -> str:
    """
    Determine the projected station status.
    """

    if utilization > 110:
        return "CRITICAL"

    if utilization > 100:
        return "OVER_CAPACITY"

    if utilization > 90:
        return "DEGRADED"

    return "RECOVERED"


# ============================================================
# ROUTE REBALANCE
# ============================================================

def simulate_route_rebalance(
    state: StationState,
) -> ScenarioResult:
    """
    Simulate moving a portion of active routes away from the
    affected station.

    Prototype assumptions:
        - 15% of routes are moved.
        - Load decreases proportionally.
        - Station capacity remains unchanged.
    """

    routes_moved = max(
        1,
        round(
            state.active_routes
            * ROUTE_REBALANCE_PERCENT
        ),
    )

    projected_routes = max(
        0,
        state.active_routes - routes_moved,
    )

    projected_load = max(
        0.0,
        state.current_load
        * (1 - ROUTE_REBALANCE_LOAD_REDUCTION),
    )

    projected_capacity = state.capacity

    projected_utilization = calculate_utilization(
        projected_capacity,
        projected_load,
    )

    projected_risk = calculate_projected_risk(
        projected_capacity,
        projected_load,
        projected_routes,
    )

    status = determine_status(
        projected_utilization,
    )

    return ScenarioResult(
        strategy="ROUTE_REBALANCE",

        projected_capacity=round(
            projected_capacity,
            2,
        ),

        projected_load=round(
            projected_load,
            2,
        ),

        projected_routes=projected_routes,

        projected_utilization=round(
            projected_utilization,
            2,
        ),

        projected_risk=projected_risk,

        capacity_recovered=0.0,

        routes_moved=routes_moved,

        status=status,
    )


# ============================================================
# CAPACITY SHIFT
# ============================================================

def simulate_capacity_shift(
    state: StationState,
) -> ScenarioResult:
    """
    Simulate shifting additional capacity into the affected station.

    Prototype assumption:
        - Station receives 15% additional effective capacity.
        - Load remains unchanged.
        - Active routes remain unchanged.
    """

    capacity_recovered = (
        state.capacity
        * CAPACITY_SHIFT_PERCENT
    )

    projected_capacity = (
        state.capacity
        + capacity_recovered
    )

    projected_load = state.current_load

    projected_routes = state.active_routes

    projected_utilization = calculate_utilization(
        projected_capacity,
        projected_load,
    )

    projected_risk = calculate_projected_risk(
        projected_capacity,
        projected_load,
        projected_routes,
    )

    status = determine_status(
        projected_utilization,
    )

    return ScenarioResult(
        strategy="CAPACITY_SHIFT",

        projected_capacity=round(
            projected_capacity,
            2,
        ),

        projected_load=round(
            projected_load,
            2,
        ),

        projected_routes=projected_routes,

        projected_utilization=round(
            projected_utilization,
            2,
        ),

        projected_risk=projected_risk,

        capacity_recovered=round(
            capacity_recovered,
            2,
        ),

        routes_moved=0,

        status=status,
    )


# ============================================================
# HYBRID RESPONSE
# ============================================================

def simulate_hybrid(
    state: StationState,
) -> ScenarioResult:
    """
    Simulate a combined intervention:

        Capacity recovery
        +
        Route redistribution
        +
        Load reduction

    This represents a more complex counterfactual response.
    """

    capacity_recovered = (
        state.capacity
        * HYBRID_CAPACITY_RECOVERY_PERCENT
    )

    projected_capacity = (
        state.capacity
        + capacity_recovered
    )

    routes_moved = max(
        1,
        round(
            state.active_routes
            * HYBRID_ROUTE_REBALANCE_PERCENT
        ),
    )

    projected_routes = max(
        0,
        state.active_routes - routes_moved,
    )

    projected_load = max(
        0.0,
        state.current_load
        * (1 - HYBRID_LOAD_REDUCTION),
    )

    projected_utilization = calculate_utilization(
        projected_capacity,
        projected_load,
    )

    projected_risk = calculate_projected_risk(
        projected_capacity,
        projected_load,
        projected_routes,
    )

    status = determine_status(
        projected_utilization,
    )

    return ScenarioResult(
        strategy="HYBRID_RESPONSE",

        projected_capacity=round(
            projected_capacity,
            2,
        ),

        projected_load=round(
            projected_load,
            2,
        ),

        projected_routes=projected_routes,

        projected_utilization=round(
            projected_utilization,
            2,
        ),

        projected_risk=projected_risk,

        capacity_recovered=round(
            capacity_recovered,
            2,
        ),

        routes_moved=routes_moved,

        status=status,
    )


# ============================================================
# RUN ALL SCENARIOS
# ============================================================

def simulate_all(
    state: StationState,
) -> List[ScenarioResult]:
    """
    Run every currently supported intervention scenario.

    The original state is never modified.
    """

    return [
        simulate_hybrid(state),
        simulate_route_rebalance(state),
        simulate_capacity_shift(state),
    ]


# ============================================================
# REPORTING
# ============================================================

def scenario_to_dict(
    scenario: ScenarioResult,
) -> dict:
    """
    Convert a ScenarioResult into a serializable dictionary.
    """

    return {
        "strategy": scenario.strategy,
        "projected_capacity": scenario.projected_capacity,
        "projected_load": scenario.projected_load,
        "projected_routes": scenario.projected_routes,
        "projected_utilization": scenario.projected_utilization,
        "projected_risk": scenario.projected_risk,
        "capacity_recovered": scenario.capacity_recovered,
        "routes_moved": scenario.routes_moved,
        "status": scenario.status,
    }


def generate_simulation_report(
    state: StationState,
) -> dict:
    """
    Generate a complete simulation report for a station.
    """

    scenarios = simulate_all(state)

    return {
        "station_id": state.station_id,
        "baseline": {
            "capacity": state.capacity,
            "current_load": state.current_load,
            "active_routes": state.active_routes,
            "utilization": round(
                state.calculate_utilization(),
                2,
            ),
        },
        "scenarios": [
            scenario_to_dict(
                scenario
            )
            for scenario in scenarios
        ],
    }


# ============================================================
# LOCAL TEST
# ============================================================

if __name__ == "__main__":

    print("=" * 60)
    print("GUARDIAN OS — SIMULATION ENGINE TEST")
    print("=" * 60)

    # Synthetic station state.
    #
    # This represents a station after a simulated
    # 20% capacity shock.
    station = StationState(
        station_id="CHN-017",
        city="Chennai",
        region="Tamil Nadu",
        capacity=8000,
        current_load=8200,
        active_routes=384,
    )

    print("\nBASELINE")
    print("-" * 60)

    print(
        f"Station: {station.station_id}"
    )

    print(
        f"Capacity: {station.capacity}"
    )

    print(
        f"Load: {station.current_load}"
    )

    print(
        f"Routes: {station.active_routes}"
    )

    print(
        f"Utilization: "
        f"{calculate_utilization(station.capacity, station.current_load):.2f}%"
    )

    print("\nSIMULATED SCENARIOS")
    print("-" * 60)

    scenarios = simulate_all(station)

    for scenario in scenarios:

        print(
            f"\nStrategy: "
            f"{scenario.strategy}"
        )

        print(
            f"Projected Capacity: "
            f"{scenario.projected_capacity}"
        )

        print(
            f"Projected Load: "
            f"{scenario.projected_load}"
        )

        print(
            f"Projected Routes: "
            f"{scenario.projected_routes}"
        )

        print(
            f"Projected Utilization: "
            f"{scenario.projected_utilization:.2f}%"
        )

        print(
            f"Projected Risk: "
            f"{scenario.projected_risk:.2f}/100"
        )

        print(
            f"Capacity Recovered: "
            f"{scenario.capacity_recovered}"
        )

        print(
            f"Routes Moved: "
            f"{scenario.routes_moved}"
        )

        print(
            f"Status: "
            f"{scenario.status}"
        )

    print("\n" + "=" * 60)
    print("SIMULATION ENGINE TEST COMPLETE")
    print("=" * 60)