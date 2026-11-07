-- Absence days by reason, among eligible students.
with students as (
    select 'S' as aggregate_level, school_code, eligible, days_absent,
           days_absent_excused, days_absent_unexcused, days_absent_oss
    from {{ ref('fct_student_school_year') }}
    union all
    select 'D', null, eligible, days_absent,
           days_absent_excused, days_absent_unexcused, days_absent_oss
    from {{ ref('fct_student_district_year') }}
)
select
    aggregate_level,
    school_code,
    count(*) as eligible_enrollment,
    round(avg(days_absent), 1) as avg_days_absent,
    round(100.0 * sum(days_absent_excused) / nullif(sum(days_absent), 0), 1) as excused_pct,
    round(100.0 * sum(days_absent_unexcused) / nullif(sum(days_absent), 0), 1) as unexcused_pct,
    round(100.0 * sum(days_absent_oss) / nullif(sum(days_absent), 0), 1) as oss_pct
from students
where eligible
group by all
