"""
Binance Futures Testnet REST client.
Wraps raw HTTP interactions — signing, error handling, retries.
"""

from __future__ import annotations

import hashlib
import hmac
import time
from typing import Any, Dict, Optional
from urllib.parse import urlencode

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from bot.logging_config import setup_logger

logger = setup_logger(__name__)

BASE_URL = "https://testnet.binancefuture.com"
API_VERSION = "/fapi/v1"


class BinanceAPIError(Exception):
    """Raised when the Binance API returns a non-2xx response or an error payload."""

    def __init__(self, code: int, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"Binance API Error {code}: {message}")


class BinanceClient:
    """
    Minimal Binance Futures Testnet REST client.

    Handles:
    - HMAC-SHA256 request signing
    - Automatic timestamp injection
    - Structured request/response logging
    - Retry logic for transient network errors
    """

    def __init__(self, api_key: str, api_secret: str, timeout: int = 10) -> None:
        """
        Initialise the client.

        Args:
            api_key:    Binance Futures Testnet API key.
            api_secret: Binance Futures Testnet API secret.
            timeout:    HTTP request timeout in seconds.
        """
        self._api_key = api_key
        self._api_secret = api_secret.encode()
        self._timeout = timeout
        self._session = self._build_session()
        logger.info("BinanceClient initialised (testnet)")

    # ── Session / HTTP helpers ────────────────────────────────────────────────

    @staticmethod
    def _build_session() -> requests.Session:
        """Return a requests.Session with retry logic baked in."""
        session = requests.Session()
        retry = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist={429, 500, 502, 503, 504},
            allowed_methods={"GET", "POST", "DELETE"},
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("https://", adapter)
        return session

    def _sign(self, params: Dict[str, Any]) -> str:
        """HMAC-SHA256 sign a query-string dict and return the hex signature."""
        query_string = urlencode(params)
        return hmac.new(self._api_secret, query_string.encode(), hashlib.sha256).hexdigest()

    def _headers(self) -> Dict[str, str]:
        return {"X-MBX-APIKEY": self._api_key, "Content-Type": "application/x-www-form-urlencoded"}

    def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        signed: bool = False,
    ) -> Dict[str, Any]:
        """
        Execute an HTTP request against the Binance Futures Testnet.

        Args:
            method:   HTTP verb ('GET', 'POST', 'DELETE').
            endpoint: API endpoint path (e.g. '/order').
            params:   Query/body parameters.
            signed:   Whether to inject timestamp and HMAC signature.

        Returns:
            Parsed JSON response as a dict.

        Raises:
            BinanceAPIError: On API-level errors.
            requests.RequestException: On network-level errors.
        """
        url = BASE_URL + API_VERSION + endpoint
        params = dict(params or {})

        if signed:
            params["timestamp"] = int(time.time() * 1000)
            params["signature"] = self._sign(params)

        logger.debug("→ %s %s | params=%s", method, endpoint, {k: v for k, v in params.items() if k != "signature"})

        try:
            if method == "GET":
                response = self._session.get(url, params=params, headers=self._headers(), timeout=self._timeout)
            elif method == "POST":
                response = self._session.post(url, data=params, headers=self._headers(), timeout=self._timeout)
            elif method == "DELETE":
                response = self._session.delete(url, params=params, headers=self._headers(), timeout=self._timeout)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            logger.debug("← %s %s | status=%d", method, endpoint, response.status_code)

            data = response.json()

            if not response.ok:
                code = data.get("code", response.status_code)
                msg = data.get("msg", response.text)
                logger.error("API error %s: %s", code, msg)
                raise BinanceAPIError(code=int(code), message=msg)

            return data

        except requests.exceptions.Timeout:
            logger.error("Request timed out: %s %s", method, endpoint)
            raise
        except requests.exceptions.ConnectionError as exc:
            logger.error("Network error: %s", exc)
            raise

    # ── Public API ────────────────────────────────────────────────────────────

    def ping(self) -> bool:
        """Return True if the testnet is reachable."""
        try:
            self._request("GET", "/ping")
            logger.info("Testnet ping successful")
            return True
        except Exception as exc:
            logger.warning("Testnet ping failed: %s", exc)
            return False

    def get_server_time(self) -> int:
        """Return Binance server time in milliseconds."""
        data = self._request("GET", "/time")
        return int(data["serverTime"])

    def get_exchange_info(self) -> Dict[str, Any]:
        """Fetch exchange info (symbols, filters, limits)."""
        return self._request("GET", "/exchangeInfo")

    def get_account(self) -> Dict[str, Any]:
        """Fetch account balance and positions."""
        return self._request("GET", "/account", signed=True)

    def place_order(self, **kwargs: Any) -> Dict[str, Any]:
        """
        Place a new futures order.

        Keyword Args:
            symbol (str):      Trading pair, e.g. 'BTCUSDT'.
            side (str):        'BUY' or 'SELL'.
            type (str):        'MARKET', 'LIMIT', or 'STOP_MARKET'.
            quantity (str):    Order quantity.
            price (str):       Limit price (required for LIMIT orders).
            stopPrice (str):   Stop trigger price (required for STOP_MARKET).
            timeInForce (str): 'GTC', 'IOC', 'FOK' (required for LIMIT).

        Returns:
            Full order response dict from Binance.
        """
        logger.info(
            "Placing order | symbol=%s side=%s type=%s qty=%s",
            kwargs.get("symbol"),
            kwargs.get("side"),
            kwargs.get("type"),
            kwargs.get("quantity"),
        )
        response = self._request("POST", "/order", params=kwargs, signed=True)
        logger.info(
            "Order placed | orderId=%s status=%s",
            response.get("orderId"),
            response.get("status"),
        )
        return response

    def cancel_order(self, symbol: str, order_id: int) -> Dict[str, Any]:
        """Cancel an open order by ID."""
        params = {"symbol": symbol, "orderId": order_id}
        logger.info("Cancelling order %s on %s", order_id, symbol)
        return self._request("DELETE", "/order", params=params, signed=True)

    def get_order(self, symbol: str, order_id: int) -> Dict[str, Any]:
        """Query status of a specific order."""
        params = {"symbol": symbol, "orderId": order_id}
        return self._request("GET", "/order", params=params, signed=True)

    def get_open_orders(self, symbol: Optional[str] = None) -> list:
        """Return all open orders, optionally filtered by symbol."""
        params = {}
        if symbol:
            params["symbol"] = symbol
        return self._request("GET", "/openOrders", params=params, signed=True)
