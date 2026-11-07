-- District level: a student who attended two schools counts once, with days combined.
with d as (
    select
        ssid,
        max(grade_level) as grade_level,
        max(grade_span) as grade_span,
        any_value(gender) as gender,
        any_value(race_ethnicity) as race_ethnicity,
        bool_and(coalesce(exempt, false)) as exempt,
        sum(expected_days) as expected_days,
        sum(days_absent) as days_absent,
        sum(days_absent_excused) as days_absent_excused,
        sum(days_absent_unexcused) as days_absent_unexcused,
        sum(days_absent_oss) as days_absent_oss
    from {{ ref('fct_student_school_year') }}
    group by ssid
)
select
    *,
    not exempt and expected_days >= {{ var('min_expected_days') }} as eligible,
    not exempt
        and expected_days >= {{ var('min_expected_days') }}
        and days_absent >= {{ var('chronic_threshold') }} * expected_days as chronically_absent
from d
