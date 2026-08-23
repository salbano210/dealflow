"""OpenRouter client with structured-output support and DB call logging."""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Any, Type, TypeVar

from openai import OpenAI
from pydantic import BaseModel, ValidationError

from dealflow.config import AppConfig
from dealflow.db.models import LlmCall
from dealflow.db.session import get_session

T = TypeVar("T", bound=BaseModel)


@dataclass
class LLMResponse:
    text: str
    parsed: BaseModel | None
    model: str
    tokens_in: int | None
    tokens_out: int | None
    cost_usd: float | None
    latency_ms: int
    llm_call_id: int


class LLMClient:
    """Thin wrapper over the OpenRouter API. One instance per app.

    Every call:
      1. Resolves the model for the step from config/models.yaml.
      2. Sends the request (with retries on transient errors).
      3. Optionally parses the response into a Pydantic schema.
      4. Logs the full call to llm_calls, including the cost OpenRouter
         reports back for that specific invocation.
    """

    def __init__(self, config: AppConfig):
        self._config = config
        api_key = os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            raise RuntimeError(
                "OPENROUTER_API_KEY is not set. Copy .env.example to .env and add your key."
            )
        headers = {}
        if app := os.environ.get("OPENROUTER_APP_URL"):
            headers["HTTP-Referer"] = app
        if name := os.environ.get("OPENROUTER_APP_NAME"):
            headers["X-Title"] = name

        self._client = OpenAI(
            api_key=api_key,
            base_url=config.models.openrouter.base_url,
            timeout=config.models.openrouter.timeout_seconds,
            default_headers=headers or None,
        )

    def complete(
        self,
        *,
        step: str,
        system: str,
        user: str,
        schema: Type[T] | None = None,
        company_id: int | None = None,
    ) -> LLMResponse:
        """Run one LLM call. If `schema` is provided, the response is
        requested in JSON format and validated against it.
        """
        step_cfg = self._config.models.for_step(step)

        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
        kwargs: dict[str, Any] = {
            "model": step_cfg.model,
            "messages": messages,
            "temperature": step_cfg.temp,
        }
        if step_cfg.max_tokens is not None:
            kwargs["max_tokens"] = step_cfg.max_tokens
        if schema is not None:
            # Request JSON. Cheap models sometimes still drift; we validate
            # below and raise on failure -- never silently corrupt data.
            kwargs["response_format"] = {"type": "json_object"}
            # Include the schema in the user prompt so the model knows the shape.
            kwargs["messages"][-1]["content"] += (
                "\n\nRespond ONLY with a JSON object matching this schema:\n"
                + json.dumps(schema.model_json_schema(), indent=2)
            )

        start = time.perf_counter()
        error: str | None = None
        response = None
        text = ""
        parsed: BaseModel | None = None
        tokens_in = tokens_out = None
        cost_usd = None

        try:
            response = self._client.chat.completions.create(**kwargs)
            text = response.choices[0].message.content or ""
            if response.usage is not None:
                tokens_in = response.usage.prompt_tokens
                tokens_out = response.usage.completion_tokens
            # OpenRouter attaches cost via an extra field.
            raw = response.model_dump()
            cost_usd = raw.get("usage", {}).get("total_cost") if isinstance(raw.get("usage"), dict) else None

            if schema is not None:
                try:
                    parsed = schema.model_validate_json(text)
                except ValidationError as e:
                    error = f"schema_validation_failed: {e}"
                    raise
        except Exception as e:
            if error is None:
                error = f"{type(e).__name__}: {e}"
            raise
        finally:
            latency_ms = int((time.perf_counter() - start) * 1000)
            call_id = _log_call(
                step=step,
                model=step_cfg.model,
                system=system,
                user=kwargs["messages"][-1]["content"],
                response_text=text,
                response_json=(parsed.model_dump() if parsed else None),
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                cost_usd=cost_usd,
                latency_ms=latency_ms,
                error=error,
                company_id=company_id,
            )

        return LLMResponse(
            text=text,
            parsed=parsed,
            model=step_cfg.model,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost_usd=cost_usd,
            latency_ms=latency_ms,
            llm_call_id=call_id,
        )


def _log_call(**kwargs) -> int:
    with get_session() as s:
        row = LlmCall(**kwargs)
        s.add(row)
        s.flush()
        return row.id


_singleton: LLMClient | None = None


def get_client(config: AppConfig) -> LLMClient:
    global _singleton
    if _singleton is None:
        _singleton = LLMClient(config)
    return _singleton
