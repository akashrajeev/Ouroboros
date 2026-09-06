"""OpenCode Zen adapter for Muse Spark 1.3 Contributor Free.

Browser Use 0.13.10 exposes ``ChatOpenAI`` through the OpenAI Chat Completions
API, while OpenCode Zen serves Muse Spark 1.3 Contributor Free through the
OpenAI Responses API. This adapter keeps Browser Use's native LLM protocol and
serializes its messages through Browser Use's existing Responses serializer.
"""

from __future__ import annotations

from typing import Any, TypeVar, overload

from openai import APIConnectionError, APIStatusError, RateLimitError
from pydantic import BaseModel

from browser_use import ChatOpenAI
from browser_use.llm.exceptions import ModelProviderError, ModelRateLimitError
from browser_use.llm.messages import BaseMessage
from browser_use.llm.openai.responses_serializer import ResponsesAPIMessageSerializer
from browser_use.llm.schema import SchemaOptimizer
from browser_use.llm.views import ChatInvokeCompletion, ChatInvokeUsage

T = TypeVar("T", bound=BaseModel)

MUSE_SPARK_MODEL = "muse-spark-1.3-contributor-free"
MUSE_SPARK_BASE_URL = "https://opencode.ai/zen/v1"


class ChatMuseSpark(ChatOpenAI):
    """Browser Use LLM wrapper backed by OpenCode Zen's Responses API."""

    @property
    def provider(self) -> str:
        return "opencode-zen"

    def _get_usage_from_responses(self, response: Any) -> ChatInvokeUsage | None:
        usage = getattr(response, "usage", None)
        if usage is None:
            return None

        input_details = getattr(usage, "input_tokens_details", None)
        cached_tokens = getattr(input_details, "cached_tokens", None) if input_details else None

        return ChatInvokeUsage(
            prompt_tokens=getattr(usage, "input_tokens", None),
            prompt_cached_tokens=cached_tokens,
            prompt_cache_creation_tokens=None,
            prompt_image_tokens=None,
            completion_tokens=getattr(usage, "output_tokens", None),
            total_tokens=getattr(usage, "total_tokens", None),
        )

    @overload
    async def ainvoke(
        self, messages: list[BaseMessage], output_format: None = None, **kwargs: Any
    ) -> ChatInvokeCompletion[str]: ...

    @overload
    async def ainvoke(
        self, messages: list[BaseMessage], output_format: type[T], **kwargs: Any
    ) -> ChatInvokeCompletion[T]: ...

    async def ainvoke(
        self, messages: list[BaseMessage], output_format: type[T] | None = None, **kwargs: Any
    ) -> ChatInvokeCompletion[T] | ChatInvokeCompletion[str]:
        """Invoke Muse Spark through the OpenAI Responses API."""
        input_messages = ResponsesAPIMessageSerializer.serialize_messages(messages)

        model_params: dict[str, Any] = {
            "model": self.model,
            "input": input_messages,
        }

        if self.max_completion_tokens is not None:
            # Browser Use calls this field max_completion_tokens; the Responses API
            # calls the equivalent budget max_output_tokens.
            model_params["max_output_tokens"] = self.max_completion_tokens

        if self.reasoning_effort:
            model_params["reasoning"] = {"effort": self.reasoning_effort}

        if self.top_p is not None:
            model_params["top_p"] = self.top_p

        if self.service_tier is not None:
            model_params["service_tier"] = self.service_tier

        if output_format is not None and not self.dont_force_structured_output:
            json_schema = SchemaOptimizer.create_optimized_json_schema(
                output_format,
                remove_min_items=self.remove_min_items_from_schema,
                remove_defaults=self.remove_defaults_from_schema,
            )
            model_params["text"] = {
                "format": {
                    "type": "json_schema",
                    "name": "agent_output",
                    "strict": True,
                    "schema": json_schema,
                }
            }

            if self.add_schema_to_system_prompt and input_messages and input_messages[0].get("role") == "system":
                schema_text = f"\n<json_schema>\n{json_schema}\n</json_schema>"
                content = input_messages[0].get("content", "")
                if isinstance(content, str):
                    input_messages[0]["content"] = content + schema_text
                elif isinstance(content, list):
                    input_messages[0]["content"] = list(content) + [
                        {"type": "input_text", "text": schema_text}
                    ]

        try:
            response = await self.get_client().responses.create(**model_params)

            usage = self._get_usage_from_responses(response)
            output_text = getattr(response, "output_text", "") or ""
            stop_reason = getattr(response, "status", None)

            if output_format is None or self.dont_force_structured_output:
                return ChatInvokeCompletion(
                    completion=output_text,
                    usage=usage,
                    stop_reason=stop_reason,
                )

            if not output_text:
                raise ModelProviderError(
                    message="Muse Spark returned no output text for structured Browser Use output",
                    status_code=502,
                    model=self.name,
                )

            parsed = output_format.model_validate_json(output_text)
            return ChatInvokeCompletion(
                completion=parsed,
                usage=usage,
                stop_reason=stop_reason,
            )

        except ModelProviderError:
            raise
        except RateLimitError as exc:
            raise ModelRateLimitError(message=exc.message, model=self.name) from exc
        except APIConnectionError as exc:
            raise ModelProviderError(message=str(exc), model=self.name) from exc
        except APIStatusError as exc:
            raise ModelProviderError(message=exc.message, status_code=exc.status_code, model=self.name) from exc
        except Exception as exc:
            raise ModelProviderError(message=str(exc), model=self.name) from exc
