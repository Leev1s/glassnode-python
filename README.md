# glassnode-python

Glassnode client that mirrors the ergonomics of `yfinance.download` while remaining lightweight and easy to embed inside data pipelines. The package exposes a single entry point, `glassnode_python.download`, plus a handful of convenience helpers for common metrics.

## Features
- Minimal `GlassnodeClient` with dependency-injected `requests.Session`
- Threaded downloads for multi-asset queries (yfinance-style `threads` flag)
- Pandas-ready OHLC parsing and automatic timezone normalization
- Metric alias registry so you can combine multiple endpoints in one call
- Fully typed helpers that make unit testing straightforward

## Installation
```bash
pip install glassnode-python
```
Until the project is published on PyPI you can install it straight from the repository root:
```bash
pip install .
```

## Quickstart
```python
from glassnode_python import download, get_price

# Export your API key: export GLASSNODE_API_KEY=... (or use a .env file)
df = download("BTC", period="3mo")
prices = get_price(["BTC", "ETH"], period="1y", interval="24h", parallel=True)
rich = download(
	["BTC", "ETH"],
	period="6mo",
	metrics=["ohlc", "price", "marketcap"],
	threads=True,
)
# group_by="ticker" makes the column index match yfinance's default order
by_ticker = download(["BTC", "ETH"], period="1mo", group_by="ticker")
```
For fine-grained control instantiate the client directly:
```python
from glassnode_python import GlassnodeClient

client = GlassnodeClient(api_key="your-key")
df = client.download("ETH", endpoint="/v1/metrics/market/mvrv")
```

## Metric aliases
The `metrics` keyword mirrors `yfinance.download` and lets you stack multiple endpoints in a single response:

| Alias | Endpoint | Columns |
| --- | --- | --- |
| `ohlc` (default) | `/v1/metrics/market/price_usd_ohlc` | `Open`, `High`, `Low`, `Close` |
| `price` | `/v1/metrics/market/price_usd_close` | `Price` |
| `marketcap` | `/v1/metrics/market/marketcap_usd` | `Marketcap` |
| `volume` | `/v1/metrics/market/spot_volume_daily_sum` | `Volume` |
| `mvrv` | `/v1/metrics/market/mvrv` | `MVRV` |
| `realizedcap` | `/v1/metrics/market/realizedcap_usd` | `RealizedCap` |

You can also pass a mapping for custom metrics:

```python
download(
	"BTC",
	metrics={
		"sopr": {"endpoint": "/v1/metrics/market/sopr"},
		"ohlc": {"endpoint": "/v1/metrics/market/price_usd_ohlc", "multi": True},
	},
)
```
Every alias cooperates with `group_by` so you can switch between `("Attribute", "Ticker")` and `("Ticker", "Attribute")` column orders just like yfinance.

## Environment variables
The client reads `GLASSNODE_API_KEY` automatically when a key is not supplied manually. You can create a `.env` file next to your notebook or script:
```
GLASSNODE_API_KEY=your-secret-key
```

## Development workflow
1. Install development dependencies: `pip install -e .[test]`
2. Run the unit tests: `pytest`
3. Cut a release by updating `glassnode_python.__version__` and `pyproject.toml`
4. Build artifacts: `python -m build`
5. Upload via `twine upload dist/*`

## License
Released under the GNU GPLv3. See [LICENSE](LICENSE).
