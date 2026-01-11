"""High-level Glassnode client with a yfinance-style API."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime
import os
from typing import Any, Dict, Iterable, List, MutableMapping, Optional, Sequence, Tuple, Union

import pandas as pd
import requests
from dotenv import load_dotenv

from .utils import compute_time_range, normalize_tickers, parse_series

DEFAULT_ENDPOINT = "/v1/metrics/market/price_usd_ohlc"
DEFAULT_INTERVAL = "24h"
DEFAULT_PERIOD = "1mo"
DEFAULT_MAX_WORKERS = 4
DEFAULT_TIMEOUT = 30

TickerInput = Union[str, Sequence[str]]
DateInput = Union[str, datetime, None]


@dataclass
class DownloadResult:
    ticker: str
    frame: Optional[pd.DataFrame]
    error: Optional[str]


class GlassnodeClient:
    """Typed interface around the Glassnode REST API."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://api.glassnode.com",
        timeout: int = DEFAULT_TIMEOUT,
        session: Optional[requests.Session] = None,
        auto_env: bool = True,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = session or requests.Session()
        if api_key is None and auto_env:
            load_dotenv()
            api_key = os.getenv("GLASSNODE_API_KEY")
        if not api_key:
            raise ValueError(
                "GLASSNODE_API_KEY could not be found. "
                "Provide it directly or via an environment variable."
            )
        self.api_key = api_key

    def download(
        self,
        tickers: TickerInput,
        period: str = DEFAULT_PERIOD,
        interval: str = DEFAULT_INTERVAL,
        start: DateInput = None,
        end: DateInput = None,
        endpoint: str = DEFAULT_ENDPOINT,
        parallel: bool = False,
        max_workers: int = DEFAULT_MAX_WORKERS,
        verbose: bool = True,
        **params: Any,
    ) -> pd.DataFrame:
        items = normalize_tickers(tickers)
        start_ts, end_ts = compute_time_range(start=start, end=end, period=period)
        base_params: Dict[str, Any] = {"i": interval, "s": start_ts, "u": end_ts, **params}

        if parallel and len(items) > 1:
            if verbose:
                print(
                    f"Downloading {len(items)} tickers in parallel with {max_workers} workers"
                )
            results = self._download_parallel(
                tickers=items,
                endpoint=endpoint,
                params=base_params,
                interval=interval,
                verbose=verbose,
                max_workers=max_workers,
            )
        else:
            results = [
                self._download_single(
                    ticker=ticker,
                    endpoint=endpoint,
                    params=base_params,
                    interval=interval,
                    verbose=verbose,
                )
                for ticker in items
            ]

        frames = {result.ticker: result.frame for result in results if result.frame is not None}
        if not frames:
            if verbose:
                print("No data was returned for the requested inputs")
            return pd.DataFrame()

        if len(frames) == 1:
            return next(iter(frames.values()))
        combined = pd.concat(frames, axis=1, keys=frames.keys())
        if isinstance(combined.columns, pd.MultiIndex):
            combined.columns.names = ["Ticker", "Attribute"]
        return combined

    def _download_parallel(
        self,
        tickers: Sequence[str],
        endpoint: str,
        params: MutableMapping[str, Any],
        interval: str,
        verbose: bool,
        max_workers: int,
    ) -> List[DownloadResult]:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_map = {
                executor.submit(
                    self._download_single,
                    ticker,
                    endpoint,
                    params,
                    interval,
                    verbose,
                ): ticker
                for ticker in tickers
            }
            results: List[DownloadResult] = []
            for future in as_completed(future_map):
                results.append(future.result())
        return results

    def _download_single(
        self,
        ticker: str,
        endpoint: str,
        params: MutableMapping[str, Any],
        interval: str,
        verbose: bool,
    ) -> DownloadResult:
        effective_params = dict(params)
        effective_params["a"] = ticker
        try:
            endpoint_name = endpoint.split("/")[-1]
            if verbose:
                print(
                    f"Downloading {ticker} (endpoint={endpoint_name}, interval={interval})"
                )
            payload = self._make_request(endpoint=endpoint, params=effective_params)
            frame = parse_series(payload)
            if frame.empty:
                message = "No data"
                if verbose:
                    print(f"✗ {ticker}: {message}")
                return DownloadResult(ticker, None, message)
            if verbose:
                print(f"✓ {ticker}: {len(frame)} records")
            return DownloadResult(ticker, frame, None)
        except Exception as exc:  # pragma: no cover - defensive logging
            message = str(exc)
            if verbose:
                print(f"✗ {ticker}: {message}")
            return DownloadResult(ticker, None, message)

    def _make_request(self, endpoint: str, params: MutableMapping[str, Any]) -> List[Dict[str, Any]]:
        url = f"{self.base_url}{endpoint}"
        params = dict(params)
        params["api_key"] = self.api_key
        response = self.session.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        return response.json()


_default_client: Optional[GlassnodeClient] = None


def get_default_client() -> GlassnodeClient:
    global _default_client
    if _default_client is None:
        _default_client = GlassnodeClient()
    return _default_client


def download(**kwargs: Any) -> pd.DataFrame:
    return get_default_client().download(**kwargs)


def get_ohlc(tickers: TickerInput, **kwargs: Any) -> pd.DataFrame:
    return download(tickers=tickers, endpoint="/v1/metrics/market/price_usd_ohlc", **kwargs)


def get_price(tickers: TickerInput, **kwargs: Any) -> pd.DataFrame:
    return download(tickers=tickers, endpoint="/v1/metrics/market/price_usd_close", **kwargs)


def get_marketcap(tickers: TickerInput, **kwargs: Any) -> pd.DataFrame:
    return download(
        tickers=tickers,
        endpoint="/v1/metrics/market/marketcap_usd",
        **kwargs,
    )


def get_volume(tickers: TickerInput, **kwargs: Any) -> pd.DataFrame:
    return download(
        tickers=tickers,
        endpoint="/v1/metrics/market/spot_volume_daily_sum",
        **kwargs,
    )


def get_mvrv(tickers: TickerInput, **kwargs: Any) -> pd.DataFrame:
    return download(tickers=tickers, endpoint="/v1/metrics/market/mvrv", **kwargs)
