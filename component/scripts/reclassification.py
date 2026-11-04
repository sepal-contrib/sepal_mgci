"""Canonical numeric class codes at the boundary between form state and GEE."""

from decimal import Decimal, InvalidOperation


def class_code(value):
    """Accept integer codes and their JSON strings without truncating fractions."""
    try:
        number = Decimal(str(value))
        if not number.is_finite() or number != number.to_integral_value():
            raise ValueError
        return int(number)
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError(f"Invalid land cover class code: {value!r}") from None


def normalize_matrix(matrix):
    result = {}
    for source, target in (matrix or {}).items():
        source = class_code(source)
        if source in result:
            raise ValueError(f"Duplicate land cover class code: {source}")
        result[source] = class_code(target)
    return result
