-- One row per student per school: attendance, eligibility and chronic status.
with enr as (
    select ssid, school_code, max(grade_level) as grade_level, min(start_date) as first_start
    from {{ ref('stg_senr') }}
    where enrollment_status in ('10', '30')
    group by 1, 2
),
info as (
    select ssid, gender, race_ethnicity
    from {{ ref('stg_sinf') }}
    qualify row_number() over (partition by ssid order by effective_date desc, line_no desc) = 1
),
att as (
    select
        e.ssid,
        e.school_code,
        e.grade_level,
        case
            when e.grade_level in ('TK', 'KN') then 'GRTKKN'
            when e.grade_level in ('01', '02', '03') then 'GR13'
            when e.grade_level in ('04', '05', '06') then 'GR46'
            when e.grade_level in ('07', '08') then 'GR78'
            else 'GR912'
        end as grade_span,
        coalesce(i.gender, 'GZ') as gender,
        coalesce(i.race_ethnicity, 'RD') as race_ethnicity,
        coalesce(s.exemption_indicator = 'Y', false) as exempt,
        s.expected_days,
        s.days_attended,
        s.days_absent_excused,
        s.days_absent_unexcused,
        s.days_absent_oss,
        s.days_absent_excused + s.days_absent_unexcused + s.days_absent_oss as days_absent
    from enr e
    join {{ ref('stg_stas') }} s using (ssid, school_code)
    left join info i using (ssid)
)
select
    *,
    not coalesce(exempt, false) and expected_days >= {{ var('min_expected_days') }} as eligible,
    not coalesce(exempt, false)
        and expected_days >= {{ var('min_expected_days') }}
        and days_absent >= {{ var('chronic_threshold') }} * expected_days as chronically_absent
from att
