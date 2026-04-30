"""
使用 pyecharts 定制绘图模块

"""
# ruff: noqa: E101  # JS 代码嵌入 Python 字符串，mixed spaces/tabs 是误报
from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional

import numpy as np
from pyecharts import options as opts
from pyecharts.charts import Bar, EffectScatter, Grid, Kline, Line, Scatter
from pyecharts.commons.utils import JsCode

from czsc.py.enum import Operate

from .ta import MACD, SMA

if TYPE_CHECKING:
    from lightweight_charts import Chart


def kline_pro(
    kline: list[dict],
    fx: list[dict] = None,
    bi: list[dict] = None,
    xd: list[dict] = None,
    bs: list[dict] = None,
    title: str = "缠中说禅K线分析",
    t_seq: list[int] = None,
    width: str = "1400px",
    height: str = "580px",
) -> Grid:
    """绘制缠中说禅K线分析结果

    :param kline: K线
    :param fx: 分型识别结果
    :param bi: 笔识别结果
        {'dt': Timestamp('2020-11-26 00:00:00'),
          'fx_mark': 'd',
          'start_dt': Timestamp('2020-11-25 00:00:00'),
          'end_dt': Timestamp('2020-11-27 00:00:00'),
          'fx_high': 144.87,
          'fx_low': 138.0,
          'bi': 138.0}
    :param xd: 线段识别结果
    :param bs: 买卖点
    :param title: 图表标题
    :param t_seq: 均线系统
    :param width: 图表宽度
    :param height: 图表高度
    :return: 用Grid组合好的图表
    """
    # 配置项设置
    # ------------------------------------------------------------------------------------------------------------------
    if t_seq is None:
        t_seq = []
    if bs is None:
        bs = []
    if xd is None:
        xd = []
    if bi is None:
        bi = []
    if fx is None:
        fx = []
    bg_color = "#1f212d"  # 背景
    up_color = "#F9293E"
    down_color = "#00aa3b"

    init_opts = opts.InitOpts(bg_color=bg_color, width=width, height=height, animation_opts=opts.AnimationOpts(False))
    title_opts = opts.TitleOpts(
        title=title,
        pos_top="1%",
        title_textstyle_opts=opts.TextStyleOpts(color=up_color, font_size=20),
        subtitle_textstyle_opts=opts.TextStyleOpts(color=down_color, font_size=12),
    )

    label_show_opts = opts.LabelOpts(is_show=True)
    label_not_show_opts = opts.LabelOpts(is_show=False)
    legend_not_show_opts = opts.LegendOpts(is_show=False)
    red_item_style = opts.ItemStyleOpts(color=up_color)
    green_item_style = opts.ItemStyleOpts(color=down_color)
    k_style_opts = opts.ItemStyleOpts(
        color=up_color, color0=down_color, border_color=up_color, border_color0=down_color, opacity=0.8
    )

    legend_opts = opts.LegendOpts(
        is_show=True,
        pos_top="1%",
        pos_left="30%",
        item_width=14,
        item_height=8,
        textstyle_opts=opts.TextStyleOpts(font_size=12, color="#0e99e2"),
    )
    brush_opts = opts.BrushOpts(
        tool_box=["rect", "polygon", "keep", "clear"],
        x_axis_index="all",
        brush_link="all",
        out_of_brush={"colorAlpha": 0.1},
        brush_type="lineX",
    )

    axis_pointer_opts = opts.AxisPointerOpts(is_show=True, link=[{"xAxisIndex": "all"}])

    dz_inside = opts.DataZoomOpts(False, "inside", xaxis_index=[0, 1, 2], range_start=80, range_end=100)
    dz_slider = opts.DataZoomOpts(
        True, "slider", xaxis_index=[0, 1, 2], pos_top="96%", pos_bottom="0%", range_start=80, range_end=100
    )

    yaxis_opts = opts.AxisOpts(
        is_scale=True,
        min_="dataMin",
        max_="dataMax",
        splitline_opts=opts.SplitLineOpts(is_show=False),
        axislabel_opts=opts.LabelOpts(color="#c7c7c7", font_size=8, position="inside"),
    )

    grid0_xaxis_opts = opts.AxisOpts(
        type_="category",
        grid_index=0,
        axislabel_opts=label_not_show_opts,
        split_number=20,
        min_="dataMin",
        max_="dataMax",
        is_scale=True,
        boundary_gap=False,
        splitline_opts=opts.SplitLineOpts(is_show=False),
        axisline_opts=opts.AxisLineOpts(is_on_zero=False),
    )

    tool_tip_opts = opts.TooltipOpts(
        trigger="axis",
        axis_pointer_type="cross",
        background_color="rgba(245, 245, 245, 0.8)",
        border_width=1,
        border_color="#ccc",
        position=JsCode(
            """
                    function (pos, params, el, elRect, size) {
    					var obj = {top: 10};
    					obj[['left', 'right'][+(pos[0] < size.viewSize[0] / 2)]] = 30;
    					return obj;
    				}
                    """
        ),
        textstyle_opts=opts.TextStyleOpts(color="#000"),
    )

    # 数据预处理
    # ------------------------------------------------------------------------------------------------------------------
    dts = [x["dt"] for x in kline]
    # k_data = [[x['open'], x['close'], x['low'], x['high']] for x in kline]
    k_data = [
        opts.CandleStickItem(name=i, value=[x["open"], x["close"], x["low"], x["high"]]) for i, x in enumerate(kline)
    ]

    vol = []
    for i, row in enumerate(kline):
        item_style = red_item_style if row["close"] > row["open"] else green_item_style
        bar = opts.BarItem(name=i, value=row["vol"], itemstyle_opts=item_style, label_opts=label_not_show_opts)
        vol.append(bar)

    close = np.array([x["close"] for x in kline], dtype=np.double)
    diff, dea, macd = MACD(close)
    macd_bar = []
    for i, v in enumerate(macd.tolist()):
        item_style = red_item_style if v > 0 else green_item_style
        bar = opts.BarItem(name=i, value=round(v, 4), itemstyle_opts=item_style, label_opts=label_not_show_opts)
        macd_bar.append(bar)

    diff = diff.round(4)
    dea = dea.round(4)

    # K 线主图
    # ------------------------------------------------------------------------------------------------------------------
    chart_k = Kline()
    chart_k.add_xaxis(xaxis_data=dts)
    chart_k.add_yaxis(series_name="Kline", y_axis=k_data, itemstyle_opts=k_style_opts)

    chart_k.set_global_opts(
        legend_opts=legend_opts,
        datazoom_opts=[dz_inside, dz_slider],
        yaxis_opts=yaxis_opts,
        tooltip_opts=tool_tip_opts,
        axispointer_opts=axis_pointer_opts,
        brush_opts=brush_opts,
        title_opts=title_opts,
        xaxis_opts=grid0_xaxis_opts,
    )

    # 加入买卖点 - 多头操作 - 空头操作
    if bs:
        long_opens = {"i": [], "val": []}
        long_exits = {"i": [], "val": []}
        short_opens = {"i": [], "val": []}
        short_exits = {"i": [], "val": []}

        for op in bs:
            _dt = op["dt"]
            _price = round(op["price"], 4)
            _info = f"{op['op_desc']} - 价格{_price}"

            if op["op"] in [Operate.LO]:
                long_opens["i"].append(_dt)
                long_opens["val"].append([_price, _info])

            if op["op"] in [Operate.LE]:
                long_exits["i"].append(_dt)
                long_exits["val"].append([_price, _info])

            if op["op"] in [Operate.SO]:
                short_opens["i"].append(_dt)
                short_opens["val"].append([_price, _info])

            if op["op"] in [Operate.SE]:
                short_exits["i"].append(_dt)
                short_exits["val"].append([_price, _info])

        chart_lo = (
            Scatter()
            .add_xaxis(xaxis_data=long_opens["i"])
            .add_yaxis(
                series_name="多头操作",
                y_axis=long_opens["val"],
                symbol_size=25,
                symbol="diamond",
                label_opts=opts.LabelOpts(is_show=False),
                itemstyle_opts=opts.ItemStyleOpts(color="#ff461f"),
                tooltip_opts=opts.TooltipOpts(
                    textstyle_opts=opts.TextStyleOpts(font_size=12),
                    formatter=JsCode("function (params) {return params.value[2];}"),
                ),
            )
        )
        chart_le = (
            Scatter()
            .add_xaxis(xaxis_data=long_exits["i"])
            .add_yaxis(
                series_name="多头操作",
                y_axis=long_exits["val"],
                symbol_size=25,
                symbol="diamond",
                label_opts=opts.LabelOpts(is_show=False),
                itemstyle_opts=opts.ItemStyleOpts(color="#afdd22"),
                tooltip_opts=opts.TooltipOpts(
                    textstyle_opts=opts.TextStyleOpts(font_size=12),
                    formatter=JsCode("function (params) {return params.value[2];}"),
                ),
            )
        )
        chart_so = (
            Scatter()
            .add_xaxis(xaxis_data=short_opens["i"])
            .add_yaxis(
                series_name="空头订单",
                y_axis=short_opens["val"],
                symbol_size=25,
                symbol="triangle",
                label_opts=opts.LabelOpts(is_show=False),
                itemstyle_opts=opts.ItemStyleOpts(color="#ff461f"),
                tooltip_opts=opts.TooltipOpts(
                    textstyle_opts=opts.TextStyleOpts(font_size=12),
                    formatter=JsCode("function (params) {return params.value[2];}"),
                ),
            )
        )
        chart_se = (
            Scatter()
            .add_xaxis(xaxis_data=short_exits["i"])
            .add_yaxis(
                series_name="空头订单",
                y_axis=short_exits["val"],
                symbol_size=25,
                symbol="triangle",
                label_opts=opts.LabelOpts(is_show=False),
                itemstyle_opts=opts.ItemStyleOpts(color="#afdd22"),
                tooltip_opts=opts.TooltipOpts(
                    textstyle_opts=opts.TextStyleOpts(font_size=12),
                    formatter=JsCode("function (params) {return params.value[2];}"),
                ),
            )
        )

        chart_k = chart_k.overlap(chart_lo)
        chart_k = chart_k.overlap(chart_le)
        chart_k = chart_k.overlap(chart_so)
        chart_k = chart_k.overlap(chart_se)

    # 均线图
    # ------------------------------------------------------------------------------------------------------------------
    chart_ma = Line()
    chart_ma.add_xaxis(xaxis_data=dts)
    if not t_seq:
        t_seq = [5, 13, 21]

    ma_keys = {}
    for t in t_seq:
        ma_keys[f"MA{t}"] = SMA(close, timeperiod=t)

    for _, (name, ma) in enumerate(ma_keys.items()):
        chart_ma.add_yaxis(
            series_name=name,
            y_axis=ma,
            is_smooth=True,
            symbol_size=0,
            label_opts=label_not_show_opts,
            linestyle_opts=opts.LineStyleOpts(opacity=0.8, width=1),
        )

    chart_ma.set_global_opts(xaxis_opts=grid0_xaxis_opts, legend_opts=legend_not_show_opts)
    chart_k = chart_k.overlap(chart_ma)

    # 缠论结果
    # ------------------------------------------------------------------------------------------------------------------
    if fx:
        fx_dts = [x["dt"] for x in fx]
        fx_val = [round(x["fx"], 2) for x in fx]
        chart_fx = Line()
        chart_fx.add_xaxis(fx_dts)
        chart_fx.add_yaxis(
            series_name="FX",
            y_axis=fx_val,
            symbol="circle",
            symbol_size=6,
            label_opts=label_show_opts,
            itemstyle_opts=opts.ItemStyleOpts(
                color="rgba(152, 147, 193, 1.0)",
            ),
        )

        chart_fx.set_global_opts(xaxis_opts=grid0_xaxis_opts, legend_opts=legend_not_show_opts)
        chart_k = chart_k.overlap(chart_fx)

    if bi:
        bi_dts = [x["dt"] for x in bi]
        bi_val = [round(x["bi"], 2) for x in bi]
        chart_bi = Line()
        chart_bi.add_xaxis(bi_dts)
        chart_bi.add_yaxis(
            series_name="BI",
            y_axis=bi_val,
            symbol="diamond",
            symbol_size=10,
            label_opts=label_show_opts,
            itemstyle_opts=opts.ItemStyleOpts(
                color="rgba(184, 117, 225, 1.0)",
            ),
            linestyle_opts=opts.LineStyleOpts(width=1.5),
        )

        chart_bi.set_global_opts(xaxis_opts=grid0_xaxis_opts, legend_opts=legend_not_show_opts)
        chart_k = chart_k.overlap(chart_bi)

    if xd:
        xd_dts = [x["dt"] for x in xd]
        xd_val = [x["xd"] for x in xd]
        chart_xd = Line()
        chart_xd.add_xaxis(xd_dts)
        chart_xd.add_yaxis(
            series_name="XD",
            y_axis=xd_val,
            symbol="triangle",
            symbol_size=10,
            itemstyle_opts=opts.ItemStyleOpts(
                color="rgba(37, 141, 54, 1.0)",
            ),
        )

        chart_xd.set_global_opts(xaxis_opts=grid0_xaxis_opts, legend_opts=legend_not_show_opts)
        chart_k = chart_k.overlap(chart_xd)

    # 成交量图
    # ------------------------------------------------------------------------------------------------------------------
    chart_vol = Bar()
    chart_vol.add_xaxis(dts)
    chart_vol.add_yaxis(series_name="Volume", y_axis=vol, bar_width="60%")
    chart_vol.set_global_opts(
        xaxis_opts=opts.AxisOpts(
            type_="category",
            grid_index=1,
            boundary_gap=False,
            axislabel_opts=opts.LabelOpts(is_show=True, font_size=8, color="#9b9da9"),
        ),
        yaxis_opts=yaxis_opts,
        legend_opts=legend_not_show_opts,
    )

    # MACD图
    # ------------------------------------------------------------------------------------------------------------------
    chart_macd = Bar()
    chart_macd.add_xaxis(dts)
    chart_macd.add_yaxis(series_name="MACD", y_axis=macd_bar, bar_width="60%")
    chart_macd.set_global_opts(
        xaxis_opts=opts.AxisOpts(
            type_="category",
            grid_index=2,
            axislabel_opts=opts.LabelOpts(is_show=False),
            splitline_opts=opts.SplitLineOpts(is_show=False),
        ),
        yaxis_opts=opts.AxisOpts(
            grid_index=2,
            split_number=4,
            axisline_opts=opts.AxisLineOpts(is_on_zero=False),
            axistick_opts=opts.AxisTickOpts(is_show=False),
            splitline_opts=opts.SplitLineOpts(is_show=False),
            axislabel_opts=opts.LabelOpts(is_show=True, color="#c7c7c7"),
        ),
        legend_opts=opts.LegendOpts(is_show=False),
    )

    line = Line()
    line.add_xaxis(dts)
    line.add_yaxis(
        series_name="DIFF",
        y_axis=diff.tolist(),
        label_opts=label_not_show_opts,
        is_symbol_show=False,
        linestyle_opts=opts.LineStyleOpts(opacity=0.8, width=1.0, color="#da6ee8"),
    )
    line.add_yaxis(
        series_name="DEA",
        y_axis=dea.tolist(),
        label_opts=label_not_show_opts,
        is_symbol_show=False,
        linestyle_opts=opts.LineStyleOpts(opacity=0.8, width=1.0, color="#39afe6"),
    )

    chart_macd = chart_macd.overlap(line)

    grid0_opts = opts.GridOpts(pos_left="0%", pos_right="1%", pos_top="12%", height="58%")
    grid1_opts = opts.GridOpts(pos_left="0%", pos_right="1%", pos_top="74%", height="8%")
    grid2_opts = opts.GridOpts(pos_left="0%", pos_right="1%", pos_top="86%", height="10%")

    grid_chart = Grid(init_opts)
    grid_chart.add(chart_k, grid_opts=grid0_opts)
    grid_chart.add(chart_vol, grid_opts=grid1_opts)
    grid_chart.add(chart_macd, grid_opts=grid2_opts)
    return grid_chart


def _safe_get(row: Any, key: str, default: Any = None) -> Any:
    if isinstance(row, Mapping):
        return row.get(key, default)
    return getattr(row, key, default)


def _parse_dt(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.replace(tzinfo=None)
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
        except Exception:
            pass
        for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%Y/%m/%d %H:%M:%S", "%Y/%m/%d"]:
            try:
                return datetime.strptime(value, fmt)
            except Exception:
                continue
        return None
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(value)
        except Exception:
            return None
    return None


def _dt_display(dt: Any) -> str:
    parsed = _parse_dt(dt)
    if parsed is None:
        return str(dt)
    return parsed.strftime("%Y-%m-%d %H:%M:%S")


def _to_float(value: Any, default: float = 0.0) -> float:
    if value is None:
        return default
    try:
        return float(value)
    except Exception:
        return default


def _resolve_axis_index(
    dt_index: list[datetime],
    dt_label_index: list[str],
    *,
    explicit_index: int | None,
    dt_value: Any = None,
) -> int | None:
    if dt_index:
        if explicit_index is not None:
            try:
                idx = int(explicit_index)
                if idx < 0:
                    return None
                if idx >= len(dt_index):
                    return len(dt_index) - 1
                return idx
            except Exception:
                pass

    if dt_value is None:
        return None

    parsed = _parse_dt(dt_value)
    if parsed is None or not dt_index:
        return None

    # 精确匹配
    for i, item in enumerate(dt_index):
        if item == parsed:
            return i

    # 最近点匹配
    if len(dt_index) == 1:
        return 0
    diffs = [abs((x - parsed).total_seconds()) for x in dt_index]
    min_idx = int(diffs.index(min(diffs)))
    if 0 <= min_idx < len(dt_label_index):
        return min_idx
    return None


def _coerce_kline(payload: Mapping[str, Any]) -> tuple[list[datetime], list[str], list[dict[str, float]]]:
    raw_rows = payload.get("kline", [])
    parsed_rows = []
    for row in raw_rows:
        dt_value = _safe_get(row, "dt")
        dt_obj = _parse_dt(dt_value)
        if dt_obj is None:
            continue
        parsed_rows.append(
            {
                "dt": dt_obj,
                "dt_display": _dt_display(dt_obj),
                "open": _to_float(_safe_get(row, "open")),
                "close": _to_float(_safe_get(row, "close")),
                "high": _to_float(_safe_get(row, "high")),
                "low": _to_float(_safe_get(row, "low")),
                "vol": _to_float(_safe_get(row, "vol", 0.0)),
            }
        )

    if not parsed_rows:
        return [], [], []
    parsed_rows = sorted(parsed_rows, key=lambda x: x["dt"])
    dt_index = [x["dt"] for x in parsed_rows]
    dt_labels = [x["dt_display"] for x in parsed_rows]
    base_kline = [{"open": x["open"], "close": x["close"], "low": x["low"], "high": x["high"], "vol": x["vol"]} for x in parsed_rows]
    return dt_index, dt_labels, base_kline


def _level_palette(idx: int) -> dict[str, Any]:
    palette = [
        {
            "bi_color": "#BA75E1",
            "xd_color": "#26A65B",
            "zone_color": "rgba(186,117,225,0.14)",
            "zone_border": "rgba(186,117,225,0.45)",
            "div_color": "#F44336",
            "bi_width": 2.0,
            "xd_width": 2.8,
            "div_width": 3.5,
        },
        {
            "bi_color": "#4A90E2",
            "xd_color": "#F0A500",
            "zone_color": "rgba(255,165,0,0.14)",
            "zone_border": "rgba(255,165,0,0.55)",
            "div_color": "#FF5722",
            "bi_width": 2.4,
            "xd_width": 3.0,
            "div_width": 3.8,
        },
        {
            "bi_color": "#777777",
            "xd_color": "#9B59B6",
            "zone_color": "rgba(128,128,128,0.12)",
            "zone_border": "rgba(128,128,128,0.5)",
            "div_color": "#9C27B0",
            "bi_width": 3.0,
            "xd_width": 3.2,
            "div_width": 4.0,
        },
    ]
    return palette[min(idx, len(palette) - 1)]


def _ensure_series_name(name: Any) -> str:
    return str(name) if name is not None else "series"


def kline_recursive(
    payload: Mapping[str, Any],
    title: str = "CZSC递归多级别分析",
    width: str = "1400px",
    height: str = "760px",
    *,
    show_levels: list[str] | None = None,
    max_levels: int | None = None,
    show_bi: bool = True,
    show_xd: bool = True,
    show_zones: bool = True,
    show_trend_types: bool = True,
    show_signals: bool = True,
    show_resonance: bool = True,
    show_divergence: bool = True,
    show_series_legend: bool = True,
) -> Grid:
    """基于递归 payload 的多级别叠加绘制

    :param payload: build_recursive_chart_payload 输出的统一 payload
    :param title: 图表标题
    :param width: 主图宽度
    :param height: 主图高度
    :param show_levels: 需要展示的级别 id，不传即按 payload 顺序展示
    :param max_levels: 最大展示级别数量
    :param show_bi: 是否绘制笔
    :param show_xd: 是否绘制线段
    :param show_zones: 是否绘制中枢
    :param show_trend_types: 是否绘制走势类型标签
    :param show_signals: 是否绘制基础买卖点
    :param show_resonance: 是否绘制共振信号
    :param show_divergence: 是否强化背驰笔/线段
    :param show_series_legend: 是否展示图例
    :return: Grid
    """
    if not isinstance(payload, Mapping):
        raise TypeError("payload must be a mapping from recursive chart payload")

    dt_index, xaxis_labels, rows = _coerce_kline(payload)
    init_opts = opts.InitOpts(
        bg_color="#1f212d", width=width, height=height, animation_opts=opts.AnimationOpts(False)
    )
    title_opts = opts.TitleOpts(
        title=title,
        pos_top="1%",
        title_textstyle_opts=opts.TextStyleOpts(color="#F9293E", font_size=20),
    )

    label_show_opts = opts.LabelOpts(is_show=True)
    label_not_show_opts = opts.LabelOpts(is_show=False)
    legend_not_show_opts = opts.LegendOpts(is_show=False)
    red_item_style = opts.ItemStyleOpts(color="#F9293E")
    green_item_style = opts.ItemStyleOpts(color="#00aa3b")
    k_style_opts = opts.ItemStyleOpts(
        color="#F9293E", color0="#00aa3b", border_color="#F9293E", border_color0="#00aa3b", opacity=0.9
    )

    legend_opts = opts.LegendOpts(
        is_show=show_series_legend,
        pos_top="1%",
        pos_left="30%",
        item_width=14,
        item_height=8,
        textstyle_opts=opts.TextStyleOpts(font_size=12, color="#0e99e2"),
    )
    brush_opts = opts.BrushOpts(
        tool_box=["rect", "polygon", "keep", "clear"],
        x_axis_index="all",
        brush_link="all",
        out_of_brush={"colorAlpha": 0.1},
        brush_type="lineX",
    )
    axis_pointer_opts = opts.AxisPointerOpts(is_show=True, link=[{"xAxisIndex": "all"}])

    dz_inside = opts.DataZoomOpts(False, "inside", xaxis_index=[0, 1, 2], range_start=80, range_end=100)
    dz_slider = opts.DataZoomOpts(
        True, "slider", xaxis_index=[0, 1, 2], pos_top="96%", pos_bottom="0%", range_start=80, range_end=100
    )

    yaxis_opts = opts.AxisOpts(
        is_scale=True,
        min_="dataMin",
        max_="dataMax",
        splitline_opts=opts.SplitLineOpts(is_show=False),
        axislabel_opts=opts.LabelOpts(color="#c7c7c7", font_size=8, position="inside"),
    )
    grid0_xaxis_opts = opts.AxisOpts(
        type_="category",
        grid_index=0,
        axislabel_opts=label_not_show_opts,
        split_number=20,
        min_="dataMin",
        max_="dataMax",
        is_scale=True,
        boundary_gap=False,
        splitline_opts=opts.SplitLineOpts(is_show=False),
        axisline_opts=opts.AxisLineOpts(is_on_zero=False),
    )

    tool_tip_opts = opts.TooltipOpts(
        trigger="axis",
        axis_pointer_type="cross",
        background_color="rgba(245, 245, 245, 0.8)",
        border_width=1,
        border_color="#ccc",
        position=JsCode(
            """
                    function (pos, params, el, elRect, size) {
                        var obj = {top: 10};
                        obj[['left', 'right'][+(pos[0] < size.viewSize[0] / 2)]] = 30;
                        return obj;
                    }
                    """
        ),
        textstyle_opts=opts.TextStyleOpts(color="#000"),
    )

    # 基础K线
    if not xaxis_labels:
        xaxis_labels = []
        rows = []
        close = np.array([], dtype=np.double)
    else:
        close = np.array([x["close"] for x in rows], dtype=np.double)

    k_data = [opts.CandleStickItem(name=i, value=[x["open"], x["close"], x["low"], x["high"]]) for i, x in enumerate(rows)]
    vol = [opts.BarItem(name=i, value=_to_float(x["vol"]), itemstyle_opts=red_item_style, label_opts=label_not_show_opts) for i, x in enumerate(rows)]

    chart_k = Kline().add_xaxis(xaxis_data=xaxis_labels).add_yaxis(series_name="K线", y_axis=k_data, itemstyle_opts=k_style_opts)
    diff, dea, macd = MACD(close) if len(close) else ([], [], [])
    macd_bar = [
        opts.BarItem(name=i, value=round(v, 4), itemstyle_opts=red_item_style if v > 0 else green_item_style, label_opts=label_not_show_opts)
        for i, v in enumerate(macd.tolist() if hasattr(macd, "tolist") else macd)
    ]
    diff = diff.round(4) if hasattr(diff, "round") else []
    dea = dea.round(4) if hasattr(dea, "round") else []
    close_for_ma = [x["close"] for x in rows] if rows else []

    chart_k.set_global_opts(
        legend_opts=legend_opts,
        datazoom_opts=[dz_inside, dz_slider],
        yaxis_opts=yaxis_opts,
        tooltip_opts=tool_tip_opts,
        axispointer_opts=axis_pointer_opts,
        brush_opts=brush_opts,
        title_opts=title_opts,
        xaxis_opts=grid0_xaxis_opts,
    )

    # MA
    if close_for_ma:
        chart_ma = Line()
        chart_ma.add_xaxis(xaxis_data=xaxis_labels)
        for t in [5, 13, 21]:
            ma = SMA(close, timeperiod=t)
            chart_ma.add_yaxis(
                series_name=f"MA{t}",
                y_axis=ma,
                is_smooth=True,
                symbol_size=0,
                label_opts=label_not_show_opts,
                linestyle_opts=opts.LineStyleOpts(opacity=0.8, width=1),
            )
        chart_ma.set_global_opts(xaxis_opts=grid0_xaxis_opts, legend_opts=legend_not_show_opts)
        chart_k = chart_k.overlap(chart_ma)

    levels = payload.get("levels", [])
    if max_levels is not None:
        levels = levels[:max_levels]
    if show_levels is not None:
        levels = [x for x in levels if x.get("id") in show_levels]

    # 递归线（笔/线段/中枢）
    for level_idx, level in enumerate(levels):
        level_id = _ensure_series_name(_safe_get(level, "id", f"L{level_idx}"))
        level_label = _ensure_series_name(_safe_get(level, "label", level_id))
        style = _level_palette(level_idx)

        if show_bi:
            bi_x: list[str] = []
            bi_y: list[float] = []
            for bi in _safe_get(level, "bi", []) or []:
                sidx = _resolve_axis_index(
                    dt_index=dt_index,
                    dt_label_index=xaxis_labels,
                    explicit_index=_safe_get(bi, "base_sidx"),
                    dt_value=_safe_get(bi, "sdt"),
                )
                eidx = _resolve_axis_index(
                    dt_index=dt_index,
                    dt_label_index=xaxis_labels,
                    explicit_index=_safe_get(bi, "base_eidx"),
                    dt_value=_safe_get(bi, "edt"),
                )
                if sidx is None or eidx is None:
                    continue
                start = _to_float(_safe_get(bi, "start_price"))
                end = _to_float(_safe_get(bi, "end_price"))
                bi_x.extend([xaxis_labels[sidx], xaxis_labels[eidx]])
                bi_y.extend([start, end])

            if bi_x:
                chart_bi = Line()
                chart_bi.add_xaxis(xaxis_data=bi_x)
                chart_bi.add_yaxis(
                    series_name=f"{level_label}-L0笔".replace("L0", level_id),
                    y_axis=bi_y,
                    is_smooth=False,
                    is_connect_nones=True,
                    symbol="none",
                    label_opts=label_not_show_opts,
                    itemstyle_opts=opts.ItemStyleOpts(color=style["bi_color"]),
                    linestyle_opts=opts.LineStyleOpts(width=style["bi_width"], color=style["bi_color"]),
                )
                chart_k = chart_k.overlap(chart_bi)

        if show_xd:
            for seg in _safe_get(level, "segments", []) or []:
                sidx = _resolve_axis_index(
                    dt_index=dt_index,
                    dt_label_index=xaxis_labels,
                    explicit_index=_safe_get(seg, "base_sidx"),
                    dt_value=_safe_get(seg, "sdt"),
                )
                eidx = _resolve_axis_index(
                    dt_index=dt_index,
                    dt_label_index=xaxis_labels,
                    explicit_index=_safe_get(seg, "base_eidx"),
                    dt_value=_safe_get(seg, "edt"),
                )
                if sidx is None or eidx is None:
                    continue
                start = _to_float(_safe_get(seg, "start_price"))
                end = _to_float(_safe_get(seg, "end_price"))
                line = Line()
                line.add_xaxis(xaxis_data=[xaxis_labels[sidx], xaxis_labels[eidx]])
                line.add_yaxis(
                    series_name=f"{level_label}-线段",
                    y_axis=[start, end],
                    is_smooth=False,
                    symbol="none",
                    label_opts=label_not_show_opts,
                    itemstyle_opts=opts.ItemStyleOpts(color=style["xd_color"]),
                    linestyle_opts=opts.LineStyleOpts(
                        width=style["xd_width"], color=style["xd_color"], type_="solid"
                    ),
                )
                chart_k = chart_k.overlap(line)

                if show_divergence and _safe_get(seg, "is_divergence_leg"):
                    div = Line()
                    div.add_xaxis(xaxis_data=[xaxis_labels[sidx], xaxis_labels[eidx]])
                    div.add_yaxis(
                        series_name=f"{level_label}-背驰线段",
                        y_axis=[start, end],
                        is_smooth=False,
                        symbol="none",
                        label_opts=label_not_show_opts,
                        itemstyle_opts=opts.ItemStyleOpts(color=style["div_color"]),
                        linestyle_opts=opts.LineStyleOpts(
                            width=style["div_width"],
                            color=style["div_color"],
                            type_="dashed",
                        ),
                    )
                    chart_k = chart_k.overlap(div)

        if show_zones:
            for zone in _safe_get(level, "zones", []) or []:
                sidx = _resolve_axis_index(
                    dt_index=dt_index,
                    dt_label_index=xaxis_labels,
                    explicit_index=_safe_get(zone, "base_sidx"),
                    dt_value=_safe_get(zone, "sdt"),
                )
                eidx = _resolve_axis_index(
                    dt_index=dt_index,
                    dt_label_index=xaxis_labels,
                    explicit_index=_safe_get(zone, "base_eidx"),
                    dt_value=_safe_get(zone, "edt"),
                )
                if sidx is None or eidx is None:
                    continue
                zg = _to_float(_safe_get(zone, "zg"))
                zd = _to_float(_safe_get(zone, "zd"))
                zi = _safe_get(zone, "index")
                zone_idx = f"{level_label}-中枢{zi if zi is not None else ''}"
                zone_top = Line()
                zone_top.add_xaxis(xaxis_data=[xaxis_labels[sidx], xaxis_labels[eidx]])
                zone_top.add_yaxis(
                    series_name=zone_idx + "-上沿",
                    y_axis=[zg, zg],
                    is_smooth=False,
                    symbol="none",
                    label_opts=label_not_show_opts,
                    itemstyle_opts=opts.ItemStyleOpts(color=style["zone_border"]),
                    linestyle_opts=opts.LineStyleOpts(color=style["zone_border"], width=1.2, type_="dashed"),
                )
                zone_bottom = Line()
                zone_bottom.add_xaxis(xaxis_data=[xaxis_labels[sidx], xaxis_labels[eidx]])
                zone_bottom.add_yaxis(
                    series_name=zone_idx + "-下沿",
                    y_axis=[zd, zd],
                    is_smooth=False,
                    symbol="none",
                    label_opts=label_not_show_opts,
                    itemstyle_opts=opts.ItemStyleOpts(color=style["zone_border"]),
                    linestyle_opts=opts.LineStyleOpts(color=style["zone_border"], width=1.2, type_="dashed"),
                )
                chart_k = chart_k.overlap(zone_top)
                chart_k = chart_k.overlap(zone_bottom)

        if show_trend_types:
            for trend_type in _safe_get(level, "trend_types", []) or []:
                sidx = _resolve_axis_index(
                    dt_index=dt_index,
                    dt_label_index=xaxis_labels,
                    explicit_index=_safe_get(trend_type, "base_sidx"),
                    dt_value=_safe_get(trend_type, "sdt"),
                )
                eidx = _resolve_axis_index(
                    dt_index=dt_index,
                    dt_label_index=xaxis_labels,
                    explicit_index=_safe_get(trend_type, "base_eidx"),
                    dt_value=_safe_get(trend_type, "edt"),
                )
                if sidx is None or eidx is None or sidx >= len(rows) or eidx >= len(rows):
                    continue

                ttype = _ensure_series_name(_safe_get(trend_type, "type", "trend"))
                if not ttype:
                    continue

                trend_color = "#0ec5ff" if ttype.startswith("上") else "#ff8f00"
                line = Line()
                line.add_xaxis(xaxis_data=[xaxis_labels[sidx], xaxis_labels[eidx]])
                line.add_yaxis(
                    series_name=f"{level_label}-走势-{ttype}",
                    y_axis=[_to_float(rows[sidx]["close"]), _to_float(rows[eidx]["close"])],
                    is_smooth=False,
                    symbol="diamond",
                    symbol_size=6,
                    label_opts=label_not_show_opts,
                    itemstyle_opts=opts.ItemStyleOpts(color=trend_color),
                    linestyle_opts=opts.LineStyleOpts(
                        width=1.0,
                        type_="dashed",
                        color=trend_color,
                    ),
                )
                chart_k = chart_k.overlap(line)

        if show_signals:
            signals = _safe_get(level, "trade_signals", []) or []
            signal_points: dict[str, tuple[list[str], list[list[Any]]]] = {}
            for signal in signals:
                sidx = _resolve_axis_index(
                    dt_index=dt_index,
                    dt_label_index=xaxis_labels,
                    explicit_index=_safe_get(signal, "base_idx"),
                    dt_value=_safe_get(signal, "dt"),
                )
                if sidx is None or sidx >= len(xaxis_labels):
                    continue
                s_type = _ensure_series_name(_safe_get(signal, "signal_type", "Signal"))
                side = _ensure_series_name(_safe_get(signal, "side", ""))
                name = f"{level_label}-{s_type}"
                point = [xaxis_labels[sidx], _to_float(_safe_get(signal, "price")), f"{side}-{s_type} @ {level_id}"]
                signal_points.setdefault(name, ([], []))
                signal_points[name][0].append(point[0])
                signal_points[name][1].append([point[1], point[2]])

            for signal_name, (sx, sy) in signal_points.items():
                if not sx:
                    continue
                s = Scatter()
                s.add_xaxis(xaxis_data=sx)
                s.add_yaxis(
                    series_name=signal_name,
                    y_axis=sy,
                    symbol_size=12,
                    symbol="circle",
                    label_opts=label_not_show_opts,
                    tooltip_opts=opts.TooltipOpts(
                        textstyle_opts=opts.TextStyleOpts(font_size=12),
                        formatter=JsCode("function (params) {return params.value[2];}"),
                    ),
                )
                chart_k = chart_k.overlap(s)

    # 共振信号
    if show_resonance:
        role_cfg = {
            "gold_blink": {"name": "共振-金色闪烁", "color": "#FFC107"},
            "magenta_blink": {"name": "共振-品红闪烁", "color": "#E91E63"},
            "red_pulse": {"name": "共振-红色脉冲", "color": "#F44336"},
        }
        resonance_groups: dict[str, tuple[list[str], list[list[Any]]]] = {}
        for sig in _safe_get(payload, "resonance_signals", []) or []:
            role = _ensure_series_name(_safe_get(sig, "visual_role", "gold_blink"))
            cfg = role_cfg.get(role, role_cfg["gold_blink"])
            ridx = _resolve_axis_index(
                dt_index=dt_index,
                dt_label_index=xaxis_labels,
                explicit_index=_safe_get(sig, "base_idx"),
                dt_value=_safe_get(sig, "dt"),
            )
            if ridx is None or ridx >= len(xaxis_labels):
                continue
            sname = f"{cfg['name']}-{_ensure_series_name(_safe_get(sig,'name'))}"
            info = (
                f"{_ensure_series_name(_safe_get(sig, 'name'))}"
                + f" 价格={_to_float(_safe_get(sig, 'price')):.4f}"
                + (
                    f" 级别={_ensure_series_name(_safe_get(sig, 'higher_level_id'))}->{_ensure_series_name(_safe_get(sig, 'lower_level_id'))}"
                    if _safe_get(sig, "higher_level_id")
                    else ""
                )
            )
            resonance_groups.setdefault(sname, ([], []))
            resonance_groups[sname][0].append(xaxis_labels[ridx])
            resonance_groups[sname][1].append([_to_float(_safe_get(sig, "price")), info])

        for sname, (rx, ry) in resonance_groups.items():
            if not rx:
                continue
            e = EffectScatter()
            color = role_cfg.get("gold_blink", {"color": "#FFC107"})["color"]
            if sname.startswith(role_cfg["gold_blink"]["name"]):
                color = role_cfg["gold_blink"]["color"]
            elif sname.startswith(role_cfg["magenta_blink"]["name"]):
                color = role_cfg["magenta_blink"]["color"]
            elif sname.startswith(role_cfg["red_pulse"]["name"]):
                color = role_cfg["red_pulse"]["color"]
            e.add_xaxis(xaxis_data=rx)
            e.add_yaxis(
                series_name=sname,
                y_axis=ry,
                effect_opts=opts.EffectOpts(scale=7, period=5, color=color, brush_type="fill"),
                symbol="pin",
                symbol_size=16,
                color=color,
                tooltip_opts=opts.TooltipOpts(
                    textstyle_opts=opts.TextStyleOpts(font_size=12),
                    formatter=JsCode("function (params) {return params.value[2];}"),
                ),
            )
            chart_k = chart_k.overlap(e)

    # 成交量图
    chart_vol = Bar()
    chart_vol.add_xaxis(xaxis_labels)
    chart_vol.add_yaxis(series_name="Volume", y_axis=vol, bar_width="60%")
    chart_vol.set_global_opts(
        xaxis_opts=opts.AxisOpts(
            type_="category",
            grid_index=1,
            boundary_gap=False,
            axislabel_opts=opts.LabelOpts(is_show=True, font_size=8, color="#9b9da9"),
        ),
        yaxis_opts=yaxis_opts,
        legend_opts=legend_not_show_opts,
    )

    # MACD图
    chart_macd = Bar()
    chart_macd.add_xaxis(xaxis_labels)
    chart_macd.add_yaxis(series_name="MACD", y_axis=macd_bar, bar_width="60%")
    chart_macd.set_global_opts(
        xaxis_opts=opts.AxisOpts(
            type_="category",
            grid_index=2,
            axislabel_opts=opts.LabelOpts(is_show=False),
            splitline_opts=opts.SplitLineOpts(is_show=False),
        ),
        yaxis_opts=opts.AxisOpts(
            grid_index=2,
            split_number=4,
            axisline_opts=opts.AxisLineOpts(is_on_zero=False),
            axistick_opts=opts.AxisTickOpts(is_show=False),
            splitline_opts=opts.SplitLineOpts(is_show=False),
            axislabel_opts=opts.LabelOpts(is_show=True, color="#c7c7c7"),
        ),
        legend_opts=opts.LegendOpts(is_show=False),
    )
    line = Line()
    line.add_xaxis(xaxis_labels)
    if hasattr(diff, "__iter__") and len(list(diff)) > 0 if hasattr(diff, "__iter__") else False:
        line.add_yaxis(
            series_name="DIFF",
            y_axis=np.asarray(diff).tolist(),
            label_opts=label_not_show_opts,
            is_symbol_show=False,
            linestyle_opts=opts.LineStyleOpts(opacity=0.8, width=1.0, color="#da6ee8"),
        )
        line.add_yaxis(
            series_name="DEA",
            y_axis=np.asarray(dea).tolist(),
            label_opts=label_not_show_opts,
            is_symbol_show=False,
            linestyle_opts=opts.LineStyleOpts(opacity=0.8, width=1.0, color="#39afe6"),
        )
    chart_macd = chart_macd.overlap(line)

    grid0_opts = opts.GridOpts(pos_left="0%", pos_right="1%", pos_top="12%", height="58%")
    grid1_opts = opts.GridOpts(pos_left="0%", pos_right="1%", pos_top="74%", height="8%")
    grid2_opts = opts.GridOpts(pos_left="0%", pos_right="1%", pos_top="86%", height="10%")

    grid_chart = Grid(init_opts)
    grid_chart.add(chart_k, grid_opts=grid0_opts)
    grid_chart.add(chart_vol, grid_opts=grid1_opts)
    grid_chart.add(chart_macd, grid_opts=grid2_opts)
    return grid_chart


def _prepare_kline_data(kline: list[dict], use_streamlit=False, width=1400, height=580) -> tuple:
    """准备K线数据

    :param kline: K线数据
    :return: (df_data, chart)
    """
    import pandas as pd
    from loguru import logger

    # 准备K线数据
    df_data = []
    for item in kline:
        # 处理时间格式
        time_str = item["dt"].strftime("%Y-%m-%d") if hasattr(item["dt"], "strftime") else str(item["dt"])

        df_data.append(
            {
                "time": time_str,
                "open": float(item["open"]),
                "high": float(item["high"]),
                "low": float(item["low"]),
                "close": float(item["close"]),
                "volume": float(item.get("vol", item.get("volume", 0))),
            }
        )

    # 创建主图表（延迟导入，避免在模块加载时引入 streamlit 等重型依赖）
    if use_streamlit:
        from lightweight_charts.widgets import StreamlitChart

        logger.info("使用 StreamlitChart")
        chart = StreamlitChart(width=width, height=height)
    else:
        from lightweight_charts import Chart

        logger.info("使用 Chart")
        chart = Chart()

    df = pd.DataFrame(df_data)
    chart.set(df)

    logger.info(f"成功创建基础K线图表，包含{len(df_data)}根K线")
    return df_data, chart


def _add_moving_averages(chart: "Chart", kline: list[dict], df_data: list[dict], t_seq: list[int]) -> None:
    """添加移动平均线

    :param chart: 图表对象
    :param kline: K线数据
    :param df_data: 格式化后的数据
    :param t_seq: 均线周期序列
    """
    import pandas as pd
    from loguru import logger

    if not t_seq:
        return

    try:
        close_prices = np.array([x["close"] for x in kline], dtype=np.double)
        # 均线颜色：橙色、蓝色、绿色、紫色、青色
        ma_colors = ["#FF9800", "#2196F3", "#4CAF50", "#9C27B0", "#00BCD4"]

        for i, period in enumerate(t_seq[:5]):  # 最多显示5条均线
            try:
                ma_values = SMA(close_prices, timeperiod=period)
                ma_data = []

                for j, item in enumerate(df_data):
                    if j >= period - 1 and j < len(ma_values) and not np.isnan(ma_values[j]):
                        ma_data.append({"time": item["time"], f"MA{period}": float(ma_values[j])})

                if ma_data:
                    ma_df = pd.DataFrame(ma_data).set_index("time")
                    color = ma_colors[i] if i < len(ma_colors) else "#999999"
                    ma_line = chart.create_line(f"MA{period}", color=color)
                    ma_line.set(ma_df)
                    logger.info(f"成功添加MA{period}均线（{color}），数据点数：{len(ma_data)}")
            except Exception as e:
                logger.warning(f"添加MA{period}均线失败: {e}")
                continue
    except Exception as e:
        logger.warning(f"添加移动平均线失败: {e}")


def _add_fractal_marks(chart: "Chart", fx: list[dict]) -> None:
    """添加分型标记

    :param chart: 图表对象
    :param fx: 分型数据
    """
    import pandas as pd
    from loguru import logger

    if not fx:
        return

    try:
        fx_data = []
        for item in fx:
            time_str = item["dt"].strftime("%Y-%m-%d") if hasattr(item["dt"], "strftime") else str(item["dt"])

            fx_data.append({"time": time_str, "分型": float(item["fx"])})

        if fx_data:
            fx_df = pd.DataFrame(fx_data).set_index("time")
            fx_line = chart.create_line("分型", color="#FF5722")  # 深橙红色
            fx_line.set(fx_df)
            logger.info(f"成功添加{len(fx_data)}个分型点（深橙红色）")
    except Exception as e:
        logger.warning(f"添加分型标记失败: {e}")


def _add_bi_lines(chart: "Chart", bi: list[dict]) -> None:
    """添加笔线

    :param chart: 图表对象
    :param bi: 笔数据
    """
    import pandas as pd
    from loguru import logger

    if not bi:
        return

    try:
        bi_data = []
        for item in bi:
            time_str = item["dt"].strftime("%Y-%m-%d") if hasattr(item["dt"], "strftime") else str(item["dt"])

            bi_data.append({"time": time_str, "笔": float(item["bi"])})

        if bi_data:
            bi_df = pd.DataFrame(bi_data).set_index("time")
            bi_line = chart.create_line("笔", color="#FFC107")  # 琥珀黄色
            bi_line.set(bi_df)
            logger.info(f"成功添加{len(bi_data)}笔（琥珀黄色）")
    except Exception as e:
        logger.warning(f"添加笔线失败: {e}")


def _add_xd_lines(chart: "Chart", xd: list[dict]) -> None:
    """添加线段

    :param chart: 图表对象
    :param xd: 线段数据
    """
    import pandas as pd
    from loguru import logger

    if not xd:
        return

    try:
        xd_data = []
        for item in xd:
            time_str = item["dt"].strftime("%Y-%m-%d") if hasattr(item["dt"], "strftime") else str(item["dt"])

            xd_data.append({"time": time_str, "线段": float(item["xd"])})

        if xd_data:
            xd_df = pd.DataFrame(xd_data).set_index("time")
            xd_line = chart.create_line("线段", color="#E91E63")  # 粉红色
            xd_line.set(xd_df)
            logger.info(f"成功添加{len(xd_data)}条线段（粉红色）")
    except Exception as e:
        logger.warning(f"添加线段失败: {e}")


def _add_macd_indicator(chart: "Chart", kline: list[dict], df_data: list[dict]) -> None:
    """添加MACD指标到子图表

    :param chart: 图表对象
    :param kline: K线数据
    :param df_data: 格式化后的数据
    """
    import pandas as pd
    from loguru import logger

    try:
        close_prices = np.array([x["close"] for x in kline], dtype=np.double)
        diff, dea, macd = MACD(close_prices)

        # 尝试创建子图表用于MACD显示
        try:
            # 重新设置主图高度，为子图腾出空间
            chart.resize(1, 0.7)  # 主图占70%高度

            # 隐藏主图的时间轴，避免重复显示
            chart.time_scale(visible=False)

            # 创建MACD子图表，占30%高度并同步时间轴
            macd_chart = chart.create_subchart(width=1, height=0.3, sync=True)

            # 确保子图显示时间轴，并设置时间轴格式保持一致
            macd_chart.time_scale(visible=True, time_visible=True, seconds_visible=False)

            logger.info("成功创建MACD子图表并设置时间轴同步")
        except Exception as subchart_e:
            # 如果不支持子图表，直接返回
            logger.warning(f"子图表创建失败，跳过MACD指标: {subchart_e}")
            return

        # 确保所有数组长度一致
        data_length = min(len(df_data), len(diff), len(dea), len(macd))

        # 重要：对NaN值填充为0，确保数据长度一致，保证时间轴对齐
        diff_line_data = []
        dea_line_data = []
        histogram_data = []

        for j in range(data_length):
            time_value = df_data[j]["time"]

            # 对NaN值填充为0，而不是跳过，确保数据长度一致
            diff_val = 0.0 if np.isnan(diff[j]) else float(diff[j])
            dea_val = 0.0 if np.isnan(dea[j]) else float(dea[j])
            macd_val = 0.0 if np.isnan(macd[j]) else float(macd[j])

            diff_line_data.append({"time": time_value, "value": diff_val})

            dea_line_data.append({"time": time_value, "value": dea_val})

            histogram_data.append(
                {"time": time_value, "value": macd_val, "color": "#26a69a" if macd_val >= 0 else "#ef5350"}
            )

        logger.info(
            f"MACD数据准备完成：总数据长度{data_length}，DIFF({len(diff_line_data)})，DEA({len(dea_line_data)})，柱状图({len(histogram_data)})"
        )

        # 添加DIFF线（MACD快线）
        if diff_line_data:
            diff_df = pd.DataFrame(diff_line_data)
            diff_line = macd_chart.create_line(color="#1976D2", width=2)  # 深蓝色
            diff_line.set(diff_df)
            logger.info(f"成功添加DIFF线（深蓝色），数据点数：{len(diff_line_data)}")

        # 添加DEA线（MACD慢线/信号线）
        if dea_line_data:
            dea_df = pd.DataFrame(dea_line_data)
            dea_line = macd_chart.create_line(color="#FF5722", width=2)  # 橙红色
            dea_line.set(dea_df)
            logger.info(f"成功添加DEA线（橙红色），数据点数：{len(dea_line_data)}")

        # 添加MACD柱状图
        if histogram_data:
            histogram_df = pd.DataFrame(histogram_data)
            macd_histogram = macd_chart.create_histogram()
            macd_histogram.set(histogram_df)
            logger.info(f"成功添加MACD柱状图，数据点数：{len(histogram_data)}")

        # 设置子图表样式和联动
        macd_chart.legend(visible=True)

        # 添加一些样式设置以确保更好的视觉效果
        try:
            # 设置MACD子图的网格线
            macd_chart.grid(vert_enabled=True, horz_enabled=True)

            # 确保子图的十字光标与主图同步
            macd_chart.crosshair(
                mode="normal", vert_color="#758494", vert_style="dotted", horz_color="#758494", horz_style="dotted"
            )
        except Exception as style_e:
            logger.debug(f"设置MACD子图样式时出现警告: {style_e}")

        logger.info("MACD子图与主图时间轴联动设置完成")

    except Exception as e:
        logger.warning(f"添加MACD指标失败: {e}")


def _add_trade_signals(chart: "Chart", bs: list[dict]) -> None:
    """添加买卖点标记

    :param chart: 图表对象
    :param bs: 买卖点数据
    """
    from datetime import datetime

    from loguru import logger

    if not bs:
        return

    try:
        for signal in bs:
            # 处理时间格式
            if hasattr(signal["dt"], "strftime"):
                marker_time = signal["dt"]
            else:
                # 尝试转换为datetime对象
                try:
                    marker_time = datetime.strptime(str(signal["dt"]), "%Y-%m-%d")
                except Exception:
                    marker_time = None

            if marker_time is None:
                continue

            # 根据操作类型设置不同的标记
            if signal["op"] in [Operate.LO]:  # 买入开仓
                chart.marker(
                    time=marker_time,
                    position="below",
                    shape="circle",
                    color="#4CAF50",
                    text=signal.get("op_desc", "买入"),
                )
            elif signal["op"] in [Operate.LE]:  # 卖出平仓
                chart.marker(
                    time=marker_time,
                    position="above",
                    shape="circle",
                    color="#F44336",
                    text=signal.get("op_desc", "卖出"),
                )
            elif signal["op"] in [Operate.SO]:  # 卖出开仓
                chart.marker(
                    time=marker_time,
                    position="above",
                    shape="arrow_down",
                    color="#FF9800",
                    text=signal.get("op_desc", "做空"),
                )
            elif signal["op"] in [Operate.SE]:  # 买入平仓
                chart.marker(
                    time=marker_time,
                    position="below",
                    shape="arrow_up",
                    color="#2196F3",
                    text=signal.get("op_desc", "平空"),
                )

        logger.info(f"成功添加{len(bs)}个买卖点标记")
    except Exception as e:
        logger.exception(f"添加买卖点标记失败: {e}")


def _setup_chart_style(chart: "Chart", title: str) -> None:
    """设置图表样式

    :param chart: 图表对象
    :param title: 图表标题
    """
    from loguru import logger

    try:
        # 设置图表样式
        chart.legend(visible=True)
        chart.watermark(title)

        # 可以添加更多样式设置
        # chart.layout(background_color='#FFFFFF', text_color='#000000')
        # chart.grid(vert_enabled=True, horz_enabled=True)

        logger.info(f"成功设置图表样式和标题: {title}")
    except Exception as e:
        logger.warning(f"设置图表样式失败: {e}")


def trading_view_kline(
    kline: list[dict],
    fx: list[dict] | None = None,
    bi: list[dict] | None = None,
    xd: list[dict] | None = None,
    bs: list[dict] | None = None,
    title: str = "缠中说禅K线分析",
    t_seq: list[int] | None = None,
    **kwargs,
) -> Optional["Chart"]:
    """使用 lightweight_charts 绘制缠中说禅K线分析结果

    注意：本函数提供基础的lightweight_charts集成。
    如需完整功能和更好的视觉效果，建议使用 kline_pro 函数。

    :param kline: K线数据
    :param fx: 分型识别结果
    :param bi: 笔识别结果
    :param xd: 线段识别结果
    :param bs: 买卖点
    :param title: 图表标题
    :param t_seq: 均线系统
    :return: lightweight_charts Chart对象 或 None
    """
    from loguru import logger

    # 设置默认值
    fx = fx or []
    bi = bi or []
    xd = xd or []
    bs = bs or []
    t_seq = t_seq or [5, 13, 21]

    use_streamlit = kwargs.get("use_streamlit", False)
    width = kwargs.get("width", 1400)
    height = kwargs.get("height", 580)

    # 准备K线数据
    df_data, chart = _prepare_kline_data(kline, use_streamlit, width, height)

    # 添加移动平均线
    _add_moving_averages(chart, kline, df_data, t_seq)

    # 添加分型标记
    _add_fractal_marks(chart, fx)

    # 添加笔线
    _add_bi_lines(chart, bi)

    # 添加线段
    _add_xd_lines(chart, xd)

    # 添加MACD指标
    _add_macd_indicator(chart, kline, df_data)

    # 添加买卖点标记
    _add_trade_signals(chart, bs)

    # 设置图表样式
    _setup_chart_style(chart, title)

    logger.info(f"创建 lightweight_charts 图表成功: {title}")
    logger.info(f"包含: K线({len(kline)}), 均线({len(t_seq)}), 分型({len(fx)}), 笔({len(bi)}), 线段({len(xd)}), MACD")

    return chart
