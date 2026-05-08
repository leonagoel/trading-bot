"""
CLI entry point for PrimeTrade Bot.
Uses argparse with a rich, color-coded terminal experience.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from decimal import Decimal
from typing import Optional

from bot.client import BinanceClient, BinanceAPIError
from bot.logging_config import setup_logger
from bot.orders import OrderResult, dispatch_order
from bot.validators import (
    ValidationError,
    validate_order_type,
    validate_price,
    validate_quantity,
    validate_side,
    validate_stop_price,
    validate_symbol,
)

logger = setup_logger("cli")

# ── ANSI helpers ───────────────────────────────────────────────────────────────

RESET  = "\033[0m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BLUE   = "\033[94m"
MAGENTA= "\033[95m"
WHITE  = "\033[97m"

def c(text: str, *codes: str) -> str:
    return "".join(codes) + str(text) + RESET


# ── Banner ─────────────────────────────────────────────────────────────────────

BANNER = f"""
{CYAN}{BOLD}
 ██████╗ ██████╗ ██╗███╗   ███╗███████╗████████╗██████╗  █████╗ ██████╗ ███████╗
 ██╔══██╗██╔══██╗██║████╗ ████║██╔════╝╚══██╔══╝██╔══██╗██╔══██╗██╔══██╗██╔════╝
 ██████╔╝██████╔╝██║██╔████╔██║█████╗     ██║   ██████╔╝███████║██║  ██║█████╗
 ██╔═══╝ ██╔══██╗██║██║╚██╔╝██║██╔══╝     ██║   ██╔══██╗██╔══██║██║  ██║██╔══╝
 ██║     ██║  ██║██║██║ ╚═╝ ██║███████╗   ██║   ██║  ██║██║  ██║██████╔╝███████╗
 ╚═╝     ╚═╝  ╚═╝╚═╝╚═╝     ╚═╝╚══════╝   ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝╚═════╝ ╚══════╝
{RESET}{DIM}  Binance Futures Testnet CLI — v1.0.0{RESET}
{DIM}  ─────────────────────────────────────────────────────────────────────{RESET}
"""


# ── Formatters ─────────────────────────────────────────────────────────────────

def print_order_summary(
    symbol: str,
    side: str,
    order_type: str,
    quantity: Decimal,
    price: Optional[Decimal],
    stop_price: Optional[Decimal],
) -> None:
    """Pretty-print the request parameters before sending."""
    side_color = GREEN if side == "BUY" else RED
    print(f"\n{BOLD}{CYAN}┌{'─'*48}┐{RESET}")
    print(f"{BOLD}{CYAN}│{'  ORDER REQUEST':^48}│{RESET}")
    print(f"{BOLD}{CYAN}├{'─'*48}┤{RESET}")
    rows = [
        ("Symbol",     c(symbol,     BOLD, WHITE)),
        ("Side",       c(side,       BOLD, side_color)),
        ("Type",       c(order_type, BOLD, YELLOW)),
        ("Quantity",   c(str(quantity), BOLD, WHITE)),
    ]
    if price is not None:
        rows.append(("Price",  c(f"${price:,}", BOLD, WHITE)))
    if stop_price is not None:
        rows.append(("Stop ⚡", c(f"${stop_price:,}", BOLD, MAGENTA)))
    for label, value in rows:
        print(f"{BOLD}{CYAN}│{RESET}  {c(f'{label:<12}', DIM)} {value:<50}{BOLD}{CYAN}│{RESET}")
    print(f"{BOLD}{CYAN}└{'─'*48}┘{RESET}\n")


def print_order_result(result: OrderResult) -> None:
    """Pretty-print the API response after an order is placed."""
    status_color = GREEN if result.is_filled else (YELLOW if result.is_open else RED)
    avg = result.avg_price if result.avg_price and result.avg_price != "0" else "—"

    print(f"\n{BOLD}{GREEN}┌{'─'*48}┐{RESET}")
    print(f"{BOLD}{GREEN}│{'  ORDER RESPONSE':^48}│{RESET}")
    print(f"{BOLD}{GREEN}├{'─'*48}┤{RESET}")
    rows = [
        ("Order ID",   c(str(result.order_id), BOLD, WHITE)),
        ("Status",     c(result.status,         BOLD, status_color)),
        ("Exec Qty",   c(result.executed_qty,   BOLD, WHITE)),
        ("Avg Price",  c(avg,                   BOLD, WHITE)),
        ("Client ID",  c(result.client_order_id[:20], DIM)),
    ]
    for label, value in rows:
        print(f"{BOLD}{GREEN}│{RESET}  {c(f'{label:<12}', DIM)} {value:<50}{BOLD}{GREEN}│{RESET}")
    print(f"{BOLD}{GREEN}└{'─'*48}┘{RESET}\n")

    if result.is_filled:
        print(f"  {BOLD}{GREEN}✔  Order FILLED successfully!{RESET}\n")
    elif result.is_open:
        print(f"  {BOLD}{YELLOW}⏳ Order is OPEN (id: {result.order_id}){RESET}\n")
    else:
        print(f"  {BOLD}{RED}✘  Order status: {result.status}{RESET}\n")


def print_error(message: str) -> None:
    print(f"\n  {BOLD}{RED}✘  Error: {message}{RESET}\n")


# ── Argument parser ────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="trading_bot",
        description="PrimeTrade — Binance Futures Testnet CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
{BOLD}Examples:{RESET}
  {DIM}# Market buy 0.01 BTC{RESET}
  python -m bot.cli place --symbol BTCUSDT --side BUY --type MARKET --quantity 0.01

  {DIM}# Limit sell 0.005 ETH at $3000{RESET}
  python -m bot.cli place --symbol ETHUSDT --side SELL --type LIMIT --quantity 0.005 --price 3000

  {DIM}# Stop-market buy 0.01 BTC triggered at $70000{RESET}
  python -m bot.cli place --symbol BTCUSDT --side BUY --type STOP_MARKET --quantity 0.01 --stop-price 70000

  {DIM}# Check account balance{RESET}
  python -m bot.cli account

  {DIM}# List open orders for BTCUSDT{RESET}
  python -m bot.cli open-orders --symbol BTCUSDT
        """,
    )

    sub = parser.add_subparsers(dest="command", required=True)

    # ── place ─────────────────────────────────────────────────────────────────
    place = sub.add_parser("place", help="Place a new futures order")
    place.add_argument("--symbol",     required=True,  help="Trading pair (e.g. BTCUSDT)")
    place.add_argument("--side",       required=True,  help="BUY or SELL")
    place.add_argument("--type",       required=True,  dest="order_type", help="MARKET | LIMIT | STOP_MARKET")
    place.add_argument("--quantity",   required=True,  help="Order size")
    place.add_argument("--price",      default=None,   help="Limit price (LIMIT orders)")
    place.add_argument("--stop-price", default=None,   dest="stop_price", help="Stop trigger price (STOP_MARKET orders)")
    place.add_argument("--tif",        default="GTC",  help="Time-in-force for LIMIT: GTC | IOC | FOK (default: GTC)")
    place.add_argument("--json",       action="store_true", dest="output_json", help="Print raw JSON response")

    # ── account ───────────────────────────────────────────────────────────────
    sub.add_parser("account", help="Show account balances and positions")

    # ── open-orders ───────────────────────────────────────────────────────────
    oo = sub.add_parser("open-orders", help="List open orders")
    oo.add_argument("--symbol", default=None, help="Filter by symbol (optional)")

    # ── ping ──────────────────────────────────────────────────────────────────
    sub.add_parser("ping", help="Check connectivity to Binance Futures Testnet")

    return parser


# ── Command handlers ───────────────────────────────────────────────────────────

def cmd_place(args: argparse.Namespace, client: BinanceClient) -> int:
    """Handle the `place` sub-command."""
    try:
        symbol     = validate_symbol(args.symbol)
        side       = validate_side(args.side)
        order_type = validate_order_type(args.order_type)
        quantity   = validate_quantity(args.quantity)
        price      = validate_price(args.price, order_type)
        stop_price = validate_stop_price(args.stop_price, order_type)
    except ValidationError as exc:
        print_error(str(exc))
        logger.error("Validation failed: %s", exc)
        return 1

    print_order_summary(symbol, side, order_type, quantity, price, stop_price)

    try:
        result = dispatch_order(
            client=client,
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=quantity,
            price=price,
            stop_price=stop_price,
            time_in_force=args.tif,
        )
    except BinanceAPIError as exc:
        print_error(f"[Binance {exc.code}] {exc.message}")
        logger.error("Order failed: %s", exc)
        return 1
    except Exception as exc:
        print_error(f"Unexpected error: {exc}")
        logger.exception("Unexpected error during order placement")
        return 1

    if args.output_json:
        print(json.dumps(result.raw, indent=2))
    else:
        print_order_result(result)

    return 0


def cmd_account(client: BinanceClient) -> int:
    """Handle the `account` sub-command."""
    try:
        data = client.get_account()
    except BinanceAPIError as exc:
        print_error(f"[Binance {exc.code}] {exc.message}")
        return 1

    assets = [a for a in data.get("assets", []) if float(a.get("walletBalance", 0)) > 0]
    positions = [p for p in data.get("positions", []) if float(p.get("positionAmt", 0)) != 0]

    print(f"\n{BOLD}{CYAN}  ── Account Balances ──────────────────────────{RESET}")
    if assets:
        for a in assets:
            print(f"  {c(a['asset']+':', BOLD, WHITE):<20} {c(a['walletBalance'], GREEN)}")
    else:
        print(f"  {DIM}No non-zero balances found.{RESET}")

    print(f"\n{BOLD}{CYAN}  ── Open Positions ────────────────────────────{RESET}")
    if positions:
        for p in positions:
            amt = float(p.get("positionAmt", 0))
            pnl = float(p.get("unrealizedProfit", 0))
            color = GREEN if pnl >= 0 else RED
            print(f"  {c(p['symbol']+':', BOLD, WHITE):<20} amt={amt:+.6f}  unrealizedPnL={c(f'{pnl:+.4f}', color)}")
    else:
        print(f"  {DIM}No open positions.{RESET}")
    print()
    return 0


def cmd_open_orders(args: argparse.Namespace, client: BinanceClient) -> int:
    """Handle the `open-orders` sub-command."""
    try:
        orders = client.get_open_orders(symbol=args.symbol)
    except BinanceAPIError as exc:
        print_error(f"[Binance {exc.code}] {exc.message}")
        return 1

    if not orders:
        print(f"\n  {DIM}No open orders found.{RESET}\n")
        return 0

    print(f"\n{BOLD}{CYAN}  ── Open Orders ({len(orders)}) ──────────────────────{RESET}")
    for o in orders:
        side_color = GREEN if o["side"] == "BUY" else RED
        print(
            f"  {c(str(o['orderId']), BOLD):<14} "
            f"{c(o['symbol'], WHITE):<12} "
            f"{c(o['side'], side_color):<8} "
            f"{c(o['type'], YELLOW):<14} "
            f"qty={o['origQty']}  price={o.get('price','—')}"
        )
    print()
    return 0


def cmd_ping(client: BinanceClient) -> int:
    """Handle the `ping` sub-command."""
    if client.ping():
        print(f"\n  {BOLD}{GREEN}✔  Testnet is reachable.{RESET}\n")
        return 0
    else:
        print(f"\n  {BOLD}{RED}✘  Testnet unreachable. Check your connection.{RESET}\n")
        return 1


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    print(BANNER)

    api_key    = os.getenv("BINANCE_TESTNET_API_KEY", "")
    api_secret = os.getenv("BINANCE_TESTNET_API_SECRET", "")

    if not api_key or not api_secret:
        print_error(
            "API credentials not set.\n"
            "  Export BINANCE_TESTNET_API_KEY and BINANCE_TESTNET_API_SECRET, "
            "or add them to a .env file."
        )
        sys.exit(1)

    parser = build_parser()
    args = parser.parse_args()

    client = BinanceClient(api_key=api_key, api_secret=api_secret)

    if args.command == "place":
        sys.exit(cmd_place(args, client))
    elif args.command == "account":
        sys.exit(cmd_account(client))
    elif args.command == "open-orders":
        sys.exit(cmd_open_orders(args, client))
    elif args.command == "ping":
        sys.exit(cmd_ping(client))
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
