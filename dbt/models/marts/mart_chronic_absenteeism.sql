-- Chronic absenteeism by entity and CDE reporting category (TA, gender, race, grade span).
-- Unsuppressed counts: suppression is applied in the publish step.
{% set dims = ["'TA'", 'gender', 'race_ethnicity', 'grade_span'] %}
with students as (
    select 'S' as aggregate_level, school_code, * exclude (school_code)
    from {{ ref('fct_student_school_year') }}
    union all by name
    select 'D' as aggregate_level, null as school_code, *
    from {{ ref('fct_student_district_year') }}
),
long as (
    {% for d in dims %}
    select aggregate_level, school_code, {{ d }} as reporting_category, eligible, chronically_absent
    from students
    {% if not loop.last %}union all{% endif %}
    {% endfor %}
)
select
    aggregate_level,
    school_code,
    reporting_category,
    count(*) filter (where eligible) as eligible_enrollment,
    count(*) filter (where chronically_absent) as chronic_count,
    round(100.0 * count(*) filter (where chronically_absent)
          / nullif(count(*) filter (where eligible), 0), 1) as chronic_rate_pct
from long
group by all
