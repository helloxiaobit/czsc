from __future__ import annotations

from datetime import datetime
from typing import Any

from .models import RecursiveLevelResult
from .serializers import (
    serialize_divergence,
    serialize_resonance,
    serialize_segment,
    serialize_trade_signal,
    serialize_zone,
    serialize_trend_type,
    to_iso,
)


def _serialize_level(level: RecursiveLevelResult) -> dict[str, Any]:
    return {
        "id": level.spec.id,
        "label": level.spec.label,
        "source": level.spec.source,
        "min_bi_count": level.spec.min_bi_count,
        "confirmed_only": bool(level.spec.confirmed_only),
        "fx": [],
        "bi": [
            {
                "sdt": to_iso(bi.sdt),
                "edt": to_iso(bi.edt),
                "direction": bi.direction.value,
                "high": bi.high,
                "low": bi.low,
                "start_price": bi.fx_a.fx,
                "end_price": bi.fx_b.fx,
                "power": bi.power_price,
                "base_span": level.bi_base_spans[idx] if idx < len(level.bi_base_spans) else (None, None),
            }
            for idx, bi in enumerate(level.bis)
        ],
        "segments": [serialize_segment(x) for x in level.segments],
        "zones": [serialize_zone(x) for x in level.zones],
        "trend_types": [serialize_trend_type(x) for x in level.trend_types],
        "trade_signals": [serialize_trade_signal(x) for x in level.signals],
        "divergences": [serialize_divergence(x) for x in level.divergences],
    }


def _serialize_kline(bars) -> list[dict[str, Any]]:
    kline = []
    for bar in bars:
        item = bar.__dict__.copy()
        if isinstance(item.get("dt"), datetime):
            item["dt"] = item["dt"].isoformat()
        kline.append(item)
    return kline


def build_recursive_chart_payload(
    symbol: str,
    base_bars: list,
    level_results: dict[str, RecursiveLevelResult],
    resonance_signals: list = None,
    base_freq: str | None = None,
    recursion_mode: str = "structure",
    max_levels: int | None = None,
    confirmed_only: bool = True,
    generated_at: datetime | None = None,
) -> dict[str, Any]:
    """
    将递归分析结果序列化为前端友好 payload。
    """
    payload: dict[str, Any] = {
        "symbol": symbol,
        "base_freq": base_freq,
        "recursion_mode": recursion_mode,
        "levels": [],
        "kline": _serialize_kline(base_bars),
        "resonance_signals": [serialize_resonance(x) for x in (resonance_signals or [])],
        "meta": {
            "confirmed_only": bool(confirmed_only),
            "max_levels": max_levels,
            "generated_at": to_iso(generated_at),
            "level_count": len(level_results),
        },
    }

    for level in level_results.values():
        payload["levels"].append(_serialize_level(level))

    return payload
