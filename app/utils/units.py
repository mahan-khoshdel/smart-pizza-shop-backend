from decimal import Decimal


UNIT_CONVERSIONS = {
    ("KILOGRAM", "GRAM"): Decimal("1000"),
    ("GRAM", "GRAM"): Decimal("1"),
    ("LITER", "MILLILITER"): Decimal("1000"),
    ("MILLILITER", "MILLILITER"): Decimal("1"),
    ("PIECE", "PIECE"): Decimal("1"),
}


def convert_quantity(
    quantity: Decimal,
    from_unit: str,
    to_unit: str,
) -> Decimal:
    """Convert a quantity between supported units."""

    if from_unit == to_unit:
        return quantity

    conversion = UNIT_CONVERSIONS.get(
        (from_unit, to_unit)
    )

    if conversion is None:
        raise ValueError(
            f"Cannot convert {from_unit} to {to_unit}."
        )

    return quantity * conversion