from dataclasses import replace
from datetime import date
import pytest
from app.scenarios import BASE, cases
from app.scope import Decision
from app.authority import Authority, CorrectionRecord, Policy, resolve

DAY = date(2026, 10, 12)
POLICY = Policy(3, date(2026, 9, 1), frozenset({'PLY-ALT', 'PLY-B'}), 'contract-v3')
PREF = cases()[7][1]
ORDER = cases()[7][2]

def rec(c=PREF, authority=Authority.CUSTOMER_DIRECTIVE, approved='customer-rep', supersedes=None):
    return CorrectionRecord(c, authority, f'email:{c.id}', approved, supersedes)

def test_approved_directive_can_be_reused():
    result = resolve([rec()], ORDER, [POLICY])
    assert result.decision == Decision.REUSE
    assert result.applied == ('corr-18',)
    assert result.policy_source == 'contract-v3'

def test_observation_cannot_become_a_preference():
    assert resolve([rec(authority=Authority.OBSERVATION)], ORDER, [POLICY]).decision == Decision.REVIEW

def test_salesperson_correction_cannot_become_a_customer_directive():
    assert resolve([rec(authority=Authority.SALES_APPROVAL)], ORDER, [POLICY]).decision == Decision.REVIEW

def test_conflicting_same_day_directives_require_review():
    other = replace(PREF, id='corr-19', substitute_sku='PLY-B')
    result = resolve([rec(), rec(other)], ORDER, [POLICY])
    assert result.decision == Decision.REVIEW
    assert 'conflicting customer directives' in result.reasons

def test_explicit_supersession_changes_selected_directive():
    newer = replace(PREF, id='corr-20', substitute_sku='PLY-B', recorded_on=date(2026, 10, 1))
    result = resolve([rec(), rec(newer, supersedes='corr-18')], ORDER, [POLICY])
    assert result.decision == Decision.REUSE
    assert result.sku == 'PLY-B'
    assert result.applied == ('corr-20',)

def test_policy_revision_invalidates_old_preference():
    newer = Policy(4, date(2026, 10, 1), frozenset({'PLY-B'}), 'contract-v4')
    result = resolve([rec()], replace(ORDER, policy_version=4), [POLICY, newer])
    assert result.decision == Decision.REVIEW
    assert result.policy_source == 'contract-v4'

def test_stale_order_policy_is_not_silently_used():
    newer = Policy(4, date(2026, 10, 1), frozenset({'PLY-ALT'}), 'contract-v4')
    assert resolve([rec()], ORDER, [POLICY, newer]).decision == Decision.REVIEW

def test_future_policy_does_not_change_past_decision():
    future = Policy(4, date(2026, 11, 1), frozenset(), 'contract-v4')
    assert resolve([rec()], ORDER, [POLICY, future]).decision == Decision.REUSE

def test_missing_provenance_rejected():
    with pytest.raises(ValueError):
        resolve([replace(rec(), evidence_id='')], ORDER, [POLICY])

def test_missing_or_conflicting_policy_requires_review():
    assert resolve([rec()], ORDER, []).decision == Decision.REVIEW
    duplicate = Policy(3, POLICY.effective_from, frozenset({'PLY-B'}), 'other-policy')
    assert resolve([rec()], ORDER, [POLICY, duplicate]).decision == Decision.REVIEW

def test_invalid_supersession_cannot_erase_history():
    newer = replace(PREF, id='corr-20', recorded_on=date(2026, 10, 1))
    assert resolve([rec(newer, supersedes='not-present')], ORDER, [POLICY]).decision == Decision.REVIEW

def test_no_cross_customer_reuse():
    assert resolve([rec()], replace(ORDER, customer='another'), [POLICY]).decision == Decision.IGNORE

def test_newer_directive_without_supersession_does_not_win_by_timestamp():
    newer = replace(PREF, id='corr-21', substitute_sku='PLY-B', recorded_on=date(2026, 10, 2))
    result = resolve([rec(), rec(newer)], ORDER, [POLICY])
    assert result.decision == Decision.REVIEW
    assert 'conflicting customer directives' in result.reasons


def test_unapproved_observation_cannot_revoke_customer_directive():
    later = replace(PREF, id='observation-99', substitute_sku='PLY-B',
                    recorded_on=date(2026, 10, 2), approved_as_preference=False)
    result = resolve([rec(), rec(later, authority=Authority.OBSERVATION,
                                 approved=None, supersedes='corr-18')], ORDER, [POLICY])
    assert result.decision == Decision.REVIEW
    assert 'unverified or invalid supersession' in result.reasons
