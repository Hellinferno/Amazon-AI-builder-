"""Conversation sessions.

The backend owns the context boundary: a session is bound to one business and
one dataset version, remembers the active what-if scenario for follow-up
questions, and stores the message history for the model. Sessions live in
memory; they are demo state, not records.
"""

import secrets
from dataclasses import dataclass, field
from datetime import date


@dataclass(frozen=True)
class ActiveScenario:
    invoice_id: str
    delay_days: int

    def as_dict(self) -> dict:
        return {"invoice_id": self.invoice_id, "delay_days": self.delay_days}


@dataclass
class Session:
    session_id: str
    business_id: str
    dataset_version: str
    horizon_end: date
    active_scenario: ActiveScenario | None = None
    messages: list[dict] = field(default_factory=list)  # Bedrock Converse message format
    turns: int = 0

    def as_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "business_id": self.business_id,
            "dataset_version": self.dataset_version,
            "horizon_end": self.horizon_end.isoformat(),
            "active_scenario": self.active_scenario.as_dict() if self.active_scenario else None,
            "turns": self.turns,
        }


MAX_HISTORY_MESSAGES = 20


class SessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}

    def create(self, business_id: str, dataset_version: str, horizon_end: date) -> Session:
        session_id = secrets.token_urlsafe(12)
        session = Session(session_id, business_id, dataset_version, horizon_end)
        self._sessions[session_id] = session
        return session

    def get(self, session_id: str | None) -> Session | None:
        if not session_id:
            return None
        return self._sessions.get(session_id)

    def rebind(self, session: Session, dataset_version: str, horizon_end: date) -> None:
        """The dataset changed under a session: drop scenario context and history."""
        session.dataset_version = dataset_version
        session.horizon_end = horizon_end
        session.active_scenario = None
        session.messages.clear()

    def clear(self) -> None:
        self._sessions.clear()

    def __len__(self) -> int:
        return len(self._sessions)


def trim_history(messages: list[dict], limit: int = MAX_HISTORY_MESSAGES) -> list[dict]:
    """Keep the most recent messages, never starting on an orphaned tool result."""
    if len(messages) <= limit:
        return messages
    trimmed = messages[-limit:]
    while trimmed and any("toolResult" in block for block in trimmed[0].get("content", [])):
        trimmed = trimmed[1:]
    return trimmed
