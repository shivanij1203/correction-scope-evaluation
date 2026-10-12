"""Source-linked quote facts and dependency invalidation.

The RFQ example is adapted from Ventura's publicly illustrated workflow.
This is a structured-input experiment, not an email or PDF parser.
"""
from dataclasses import dataclass
from enum import Enum


class Status(str, Enum):
    CURRENT = 'current'
    MISSING = 'missing'
    STALE = 'stale'
    CONFLICT = 'conflict'


@dataclass(frozen=True)
class Fact:
    field: str
    value: str | None
    source: str
    source_revision: int


@dataclass(frozen=True)
class DerivedChoice:
    field: str
    value: str
    dependencies: tuple[str, ...]
    evidence_revision: int
    catalog_revision: int
    policy_revision: int


@dataclass(frozen=True)
class Assessment:
    status: Status
    reasons: tuple[str, ...]
    sources: tuple[str, ...]


def assess(choice: DerivedChoice, facts: tuple[Fact, ...], *,
           evidence_revision: int, catalog_revision: int,
           policy_revision: int) -> Assessment:
    """Only current, unambiguous inputs can support a derived quote choice."""
    reasons = []
    sources = []
    for field in choice.dependencies:
        matching = [f for f in facts if f.field == field]
        if not matching or all(f.value is None for f in matching):
            reasons.append(f'missing {field}')
            continue
        sources.extend(f.source for f in matching)
        if len({f.value for f in matching if f.value is not None}) > 1:
            reasons.append(f'conflicting {field}')
        if any(f.source_revision != evidence_revision for f in matching):
            reasons.append(f'stale {field} evidence')
    if choice.evidence_revision != evidence_revision:
        reasons.append('request revised since choice')
    if choice.catalog_revision != catalog_revision:
        reasons.append('catalog changed since choice')
    if choice.policy_revision != policy_revision:
        reasons.append('operating rules changed since choice')
    if any(x.startswith('conflicting') for x in reasons):
        status = Status.CONFLICT
    elif any(x.startswith('missing') for x in reasons):
        status = Status.MISSING
    elif reasons:
        status = Status.STALE
    else:
        status = Status.CURRENT
    return Assessment(status, tuple(reasons), tuple(sorted(set(sources))))


def public_rfq_example():
    """Adapted from https://ventura.ai/product/; synthetic IDs and revisions."""
    facts = (
        Fact('plywood_spec', '23/32 ply 4x8', 'email:line1', 1),
        Fact('plywood_qty', '120 sheets', 'email:line1', 1),
        Fact('lumber_spec', '#2 SPF 2x4', 'email:line2', 1),
        Fact('lumber_qty', '60 pieces', 'email:line2', 1),
    )
    lumber = DerivedChoice('lumber_sku', 'SPF-248',
                           ('lumber_spec', 'lumber_qty', 'lumber_length'), 1, 3, 2)
    return facts, lumber
