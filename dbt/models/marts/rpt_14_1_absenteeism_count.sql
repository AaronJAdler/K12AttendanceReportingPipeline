-- Shaped like CALPADS Report 14.1: unduplicated students with absence data and exemptions.
select
    school_code,
    grade_level,
    count(distinct ssid) filter (where not coalesce(exempt, false)) as students_with_absence_data,
    count(distinct ssid) filter (where exempt) as students_with_exemptions,
    count(distinct ssid) filter (where chronically_absent) as chronically_absent
from {{ ref('fct_student_school_year') }}
group by all
