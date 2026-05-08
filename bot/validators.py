"""
Input validation for trading parameters.
All validation logic lives here — CLI and programmatic callers both use this.
"""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from typing import Optional

from bot.logging_config import setup_logger

logger = setup_logger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────────
VALID_SIDES = {"BUY", "SELL"}
VALID_ORDER_TYPES = {"MARKET", "LIMIT", "STOP_MARKET"}
SYMBOL_PATTERN = re.compile(r"^[A-Z]{2,10}USDT$")

MIN_QUANTITY = Decimal("0.00000001")
MAX_QUANTITY = Decimal("1_000_000")
MIN_PRICE = Decimal("0.00000001")
MAX_PRICE = Decimal("10_000_000")


class ValidationError(ValueError):
    """Raised when user-supplied trading parameters fail validation."""


def validate_symbol(symbol: str) -> str:
    """
    Validate and normalise a trading symbol.

    Args:
        symbol: Raw symbol string, e.g. 'btcusdt' or 'BTCUSDT'.

    Returns:
        Upper-cased, validated symbol.

    Raises:
        ValidationError: If the symbol format is invalid.
    """
    normalised = symbol.strip().upper()
    if not SYMBOL_PATTERN.match(normalised):
        raise ValidationError(
            f"Invalid symbol '{symbol}'. "
            "Expected format: <BASE>USDT (e.g. BTCUSDT, ETHUSDT)."
        )
    logger.debug("Symbol validated: %s", normalised)
    return normalised


def validate_side(side: str) -> str:
    """
    Validate order side.

    Args:
        side: 'BUY' or 'SELL' (case-insensitive).

    Returns:
        Upper-cased side string.

    Raises:
        ValidationError: If side is not BUY or SELL.
    """
    normalised = side.strip().upper()
    if normalised not in VALID_SIDES:
        raise ValidationError(
            f"Invalid side '{side}'. Must be one of: {', '.join(sorted(VALID_SIDES))}."
        )
    logger.debug("Side validated: %s", normalised)
    return normalised


def validate_order_type(order_type: str) -> str:
    """
    Validate order type.

    Args:
        order_type: 'MARKET', 'LIMIT', or 'STOP_MARKET' (case-insensitive).

    Returns:
        Upper-cased order type string.

    Raises:
        ValidationError: If type is unsupported.
    """
    normalised = order_type.strip().upper()
    if normalised not in VALID_ORDER_TYPES:
        raise ValidationError(
            f"Invalid order type '{order_type}'. "
            f"Must be one of: {', '.join(sorted(VALID_ORDER_TYPES))}."
        )
    logger.debug("Order type validated: %s", normalised)
    return normalised


def validate_quantity(quantity: str | float) -> Decimal:
    """
    Validate order quantity.

    Args:
        quantity: Quantity as string or float.

    Returns:
        Validated Decimal quantity.

    Raises:
        ValidationError: If quantity is not a positive finite number within bounds.
    """
    try:
        qty = Decimal(str(quantity))
    except InvalidOperation:
        raise ValidationError(f"Quantity '{quantity}' is not a valid number.")

    if qty <= 0:
        raise ValidationError(f"Quantity must be positive, got {qty}.")
    if qty < MIN_QUANTITY:
        raise ValidationError(f"Quantity {qty} is below minimum allowed ({MIN_QUANTITY}).")
    if qty > MAX_QUANTITY:
        raise ValidationError(f"Quantity {qty} exceeds maximum allowed ({MAX_QUANTITY}).")

    logger.debug("Quantity validated: %s", qty)
    return qty


def validate_price(price: str | float, order_type: str) -> Optional[Decimal]:
    """
    Validate order price.

    For MARKET orders price is not required (returns None).
    For LIMIT / STOP_MARKET orders it is mandatory and must be positive.

    Args:
        price: Price as string or float, or None.
        order_type: The order type (validated).

    Returns:
        Validated Decimal price, or None for MARKET orders.

    Raises:
        ValidationError: If price is required but missing/invalid.
    """
    if order_type == "MARKET":
        if price is not None:
            logger.warning("Price supplied for MARKET order — it will be ignored.")
        return None

    # LIMIT and STOP_MARKET require a price
    if price is None:
        raise ValidationError(f"A price is required for {order_type} orders.")

    try:
        prc = Decimal(str(price))
    except InvalidOperation:
        raise ValidationError(f"Price '{price}' is not a valid number.")

    if prc <= 0:
        raise ValidationError(f"Price must be positive, got {prc}.")
    if prc < MIN_PRICE:
        raise ValidationError(f"Price {prc} is below minimum allowed ({MIN_PRICE}).")
    if prc > MAX_PRICE:
        raise ValidationError(f"Price {prc} exceeds maximum allowed ({MAX_PRICE}).")

    logger.debug("Price validated: %s", prc)
    return prc


def validate_stop_price(stop_price: str | float | None, order_type: str) -> Optional[Decimal]:
    """
    Validate stop price for STOP_MARKET orders.

    Args:
        stop_price: Stop price value or None.
        order_type: The order type.

    Returns:
        Validated Decimal stop price, or None.

    Raises:
        ValidationError: If stop price is required but missing/invalid.
    """
    if order_type != "STOP_MARKET":
        return None

    if stop_price is None:
        raise ValidationError("A stopPrice is required for STOP_MARKET orders.")

    try:
        sp = Decimal(str(stop_price))
    except InvalidOperation:
        raise ValidationError(f"Stop price '{stop_price}' is not a valid number.")

    if sp <= 0:
        raise ValidationError(f"Stop price must be positive, got {sp}.")

    logger.debug("Stop price validated: %s", sp)
    return sp
