"""
Order placement logic.
Bridges the validated CLI parameters to the BinanceClient API layer.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, Optional

from bot.client import BinanceClient, BinanceAPIError
from bot.logging_config import setup_logger

logger = setup_logger(__name__)


class OrderResult:
    """Structured representation of a placed order response."""

    def __init__(self, raw: Dict[str, Any]) -> None:
        self.raw = raw
        self.order_id: int = raw.get("orderId", 0)
        self.symbol: str = raw.get("symbol", "")
        self.side: str = raw.get("side", "")
        self.order_type: str = raw.get("type", "")
        self.status: str = raw.get("status", "")
        self.price: str = raw.get("price", "0")
        self.avg_price: str = raw.get("avgPrice", "0")
        self.orig_qty: str = raw.get("origQty", "0")
        self.executed_qty: str = raw.get("executedQty", "0")
        self.time_in_force: str = raw.get("timeInForce", "")
        self.client_order_id: str = raw.get("clientOrderId", "")
        self.update_time: int = raw.get("updateTime", 0)

    @property
    def is_filled(self) -> bool:
        return self.status == "FILLED"

    @property
    def is_open(self) -> bool:
        return self.status in {"NEW", "PARTIALLY_FILLED"}

    def __repr__(self) -> str:
        return (
            f"OrderResult(id={self.order_id}, symbol={self.symbol}, "
            f"side={self.side}, type={self.order_type}, status={self.status})"
        )


def place_market_order(
    client: BinanceClient,
    symbol: str,
    side: str,
    quantity: Decimal,
) -> OrderResult:
    """
    Place a MARKET order on Binance Futures Testnet.

    Args:
        client:   Authenticated BinanceClient.
        symbol:   Trading pair (e.g. 'BTCUSDT').
        side:     'BUY' or 'SELL'.
        quantity: Order size.

    Returns:
        OrderResult wrapping the API response.
    """
    logger.info("Submitting MARKET order | %s %s qty=%s", side, symbol, quantity)

    response = client.place_order(
        symbol=symbol,
        side=side,
        type="MARKET",
        quantity=str(quantity),
    )
    result = OrderResult(response)
    logger.info("MARKET order confirmed | %s", result)
    return result


def place_limit_order(
    client: BinanceClient,
    symbol: str,
    side: str,
    quantity: Decimal,
    price: Decimal,
    time_in_force: str = "GTC",
) -> OrderResult:
    """
    Place a LIMIT order on Binance Futures Testnet.

    Args:
        client:         Authenticated BinanceClient.
        symbol:         Trading pair.
        side:           'BUY' or 'SELL'.
        quantity:       Order size.
        price:          Limit price.
        time_in_force:  'GTC' (default), 'IOC', or 'FOK'.

    Returns:
        OrderResult wrapping the API response.
    """
    logger.info(
        "Submitting LIMIT order | %s %s qty=%s @ %s [%s]",
        side, symbol, quantity, price, time_in_force,
    )

    response = client.place_order(
        symbol=symbol,
        side=side,
        type="LIMIT",
        quantity=str(quantity),
        price=str(price),
        timeInForce=time_in_force,
    )
    result = OrderResult(response)
    logger.info("LIMIT order confirmed | %s", result)
    return result


def place_stop_market_order(
    client: BinanceClient,
    symbol: str,
    side: str,
    quantity: Decimal,
    stop_price: Decimal,
) -> OrderResult:
    """
    Place a STOP_MARKET order (bonus order type) on Binance Futures Testnet.

    Args:
        client:     Authenticated BinanceClient.
        symbol:     Trading pair.
        side:       'BUY' or 'SELL'.
        quantity:   Order size.
        stop_price: Trigger price.

    Returns:
        OrderResult wrapping the API response.
    """
    logger.info(
        "Submitting STOP_MARKET order | %s %s qty=%s stopPrice=%s",
        side, symbol, quantity, stop_price,
    )

    response = client.place_order(
        symbol=symbol,
        side=side,
        type="STOP_MARKET",
        quantity=str(quantity),
        stopPrice=str(stop_price),
    )
    result = OrderResult(response)
    logger.info("STOP_MARKET order confirmed | %s", result)
    return result


def dispatch_order(
    client: BinanceClient,
    symbol: str,
    side: str,
    order_type: str,
    quantity: Decimal,
    price: Optional[Decimal] = None,
    stop_price: Optional[Decimal] = None,
    time_in_force: str = "GTC",
) -> OrderResult:
    """
    Route to the correct placement function based on order_type.

    Args:
        client:         Authenticated BinanceClient.
        symbol:         Trading pair.
        side:           'BUY' or 'SELL'.
        order_type:     'MARKET', 'LIMIT', or 'STOP_MARKET'.
        quantity:       Order size.
        price:          Required for LIMIT.
        stop_price:     Required for STOP_MARKET.
        time_in_force:  Relevant for LIMIT orders.

    Returns:
        OrderResult from whichever placement function runs.

    Raises:
        ValueError: If order_type is unrecognised.
        BinanceAPIError: Propagated from the client on API failures.
    """
    if order_type == "MARKET":
        return place_market_order(client, symbol, side, quantity)
    elif order_type == "LIMIT":
        if price is None:
            raise ValueError("price is required for LIMIT orders")
        return place_limit_order(client, symbol, side, quantity, price, time_in_force)
    elif order_type == "STOP_MARKET":
        if stop_price is None:
            raise ValueError("stop_price is required for STOP_MARKET orders")
        return place_stop_market_order(client, symbol, side, quantity, stop_price)
    else:
        raise ValueError(f"Unknown order type: {order_type}")
