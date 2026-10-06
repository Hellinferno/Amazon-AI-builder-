"""Live provider: Amazon Bedrock Converse API with tool use.

Credentials come from the standard AWS credential chain (profile, SSO, or
environment); nothing here stores or logs them. This module is only imported
when APP_MODE=live. It has NOT been exercised against a real account in this
repository until docs/TEST_PLAN.md records a live run.
"""

from .provider import ModelTurn, PlannerContext, ProviderError, ProviderTimeout, ToolCall


class BedrockConverseProvider:
    name = "bedrock"
    mode = "live"

    def __init__(self, *, region: str, model_id: str, timeout: float, max_retries: int = 1):
        try:
            import boto3
            from botocore.config import Config
        except ImportError:  # pragma: no cover - depends on the environment
            raise ProviderError(
                "missing_dependency", "boto3 is not installed; install cashflow[aws]"
            ) from None
        self.model_id = model_id
        self.region = region
        self._client = boto3.client(
            "bedrock-runtime",
            region_name=region,
            config=Config(
                connect_timeout=min(10.0, timeout),
                read_timeout=timeout,
                retries={"max_attempts": max_retries, "mode": "standard"},
            ),
        )

    def complete(
        self,
        system_prompt: str,
        messages: list[dict],
        tool_specs: tuple[dict, ...],
        *,
        max_tokens: int,
        timeout: float,
        context: PlannerContext,
    ) -> ModelTurn:
        from botocore.exceptions import (
            BotoCoreError,
            ClientError,
            ConnectTimeoutError,
            NoCredentialsError,
            ReadTimeoutError,
        )

        try:
            response = self._client.converse(
                modelId=self.model_id,
                system=[{"text": system_prompt}],
                messages=messages,
                toolConfig={"tools": [{"toolSpec": spec} for spec in tool_specs]},
                inferenceConfig={"maxTokens": max_tokens, "temperature": 0},
            )
        except (ReadTimeoutError, ConnectTimeoutError) as exc:
            raise ProviderTimeout(f"Bedrock did not answer within {timeout:.0f}s") from exc
        except NoCredentialsError as exc:
            raise ProviderError("no_credentials", "no AWS credentials were found") from exc
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code", "ClientError")
            message = exc.response.get("Error", {}).get("Message", str(exc))
            raise ProviderError(code, f"Bedrock request failed: {message}") from exc
        except BotoCoreError as exc:
            raise ProviderError("botocore", f"AWS client error: {exc}") from exc

        return parse_converse_response(response)


def parse_converse_response(response: dict) -> ModelTurn:
    """Translate a Converse response into a ``ModelTurn``. Pure; tested offline."""
    message = response.get("output", {}).get("message", {})
    texts: list[str] = []
    calls: list[ToolCall] = []
    for block in message.get("content", []):
        if "text" in block:
            texts.append(block["text"])
        elif "toolUse" in block:
            use = block["toolUse"]
            arguments = use.get("input")
            calls.append(
                ToolCall(
                    call_id=str(use.get("toolUseId", "")),
                    name=str(use.get("name", "")),
                    arguments=arguments if isinstance(arguments, dict) else {},
                )
            )
    usage = response.get("usage", {})
    return ModelTurn(
        text="\n".join(texts).strip() or None,
        tool_calls=tuple(calls),
        usage={
            "input_tokens": usage.get("inputTokens"),
            "output_tokens": usage.get("outputTokens"),
            "total_tokens": usage.get("totalTokens"),
        },
        stop_reason=response.get("stopReason"),
    )
