import json
from pathlib import Path
from typing import Any, Dict, List

from services.event_ingestion.event_models import (
    OperationalEvent,
    event_from_dict,
)


# =========================================================
# GUARDIAN OS — EVENT INGESTION SERVICE
# =========================================================
#
# Responsibility:
#
#   Raw event payload
#          ↓
#   Parse / validate
#          ↓
#   OperationalEvent
#          ↓
#   Normalized event context
#
# This layer does NOT calculate risk.
# This layer does NOT choose interventions.
# This layer does NOT call an LLM.
#
# It establishes a clean boundary between external event
# data and the Guardian control plane.
# =========================================================


PROJECT_ROOT = Path(__file__).resolve().parents[2]

SIMULATOR_DIR = (
    PROJECT_ROOT / "simulator"
)

EVENTS_FILE = (
    SIMULATOR_DIR / "events.json"
)


# =========================================================
# RAW DATA LOADING
# =========================================================


def load_json(
    file_path: Path,
) -> Any:
    """
    Load JSON data from disk.

    The simulator is our BUILD IT input source.
    """

    if not file_path.exists():
        raise FileNotFoundError(
            f"Data file not found: {file_path}"
        )

    with file_path.open(
        "r",
        encoding="utf-8",
    ) as file:

        return json.load(file)


# =========================================================
# EVENT NORMALIZATION
# =========================================================


def normalize_event(
    payload: Dict[str, Any],
) -> OperationalEvent:
    """
    Convert a raw event payload into Guardian's canonical
    OperationalEvent model.

    All validation is delegated to event_from_dict().
    """

    return event_from_dict(
        payload
    )


# =========================================================
# BATCH INGESTION
# =========================================================


def ingest_events(
    payload: Any,
) -> List[OperationalEvent]:
    """
    Ingest one event or a batch of events.

    Accepted input:

        {
            ...event...
        }

    or:

        [
            {...event...},
            {...event...}
        ]
    """

    if isinstance(
        payload,
        dict,
    ):

        payloads = [payload]

    elif isinstance(
        payload,
        list,
    ):

        payloads = payload

    else:

        raise TypeError(
            "Event input must be a dictionary "
            "or a list of dictionaries."
        )

    events = []

    for index, item in enumerate(
        payloads
    ):

        if not isinstance(
            item,
            dict,
        ):

            raise TypeError(
                f"Event at index {index} "
                "must be a dictionary."
            )

        event = normalize_event(
            item
        )

        events.append(
            event
        )

    return events


# =========================================================
# EVENT CONTEXT
# =========================================================


def build_event_context(
    event: OperationalEvent,
) -> Dict[str, Any]:
    """
    Produce the normalized operational context consumed by
    downstream Guardian services.

    This deliberately contains structured facts rather than
    calculated risk or AI-generated conclusions.
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
            "city": (
                event.station.city
            ),
            "region": (
                event.station.region
            ),
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

        "metadata": (
            event.metadata or {}
        ),
    }


# =========================================================
# SINGLE EVENT PROCESSING
# =========================================================


def process_event(
    payload: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Validate and normalize a single operational event.

    Returns a downstream-ready event context.
    """

    event = normalize_event(
        payload
    )

    return build_event_context(
        event
    )


# =========================================================
# LOCAL SERVICE TEST
# =========================================================


if __name__ == "__main__":

    raw_events = load_json(
        EVENTS_FILE
    )

    events = ingest_events(
        raw_events
    )

    print()
    print("=" * 75)
    print("                         GUARDIAN OS")
    print("                    EVENT INGESTION")
    print("=" * 75)

    print()
    print(
        f"Events received   : "
        f"{len(events)}"
    )

    print(
        f"Events validated  : "
        f"{len(events)}"
    )

    for event in events:

        context = build_event_context(
            event
        )

        print()
        print("EVENT")
        print("-" * 75)

        print(
            f"Event ID          : "
            f"{context['event_id']}"
        )

        print(
            f"Event Type        : "
            f"{context['event_type']}"
        )

        print(
            f"Source            : "
            f"{context['source']}"
        )

        print(
            f"Station           : "
            f"{context['station']['station_id']}"
        )

        print(
            f"City              : "
            f"{context['station']['city']}"
        )

        print(
            f"Severity          : "
            f"{context['impact']['severity']}"
        )

        print(
            f"Capacity Change   : "
            f"{context['impact']['capacity_change_percent']}%"
        )

    print()
    print("=" * 75)
    print("                 INGESTION TEST PASSED")
    print("=" * 75)