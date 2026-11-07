select * from {{ ref('mart_chronic_absenteeism') }}
where chronic_count > eligible_enrollment or eligible_enrollment < 0
