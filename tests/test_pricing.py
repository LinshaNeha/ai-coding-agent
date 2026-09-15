from app.services.pricing import calculate_cost
from app.services.classifier import classify_difficulty


def test_calculate_cost_basic():
    cost = calculate_cost("gemini-3.6-flash", 1_000_000, 0)
    assert cost == 0.75


def test_calculate_cost_unknown_model_uses_default():
    cost = calculate_cost("some-made-up-model", 1_000_000, 1_000_000)
    assert cost == 0.75 + 3.75


def test_classify_difficulty_simple():
    assert classify_difficulty("What is FastAPI?") == "simple"


def test_classify_difficulty_complex():
    assert classify_difficulty("Explain how the retriever works in detail") == "complex"