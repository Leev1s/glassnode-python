"""Legacy shim that forwards to the glassnode_python package."""
from glassnode_python import (
    GlassnodeClient,
    download,
    get_marketcap,
    get_mvrv,
    get_ohlc,
    get_price,
    get_volume,
)

__all__ = [
    "GlassnodeClient",
    "download",
    "get_marketcap",
    "get_mvrv",
    "get_ohlc",
    "get_price",
    "get_volume",
]

if __name__ == "__main__":
    print("glassnode-python is now a package. Import glassnode_python in your projects.")
