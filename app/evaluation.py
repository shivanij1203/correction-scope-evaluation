"""A small, explicitly labeled synthetic challenge set.

Labels describe intended business behavior, not model predictions.
This is an internal stress test, not an external benchmark.
"""
from dataclasses import dataclass, replace
from datetime import date
from app.authority import Authority, CorrectionRecord, Policy, resolve
from app.scope import Correction, Decision, Order

DAY = date(2026, 10, 12)
BASE = Correction("pref-01", "acme", "north", "PLY-23", "PLY-ALT",
                  "customer_preference", date(2026, 9, 1), None, 3, "q-100", True)
ORDER = Order("o-200", "acme", "north", "PLY-23", DAY, 3, False, True)
POLICY = Policy(3, date(2026, 9, 1), frozenset({"PLY-ALT", "PLY-B"}), "contract-v3")

def record(c=BASE, authority=Authority.CUSTOMER_DIRECTIVE, approved="customer-rep",
           supersedes=None):
    return CorrectionRecord(c, authority, "evidence:" + c.id, approved, supersedes)

@dataclass(frozen=True)
class Case:
    name: str
    records: tuple[CorrectionRecord, ...]
    order: Order
    policies: tuple[Policy, ...]
    expected: Decision
    rationale: str

def challenge_cases():
    alt = replace(BASE, id="pref-02", substitute_sku="PLY-B", recorded_on=date(2026, 10, 1))
    v4 = Policy(4, date(2026, 10, 1), frozenset({"PLY-B"}), "contract-v4")
    v4_alt = Policy(4, date(2026, 10, 1), frozenset({"PLY-ALT"}), "contract-v4a")
    stock = replace(BASE, id="stock-01", reason="stockout", approved_as_preference=False)
    oneoff = replace(BASE, id="oneoff-01", reason="sales_exception", approved_as_preference=False)
    specs = [
        ("approved preference", (record(),), ORDER, (POLICY,), Decision.REUSE, "Approved directive and current contract permit the substitution"),
        ("same sku another customer", (record(),), replace(ORDER, customer="beta"), (POLICY,), Decision.IGNORE, "Customer-specific preference does not transfer"),
        ("same customer other branch", (record(),), replace(ORDER, branch="south"), (POLICY,), Decision.IGNORE, "Branch scope differs"),
        ("different requested sku", (record(),), replace(ORDER, requested_sku="PLY-19"), (POLICY,), Decision.IGNORE, "Different product"),
        ("record in the future", (record(replace(BASE, recorded_on=date(2026, 10, 20))),), ORDER, (POLICY,), Decision.IGNORE, "Correction not yet recorded"),
        ("expired directive", (record(replace(BASE, valid_until=date(2026, 10, 1))),), ORDER, (POLICY,), Decision.IGNORE, "Directive expired"),
        ("observed substitution", (record(authority=Authority.OBSERVATION),), ORDER, (POLICY,), Decision.REVIEW, "Observation is not permission"),
        ("sales approval", (record(authority=Authority.SALES_APPROVAL),), ORDER, (POLICY,), Decision.REVIEW, "One-order approval is not customer directive"),
        ("no approver", (record(approved=None),), ORDER, (POLICY,), Decision.REVIEW, "Unverified authority"),
        ("temporary stockout", (record(stock),), ORDER, (POLICY,), Decision.REVIEW, "Temporary stockout cannot establish durable preference"),
        ("one-off exception", (record(oneoff),), ORDER, (POLICY,), Decision.REVIEW, "One-time override requires review"),
        ("two conflicting directives", (record(), record(alt)), ORDER, (POLICY,), Decision.REVIEW, "Conflicting authorized preferences"),
        ("explicit supersession", (record(), record(alt, supersedes="pref-01")), ORDER, (POLICY,), Decision.REUSE, "Newer approved directive explicitly replaces prior one"),
        ("no implicit supersession", (record(), record(alt)), ORDER, (POLICY,), Decision.REVIEW, "Later timestamp alone cannot revoke prior directive"),
        ("policy changed", (record(),), replace(ORDER, policy_version=4), (POLICY, v4), Decision.REVIEW, "Old correction not reapproved under new contract"),
        ("stale policy snapshot", (record(),), ORDER, (POLICY, v4), Decision.REVIEW, "Order is using stale policy snapshot"),
        ("conflicting policy sources", (record(),), ORDER, (POLICY, replace(POLICY, source_id="other-contract")), Decision.REVIEW, "Ambiguous applicable contract"),
        ("no policy", (record(),), ORDER, (), Decision.REVIEW, "No effective governing policy"),
        ("substitute unavailable", (record(),), replace(ORDER, substitute_available=False), (POLICY,), Decision.REVIEW, "Cannot use unavailable substitute"),
        ("invalid supersession", (record(alt, supersedes="missing"),), ORDER, (POLICY,), Decision.REVIEW, "Superseded record is not verifiable"),
        ("future contract not applicable", (record(),), ORDER, (POLICY, replace(v4_alt, effective_from=date(2026, 11, 1))), Decision.REUSE, "Future contract must not retroactively apply"),
        ("contract disallows sku", (record(),), ORDER, (replace(POLICY, permitted_substitutes=frozenset({"PLY-B"})),), Decision.REVIEW, "Effective contract disallows chosen SKU"),
        ("irrelevant extra record", (record(), record(replace(alt, customer="beta"))), ORDER, (POLICY,), Decision.REUSE, "Other customer's record cannot change this order"),
        ("wrong branch extra directive", (record(), record(replace(alt, branch="south"))), ORDER, (POLICY,), Decision.REUSE, "Other branch directive is irrelevant"),
    ]
    return tuple(Case(*spec) for spec in specs)

def combined_challenges():
    """Composed cases kept separate from the original 24 specification examples.

    These are still synthetic author-labeled examples, not an independent holdout.
    """
    base = challenge_cases()
    approved = base[0]
    conflicting = base[11]
    changed = base[14]
    unavailable = base[18]
    cases = (
        Case("conflict plus unavailable substitute", conflicting.records,
             replace(conflicting.order, substitute_available=False),
             conflicting.policies, Decision.REVIEW,
             "Conflicting directives and no available substitute"),
        Case("policy revision plus unavailable substitute", changed.records,
             replace(changed.order, substitute_available=False),
             changed.policies, Decision.REVIEW,
             "Old directive cannot survive contract revision"),
        Case("approved directive but different customer and stale snapshot",
             approved.records, replace(approved.order, customer="gamma", policy_version=2),
             approved.policies, Decision.REVIEW,
             "Stale governing policy must be resolved before reuse"),
        Case("approved directive but future dated policy only",
             approved.records, approved.order,
             (replace(POLICY, effective_from=date(2026, 11, 1)),),
             Decision.REVIEW, "No effective contract"),
        Case("approved directive plus irrelevant sales observation",
             approved.records + (record(replace(BASE, id="obs-77", customer="beta"),
                                         authority=Authority.OBSERVATION),),
             approved.order, approved.policies, Decision.REUSE,
             "Unrelated observation must not defeat valid directive"),
        Case("conflicting directives plus new contract",
             conflicting.records, replace(conflicting.order, policy_version=4),
             (POLICY, Policy(4, date(2026, 10, 1),
                             frozenset({"PLY-ALT", "PLY-B"}), "contract-v4")),
             Decision.REVIEW, "Contract change cannot silently settle conflict"),
        Case("one-time substitution plus expired contract",
             base[10].records, base[10].order,
             (replace(POLICY, effective_from=date(2026, 11, 1)),),
             Decision.REVIEW, "Missing effective contract blocks reuse"),
        Case("valid directive with unrelated future policy",
             approved.records, approved.order,
             (POLICY, Policy(4, date(2026, 11, 1),
                             frozenset(), "future-contract")),
             Decision.REUSE, "Future contract does not retroactively change decision"),
    )
    return cases


def naive_last_correction(case):
    """Baseline: reuse the latest correction with matching requested SKU."""
    candidates = [r for r in case.records if r.correction.requested_sku == case.order.requested_sku
                  and r.correction.recorded_on <= case.order.on_date]
    return Decision.REUSE if candidates else Decision.IGNORE

def naive_latest_approved(case):
    """Baseline: latest 'approved' preference, ignoring policy and full scope."""
    candidates = [r for r in case.records if r.approved_by and r.correction.approved_as_preference
                  and r.correction.requested_sku == case.order.requested_sku
                  and r.correction.recorded_on <= case.order.on_date]
    return Decision.REUSE if candidates else Decision.REVIEW

def scoped_baseline(case):
    """A practical context-aware baseline without authority or contract precedence.

    Checks customer, branch, SKU, effective dates, and availability, but treats
    any matching historical substitution as a reusable preference.
    """
    candidates = [
        r for r in case.records
        if r.correction.customer == case.order.customer
        and r.correction.branch == case.order.branch
        and r.correction.requested_sku == case.order.requested_sku
        and r.correction.recorded_on <= case.order.on_date
        and (r.correction.valid_until is None
             or case.order.on_date <= r.correction.valid_until)
    ]
    if not candidates:
        return Decision.IGNORE
    if not case.order.substitute_available:
        return Decision.REVIEW
    return Decision.REUSE


def scoped(case):
    return resolve(case.records, case.order, case.policies).decision

def metrics(cases, policy):
    counts = {"total": 0, "correct": 0, "unsafe_reuse": 0, "unnecessary_review": 0,
              "missed_reuse": 0}
    for case in cases:
        prediction = policy(case)
        counts["total"] += 1
        counts["correct"] += prediction == case.expected
        counts["unsafe_reuse"] += prediction == Decision.REUSE and case.expected != Decision.REUSE
        counts["unnecessary_review"] += prediction == Decision.REVIEW and case.expected == Decision.IGNORE
        counts["missed_reuse"] += prediction != Decision.REUSE and case.expected == Decision.REUSE
    return counts

def report():
    cases = challenge_cases()
    for name, policy in (("latest correction", naive_last_correction),
                         ("latest approved", naive_latest_approved),
                         ("context baseline", scoped_baseline),
                         ("scope evaluator", scoped)):
        result = metrics(cases, policy)
        print(f"{name:20} correct={result['correct']:2}/{result['total']} "
              f"unsafe_reuse={result['unsafe_reuse']:2} "
              f"unnecessary_review={result['unnecessary_review']:2} "
              f"missed_reuse={result['missed_reuse']:2}")

def challenge_report():
    print("\nComposed challenge cases (synthetic, author-labeled)")
    cases = combined_challenges()
    for name, policy in (("context baseline", scoped_baseline),
                         ("scope evaluator", scoped)):
        result = metrics(cases, policy)
        print(f"{name:20} correct={result['correct']:2}/{result['total']} "
              f"unsafe_reuse={result['unsafe_reuse']:2} "
              f"unnecessary_review={result['unnecessary_review']:2} "
              f"missed_reuse={result['missed_reuse']:2}")

if __name__ == "__main__":
    report()
    challenge_report()

