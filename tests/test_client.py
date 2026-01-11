import threading
from typing import Any, Dict, List

import pandas as pd

from glassnode_python import GlassnodeClient


class MockResponse:
    def __init__(self, payload: List[Dict[str, Any]], status_code: int = 200) -> None:
        self.payload = payload
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError("mock error")

    def json(self) -> List[Dict[str, Any]]:
        return self.payload


class MockSession:
    def __init__(self, payloads: Dict[str, List[Dict[str, Any]]]) -> None:
        self.payloads = payloads
        self.calls: List[Dict[str, Any]] = []
        self.lock = threading.Lock()

    def get(self, url: str, params: Dict[str, Any], timeout: int) -> MockResponse:
        ticker = params.get("a")
        if ticker not in self.payloads:
            raise KeyError(f"unexpected ticker {ticker}")
        with self.lock:
            self.calls.append({"url": url, "params": dict(params), "timeout": timeout})
        return MockResponse(self.payloads[ticker])


def sample_payload(start_ts: int) -> List[Dict[str, Any]]:
    return [
        {"t": start_ts, "o": {"o": 1, "h": 2, "l": 0, "c": 1}},
        {"t": start_ts + 86400, "o": {"o": 2, "h": 3, "l": 1, "c": 2}},
    ]


def test_download_combines_multiple_tickers():
    payloads = {"BTC": sample_payload(0), "ETH": sample_payload(0)}
    session = MockSession(payloads)
    client = GlassnodeClient(api_key="test", session=session, auto_env=False)

    frame = client.download(
        tickers=["BTC", "ETH"],
        start="2024-01-01",
        end="2024-01-05",
        verbose=False,
    )

    assert isinstance(frame.index, pd.DatetimeIndex)
    assert ("BTC", "Open") in frame.columns
    assert ("ETH", "Close") in frame.columns


def test_download_injects_api_key_and_handles_parallel():
    payloads = {"SOL": sample_payload(0), "MATIC": sample_payload(0)}
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
    payloads = {"BTC": []}
    session = MockSession(payloads)
    client = GlassnodeClient(api_key="x", session=session, auto_env=False)

    frame = client.download(
        tickers="BTC",
        start="2024-01-01",
        end="2024-01-02",
        verbose=False,
    )

    assert frame.empty
