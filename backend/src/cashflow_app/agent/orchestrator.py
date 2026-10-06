"""Bounded tool-calling loop with numerical grounding.

The loop allows at most ``max_tool_calls`` tool executions per question,
accepts only allowlisted tool names, validates every argument through the
tool layer, and checks that each money amount in the final explanation was
returned by a tool. Tool results are preserved even when the model fails.
"""

import re
import time
from dataclasses import dataclass, field

from cashflow.models import Dataset

from ..config import AppConfig
from ..envelope import (
    E_PROVIDER,
    E_PROVIDER_TIMEOUT,
    E_TOOL_LIMIT,
    E_UNGROUNDED,
    STATUS_ERROR,
    STATUS_OK,
    dedupe_evidence,
)
from ..session import ActiveScenario, Session, trim_history
from ..tools import TOOL_SIMULATE_DELAY, TOOL_SPECS, ToolContext, run_tool
from .compose import FALLBACK_NOTE, compose_answer
from .prompts import build_system_prompt
from .provider import (
    ModelProvider,
    PlannerContext,
    ProviderError,
    ProviderTimeout,
    assistant_text_message,
    assistant_tool_use_message,
    tool_result_message,
    user_text_message,
)

_MONEY_TOKEN = re.compile(r"-?\d{1,3}(?:,\d{2,3})+\.\d{2}|-?\d+\.\d{2}")
_MONEY_VALUE = re.compile(r"^-?\d+\.\d{2}$")


@dataclass
class ChatResult:
    status: str
    answer: str
    mode: str
    model_id: str
    tool_trace: list[dict] = field(default_factory=list)
    tool_results: list[dict] = field(default_factory=list)
    evidence: list[dict] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    error: dict | None = None
    grounded: bool = True
    usage: dict = field(default_factory=dict)
    session: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {
            "status": self.status,
            "answer": self.answer,
            "mode": self.mode,
            "model_id": self.model_id,
            "tool_trace": self.tool_trace,
            "tool_results": self.tool_results,
            "evidence": self.evidence,
            "warnings": self.warnings,
            "error": self.error,
            "grounded": self.grounded,
            "usage": self.usage,
            "session": self.session,
        }


def money_values(obj: object, out: set[str] | None = None) -> set[str]:
    """Every two-decimal money string found anywhere in a tool envelope."""
    out = set() if out is None else out
    if isinstance(obj, str):
        if _MONEY_VALUE.match(obj):
            out.add(obj)
        else:
            # Money-looking text inside a record field (for example a customer name)
            # is tool output too; quoting it verbatim is not an invented figure.
            for token in _MONEY_TOKEN.findall(obj):
                out.add(token.replace(",", ""))
    elif isinstance(obj, dict):
        for v in obj.values():
            money_values(v, out)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            money_values(v, out)
    return out


def check_grounding(answer: str, envelopes: list[dict]) -> list[str]:
    """Money tokens in ``answer`` that no tool returned. Empty means grounded."""
    allowed = set()
    for env in envelopes:
        money_values(env.get("facts"), allowed)
    unknown: list[str] = []
    for token in _MONEY_TOKEN.findall(answer):
        normalized = token.replace(",", "")
        if normalized not in allowed and normalized not in unknown:
            unknown.append(normalized)
    return unknown


class Orchestrator:
    def __init__(self, provider: ModelProvider, config: AppConfig):
        self.provider = provider
        self.config = config

    def chat(
        self,
        session: Session,
        dataset: Dataset,
        question: str,
        *,
        created_at: str,
        business_name: str,
    ) -> ChatResult:
        snapshot = dataset.snapshot
        ctx = ToolContext(
            dataset=dataset,
            default_horizon_end=session.horizon_end,
            created_at=created_at,
            business_name=business_name,
        )
        system_prompt = build_system_prompt(
            as_of=snapshot.as_of_date,
            horizon_end=session.horizon_end,
            currency=snapshot.currency,
            timezone=snapshot.timezone,
            dataset_version=snapshot.dataset_version,
        )
        session.messages.append(user_text_message(question))
        session.turns += 1

        result = ChatResult(
            status=STATUS_OK, answer="", mode=self.provider.mode, model_id=self.provider.model_id
        )
        usage_totals: dict[str, int] = {}
        calls_made = 0
        # At most one provider call per tool round plus the final answer.
        for _ in range(self.config.max_tool_calls + 2):
            planner = PlannerContext(
                dataset=dataset,
                horizon_end=session.horizon_end,
                active_scenario=session.active_scenario,
                question=question,
            )
            try:
                turn = self.provider.complete(
                    system_prompt,
                    trim_history(session.messages),
                    TOOL_SPECS,
                    max_tokens=self.config.max_output_tokens,
                    timeout=self.config.model_timeout_seconds,
                    context=planner,
                )
            except ProviderTimeout as exc:
                return self._provider_failure(result, session, question, E_PROVIDER_TIMEOUT, str(exc))
            except ProviderError as exc:
                return self._provider_failure(
                    result, session, question, E_PROVIDER, f"{exc} (provider code {exc.code})"
                )
            for key, value in turn.usage.items():
                if isinstance(value, int):
                    usage_totals[key] = usage_totals.get(key, 0) + value

            if turn.tool_calls:
                if calls_made + len(turn.tool_calls) > self.config.max_tool_calls:
                    result.error = {
                        "code": E_TOOL_LIMIT,
                        "message": f"the model asked for more than {self.config.max_tool_calls} tool calls",
                    }
                    result.status = STATUS_ERROR
                    result.answer = compose_answer(question, result.tool_results)
                    result.warnings.append("Tool-call limit reached; showing the results gathered so far.")
                    self._finish(result, session, usage_totals)
                    return result
                session.messages.append(assistant_tool_use_message(turn.tool_calls, turn.text))
                outcomes: list[tuple[str, dict]] = []
                for call in turn.tool_calls:
                    started = time.perf_counter()
                    envelope = run_tool(ctx, call.name, call.arguments)
                    elapsed_ms = round((time.perf_counter() - started) * 1000, 1)
                    calls_made += 1
                    result.tool_trace.append(
                        {
                            "tool": call.name,
                            "arguments": call.arguments,
                            "status": envelope["status"],
                            "error_code": (envelope.get("error") or {}).get("code"),
                            "duration_ms": elapsed_ms,
                        }
                    )
                    result.tool_results.append(envelope)
                    outcomes.append((call.call_id, envelope))
                    self._remember(session, call.name, call.arguments, envelope)
                session.messages.append(tool_result_message(outcomes))
                continue

            text = (turn.text or "").strip()
            if not text:
                text = compose_answer(question, result.tool_results)
                result.warnings.append("The model returned no text; a template summary is shown.")
            unknown = check_grounding(text, result.tool_results)
            if unknown:
                result.grounded = False
                result.warnings.append(
                    "The model's explanation contained amounts not returned by any tool ("
                    + ", ".join(unknown)
                    + "); it was replaced by a template built from the tool results."
                )
                result.error = {"code": E_UNGROUNDED, "message": "ungrounded amounts: " + ", ".join(unknown)}
                text = FALLBACK_NOTE + "\n\n" + compose_answer(question, result.tool_results)
            result.answer = text
            session.messages.append(assistant_text_message(text))
            self._finish(result, session, usage_totals)
            return result

        result.status = STATUS_ERROR
        result.error = {"code": E_TOOL_LIMIT, "message": "the conversation loop did not finish"}
        result.answer = compose_answer(question, result.tool_results)
        self._finish(result, session, usage_totals)
        return result

    def _remember(self, session: Session, name: str, arguments: dict, envelope: dict) -> None:
        if envelope.get("status") != STATUS_OK:
            return
        facts = envelope.get("facts", {})
        if name == TOOL_SIMULATE_DELAY:
            session.active_scenario = ActiveScenario(facts["invoice_id"], int(facts["delay_days"]))
        horizon = facts.get("horizon_end")
        if isinstance(horizon, str):
            from datetime import date

            session.horizon_end = date.fromisoformat(horizon)

    def _provider_failure(
        self, result: ChatResult, session: Session, question: str, code: str, message: str
    ) -> ChatResult:
        result.status = STATUS_ERROR
        result.error = {"code": code, "message": message}
        if result.tool_results:
            result.answer = (
                "The model service failed, so here is a template summary of the calculations that "
                "did complete.\n\n" + compose_answer(question, result.tool_results)
            )
        else:
            result.answer = "The model service is unavailable right now. The calculations on this page do not depend on it; try again shortly."
        result.warnings.append(message)
        # Keep the history consistent: drop the unanswered question.
        if session.messages and session.messages[-1].get("role") == "user":
            session.messages.pop()
        self._finish(result, session, {})
        return result

    def _finish(self, result: ChatResult, session: Session, usage: dict) -> None:
        evidence: list[dict] = []
        for env in result.tool_results:
            evidence.extend(env.get("evidence", []))
            for w in env.get("warnings", []):
                if w not in result.warnings:
                    result.warnings.append(w)
        result.evidence = dedupe_evidence(evidence)
        result.usage = usage
        result.session = session.as_dict()
