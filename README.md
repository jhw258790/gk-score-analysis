# 内蒙古高考一分一段数据分析（2022–2025）

> 采集公开的一分一段数据 → 入库 MySQL → SQL 统计分析 → ECharts 可视化。
> 数据全部来自公开渠道，每条记录可追溯到原始页面。

## 数据

| 项 | 值 |
|---|---|
| 年度 | 2022、2023、2024、2025 |
| 科类 | 10 个（文科/理科/历史类/物理类/两类专项） |
| 记录数 | **4375 条** 分数段记录 |
| 分数范围 | 200–704 分 |
| 来源 | 通辽市教育局（2025）、内蒙古新闻网、阳光高考转载（2022–2024） |

原始 HTML 保留在 `真实数据/` 下，便于复核；`真实数据/nm_gk_score.csv` 是清洗后的统一格式。

**已知局限**

- 2021 年公布的表格是图片，未能解析，故只覆盖四个年度
- 内蒙古 2025 年首年新高考，科类由「文科/理科」改为「历史类/物理类」，跨年同比时需手工对齐，`lag` 按科类名分组会断档
- 一分一段表只给累计人数，本段人数由差分得到（窗口函数 `lag`）

## 目录

```
数据采集与分析/
├── 真实数据/
│   ├── *.html            原始页面（可复核）
│   ├── build_csv.py      解析 HTML → nm_gk_score.csv
│   └── nm_gk_score.csv   统一格式数据（year, category, score, cumulative）
├── 项目代码/
│   ├── app.py            Flask 应用（采集/清洗/分析/可视化四段）
│   ├── db/
│   │   ├── init_gk.sql   建库建表语句
│   │   ├── build_load.py CSV → load_gk.sql（含窗口函数更新本段人数）
│   │   ├── analysis.sql  10 条分析 SQL（含 EXPLAIN 对比）
│   │   └── run_analysis.py 执行分析并导出 JSON
│   └── templates/        ECharts 页面
└── 实验报告/             课程实验报告 5 份
```

## 复现步骤

```bash
# 1. 解析原始页面，生成 CSV
python 真实数据/build_csv.py

# 2. 生成入库 SQL 并执行（需 MySQL 8）
python 项目代码/db/build_load.py
mysql -u root -p --default-character-set=utf8mb4 < 项目代码/db/load_gk.sql

# 3. 跑分析，结果写入 data/analysis_mysql.json
python 项目代码/db/run_analysis.py

# 4. 启动页面查看图表
python 项目代码/app.py
```

## 表结构

```sql
create table nm_gk_score (
    id          int auto_increment primary key,
    year        smallint    not null,   -- 年份
    category    varchar(20) not null,   -- 科类
    score       smallint    not null,   -- 分数
    cumulative  int         not null,   -- 该分数及以上累计人数
    band_count  int         null,       -- 本段人数（差分计算）
    key idx_year_cat_score (year, category, score)
);
```

## 分析结论（由 SQL 得出）

| 年份 | 科类 | 600 分以上 | 总人数 | 占比 |
|---|---|---|---|---|
| 2022 | 文科 | 95 | 28551 | 0.33% |
| 2022 | 理科 | 1384 | 74716 | 1.85% |
| 2023 | 文科 | 141 | 28783 | 0.49% |
| 2023 | 理科 | 1729 | 74996 | 2.31% |
| 2024 | 文科 | 279 | 29405 | 0.95% |
| 2024 | 理科 | 4322 | 83803 | 5.16% |
| 2025 | 历史类 | 1570 | 32644 | 4.81% |
| 2025 | 物理类 | 6349 | 83716 | 7.58% |

- 高分段集中度显著上升：2025 物理类 600 分以上占比 7.58%，比 2024 理科高 2.4 个百分点
- 竞争最激烈的分数段落在 400–450 分，单段人数过万
- 考生总量在 2024 年出现跳升（理科 7.5 万 → 8.4 万），与招生计划扩张有关

## 技术点

- **窗口函数**：`lag` 求本段人数与同比、`row_number` 取前 N、`rank` 找竞争最激烈分数段
- **索引**：`(year, category, score)` 联合索引，`EXPLAIN` 对比走索引与全表扫描
- **数据校验**：累计人数须随分数下降单调递增，校验异常 0 行
- **可视化**：Flask + ECharts，分析结果由 MySQL 导出 JSON 驱动
