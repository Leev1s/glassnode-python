# glassnode-python

Glassnode client that mirrors the ergonomics of `yfinance.download` while remaining lightweight and easy to embed inside data pipelines. The package exposes a single entry point, `glassnode_python.download`, plus a handful of convenience helpers for common metrics.

## Features
- Minimal `GlassnodeClient` with dependency-injected `requests.Session`
- Threaded downloads for multi-asset queries
- Pandas-ready OHLC parsing and automatic timezone normalization
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
```
For fine-grained control instantiate the client directly:
```python
from glassnode_python import GlassnodeClient

client = GlassnodeClient(api_key="your-key")
df = client.download("ETH", endpoint="/v1/metrics/market/mvrv")
```

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
