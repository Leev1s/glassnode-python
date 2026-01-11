"""Interactive ETH/SOL dashboard using real Glassnode data."""
from __future__ import annotations

import os
from typing import Dict

from dotenv import load_dotenv
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from glassnode_python import download

ASSETS = ["ETH", "SOL"]
PERIOD = "1y"
INTERVAL = "24h"
EMA_WINDOWS = (20, 50)


def main() -> None:
    load_dotenv()
    api_key = os.getenv("GLASSNODE_API_KEY")
    if not api_key:
        raise SystemExit("GLASSNODE_API_KEY is missing; set it in your shell or .env file.")

    frame = download(
        ASSETS,
        period=PERIOD,
        interval=INTERVAL,
        metrics=["ohlc"],
        group_by="ticker",
        threads=False,
        api_key=api_key,
        verbose=True,
    )
    frame.index = frame.index.tz_convert(None)

    enriched = {ticker: _add_overlays(frame[ticker]) for ticker in ASSETS}
    fig = _build_layout(enriched)
    fig.update_layout(
        title="Glassnode ETH & SOL Daily Candles (1Y)",
        template="plotly_dark",
        hovermode="x unified",
        height=900,
    )
    fig.show()


def _add_overlays(candles: pd.DataFrame) -> pd.DataFrame:
    data = candles.copy()
    for window in EMA_WINDOWS:
        column = f"ema{window}"
        data[column] = data["close"].ewm(span=window, adjust=False).mean()
    return data


def _build_layout(data: Dict[str, pd.DataFrame]) -> go.Figure:
    fig = make_subplots(rows=len(data), cols=1, shared_xaxes=True, vertical_spacing=0.04)
    for idx, (ticker, frame) in enumerate(data.items(), start=1):
        fig.add_trace(
            go.Candlestick(
                x=frame.index,
                open=frame["open"],
                high=frame["high"],
                low=frame["low"],
                close=frame["close"],
                name=f"{ticker} OHLC",
                showlegend=False,
            ),
            row=idx,
            col=1,
        )
        for window in EMA_WINDOWS:
            column = f"ema{window}"
            fig.add_trace(
                go.Scatter(
                    x=frame.index,
                    y=frame[column],
                    name=f"{ticker} EMA {window}",
                    mode="lines",
                    line=dict(width=1.4),
                    showlegend=(idx == 1),
                ),
                row=idx,
                col=1,
            )
        fig.update_yaxes(title_text=ticker, row=idx, col=1)

    fig.update_xaxes(rangeslider_visible=False)
    return fig


if __name__ == "__main__":
    main()