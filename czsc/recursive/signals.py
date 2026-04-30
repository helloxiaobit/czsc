from __future__ import annotations

from datetime import datetime
from statistics import mean
from typing import Dict, Sequence

from czsc.py.enum import Direction
from czsc.py.objects import BI as RawBI

from .axis import map_dt_to_base
from .models import Divergence, ResonanceSignal, Segment, TradeSignal, Zone


def _safe_datetime(value) -> datetime | None:
    return value if isinstance(value, datetime) else None


def _safe_base_idx(level_dt_index: list[datetime] | None, dt: datetime | None) -> int | None:
    if not level_dt_index or dt is None:
        return None
    try:
        return map_dt_to_base(level_dt_index, dt)
    except Exception:
        return None


def _signal_side(signal_type: str) -> str:
    return "buy" if signal_type.endswith("买") else "sell"


def _build_trade_signal(
    level_id: str,
    dt,
    price: float,
    signal_type: str,
    signal_id: str,
    base_idx: int | None,
    source: str = "structure",
) -> TradeSignal:
    return TradeSignal(
        id=signal_id,
        level_id=level_id,
        dt=_safe_datetime(dt) or datetime(1970, 1, 1),
        price=float(price),
        side=_signal_side(signal_type),
        signal_type=signal_type,
        source=source,
        base_idx=base_idx,
        confirmed=True,
    )


def _turning_pattern(bis: list[RawBI], direction: Direction) -> bool:
    if len(bis) < 3 or len(bis) % 2 == 0:
        return False

    if bis[0].direction != direction or bis[-1].direction != direction:
        return False

    if direction == Direction.Down:
        return (max(x.high for x in bis) == bis[0].high) and (min(x.low for x in bis) == bis[-1].low)

    return (max(x.high for x in bis) == bis[-1].high) and (min(x.low for x in bis) == bis[0].low)


def _is_divergence_like(bis: list[RawBI]) -> bool:
    if len(bis) < 3:
        return False

    direction = bis[0].direction
    if direction != bis[-1].direction:
        return False

    key_bis = []
    for i in range(0, len(bis) - 2, 2):
        if i == 0:
            key_bis.append(bis[i])
            continue

        prev, _, cur = bis[i - 2 : i + 1]
        if direction == Direction.Down and cur.low < prev.low:
            key_bis.append(cur)
        if direction == Direction.Up and cur.high > prev.high:
            key_bis.append(cur)

    if len(key_bis) < 2:
        return False

    bc_price = bis[-1].power_price < max(bis[-3].power_price, mean([x.power_price for x in key_bis]))
    bc_volume = bis[-1].power_volume < max(bis[-3].power_volume, mean([x.power_volume for x in key_bis]))
    bc_length = bis[-1].length < max(bis[-3].length, mean([x.length for x in key_bis]))
    return bool(bc_price and (bc_volume or bc_length))


def build_level_signals(
    level_id: str,
    bis: list[RawBI],
    segments: list[Segment],
    min_signals: int = 0,
    base_dt_index: list[datetime] | None = None,
    zones: list[Zone] | None = None,
) -> list[TradeSignal]:
    """
    结构化信号输出（不依赖 cxt 全量信号库，保证轻量可用）。

    以笔级别模式构建：
    - 1买/1卖
    - 2买/2卖
    - 类2买/类2卖
    - 3买/3卖

    返回时会为信号附带 base_idx（能映射到底层轴），方便前端对齐。
    """
    signals: list[TradeSignal] = []
    if not bis:
        return signals

    # 方向与窗口的定义采用“典型分型翻转”启发式，窗口越长置信度越高。
    templates = [
        ("1买", Direction.Down, (21, 19, 17, 15, 13, 11, 9, 7, 5)),
        ("1卖", Direction.Up, (21, 19, 17, 15, 13, 11, 9, 7, 5)),
        ("2买", Direction.Down, (17, 15, 13, 11, 9, 7, 5)),
        ("2卖", Direction.Up, (17, 15, 13, 11, 9, 7, 5)),
        ("类2买", Direction.Down, (13, 11, 9, 7, 5)),
        ("类2卖", Direction.Up, (13, 11, 9, 7, 5)),
        ("3买", Direction.Down, (11, 9, 7, 5)),
        ("3卖", Direction.Up, (11, 9, 7, 5)),
    ]

    emitted_types = set()
    for signal_type, expected_direction, sizes in templates:
        if len(emitted_types) >= 8:
            break

        for size in sizes:
            if len(bis) < size:
                continue

            window = bis[-size:]
            if not _turning_pattern(window, expected_direction):
                continue

            if signal_type in emitted_types:
                break

            trigger = window[-1]
            signal = _build_trade_signal(
                level_id=level_id,
                dt=trigger.edt,
                price=trigger.fx_b.fx,
                signal_type=signal_type,
                signal_id=f"{level_id}:{signal_type}:{trigger.edt.timestamp()}:{len(signals)}",
                base_idx=_safe_base_idx(base_dt_index, trigger.edt),
                source="structure_pattern",
            )

            signals.append(signal)
            emitted_types.add(signal_type)
            break

    # 有背驰线索且缺信号时补充低强度“类2”锚点，避免前端完全空白。
    if len(signals) < min_signals and zones and len(zones) >= 2 and _is_divergence_like(bis[-min(len(bis), 5) :]):
        zone = zones[-1]
        anchor_type = "类2买" if bis[-1].direction == Direction.Down else "类2卖"
        signals.append(
            _build_trade_signal(
                level_id=level_id,
                dt=zone.edt,
                price=zone.zz,
                signal_type=anchor_type,
                signal_id=f"{level_id}:zone_anchor:{int((zone.edt or bis[-1].edt).timestamp())}",
                base_idx=_safe_base_idx(base_dt_index, zone.edt),
                source="structure_divergence_anchor",
            )
        )

    if min_signals > 0:
        return signals[: min_signals]
    return signals


def detect_divergences(level_id: str, bis: list[RawBI], segments: list[Segment]) -> list[Divergence]:
    """
    基于线段级别做轻量化背驰检测：寻找连续线段的长度和幅度是否同时衰减的情况。
    """
    if not segments or len(segments) < 2:
        return []

    divergences: list[Divergence] = []
    for i in range(1, len(segments)):
        prev_seg = segments[i - 1]
        cur_seg = segments[i]

        prev_power = abs(prev_seg.end_price - prev_seg.start_price)
        cur_power = abs(cur_seg.end_price - cur_seg.start_price)
        length_prev = len(prev_seg.bi_indices)
        length_cur = len(cur_seg.bi_indices)

        if cur_seg.direction != prev_seg.direction:
            continue
        if cur_power >= prev_power or length_cur >= length_prev:
            continue

        side = "bottom" if cur_seg.direction == "up" else "top"
        evidence: Dict[str, float | int | tuple] = {
            "segment_power": {"previous": round(prev_power, 4), "current": round(cur_power, 4)},
            "segment_length": {"previous": length_prev, "current": length_cur},
        }
        div_id = f"{level_id}:div:{i}"
        divergence = Divergence(
            id=div_id,
            level_id=level_id,
            side=side,
            kind="趋势背驰" if prev_seg.quality == "strict" else "盘整背驰",
            bi_indices=cur_seg.bi_indices,
            segment_indices=(i - 1, i),
            sdt=cur_seg.sdt,
            edt=cur_seg.edt,
            price=cur_seg.end_price,
            base_sidx=cur_seg.base_sidx,
            base_eidx=cur_seg.base_eidx,
            evidence=evidence,
        )

        divergences.append(divergence)
        prev_seg.is_divergence_leg = True
        cur_seg.is_divergence_leg = True
        prev_seg.divergence_id = div_id
        cur_seg.divergence_id = div_id

    return divergences


def _higher_signal_in_window(
    lower: TradeSignal,
    higher: TradeSignal,
    higher_level_signals: Sequence[TradeSignal],
) -> bool:
    if lower.base_idx is None or higher.base_idx is None:
        return False

    same_side = [x for x in higher_level_signals if x.side == lower.side and x.base_idx is not None]
    if not same_side:
        return False

    sorted_signals = sorted(same_side, key=lambda x: x.base_idx)
    try:
        idx = next(i for i, x in enumerate(sorted_signals) if x.id == higher.id)
    except StopIteration:
        return False

    start = sorted_signals[idx].base_idx
    end = sorted_signals[idx + 1].base_idx if idx + 1 < len(sorted_signals) else start + 9999
    return start <= lower.base_idx <= end


def _resonance_strength(
    higher: TradeSignal,
    lower: TradeSignal,
    *,
    same_trend: bool,
    in_window: bool,
    with_divergence: bool,
    higher_has_dt: bool,
) -> int:
    if higher.base_idx is None or lower.base_idx is None:
        return 40

    score = 60
    if same_trend:
        score += 10
    if in_window and abs(lower.base_idx - higher.base_idx) < 120:
        score += 10
    if higher_has_dt:
        score += 10
    if with_divergence:
        score += 10
    return min(score, 100)


def _class1_matches(higher_type: str, lower_type: str) -> bool:
    buy_map = {"2买", "类2买", "3买"}
    sell_map = {"2卖", "类2卖", "3卖"}
    return (
        (higher_type in buy_map and lower_type == "2买")
        or (higher_type in sell_map and lower_type == "2卖")
    )


def _active_divergence(
    signal: TradeSignal,
    divergences: Sequence[Divergence] | None,
) -> Divergence | None:
    if not divergences:
        return None

    sid = 0
    if signal.base_idx is None:
        return None
    candidates = [d for d in divergences if d.side == signal.side.replace("buy", "bottom").replace("sell", "top")]
    if not candidates:
        return None

    for d in candidates:
        if d.base_sidx is None or d.base_eidx is None:
            continue
        if d.base_sidx <= signal.base_idx <= d.base_eidx and sid < d.base_eidx:
            sid = d.base_eidx
    if not sid:
        return None
    return candidates[-1]


def detect_cross_level_resonance(
    higher_level_signals: Sequence[TradeSignal],
    lower_level_signals: Sequence[TradeSignal],
    enable_divergence: bool = False,
    divergence_signals: Sequence[Divergence] | None = None,
) -> list[ResonanceSignal]:
    """
    匹配高低级别信号，生成共振。

    第一类：大2+小2 / 类2+小2 / 大3+小2（默认）。
    第二类：背驰后的大1+小2（当 enable_divergence=True 且有背驰证据时）。
    """
    resonances: list[ResonanceSignal] = []
    if not higher_level_signals or not lower_level_signals:
        return resonances

    seen = set()
    for h in higher_level_signals:
        higher_has_dt = bool(h.dt)
        for l in lower_level_signals:
            if l.side != h.side:
                continue
            if not _higher_signal_in_window(l, h, higher_level_signals):
                continue

            is_class1 = l.signal_type in {"2买", "2卖"} and _class1_matches(h.signal_type, l.signal_type)
            is_class2 = False
            divergence = None
            if enable_divergence and h.signal_type in {"1买", "1卖"} and l.signal_type == ("2买" if h.side == "buy" else "2卖"):
                divergence = _active_divergence(h, divergence_signals)
                is_class2 = divergence is not None

            if not is_class1 and not is_class2:
                continue

            category = "class2" if is_class2 else "class1"
            visual_role = "red_pulse" if is_class2 else ("gold_blink" if h.side == "buy" else "magenta_blink")
            key = f"{h.id}#{l.id}"
            if key in seen:
                continue
            seen.add(key)

            resonances.append(
                ResonanceSignal(
                    id=f"{h.id}:{l.id}",
                    category=category,
                    name=f"{h.signal_type}+{l.signal_type}",
                    side=h.side,
                    higher_level_id=h.level_id,
                    lower_level_id=l.level_id,
                    higher_signal_id=h.id,
                    lower_signal_id=l.id,
                    divergence_id=(divergence.id if divergence else None),
                    dt=h.dt,
                    price=l.price,
                    base_idx=l.base_idx,
                    strength=_resonance_strength(
                        higher=h,
                        lower=l,
                        same_trend=(h.signal_type.startswith("3") or h.signal_type.startswith("类3")),
                        in_window=True,
                        with_divergence=is_class2,
                        higher_has_dt=higher_has_dt,
                    ),
                    visual_role=visual_role,
                )
            )

    return resonances
