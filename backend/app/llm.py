"""Thin OpenAI wrapper: one structured-output call and what it cost (ADR 0007)."""

from functools import cache

from openai import OpenAI
from pydantic import BaseModel

from app.config import settings

EDITOR_MODEL = "gpt-6-luna"
WRITER_MODEL = "gpt-6-sol"
CHECKER_MODEL = "gpt-6-sol"
ASK_MODEL = "gpt-6-luna"

# USD per 1M tokens: (input, cached input, output). openai.com pricing, standard, 2026-10-01.
PRICES = {
    "gpt-6-sol": (2.00, 0.20, 10.00),
    "gpt-6-luna": (0.10, 0.01, 0.50),
}


def cost_usd(model: str, input_tokens: int, cached_tokens: int, output_tokens: int) -> float:
    price_in, price_cached, price_out = PRICES[model]
    fresh = input_tokens - cached_tokens
    return (fresh * price_in + cached_tokens * price_cached + output_tokens * price_out) / 1e6


@cache
def client() -> OpenAI:
    return OpenAI(api_key=settings.openai_api_key, max_retries=3, timeout=180)


def parse[T: BaseModel](model: str, system: str, user: str, schema: type[T]) -> tuple[T, dict]:
    """Ask `model` for an instance of `schema` (Structured Outputs). Returns (result, usage)."""
    response = client().responses.parse(
        model=model,
        input=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        text_format=schema,
    )
    if response.output_parsed is None:
        raise RuntimeError(f"{model} returned no {schema.__name__} (refusal or truncation)")
    u = response.usage
    cached = u.input_tokens_details.cached_tokens if u.input_tokens_details else 0
    usage = {
        "usd": cost_usd(model, u.input_tokens, cached, u.output_tokens),
        "in": u.input_tokens,
        "out": u.output_tokens,
    }
    return response.output_parsed, usage
