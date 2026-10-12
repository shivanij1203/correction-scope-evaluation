"""Resolve competing correction records without turning observations into policy."""
from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import Iterable
from .scope import Correction, Order, Decision, evaluate


class Authority(str, Enum):
    OBSERVATION = 'observation'
    SALES_APPROVAL = 'sales_approval'
    CUSTOMER_DIRECTIVE = 'customer_directive'


@dataclass(frozen=True)
class CorrectionRecord:
    correction: Correction
    authority: Authority
    evidence_id: str
    approved_by: str | None = None
    supersedes: str | None = None


@dataclass(frozen=True)
class Policy:
    version: int
    effective_from: date
    permitted_substitutes: frozenset[str]
    source_id: str


@dataclass(frozen=True)
class Resolution:
    decision: Decision
    sku: str | None
    applied: tuple[str, ...]
    considered: tuple[str, ...]
    reasons: tuple[str, ...]
    policy_source: str | None


def resolve(records: Iterable[CorrectionRecord], order: Order, policies: Iterable[Policy]) -> Resolution:
    records = tuple(records)
    ids = [r.correction.id for r in records]
    if len(set(ids)) != len(ids):
        raise ValueError('duplicate correction IDs')
    if any(not r.evidence_id for r in records):
        raise ValueError('missing correction provenance')

    eligible_policies = [p for p in policies if p.effective_from <= order.on_date]
    if not eligible_policies:
        return Resolution(Decision.REVIEW, None, (), ids, ('no effective policy',), None)
    newest_date = max(p.effective_from for p in eligible_policies)
    current = [p for p in eligible_policies if p.effective_from == newest_date]
    if len(current) != 1:
        return Resolution(Decision.REVIEW, None, (), ids, ('conflicting effective policies',), None)
    policy = current[0]
    if policy.version != order.policy_version:
        return Resolution(Decision.REVIEW, None, (), ids, ('order policy snapshot is stale',), policy.source_id)

    applicable = []
    for record in records:
        c = record.correction
        if (c.customer, c.branch, c.requested_sku) != (order.customer, order.branch, order.requested_sku):
            continue
        if c.recorded_on > order.on_date or (c.valid_until and order.on_date > c.valid_until):
            continue
        applicable.append(record)

    # A supersession must be explicit and refer to an existing record in the same scope.
    by_id = {r.correction.id: r for r in applicable}
    superseded = set()
    for r in applicable:
        if r.supersedes:
            previous = by_id.get(r.supersedes)
            if previous is None or previous.correction.recorded_on > r.correction.recorded_on:
                return Resolution(Decision.REVIEW, None, (), ids, ('invalid supersession chain',), policy.source_id)
            superseded.add(r.supersedes)
    active = [r for r in applicable if r.correction.id not in superseded]

    # No auto-learning from observations or unapproved sales decisions.
    candidates = []
    for r in active:
        c = r.correction
        if c.policy_version != policy.version:
            continue
        if r.authority == Authority.CUSTOMER_DIRECTIVE and r.approved_by and c.reason == 'customer_preference' and c.approved_as_preference:
            candidates.append(r)

    if not candidates:
        return Resolution(Decision.REVIEW if active else Decision.IGNORE, None, (), ids,
                          ('no approved reusable directive',) if active else ('no applicable corrections',), policy.source_id)
    # A newer timestamp alone does not revoke an earlier directive.
    # Explicit supersession is required to remove the older authority.
    latest = candidates
    skus = {r.correction.substitute_sku for r in latest}
    if len(skus) != 1:
        return Resolution(Decision.REVIEW, None, (), ids, ('conflicting customer directives',), policy.source_id)
    chosen = latest[0].correction.substitute_sku
    if chosen not in policy.permitted_substitutes:
        return Resolution(Decision.REVIEW, None, (), ids, ('substitute disallowed by effective policy',), policy.source_id)
    if not order.substitute_available:
        return Resolution(Decision.REVIEW, None, (), ids, ('substitute currently unavailable',), policy.source_id)
    return Resolution(Decision.REUSE, chosen, tuple(r.correction.id for r in latest), ids,
                      ('approved directive applies under effective policy',), policy.source_id)
