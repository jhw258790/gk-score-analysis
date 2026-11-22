# -*- coding: utf-8 -*-
"""把 nm_gk_score.csv 转成可直接执行的 SQL（建表 + 插入 + 窗口函数补本段人数）。

生成的 load_gk.sql 用 mysql 客户端执行：
    mysql -u root -p --default-character-set=utf8mb4 < load_gk.sql
"""
import csv
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CSV_PATH = os.path.join(os.path.dirname(ROOT), "真实数据", "nm_gk_score.csv")
OUT_SQL = os.path.join(HERE, "load_gk.sql")

HEAD = """-- 自动生成：内蒙古高考一分一段数据入库（2022-2025）
drop database if exists gaokao;
create database gaokao default charset utf8mb4 collate utf8mb4_general_ci;
use gaokao;

create table nm_gk_score (
    id          int auto_increment primary key,
    year        smallint    not null comment '年份',
    category    varchar(20) not null comment '科类',
    score       smallint    not null comment '分数',
    cumulative  int         not null comment '该分数及以上累计人数',
    band_count  int         null comment '本段人数',
    coverage    varchar(10) not null default 'full' comment '数据覆盖范围',
    key idx_year_cat_score (year, category, score)
) engine=InnoDB default charset=utf8mb4 comment='内蒙古高考一分一段（2022-2025）';
"""

TAIL = """
-- 用窗口函数计算本段人数：同组内上一行（更高分）的累计 - 本行累计
update nm_gk_score t
join (
    select id,
           cumulative - lag(cumulative, 1, 0) over (
               partition by year, category order by score desc) as band
    from nm_gk_score
) d on d.id = t.id
set t.band_count = greatest(d.band, 0);

select '--- 入库结果 ---' as '';
select year, category, count(*) as rows_, min(score) as min_score,
       max(score) as max_score, max(cumulative) as total_exam
from nm_gk_score
group by year, category
order by year, category;

select '--- 单调性校验（累计人数应随分数下降递增，异常行数应为 0）---' as '';
select count(*) as bad_rows from (
    select cumulative,
           lag(cumulative) over (partition by year, category order by score desc) as prev_cum
    from nm_gk_score
) t where prev_cum is not null and cumulative < prev_cum;
"""


def esc(s):
    return s.replace("\\", "\\\\").replace("'", "''")


def main():
    rows = []
    with open(CSV_PATH, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            rows.append((int(r["year"]), r["category"], int(r["score"]), int(r["cumulative"])))

    with open(OUT_SQL, "w", encoding="utf-8") as f:
        f.write(HEAD)
        for i in range(0, len(rows), 200):
            values = ",\n".join(
                "(%d,'%s',%d,%d,'full')" % (y, esc(c), s, cum)
                for y, c, s, cum in rows[i:i + 200])
            f.write("insert into nm_gk_score(year, category, score, cumulative, coverage) values\n%s;\n" % values)
        f.write(TAIL)

    print("已生成:", OUT_SQL, "%.0f KB，%d 行" % (os.path.getsize(OUT_SQL) / 1024, len(rows)))


if __name__ == "__main__":
    raise SystemExit(main())
