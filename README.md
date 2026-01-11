<div align="center">

# glassnode-python

**English-first documentation with side-by-side Chinese notes for global quant teams.**  
面向全球量化/数据团队的加密链上数据 SDK，提供中英文并行说明。

</div>

---

## ✨ Feature Highlights · 功能亮点

| Capability | 描述 |
| --- | --- |
| yfinance-style `download()` | 完全复刻 `yfinance.download` 的参数语义，支持 `threads`, `group_by`, `progress`, `metrics` 等。|
| Multi-metric alias registry | 内置别名表（price/mvrv/marketcap…），也可自定义 endpoint，轻松拼装多指标矩阵。|
| Request resilience | 自动注入 API Key、可配置代理，内建重试 + `Retry-After` 退避，API 限速时仍保持稳定。|
| Pandas-native output | DateTimeIndex + MultiIndex 列设计，与 NumPy / pandas / polars / backtrader 等生态无缝衔接。|
| Visualization ready | 自带 Plotly TradingView 风格脚本，1️⃣ 命令完成 ETH / SOL 年度日 K 可视化。|

> **EN:** Think of `glassnode_python` as “Glassnode meets yfinance”.
>
> **ZH:** 把 Glassnode 官方 API 包装成 yfinance 一样的体验，插上 pandas/Plotly 就能工作。

---

## 📦 Installation · 安装

```bash
pip install glassnode-python           # coming soon on PyPI
pip install -e .[test]                 # from source (dev mode)
pip install -e .[viz]                  # optional Plotly viewer extras
```

> **ZH:** 如果还未发布到 PyPI，可在仓库根目录执行 `pip install .` 或 `pip install -e .` 进入开发模式。

---

## ⚡ Quickstart · 快速上手（30 秒）

```python
from glassnode_python import download
from dotenv import load_dotenv
import os

load_dotenv()
api_key = os.environ["GLASSNODE_API_KEY"]

btc = download("BTC", period="3mo", metrics=["price"], api_key=api_key)
print(btc.tail())
```

> **ZH:** 载入 `.env`，显式传入 `api_key`，默认返回 `("Attribute",)` 列结构，直接丢给 pandas/plotly 即可。

---

## 🧰 Essential Recipes · 核心范例

### 1. Multi-asset OHLC (yfinance style) · 多资产 K 线

```python
rich = download(
	["BTC", "ETH", "SOL"],
	period="1y",
	interval="24h",
	metrics=["ohlc"],
	group_by="ticker",   # swap column order to (Ticker, Attribute)
	threads=True,         # enable worker pool when API 限速允许
	api_key=api_key,
)
rich["ETH"].tail()
```

### 2. Mix & match metrics · 混合指标矩阵

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

### 3. Custom endpoint mapping · 自定义端点

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

### 4. Full-control client · 完全自定义客户端

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

## 📊 Metric Alias Catalog · 指标别名目录

| Alias | Endpoint | Columns | 中文说明 |
| --- | --- | --- | --- |
| `ohlc` | `/v1/metrics/market/price_usd_ohlc` | `Open,High,Low,Close` | 日 K 线 (默认) |
| `price` | `/v1/metrics/market/price_usd_close` | `Price` | 收盘价 |
| `marketcap` | `/v1/metrics/market/marketcap_usd` | `Marketcap` | 市值 |
| `volume` | `/v1/metrics/market/spot_volume_daily_sum` | `Volume` | 现货成交量 |
| `mvrv` | `/v1/metrics/market/mvrv` | `Mvrv` | MVRV 比率 |
| `realizedcap` | `/v1/metrics/market/realizedcap_usd` | `RealizedCap` | 实现市值 |

> **Tip:** All aliases respect `group_by`, `rounding`, `fill_method`, etc., so the dataframe layout stays predictable.

---

## 📺 TradingView-like Dashboard · TradingView 风格看板

```bash
pip install -e .[viz]
python scripts/eth_sol_tradingview.py
```

- Pulls 1-year daily OHLC for ETH & SOL (sequential mode to stay within rate limits).
- Adds EMA20/EMA50 overlays + Plotly dark theme, hover linking, zoom/pan just like TradingView.
- Feel free to tweak `EMA_WINDOWS`, add RSI/MACD traces, or export via `fig.write_html()`.

> **ZH:** 运行脚本会自动打开浏览器窗口，实现“丝滑”互动体验，无需上传截图。

---

## 🔐 API Keys & Environment · API 密钥

```bash
echo "GLASSNODE_API_KEY=your-secret" >> .env
```

- If `api_key` is omitted, the client lazy-loads `.env` on first use.
- Module-level helpers accept `api_key=` for one-off calls, or `client=` to reuse a configured `GlassnodeClient`.

---

## 🧪 Testing & Release Flow · 测试与发布

```bash
pip install -e .[test]
pytest

python -m build
twine upload dist/*
```

> **ZH:** 发布前更新 `glassnode_python/__init__.__version__` 与 `pyproject.toml`，再执行 `python -m build` + `twine`。

---

## 📄 License · 许可证

GNU GPLv3 — see [LICENSE](LICENSE).

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
from dotenv import load_dotenv
import os

# Load your API key explicitly
load_dotenv()
api_key = os.environ["GLASSNODE_API_KEY"]

df = download("BTC", period="3mo", api_key=api_key)
prices = get_price(["BTC", "ETH"], period="1y", interval="24h", parallel=True)
rich = download(
	["BTC", "ETH"],
	period="6mo",
	metrics=["ohlc", "price", "marketcap"],
	threads=True,
	api_key=api_key,
)
# group_by="ticker" makes the column index match yfinance's default order
by_ticker = download(["BTC", "ETH"], period="1mo", group_by="ticker", api_key=api_key)
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

## TradingView-style dashboard

To spin up an interactive viewer powered by Plotly, install the optional visualization extras and run the bundled script:

```bash
pip install -e .[viz]
python scripts/eth_sol_tradingview.py
```

The script pulls a full year of daily OHLC candles for ETH and SOL directly from Glassnode using your `GLASSNODE_API_KEY`, overlays 20/50-day EMAs, and opens a browser window with TradingView-like zoom, pan, and hover interactions.

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
