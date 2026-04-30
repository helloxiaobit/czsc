from __future__ import annotations

from datetime import datetime

from czsc.py.objects import BI
from czsc.utils.sig import get_zs_seq

from .axis import map_interval_to_base
from .models import TrendType, Zone


def _safe_base_span(level_dt_index: list[datetime] | None, sdt: datetime | None, edt: datetime | None):
    if not level_dt_index or sdt is None or edt is None:
        return None, None

    try:
        return map_interval_to_base(level_dt_index, sdt, edt)
    except Exception:
        return None, None


def find_zones_from_bis(bis: list[BI], level_id: str, base_dt_index: list[datetime] | None = None) -> list[Zone]:
    """
    使用 BI 序列生成可视化中枢列表。
    """
    zs_seq = get_zs_seq(list(bis))
    zones: list[Zone] = []

    cursor = 0
    for idx, zs in enumerate(zs_seq):
        if not zs.is_valid:
            cursor += len(zs.bis)
            continue

        element_indices = tuple(range(cursor, cursor + len(zs.bis)))
        base_sidx, base_eidx = _safe_base_span(base_dt_index, zs.sdt, zs.edt)
        zones.append(
            Zone(
                level_id=level_id,
                index=idx,
                sdt=zs.sdt,
                edt=zs.edt,
                zg=zs.zg,
                zd=zs.zd,
                gg=zs.gg,
                dd=zs.dd,
                zz=zs.zz,
                element_indices=element_indices,
                source_type="bi",
                base_sidx=base_sidx,
                base_eidx=base_eidx,
            )
        )
        cursor += len(zs.bis)

    return zones


def _relation_type(prev: Zone, curr: Zone) -> str:
    if curr.zg >= prev.gg and curr.zd >= prev.zd:
        return "up"
    if curr.dd <= prev.dd and curr.zg <= prev.dd:
        return "down"
    if curr.zg > prev.gg and curr.zd < prev.dd:
        return "expand"
    return "overlap"


def _trend_type_from_relation(relation: str) -> str:
    return {
        "up": "上涨趋势",
        "down": "下跌趋势",
        "expand": "中枢扩展",
        "overlap": "盘整",
    }[relation]


def detect_trend_types(zones: list[Zone], level_id: str | None = None) -> list[TrendType]:
    """
    根据中枢序列给出趋势段分段结果。
    """
    if not zones:
        return []

    base_level_id = level_id or zones[0].level_id
    if len(zones) == 1:
        return [
            TrendType(
                level_id=base_level_id,
                index=0,
                type="盘整",
                zone_indices=(0,),
                sdt=zones[0].sdt,
                edt=zones[0].edt,
                base_sidx=zones[0].base_sidx,
                base_eidx=zones[0].base_eidx,
            )
        ]

    trend_types: list[TrendType] = []
    current_rel = _relation_type(zones[0], zones[1])
    start = 0

    for i in range(1, len(zones)):
        rel = _relation_type(zones[i - 1], zones[i])
        if rel != current_rel:
            trend_types.append(
                TrendType(
                    level_id=base_level_id,
                    index=len(trend_types),
                    type=_trend_type_from_relation(current_rel),
                    zone_indices=tuple(range(start, i)),
                    sdt=zones[start].sdt,
                    edt=zones[i - 1].edt,
                    base_sidx=zones[start].base_sidx,
                    base_eidx=zones[i - 1].base_eidx,
                )
            )
            start = i - 1
            current_rel = rel

    trend_types.append(
        TrendType(
            level_id=base_level_id,
            index=len(trend_types),
            type=_trend_type_from_relation(current_rel),
            zone_indices=tuple(range(start, len(zones))),
            sdt=zones[start].sdt,
            edt=zones[-1].edt,
            base_sidx=zones[start].base_sidx,
            base_eidx=zones[-1].base_eidx,
        )
    )

    return trend_types
