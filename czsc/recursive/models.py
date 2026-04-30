from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from czsc.py.objects import BI, RawBar


@dataclass
class RecursiveLevelSpec:
    id: str
    label: str
    source: str
    min_bi_count: int = 7
    confirmed_only: bool = True
    max_segments: Optional[int] = None


@dataclass
class Segment:
    level_id: str
    index: int
    direction: str
    sdt: datetime
    edt: datetime
    start_price: float
    end_price: float
    high: float
    low: float
    bi_indices: Tuple[int, ...]
    confirmed: bool = True
    base_sidx: Optional[int] = None
    base_eidx: Optional[int] = None
    source_parent_level_id: Optional[str] = None
    source_segment_indices: Tuple[int, ...] = field(default_factory=tuple)
    quality: str = "strict"
    is_divergence_leg: bool = False
    divergence_id: Optional[str] = None


@dataclass
class Zone:
    level_id: str
    index: int
    sdt: Optional[datetime]
    edt: Optional[datetime]
    zg: float
    zd: float
    gg: float
    dd: float
    zz: float
    element_indices: Tuple[int, ...]
    source_type: str = "bi"
    base_sidx: Optional[int] = None
    base_eidx: Optional[int] = None


@dataclass
class TrendType:
    level_id: str
    index: int
    type: str
    zone_indices: Tuple[int, ...]
    sdt: Optional[datetime]
    edt: Optional[datetime]
    base_sidx: Optional[int] = None
    base_eidx: Optional[int] = None


@dataclass
class TradeSignal:
    id: str
    level_id: str
    dt: datetime
    price: float
    side: str
    signal_type: str
    source: str
    base_idx: Optional[int] = None
    confirmed: bool = True


@dataclass
class Divergence:
    id: str
    level_id: str
    side: str
    kind: str
    bi_indices: Tuple[int, ...]
    segment_indices: Tuple[int, ...]
    sdt: datetime
    edt: datetime
    price: float
    base_sidx: Optional[int] = None
    base_eidx: Optional[int] = None
    evidence: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ResonanceSignal:
    id: str
    category: str
    name: str
    side: str
    higher_level_id: str
    lower_level_id: str
    higher_signal_id: str
    lower_signal_id: str
    divergence_id: Optional[str]
    dt: datetime
    price: float
    base_idx: Optional[int] = None
    strength: int = 0
    visual_role: str = "gold_blink"


@dataclass
class RecursiveLevelResult:
    spec: RecursiveLevelSpec
    dt_index: List[datetime] = field(default_factory=list)
    bars: List[RawBar] = field(default_factory=list)
    bis: List[BI] = field(default_factory=list)
    bi_base_spans: List[Tuple[Optional[int], Optional[int]]] = field(default_factory=list)
    segments: List[Segment] = field(default_factory=list)
    segment_base_spans: List[Tuple[Optional[int], Optional[int]]] = field(default_factory=list)
    zones: List[Zone] = field(default_factory=list)
    trend_types: List[TrendType] = field(default_factory=list)
    signals: List[TradeSignal] = field(default_factory=list)
    divergences: List[Divergence] = field(default_factory=list)
