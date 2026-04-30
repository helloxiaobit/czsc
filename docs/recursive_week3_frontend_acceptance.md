# Week3 前端渲染验收清单

本页用于 Week3（递归多级别前端）闭环验收，按“执行命令 -> 预期结果”展开，便于复现。

## 1. 依赖准备

```bash
pip install -r requirements.txt
```

> 测试依赖里不包含前端渲染的可视化库，若出现 import 失败需补齐：

```bash
pip install pyecharts streamlit
```

## 2. 递归核心回归

```bash
python -m pytest test/test_recursive_payload.py test/test_recursive_levels.py test/test_recursive_segments.py test/test_recursive_signals.py test/test_recursive_zones.py -q
```

预期：8 passed

```bash
python -m pytest test/test_payload_and_plot.py -q
```

预期：3 passed（若无 `pyecharts`，本文件会在模块级别跳过）

## 3. 手工验证（前端）

```bash
streamlit run examples/recursive_multi_level_app.py
```

验收点：

- [x] 页面可正常启动且展示标题与侧边控制区
- [x] 可切换数据源（Mock / CSV）并触发重绘
- [x] 可配置的开关能控制显示：笔、线段、中枢、走势类型、信号、共振、背驰
- [x] 支持 `max_levels` 调整，至少能观察到 L0-L2 的叠加
- [x] 默认显示第一类共振（金色/品红闪烁色）
- [x] 勾选“开启第二类共振（背驰）”后，出现红色脉冲标记
- [x] 点击图例可查看各条线/信号归属
- [x] 支持 CSV 模板与样例 CSV 下载，用于快速复现
- [x] 提供“下载图表 HTML 快照”按钮（便于离线共享与复现）
- [x] 页面提示可通过浏览器对图表进行 PNG 截图

## 4. 关键文件清单

- `czsc/recursive/signals.py`：共振类别与背驰受控逻辑（`visual_role`）
- `czsc/recursive/analysis.py`：递归链路 `build_recursive_levels -> zones -> signals -> resonances`
- `czsc/utils/echarts_plot.py`：`kline_recursive` 渲染器
- `czsc/svc/recursive_chart.py`：服务层统一入口（payload + chart）
- `examples/recursive_multi_level_app.py`：前端页面与交互
- `test/test_payload_and_plot.py`：payload/chart 集成用例
