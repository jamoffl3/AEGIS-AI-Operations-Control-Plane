"""
GUARDIAN OS — AI Intelligence Prompt Builder

Builds grounded prompts for the AI explanation and recommendation layer.

The prompt builder does not calculate risk, simulate interventions,
or execute actions. It converts deterministic Guardian OS outputs
into structured context for an LLM.
"""

from services.ai_intelligence.intelligence_models import (
    OperationalContext,
)


SYSTEM_INSTRUCTION = """
You are Guardian OS Intelligence, an AI operations intelligence layer.

Your role is to explain deterministic operational analysis and translate
it into concise, auditable operational guidance.

You MUST follow these rules:

1. Treat all numeric values supplied in the context as authoritative
   deterministic outputs from Guardian OS.
2. Do not invent operational measurements, events, or outcomes.
3. Do not recalculate risk scores or simulation results.
4. Do not claim access to proprietary Amazon systems or private data.
5. The underlying prototype data is synthetic/simulated unless explicitly
   stated otherwise.
6. Distinguish observed state, simulated projections, executed actions,
   and measured outcomes.
7. If an intervention requires human authorization, clearly state that.
8. Do not present prototype policy parameters as validated production KPIs.
9. Base recommendations only on the supplied operational context.
10. Be concise, operational, and evidence-grounded.
"""


def build_context_prompt(context: OperationalContext) -> str:
    """
    Convert an OperationalContext into a grounded AI prompt.
    """

    risk_driver_lines = []

    for driver in context.risk_drivers:
        risk_driver_lines.append(
            f"- {driver.name}: value={driver.value:.2f}, "
            f"contribution={driver.contribution:.2f}. "
            f"{driver.description}"
        )

    scenario_lines = []

    for scenario in context.scenarios:
        scenario_lines.append(
            f"- {scenario.strategy}: "
            f"projected risk={scenario.projected_risk:.2f}, "
            f"projected utilization={scenario.projected_utilization:.2f}%, "
            f"projected capacity={scenario.projected_capacity:.2f}, "
            f"projected load={scenario.projected_load:.2f}, "
            f"projected routes={scenario.projected_routes}, "
            f"risk reduction={scenario.risk_reduction:.2f}, "
            f"utilization improvement="
            f"{scenario.utilization_improvement:.2f} percentage points, "
            f"decision score={scenario.decision_score:.2f}, "
            f"safety passed={scenario.safety_passed}"
        )

    risk_drivers = "\n".join(risk_driver_lines)
    scenarios = "\n".join(scenario_lines)

    decision_section = (
        f"Selected strategy: {context.selected_strategy}\n"
        f"Decision score: "
        f"{context.decision_score:.2f}"
        if context.selected_strategy is not None
        and context.decision_score is not None
        else "No intervention has been selected."
    )

    execution_section = (
        f"Execution status: {context.execution_status}"
        if context.execution_status is not None
        else "No intervention has been executed."
    )

    outcome_section = (
        f"Outcome status: {context.outcome_status}\n"
        f"Outcome effectiveness: "
        f"{context.outcome_effectiveness:.2f}/100"
        if context.outcome_status is not None
        and context.outcome_effectiveness is not None
        else "No measured intervention outcome is available."
    )

    prompt = f"""
{SYSTEM_INSTRUCTION}

Analyze the following Guardian OS operational context.

========================
OPERATIONAL EVENT
========================

Event type: {context.event_type}
Severity: {context.event_severity}
Description: {context.event_description}

========================
STATION STATE
========================

Station ID: {context.station_id}
City: {context.city}
Region: {context.region}

Capacity: {context.capacity:.2f}
Current load: {context.current_load:.2f}
Active routes: {context.active_routes}

Current utilization: {context.utilization:.2f}%
Current risk score: {context.risk_score:.2f}/100
Current risk level: {context.risk_level}

========================
RISK DRIVERS
========================

{risk_drivers}

========================
SIMULATED INTERVENTIONS
========================

{scenarios}

========================
DECISION
========================

{decision_section}

========================
EXECUTION
========================

{execution_section}

========================
OUTCOME
========================

{outcome_section}

========================
TASK
========================

Produce:

1. A concise operational explanation of the current situation.
2. The key risks and their evidence.
3. The operational implications of the simulated interventions.
4. A recommendation grounded strictly in the supplied evidence.
5. Any constraints or human-review requirements.

Do not invent missing information.
Do not change any numeric values.
Do not describe simulations as observed real-world results.
"""

    return prompt.strip()


def build_explanation_prompt(context: OperationalContext) -> str:
    """
    Build a prompt focused specifically on operational explanation.
    """

    return (
        build_context_prompt(context)
        + """

Focus the response on:
- what happened,
- why the station is currently at risk,
- which deterministic factors drive the risk,
- what the simulated scenarios imply,
- and what changed after execution, if an outcome is available.
"""
    )


def build_recommendation_prompt(context: OperationalContext) -> str:
    """
    Build a prompt focused specifically on intervention recommendation.
    """

    return (
        build_context_prompt(context)
        + """

Focus the response on:
- the intervention selected by the deterministic decision engine,
- the evidence supporting that selection,
- the expected operational effect,
- constraints,
- and whether human review is required before execution.
"""
    )


def validate_prompt(prompt: str) -> None:
    """
    Basic contract validation for generated prompts.
    """

    required_sections = [
        "OPERATIONAL EVENT",
        "STATION STATE",
        "RISK DRIVERS",
        "SIMULATED INTERVENTIONS",
        "DECISION",
        "EXECUTION",
        "OUTCOME",
    ]

    for section in required_sections:
        if section not in prompt:
            raise ValueError(
                f"Prompt validation failed: missing section '{section}'."
            )


if __name__ == "__main__":
    from services.ai_intelligence.intelligence_models import (
        RiskDriver,
        ScenarioSummary,
    )

    context = OperationalContext(
        station_id="CHN-017",
        city="Chennai",
        region="Tamil Nadu",
        event_type="STATION_CAPACITY_SHOCK",
        event_severity="HIGH",
        event_description="Synthetic station capacity disruption",
        capacity=8000,
        current_load=8200,
        active_routes=384,
        utilization=102.50,
        risk_score=72.77,
        risk_level="HIGH",
        risk_drivers=[
            RiskDriver(
                name="Utilization Pressure",
                value=102.50,
                contribution=40.00,
                description="Station utilization exceeds nominal capacity.",
            ),
            RiskDriver(
                name="Capacity Overload",
                value=2.50,
                contribution=6.25,
                description="Current load exceeds available capacity.",
            ),
        ],
        scenarios=[
            ScenarioSummary(
                strategy="HYBRID_RESPONSE",
                projected_risk=39.26,
                projected_utilization=83.86,
                projected_capacity=8800,
                projected_load=7380,
                projected_routes=346,
                risk_reduction=33.51,
                utilization_improvement=18.64,
                decision_score=46.56,
                safety_passed=True,
            ),
            ScenarioSummary(
                strategy="ROUTE_REBALANCE",
                projected_risk=44.44,
                projected_utilization=87.12,
                projected_capacity=8000,
                projected_load=6970,
                projected_routes=326,
                risk_reduction=28.33,
                utilization_improvement=15.38,
                decision_score=39.56,
                safety_passed=True,
            ),
            ScenarioSummary(
                strategy="CAPACITY_SHIFT",
                projected_risk=50.43,
                projected_utilization=89.13,
                projected_capacity=9200,
                projected_load=8200,
                projected_routes=384,
                risk_reduction=22.34,
                utilization_improvement=13.37,
                decision_score=32.57,
                safety_passed=True,
            ),
        ],
        selected_strategy="HYBRID_RESPONSE",
        decision_score=46.56,
        execution_status="EXECUTED",
        outcome_status="IMPROVED",
        outcome_effectiveness=51.52,
        metadata={
            "simulation": True,
            "data_source": "synthetic",
        },
    )

    prompt = build_context_prompt(context)

    validate_prompt(prompt)

    print("=" * 70)
    print("GUARDIAN OS — AI PROMPT BUILDER TEST")
    print("=" * 70)

    print("\nPROMPT VALIDATION")
    print("-" * 70)
    print("Required sections: PASSED")
    print("Grounding instructions: PRESENT")
    print("Synthetic-data constraint: PRESENT")

    print("\nPROMPT METADATA")
    print("-" * 70)
    print(f"Characters: {len(prompt)}")
    print(f"Lines: {len(prompt.splitlines())}")

    print("\nPROMPT PREVIEW")
    print("-" * 70)
    print(prompt[:1200])

    print("\n" + "=" * 70)
    print("AI PROMPT BUILDER TEST COMPLETE")
    print("=" * 70)