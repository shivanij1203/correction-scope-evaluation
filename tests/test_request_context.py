from dataclasses import replace
from app.request_context import Fact, Status, assess, public_rfq_example


def check(choice, facts, evidence=1, catalog=3, policy=2):
    return assess(choice, facts, evidence_revision=evidence,
                  catalog_revision=catalog, policy_revision=policy)


def test_public_rfq_missing_lumber_length():
    facts, choice = public_rfq_example()
    result = check(choice, facts)
    assert result.status == Status.MISSING
    assert result.reasons == ('missing lumber_length',)
    assert result.sources == ('email:line2',)


def test_rep_supplies_length_with_source():
    facts, choice = public_rfq_example()
    updated = facts + (Fact('lumber_length', '8 ft', 'rep:confirmation', 1),)
    assert check(choice, updated).status == Status.CURRENT


def test_conflicting_length_does_not_silently_select_one():
    facts, choice = public_rfq_example()
    updated = facts + (Fact('lumber_length', '8 ft', 'rep:confirmation', 1),
                       Fact('lumber_length', '10 ft', 'attachment:line4', 1))
    result = check(choice, updated)
    assert result.status == Status.CONFLICT
    assert 'conflicting lumber_length' in result.reasons


def test_catalog_change_invalidates_derived_choice():
    facts, choice = public_rfq_example()
    updated = facts + (Fact('lumber_length', '8 ft', 'rep:confirmation', 1),)
    assert check(choice, updated, catalog=4).status == Status.STALE


def test_policy_change_invalidates_derived_choice():
    facts, choice = public_rfq_example()
    updated = facts + (Fact('lumber_length', '8 ft', 'rep:confirmation', 1),)
    assert 'operating rules changed since choice' in check(choice, updated, policy=3).reasons


def test_new_email_revision_requires_rederivation():
    facts, choice = public_rfq_example()
    updated = tuple(replace(f, source_revision=2) for f in facts)
    updated += (Fact('lumber_length', '8 ft', 'rep:confirmation', 2),)
    result = check(choice, updated, evidence=2)
    assert result.status == Status.STALE
    assert 'request revised since choice' in result.reasons


def test_unrelated_source_change_does_not_invalidate_choice():
    facts, choice = public_rfq_example()
    updated = facts + (Fact('lumber_length', '8 ft', 'rep:confirmation', 1),
                       Fact('unrelated_note', 'call before delivery', 'email:line3', 1))
    assert check(choice, updated).status == Status.CURRENT
