-- ============================================================
-- 内蒙古高考一分一段数据分析（2022–2025，4375 行）
-- 用法：mysql -u root -p --default-character-set=utf8mb4 gaokao < analysis.sql
-- ============================================================
use gaokao;

-- Q1 各年度各科类考生规模（最高累计人数即该科类总人数）
select year, category, max(cumulative) as total_exam
from nm_gk_score
group by year, category
order by year, category;

-- Q2 各科类最高分及其位次
select year, category, max(score) as top_score,
       min(cumulative) as top_rank
from nm_gk_score
group by year, category
order by year, category;

-- Q3 每 50 分一档的人数分布（2025 物理类）
select floor(score / 50) * 50 as band_start,
       sum(band_count) as students
from nm_gk_score
where year = 2025 and category = '物理类'
group by band_start
order by band_start desc;

-- Q4 600 分以上人数占比（各年各主科类，用窗口函数算占比）
select year, category,
       sum(case when score >= 600 then band_count else 0 end) as above_600,
       max(cumulative) as total_exam,
       round(100.0 * sum(case when score >= 600 then band_count else 0 end)
             / max(cumulative), 2) as pct_above_600
from nm_gk_score
where category in ('文科', '理科', '历史类', '物理类')
group by year, category
order by year, category;

-- Q5 单科类年度对比：2025 物理类 vs 2024 理科 在同一分数上的位次差
select a.score,
       a.cumulative as r2025,
       b.cumulative as r2024,
       b.cumulative - a.cumulative as gap
from nm_gk_score a
join nm_gk_score b on b.score = a.score
where a.year = 2025 and a.category = '物理类'
  and b.year = 2024 and b.category = '理科'
  and a.score between 500 and 600
order by a.score desc
limit 10;

-- Q6 用 row_number 找每个科类分数最高的 3 个分数档
select * from (
    select year, category, score, band_count,
           row_number() over (partition by year, category order by score desc) as rn
    from nm_gk_score
) t
where rn <= 3
order by year, category, rn;

-- Q7 累计人数环比：同科类相邻年份在 550 分处的考生规模变化（窗口 lag）
select category, year, cumulative as cum_550,
       lag(cumulative) over (partition by category order by year) as prev_cum,
       cumulative - lag(cumulative) over (partition by category order by year) as diff
from nm_gk_score
where score = 550 and category in ('文科', '理科', '历史类', '物理类')
order by category, year;

-- Q8 本科线附近竞争最激烈的分数段（本段人数最多）
select year, category, score, band_count
from (
    select year, category, score, band_count,
           rank() over (partition by year, category order by band_count desc) as rk
    from nm_gk_score
) t
where rk = 1
order by year, category;

-- Q9 索引验证：对比走索引与全表扫描的执行计划
explain select sum(band_count) from nm_gk_score
where year = 2025 and category = '物理类' and score >= 600;

explain select sum(band_count) from nm_gk_score ignore index (idx_year_cat_score)
where year = 2025 and category = '物理类' and score >= 600;
