from __future__ import annotations

from collections.abc import Sequence

from .levels import build_recursive_levels
from .models import RecursiveLevelResult, RecursiveLevelSpec, ResonanceSignal
from .zones import detect_trend_types, find_zones_from_bis
from .signals import build_level_signals, detect_cross_level_resonance, detect_divergences


def analyze_recursive_structure(
    base_bars,
    specs: Sequence[RecursiveLevelSpec],
    *,
    max_levels: int = 3,
    min_signals: int = 0,
    enable_divergence: bool = False,
) -> tuple[dict[str, RecursiveLevelResult], list[ResonanceSignal]]:
    """
    递归构建“笔/线段/中枢/背驰/共振”核心结构，返回每层结果与共振列表。

    Args:
        base_bars: 底层K线（原始频率）。
        specs: 递归级别规格列表，按绘制顺序排列。
        max_levels: 最大级数。
        min_signals: 每层保留最低信号数（0 表示不裁剪）。
        enable_divergence: 是否开启第二类共振（背驰+大1+小2）配对。
    """
    level_results = build_recursive_levels(base_bars=base_bars, specs=list(specs), max_levels=max_levels)
    level_ids: list[str] = [x.id for x in specs]

    for level_id in level_ids:
        level = level_results.get(level_id)
        if level is None:
            continue

        level.zones = find_zones_from_bis(level.bis, level_id=level_id, base_dt_index=level.dt_index)
        level.trend_types = detect_trend_types(level.zones, level_id=level_id)
        level.signals = build_level_signals(
            level_id=level_id,
            bis=level.bis,
            segments=level.segments,
            min_signals=min_signals,
            base_dt_index=level.dt_index,
            zones=level.zones,
        )
        level.divergences = detect_divergences(level_id=level_id, bis=level.bis, segments=level.segments)

    level_ids = [lid for lid in level_ids if lid in level_results]
    if not level_ids:
        return {}, []

    resonances: list[ResonanceSignal] = []
    for higher_id, lower_id in zip(level_ids[:-1], level_ids[1:]):
        higher_level = level_results[higher_id]
        lower_level = level_results[lower_id]
        resonances.extend(
            detect_cross_level_resonance(
                higher_level_signals=higher_level.signals,
                lower_level_signals=lower_level.signals,
                enable_divergence=enable_divergence,
                divergence_signals=higher_level.divergences,
            )
        )

    return level_results, resonances
