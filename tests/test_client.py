import threading
from typing import Any, Dict, List, Mapping, Optional, Tuple

import pandas as pd
import pytest
import requests

import glassnode_python
import glassnode_python.client as client_module
from glassnode_python import GlassnodeClient

BASE_URL = "https://api.glassnode.com"
OHLC_ENDPOINT = "/v1/metrics/market/price_usd_ohlc"
PRICE_ENDPOINT = "/v1/metrics/market/price_usd_close"
MARKETCAP_ENDPOINT = "/v1/metrics/market/marketcap_usd"


class MockResponse:
    def __init__(
        self,
        payload: List[Dict[str, Any]],
        status_code: int = 200,
        headers: Optional[Mapping[str, str]] = None,
    ) -> None:
        self.payload = payload
        self.status_code = status_code
        self.headers = dict(headers or {})

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(response=self)

    def json(self) -> List[Dict[str, Any]]:
        return self.payload


class MockSession:
    def __init__(self, payloads: Mapping[Tuple[str, str], Any]) -> None:
        self.payloads = dict(payloads)
        self.calls: List[Dict[str, Any]] = []
        self.lock = threading.Lock()

    def get(self, url: str, params: Dict[str, Any], **kwargs: Any) -> MockResponse:
        ticker = params.get("a")
        endpoint = url.split(BASE_URL)[-1]
        key = (ticker, endpoint)
        if key not in self.payloads:
            raise KeyError(f"unexpected request for {key}")
        with self.lock:
            call = {"url": url, "params": dict(params)}
            call.update(kwargs)
            self.calls.append(call)
        payload = self.payloads[key]
        if isinstance(payload, list) and payload and isinstance(payload[0], MockResponse):
            response = payload.pop(0)
        elif isinstance(payload, MockResponse):
            response = payload
        else:
            response = MockResponse(payload)
        return response


def ohlc_payload(start_ts: int) -> List[Dict[str, Any]]:
    return [
        {"t": start_ts, "o": {"o": 1, "h": 2, "l": 0, "c": 1}},
        {"t": start_ts + 86400, "o": {"o": 2, "h": 3, "l": 1, "c": 2}},
    ]


def value_payload(start_ts: int, value: float) -> List[Dict[str, Any]]:
    return [
        {"t": start_ts, "v": value},
        {"t": start_ts + 86400, "v": value + 1},
    ]


def test_download_combines_multiple_tickers():
    payloads = {
        ("BTC", OHLC_ENDPOINT): ohlc_payload(0),
        ("ETH", OHLC_ENDPOINT): ohlc_payload(0),
    }
    session = MockSession(payloads)
    client = GlassnodeClient(api_key="test", session=session, auto_env=False)

    frame = client.download(
        tickers=["BTC", "ETH"],
        start="2024-01-01",
        end="2024-01-05",
        verbose=False,
        parallel=False,
    )

    assert isinstance(frame.index, pd.DatetimeIndex)
    assert ("Open", "BTC") in frame.columns
    assert ("Close", "ETH") in frame.columns


def test_download_injects_api_key_and_handles_parallel():
    payloads = {
        ("SOL", OHLC_ENDPOINT): ohlc_payload(0),
        ("MATIC", OHLC_ENDPOINT): ohlc_payload(0),
    }
    session = MockSession(payloads)
    client = GlassnodeClient(api_key="abc", session=session, auto_env=False)

    frame = client.download(
        tickers=["SOL", "MATIC"],
        start="2024-01-01",
        end="2024-01-02",
        parallel=True,
        max_workers=2,
        verbose=False,
    )

    assert not frame.empty
    assert len(session.calls) == 2
    for call in session.calls:
        assert call["params"]["api_key"] == "abc"


def test_download_returns_empty_frame_when_no_data():
    payloads = {("BTC", OHLC_ENDPOINT): []}
    session = MockSession(payloads)
    client = GlassnodeClient(api_key="x", session=session, auto_env=False)

    frame = client.download(
        tickers="BTC",
        start="2024-01-01",
        end="2024-01-02",
        verbose=False,
        parallel=False,
    )

    assert frame.empty


def test_metric_aliases_return_named_columns():
    payloads = {
        ("BTC", PRICE_ENDPOINT): value_payload(0, 10),
        ("BTC", MARKETCAP_ENDPOINT): value_payload(0, 100),
    }
    session = MockSession(payloads)
    client = GlassnodeClient(api_key="alias", session=session, auto_env=False)

    frame = client.download(
        tickers="BTC",
        start="2024-01-01",
        end="2024-01-03",
        metrics=["price", "marketcap"],
        verbose=False,
        parallel=False,
    )

    assert list(frame.columns) == ["Price", "Marketcap"]


def test_group_by_ticker_swaps_levels():
    payloads = {
        ("BTC", OHLC_ENDPOINT): ohlc_payload(0),
        ("ETH", OHLC_ENDPOINT): ohlc_payload(0),
    }
    session = MockSession(payloads)
    client = GlassnodeClient(api_key="grp", session=session, auto_env=False)

    frame = client.download(
        tickers=["BTC", "ETH"],
        start="2024-01-01",
        end="2024-01-03",
        group_by="ticker",
        verbose=False,
        parallel=False,
    )

    assert ("BTC", "Open") in frame.columns
    assert frame.columns.names == ["Ticker", "Attribute"]


def test_unknown_metric_alias_raises_key_error():
    session = MockSession({})
    client = GlassnodeClient(api_key="x", session=session, auto_env=False)

    with pytest.raises(KeyError):
        client.download(
            tickers="BTC",
            start="2024-01-01",
            end="2024-01-02",
            metrics=["does_not_exist"],
            verbose=False,
            parallel=False,
        )


def test_download_retries_when_rate_limited(monkeypatch):
    payloads = {
        ("BTC", PRICE_ENDPOINT): [
            MockResponse([], status_code=429, headers={"Retry-After": "0"}),
            MockResponse(value_payload(0, 10)),
        ]
    }
    session = MockSession(payloads)
    client = GlassnodeClient(
        api_key="retry",
        session=session,
        auto_env=False,
        max_retries=2,
        retry_backoff=0,
    )

    frame = client.download(
        tickers="BTC",
        start="2024-01-01",
        end="2024-01-02",
        metrics=["price"],
        verbose=False,
        parallel=False,
    )

    assert not frame.empty
    assert len(session.calls) == 2


def test_module_download_accepts_client_instance():
    payloads = {("BTC", PRICE_ENDPOINT): value_payload(0, 10)}
    session = MockSession(payloads)
    client = GlassnodeClient(api_key="client", session=session, auto_env=False)

    frame = glassnode_python.download(
        ["BTC"],
        client=client,
        start="2024-01-01",
        end="2024-01-03",
        metrics=["price"],
        verbose=False,
        parallel=False,
    )

    assert not frame.empty


def test_module_download_instantiate_client_when_api_key_provided(monkeypatch):
    created: Dict[str, Any] = {}

    class DummyClient:
        def __init__(self, **kwargs: Any) -> None:
            created["kwargs"] = kwargs

        def download(self, **kwargs: Any) -> pd.DataFrame:
            created["download_kwargs"] = kwargs
            index = pd.date_range("2024-01-01", periods=1, freq="D")
            return pd.DataFrame({"Value": [1]}, index=index)

    monkeypatch.setattr(client_module, "GlassnodeClient", DummyClient)
    monkeypatch.setattr(client_module, "_default_client", None)

    frame = glassnode_python.download(
        "BTC",
        api_key="explicit",
        metrics=["price"],
        start="2024-01-01",
        end="2024-01-02",
        verbose=False,
        parallel=False,
    )

    assert not frame.empty
    assert created["kwargs"]["api_key"] == "explicit"
