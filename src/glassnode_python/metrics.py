"""Metric alias registry and resolution helpers."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Optional, Sequence, Tuple, Union

from .utils import endpoint_to_column_name

MetricInput = Union[
    str,
    Sequence[str],
    Mapping[str, Union[str, Mapping[str, Any], None]],
]


@dataclass(frozen=True)
class MetricDescriptor:
    endpoint: str
    multi: bool = False
    column: Optional[str] = None
    description: str = ""


@dataclass(frozen=True)
class MetricPlan:
    alias: str
    endpoint: str
    multi: bool
    column: Optional[str] = None

    @property
    def label(self) -> str:
        return self.alias or (self.column or endpoint_to_column_name(self.endpoint))


METRIC_ALIASES: Dict[str, MetricDescriptor] = {
    "ohlc": MetricDescriptor(
        endpoint="/v1/metrics/market/price_usd_ohlc",
        multi=True,
        description="USD-denominated OHLC candles",
    ),
    "price": MetricDescriptor(
        endpoint="/v1/metrics/market/price_usd_close",
        column="Price",
        description="Closing spot price in USD",
    ),
    "marketcap": MetricDescriptor(
        endpoint="/v1/metrics/market/marketcap_usd",
        column="Marketcap",
        description="Market capitalization in USD",
    ),
    "volume": MetricDescriptor(
        endpoint="/v1/metrics/market/spot_volume_daily_sum",
        column="Volume",
        description="Aggregated spot volume (daily)",
    ),
    "mvrv": MetricDescriptor(
        endpoint="/v1/metrics/market/mvrv",
        column="MVRV",
        description="Market Value to Realized Value ratio",
    ),
    "realizedcap": MetricDescriptor(
        endpoint="/v1/metrics/market/realizedcap_usd",
        column="RealizedCap",
        description="Realized capitalization in USD",
    ),
}


def resolve_metric_plans(
    metrics: Optional[MetricInput],
    endpoint: Optional[Union[str, Mapping[str, Any]]],
) -> List[MetricPlan]:
    if metrics is None and isinstance(endpoint, Mapping):
        metrics = endpoint
        endpoint = None

    if metrics is None:
        descriptor, alias = _descriptor_from_endpoint(endpoint)
        return [MetricPlan(alias=alias, endpoint=descriptor.endpoint, multi=descriptor.multi, column=descriptor.column)]

    if isinstance(metrics, Mapping):
        plans: List[MetricPlan] = []
        for alias, spec in metrics.items():
            descriptor = _descriptor_from_spec(alias, spec)
            plans.append(
                MetricPlan(
                    alias=_normalize_alias(alias),
                    endpoint=descriptor.endpoint,
                    multi=descriptor.multi,
                    column=descriptor.column or _alias_to_column(alias),
                )
            )
        return plans

    normalized = _ensure_sequence(metrics)
    plans = []
    for alias in normalized:
        descriptor = _descriptor_from_alias(alias)
        plans.append(
            MetricPlan(
                alias=_normalize_alias(alias),
                endpoint=descriptor.endpoint,
                multi=descriptor.multi,
                column=descriptor.column or _alias_to_column(alias),
            )
        )
    return plans


def _descriptor_from_endpoint(
    endpoint: Optional[Union[str, Mapping[str, Any]]]
) -> Tuple[MetricDescriptor, str]:
    if endpoint is None:
        descriptor = METRIC_ALIASES["ohlc"]
        return descriptor, "ohlc"
    if isinstance(endpoint, Mapping):
        raise TypeError("endpoint mapping is not supported when metrics are provided")
    for key, descriptor in METRIC_ALIASES.items():
        if descriptor.endpoint == endpoint:
            return descriptor, key
    column = endpoint_to_column_name(endpoint)
    return MetricDescriptor(endpoint=endpoint, column=column, multi=False), column.lower()


def _descriptor_from_spec(alias: str, spec: Union[str, Mapping[str, Any], None]) -> MetricDescriptor:
    if spec is None:
        return _descriptor_from_alias(alias)
    if isinstance(spec, str):
        return MetricDescriptor(endpoint=spec, column=_alias_to_column(alias), multi=False)
    if not isinstance(spec, Mapping):
        raise TypeError("metric specification must be a string, mapping, or None")
    endpoint = spec.get("endpoint")
    if not endpoint:
        raise ValueError("metric specification requires an 'endpoint' field")
    multi = bool(spec.get("multi", False))
    column = spec.get("column") or _alias_to_column(alias)
    return MetricDescriptor(endpoint=endpoint, multi=multi, column=column)


def _descriptor_from_alias(alias: str) -> MetricDescriptor:
    key = _normalize_alias(alias)
    descriptor = METRIC_ALIASES.get(key)
    if descriptor is None:
        raise KeyError(f"Unknown metric alias: {alias}")
    return descriptor


def _alias_to_column(alias: str) -> str:
    return alias.replace("_", " ").title().replace(" ", "")


def _normalize_alias(value: str) -> str:
    return value.lower().strip()


def _ensure_sequence(value: Union[str, Sequence[str]]) -> Sequence[str]:
    if isinstance(value, str):
        return [value]
    return value


__all__ = [
    "MetricDescriptor",
    "MetricPlan",
    "MetricInput",
    "METRIC_ALIASES",
    "resolve_metric_plans",
]
