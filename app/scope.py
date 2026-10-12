from dataclasses import dataclass
from datetime import date
from enum import Enum


class Decision(str, Enum):
    REUSE = 'reuse'
    REVIEW = 'review'
    IGNORE = 'ignore'


@dataclass(frozen=True)
class Correction:
    id: str
    customer: str
    branch: str
    requested_sku: str
    substitute_sku: str
    reason: str
    recorded_on: date
    valid_until: date | None
    policy_version: int
    source_order: str
    approved_as_preference: bool = False


@dataclass(frozen=True)
class Order:
    id: str
    customer: str
    branch: str
    requested_sku: str
    on_date: date
    policy_version: int
    requested_available: bool
    substitute_available: bool


@dataclass(frozen=True)
class Result:
    decision: Decision
    proposed_sku: str | None
    reasons: tuple[str, ...]
    correction_id: str
    source_order: str


def naive_reuse(c: Correction, o: Order) -> bool:
    # Common but unsafe baseline: a previous substitution for the same SKU.
    return c.requested_sku == o.requested_sku


def evaluate(c: Correction, o: Order) -> Result:
    reasons = []
    if c.requested_sku != o.requested_sku:
        return Result(Decision.IGNORE, None, ('different requested product',), c.id, c.source_order)
    if c.customer != o.customer:
        return Result(Decision.IGNORE, None, ('different customer',), c.id, c.source_order)
    if c.branch != o.branch:
        return Result(Decision.IGNORE, None, ('different branch',), c.id, c.source_order)
    if o.on_date < c.recorded_on:
        return Result(Decision.IGNORE, None, ('correction did not exist yet',), c.id, c.source_order)
    if c.valid_until is not None and o.on_date > c.valid_until:
        return Result(Decision.IGNORE, None, ('correction expired',), c.id, c.source_order)
    if c.policy_version != o.policy_version:
        return Result(Decision.REVIEW, None, ('policy changed since correction',), c.id, c.source_order)
    if not o.substitute_available:
        return Result(Decision.REVIEW, None, ('substitute unavailable',), c.id, c.source_order)
    if c.reason == 'stockout':
        if o.requested_available:
            return Result(Decision.IGNORE, None, ('original product back in stock',), c.id, c.source_order)
        return Result(Decision.REVIEW, c.substitute_sku, ('stockout substitution requires fresh approval',), c.id, c.source_order)
    if c.reason == 'customer_preference' and c.approved_as_preference:
        return Result(Decision.REUSE, c.substitute_sku, ('approved customer preference within scope',), c.id, c.source_order)
    return Result(Decision.REVIEW, c.substitute_sku, ('one-time correction, scope not established',), c.id, c.source_order)
