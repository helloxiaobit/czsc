from __future__ import annotations

from typing import List

from czsc.py.enum import Direction
from czsc.py.objects import BI

from .models import Segment


def _bi_direction_value(bi: BI) -> str:
    return "up" if bi.direction == Direction.Up else "down"


def _segment_slice_ok(bis: list[BI], start: int, end: int, direction: str) -> bool:
    if end - start + 1 < 3:
        return False
    first = bis[start]
    last = bis[end]
    if direction == "up":
        return last.high >= first.high
    return last.low <= first.low


def find_segments(
    bis: List[BI],
    level_id: str,
    mode: str = "strict",
    min_bi_count: int = 3,
) -> List[Segment]:
    if not bis:
        return []
    if mode not in {"strict", "pragmatic"}:
        raise ValueError("mode must be strict or pragmatic")

    target_len = 2 if mode == "pragmatic" else min_bi_count
    segments: List[Segment] = []

    if len(bis) < target_len:
        return []

    current = 0
    current_dir = _bi_direction_value(bis[current])

    for idx in range(2, len(bis)):
        if idx - current + 1 < target_len:
            continue

        if _bi_direction_value(bis[idx]) == current_dir:
            sub = bis[current : idx + 1]
            if len(sub) >= target_len and sub[0].direction == sub[-1].direction:
                seg = Segment(
                    level_id=level_id,
                    index=len(segments),
                    direction=current_dir,
                    sdt=sub[0].sdt,
                    edt=sub[-1].edt,
                    start_price=sub[0].fx_a.fx,
                    end_price=sub[-1].fx_b.fx,
                    high=max(x.high for x in sub),
                    low=min(x.low for x in sub),
                    bi_indices=tuple(range(current, idx + 1)),
                    confirmed=True,
                    quality="strict" if mode == "strict" else "pragmatic",
                )

                segments.append(seg)
                current = idx

    if len(bis) - current >= target_len:
        sub = bis[current:]
        if sub[0].direction == sub[-1].direction:
            segments.append(
                Segment(
                    level_id=level_id,
                    index=len(segments),
                    direction=_bi_direction_value(sub[0]),
                    sdt=sub[0].sdt,
                    edt=sub[-1].edt,
                    start_price=sub[0].fx_a.fx,
                    end_price=sub[-1].fx_b.fx,
                    high=max(x.high for x in sub),
                    low=min(x.low for x in sub),
                    bi_indices=tuple(range(current, len(bis))),
                    confirmed=True,
                    quality="strict" if mode == "strict" else "pragmatic",
                )
            )

    if not segments:
        return []

    return segments
