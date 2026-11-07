-- The district TA row must equal the count of eligible students in the district fact.
select m.eligible_enrollment, f.n
from {{ ref('mart_chronic_absenteeism') }} m
cross join (select count(*) filter (where eligible) n from {{ ref('fct_student_district_year') }}) f
where m.aggregate_level = 'D' and m.reporting_category = 'TA' and m.eligible_enrollment <> f.n
