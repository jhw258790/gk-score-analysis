-- 内蒙古高考一分一段数据表
-- 数据来源：通辽市教育局（2025）、内蒙古新闻网/阳光高考转载（2022–2024）
-- coverage: full=全分段（200 分起）  partial=仅本科线以上片段

drop database if exists gaokao;
create database gaokao default charset utf8mb4 collate utf8mb4_general_ci;
use gaokao;

create table nm_gk_score (
    id          int auto_increment primary key,
    year        smallint    not null comment '年份',
    category    varchar(20) not null comment '科类：文科/理科/历史类/物理类/专项类',
    score       smallint    not null comment '分数',
    cumulative  int         not null comment '该分数及以上累计人数',
    band_count  int         null comment '本段人数（由累计差分计算）',
    coverage    varchar(10) not null default 'full' comment 'full=全分段 partial=仅本科线以上',
    key idx_year_cat_score (year, category, score)
) engine=InnoDB default charset=utf8mb4 comment='内蒙古高考一分一段（2022-2025）';
