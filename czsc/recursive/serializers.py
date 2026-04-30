from __future__ import annotations

from datetime import datetime

from .models import (
    Segment,
    Zone,
    TradeSignal,
    Divergence,
    ResonanceSignal,
    TrendType,
)


def to_iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    return dt.isoformat()


def _to_list(item):
    if isinstance(item, tuple):
        return list(item)
    return item


def serialize_segment(seg: Segment) -> dict:
    return {
        "level_id": seg.level_id,
        "index": seg.index,
        "direction": seg.direction,
        "sdt": to_iso(seg.sdt),
        "edt": to_iso(seg.edt),
        "start_price": seg.start_price,
        "end_price": seg.end_price,
        "high": seg.high,
        "low": seg.low,
        "bi_indices": _to_list(seg.bi_indices),
        "confirmed": seg.confirmed,
        "base_sidx": seg.base_sidx,
        "base_eidx": seg.base_eidx,
        "source_parent_level_id": seg.source_parent_level_id,
        "source_segment_indices": _to_list(seg.source_segment_indices),
        "quality": seg.quality,
        "is_divergence_leg": seg.is_divergence_leg,
        "divergence_id": seg.divergence_id,
    }


def serialize_zone(zone: Zone) -> dict:
    return {
        "level_id": zone.level_id,
        "index": zone.index,
        "sdt": to_iso(zone.sdt),
        "edt": to_iso(zone.edt),
        "zg": zone.zg,
        "zd": zone.zd,
        "gg": zone.gg,
        "dd": zone.dd,
        "zz": zone.zz,
        "element_indices": _to_list(zone.element_indices),
        "source_type": zone.source_type,
        "base_sidx": zone.base_sidx,
        "base_eidx": zone.base_eidx,
    }


def serialize_trade_signal(sig: TradeSignal) -> dict:
    return {
        "id": sig.id,
        "level_id": sig.level_id,
        "dt": to_iso(sig.dt),
        "price": sig.price,
        "side": sig.side,
        "signal_type": sig.signal_type,
        "source": sig.source,
        "base_idx": sig.base_idx,
        "confirmed": sig.confirmed,
    }


def serialize_divergence(div: Divergence) -> dict:
    return {
        "id": div.id,
        "level_id": div.level_id,
        "side": div.side,
        "kind": div.kind,
        "bi_indices": _to_list(div.bi_indices),
        "segment_indices": _to_list(div.segment_indices),
        "sdt": to_iso(div.sdt),
        "edt": to_iso(div.edt),
        "price": div.price,
        "base_sidx": div.base_sidx,
        "base_eidx": div.base_eidx,
        "evidence": div.evidence,
    }


def serialize_resonance(sig: ResonanceSignal) -> dict:
    return {
        "id": sig.id,
        "category": sig.category,
        "name": sig.name,
        "side": sig.side,
        "higher_level_id": sig.higher_level_id,
        "lower_level_id": sig.lower_level_id,
        "higher_signal_id": sig.higher_signal_id,
        "lower_signal_id": sig.lower_signal_id,
        "divergence_id": sig.divergence_id,
        "dt": to_iso(sig.dt),
        "price": sig.price,
        "base_idx": sig.base_idx,
        "strength": sig.strength,
        "visual_role": sig.visual_role,
    }


def serialize_trend_type(tt: TrendType) -> dict:
    return {
        "level_id": tt.level_id,
        "index": tt.index,
        "type": tt.type,
        "zone_indices": _to_list(tt.zone_indices),
        "sdt": to_iso(tt.sdt),
        "edt": to_iso(tt.edt),
        "base_sidx": tt.base_sidx,
        "base_eidx": tt.base_eidx,
    }
