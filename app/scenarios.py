from datetime import date
from .scope import Correction, Order, Decision

BASE = Correction('corr-17', 'acme', 'north', 'PLY-23', 'PLY-ALT', 'stockout', date(2026, 9, 1), date(2026, 10, 31), 3, 'quote-100')


def cases():
    def order(id, **changes):
        fields = dict(id=id, customer='acme', branch='north', requested_sku='PLY-23', on_date=date(2026, 10, 12), policy_version=3, requested_available=False, substitute_available=True)
        fields.update(changes)
        return Order(**fields)

    pref = Correction('corr-18', 'acme', 'north', 'PLY-23', 'PLY-ALT', 'customer_preference', date(2026, 9, 1), None, 3, 'quote-101', True)
    return [
        ('temporary stockout', BASE, order('o1'), Decision.REVIEW),
        ('stock restored', BASE, order('o2', requested_available=True), Decision.IGNORE),
        ('different branch', BASE, order('o3', branch='south'), Decision.IGNORE),
        ('different customer', BASE, order('o4', customer='beta'), Decision.IGNORE),
        ('expired', BASE, order('o5', on_date=date(2026, 11, 1)), Decision.IGNORE),
        ('policy revision', BASE, order('o6', policy_version=4), Decision.REVIEW),
        ('substitute out of stock', BASE, order('o7', substitute_available=False), Decision.REVIEW),
        ('approved preference', pref, order('o8'), Decision.REUSE),
        ('preference under new policy', pref, order('o9', policy_version=4), Decision.REVIEW),
        ('past order', pref, order('o10', on_date=date(2026, 8, 1)), Decision.IGNORE),
    ]
