# -*- coding: utf-8 -*-
"""在 MySQL 上执行统计分析，控制台打印 + 导出 JSON 供前端图表使用。

用法：python run_analysis.py
依赖：pymysql
"""
import json
import os

import pymysql

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT_JSON = os.path.join(ROOT, "data", "analysis_mysql.json")

MYSQL = dict(host="127.0.0.1", port=3306, user="root", password="258790",
             database="gaokao", charset="utf8mb4", cursorclass=pymysql.cursors.DictCursor)

QUERIES = {
    "规模": """
        select year, category, max(cumulative) as total_exam
        from nm_gk_score group by year, category order by year, category
    """,
    "最高分": """
        select year, category, max(score) as top_score, min(cumulative) as top_rank
        from nm_gk_score group by year, category order by year, category
    """,
    "分数段分布_2025物理类": """
        select floor(score / 50) * 50 as band_start, sum(band_count) as students
        from nm_gk_score where year = 2025 and category = '物理类'
        group by band_start order by band_start
    """,
    "600分以上占比": """
        select year, category,
               sum(case when score >= 600 then band_count else 0 end) as above_600,
               max(cumulative) as total_exam,
               round(100.0 * sum(case when score >= 600 then band_count else 0 end)
                     / max(cumulative), 2) as pct_above_600
        from nm_gk_score
        where category in ('文科','理科','历史类','物理类')
        group by year, category order by year, category
    """,
    "位次同比": """
        select category, year, cumulative as cum_550,
               lag(cumulative) over (partition by category order by year) as prev_cum,
               cumulative - lag(cumulative) over (partition by category order by year) as diff
        from nm_gk_score
        where score = 550 and category in ('文科','理科','历史类','物理类')
        order by category, year
    """,
    "竞争最激烈分数段": """
        select year, category, score, band_count from (
            select year, category, score, band_count,
                   rank() over (partition by year, category order by band_count desc) as rk
            from nm_gk_score
        ) t where rk = 1 order by year, category
    """,
    "各科类前三高分档": """
        select * from (
            select year, category, score, band_count,
                   row_number() over (partition by year, category order by score desc) as rn
            from nm_gk_score
        ) t where rn <= 3 order by year, category, rn
    """,
}


def main():
    conn = pymysql.connect(**MYSQL)
    result = {}
    try:
        with conn.cursor() as cur:
            for name, sql in QUERIES.items():
                cur.execute(sql)
                rows = cur.fetchall()
                result[name] = rows
                print("\n=== %s（%d 行）===" % (name, len(rows)))
                for r in rows[:8]:
                    print("   ", r)
    finally:
        conn.close()

    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2,
                  default=lambda o: float(o) if hasattr(o, "as_tuple") else str(o))
    print("\n已导出：%s" % OUT_JSON)


if __name__ == "__main__":
    raise SystemExit(main())
