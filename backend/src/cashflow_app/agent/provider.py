"""Model provider contract.

Messages use the Bedrock Converse block format so the live provider needs no
translation and the mock provider can read the same history:

    {"role": "user", "content": [{"text": "..."}]}
    {"role": "assistant", "content": [{"toolUse": {"toolUseId", "name", "input"}}]}
    {"role": "user", "content": [{"toolResult": {"toolUseId", "content": [{"json": {...}}], "status"}}]}
"""

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Protocol

from cashflow.models import Dataset

from ..session import ActiveScenario


class ProviderError(Exception):
    """The model service failed. ``code`` is a short machine-readable key."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


class ProviderTimeout(ProviderError):
    def __init__(self, message: str = "the model service did not answer in time"):
        super().__init__("timeout", message)


@dataclass(frozen=True)
class ToolCall:
    call_id: str
    name: str
    arguments: dict


@dataclass(frozen=True)
class ModelTurn:
    """Either tool calls to execute or the final text (or both, text first)."""

    text: str | None = None
    tool_calls: tuple[ToolCall, ...] = ()
    usage: dict = field(default_factory=dict)
    stop_reason: str | None = None


@dataclass(frozen=True)
class PlannerContext:
    """Trusted per-turn context. The mock planner uses it to resolve names and
    dates; the live provider ignores it (the model must call tools instead)."""

    dataset: Dataset
    horizon_end: date
    active_scenario: ActiveScenario | None
    question: str


class ModelProvider(Protocol):
    name: str
    model_id: str
    mode: str  # "mock" or "live"

    def complete(
        self,
        system_prompt: str,
        messages: list[dict],
        tool_specs: tuple[dict, ...],
        *,
        max_tokens: int,
        timeout: float,
        context: PlannerContext,
    ) -> ModelTurn: ...


def user_text_message(text: str) -> dict:
    return {"role": "user", "content": [{"text": text}]}


def assistant_text_message(text: str) -> dict:
    return {"role": "assistant", "content": [{"text": text}]}


def assistant_tool_use_message(calls: tuple[ToolCall, ...], text: str | None = None) -> dict:
    content: list[dict[str, Any]] = []
    if text:
        content.append({"text": text})
    content.extend(
        {"toolUse": {"toolUseId": c.call_id, "name": c.name, "input": c.arguments}} for c in calls
    )
    return {"role": "assistant", "content": content}


def tool_result_message(results: list[tuple[str, dict]]) -> dict:
    return {
        "role": "user",
        "content": [
            {
                "toolResult": {
                    "toolUseId": call_id,
                    "content": [{"json": envelope}],
                    "status": "success" if envelope.get("status") == "ok" else "error",
                }
            }
            for call_id, envelope in results
        ],
    }


def latest_user_text(messages: list[dict]) -> tuple[int, str]:
    """Index and text of the most recent plain user message (not a tool result)."""
    for idx in range(len(messages) - 1, -1, -1):
        msg = messages[idx]
        if msg.get("role") != "user":
            continue
        texts = [b["text"] for b in msg.get("content", []) if "text" in b]
        if texts:
            return idx, "\n".join(texts)
    return -1, ""


def tool_results_after(messages: list[dict], index: int) -> list[dict]:
    """Envelopes of every tool result that follows ``index`` in the history."""
    out: list[dict] = []
    for msg in messages[index + 1 :]:
        for block in msg.get("content", []):
            result = block.get("toolResult")
            if not result:
                continue
            for part in result.get("content", []):
                if "json" in part:
                    out.append(part["json"])
    return out
