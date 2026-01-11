"""High-level Glassnode client with a yfinance-style API."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime
import os
import time
from typing import Any, Dict, List, Mapping, MutableMapping, Optional, Sequence, Tuple, Union

import pandas as pd
import requests
from dotenv import load_dotenv

from .metrics import MetricInput, MetricPlan, resolve_metric_plans
from .utils import compute_time_range, normalize_tickers, parse_series

DEFAULT_ENDPOINT = "/v1/metrics/market/price_usd_ohlc"
DEFAULT_INTERVAL = "24h"
DEFAULT_PERIOD = "1mo"
DEFAULT_MAX_WORKERS = 4
DEFAULT_TIMEOUT = 30
RETRY_STATUS_CODES = {429, 500, 502, 503, 504}

TickerInput = Union[str, Sequence[str]]
DateInput = Union[str, datetime, None]
EndpointInput = Union[str, Mapping[str, Any], None]
ProxyInput = Union[str, Mapping[str, str], None]


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
        proxies: Optional[Mapping[str, str]] = None,
        headers: Optional[Mapping[str, str]] = None,
        max_retries: int = 3,
        retry_backoff: float = 2.0,
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
        self.proxies = _normalize_proxy_mapping(proxies)
        self.headers = dict(headers) if headers else None
        self.max_retries = max(1, int(max_retries))
        self.retry_backoff = max(0.0, float(retry_backoff))

    def download(
        self,
        tickers: TickerInput,
        period: str = DEFAULT_PERIOD,
        interval: str = DEFAULT_INTERVAL,
        start: DateInput = None,
        end: DateInput = None,
        endpoint: EndpointInput = DEFAULT_ENDPOINT,
        parallel: Optional[bool] = None,
        max_workers: int = DEFAULT_MAX_WORKERS,
        verbose: bool = True,
        *,
        metrics: Optional[MetricInput] = None,
        group_by: str = "column",
        threads: Optional[bool] = True,
        progress: Optional[bool] = None,
        show_errors: bool = True,
        raise_errors: bool = False,
        rounding: Optional[Union[int, bool]] = None,
        keepna: bool = False,
        dropna: bool = False,
        dropna_axis: int = 0,
        fill_method: Optional[str] = None,
        fill_value: Optional[Any] = None,
        timeout: Optional[int] = None,
        proxy: ProxyInput = None,
        **params: Any,
    ) -> pd.DataFrame:
        """Download one or multiple Glassnode metrics with yfinance-style knobs."""

        items = normalize_tickers(tickers)
        start_ts, end_ts = compute_time_range(start=start, end=end, period=period)
        base_params: Dict[str, Any] = {"i": interval, "s": start_ts, "u": end_ts, **params}
        plans = resolve_metric_plans(metrics=metrics, endpoint=endpoint)

        if parallel is not None:
            use_parallel = parallel
        else:
            use_parallel = threads if threads is not None else len(items) > 1

        show_progress = progress if progress is not None else verbose
        request_timeout = timeout if timeout is not None else self.timeout
        request_proxies = _coalesce_proxies(proxy, self.proxies)
        request_kwargs: Dict[str, Any] = {"timeout": request_timeout}
        if request_proxies:
            request_kwargs["proxies"] = request_proxies

        per_ticker_frames: Dict[str, List[pd.DataFrame]] = {ticker: [] for ticker in items}
        per_ticker_errors: Dict[str, List[str]] = {ticker: [] for ticker in items}

        for plan in plans:
            results = self._run_plan(
                plan=plan,
                tickers=items,
                params=base_params,
                interval=interval,
                parallel=use_parallel,
                max_workers=max_workers,
                progress=show_progress,
                show_errors=show_errors,
                request_kwargs=request_kwargs,
            )
            for result in results:
                if result.frame is not None and not result.frame.empty:
                    prepared = self._prepare_plan_frame(result.frame, plan)
                    if not prepared.empty:
                        per_ticker_frames[result.ticker].append(prepared)
                elif result.error:
                    per_ticker_errors[result.ticker].append(f"{plan.label}: {result.error}")

        assembled = {
            ticker: pd.concat(frames, axis=1)
            for ticker, frames in per_ticker_frames.items()
            if frames
        }

        if not assembled:
            if show_errors:
                print("No data was returned for the requested inputs")
            if raise_errors:
                raise RuntimeError("All downloads failed")
            return pd.DataFrame()

        failed = {ticker: errs for ticker, errs in per_ticker_errors.items() if errs}
        if failed:
            if show_errors:
                for ticker, messages in failed.items():
                    print(f"✗ {ticker}: {'; '.join(messages)}")
            if raise_errors:
                raise RuntimeError("; ".join(f"{ticker}: {'; '.join(msgs)}" for ticker, msgs in failed.items()))

        return self._finalize_output(
            assembled,
            group_by=group_by,
            rounding=rounding,
            keepna=keepna,
            dropna=dropna,
            dropna_axis=dropna_axis,
            fill_method=fill_method,
            fill_value=fill_value,
        )

    def _run_plan(
        self,
        plan: MetricPlan,
        tickers: Sequence[str],
        params: MutableMapping[str, Any],
        interval: str,
        parallel: bool,
        max_workers: int,
        progress: bool,
        show_errors: bool,
        request_kwargs: Mapping[str, Any],
    ) -> List[DownloadResult]:
        if parallel and len(tickers) > 1:
            return self._download_parallel(
                tickers=tickers,
                plan=plan,
                params=params,
                interval=interval,
                progress=progress,
                show_errors=show_errors,
                max_workers=max_workers,
                request_kwargs=request_kwargs,
            )
        return [
            self._download_single(
                ticker=ticker,
                plan=plan,
                params=params,
                interval=interval,
                progress=progress,
                show_errors=show_errors,
                request_kwargs=request_kwargs,
            )
            for ticker in tickers
        ]

    def _prepare_plan_frame(self, frame: pd.DataFrame, plan: MetricPlan) -> pd.DataFrame:
        label = self._format_metric_label(plan.alias or plan.column or plan.label)
        if label == "ohlc":
            return frame.rename(columns={col: str(col).lower() for col in frame.columns})

        columns = list(frame.columns)
        if len(columns) == 1 and str(columns[0]).lower() == "value":
            return frame.rename(columns={columns[0]: label})

        rename_map = {col: f"{label}_{str(col).lower()}" for col in frame.columns}
        return frame.rename(columns=rename_map)

    def _finalize_output(
        self,
        frames: Dict[str, pd.DataFrame],
        *,
        group_by: str,
        rounding: Optional[Union[int, bool]],
        keepna: bool,
        dropna: bool,
        dropna_axis: int,
        fill_method: Optional[str],
        fill_value: Optional[Any],
    ) -> pd.DataFrame:
        if len(frames) == 1:
            result = next(iter(frames.values()))
        else:
            result = pd.concat(frames, axis=1, keys=frames.keys())
        if rounding:
            decimals = 6 if rounding is True else int(rounding)
            result = result.round(decimals)
        if fill_value is not None:
            result = result.fillna(fill_value)
        if fill_method:
            result = result.fillna(method=fill_method)
        if dropna:
            result = result.dropna(axis=dropna_axis)
        elif not keepna:
            result = result.dropna(axis=0, how="all")
        if isinstance(result.columns, pd.MultiIndex):
            result.columns.names = ["Ticker", "Attribute"]
            if group_by.lower() == "column":
                result = result.swaplevel(axis=1).sort_index(axis=1)
                result.columns.names = ["Attribute", "Ticker"]
            elif group_by.lower() == "ticker":
                result = result.sort_index(axis=1)
        return result

    @staticmethod
    def _format_metric_label(value: Optional[str]) -> str:
        text = (value or "").strip()
        if not text:
            text = "Metric"
        return text.replace(" ", "_").lower()

    def _download_parallel(
        self,
        tickers: Sequence[str],
        plan: MetricPlan,
        params: MutableMapping[str, Any],
        interval: str,
        progress: bool,
        show_errors: bool,
        max_workers: int,
        request_kwargs: Mapping[str, Any],
    ) -> List[DownloadResult]:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_map = {
                executor.submit(
                    self._download_single,
                    ticker,
                    plan,
                    params,
                    interval,
                    progress,
                    show_errors,
                    request_kwargs,
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
        plan: MetricPlan,
        params: MutableMapping[str, Any],
        interval: str,
        progress: bool,
        show_errors: bool,
        request_kwargs: Mapping[str, Any],
    ) -> DownloadResult:
        effective_params = dict(params)
        effective_params["a"] = ticker
        try:
            if progress:
                print(
                    f"Downloading {ticker} (metric={plan.label}, interval={interval})"
                )
            payload = self._make_request(
                endpoint=plan.endpoint,
                params=effective_params,
                request_kwargs=request_kwargs,
            )
            frame = parse_series(payload)
            if frame.empty:
                message = "No data"
                if show_errors:
                    print(f"✗ {ticker} ({plan.label}): {message}")
                return DownloadResult(ticker, None, message)
            if progress:
                print(f"✓ {ticker} ({plan.label}): {len(frame)} records")
            return DownloadResult(ticker, frame, None)
        except Exception as exc:  # pragma: no cover - defensive logging
            message = str(exc)
            if show_errors:
                print(f"✗ {ticker} ({plan.label}): {message}")
            return DownloadResult(ticker, None, message)

    def _make_request(
        self,
        endpoint: str,
        params: MutableMapping[str, Any],
        request_kwargs: Mapping[str, Any],
    ) -> List[Dict[str, Any]]:
        url = f"{self.base_url}{endpoint}"
        request_params = dict(params)
        request_params["api_key"] = self.api_key
        kwargs = dict(request_kwargs)
        headers = dict(self.headers) if self.headers else {}
        if headers:
            kwargs.setdefault("headers", headers)
        attempts = self.max_retries
        last_error: Optional[Exception] = None
        for attempt in range(1, attempts + 1):
            response = self.session.get(url, params=request_params, **kwargs)
            status = getattr(response, "status_code", None)
            try:
                response.raise_for_status()
                return response.json()
            except requests.HTTPError as exc:
                last_error = exc
                if status in RETRY_STATUS_CODES and attempt < attempts:
                    time.sleep(self._retry_wait(response, attempt))
                    continue
                raise
            except requests.RequestException as exc:
                last_error = exc
                if attempt < attempts:
                    time.sleep(self._retry_wait(None, attempt))
                    continue
                raise
        if last_error:
            raise last_error
        raise RuntimeError("Unspecified request failure")

    def _retry_wait(
        self,
        response: Optional[requests.Response],
        attempt: int,
    ) -> float:
        if response is not None:
            retry_after = response.headers.get("Retry-After") if hasattr(response, "headers") else None
            if retry_after:
                try:
                    return float(retry_after)
                except ValueError:
                    pass
        return self.retry_backoff * max(1, attempt)


def _normalize_proxy_mapping(proxies: Optional[Mapping[str, str]]) -> Optional[Dict[str, str]]:
    if proxies is None:
        return None
    return {k: v for k, v in proxies.items()}


def _coalesce_proxies(
    call_proxy: ProxyInput,
    default_proxy: Optional[Mapping[str, str]],
) -> Optional[Dict[str, str]]:
    if call_proxy is None:
        if default_proxy is None:
            return None
        return dict(default_proxy)
    if isinstance(call_proxy, str):
        return {"http": call_proxy, "https": call_proxy}
    return {k: v for k, v in call_proxy.items()}


_default_client: Optional[GlassnodeClient] = None


def get_default_client() -> GlassnodeClient:
    global _default_client
    if _default_client is None:
        _default_client = GlassnodeClient()
    return _default_client


def download(
    tickers: TickerInput,
    /,
    *,
    client: Optional[GlassnodeClient] = None,
    api_key: Optional[str] = None,
    **kwargs: Any,
) -> pd.DataFrame:
    if client is not None:
        return client.download(tickers=tickers, **kwargs)
    if api_key is not None:
        temp_client = GlassnodeClient(api_key=api_key, auto_env=False)
        return temp_client.download(tickers=tickers, **kwargs)
    return get_default_client().download(tickers=tickers, **kwargs)


def get_ohlc(tickers: TickerInput, **kwargs: Any) -> pd.DataFrame:
    return download(tickers, endpoint=DEFAULT_ENDPOINT, **kwargs)


def get_price(tickers: TickerInput, **kwargs: Any) -> pd.DataFrame:
    return download(tickers, endpoint="/v1/metrics/market/price_usd_close", **kwargs)


def get_marketcap(tickers: TickerInput, **kwargs: Any) -> pd.DataFrame:
    return download(
        tickers,
        endpoint="/v1/metrics/market/marketcap_usd",
        **kwargs,
    )


def get_volume(tickers: TickerInput, **kwargs: Any) -> pd.DataFrame:
    return download(
        tickers,
        endpoint="/v1/metrics/market/spot_volume_daily_sum",
        **kwargs,
    )


def get_mvrv(tickers: TickerInput, **kwargs: Any) -> pd.DataFrame:
    return download(tickers, endpoint="/v1/metrics/market/mvrv", **kwargs)
