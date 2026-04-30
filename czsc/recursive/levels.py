from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional, Tuple

from czsc.py.analyze import CZSC
from czsc.py.enum import Freq
from czsc.py.objects import BI, RawBar

from .axis import build_dt_index, map_interval_to_base
from .models import RecursiveLevelResult, RecursiveLevelSpec, Segment
from .segments import find_segments


def _infer_next_freq(freq: Freq) -> Freq:
    freq_order = {
        Freq.F1: Freq.F5,
        Freq.F2: Freq.F5,
        Freq.F3: Freq.F5,
        Freq.F4: Freq.F5,
        Freq.F5: Freq.F15,
        Freq.F6: Freq.F15,
        Freq.F10: Freq.F15,
        Freq.F12: Freq.F15,
        Freq.F15: Freq.F30,
        Freq.F20: Freq.F30,
        Freq.F30: Freq.F60,
        Freq.F60: Freq.D,
    }
    return freq_order.get(freq, freq)


def _to_raw_base(
    dt_index: List[datetime],
    bars: list[RawBar],
    sidx: Optional[int],
    eidx: Optional[int],
) -> Tuple[List[RawBar], Optional[int], Optional[int]]:
    if not bars or sidx is None or eidx is None:
        return [], None, None

    if not dt_index:
        return [], None, None

    length = len(bars)
    s = max(0, min(length - 1, int(sidx)))
    e = max(0, min(length - 1, int(eidx)))
    if e < s:
        s, e = e, s

    sub = bars[s : e + 1]
    return sub, s, e


def segments_to_synthetic_bars(
    segments: list[Segment],
    freq: Freq,
    symbol: str,
    source_bars: list[RawBar],
) -> list[RawBar]:
    """
    把已确认线段压缩成上一级结构K线。

    open = segment.start_price
    close = segment.end_price
    high = segment.high
    low = segment.low
    dt = segment.edt
    """
    if not segments:
        return []

    # 映射源序列到“当前频率坐标轴”，用于聚合成交量与成交额
    source_dt_index = build_dt_index(source_bars)
    bars: list[RawBar] = []

    for i, seg in enumerate(segments):
        if not seg.confirmed:
            continue

        vol = 0
        amount = 0
        cache = {"synthetic": True}

        if source_dt_index and seg.sdt is not None and seg.edt is not None:
            try:
                sidx, eidx = map_interval_to_base(source_dt_index, seg.sdt, seg.edt)
                sub_bars, _, _ = _to_raw_base(source_dt_index, source_bars, sidx, eidx)
                if sub_bars:
                    vol = sum(x.vol for x in sub_bars)
                    amount = sum(x.amount for x in sub_bars)
                    cache["synthetic_source_span"] = [sidx, eidx]
            except Exception:
                pass

        bars.append(
            RawBar(
                symbol=symbol,
                id=i,
                dt=seg.edt,
                freq=freq,
                open=float(seg.start_price),
                close=float(seg.end_price),
                high=float(seg.high),
                low=float(seg.low),
                vol=float(vol),
                amount=float(amount),
                cache=cache,
            )
        )

    return bars


def _map_span_to_base(base_dt: List[datetime], dt_from: datetime, dt_to: datetime) -> Tuple[Optional[int], Optional[int]]:
    if not base_dt or not dt_from or not dt_to:
        return None, None

    try:
        return map_interval_to_base(base_dt, dt_from, dt_to)
    except Exception:
        return None, None


def _prepare_bis(level_czsc: CZSC, confirmed_only: bool) -> list[BI]:
    if not level_czsc:
        return []
    if confirmed_only:
        return list(level_czsc.finished_bis)

    return list(level_czsc.bi_list)


def _map_bi_spans(level: RecursiveLevelResult, dt_index: List[datetime]) -> None:
    level.bi_base_spans = []
    for bi in level.bis:
        if bi.sdt is not None and bi.edt is not None:
            level.bi_base_spans.append(_map_span_to_base(dt_index, bi.sdt, bi.edt))
        else:
            level.bi_base_spans.append((None, None))


def _map_segment_spans(level: RecursiveLevelResult, dt_index: List[datetime]) -> None:
    level.segment_base_spans = []
    for seg in level.segments:
        if seg.sdt is not None and seg.edt is not None:
            seg.base_sidx, seg.base_eidx = _map_span_to_base(dt_index, seg.sdt, seg.edt)
            level.segment_base_spans.append((seg.base_sidx, seg.base_eidx))
        else:
            seg.base_sidx = None
            seg.base_eidx = None
            level.segment_base_spans.append((None, None))


def build_recursive_levels(
    base_bars: list[RawBar],
    specs: list[RecursiveLevelSpec],
    max_levels: int = 3,
) -> Dict[str, RecursiveLevelResult]:
    """
    从底层K线递归构建各级别结构。

    - 只使用已确认线段推进到上一级\n
    - 数据不足时优雅停止\n
    - 保留所有级别到底层K线的映射坐标
    """
    if not base_bars:
        return {}
    if max_levels <= 0 or not specs:
        return {}

    bars = sorted(base_bars, key=lambda x: x.dt)
    base_dt_index = build_dt_index(bars)

    result: Dict[str, RecursiveLevelResult] = {}
    current_bars = bars
    current_dt_index = base_dt_index
    prev_id: Optional[str] = None

    for level_idx, spec in enumerate(specs[: max_levels]):
        if not current_bars:
            break

        c = CZSC(bars=current_bars, max_bi_num=max(200, spec.min_bi_count * 20))
        level = RecursiveLevelResult(spec=spec, dt_index=base_dt_index, bars=current_bars)
        level.bis = _prepare_bis(c, spec.confirmed_only)

        segments = find_segments(level.bis, level_id=spec.id, mode="strict", min_bi_count=spec.min_bi_count)

        if not segments and spec.confirmed_only:
            segments = find_segments(level.bis, level_id=spec.id, mode="pragmatic", min_bi_count=max(2, spec.min_bi_count))
            for seg in segments:
                seg.confirmed = False
                seg.quality = "pragmatic"

        # 上一级来源关系
        for seg in segments:
            seg.source_parent_level_id = prev_id

        level.segments = segments

        _map_bi_spans(level, current_dt_index)
        _map_segment_spans(level, base_dt_index)
        result[spec.id] = level

        if level_idx + 1 >= max_levels:
            break
        if len(level.segments) < 2:
            break

        next_freq = _infer_next_freq(current_bars[0].freq)
        source_bars = segments_to_synthetic_bars(
            segments=level.segments,
            freq=next_freq,
            symbol=spec.id,
            source_bars=current_bars,
        )
        if not source_bars:
            break
        if len(source_bars) < spec.min_bi_count:
            break

        current_bars = source_bars
        current_dt_index = build_dt_index(current_bars)
        prev_id = spec.id

    return result
