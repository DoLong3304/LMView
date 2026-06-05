"""
OKX exchange client implementation.

Implements the ExchangeClient interface for OKX's REST and WebSocket APIs.
All OKX-specific URLs, endpoints, and protocols are encapsulated here.
"""

import json
import logging
import time

import requests

from exchanges.base import ExchangeClient
from exchanges.okx import mappers

log = logging.getLogger(__name__)

# ── OKX constants ────────────────────────────────────────────────────────────
REST_INSTRUMENTS_URL = "https://www.okx.com/api/v5/public/instruments"
REST_CANDLES_URL     = "https://www.okx.com/api/v5/market/candles"
WS_PUBLIC_URL        = "wss://ws.okx.com:8443/ws/v5/public"
EPOCH_MS             = 1_500_000_000_000  # ~2017-07-14


class OKXClient(ExchangeClient):
    """OKX exchange implementation.

    Usage::

        client = OKXClient(max_retries=5, request_delay=0.12)
        symbols = client.fetch_symbols("USDT")
        klines  = client.fetch_klines("BTCUSDT", start_ms, end_ms)
    """

    def __init__(self, max_retries: int = 5, request_delay: float = 0.12):
        self.max_retries = max_retries
        self.request_delay = request_delay

    # ── REST: Symbols ────────────────────────────────────────────────────────

    def fetch_symbols(self, quote_asset: str = "USDT") -> list[str]:
        """Fetch all active spot trading pairs from OKX."""
        for attempt in range(self.max_retries):
            try:
                log.info("Fetching %s trading pairs from OKX REST API...", quote_asset)
                resp = requests.get(
                    REST_INSTRUMENTS_URL,
                    params={"instType": "SPOT"},
                    timeout=15,
                )
                resp.raise_for_status()
                data = resp.json()

                if data.get("code") != "0":
                    log.warning("OKX API error: %s", data.get("msg"))
                    time.sleep(2 ** attempt)
                    continue

                instruments = data.get("data", [])
                symbols = [
                    mappers.normalize_symbol(inst["instId"])
                    for inst in instruments
                    if inst.get("quoteCcy") == quote_asset
                    and inst.get("state") == "live"
                ]
                log.info("Found %d active %s spot pairs on OKX.", len(symbols), quote_asset)
                return sorted(symbols)
            except Exception as e:
                log.warning("fetch_symbols attempt %d failed: %s", attempt + 1, e)
                time.sleep(2 ** attempt)
        raise RuntimeError("Cannot fetch symbol list from OKX after retries.")

    # ── REST: Klines ─────────────────────────────────────────────────────────

    def fetch_klines(
        self,
        symbol: str,
        start_ms: int,
        end_ms: int,
        interval: str = "1m",
        batch_limit: int = 100,
    ) -> list[list]:
        """Fetch OHLCV klines with auto-pagination.

        OKX API returns max 100 candles per request.
        """
        all_klines: list[list] = []
        current_end = end_ms

        # Convert symbol BTCUSDT -> BTC-USDT
        inst_id = f"{symbol[:-4]}-{symbol[-4:]}"

        # Map interval: 1m -> 1m, 1h -> 1H (OKX format)
        okx_interval = interval.upper() if interval != "1m" else "1m"

        while current_end > start_ms:
            for attempt in range(self.max_retries):
                try:
                    resp = requests.get(
                        REST_CANDLES_URL,
                        params={
                            "instId": inst_id,
                            "bar": okx_interval,
                            "before": str(start_ms),
                            "after": str(current_end),
                            "limit": str(batch_limit),
                        },
                        timeout=15,
                    )

                    if resp.status_code == 429:
                        retry_after = int(resp.headers.get("Retry-After", 60))
                        log.warning("[%s] Rate limited. Sleeping %ds.", symbol, retry_after)
                        time.sleep(retry_after)
                        continue

                    resp.raise_for_status()
                    data = resp.json()

                    if data.get("code") != "0":
                        log.warning("[%s] OKX API error: %s", symbol, data.get("msg"))
                        time.sleep(2 ** attempt)
                        continue

                    batch = data.get("data", [])
                    break
                except Exception as e:
                    log.warning("[%s] klines attempt %d failed: %s", symbol, attempt + 1, e)
                    time.sleep(2 ** attempt)
            else:
                log.error("[%s] Giving up on window ending %d.", symbol, current_end)
                break

            if not batch:
                break

            all_klines.extend(batch)

            # OKX returns newest first, so last item is oldest
            oldest_time = int(batch[-1][0])
            if oldest_time >= current_end:
                break
            current_end = oldest_time
            time.sleep(self.request_delay)

        return all_klines

    def fetch_first_available_start(self, symbol: str) -> int:
        """Return the earliest available 1m candle open time for a symbol."""
        inst_id = f"{symbol[:-4]}-{symbol[-4:]}"

        for attempt in range(self.max_retries):
            try:
                resp = requests.get(
                    REST_CANDLES_URL,
                    params={
                        "instId": inst_id,
                        "bar": "1m",
                        "limit": "1",
                    },
                    timeout=15,
                )

                if resp.status_code == 429:
                    retry_after = int(resp.headers.get("Retry-After", 60))
                    log.warning("[%s] Rate limited. Sleeping %ds.", symbol, retry_after)
                    time.sleep(retry_after)
                    continue

                resp.raise_for_status()
                data = resp.json()

                if data.get("code") == "0":
                    rows = data.get("data", [])
                    if rows:
                        return int(rows[0][0])
                return EPOCH_MS
            except Exception as e:
                log.warning("[%s] first-candle probe attempt %d failed: %s", symbol, attempt + 1, e)
                time.sleep(2 ** attempt)
        return EPOCH_MS

    # ── WebSocket URL builders ───────────────────────────────────────────────

    def build_ticker_stream_url(self) -> str:
        """OKX uses public WebSocket URL with channel subscription."""
        return WS_PUBLIC_URL

    def build_combined_stream_url(self, streams: list[str]) -> str:
        """OKX uses single WebSocket with multiple channel subscriptions."""
        return WS_PUBLIC_URL

    # ── Stream name builders ─────────────────────────────────────────────────

    def trade_stream_name(self, symbol: str) -> str:
        """OKX trade channel format: trades for BTC-USDT."""
        inst_id = f"{symbol[:-4]}-{symbol[-4:]}"
        return f"trades:{inst_id}"

    def kline_stream_name(self, symbol: str, interval: str) -> str:
        """OKX kline channel format: candle1s for BTC-USDT."""
        inst_id = f"{symbol[:-4]}-{symbol[-4:]}"
        # OKX uses candle1s, candle1m, candle1H, etc.
        okx_interval = interval.replace("s", "s").replace("m", "m").replace("h", "H").replace("d", "D")
        return f"candle{okx_interval}:{inst_id}"

    def depth_stream_name(self, symbol: str, level: str, update_ms: str) -> str:
        """OKX depth channel format: books5 for BTC-USDT."""
        inst_id = f"{symbol[:-4]}-{symbol[-4:]}"
        return f"books{level}:{inst_id}"

    # ── Data mappers (delegate to mappers module) ────────────────────────────

    def map_ticker(self, raw: dict) -> dict:
        return mappers.map_ticker(raw)

    def map_trade(self, raw: dict) -> dict:
        return mappers.map_agg_trade(raw)

    def map_kline(self, raw: dict) -> dict:
        return mappers.map_kline(raw)

    def map_depth(self, raw: dict) -> dict:
        return mappers.map_depth(raw)

    # --- Subscription frame builder (OKX protocol) ---

    def build_subscribe_frame(self, channels: list[dict], op: str = "subscribe") -> str:
        """Build an OKX WebSocket subscription/unsubscription frame.

        Args:
            channels: List of {channel, instId} dicts, e.g. [{"channel": "tickers", "instId": "BTC-USDT"}]
            op: "subscribe" or "unsubscribe"

        Returns:
            JSON string to send on the WebSocket after connection opens.
        """
        args = []
        for ch in channels:
            arg = {"channel": ch["channel"]}
            if "instId" in ch:
                arg["instId"] = ch["instId"]
            args.append(arg)
        return json.dumps({"op": op, "args": args})

    @property
    def uses_subscription_frames(self) -> bool:
        return True

    @property
    def exchange_name(self) -> str:
        """Return the exchange identifier for this client."""
        return "okx"

    def build_ticker_channels(self, symbols: list[str]) -> list[dict]:
        """Build ticker channel subscriptions for the given symbols.

        OKX uses 'tickers' (plural). instId format: 'BTC-USDT'.
        """
        return [{"channel": "tickers", "instId": f"{s[:-4]}-{s[-4:]}"} for s in symbols]

    def build_trade_channels(self, symbols: list[str]) -> list[dict]:
        """Build trade channel subscriptions for the given symbols."""
        return [{"channel": "trades", "instId": f"{s[:-4].upper()}-{s[-4:].upper()}"} for s in symbols]

    def build_kline_channels(self, symbols: list[str], interval: str = "1m") -> list[dict]:
        """Build kline channel subscriptions for the given symbols."""
        # OKX candle channel names: candle1s, candle1m, candle1H, candle1D
        okx_bar = interval.replace("h", "H").replace("d", "D").replace("w", "1W")
        return [{"channel": f"candle{okx_bar}", "instId": f"{s[:-4].upper()}-{s[-4:].upper()}"} for s in symbols]

    def build_depth_channels(self, symbols: list[str], level: str = "5") -> list[dict]:
        """Build depth channel subscriptions for the given symbols."""
        # OKX books5, books50, etc.
        return [{"channel": f"books{level}", "instId": f"{s[:-4].upper()}-{s[-4:].upper()}"} for s in symbols]

