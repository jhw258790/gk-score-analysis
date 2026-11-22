# -*- coding: utf-8 -*-
"""解析各年份一分一段表 HTML，生成统一 CSV。

支持三种表格结构：
  2 列：分数 | 累计人数
  3 列：分数 | 本段人数 | 累计人数
  6 列：分数 | 人数 | 累计 | 分数 | 人数 | 累计（一行两组，左右半边）
"""
import csv
import os
import re

from lxml import html

BASE = r"D:\app\deepseek work\数据采集与分析\真实数据"
OUT = os.path.join(BASE, "nm_gk_score.csv")


def clean_cells(tr):
    out = []
    for td in tr.xpath("./td|./th"):
        s = "".join(td.itertext()).replace("\u00a0", " ").strip()
        out.append(s)
    return out


def score_of(s):
    m = re.match(r"^(\d{2,3})", s)
    return int(m.group(1)) if m else None


def rows_from_table(tbl):
    """产出 (score, cumulative)。"""
    for tr in tbl.xpath(".//tr"):
        cells = clean_cells(tr)
        if len(cells) == 6:
            for si, ci in ((0, 2), (3, 5)):
                sc, cum = score_of(cells[si]), re.sub(r"\D", "", cells[ci])
                if sc and cum:
                    yield sc, int(cum)
        elif len(cells) == 3:
            sc, cum = score_of(cells[0]), re.sub(r"\D", "", cells[2])
            if sc and cum:
                yield sc, int(cum)
        elif len(cells) == 2:
            sc, cum = score_of(cells[0]), re.sub(r"\D", "", cells[1])
            if sc and cum:
                yield sc, int(cum)


def collect(year, category, filename, table_index):
    doc = html.fromstring(open(os.path.join(BASE, filename), "rb").read())
    tables = doc.xpath("//table")
    if table_index >= len(tables):
        return []
    return [(year, category, s, c) for s, c in rows_from_table(tables[table_index])]


JOBS = [
    # 2025：通辽市教育局，4 个科类（8 张表是两份拷贝，取前 4）
    (2025, "历史类", "2025_tongliao.html", 0),
    (2025, "历史类（专项类）", "2025_tongliao.html", 1),
    (2025, "物理类", "2025_tongliao.html", 2),
    (2025, "物理类（专项类）", "2025_tongliao.html", 3),
    # 2023：同页含 2023 与 2022 文理
    (2023, "文科", "2023_gk100.html", 1),
    (2023, "理科", "2023_gk100.html", 2),
    (2022, "理科", "2023_gk100.html", 3),
    (2022, "文科", "2023_gk100.html", 4),
    # 2024：一行两组结构
    (2024, "理科", "2024_gk100.html", 0),
    (2024, "文科", "2024_gk100.html", 1),
]

all_rows = []
for job in JOBS:
    got = collect(*job)
    print("%d %-14s 解析 %d 行" % (job[0], job[1], len(got)))
    all_rows += got

uniq = sorted(set(all_rows), key=lambda r: (r[0], r[1], -r[2]))

from collections import Counter
print("\n按年/科类统计：")
for (y, c), n in sorted(Counter((r[0], r[1]) for r in uniq).items()):
    scores = [r[2] for r in uniq if r[0] == y and r[1] == c]
    print("  %d %-14s %3d 行  分数 %d~%d" % (y, c, n, min(scores), max(scores)))

with open(OUT, "w", encoding="utf-8-sig", newline="") as f:
    w = csv.writer(f)
    w.writerow(["year", "category", "score", "cumulative"])
    for r in uniq:
        w.writerow(r)
print("\n已写出:", OUT, "%.0f KB, %d 行" % (os.path.getsize(OUT) / 1024, len(uniq)))
