import pytest

from app.llm import PRICES, WRITER_MODEL, cost_usd


def test_cost_counts_cached_input_at_the_cached_rate():
    # 1M input of which 200k cached, 100k output on gpt-6-sol: 0.8*2.00 + 0.2*0.20 + 0.1*10.00
    usd = cost_usd(
        "gpt-6-sol", input_tokens=1_000_000, cached_tokens=200_000, output_tokens=100_000
    )
    assert usd == pytest.approx(1.60 + 0.04 + 1.00)


def test_every_pipeline_model_has_a_price():
    from app import llm

    for model in (llm.EDITOR_MODEL, WRITER_MODEL, llm.CHECKER_MODEL, llm.ASK_MODEL):
        assert model in PRICES


def test_unknown_model_fails_loudly():
    with pytest.raises(KeyError):
        cost_usd("gpt-unknown", 1, 0, 1)
