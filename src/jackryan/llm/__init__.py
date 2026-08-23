"""LLM client abstraction.

All LLM calls go through this module. Every call is logged to the
`llm_calls` table with prompt, response, tokens, cost, and latency.

Provider: OpenRouter (OpenAI-compatible API). One key, many models.
"""

from jackryan.llm.client import LLMClient, LLMResponse, get_client

__all__ = ["LLMClient", "LLMResponse", "get_client"]
