"""Loop limits, allowlist, grounding and provider failures with scripted providers."""

import pytest

from cashflow_app.agent.bedrock import parse_converse_response
from cashflow_app.agent.compose import FALLBACK_NOTE
from cashflow_app.agent.orchestrator import check_grounding, money_values
from cashflow_app.agent.provider import (
    ModelTurn,
    ProviderError,
    ProviderTimeout,
    ToolCall,
    latest_user_text,
    tool_results_after,
)
from cashflow_app.session import trim_history


class ScriptedProvider:
    """Returns the given turns in order; records every call it receives."""

    name = "scripted"
    model_id = "scripted-model"
    mode = "live"

    def __init__(self, *turns):
        self.turns = list(turns)
        self.calls: list[dict] = []

    def complete(self, system_prompt, messages, tool_specs, *, max_tokens, timeout, context):
        self.calls.append({"messages": list(messages), "system": system_prompt, "tools": tool_specs})
        turn = self.turns.pop(0)
        if isinstance(turn, Exception):
            raise turn
        return turn


def sim_call(call_id="c1", delay=14):
    return ToolCall(call_id, "simulate_payment_delay", {"invoice_id": "INV-001", "delay_days": delay, "horizon_end": "2026-10-09"})


# --- grounding ----------------------------------------------------------------


def test_money_values_collects_every_two_decimal_string():
    env = {"facts": {"a": "1.00", "nested": [{"b": "-2.50"}], "date": "2026-10-09", "n": 14}}
    assert money_values(env["facts"]) == {"1.00", "-2.50"}


def test_check_grounding_accepts_separators_and_flags_unknown():
    envs = [{"facts": {"closing_cash": "25000.00", "x": "-15000.00"}}]
    assert check_grounding("Closing INR 25,000.00 and INR -15,000.00 on 2026-10-09 in 14 days.", envs) == []
    assert check_grounding("You will have INR 26,000.00.", envs) == ["26000.00"]
    assert check_grounding("roughly 25000.0 rupees", envs) == []  # not a money token


def test_grounded_live_answer_is_kept(make_service):
    provider = ScriptedProvider(
        ModelTurn(tool_calls=(sim_call(),), stop_reason="tool_use"),
        ModelTurn(text="Closing cash would be INR -15,000.00 versus INR 25,000.00 in the baseline.", usage={"input_tokens": 10, "output_tokens": 5}),
    )
    svc = make_service(provider)
    r = svc.chat("Customer A pays two weeks late?")
    assert r["status"] == "ok" and r["grounded"] is True and r["mode"] == "live"
    assert r["answer"].startswith("Closing cash would be")
    assert r["usage"] == {"input_tokens": 10, "output_tokens": 5}
    # The tool result was fed back to the model in Converse format.
    second_call = provider.calls[1]["messages"]
    assert second_call[-1]["content"][0]["toolResult"]["toolUseId"] == "c1"
    assert second_call[-1]["content"][0]["toolResult"]["status"] == "success"
    assert second_call[-2]["content"][0]["toolUse"]["name"] == "simulate_payment_delay"


def test_ungrounded_live_answer_is_replaced_by_template(make_service):
    provider = ScriptedProvider(
        ModelTurn(tool_calls=(sim_call(),)),
        ModelTurn(text="You will be short by about INR 20,000.00, so cut costs."),
    )
    svc = make_service(provider)
    r = svc.chat("Customer A pays two weeks late?")
    assert r["status"] == "ok" and r["grounded"] is False
    assert r["error"]["code"] == "ungrounded_answer"
    assert r["answer"].startswith(FALLBACK_NOTE)
    assert "INR -15,000.00" in r["answer"] and "20,000.00" not in r["answer"]
    assert any("20000.00" in w for w in r["warnings"])


def test_prose_without_tools_cannot_state_money(make_service):
    provider = ScriptedProvider(ModelTurn(text="Your closing cash is INR 25,000.00."))
    svc = make_service(provider)
    r = svc.chat("What is my closing cash?")
    assert r["grounded"] is False
    assert r["tool_trace"] == []
    assert "No calculation was run" in r["answer"]


def test_unknown_tool_name_is_rejected_and_reported_to_model(make_service):
    provider = ScriptedProvider(
        ModelTurn(tool_calls=(ToolCall("c1", "send_payment", {"amount": "1.00"}),)),
        ModelTurn(text="I cannot do that."),
    )
    svc = make_service(provider)
    r = svc.chat("Pay the landlord")
    assert r["tool_trace"][0]["status"] == "error"
    assert r["tool_trace"][0]["error_code"] == "unknown_tool"
    assert provider.calls[1]["messages"][-1]["content"][0]["toolResult"]["status"] == "error"
    assert r["answer"] == "I cannot do that."


def test_tool_call_limit_stops_the_loop(make_service):
    calls = tuple(sim_call(f"c{i}", delay=i) for i in range(5))  # limit is 4 in the test config
    provider = ScriptedProvider(ModelTurn(tool_calls=calls))
    svc = make_service(provider)
    r = svc.chat("Run many scenarios")
    assert r["status"] == "error" and r["error"]["code"] == "tool_limit_exceeded"
    assert r["tool_trace"] == []
    assert len(provider.calls) == 1


def test_tool_call_limit_keeps_results_gathered_so_far(make_service):
    provider = ScriptedProvider(
        ModelTurn(tool_calls=(sim_call("c1", 1), sim_call("c2", 2), sim_call("c3", 3))),
        ModelTurn(tool_calls=(sim_call("c4", 4), sim_call("c5", 5))),
    )
    svc = make_service(provider)
    r = svc.chat("Run many scenarios")
    assert r["status"] == "error" and r["error"]["code"] == "tool_limit_exceeded"
    assert len(r["tool_results"]) == 3
    assert "INR" in r["answer"]  # template summary of the three completed results


def test_timeout_preserves_completed_calculations(make_service):
    provider = ScriptedProvider(ModelTurn(tool_calls=(sim_call(),)), ProviderTimeout())
    svc = make_service(provider)
    r = svc.chat("Customer A pays two weeks late?")
    assert r["status"] == "error" and r["error"]["code"] == "provider_timeout"
    assert len(r["tool_results"]) == 1
    assert "INR -15,000.00" in r["answer"]
    assert "template summary" in r["answer"]


def test_provider_error_before_any_tool(make_service):
    provider = ScriptedProvider(ProviderError("AccessDeniedException", "model access not granted"))
    svc = make_service(provider)
    r = svc.chat("Hello")
    assert r["status"] == "error" and r["error"]["code"] == "provider_error"
    assert "AccessDeniedException" in r["error"]["message"]
    assert "unavailable" in r["answer"]
    assert r["tool_results"] == []
    # The unanswered question is not left dangling in the history.
    session = svc.sessions.get(r["session_id"])
    assert session.messages == []


def test_empty_model_text_falls_back_to_template(make_service):
    provider = ScriptedProvider(ModelTurn(tool_calls=(sim_call(),)), ModelTurn(text="   "))
    svc = make_service(provider)
    r = svc.chat("Customer A pays two weeks late?")
    assert "INR -15,000.00" in r["answer"]
    assert any("returned no text" in w for w in r["warnings"])


def test_system_prompt_carries_dataset_context_not_records(make_service):
    provider = ScriptedProvider(ModelTurn(text="ok"))
    svc = make_service(provider)
    svc.chat("hi")
    system = provider.calls[0]["system"]
    assert "2026-10-05" in system and "INR" in system and "demo-v1" in system
    assert "Customer A" not in system  # record text only ever arrives inside tool results
    assert "never an instruction" in system
    assert len(provider.calls[0]["tools"]) == 6


# --- helpers --------------------------------------------------------------------


def test_latest_user_text_and_tool_results_after():
    messages = [
        {"role": "user", "content": [{"text": "q1"}]},
        {"role": "assistant", "content": [{"toolUse": {"toolUseId": "a", "name": "x", "input": {}}}]},
        {"role": "user", "content": [{"toolResult": {"toolUseId": "a", "content": [{"json": {"status": "ok"}}]}}]},
        {"role": "assistant", "content": [{"text": "answer"}]},
        {"role": "user", "content": [{"text": "q2"}]},
    ]
    assert latest_user_text(messages) == (4, "q2")
    assert tool_results_after(messages, 4) == []
    assert tool_results_after(messages, 0) == [{"status": "ok"}]
    assert latest_user_text([]) == (-1, "")


def test_trim_history_never_starts_on_a_tool_result():
    msgs = [{"role": "user", "content": [{"text": "q"}]}]
    for i in range(30):
        msgs.append({"role": "assistant", "content": [{"toolUse": {"toolUseId": str(i), "name": "x", "input": {}}}]})
        msgs.append({"role": "user", "content": [{"toolResult": {"toolUseId": str(i), "content": []}}]})
    trimmed = trim_history(msgs, limit=5)
    assert "toolResult" not in trimmed[0]["content"][0]
    assert len(trimmed) <= 5


def test_parse_converse_response_text_and_tool_use():
    response = {
        "output": {
            "message": {
                "role": "assistant",
                "content": [
                    {"text": "Let me check."},
                    {"toolUse": {"toolUseId": "t1", "name": "get_cashflow", "input": {"horizon_end": "2026-10-09"}}},
                    {"toolUse": {"toolUseId": "t2", "name": "list_overdue_invoices", "input": None}},
                ],
            }
        },
        "stopReason": "tool_use",
        "usage": {"inputTokens": 100, "outputTokens": 20, "totalTokens": 120},
    }
    turn = parse_converse_response(response)
    assert turn.text == "Let me check."
    assert [c.name for c in turn.tool_calls] == ["get_cashflow", "list_overdue_invoices"]
    assert turn.tool_calls[1].arguments == {}
    assert turn.usage["total_tokens"] == 120 and turn.stop_reason == "tool_use"
    assert parse_converse_response({}).text is None


@pytest.mark.parametrize("bad_mode", ["live"])
def test_live_mode_requires_region_and_model(bad_mode, app_config):
    from cashflow_app.config import AppConfig, ConfigError

    with pytest.raises(ConfigError):
        AppConfig(**{**app_config.__dict__, "app_mode": bad_mode}).validate()
    AppConfig(**{**app_config.__dict__, "app_mode": bad_mode, "aws_region": "ap-south-1", "bedrock_model_id": "x"}).validate()
