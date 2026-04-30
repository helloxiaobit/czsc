from __future__ import annotations

from bisect import bisect_left
from datetime import datetime
from typing import List, Tuple


def build_dt_index(bars):
    return [bar.dt for bar in bars]


def map_dt_to_base(dt_index: List[datetime], dt: datetime) -> int:
    if not dt_index:
        raise ValueError("dt_index 不能为空")

    if dt <= dt_index[0]:
        return 0

    if dt >= dt_index[-1]:
        return len(dt_index) - 1

    pos = bisect_left(dt_index, dt)
    if pos < len(dt_index) and dt_index[pos] == dt:
        return pos

    if pos >= len(dt_index):
        return len(dt_index) - 1

    return pos


def map_interval_to_base(dt_index: List[datetime], sdt: datetime, edt: datetime) -> Tuple[int, int]:
    if sdt > edt:
        raise ValueError("sdt must be <= edt")

    if not dt_index:
        raise ValueError("dt_index 不能为空")

    sidx = map_dt_to_base(dt_index, sdt)
    eidx = map_dt_to_base(dt_index, edt)
    if eidx < sidx:
        eidx = sidx
    return sidx, eidx
