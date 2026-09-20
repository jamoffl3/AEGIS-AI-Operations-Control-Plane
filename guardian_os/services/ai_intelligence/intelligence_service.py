"""
GUARDIAN OS — AI Intelligence Service

Orchestrates:
    OperationalContext
        ↓
    Prompt Builder
        ↓
    Bedrock Client
        ↓
    IntelligenceResult

This service is the single entry point for Guardian OS AI intelligence.

It does NOT:
- calculate operational risk
- run simulations
- select interventions
- execute interventions

Those responsibilities remain in the deterministic engines.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from services.ai_intelligence.bedrock_client import (
    BedrockClient,
    BedrockResponse,
    create_bedrock_client,
)
from services.ai_intelligence.intelligence_models import (
    AIExplanation,
    AIRecommendation,
    IntelligenceResult,
    OperationalContext,
)
from services.ai_intelligence.prompt_builder import (
    build_explanation_prompt,
    build_recommendation_prompt,
    validate_prompt,
)


@dataclass(frozen=True)
class IntelligenceServiceConfig:
    """
    Configuration for the AI intelligence service.
    """

    model_id: str = "amazon.nova-lite-v1:0"
    region_name: str = "us-east-1"
    max_tokens: int = 1000
    temperature: float = 0.2
    mock_mode: bool = True


class IntelligenceService:
    """
    Guardian OS AI intelligence orchestration service.
    """

    def __init__(
        self,
        client: Optional[BedrockClient] = None,
        config: Optional[IntelligenceServiceConfig] = None,
    ) -> None:

        self.config = config or IntelligenceServiceConfig()

        self.client = client or create_bedrock_client(
            model_id=self.config.model_id,
            region_name=self.config.region_name,
            mock_mode=self.config.mock_mode,
        )

    def analyze(
        self,
        context: OperationalContext,
    ) -> IntelligenceResult:
        """
        Generate both an explanation and recommendation.

        The two AI calls use the same deterministic operational context
        but have different purposes.
        """

        self._validate_context(context)

        explanation_prompt = build_explanation_prompt(context)
        recommendation_prompt = build_recommendation_prompt(context)

        validate_prompt(explanation_prompt)
        validate_prompt(recommendation_prompt)

        explanation_response = self.client.invoke(
            explanation_prompt,
            max_tokens=self.config.max_tokens,
            temperature=self.config.temperature,
        )

        recommendation_response = self.client.invoke(
            recommendation_prompt,
            max_tokens=self.config.max_tokens,
            temperature=self.config.temperature,
        )

        explanation = self._build_explanation(
            context,
            explanation_response,
        )

        recommendation = self._build_recommendation(
            context,
            recommendation_response,
        )

        return IntelligenceResult(
            station_id=context.station_id,
            explanation=explanation,
            recommendation=recommendation,
            generated_by=(
                "GUARDIAN_MOCK_MODEL"
                if self.config.mock_mode
                else "AMAZON_BEDROCK"
            ),
            model_id=(
                None
                if self.config.mock_mode
                else self.config.model_id
            ),
            grounded_in_deterministic_data=True,
            metadata={
                "event_type": context.event_type,
                "risk_score": context.risk_score,
                "risk_level": context.risk_level,
                "selected_strategy": context.selected_strategy,
                "execution_status": context.execution_status,
                "outcome_status": context.outcome_status,
                "synthetic_data": True,
                "mock_mode": self.config.mock_mode,
            },
        )

    def explain(
        self,
        context: OperationalContext,
    ) -> AIExplanation:
        """
        Generate only an operational explanation.
        """

        self._validate_context(context)

        prompt = build_explanation_prompt(context)
        validate_prompt(prompt)

        response = self.client.invoke(
            prompt,
            max_tokens=self.config.max_tokens,
            temperature=self.config.temperature,
        )

        return self._build_explanation(
            context,
            response,
        )

    def recommend(
        self,
        context: OperationalContext,
    ) -> AIRecommendation:
        """
        Generate only an operational recommendation.
        """

        self._validate_context(context)

        prompt = build_recommendation_prompt(context)
        validate_prompt(prompt)

        response = self.client.invoke(
            prompt,
            max_tokens=self.config.max_tokens,
            temperature=self.config.temperature,
        )

        return self._build_recommendation(
            context,
            response,
        )

    @staticmethod
    def _validate_context(
        context: OperationalContext,
    ) -> None:

        if not isinstance(context, OperationalContext):
            raise TypeError(
                "context must be an OperationalContext instance."
            )

        if not context.station_id:
            raise ValueError(
                "OperationalContext must contain a station_id."
            )

        if context.risk_score < 0 or context.risk_score > 100:
            raise ValueError(
                "risk_score must be between 0 and 100."
            )

    @staticmethod
    def _build_explanation(
        context: OperationalContext,
        response: BedrockResponse,
    ) -> AIExplanation:
        """
        Convert raw model output into the Guardian OS explanation contract.

        In production, this can later be replaced with structured model
        output parsing without changing the rest of the application.
        """

        return AIExplanation(
            summary=response.text,
            key_risks=[
                driver.description
                for driver in context.risk_drivers
            ],
            operational_implications=[
                (
                    f"{scenario.strategy}: projected risk "
                    f"{scenario.projected_risk:.2f}, "
                    f"projected utilization "
                    f"{scenario.projected_utilization:.2f}%."
                )
                for scenario in context.scenarios
            ],
            confidence_note=(
                "AI explanation is grounded in deterministic Guardian OS "
                "outputs. Numeric risk and simulation results are produced "
                "by deterministic engines."
            ),
        )

    @staticmethod
    def _build_recommendation(
        context: OperationalContext,
        response: BedrockResponse,
    ) -> AIRecommendation:
        """
        Convert raw model output into the Guardian OS recommendation
        contract.
        """

        selected_strategy = (
            context.selected_strategy
            or "NO_STRATEGY_SELECTED"
        )

        expected_effect = (
            f"Selected strategy: {selected_strategy}. "
            f"Decision score: "
            f"{context.decision_score:.2f}."
            if context.decision_score is not None
            else "No deterministic intervention score is available."
        )

        return AIRecommendation(
            recommended_action=response.text,
            reasoning=(
                "Recommendation is grounded in the deterministic "
                "Guardian OS intervention analysis."
            ),
            expected_effect=expected_effect,
            constraints=[
                "Prototype uses synthetic/simulated operational data.",
                "Deterministic risk and intervention outputs remain "
                "the source of truth.",
                "Production execution requires appropriate human "
                "authorization and operational controls.",
            ],
            requires_human_review=True,
        )


def create_intelligence_service(
    *,
    mock_mode: bool = True,
    model_id: str = "amazon.nova-lite-v1:0",
    region_name: str = "us-east-1",
) -> IntelligenceService:
    """
    Factory for creating a configured Guardian OS intelligence service.
    """

    config = IntelligenceServiceConfig(
        model_id=model_id,
        region_name=region_name,
        mock_mode=mock_mode,
    )

    return IntelligenceService(
        config=config,
    )


if __name__ == "__main__":

    from services.ai_intelligence.intelligence_models import (
        RiskDriver,
        ScenarioSummary,
    )

    print("=" * 70)
    print("GUARDIAN OS — AI INTELLIGENCE SERVICE TEST")
    print("=" * 70)

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
                description=(
                    "Station utilization exceeds nominal capacity."
                ),
            ),
            RiskDriver(
                name="Capacity Overload",
                value=2.50,
                contribution=6.25,
                description=(
                    "Current load exceeds available capacity."
                ),
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

    service = create_intelligence_service(
        mock_mode=True,
    )

    print("\nSERVICE CREATED")
    print("-" * 70)
    print(f"Service type: {type(service).__name__}")
    print(f"Mock mode: {service.config.mock_mode}")
    print(f"Model: {service.config.model_id}")

    print("\nFULL ANALYSIS")
    print("-" * 70)

    result = service.analyze(context)

    print(f"Station: {result.station_id}")
    print(f"Generated by: {result.generated_by}")
    print(
        f"Grounded in deterministic data: "
        f"{result.grounded_in_deterministic_data}"
    )

    print("\nEXPLANATION")
    print("-" * 70)
    print(result.explanation.summary)

    print("\nKEY RISKS")
    print("-" * 70)

    for risk in result.explanation.key_risks:
        print(f"- {risk}")

    print("\nRECOMMENDATION")
    print("-" * 70)
    print(result.recommendation.recommended_action)

    print("\nCONSTRAINTS")
    print("-" * 70)

    for constraint in result.recommendation.constraints:
        print(f"- {constraint}")

    print("\nHUMAN REVIEW")
    print("-" * 70)
    print(
        f"Required: "
        f"{result.recommendation.requires_human_review}"
    )

    print("\nSEPARATE METHOD TESTS")
    print("-" * 70)

    explanation = service.explain(context)
    recommendation = service.recommend(context)

    print(
        f"Explain method: "
        f"{isinstance(explanation, AIExplanation)}"
    )

    print(
        f"Recommend method: "
        f"{isinstance(recommendation, AIRecommendation)}"
    )

    print("\nARCHITECTURE CHECK")
    print("-" * 70)
    print("Risk calculation: OUTSIDE AI")
    print("Simulation: OUTSIDE AI")
    print("Intervention selection: OUTSIDE AI")
    print("Execution: OUTSIDE AI")
    print("AI orchestration: INTELLIGENCE SERVICE")
    print("Bedrock boundary: BEDROCK CLIENT")

    print("\n" + "=" * 70)
    print("AI INTELLIGENCE SERVICE TEST COMPLETE")
    print("=" * 70)