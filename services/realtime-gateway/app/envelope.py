from datetime import UTC, datetime
from uuid import uuid4


def envelope(event_type: str, sequence: int, data: dict) -> dict:
    return {
        "type": event_type,
        "event_id": str(uuid4()),
        "sequence": sequence,
        "occurred_at": datetime.now(UTC).isoformat(),
        "data": data,
    }
