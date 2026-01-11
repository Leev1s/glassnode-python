<div align="center">

# glassnode-python

Glassnode API toolkit with a yfinance-style interface.

[Chinese version](README_CN.md)

</div>

---

## ✨ Feature Highlights

| Capability | Details |
| --- | --- |
| yfinance-style `download()` | Mirrors `yfinance.download` semantics including `period`, `interval`, `metrics`, `threads`, `group_by`, and progress hooks. |
| Multi-metric alias registry | Built-in alias table for price, OHLC, marketcap, and other endpoints, plus support for custom endpoint dictionaries. |
| Request resilience | Injects API keys automatically, supports proxy-aware `requests.Session`, and retries with exponential backoff on 429/50x responses. |
| Pandas-native output | DateTime index + MultiIndex columns flow directly into NumPy, pandas, polars, or backtesting engines. |
| Visualization ready | Bundled Plotly script launches a TradingView-style ETH/SOL dashboard with one command. |

---

## 📦 Installation

```bash
pip install glassnode-python           # install from PyPI (v0.3.0+)
pip install -e .[test]                 # developer setup
pip install -e .[viz]                  # Plotly dashboard extras
```

If you prefer a local checkout, run `pip install .` from the repo root.

---

## ⚡ Quickstart (30 seconds)

```python
from glassnode_python import download
from dotenv import load_dotenv
import os

load_dotenv()
api_key = os.environ["GLASSNODE_API_KEY"]

btc = download("BTC", period="3mo", metrics=["price"], api_key=api_key)
print(btc.tail())
```

The helper returns a pandas dataframe with a DateTime index and a column MultiIndex of `(Attribute, Ticker)` by default.

---

## 🧰 Essential Recipes

### Multi-asset OHLC (yfinance style)

```python
rich = download(
	["BTC", "ETH", "SOL"],
	period="1y",
	interval="24h",
	metrics=["ohlc"],
	group_by="ticker",   # switch to (Ticker, Attribute)
	threads=True,
	api_key=api_key,
)
```

### Mix & match metrics

```python
matrix = download(
	"BTC",
	metrics=["price", "marketcap", "mvrv"],
	period="6mo",
	rounding=2,
	dropna=True,
	api_key=api_key,
)
```

### Custom endpoint mapping

```python
download(
	"ETH",
	metrics={
		"sopr": {"endpoint": "/v1/metrics/market/sopr"},
		"ohlc": {"endpoint": "/v1/metrics/market/price_usd_ohlc", "multi": True},
		"fees": {
			"endpoint": "/v1/metrics/transactions/transfers_volume_sum",
			"column": "TransferVolume",
		},
	},
	api_key=api_key,
)
```

### Full-control client

```python
from glassnode_python import GlassnodeClient
import requests

session = requests.Session()
session.headers.update({"User-Agent": "glassnode-python/0.2"})

client = GlassnodeClient(
	api_key=api_key,
	session=session,
	proxies={"https": "http://127.0.0.1:7890"},
	max_retries=5,
	retry_backoff=1.5,
)

df = client.download(
	["BTC", "SOL"],
	start="2025-01-01",
	end="2025-12-31",
	metrics=["price", "volume"],
	progress=False,
)
```

---

## 📊 Metric Alias Catalog

| Alias | Endpoint | Columns |
| --- | --- | --- |
| `ohlc` | `/v1/metrics/market/price_usd_ohlc` | `Open, High, Low, Close` |
| `price` | `/v1/metrics/market/price_usd_close` | `Price` |
| `marketcap` | `/v1/metrics/market/marketcap_usd` | `Marketcap` |
| `volume` | `/v1/metrics/market/spot_volume_daily_sum` | `Volume` |
| `mvrv` | `/v1/metrics/market/mvrv` | `Mvrv` |
| `realizedcap` | `/v1/metrics/market/realizedcap_usd` | `RealizedCap` |

Aliases respect `group_by`, `rounding`, and fill methods so the dataframe layout stays predictable.

---

## 📺 TradingView-like Dashboard

```bash
pip install -e .[viz]
python scripts/eth_sol_tradingview.py
```

- Fetches one year of daily OHLC candles for ETH and SOL (sequential mode to stay within rate limits).
- Adds EMA20/EMA50 overlays plus Plotly dark theme, linked hover, and full zoom/pan controls.
- Customize via the `EMA_WINDOWS` constant or export HTML with `fig.write_html()`.

---

## 🔐 API Keys & Environment

```bash
echo "GLASSNODE_API_KEY=your-secret" >> .env
```

- If `api_key` is omitted, the module lazily loads `.env` on first use.
- Pass `api_key=` for one-off calls or `client=` to reuse a configured `GlassnodeClient`.

---

## 🧪 Testing & Release Flow

```bash
pip install -e .[test]
pytest

python -m build
twine upload dist/*
```

Update `__version__` inside `src/glassnode_python/__init__.py` and the `project.version` in `pyproject.toml` before cutting a release.

---

## 📄 License

GNU GPLv3 — see [LICENSE](LICENSE).
