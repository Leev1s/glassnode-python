<div align="center">

# glassnode-python

面向量化与数据团队的 Glassnode API SDK，操作体验贴近 yfinance。

[English README](README.md)

</div>

---

## ✨ 功能亮点

| 能力 | 说明 |
| --- | --- |
| yfinance 风格 `download()` | 覆盖 `period`、`interval`、`metrics`、`threads`、`group_by`、`progress` 等全部常用参数。 |
| 指标别名注册表 | 内置 price/ohlc/marketcap 等别名，可继续传入自定义端点字典，一次性拼装多指标矩阵。 |
| 稳健的请求链路 | 自动注入 API Key，支持代理 Session，并对 429/50x 做指数退避重试。 |
| Pandas 友好输出 | 使用 DateTimeIndex + MultiIndex 列结构，可直接对接 pandas、polars、回测框架。 |
| 可视化即开即用 | 附带 Plotly TradingView 脚本，一条命令拉取 ETH/SOL 年度日 K 叠加 EMA。 |

---

## 📦 安装

```bash
pip install glassnode-python           # 即将发布到 PyPI
pip install -e .[test]                 # 本地开发依赖
pip install -e .[viz]                  # Plotly 看板可选组件
```

若尚未推送 PyPI，可在仓库根目录直接安装：

```bash
pip install .
```

---

## ⚡ 30 秒快速上手

```python
from glassnode_python import download
from dotenv import load_dotenv
import os

load_dotenv()
api_key = os.environ["GLASSNODE_API_KEY"]

btc = download("BTC", period="3mo", metrics=["price"], api_key=api_key)
print(btc.tail())
```

默认返回 `("Attribute", "Ticker")` 的列 MultiIndex，方便直接对接 pandas/plotly。

---

## 🧰 核心范例

### 1. 多资产 OHLC（yfinance 同款列顺序）

```python
rich = download(
    ["BTC", "ETH", "SOL"],
    period="1y",
    interval="24h",
    metrics=["ohlc"],
    group_by="ticker",
    threads=True,
    api_key=api_key,
)
```

### 2. 混合指标矩阵

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

### 3. 自定义端点映射

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

### 4. 完全自定义客户端

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

## 📊 指标别名目录

| 别名 | Endpoint | 列名 |
| --- | --- | --- |
| `ohlc` | `/v1/metrics/market/price_usd_ohlc` | `Open, High, Low, Close` |
| `price` | `/v1/metrics/market/price_usd_close` | `Price` |
| `marketcap` | `/v1/metrics/market/marketcap_usd` | `Marketcap` |
| `volume` | `/v1/metrics/market/spot_volume_daily_sum` | `Volume` |
| `mvrv` | `/v1/metrics/market/mvrv` | `Mvrv` |
| `realizedcap` | `/v1/metrics/market/realizedcap_usd` | `RealizedCap` |

所有别名都支持 `group_by`、`rounding`、`fill_method` 等参数，DataFrame 结构保持一致。

---

## 📺 TradingView 风格脚本

```bash
pip install -e .[viz]
python scripts/eth_sol_tradingview.py
```

- 顺序请求 ETH/SOL 一年日 K，规避 Glassnode 限速。
- 内置 EMA20/EMA50、暗色主题、联动 Hover、缩放/拖拽操作。
- 可修改 `EMA_WINDOWS` 添加 RSI/MACD，或用 `fig.write_html()` 输出静态报告。

---

## 🔐 API Key 与环境

```bash
echo "GLASSNODE_API_KEY=your-secret" >> .env
```

- 若未显式传入 `api_key`，模块会在首次调用时自动加载 `.env`。
- 也可以传入 `client=`，在多次请求之间复用自定义 `GlassnodeClient`。

---

## 🧪 测试与发布流程

```bash
pip install -e .[test]
pytest

python -m build
twine upload dist/*
```

发布前请同步更新 `src/glassnode_python/__init__.__version__` 与 `pyproject.toml` 中的 `project.version`，再执行构建与上传。

---

## 📄 许可证

遵循 GNU GPLv3，详情见 [LICENSE](LICENSE)。
