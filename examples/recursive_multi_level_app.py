"""Streamlit 示例：递归多级别结构可视化。"""

from __future__ import annotations

from datetime import datetime
from io import BytesIO
from pathlib import Path
import os
import re
import sys
import tempfile
import types
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _install_rs_czsc_stub() -> None:
    """当环境缺少 rs_czsc 时，用轻量桩保证前端可启动。"""
    if "rs_czsc" in sys.modules:
        return

    try:
        import rs_czsc
        sys.modules["rs_czsc"] = rs_czsc
        return
    except ModuleNotFoundError:
        os.environ["CZSC_USE_PYTHON"] = "1"
        pass

    msg = (
        "缺少 rs_czsc 运行依赖：请在环境中执行 `pip install rs_czsc`。\n"
        "当前前端会退化到可运行模式，仅用于界面可视化演示。"
    )

    def _missing_callable(*_: Any, **__: Any) -> None:
        raise ModuleNotFoundError(msg)

    class _MissingWeightBacktest:
        def __init__(self, *_: Any, **__: Any) -> None:
            raise ModuleNotFoundError(msg)

    stub = types.ModuleType("rs_czsc")
    stub.__version__ = "0.0.0"
    stub.WeightBacktest = _MissingWeightBacktest
    stub.daily_performance = _missing_callable
    stub.top_drawdowns = _missing_callable
    sys.modules["rs_czsc"] = stub


_install_rs_czsc_stub()

import numpy as np
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from czsc.py.enum import Freq
from czsc.svc.recursive_chart import (
    dataframe_to_raw_bars,
    build_default_level_specs,
    build_recursive_chart_from_bars,
)


def _build_mock_kline(
    symbol: str,
    *,
    freq: str = "1m",
    bars: int = 400,
    seed: int = 17,
) -> pd.DataFrame:
    """生成用于演示的模拟 K 线。"""
    rng = np.random.default_rng(seed)
    bars = max(30, int(bars))
    freq_map = {"1m": "1min", "5m": "5min", "15m": "15min", "30m": "30min", "60m": "60min", "1h": "60min", "120m": "120min"}
    p = pd.date_range(end=datetime.now(), periods=bars, freq=freq_map.get(freq, "1min"))
    steps = rng.normal(0, 1.2, size=bars).cumsum()
    close = 100 + steps
    open_ = close + rng.normal(0, 0.35, size=bars)
    high = close + np.abs(rng.normal(0.8, 0.35, size=bars))
    low = close - np.abs(rng.normal(0.8, 0.35, size=bars))
    vol = np.clip(rng.integers(50, 500, size=bars), 1, None)
    amount = vol * close
    return pd.DataFrame(
        {
            "dt": p,
            "open": open_,
            "close": close,
            "high": np.maximum(open_, high),
            "low": np.minimum(close, low),
            "vol": vol,
            "amount": amount,
        }
    )


def _csv_template() -> str:
    template = pd.DataFrame(
        {
            "dt": [datetime.now() - pd.Timedelta(minutes=5), datetime.now()],
            "open": [100.0, 101.2],
            "close": [101.0, 101.8],
            "high": [101.4, 102.0],
            "low": [99.9, 100.7],
            "vol": [1000, 1000],
            "amount": [101000, 101800],
        }
    )
    return template.to_csv(index=False)


def _sample_csv(symbol: str, *, freq: str = "1m") -> str:
    return _build_mock_kline(symbol=symbol, freq=freq, bars=180, seed=42).to_csv(index=False)


def _to_chart_html(chart) -> bytes:
    with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as fp:
        html_path = Path(fp.name)
    try:
        chart.render(str(html_path))
        return html_path.read_bytes()
    finally:
        html_path.unlink(missing_ok=True)


def _to_safe_filename(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9._-]", "_", value) or "recursive_chart"


def _to_bars(df: pd.DataFrame, *, symbol: str, freq: str | Freq) -> list:
    """DataFrame 转 RawBar 列表。"""
    return dataframe_to_raw_bars(df, symbol=symbol, freq=freq)


def main() -> None:
    st.set_page_config(layout="wide", page_title="CZSC递归可视化")
    st.title("CZSC 递归多级别前端集成示例")
    st.caption("底层 K 线 → 逐级笔/线段压缩 → 上一级结构递归可视化")

    with st.sidebar:
        st.header("输入参数")
        symbol = st.text_input("股票/期货代码", value="000001")
        freq = st.selectbox("底层频率", ["1m", "5m", "15m", "30m", "60m", "1h", "120m"], index=0)
        data_mode = st.radio("数据源", ["mock（内置模拟）", "CSV 上传"])

        if data_mode.startswith("mock"):
            bars = st.slider("基础K线数量", 60, 2000, 800, 20)
            seed = st.slider("模拟随机种子", 1, 999, 17)
        else:
            bars = 0
            seed = 17

        st.divider()
        st.subheader("CSV 参数")
        max_csv_rows = st.slider("CSV 最大读取行数（避免超时）", 1000, 20000, 8000, 1000)

        st.divider()
        st.subheader("递归参数")
        max_levels = st.slider("显示层级数量", 1, 6, 3)
        min_signals = st.number_input("每层最低信号条数（0表示不裁剪）", min_value=0, max_value=10, value=0, step=1)
        min_bi_count = st.slider("每层最小笔数", 2, 21, 7)
        enable_divergence = st.checkbox("开启第二类共振（背驰）", value=False)

        st.divider()
        st.subheader("显示开关")
        show_bi = st.checkbox("显示笔", value=True)
        show_xd = st.checkbox("显示线段", value=True)
        show_zones = st.checkbox("显示中枢", value=True)
        show_trend_types = st.checkbox("显示走势类型", value=True)
        show_signals = st.checkbox("显示买卖点", value=True)
        show_resonance = st.checkbox("显示共振信号", value=True)
        show_divergence = st.checkbox("突出背驰", value=True)
        show_series_legend = st.checkbox("显示图例", value=True)

    if data_mode.startswith("mock"):
        source_df = _build_mock_kline(symbol=symbol, freq=freq, bars=bars, seed=seed)
    else:
        uploaded = st.file_uploader("上传 CSV 文件（dt,open,high,low,close，vol/volume/amount 可选）", type=["csv"])
        template_csv = _csv_template()
        sample_csv = _sample_csv(symbol=symbol, freq=freq)
        use_sample = st.button("直接加载样例 CSV（不上传）", help="使用内置样例数据快速启动示例")

        st.caption("CSV 导入说明：字段必须包含 dt/open/close/high/low，vol 或 volume 或 amount 为可选字段。")
        col_template, col_sample = st.columns(2)
        col_template.download_button(
            "下载 CSV 模板",
            data=template_csv.encode("utf-8"),
            file_name="recursive_chart_template.csv",
            mime="text/csv",
        )
        col_sample.download_button(
            "下载样例 CSV",
            data=sample_csv.encode("utf-8"),
            file_name=f"{symbol}_{freq}_sample.csv",
            mime="text/csv",
        )

        if uploaded is not None:
            if uploaded.size and uploaded.size > 20 * 1024 * 1024:
                st.warning("CSV 文件较大，已自动按前 N 行读取，避免前端超时（可在侧边栏调大）")
            try:
                source_df = pd.read_csv(BytesIO(uploaded.getvalue()), nrows=max_csv_rows)
            except Exception as exc:
                st.error(f"CSV 解析失败: {exc}")
                return
        elif use_sample:
            source_df = pd.read_csv(BytesIO(sample_csv.encode("utf-8")))
        else:
            st.info("请上传 CSV 后继续")
            return

        st.success(f"已加载 CSV: {len(source_df)} 行")
        st.caption(f"列名: {', '.join(source_df.columns.tolist())}")

        if source_df.empty:
            st.warning("CSV 中没有可用行")
            return

    if source_df.empty:
        st.warning("输入数据为空")
        return

    try:
        freq_enum = Freq.F1
        if freq == "1m":
            freq_enum = Freq.F1
        elif freq == "5m":
            freq_enum = Freq.F5
        elif freq == "15m":
            freq_enum = Freq.F15
        elif freq == "30m":
            freq_enum = Freq.F30
        elif freq in {"60m", "1h"}:
            freq_enum = Freq.F60
        elif freq == "120m":
            freq_enum = Freq.F120

        bars_data = _to_bars(source_df, symbol=symbol, freq=freq_enum)
        payload, chart = build_recursive_chart_from_bars(
            bars=bars_data,
            symbol=symbol,
            max_levels=max_levels,
            min_signals=min_signals,
            min_bi_count=min_bi_count,
            enable_divergence=enable_divergence,
            base_freq=freq_enum,
            level_specs=build_default_level_specs(max_levels=max_levels, min_bi_count=min_bi_count),
            chart_title=f"{symbol} 递归多级别结构图",
            show_bi=show_bi,
            show_xd=show_xd,
            show_zones=show_zones,
            show_trend_types=show_trend_types,
            show_signals=show_signals,
            show_resonance=show_resonance,
            show_divergence=show_divergence,
            show_series_legend=show_series_legend,
        )
    except Exception as exc:
        st.error(f"构建失败: {exc}")
        return

    st.subheader("图表")
    chart_embed_html = chart.render_embed()
    components.html(chart_embed_html, height=900, scrolling=True)

    chart_snapshot = _to_chart_html(chart)
    st.download_button(
        "下载图表 HTML 快照",
        data=chart_snapshot,
        file_name=f"{_to_safe_filename(symbol)}_recursive_chart_snapshot.html",
        mime="text/html",
        help="下载当前视图为完整 HTML，便于离线复现。",
    )
    st.caption("若需图片截图，可在浏览器内对图表区域直接右键另存为 PNG。")

    with st.expander("Payload 元数据"):
        st.json(payload.get("meta", {}))
    st.caption(f"共振信号: {len(payload.get('resonance_signals', []))}")


if __name__ == "__main__":
    main()
