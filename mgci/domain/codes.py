"""Normalize class codes before they reach scientific computations."""

from decimal import Decimal, InvalidOperation


def class_code(value: object) -> int:
    if isinstance(value, bool):
        raise ValueError('Boolean is not a class code')
    try:
        number = Decimal(str(value))
        if not number.is_finite() or number != number.to_integral_value():
            raise ValueError
        return int(number)
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError(f'Invalid integer class code: {value!r}') from None


def normalize_mapping(items) -> tuple[tuple[int, int], ...]:
    result = {}
    for source, target in items:
        source, target = class_code(source), class_code(target)
        if source in result:
            raise ValueError(f'Duplicate class code: {source}')
        result[source] = target
    return tuple(sorted(result.items()))
