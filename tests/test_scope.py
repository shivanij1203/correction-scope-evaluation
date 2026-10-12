from dataclasses import replace
from datetime import date
from app.scenarios import BASE, cases
from app.scope import Decision, evaluate, naive_reuse


def test_fixture_expectations():
    for name, correction, order, expected in cases():
        assert evaluate(correction, order).decision == expected, name


def test_baseline_overgeneralizes_stockout():
    _, correction, order, expected = cases()[1]
    assert naive_reuse(correction, order)
    assert expected == Decision.IGNORE


def test_provenance_is_preserved():
    _, correction, order, _ = cases()[0]
    result = evaluate(correction, order)
    assert result.source_order == 'quote-100'
    assert result.correction_id == 'corr-17'
    assert result.reasons


def test_policy_change_requires_review_even_for_approved_preference():
    _, correction, order, _ = cases()[7]
    assert evaluate(correction, replace(order, policy_version=4)).decision == Decision.REVIEW


def test_future_correction_cannot_change_past_order():
    _, correction, order, _ = cases()[7]
    assert evaluate(correction, replace(order, on_date=date(2026, 8, 1))).decision == Decision.IGNORE


def test_one_time_customer_correction_is_not_auto_promoted():
    _, correction, order, _ = cases()[7]
    assert evaluate(replace(correction, approved_as_preference=False), order).decision == Decision.REVIEW
