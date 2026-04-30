"""递归多级别图表服务层。

该模块聚焦“底层K线 -> 笔 -> 线段 -> 上一级结构递归”的统一管线，
并将递归分析结果直接喂给前端渲染层 `kline_recursive`。
"""

from __future__ import annotations

import io
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from czsc.py.enum import Freq
from czsc.py.objects import RawBar
from czsc.recursive import RecursiveLevelSpec, analyze_recursive_structure, build_recursive_chart_payload
from czsc.utils import kline_recursive


REQUIRED_BAR_COLUMNS = {"dt", "open", "close", "high", "low"}
FREQ_ALIASES = {
    "1m": "1分钟",
    "5m": "5分钟",
    "15m": "15分钟",
    "30m": "30分钟",
    "60m": "60分钟",
    "120m": "120分钟",
    "1h": "60分钟",
    "1d": "日线",
    "d": "日线",
}


def _coerce_freq(value: str | Freq | None) -> Freq:
    if value is None:
        return Freq.F1
    if isinstance(value, Freq):
        return value
    if not isinstance(value, str):
        return Freq.F1

    freq = value.strip()
    if not freq:
        return Freq.F1

    if freq in FREQ_ALIASES:
        freq = FREQ_ALIASES[freq]

    try:
        return Freq(freq)
    except Exception:
        # 常见写法兼容：如 "5" -> "5分钟"
        normalized = freq.replace(" ", "").replace("min", "分钟").replace("MIN", "分钟")
        if normalized.isdigit():
            normalized = f"{normalized}分钟"
        if normalized in FREQ_ALIASES:
            return Freq(FREQ_ALIASES[normalized])
        return Freq(normalized) if normalized in {x.value for x in Freq} else Freq.F1


def _to_datetime(value) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.replace(tzinfo=None)
    try:
        dt = pd.to_datetime(value)
    except Exception:
        return None
    if pd.isna(dt):
        return None
    dt_val = dt.to_pydatetime()
    if getattr(dt_val, "tzinfo", None) is not None:
        return dt_val.replace(tzinfo=None)
    return dt_val


def _to_float(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _get_row_value(row: Any, *names: str) -> Any:
    for name in names:
        if hasattr(row, name):
            value = getattr(row, name)
            if pd.notna(value):
                return value
    return None


def build_default_level_specs(*, max_levels: int = 3, min_bi_count: int = 7, confirmed_only: bool = True) -> list[RecursiveLevelSpec]:
    """构建默认的递归层级规格（L0/L1/...）。"""
    specs: list[RecursiveLevelSpec] = []
    if max_levels <= 0:
        return specs

    for idx in range(max_levels):
        specs.append(
            RecursiveLevelSpec(
                id=f"L{idx}",
                label=f"L{idx}",
                source="raw_bars" if idx == 0 else f"segments:L{idx - 1}",
                min_bi_count=min_bi_count,
                confirmed_only=confirmed_only,
            )
        )

    return specs


def build_recursive_payload(
    *,
    bars: list[RawBar],
    symbol: str | None = None,
    max_levels: int = 3,
    min_signals: int = 0,
    min_bi_count: int = 7,
    enable_divergence: bool = False,
    base_freq: str | Freq | None = None,
    recursion_mode: str = "structure",
    level_specs: list[RecursiveLevelSpec] | None = None,
    confirmed_only: bool = True,
) -> tuple[dict[str, Any], list[RecursiveLevelSpec], list]:
    """运行递归分析并生成前端 payload。

    返回 (payload, level_specs, resonances)
    """
    if not bars:
        raise ValueError("bars 不能为空")

    symbol = symbol or bars[0].symbol
    specs = level_specs or build_default_level_specs(
        max_levels=max_levels,
        min_bi_count=min_bi_count,
        confirmed_only=confirmed_only,
    )

    level_results, resonances = analyze_recursive_structure(
        base_bars=bars,
        specs=specs,
        max_levels=max_levels,
        min_signals=min_signals,
        enable_divergence=enable_divergence,
    )
    freq = _coerce_freq(base_freq)

    payload = build_recursive_chart_payload(
        symbol=symbol,
        base_bars=bars,
        level_results=level_results,
        resonance_signals=resonances,
        base_freq=freq.value,
        recursion_mode=recursion_mode,
        max_levels=max_levels,
        confirmed_only=confirmed_only,
        generated_at=datetime.now(),
    )

    return payload, specs, resonances


def render_recursive_chart(
    payload: dict[str, Any],
    *,
    title: str | None = None,
    width: str = "1400px",
    height: str = "760px",
    **options,
):
    """将 payload 渲染为 pyecharts Grid 图。"""
    if title is None:
        title = f"{payload.get('symbol', '')} 递归多级别结构图"
    return kline_recursive(payload=payload, title=title, width=width, height=height, **options)


def build_payload_from_csv_bytes(
    data: bytes | str | Path,
    *,
    symbol: str,
    freq: str | Freq | None = None,
    sort_ascending: bool = True,
) -> list[RawBar]:
    """从 CSV 构造 RawBar。

    支持：
    - 上传对象 bytes
    - 本地路径（Path）
    - 原始 CSV 文本字符串
    """
    if isinstance(data, Path):
        df = pd.read_csv(data)
    elif isinstance(data, (bytes, bytearray)):
        df = pd.read_csv(io.BytesIO(data))
    elif isinstance(data, str):
        candidate = Path(data)
        if candidate.exists():
            df = pd.read_csv(candidate)
        else:
            df = pd.read_csv(io.StringIO(data))
    else:
        raise TypeError("不支持的 CSV 输入类型")

    return dataframe_to_raw_bars(df, symbol=symbol, freq=freq, sort_ascending=sort_ascending)


def dataframe_to_raw_bars(
    df: pd.DataFrame,
    *,
    symbol: str,
    freq: str | Freq | None = None,
    sort_ascending: bool = True,
) -> list[RawBar]:
    """把标准 K 线 DataFrame 转成 `RawBar` 列表。"""
    normalized = {c.lower(): c for c in df.columns}
    if any(k not in normalized for k in REQUIRED_BAR_COLUMNS):
        missing = sorted(REQUIRED_BAR_COLUMNS - set(normalized))
        raise ValueError(f"CSV 缺少必需字段: {missing}")

    frame = df.copy()
    frame.columns = [str(c).strip().lower() for c in frame.columns]
    if sort_ascending:
        frame = frame.sort_values("dt")

    freq_enum = _coerce_freq(freq or Freq.F1)
    bars: list[RawBar] = []
    for i, row in enumerate(frame.itertuples(index=False)):
        dt = _to_datetime(getattr(row, "dt"))
        if dt is None:
            continue

        bars.append(
            RawBar(
                symbol=symbol,
                id=int(i),
                dt=dt,
                freq=freq_enum,
                open=_to_float(getattr(row, "open")),
                close=_to_float(getattr(row, "close")),
                high=_to_float(getattr(row, "high")),
                low=_to_float(getattr(row, "low")),
                vol=_to_float(_get_row_value(row, "vol", "volume"), default=0.0),
                amount=_to_float(_get_row_value(row, "amount", "amt", "amount"), default=0.0),
            )
        )

    if not bars:
        raise ValueError("CSV 转换后无有效K线数据")
    return bars


def build_recursive_chart_from_bars(
    bars: list[RawBar],
    *,
    symbol: str | None = None,
    max_levels: int = 3,
    min_signals: int = 0,
    min_bi_count: int = 7,
    enable_divergence: bool = False,
    base_freq: str | Freq | None = None,
    level_specs: list[RecursiveLevelSpec] | None = None,
    confirmed_only: bool = True,
    recursion_mode: str = "structure",
    chart_title: str | None = None,
    width: str = "1400px",
    height: str = "760px",
    **chart_options,
):
    payload, _specs, _ = build_recursive_payload(
        bars=bars,
        symbol=symbol,
        max_levels=max_levels,
        min_signals=min_signals,
        min_bi_count=min_bi_count,
        enable_divergence=enable_divergence,
        base_freq=base_freq,
        recursion_mode=recursion_mode,
        level_specs=level_specs,
        confirmed_only=confirmed_only,
    )
    chart = render_recursive_chart(payload, title=chart_title, width=width, height=height, **chart_options)
    return payload, chart


def build_recursive_chart_from_csv(
    data: bytes | str | Path,
    *,
    symbol: str,
    freq: str | Freq | None = None,
    max_levels: int = 3,
    min_signals: int = 0,
    min_bi_count: int = 7,
    enable_divergence: bool = False,
    confirmed_only: bool = True,
    level_specs: list[RecursiveLevelSpec] | None = None,
    recursion_mode: str = "structure",
    chart_title: str | None = None,
    width: str = "1400px",
    height: str = "760px",
    sort_ascending: bool = True,
    **chart_options,
):
    bars = build_payload_from_csv_bytes(data, symbol=symbol, freq=freq, sort_ascending=sort_ascending)
    return build_recursive_chart_from_bars(
        bars=bars,
        symbol=symbol,
        max_levels=max_levels,
        min_signals=min_signals,
        min_bi_count=min_bi_count,
        enable_divergence=enable_divergence,
        base_freq=freq,
        level_specs=level_specs,
        confirmed_only=confirmed_only,
        recursion_mode=recursion_mode,
        chart_title=chart_title,
        width=width,
        height=height,
        **chart_options,
    )
